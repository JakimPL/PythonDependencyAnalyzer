from enum import StrEnum


class ModuleAvailability(StrEnum):
    INSTALLED = "installed"
    MISSING = "missing"
    CONDITIONAL = "conditional"
