from collections.abc import Iterable
from copy import copy
from typing import Self, Tuple, Union, overload

from pda.specification.modules.categorized import CategorizedModule
from pda.specification.modules.category import ModuleCategory
from pda.specification.modules.types import CategorizedModuleDict, ModuleCollectionDict


class ModulesCollection:
    """
    A collection of modules categorized by their type:
    * stdlib (standard library)
    * external (third-party packages)
    * local (project-specific modules)
    * unavailable (modules that could not be categorized)
    """

    def __init__(
        self,
        modules: Iterable[CategorizedModule] = (),
        allow_unavailable: bool = False,
    ) -> None:
        self._allow_unavailable: bool = allow_unavailable
        self._categorized_modules: ModuleCollectionDict = self._initialize_modules_collection(modules)

    def __bool__(self) -> bool:
        return any(modules for modules in self._categorized_modules.values())

    def __contains__(self, name: str) -> bool:
        return any(name in modules for modules in self._categorized_modules.values())

    @overload
    def __getitem__(self, name_or_category: ModuleCategory) -> CategorizedModuleDict: ...

    @overload
    def __getitem__(self, name_or_category: str) -> CategorizedModule: ...

    def __getitem__(
        self, name_or_category: Union[str, ModuleCategory]
    ) -> Union[CategorizedModule, CategorizedModuleDict]:
        if isinstance(name_or_category, ModuleCategory):
            if name_or_category == ModuleCategory.UNAVAILABLE:
                raise ValueError("Unavailable modules are not stored in this registry")

            return self._categorized_modules[name_or_category]

        if name_or_category in ModuleCategory:
            raise TypeError(
                f"Module category '{name_or_category}' should be accessed using its enum value, not as a string"
            )

        if not isinstance(name_or_category, str):
            raise TypeError(
                f"Module name must be either a category enum or a string, got {type(name_or_category).__name__}"
            )

        for category in self.categories:
            if name_or_category in self._categorized_modules[category]:
                return self._categorized_modules[category][name_or_category]

        raise KeyError(f"Module '{name_or_category}' not found")

    def __len__(self) -> int:
        return sum(len(modules) for modules in self._categorized_modules.values())

    def __copy__(self) -> Self:
        cls = self.__class__
        return cls(modules=self.modules.values(), allow_unavailable=self._allow_unavailable)

    def clear(self) -> None:
        for modules in self._categorized_modules.values():
            modules.clear()

    def copy(self) -> Self:
        return copy(self)

    def add(self, module: CategorizedModule) -> None:
        if module.category not in self.categories:
            raise ValueError(f"Module category '{module.category}' is not allowed in this collection")

        self._categorized_modules[module.category][module.name] = module

    @property
    def stdlib(self) -> CategorizedModuleDict:
        return self._categorized_modules[ModuleCategory.STDLIB].copy()

    @property
    def external(self) -> CategorizedModuleDict:
        return self._categorized_modules[ModuleCategory.EXTERNAL].copy()

    @property
    def local(self) -> CategorizedModuleDict:
        return self._categorized_modules[ModuleCategory.LOCAL].copy()

    @property
    def unavailable(self) -> CategorizedModuleDict:
        if not self._allow_unavailable:
            raise ValueError("Unavailable modules are not stored in this registry")

        return self._categorized_modules[ModuleCategory.UNAVAILABLE].copy()

    @property
    def modules(self) -> CategorizedModuleDict:
        return {module.name: module for modules in self._categorized_modules.values() for module in modules.values()}

    @property
    def categories(self) -> Tuple[ModuleCategory, ...]:
        return tuple(
            filter(
                lambda category: category != ModuleCategory.UNAVAILABLE or self._allow_unavailable,
                ModuleCategory,
            )
        )

    def _initialize_modules_collection(self, modules: Iterable[CategorizedModule]) -> ModuleCollectionDict:
        categorized_modules: ModuleCollectionDict = {category: {} for category in self.categories}
        for module in modules:
            if module.category not in self.categories:
                continue

            categorized_modules[module.category][module.name] = module

        return categorized_modules
