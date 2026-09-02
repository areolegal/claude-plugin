#!/usr/bin/env python3
"""AreoLegal MCP proxy (stdio).

A thin, dependency-free MCP server bundled with the AreoLegal plugin.
It holds NO legal content. Every content request is forwarded over HTTPS
to the AreoLegal backend, which validates the subscription license on
each call. If the subscription is inactive, tool calls return a renewal
message instead of content.

License key resolution order:
  1. env AREOLEGAL_LICENSE_KEY
  2. ~/.areolegal/license.json  {"license_key": "...", "api_url": "..."}

Backend URL resolution order:
  1. env AREOLEGAL_API_URL
  2. "api_url" in ~/.areolegal/license.json
  3. DEFAULT_API_URL below
"""

import json
import pathlib
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DEFAULT_API_URL = "https://areo.co.il"
PROTOCOL_VERSION = "2024-11-05"
PLUGIN_VERSION = "1.11.1"   # kept in step with plugin.json by release.sh
SERVER_INFO = {"name": "areolegal", "version": "1.0.4"}
TIMEOUT = 60


def config_paths() -> list:
    """License storage candidates, most-preferred first.

    CLAUDE_PLUGIN_DATA (persistent per-plugin dir, survives updates and is the
    durable location inside Cowork's managed VM) wins when available; the
    home-directory path covers Claude Code CLI / Desktop Code tab on the host.
    """
    paths = []
    data_dir = os.environ.get("CLAUDE_PLUGIN_DATA")
    if data_dir:
        paths.append(Path(data_dir) / "license.json")
    paths.append(Path.home() / ".areolegal" / "license.json")
    return paths

TOOLS = [
    {
        "name": "license_status",
        "description": (
            "Check the AreoLegal subscription status for this machine. "
            "Call this first when any AreoLegal skill starts, and whenever another "
            "AreoLegal tool reports a license problem."
        ),
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "activate",
        "description": (
            "Activate AreoLegal on this machine by saving the customer's license key "
            "locally and validating it against the AreoLegal service. "
            "Use during setup/onboarding when the user provides their license key."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "license_key": {"type": "string", "description": "License key from areolegal purchase"}
            },
            "required": ["license_key"],
            "additionalProperties": False,
        },
    },
    {
        "name": "list_resources",
        "description": (
            "List the professional reference resources available for an AreoLegal skill. "
            "skill is one of: contract-playbook-builder, contract-negotiation-orchestrator, "
            "contract-setup-diagnostician. Requires an active subscription."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"skill": {"type": "string"}},
            "required": ["skill"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_resource",
        "description": (
            "Fetch one AreoLegal professional reference resource (methodology, taxonomy, "
            "legal anchors, templates, schemas) by skill and resource name, e.g. "
            "get_resource(skill='contract-negotiation-orchestrator', name='policy_taxonomy.md'). "
            "Requires an active subscription. The content is licensed to the subscriber only."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "skill": {"type": "string"},
                "name": {"type": "string"},
            },
            "required": ["skill", "name"],
            "additionalProperties": False,
        },
    },
    {
        "name": "save_resource",
        "description": (
            "Download one AreoLegal resource straight to a file on this machine and return "
            "only the path and size -- the file's content is NEVER returned into the "
            "conversation. ALWAYS use this instead of get_resource for deliverable HTML "
            "templates and any other large file that is passed to a build script rather than "
            "read: it avoids carrying tens of thousands of tokens of markup through the "
            "conversation and re-writing them by hand. Use get_resource only for methodology "
            "text you actually need to read. Requires an active subscription."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "skill": {"type": "string"},
                "name": {"type": "string"},
                "path": {
                    "type": "string",
                    "description": "Where to write the file, relative to the working directory.",
                },
            },
            "required": ["skill", "name", "path"],
            "additionalProperties": False,
        },
    },
]


def read_config() -> dict:
    for path in config_paths():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
    return {}


def license_key() -> str:
    return os.environ.get("AREOLEGAL_LICENSE_KEY") or read_config().get("license_key", "")


def api_url() -> str:
    url = os.environ.get("AREOLEGAL_API_URL") or read_config().get("api_url") or DEFAULT_API_URL
    return url.rstrip("/")


def device_id() -> str:
    """Stable anonymous per-machine id; persisted so hostname changes don't churn it."""
    cfg = read_config()
    if cfg.get("device_id"):
        return cfg["device_id"]
    import getpass
    import hashlib
    import platform

    raw = f"{platform.node()}|{getpass.getuser()}|{Path.home()}"
    did = hashlib.sha256(raw.encode()).hexdigest()[:16]
    cfg["device_id"] = did
    for path in config_paths():
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
            break
        except OSError:
            continue
    return did


def http_get(path: str, key: str) -> tuple[int, dict]:
    req = urllib.request.Request(
        api_url() + path,
        headers={
            "Authorization": "Bearer " + key,
            "User-Agent": f"areolegal-mcp/{PLUGIN_VERSION}",
            "X-Areo-Device": device_id(),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode("utf-8"))
        except ValueError:
            body = {}
        return e.code, body
    except (urllib.error.URLError, OSError) as e:
        return 0, {"error": str(e)}


NO_KEY_MSG = (
    "לא נמצא רישיון AreoLegal במחשב הזה. "
    "אם יש למשתמש מפתח רישיון, הפעל את הכלי activate עם המפתח. "
    "אם אין, הפנה אותו לרכישת מנוי באתר AreoLegal.\n"
    "(No AreoLegal license key found on this machine. If the user has a key, call the "
    "'activate' tool with it; otherwise direct them to purchase a subscription.)"
)

CONN_ERR_MSG = (
    "שירות AreoLegal אינו זמין כרגע (בעיית תקשורת). נסה שוב בעוד רגע. "
    "אם הבעיה נמשכת, בדוק חיבור לאינטרנט או פנה לתמיכה.\n(Connection error: {err})"
)


def denial_text(status: int, body: dict) -> str:
    msg = body.get("message") or body.get("detail") or ""
    if status in (401, 403):
        return (
            "המנוי ל-AreoLegal אינו פעיל או שהמפתח שגוי. "
            "יש לחדש את המנוי באתר AreoLegal ואז לנסות שוב. "
            + (f"\nפרטים: {msg}" if msg else "")
            + "\n(Subscription inactive or invalid key — the user must renew before this "
            "skill can continue. Do not attempt to proceed without the licensed content.)"
        )
    if status == 404:
        return f"Resource not found. פרטים: {msg or 'not found'}"
    return f"AreoLegal service error (HTTP {status}). {msg}"


def call_tool(name: str, args: dict) -> str:
    if name == "activate":
        key = (args.get("license_key") or "").strip()
        if not key:
            return "לא סופק מפתח רישיון. (No license key provided.)"
        status, body = http_get("/v1/license/status", key)
        if status == 0:
            return CONN_ERR_MSG.format(err=body.get("error", "unknown"))
        if status != 200 or body.get("status") not in ("active", "trialing"):
            return denial_text(status if status != 200 else 403, body)
        cfg = read_config()
        cfg["license_key"] = key
        saved = False
        for path in config_paths():
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                path.chmod(0o600)
                saved = True
            except OSError:
                continue
        if not saved:
            return "שגיאה בשמירת הרישיון מקומית. (Failed to persist the license locally.)"
        return (
            "הרישיון הופעל בהצלחה במחשב הזה. סטטוס מנוי: "
            + json.dumps(body, ensure_ascii=False)
        )

    key = license_key()
    if not key:
        return NO_KEY_MSG

    if name == "license_status":
        path = "/v1/license/status"
    elif name == "list_resources":
        path = f"/v1/resources/{urllib.parse.quote(str(args.get('skill', '')))}"
    elif name in ("get_resource", "save_resource"):
        skill = urllib.parse.quote(str(args.get("skill", "")))
        res = urllib.parse.quote(str(args.get("name", "")))
        path = f"/v1/resources/{skill}/{res}"
    else:
        return f"Unknown tool: {name}"

    status, body = http_get(path, key)
    if status == 0:
        return CONN_ERR_MSG.format(err=body.get("error", "unknown"))
    if status != 200:
        return denial_text(status, body)
    if name == "get_resource":
        return body.get("content", "")
    if name == "save_resource":
        return save_to_disk(body.get("content", ""), str(args.get("path", "")))
    return json.dumps(body, ensure_ascii=False, indent=2)


def save_to_disk(content: str, dest: str) -> str:
    """Write a fetched resource to a local file and report only path and size.

    A deliverable template is ~114 KB of markup. Returning it as tool output puts
    it in the conversation and then requires it to be written back out verbatim to
    create the file -- roughly 33k tokens each way, and the write is serial, so it
    dominates the wall-clock time of a build. Writing it here costs nothing.
    """
    if not dest:
        return "Error: path is required."
    target = pathlib.Path(dest).expanduser()
    if target.is_absolute() or ".." in target.parts:
        return ("Error: path must be relative to the working directory and may not "
                "contain '..'. Received: %s" % dest)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    except OSError as exc:
        return "Error: could not write %s (%s)" % (dest, exc)
    return json.dumps({"path": str(target), "bytes": len(content.encode("utf-8")),
                       "note": "Saved. Pass this path to the build script; do not read the file."},
                      ensure_ascii=False)


def handle(msg: dict):
    method = msg.get("method")
    msg_id = msg.get("id")
    if method == "initialize":
        client_ver = (msg.get("params") or {}).get("protocolVersion") or PROTOCOL_VERSION
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": client_ver,
                "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO,
            },
        }
    if method == "notifications/initialized":
        return None
    if method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = msg.get("params") or {}
        text = call_tool(params.get("name", ""), params.get("arguments") or {})
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {"content": [{"type": "text", "text": text}]},
        }
    if msg_id is not None:
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }
    return None


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        try:
            reply = handle(msg)
        except Exception as e:  # never crash the transport
            reply = None
            if msg.get("id") is not None:
                reply = {
                    "jsonrpc": "2.0",
                    "id": msg.get("id"),
                    "error": {"code": -32603, "message": f"Internal error: {e}"},
                }
        if reply is not None:
            sys.stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
