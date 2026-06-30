from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Optional


class ResolutionDiagnosticCode(StrEnum):
    MODULE_SPEC_NOT_FOUND = "module_spec_not_found"
    IMPORT_PATH_EMPTY = "import_path_empty"
    IMPORT_PATH_UNRESOLVED = "import_path_unresolved"
    RELATIVE_IMPORT_ESCAPES_PACKAGE = "relative_import_escapes_package"
    AMBIGUOUS_FROM_IMPORT = "ambiguous_from_import"
    PATH_OUTSIDE_SOURCE_ROOTS = "path_outside_source_roots"
    PATH_NOT_PYTHON_MODULE = "path_not_python_module"
    NAMESPACE_WITHOUT_PYTHON_CHILD = "namespace_without_python_child"
    PATH_UNRESOLVED = "path_unresolved"


@dataclass(frozen=True)
class ResolutionDiagnosticDetail:
    key: str
    value: str


@dataclass(frozen=True)
class ResolutionDiagnostic:
    code: ResolutionDiagnosticCode
    message: str
    details: tuple[ResolutionDiagnosticDetail, ...] = ()

    @classmethod
    def create(
        cls,
        code: ResolutionDiagnosticCode,
        message: str,
        **details: str,
    ) -> ResolutionDiagnostic:
        return cls(
            code=code,
            message=message,
            details=tuple(ResolutionDiagnosticDetail(key, value) for key, value in details.items()),
        )

    def detail(self, key: str) -> Optional[str]:
        for item in self.details:
            if item.key == key:
                return item.value

        return None
