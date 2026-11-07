#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
'מונחים עמומים בהסכם, מאותה רשימה שהנושא ונותן משתמש בה (`lib/common/vague_terms.py`).\n\nרשימה אחת, משותפת לשני הרכיבים. מעריך הסיכונים מריץ אותה על\nההסכם כולו, ורושם כל מופע שהעמימות בו פועלת נגד הלקוח כסיכון מסוג `vague_term` (r2-lenses.md, "מונחים\nעמומים"). `defined: true` הוא מופע שיש לו אמת מידה באותו משפט (תקן, נספח, הוראות בכתב, רף מספרי).\n\n    python "AREO_RT/skills/contract-risk-assessor/scripts/vague_terms.py" "<ההסכם>.docx"\n\nהפלט: JSON, לכל מופע פסקה, מונח, defined, context (המשפט שבו המונח) וקטע מתחילת הפסקה. הסקריפט אינו כותב דבר ואינו יוצא לרשת.\n'
import sys,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import areo_lib
from common import vague_terms
if __name__=='__main__':
	sys.dont_write_bytecode=True;sys.stdout.reconfigure(encoding='utf-8')
	if any(A in('-h','--help')for A in sys.argv[1:]):print(__doc__);sys.exit(0)
	sys.exit(vague_terms.main())
