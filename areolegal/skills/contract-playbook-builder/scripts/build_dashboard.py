# -*- coding: utf-8 -*-
"""מזריק נתוני פלייבוק לתבנית הדשבורד הקנונית. אין לבנות דשבורד מאפס.

שימוש בסיסי, קובץ HTML מקומי:
  python3 build_dashboard.py assets/dashboard_template.html payload.json dashboard.html
  python3 build_dashboard.py payload.json dashboard.html      (בלי תבנית: העותק שבתוסף, assets/dashboard_template.html)

התבנית נארזה בתוסף ואינה מורדת מהשרת בזמן ריצה. בלי נתיב תבנית (שני ארגומנטים בלבד) נלקחת
assets/dashboard_template.html של הרכיב, ואשף ההערות שלידה (assets/wizard_template.html). נתיב מפורש גובר.

שימוש מלא, שני התוצרים באותה הרצה:
  python3 build_dashboard.py assets/dashboard_template.html payload.json out.html --artifact artifact.html

--artifact  מפיק תוכן לפרסום כעמוד משותף: ללא תגיות doctype/html/head/body,
            publishTarget=artifact, וללא מסלולי הורדת קבצים. ספריית הגרפים
            מוטמעת בקובץ עצמו בשני התוצרים, כי טעינה מרשת חיצונית חסומה בעמוד משותף.

--wizard <wizard_template.html>
            בונה גם את אשף ההערות, אשף אחד לכל פלייבוק שבדף, לצד הדף המקומי:
            <שם הדף>.wizard.<מזהה>.html. בדף מופיע הכפתור "להערות ולהצעות
            נוסח", והוא פותח את האשף של סוג ההסכם שנבחר בבורר. האשף נבנה
            מאותם נתונים בדיוק, כי "מחולל אחד, שתי תצוגות" (wizard_spec.md),
            ומוטמע בו רק מה שהוא מציג (wizard_data), כדי שייפתח מהר.
            בעמוד משותף מפרסמים את קובצי האשף כקבצים נלווים באותם שמות.

ה-payload חייב לכלול: meta (כולל slug ו-ls_key), rules, cites, sources, segments,
friendly/shortx (מיפוי שמות ידידותיים למקורות), precedents, templateFindings, queue, cross.
meta יכול לכלול גם: sharing (personal|shared|both), publishTarget, docAccess {mode, baseUrl}.

--profile <פרופיל-לקוח.json>
            צבעי המותג של הלקוח (branding.theme), כשהלקוח אישר מיתוג והצבעים נגזרו: נכנסים ל-meta.branding.theme
            בדף ובאשף, וכך גם הלוגו שבנתונים (meta.branding.logo) עובר לאשף.

-h, --help  מדפיס את ההוראות האלה ויוצא בקוד 0.

--lang he|en  שפת הדף (meta.lang). בלעדיו: deliverable_language מ---profile (ו-display_language כשהיא
            "both"), ובלעדיהם מה שבנתונים (build_workspace_payload.py כותב אותו מ-deliverable_language),
            וברירת המחדל עברית. כך דף של לקוח באנגלית לעולם אינו נבנה בעברית. השפה קובעת את dir ו-lang של
            הדף ואת כל הטקסט הקבוע בתבנית ובאשף; הנתונים עצמם אינם מתורגמים.
"""
import io, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # גם ב-python -I, שאינו מוסיף את תיקיית הסקריפט
import areo_lib  # noqa: F401  מוסיף את areolegal/lib לנתיב הייבוא, ופלט UTF-8 בקונסולה
DEFAULT_TEMPLATE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets',
                                                 'dashboard_template.html'))
from common.cli import OutputRefused, guard_out  # noqa: E402
from common.branding import apply_theme  # noqa: E402
from common import capabilities as CAP  # noqa: E402
from playbook import approval_sheet as A  # noqa: E402
from playbook import status as S  # noqa: E402

def load(p):
    return io.open(p, encoding='utf-8').read()

# איסור המקפים חל על טקסט שהמערכת כותבת. ציטוט מילולי ממסמך מקור נשאר כלשונו, כולל הפיסוק
# (output-rules.md, "כללי נוסח"): בציטוט המקף נכתב כבריחת JSON (\u2014), ולכן הדף מציג אותו,
# ובקוד המקור של הדף עדיין אין אף מקף (הבדיקה למטה, qa_dashboard.js ו-validate_playbook_html.py)
_QMARK = {'\u2014': '\ue014', '\u2013': '\ue013'}


def _protect_quotes(v, key=''):
    """`quote` בכל מקום, ו-`text` של ציטוט ב-cites[]: המקפים בהם מסומנים לפני ההחלפה הכללית."""
    if isinstance(v, dict):
        return {k: _protect_quotes(x, k if not (key == 'cites' and k == 'text') else 'quote')
                for k, x in v.items()}
    if isinstance(v, list):
        return [_protect_quotes(x, key) for x in v]
    if isinstance(v, str) and key == 'quote':
        for d, mark in _QMARK.items():
            v = v.replace(d, mark)
    return v


def _dump(data):
    blob = json.dumps(_protect_quotes(data), ensure_ascii=False)
    blob = blob.replace('—', ', ').replace('–', '-')   # איסור מקפים ארוכים, בטקסט שאינו ציטוט
    return blob.replace('\ue014', '\\u2014').replace('\ue013', '\\u2013')

def inject(tpl, data, chartjs):
    blob = _dump(data)
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

def page_lang(data):
    """he או en, מ-meta.lang (או deliverable_language). כל ערך אחר: עברית."""
    m = data.get('meta') or {}
    v = str(m.get('lang') or m.get('deliverable_language') or 'he').strip().lower()
    return 'en' if v.startswith('en') else 'he'


def to_artifact(html, lang='he'):
    """הפשטה לתוכן בלבד, כנדרש בעמוד משותף. הכיוון והשפה לפי שפת הדף."""
    title = re.search(r'<title>.*?</title>', html, re.S)
    body  = re.search(r'<body[^>]*>(.*)</body>', html, re.S)
    if not (title and body):
        sys.exit('שגיאה: מבנה התבנית אינו כצפוי, לא ניתן להפיק עמוד משותף')
    head_bits = re.findall(r'<style>.*?</style>|<script>.*?</script>',
                           html[:html.index('<body')], re.S)
    return (title.group(0) + '\n' + '\n'.join(head_bits) +
            '\n<script>document.documentElement.setAttribute("dir","%s");'
            'document.documentElement.setAttribute("lang","%s");</script>\n'
            % ('ltr' if lang == 'en' else 'rtl', lang) +
            body.group(1).strip() + '\n')

def wizard_name(out_path, book_id):
    stem = os.path.splitext(os.path.basename(out_path))[0]
    key = re.sub(r'[^A-Za-z0-9_]+', '_', str(book_id or 'playbook')).strip('_') or 'playbook'
    return '%s.wizard.%s.html' % (stem, key)


_TRACKS = ('green', 'yellow', 'red')


def _wiz_hash(text):
    """טביעת האצבע של הנוסח, החישוב האחד (approval_sheet.wiz_hash) שגם apply_decisions.py מחשב. מחושבת כאן על
    הנוסח המקורי, לפני החלפת המקפים בהזרקה, כדי שתתאים לנוסח שבמודל."""
    return A.wiz_hash(text)


def _first_sent(t, n=220):
    t = str(t or '')
    i = t.find('. ')
    return t[:i + 1] if 0 < i < n else t[:n]


def disp_num(r, idx):
    """מספר הסעיף לתצוגה, אותו חישוב כמו rnum בתבנית: num, אחרת המזהה בלי R- ובלי אפס מוביל כשהוא
    מספר, אחרת המקום ברשימה. כך "1" בסביבת העבודה הוא "1" גם באשף, ולא "R-01"."""
    if r.get('num'):
        return str(r['num'])
    bare = re.sub(r'^0', '', str(r.get('id') or '').replace('R-', '', 1))
    return bare if re.fullmatch(r'[0-9][0-9.]*', bare) else str(idx + 1)


# המעטפת של הדף ושל האשף בשפת הדף: lang, dir והכותרת נקבעים כבר בקובץ, ולא רק אחרי שהסקריפט רץ
SHELL_TITLES = {'page': {'he': 'מדיניות חוזית', 'en': 'Contract policy'},
                'wizard': {'he': 'אשף ההערות', 'en': 'Comments wizard'}}


def localize_shell(html, lang, kind='page'):
    """<html lang dir> ו-<title> לפי שפת הדף. תבנית בלי התגיות האלה חוזרת כמו שהיא."""
    d = 'ltr' if lang == 'en' else 'rtl'
    html = re.sub(r'<html\b[^>]*>', '<html lang="%s" dir="%s">' % (lang, d), html, count=1)
    return re.sub(r'<title>.*?</title>', '<title>%s</title>' % SHELL_TITLES[kind][lang], html, count=1, flags=re.S)


def wizard_data(book, bid, dashboard_href):
    """רק מה שהאשף מציג: כרטיס הסעיף, שלוש העמדות, הציטוטים שמשויכים לעמדה והמקורות שלהם,
    המקורות הנורמטיביים והשאלות הפתוחות. הנימוק המלא, הסגמנטים, הנתונים המסחריים והכיסוי
    נשארים בסביבת העבודה, וכך האשף קטן ונפתח מהר (wizard_spec.md, "קלט, ומה בונה אותו")."""
    m = book.get('meta') or {}
    # approved_count ו-positions_count: אותו מונה ואותה יחידה (עמדה = סעיף × צבע) כמו בסביבת העבודה, כדי שהאשף
    # יאמר "X מתוך N עמדות" באותו מכנה (ביקורת 31.10, כלל 10)
    meta = {k: m[k] for k in ('id', 'slug', 'title', 'company', 'lang', 'deliverable_language',
                              'version', 'created', 'updated', 'type_short',
                              'approved_count', 'positions_count') if k in m}
    meta['dashboard_href'] = dashboard_href
    meta['segments_count'] = len(book.get('segments') or [])
    pb = book.get('pb')
    if not pb:
        # דף של פלייבוק אחד: סוג ההסכם והצד נלקחים מהיקף הפלייבוק, כדי שהאשף יאמר על מה הוא
        fam = ((book.get('scope') or {}).get('contract_families') or [{}])[0] or {}
        pb = {'id': bid, 'family': m.get('type_short') or fam.get('contract_family_name') or '',
              'role': fam.get('company_role') or ''}
    rules, rids = [], set()
    all_rules = book.get('rules') or []
    for idx, r in enumerate(all_rules):
        rat, persp = r.get('rat') or {}, r.get('persp') or {}
        legal = (rat.get('protected_interest_and_clause_purpose')
                 or rat.get('legal_risk_and_legal_framework') or persp.get('legal_analysis') or '')
        comm = rat.get('business_operational_impact') or persp.get('business_analysis') or ''
        tl = {}
        for k in _TRACKS:
            l = (r.get('tl') or {}).get(k) or {}
            tl[k] = {'pos': l.get('pos') or '', 'clause': l.get('clause') or '',
                     'h': _wiz_hash(l.get('clause') or '')}
            # השפה של הנוסח שהוצג (approval_sheet.clause_text), וסוגריים של ערך שלא נקבע: האשף רושם את
            # השפה בקובץ, וחוסם אישור של עמדה שנשארו בה סוגריים
            if l.get('clause_lang'):
                tl[k]['lang'] = l['clause_lang']
            if l.get('slots'):
                tl[k]['slots'] = list(l['slots'])
            # מה שהעורך רואה בדשבורד על העמדה: סימון הצעת Areo, הסבר ההתאמה והאם נשארה בדיקה משפטית פתוחה
            for fld in ('label', 'basis_note', 'company_effect'):
                if l.get(fld):
                    tl[k][fld] = l[fld]
            if l.get('legal_review_open'):
                tl[k]['legal_review_open'] = True
        w = {'id': r.get('id'), 'tl': tl,
             'interest': {'legal': _first_sent(legal), 'comm': _first_sent(comm)},
             'norms': [{'law': n.get('law') or '', 'ref': n.get('ref') or '',
                        'meaning': n.get('meaning') or ''} for n in (r.get('norms') or [])
                       if isinstance(n, dict)]}
        for k in ('topic', 'issue', 'kind', 'why', 'they'):
            if r.get(k):
                w[k] = r[k]
        # אותו מספר סעיף כמו בסביבת העבודה (rnum בתבנית): num, ובלעדיו המספר שבמזהה או המקום ברשימה
        w['num'] = disp_num(r, idx)
        if r.get('walk_away') is True:
            w['walk_away'] = True
        if r.get('client_concern') is True:
            w['client_concern'] = True
        rules.append(w)
        rids.add(r.get('id'))
    cites, used = [], set()
    for c in book.get('cites') or []:
        if str(c.get('track') or '') not in _TRACKS:
            continue
        rs = [x for x in (c.get('rules') or []) if x in rids]
        if not rs:
            continue
        cites.append({'id': c.get('id'), 'rules': rs, 'src': c.get('src'), 'text': c.get('text') or '',
                      'ref': c.get('ref') or '', 'track': c.get('track')})
        used.add(c.get('src'))
    srcs = book.get('sources') or {}
    sources = {k: {f: v[f] for f in ('label', 'title', 'short', 'paper', 'kind', 'status', 'role',
                                       'date', 'loc') if (v or {}).get(f)}
               for k, v in srcs.items() if k in used}
    # המכנה של האחוז: ההסכמים הפנימיים של הסוג הזה, כמו בסביבת העבודה (trackPct)
    meta['int_total'] = sum(1 for v in srcs.values()
                            if (v or {}).get('kind') == 'internal'
                            and (not v.get('pb') or v.get('pb') == pb.get('id')))
    out = {'meta': meta, 'pb': pb, 'rules': rules, 'cites': cites, 'sources': sources,
           'queue': [{'rule_id': q.get('rule_id'), 'question': q.get('question') or '',
                      'issue': q.get('issue') or ''}
                     for q in (book.get('queue') or []) ]}
    if book.get('shortx'):
        out['shortx'] = {k: v for k, v in book['shortx'].items() if k in used}
    return out


def inject_wizard(tpl, data):
    """האשף אינו צריך את ספריית הגרפים, ולכן ההזרקה שלו בלי מציין המקום שלה."""
    blob = _dump(data)
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
        w = wizard_data(book, bid, os.path.basename(out_path))
        w['meta'].setdefault('lang', page_lang(data))   # שפת האשף היא שפת הדף
        br = (book.get('meta') or {}).get('branding') or (data.get('meta') or {}).get('branding')
        if br:
            w['meta']['branding'] = br                     # הלוגו וצבעי המותג, כמו בסביבת העבודה
        name = wizard_name(out_path, bid)
        wiz_html = localize_shell(inject_wizard(wiz_tpl, w), w['meta']['lang'] if w['meta'].get('lang') in ('he', 'en')
                                  else page_lang(data), 'wizard')
        io.open(os.path.join(out_dir, name), 'w', encoding='utf-8').write(wiz_html)
        book.setdefault('meta', {})['wizard_href'] = name
        # לשונית "הכרעה ואישור" בתוך סביבת העבודה: אותו דף, משובץ, כדי שהכול יהיה במסך אחד
        book['meta']['wizard_doc'] = wiz_html
        made[bid] = name
    if books:
        cur = next((p['id'] for p in data.get('playbooks') or [] if p.get('current')), None)
        if cur in made:
            data['meta']['wizard_href'] = made[cur]
            data['meta']['wizard_doc'] = books[cur]['meta'].get('wizard_doc')
    return made


def main():
    args = sys.argv[1:]
    if '-h' in args or '--help' in args:
        print(__doc__)
        sys.exit(0)
    art = None
    wiz = None
    if '--artifact' in args:
        i = args.index('--artifact'); art = args[i+1]; del args[i:i+2]
    if '--wizard' in args:
        i = args.index('--wizard'); wiz = args[i+1]; del args[i:i+2]
    prof_path = None
    if '--profile' in args:
        i = args.index('--profile'); prof_path = args[i+1]; del args[i:i+2]
    lang = None
    if '--lang' in args:
        i = args.index('--lang'); lang = args[i+1]; del args[i:i+2]
        if lang == 'both':
            lang = None     # "both" הוא שפת הממשק: נקבע מ-display_language בפרופיל, למטה
        elif lang not in ('he', 'en'):
            sys.exit('--lang: he או en')
    if len(args) == 2:
        # בלי תבנית: העותק שנארז בתוסף (אין הורדה מהשרת בזמן ריצה)
        args = [DEFAULT_TEMPLATE] + args
    if len(args) < 3:
        sys.exit(__doc__)
    tpl_path, payload_path, out_path = args[0], args[1], args[2]
    if not wiz:   # אשף ההערות והאישור הוא חלק מהסביבה: בלי --wizard משתמשים בזה שליד התבנית
        _w = os.path.join(os.path.dirname(os.path.abspath(tpl_path)), 'wizard_template.html')
        if os.path.isfile(_w):
            wiz = _w
    # הדף והעמוד המשותף לעולם אינם נכתבים על התבנית, על הנתונים או על מסמך קיים
    try:
        ins = [tpl_path, payload_path, wiz]
        if out_path:
            guard_out(out_path, inputs=ins)
        if art:
            guard_out(art, inputs=ins + [out_path])
    except OutputRefused as exc:
        print('refused: %s' % exc, file=sys.stderr)
        sys.exit(2)
    tpl = load(tpl_path)
    data = json.load(io.open(payload_path, encoding='utf-8'))
    # The template may be an explicit copy in another folder, so look for the vendored
    # library beside the template first and then in this skill's assets folder.
    lib = os.path.join(os.path.dirname(os.path.abspath(tpl_path)), 'chart.umd.js')
    if not os.path.exists(lib):
        lib = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           '..', 'assets', 'chart.umd.js')
        lib = os.path.normpath(lib)
    if not os.path.exists(lib):
        sys.exit('שגיאה: chart.umd.js חסר בתיקיית assets. הספרייה מוטמעת ואינה נטענת מהרשת.')
    chartjs = load(lib)

    meta = data.setdefault('meta', {})
    if not lang and prof_path:
        # בלי --lang: שפת התוצר מהפרופיל, ו-display_language כשהיא both (status.norm_lang מחזיר None ל-both)
        prof = json.load(io.open(prof_path, encoding='utf-8'))
        lang = S.norm_lang(prof.get('deliverable_language')) or S.norm_lang(prof.get('display_language'))
    if lang:
        meta['lang'] = lang
        for b in (data.get('books') or {}).values():
            b.setdefault('meta', {})['lang'] = lang
        # תווית המעמד בשפת הדף (meta.labels נכתב ב-build_workspace_payload.py מאותה גזירה)
        for m_ in [meta] + [b.get('meta') or {} for b in (data.get('books') or {}).values()]:
            lab = (m_.get('labels') or {}).get(lang)
            if lab:
                m_['label_now'] = m_['status_label'] = lab
            comp = (m_.get('company_by_lang') or {}).get(lang)
            if comp:
                m_['company'] = comp
        for p_ in data.get('playbooks') or []:
            book = (data.get('books') or {}).get(p_.get('id')) or {}
            lab = ((book.get('meta') or {}).get('labels') or {}).get(lang)
            if lab:
                p_['status_label'] = lab
    brand_note = apply_theme(data, json.load(io.open(prof_path, encoding='utf-8'))) if prof_path else None
    wizards = build_wizards(load(wiz), data, out_path) if wiz else {}

    def target(d, where):
        d['meta']['publishTarget'] = where
        for b in (d.get('books') or {}).values():
            b.setdefault('meta', {})['publishTarget'] = where
        return d

    if out_path:
        d = target(json.loads(json.dumps(data)), 'local')
        io.open(out_path, 'w', encoding='utf-8').write(localize_shell(inject(tpl, d, chartjs), page_lang(d)))
    if art:
        # עמוד משותף בלי הצהרה על היכולות שהתבנית קוראת להן מקבל null, וההערות נשארות בדפדפן: לא מפרסמים כך
        miss = CAP.missing('workspace', [p for p in (tpl_path, wiz) if p])
        if miss:
            print('העמוד המשותף לא נבנה: התבנית קוראת ל-%s, ואין להן הצהרה (common/capabilities.py)' % ', '.join(miss),
                  file=sys.stderr)
            sys.exit(3)
        d = target(json.loads(json.dumps(data)), 'artifact')
        io.open(art, 'w', encoding='utf-8').write(to_artifact(localize_shell(inject(tpl, d, chartjs), page_lang(d)),
                                                              page_lang(d)))

    mode = (meta.get('docAccess') or {}).get('mode', 'local')
    srcs = data.get('sources') or {}
    linked = sum(1 for k in srcs if (srcs[k] or {}).get('url'))
    print('נבנה %s%s. מצב גישה: %s. מקורות עם קישור: %d מתוך %d. שפת הדף: %s'
          % (out_path, (' ו-'+art) if art else '', mode, linked, len(srcs), page_lang(data)))
    if brand_note:
        print(brand_note)
    if data.get('books'):
        print('פלייבוקים בדף: %d' % len(data['books']))
    for bid, name in wizards.items():
        print('אשף: %s  (%s)' % (name, bid))
    if wiz and art:
        print('בעמוד המשותף: פרסם את קובצי האשף כקבצים נלווים, באותם שמות')
    if art:
        print('בפרסום הראשון של העמוד המשותף העבר capabilities בדיוק כך: %s'
              % json.dumps(CAP.CAPABILITIES['workspace'], ensure_ascii=False))
    print('בדיקה: node --check על מקטע הסקריפט, ואז node scripts/qa_dashboard.js')

if __name__ == '__main__':
    main()
