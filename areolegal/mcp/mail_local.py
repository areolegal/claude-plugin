"""Open a ready email in the mail app on this computer: recipients, subject, text and the file attached.

Everything happens on the lawyer's machine. Nothing here touches the network and nothing is sent
to the Areo service: the file is written to a private temporary folder, and Outlook is asked to
open a new message with it. The lawyer reviews it and presses Send in Outlook.

macOS: Microsoft Outlook through AppleScript (works in the new Outlook for Mac too, checked
04.11.2026). Windows: the classic Outlook through COM. Anything else answers opened=false with a
reason, and the page falls back to copying the text.
"""
import base64
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

MAX_BYTES = 20 * 1024 * 1024
EMAIL_RE = re.compile(r"^[^@\s<>\"']+@[^@\s<>\"']+\.[^@\s<>\"']+$")

# Values reach AppleScript only as argv items, never inside the script text, so no subject or
# body can change what the script does.
_APPLESCRIPT = r'''
on run argv
  set subj to item 1 of argv
  set html to item 2 of argv
  set fpath to item 3 of argv
  tell application "Microsoft Outlook"
    set m to make new outgoing message with properties {subject:subj, content:html}
    repeat with i from 4 to count of argv
      make new recipient at m with properties {email address:{address:(item i of argv)}}
    end repeat
    if fpath is not "" then make new attachment at m with properties {file:POSIX file fpath}
    open m
    activate
  end tell
end run
'''

# Windows: the values come from a JSON file, read as data by the script.
_POWERSHELL = r'''
$s = Get-Content -Raw -Encoding UTF8 $args[0] | ConvertFrom-Json
$o = New-Object -ComObject Outlook.Application
$m = $o.CreateItem(0)
$m.To = ($s.to -join ';')
$m.Subject = $s.subject
$m.HTMLBody = $s.html
if ($s.file) { [void]$m.Attachments.Add($s.file) }
$m.Display()
'''


def _safe_name(name: str) -> str:
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "", (name or "").strip()) or "מסמך.docx"
    if not name.lower().endswith(".docx"):
        name += ".docx"
    return name[:180]


def _result(opened: bool, **kw) -> str:
    return json.dumps(dict(opened=opened, **kw), ensure_ascii=False)


def open_mail_draft(args: dict, runner=subprocess.run, platform: str = sys.platform) -> str:
    to = [e.strip() for e in (args.get("to") or []) if isinstance(e, str) and EMAIL_RE.match(e.strip())]
    if not to:
        return _result(False, reason="bad_recipient")
    subject = str(args.get("subject") or "")[:255]
    html = str(args.get("body_html") or "")[:200000]
    path = ""
    if args.get("file_base64"):
        try:
            data = base64.b64decode(args["file_base64"], validate=True)
        except Exception:
            return _result(False, reason="bad_file")
        if not data or len(data) > MAX_BYTES:
            return _result(False, reason="bad_file")
        folder = Path(tempfile.mkdtemp(prefix="areo-mail-"))
        os.chmod(folder, 0o700)
        f = folder / _safe_name(args.get("file_name"))
        f.write_bytes(data)
        path = str(f)

    if platform == "darwin":
        if not Path("/Applications/Microsoft Outlook.app").exists():
            return _result(False, reason="no_outlook")
        r = runner(["osascript", "-e", _APPLESCRIPT, subject, html, path, *to],
                   capture_output=True, text=True, timeout=60)
    elif platform.startswith("win"):
        folder = Path(tempfile.mkdtemp(prefix="areo-mail-"))
        spec = folder / "spec.json"
        spec.write_text(json.dumps({"to": to, "subject": subject, "html": html, "file": path},
                                   ensure_ascii=False), encoding="utf-8")
        script = folder / "open.ps1"
        script.write_text(_POWERSHELL, encoding="utf-8")
        r = runner(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), str(spec)],
                   capture_output=True, text=True, timeout=60)
    else:
        return _result(False, reason="unsupported_system")
    if r.returncode != 0:
        return _result(False, reason="outlook_refused", detail=(r.stderr or "")[-300:])
    return _result(True, app="Outlook", attached=bool(path))
