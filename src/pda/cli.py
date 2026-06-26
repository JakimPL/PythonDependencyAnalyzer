import argparse
from pathlib import Path
from typing import List, Optional, Sequence

from pda.analyzer import ModuleImportsAnalyzer, ModulesCollector
from pda.config import ModuleImportsAnalyzerConfig, ModulesCollectorConfig
from pda.exceptions import PDAException
from pda.models import ModuleGraph
from pda.tools.logger import logger


def _split_paths(value: str) -> List[Path]:
    return [Path(item.strip()) for item in value.split(",") if item.strip()]


def _export(graph: ModuleGraph, output: Path) -> int:
    graph.save(output)
    logger.info("Wrote %d nodes and %d edges to %s", len(graph), len(graph.edges), output)
    return 0


def _run_analyze(args: argparse.Namespace) -> int:
    project_root: Path = args.project_root
    package: str = args.package
    paths: List[Path] = args.paths if args.paths is not None else [project_root]
    output: Path = args.output if args.output is not None else Path(f"{package}_imports.json")

    analyzer = ModuleImportsAnalyzer(
        config=ModuleImportsAnalyzerConfig(),
        project_root=project_root,
        package=package,
    )
    return _export(analyzer(paths), output)


def _run_collect(args: argparse.Namespace) -> int:
    project_root: Optional[Path] = args.project_root
    package: Optional[str] = args.package
    if project_root is not None and package is None:
        logger.error("A package name is required when a project root is provided.")
        return 2

    default_output = Path(f"{package}-modules.json") if package is not None else Path("modules.json")
    output: Path = args.output if args.output is not None else default_output

    collector = ModulesCollector(
        config=ModulesCollectorConfig(),
        project_root=project_root,
        package=package,
    )

    return _export(collector(), output)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pda",
        description="Analyze and export Python module dependency graphs as node-link JSON.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser(
        "analyze",
        help="Build a package's import-dependency graph and export it as JSON.",
    )
    analyze.add_argument(
        "project_root",
        type=Path,
        help="Path to the project root.",
    )
    analyze.add_argument(
        "package",
        help="Top-level package name to analyze.",
    )
    analyze.add_argument(
        "--paths",
        type=_split_paths,
        default=None,
        help="Comma-separated entry-point files or directories. Defaults to the project root.",
    )
    analyze.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output JSON path. Defaults to '<package>_imports.json'.",
    )
    analyze.set_defaults(handler=_run_analyze)

    collect = subparsers.add_parser(
        "collect",
        help="Collect installed and local modules into a graph and export it as JSON.",
    )
    collect.add_argument(
        "project_root",
        nargs="?",
        type=Path,
        default=None,
        help="Optional path to the project root.",
    )
    collect.add_argument(
        "package",
        nargs="?",
        default=None,
        help="Package name. Required when a project root is provided.",
    )
    collect.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output JSON path. Defaults to '<package>-modules.json', or 'modules.json'.",
    )
    collect.set_defaults(handler=_run_collect)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except (PDAException, ValueError, OSError) as error:
        logger.error("%s", error)
        return 1
