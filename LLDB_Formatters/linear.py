# ---------------------------------------------------------------------- #
# FILE: linear.py
#
# DESCRIPTION:
# This module provides the summary formatter for linear, pointer-based
# data structures such as singly-linked lists, stacks, and queues.
#
# It follows the new architecture by:
#   1. Using a 'register_summary' decorator to announce its capability.
#   2. Employing the 'LinearTraversalStrategy' to decouple the traversal
#      logic from the presentation logic.
#   3. Formatting the results from the strategy into a final, user-
#      facing summary string.
# ---------------------------------------------------------------------- #

from .helpers import (
    Colors,
    get_child_member_by_names,
    get_raw_pointer,
    should_use_colors,
    g_config,
)
from .registry import register_summary
from .strategies import LinearTraversalStrategy


@register_summary(r"^(Custom|My)?(Linked)?List<.*>$")
@register_summary(r"^(Custom|My)?Stack<.*>$")
@register_summary(r"^(Custom|My)?Queue<.*>$")
def linear_container_summary_provider(valobj, internal_dict):
    """
    This is the registered summary provider for all linear containers.
    It orchestrates fetching data using a strategy and formatting the
    final summary string.

    Args:
        valobj: The SBValue object representing the list/stack/queue.
        internal_dict: The LLDB internal dictionary.

    Returns:
        A formatted one-line summary string.
    """
    # Use the appropriate strategy to traverse the data structure.
    strategy = LinearTraversalStrategy()
    use_colors = should_use_colors()

    # Find the head pointer of the container.
    head_ptr = get_child_member_by_names(valobj, ["head", "m_head", "_head", "top"])
    if not head_ptr:
        return "Error: Could not find head pointer member."

    if get_raw_pointer(head_ptr) == 0:
        return "size = 0, []"

    # The strategy returns the list of values and metadata about the traversal.
    values, metadata = strategy.traverse(head_ptr, g_config.summary_max_items)

    # --- Format the output string ---
    C_GREEN = Colors.GREEN if use_colors else ""
    C_RESET = Colors.RESET if use_colors else ""
    C_YELLOW = Colors.YELLOW if use_colors else ""
    C_BOLD_CYAN = Colors.BOLD_CYAN if use_colors else ""
    C_RED = Colors.RED if use_colors else ""

    # Format the size information.
    size_member = get_child_member_by_names(
        valobj, ["count", "size", "m_size", "_size"]
    )
    size_str = f"size = {size_member.GetValueAsUnsigned()}" if size_member else ""

    # Colorize values. Red for errors, yellow for data.
    colored_values = []
    for v in values:
        if v.startswith("["):  # Error or cycle
            colored_values.append(f"{C_RED}{v}{C_RESET}")
        else:
            colored_values.append(f"{C_YELLOW}{v}{C_RESET}")

    # Choose the appropriate separator based on linked list type.
    separator = (
        f" {C_BOLD_CYAN}<->{C_RESET} "
        if metadata.get("doubly_linked", False)
        else f" {C_BOLD_CYAN}->{C_RESET} "
    )

    summary_str = separator.join(colored_values)

    if metadata.get("truncated", False):
        summary_str += f" {separator.strip()} ..."

    return f"{C_GREEN}{size_str}{C_RESET}, [{summary_str}]"
