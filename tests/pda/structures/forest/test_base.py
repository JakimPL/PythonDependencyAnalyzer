from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Set

import pytest
from anytree import Node

from pda.structures.forest.base import Forest


class TreeStructures:
    @staticmethod
    def chain() -> Dict[str, Node]:
        a = Node("A")
        b = Node("B", parent=a)
        c = Node("C", parent=b)
        return {"a": a, "b": b, "c": c}

    @staticmethod
    def deep_chain() -> Dict[str, Node]:
        a = Node("A")
        b = Node("B", parent=a)
        c = Node("C", parent=b)
        d = Node("D", parent=c)
        e = Node("E", parent=d)
        return {"a": a, "b": b, "c": c, "d": d, "e": e}

    @staticmethod
    def binary_tree() -> Dict[str, Node]:
        a = Node("A")
        b = Node("B", parent=a)
        c = Node("C", parent=a)
        d = Node("D", parent=b)
        e = Node("E", parent=b)
        f = Node("F", parent=c)
        return {"a": a, "b": b, "c": c, "d": d, "e": e, "f": f}

    @staticmethod
    def ternary_tree() -> Dict[str, Node]:
        root = Node("Root")
        a = Node("A", parent=root)
        b = Node("B", parent=root)
        c = Node("C", parent=root)
        a1 = Node("A1", parent=a)
        a2 = Node("A2", parent=a)
        b1 = Node("B1", parent=b)
        c1 = Node("C1", parent=c)
        c2 = Node("C2", parent=c)
        c3 = Node("C3", parent=c)
        return {"root": root, "a": a, "b": b, "c": c, "a1": a1, "a2": a2, "b1": b1, "c1": c1, "c2": c2, "c3": c3}

    @staticmethod
    def multi_level_wide() -> Dict[str, Node]:
        root = Node("Root")
        l1_a = Node("L1_A", parent=root)
        l1_b = Node("L1_B", parent=root)
        l1_c = Node("L1_C", parent=root)
        l1_d = Node("L1_D", parent=root)
        l2_a1 = Node("L2_A1", parent=l1_a)
        l2_a2 = Node("L2_A2", parent=l1_a)
        l2_b1 = Node("L2_B1", parent=l1_b)
        l2_c1 = Node("L2_C1", parent=l1_c)
        l2_d1 = Node("L2_D1", parent=l1_d)
        l2_d2 = Node("L2_D2", parent=l1_d)
        return {
            "root": root,
            "l1_a": l1_a,
            "l1_b": l1_b,
            "l1_c": l1_c,
            "l1_d": l1_d,
            "l2_a1": l2_a1,
            "l2_a2": l2_a2,
            "l2_b1": l2_b1,
            "l2_c1": l2_c1,
            "l2_d1": l2_d1,
            "l2_d2": l2_d2,
        }

    @staticmethod
    def two_chains() -> Dict[str, Node]:
        a = Node("A")
        b = Node("B", parent=a)
        x = Node("X")
        y = Node("Y", parent=x)
        return {"a": a, "b": b, "x": x, "y": y}

    @staticmethod
    def three_separate_trees() -> Dict[str, Node]:
        a = Node("A")
        a1 = Node("A1", parent=a)
        a2 = Node("A2", parent=a)
        b = Node("B")
        b1 = Node("B1", parent=b)
        c = Node("C")
        return {"a": a, "a1": a1, "a2": a2, "b": b, "b1": b1, "c": c}


class TestFindTopLevelNodes:
    @dataclass
    class TestCase:
        __test__ = False

        label: str
        nodes: Set[Node]
        expected: Set[Node]

    single = Node("Single")
    external_parent = Node("ExternalParent")
    with_external = Node("WithExternal", parent=external_parent)
    chain = TreeStructures.chain()
    deep = TreeStructures.deep_chain()
    binary = TreeStructures.binary_tree()
    ternary = TreeStructures.ternary_tree()
    wide = TreeStructures.multi_level_wide()
    two_chains = TreeStructures.two_chains()
    three_trees = TreeStructures.three_separate_trees()

    test_cases = [
        TestCase(label="empty_set", nodes=set(), expected=set()),
        TestCase(label="single_node", nodes={single}, expected={single}),
        TestCase(label="node_with_external_parent", nodes={with_external}, expected={with_external}),
        TestCase(label="chain_all_nodes", nodes=set(chain.values()), expected={chain["a"]}),
        TestCase(label="chain_skip_middle", nodes={chain["a"], chain["c"]}, expected={chain["a"]}),
        TestCase(label="chain_only_middle", nodes={chain["b"]}, expected={chain["b"]}),
        TestCase(label="chain_skip_root", nodes={chain["b"], chain["c"]}, expected={chain["b"]}),
        TestCase(
            label="deep_chain_all_nodes",
            nodes=set(deep.values()),
            expected={deep["a"]},
        ),
        TestCase(
            label="deep_chain_sparse",
            nodes={deep["a"], deep["c"], deep["e"]},
            expected={deep["a"]},
        ),
        TestCase(
            label="binary_tree_all_nodes",
            nodes=set(binary.values()),
            expected={binary["a"]},
        ),
        TestCase(
            label="binary_tree_root_and_leaves",
            nodes={binary["a"], binary["d"], binary["f"]},
            expected={binary["a"]},
        ),
        TestCase(
            label="binary_tree_middle_level_and_leaves",
            nodes={binary["b"], binary["c"], binary["d"], binary["e"], binary["f"]},
            expected={binary["b"], binary["c"]},
        ),
        TestCase(
            label="binary_tree_only_leaves",
            nodes={binary["d"], binary["e"], binary["f"]},
            expected={binary["d"], binary["e"], binary["f"]},
        ),
        TestCase(
            label="binary_tree_siblings",
            nodes={binary["d"], binary["e"]},
            expected={binary["d"], binary["e"]},
        ),
        TestCase(
            label="ternary_tree_all_nodes",
            nodes=set(ternary.values()),
            expected={ternary["root"]},
        ),
        TestCase(
            label="ternary_tree_level_one_and_leaves",
            nodes={ternary["a"], ternary["b"], ternary["c"], ternary["a1"], ternary["c2"], ternary["c3"]},
            expected={ternary["a"], ternary["b"], ternary["c"]},
        ),
        TestCase(
            label="ternary_tree_mixed_levels",
            nodes={ternary["root"], ternary["a1"], ternary["b"], ternary["c3"]},
            expected={ternary["root"]},
        ),
        TestCase(
            label="wide_tree_all_nodes",
            nodes=set(wide.values()),
            expected={wide["root"]},
        ),
        TestCase(
            label="wide_tree_level_one",
            nodes={wide["l1_a"], wide["l1_b"], wide["l1_c"], wide["l1_d"]},
            expected={wide["l1_a"], wide["l1_b"], wide["l1_c"], wide["l1_d"]},
        ),
        TestCase(
            label="wide_tree_level_two",
            nodes={wide["l2_a1"], wide["l2_a2"], wide["l2_b1"], wide["l2_c1"], wide["l2_d1"], wide["l2_d2"]},
            expected={wide["l2_a1"], wide["l2_a2"], wide["l2_b1"], wide["l2_c1"], wide["l2_d1"], wide["l2_d2"]},
        ),
        TestCase(
            label="wide_tree_mixed_branches",
            nodes={wide["root"], wide["l1_b"], wide["l2_a1"], wide["l2_d2"]},
            expected={wide["root"]},
        ),
        TestCase(
            label="two_chains_all_nodes",
            nodes=set(two_chains.values()),
            expected={two_chains["a"], two_chains["x"]},
        ),
        TestCase(
            label="two_chains_partial",
            nodes={two_chains["a"], two_chains["y"]},
            expected={two_chains["a"], two_chains["y"]},
        ),
        TestCase(
            label="three_trees_all_nodes",
            nodes=set(three_trees.values()),
            expected={three_trees["a"], three_trees["b"], three_trees["c"]},
        ),
        TestCase(
            label="three_trees_partial",
            nodes={three_trees["a1"], three_trees["b"], three_trees["c"]},
            expected={three_trees["a1"], three_trees["b"], three_trees["c"]},
        ),
        TestCase(
            label="three_trees_mixed",
            nodes={three_trees["a"], three_trees["a2"], three_trees["b1"]},
            expected={three_trees["a"], three_trees["b1"]},
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda tc: tc.label,
    )
    def test_find_top_level_nodes(self, test_case: TestCase) -> None:
        result = Forest._find_top_level_nodes(test_case.nodes)
        assert result == test_case.expected
