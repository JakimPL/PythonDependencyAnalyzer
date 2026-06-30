from enum import StrEnum


class ModuleKind(StrEnum):
    """The Python primitive a resolved module represents, independent of its dependency category."""

    SOURCE_MODULE = "source_module"
    REGULAR_PACKAGE = "regular_package"
    NAMESPACE_PACKAGE = "namespace_package"
    BUILTIN = "builtin"
    FROZEN = "frozen"
    EXTENSION = "extension"
    UNKNOWN = "unknown"
