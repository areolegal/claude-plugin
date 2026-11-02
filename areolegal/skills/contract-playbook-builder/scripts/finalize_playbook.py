"""finalize_playbook.py: כל שלב הסיום של בונה הפלייבוק בקריאה אחת, במקום שתים-עשרה קריאות נפרדות.

מריץ לפי הסדר המחייב של b5-outputs.md ("בדיקות החובה לפני שהפלייבוק נמסר"): הגרעין, הרישום באינדקס, נתוני
סביבת העבודה, שכבת האכיפה, בדיקת הנתונים, סביבת העבודה (עם לשונית "הכרעה ואישור"), ה-Word, המאמת, בדיקת החוזה
מול הנושא ונותן, ושער המסירה. כל שלב הוא הסקריפט הקיים, כלשונו; כאן רק מריצים אותם ברצף ומדפיסים דוח אחד.

    python3 -B finalize_playbook.py --model <model> --core <core> --data Areo-נתונים --profile <profile_path> \\
        --lang he --extract Areo-נתונים/corpus-extract.json --workspace "<סביבה>.html" \\
        --out-dir "<playbooks/<family_id>>" --index <רשומת האינדקס> --inventory <clause-inventory.json> \\
        [--current <family_id>] [--artifact <artifact.html>]
        [--dashboard-template <dashboard_template.html>] [--wizard-template <wizard_template.html>]
        [--approved-sources <מקורות-מאושרים.json>]

התבניות ורשימת המקורות המאושרים נארזו בתוסף, ואינן מורדות מהשרת בזמן ריצה: בלי --dashboard-template
ו---wizard-template נלקחות התבניות שב-assets של הרכיב (assets/dashboard_template.html, assets/wizard_template.html);
בלי --approved-sources המאמת קורא את AREO_APPROVED_SOURCES, ואחריו את העותק שבתוסף (lib/מקורות-מאושרים.json).
ארגומנט מפורש גובר תמיד.

שלב שנכשל: שכבת האכיפה עוצרת את הבנייה (כמו בהוראות). שאר השלבים רצים עד הסוף, כדי שהדוח יראה את כל הבעיות.
קוד יציאה 0 רק כשכל השלבים עברו. אחרי תיקון מריצים שוב את הסקריפט הזה, או רק את השלב שנכשל.
"""
import argparse
import glob
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
NEG = os.path.normpath(os.path.join(HERE, '..', '..', 'contract-negotiation-orchestrator', 'scripts'))
ASSETS = os.path.normpath(os.path.join(HERE, '..', 'assets'))
DEFAULT_DASHBOARD_TEMPLATE = os.path.join(ASSETS, 'dashboard_template.html')
DEFAULT_WIZARD_TEMPLATE = os.path.join(ASSETS, 'wizard_template.html')


def run(name, args, report):
    # -B בלי -I: -I מסתיר את ספריות המשתמש (python-docx שהותקן ב-pip --user ב-macOS), והשלבים צריכים אותן
    cmd = [sys.executable, '-B'] + args
    p = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    out = (p.stdout or '') + (p.stderr or '')
    tail = '\n'.join(out.strip().splitlines()[-6:])
    report.append({'step': name, 'ok': p.returncode == 0, 'exit': p.returncode, 'tail': tail})
    return p.returncode == 0


def main(argv=None):
    ap = argparse.ArgumentParser(description='שלב הסיום של בונה הפלייבוק בקריאה אחת')
    for k in ('model', 'core', 'data', 'profile', 'lang', 'extract', 'workspace', 'out-dir', 'index', 'inventory'):
        ap.add_argument('--' + k, required=True)
    ap.add_argument('--dashboard-template', default=DEFAULT_DASHBOARD_TEMPLATE)
    ap.add_argument('--wizard-template', default=DEFAULT_WIZARD_TEMPLATE)
    ap.add_argument('--approved-sources', default=None)
    ap.add_argument('--payload', default='payload.json')
    ap.add_argument('--current', default=None)
    ap.add_argument('--artifact', default=None)
    a = ap.parse_args(argv)
    missing = [p for p in (a.model, a.profile, a.extract, a.dashboard_template, a.wizard_template) if not os.path.isfile(p)]
    if missing:
        print(json.dumps({'ok': False, 'stopped_at': 'inputs', 'missing': missing}, ensure_ascii=False, indent=1))
        return 2
    S = lambda n: os.path.join(HERE, n)
    rep = []
    run('core', [S('build_playbook_core.py'), '--model', a.model], rep)
    run('register', [S('register_playbook.py'), '--data', a.data, '--model', a.model, '--core', a.core], rep)
    pay = [S('build_workspace_payload.py'), a.model, '--data', a.data, a.payload, '--profile', a.profile,
           '--lang', a.lang, '--extract', a.extract] + (['--current', a.current] if a.current else [])
    run('payload', pay, rep)
    if not run('enforce', [S('enforce_playbook_checks.py'), a.model, '--extract', a.extract], rep):
        print(json.dumps({'ok': False, 'stopped_at': 'enforce', 'steps': rep}, ensure_ascii=False, indent=1))
        return 2
    run('validate_data', [S('validate_data.py'), '--data', a.payload], rep)
    dash = [S('build_dashboard.py'), a.dashboard_template, a.payload, a.workspace, '--wizard', a.wizard_template,
            '--lang', a.lang, '--profile', a.profile] + (['--artifact', a.artifact] if a.artifact else [])
    run('workspace', dash, rep)
    run('word', [S('build_playbook_docx.py'), '--model', a.model, '--profile', a.profile, '--out-dir', a.out_dir], rep)
    docs = sorted(glob.glob(os.path.join(a.out_dir, '*.docx')), key=os.path.getmtime)
    word = docs[-1] if docs else ''
    run('validate_model', [S('validate_playbook_model.py'), a.model, '--core', a.core, '--index', a.index,
                           '--word', word, '--workspace', a.workspace, '--inventory', a.inventory,
                           '--extract', a.extract] + (['--approved-sources', a.approved_sources]
                                                      if a.approved_sources else []), rep)
    if os.path.isfile(os.path.join(NEG, 'check_playbook_contract.py')):
        run('contract', [os.path.join(NEG, 'check_playbook_contract.py'), a.model, '--core', a.core], rep)
    run('deliverables', [S('check_deliverables.py'), '--word', word, '--workspace', a.workspace], rep)
    ok = all(r['ok'] for r in rep)
    print(json.dumps({'ok': ok, 'word': word, 'workspace': a.workspace, 'steps': rep}, ensure_ascii=False, indent=1))
    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(main())
