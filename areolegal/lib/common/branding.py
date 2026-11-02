# -*- coding: utf-8 -*-
"""common/branding.py: צבעי המותג של הלקוח, מהפרופיל לנתוני תוצר HTML (meta.branding.theme).

הצבעים נגזרים רק ברכיב ההקמה (build_profile.py --derive-theme), בהסכמת הלקוח (branding.theme.choice = yes),
ושם נבדקת הניגודיות. כאן הם רק מועתקים לנתונים. ערך אחד שאינו #RRGGBB פוסל את כולם, והתוצר נבנה בעיצוב
הרגיל של Areo. התבניות מחליפות בהם את צבעי המותג בלבד; צבעי הרמזור, הטקסט וסימן Areo אינם משתנים.
"""
import re

THEME_KEYS = ("primary_light", "secondary_light", "soft_light", "on_light",
              "primary_dark", "secondary_dark", "soft_dark", "on_dark")
_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


def valid_tokens(t):
    return isinstance(t, dict) and set(t) == set(THEME_KEYS) and all(_HEX.match(str(t[k])) for k in THEME_KEYS)


def profile_theme(profile):
    """אסימוני המותג מהפרופיל, או None: בלי הסכמה, לפני גזירה, או כשערך אינו תקין."""
    th = ((profile or {}).get("branding") or {}).get("theme") or {}
    tok = th.get("tokens") or {}
    if th.get("choice") != "yes":
        return None
    tok = {k: tok.get(k) for k in THEME_KEYS}
    return tok if valid_tokens(tok) else None


def apply_theme(data, profile):
    """meta.branding.theme בנתונים, וגם בכל ספר בדף של כמה פלייבוקים. מחזיר שורה לסיכום ההרצה."""
    th = ((profile or {}).get("branding") or {}).get("theme") or {}
    tok = profile_theme(profile)
    if not tok:
        if th.get("choice") == "yes":
            return "מיתוג: אושר, אך הצבעים עוד לא נגזרו (build_profile.py --derive-theme). התוצר נבנה בעיצוב הרגיל"
        return None
    for meta in [data.setdefault("meta", {})] + [b.setdefault("meta", {}) for b in (data.get("books") or {}).values()
                                                 if isinstance(b, dict)]:
        meta.setdefault("branding", {})["theme"] = dict(tok)
    return "מיתוג: צבעי המותג של הלקוח הוחלו (%s)" % tok["primary_light"]
