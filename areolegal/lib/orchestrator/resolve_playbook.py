# -*- coding: utf-8 -*-
"""איתור הפלייבוק בסקריפט אחד ודטרמיניסטי (מימוש ייחוס, הערות הנושא ונותן 4.8, שינוי 73; מרחיב את 48 ו-48א;
4.9, שינוי 83: בלי טבלת סמכויות ובלי מאשר נדרש).

מה חדש מול ההדמיות של סבב 2 (c1b/resolve_playbook.py, c2orch/resolve_playbook.py, resolve_playbook_emul.py):
- מסמך מדיניות כללי של הלקוחה שנגזר מכמה משפחות הסכמים (למשל מנספח מיקור חוץ, מהסכם לקבלן עצמאי ומהסכם
  עבודה), או שנשען על פסיקה, אינו מקור עמדות. הוא נרשם כ"רקע של הלקוחה" (background_documents), ולעולם אינו
  גובר על פלייבוק. פלייבוק של אותה משפחה ואותו צד נבחר לפניו גם כשתנאי ההפעלה של הפלייבוק אינם מתקיימים
  בצד שכנגד הזה (ואז activation_question=True: שאלה אחת, מצב 4, לפי שינוי 52 ו-48א). כשאין פלייבוק בכלל,
  התוצאה no_match, המסלול "אין פלייבוק", והמסמך עובר לרכיב הפלייבוק כרקע.
- דוח סקירה ועותק תצוגה (Workspace, דשבורד) אינם פלייבוק, ואינם מועמדים.
- אין שרשרת אישורים (החלטת מוצר 1, 14.10.2026). טבלת סמכויות שמופיעה במסמך מדיניות אינה נקראת, ואין "מאשר
  נדרש". הכרעה שחוצה קו אדום או יורדת מתחת לנסיגה מוצגת למשתמש כ"נדרשת הכרעתך" באחד מתשעת המצבים, והתשובה שלו
  נרשמת כהכרעת המשתמש (state_builder.record_user_decision).
- כשתנאי ההפעלה של הפלייבוק אינם מתקיימים בצד שכנגד הזה, תווית המקור אינה "מהפלייבוק" אלא "שיקול מקצועי, בהשראת
  פלייבוק של סוג אחר" (source_label), עד שהמשתמש עונה במפורש שהפלייבוק חל.
- פריט אימות של דין בפלייבוק שנפסל נשאר בתוקף לנושא (law_items_carried), ואינו רק חלק מסיבת הפסילה.
- פלייבוק שנבנה בגרסה ישנה (produced_with.skill_version נמוך מהמינימום) מקבל אזהרה.

    from orchestrator.resolve_playbook import resolve
    res = resolve(data_dir, folder, family='services', role='service_recipient', agreement_language='he',
                  counterparty_kind='company')

Python 3, ספרייה סטנדרטית ו-lxml.
"""
import glob
import json
import os
import re
import zipfile

from lxml import etree

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
CASE_LAW = re.compile(r'ע"א|רע"א|בג"ץ|דנ"א|ע"ע|ת"א\s*\d|פס"ד|פסק הדין|הלכת\s|אפרופים|קסטרו|שילה|הפסיקה קבעה')
FAMILY_WORDS = {
    'nda': r'הסכם סודיות|הסכמי סודיות|\bNDA\b|non-disclosure',
    'outsourcing': r'מיקור חוץ',
    'freelance': r'פרילאנס|קבלן עצמאי',
    'employment': r'הסכם(י)? העסקה|חוזה עבודה|הסכם עבודה',
    'distribution': r'הסכם(י)? הפצה|מפיץ',
    'services': r'הסכם(י)? שירות(ים)?|הסכם ייעוץ|שירותי ייעוץ|מקבל(ת)? השירותים|נותן השירותים',
}
# משפחה שהיא תת-סוג של משפחה אחרת לעניין ההתאמה (תנאי ההפעלה מבחינים ביניהן)
FAMILY_GROUP = {'freelance': 'services'}
DERIVATION = re.compile(r'(נבנה|נבנתה|נגזר|נגזרה|מבוסס|מבוססת|על בסיס|מתוך)[^.\n]{0,260}')
ROLE_WORDS = {
    'service_recipient': r'מקבל(ת)? השירותים|מזמינ(ת|ה) השירות',
    'service_provider': r'נותנ(ת)? השירותים|נותני (ה)?שירותים|מבט הספק|פלייבוק ספק|מנקודת מבט הספק',
    'mutual': r'הדדי|mutual',
    'disclosing': r'הצד המגלה|disclosing',
    'receiving': r'הצד המקבל|receiving party',
}
# 1.2.0: אוצר המילים של התפקיד שונה בין הבונה, האינדקס והקורא (customer, service_recipient, buyer...). כל
# תפקיד ממופה לצד כללי אחד, וההשוואה היא בין הצדדים. המשפחה נבדקת בנפרד, ולכן "קונה" ו"שוכר" אינם מתערבבים.
ROLE_SIDE = {}
for _side, _names in {
        'recipient_side': ('customer', 'client', 'service_recipient', 'recipient', 'buyer', 'purchaser', 'licensee',
                           'lessee', 'tenant', 'receiving', 'receiving_party', 'orderer', 'subscriber', 'employer',
                           'principal'),
        'provider_side': ('supplier', 'vendor', 'provider', 'service_provider', 'seller', 'licensor', 'lessor',
                          'landlord', 'contractor', 'disclosing', 'disclosing_party', 'consultant', 'distributor',
                          'employee', 'agent'),
        'mutual': ('mutual', 'both', 'bilateral', 'reciprocal')}.items():
    for _n in _names:
        ROLE_SIDE[_n] = _side


def role_side(role):
    """הצד הכללי של תפקיד (recipient_side / provider_side / mutual), או התפקיד עצמו כשאינו במילון."""
    if not role:
        return role
    key = re.sub(r'[\s\-]+', '_', str(role).strip().lower())
    return ROLE_SIDE.get(key, key)


def same_role(a, b):
    return role_side(a) == role_side(b)


NOT_A_POLICY = re.compile(r'^\s*(דוח|דו"ח|סקירת|סקירה|review|report)', re.I)
RENDERING = re.compile(r'Workspace|דשבורד|dashboard', re.I)
BUILDER_VOLUME = re.compile(r'כרך הנימוקים|הכרך התפעולי|כרך תפעולי')
POLICY_NAME = re.compile(r'מדיניות|פלייבוק|playbook|policy', re.I)


def _docx_text(path):
    try:
        root = etree.fromstring(zipfile.ZipFile(path).read('word/document.xml'))
    except (zipfile.BadZipFile, KeyError, etree.XMLSyntaxError):
        return ''
    return '\n'.join(''.join(t.text or '' for t in p.iter(W + 't')) for p in root.iter(W + 'p'))


def read_text(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == '.docx':
        return _docx_text(path)
    if ext in ('.md', '.txt', '.json', '.html', '.htm'):
        t = open(path, encoding='utf-8', errors='replace').read()
        return re.sub(r'<[^>]+>', ' ', t) if ext.startswith('.htm') else t
    return ''


def families_in(text):
    return {f: len(re.findall(rx, text, re.I)) for f, rx in FAMILY_WORDS.items()}


def family_of(text):
    counts = families_in(text)
    return max(counts, key=counts.get) if any(counts.values()) else 'unknown'


def derivation_families(text):
    """המשפחות שהמסמך אומר שנגזר מהן ("נבנה על בסיס נספח מיקור חוץ, הסכם לקבלן עצמאי והסכם עבודה")."""
    fams = set()
    for m in DERIVATION.finditer(text):
        for f, rx in FAMILY_WORDS.items():
            if f != 'services' and re.search(rx, m.group(0), re.I):
                fams.add(f)
    return fams


def side_of(text):
    """הצד שהמסמך נכתב בשבילו. הכותרת (300 התווים הראשונים) שוקלת פי שלושה מההמשך."""
    head, title = text[:1500], text[:300]
    counts = {r: 3 * len(re.findall(rx, title, re.I)) + len(re.findall(rx, head, re.I)) for r, rx in ROLE_WORDS.items()}
    best = max(counts, key=counts.get)
    return best if counts[best] else None


def classify_document(text):
    derived = derivation_families(text)
    dates = re.findall(r'\b(\d{1,2})\.(\d{1,2})\.(20\d\d)\b', text) + \
        [(d, mo, y) for y, mo, d in re.findall(r'\b(20\d\d)-(\d\d)-(\d\d)\b', text[:600])]
    date = max(('%s-%02d-%02d' % (y, int(mo), int(d)) for d, mo, y in dates), default='')
    first = [ln for ln in text.split('\n') if ln.strip()][:3]
    return {'family': family_of(text[:3000]), 'derived_from': sorted(derived), 'mixed_family': len(derived) >= 2,
            'cites_case_law': bool(CASE_LAW.search(text)), 'side': side_of(text), 'date': date,
            'not_a_policy': any(NOT_A_POLICY.search(ln) for ln in first)}


def _same_family(a, b):
    return FAMILY_GROUP.get(a, a) == FAMILY_GROUP.get(b, b)


def _conditions_text(conds):
    """activation_conditions may be a string, a list of strings, or a list of objects
    (e.g. {"condition": ..., "deciding_question": ...}). Flatten all of them to text."""
    if not conds:
        return ''
    if isinstance(conds, str):
        return conds
    if isinstance(conds, dict):
        conds = [conds]
    parts = []
    for c in conds:
        if isinstance(c, dict):
            parts.extend(str(v) for v in c.values() if isinstance(v, (str, int, float)))
        else:
            parts.append(str(c))
    return ' '.join(parts)


def _activation_share(model, counterparty_kind):
    rules = (model or {}).get('rules', [])
    if not rules:
        return 0.0
    miss = 0
    for r in rules:
        conds = _conditions_text(r.get('activation_conditions'))
        if counterparty_kind == 'company' and re.search(r'יחיד|individual|sole', conds):
            miss += 1
        elif counterparty_kind == 'individual' and re.search(r'תאגיד|חברה בע"מ|corporate', conds):
            miss += 1
    return miss / len(rules)


def _version_tuple(v):
    return tuple(int(x) for x in re.findall(r'\d+', str(v or '0')))


def _builder_candidate(core_path, data_dir, family, role, counterparty_kind, entry=None, legacy=False,
                       min_skill_version=None, agreement_family_label=None):
    core = json.load(open(core_path, encoding='utf-8'))
    model_path = os.path.join(os.path.dirname(core_path), 'playbook-model.json')
    model = json.load(open(model_path, encoding='utf-8')) if os.path.exists(model_path) else core
    entry = entry or {}
    scope = model.get('scope_summary') or {}
    names = [entry.get('family_name', ''), ' '.join(entry.get('family_aliases', [])), str(core.get('family_name', ''))]
    names += [f.get('contract_family_name', '') for f in scope.get('contract_families', [])]
    cand_family = core.get('family_code') or entry.get('family_code') or family_of(' '.join(names))
    side = entry.get('company_role_code') or core.get('company_role_code') or side_of(str(scope.get('company_role', '')))
    language = entry.get('language') or core.get('output_language') or model.get('output_language')
    excluded = []
    if not _same_family(cand_family, family):
        excluded.append('other_family')
    if not same_role(side, role):
        excluded.append('mutuality_mismatch' if 'mutual' in (role_side(side), role_side(role)) else 'opposite_side')
    not_cov = [(x.get('kind') or x.get('label') or str(x)) if isinstance(x, dict) else str(x)
               for x in (core.get('applicability') or {}).get('not_covered', [])]
    if agreement_family_label and any(agreement_family_label in n for n in not_cov):
        excluded.append('not_covered')
    share = _activation_share(model, counterparty_kind)
    warnings = []
    pw = core.get('produced_with') or {}
    if min_skill_version and _version_tuple(pw.get('skill_version')) < _version_tuple(min_skill_version):
        warnings.append('built_with_older_version')
    queue = model.get('validation_queue', []) or core.get('validation_queue', [])
    return {'path': os.path.relpath(core_path, data_dir), 'form': 'builder_json', 'legacy_root': legacy,
            'family': cand_family, 'side': side, 'language': language,
            'date': entry.get('last_updated') or core.get('last_updated') or model.get('last_updated', ''),
            'status': core.get('playbook_status'), 'activation_ok': share < 0.5, 'activation_share': share,
            'not_covered': not_cov, 'excluded_because': excluded, 'warnings': warnings, 'validation_queue': queue}


def _client_documents(folder, uploaded):
    docs = []
    for root, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if d != 'Areo-נתונים' and not d.startswith('.')]
        for f in files:
            if POLICY_NAME.search(f) and os.path.splitext(f)[1].lower() in ('.docx', '.md', '.txt', '.html', '.htm'):
                docs.append(os.path.join(root, f))
    if uploaded:
        docs.append(uploaded)
    return docs


def resolve(data_dir, folder, family, role, agreement_language, counterparty_kind='company', uploaded=None,
            min_skill_version=None, agreement_family_label=None):
    cands, seen = [], set()
    index = os.path.join(data_dir, 'playbooks', 'index.json')
    if os.path.exists(index):
        for e in json.load(open(index, encoding='utf-8')).get('playbooks', []):
            rel = e.get('core_path') or e.get('path')   # 1.2.0: שתי הצורות של האינדקס, בלי KeyError
            if not rel:
                continue
            core = os.path.join(data_dir, rel)
            if os.path.isdir(core):
                core = os.path.join(core, 'playbook-core.json')
            if os.path.exists(core):
                seen.add(os.path.normcase(os.path.abspath(core)))
                cands.append(_builder_candidate(core, data_dir, family, role, counterparty_kind, e, bool(e.get('legacy')),
                                                min_skill_version, agreement_family_label))
    for core in glob.glob(os.path.join(data_dir, 'playbooks', '*', 'playbook-core.json')) + \
            [os.path.join(data_dir, 'playbook-core.json')]:
        k = os.path.normcase(os.path.abspath(core))
        if k in seen or not os.path.exists(core):
            continue
        seen.add(k)
        cands.append(_builder_candidate(core, data_dir, family, role, counterparty_kind, legacy=True,
                                        min_skill_version=min_skill_version, agreement_family_label=agreement_family_label))
    background = []
    for p in _client_documents(folder, uploaded):
        text = read_text(p)
        if not text.strip():
            continue
        c = classify_document(text)
        rel = os.path.basename(p) if p == uploaded else os.path.relpath(p, folder)
        cand = {'path': rel, 'form': 'client_document', 'family': c['family'], 'side': c['side'],
                'language': 'he' if re.search(r'[֐-׿]', text) else 'en', 'date': c['date'],
                'mixed_family': c['mixed_family'], 'derived_from': c['derived_from'], 'activation_ok': True,
                'cites_case_law': c['cites_case_law'], 'excluded_because': [], 'warnings': [], 'validation_queue': []}
        builder_dates = {b['date'] for b in cands if b['form'] == 'builder_json' and _same_family(b['family'], c['family'])}
        if RENDERING.search(os.path.basename(p)) or BUILDER_VOLUME.search(text[:1500]) or \
                (c['date'] and c['date'] in builder_dates):
            cand['excluded_because'].append('rendering_only')  # עותק תצוגה של פלייבוק שכבר מועמד
        elif c['not_a_policy'] or NOT_A_POLICY.search(os.path.basename(p)):
            cand['excluded_because'].append('not_a_policy')
        elif c['mixed_family'] or c['cites_case_law']:
            reason = 'mixed_family_background' if c['mixed_family'] else 'case_law_background'
            cand['excluded_because'].append(reason)
            background.append({'path': rel, 'reason': reason, 'date': c['date'], 'derived_from': c['derived_from'],
                               'cites_case_law': c['cites_case_law']})
        if not _same_family(c['family'], family):
            cand['excluded_because'].append('other_family')
        if c['side'] and not same_role(c['side'], role):
            cand['excluded_because'].append('mutuality_mismatch' if 'mutual' in (role_side(c['side']), role_side(role))
                                            else 'opposite_side')
        cands.append(cand)
    valid = [c for c in cands if not c['excluded_because']]
    # דירוג: (1) תחולה, כולל תנאי ההפעלה; (2) שפת ההסכם; (3) תאריך. מסמך רקע אינו בדירוג בכלל.
    valid.sort(key=lambda c: (c['activation_ok'], c['language'] == agreement_language, c['date'] or ''), reverse=True)
    chosen = valid[0] if valid else None
    if chosen:
        for c in valid[1:]:
            if not c['activation_ok'] and chosen['activation_ok']:
                c['excluded_because'].append('activation_mismatch')
            elif c['language'] != agreement_language:
                c['excluded_because'].append('other_language')
            else:
                c['excluded_because'].append('older')
    law_items = []
    for c in cands:
        c['chosen'] = c is chosen
        queue = c.pop('validation_queue', [])
        if c is chosen:
            continue
        c['open_items_on_rejection'] = [q.get('id') for q in queue]
        for q in queue:
            if re.search(r'חוק|דין|תקנות|\blaw\b', json.dumps(q, ensure_ascii=False)):
                law_items.append({'from': c['path'], 'id': q.get('id'), 'question': q.get('question'),
                                  'rule_id': q.get('rule_id')})
    warnings = sorted({w for c in cands for w in c.get('warnings', [])})
    if chosen:
        result = 'match'
        reason = 'נבחר לפי משפחה, צד, תחולה, שפה ותאריך: %s' % chosen['path']
    else:
        result = 'no_match'
        reason = 'אין פלייבוק להסכם הזה ולצד הזה. ' + (
            'מסמכי מדיניות כלליים של הלקוחה משמשים רקע בלבד: %s' % ', '.join(b['path'] for b in background)
            if background else 'אין מסמך רקע.')
    return {'result': result, 'chosen': chosen['path'] if chosen else '', 'reason': reason,
            'activation_question': bool(chosen and not chosen['activation_ok']),
            'agreement_language': agreement_language, 'candidates': cands, 'background_documents': background,
            'law_items_carried': law_items, 'warnings': warnings}


def source_label(resolution, activation_answer_kind=None):
    """תווית המקור לטבלת "לאישורך". מסמך רקע לעולם אינו "מהפלייבוק".
    כשתנאי ההפעלה של הפלייבוק שנבחר אינם מתקיימים (activation_question), התווית היא "מהפלייבוק" רק אחרי תשובה
    מפורשת שהפלייבוק חל (activation_answer_kind == 'explicit'). תשובה כללית ("תפעלו לפי הפלייבוק") אינה מחילה
    התאמות לפלייבוק של סוג אחר (4.9, שינוי 83)."""
    if resolution['result'] == 'match':
        if resolution.get('activation_question') and activation_answer_kind != 'explicit':
            return 'שיקול מקצועי, בהשראת פלייבוק של סוג אחר'
        return 'מהפלייבוק'
    if resolution['background_documents']:
        b = resolution['background_documents'][0]
        return 'ממסמך מדיניות שמעמדו לא נבדק (%s), רקע בלבד' % (b.get('date') or 'בלי תאריך')
    return 'שיקול מקצועי'
