import os
import sys

from mcp.server.fastmcp import FastMCP

# Add the src directory to the path so 'clients' package is importable
current_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.insert(0, workspace_root)

from clients.client_factory import get_client

mcp = FastMCP("confluence-server")

_client = None


def get_confluence_client():
    global _client
    if _client is None:
        _client = get_client("confluence-server")
    return _client


@mcp.tool()
def list_confluence_spaces(limit: int = 100) -> list:
    """
    List accessible Confluence spaces.

    Args:
        limit: Max number of spaces to return.

    Returns:
        List of spaces with key, name, and type.
    """
    return get_confluence_client().list_spaces(limit=limit)


@mcp.tool()
def search_confluence_space(space_key: str, query: str = None, limit: int = 25) -> list:
    """
    Search for pages within a Confluence space.

    Args:
        space_key: Space key, e.g. "RDCS".
        query: Optional text query.
        limit: Max number of matching pages to return.

    Returns:
        List of matching pages with id, title, and URL.
    """
    return get_confluence_client().search_space(
        space_key=space_key,
        query=query,
        limit=limit,
    )


@mcp.tool()
def get_confluence_space_pages(space_key: str, limit: int = 100) -> list:
    """
    Get pages from a Confluence space.

    Args:
        space_key: Space key, e.g. "RDCS".
        limit: Max number of pages to return.

    Returns:
        List of pages with id, title, and URL.
    """
    return get_confluence_client().get_space_pages(space_key=space_key, limit=limit)


@mcp.tool()
def get_confluence_page(page_id: str) -> dict:
    """
    Get Confluence page details.

    Args:
        page_id: Confluence page ID.

    Returns:
        Page details including title, space, version, HTML, text, and URL.
    """
    return get_confluence_client().get_page(page_id)


@mcp.tool()
def get_confluence_page_text(page_id: str) -> dict:
    """
    Get the plain text content of a Confluence page.

    Args:
        page_id: Confluence page ID.

    Returns:
        Page ID and extracted plain text.
    """
    return {
        "page_id": page_id,
        "text": get_confluence_client().get_page_text(page_id),
    }


@mcp.tool()
def create_confluence_page(space_key: str, title: str, content: str,
                           parent_id: str = None, is_html: bool = False) -> dict:
    """
    Create a Confluence page.

    Args:
        space_key: Destination space key.
        title: Page title.
        content: Page content.
        parent_id: Optional parent page ID.
        is_html: Whether content is already Confluence storage HTML.

    Returns:
        Created page result.
    """
    return get_confluence_client().create_page(
        space_key=space_key,
        title=title,
        content=content,
        parent_id=parent_id,
        is_html=is_html,
    )


@mcp.tool()
def update_confluence_page(page_id: str, title: str = None, content: str = None,
                           is_html: bool = False) -> dict:
    """
    Update a Confluence page.

    Args:
        page_id: Confluence page ID.
        title: Optional new title.
        content: Optional new content.
        is_html: Whether content is already Confluence storage HTML.

    Returns:
        Updated page result.
    """
    return get_confluence_client().update_page(
        page_id=page_id,
        title=title,
        content=content,
        is_html=is_html,
    )


@mcp.tool()
def append_to_confluence_page(page_id: str, content: str, is_html: bool = False) -> dict:
    """
    Append content to an existing Confluence page.

    Args:
        page_id: Confluence page ID.
        content: Content to append.
        is_html: Whether content is already Confluence storage HTML.

    Returns:
        Updated page result.
    """
    return get_confluence_client().append_to_page(
        page_id=page_id,
        content=content,
        is_html=is_html,
    )


@mcp.tool()
def get_confluence_comments(page_id: str) -> list:
    """
    Get comments for a Confluence page.

    Args:
        page_id: Confluence page ID.

    Returns:
        List of page comments.
    """
    return get_confluence_client().get_comments(page_id)


@mcp.tool()
def add_confluence_comment(page_id: str, comment: str) -> dict:
    """
    Add a comment to a Confluence page.

    Args:
        page_id: Confluence page ID.
        comment: Comment text.

    Returns:
        Comment creation result.
    """
    return get_confluence_client().add_comment(page_id, comment)



if __name__ == "__main__":
    mcp.run()
