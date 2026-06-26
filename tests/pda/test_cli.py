import json
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import pytest

from pda import cli
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

    def factory(*, config: object, project_root: object, package: object) -> Callable[..., ModuleGraph]:
        captured.update(config=config, project_root=project_root, package=package)

        def run(paths: object = None, *, refresh: bool = False) -> ModuleGraph:
            captured["paths"] = paths
            return graph

        return run

    monkeypatch.setattr(cli, attr, factory)
    return captured


class TestAnalyze:
    def test_default_output_and_paths(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        captured = _patch(monkeypatch, "ModuleImportsAnalyzer", _graph([("mypkg.a", "mypkg.b")]))
        monkeypatch.chdir(tmp_path)

        code = cli.main(["analyze", str(tmp_path), "mypkg"])

        assert code == 0
        assert captured["project_root"] == tmp_path
        assert captured["package"] == "mypkg"
        assert captured["paths"] == [tmp_path]

        data = json.loads((tmp_path / "mypkg-imports.json").read_text(encoding="utf-8"))
        assert {node["id"] for node in data["nodes"]} == {"mypkg.a", "mypkg.b"}

    def test_custom_output_and_explicit_paths(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        captured = _patch(monkeypatch, "ModuleImportsAnalyzer", _graph([("mypkg.a", "mypkg.b")]))
        output = tmp_path / "graph.json"

        code = cli.main(["analyze", str(tmp_path), "mypkg", "--paths", "a.py, b.py", "--output", str(output)])

        assert code == 0
        assert output.exists()
        assert captured["paths"] == [Path("a.py"), Path("b.py")]


class TestCollect:
    def test_default_output_with_package(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        captured = _patch(monkeypatch, "ModulesCollector", _graph([("mypkg", "mypkg.sub")]))
        monkeypatch.chdir(tmp_path)

        code = cli.main(["collect", str(tmp_path), "mypkg"])

        assert code == 0
        assert captured["project_root"] == tmp_path
        assert captured["package"] == "mypkg"
        assert (tmp_path / "mypkg-modules.json").exists()

    def test_default_output_without_arguments(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        captured = _patch(monkeypatch, "ModulesCollector", _graph([("os", "os.path")]))
        monkeypatch.chdir(tmp_path)

        code = cli.main(["collect"])

        assert code == 0
        assert captured["project_root"] is None
        assert captured["package"] is None
        assert (tmp_path / "modules.json").exists()

    def test_project_root_without_package_is_rejected(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)

        code = cli.main(["collect", str(tmp_path)])

        assert code == 2
        assert list(tmp_path.glob("*.json")) == []


class TestConfigFlags:
    def test_analyze_defaults_when_no_flags(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        captured = _patch(monkeypatch, "ModuleImportsAnalyzer", _graph([("a", "b")]))
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
        monkeypatch.chdir(tmp_path)

        assert cli.main(["analyze", str(tmp_path), "mypkg", "--collapse-level", "-1"]) == 1


class TestErrors:
    def test_runtime_error_returns_one(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        def action(*, config: object, project_root: object, package: object) -> Callable[..., ModuleGraph]:
            def run(paths: Optional[object] = None, *, refresh: bool = False) -> ModuleGraph:
                raise ValueError("no modules found")

            return run

        monkeypatch.setattr(cli, "ModuleImportsAnalyzer", action)

        assert cli.main(["analyze", str(tmp_path), "mypkg"]) == 1

    def test_missing_subcommand_exits(self) -> None:
        with pytest.raises(SystemExit):
            cli.main([])
