# -*- coding: utf-8 -*-
"""מזריק נתוני פלייבוק לתבנית הדשבורד הקנונית. אין לבנות דשבורד מאפס.

שימוש בסיסי, קובץ HTML מקומי:
  python3 build_dashboard.py assets/dashboard_template.html payload.json dashboard.html

שימוש מלא, שני התוצרים באותה הרצה:
  python3 build_dashboard.py assets/dashboard_template.html payload.json out.html --artifact artifact.html

--artifact  מפיק תוכן לפרסום כעמוד משותף: ללא תגיות doctype/html/head/body,
            publishTarget=artifact, וללא מסלולי הורדת קבצים. ספריית הגרפים
            מוטמעת בקובץ עצמו בשני התוצרים, כי טעינה מרשת חיצונית חסומה בעמוד משותף.

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

def main():
    args = sys.argv[1:]
    art = None
    if '--artifact' in args:
        i = args.index('--artifact'); art = args[i+1]; del args[i:i+2]
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
    if out_path:
        d = json.loads(json.dumps(data)); d['meta']['publishTarget'] = 'local'
        io.open(out_path, 'w', encoding='utf-8').write(inject(tpl, d, chartjs))
    if art:
        d = json.loads(json.dumps(data)); d['meta']['publishTarget'] = 'artifact'
        io.open(art, 'w', encoding='utf-8').write(to_artifact(inject(tpl, d, chartjs)))

    mode = (meta.get('docAccess') or {}).get('mode', 'local')
    srcs = data.get('sources') or {}
    linked = sum(1 for k in srcs if (srcs[k] or {}).get('url'))
    print('נבנה %s%s. מצב גישה: %s. מקורות עם קישור: %d מתוך %d'
          % (out_path, (' ו-'+art) if art else '', mode, linked, len(srcs)))
    print('בדיקה: node --check על מקטע הסקריפט, ואז node scripts/qa_dashboard.js')

if __name__ == '__main__':
    main()
