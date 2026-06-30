import json
from pathlib import Path
from typing import Any, Set, Tuple

import pytest

from pda import cli
from pda.analyzer import ModuleImportsAnalyzer
from pda.analyzer.imports.report import build_cycle_report
from pda.config import ModuleImportsAnalyzerConfig
from pda.exceptions import PDADependencyCycleError
from pda.models import ModuleGraph, module_pyvis_converter

PACKAGES = Path(__file__).parent / "packages"


def _analyze(root_module_name: str, **overrides: Any) -> ModuleGraph:
    config = ModuleImportsAnalyzerConfig(**overrides)
    analyzer = ModuleImportsAnalyzer(config=config, project_root=PACKAGES, root_module_name=root_module_name)
    return analyzer(PACKAGES / root_module_name)


def _edges(graph: ModuleGraph) -> Set[Tuple[str, str]]:
    return {(source.identifier, target.identifier) for source, target in graph.edges}


class TestCycleInGraph:
    def test_two_module_cycle_present_in_both_directions(self) -> None:
        graph = _analyze("cyclic_two")

        assert graph.has_cycles
        edges = _edges(graph)
        assert ("cyclic_two.a", "cyclic_two.b") in edges
        assert ("cyclic_two.b", "cyclic_two.a") in edges

    def test_acyclic_control_is_dag(self) -> None:
        assert not _analyze("acyclic").has_cycles

    def test_three_module_cycle_is_one_component(self) -> None:
        nodes = _analyze("cyclic_three").to_dict()["nodes"]

        in_cycle = {node["id"] for node in nodes if node.get("in_cycle")}
        components = {node["component"] for node in nodes if node.get("in_cycle")}
        assert {"cyclic_three.a", "cyclic_three.b", "cyclic_three.c"} <= in_cycle
        assert len(components) == 1

    def test_acyclic_export_omits_cycle_fields(self) -> None:
        nodes = _analyze("acyclic").to_dict()["nodes"]

        assert all("in_cycle" not in node and "component" not in node for node in nodes)


class TestFailOnCycle:
    def test_default_does_not_raise(self) -> None:
        assert _analyze("cyclic_two").has_cycles

    def test_fail_on_cycle_raises_with_report(self) -> None:
        with pytest.raises(PDADependencyCycleError, match="cycle"):
            _analyze("cyclic_two", fail_on_cycle=True)


class TestCycleReportConfig:
    def test_examples_zero_keeps_membership(self) -> None:
        report = build_cycle_report(_analyze("cyclic_three"), length_bound=8, max_examples=0)

        assert report["cycle_count"] == 1
        assert report["components"][0]["examples"] == []
        assert len(report["components"][0]["modules"]) == 3

    def test_invalid_cycle_length_bound_rejected(self) -> None:
        with pytest.raises(ValueError, match="cycle_length_bound"):
            ModuleImportsAnalyzerConfig(cycle_length_bound=0)

    def test_invalid_cycle_examples_rejected(self) -> None:
        with pytest.raises(ValueError, match="cycle_examples"):
            ModuleImportsAnalyzerConfig(cycle_examples=-1)


class TestRendering:
    def test_cyclic_graph_renders_without_crashing(self) -> None:
        graph = _analyze("cyclic_three")

        for theme in ("light", "dark"):
            for layout in (None, "package_ring"):
                converter = module_pyvis_converter(theme=theme, layout=layout)
                html = converter(graph, html=True)
                assert isinstance(html, str) and html


class TestCli:
    def test_cycles_output_written(self, tmp_path: Path) -> None:
        cycles = tmp_path / "cycles.json"
        code = cli.main(
            [
                "analyze",
                str(PACKAGES),
                "cyclic_two",
                "--cycles-output",
                str(cycles),
                "--output",
                str(tmp_path / "graph.json"),
            ]
        )

        assert code == 0
        report = json.loads(cycles.read_text(encoding="utf-8"))
        assert report["cycle_count"] >= 1
        assert any("cyclic_two.a" in component["modules"] for component in report["components"])

    def test_fail_on_cycle_exit_code(self, tmp_path: Path) -> None:
        code = cli.main(
            ["analyze", str(PACKAGES), "cyclic_two", "--fail-on-cycle", "--output", str(tmp_path / "graph.json")]
        )

        assert code == 1
