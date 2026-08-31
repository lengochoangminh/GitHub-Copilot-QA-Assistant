# GitHub Copilot QA Assistant - Jira Server operations

> ⚠️ **Internal Network Access Required** <br>
> Jira Server (`https://pdjira.tp-link.com`) is an internal company system. MCP tools and workflow scripts that call Jira will fail outside the company network or VPN. Connect to the internal network before using this integration.

This project exposes Jira Server operations to GitHub Copilot through a local MCP server. The current implementation lets Copilot read Jira issues, search issues with JQL, list issues assigned to the current user, create issues, add comments, and transition issues by calling Python code in this repository.

The repository already contains one important customization point:

- `.vscode/mcp.json` registers the local MCP server so Copilot can discover its Jira tools.

Unlike the Bugzilla integration, the repository does not currently include a Jira-specific prompt file under `.github/prompts`. The Jira MCP server is implemented and registered, but there is no Jira prompt yet to narrow tool choice or define Jira-specific assistant behavior.

## Current Implementation

### 1. MCP server layer

The main Jira MCP entry point is `src/mcp_servers/jira_mcp_server.py`.

It creates a FastMCP server named `jira-server` and exposes these tools with `@mcp.tool()`:

- `get_jira_issue`
- `search_jira_issues`
- `get_my_jira_issues`
- `create_jira_issue`
- `add_jira_comment`
- `transition_jira_issue`

These are the tool functions Copilot can call after the MCP server is registered.

### 2. Jira client layer

The Jira integration logic lives in `src/clients/jira_client.py`.

This client uses Jira Server REST API v2 endpoints under `/rest/api/2/` and currently supports:

- issue creation through `POST /issue`
- bulk issue creation through `POST /issue/bulk`
- JQL search through `GET /search`
- single issue lookup through `GET /issue/{issueKey}`
- comment creation through `POST /issue/{issueKey}/comment`
- status transition through `POST /issue/{issueKey}/transitions`

Implemented client methods include:

- `request`
- `create_issue`
- `batch_create_issues`
- `search_issues`
- `get_issue`
- `add_comment`
- `transition_issue`

### 3. Client factory and environment loading

`src/clients/client_factory.py` is responsible for:

- loading values from the root `.env` file
- caching instantiated clients
- constructing the `JiraClient`

The current Jira configuration keys are:

- `JIRA_BASE_URL`
- `JIRA_COOKIE`
- `JIRA_TOKEN`

Behavior details matter here:

- the factory explicitly prompts for `JIRA_BASE_URL` and `JIRA_COOKIE`
- the `JiraClient` itself prefers `JIRA_TOKEN` over `JIRA_COOKIE` if `JIRA_TOKEN` already exists in the environment
- if neither token nor cookie is available when the client is created, initialization fails
- if a key exists in `.env` with an empty value, it is treated as intentionally defined and the factory will not prompt for it

This means token authentication is supported by the client, but the factory does not currently prompt for `JIRA_TOKEN`. If you want token-based setup without interactive changes, define `JIRA_TOKEN` in the root `.env` file before starting the MCP server.

### 4. Python dependencies

Current dependencies from `requirements.txt`:

- `requests`
- `urllib3`
- `fastmcp`
- `python-dotenv`
- `beautifulsoup4`

The Jira path directly uses `requests`, `urllib3`, and `fastmcp`. The shared environment loading flow also depends on `python-dotenv` being available elsewhere in the project setup.

## How the Current MCP Integration Works

The registration file is `.vscode/mcp.json`.

```json
{
  "servers": {
    "bugzilla": {
      "command": "python",
      "args": ["src/mcp_servers/bugzilla_mcp_server.py"],
      "cwd": "${workspaceFolder}",
      "env": {
        "PYTHONPATH": "${workspaceFolder}/src"
      }
    },
    "jira-server": {
      "command": "python",
      "args": ["src/mcp_servers/jira_mcp_server.py"],
      "cwd": "${workspaceFolder}",
      "env": {
        "PYTHONPATH": "${workspaceFolder}/src"
      }
    }
  }
}
```

For Jira, this does four things:

1. Registers a server named `jira-server`
2. Starts `src/mcp_servers/jira_mcp_server.py`
3. Runs it from the workspace root
4. Sets `PYTHONPATH` so imports from `src` work correctly

Once VS Code and GitHub Copilot detect this MCP server, the tool functions exposed by `FastMCP("jira-server")` become available under the Jira MCP namespace.

## Current Jira Tool Behavior

The Jira MCP tools currently return simplified payloads that are easy for Copilot to reason over.

### 1. Issue lookup

`get_jira_issue(issue_key)` returns a normalized dictionary with fields such as:

- `key`
- `summary`
- `status`
- `priority`
- `issuetype`
- `assignee`
- `reporter`
- `created`
- `updated`
- `description`
- `components`
- `labels`
- `fixVersions`

### 2. JQL search

`search_jira_issues(jql, max_results)` returns a list of summarized issues with:

- `key`
- `summary`
- `status`
- `assignee`
- `priority`

### 3. My issues

`get_my_jira_issues(max_results)` is a convenience wrapper over JQL search. It runs:

```text
assignee = currentUser() ORDER BY updated DESC
```

and returns the same summarized issue shape as the general search tool.

### 4. Issue creation

`create_jira_issue(project_key, summary, description, issue_type, priority, components)` creates a Jira issue and returns:

- `key`
- `url`
- `id`

The current MCP tool exposes a focused create flow. It does not currently expose optional client-side fields such as `assignee`, `reporter`, or arbitrary `extra_fields`.

### 5. Comment creation

`add_jira_comment(issue_key, comment)` returns a success flag and message. A `200` or `201` response is treated as success.

### 6. Issue transition

`transition_jira_issue(issue_key, transition_id, comment)` returns a success flag and message. A `200` or `204` response is treated as success.

Important limitation:

- the tool requires the numeric Jira `transition_id`
- the current implementation does not expose a helper tool to list available transitions for an issue

In practice, that means status transitions are supported, but the caller needs to already know the target transition ID.

## How to Add a Jira Prompt Customization

The repository does not currently contain a Jira prompt file, but adding one would improve Copilot tool selection and behavior.

Suggested location:

```text
.github/prompts/jira.prompt.md
```

Minimal example:

```md
---
name: Jira Server Assistant
description: Query and interact with Jira Server issues
tools:
  - jira-server/get_jira_issue
  - jira-server/search_jira_issues
  - jira-server/get_my_jira_issues
  - jira-server/create_jira_issue
  - jira-server/add_jira_comment
  - jira-server/transition_jira_issue
---

You are a Jira Server assistant. Help the user inspect and update Jira issues safely.

Rules:
- Read the issue before changing it.
- Use JQL search when the user gives filters instead of an issue key.
- Summarize create or transition inputs before performing write actions.
- Ask for missing project key, summary, or transition ID before proceeding.
```

Recommended prompt design:

- put the exact MCP tool names in the `tools:` list
- describe the assistant role in one sentence
- describe accepted input formats such as issue keys and JQL
- add guardrails for write actions such as create, comment, and transition
- keep the instructions specific to Jira Server behavior in this repo

## How to Teach GitHub Copilot to Use the Jira Tools Well

GitHub Copilot works best when the repository gives it three layers of guidance.

### 1. Tool availability

Copilot can only call tools that are actually registered through MCP. In this project, that means the server must exist in `.vscode/mcp.json`, and the Python module must expose functions with `@mcp.tool()`.

If a tool is not registered there, Copilot cannot use it.

### 2. Tool allow-list inside a prompt

If you add a Jira prompt file, the `tools:` section should explicitly list Jira operations instead of leaving tool choice fully open.

This reduces tool confusion and makes Copilot more likely to choose the correct Jira action for the user request.

### 3. Clear behavioral instructions

The markdown body in a prompt should teach Copilot how to behave before it acts.

Good Jira instructions usually include:

- when to search first
- when to read issue details first
- what fields to return in a summary
- when to avoid write actions until inputs are confirmed
- what validation to do before transitions or issue creation

For this repo, a good Jira prompt should encourage this flow:

1. Parse the issue key or JQL intent
2. Read the issue first when the user references a specific ticket
3. Search with JQL when the request is filter-based
4. Only then add a comment, create an issue, or transition status

## How to Use the Jira MCP Server in VS Code

Once the workspace is open and Copilot detects the MCP server, Jira tasks can be handled through the registered MCP tools.

Practical usage pattern:

1. Open GitHub Copilot Chat in VS Code
2. Ensure the local Jira MCP server from `.vscode/mcp.json` is available
3. Ask a Jira task, for example:

```text
Get Jira issue UID-287
```

```text
Find open UID issues assigned to me
```

```text
Create a Task in UID with summary "Investigate login timeout" and description "Observed during regression on staging"
```

```text
Add a comment to UID-287 saying the issue is reproduced on the latest build
```

```text
Transition UID-287 using transition ID 31 with comment "Verified and moving to Done"
```

Important behavior:

- MCP registration makes the tools callable
- a Jira prompt file would make tool selection more reliable, but it is not required for the server to work
- transition requests need a valid transition ID because the current toolset does not discover transitions automatically

## Example User Flows

### Issue lookup flow

User asks:

```text
Get Jira issue UID-287
```

Copilot should use:

- `jira-server/get_jira_issue`

### Search flow

User asks:

```text
Find open UID issues assigned to me
```

Copilot should use:

- `jira-server/get_my_jira_issues`

or, when filters are broader:

- `jira-server/search_jira_issues`

### Comment flow

User asks:

```text
Add a comment to UID-287 saying the issue is reproduced on the latest build
```

Copilot should ideally:

1. Read the issue first
2. Then call `jira-server/add_jira_comment`

### Transition flow

User asks:

```text
Move UID-287 to Done using transition ID 31
```

Copilot should ideally:

1. Read the current issue status
2. Verify the transition ID is provided
3. Call `jira-server/transition_jira_issue`

### Create flow

User asks:

```text
Create a UID task for a regression in logout flow
```

Copilot should ideally:

1. Confirm the project key, summary, and description
2. Optionally confirm issue type, priority, and components
3. Call `jira-server/create_jira_issue`

## Quick Start for Contributors

1. Install dependencies from `requirements.txt`
2. Create a root `.env` file with Jira credentials
3. Set `JIRA_BASE_URL` to the Jira Server instance
4. Set either `JIRA_COOKIE` or `JIRA_TOKEN`
5. Ensure `.vscode/mcp.json` points to the correct Python environment if needed
6. Open the workspace in VS Code with GitHub Copilot enabled

## Summary

This repository currently implements a local Jira Server MCP integration for GitHub Copilot.

- The Python MCP server is in `src/mcp_servers/jira_mcp_server.py`
- The Jira REST client is in `src/clients/jira_client.py`
- Shared client construction is in `src/clients/client_factory.py`
- MCP registration is in `.vscode/mcp.json`

The current Jira integration is functional for lookup, search, my issues, creation, commenting, and transitions. The main gaps today are the lack of a Jira-specific prompt file and the lack of a helper tool to discover valid transition IDs.