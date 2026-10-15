# -*- coding: utf-8 -*-
"""מוסיף את ספריית הייחוס המשותפת לנתיב הייבוא.

המודולים ב-`areolegal/lib` מייבאים זה את זה (`orchestrator` ו-`playbook`
ו-`risk` מייבאים מ-`common`), ולכן הם צריכים שהתיקייה שמעליהם תהיה בנתיב.
סקריפט של סקיל מייבא את הקובץ הזה ראשון:

    import areo_lib  # noqa: F401
    from common.paths import safe_out_paths

הקובץ הזה זהה בכל הסקילים, ו-`release.sh` מאמת שהם לא נסחפו זה מזה.
"""
import sys
from pathlib import Path

LIB = Path(__file__).resolve().parents[3] / "lib"
if LIB.is_dir() and str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))
