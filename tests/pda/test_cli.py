import json
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import pytest

from pda import cli
from pda.cli import commands, output
from pda.models import ModuleGraph, ModuleNode
from pda.specification import CategorizedModule, ModuleCategory, UnavailableModule


def _graph(edges: List[Tuple[str, str]]) -> ModuleGraph:
    graph = ModuleGraph()
    nodes: Dict[str, ModuleNode] = {}
    for source, target in edges:
        for name in (source, target):
            module = CategorizedModule(module=UnavailableModule(name=name), category=ModuleCategory.LOCAL)
            nodes.setdefault(name, ModuleNode(module, qualified_name=True))
        graph.add_edge(nodes[source], nodes[target])

    return graph


def _patch(monkeypatch: pytest.MonkeyPatch, attr: str, graph: ModuleGraph) -> Dict[str, object]:
    captured: Dict[str, object] = {}

    def factory(
        *,
        config: object,
        project_root: object,
        root_module_name: object,
        source_roots: object = None,
        local_boundary: object = None,
    ) -> Callable[..., ModuleGraph]:
        captured.update(
            config=config,
            project_root=project_root,
            root_module_name=root_module_name,
            source_roots=source_roots,
            local_boundary=local_boundary,
        )

        def run(paths: object = None, *, refresh: bool = False) -> ModuleGraph:
            captured["paths"] = paths
            return graph

        return run

    monkeypatch.setattr(commands, attr, factory)
    return captured


def _write_package_root(source_root: Path, name: str = "mypkg") -> Path:
    package = source_root / name
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    return package


class TestAnalyze:
    def test_default_output_and_paths(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        captured = _patch(monkeypatch, "ModuleImportsAnalyzer", _graph([("mypkg.a", "mypkg.b")]))
        package = _write_package_root(tmp_path)
        monkeypatch.chdir(tmp_path)

        code = cli.main(["analyze", str(tmp_path), "mypkg"])

        assert code == 0
        assert captured["project_root"] == tmp_path
        assert captured["root_module_name"] == "mypkg"
        assert captured["source_roots"] is None
        assert captured["local_boundary"] is None
        assert captured["paths"] == [package]

        data = json.loads((tmp_path / "mypkg-imports.json").read_text(encoding="utf-8"))
        assert {node["id"] for node in data["nodes"]} == {"mypkg.a", "mypkg.b"}

    def test_custom_output_and_explicit_paths(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        captured = _patch(monkeypatch, "ModuleImportsAnalyzer", _graph([("mypkg.a", "mypkg.b")]))
        output = tmp_path / "graph.json"

        code = cli.main(["analyze", str(tmp_path), "mypkg", "--paths", "a.py, b.py", "--output", str(output)])

        assert code == 0
        assert output.exists()
        assert captured["paths"] == [Path("a.py"), Path("b.py")]

    def test_source_roots_become_default_paths(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        captured = _patch(monkeypatch, "ModuleImportsAnalyzer", _graph([("mypkg.a", "mypkg.b")]))
        source_root = tmp_path / "src"
        package = _write_package_root(source_root)
        monkeypatch.chdir(tmp_path)

        code = cli.main(["analyze", str(tmp_path), "mypkg", "--source-roots", "src"])

        assert code == 0
        assert captured["source_roots"] == (Path("src"),)
        assert captured["paths"] == [package]


class TestCollect:
    def test_default_output_with_root_module(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        captured = _patch(monkeypatch, "ModulesCollector", _graph([("mypkg", "mypkg.sub")]))
        monkeypatch.chdir(tmp_path)

        code = cli.main(["collect", str(tmp_path), "mypkg"])

        assert code == 0
        assert captured["project_root"] == tmp_path
        assert captured["root_module_name"] == "mypkg"
        assert (tmp_path / "mypkg-modules.json").exists()

    def test_source_roots_are_passed_to_collector(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        captured = _patch(monkeypatch, "ModulesCollector", _graph([("mypkg", "mypkg.sub")]))
        monkeypatch.chdir(tmp_path)

        code = cli.main(
            ["collect", str(tmp_path), "mypkg", "--source-roots", "src,lib", "--local-boundary", str(tmp_path)]
        )

        assert code == 0
        assert captured["source_roots"] == (Path("src"), Path("lib"))
        assert captured["local_boundary"] == tmp_path

    def test_default_output_without_arguments(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        captured = _patch(monkeypatch, "ModulesCollector", _graph([("os", "os.path")]))
        monkeypatch.chdir(tmp_path)

        code = cli.main(["collect"])

        assert code == 0
        assert captured["project_root"] is None
        assert captured["root_module_name"] is None
        assert (tmp_path / "modules.json").exists()

    def test_project_root_without_root_module_is_rejected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)

        code = cli.main(["collect", str(tmp_path)])

        assert code == 2
        assert list(tmp_path.glob("*.json")) == []

    def test_source_roots_without_project_root_are_rejected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)

        code = cli.main(["collect", "--source-roots", "src"])

        assert code == 2
        assert list(tmp_path.glob("*.json")) == []


class TestConfigFlags:
    def test_analyze_defaults_when_no_flags(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        captured = _patch(monkeypatch, "ModuleImportsAnalyzer", _graph([("a", "b")]))
        _write_package_root(tmp_path)
        monkeypatch.chdir(tmp_path)

        cli.main(["analyze", str(tmp_path), "mypkg"])

        config = captured["config"]
        assert config.stdlib_depth == 1
        assert config.hide_private is True
        assert config.collapse_level is None
        assert config.unify_nodes is True

    def test_analyze_flat_flags_override_nested_and_top_fields(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured = _patch(monkeypatch, "ModuleImportsAnalyzer", _graph([("a", "b")]))
        _write_package_root(tmp_path)
        monkeypatch.chdir(tmp_path)

        cli.main(
            [
                "analyze",
                str(tmp_path),
                "mypkg",
                "--collapse-level",
                "2",
                "--stdlib-depth",
                "0",
                "--no-hide-private",
                "--qualified-names",
                "--unify-nodes",
                "--sort-method",
                "topological",
            ]
        )

        config = captured["config"]
        assert config.collapse_level == 2
        assert config.stdlib_depth == 0
        assert config.hide_private is False
        assert config.qualified_names is True
        assert config.unify_nodes is True
        assert config.sort_method == "topological"
        assert config.external_depth == 1

    def test_collect_shared_flags(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        captured = _patch(monkeypatch, "ModulesCollector", _graph([("a", "b")]))
        monkeypatch.chdir(tmp_path)

        cli.main(["collect", str(tmp_path), "mypkg", "--external-depth", "1", "--qualified-names"])

        config = captured["config"]
        assert config.external_depth == 1
        assert config.qualified_names is True

    def test_collect_rejects_imports_only_flag(self, tmp_path: Path) -> None:
        with pytest.raises(SystemExit):
            cli.main(["collect", str(tmp_path), "mypkg", "--sort-method", "auto"])

    def test_invalid_collapse_level_returns_one(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch(monkeypatch, "ModuleImportsAnalyzer", _graph([("a", "b")]))
        _write_package_root(tmp_path)
        monkeypatch.chdir(tmp_path)

        assert cli.main(["analyze", str(tmp_path), "mypkg", "--collapse-level", "-1"]) == 1


class TestErrors:
    def test_missing_default_analysis_target_returns_one(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch(monkeypatch, "ModuleImportsAnalyzer", _graph([("a", "b")]))

        assert cli.main(["analyze", str(tmp_path), "missing_pkg"]) == 1

    def test_runtime_error_returns_one(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        def action(
            *,
            config: object,
            project_root: object,
            root_module_name: object,
            source_roots: object = None,
            local_boundary: object = None,
        ) -> Callable[..., ModuleGraph]:
            def run(paths: Optional[object] = None, *, refresh: bool = False) -> ModuleGraph:
                raise ValueError("no modules found")

            return run

        monkeypatch.setattr(commands, "ModuleImportsAnalyzer", action)
        _write_package_root(tmp_path)

        assert cli.main(["analyze", str(tmp_path), "mypkg"]) == 1

    def test_missing_subcommand_exits(self) -> None:
        with pytest.raises(SystemExit):
            cli.main([])


class TestFormatResolution:
    def test_extension_selects_format(self) -> None:
        assert output.resolve_format(Path("graph.json"), None) == "json"
        assert output.resolve_format(Path("graph.html"), None) == "html"
        assert output.resolve_format(Path("graph.htm"), None) == "html"

    def test_explicit_format_wins_over_extension(self) -> None:
        assert output.resolve_format(Path("graph.json"), "html") == "html"
        assert output.resolve_format(Path("graph.html"), "json") == "json"

    def test_unsupported_extension_rejected(self) -> None:
        with pytest.raises(ValueError, match="Unsupported output extension"):
            output.resolve_format(Path("graph.txt"), None)

        with pytest.raises(ValueError, match="Unsupported output extension"):
            output.resolve_format(Path("graph.txt"), "html")

    def test_missing_extension_defaults_to_format_or_json(self) -> None:
        assert output.resolve_format(Path("graph"), None) == "json"
        assert output.resolve_format(Path("graph"), "html") == "html"

    def test_default_output_name_follows_format(self) -> None:
        assert output.resolve_output(None, None, "mypkg-imports") == (Path("mypkg-imports.json"), "json")
        assert output.resolve_output(None, "html", "mypkg-imports") == (Path("mypkg-imports.html"), "html")


class TestHtmlOutput:
    def test_analyze_writes_self_contained_html(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch(monkeypatch, "ModuleImportsAnalyzer", _graph([("mypkg.a", "mypkg.b")]))
        _write_package_root(tmp_path)
        output = tmp_path / "graph.html"

        code = cli.main(["analyze", str(tmp_path), "mypkg", "--output", str(output)])

        assert code == 0
        html = output.read_text(encoding="utf-8")
        assert "<html" in html.lower()
        assert 'src="lib/' not in html and 'href="lib/' not in html
        assert "vis-network" in html and len(html) > 200_000

    def test_format_html_overrides_json_extension(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch(monkeypatch, "ModuleImportsAnalyzer", _graph([("mypkg.a", "mypkg.b")]))
        _write_package_root(tmp_path)
        output = tmp_path / "graph.json"

        code = cli.main(["analyze", str(tmp_path), "mypkg", "--output", str(output), "--format", "html"])

        assert code == 0
        assert "<html" in output.read_text(encoding="utf-8").lower()

    def test_unsupported_extension_returns_one(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch(monkeypatch, "ModuleImportsAnalyzer", _graph([("mypkg.a", "mypkg.b")]))
        _write_package_root(tmp_path)

        assert cli.main(["analyze", str(tmp_path), "mypkg", "--output", str(tmp_path / "graph.txt")]) == 1

    def test_invalid_layout_exits(self, tmp_path: Path) -> None:
        with pytest.raises(SystemExit):
            cli.main(["analyze", str(tmp_path), "mypkg", "--layout", "bogus"])

    def test_invalid_theme_exits(self, tmp_path: Path) -> None:
        with pytest.raises(SystemExit):
            cli.main(["analyze", str(tmp_path), "mypkg", "--theme", "bogus"])

    def test_collect_writes_html(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch(monkeypatch, "ModulesCollector", _graph([("mypkg", "mypkg.sub")]))
        output = tmp_path / "modules.html"

        code = cli.main(["collect", str(tmp_path), "mypkg", "--output", str(output)])

        assert code == 0
        assert "<html" in output.read_text(encoding="utf-8").lower()
