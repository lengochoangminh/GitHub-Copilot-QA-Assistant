import os
import sys

from mcp.server.fastmcp import FastMCP

# Add the src directory to the path so 'clients' package is importable
current_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.insert(0, workspace_root)

from clients.client_factory import get_client

mcp = FastMCP("jira-server")


def get_jira_client():
    return get_client("jira-server")


@mcp.tool()
def get_jira_issue(issue_key: str) -> dict:
    """
    Get details of a Jira issue.

    Args:
        issue_key: Issue key, e.g. UID-292

    Returns:
        Issue details including summary, status, assignee, description
    """
    response = get_jira_client().get_issue(issue_key)
    data = response.json()
    fields = data.get("fields", {})
    return {
        "key": data.get("key"),
        "summary": fields.get("summary"),
        "status": (fields.get("status") or {}).get("name"),
        "priority": (fields.get("priority") or {}).get("name"),
        "issuetype": (fields.get("issuetype") or {}).get("name"),
        "assignee": (fields.get("assignee") or {}).get("displayName"),
        "reporter": (fields.get("reporter") or {}).get("displayName"),
        "created": fields.get("created"),
        "updated": fields.get("updated"),
        "description": fields.get("description"),
        "components": [c.get("name") for c in fields.get("components", [])],
        "labels": fields.get("labels", []),
        "fixVersions": [v.get("name") for v in fields.get("fixVersions", [])],
    }


@mcp.tool()
def search_jira_issues(jql: str, max_results: int = 20) -> list:
    """
    Search Jira issues using JQL.

    Args:
        jql: JQL query string, e.g. "project = UID AND status = Open"
        max_results: Max number of results to return (default 20)

    Returns:
        List of matching issues with key, summary, status, assignee
    """
    response = get_jira_client().search_issues(jql, max_results)
    data = response.json()
    issues = []
    for issue in data.get("issues", []):
        fields = issue.get("fields", {})
        issues.append({
            "key": issue.get("key"),
            "summary": fields.get("summary"),
            "status": (fields.get("status") or {}).get("name"),
            "assignee": (fields.get("assignee") or {}).get("displayName"),
            "priority": (fields.get("priority") or {}).get("name"),
        })
    return issues


@mcp.tool()
def get_my_jira_issues(max_results: int = 20) -> list:
    """
    Get Jira issues assigned to the current user.

    Returns:
        List of issues ordered by last updated
    """
    response = get_jira_client().search_issues(
        "assignee = currentUser() ORDER BY updated DESC", max_results
    )
    data = response.json()
    issues = []
    for issue in data.get("issues", []):
        fields = issue.get("fields", {})
        issues.append({
            "key": issue.get("key"),
            "summary": fields.get("summary"),
            "status": (fields.get("status") or {}).get("name"),
            "assignee": (fields.get("assignee") or {}).get("displayName"),
            "priority": (fields.get("priority") or {}).get("name"),
        })
    return issues


@mcp.tool()
def create_jira_issue(project_key: str, summary: str, description: str,
                      issue_type: str = "Task", priority: str = "Medium",
                      components: list = None) -> dict:
    """
    Create a new Jira issue.

    Args:
        project_key: Project key, e.g. UID
        summary: Issue title
        description: Issue description
        issue_type: Issue type, default Task
        priority: Priority level (Highest/High/Medium/Low/Lowest)
        components: List of component names

    Returns:
        Created issue key and URL
    """
    resp = get_jira_client().create_issue(
        project_key=project_key,
        summary=summary,
        description=description,
        issue_type=issue_type,
        priority=priority,
        components=components or [],
    )
    data = resp.json()
    return {
        "key": data.get("key"),
        "url": f"https://pdjira.tp-link.com/browse/{data.get('key')}",
        "id": data.get("id"),
    }


@mcp.tool()
def add_jira_comment(issue_key: str, comment: str) -> dict:
    """
    Add a comment to a Jira issue.

    Args:
        issue_key: Issue key, e.g. UID-292
        comment: Comment text (plain text)

    Returns:
        Result with success status
    """
    resp = get_jira_client().add_comment(issue_key, comment)
    if resp.status_code in (200, 201):
        return {"success": True, "message": f"Comment added to {issue_key}"}
    return {"success": False, "message": resp.text}


@mcp.tool()
def transition_jira_issue(issue_key: str, transition_id: str, comment: str = None) -> dict:
    """
    Transition a Jira issue to a new status.

    Args:
        issue_key: Issue key, e.g. UID-292
        transition_id: Transition ID (numeric string)
        comment: Optional comment to add during transition

    Returns:
        Result with success status
    """
    resp = get_jira_client().transition_issue(issue_key, transition_id, comment)
    if resp.status_code in (200, 204):
        return {"success": True, "message": f"Issue {issue_key} transitioned successfully"}
    return {"success": False, "message": resp.text}


if __name__ == "__main__":
    mcp.run()
