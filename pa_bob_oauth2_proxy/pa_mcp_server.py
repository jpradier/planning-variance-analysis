"""
Minimal local MCP bridge: Claude Desktop <-> IBM Planning Analytics (PA)
 
Works with both kinds of PA deployment:
  - PA on Cloud, no tenant ID (e.g. citibranch.planning-analytics.cloud.ibm.com):
    leave PA_TENANT_ID unset.
  - PA as a Service, tenant based (e.g. us-east-1.planninganalytics.saas.ibm.com):
    set PA_TENANT_ID to the tenant ID shown in the PA Workspace URL.
 
Architecture:
  Claude Desktop --stdio (local, trusted)--> this script --HTTPS + OAuth--> PA Agent MCP endpoint
 
Setup:
  1. In PA Workspace: Administration -> Integrations -> Add client
     - Redirect URL: http://localhost:8765/callback   (must match PA_REDIRECT_URI below exactly)
     - Copy the generated Client ID and Client Secret. You will paste them directly
       into claude_desktop_config.json (no .env file is used by this script).
  2. pip install -r requirements.txt
  3. Add this script to claude_desktop_config.json, with PA_HOST, PA_CLIENT_ID, and
     PA_CLIENT_SECRET set in its "env" block. Also set PA_TENANT_ID there if your
     instance uses one (see the setup guide for the exact format).
  4. Restart Claude Desktop. The first tool call will pop your browser for PA login.
     After that, tokens are cached and refreshed automatically until the refresh
     token itself expires, at which point it will pop the browser again.
 
This script:
  - Runs a tiny local HTTP server on the callback port, just to catch PA's OAuth
    redirect (the ?code=... query param).
  - Exchanges that code for an access_token + refresh_token at PA's /oauth2/token.
  - Caches tokens on disk (token_cache.json) and refreshes automatically.
  - Proxies IBM's prebuilt "PA Agent" remote MCP tools (list_pa_agent_tools /
    call_pa_agent_tool) by connecting to it as a client with that token.
    Requires the PA Agent feature entitlement on this PA instance.
"""
 
import os
import json
import time
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs, urlencode
 
import requests
from mcp.server.fastmcp import FastMCP
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
 
PA_HOST = os.environ["PA_HOST"]  # e.g. mycompany.planning-analytics.cloud.ibm.com (no https://, no trailing slash)
PA_TENANT_ID = os.environ.get("PA_TENANT_ID", "").strip()  # leave unset for a no-tenant PA on Cloud instance
CLIENT_ID = os.environ["PA_CLIENT_ID"]
CLIENT_SECRET = os.environ["PA_CLIENT_SECRET"]
REDIRECT_URI = os.environ.get("PA_REDIRECT_URI", "http://localhost:8765/callback")
TOKEN_CACHE_PATH = os.path.join(os.path.dirname(__file__), "token_cache.json")
 
AUTH_URL = f"https://{PA_HOST}/oauth2/authorize"
TOKEN_URL = f"https://{PA_HOST}/oauth2/token"
 
# IBM's prebuilt "PA Agent" remote MCP endpoint (requires PA Agent feature entitlement).
# Tenant-based PAaaS instances need the tenant ID in the path; no-tenant PA on Cloud
# instances omit it. PA_TENANT_ID being empty or unset covers the no-tenant case.
_tenant_segment = f"{PA_TENANT_ID}/" if PA_TENANT_ID else ""
PA_AGENT_MCP_URL = os.environ.get(
    "PA_AGENT_MCP_URL",
    f"https://{PA_HOST}/api/{_tenant_segment}v0/agentic-ai/ibm-pa-tools/mcp",
)
 
_callback_result = {}
 
 
class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != urlparse(REDIRECT_URI).path:
            self.send_response(404)
            self.end_headers()
            return
        params = parse_qs(parsed.query)
        _callback_result["code"] = params.get("code", [None])[0]
        _callback_result["error"] = params.get("error", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        msg = "Login successful, you can close this tab." if _callback_result.get("code") else "Login failed."
        self.wfile.write(f"<html><body><h3>{msg}</h3></body></html>".encode())
 
    def log_message(self, *args):
        pass  # silence default request logging, it pollutes Claude Desktop's MCP log
 
 
class _CallbackHTTPServer(HTTPServer):
    allow_reuse_address = True  # avoid "Address already in use" if a prior socket is in TIME_WAIT
 
 
def _run_local_callback_server(port: int):
    server = _CallbackHTTPServer(("localhost", port), _CallbackHandler)
    server.handle_request()  # handle exactly one request, then stop
 
 
def _load_cached_token():
    if os.path.exists(TOKEN_CACHE_PATH):
        with open(TOKEN_CACHE_PATH) as f:
            return json.load(f)
    return None
 
 
def _save_token(token: dict):
    token["obtained_at"] = time.time()
    with open(TOKEN_CACHE_PATH, "w") as f:
        json.dump(token, f)
 
 
def _token_expired(token: dict) -> bool:
    expires_in = float(token.get("expires_in", 3600))  # PA's token endpoint may return this as a string
    obtained_at = float(token.get("obtained_at", 0))
    return time.time() > obtained_at + expires_in - 60  # refresh 60s early
 
 
def _refresh_token(token: dict) -> dict:
    resp = requests.post(TOKEN_URL, data={
        "grant_type": "refresh_token",
        "refresh_token": token["refresh_token"],
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    })
    resp.raise_for_status()
    new_token = resp.json()
    _save_token(new_token)
    return new_token
 
 
def _interactive_login() -> dict:
    port = int(urlparse(REDIRECT_URI).port or 8765)
    server_thread = threading.Thread(target=_run_local_callback_server, args=(port,), daemon=True)
    server_thread.start()
 
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": "v0userContext",
    }
    webbrowser.open(f"{AUTH_URL}?{urlencode(params)}")
 
    server_thread.join(timeout=180)  # wait up to 3 min for the user to log in
    if not _callback_result.get("code"):
        raise RuntimeError(f"PA login failed or timed out: {_callback_result.get('error')}")
 
    resp = requests.post(TOKEN_URL, data={
        "grant_type": "authorization_code",
        "code": _callback_result["code"],
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    })
    resp.raise_for_status()
    token = resp.json()
    _save_token(token)
    return token
 
 
def get_access_token() -> str:
    token = _load_cached_token()
    if token and not _token_expired(token):
        return token["access_token"]
    if token and token.get("refresh_token"):
        try:
            token = _refresh_token(token)
            return token["access_token"]
        except requests.HTTPError:
            pass  # refresh failed (likely expired) -- fall through to full login
    token = _interactive_login()
    return token["access_token"]
 
 
# ---- Proxy to IBM's prebuilt "PA Agent" remote MCP tools ----
 
def _unwrap_exception(exc: BaseException) -> str:
    """TaskGroup/ExceptionGroup wrappers hide the real cause. Recursively pull out
    the leaf exception message(s) so tool errors are actually diagnosable."""
    if hasattr(exc, "exceptions"):  # BaseExceptionGroup (py3.11+) / anyio's ExceptionGroup
        return " | ".join(_unwrap_exception(e) for e in exc.exceptions)
    return f"{type(exc).__name__}: {exc}"
 
 
async def _call_remote_pa_agent(fn):
    """Open a session against IBM's PA Agent MCP endpoint using our OAuth bearer
    token, run `fn(session)`, and clean up. `fn` is an async callable."""
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    try:
        async with streamablehttp_client(PA_AGENT_MCP_URL, headers=headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await fn(session)
    except BaseException as exc:
        raise RuntimeError(
            f"PA Agent MCP call failed at {PA_AGENT_MCP_URL}: {_unwrap_exception(exc)}"
        ) from exc
 
 
mcp = FastMCP("planning-analytics-bridge")
 
 
@mcp.tool()
async def list_pa_agent_tools() -> list:
    """List the prebuilt tools available from IBM's PA Agent remote MCP server
    (natural-language cube exploration, sandbox/view management, impact analysis,
    outlier detection, TI process monitoring, etc). Call this first to see what's
    available before using call_pa_agent_tool."""
    async def _list(session):
        result = await session.list_tools()
        return [{"name": t.name, "description": t.description} for t in result.tools]
    return await _call_remote_pa_agent(_list)
 
 
@mcp.tool()
async def call_pa_agent_tool(tool_name: str, arguments: dict = None) -> dict:
    """Call a specific tool on IBM's PA Agent remote MCP server by name, with a
    dict of arguments matching what list_pa_agent_tools() describes for it."""
    async def _call(session):
        result = await session.call_tool(tool_name, arguments or {})
        return {
            "content": [getattr(block, "text", str(block)) for block in result.content],
            "isError": result.isError,
        }
    return await _call_remote_pa_agent(_call)
 
 
if __name__ == "__main__":
    mcp.run(transport="stdio")
