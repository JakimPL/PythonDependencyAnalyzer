from dataclasses import dataclass
from typing import Optional

import pytest

from pda.analyzer.depth import CategoryContext, CategoryDepthPolicy
from pda.specification import ModuleCategory


class TestShouldIncludeAndRecurse:
    @dataclass
    class TestCase:
        __test__ = False

        label: str
        depth: Optional[int]
        k: int
        include: bool
        recurse: bool

    test_cases = [
        TestCase(label="none_boundary", depth=None, k=1, include=True, recurse=True),
        TestCase(label="none_deep", depth=None, k=9, include=True, recurse=True),
        TestCase(label="zero_boundary", depth=0, k=1, include=False, recurse=False),
        TestCase(label="one_boundary", depth=1, k=1, include=True, recurse=False),
        TestCase(label="one_beyond", depth=1, k=2, include=False, recurse=False),
        TestCase(label="two_first", depth=2, k=1, include=True, recurse=True),
        TestCase(label="two_second", depth=2, k=2, include=True, recurse=False),
        TestCase(label="two_third", depth=2, k=3, include=False, recurse=False),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda tc: tc.label)
    @pytest.mark.parametrize("category", [ModuleCategory.STDLIB, ModuleCategory.EXTERNAL])
    def test_include_and_recurse(self, test_case: TestCase, category: ModuleCategory) -> None:
        policy = CategoryDepthPolicy(stdlib_depth=test_case.depth, external_depth=test_case.depth)
        context = CategoryContext(category, test_case.k)

        assert policy.should_include(context) is test_case.include
        assert policy.should_recurse(context) is test_case.recurse

    @pytest.mark.parametrize("category", [ModuleCategory.LOCAL, ModuleCategory.UNKNOWN])
    def test_non_foreign_always_passes(self, category: ModuleCategory) -> None:
        policy = CategoryDepthPolicy(stdlib_depth=0, external_depth=0)
        context = CategoryContext(category, 0)

        assert policy.should_include(context) is True
        assert policy.should_recurse(context) is True

    def test_independent_per_category_limits(self) -> None:
        policy = CategoryDepthPolicy(stdlib_depth=None, external_depth=0)

        assert policy.should_include(CategoryContext(ModuleCategory.STDLIB, 5)) is True
        assert policy.should_include(CategoryContext(ModuleCategory.EXTERNAL, 1)) is False


class TestDescend:
    def test_root_context_is_local(self) -> None:
        root = CategoryContext.root()

        assert root.category == ModuleCategory.LOCAL
        assert root.depth == 0

    def test_local_to_foreign_starts_at_one(self) -> None:
        policy = CategoryDepthPolicy(None, None)
        root = CategoryContext.root()

        assert policy.descend(root, ModuleCategory.EXTERNAL) == CategoryContext(ModuleCategory.EXTERNAL, 1)
        assert policy.descend(root, ModuleCategory.STDLIB) == CategoryContext(ModuleCategory.STDLIB, 1)

    def test_same_category_increments(self) -> None:
        policy = CategoryDepthPolicy(None, None)
        parent = CategoryContext(ModuleCategory.EXTERNAL, 3)

        assert policy.descend(parent, ModuleCategory.EXTERNAL) == CategoryContext(ModuleCategory.EXTERNAL, 4)

    def test_crossing_between_foreign_resets(self) -> None:
        policy = CategoryDepthPolicy(None, None)
        parent = CategoryContext(ModuleCategory.EXTERNAL, 3)

        assert policy.descend(parent, ModuleCategory.STDLIB) == CategoryContext(ModuleCategory.STDLIB, 1)

    def test_returning_to_non_foreign_is_zero(self) -> None:
        policy = CategoryDepthPolicy(None, None)
        parent = CategoryContext(ModuleCategory.STDLIB, 4)

        assert policy.descend(parent, ModuleCategory.LOCAL) == CategoryContext(ModuleCategory.LOCAL, 0)
        assert policy.descend(parent, ModuleCategory.UNKNOWN) == CategoryContext(ModuleCategory.UNKNOWN, 0)
