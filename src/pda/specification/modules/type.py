from enum import StrEnum


class ModuleType(StrEnum):
    MODULE = "module"
    PACKAGE = "package"
    NAMESPACE_PACKAGE = "namespace_package"
