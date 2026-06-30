import argparse
from pathlib import Path
from typing import Final, List, Optional, Tuple, TypeVar

from pda.analyzer import ModuleImportsAnalyzer, ModulesCollector
from pda.analyzer.imports.report import build_cycle_report
from pda.analyzer.target import AnalysisTarget, AnalysisTargetResolver
from pda.cli.flags import build_config
from pda.cli.output import export, resolve_output
from pda.config import ModuleAnalyzerConfig, ModuleImportsAnalyzerConfig, ModuleResolutionConfig, ModulesCollectorConfig
from pda.resolution import ProjectResolutionContext
from pda.tools.logger import logger
from pda.tools.serialization import save_json

SUFFIX_IMPORTS: Final = "imports"
SUFFIX_MODULES: Final = "modules"
_ConfigT = TypeVar("_ConfigT", bound=ModuleAnalyzerConfig)


def _source_roots_arg(args: argparse.Namespace) -> Optional[Tuple[Path, ...]]:
    if args.source_roots is None:
        return None

    return tuple(args.source_roots)


def _external_roots_arg(args: argparse.Namespace) -> Tuple[Path, ...]:
    if args.external_roots is None:
        return ()

    return tuple(args.external_roots)


def _resolution_config(args: argparse.Namespace) -> ModuleResolutionConfig:
    return ModuleResolutionConfig(
        source_roots=_source_roots_arg(args),
        local_boundary=args.local_boundary,
        external_roots=_external_roots_arg(args),
        include_sys_path=args.include_sys_path,
    )


def _build_analyzer_config(config_cls: type[_ConfigT], args: argparse.Namespace) -> _ConfigT:
    base_config = build_config(config_cls, args)
    data = base_config.model_dump(exclude={"resolution"})
    data["resolution"] = _resolution_config(args)
    return config_cls(**data)


def _append_suffix(name: Optional[str], suffix: str) -> str:
    return suffix if name is None else f"{name}-{suffix}"


def _default_analyze_paths(
    project_root: Path,
    root_module_name: str,
    resolution_config: ModuleResolutionConfig,
) -> List[Path]:
    project_context = ProjectResolutionContext.create(
        project_root,
        source_roots=resolution_config.source_roots,
        local_boundary=resolution_config.local_boundary,
        external_roots=resolution_config.external_roots,
        include_sys_path=resolution_config.include_sys_path,
    )
    target = AnalysisTarget(root_module_name=root_module_name)
    resolved_target = AnalysisTargetResolver(project_context).resolve(target)
    return list(resolved_target.local_entry_paths)


def run_analyze(args: argparse.Namespace) -> int:
    project_root: Path = args.project_root
    root_module_name: str = args.root_module
    config = _build_analyzer_config(ModuleImportsAnalyzerConfig, args)
    paths: List[Path] = (
        args.paths
        if args.paths is not None
        else _default_analyze_paths(
            project_root,
            root_module_name,
            config.resolution,
        )
    )
    output, fmt = resolve_output(
        args.output,
        args.format,
        _append_suffix(
            root_module_name,
            SUFFIX_IMPORTS,
        ),
    )

    analyzer = ModuleImportsAnalyzer(
        config=config,
        project_root=project_root,
        root_module_name=root_module_name,
    )
    graph = analyzer(paths)
    if args.cycles_output is not None:
        report = build_cycle_report(
            graph,
            length_bound=config.cycle_length_bound,
            max_examples=config.cycle_examples,
        )
        save_json(report, args.cycles_output)

    return export(
        graph,
        output,
        fmt,
        theme=args.theme or "light",
        layout=args.layout,
    )


def run_collect(args: argparse.Namespace) -> int:
    project_root: Optional[Path] = args.project_root
    root_module_name: Optional[str] = args.root_module
    config = _build_analyzer_config(ModulesCollectorConfig, args)
    resolution = config.resolution
    if project_root is not None and root_module_name is None:
        logger.error("A root module name is required when a project root is provided.")
        return 2

    if project_root is None and (
        resolution.source_roots is not None or resolution.local_boundary is not None or resolution.external_roots
    ):
        logger.error("source roots, local boundary, and external roots require a project root.")
        return 2

    stem = _append_suffix(root_module_name, SUFFIX_MODULES)
    output, fmt = resolve_output(args.output, args.format, stem)

    collector = ModulesCollector(
        config=config,
        project_root=project_root,
        root_module_name=root_module_name,
    )
    return export(
        collector(),
        output,
        fmt,
        theme=args.theme or "light",
        layout=args.layout,
    )
