"""
Confluence API Client
"""

import requests
from bs4 import BeautifulSoup
from typing import Optional, List, Dict, Any
import os
import sys
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ConfluenceClient:    

    def __init__(
        self,
        base_url: str = None,
        cookie: str = None,
        token: str = None
    ):
        
        self.base_url = base_url or os.environ.get("CONFLUENCE_BASE_URL")
                
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        if token or os.environ.get("CONFLUENCE_TOKEN"):
            token = token or os.environ.get("CONFLUENCE_TOKEN")
            self.headers["Authorization"] = f"Bearer {token}"
        elif cookie or os.environ.get("CONFLUENCE_SESSION_ID"):
            cookie = cookie or os.environ.get("CONFLUENCE_SESSION_ID")
            self.headers["Cookie"] = f"{cookie}"
        else:
            raise ValueError(
                "Authentication credentials required: CONFLUENCE_TOKEN or CONFLUENCE_SESSION_ID"
            )    
        

    def search_space(
        self,
        space_key: str,
        query: Optional[str] = None,
        limit: int = 25
    ) -> List[Dict[str, Any]]:
        """
        Search for pages within a Confluence space.

        Args:
        space_key: The Space identifier (e.g., "RDCS").
        query: Search keywords (optional).
        limit: The maximum number of results to return.

        Returns:
        A list of pages in the format [{id, title, url}, ...].
        """
        if query:
            cql = f'space="{space_key}" AND type=page AND text~"{query}"'
        else:
            cql = f'space="{space_key}" AND type=page'

        url = f"{self.base_url}/rest/api/search"
        params = {
            "cql": cql,
            "limit": limit
        }

        try:
            response = requests.get(
                url,
                headers=self.headers,
                params=params,
                verify=False,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            pages = []
            for item in data.get("results", []):
                content = item.get("content", {})
                pages.append({
                    "id": content.get("id"),
                    "title": content.get("title"),
                    "url": f"{self.base_url}/pages/viewpage.action?pageId={content.get('id')}"
                })

            return pages

        except requests.exceptions.RequestException as e:
            print(f"Search failed:: {e}")
            return []

    def get_page(self, page_id: str) -> Dict[str, Any]:
        """
        Retrieve Page Details

        Args:
        page_id: Page ID

        Returns:
        Page information {id, title, html, text, url}
        """
        url = f"{self.base_url}/rest/api/content/{page_id}"
        params = {
            "expand": "body.storage,version,space"
        }

        try:
            response = requests.get(
                url,
                headers=self.headers,
                params=params,
                verify=False,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            html = data.get("body", {}).get("storage", {}).get("value", "")
            text = self._html_to_text(html)

            return {
                "id": data.get("id"),
                "title": data.get("title"),
                "space": data.get("space", {}).get("key"),
                "version": data.get("version", {}).get("number"),
                "html": html,
                "text": text,
                "url": f"{self.base_url}/pages/viewpage.action?pageId={page_id}"
            }

        except requests.exceptions.RequestException as e:
            print(f"Failed to retrieve page: {e}")
            return {}

    def get_page_text(self, page_id: str) -> str:
        """
        Retrieve the plain text content of a page.

        Args:
        page_id: The page ID.

        Returns:
        The text content of the page.
        """
        page = self.get_page(page_id)
        return page.get("text", "")

    def list_spaces(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        List all accessible spaces.

        Args:
        limit: The maximum number of results to return.

        Returns:
        A list of Spaces: [{key, name, type}, ...]
        """
        url = f"{self.base_url}/rest/api/space"
        params = {"limit": limit}

        try:
            response = requests.get(
                url,
                headers=self.headers,
                params=params,
                verify=False,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            spaces = []
            for space in data.get("results", []):
                spaces.append({
                    "key": space.get("key"),
                    "name": space.get("name"),
                    "type": space.get("type")
                })

            return spaces

        except requests.exceptions.RequestException as e:
            print(f"获取 spaces 失败: {e}")
            return []

    def get_space_pages(
        self,
        space_key: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all pages within a space.

        Args:
        space_key: The Space identifier.
        limit: The maximum number of results to return.

        Returns:
        A list of pages.
        """
        url = f"{self.base_url}/rest/api/space/{space_key}/content/page"
        params = {"limit": limit}

        try:
            response = requests.get(
                url,
                headers=self.headers,
                params=params,
                verify=False,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            pages = []
            for page in data.get("results", []):
                pages.append({
                    "id": page.get("id"),
                    "title": page.get("title"),
                    "url": f"{self.base_url}/pages/viewpage.action?pageId={page.get('id')}"
                })

            return pages

        except requests.exceptions.RequestException as e:
            print(f"Failed to retrieve page list: {e}")
            return []

    def update_page(
        self,
        page_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        is_html: bool = False
    ) -> Dict[str, Any]:
        """
       Update Page Content

        Args:
        page_id: Page ID
        title: New title (Optional; if omitted, the original title is retained)
        content: New content (Plain text or HTML)
        is_html: Whether the content is in HTML format (If False, it is automatically converted)

        Returns:
        Updated page information
        """
        current_page = self.get_page(page_id)
        if not current_page:
            return {"error": "Page does not exist"}

        current_version = current_page.get("version", 1)
        current_title = current_page.get("title", "")
        space_key = current_page.get("space", "")

        new_title = title if title else current_title

        if content:
            if is_html:
                new_html = content
            else:
                new_html = self._text_to_html(content)
        else:
            new_html = current_page.get("html", "")

        url = f"{self.base_url}/rest/api/content/{page_id}"
        payload = {
            "id": page_id,
            "type": "page",
            "title": new_title,
            "space": {"key": space_key},
            "body": {
                "storage": {
                    "value": new_html,
                    "representation": "storage"
                }
            },
            "version": {
                "number": current_version + 1
            }
        }

        try:
            response = requests.put(
                url,
                headers=self.headers,
                json=payload,
                verify=False,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            return {
                "success": True,
                "id": data.get("id"),
                "title": data.get("title"),
                "version": data.get("version", {}).get("number"),
                "url": f"{self.base_url}/pages/viewpage.action?pageId={page_id}"
            }

        except requests.exceptions.RequestException as e:
            return {"error": f"Update failed: {e}"}

    def append_to_page(
        self,
        page_id: str,
        content: str,
        is_html: bool = False
    ) -> Dict[str, Any]:
        """
        Append content to the end of a page
        
        Args:
            page_id: Page ID
            content: Content to append
            is_html: Whether the content is in HTML format
        
        Returns:
            Updated page information
        """
        current_page = self.get_page(page_id)
        if not current_page:
            return {"error": "Page does not exist"}

        current_html = current_page.get("html", "")

        if is_html:
            new_content_html = content
        else:
            new_content_html = self._text_to_html(content)

        combined_html = current_html + new_content_html

        return self.update_page(page_id, content=combined_html, is_html=True)

    def create_page(
        self,
        space_key: str,
        title: str,
        content: str,
        parent_id: Optional[str] = None,
        is_html: bool = False
    ) -> Dict[str, Any]:
        """
        Create a new page
        
        Args:
            space_key: Space key
            title: Page title
            content: Page content
            parent_id: Parent page ID (Optional)
            is_html: Whether the content is in HTML format
        
        Returns:
            Created page information
        """
        if is_html:
            html_content = content
        else:
            html_content = self._text_to_html(content)

        url = f"{self.base_url}/rest/api/content"
        payload = {
            "type": "page",
            "title": title,
            "space": {"key": space_key},
            "body": {
                "storage": {
                    "value": html_content,
                    "representation": "storage"
                }
            }
        }

        if parent_id:
            payload["ancestors"] = [{"id": parent_id}]

        try:
            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                verify=False,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            return {
                "success": True,
                "id": data.get("id"),
                "title": data.get("title"),
                "url": f"{self.base_url}/pages/viewpage.action?pageId={data.get('id')}"
            }

        except requests.exceptions.RequestException as e:
            return {"error": f"Create failed: {e}"}

    def add_comment(
        self,
        page_id: str,
        comment: str
    ) -> Dict[str, Any]:
        """
        Add a comment to a page
        
        Args:
            page_id: Page ID
            comment: Comment content (plain text)
        
        Returns:
            Comment result
        """
        url = f"{self.base_url}/rest/api/content"
        
        html_comment = self._text_to_html(comment)
        
        payload = {
            "type": "comment",
            "container": {
                "id": page_id,
                "type": "page"
            },
            "body": {
                "storage": {
                    "value": html_comment,
                    "representation": "storage"
                }
            }
        }

        try:
            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                verify=False,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            return {
                "success": True,
                "comment_id": data.get("id"),
                "page_id": page_id
            }

        except requests.exceptions.RequestException as e:
            return {"error": f"Add comment failed: {e}"}

    def get_comments(self, page_id: str) -> List[Dict[str, Any]]:
        """
        Get all comments for a page
        
        Args:
            page_id: Page ID
        
        Returns:
            List of comments
        """
        url = f"{self.base_url}/rest/api/content/{page_id}/child/comment"
        params = {
            "expand": "body.storage,version",
            "limit": 100
        }

        try:
            response = requests.get(
                url,
                headers=self.headers,
                params=params,
                verify=False,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            comments = []
            for item in data.get("results", []):
                html = item.get("body", {}).get("storage", {}).get("value", "")
                comments.append({
                    "id": item.get("id"),
                    "text": self._html_to_text(html),
                    "version": item.get("version", {}).get("number")
                })

            return comments

        except requests.exceptions.RequestException as e:
            print(f"Get comments failed: {e}")
            return []

    def _text_to_html(self, text: str) -> str:
        """
        Convert plain text to Confluence HTML format
        
        Args:
            text: Plain text
        
        Returns:
            HTML formatted content
        """
        if not text:
            return ""

        import html
        escaped = html.escape(text)
        paragraphs = escaped.split("\n\n")
        html_parts = []

        for para in paragraphs:
            lines = para.split("\n")
            formatted_lines = "<br/>".join(lines)
            html_parts.append(f"<p>{formatted_lines}</p>")

        return "".join(html_parts)

    def _html_to_text(self, html: str) -> str:
        """
        Convert HTML to plain text
        
        Args:
            html: HTML content
        
        Returns:
            Plain text
        """
        if not html:
            return ""

        soup = BeautifulSoup(html, "html.parser")

        for script in soup(["script", "style"]):
            script.decompose()

        text = soup.get_text(separator="\n")

        lines = [line.strip() for line in text.splitlines()]
        text = "\n".join(line for line in lines if line)

        return text

if __name__ == "__main__":
    
    import json, os
    from dotenv import load_dotenv
    
    load_dotenv()
    CONFLUENCE_BASE_URL = os.environ.get("CONFLUENCE_BASE_URL")    
    CONFLUENCE_COOKIE = os.environ.get("CONFLUENCE_COOKIE")            

    print("🚀 Confluence Client Test")
    print("=" * 60)

    try:
        client = ConfluenceClient(base_url=CONFLUENCE_BASE_URL, cookie=CONFLUENCE_COOKIE)
        print("✅ Client initialized successfully")
    except Exception as e:
        print(f"❌ Client initialization failed: {e}")
        sys.exit(1)
    
    print("=" * 60)
    print("🔍 Searching for pages in space 'EBGQA'")
    _space = client.search_space("EBGQA", limit=5)   # ~minh.le@tp-link.com
    print(json.dumps(_space, indent=2))
    
    print("=" * 60)
    print("📄 Read the page id '332011472'")
    _page = client.get_page_text("332011472")   
    print(_page)
    
    # print("\n📂 Test: List Spaces...")
    # spaces = client.list_spaces(limit=50)
    # if spaces:
    #     print(f"✅ Retrieved {len(spaces)} spaces:")
    #     for space in spaces:
    #         print(f"   - {space['key']}: {space['name']}")
    # else:
    #     print("⚠️ No spaces retrieved (possible permission issue)")

    # if len(sys.argv) > 1:
    #     space_key = sys.argv[1]
    #     print(f"\n🔍 Test: Search Space '{space_key}'...")
    #     pages = client.search_space(space_key, limit=5)
    #     if pages:
    #         print(f"✅ Retrieved {len(pages)} pages:")
    #         for page in pages[:5]:
    #             print(f"   - [{page['id']}] {page['title']}")

    #         print(f"\n📄 Test: Read the first page...")
    #         first_page = pages[0]
    #         page_detail = client.get_page(first_page['id'])
    #         if page_detail:
    #             print(f"✅ Page Title: {page_detail.get('title')}")
    #             print(f"   Space: {page_detail.get('space')}")
    #             print(f"   Version: {page_detail.get('version')}")
    #             text = page_detail.get('text', '')[:500]
    #             print(f"   Content Preview:\n{text}...")
    #     else:
    #         print("⚠️ No pages found")

    print("\n" + "=" * 60)
    print("✅ Test completed")