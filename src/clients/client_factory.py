import os
import sys

from clients.bugzilla_client import BugzillaClient
from clients.confluence_client import ConfluenceClient
from clients.jira_client import JiraClient

# Ensure the `utils` directory is in the PATH.
_src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

_client_cache = {}
_env_loaded = False
_env_keys = set()  # Record keys defined in the .env file (even if the value is empty)

def _load_env_file():
    """Load environment variables from the .env file"""
    global _env_loaded
    if _env_loaded:
        return
    
    # Look for the .env file (in the src directory)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(current_dir, "..", "..", ".env")
    
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                # Parse KEY=VALUE
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    # Record this key as defined in the .env file
                    _env_keys.add(key)
                    # Set the environment variable (even if the value is empty)
                    if not os.environ.get(key):
                        os.environ[key] = value
    
    _env_loaded = True

def _get_env_or_input(key: str, prompt: str) -> str:
    """Retrieve environment variables; if defined in the `.env` file (even if empty), do not prompt for input."""
    value = os.environ.get(key, "")
    # If the key is defined in the .env file, return its value (which may be empty)
    if key in _env_keys:
        return value
    # Otherwise, if the value is empty, prompt for input
    if not value:
        return input(prompt)
    return value

def get_client(system_name: str):

    _load_env_file()
    
    if system_name in _client_cache:
        return _client_cache[system_name]

    
    if system_name == "bugzilla":        
        base_url = _get_env_or_input("BUGZILLA_BASE_URL", "Enter Bugzilla base URL: ")        
        cookie = _get_env_or_input("BUGZILLA_COOKIE", "Enter Bugzilla cookie: ")        
        api_key = _get_env_or_input("BUGZILLA_API_KEY", "Enter Bugzilla API key (press Enter to skip): ").strip()
        
        client = BugzillaClient(base_url, cookie, api_key if api_key else None)    
    elif system_name == "jira-server":
        base_url = _get_env_or_input("JIRA_BASE_URL", "Enter Jira base URL: ")
        cookie = _get_env_or_input("JIRA_COOKIE", "Enter Jira cookie: ")
        client = JiraClient(base_url, cookie)        
    elif system_name == "confluence-server":
        base_url = _get_env_or_input("CONFLUENCE_BASE_URL", "Enter Confluence base URL: ")
        cookie = _get_env_or_input("CONFLUENCE_COOKIE", "Enter Confluence cookie: ")
        client = ConfluenceClient(base_url, cookie)
    else:
        raise ValueError(f"Unknown system: {system_name}")

    _client_cache[system_name] = client
    return client
