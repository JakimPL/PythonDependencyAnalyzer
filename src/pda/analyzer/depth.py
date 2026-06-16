from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from pda.specification import ModuleCategory

_FOREIGN_CATEGORIES = frozenset(
    {
        ModuleCategory.STDLIB,
        ModuleCategory.EXTERNAL,
    }
)


@dataclass(frozen=True)
class CategoryContext:
    """
    Category-depth context carried through a dependency traversal.

    ``depth`` counts how deep the current node sits within an uninterrupted run of a
    single foreign category (standard library or external), where ``1`` is the boundary
    node that first crossed into that category. Local, unavailable, and root nodes carry
    ``depth`` ``0`` because the per-category depth limits do not apply to them.
    """

    category: ModuleCategory
    depth: int

    @classmethod
    def root(cls) -> CategoryContext:
        """Context for a traversal entry point, which is always treated as local."""
        return cls(category=ModuleCategory.LOCAL, depth=0)


@dataclass(frozen=True)
class CategoryDepthPolicy:
    """
    Decides how far a traversal descends into foreign (standard-library / external)
    module categories, given a per-category depth limit.

    For a foreign category with limit ``d`` and a node at category-depth ``k`` (``1`` at
    the boundary):

    * ``d is None`` -- unlimited: every node is included and recursed into.
    * ``d == 0`` -- the category is hidden entirely; no node is included.
    * otherwise -- nodes with ``k <= d`` are included, and traversal recurses while
      ``k < d`` (so a node at depth ``d`` is shown as a boundary but not expanded).

    Local and unavailable categories are never constrained here; their visibility is
    governed by the dedicated ``hide_*`` options instead.
    """

    stdlib_depth: Optional[int]
    external_depth: Optional[int]

    def _limit(self, category: ModuleCategory) -> Optional[int]:
        if category == ModuleCategory.STDLIB:
            return self.stdlib_depth

        if category == ModuleCategory.EXTERNAL:
            return self.external_depth

        return None

    def should_include(self, context: CategoryContext) -> bool:
        """Whether a node with the given context is added to the graph."""
        if context.category not in _FOREIGN_CATEGORIES:
            return True

        limit = self._limit(context.category)
        return limit is None or (limit != 0 and context.depth <= limit)

    def should_recurse(self, context: CategoryContext) -> bool:
        """Whether the traversal descends into the dependencies of a node with the given context."""
        if context.category not in _FOREIGN_CATEGORIES:
            return True

        limit = self._limit(context.category)
        return limit is None or (limit != 0 and context.depth < limit)

    def descend(self, parent: CategoryContext, child_category: ModuleCategory) -> CategoryContext:
        """
        Context for a child module reached from ``parent``. Crossing into a different
        foreign category restarts the count at ``1``; staying within the same foreign
        category increments it; leaving the foreign categories resets it to ``0``.
        """
        if child_category not in _FOREIGN_CATEGORIES:
            return CategoryContext(child_category, 0)

        if child_category == parent.category:
            return CategoryContext(child_category, parent.depth + 1)

        return CategoryContext(child_category, 1)
