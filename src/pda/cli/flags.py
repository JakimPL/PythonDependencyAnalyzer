import argparse
from collections import defaultdict
from dataclasses import dataclass
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

from pda.config import ModuleAnalyzerConfig

_ConfigT = TypeVar("_ConfigT", bound=ModuleAnalyzerConfig)


@dataclass(frozen=True)
class _Flag:
    field: str
    container: Optional[str]
    kind: str
    choices: Optional[Tuple[Any, ...]]
    help: Optional[str]


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


def flags_for(model: type[BaseModel], container: Optional[str] = None) -> List[_Flag]:
    flags: List[_Flag] = []
    for name, info in model.model_fields.items():
        if isinstance(info.json_schema_extra, dict) and info.json_schema_extra.get("cli") is False:
            continue

        annotation = info.annotation
        if annotation is None:
            continue

        nested = _as_model(annotation)
        if nested is not None:
            if container is not None:
                raise ValueError("Nested configuration deeper than one level is not supported by the CLI.")

            flags.extend(flags_for(nested, container=name))
            continue

        kind, choices = _classify(annotation)
        if kind is None:
            continue

        flags.append(_Flag(name, container, kind, choices, _normalize_help(info.description)))

    return flags


def add_flags(parser: argparse.ArgumentParser, flags: Sequence[_Flag]) -> None:
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


def build_config(config_cls: type[_ConfigT], args: argparse.Namespace) -> _ConfigT:
    top: Dict[str, Any] = {}
    nested: DefaultDict[str, Dict[str, Any]] = defaultdict(dict)
    for flag in flags_for(config_cls):
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
