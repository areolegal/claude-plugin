#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""מונחים עמומים בהסכם, מאותה רשימה שהנושא ונותן משתמש בה (`areolegal/lib/common/vague_terms.py`).

הערות ענבל לנושא ונותן, 22.10.2026, כלל 5: רשימה אחת, משותפת לשני הרכיבים. מעריך הסיכונים מריץ אותה על
ההסכם כולו, ורושם כל מופע שהעמימות בו פועלת נגד הלקוח כסיכון מסוג `vague_term` (methodology.md, "מונחים
עמומים"). `defined: true` הוא מופע שיש לו אמת מידה באותו משפט (תקן, נספח, הוראות בכתב, רף מספרי).

    python scripts/vague_terms.py "<ההסכם>.docx"

הפלט: JSON, לכל מופע פסקה, מונח, defined וקטע מהפסקה. הסקריפט אינו כותב דבר ואינו יוצא לרשת.
"""
import sys

import areo_lib  # noqa: F401  מוסיף את areolegal/lib לנתיב הייבוא

from common import vague_terms  # noqa: E402

if __name__ == "__main__":
    sys.dont_write_bytecode = True
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(vague_terms.main())
