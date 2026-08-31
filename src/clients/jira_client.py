# clients/jira_client.py
import os
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class JiraClient:
    """
    Jira REST API client.
    Supports two authentication methods (token takes priority over cookie):
      - Token Authentication: Bearer token (JIRA_TOKEN env var or token param).
      - Cookie Authentication: captured from the browser's F12 developer tools.
    Jira REST API Documentation: /rest/api/2/
    """

    def __init__(self, base_url: str = None, cookie: str = None, token: str = None):
        self.base_url = (base_url or os.environ.get("JIRA_BASE_URL", "")).rstrip("/")
        self.session = requests.Session()
        self.session.verify = False
        headers = {"Content-Type": "application/json"}
        if token or os.environ.get("JIRA_TOKEN"):
            token = token or os.environ.get("JIRA_TOKEN")
            headers["Authorization"] = f"Bearer {token}"
        elif cookie or os.environ.get("JIRA_COOKIE"):
            cookie = cookie or os.environ.get("JIRA_COOKIE")
            headers["Cookie"] = cookie
        else:
            raise ValueError("Authentication credentials required: JIRA_TOKEN or JIRA_COOKIE")
        self.session.headers.update(headers)

    def request(self, method, endpoint, **kwargs):
        url = self.base_url + endpoint
        print(f"start jira request: {url}")
        return self.session.request(method, url, **kwargs)

    # ---- Convenience Methods ----

    def create_issue(self, project_key: str, summary: str, description: str,
                     issue_type: str = "Task", priority: str = "Medium",
                     components: list = None, assignee: str = None,
                     reporter: str = None, extra_fields: dict = None):
        """Create a single issue"""
        fields = {
            "project": {"key": project_key},
            "summary": summary,
            "description": description,
            "issuetype": {"name": issue_type},
            "priority": {"name": priority},
        }
        if components:
            fields["components"] = [{"name": c} for c in components]
        if assignee:
            fields["assignee"] = {"name": assignee}
        if reporter:
            fields["reporter"] = {"name": reporter}
        if extra_fields:
            fields.update(extra_fields)

        return self.request("POST", "/rest/api/2/issue", json={"fields": fields})

    def batch_create_issues(self, issues: list):
        """
        Batch create issues
        issues: list of dicts, each dict has the same structure as the fields in create_issue
        """
        payload = {
            "issueUpdates": [{"fields": issue} for issue in issues]
        }
        return self.request("POST", "/rest/api/2/issue/bulk", json=payload)

    def search_issues(self, jql: str, max_results: int = 50, fields: list = None):
        """JQL search"""
        params = {"jql": jql, "maxResults": max_results}
        if fields:
            params["fields"] = ",".join(fields)
        return self.request("GET", "/rest/api/2/search", params=params)

    def get_issue(self, issue_key: str, fields: str = None):
        """Get single issue details"""
        params = {}
        if fields:
            params["fields"] = fields
        return self.request("GET", f"/rest/api/2/issue/{issue_key}", params=params)

    def add_comment(self, issue_key: str, body: str):
        """Add a comment to an issue"""
        return self.request("POST", f"/rest/api/2/issue/{issue_key}/comment", json={"body": body})

    def transition_issue(self, issue_key: str, transition_id: str, comment: str = None):
        """Update issue status"""
        payload = {"transition": {"id": transition_id}}
        if comment:
            payload["update"] = {"comment": [{"add": {"body": comment}}]}
        return self.request("POST", f"/rest/api/2/issue/{issue_key}/transitions", json=payload)

if __name__ == "__main__":    
    
    import json, os
    from dotenv import load_dotenv

    load_dotenv()
    BUG_ID = "UID-292"

    client = JiraClient()  # reads JIRA_BASE_URL, JIRA_TOKEN (or JIRA_COOKIE) from env
    response = client.get_issue(BUG_ID)
    print(response.json())