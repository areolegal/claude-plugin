# -*- coding: utf-8 -*-
"""מזריק נתוני פלייבוק לתבנית הדשבורד הקנונית. אין לבנות דשבורד מאפס.

שימוש בסיסי, קובץ HTML מקומי:
  python3 build_dashboard.py assets/dashboard_template.html payload.json dashboard.html

שימוש מלא, שני התוצרים באותה הרצה:
  python3 build_dashboard.py assets/dashboard_template.html payload.json out.html --artifact artifact.html

--artifact  מפיק תוכן לפרסום כעמוד משותף: ללא תגיות doctype/html/head/body,
            publishTarget=artifact, וללא מסלולי הורדת קבצים. ספריית הגרפים
            מוטמעת בקובץ עצמו בשני התוצרים, כי טעינה מרשת חיצונית חסומה בעמוד משותף.

--wizard <wizard_template.html>
            בונה גם את אשף ההערות, אשף אחד לכל פלייבוק שבדף, לצד הדף המקומי:
            <שם הדף>.wizard.<מזהה>.html. בדף מופיע הכפתור "להערות ולהצעות
            נוסח", והוא פותח את האשף של סוג ההסכם שנבחר בבורר. האשף נבנה
            מאותם נתונים בדיוק, כי "מחולל אחד, שתי תצוגות" (wizard_spec.md).
            בעמוד משותף מפרסמים את קובצי האשף כקבצים נלווים באותם שמות.

ה-payload חייב לכלול: meta (כולל slug ו-ls_key), rules, cites, sources, segments,
friendly/shortx (מיפוי שמות ידידותיים למקורות), precedents, templateFindings, queue, cross.
meta יכול לכלול גם: sharing (personal|shared|both), publishTarget, docAccess {mode, baseUrl}.
"""
import io, json, os, re, sys

def load(p):
    return io.open(p, encoding='utf-8').read()

def inject(tpl, data, chartjs):
    blob = json.dumps(data, ensure_ascii=False)
    blob = blob.replace('—', ', ').replace('–', '-')   # איסור מקפים ארוכים
    # הנתונים יושבים בתוך <script> בדף, ולכן ציטוט מהסכם שמכיל </script>
    # היה סוגר את הבלוק ומרוקן את הדף. הבריחה היא ברמת ה-JSON, ולכן הנוסח
    # של הציטוט נשאר מילה במילה: המפרש מחזיר בדיוק את אותה מחרוזת.
    # U+2028 ו-U+2029 חוקיים ב-JSON ואסורים בתוך קוד JavaScript.
    blob = (blob.replace('</', '<\\/')
                .replace('\u2028', '\\u2028').replace('\u2029', '\\u2029'))
    assert tpl.count('/*__DATA__*/null') == 1, 'injection point missing'
    assert tpl.count('/*__CHARTJS__*/') == 1, 'chart library placeholder missing'
    h = tpl.replace('/*__DATA__*/null', blob).replace('/*__CHARTJS__*/', chartjs)
    assert '—' not in h and '–' not in h, 'em/en dash leaked'
    return h

def to_artifact(html):
    """הפשטה לתוכן בלבד, כנדרש בעמוד משותף."""
    title = re.search(r'<title>.*?</title>', html, re.S)
    body  = re.search(r'<body[^>]*>(.*)</body>', html, re.S)
    if not (title and body):
        sys.exit('שגיאה: מבנה התבנית אינו כצפוי, לא ניתן להפיק עמוד משותף')
    head_bits = re.findall(r'<style>.*?</style>|<script>.*?</script>',
                           html[:html.index('<body')], re.S)
    return (title.group(0) + '\n' + '\n'.join(head_bits) +
            '\n<script>document.documentElement.setAttribute("dir","rtl");'
            'document.documentElement.setAttribute("lang","he");</script>\n' +
            body.group(1).strip() + '\n')

def wizard_name(out_path, book_id):
    stem = os.path.splitext(os.path.basename(out_path))[0]
    key = re.sub(r'[^A-Za-z0-9_]+', '_', str(book_id or 'playbook')).strip('_') or 'playbook'
    return '%s.wizard.%s.html' % (stem, key)


def inject_wizard(tpl, data):
    """האשף אינו צריך את ספריית הגרפים, ולכן ההזרקה שלו בלי מציין המקום שלה."""
    blob = json.dumps(data, ensure_ascii=False)
    blob = blob.replace('—', ', ').replace('–', '-')
    blob = (blob.replace('</', '<\\/')
                .replace('\u2028', '\\u2028').replace('\u2029', '\\u2029'))
    assert tpl.count('/*__DATA__*/null') == 1, 'injection point missing in the wizard'
    return tpl.replace('/*__DATA__*/null', blob)


def build_wizards(wiz_tpl, data, out_path):
    """אשף לכל פלייבוק בדף. מחזיר {מזהה: שם הקובץ}, ומסמן את הכתובת במטא
    של כל ספר כדי שהכפתור בדף יפתח את האשף של הסוג שנבחר."""
    books = data.get('books') or None
    if books:
        items = list(books.items())
    else:
        bid = (data.get('meta') or {}).get('id') or 'playbook'
        items = [(bid, data)]
    out_dir = os.path.dirname(os.path.abspath(out_path))
    made = {}
    for bid, book in items:
        w = json.loads(json.dumps(book))
        w.pop('books', None)
        w.setdefault('pb', {'id': bid, 'family': (w.get('meta') or {}).get('type_short') or '',
                            'role': ''})
        w.setdefault('meta', {})['dashboard_href'] = os.path.basename(out_path)
        name = wizard_name(out_path, bid)
        io.open(os.path.join(out_dir, name), 'w', encoding='utf-8').write(inject_wizard(wiz_tpl, w))
        book.setdefault('meta', {})['wizard_href'] = name
        made[bid] = name
    if books:
        cur = next((p['id'] for p in data.get('playbooks') or [] if p.get('current')), None)
        if cur in made:
            data['meta']['wizard_href'] = made[cur]
    return made


def main():
    args = sys.argv[1:]
    art = None
    wiz = None
    if '--artifact' in args:
        i = args.index('--artifact'); art = args[i+1]; del args[i:i+2]
    if '--wizard' in args:
        i = args.index('--wizard'); wiz = args[i+1]; del args[i:i+2]
    if len(args) < 3:
        sys.exit(__doc__)
    tpl_path, payload_path, out_path = args[0], args[1], args[2]
    tpl = load(tpl_path)
    data = json.load(io.open(payload_path, encoding='utf-8'))
    # The template is fetched from the AreoLegal service into a working folder,
    # so look for the vendored library beside the template first and then beside
    # this script (its home in the plugin) rather than failing.
    lib = os.path.join(os.path.dirname(os.path.abspath(tpl_path)), 'chart.umd.js')
    if not os.path.exists(lib):
        lib = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           '..', 'assets', 'chart.umd.js')
        lib = os.path.normpath(lib)
    if not os.path.exists(lib):
        sys.exit('שגיאה: chart.umd.js חסר בתיקיית assets. הספרייה מוטמעת ואינה נטענת מהרשת.')
    chartjs = load(lib)

    meta = data.setdefault('meta', {})
    wizards = build_wizards(load(wiz), data, out_path) if wiz else {}

    def target(d, where):
        d['meta']['publishTarget'] = where
        for b in (d.get('books') or {}).values():
            b.setdefault('meta', {})['publishTarget'] = where
        return d

    if out_path:
        d = target(json.loads(json.dumps(data)), 'local')
        io.open(out_path, 'w', encoding='utf-8').write(inject(tpl, d, chartjs))
    if art:
        d = target(json.loads(json.dumps(data)), 'artifact')
        io.open(art, 'w', encoding='utf-8').write(to_artifact(inject(tpl, d, chartjs)))

    mode = (meta.get('docAccess') or {}).get('mode', 'local')
    srcs = data.get('sources') or {}
    linked = sum(1 for k in srcs if (srcs[k] or {}).get('url'))
    print('נבנה %s%s. מצב גישה: %s. מקורות עם קישור: %d מתוך %d'
          % (out_path, (' ו-'+art) if art else '', mode, linked, len(srcs)))
    if data.get('books'):
        print('פלייבוקים בדף: %d' % len(data['books']))
    for bid, name in wizards.items():
        print('אשף: %s  (%s)' % (name, bid))
    if wiz and art:
        print('בעמוד המשותף: פרסם את קובצי האשף כקבצים נלווים, באותם שמות')
    print('בדיקה: node --check על מקטע הסקריפט, ואז node scripts/qa_dashboard.js')

if __name__ == '__main__':
    main()
