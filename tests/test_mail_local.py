"""open_mail_draft: opens a ready Outlook message on this computer, and never touches the network.

Neil, 04.11.2026: client emails and contract files must never pass through the Areo service.
These tests hold the local tool to that: no HTTP, values passed to Outlook as data only, and the
file written to a private temporary folder under the name the page asked for.
"""
import base64
import json
import sys
from pathlib import Path

MCP = Path(__file__).resolve().parents[1] / "areolegal" / "mcp"
sys.path.insert(0, str(MCP))

import mail_local  # noqa: E402
import areolegal_mcp  # noqa: E402


class Run:
    def __init__(self, code=0):
        self.calls, self.code = [], code

    def __call__(self, cmd, **kw):
        self.calls.append(cmd)
        return type("R", (), {"returncode": self.code, "stderr": "boom" if self.code else ""})()


DOCX = base64.b64encode(b"PK\x03\x04 test docx bytes").decode()


def test_mac_opens_outlook_with_the_file_and_passes_values_as_data(monkeypatch):
    monkeypatch.setattr(mail_local.Path, "exists", lambda self: True)
    run = Run()
    out = json.loads(mail_local.open_mail_draft(
        {"to": ["legal@maarachot.co.il"], "subject": 'הסכם "שירותים" end tell', "body_html": "<p>שלום</p>",
         "file_name": 'הסכם שירותים - מערכות בע״מ - סבב 1.docx', "file_base64": DOCX},
        runner=run, platform="darwin"))
    assert out == {"opened": True, "app": "Outlook", "attached": True}
    cmd = run.calls[0]
    assert cmd[0] == "osascript" and cmd[1] == "-e"
    script = cmd[2]
    # the subject and body never enter the script text, only argv
    assert 'end tell' not in script.split("on run argv")[0] and "שלום" not in script and "שירותים" not in script
    subject, html, path, to = cmd[3], cmd[4], cmd[5], cmd[6:]
    assert subject == 'הסכם "שירותים" end tell' and html == "<p>שלום</p>" and to == ["legal@maarachot.co.il"]
    f = Path(path)
    assert f.name == "הסכם שירותים - מערכות בע״מ - סבב 1.docx" and f.read_bytes() == base64.b64decode(DOCX)
    assert oct(f.parent.stat().st_mode)[-3:] == "700"


def test_windows_uses_classic_outlook_with_a_data_file():
    run = Run()
    out = json.loads(mail_local.open_mail_draft({"to": ["a@b.co"], "subject": "s", "file_base64": DOCX},
                                                runner=run, platform="win32"))
    assert out["opened"] is True
    cmd = run.calls[0]
    assert cmd[0] == "powershell" and cmd[-1].endswith("spec.json")
    spec = json.loads(Path(cmd[-1]).read_text(encoding="utf-8"))
    assert spec["to"] == ["a@b.co"] and spec["subject"] == "s" and spec["file"].endswith(".docx")


def test_refuses_bad_input_without_running_anything():
    run = Run()
    assert json.loads(mail_local.open_mail_draft({"to": ["not an address"]}, runner=run, platform="darwin")) == \
        {"opened": False, "reason": "bad_recipient"}
    assert json.loads(mail_local.open_mail_draft({"to": ["a@b.co"], "file_base64": "%%%"}, runner=run,
                                                 platform="darwin"))["reason"] == "bad_file"
    assert json.loads(mail_local.open_mail_draft({"to": ["a@b.co"]}, runner=run, platform="linux"))["reason"] == \
        "unsupported_system"
    assert run.calls == []


def test_outlook_refusal_is_reported(monkeypatch):
    monkeypatch.setattr(mail_local.Path, "exists", lambda self: True)
    out = json.loads(mail_local.open_mail_draft({"to": ["a@b.co"]}, runner=Run(code=1), platform="darwin"))
    assert out["opened"] is False and out["reason"] == "outlook_refused"


def test_the_tool_is_listed_and_never_calls_the_areo_service(monkeypatch):
    assert any(t["name"] == "open_mail_draft" for t in areolegal_mcp.TOOLS)

    def no_network(*a, **k):
        raise AssertionError("open_mail_draft must not call the Areo service")
    monkeypatch.setattr(areolegal_mcp, "http_get", no_network)
    monkeypatch.setattr(areolegal_mcp, "http_post", no_network)
    called = {}
    monkeypatch.setattr(mail_local, "open_mail_draft", lambda args: called.setdefault("args", args) and "{}")
    areolegal_mcp.call_tool("open_mail_draft", {"to": ["a@b.co"]})
    assert called["args"] == {"to": ["a@b.co"]}
    src = (MCP / "mail_local.py").read_text(encoding="utf-8")
    assert "urllib" not in src and "http" not in src.split('"""', 2)[2]
