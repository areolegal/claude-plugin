# -*- coding: utf-8 -*-
"""מוסיף את ספריית הייחוס המשותפת לנתיב הייבוא.

המודולים ב-`areolegal/lib` מייבאים זה את זה (`orchestrator` ו-`playbook`
ו-`risk` מייבאים מ-`common`), ולכן הם צריכים שהתיקייה שמעליהם תהיה בנתיב.
סקריפט של סקיל מייבא את הקובץ הזה ראשון:

    import areo_lib  # noqa: F401
    from common.paths import safe_out_paths

הקובץ הזה זהה בכל הסקילים, ו-`release.sh` מאמת שהם לא נסחפו זה מזה.

הוא גם מעביר את stdout ו-stderr ל-UTF-8 (errors="replace"), כש-reconfigure זמין: בלי
זה, בקונסולה ב-cp1252 (או PYTHONIOENCODING=cp1252), print של עברית נופל ב-
UnicodeEncodeError, והסקריפט מסתיים בקוד 1 באמצע הפלט.
"""
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):   # לא TextIOWrapper (לכידה בבדיקות, pythonw)
        pass

LIB = Path(__file__).resolve().parents[3] / "lib"
if LIB.is_dir() and str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))
