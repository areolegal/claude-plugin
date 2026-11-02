# -*- coding: utf-8 -*-
"""איתור הספרייה המשותפת (AREO_RT/lib) מתוך סקריפט של המנסח. הסקריפטים רצים מהתוסף, והספרייה (common, playbook)
נפרסת בתיקיית זמן הריצה של המחשב אחרי אימות הרישיון (SKILL.md, "טעינת רכיבי המערכת"), כמו אצל הנושא ונותן.

הסדר: משתנה הסביבה AREO_RT; אחריו התיקייה החדשה ביותר בשם areo-rt-* בתיקייה הזמנית שיש בה lib/common (אין עוד
תיקייה קבועה בשם areo-runtime); ואחריו מיקום הסקריפט עצמו כשהוא רץ מתוך החבילה (AREO_RT/skills/<סוכן>/scripts).
מחזיר None כשלא נמצאה: מי שקורא נופל לבדיקה המקומית שלו.
"""
import os
import sys
import tempfile


def _newest_rt_dir():
    """התיקייה החדשה ביותר areo-rt-* בתיקייה הזמנית שיש בה lib/common, לפי זמן שינוי. None כשאין."""
    best, best_t = None, -1.0
    try:
        names = os.listdir(tempfile.gettempdir())
    except OSError:
        return None
    for name in names:
        if not name.startswith("areo-rt-"):
            continue
        root = os.path.join(tempfile.gettempdir(), name)
        if os.path.isdir(os.path.join(root, "lib", "common")):
            try:
                t = os.path.getmtime(root)
            except OSError:
                continue
            if t > best_t:
                best, best_t = root, t
    return best


def areo_lib():
    here = os.path.dirname(os.path.abspath(__file__))
    # הסדר: משתנה הסביבה של השיחה, אחר כך החבילה שהסקריפט רץ ממנה. בחירה לפי "התיקייה החדשה ביותר" נשארה רק כמוצא אחרון,
    # כדי ששיחה שנייה לא תגרום לשיחה הראשונה לטעון קוד מחבילה אחרת
    for root in (os.environ.get("AREO_RT"), os.path.join(here, "..", "..", ".."), _newest_rt_dir()):
        if root:
            lib = os.path.normpath(os.path.join(root, "lib"))
            if os.path.isdir(os.path.join(lib, "common")):
                return lib
    return None


def ensure_lib():
    """מוסיף את הספרייה ל-sys.path (בסוף, כדי שהסקריפטים השכנים לא יוחלפו). מחזיר את הנתיב או None."""
    lib = areo_lib()
    if lib and lib not in sys.path:
        sys.path.append(lib)
    return lib
