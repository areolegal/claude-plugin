#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""מונחים עמומים בהסכם, מאותה רשימה שהנושא ונותן משתמש בה (`lib/common/vague_terms.py`).

רשימה אחת, משותפת לשני הרכיבים. מעריך הסיכונים מריץ אותה על
ההסכם כולו, ורושם כל מופע שהעמימות בו פועלת נגד הלקוח כסיכון מסוג `vague_term` (r2-lenses.md, "מונחים
עמומים"). `defined: true` הוא מופע שיש לו אמת מידה באותו משפט (תקן, נספח, הוראות בכתב, רף מספרי).

    python "AREO_RT/skills/contract-risk-assessor/scripts/vague_terms.py" "<ההסכם>.docx"

הפלט: JSON, לכל מופע פסקה, מונח, defined, context (המשפט שבו המונח) וקטע מתחילת הפסקה. הסקריפט אינו כותב דבר ואינו יוצא לרשת.
"""
import sys

import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # גם ב-python -I, שאינו מוסיף את תיקיית הסקריפט
import areo_lib  # noqa: F401  מוסיף את areolegal/lib לנתיב הייבוא

from common import vague_terms  # noqa: E402

if __name__ == "__main__":
    sys.dont_write_bytecode = True
    sys.stdout.reconfigure(encoding="utf-8")
    if any(x in ("-h", "--help") for x in sys.argv[1:]):
        print(__doc__)
        sys.exit(0)
    sys.exit(vague_terms.main())
