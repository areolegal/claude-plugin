"""check_deliverables.py: שער המסירה של בונה הפלייבוק. כל הרצה מסתיימת בשני תוצרים, ואין מסירה בלי שניהם.

    python -B -I check_deliverables.py --word "<הפלייבוק>.docx" --workspace "<סביבה>.html"

1. קובץ Word תקין (docx: zip עם word/document.xml).
2. סביבת העבודה (Areo Workspace): HTML שנבנה מהתבנית, עם נתוני הפלייבוק.
   ובתוכה הלשונית "הכרעה ואישור" (דף האשף משובץ בסביבת העבודה).
קוד יציאה 0 רק כששניהם קיימים ותקינים. אחרת 2, עם שורה לכל תוצר חסר. אין מסירה עד שהבדיקה עוברת.
"""
import argparse
import json
import os
import sys
import zipfile


def _html_ok(path, must):
    try:
        with open(path, encoding='utf-8') as fh:
            text = fh.read()
    except (OSError, UnicodeDecodeError):
        return False
    return len(text) > 2000 and all(m in text for m in must)


def check(word, workspace, wizard=None):
    problems = []
    if not word or not os.path.isfile(word):
        problems.append('word: missing')
    else:
        try:
            with zipfile.ZipFile(word) as z:
                if 'word/document.xml' not in z.namelist():
                    problems.append('word: not a valid docx')
        except (zipfile.BadZipFile, OSError):
            problems.append('word: not a valid docx')
    if not workspace or not os.path.isfile(workspace):
        problems.append('workspace: missing')
    elif not _html_ok(workspace, ('AREO-KIT:BEGIN', '<html')):
        problems.append('workspace: not built from the template')
    if workspace and os.path.isfile(workspace) and not _html_ok(workspace, ('"wizard_doc":', 'vApprove')):
        problems.append('workspace: the decide-and-approve tab is missing (build with --wizard)')
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description='שער המסירה: Word, וסביבת עבודה עם לשונית הכרעה ואישור')
    ap.add_argument('--word', required=True)
    ap.add_argument('--workspace', required=True)
    ap.add_argument('--wizard', default=None, help='לא נדרש עוד: דף האישור משובץ בסביבת העבודה')
    a = ap.parse_args(argv)
    problems = check(a.word, a.workspace, a.wizard)
    print(json.dumps({'ok': not problems, 'problems': problems}, ensure_ascii=False))
    return 0 if not problems else 2


if __name__ == '__main__':
    sys.exit(main())
