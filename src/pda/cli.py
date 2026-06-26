import argparse
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from types import NoneType, UnionType
from typing import (
    Any,
    DefaultDict,
    Dict,
    List,
    Literal,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
    get_args,
    get_origin,
)

from pydantic import BaseModel

from pda.analyzer import ModuleImportsAnalyzer, ModulesCollector
from pda.config import ModuleAnalyzerConfig, ModuleImportsAnalyzerConfig, ModulesCollectorConfig
from pda.exceptions import PDAException
from pda.models import ModuleGraph
from pda.tools.logger import logger

_ConfigT = TypeVar("_ConfigT", bound=ModuleAnalyzerConfig)


@dataclass(frozen=True)
class _Flag:
    field: str
    container: Optional[str]
    kind: str
    choices: Optional[Tuple[Any, ...]]
    help: Optional[str]


def _split_paths(value: str) -> List[Path]:
    return [Path(item.strip()) for item in value.split(",") if item.strip()]


def _normalize_help(text: Optional[str]) -> Optional[str]:
    return " ".join(text.split()) if text else None


def _unwrap_optional(annotation: Any) -> Any:
    if get_origin(annotation) in (Union, UnionType):
        non_none = [arg for arg in get_args(annotation) if arg is not NoneType]
        if len(non_none) == 1:
            return non_none[0]

    return annotation


def _as_model(annotation: Any) -> Optional[type[BaseModel]]:
    inner = _unwrap_optional(annotation)
    if isinstance(inner, type) and issubclass(inner, BaseModel):
        return inner

    return None


def _classify(annotation: Any) -> Tuple[Optional[str], Optional[Tuple[Any, ...]]]:
    inner = _unwrap_optional(annotation)
    if inner is bool:
        return "bool", None

    if get_origin(inner) is Literal:
        return "choices", get_args(inner)

    if inner is int:
        return "int", None

    if inner is str:
        return "str", None

    return None, None


def _flags_for(model: type[BaseModel], container: Optional[str] = None) -> List[_Flag]:
    flags: List[_Flag] = []
    for name, info in model.model_fields.items():
        annotation = info.annotation
        if annotation is None:
            continue

        nested = _as_model(annotation)
        if nested is not None:
            if container is not None:
                raise ValueError("Nested configuration deeper than one level is not supported by the CLI.")

            flags.extend(_flags_for(nested, container=name))
            continue

        kind, choices = _classify(annotation)
        if kind is None:
            continue

        flags.append(_Flag(name, container, kind, choices, _normalize_help(info.description)))

    return flags


def _add_flags(parser: argparse.ArgumentParser, flags: Sequence[_Flag]) -> None:
    for flag in flags:
        option = f"--{flag.field.replace('_', '-')}"
        match flag.kind:
            case "bool":
                parser.add_argument(
                    option, dest=flag.field, action=argparse.BooleanOptionalAction, default=None, help=flag.help
                )
            case "choices":
                parser.add_argument(option, dest=flag.field, choices=flag.choices, default=None, help=flag.help)
            case "int":
                parser.add_argument(option, dest=flag.field, type=int, default=None, help=flag.help)
            case _:
                parser.add_argument(option, dest=flag.field, default=None, help=flag.help)


def _build_config(config_cls: type[_ConfigT], args: argparse.Namespace) -> _ConfigT:
    top: Dict[str, Any] = {}
    nested: DefaultDict[str, Dict[str, Any]] = defaultdict(dict)
    for flag in _flags_for(config_cls):
        value = getattr(args, flag.field)
        if value is None:
            continue

        if flag.container is None:
            top[flag.field] = value
        else:
            nested[flag.container][flag.field] = value

    defaults = config_cls()
    data: Dict[str, Any] = dict(top)
    for container, overrides in nested.items():
        current = getattr(defaults, container)
        data[container] = type(current)(**{**current.model_dump(), **overrides})

    return config_cls(**data)


def _export(graph: ModuleGraph, output: Path) -> int:
    graph.save(output)
    logger.info("Wrote %d nodes and %d edges to %s", len(graph), len(graph.edges), output)
    return 0


def _run_analyze(args: argparse.Namespace) -> int:
    project_root: Path = args.project_root
    package: str = args.package
    paths: List[Path] = args.paths if args.paths is not None else [project_root]
    output: Path = args.output if args.output is not None else Path(f"{package}-imports.json")

    config = _build_config(ModuleImportsAnalyzerConfig, args)
    analyzer = ModuleImportsAnalyzer(config=config, project_root=project_root, package=package)
    return _export(analyzer(paths), output)


def _run_collect(args: argparse.Namespace) -> int:
    project_root: Optional[Path] = args.project_root
    package: Optional[str] = args.package
    if project_root is not None and package is None:
        logger.error("A package name is required when a project root is provided.")
        return 2

    default_output = Path(f"{package}-modules.json") if package is not None else Path("modules.json")
    output: Path = args.output if args.output is not None else default_output

    config = _build_config(ModulesCollectorConfig, args)
    collector = ModulesCollector(config=config, project_root=project_root, package=package)
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
    analyze.add_argument("project_root", type=Path, help="Path to the project root.")
    analyze.add_argument("package", help="Top-level package name to analyze.")
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
        help="Output JSON path. Defaults to '<package>-imports.json'.",
    )
    _add_flags(analyze, _flags_for(ModuleImportsAnalyzerConfig))
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
    _add_flags(collect, _flags_for(ModulesCollectorConfig))
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
