from pathlib import Path

from pda.specification import Module, ModuleCategory, ModuleKind, NamespacePortion
from pda.specification.imports.origin import OriginType


def test_namespace_portion_preserves_module_category_enum(tmp_path: Path) -> None:
    portion = NamespacePortion(
        path=tmp_path / "acme",
        matched_root=tmp_path,
        category=ModuleCategory.LOCAL,
    )

    assert portion.category == ModuleCategory.LOCAL


def test_module_exposes_namespace_portions_as_specification_facts(tmp_path: Path) -> None:
    portion = NamespacePortion(
        path=tmp_path / "acme",
        matched_root=tmp_path,
        category=ModuleCategory.LOCAL,
    )

    module = Module(
        name="acme",
        kind=ModuleKind.NAMESPACE_PACKAGE,
        origin=None,
        origin_type=OriginType.NONE,
        submodule_search_locations=(portion.path,),
        namespace_portions=(portion,),
    )

    assert module.namespace_portions == (portion,)
