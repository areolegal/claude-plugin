"""The workspace "cut off" check: a page embedded as data (the comments wizard, with its own "<script" inside a
string and escaped closings) is not a truncated file. Found in the overnight end-to-end run, 05.11.2026:
every finished playbook was reported as not passing its checks."""
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "areolegal" / "skills" / "contract-playbook-builder" / "scripts" / "validate_playbook_model.py"
spec = importlib.util.spec_from_file_location("vpm", SCRIPT)
vpm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vpm)


def _page(body):
    return "<!doctype html><html><head></head><body>" + body + "</body></html>"


def test_embedded_page_in_a_string_is_not_truncation(tmp_path):
    wizard = '<script type=\\"application/json\\">{}<\\/script>\\n<script>\\nrun();\\n<\\/script>'
    p = tmp_path / "ws.html"
    p.write_text(_page('<script>const W="' + wizard + '";</script><script>go()</script>'), encoding="utf-8")
    assert not [x for x in vpm.workspace_file_problems(str(p)) if "נחתך" in x]


def test_unclosed_script_is_still_caught(tmp_path):
    p = tmp_path / "ws.html"
    p.write_text("<!doctype html><html><body><script>const D={", encoding="utf-8")
    assert [x for x in vpm.workspace_file_problems(str(p)) if "נחתך" in x]
