# GitHub Copilot QA Assistant

> Internal network access is required. The Bugzilla, Jira, and Confluence integrations target internal systems and will not work outside the company network or VPN.

This repository contains MCP servers and API clients for three internal systems:

1. Bugzilla
2. Jira
3. Confluence

Older database-execution and Bugzilla-to-Jira workflow sections were removed because those code paths are not present in the current repository.

## Overview

Each MCP server exposes a focused tool surface for GitHub Copilot Agent Mode:

- Bugzilla: get bugs, search bugs, get comments, add comments, update bugs, create bugs
- Jira: get issues, search issues, get assigned issues, create issues, add comments, transition issues
- Confluence: list spaces, search pages, get pages, extract page text, create pages, update pages, append content, manage comments

## Project Structure

```text
.
|-- README.md
|-- requirements.txt
|-- Documentation/
|   |-- QA-Assistant-Bugzilla-Operations.md
|   `-- QA-Assistant-Jira-Server-Operations.md
`-- src/
    |-- clients/
    |   |-- bugzilla_client.py
    |   |-- client_factory.py
    |   |-- confluence_client.py
    |   `-- jira_client.py
    `-- mcp_servers/
        |-- bugzilla_mcp_server.py
        |-- confluence_mcp_server.py
        `-- jira_mcp_server.py
```

## How It Works

```text
GitHub Copilot Agent Mode
        |
        v
VS Code MCP registration (.vscode/mcp.json)
        |
        v
src/mcp_servers/*.py
        |
        v
src/clients/*.py
        |
        v
Internal Bugzilla / Jira / Confluence APIs
```

## Prerequisites

- Python 3.10+
- Access to the internal Bugzilla, Jira, and/or Confluence instances
- Valid credentials for the systems you want to use
- VS Code with GitHub Copilot

## Setup

```bash
python -m venv venv

# Windows
venv\Scripts\activate

pip install -r requirements.txt
```

Create a `.env` file in the project root by copying `.env.example` and filling in your values.

```env
BUGZILLA_BASE_URL=https://bugzilla.example.com
BUGZILLA_COOKIE=Bugzilla_login=YOUR_LOGIN_VALUE; Bugzilla_logincookie=YOUR_COOKIE_VALUE
BUGZILLA_API_KEY=

JIRA_BASE_URL=https://pdjira.example.com
JIRA_COOKIE=JSESSIONID=YOUR_JIRA_COOKIE_VALUE

CONFLUENCE_BASE_URL=https://pdconfluence.example.com
CONFLUENCE_COOKIE=JSESSIONID=YOUR_CONFLUENCE_COOKIE_VALUE
CONFLUENCE_TOKEN=
```

Notes:

- `src/clients/client_factory.py` loads `.env` from the repository root.
- Bugzilla supports cookie auth and an optional API key.
- Jira is currently initialized from base URL plus cookie.
- Confluence can use a cookie or bearer token.

## Running The MCP Servers

VS Code reads server registration from `.vscode/mcp.json`.

You can also start the servers manually:

```bash
python src/mcp_servers/bugzilla_mcp_server.py
python src/mcp_servers/jira_mcp_server.py
python src/mcp_servers/confluence_mcp_server.py
```

## Available Tools

### Bugzilla

- `bugzilla_get_bug`
- `bugzilla_search_bugs`
- `bugzilla_get_comments`
- `bugzilla_add_comment`
- `bugzilla_update_bug`
- `bugzilla_create_bug`

### Jira

- `get_jira_issue`
- `search_jira_issues`
- `get_my_jira_issues`
- `create_jira_issue`
- `add_jira_comment`
- `transition_jira_issue`

### Confluence

- `list_confluence_spaces`
- `search_confluence_space`
- `get_confluence_space_pages`
- `get_confluence_page`
- `get_confluence_page_text`
- `create_confluence_page`
- `update_confluence_page`
- `append_to_confluence_page`
- `get_confluence_comments`
- `add_confluence_comment`

## Usage Examples

Example prompts for Copilot Agent Mode:

```text
Get the details of bug 1256082
```

```text
Search Jira issues in project UID assigned to me
```

```text
List Confluence spaces I can access
```

```text
Get the plain text of Confluence page 123456789
```

## Documentation

Additional operation notes are available in `Documentation/`.
