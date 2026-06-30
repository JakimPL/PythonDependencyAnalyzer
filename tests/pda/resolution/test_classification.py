from pathlib import Path

from pda.resolution.classification import ModuleClassifier
from pda.resolution.models.environment import TargetEnvironment
from pda.specification import ModuleCategory


def test_matched_root_and_category_agree_under_local_boundary_and_stdlib(tmp_path: Path) -> None:
    boundary = tmp_path / "project"
    stdlib_root = boundary / "vendored_stdlib"
    nested = stdlib_root / "mod"
    nested.mkdir(parents=True)

    environment = TargetEnvironment(
        source_roots=(),
        local_boundary=boundary,
        stdlib_roots=(stdlib_root,),
    )
    classifier = ModuleClassifier(environment)

    assert classifier.category_for_path(nested) == ModuleCategory.LOCAL
    assert classifier.matched_root_for_path(nested) == boundary
