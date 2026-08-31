# GitHub Copilot QA Assistant - Bugzilla operations

This project exposes Bugzilla operations to GitHub Copilot through an MCP server. The current implementation lets Copilot read Bugzilla bugs, search bugs, read comments, add comments, update bugs, and create new bugs by calling Python code in this repository.

The repository already contains two important customization points:

- [.vscode/mcp.json](.vscode/mcp.json) registers the local MCP server so Copilot can discover its tools.
- [.github/prompts/bugzilla.prompt.md](.github/prompts/bugzilla.prompt.md) defines a reusable prompt that tells Copilot when and how to use those tools.

## Current Implementation

### 1. MCP server layer

The main MCP entry point is [src/mcp_servers/bugzilla_mcp_server.py](src/mcp_servers/bugzilla_mcp_server.py).

It creates a FastMCP server named `bugzilla` and exposes these tools with `@mcp.tool()`:

- `bugzilla_get_bug`
- `bugzilla_search_bugs`
- `bugzilla_get_comments`
- `bugzilla_add_comment`
- `bugzilla_update_bug`
- `bugzilla_create_bug`

These tools are the functions GitHub Copilot can call after the MCP server is registered.

### 2. Bugzilla client layer

The Bugzilla integration logic lives in [src/clients/bugzilla_client.py](src/clients/bugzilla_client.py).

This client uses a hybrid approach because the target Bugzilla environment does not fully support every API operation in the same way:

- Read bug details through `show_bug.cgi?ctype=xml`
- Search bugs through `buglist.cgi` with CSV output
- Try write operations through JSON-RPC first
- Fall back to CGI form submission when JSON-RPC is not allowed

Implemented client methods include:

- `get_bug`
- `get_bugs`
- `get_comments`
- `search_bugs`
- `add_comment`
- `update_bug`
- `create_bug`
- `get_history`
- `get_version`

### 3. Client factory and environment loading

[src/clients/client_factory.py](src/clients/client_factory.py) is responsible for:

- loading values from the root `.env` file
- caching instantiated clients
- constructing the `BugzillaClient`

The current Bugzilla configuration keys are:

- `BUGZILLA_BASE_URL`
- `BUGZILLA_COOKIE`
- `BUGZILLA_API_KEY`

If a key is not defined in `.env`, the factory can prompt for it at runtime. If a key exists in `.env` with an empty value, it is treated as intentionally defined and will not prompt.

### 4. Python dependencies

Current dependencies from [requirements.txt](requirements.txt):

- `requests`
- `urllib3`
- `fastmcp`
- `python-dotenv`
- `beautifulsoup4`

## How the Current MCP Integration Works

The registration file is [.vscode/mcp.json](.vscode/mcp.json).

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
    }
  }
}
```

This does four things:

1. Registers a server named `bugzilla`
2. Starts the Python file [src/mcp_servers/bugzilla_mcp_server.py](src/mcp_servers/bugzilla_mcp_server.py)
3. Runs it from the workspace root
4. Sets `PYTHONPATH` so imports from `src` work correctly

Once VS Code and GitHub Copilot detect this MCP server, the tools exposed by `FastMCP("bugzilla")` become available under the `bugzilla/...` namespace.

## How the Current Prompt Customization Works

The reusable prompt file is [.github/prompts/bugzilla.prompt.md](.github/prompts/bugzilla.prompt.md).

Its frontmatter currently looks like this:

```md
---
name: Bugzilla Assistant
description: Query and interact with Bugzilla bugs
tools:
  - bugzilla/bugzilla_get_bug
  - bugzilla/bugzilla_search_bugs
  - bugzilla/bugzilla_get_comments
  - bugzilla/bugzilla_add_comment
  - bugzilla/bugzilla_update_bug  

---
```

This frontmatter matters because it narrows which tools Copilot should use for that prompt. The body of the file then teaches Copilot:

- what role it should play
- which bug operations it should perform
- what input formats it should accept
- what guardrails it should follow before updating Bugzilla

In practice, this means the prompt is doing two jobs:

1. Tool selection control
2. Behavioral instruction

One current limitation is important: the prompt does not list `bugzilla/bugzilla_create_bug`, even though the MCP server implements `bugzilla_create_bug`. That means Copilot is less likely to use bug creation when this prompt is the active guide. If you want prompt-driven bug creation, add that tool name to the frontmatter.

## How to Extend the MCP Pattern

If you want to extend this project later, follow the same structure already used for Bugzilla.

### Step 1. Create a new client module

Add a client module under [src/clients](src/clients) for the new workflow or external system.

Example:

```text
src/clients/another_system_client.py
```

That client should keep the integration details local to one place, similar to [src/clients/bugzilla_client.py](src/clients/bugzilla_client.py).

### Step 2. Register the client in the factory

Update [src/clients/client_factory.py](src/clients/client_factory.py) so `get_client()` can build the new client.

Pattern:

```python
if system_name == "another_system":
  base_url = _get_env_or_input("ANOTHER_SYSTEM_BASE_URL", "Enter system base URL: ")
  token = _get_env_or_input("ANOTHER_SYSTEM_TOKEN", "Enter system token: ")
  client = AnotherSystemClient(base_url, token)
```

This keeps all runtime configuration in one place.

### Step 3. Create a new MCP server module

Add a new file under [src/mcp_servers](src/mcp_servers).

Example:

```text
src/mcp_servers/another_system_mcp_server.py
```

Minimal pattern:

```python
from mcp.server.fastmcp import FastMCP
from clients.client_factory import get_client

mcp = FastMCP("another_system")

@mcp.tool()
def another_system_get_item(item_id: str) -> dict:
  client = get_client("another_system")
  return client.get_item(item_id)

if __name__ == "__main__":
  mcp.run()
```

Recommendations:

- Keep each tool small and focused
- Return plain dictionaries or lists that Copilot can reason over easily
- Normalize output fields to a consistent shape
- Hide protocol details inside the client layer, not inside the MCP tool function

### Step 4. Register the new server in `.vscode/mcp.json`

Extend [.vscode/mcp.json](.vscode/mcp.json) like this:

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
    "another_system": {
      "command": "python",
      "args": ["src/mcp_servers/another_system_mcp_server.py"],
      "cwd": "${workspaceFolder}",
      "env": {
        "PYTHONPATH": "${workspaceFolder}/src"
      }
    }
  }
}
```

### Step 5. Add environment variables

Add any new configuration values to the root `.env` file.

Example:

```env
ANOTHER_SYSTEM_BASE_URL=https://your-system-instance
ANOTHER_SYSTEM_TOKEN=
```

## How to Add Another Custom Prompt

Prompt files should live under [.github/prompts](.github/prompts).

Example new prompt:

```text
.github/prompts/bugzilla-create-bug.prompt.md
```

Minimal pattern:

```md
---
name: Bugzilla Create Bug Assistant
description: Create new Bugzilla bugs with the required fields
tools:
  - bugzilla/bugzilla_create_bug
  - bugzilla/bugzilla_get_bug
---

You are a Bugzilla assistant. Help the user create Bugzilla bugs safely.

Rules:
- Confirm the product, component, and summary before creating the bug.
- Ask for missing required fields.
- Summarize the bug payload before making the write action.
```

Recommended prompt design:

- Put the exact MCP tool names in the `tools:` list
- Describe the assistant role in one sentence
- Describe accepted input formats
- Add guardrails for risky write actions
- Keep the instructions concrete and specific to the system

## How to Teach GitHub Copilot to Use Your MCP Tools Well

GitHub Copilot works best when the repository gives it three layers of guidance:

### 1. Tool availability

Copilot can only call tools that are actually registered through MCP. In this project, that means the server must exist in [.vscode/mcp.json](.vscode/mcp.json), and the Python module must expose functions with `@mcp.tool()`.

If a tool is not registered here, Copilot cannot use it.

### 2. Tool allow-list inside the prompt

The `tools:` section in a prompt file tells Copilot which tools belong to that task. This reduces tool confusion and improves tool choice.

For example, [.github/prompts/bugzilla.prompt.md](.github/prompts/bugzilla.prompt.md) explicitly lists Bugzilla operations instead of leaving tool selection fully open.

### 3. Clear behavioral instructions

The markdown body in the prompt should teach Copilot how to think before it acts.

Good instructions usually include:

- when to search first
- when to read details first
- what data to return to the user
- when to avoid write actions
- what validation to do before updates

For this repo, a good Bugzilla prompt should encourage this flow:

1. Parse the bug ID or URL
2. Read the current bug first
3. Read comments if context is needed
4. Only then add a comment or update status

## How to Use the Prompt in VS Code

Once the workspace is open and Copilot detects the MCP server, use the Bugzilla prompt as the task guide for chat requests about Bugzilla.

Practical usage pattern:

1. Open GitHub Copilot Chat in VS Code
2. Start from the Bugzilla prompt file in [.github/prompts/bugzilla.prompt.md](.github/prompts/bugzilla.prompt.md), or otherwise use that prompt content as the instruction context for the chat
3. Ask a task that matches the allowed tools, for example:

```text
Get bug 1241587 and summarize the latest comments
```

```text
Find open bugs in HomeShield assigned to qa@example.com
```

```text
Add a comment to bug 1241587 saying the issue is reproduced on v1.7.44
```

Important behavior:

- If the active prompt lists a tool, Copilot is guided to use it
- If the active prompt omits a tool, Copilot may avoid it even if the MCP server exposes it
- If the MCP server is not registered, the prompt alone is not enough because Copilot still needs a callable tool implementation

If you want Copilot to create bugs from the Bugzilla prompt, update the prompt frontmatter to include:

```md
- bugzilla/bugzilla_create_bug
```

## Recommended Pattern for This Repository

If you keep extending this project, the cleanest structure is:

- one client per external system
- one MCP server per system or workflow area
- one prompt per user task or assistant role
- one small set of tools per prompt

For example:

```text
src/
  clients/
    bugzilla_client.py
    another_system_client.py
  mcp_servers/
    bugzilla_mcp_server.py
    another_system_mcp_server.py
.github/
  prompts/
    bugzilla.prompt.md
    bugzilla-create-bug.prompt.md
.vscode/
  mcp.json
```

## Example User Flows

### Bug lookup flow

User asks:

```text
Get Bugzilla bug 1241587
```

Copilot should use:

- `bugzilla/bugzilla_get_bug`

### Search flow

User asks:

```text
Find open HomeShield bugs assigned to qa@example.com
```

Copilot should use:

- `bugzilla/bugzilla_search_bugs`

### Comment flow

User asks:

```text
Add a comment to bug 1241587 saying the issue is reproduced on v1.7.44
```

Copilot should ideally:

1. Read the bug first
2. Optionally inspect comments
3. Call `bugzilla/bugzilla_add_comment`

### Status update flow

User asks:

```text
Resolve bug 1241587 as FIXED
```

Copilot should ideally:

1. Read the current bug status
2. Verify the transition is sensible
3. Call `bugzilla/bugzilla_update_bug`

## Quick Start for Contributors

1. Install dependencies from [requirements.txt](requirements.txt)
2. Create a root `.env` file with Bugzilla credentials
3. Ensure [ .vscode/mcp.json ](.vscode/mcp.json) points to the correct Python environment if needed
4. Open the workspace in VS Code with GitHub Copilot enabled
5. Use the Bugzilla prompt file to guide Copilot toward the Bugzilla tool set

## Summary

This repository currently implements a local Bugzilla MCP integration for GitHub Copilot.

- The Python MCP server is in [src/mcp_servers/bugzilla_mcp_server.py](src/mcp_servers/bugzilla_mcp_server.py)
- The Bugzilla API and CGI handling is in [src/clients/bugzilla_client.py](src/clients/bugzilla_client.py)
- MCP registration is in [.vscode/mcp.json](.vscode/mcp.json)
- Copilot task guidance is in [.github/prompts/bugzilla.prompt.md](.github/prompts/bugzilla.prompt.md)

If you want Copilot to use custom tools reliably, keep the pattern strict: register the MCP server, expose small tool functions, list those tools in a prompt file, and write instructions that make the intended tool flow explicit.