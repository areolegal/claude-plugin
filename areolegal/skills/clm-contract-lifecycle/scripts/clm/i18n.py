"""שפת הנתונים: עברית (he) או אנגלית (en), לפי meta.lang.

ההרכבה קובעת את השפה פעם אחת (using), וכל מחרוזת שהלקוח רואה נבחרת ב-t(עברית, אנגלית).
מחוץ להרכבה השפה היא עברית, ולכן קריאה ישירה לפונקציות (בבדיקות ובוולידציה) נשארת כפי שהייתה.
המפתחות והקודים בנתונים אינם משתנים לפי שפה. ציטוט מההסכם אינו מתורגם לעולם.
"""
import contextlib

LANGS = ("he", "en")
_state = {"lang": "he"}


def norm(lang):
    """he או en. כל ערך שאינו מתחיל ב-en (כולל both וריק) הוא עברית."""
    return "en" if str(lang or "").strip().lower()[:2] == "en" else "he"


def lang():
    return _state["lang"]


def en():
    return _state["lang"] == "en"


def t(he, en_text):
    """המחרוזת בשפה הנוכחית."""
    return en_text if _state["lang"] == "en" else he


@contextlib.contextmanager
def using(value):
    before = _state["lang"]
    _state["lang"] = norm(value)
    try:
        yield _state["lang"]
    finally:
        _state["lang"] = before
