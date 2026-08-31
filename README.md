# GitHub Copilot AI Agent

> ⚠️ **Internal Network Access Required**
> Bugzilla (`https://bugzilla.tp-link.com`) and Jira (`https://pdjira.tp-link.com`) are **internal company systems**. All MCP tools and workflow scripts that interact with these services will fail if run outside the company network or VPN. Ensure you are connected to the TP-Link internal network before using this project.

This project contains four main capabilities:
1. **Bugzilla MCP Server** — A Model Context Protocol (MCP) server that exposes Bugzilla operations as tools consumable by AI Agents (e.g. GitHub Copilot Agent Mode).
2. **Jira MCP Server** — An MCP server that exposes Jira REST API operations (get, search, create, comment, transition) as tools consumable by AI Agents.
3. **Database Execution** — A script to execute SQL/MongoDB commands directly against DevOps-managed databases, bypassing the ticket approval process.
4. **Bugzilla → Jira Workflow** — An automated workflow that reads a Bugzilla bug, creates a corresponding Jira ticket, and writes the Jira link back as a Bugzilla comment. Runnable via CLI, script import, or the `/Bugzilla-Jira-Workflow` AI Agent prompt.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [File Reference](#file-reference)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Configuration](#configuration)
- [Running the MCP Servers](#running-the-mcp-servers)
- [Database Execution](#database-execution)
- [Bugzilla → Jira Workflow](#bugzilla--jira-workflow)
- [Available Tools](#available-tools)
- [Usage Examples](#usage-examples)

---

## Overview

### Bugzilla MCP Server
This project bridges **GitHub Copilot Agent Mode** and a self-hosted **Bugzilla 4.x** instance via the MCP (Model Context Protocol) standard. Instead of calling Bugzilla APIs manually, you interact in plain English — the AI Agent selects and calls the appropriate MCP tool on your behalf.

```
User (natural language)
        │
        ▼
GitHub Copilot Agent Mode
        │  MCP stdio transport
        ▼
bugzilla_mcp_server.py   ←── FastMCP server (tool definitions)
        │
        ▼
BugzillaClient           ←── HTTP layer (XML/JSON-RPC/CGI hybrid)
        │
        ▼
https://bugzilla.tp-link.com
```

### Jira MCP Server
This project also bridges **GitHub Copilot Agent Mode** and a self-hosted **Jira** instance via MCP. Interact in plain English to get issue details, search with JQL, create issues, add comments, or transition statuses.

```
User (natural language)
        │
        ▼
GitHub Copilot Agent Mode
        │  MCP stdio transport
        ▼
jira_mcp_server.py       ←── FastMCP server (tool definitions)
        │
        ▼
JiraClient               ←── HTTP layer (cookie auth)
        │
        ▼
https://pdjira.tp-link.com
```

### Database Execution
Execute SQL or MongoDB commands directly against DevOps-managed databases without going through the ticket approval workflow. Useful for quick UAT/STG data queries and one-off modifications.

```
execute_db.py
        │
        ▼
DevopsClient             ←── HTTP client (cookie + token auth)
        │
        ▼
https://devops.crd.tp-link.com/v1/api/database/execution/search
```

---

## Architecture

```
Github-Copilot-AI-Agent/
│
├── .github/
│   └── prompts/
│       ├── bugzilla.prompt.md              # Copilot Agent prompt — Bugzilla assistant
│       └── bugzilla_to_jira.prompt.md      # Copilot Agent prompt — Bugzilla → Jira workflow
│
├── .vscode/
│   └── mcp.json                        # MCP server registration for VS Code
│
├── src/
│   ├── api_definitions/
│   │   └── devops/
│   │       └── database_execution.json # API definition for DB execution endpoint
│   │
│   ├── business/
│   │   ├── bugzilla/
│   │   │   └── bugzilla_mcp_server.py  # FastMCP server — Bugzilla tool definitions
│   │   ├── jira/
│   │   │   └── jira_mcp_server.py      # FastMCP server — Jira tool definitions
│   │   ├── workflow/
│   │   │   └── bugzilla_to_jira.py     # Bugzilla → Jira automated workflow
│   │   └── database_execution/
│   │       └── execute_db.py           # DB execution script
│   │
│   ├── clients/
│   │   ├── bugzilla_client.py          # Low-level Bugzilla HTTP client
│   │   ├── jira_client.py              # Low-level Jira REST API client
│   │   ├── devops_client.py            # Low-level DevOps HTTP client
│   │   └── client_factory.py          # Factory: loads .env and constructs clients
│   │
│   └── utils/
│       └── request_builder.py          # Loads API definitions and builds requests
│
├── .env                                # Local credentials (git-ignored)
├── requirements.txt                    # Python dependencies
└── README.md
```

### How the layers fit together

| Layer | Responsibility |
|---|---|
| **VS Code / Copilot Agent** | Interprets user intent and decides which MCP tool to call |
| **`bugzilla_mcp_server.py`** | Declares MCP tools; thin wrappers that delegate to `BugzillaClient` |
| **`jira_mcp_server.py`** | Declares MCP tools; thin wrappers that delegate to `JiraClient` |
| **`execute_db.py`** | Builds and sends database execution requests via `DevopsClient` |
| **`client_factory.py`** | Reads `.env`, constructs and caches client singletons |
| **`bugzilla_client.py`** | All HTTP communication with Bugzilla (XML parsing, JSON-RPC, CGI fallbacks) |
| **`jira_client.py`** | All HTTP communication with Jira REST API (cookie auth) |
| **`devops_client.py`** | All HTTP communication with the DevOps portal (cookie + token auth) |

---

## File Reference

### `.vscode/mcp.json`
Registers both MCP servers with VS Code so GitHub Copilot Agent Mode can discover and launch them. Each server starts as a **stdio** child process using the local `venv` Python interpreter.

- **`bugzilla`** server — injects `BUGZILLA_BASE_URL` into the process environment.
- **`jira`** server — reads Jira credentials (`JIRA_BASE_URL`, `JIRA_COOKIE`) from `src/.env` via `client_factory`.

### `.github/prompts/bugzilla.prompt.md`
A **Copilot Agent prompt** (`.prompt.md` file) that sets the AI persona and lists the available tools. When you invoke this prompt in Copilot Chat, the agent knows it is a Bugzilla assistant and which tools it can call.

### `.github/prompts/bugzilla_to_jira.prompt.md`
A **Copilot Agent prompt** that drives the end-to-end Bugzilla → Jira workflow. Invoke it in Copilot Chat with `/Bugzilla-Jira-Workflow <bug_id_or_url>`. The agent will fetch bug details, check for duplicate Jira tickets, create the Jira issue, and write the result back to Bugzilla.

---

### `clients/bugzilla_client.py`
The core HTTP client for Bugzilla 4.0.1 (TP-Link internal instance). Because this version has restricted REST and JSON-RPC access, the client uses a **hybrid strategy**:

- **Reading bugs** — `show_bug.cgi?ctype=xml` (parses XML response)
- **Searching bugs** — `buglist.cgi?ctype=csv` (parses CSV response)
- **Write operations** — attempts JSON-RPC (`/jsonrpc.cgi`) first; automatically falls back to CGI form POST (`process_bug.cgi` / `post_bug.cgi`) if permissions are denied

Key methods:

| Method | Description |
|---|---|
| `get_bug(bug_id)` | Fetch a single bug and all its comments via XML |
| `get_bugs(bug_ids)` | Batch fetch multiple bugs |
| `get_comments(bug_id)` | Extract comments for a bug |
| `search_bugs(...)` | Filter bugs by product, component, status, assignee, summary |
| `add_comment(bug_id, comment)` | Post a comment (JSON-RPC → CGI fallback) |
| `update_bug(bug_id, updates)` | Update status/resolution (JSON-RPC → CGI fallback) |
| `create_bug(...)` | Create a new bug (JSON-RPC → CGI fallback) |
| `get_history(bug_id)` | Retrieve the change history for a bug |
| `get_version()` | Get Bugzilla server version |

Authentication is handled via **cookie** (`Bugzilla_login` + `Bugzilla_logincookie`) and optionally an **API key** header, both supplied through the factory.

---

### `clients/client_factory.py`
A singleton factory responsible for:

1. **Loading `.env`** — parses `KEY=VALUE` pairs and sets them as environment variables (skips keys already set in the environment, so CI/CD injected values take priority).
2. **Prompting for missing credentials** — if a required credential is absent from `.env` *and* the environment, it falls back to `input()` to prompt the user at runtime (useful during development).
3. **Constructing and caching clients** — each system (`"bugzilla"`) is instantiated once and reused for the lifetime of the process.

---

### `clients/jira_client.py`
HTTP client for the Jira REST API (`/rest/api/2/`). Authenticates via **cookie** (`JSESSIONID` + `atlassian.xsrf.token`) supplied through the factory.

| Method | Description |
|---|---|
| `get_issue(issue_key)` | Fetch a single issue's full details |
| `search_issues(jql, max_results)` | Search issues using a JQL query |
| `create_issue(...)` | Create a new issue with full field support |
| `batch_create_issues(issues)` | Bulk-create multiple issues in one request |
| `add_comment(issue_key, body)` | Post a comment on an issue |
| `transition_issue(issue_key, transition_id)` | Move an issue to a new status |

---

### `src/business/jira/jira_mcp_server.py`
The **FastMCP server** for Jira — launched by VS Code alongside the Bugzilla server. It:

- Creates a `FastMCP("jira")` instance.
- Exposes each Jira operation as an `@mcp.tool()` decorated function.
- Delegates all real work to `JiraClient` via `client_factory.get_client("jira")`.
- Runs via `mcp.run()` using stdio transport when executed directly.

Registered tools:

| Tool | Purpose |
|---|---|
| `get_jira_issue` | Get full details of a Jira issue |
| `search_jira_issues` | Search issues with a JQL query |
| `get_my_jira_issues` | List issues assigned to the current user |
| `create_jira_issue` | Create a new Jira issue |
| `add_jira_comment` | Add a comment to an issue |
| `transition_jira_issue` | Transition an issue to a new status |

---

### `src/business/bugzilla/bugzilla_mcp_server.py`
The **FastMCP server** for Bugzilla — the entry point launched by VS Code. It:

- Creates a `FastMCP("bugzilla")` instance.
- Exposes each Bugzilla operation as an `@mcp.tool()` decorated function with typed arguments and docstrings (the docstrings become the tool descriptions shown to the AI).
- Delegates all real work to `BugzillaClient` via `client_factory.get_client("bugzilla")`.
- Runs via `mcp.run()` using stdio transport when executed directly.

Registered tools:

| Tool | Purpose |
|---|---|
| `bugzilla_get_bug` | Get full details of a bug |
| `bugzilla_search_bugs` | Search bugs with filters |
| `bugzilla_get_comments` | List all comments on a bug |
| `bugzilla_add_comment` | Add a comment to a bug |
| `bugzilla_update_bug` | Change bug status / resolution |
| `bugzilla_create_bug` | Create a new bug |

---

### `src/business/workflow/bugzilla_to_jira.py`
Implements the automated Bugzilla → Jira workflow. Can be invoked three ways:

1. **CLI**: `python src/business/workflow/bugzilla_to_jira.py 12345 12346`
2. **Script import**: call `run_workflow(arguments)` from other Python scripts
3. **AI Agent prompt**: use `/Bugzilla-Jira-Workflow` in Copilot Chat

Key functions:

| Function | Description |
|---|---|
| `run_workflow(arguments, ...)` | Entry point — parses bug IDs, runs the full pipeline, returns a summary dict |
| `process_single_bug(...)` | Processes one bug: fetch → deduplicate → create Jira ticket → comment Bugzilla |
| `check_jira_duplicate(...)` | Searches Jira for an existing ticket for the same bug |
| `map_priority(severity, bz_priority)` | Maps Bugzilla severity to Jira priority |
| `format_jira_description(...)` | Builds the Jira ticket description from Bugzilla bug fields |

---

### `src/clients/devops_client.py`
HTTP client for the internal DevOps portal (`https://devops.crd.tp-link.com`). Authenticates via **cookie** and **Authorization** header (plus an optional `authorization-ims` bearer token). SSL verification is disabled because the DevOps host uses a self-signed certificate.

| Method | Description |
|---|---|
| `request(method, endpoint, **kwargs)` | Generic HTTP request — prepends `base_url` and delegates to `requests.Session` |

---

### `src/api_definitions/devops/database_execution.json`
Declarative API definition for the `POST /v1/api/database/execution/search` endpoint. Consumed by `request_builder` to construct the final HTTP request, keeping endpoint metadata out of business logic.

---

### `src/business/database_execution/execute_db.py`
Script that executes SQL or MongoDB commands directly against DevOps-managed databases. Key functions:

| Function | Description |
|---|---|
| `build_execution_payload(...)` | Assembles the JSON body for the execution request |
| `execute_db_command(devops_client, payload)` | Loads the API definition, builds the request, sends it, and returns the parsed response |

---

## Prerequisites

- Python **3.10+**
- A Bugzilla 4.x instance accessible over HTTPS
- A valid Bugzilla **session cookie** (obtained by logging in via browser)
- A valid Jira **session cookie** (`JSESSIONID` + `atlassian.xsrf.token`, obtained from the browser)
- A valid DevOps **cookie** and **Authorization** token (for database execution)
- **VS Code** with the **GitHub Copilot** extension (for Agent Mode)

---

## Setup

**1. Clone the repository**

```bash
git clone <repo-url>
cd Github-Copilot-AI-Agent
```

**2. Create and activate a virtual environment**

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

**4. Configure credentials** — see [Configuration](#configuration) below.

---

## Configuration

Create a `.env` file in the project root (it is already git-ignored):

```env
# Bugzilla
BUGZILLA_BASE_URL   = https://bugzilla.example.com
BUGZILLA_COOKIE     = Bugzilla_login=YOUR_LOGIN_VALUE; Bugzilla_logincookie=YOUR_COOKIE_VALUE

# Jira
JIRA_BASE_URL       = https://pdjira.tp-link.com
JIRA_COOKIE         = JSESSIONID=YOUR_JSESSIONID; atlassian.xsrf.token=YOUR_XSRF_TOKEN

# DevOps (for database execution)
DEVOPS_COOKIE       = YOUR_DEVOPS_COOKIE
DEVOPS_AUTH         = YOUR_DEVOPS_AUTHORIZATION_TOKEN
DEVOPS_AUTH_IMS     = YOUR_IMS_BEARER_TOKEN   # optional
```

### How to get your Bugzilla cookie

1. Log in to Bugzilla in your browser.
2. Open **DevTools → Application → Cookies**.
3. Copy the values for `Bugzilla_login` and `Bugzilla_logincookie`.
4. Paste them into `.env` as shown above.

> Cookies expire when you log out or after a session timeout. Regenerate them when operations start returning authentication errors.

### How to get your Jira cookie

1. Log in to Jira in your browser.
2. Open **DevTools → Application → Cookies**.
3. Copy the values for `JSESSIONID` and `atlassian.xsrf.token`.
4. Paste them into `.env` as shown above.

### How to get your DevOps credentials

1. Log in to the DevOps portal in your browser.
2. Open **DevTools → Application → Cookies** and copy the full cookie string into `DEVOPS_COOKIE`.
3. Open **DevTools → Network**, trigger any request, and copy the `Authorization` header value into `DEVOPS_AUTH`.
4. If requests return 401, also copy the `authorization-ims` header value into `DEVOPS_AUTH_IMS`.

---

## Running the MCP Servers

### Via VS Code (recommended)

Both servers are registered in `.vscode/mcp.json` and start automatically when GitHub Copilot Agent Mode needs them. No manual steps are required — just open the project in VS Code with the Copilot extension active.

To use the Bugzilla Agent persona, open Copilot Chat and select the **Bugzilla Assistant** prompt from `.github/prompts/bugzilla.prompt.md`.

### Manually (for debugging)

```bash
# Bugzilla MCP server
python src/business/bugzilla/bugzilla_mcp_server.py

# Jira MCP server
python src/business/jira/jira_mcp_server.py
```

Both servers start listening on stdio when run directly.

---

## Database Execution

Execute SQL or MongoDB commands directly against a DevOps-managed instance, bypassing the ticket approval workflow.

### Running

```bash
cd src/business/database_execution
PYTHONPATH=../../ python execute_db.py
```

On Windows (with the venv activated):

```powershell
cd src\business\database_execution
$env:PYTHONPATH = "..\..\.."; python execute_db.py
```

### Example — Query

```python
from clients.client_factory import get_client
from business.database_execution.execute_db import build_execution_payload, execute_db_command

devops_client = get_client("devops")

payload = build_execution_payload(
    applicant_name="Minh Le",
    email="minh.le@domain.com",
    command="SELECT * FROM TABLE'",
    database_list=[{"name": "database"}],
    database_type="MySQL",
    environment="UAT",
    instance_name="instance_name",
    operation_type="DB_QUERY",
    region="region",
    service_name="service_name",
)

result = execute_db_command(devops_client, payload)
print(result)
```
---

## Bugzilla → Jira Workflow

Automatically converts a Bugzilla bug into a Jira ticket and writes the result back to Bugzilla.

### Via AI Agent (recommended)

In Copilot Chat (Agent Mode), type:

```
/Bugzilla-Jira-Workflow 1254348
```

or with a full URL:

```
/Bugzilla-Jira-Workflow https://bugzilla.tp-link.com/show_bug.cgi?id=1254348
```

The agent will:
1. Fetch bug details from Bugzilla
2. Check for an existing duplicate Jira ticket
3. Create a new Jira Bug ticket (project `UID` by default)
4. Add a comment to the Bugzilla bug with the Jira link
5. Update the Bugzilla status to `ASSIGNED` if it was `NEW` or `UNCONFIRMED`

### Via CLI

```bash
python src/business/workflow/bugzilla_to_jira.py 1254348
# or multiple bugs:
python src/business/workflow/bugzilla_to_jira.py 1254348 1254349
```

### Output

```json
{
  "total": 1,
  "created": 1,
  "skipped": 0,
  "failed": 0,
  "results": [
    {
      "bug_id": "1254348",
      "bug_summary": "[Company Transfer Owner] Unverified Member Appears in Candidate List",
      "jira_key": "UID-336",
      "jira_url": "https://pdjira.tp-link.com/browse/UID-336",
      "bugzilla_url": "https://bugzilla.tp-link.com/show_bug.cgi?id=1254348",
      "status": "created",
      "message": "Successfully created"
    }
  ]
}
```

> ⚠️ Requires internal network access to both Bugzilla and Jira.

---

## Available Tools

### Bugzilla

| Tool | Key Arguments | Description |
|---|---|---|
| `bugzilla_get_bug` | `bug_id` | Retrieve bug details (summary, product, component, severity, status, etc.) |
| `bugzilla_search_bugs` | `product`, `component`, `status`, `assigned_to`, `summary`, `limit` | Search bugs with optional filters |
| `bugzilla_get_comments` | `bug_id` | List all comments with author and timestamp |
| `bugzilla_add_comment` | `bug_id`, `comment` | Post a new comment |
| `bugzilla_update_bug` | `bug_id`, `status`, `resolution` | Update bug status and/or resolution |
| `bugzilla_create_bug` | `product`, `component`, `summary`, `description`, `severity`, `priority`, `extra_fields`, … | Create a new bug with full field support |

### Jira

| Tool | Key Arguments | Description |
|---|---|---|
| `get_jira_issue` | `issue_key` | Get full details of a Jira issue (e.g. `UID-292`) |
| `search_jira_issues` | `jql`, `max_results` | Search issues using a JQL query |
| `get_my_jira_issues` | `max_results` | List issues assigned to the current user |
| `create_jira_issue` | `project_key`, `summary`, `description`, `issue_type`, `priority`, `components` | Create a new Jira issue |
| `add_jira_comment` | `issue_key`, `comment` | Add a comment to an issue |
| `transition_jira_issue` | `issue_key`, `transition_id` | Move an issue to a new status |

---

## Usage Examples

### Bugzilla

All examples below are natural language prompts typed into **GitHub Copilot Chat** (Agent Mode, with the Bugzilla MCP server active).

```
Get the details of bug #1256082
```

```
Search for all OPEN bugs in the "HomeShield" product assigned to john@example.com
```

```
Add a comment "Rejected by AI Agent" to bug https://bugzilla.tp-link.com/show_bug.cgi?id=1256082
```

```
Resolve bug #1256082 as FIXED
```

```
Create a new bug in product "Unified ID v1.7", component "Login", summary "Login fails on Safari 17"
```

### Jira

All examples below are natural language prompts typed into **GitHub Copilot Chat** (Agent Mode, with the Jira MCP server active).

```
Get the details of Jira ticket https://pdjira.tp-link.com/browse/UID-292
```

```
Search for all open Jira issues in project UID assigned to me
```

```
Create a Jira task in project UID with summary "Fix session expiry handling" and priority High
```

```
Add a comment "Verified on UAT" to Jira ticket UID-292
```
