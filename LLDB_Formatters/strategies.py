# ---------------------------------------------------------------------- #
# FILE: strategies.py
#
# DESCRIPTION:
# This module implements the Strategy Pattern for traversing data
# structures. It defines a common interface, 'TraversalStrategy', and
# provides concrete implementations for various traversal algorithms.
#
# By encapsulating the traversal logic in separate strategy classes, we
# decouple it from the summary providers. This allows for greater
# flexibility, such as changing the traversal order of a tree at
# runtime or easily adding new traversal methods.
# ---------------------------------------------------------------------- #

from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Any

# The 'lldb' module is not available in a standard Python interpreter.
# We use this block to allow type hinting without causing an ImportError
# when running static analysis tools.
try:
    import lldb  # type: ignore
except ImportError:
    pass

from .helpers import (
    get_child_member_by_names,
    get_raw_pointer,
    get_value_summary,
    _safe_get_node_from_pointer,
    _get_node_children,
    type_has_field,
)


class TraversalStrategy(ABC):
    """
    Abstract base class for all traversal strategies. It defines a single
    'traverse' method that concrete strategies must implement.
    """

    @abstractmethod
    def traverse(
        self, root_ptr: "lldb.SBValue", max_items: int
    ) -> Tuple[List[str], Dict[str, Any]]:
        """
        Traverses a data structure starting from a root pointer.

        Args:
            root_ptr: An SBValue pointing to the start of the structure (e.g., head, root).
            max_items: The maximum number of nodes to visit to prevent excessive output.

        Returns:
            A tuple containing:
            - A list of strings, where each string is the summary of a visited node's value.
            - A dictionary of metadata about the traversal (e.g., {'truncated': True}).
        """
        pass


class LinearTraversalStrategy(TraversalStrategy):
    """A strategy for traversing linear, pointer-linked structures like lists."""

    def traverse(
        self, root_ptr: "lldb.SBValue", max_items: int
    ) -> Tuple[List[str], Dict[str, Any]]:
        if not root_ptr or get_raw_pointer(root_ptr) == 0:
            return [], {}

        # Introspect the first node to find member names dynamically.
        node_obj = root_ptr.Dereference()
        if not node_obj or not node_obj.IsValid():
            return [], {}

        node_type = node_obj.GetType()
        next_ptr_name, value_name = None, None
        is_doubly_linked = False

        for name in ["next", "m_next", "_next", "pNext"]:
            if type_has_field(node_type, name):
                next_ptr_name = name
                break
        for name in ["value", "val", "data", "m_data", "key"]:
            if type_has_field(node_type, name):
                value_name = name
                break
        for name in ["prev", "m_prev", "_prev", "pPrev"]:
            if type_has_field(node_type, name):
                is_doubly_linked = True
                break

        if not next_ptr_name or not value_name:
            return ["Error: Could not determine node structure (val/next)"], {}

        values: List[str] = []
        visited_addrs = set()
        current_ptr = root_ptr
        truncated = False

        while get_raw_pointer(current_ptr) != 0:
            if len(values) >= max_items:
                truncated = True
                break

            node_addr = get_raw_pointer(current_ptr)
            if node_addr in visited_addrs:
                values.append("[CYCLE DETECTED]")
                break
            visited_addrs.add(node_addr)

            node_struct = current_ptr.Dereference()
            if not node_struct or not node_struct.IsValid():
                break

            value_child = node_struct.GetChildMemberWithName(value_name)
            values.append(get_value_summary(value_child))

            current_ptr = node_struct.GetChildMemberWithName(next_ptr_name)

        metadata: Dict[str, Any] = {
            "truncated": truncated,
            "doubly_linked": is_doubly_linked,
        }
        return values, metadata


class PreOrderTreeStrategy(TraversalStrategy):
    """A strategy for traversing trees in Pre-Order (Root, Left, Right)."""

    def traverse(
        self, root_ptr: "lldb.SBValue", max_items: int
    ) -> Tuple[List[str], Dict[str, Any]]:
        values: List[str] = []
        visited_addrs = set()

        def _recursive_traverse(node_ptr):
            if (
                not node_ptr
                or get_raw_pointer(node_ptr) == 0
                or len(values) >= max_items
            ):
                return

            node_addr = get_raw_pointer(node_ptr)
            if node_addr in visited_addrs:
                values.append("[CYCLE]")
                return
            visited_addrs.add(node_addr)

            node = _safe_get_node_from_pointer(node_ptr)
            if not node or not node.IsValid():
                return

            # 1. Visit Root
            value = get_child_member_by_names(node, ["value", "val", "data", "key"])
            values.append(get_value_summary(value))

            # 2. Recurse on children
            if len(values) < max_items:
                children = _get_node_children(node)
                for child in children:
                    _recursive_traverse(child)

        _recursive_traverse(root_ptr)
        metadata: Dict[str, Any] = {"truncated": len(values) >= max_items}
        return values, metadata


class InOrderTreeStrategy(TraversalStrategy):
    """
    A strategy for traversing trees In-Order.
    - Binary Tree: (Left, Root, Right)
    - N-ary Tree: (First Child, Root, Other Children)
    """

    def traverse(
        self, root_ptr: "lldb.SBValue", max_items: int
    ) -> Tuple[List[str], Dict[str, Any]]:
        values: List[str] = []
        visited_addrs = set()

        def _recursive_traverse(node_ptr):
            if (
                not node_ptr
                or get_raw_pointer(node_ptr) == 0
                or len(values) >= max_items
            ):
                return

            node_addr = get_raw_pointer(node_ptr)
            if node_addr in visited_addrs:
                values.append("[CYCLE]")
                return
            visited_addrs.add(node_addr)

            node = _safe_get_node_from_pointer(node_ptr)
            if not node or not node.IsValid():
                return

            value = get_child_member_by_names(node, ["value", "val", "data", "key"])

            # Intelligently distinguish between binary and n-ary trees.
            left = get_child_member_by_names(node, ["left", "m_left", "_left"])
            right = get_child_member_by_names(node, ["right", "m_right", "_right"])

            # If the node has 'left' or 'right' members, treat it as a binary tree
            # to enforce the strict Left -> Root -> Right order.
            is_binary = (left and left.IsValid()) or (right and right.IsValid())

            if is_binary:
                # 1. Recurse on Left Subtree
                if left and get_raw_pointer(left) != 0:
                    _recursive_traverse(left)

                if len(values) >= max_items:
                    return

                # 2. Visit Root
                values.append(get_value_summary(value))

                if len(values) >= max_items:
                    return

                # 3. Recurse on Right Subtree
                if right and get_raw_pointer(right) != 0:
                    _recursive_traverse(right)
            else:
                # Fallback to the n-ary tree generalization:
                # (First Child, Root, Other Children)
                children = _get_node_children(node)

                # 1. Recurse on first child's subtree
                if children:
                    _recursive_traverse(children[0])

                if len(values) >= max_items:
                    return

                # 2. Visit Root
                values.append(get_value_summary(value))

                if len(values) >= max_items:
                    return

                # 3. Recurse on the rest of the children's subtrees
                for i in range(1, len(children)):
                    _recursive_traverse(children[i])

        _recursive_traverse(root_ptr)
        metadata: Dict[str, Any] = {"truncated": len(values) >= max_items}
        return values, metadata


class PostOrderTreeStrategy(TraversalStrategy):
    """A strategy for traversing trees in Post-Order (Left, Right, Root)."""

    def traverse(
        self, root_ptr: "lldb.SBValue", max_items: int
    ) -> Tuple[List[str], Dict[str, Any]]:
        values: List[str] = []
        visited_addrs = set()

        def _recursive_traverse(node_ptr):
            if (
                not node_ptr
                or get_raw_pointer(node_ptr) == 0
                or len(values) >= max_items
            ):
                return

            node_addr = get_raw_pointer(node_ptr)
            if node_addr in visited_addrs:
                # In post-order, a cycle can fill the list, so we check before appending.
                if len(values) < max_items:
                    values.append("[CYCLE]")
                return
            visited_addrs.add(node_addr)

            node = _safe_get_node_from_pointer(node_ptr)
            if not node or not node.IsValid():
                return

            # 1. Recurse on all children
            children = _get_node_children(node)
            for child in children:
                _recursive_traverse(child)

            if len(values) >= max_items:
                return

            # 2. Visit Root
            value = get_child_member_by_names(node, ["value", "val", "data", "key"])
            values.append(get_value_summary(value))

        _recursive_traverse(root_ptr)
        metadata: Dict[str, Any] = {"truncated": len(values) >= max_items}
        return values, metadata
