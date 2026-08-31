"""
Bugzilla → Jira MCP Server
Provides AI Agents with the ability to read Bugzilla bugs and automatically create Jira tickets.

Note: Bugzilla 4.0.1 uses JSON-RPC (/jsonrpc.cgi).
      All client methods return dictionaries directly, not Response objects.
"""

import os
import sys

from mcp.server.fastmcp import FastMCP

# Add the src directory to the path so 'clients' package is importable
current_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
sys.path.insert(0, workspace_root)

from clients.client_factory import get_client
# from business.bugzilla_to_jira.bugzilla_to_jira import run_workflow

mcp = FastMCP("bugzilla")

_client = None


def get_bugzilla_client():
    global _client
    if _client is None:
        _client = get_client("bugzilla")
    return _client


@mcp.tool()
def bugzilla_get_bug(bug_id: str) -> dict:
    """
    Get details of a Bugzilla bug.

    Args:
        bug_id: Bugzilla bug ID, e.g. "12345"

    Returns:
        Bug details including summary, product, component, severity, status, etc.
    """
    client = get_bugzilla_client()
    data = client.get_bug(bug_id)
    bugs = data.get("bugs", [])
    if not bugs:
        return {"error": f"Bug #{bug_id} not found"}
    bug = bugs[0]
    return {
        "id": bug.get("id"),
        "summary": bug.get("summary"),
        "product": bug.get("product"),
        "component": bug.get("component"),
        "severity": bug.get("severity"),
        "priority": bug.get("priority"),
        "status": bug.get("status"),
        "resolution": bug.get("resolution"),
        "assigned_to": bug.get("assigned_to"),
        "creator": bug.get("creator"),
        "creation_time": bug.get("creation_time"),
        "last_change_time": bug.get("last_change_time"),
        "url": f"{client.base_url}/show_bug.cgi?id={bug.get('id')}"
    }


@mcp.tool()
def bugzilla_search_bugs(product: str = "", component: str = "",
                         status: str = "", assigned_to: str = "",
                         summary: str = "", limit: int = 20) -> list:
    """
    Search Bugzilla bugs by filters.

    Args:
        product: Product name filter (e.g. "HomeShield")
        component: Component name filter
        status: Status filter (e.g. "NEW", "ASSIGNED", "RESOLVED")
        assigned_to: Assigned user email
        summary: Keyword in bug summary
        limit: Max results (default 20)

    Returns:
        List of matching bugs
    """
    client = get_bugzilla_client()
    data = client.search_bugs(
        product=product or None,
        component=component or None,
        status=status or None,
        assigned_to=assigned_to or None,
        summary=summary or None,
        limit=limit
    )
    return [
        {
            "id": b.get("id"),
            "summary": b.get("summary"),
            "product": b.get("product"),
            "severity": b.get("severity"),
            "status": b.get("status"),
            "assigned_to": b.get("assigned_to"),
            "url": f"{client.base_url}/show_bug.cgi?id={b.get('id')}"
        }
        for b in data.get("bugs", [])
    ]


@mcp.tool()
def bugzilla_get_comments(bug_id: str) -> list:
    """
    Get all comments on a Bugzilla bug.

    Args:
        bug_id: Bugzilla bug ID

    Returns:
        List of comments with author, text, and timestamp
    """
    client = get_bugzilla_client()
    data = client.get_comments(bug_id)
    comments = data.get("bugs", {}).get(str(bug_id), {}).get("comments", [])
    return [
        {
            "id": c.get("id"),
            "author": c.get("author"),
            "text": c.get("text", "")[:1000],
            "time": c.get("time"),
            "is_private": c.get("is_private", False)
        }
        for c in comments
    ]


@mcp.tool()
def bugzilla_add_comment(bug_id: str, comment: str) -> dict:
    """
    Add a comment to a Bugzilla bug.

    Args:
        bug_id: Bugzilla bug ID
        comment: Comment text

    Returns:
        Result with comment id
    """
    client = get_bugzilla_client()
    result = client.add_comment(bug_id, comment)
    return {"success": True, "bug_id": bug_id, "comment_id": result.get("id")}


@mcp.tool()
def bugzilla_update_bug(bug_id: str, status: str = "",
                        resolution: str = "") -> dict:
    """
    Update a Bugzilla bug's status/resolution.

    Args:
        bug_id: Bugzilla bug ID
        status: New status (e.g. "ASSIGNED", "RESOLVED")
        resolution: Resolution (e.g. "FIXED", required when status=RESOLVED)

    Returns:
        Result with success status
    """
    updates = {}
    if status:
        updates["status"] = status
    if resolution:
        updates["resolution"] = resolution
    if not updates:
        return {"error": "No updates provided"}

    client = get_bugzilla_client()
    result = client.update_bug(bug_id, updates)
    return {"success": True, "bug_id": bug_id, "updates": updates}


@mcp.tool()
def bugzilla_create_bug(product: str, component: str, summary: str,
                        description: str = "", version: str = "unspecified",
                        severity: str = "normal", priority: str = "P2",
                        op_sys: str = "All", platform: str = "All",
                        extra_fields: dict = None) -> dict:
    """
    Create a new Bugzilla bug.

    Args:
        product: Product name (e.g. "Unified ID v1.7")
        component: Component name (e.g. "ProductID_20572_Comp")
        summary: Bug title / short description
        description: Detailed bug description (initial comment)
        version: Product version (e.g. "v1.7.44")
        severity: Severity level — normal, critical, major, minor, trivial, enhancement (default "normal")
        priority: Priority level — P1, P2, P3, P4, P5 (default "P2")
        op_sys: Operating system (default "All")
        platform: Hardware platform (default "All")
        extra_fields: Additional custom or standard fields as a dict, e.g.
            {
                "cf_module": "Cloud_Account_Management",
                "cf_bugcategory": "Function",
                "cf_testcase": "无",
                "cf_reproducesteps": "Steps to reproduce ...",
                "cf_testresult": "Actual result ...",
                "cf_expectresult": "Expected result ...",
                "cf_problemanalysis": "Root cause ...",
                "cf_bugimpact": "Impact description ..."
            }

    Returns:
        {"id": <new_bug_id>, "success": True, "url": "https://..."}
    """
    client = get_bugzilla_client()
    result = client.create_bug(
        product=product,
        component=component,
        summary=summary,
        description=description,
        version=version,
        severity=severity,
        priority=priority,
        op_sys=op_sys,
        platform=platform,
        extra_fields=extra_fields,
    )
    new_id = result.get("id")
    return {
        "id": new_id,
        "success": bool(new_id),
        "url": f"{client.base_url}/show_bug.cgi?id={new_id}" if new_id else None,
    }


# @mcp.tool()
# def bugzilla_to_jira(bug_ids: str, update_bugzilla: bool = True) -> dict:
#     """
#     Convert Bugzilla bugs to Jira tickets in CS/HomeShield.
#     Creates Jira Bug tickets, adds comments to Bugzilla with Jira links,
#     and updates Bugzilla status to ASSIGNED.

#     Args:
#         bug_ids: Bug IDs or URLs, space/comma separated (e.g. "12345, 12346")
#         update_bugzilla: Whether to write back to Bugzilla (default True)

#     Returns:
#         Summary with created/skipped/failed counts and per-bug details
#     """
#     return run_workflow(
#         arguments=bug_ids,
#         update_bugzilla=update_bugzilla
#     )


if __name__ == "__main__":
    print("Starting Bugzilla MCP Server...")
    print("Available tools:")
    print("  - bugzilla_get_bug(bug_id)")
    print("  - bugzilla_search_bugs(product, component, status, ...)")
    print("  - bugzilla_get_comments(bug_id)")
    print("  - bugzilla_add_comment(bug_id, comment)")
    print("  - bugzilla_update_bug(bug_id, status, resolution)")
    print("  - bugzilla_create_bug(product, component, summary, ...)")
    print("  - bugzilla_to_jira(bug_ids, update_bugzilla)")
    mcp.run()
