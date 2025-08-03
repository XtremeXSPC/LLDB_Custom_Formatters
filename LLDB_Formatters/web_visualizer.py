# ---------------------------------------------------------------------- #
# FILE: web_visualizer.py
#
# DESCRIPTION:
# This module implements advanced, interactive data structure
# visualizations by generating self-contained HTML files that use the
# 'vis.js' JavaScript library.
#
# It provides three main commands:
#   - 'export_list_web': Generates an interactive, linear view of a
#     linked list with traversal animation.
#   - 'export_tree_web': Generates an interactive, hierarchical view
#     of a tree structure.
#   - 'export_graph_web': Generates an interactive, physics-based
#     force-directed layout of a graph structure.
#
# The generated HTML file is automatically opened in the user's
# default web browser.
#
# NOTE: ON DESIGN
# This module intentionally does NOT use the TraversalStrategy classes.
# The strategies are designed to produce linear text summaries, while the
# web visualizer needs the full structural information of the data
# (nodes, edges, addresses) to render it graphically.
# ---------------------------------------------------------------------- #

from .helpers import (
    get_child_member_by_names,
    get_raw_pointer,
    get_value_summary,
    type_has_field,
    debug_print,
    _safe_get_node_from_pointer,
    _get_node_children,
)

import json
import tempfile
import webbrowser
import os
import shlex


# ---------------------------------------------------------------------- #
# SECTION 1: PRIVATE HELPER FUNCTIONS
# These functions are for internal use within this module.
# ---------------------------------------------------------------------- #


def _load_static_file(file_path):
    """
    Generic helper to load a static file from the templates/static directory.
    """
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(script_dir, "templates/static", file_path)
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        debug_print(f"Failed to load static file {file_path}: {e}")
        return f"/* FAILED TO LOAD {file_path} */"


def _load_visjs_library():
    """Loads the content of the vis-network.min.js library."""
    return _load_static_file("vis-network.min.js")


def _load_shared_css():
    """Loads the content of style.css."""
    return _load_static_file("style.css")


def _load_shared_js():
    """Loads the content of common.js."""
    return _load_static_file("common.js")


def _build_visjs_data_for_list(valobj):
    """
    Traverses a linked list SBValue and returns all data required for its
    vis.js visualization in a dictionary.
    Returns None if the list is empty or its structure cannot be determined.
    """
    head_ptr = get_child_member_by_names(valobj, ["head", "m_head", "_head", "top"])
    if not head_ptr or get_raw_pointer(head_ptr) == 0:
        return None

    first_node = head_ptr.Dereference()
    if not first_node or not first_node.IsValid():
        return None

    # Dynamically determine member names for 'next', 'value', and 'prev'
    node_type = first_node.GetType()
    next_ptr_name = next(
        (
            n
            for n in ["next", "m_next", "_next", "pNext"]
            if type_has_field(node_type, n)
        ),
        None,
    )
    value_name = next(
        (
            n
            for n in ["value", "val", "data", "m_data", "key"]
            if type_has_field(node_type, n)
        ),
        None,
    )
    has_prev_field = any(
        type_has_field(node_type, n) for n in ["prev", "m_prev", "_prev", "pPrev"]
    )

    if not next_ptr_name or not value_name:
        debug_print("Could not determine list node structure ('next'/'value' members).")
        return None

    # Traverse the list and collect node/edge data
    nodes_data, edges_data, traversal_order, visited_addrs = [], [], [], set()
    current_ptr = head_ptr
    while get_raw_pointer(current_ptr) != 0:
        node_addr = get_raw_pointer(current_ptr)
        if node_addr in visited_addrs:
            break  # Cycle detected
        visited_addrs.add(node_addr)
        traversal_order.append(f"0x{node_addr:x}")

        node_struct = current_ptr.Dereference()
        if not node_struct or not node_struct.IsValid():
            break

        val_summary = get_value_summary(node_struct.GetChildMemberWithName(value_name))
        nodes_data.append(
            {
                "id": f"0x{node_addr:x}",
                "value": val_summary,
                "address": f"0x{node_addr:x}",
            }
        )

        next_node_ptr = node_struct.GetChildMemberWithName(next_ptr_name)
        if get_raw_pointer(next_node_ptr) != 0:
            edges_data.append(
                {
                    "from": f"0x{node_addr:x}",
                    "to": f"0x{get_raw_pointer(next_node_ptr):x}",
                }
            )
        current_ptr = next_node_ptr

    size_member = get_child_member_by_names(valobj, ["size", "m_size", "count"])
    list_size = size_member.GetValueAsUnsigned() if size_member else len(nodes_data)

    return {
        "nodes_data": nodes_data,
        "edges_data": edges_data,
        "traversal_order": traversal_order,
        "list_size": list_size,
        "is_doubly_linked": has_prev_field,
    }


def _build_visjs_data_for_tree(node_ptr, nodes_list, edges_list, visited):
    """
    Recursively traverses a tree from the given node pointer to build node
    and edge lists compatible with vis.js.
    """
    node_addr = get_raw_pointer(node_ptr)
    if not node_ptr or node_addr == 0 or node_addr in visited:
        return

    visited.add(node_addr)
    node_struct = _safe_get_node_from_pointer(node_ptr)
    if not node_struct or not node_struct.IsValid():
        return

    value = get_child_member_by_names(node_struct, ["value", "val", "data", "key"])
    val_summary = get_value_summary(value)

    # Add the current node with a detailed tooltip
    title_str = f"Value: {val_summary}\nAddress: 0x{node_addr:x}"
    nodes_list.append(
        {
            "id": f"0x{node_addr:x}",
            "label": val_summary,
            "title": title_str,
            "address": f"0x{node_addr:x}",
        }
    )

    # Recurse on all children (supports both binary and n-ary trees)
    children = _get_node_children(node_struct)
    for child_ptr in children:
        child_addr = get_raw_pointer(child_ptr)
        if child_addr != 0:
            edges_list.append({"from": f"0x{node_addr:x}", "to": f"0x{child_addr:x}"})
            _build_visjs_data_for_tree(child_ptr, nodes_list, edges_list, visited)


def _build_visjs_data_for_graph(valobj):
    """
    Traverses a graph SBValue and returns all data needed for its
    vis.js visualization in a dictionary.
    Returns None if the graph is empty or its structure cannot be determined.
    """
    nodes_container = get_child_member_by_names(
        valobj, ["nodes", "m_nodes", "adj", "adjacency_list"]
    )
    if not nodes_container or not nodes_container.MightHaveChildren():
        return None

    # Iterate through all nodes in the graph's adjacency list/vector
    nodes, edges, visited_edges = [], [], set()
    for i in range(nodes_container.GetNumChildren()):
        node = nodes_container.GetChildAtIndex(i)
        if node.GetType().IsPointerType():
            node = node.Dereference()
        if not node or not node.IsValid():
            continue

        node_addr = get_raw_pointer(node)
        val_summary = get_value_summary(
            get_child_member_by_names(node, ["value", "val", "data"])
        )

        nodes.append(
            {
                "id": f"0x{node_addr:x}",
                "label": val_summary,
                "title": f"Value: {val_summary}",
                "address": f"0x{node_addr:x}",
            }
        )

        # Iterate through this node's neighbors to define edges
        neighbors = get_child_member_by_names(node, ["neighbors", "adj", "edges"])
        if neighbors and neighbors.MightHaveChildren():
            for j in range(neighbors.GetNumChildren()):
                neighbor = neighbors.GetChildAtIndex(j)
                if neighbor.GetType().IsPointerType():
                    neighbor = neighbor.Dereference()
                if not neighbor or not neighbor.IsValid():
                    continue

                neighbor_addr = get_raw_pointer(neighbor)
                edge_tuple = tuple(sorted((node_addr, neighbor_addr)))
                if edge_tuple not in visited_edges:
                    edges.append(
                        {
                            "from": f"0x{node_addr:x}",
                            "to": f"0x{neighbor_addr:x}",
                            "arrows": "to",
                        }
                    )
                    visited_edges.add(edge_tuple)
    return {"nodes_data": nodes, "edges_data": edges}


# ---------------------------------------------------------------------- #
# SECTION 2: PUBLIC REUSABLE HTML GENERATORS
# These functions orchestrate the creation of the final HTML content.
# ---------------------------------------------------------------------- #


def _generate_html(template_name, template_data):
    """
    Generic private helper to load an HTML template, substitute placeholders
    with data, and return the final HTML string.
    """
    template_data["__VISJS_LIBRARY__"] = _load_visjs_library()
    template_data["__SHARED_CSS__"] = _load_shared_css()
    template_data["__SHARED_JS__"] = _load_shared_js()

    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(script_dir, "templates", template_name)
        with open(template_path, "r", encoding="utf-8") as f:
            final_html = f.read()
        # Replace all placeholders with their corresponding data
        for placeholder, value in template_data.items():
            final_html = final_html.replace(placeholder, str(value))
        return final_html
    except Exception as e:
        return f"<html><body>Error generating visualizer from template '{template_name}': {e}</body></html>"


def generate_list_visualization_html(valobj):
    """
    Takes a list SBValue and returns a complete, self-contained HTML string
    for its visualization. Returns None if data generation fails.
    """
    list_data = _build_visjs_data_for_list(valobj)
    if not list_data:
        return None

    # ----- UNIFIED INFO TABLE GENERATION ------ #
    info = {
        "Variable Name": valobj.GetName(),
        "Type Name": valobj.GetTypeName(),
        "Size": list_data["list_size"],
        "Is Doubly Linked": "Yes" if list_data["is_doubly_linked"] else "No",
    }
    info_html = "<h3>List Information</h3><table>"
    for key, value in info.items():
        info_html += f"<tr><th>{key}</th><td>{value}</td></tr>"
    info_html += "</table>"

    template_data = {
        "__NODES_DATA__": json.dumps(list_data["nodes_data"]),
        "__EDGES_DATA__": json.dumps(list_data["edges_data"]),
        "__TRAVERSAL_ORDER_DATA__": json.dumps(list_data["traversal_order"]),
        "__IS_DOUBLY_LINKED__": json.dumps(list_data["is_doubly_linked"]),
        "__TYPE_INFO_HTML__": info_html,
    }
    return _generate_html("list_visualizer.html", template_data)


def generate_tree_visualization_html(valobj):
    """
    Takes a tree SBValue and returns a complete, self-contained HTML string
    for its visualization. Returns None if the tree is empty.
    This function is designed to be imported by other modules (e.g., tree.py).
    """
    root_node_ptr = get_child_member_by_names(valobj, ["root", "m_root", "_root"])
    if not root_node_ptr or get_raw_pointer(root_node_ptr) == 0:
        return None

    nodes_data, edges_data, visited_addrs = [], [], set()
    _build_visjs_data_for_tree(root_node_ptr, nodes_data, edges_data, visited_addrs)

    # ----- UNIFIED INFO TABLE GENERATION ------ #
    size_member = get_child_member_by_names(valobj, ["size", "m_size", "count"])
    info = {
        "Variable Name": valobj.GetName(),
        "Type Name": valobj.GetTypeName(),
        "Size": size_member.GetValueAsUnsigned() if size_member else "N/A",
        "Root Address": f"0x{get_raw_pointer(root_node_ptr):x}",
    }
    info_html = "<h3>Tree Information</h3><table>"
    for key, value in info.items():
        info_html += f"<tr><th>{key}</th><td>{value}</td></tr>"
    info_html += "</table>"

    template_data = {
        "__NODES_DATA__": json.dumps(nodes_data),
        "__EDGES_DATA__": json.dumps(edges_data),
        "__TYPE_INFO_HTML__": info_html,  # Pass the full HTML block
    }
    return _generate_html("tree_visualizer.html", template_data)


def generate_graph_visualization_html(valobj):
    """
    Takes a graph SBValue and returns a complete, self-contained HTML string
    for its visualization. Returns None if data generation fails.
    """
    graph_data = _build_visjs_data_for_graph(valobj)
    if not graph_data:
        return None

    # ----- UNIFIED INFO TABLE GENERATION ------ #
    num_nodes_member = get_child_member_by_names(
        valobj, ["num_nodes", "V", "node_count"]
    )
    num_edges_member = get_child_member_by_names(
        valobj, ["num_edges", "E", "edge_count"]
    )
    info = {
        "Variable Name": valobj.GetName(),
        "Type Name": valobj.GetTypeName(),
        "Nodes (V)": (
            num_nodes_member.GetValueAsUnsigned()
            if num_nodes_member
            else len(graph_data["nodes_data"])
        ),
        "Edges (E)": (
            num_edges_member.GetValueAsUnsigned()
            if num_edges_member
            else len(graph_data["edges_data"])
        ),
    }
    info_html = "<h3>Graph Information</h3><table>"
    for key, value in info.items():
        info_html += f"<tr><th>{key}</th><td>{value}</td></tr>"
    info_html += "</table>"

    template_data = {
        "__NODES_DATA__": json.dumps(graph_data["nodes_data"]),
        "__EDGES_DATA__": json.dumps(graph_data["edges_data"]),
        "__TYPE_INFO_HTML__": info_html,  # Pass the full HTML block
    }
    return _generate_html("graph_visualizer.html", template_data)


# ---------------------------------------------------------------------- #
# SECTION 3: CUSTOM LLDB COMMANDS
# These functions are registered in __init__.py and are callable from LLDB.
# ---------------------------------------------------------------------- #


def _display_html_content(html_content, var_name, result):
    """
    Handles displaying the generated HTML. It attempts to use the direct
    CodeLLDB API first, and falls back to opening a file in the default
    web browser if the API is not available (e.g., in a standard terminal).
    """
    if not html_content:
        result.AppendMessage(
            f"Could not generate visualization for '{var_name}'. The variable might be empty or invalid."
        )
        return

    # Try to use the direct CodeLLDB API for in-IDE visualization
    display_html = None
    try:
        from debugger import display_html  # type: ignore
    except ImportError:
        display_html = None

    if display_html:
        try:
            display_html(html_content)
            result.AppendMessage(
                f"Displayed interactive visualizer for '{var_name}' in a new tab."
            )
            return
        except Exception as e:
            debug_print(f"Failed to use CodeLLDB display_html: {e}")

    # Fallback for standard terminals
    result.AppendMessage("CodeLLDB API not found. Falling back to a web browser.")
    try:
        with tempfile.NamedTemporaryFile(
            "w", delete=False, suffix=".html", encoding="utf-8"
        ) as f:
            f.write(html_content)
            output_filename = f.name
        webbrowser.open(f"file://{os.path.realpath(output_filename)}")
        result.AppendMessage(
            f"Successfully exported visualizer to '{output_filename}'."
        )
    except Exception as e:
        result.SetError(f"Failed to create or open the HTML file: {e}")


def _get_variable_from_command(command, debugger, result):
    """
    A utility to parse the command arguments to get the variable name
    and retrieve the corresponding SBValue from the debugger frame.
    Handles common errors like missing arguments or invalid variables.
    """
    args = shlex.split(command)
    if not args:
        result.SetError("Usage: <command> <variable_name>")
        return None, None

    var_name = args[0]
    frame = (
        debugger.GetSelectedTarget().GetProcess().GetSelectedThread().GetSelectedFrame()
    )
    if not frame.IsValid():
        result.SetError("Cannot execute command: invalid execution context.")
        return None, None

    valobj = frame.FindVariable(var_name)
    if not valobj or not valobj.IsValid():
        result.SetError(f"Could not find a variable named '{var_name}'.")
        return None, None

    return var_name, valobj


def export_list_web_command(debugger, command, result, internal_dict):
    """Implements the 'weblist' command."""
    var_name, valobj = _get_variable_from_command(command, debugger, result)
    if not valobj:
        return
    html_content = generate_list_visualization_html(valobj)
    _display_html_content(html_content, var_name, result)


def export_tree_web_command(debugger, command, result, internal_dict):
    """Implements the 'webtree' command."""
    var_name, valobj = _get_variable_from_command(command, debugger, result)
    if not valobj:
        return
    html_content = generate_tree_visualization_html(valobj)
    _display_html_content(html_content, var_name, result)


def export_graph_web_command(debugger, command, result, internal_dict):
    """Implements the 'webgraph' command."""
    var_name, valobj = _get_variable_from_command(command, debugger, result)
    if not valobj:
        return
    html_content = generate_graph_visualization_html(valobj)
    _display_html_content(html_content, var_name, result)
