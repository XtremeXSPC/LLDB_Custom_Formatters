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


# ------------------- Traversal Strategy Base Class -------------------- #
class TraversalStrategy(ABC):
    """
    Abstract base class for all traversal strategies. It defines a common
    interface for different traversal algorithms.
    """

    @abstractmethod
    def traverse(
        self, root_ptr: "lldb.SBValue", max_items: int
    ) -> Tuple[List[str], Dict[str, Any]]:
        """
        Traverses a data structure and returns a list of value summaries.
        """
        pass

    def traverse_for_dot(
        self, root_ptr: "lldb.SBValue"
    ) -> Tuple[List[str], Dict[str, Any]]:
        """
        Traverses a data structure and generates content for a Graphviz .dot file.
        This base implementation is for non-graph structures and can be overridden.
        """
        # Default implementation for non-tree-like structures
        values, metadata = self.traverse(root_ptr, max_items=1000)
        dot_lines = ["digraph G {", '  rankdir="LR";', "  node [shape=box];"]
        for i, value in enumerate(values):
            dot_lines.append(f'  Node_{i} [label="{value}"];')
            if i > 0:
                dot_lines.append(f"  Node_{i-1} -> Node_{i};")
        dot_lines.append("}")
        return dot_lines, metadata


# ------------------ Concrete Traversal Strategies --------------------- #
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

            node_struct = _safe_get_node_from_pointer(current_ptr)
            if not node_struct or not node_struct.IsValid():
                break

            value_child = get_child_member_by_names(node_struct, [value_name])
            values.append(get_value_summary(value_child))

            current_ptr = get_child_member_by_names(node_struct, [next_ptr_name])

        metadata: Dict[str, Any] = {
            "truncated": truncated,
            "doubly_linked": is_doubly_linked,
        }
        return values, metadata


# ----------------- Tree Traversal Strategy Base Class ----------------- #
class TreeTraversalStrategy(TraversalStrategy):
    """
    An intermediate base class for tree traversal strategies.

    This class provides an implementation of `traverse_for_dot` that
    visualizes the actual tree structure instead of a linear list. It can
    also annotate the nodes with their traversal order.
    """

    def traverse_for_dot(
        self, root_ptr: "lldb.SBValue", annotate: bool = False
    ) -> Tuple[List[str], Dict[str, Any]]:
        """
        Traverses a tree and generates content for a Graphviz .dot file,
        correctly representing the parent-child structure.
        """
        dot_lines = []
        visited_addrs = set()
        traversal_map = {}

        if annotate:
            # To annotate, we need to perform the specific traversal (pre, in, post)
            # and store the order of each node's address.
            ordered_addrs = self._get_ordered_addresses(root_ptr)
            traversal_map = {addr: i for i, addr in enumerate(ordered_addrs, 1)}

        self._build_dot_recursive(root_ptr, dot_lines, visited_addrs, traversal_map)

        # The first two lines are added by the caller, so we just return the body.
        return dot_lines, {}

    def _get_ordered_addresses(self, root_ptr: "lldb.SBValue") -> List[int]:
        """
        An internal traversal implementation that returns a list of node
        addresses in the specific traversal order of the strategy.
        This must be implemented by each concrete tree strategy.
        """
        raise NotImplementedError

    def _build_dot_recursive(
        self,
        node_ptr: "lldb.SBValue",
        dot_lines: List[str],
        visited_addrs: set,
        traversal_map: Dict[int, int],
    ):
        """Recursive helper to generate Graphviz .dot content for a tree."""
        node_addr = get_raw_pointer(node_ptr)
        if node_addr == 0 or node_addr in visited_addrs:
            return
        visited_addrs.add(node_addr)

        node_struct = _safe_get_node_from_pointer(node_ptr)
        if not node_struct or not node_struct.IsValid():
            return

        value = get_child_member_by_names(node_struct, ["value", "val", "data", "key"])
        val_summary = get_value_summary(value).replace('"', '"')

        label = val_summary
        if traversal_map and node_addr in traversal_map:
            order_index = traversal_map[node_addr]
            label = f'"{order_index}: {val_summary}"'
        else:
            label = f'"{val_summary}"'

        dot_lines.append(f"  Node_{node_addr} [label={label}];")

        children = _get_node_children(node_struct)
        for child_ptr in children:
            child_addr = get_raw_pointer(child_ptr)
            if child_addr != 0:
                dot_lines.append(f"  Node_{node_addr} -> Node_{child_addr};")
                self._build_dot_recursive(
                    child_ptr, dot_lines, visited_addrs, traversal_map
                )


# ----------------- Concrete Tree Traversal Strategies ----------------- #
class PreOrderTreeStrategy(TreeTraversalStrategy):
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

    def _get_ordered_addresses(self, root_ptr: "lldb.SBValue") -> List[int]:
        """Returns a list of node addresses in pre-order."""
        addresses: List[int] = []
        visited_addrs = set()

        def _recursive_traverse_addr(node_ptr):
            if not node_ptr or get_raw_pointer(node_ptr) == 0:
                return

            node_addr = get_raw_pointer(node_ptr)
            if node_addr in visited_addrs:
                return
            visited_addrs.add(node_addr)

            # 1. Visit Root (add address)
            addresses.append(node_addr)

            # 2. Recurse on children
            node = _safe_get_node_from_pointer(node_ptr)
            if node and node.IsValid():
                children = _get_node_children(node)
                for child in children:
                    _recursive_traverse_addr(child)

        _recursive_traverse_addr(root_ptr)
        return addresses


class InOrderTreeStrategy(TreeTraversalStrategy):
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

    def _get_ordered_addresses(self, root_ptr: "lldb.SBValue") -> List[int]:
        """Returns a list of node addresses in in-order."""
        addresses: List[int] = []
        visited_addrs = set()

        def _recursive_traverse_addr(node_ptr):
            if not node_ptr or get_raw_pointer(node_ptr) == 0:
                return

            node_addr = get_raw_pointer(node_ptr)
            if node_addr in visited_addrs:
                return
            visited_addrs.add(node_addr)

            node = _safe_get_node_from_pointer(node_ptr)
            if not node or not node.IsValid():
                return

            left = get_child_member_by_names(node, ["left", "m_left", "_left"])
            right = get_child_member_by_names(node, ["right", "m_right", "_right"])
            is_binary = (left and left.IsValid()) or (right and right.IsValid())

            if is_binary:
                if left and get_raw_pointer(left) != 0:
                    _recursive_traverse_addr(left)
                addresses.append(node_addr)
                if right and get_raw_pointer(right) != 0:
                    _recursive_traverse_addr(right)
            else:
                children = _get_node_children(node)
                if children:
                    _recursive_traverse_addr(children[0])
                addresses.append(node_addr)
                for i in range(1, len(children)):
                    _recursive_traverse_addr(children[i])

        _recursive_traverse_addr(root_ptr)
        return addresses


class PostOrderTreeStrategy(TreeTraversalStrategy):
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

    def _get_ordered_addresses(self, root_ptr: "lldb.SBValue") -> List[int]:
        """Returns a list of node addresses in post-order."""
        addresses: List[int] = []
        visited_addrs = set()

        def _recursive_traverse_addr(node_ptr):
            if not node_ptr or get_raw_pointer(node_ptr) == 0:
                return

            node_addr = get_raw_pointer(node_ptr)
            if node_addr in visited_addrs:
                return
            visited_addrs.add(node_addr)

            node = _safe_get_node_from_pointer(node_ptr)
            if node and node.IsValid():
                children = _get_node_children(node)
                for child in children:
                    _recursive_traverse_addr(child)

            addresses.append(node_addr)

        _recursive_traverse_addr(root_ptr)
        return addresses
