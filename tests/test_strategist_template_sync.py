# -*- coding: utf-8 -*-
"""הבודק של האסטרטג והתבנית של מרכז ההיערכות מתואמים (הערות ענבל 22.10.2026, כלל 14).

כל ערך שהבודק (`validate_data.py`) מאשר, התבנית יודעת להציג, ולהפך. הבדיקה רצה בבניית הגרסה
(release.sh, שלב הבדיקות), ולא אצל הלקוח. היא נכתבה אחרי שנמצא שהבודק התיר בעץ התגובות hard,
soft, open ו-bridge, כשהתבנית צובעת רק green, yellow ו-red: כל שורה בעץ הוצגה באפור.

שני מקורות בתבנית: סכמת הנתונים שבראש הקובץ ("a|b|c"), ומפות התצוגה בקוד (SEV, LVL, BRIDGE_SRC).
"""
import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "plugin" / "areolegal" / "skills" / "negotiation-strategist" / "scripts"
TEMPLATE = ROOT / "server" / "content" / "negotiation-strategist" / "prep-center-template.html"

pytestmark = pytest.mark.skipif(not TEMPLATE.exists(), reason="עץ התוכן (../server) אינו מחולץ כאן")

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


def _js_map_keys(name):
    m = re.search(r"const\s+%s\s*=\s*\{(.*?)\};" % name, _html(), re.S)
    assert m, "המפה %s חסרה בתבנית" % name
    return set(re.findall(r"(?:^|[,{\s])([a-z_]+)\s*:", "{" + m.group(1)))


# הערך בבודק, השדה בסכמה של התבנית, ומפת התצוגה בקוד (כשיש)
PAIRS = [
    ("risk.severity", "severity", "SEV"),
    ("node.level", "level", "LVL"),
    ("node.side", "side", None),
    ("dialogue.who", "who", None),
    ("docAccess.mode", "mode", None),
    ("bridge.source", "source", "BRIDGE_SRC"),
]


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
    assert set(V.ENUMS) == {k for k, _, _ in PAIRS}


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
