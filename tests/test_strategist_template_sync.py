# -*- coding: utf-8 -*-
"""הבודק של האסטרטג והתבנית של מרכז ההיערכות מתואמים (הערות ענבל 22.10.2026, כלל 14).

כל ערך שהבודק (`validate_data.py`) מאשר, התבנית יודעת להציג, ולהפך. הבדיקה רצה בבניית הגרסה
(release.sh, שלב הבדיקות), ולא אצל הלקוח. היא נכתבה אחרי שנמצא שהבודק התיר בעץ התגובות hard,
soft, open ו-bridge, כשהתבנית צובעת רק green, yellow ו-red: כל שורה בעץ הוצגה באפור.

שני מקורות בתבנית: סכמת הנתונים שבראש הקובץ ("a|b|c"), ומפות התצוגה בקוד (SEV, LVL, BRIDGE_SRC).
מפה שמוגדרת מהמילון (BRIDGE_SRC = T.bridgeSrc) נבדקת בכל שפה שבמילון.

התבנית היא העותק שנארז בתוסף (skills/negotiation-strategist/assets), כי הקוד והתבניות אינם נשלפים מהשרת בזמן ריצה.
"""
import importlib.util
import re
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parents[1] / "areolegal" / "skills" / "negotiation-strategist"
SCRIPTS = SKILL / "scripts"
TEMPLATE = SKILL / "assets" / "prep-center-template.html"

# נטען בשם נפרד: גם למעריך הסיכונים יש validate_data, ושני המודולים אינם נדרסים זה בזה
_spec = importlib.util.spec_from_file_location("strategist_validate_data", SCRIPTS / "validate_data.py")
V = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V)


def _html():
    return TEMPLATE.read_text(encoding="utf-8")


def _schema_values(field):
    """כל הערכים "a|b|c" שהסכמה בראש התבנית נותנת לשדה. כמה מופעים: איחוד."""
    head = _html().split("<script", 1)[0] + _html()[:6000]
    vals = set()
    for m in re.finditer(r'"%s"\s*:\s*"([a-z_]+(?:\|[a-z_]+)+)"' % re.escape(field), head):
        vals |= set(m.group(1).split("|"))
    return vals


def _keys(body):
    return set(re.findall(r"(?:^|[,{\s])([a-z_]+)\s*:", "{" + body))


def _js_map_keys(name):
    """המפתחות של מפת תצוגה: אובייקט מפורש (const X = {...}), או הפניה למילון (const X = T.key), ואז המפה
    של כל שפה במילון חייבת להכיל אותם מפתחות."""
    html = _html()
    m = re.search(r"const\s+%s\s*=\s*\{(.*?)\};" % name, html, re.S)
    if m:
        return _keys(m.group(1))
    a = re.search(r"const\s+%s\s*=\s*T\.(\w+)\s*;" % name, html)
    assert a, "המפה %s חסרה בתבנית" % name
    per_lang = [_keys(x) for x in re.findall(r"\b%s\s*:\s*\{([^{}]*)\}" % a.group(1), html)]
    assert len(per_lang) >= 2, "המפה %s (T.%s) חסרה באחת השפות" % (name, a.group(1))
    assert all(k == per_lang[0] for k in per_lang), "T.%s שונה בין השפות: %s" % (a.group(1), per_lang)
    return per_lang[0]


# הערך בבודק, השדה בסכמה של התבנית, ומפת התצוגה בקוד (כשיש)
PAIRS = [
    ("risk.severity", "severity", "SEV"),
    ("node.level", "level", "LVL"),
    ("node.side", "side", None),
    ("dialogue.who", "who", None),
    ("docAccess.mode", "mode", None),
    ("bridge.source", "source", "BRIDGE_SRC"),
    ("meta.deliverable_language", "deliverable_language", None),
    ("meta.display_language", "display_language", None),
    ("meta.agreement_language", "agreement_language", None),
]
# סוג הנייר אינו בסכמה שבראש התבנית: התבנית מזהה אותו בביטוי בקוד (PT), וכל ערך אחר מוצג כ-negotiable
CODE_ENUMS = {"meta.paper_type": r"const\s+PT\s*=\s*/\^\(([a-z_|]+)\)\$/.*?:\s*\"([a-z_]+)\"\s*;"}


@pytest.mark.parametrize("key,field,jsmap", PAIRS)
def test_checker_and_template_allow_the_same_values(key, field, jsmap):
    allowed = V.ENUMS[key]
    schema = _schema_values(field)
    assert schema, "לשדה %s אין ערכים בסכמה שבראש התבנית" % field
    assert allowed == schema, "%s: הבודק מתיר %s, והסכמה של התבנית %s" % (key, sorted(allowed), sorted(schema))
    if jsmap:
        shown = _js_map_keys(jsmap)
        assert allowed <= shown, "%s: ערכים שהבודק מתיר ואין להם תצוגה ב-%s: %s" % (
            key, jsmap, sorted(allowed - shown))
        assert shown <= allowed, "%s: ערכים ש-%s מציגה והבודק דוחה: %s" % (key, jsmap, sorted(shown - allowed))


def test_every_checker_enum_is_covered_here():
    """ערך חדש בבודק נכנס גם לבדיקה הזו, אחרת התיאום שלו אינו נבדק."""
    assert set(V.ENUMS) == {k for k, _, _ in PAIRS} | set(CODE_ENUMS)


@pytest.mark.parametrize("key", sorted(CODE_ENUMS))
def test_checker_and_template_code_allow_the_same_values(key):
    m = re.search(CODE_ENUMS[key], _html())
    assert m, "%s: הביטוי בתבנית לא נמצא" % key
    shown = set(m.group(1).split("|")) | {m.group(2)}
    assert V.ENUMS[key] == shown, "%s: הבודק מתיר %s, והתבנית מציגה %s" % (key, sorted(V.ENUMS[key]), sorted(shown))


def test_a_bridge_without_a_source_is_flagged_and_a_wrong_one_fails():
    clause = {"id": "R-1", "title": "t", "playbook": {"position": "p"},
              "lines": {"red": {"what": "x"}, "yellow": {"what": "y"}, "bridge": {"wording": "z"}}}
    data = {"meta": {}, "counters": {}, "clauses": [clause]}
    r = V.validate(data)
    assert any("source" in m for _, m in r.warns)
    clause["lines"]["bridge"]["source"] = "invented"
    r = V.validate(data)
    assert any("source" in m and "invented" in m for _, m in r.errors)
    clause["lines"]["bridge"]["source"] = "their_wording"
    r = V.validate(data)
    assert not any("source" in m for _, m in r.errors + r.warns)


# ---------------------------------------------------------------- התבנית שנארזת בתוסף היא ברירת המחדל
def _build(tmp_path, *args):
    import json
    import subprocess
    import sys
    data = tmp_path / "strategy-data.json"
    data.write_text(json.dumps({"meta": {}, "counters": {}, "clauses": []}), encoding="utf-8")
    return subprocess.run([sys.executable, "-B", str(SCRIPTS / "build_prep_center.py"), "--data", str(data)]
                          + [str(x) for x in args], capture_output=True, text=True)


def test_without_template_the_bundled_copy_is_used_and_kept(tmp_path):
    assert TEMPLATE.is_file()
    before = TEMPLATE.read_bytes()
    out = tmp_path / "center.html"
    r = _build(tmp_path, "--out", out)
    assert r.returncode == 0, r.stdout + r.stderr
    html = out.read_text(encoding="utf-8")
    assert "__STRATEGY_DATA__" not in html and "מרכז היערכות" in html
    explicit = tmp_path / "explicit.html"
    assert _build(tmp_path, "--out", explicit, "--template", TEMPLATE).returncode == 0
    assert explicit.read_text(encoding="utf-8") == html
    assert TEMPLATE.read_bytes() == before   # העותק שבתוסף לעולם אינו נמחק


def test_a_template_inside_the_client_folder_is_still_refused(tmp_path):
    client = tmp_path / "client"
    (client / "Areo-נתונים").mkdir(parents=True)
    tpl = client / "prep-center-template.html"
    tpl.write_bytes(TEMPLATE.read_bytes())
    r = _build(tmp_path, "--out", tmp_path / "c.html", "--template", tpl)
    assert r.returncode == 2 and "save_resource" not in r.stdout and "בלי --template" in r.stdout
    assert not (tmp_path / "c.html").exists()
