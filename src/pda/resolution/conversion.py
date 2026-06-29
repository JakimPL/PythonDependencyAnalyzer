from pda.resolution.models.resolution import ModuleResolution
from pda.specification import ModuleCategory
from pda.specification.modules.module.categorized import CategorizedModule
from pda.specification.modules.module.module import Module
from pda.specification.modules.module.unavailable import UnavailableModule


class CategorizedModuleBuilder:
    def from_resolution(
        self,
        resolution: ModuleResolution,
    ) -> CategorizedModule:
        if not resolution.resolved or resolution.identity is None or resolution.location is None:
            return CategorizedModule(
                module=UnavailableModule(
                    name=resolution.identity.name if resolution.identity is not None else resolution.requested,
                    error=Exception(resolution.reason or "module not resolved"),
                ),
                category=ModuleCategory.UNKNOWN,
            )

        module = Module(
            name=resolution.identity.name,
            origin=resolution.location.origin,
            origin_type=resolution.location.origin_type,
            submodule_search_locations=resolution.location.submodule_search_locations,
        )
        return CategorizedModule.from_module(
            module,
            category=resolution.category,
        )
