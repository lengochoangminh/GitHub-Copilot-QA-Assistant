# clients/bugzilla_client.py
"""
Bugzilla Client (Bugzilla 4.0.1 - TP 1.5.2)

Your Bugzilla Environment:
- REST API (/rest/): Not Found (404)
- JSON-RPC: Bug.get is permission-restricted (error 32000)
- show_bug.cgi?ctype=xml: ✅ Working normally

This client employs a hybrid strategy:
- Reading bugs:  show_bug.cgi?ctype=xml (parses XML)
- Version information:  JSON-RPC Bugzilla.version (no permission restrictions)
- Write operations:    JSON-RPC Bug.add_comment / Bug.update (attempted first; falls back to CGI if unsuccessful)
"""

import re
import requests
import urllib3
from xml.etree import ElementTree as ET
from typing import Dict, List, Optional, Any

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class BugzillaError(Exception):
    """Bugzilla Operation Error"""
    pass


class BugzillaClient:
    """
    Bugzilla Hybrid Client (CGI + JSON-RPC).
    Uses cookie authentication (Bugzilla_login + Bugzilla_logincookie).
    """

    def __init__(self, base_url: str, cookie: str = None, api_key: str = None):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.verify = False

        headers = {}
        if cookie:
            headers["Cookie"] = cookie
        if api_key:
            headers["X-BUGZILLA-API-KEY"] = api_key
        self.session.headers.update(headers)

        self._request_id = 0

    # ════════════════════════════════════════════════════
    #  Read: show_bug.cgi?ctype=xml
    # ════════════════════════════════════════════════════

    def _parse_bug_xml(self, xml_text: str) -> List[Dict[str, Any]]:
        """
        Parse the XML returned by show_bug.cgi?ctype=xml and extract bug information.
        """
        root = ET.fromstring(xml_text)
        bugs = []

        for bug_elem in root.findall("bug"):
            # Check for errors (e.g., bug does not exist)
            if bug_elem.get("error"):
                continue

            bug = {}
            # Simple field mapping: XML tag → dict key
            field_map = {
                "bug_id": "id",
                "short_desc": "summary",
                "product": "product",
                "component": "component",
                "bug_status": "status",
                "resolution": "resolution",
                "bug_severity": "severity",
                "priority": "priority",
                "assigned_to": "assigned_to",
                "reporter": "creator",
                "creation_ts": "creation_time",
                "delta_ts": "last_change_time",
                "version": "version",
                "target_milestone": "target_milestone",
                "op_sys": "op_sys",
                "rep_platform": "platform",
            }

            for xml_tag, dict_key in field_map.items():
                elem = bug_elem.find(xml_tag)
                if elem is not None and elem.text:
                    bug[dict_key] = elem.text.strip()

            # Convert bug_id to int
            if "id" in bug:
                try:
                    bug["id"] = int(bug["id"])
                except ValueError:
                    pass

            # Extract the first long_desc as description
            long_descs = bug_elem.findall("long_desc")
            if long_descs:
                desc_elem = long_descs[0].find("thetext")
                if desc_elem is not None and desc_elem.text:
                    bug["description"] = desc_elem.text.strip()

            # Extract all comments
            comments = []
            for ld in long_descs:
                comment = {}
                who = ld.find("who")
                if who is not None:
                    comment["author"] = who.text.strip() if who.text else ""
                    comment["author_name"] = who.get("name", "")
                when = ld.find("bug_when")
                if when is not None:
                    comment["time"] = when.text.strip() if when.text else ""
                thetext = ld.find("thetext")
                if thetext is not None:
                    comment["text"] = thetext.text.strip() if thetext.text else ""
                comment["is_private"] = ld.get("isprivate", "0") == "1"
                comments.append(comment)
            bug["_comments"] = comments

            bugs.append(bug)

        return bugs

    def get_bug(self, bug_id: str) -> Dict[str, Any]:
        """
        Get bug details (via show_bug.cgi?ctype=xml).

        Returns:
            {"bugs": [{"id": 12345, "summary": "...", ...}]}
        """
        url = f"{self.base_url}/show_bug.cgi"
        params = {"id": bug_id, "ctype": "xml"}

        print(f"start bugzilla request: get_bug #{bug_id} → {url}")
        resp = self.session.get(url, params=params, timeout=30)
        resp.raise_for_status()

        bugs = self._parse_bug_xml(resp.text)
        return {"bugs": bugs}

    def get_bugs(self, bug_ids: list) -> Dict[str, Any]:
        """Get multiple bugs in batch"""
        all_bugs = []
        for bid in bug_ids:
            result = self.get_bug(str(bid))
            all_bugs.extend(result.get("bugs", []))
        return {"bugs": all_bugs}

    def get_comments(self, bug_id: str) -> Dict[str, Any]:
        """
        Get all comments of a bug (extracted from XML).

        Returns:
            {"bugs": {"12345": {"comments": [...]}}}
        """
        result = self.get_bug(bug_id)
        bugs = result.get("bugs", [])
        comments = bugs[0].get("_comments", []) if bugs else []
        return {"bugs": {str(bug_id): {"comments": comments}}}

    def search_bugs(self, product: str = None, component: str = None,
                    status: str = None, assigned_to: str = None,
                    summary: str = None, limit: int = 50,
                    extra_params: dict = None) -> Dict[str, Any]:
        """
        Search bugs (via buglist.cgi?ctype=atom or buglist.cgi + parameters).
        """
        url = f"{self.base_url}/buglist.cgi"
        params = {"ctype": "csv", "limit": str(limit)}
        if product:
            params["product"] = product
        if component:
            params["component"] = component
        if status:
            params["bug_status"] = status
        if assigned_to:
            params["emailassigned_to1"] = "1"
            params["email1"] = assigned_to
            params["emailtype1"] = "exact"
        if summary:
            params["short_desc"] = summary
            params["short_desc_type"] = "allwordssubstr"
        if extra_params:
            params.update(extra_params)

        print(f"start bugzilla request: search_bugs → {url}")
        resp = self.session.get(url, params=params, timeout=30)
        resp.raise_for_status()

        # Parse CSV results to get bug IDs
        import csv
        import io
        reader = csv.DictReader(io.StringIO(resp.text))
        bugs = []
        for row in reader:
            bug = {
                "id": int(row.get("bug_id", 0)),
                "summary": row.get("short_desc", row.get("short_short_desc", "")),
                "product": row.get("product", ""),
                "status": row.get("bug_status", ""),
                "severity": row.get("bug_severity", ""),
                "priority": row.get("priority", ""),
                "assigned_to": row.get("assigned_to", ""),
            }
            bugs.append(bug)

        return {"bugs": bugs}

    # ════════════════════════════════════════════════════
    #  Write operations: try JSON-RPC first, fallback to CGI form
    # ════════════════════════════════════════════════════

    def _jsonrpc_call(self, method: str, params: dict = None) -> Dict:
        """Send JSON-RPC request"""
        self._request_id += 1
        payload = {
            "method": method,
            "params": [params or {}],
            "id": self._request_id
        }
        resp = self.session.post(
            f"{self.base_url}/jsonrpc.cgi",
            json=payload,
            headers={**self.session.headers, "Content-Type": "application/json"},
            timeout=30
        )
        resp.raise_for_status()
        data = resp.json()
        error = data.get("error")
        if error:
            raise BugzillaError(f"JSON-RPC {error.get('code')}: {error.get('message')}")
        return data.get("result", {})

    def _get_token(self, bug_id: str) -> str:
        """
        Extract CSRF token from show_bug.cgi page.
        Bugzilla 4.x form submissions require a token.
        """
        url = f"{self.base_url}/show_bug.cgi?id={bug_id}"
        resp = self.session.get(url, timeout=30)
        resp.raise_for_status()
        match = re.search(r'name="token"\s+value="([^"]+)"', resp.text)
        return match.group(1) if match else ""

    def _get_create_token(self, product: str, component: str) -> str:
        """
        Extract CSRF token from enter_bug.cgi page (required for post_bug.cgi).
        """
        url = f"{self.base_url}/enter_bug.cgi"
        resp = self.session.get(url, params={"product": product, "component": component}, timeout=30)
        resp.raise_for_status()
        match = re.search(r'name="token"\s+value="([^"]+)"', resp.text)
        return match.group(1) if match else ""

    def add_comment(self, bug_id: str, comment: str, is_private: bool = False) -> Dict:
        """Add a comment to a bug"""
        # Option 1: JSON-RPC
        try:
            return self._jsonrpc_call("Bug.add_comment", {
                "id": int(bug_id),
                "comment": comment,
                "is_private": is_private,
            })
        except BugzillaError:
            pass

        # Option 2: CGI form POST
        print(f"[bugzilla] JSON-RPC add_comment no permission, using CGI form submission")
        token = self._get_token(bug_id)
        form_data = {
            "id": bug_id,
            "comment": comment,
            "token": token,
        }
        if is_private:
            form_data["commentprivacy"] = "1"

        resp = self.session.post(
            f"{self.base_url}/process_bug.cgi",
            data=form_data,
            timeout=30,
            allow_redirects=True
        )
        resp.raise_for_status()
        return {"id": None, "success": True}

    def update_bug(self, bug_id: str, updates: dict) -> Dict:
        """Update bug fields (status, resolution, etc.)"""
        # Option 1: JSON-RPC
        try:
            params = {"ids": [int(bug_id)]}
            params.update(updates)
            return self._jsonrpc_call("Bug.update", params)
        except BugzillaError:
            pass

        # Option 2: CGI form POST
        print(f"[bugzilla] JSON-RPC update no permission, using CGI form submission")
        token = self._get_token(bug_id)
        form_data = {
            "id": bug_id,
            "token": token,
        }
        # Map Bugzilla 4.x form fields
        field_map = {
            "status": "bug_status",
            "resolution": "resolution",
            "assigned_to": "assigned_to",
            "severity": "bug_severity",
            "priority": "priority",
        }
        for key, val in updates.items():
            form_key = field_map.get(key, key)
            form_data[form_key] = val

        # knob parameter: Bugzilla 4.x uses this to indicate the type of status change
        if "status" in updates:
            status = updates["status"]
            if status == "ASSIGNED":
                form_data["knob"] = "accept"
            elif status == "RESOLVED":
                form_data["knob"] = "resolve"
            elif status == "REOPENED":
                form_data["knob"] = "reopen"

        resp = self.session.post(
            f"{self.base_url}/process_bug.cgi",
            data=form_data,
            timeout=30,
            allow_redirects=True
        )
        resp.raise_for_status()
        return {"bugs": [{"id": int(bug_id), "changes": updates}]}

    def create_bug(self, product: str, component: str, summary: str,
                   description: str = "", version: str = "unspecified",
                   severity: str = "normal", priority: str = "P2",
                   op_sys: str = "All", platform: str = "All",
                   extra_fields: dict = None) -> Dict:
        """
        Create a new bug.
        Tries JSON-RPC Bug.create first, falls back to CGI post_bug.cgi form.

        Returns:
            {"id": <new_bug_id>}
        """
        # Option 1: JSON-RPC
        try:
            params = {
                "product": product,
                "component": component,
                "summary": summary,
                "description": description,
                "version": version,
                "severity": severity,
                "priority": priority,
                "op_sys": op_sys,
                "platform": platform,
            }
            if extra_fields:
                params.update(extra_fields)
            print(f"start bugzilla request: create_bug → {self.base_url}/jsonrpc.cgi")
            return self._jsonrpc_call("Bug.create", params)
        except BugzillaError:
            pass

        # Option 2: CGI form POST (post_bug.cgi)
        print("[bugzilla] JSON-RPC create no permission, using CGI form submission")
        token = self._get_create_token(product, component)
        form_data = {
            "product": product,
            "component": component,
            "short_desc": summary,
            "comment": description,
            "version": version,
            "bug_severity": severity,
            "priority": priority,
            "op_sys": op_sys,
            "rep_platform": platform,
            "token": token,
        }
        if extra_fields:
            cgi_field_map = {
                "assigned_to": "assigned_to",
                "cc": "cc",
                "target_milestone": "target_milestone",
                "keywords": "keywords",
            }
            for key, val in extra_fields.items():
                form_data[cgi_field_map.get(key, key)] = val

        resp = self.session.post(
            f"{self.base_url}/post_bug.cgi",
            data=form_data,
            timeout=30,
            allow_redirects=True
        )
        resp.raise_for_status()

        # Extract new bug ID — try multiple patterns
        new_bug_id = None

        # Pattern 1: redirect/final URL contains show_bug.cgi?id=XXXXX
        if "show_bug.cgi" in resp.url:
            match = re.search(r'[?&]id=(\d+)', resp.url)
            if match:
                new_bug_id = int(match.group(1))

        # Pattern 2: response body "Bug XXXXX submitted"
        if not new_bug_id:
            match = re.search(r'[Bb]ug\s+(\d+)\s+[Ss]ubmitted', resp.text)
            if match:
                new_bug_id = int(match.group(1))

        # Pattern 3: anchor/link to show_bug.cgi?id=XXXXX anywhere in body
        if not new_bug_id:
            match = re.search(r'show_bug\.cgi\?id=(\d+)', resp.text)
            if match:
                new_bug_id = int(match.group(1))

        # Pattern 4: "id=XXXXX" in final URL even without show_bug.cgi
        if not new_bug_id and "id=" in resp.url:
            match = re.search(r'[?&]id=(\d+)', resp.url)
            if match:
                new_bug_id = int(match.group(1))

        return {"id": new_bug_id, "success": True}

    def get_history(self, bug_id: str) -> Dict:
        """Retrieve Bug Fix History"""
        try:
            return self._jsonrpc_call("Bug.history", {"ids": [int(bug_id)]})
        except BugzillaError:
            # Fallback: Failed to parse history from XML; returning empty.
            return {"bugs": [{"id": int(bug_id), "history": []}]}

    def get_version(self) -> Dict:
        """Get Bugzilla version (JSON-RPC, no permission required)"""
        return self._jsonrpc_call("Bugzilla.version")


if __name__ == "__main__":
    import json, os
    from dotenv import load_dotenv

    load_dotenv()
    BASE_URL = os.getenv("BUGZILLA_BASE_URL", "https://bugzilla.tp-link.com")
    COOKIE   = os.getenv("BUGZILLA_COOKIE", "").strip()
    BUG_ID   = "1172144"

    client = BugzillaClient(base_url=BASE_URL, cookie=COOKIE)

    print(f"\n--- get_bug #{BUG_ID} ---")
    result = client.get_bug(BUG_ID)
    bugs = result.get("bugs", [])

    if not bugs:
        print(f"Bug #{BUG_ID} not found or access denied.")
    else:
        bug = bugs[0]
        # Print all fields except the raw comments list for readability
        display = {k: v for k, v in bug.items() if k != "_comments"}
        print(json.dumps(display, indent=2, ensure_ascii=False))

        comments = bug.get("_comments", [])
        print(f"\nTotal comments: {len(comments)}")
        for i, c in enumerate(comments, 1):
            print(f"  [{i}] {c.get('time', '')} | {c.get('author_name') or c.get('author', '')}")
            text_preview = (c.get("text") or "")[:120].replace("\n", " ")
            print(f"       {text_preview}")


# if __name__ == "__main__":
#     import json, os
#     from dotenv import load_dotenv

#     load_dotenv()
#     BASE_URL = os.getenv("BUGZILLA_BASE_URL", "https://bugzilla.tp-link.com")
#     COOKIE   = os.getenv("BUGZILLA_COOKIE", "").strip()
#     PRODUCT   = "Unified ID v1.7"
#     COMPONENT = "ProductID_20572_Comp"
#     VERSION   = "v1.7.44"
#     # ────────────────────────────────────────────────────────────────────────

#     client = BugzillaClient(base_url=BASE_URL, cookie=COOKIE)

#     print("\n--- create_bug ---")
#     result = client.create_bug(
#         product=PRODUCT,
#         component=COMPONENT,
#         summary="[AI Agent] Verify create_bug function",
#         description=(
#             "This bug was created automatically to verify the create_bug() function.\n"
#             "It is safe to close/resolve this bug immediately."
#         ),
#         version=VERSION,
#         extra_fields={
#             "cf_module": "Cloud_Account_Management",
#             "cf_bugcategory": "Function",
#             "cf_testcase": "无",
#             "cf_reproducesteps": "N/A",
#             "cf_testresult": "N/A",
#             "cf_expectresult": "N/A",
#             "cf_problemanalysis": "N/A",
#             "cf_bugimpact": "N/A",
#         },
#     )
#     print(json.dumps(result, indent=2, ensure_ascii=False))

#     new_bug_id = result.get("id")
#     if new_bug_id:
#         print(f"\n✓ Bug created successfully. Fetching bug #{new_bug_id} to confirm …")
#         verify = client.get_bug(str(new_bug_id))
#         bugs = verify.get("bugs", [])
#         if bugs:
#             display = {k: v for k, v in bugs[0].items() if k != "_comments"}
#             print(json.dumps(display, indent=2, ensure_ascii=False))
#         else:
#             print("Could not fetch the new bug — check permissions or bug ID.")
#     else:
#         print("\n✗ Bug creation did not return an ID. Check the response above.")