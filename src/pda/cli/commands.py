import argparse
from pathlib import Path
from typing import List, Optional

from pda.analyzer import ModuleImportsAnalyzer, ModulesCollector
from pda.analyzer.imports.report import build_cycle_report
from pda.cli.flags import build_config
from pda.cli.output import export, resolve_output
from pda.config import ModuleImportsAnalyzerConfig, ModulesCollectorConfig
from pda.tools.logger import logger
from pda.tools.serialization import save_json


def run_analyze(args: argparse.Namespace) -> int:
    project_root: Path = args.project_root
    package: str = args.package
    paths: List[Path] = args.paths if args.paths is not None else [project_root]
    output, fmt = resolve_output(args.output, args.format, f"{package}-imports")

    config = build_config(ModuleImportsAnalyzerConfig, args)
    analyzer = ModuleImportsAnalyzer(config=config, project_root=project_root, package=package)
    graph = analyzer(paths)
    if args.cycles_output is not None:
        report = build_cycle_report(
            graph,
            length_bound=config.cycle_length_bound,
            max_examples=config.cycle_examples,
        )
        save_json(report, args.cycles_output)

    return export(graph, output, fmt, theme=args.theme or "light", layout=args.layout)


def run_collect(args: argparse.Namespace) -> int:
    project_root: Optional[Path] = args.project_root
    package: Optional[str] = args.package
    if project_root is not None and package is None:
        logger.error("A package name is required when a project root is provided.")
        return 2

    stem = f"{package}-modules" if package is not None else "modules"
    output, fmt = resolve_output(args.output, args.format, stem)

    config = build_config(ModulesCollectorConfig, args)
    collector = ModulesCollector(config=config, project_root=project_root, package=package)
    return export(collector(), output, fmt, theme=args.theme or "light", layout=args.layout)
