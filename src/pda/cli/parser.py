import argparse
from pathlib import Path
from typing import List, get_args

from pda.cli.commands import run_analyze, run_collect
from pda.cli.flags import add_flags, flags_for
from pda.config import LayoutMode, ModuleImportsAnalyzerConfig, ModulesCollectorConfig, Theme


def _split_paths(value: str) -> List[Path]:
    return [Path(item.strip()) for item in value.split(",") if item.strip()]


def _add_output_format_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--format",
        choices=("json", "html"),
        default=None,
        help="Output format. Inferred from the --output extension when omitted, otherwise 'json'.",
    )
    parser.add_argument(
        "--theme",
        choices=get_args(Theme),
        default=None,
        help="Colour theme for HTML output. Defaults to 'light'.",
    )
    parser.add_argument(
        "--layout",
        choices=get_args(LayoutMode),
        default=None,
        help="Node layout for HTML output. Defaults to the bundled configuration.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pda",
        description="Analyze and export Python module dependency graphs as node-link JSON or interactive HTML.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser(
        "analyze",
        help="Build a package's import-dependency graph and export it as JSON or interactive HTML.",
    )
    analyze.add_argument("project_root", type=Path, help="Path to the project root.")
    analyze.add_argument("package", help="Top-level package name to analyze.")
    analyze.add_argument(
        "--paths",
        type=_split_paths,
        default=None,
        help="Comma-separated entry-point files or directories. Defaults to the project root.",
    )
    analyze.add_argument(
        "--source-roots",
        type=_split_paths,
        default=None,
        help="Comma-separated import source roots, resolved relative to the project root when relative.",
    )
    analyze.add_argument(
        "--local-boundary",
        type=Path,
        default=None,
        help="Filesystem boundary for local module categorization. Defaults to the project root.",
    )
    analyze.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output path. Format follows the extension or --format; defaults to '<package>-imports.json'.",
    )
    analyze.add_argument(
        "--cycles-output",
        type=Path,
        default=None,
        help="Write a JSON report of detected import cycles to this path.",
    )
    _add_output_format_flags(analyze)
    add_flags(analyze, flags_for(ModuleImportsAnalyzerConfig))
    analyze.set_defaults(handler=run_analyze)

    collect = subparsers.add_parser(
        "collect",
        help="Collect installed and local modules into a graph and export it as JSON or interactive HTML.",
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
        "--source-roots",
        type=_split_paths,
        default=None,
        help="Comma-separated import source roots, resolved relative to the project root when relative.",
    )
    collect.add_argument(
        "--local-boundary",
        type=Path,
        default=None,
        help="Filesystem boundary for local module categorization. Defaults to the project root.",
    )
    collect.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output path. Format follows the extension or --format; defaults to '<package>-modules.json'.",
    )
    _add_output_format_flags(collect)
    add_flags(collect, flags_for(ModulesCollectorConfig))
    collect.set_defaults(handler=run_collect)

    return parser
