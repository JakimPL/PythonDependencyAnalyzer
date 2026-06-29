from typing import Optional

from pda.constants import DELIMITER
from pda.resolution.models.source import SourceModuleContext
from pda.specification import ImportPath


class ImportPathCandidateBuilder:
    def candidates(
        self,
        context: SourceModuleContext,
        import_path: ImportPath,
    ) -> tuple[str, ...]:
        base_name = self._absolute_module_name(
            context,
            import_path.module,
            import_path.level,
        )
        if import_path.relative and base_name is None:
            return ()

        candidates: list[str] = []
        if import_path.name and import_path.name != "*":
            if base_name:
                candidates.append(f"{base_name}{DELIMITER}{import_path.name}")
            elif not import_path.relative:
                candidates.append(import_path.name)

        if base_name:
            candidates.append(base_name)

        return self._unique(candidates)

    def _absolute_module_name(
        self,
        context: SourceModuleContext,
        module: Optional[str],
        level: int,
    ) -> Optional[str]:
        if level == 0:
            return module

        package_path = ImportPath.from_string(context.containing_package)
        levels_to_climb = level - 1
        if levels_to_climb >= len(package_path.parts):
            return None

        parent = package_path.get_parent(levels_to_climb)
        resolved = parent / module
        return resolved.module

    def _unique(self, candidates: list[str]) -> tuple[str, ...]:
        unique: list[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            if candidate in seen:
                continue

            seen.add(candidate)
            unique.append(candidate)

        return tuple(unique)
