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
- כשתנאי ההפעלה של הפלייבוק אינם מתקיימים בצד שכנגד הזה, תווית המקור (source_label) אומרת זאת, עד שהמשתמש עונה
  במפורש שהפלייבוק חל: "מפלייבוק מוצע, שלא נבנה מול צד שכנגד מסוג זה: כל סטייה מסומנת" כשהפלייבוק שנבחר הוא
  בהתאמה מלאה למשפחה ולצד (S1d-R2, 28.10.2026: התווית "בהשראת פלייבוק של סוג אחר" הודפסה גם בהתאמה מלאה). "שיקול
  מקצועי, בהשראת פלייבוק של סוג אחר" רק כשהמועמד שנבחר אינו בהתאמה מלאה.
- פריט אימות של דין בפלייבוק שנפסל נשאר בתוקף לנושא (law_items_carried), ואינו רק חלק מסיבת הפסילה.
- פלייבוק שנבנה בגרסה ישנה (produced_with.skill_version נמוך מהמינימום) מקבל אזהרה.
- 1.3.0 (ביקורת כלליות, ממצאים 1, 3, 4): המשפחה מתקבלת כקוד, שם או כינוי, בעברית או באנגלית, ומושווית
  לשמות ולכינויים של הפלייבוקים הקיימים בלבד, בלי מילון. משפחה שאינה מוכרת אינה עצירה: בלי
  התאמה התוצאה no_match. התפקיד הוא טקסט חופשי, בלי מילון תפקידים; other, צד שאינו מזוהה, מסמך שלא נקרא והתאמת
  שם לא ודאית מחזירים choose ("לבחירה") עם שאלה אחת, ולא התאמה אוטומטית. PDF ו-Excel של הלקוח נקראים לזיהוי,
  ומסמך שלא נקרא חוזר כמועמד עם read_with.

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
try:
    from common.case_law import case_law_mentions
except ImportError:  # pragma: no cover
    case_law_mentions = lambda text: []   # noqa: E731
# אין בקוד רשימת משפחות הסכם ואין מילון תפקידים. המשפחה של מסמך נגזרת בזמן ריצה מהכותרת שלו ומשם הקובץ של הלקוח
# (family_of), והתפקיד הוא טקסט חופשי בלשון המסמכים (role_code). משפחה או תפקיד שאין להם התאמה ודאית: "לבחירה",
# שאלה אחת, ולא התאמה אוטומטית. אין "צד נותן" ו"צד מקבל" שנגזרים ממילון.
DERIVATION = re.compile(r'(נבנה|נבנתה|נגזר|נגזרה|מבוסס|מבוססת|על בסיס|מתוך|derived from|based on)[^.\n]{0,260}', re.I)
MUTUAL_WORDS = re.compile(r'הדדי(ת)?|mutual|bilateral|reciprocal|^both$', re.I)
# ביטוי של נקודת מבט ("מנקודת המבט של X", "X's perspective", "playbook of X"): X הוא התפקיד, כלשון המסמך
PERSPECTIVE = re.compile(r"(?:מנקודת המבט של|מבט של|בצד|פלייבוק (?:של )?)\s*(?:ה)?([֐-׿\"״']{2,20}(?: [֐-׿\"״']{2,20})?)|"
                         r"\b([A-Za-z][A-Za-z\- ]{2,24}?)(?:'s)?[\s\-](?:perspective|side|view|playbook)\b|"
                         r"from the ([A-Za-z][A-Za-z\- ]{2,24}?)(?:'s)? (?:perspective|side|view)", re.I)
CLEAR_SIDES = ('mutual',)


def _role_key(text):
    t = re.sub(r'[\s_\-]+', ' ', str(text or '').strip().lower()).strip(' .,:;"\'״')
    if t.startswith('ה') and len(t) > 3:
        t = t[1:]
    return t.replace(' ', '_')


def role_code(text):
    """מפתח מנורמל של תפקיד שנכתב בעברית או באנגלית, בלי מילון: הטקסט עצמו, באותיות קטנות, בלי "ה" הידיעה.
    other, ריק או לא מזוהה: None או 'other'. הדדי: 'mutual'."""
    if not text or not str(text).strip():
        return None
    if MUTUAL_WORDS.search(str(text)):
        return 'mutual'
    return _role_key(text) or None


def role_side(role):
    """הצד של תפקיד להשוואה: 'mutual' להדדי, ואחרת המפתח המנורמל של הטקסט. אין מיפוי לצד "נותן" או "מקבל"."""
    return role_code(role) if role else role


def same_role(a, b):
    return role_side(a) == role_side(b)


def _script(key):
    return 'he' if re.search(r'[֐-׿]', key or '') else 'en'


def side_status(cand_side, role):
    """same / mutuality_mismatch / unclear. same: אותו תפקיד בדיוק (אחרי נרמול). הדדי מול שאינו הדדי:
    mutuality_mismatch. כל השאר, כולל שני תפקידים שונים או בשתי שפות: unclear. פלייבוק במצב unclear אינו נבחר
    אוטומטית: הוא חוזר "לבחירה" עם שאלה. אין קביעה אוטומטית ש"הצד הזה הוא הצד שכנגד"."""
    rs, cs = role_side(role), role_side(cand_side)
    if rs in CLEAR_SIDES or cs in CLEAR_SIDES:
        if rs == cs:
            return 'same'
        if rs and cs:
            return 'mutuality_mismatch'
        return 'unclear'
    if rs and cs and rs == cs and rs != 'other':
        return 'same'
    return 'unclear'


def _norm_name(s):
    return re.sub(r'\s+', ' ', re.sub(r'[\W_]+', ' ', str(s or '').lower())).strip()


_NAME_STOP = {'הסכם', 'הסכמי', 'חוזה', 'נספח', 'agreement', 'agreements', 'contract', 'the', 'of', 'and', 'for', 'a'}


def family_keys(*names):
    '''(שמות מנורמלים, קבוצת משפחות ריקה) לרשימת שמות. אין מילון משפחות: ההתאמה היא לשם, לא למשפחה במילון.'''
    exact = set()
    for n in names:
        t = _norm_name(n)
        if t:
            exact.add(t)
    return exact, set()


def family_match(requested, cand_names):
    """exact (אותו שם או קוד), family (אותה משפחה במילון), partial (חפיפת מילים בלבד, לא ודאי), או None."""
    r_exact, r_canon = requested
    c_exact, c_canon = family_keys(*cand_names)
    if r_exact & c_exact:
        return 'exact'
    if r_canon & c_canon:
        return 'family'
    if not r_canon:
        r_tok = {w for t in r_exact for w in t.split()} - _NAME_STOP
        for t in c_exact:
            c_tok = set(t.split()) - _NAME_STOP
            if r_tok and c_tok and (r_tok <= c_tok or c_tok <= r_tok):
                return 'partial'
    return None


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
    # 1.3.0 (ממצא 3): PDF ו-Excel נקראים לזיהוי המשפחה והצד. העמדות עצמן נקראות ב-read_playbook_doc.py.
    # PDF סרוק, או Excel בלי openpyxl, מחזירים '' והמסמך חוזר כמועמד "לא נקרא", ולא נעלם.
    if ext == '.pdf':
        try:
            from risk.page_text import pdf_text
            with open(path, 'rb') as fh:
                return pdf_text(fh.read())
        except Exception:  # noqa: BLE001  PdfTextUnavailable, ספרייה חסרה או קובץ פגום: לא נקרא
            return ''
    if ext in ('.xlsx', '.xlsm'):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
            rows = [' | '.join(str(c) for c in r if c is not None) for ws in wb.worksheets
                    for r in ws.iter_rows(values_only=True)]
            return '\n'.join(r for r in rows if r)
        except Exception:  # noqa: BLE001
            return ''
    return ''


def title_of(text):
    '''הכותרת של מסמך: השורה הראשונה הלא ריקה, מנורמלת וקצרה. זו המשפחה כפי שהמסמך עצמו קורא לה.'''
    for ln in (text or '').split(chr(10)):
        if ln.strip():
            return _norm_name(ln)[:60] or 'unknown'
    return 'unknown'


def family_of(text):
    '''המשפחה כשם: כותרת המסמך (או שם הקובץ). אין זיהוי לפי מילון; בלי כותרת: 'unknown'.'''
    return title_of(text)


def derivation_families(text):
    '''המסמכים שהמסמך אומר שנגזר מהם ("נבנה על בסיס X, Y ו-Z"): שלושה פריטים או יותר שכל אחד מהם נקרא הסכם או נספח.'''
    out = set()
    for m in DERIVATION.finditer(text):
        items = re.split(r',|;| ו(?=[֐-׿])|\band\b', m.group(0))
        items = [_norm_name(x) for x in items if re.search(r'הסכם|נספח|agreement|addendum|contract', x, re.I)]
        if len(items) >= 3:
            out.update(items)
    return out


def side_of(text):
    '''הצד שהמסמך נכתב בשבילו, לפי ביטוי של נקודת מבט בכותרת או בפתיח (PERSPECTIVE), כלשון המסמך. None כשאין.'''
    head = (text or '')[:1500]
    m = PERSPECTIVE.search(head[:300]) or PERSPECTIVE.search(head)
    if m:
        return role_code(next(g for g in m.groups() if g))
    return role_code('mutual') if MUTUAL_WORDS.search(head[:300]) else None


def classify_document(text):
    derived = derivation_families(text)
    dates = re.findall(r'\b(\d{1,2})\.(\d{1,2})\.(20\d\d)\b', text) + \
        [(d, mo, y) for y, mo, d in re.findall(r'\b(20\d\d)-(\d\d)-(\d\d)\b', text[:600])]
    date = max(('%s-%02d-%02d' % (y, int(mo), int(d)) for d, mo, y in dates), default='')
    first = [ln for ln in text.split('\n') if ln.strip()][:3]
    return {'family': family_of(text[:3000]), 'derived_from': sorted(derived), 'mixed_family': len(derived) >= 2,
            'cites_case_law': bool(case_law_mentions(text)), 'side': side_of(text), 'date': date,
            'not_a_policy': any(NOT_A_POLICY.search(ln) for ln in first)}


def _same_family(a, b):
    '''אותו שם משפחה (אחרי נרמול), או חפיפת מילים מלאה של אחד בשני.'''
    ta, tb = set(_norm_name(a).split()) - _NAME_STOP, set(_norm_name(b).split()) - _NAME_STOP
    return bool(ta and tb and (ta <= tb or tb <= ta))


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


# תנאי ההפעלה של הפלייבוק מול סוג הצד שכנגד (הרצה S1c, 28.10.2026: applicability החריג "גופים ציבוריים ומוסדות
# שמציגים נייר משלהם", הצד שכנגד היה גוף ציבורי, והפלייבוק הוחל בלי activation_ok ובלי שאלה). counterparty_kind הוא
# סוג הישות, לפי אוצר המילים האחד של playbook-schema.md (applicability): public_body, university, non_profit,
# government_company, foreign, large_enterprise, sme, consumer ו-individual, וגם company ו-group. אפשר כמה ערכים בפסיק
# (למשל "university,foreign"). ערך שאינו במילון נזרק, ולכן כל ערך בסכמה וכל כינוי מוכר ממופה כאן (non_profit לא נבדק
# בכלל עד 28.10.2026)
ENTITY_KINDS = {'company': 'company', 'corporate': 'company', 'individual': 'individual', 'person': 'individual',
                'public_body': 'public_body', 'public': 'public_body', 'government': 'public_body',
                'municipality': 'public_body', 'university': 'university', 'academic': 'university',
                'non_profit': 'non_profit', 'npo': 'non_profit', 'nonprofit': 'non_profit', 'non-profit': 'non_profit',
                'charity': 'non_profit', 'government_company': 'government_company', 'foreign': 'foreign',
                'large_enterprise': 'large_enterprise', 'large': 'large_enterprise', 'enterprise': 'large_enterprise',
                'sme': 'sme', 'small': 'sme', 'consumer': 'consumer', 'group': 'group', 'partnership': 'partnership'}
KIND_ATTRIBUTES = {'foreign', 'large_enterprise', 'sme'}
# סוג שהוא גם סוג רחב יותר: מוסד ציבורי הוא גם גוף ציבורי, וחברה ממשלתית וחברה בקבוצה הן גם חברה
KIND_PARENTS = {'university': {'public_body'}, 'government_company': {'company', 'public_body'},
                'group': {'company'}, 'large_enterprise': {'company'}, 'sme': {'company'}, 'consumer': {'individual'}}
NOT_COVERED_BY_KIND = {
    'public_body': re.compile(r'ציבורי|ממשלת|רשות מקומית|מוסד|public|government|authorit|institution|municipal', re.I),
    'university': re.compile(r'אוניברסיט|מוסד להשכלה|אקדמ|universit|academic|higher education', re.I),
    'individual': re.compile(r'אדם יחיד|יחידים|individual|natural person', re.I),
    'consumer': re.compile(r'צרכנ|consumer', re.I),
    'non_profit': re.compile(r'עמות|מלכ"ר|חל"צ|הקדש|ללא כוונת רווח|non-?profit|charit', re.I),
    'government_company': re.compile(r'חברה ממשלתית|government compan', re.I),
    'foreign': re.compile(r'צד זר|חברה זרה|foreign', re.I),
    'large_enterprise': re.compile(r'תאגיד גדול|large enterprise', re.I),
    'sme': re.compile(r'עסק קטן|קטן או בינוני|\bSMEs?\b', re.I),
}


# שאלה בתור ההכרעות על העמדה מול סוג צד (ולא, למשל, על מעמד המסמכים): "איזו עמדה תחול", "פער כיסוי", "סגמנט"
OPEN_POSITION_Q = re.compile(r'עמד[הת]|פער כיסוי|סגמנט|position|coverage gap|segment', re.I)


KIND_NAMES = {'he': {'company': 'חברות', 'individual': 'אנשים יחידים', 'public_body': 'גופים ציבוריים',
                     'university': 'אוניברסיטאות', 'non_profit': 'עמותות', 'government_company': 'חברות ממשלתיות',
                     'foreign': 'צדדים זרים', 'large_enterprise': 'תאגידים גדולים', 'sme': 'עסקים קטנים ובינוניים',
                     'consumer': 'צרכנים', 'group': 'חברות בקבוצה', 'partnership': 'שותפויות'},
              'en': {'company': 'companies', 'individual': 'individuals', 'public_body': 'public bodies',
                     'university': 'universities', 'non_profit': 'non-profits', 'government_company': 'government companies',
                     'foreign': 'foreign parties', 'large_enterprise': 'large enterprises', 'sme': 'SMEs',
                     'consumer': 'consumers', 'group': 'group companies', 'partnership': 'partnerships'}}


def _entity_kinds(counterparty_kind):
    raw = counterparty_kind if isinstance(counterparty_kind, (list, tuple)) else str(counterparty_kind or '').split(',')
    return {ENTITY_KINDS[k.strip().lower()] for k in raw if k and k.strip().lower() in ENTITY_KINDS}


def _with_parents(kinds):
    out = set(kinds)
    for k in kinds:
        out |= KIND_PARENTS.get(k, set())
    return out


def _entry_kinds(x):
    """סוגי הצד ברשומה של not_observed או not_covered: kind מהמילון, ואחרת לפי הטקסט (label, kind)."""
    if isinstance(x, dict):
        k = str(x.get('kind') or '').strip().lower()
        text = ' '.join(str(x.get(f) or '') for f in ('kind', 'label'))
    else:
        k, text = str(x).strip().lower(), str(x)
    if k in ENTITY_KINDS:
        return {ENTITY_KINDS[k]}
    return {kind for kind, rx in NOT_COVERED_BY_KIND.items() if rx.search(text)}


def activation_check(core, model, counterparty_kind):
    """(activation_ok, reasons): applicability.counterparty_kinds של הפלייבוק מול סוג הצד שכנגד, applicability.not_observed
    (ורשומה ישנה ב-not_covered שנוקבת בסוג צד), ותנאי ההפעלה של הכללים (_activation_share). reasons: [{'code', 'text',
    'recommendation'}]. activation_ok=false אינו מוציא את הפלייבוק מהבחירה: הוא שאלה אחת עם שני כפתורים."""
    app = (core or {}).get('applicability') or (model or {}).get('applicability') or {}
    kinds = _entity_kinds(counterparty_kind)
    reasons = []
    allowed = {ENTITY_KINDS.get(str(k).lower(), str(k).lower()) for k in app.get('counterparty_kinds') or ()}
    # כל סוג ישות של הצד צריך כיסוי (גוף גדול וזר: כל התכונות שלו). זר, גדול וקטן הם תכונות, ונבדקים רק
    # כשהפלייבוק נוקב בתכונה כזו
    full_allowed = _with_parents(allowed)
    check = {k for k in kinds if k not in KIND_ATTRIBUTES or allowed & KIND_ATTRIBUTES}
    missing = {k for k in check if not (_with_parents({k}) & full_allowed)}
    if kinds and allowed and not ({'any', 'all'} & allowed) and missing:
        he = lambda ks: ', '.join(KIND_NAMES['he'].get(k, k) for k in sorted(ks))  # noqa: E731
        en = lambda ks: ', '.join(KIND_NAMES['en'].get(k, k) for k in sorted(ks))  # noqa: E731
        reasons.append({'code': 'counterparty_kind_not_covered',
                        'text': 'הפלייבוק נבנה מול %s, והצד שכנגד מסוג %s' % (he(allowed), he(missing)),
                        'text_en': 'the playbook was built for %s, and the counterparty is %s' % (en(allowed), en(missing)),
                        'recommendation': ''})
    # not_observed[]: סוג צד שלא נצפה בקורפוס. רשומה ישנה ב-not_covered שנוקבת בסוג צד נקראת כמוה (playbook-schema.md).
    # התוצאה היא activation_ok=false ושאלה אחת במנת השאלות, ולעולם לא "לא להחיל": אין מצב עבודה בלי פלייבוק
    observed_not = list(app.get('not_observed') or ()) + [x for x in app.get('not_covered') or () if _entry_kinds(x)]
    full = _with_parents(kinds)
    for x in observed_not:
        hit = _entry_kinds(x) & full
        if hit:
            label = (x.get('label') if isinstance(x, dict) else '') or 'לא נצפה בקורפוס'
            he_k = ', '.join(KIND_NAMES['he'].get(k, k) for k in sorted(hit))
            en_k = ', '.join(KIND_NAMES['en'].get(k, k) for k in sorted(hit))
            reasons.append({'code': 'not_observed', 'kinds': sorted(hit), 'text': '%s: %s' % (he_k, label),
                            'text_en': '%s: not observed in the corpus' % en_k,
                            'recommendation': (x.get('recommendation') or '') if isinstance(x, dict) else ''})
    # שאלה פתוחה בתור ההכרעות של הפלייבוק (validation_queue, scope: playbook) שאומרת שאין עדיין עמדה מול סוג הצד הזה
    # (פער כיסוי): גם כשהסוג רשום ב-counterparty_kinds, הפלייבוק עוד לא קבע איך הוא חל מולו, ולכן זו אותה שאלה אחת
    for q in (model or {}).get('validation_queue') or (core or {}).get('validation_queue') or ():
        if not isinstance(q, dict) or q.get('answered') or q.get('status') == 'closed':
            continue
        if q.get('scope') != 'playbook':
            continue
        text = '%s %s' % (q.get('topic') or '', q.get('question') or '')
        if not OPEN_POSITION_Q.search(text):
            continue
        hit = {k for k, rx in NOT_COVERED_BY_KIND.items() if rx.search(text)} & full
        if hit:
            he_k = ', '.join(KIND_NAMES['he'].get(k, k) for k in sorted(hit))
            en_k = ', '.join(KIND_NAMES['en'].get(k, k) for k in sorted(hit))
            reasons.append({'code': 'open_question', 'kinds': sorted(hit), 'question_id': q.get('id'),
                            'question': q.get('question') or '',
                            'text': 'בפלייבוק פתוחה שאלה על %s: %s' % (he_k, str(q.get('question') or q.get('topic')).rstrip('?. ')),
                            'text_en': 'an open question in the playbook about %s (%s)' % (en_k, q.get('id') or ''),
                            'recommendation': q.get('recommendation') or ''})
    share = _activation_share(model, counterparty_kind)
    if share >= 0.5:
        reasons.append({'code': 'rule_conditions', 'text': 'תנאי ההפעלה של %d%% מהכללים אינם מתקיימים בצד שכנגד הזה'
                        % int(round(share * 100)), 'text_en': 'the activation conditions of %d%% of the rules are '
                        'not met for this counterparty' % int(round(share * 100)), 'recommendation': ''})
    return not reasons, reasons


def _version_tuple(v):
    return tuple(int(x) for x in re.findall(r'\d+', str(v or '0')))


def _builder_candidate(core_path, data_dir, family, role, counterparty_kind, entry=None, legacy=False,
                       min_skill_version=None, agreement_family_label=None):
    core = json.load(open(core_path, encoding='utf-8'))
    model_path = os.path.join(os.path.dirname(core_path), 'playbook-model.json')
    model = json.load(open(model_path, encoding='utf-8')) if os.path.exists(model_path) else core
    entry = entry or {}
    scope = model.get('scope_summary') or {}
    families = [f for f in list(scope.get('contract_families') or []) + list(core.get('contract_families') or [])
                if isinstance(f, dict)]
    req = (model.get('meta') or {}).get('build_request') or {}
    names = [entry.get('family_name', ''), str(core.get('family_name', '')), req.get('family_label') or '']
    names += list(entry.get('family_aliases') or []) + list(req.get('family_aliases') or [])
    for f in families:
        names += [f.get('contract_family_name', '')] + list(f.get('family_aliases') or [])
    codes = [core.get('family_code'), entry.get('family_code'), core.get('family_id'), entry.get('family_id'),
             model.get('family_code'), model.get('family_id')]
    cand_family = core.get('family_code') or entry.get('family_code') or family_of(' '.join(n for n in names if n))
    if cand_family == 'unknown':
        cand_family = core.get('family_id') or entry.get('family_id') or cand_family
    side = entry.get('company_role_code') or core.get('company_role_code') or \
        next((f.get('company_role_code') for f in families if f.get('company_role_code')), None) or \
        side_of(str(scope.get('company_role', '')))
    language = entry.get('language') or core.get('output_language') or model.get('output_language')
    excluded = []
    fam = family_match(family, [n for n in names + codes if n])
    if not fam:
        excluded.append('other_family')
    st = side_status(side, role)
    if st in ('opposite', 'mutuality_mismatch'):
        excluded.append('mutuality_mismatch' if st == 'mutuality_mismatch' else 'opposite_side')
    # not_covered הוא רק סוג עסקה. רשומה שנוקבת בסוג צד אינה מחריגה: היא not_observed (activation_check)
    not_cov = [(x.get('kind') or x.get('label') or str(x)) if isinstance(x, dict) else str(x)
               for x in (core.get('applicability') or {}).get('not_covered', []) if not _entry_kinds(x)]
    if agreement_family_label and any(agreement_family_label in n for n in not_cov):
        excluded.append('not_covered')
    share = _activation_share(model, counterparty_kind)
    act_ok, act_reasons = activation_check(core, model, counterparty_kind)
    warnings = []
    pw = core.get('produced_with') or {}
    if min_skill_version and _version_tuple(pw.get('skill_version')) < _version_tuple(min_skill_version):
        warnings.append('built_with_older_version')
    queue = model.get('validation_queue', []) or core.get('validation_queue', [])
    return {'path': os.path.relpath(core_path, data_dir), 'form': 'builder_json', 'legacy_root': legacy,
            'family': cand_family, 'side': side, 'language': language, 'family_match': fam,
            'side_unclear': st == 'unclear',
            'date': entry.get('last_updated') or core.get('last_updated') or model.get('last_updated', ''),
            'status': core.get('playbook_status'), 'activation_ok': act_ok, 'activation_share': share,
            'activation_reasons': act_reasons,
            'not_covered': not_cov, 'excluded_because': excluded, 'warnings': warnings, 'validation_queue': queue,
            **_status_fields(model, model_path if model is not core else None, core, entry)}


def _status_fields(model, model_path, core, entry):
    """התווית של שער המדיניות (playbook/status.gate_status), הפער מול הגרעין והאינדקס, והמשפט המתוסרט על פלייבוק
    מוצע, שנגזר מהנתונים (proposed_notice). הנושא ונותן מציג את התווית הזו, ולא את מה שנשמר בגרעין או באינדקס."""
    try:
        from playbook import status as S
        gap = S.label_gap(model, model_path, core=core, index_entry=entry or None)
    except Exception:          # מודל חלקי: אין תווית מחושבת, והרכיב אומר "מעמד הפלייבוק לא נקרא"
        return {}
    label, mismatch = basis_guard(core, gap['label'], list(gap['mismatch'] or []))
    return {'status_label': label, 'label_mismatch': mismatch, 'stored_labels': gap['stored'],
            'proposed_notice': proposed_notice(model) if is_proposed_status(gap['playbook_status']) else None}


COMPANY_BASIS_CODES = ('own', 'mixed')
NON_COMPANY_TRACK_BASES = ('market_standard', 'areo_proposal')


def company_backed_rules(core):
    """כמה כללים בגרעין נשענים במסלול כלשהו על מסמך של החברה (basis שאינו שוק ואינו הצעת Areo), וכמה אינם."""
    backed = total = 0
    for c in (core or {}).get('clauses') or (core or {}).get('rules') or []:
        if not isinstance(c, dict):
            continue
        total += 1
        tl = c.get('traffic_light') if isinstance(c.get('traffic_light'), dict) else c
        bases = [((tl.get(t) or {}).get('basis') if isinstance(tl.get(t), dict) else None) for t in ('green', 'yellow', 'red')]
        if any(b and b not in NON_COMPANY_TRACK_BASES for b in bases):
            backed += 1
    return backed, total


def basis_guard(core, label, mismatch):
    """תווית המעמד מהבסיס האמיתי של המסלולים (סקירת ארכיטקטורה 30.10.2026, כשל 7; עו"ד, נספח 5): תווית שאומרת
    "מבוסס הסכמי החברה" (own/mixed) כשאף כלל בגרעין אינו נשען על מסמך של החברה מוחלפת בתווית "הצעת Areo" (או
    "מחקר שוק" כשהבסיס היה mixed), ו-label_mismatch מקבל 'basis_vs_tracks'. הנושא ונותן מציג את התווית המתוקנת."""
    if not label or not core:
        return label, mismatch
    try:
        from playbook import status as S
        code, lang, _old = S.code_of_label(label)
    except Exception:  # noqa: BLE001
        return label, mismatch
    if not code or not any(code.startswith(p) for p in COMPANY_BASIS_CODES):
        return label, mismatch
    backed, total = company_backed_rules(core)
    if total == 0 or backed > 0:
        return label, mismatch
    fixed = S.LABELS[lang]['market' if code.startswith('mixed') else 'areo']
    return fixed, list(mismatch) + ['basis_vs_tracks:0/%d company-backed rules' % total]


# המשפט על פלייבוק מוצע (n3-decisions.md, "החלה של פלייבוק מוצע"), לפי מעמד המאגר ולפי מצב מחקר השוק בפועל.
# בהרצה S1c (28.10.2026) נאמר "מההסכמים של החברה וממחקר שוק" כשמחקר לא בוצע, על נוסחים שהחברה מציגה ללקוחותיה
NOTICE_DOCS = {
    'he': {'signed': 'ההסכמים של החברה', 'mostly_drafts': 'מסמכים של החברה (רובם טיוטות ולא הסכמים חתומים)',
           'company_forms': 'נוסחים שהחברה מציגה לצד שכנגד (לא הסכמים חתומים)',
           'third_party_forms': 'נוסחים שאינם הסכמים חתומים של החברה',
           'unknown': 'נוסחים שאינם הסכמים חתומים של החברה'},
    'en': {'signed': "the company's agreements",
           'mostly_drafts': 'company documents (most of them drafts, not signed agreements)',
           'company_forms': 'forms the company presents to its counterparties (not signed agreements)',
           'third_party_forms': 'forms that are not signed agreements of the company',
           'unknown': 'forms that are not signed agreements of the company'},
}
NOTICE_TXT = {
    'he': {'lead': 'העמדות בעסקה הזו באות מטיוטת מדיניות שסוכן הפלייבוק הכין מ%s%s. ',
           'market_only': 'מחקר שוק בלבד, בלי הסכמים של החברה מהסוג הזה',
           'performed': ' וממחקר שוק', 'partial': ' וממחקר שוק חלקי',
           'declined': ', בלי מחקר שוק (החברה בחרה שלא לשלב אותו)', 'none': ', בלי מחקר שוק',
           'tail': 'היא מחכה לאישור שלכם. המקורות שלה מפורטים ברשימת המקורות: %s.', 'where': '<המיקום>'},
    'en': {'lead': 'The positions in this deal come from a draft policy that the playbook agent prepared from %s%s. ',
           'market_only': 'market research only, without company agreements of this type',
           'performed': ' and market research', 'partial': ' and partial market research',
           'declined': ', without market research (the company chose not to include it)',
           'none': ', without market research',
           'tail': "It awaits your approval. Its sources are listed in the source list: %s.", 'where': '<location>'},
}


def research_state(model):
    """מצב מחקר השוק בפועל: performed, partial, declined או none (market_research.status, not_performed_reason
    ו-asks[].answer). ממצא שוק שהלקוחה בחרה לכלול (uses_market) הוא מחקר שבוצע גם כשהמעמד לא נכתב."""
    from playbook import status as S
    mr = model.get('market_research') or {}
    st = str(mr.get('status') or '')
    if st in ('Performed', 'Completed'):
        return 'performed'
    if st == 'Partial':
        return 'partial'
    if not st and S.uses_market(model):
        return 'performed'
    if st == 'Declined' or 'declin' in str(mr.get('not_performed_reason') or '') or \
            any(isinstance(x, dict) and x.get('answer') == 'no' for x in mr.get('asks') or ()):
        return 'declined'
    return 'none'


def proposed_notice(model, location=None):
    """המשפט המתוסרט על פלייבוק מוצע, בעברית ובאנגלית: {'he', 'en', 'corpus_status', 'research'}. נגזר מ-corpus_status
    (אותה גזירה כמו התווית ושורת הבסיס) וממצב המחקר בפועל. "ממחקר שוק" נאמר רק כשמחקר בוצע."""
    from playbook import status as S
    cs, rs = S.corpus_status(model), research_state(model)
    market_only = S.base_code(model) == 'market'
    out = {'corpus_status': cs, 'research': 'market_only' if market_only else rs}
    for lang in ('he', 'en'):
        t = NOTICE_TXT[lang]
        if market_only:
            src, extra = t['market_only'], ''
        else:
            src, extra = NOTICE_DOCS[lang].get(cs) or NOTICE_DOCS[lang]['signed'], t[rs]
        # בלי מיקום ידוע אין מציין מקום במשפט שנאמר ללקוח: המשפט מפנה לרשימת המקורות של המדיניות עצמה
        tail = t['tail'] % location if location else t['tail'].split(':')[0] + '.'
        out[lang] = (t['lead'] % (src, extra)) + tail
    return out


CLIENT_DOC_EXT = ('.docx', '.md', '.txt', '.html', '.htm', '.pdf', '.xlsx', '.xlsm')
TOOL_READ = 'scripts/read_playbook_doc.py'


def _client_documents(folder, uploaded):
    docs, seen = [], set()
    for root, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if d != 'Areo-נתונים' and not d.startswith('.')]
        for f in files:
            # 1.3.0 (ממצא 3): גם PDF ו-Excel, כמו ש-SKILL.md מתיר
            if POLICY_NAME.search(f) and os.path.splitext(f)[1].lower() in CLIENT_DOC_EXT:
                docs.append(os.path.join(root, f))
                seen.add(os.path.normcase(os.path.abspath(docs[-1])))
    if uploaded and os.path.normcase(os.path.abspath(uploaded)) not in seen:
        docs.append(uploaded)
    return docs


def _describe(c):
    return '%s (משפחה %s, צד %s%s)' % (c['path'], c.get('family') or 'לא ידועה', c.get('side') or 'לא ידוע',
                                     ', עדכון %s' % c['date'] if c.get('date') else '')


def resolve(data_dir, folder, family, role, agreement_language, counterparty_kind='company', uploaded=None,
            min_skill_version=None, agreement_family_label=None):
    """family: קוד, שם או כינוי, בעברית או באנגלית. role: קוד או שם של תפקיד. התוצאה: match, choose או no_match.
    1.3.0 (ממצאים 1, 3, 4): משפחה שאינה במילון מושווית לשמות הפלייבוקים, ובלי התאמה התוצאה no_match. צד
    other, צד שאינו מזוהה, מסמך שלא נקרא והתאמת שם לא ודאית אינם נבחרים אוטומטית: התוצאה choose, עם שאלה אחת."""
    requested = family_keys(family)
    if not requested[1] and agreement_family_label:
        requested = (requested[0], family_keys(agreement_family_label)[1])
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
                cands.append(_builder_candidate(core, data_dir, requested, role, counterparty_kind, e,
                                                bool(e.get('legacy')), min_skill_version, agreement_family_label))
    for core in glob.glob(os.path.join(data_dir, 'playbooks', '*', 'playbook-core.json')) + \
            [os.path.join(data_dir, 'playbook-core.json')]:
        k = os.path.normcase(os.path.abspath(core))
        if k in seen or not os.path.exists(core):
            continue
        seen.add(k)
        cands.append(_builder_candidate(core, data_dir, requested, role, counterparty_kind, legacy=True,
                                        min_skill_version=min_skill_version, agreement_family_label=agreement_family_label))
    background = []
    for p in _client_documents(folder, uploaded):
        text = read_text(p)
        ext = os.path.splitext(p)[1].lower()
        rel = os.path.basename(p) if p == uploaded else os.path.relpath(p, folder)
        if not text.strip():
            if ext not in ('.pdf', '.xlsx', '.xlsm', '.docx') and p != uploaded:
                continue
            # 1.3.0 (ממצא 3): מסמך שלא נקרא אינו נעלם. הוא מועמד "לא נקרא", לקריאה בכלי, ואינו נבחר אוטומטית.
            # המשפחה אינה ידועה; רק שם קובץ שמציין במפורש משפחה אחרת פוסל אותו (family_source: file_name).
            hint = _norm_name(os.path.splitext(os.path.basename(p))[0])
            cand = {'path': rel, 'form': 'client_document', 'family': 'unknown', 'side': None, 'language': None,
                    'date': '', 'unread': True, 'read_with': TOOL_READ, 'family_hint': hint, 'activation_ok': True,
                    'excluded_because': [], 'warnings': ['unread_client_document'], 'validation_queue': []}
            cands.append(cand)
            continue
        c = classify_document(text)
        cand = {'path': rel, 'form': 'client_document', 'family': c['family'], 'side': c['side'],
                'language': 'he' if re.search(r'[֐-׿]', text) else 'en', 'date': c['date'],
                'mixed_family': c['mixed_family'], 'derived_from': c['derived_from'], 'activation_ok': True,
                'cites_case_law': c['cites_case_law'], 'read_with': TOOL_READ, 'excluded_because': [], 'warnings': [],
                'validation_queue': []}
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
        # המשפחה של מסמך נקבעת מהכותרת שלו, בלי מילון: התאמה חלקית בלבד, ולעולם לא "exact" של שם פלייבוק
        fam = None
        if any(len(t) >= 4 and t in _norm_name(text[:1500]) for t in requested[0]):
            fam = 'partial'   # השם שהמשתמש נתן מופיע בכותרת: לא ודאי, לכן לבחירה
        cand['family_match'] = fam
        if not fam:
            cand['excluded_because'].append('other_family')
        st = side_status(c['side'], role)
        if st in ('opposite', 'mutuality_mismatch'):
            cand['excluded_because'].append('mutuality_mismatch' if st == 'mutuality_mismatch' else 'opposite_side')
        cand['side_unclear'] = st == 'unclear'
        cands.append(cand)
    valid = [c for c in cands if not c['excluded_because']]
    # 1.3.0: נבחר אוטומטית רק מועמד שהמשפחה שלו ודאית, הצד שלו ידוע, והוא נקרא. השאר "לבחירה".
    auto = [c for c in valid if c.get('family_match') in ('exact', 'family') and not c.get('side_unclear')
            and not c.get('unread')]
    pending = [c for c in valid if c not in auto]
    exact_codes = {_norm_name(c['family']) for c in auto
                   if c['form'] == 'builder_json' and c.get('family_match') == 'exact'}
    if exact_codes:
        # המשתמש נתן את השם או הקוד של פלייבוק מסוים: פלייבוק אחר של הבונה באותה משפחה כללית הוא סוג אחר
        for c in auto:
            if c['form'] == 'builder_json' and _norm_name(c['family']) not in exact_codes:
                c['excluded_because'].append('other_family')
        auto = [c for c in auto if not c['excluded_because']]
    # דירוג: (1) תחולה, כולל תנאי ההפעלה; (2) שפת ההסכם; (3) תאריך. מסמך רקע אינו בדירוג בכלל.
    rank = lambda c: (c['activation_ok'], c['language'] == agreement_language, c['date'] or '')  # noqa: E731
    auto.sort(key=rank, reverse=True)
    pending.sort(key=rank, reverse=True)
    builder_codes = {_norm_name(c['family']) for c in auto if c['form'] == 'builder_json'}
    chosen, choices, question = None, [], ''
    if len(builder_codes) >= 2:
        # (ה) כמה משפחות של הבונה מתאימות לשם: אין הכרעה בין משפחות שונות לפי התאריך
        choices = auto
        question = 'נמצאו כמה פלייבוקים שמתאימים ל"%s" ולצד הזה: %s. איזה מהם חל על ההסכם? המלצה: %s.' % (
            family, '; '.join(_describe(c) for c in auto), auto[0]['path'])
    elif auto:
        chosen = auto[0]
        for c in auto[1:]:
            if not c['activation_ok'] and chosen['activation_ok']:
                c['excluded_because'].append('activation_mismatch')
            elif c['language'] != agreement_language:
                c['excluded_because'].append('other_language')
            else:
                c['excluded_because'].append('older')
        for c in pending:
            c['excluded_because'].append('unread' if c.get('unread') else
                                         'side_unclear' if c.get('side_unclear') else 'family_uncertain')
    elif pending:
        choices = pending
        parts = []
        unread = [c for c in pending if c.get('unread')]
        side_q = [c for c in pending if not c.get('unread') and c.get('side_unclear')]
        fam_q = [c for c in pending if not c.get('unread') and not c.get('side_unclear')]
        if side_q:
            parts.append('הצד של החברה בהסכם ("%s"), או הצד שהפלייבוק נכתב בשבילו, אינו מזוהה, ולכן אין התאמה '
                         'אוטומטית: %s. מה הצד של החברה בהסכם הזה, והאם הפלייבוק נכתב לאותו צד?'
                         % (role, '; '.join(_describe(c) for c in side_q)))
        if fam_q:
            parts.append('ההתאמה בין "%s" לבין שם הפלייבוק אינה ודאית: %s. האם זה אותו סוג הסכם?'
                         % (family, '; '.join(_describe(c) for c in fam_q)))
        if unread:
            parts.append('המסמך %s לא נקרא (למשל PDF סרוק, או Excel בלי openpyxl). קראו אותו ב-%s, וקבעו את '
                         'המשפחה והצד שלו.' % (', '.join(c['path'] for c in unread), TOOL_READ))
        question = ' '.join(parts)
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
    elif choices:
        result = 'choose'
        reason = 'לבחירה: ' + question
    else:
        result = 'no_match'
        reason = 'אין פלייבוק להסכם הזה ולצד הזה. ' + (
            'מסמכי מדיניות כלליים של הלקוחה משמשים רקע בלבד: %s' % ', '.join(b['path'] for b in background)
            if background else 'אין מסמך רקע.')
    return {'result': result, 'chosen': chosen['path'] if chosen else '', 'reason': reason,
            'activation_question': bool(chosen and not chosen['activation_ok']),
            # תנאי ההפעלה של הפלייבוק שנבחר, תמיד נכתבים (מעריך הסיכונים קורא אותם מ-playbook_resolution בקובץ המצב).
            # activation_ok: false הוא שאלה אחת במנת השאלות, מצב 4 (round_tools.py questions --resolution)
            'activation_ok': bool(chosen['activation_ok']) if chosen else None,
            'activation_reason': '; '.join(r['text'] for r in chosen.get('activation_reasons') or ()) if chosen else '',
            'activation_reasons': list(chosen.get('activation_reasons') or ()) if chosen else [],
            'counterparty_kind': counterparty_kind,
            'playbook_status': chosen.get('status') if chosen else None,
            # התווית של שער המדיניות, פער מול הגרעין והאינדקס, והמשפט על פלייבוק מוצע (ממצאים 1 ו-5, הרצה S1c)
            'status_label': chosen.get('status_label') if chosen else None,
            'label_mismatch': chosen.get('label_mismatch') or [] if chosen else [],
            'proposed_notice': chosen.get('proposed_notice') if chosen else None,
            'choices': [c['path'] for c in choices], 'question': question,
            'requested_family': {'names': sorted(requested[0]), 'families': sorted(requested[1])},
            'agreement_language': agreement_language, 'candidates': cands, 'background_documents': background,
            'law_items_carried': law_items, 'warnings': warnings}


# מעמד של פלייבוק שעדיין אינו מדיניות מאושרת: התווית היא "מפלייבוק מוצע", ולא "מהפלייבוק" (באג 7, הרצה S1b)
PROPOSED_STATUSES = ('draft', 'inferred', 'proposed', 'provisional', 'suggested', 'partiallyapproved')
# מעמד מאושר: הקוד Approved (playbook/status.STATUS_APPROVED), מעמד תא approved או approved_modified, או תווית שער
# המדיניות שפותחת ב"מדיניות מאושרת" / "Approved policy". כל מעמד אחר שנרשם (Draft, PartiallyApproved, תווית של פלייבוק
# מוצע או אושר בחלקו) הוא פלייבוק מוצע
APPROVED_STATUSES = ('approved', 'approved_modified')
APPROVED_LABEL_PREFIXES = ('מדיניות מאושרת', 'approved policy')


# --------------------------------------------------------------------------- סוג הנייר: מכרז, תנאים מקוונים, משא ומתן
# סימנים כלליים, בעברית ובאנגלית, לכל גוף ציבורי ובכל מדינה. הקוד מציע סוג נייר; המשתמש מאשר בשאלה מפורשת
# (question_batch, kind: paper_type), והתשובה נרשמת ב-meta.paper_type (round_tools.py paper-type --set).
PAPER_TENDER = re.compile(
    r"מכרז(?: פומבי| סגור)? (?:מס'|מס׳|מספר)|הזמנה להציע הצעות|ועדת (?:ה)?מכרזים|(?<![א-ת])ה?מציע(?:ים)?(?![א-ת])|"
    r"שאלות (?:ה)?הבהרה|מועד אחרון להגשת|הגשת (?:ה)?הצעות|עורך המכרז|מסמכי המכרז|"
    r"invitation to tender|\bITT\b|request for (?:proposals?|quotations?|tenders?)|\bRF[PQ]\b|\btenderers?\b|"
    r"\bbidders?\b|clarification (?:questions|requests)|deadline for (?:the )?(?:receipt|submission) of (?:tenders|bids|"
    r"proposals)|contracting authority|procurement procedure|tender documents", re.I)
PAPER_AWARD = re.compile(
    r"זכ(?:ה|תה|ו) במכרז|הזוכה במכרז|הצע(?:ת|תו|תה) (?:ה)?זוכה|הודעת (?:ה)?זכייה|זכתה ואושרה|זכה ואושר|"
    r"מסמכי המכרז (?:יגברו|הם חלק|מהווים חלק)|successful (?:tenderer|bidder)|notice of award|awarded (?:the|this) "
    r"(?:contract|tender)|following the award|(?:the )?tender documents (?:shall prevail|form part)", re.I)
PAPER_PUBLIC = re.compile(
    r"משרד (?:ה)?[א-ת]+|(?<![א-ת])ה?רשות (?:ה)?[א-ת]+|עיריי?ת|מועצה (?:מקומית|אזורית)|"
    r"חברה ממשלתית|ministry|municipal|county council|city council|public (?:body|authority|sector)|"
    r"government|federal|state agency|contracting authority", re.I)
# תנאים מקוונים: רק אישור בלחיצה. "terms of service" לבדו מופיע בהסכמים רבים ואינו סימן
PAPER_ONLINE = re.compile(r"by clicking|click(?:ing)? (?:on )?\W?(?:I )?(?:accept|agree)|clickwrap|click-wrap|"
                          r"by (?:accessing|using) the (?:service|website|platform)[^.]{0,40}you agree|"
                          r"בלחיצה על|בסימון התיבה|בעצם השימוש באתר", re.I)
PAPER_SIGNED = re.compile(r"in witness whereof|signature|signed by|duly authori[sz]ed|ולראיה באו הצדדים|חתימת|"
                          r"\bby:\s|name:\s|title:\s", re.I)


def detect_paper_type(paragraphs):
    """הצעה לסוג הנייר מתוך הטקסט: {'suggested', 'signals': {tender, award, public, online}, 'confident'}.
    הקודים tender_pre_bid / tender_awarded הם קודי ממשק פנימיים של "נייר של הליך תחרותי של גוף ציבורי" (לפני הגשה /
    אחרי זכייה), שנשארו כמו שהם בשל רכיבים אחרים שקוראים אותם. האותות מבניים (הזמנה להציע הצעות, מציע, גוף מזמין),
    ואין רשימת גופים בשמם. tender_awarded: סימני זכייה וסימני הליך תחרותי או גוף ציבורי;
    tender_pre_bid: שני סימני הליך תחרותי ומעלה, בלי זכייה;
    standard_form_online: תנאים מקוונים; אחרת negotiable. ההצעה אינה החלטה: המשתמש מאשר."""
    text = "\n".join(p or "" for p in paragraphs)
    sig = {k: sorted({m.group(0).strip() for m in rx.finditer(text)})[:6]
           for k, rx in (("tender", PAPER_TENDER), ("award", PAPER_AWARD), ("public", PAPER_PUBLIC),
                         ("online", PAPER_ONLINE))}
    if sig["award"] and (sig["tender"] or sig["public"]):
        sug = "tender_awarded"
    elif len(sig["tender"]) >= 2:
        sug = "tender_pre_bid"
    elif sig["online"] and not sig["tender"] and not PAPER_SIGNED.search(text):
        sug = "standard_form_online"
    else:
        sug = "negotiable"
    confident = (sug == "negotiable" and not any(sig[k] for k in ("tender", "award", "online"))) or         (sug == "tender_awarded" and len(sig["award"]) + len(sig["tender"]) >= 2) or         (sug == "tender_pre_bid" and len(sig["tender"]) >= 3) or (sug == "standard_form_online" and len(sig["online"]) >= 2)
    # כשהזיהוי אינו בטוח אין המלצה כלל (סקירת ארכיטקטורה 30.10.2026, כשל 1; user-B #9): השאלה נשאלת עם המשפט
    # "הזיהוי אינו ודאי", והמשתמש בוחר. המלצה על "הסכם רגיל" כשהנייר הוא חוזה של הליך תחרותי הייתה הכשל
    return {"suggested": sug, "signals": sig, "confident": confident,
            "recommended": sug if confident else None}


# כמויות עם יחידה, להשוואת העובדות שהמשתמש מסר לנוסח (שטח, תקופה, כמות). תקופה מושווית בחודשים
_QTY_UNITS = (
    ("area", r'מ"ר|מ״ר|מטר(?:ים)? רבוע(?:ים)?|m2|m²|sq\.? ?m|square met(?:re|er)s?|sq\.? ?ft|square feet', 1),
    ("months", r"חודשים|חודש|months?", 1),
    ("months", r"שנים|שנה|years?", 12),
    ("units", r"יחידות|משתמשים|רישיונות|units|users|licen[cs]es|seats", 1),
)
_QTY_RX = [(cls, re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(?:-|\s)?\s*(?:" + u + r")(?![א-תA-Za-z])", re.I), mult)
           for cls, u, mult in _QTY_UNITS]


def quantities(text):
    """[(class, value)] של כמויות עם יחידה בטקסט."""
    out = []
    for cls, rx, mult in _QTY_RX:
        for m in rx.finditer(text or ""):
            try:
                out.append((cls, float(m.group(1).replace(",", "")) * mult))
            except ValueError:
                pass
    return out


def facts_mismatch(facts, paragraphs):
    """עובדות שהמשתמש מסר (deal_context.facts, או מחרוזות) שאינן תואמות את הנוסח: כמות עם יחידה (שטח, תקופה, כמות)
    שהנוסח נוקב באותה יחידה בערך אחר, וערך העובדה אינו מופיע בו. מחזיר [{'fact', 'unit', 'fact_value',
    'draft_values'}]. למשל <כמות> בעובדות מול <כמות אחרת> במסמך."""
    draft = {}
    for cls, v in quantities("\n".join(p or "" for p in paragraphs)):
        draft.setdefault(cls, set()).add(v)
    out = []
    for f in facts or ():
        txt = f.get("fact") if isinstance(f, dict) else str(f)
        for cls, v in quantities(txt or ""):
            have = draft.get(cls)
            if have and v not in have:
                out.append({"fact": txt, "unit": cls, "fact_value": v, "draft_values": sorted(have)[:6]})
    return out


def is_approved_status(status):
    s = str(status or '').strip()
    return s.lower() in APPROVED_STATUSES or s.lower().startswith(APPROVED_LABEL_PREFIXES)


def is_proposed_status(status):
    """האם מעמד הפלייבוק (playbook_status בגרעין או בקובץ המצב, מחרוזת או dict) הוא פלייבוק מוצע: כל מעמד שנרשם
    ואינו מאושר (is_approved_status), כולל PartiallyApproved. מעמד שלא נרשם כלל אינו נקבע כאן (False)."""
    if isinstance(status, dict):
        by = status.get('rules_by_status') or {}
        if by and any(not is_approved_status(k) for k in by):
            return True
        return any(is_proposed_status(status.get(k)) for k in ('playbook', 'status', 'code', 'status_label')
                   if status.get(k))
    s = str(status or '').strip()
    return bool(s) and not is_approved_status(s)


LABELS = {'he': {'pb': 'מהמדיניות שלכם', 'proposed': 'מטיוטת המדיניות', 'other': 'שיקול מקצועי, בהשראת פלייבוק של סוג אחר',
                 'choose': 'טרם נבחר פלייבוק: ממתין לבחירת המשתמש',
                 'background': 'ממסמך מדיניות שמעמדו לא נבדק (%s), רקע בלבד', 'no_date': 'בלי תאריך',
                 'prof': 'שיקול מקצועי', 'activation': ', שלא נבנה מול צד שכנגד מסוג זה: כל סטייה מסומנת'},
          'en': {'pb': 'From your policy', 'proposed': 'From the draft policy',
                 'activation': ', which was not built for this type of counterparty: every deviation is flagged',
                 'other': 'Professional judgment, inspired by a playbook of another type',
                 'choose': 'No playbook chosen yet: awaiting your choice',
                 'background': 'From a policy document whose status was not checked (%s), background only',
                 'no_date': 'undated', 'prof': 'Professional judgment'}}


def source_label(resolution, activation_answer_kind=None, lang='he', playbook_status=None):
    """תווית המקור לטבלת "לאישורך". מסמך רקע לעולם אינו "מהפלייבוק".
    כשתנאי ההפעלה של הפלייבוק שנבחר אינם מתקיימים (activation_question), התווית היא "מהפלייבוק" רק אחרי תשובה
    מפורשת שהפלייבוק חל (activation_answer_kind == 'explicit'). תשובה כללית ("תפעלו לפי הפלייבוק") אינה מחילה
    התאמות לפלייבוק של סוג אחר (4.9, שינוי 83). פלייבוק במעמד Draft, Inferred או "מוצע" (המעמד של המועמד שנבחר,
    או playbook_status שנמסר): "מטיוטת המדיניות" (EN: "From the draft policy"); מאושר: "מהמדיניות שלכם"."""
    t = LABELS['en' if str(lang or '').lower()[:2] == 'en' else 'he']
    if resolution['result'] == 'match':
        chosen = next((c for c in resolution.get('candidates') or [] if c.get('chosen')), {})
        base = t['proposed'] if (is_proposed_status(playbook_status) or is_proposed_status(chosen.get('status'))
                                 or is_proposed_status(resolution.get('playbook_status'))) else t['pb']
        if resolution.get('activation_question') and activation_answer_kind != 'explicit':
            # S1d-R2 (28.10.2026): הפלייבוק שנבחר הוא מאותה משפחה ומאותו צד; רק סוג הצד שכנגד לא נצפה בקורפוס.
            # "בהשראת פלייבוק של סוג אחר" רק כשהמועמד שנבחר אינו בהתאמה מלאה למשפחה ולצד
            if chosen and (chosen.get('family_match') in (None, False, '') or chosen.get('side_unclear')):
                return t['other']
            return base + t['activation']
        return base
    if resolution['result'] == 'choose':
        return t['choose']
    if resolution['background_documents']:
        b = resolution['background_documents'][0]
        return t['background'] % (b.get('date') or t['no_date'])
    return t['prof']
