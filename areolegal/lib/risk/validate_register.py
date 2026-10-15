# -*- coding: utf-8 -*-
"""risk/validate_register.py: הבדיקה הממוחשבת של risk-register.json לפני בניית הדוח.

מחליף את contract-risk-assessor/scripts/validate_data.py שבחבילה, שבסבב 2 דחה מרשמים תקינים
(24 שגיאות ב-C1ב, 40 ב-C2: שש עדשות, category, why_dangerous_together). מאחד את שתי ההדמיות של סבב 2
(C1ב: risk_c1b_r2/validate_v34.py; C2: c2risk/validate_fixed.py) לכלל אחד, ומוסיף את כללי הערות 3.5:
  - תקציב עמודים: אורך מרבי לכל תא שמוצג (LIMITS), ותבנית אחת להפניה לסעיף (clause_ref_ok).
  - ויתור מכוון: סיכון שנובע מוויתור שהנושא ונותן רשם הוא "סיכון שהתקבל", ואינו ברשימת "לתיקון".
  - מספור סעיפים: כל שורה ב"לתיקון" נושאת state_clause_id מקובץ המצב של העסקה, וההפניה תואמת
    ל-numbering_map של קובץ המצב (מספור התגובה שלנו, הערות הנושא ונותן 4.8); text_status זהה לזה שבקובץ המצב;
    ויתור מכוון נקרא מ-deliberate_concessions[] (clause_ref, report_as: "accepted_risk").
  - הסכם הדדי: side חובה בכל סיכון.
  - מעמד הפלייבוק: benchmark_status נגזר ממעמד אחד (playbook/status.py, derive_status).
  - עדכניות חוק: מקור שנוסחו קודם לתיקון ידוע אינו "ודאות גבוהה". רשימת התיקונים היא נתון שמגיע מבחוץ
    (known_amendments, --amendments), לא קבוע בקוד.
  - עובדה שהפרופיל קובע (רגולטור במעמד Confirmed, פעילות, מסחר בבורסה) אינה "הנחה לאישור".
  - דוח חקר ישות: validate_entity_report() (התאמת שם, ממצא חוסם, why חובה, כתובות בלי טוקנים).
ונוסף בהערות 3.6 (סבב 3). כל כלל כאן כללי לכל סוג הסכם ולכל לקוח (החלטה 22, כלל 2.26): אין בקוד חוק,
תיקון, רגולטור או סוג הסכם מסוים; מה שתלוי בסוג ההסכם או בלקוח מגיע בזמן ריצה מהפרופיל, מקובץ המצב או מנתון חיצוני.
  - עותק גולמי ב-PDF נקרא דרך שכבת הטקסט (risk/page_text.py), או דרך raw_copies[].text_file; גרשיים בתוך
    מילה עברית ("התשע"ז") אינם גבול של ציטוט. אותו נרמול לציטוטים מההסכם.
  - ויתור מכוון: clause_ref הוא מזהה סעיף מקובץ המצב (לא מזהה כלל), וכל ויתור מופיע כסיכון שהתקבל.
  - החלטה 1 (14.10.2026): אין שרשרת אישורים. סיכון שהתקבל הוא הכרעת המשתמש: אין שדה אישור, אין
    "ממתין לאישור" ואין שם של מאשר.
  - חוזה הלולאה לפני משלוח: pre_send_fixes[] עם id, clause_ref (מזהה סעיף מ-numbering_map) ו-status
    (open | resolved | accepted_as_concession); סיכון שהתגובה יצרה נכנס לרשימה בלי קשר לחומרה.
  - חותמת זמן עם שעה: ISO מלא עם היסט; search_log עם user_agent של Areo בלבד.
  - playbook_resolution מקובץ המצב: כשתנאי ההפעלה אינם מתקיימים, אין סימון פלייבוק.

שימוש:
  python -I validate_register.py <risk-register.json> [--corpus corpus.json] [--deal DIR]
         [--state negotiation_state.json] [--profile פרופיל-לקוח.json] [--playbook-status status.json]
         [--entity entity-report.json] [--out report.json]
         (גרסה 1.2.0: כל הקלט קריאה בלבד; --out אופציונלי, רק לדוח השגיאות, ולעולם לא קובץ קלט)
קוד יציאה 1 על כל שגיאה. ספרייה סטנדרטית בלבד.
"""
import hashlib
import html as _html
import io
import json
import os
import re
import sys

if __name__ == '__main__':
    sys.dont_write_bytecode = True   # הרצה משורת הפקודה אינה כותבת __pycache__ לתוך החבילה

try:  # הרצה כחבילה (pytest) או כקובץ בודד
    from .entity_store import has_secret
    from .page_text import PdfTextUnavailable, decode_page, excerpt_in, norm, page_text  # noqa: F401
except ImportError:  # pragma: no cover
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from entity_store import has_secret
    from page_text import PdfTextUnavailable, decode_page, excerpt_in, norm, page_text  # noqa: F401
try:
    from common.cli import guard_out, parser, run, write_json
    from common.net import client_detail_in_query
    from common.terms import terms_re
except ImportError:  # pragma: no cover
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from common.cli import guard_out, parser, run, write_json
    from common.net import client_detail_in_query
    from common.terms import terms_re

LENS8 = ['legal', 'financial', 'operational', 'technology', 'regulatory', 'reputational', 'insurance', 'force_majeure']
KINDS = {'clause', 'silence', 'vague_term', 'back_to_back', 'external', 'hidden_text', 'untracked_change'}
META_KEYS = {'company', 'scope', 'transaction_id', 'party_terms', 'scope_label', 'source_ref', 'source_version',
             'annexes_reviewed', 'annexes_missing', 'deal_value', 'generated_at', 'last_updated', 'docAccess',
             'publishTarget', 'branding', 'display_language', 'prepared_for_counsel', 'user_focus', 'counterparty',
             'document_title', 'position', 'mutual_primary_role', 'playbook_ref', 'benchmark_status'}
RISK_KEYS = {'id', 'risk_no', 'kind', 'name', 'description', 'hidden_text', 'primary_lens', 'lens', 'inherent',
             'severity_level', 'controls', 'residual', 'exposure', 'scenario', 'critical_detail', 'anchors',
             'treatment_direction', 'playbook_flag', 'certainty', 'external_source_ids', 'side', 'decision',
             'drafted_by', 'regulatory_basis', 'created_by_response'}
FORBIDDEN_RISK = {'mitigation', 'feasibility_basis', 'leverage_window', 'owner', 'mitigation_channel', 'category',
                  'estimated_amount', 'ratio_to_deal_value'}
DEF_TYPES = {'contradiction', 'ambiguity', 'missing_annex', 'missing_agreement', 'undefined_term', 'inconsistent_term',
             'broken_reference', 'precedence_missing', 'version_mismatch', 'language_mismatch', 'leftover_text',
             'blank_field', 'unilateral_document', 'cumulative_requirement'}
TEXT_STATUS = {'agreed', 'counterparty_draft', 'our_unsent_response', 'our_sent_response'}
APPROVED_DOMAINS = ('nevo.co.il', 'knesset.gov.il', 'gov.il', 'boi.org.il', 'data.gov.il', 'justice.gov.il',
                    'tase.co.il', 'isa.gov.il', 'magna.isa.gov.il', 'sec.gov', 'treas.gov', 'un.org', 'europa.eu',
                    'gov.uk', 'service.gov.uk', 'delaware.gov')
BLOCKED_PHRASES = ['תוחלת נזק', 'סיכון מצטבר', 'תיאבון סיכון', 'אינו ייעוץ משפטי', 'מודל שפה', 'קו אדום',
                   'חבילת ויתורים', 'חלון מינוף', 'ישימות', 'אם הצד השני ידחה', 'ודאית', 'מהיום הראשון', 'אין בקרה',
                   'מופר', 'הפרנו', 'לא נעמוד', 'לא תקוים', 'אינה ניתנת לקיום', 'לחץ פנימי', 'יודע ש',
                   'עמדת נסיגה', 'פלייבוק באחוזים', 'להתעקש', 'לדרוש', 'הצד שכנגד יטען', 'אומדן', 'משוער',
                   'חלוקת השווי']
CODE_RE = re.compile(r'\b(?:R-?\d{2}|Q\d+|V-\d+|REG\d+|SEG-\d+|APR-\d+|RSK-\d+|DEF-\d+|CMB-\d+|ENT-\d+|SRC-\d+)\b'
                     r'|כלל \d|\bסבב \d|\b(?:ILS|NIS|USD|EUR)\b|\d+\s*[xX×]\s*\d+')
SKIP_TEXT = re.compile(r'(\.id$|_id$|\.file$|source_ref$|source_version|\.logo$|\.url$|typed_url|final_url|\.sha256|'
                       r'risk_ids|\.lens(\[\d+\])?$|\.kind$|\.type$|\.status$|\.combo_id|\.currency|primary_lens|'
                       r'playbook_flag|certainty|drafted_by|\.mode$|\.role$|urlSource|text_status|sign_as_is|\.label$|'
                       r'\.result$|\.prevails$|missing_identifiers|\.question\[\d+\]|external_source_ids|transaction_id|'
                       r'\.scope$|display_language|benchmark_status|\.saved_at|\.at$|\.date$|defined_at|generated_at|'
                       r'last_updated|set_at|offered_at|\.country$|\.excerpt$|search_log|raw_copies|\.query|'
                       r'state_clause_id|regulatory_basis|\.basis$|version_date|\.side$|docAccess|deal_value\.source)')

# ---- תקציב העמודים: אורך מרבי בתווים לכל תא שמוצג (הערות 3.5, ההרחבה של שינוי 1). ----
LIMITS = {
    'risks[].name': 70, 'risks[].treatment_direction': 70, 'risks[].anchors[].clause': 30,
    'pre_send_fixes[].gap': 80, 'pre_send_fixes[].where': 30,
    'summary.bottom_line[]': 160, 'summary.deal_one_line': 100,
    'summary.key_dates[].what': 45, 'summary.key_dates[].consequence': 45, 'summary.key_dates[].window': 40,
    'summary.key_dates[].clause': 30,
    'document_defects[].topic': 25, 'document_defects[].risk_created': 120, 'document_defects[].proposed_fix': 70,
    'document_defects[].locations[].quote': 120, 'document_defects[].prevails_basis': 100,
    'dangerous_combinations[].why_together': 220, 'dangerous_combinations[].breaking_fix': 80,
    'dangerous_combinations[].neutralizes': 100,
    'summary.not_checked[].item': 110, 'summary.not_checked[].why': 80, 'summary.assumptions[]': 200,
    'coverage[].note': 80,
    'risks[].critical_detail.what_happens': 300, 'risks[].critical_detail.why_not_protected': 300,
}
MAX_KEY_DATES = 5
WORDS_WARN, WORDS_FAIL = 2800, 3200

# ---- הפניה לסעיף: תבנית אחת (הערות 3.5, ההרחבה של שינוי 1) ----
FIXED_REFS = {'פתיח', 'מבוא', 'הגדרות', 'חתימות', 'בלוק החתימות', 'בלוק הצדדים', 'כותרת', 'נספחים',
              'preamble', 'recitals', 'definitions', 'signatures'}
_NUM = r'\d+[א-ת]?(?:\.\d+[א-ת]?)*(?:\([א-תa-z0-9]{1,3}\))*'
_REF_RE = re.compile(r'^(?:[^\d;,]{1,30}?,?\s)?(?:סעיף |סעיפים |פסקה |section |clause )?' + _NUM +
                     r'(?:\s*(?:,|ו-?)\s*' + _NUM + r')*$', re.I)


def clause_ref_ok(s):
    """"סעיף 7.2(א)", "תמורה 1", "היקף הייעוץ, סעיף 1", "6, 9", "פתיח", "נספח ב", "חדש אחרי סעיף 5";
    כמה הפניות מופרדות ב-"; ". לא: משפט, ציטוט, "פסקה 5 בטיוטה" או מספור של הנוסח המוצע בלי הסבר."""
    s = (s or '').strip()
    if not s:
        return False
    for part in re.split(r'\s*;\s*', s):
        if part.startswith('חדש אחרי '):
            part = part[len('חדש אחרי '):].strip()
        if part in FIXED_REFS or re.match(r'^נספח [^\s;]{1,20}( [^\s;]{1,20})?$', part):
            continue
        if all(x.strip() in FIXED_REFS for x in part.split(',')):
            continue
        if not _REF_RE.match(part):
            return False
    return True


# ---- עדכניות: תיקונים ידועים שאחריהם נוסח קודם אינו "ודאות גבוהה" (הערות 3.5, ההרחבה של שינוי 19) ----
def load_amendments(items):
    """רשימת התיקונים הידועים, כנתון (מהכללים המשותפים או מההרצה), לא כקבוע בקוד:
    [{"match": "<ביטוי לשם החוק>", "name": "<שם התיקון>", "in_force": "YYYY-MM-DD",
      "topic": "<ביטוי לנושא, לא חובה>", "exclude": "<ביטוי למקור שהוא החוק המתקן עצמו, לא חובה>"}]."""
    out = []
    for a in items or []:
        out.append({'match': re.compile(a['match']), 'name': a['name'], 'in_force': a['in_force'],
                    'topic': re.compile(a['topic']) if a.get('topic') else None,
                    'exclude': re.compile(a['exclude']) if a.get('exclude') else None})
    return out


# ---- החלטה 1 (14.10.2026): אין שרשרת אישורים. הכרעת המשתמש נרשמת כהכרעה, בלי מאשר ובלי מצב "ממתין" ----
DECISION_KEYS = {'status', 'basis', 'state_clause_id', 'state_clause_ids', 'note', 'decided_at'}
APPROVAL_PHRASES = ['ממתין לאישור', 'ממתינה לאישור', 'ממתינים לאישור', 'טעון אישור מנכ', 'אישור מנכ"ל', 'אישור מנכ״ל',
                    'אישור המנכ"ל', 'אישור המנכ״ל', 'טבלת הסמכויות', 'מוצע לקבלה', 'awaiting approval',
                    'pending approval', 'subject to CEO approval']
SIDES = ('as_obligor', 'as_beneficiary', 'both', 'as_discloser', 'as_recipient')  # שני האחרונים: מרשם ישן
FIX_STATUS = ('open', 'resolved', 'accepted_as_concession', 'conceded')   # conceded: השם בהערות הנושא ונותן 4.9
CONCEDED = ('accepted_as_concession', 'conceded')
FIX_KINDS = ('missing', 'incomplete', 'created_by_response', 'polish')   # polish: ליטוש, אינו חוסם משלוח
RULE_ID_RE = re.compile(r'^(?:R-?\d+|mandatory_list:.*|rule:.*)$')   # רק לנוסח השגיאה; ההכרעה: מזהה בקובץ המצב
AREO_UA_PREFIX = 'AreoLegal-research/'
# גרסה 1.2.0 (כלל 2.25): המזהה כולל את שם הארגון וכתובת קשר, ואינו מזהה דפדפן
AREO_UA_CONTACT = re.compile(r'AreoLegal\b.*contact: [A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\)$')
BROWSER_UA = re.compile(r'Mozilla/|Chrome/|Safari/|Firefox/|Edg/|Gecko', re.I)


_TERM_CACHE = {}


def _term(phrase):
    if phrase not in _TERM_CACHE:
        _TERM_CACHE[phrase] = terms_re([phrase])
    return _TERM_CACHE[phrase]


def ua_problem(ua):
    # '' כשהמזהה תקין; אחרת הסיבה
    ua = str(ua)
    if not ua.startswith(AREO_UA_PREFIX) or BROWSER_UA.search(ua):
        return 'user_agent שאינו המזהה של Areo (%s): אסור מזהה דפדפן' % ua[:40]
    if not AREO_UA_CONTACT.search(ua):
        return 'user_agent בלי שם הארגון וכתובת קשר (%s): נדרש "AreoLegal ... contact: <email>"' % ua[:60]
    return ''
ISO_TS = re.compile(r'^\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2}))?$')
TS_KEY = re.compile(r'(?:_at|^at|saved_at|looked_up_at|defined_at)$')

# ---- עובדות שהפרופיל קובע (הערות 3.6, כללי): רגולטורים במעמד Confirmed, פעילויות, ומקומות מסחר. מה שהפרופיל
# קובע אינו "הנחה לאישור". אין כאן רשימה של רגולטורים, פעילויות או חוקים מסוימים. ----
def profile_status(profile):
    p = profile or {}
    regs = (p.get('regulatory_footprint_primary') or []) + (p.get('regulatory_footprint_secondary') or [])
    pm = p.get('public_market') or {}
    return {
        'confirmed_regulators': [r.get('regulator_name', '') for r in regs
                                 if r.get('applicability_status') == 'Confirmed' and r.get('regulator_name')],
        'activities': [a for a in ((p.get('sector') or {}).get('financial_activity') or []) +
                       ((p.get('sector') or {}).get('activities') or []) if a],
        'listed': bool(pm.get('listed')),
        'venues': [v for v in pm.get('venues') or [] if v],
    }


def profile_facts(profile):
    """המחרוזות שהפרופיל קובע כעובדה ושאסור להציג כהנחה: שמות הרגולטורים במעמד Confirmed."""
    return [x for x in profile_status(profile)['confirmed_regulators'] if len(x) >= 4]


def lvl(score):
    return 'critical' if score >= 16 else 'high' if score >= 9 else 'medium' if score >= 4 else 'low'


def _walk(o, path=''):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from _walk(v, path + '.' + k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from _walk(v, '%s[%d]' % (path, i))
    elif isinstance(o, str):
        yield path, o


def _limit_paths(reg):
    """מחזיר (תבנית, נתיב, ערך) לכל שדה שיש לו תקרת אורך."""
    S = reg.get('summary') or {}
    for r in reg.get('risks') or []:
        yield 'risks[].name', 'risk %s.name' % r.get('id'), r.get('name')
        yield 'risks[].treatment_direction', 'risk %s.treatment_direction' % r.get('id'), r.get('treatment_direction')
        for a in r.get('anchors') or []:
            yield 'risks[].anchors[].clause', 'risk %s.anchor.clause' % r.get('id'), a.get('clause')
        cd = r.get('critical_detail') or {}
        yield 'risks[].critical_detail.what_happens', 'risk %s.critical_detail' % r.get('id'), cd.get('what_happens')
        yield 'risks[].critical_detail.why_not_protected', 'risk %s.critical_detail' % r.get('id'), cd.get('why_not_protected')
    for i, p in enumerate(reg.get('pre_send_fixes') or []):
        yield 'pre_send_fixes[].gap', 'pre_send %d.gap' % i, p.get('gap')
        yield 'pre_send_fixes[].where', 'pre_send %d.where' % i, p.get('where')
    for s in S.get('bottom_line') or []:
        yield 'summary.bottom_line[]', 'summary.bottom_line', s
    yield 'summary.deal_one_line', 'summary.deal_one_line', S.get('deal_one_line')
    for k in S.get('key_dates') or []:
        for f in ('what', 'consequence', 'window', 'clause'):
            yield 'summary.key_dates[].' + f, 'key_dates.' + f, k.get(f)
    for d in reg.get('document_defects') or []:
        for f in ('topic', 'risk_created', 'proposed_fix', 'prevails_basis'):
            yield 'document_defects[].' + f, '%s.%s' % (d.get('id'), f), d.get(f)
        for l in d.get('locations') or []:
            yield 'document_defects[].locations[].quote', '%s.quote' % d.get('id'), l.get('quote')
    for c in reg.get('dangerous_combinations') or []:
        for f in ('why_together', 'breaking_fix', 'neutralizes'):
            yield 'dangerous_combinations[].' + f, '%s.%s' % (c.get('combo_id'), f), c.get(f)
    for x in S.get('not_checked') or []:
        yield 'summary.not_checked[].item', 'not_checked.item', x.get('item')
        yield 'summary.not_checked[].why', 'not_checked.why', x.get('why')
    for a in S.get('assumptions') or []:
        yield 'summary.assumptions[]', 'summary.assumptions', a
    for c in reg.get('coverage') or []:
        yield 'coverage[].note', 'coverage %s.note' % c.get('lens'), c.get('note')


def concessions(state):
    """הוויתורים המכוונים בקובץ המצב, כרשימה (שני ויתורים יכולים לחול על אותו סעיף).
    לפי הערות הנושא ונותן 4.9: deliberate_concessions[] עם clause_ref, שהוא מזהה הסעיף בקובץ המצב
    (clauses[].clause_id או מפתח ב-numbering_map), ו-report_as: "accepted_risk". שדה אישור, אם נשאר בקובץ
    מצב ישן (approval, required_by), אינו נקרא: החלטה 1 מ-14.10.2026."""
    out = []
    for d in (state or {}).get('deliberate_concessions') or []:
        if d.get('report_as', 'accepted_risk') != 'accepted_risk':
            continue
        out.append({'clause_ref': d.get('clause_ref') or d.get('clause_id'), 'topic': d.get('topic') or d.get('what') or ''})
    return out


def deliberate_waivers(state):
    """מזהי הסעיפים בקובץ המצב שהנושא ונותן ויתר עליהם במכוון.
    קובץ מצב לפי הערות הנושא ונותן 4.9: deliberate_concessions[] עם clause_ref (מזהה סעיף, לא מזהה כלל)
    ו-report_as: "accepted_risk". קובץ מצב ישן: clauses[].concession_history[] עם who == "us"
    ו-deliberate: true, או in_exchange_for שמתחיל ב"ויתור מכוון"."""
    out = {}
    if not state:
        return out
    for d in state.get('deliberate_concessions') or []:
        if d.get('report_as', 'accepted_risk') != 'accepted_risk':
            continue
        cid = d.get('clause_ref') or d.get('clause_id')
        if cid:
            out[cid] = d.get('topic') or d.get('what') or ''
    for c in state.get('clauses') or []:
        for h in c.get('concession_history') or []:
            if h.get('who') == 'us' and (h.get('deliberate') is True or
                                          str(h.get('in_exchange_for') or '').startswith('ויתור מכוון')):
                out[c.get('clause_id')] = h.get('what') or ''
    return out


def _norm_topic(t):
    return re.sub(r'\s+', ' ', str(t or '')).strip().casefold()


def concession_records(state, clause_ref):
    # הוויתורים המכוונים בסעיף אחד, עם הנושא וקודי הפער שלהם (גרסה 1.2.0)
    out = []
    for d in (state or {}).get('deliberate_concessions') or []:
        if d.get('report_as', 'accepted_risk') == 'accepted_risk' and \
                (d.get('clause_ref') or d.get('clause_id')) == clause_ref:
            out.append({'topic': d.get('topic') or d.get('what') or '', 'gap': d.get('gap') or '',
                        'gap_codes': list(d.get('gap_codes') or [])})
    for c in (state or {}).get('clauses') or []:
        if c.get('clause_id') != clause_ref:
            continue
        for h in c.get('concession_history') or []:
            if h.get('who') == 'us' and (h.get('deliberate') is True or
                                          str(h.get('in_exchange_for') or '').startswith('ויתור מכוון')):
                out.append({'topic': h.get('what') or '', 'gap': '', 'gap_codes': []})
    return out


def same_topic(fix, conc):
    # האם שורת "לתיקון" עוסקת באותו נושא של ויתור מכוון באותו סעיף. משווים topic, אחר כך קוד פער (gap_code),
    # ואחר כך את נושא הוויתור בתוך gap. ויתור בלי נושא: אי אפשר להבחין, ולכן נחשב אותו נושא.
    ft, ct = _norm_topic(fix.get('topic')), _norm_topic(conc.get('topic'))
    if ft and ct:
        return ft == ct
    fcodes = set(fix.get('gap_codes') or []) | ({fix['gap_code']} if fix.get('gap_code') else set())
    if fcodes and conc.get('gap_codes'):
        return bool(fcodes & set(conc['gap_codes']))
    if not ct:
        return True
    text = _norm_topic(fix.get('gap')) + ' ' + _norm_topic(fix.get('topic'))
    if ct in text:
        return True
    # בלי topic ובלי קוד פער: נחשב נושא אחר רק כשאף מילה מנושא הוויתור (בלי אותיות שימוש) אינה מופיעה בפער
    for w in re.findall(r'\w+', ct):
        stem = re.sub(r'^[ובכלמשה]{1,2}(?=\w{3})', '', w)
        if len(stem) >= 3 and (stem in text or (len(stem) >= 4 and stem[:3] in text)):
            return True
    return False


def state_clause_ids(state):
    ids = {c.get('clause_id') for c in (state or {}).get('clauses') or [] if c.get('clause_id')}
    return ids | set(((state or {}).get('numbering_map') or {}).keys())


def numbering_consistent(where, mapped):
    """ההפניה ב-where (קצרה, עד 30 תווים) תואמת לשם הסעיף בתגובה שלנו לפי numbering_map: כל מספר
    שב-where מופיע בשם המלא ("סעיף 2 בפרק 'תמורה ותנאי תשלום'" מול "תמורה 2")."""
    nums = re.findall(r'\d+[א-ת]?(?:\.\d+[א-ת]?)*', where or '')
    have = set(re.findall(r'\d+[א-ת]?(?:\.\d+[א-ת]?)*', mapped or ''))
    return all(n in have for n in nums)


def validate(reg, corpus=None, deal_dir=None, state=None, profile=None, playbook_status=None, known_amendments=None):
    E, W = [], []

    def err(where, msg):
        E.append('%s: %s' % (where, msg))

    def warn(where, msg):
        W.append('%s: %s' % (where, msg))

    M = reg.get('meta') or {}
    S = reg.get('summary') or {}
    sv = M.get('source_version') or {}
    ts = sv.get('text_status')

    # ---------- meta ----------
    for k in M:
        if k not in META_KEYS:
            err('meta', 'שדה לא מוכר: %s' % k)
    for k in ('company', 'scope', 'generated_at', 'source_version', 'counterparty', 'display_language'):
        if not M.get(k):
            err('meta', 'חסר שדה חובה %s' % k)
    if 'annexes_reviewed' in reg:
        err('root', 'annexes_reviewed בשורש המרשם')
    if M.get('scope') == 'deal' and not re.match(r'^deal_[^_]+_\d{4}-\d{2}-\d{2}$', M.get('transaction_id') or ''):
        err('meta.transaction_id', 'במצב deal נדרש deal_<slug>_<YYYY-MM-DD> מקובץ המצב')
    if ts not in TEXT_STATUS:
        err('meta.source_version', 'text_status לא חוקי')
    cp = (M.get('counterparty') or {}).get('name', '') or ''
    if not cp.strip() or re.search(r'\[[^\]]*\]|להשלים', cp):
        err('meta.counterparty.name', 'שם ריק או מציין מקום')
    ER = reg.get('entity_research') or {}
    if '(השם לא מולא בהסכם)' in cp and not ER.get('missing_identifiers'):
        err('meta.counterparty.name', '"השם לא מולא בהסכם" בלי missing_identifiers')
    br = M.get('branding') or {}
    if set(br) - {'logo'}:
        err('meta.branding', 'שדות נוספים תחת branding')
    logo = br.get('logo') or ''
    if logo and (not logo.startswith('data:image/') or len(logo) * 3 / 4 > 150 * 1024):
        err('meta.branding.logo', 'לא תמונה מוטמעת, או מעל 150 קילובייט')
    if not M.get('prepared_for_counsel'):
        warn('meta', 'אין שם עורך דין: הדוח יציג אזהרת חיסיון')
    mutual = M.get('position') == 'הדדי' or bool(M.get('mutual_primary_role'))
    if M.get('position') == 'הדדי' and not M.get('mutual_primary_role'):
        err('meta', 'הסכם הדדי בלי mutual_primary_role')
    if M.get('benchmark_status') not in (None, 'approved', 'draft', 'none'):
        err('meta.benchmark_status', 'ערך לא חוקי')
    if playbook_status is not None and M.get('playbook_ref'):
        want = 'approved' if playbook_status.get('playbook_status') == 'Approved' else 'draft'
        if M.get('benchmark_status') != want:
            err('meta.benchmark_status', '%s, אבל המעמד הנגזר של הפלייבוק הוא %s (playbook/status.py)' % (
                M.get('benchmark_status'), playbook_status.get('playbook_status')))

    # ---------- documents and quotes ----------
    docs = {d.get('title'): d for d in reg.get('documents') or []}
    texts = {}
    for d in corpus or []:
        acc = ' '.join(p['text_accept_all'] for ps in d['parts'].values() for p in ps)
        rej = ' '.join(p['text_reject_all'] for ps in d['parts'].values() for p in ps)
        texts[d['file']] = (norm(acc), norm(rej))

    def quote_ok(a, where):
        if a.get('document') not in docs:
            err(where, 'עוגן למסמך שאינו ב-documents: %r' % a.get('document'))
            return
        if re.search(r'\.json|פלייבוק|פרופיל|negotiation_state', a.get('document') or ''):
            err(where, 'עוגן לקובץ פנימי')
        if corpus is None:
            return
        t = docs[a.get('document')]
        src = texts.get(t.get('file'))
        if not src:
            err(where, 'אין טקסט מקור למסמך %s' % t.get('file'))
            return
        qt = norm(a.get('quote'))
        if not qt:
            err(where, 'ציטוט ריק')
            return
        if t.get('role') == 'our_response':
            ok = qt in src[0]
        else:
            ok = qt in src[0] or qt in src[1]
        if not ok:
            err(where, 'הציטוט לא נמצא מילה במילה: %s' % qt[:60])

    # ---------- risks ----------
    R = reg.get('risks') or []
    ids = [r.get('id') for r in R]
    idset = set(ids)
    if len(idset) != len(ids):
        err('risks', 'מזהים כפולים')
    if sorted(r.get('risk_no') or 0 for r in R) != list(range(1, len(R) + 1)):
        err('risks', 'risk_no אינו רציף מ-1')
    rank = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
    byno = sorted(R, key=lambda r: r.get('risk_no') or 0)

    def score_of(r):
        return (r.get('residual') or {}).get('score') or (r.get('inherent') or {}).get('score') or 0

    for a, b in zip(byno, byno[1:]):
        if (rank.get(b.get('severity_level'), 0), score_of(b)) > (rank.get(a.get('severity_level'), 0), score_of(a)):
            err('risks', 'risk_no %s לפני %s אינו לפי חומרה' % (a.get('risk_no'), b.get('risk_no')))
    seen_anchor, crit = {}, 0
    for r in R:
        w = 'risk %s' % r.get('id')
        for k in r:
            if k in FORBIDDEN_RISK:
                err(w, 'שדה שיצא מהסכמה: %s' % k)
            elif k not in RISK_KEYS:
                err(w, 'שדה לא מוכר: %s' % k)
        for k in ('estimated_amount', 'ratio_to_deal_value'):
            if k in (r.get('exposure') or {}):
                err(w, 'שדה אומדן שיצא: %s' % k)
        if r.get('kind') not in KINDS:
            err(w, 'kind לא חוקי')
        if r.get('primary_lens') not in LENS8:
            err(w, 'primary_lens לא חוקי')
        for L in r.get('lens') or []:
            if L not in LENS8:
                err(w, 'lens לא חוקי %s' % L)
        if len((r.get('name') or '').split()) > 16:
            err(w, 'שם ארוך מ-15 מילים')
        inh, res = r.get('inherent') or {}, r.get('residual') or {}
        for blk in (inh, res):
            if blk and blk.get('score') != (blk.get('severity') or 0) * (blk.get('likelihood') or 0):
                err(w, 'ניקוד אינו מכפלה')
        exp = lvl(score_of(r))
        if r.get('severity_level') != exp:
            err(w, 'severity_level לא נגזר נכון (%s במקום %s)' % (r.get('severity_level'), exp))
        if exp == 'critical':
            crit += 1
            cd = r.get('critical_detail') or {}
            if not cd.get('what_happens') or not cd.get('why_not_protected'):
                err(w, 'קריטי בלי critical_detail')
        an = r.get('anchors') or []
        if not an and r.get('certainty') != 'hypothesis':
            err(w, 'סיכון בלי עוגן חייב להיות השערה')
        for i, a in enumerate(an):
            quote_ok(a, '%s anchor %d' % (w, i))
            if a.get('clause') and not clause_ref_ok(a['clause']):
                err('%s anchor %d' % (w, i), 'הפניה לסעיף שלא בתבנית: %r' % a['clause'])
        if an:
            key = (an[0].get('clause'), r.get('primary_lens'))
            if key in seen_anchor:
                err(w, 'אותו עוגן ראשון ואותה עדשה כמו %s' % seen_anchor[key])
            seen_anchor[key] = r.get('id')
        if mutual and r.get('side') not in SIDES:
            err(w, 'side חובה בהסכם הדדי')
        if not mutual and r.get('side') not in (None, ''):
            err(w, 'side רק בהסכם הדדי')
        for c in r.get('controls') or []:
            if c.get('basis') == 'proposed_text' and ts not in ('our_unsent_response', 'our_sent_response'):
                err(w, 'proposed_text בנוסח שאינו התגובה שלנו')
        am = (r.get('exposure') or {}).get('amount') or {}
        if am.get('value') is not None:
            if am.get('source') not in ('contract', 'client'):
                err(w, 'סכום בלי מקור מההסכם או מהלקוח')
            if am.get('source') == 'contract' and not (am.get('source_ref') and am.get('calc')):
                err(w, 'סכום מההסכם בלי סעיף וחישוב')
        if r.get('playbook_flag') not in ('none', 'red_line', 'deviates_from_benchmark'):
            err(w, 'playbook_flag לא חוקי')
        if r.get('playbook_flag') == 'red_line' and M.get('benchmark_status') != 'approved':
            err(w, '"חוצה קו אדום" רק מול פלייבוק מאושר')
        if r.get('regulatory_basis') not in (None, 'law_verified', 'law_claimed', 'commercial'):
            err(w, 'regulatory_basis לא חוקי')
        dec = r.get('decision') or {}
        for k in dec:
            if k not in DECISION_KEYS:
                err(w, 'שדה לא מוכר ב-decision: %s (אין שדות אישור: החלטה 1, הכרעת המשתמש היא ההחלטה)' % k)
        if dec and dec.get('status') not in (None, 'open', 'mitigating', 'accepted'):
            err(w, 'decision.status לא חוקי: %s (אין מצב "ממתין לאישור")' % dec.get('status'))
        if dec.get('basis') == 'deliberate_waiver' and dec.get('status') != 'accepted':
            err(w, 'ויתור מכוון חייב decision.status "accepted"')
        if dec.get('basis') == 'deliberate_waiver':
            for x in [dec.get('state_clause_id')] + list(dec.get('state_clause_ids') or []):
                if x and RULE_ID_RE.match(str(x)):
                    err(w, 'decision.state_clause_id %s הוא מזהה כלל; נדרש מזהה הסעיף בקובץ המצב' % x)
        if r.get('created_by_response') and ts != 'our_unsent_response':
            err(w, 'created_by_response רק בתגובה שטרם נשלחה')
        src_ids = {s.get('id') for s in (reg.get('research') or {}).get('sources_checked') or []}
        for sid in r.get('external_source_ids') or []:
            if sid not in src_ids:
                err(w, 'external_source_id לא קיים: %s' % sid)
        if r.get('certainty') == 'fact':
            warn(w, 'certainty fact: לוודא שזה רק תיאור הסעיף')
    if crit > 5:
        err('risks', 'יותר מחמישה קריטיים')
    # שם סיכון שחוזר כלשונו בשדה אחר
    fields = list(_walk({k: v for k, v in reg.items() if k != 'meta'}))
    for r in R:
        nm = r.get('name') or ''
        for p, s in fields:
            if nm and nm in s and not p.endswith('.name'):
                err('risk %s' % r.get('id'), 'השם חוזר כלשונו בשדה %s' % p)
                break

    # ---------- coverage ----------
    cov = {c.get('lens'): c for c in reg.get('coverage') or []}
    for L in LENS8:
        c = cov.get(L)
        if not c:
            err('coverage', 'עדשה %s לא דווחה' % L)
            continue
        if c.get('status') not in ('findings', 'none_found', 'not_checked'):
            err('coverage', 'status לא חוקי ב-%s' % L)
        if c.get('status') in ('none_found', 'not_checked') and not c.get('note'):
            err('coverage', 'חסר note ב-%s' % L)
        prim = sorted(r.get('id') for r in R if r.get('primary_lens') == L)
        if sorted(c.get('risk_ids') or []) != prim:
            err('coverage', 'risk_ids ב-%s אינם תואמים לעדשה הראשית' % L)
        if c.get('status') == 'findings' and not prim:
            err('coverage', 'findings בלי סיכונים ב-%s' % L)
    for c in reg.get('coverage') or []:
        if c.get('lens') not in LENS8:
            err('coverage', 'עדשה לא מוכרת %s' % c.get('lens'))

    # ---------- summary ----------
    if S.get('sign_as_is') not in ('yes', 'with_fixes', 'no'):
        err('summary', 'sign_as_is לא חוקי')
    bl = S.get('bottom_line') or []
    if not 3 <= len(bl) <= 4:
        err('summary.bottom_line', 'צריך 3 עד 4 משפטים')
    if any('אפשר לחתום' in b for b in bl):
        warn('summary.bottom_line', 'חוזר על התווית')
    KD = S.get('key_dates') or []
    if len(KD) > MAX_KEY_DATES:
        err('summary.key_dates', 'יותר מ-%d' % MAX_KEY_DATES)
    for k in KD:
        if k.get('date') is None:
            if not k.get('window'):
                err('summary.key_dates', 'date ריק בלי window')
        elif not re.match(r'^\d{4}-\d{2}-\d{2}$', str(k['date'])):
            err('summary.key_dates', 'date לא ISO')
        if k.get('clause') and not clause_ref_ok(k['clause']):
            err('summary.key_dates', 'הפניה לסעיף שלא בתבנית: %r' % k['clause'])

    # ---------- pre-send, deliberate waivers, numbering (הערות 3.6: חוזה הלולאה לפני משלוח) ----------
    P = reg.get('pre_send_fixes') or []
    if P and ts != 'our_unsent_response':
        err('pre_send_fixes', 'רק בתגובה שטרם נשלחה')
    if ts == 'our_unsent_response' and S.get('sign_as_is') == 'with_fixes' and not P:
        err('summary', 'with_fixes בלי pre_send_fixes')
    if len(P) > 6:
        err('pre_send_fixes', 'יותר משש שורות')
    accepted = {r.get('id') for r in R if (r.get('decision') or {}).get('basis') == 'deliberate_waiver'}
    waived = deliberate_waivers(state)
    known_ids = state_clause_ids(state)
    nmap = (state or {}).get('numbering_map') or {}
    fix_ids = set()
    in_fixes = set()
    for i, p in enumerate(P):
        w = 'pre_send %d' % i
        if p.get('kind') not in FIX_KINDS:
            err(w, 'kind לא חוקי')
        if not p.get('risk_ids') or any(x not in idset for x in p.get('risk_ids')):
            err(w, 'risk_ids חסר או לא קיים')
        if p.get('kind') != 'polish':
            in_fixes |= set(p.get('risk_ids') or [])
        if set(p.get('risk_ids') or []) & accepted:
            err(w, 'סיכון שהתקבל בוויתור מכוון אינו ברשימה "לתיקון לפני שליחת התגובה"')
        if p.get('where') and not clause_ref_ok(p['where']):
            err(w, 'where שלא בתבנית ההפניה: %r' % p['where'])
        if 'blocks_signing' in p and not isinstance(p['blocks_signing'], bool):
            err(w, 'blocks_signing בוליאני')
        if re.search(r'"[^"]{25,}"', p.get('gap') or ''):
            warn(w, 'נראה כמו נוסח מצוטט')
        # חוזה הלולאה: id יציב, clause_ref (מזהה סעיף) ו-status שהנושא ונותן מעדכן
        fid = p.get('id')
        if not fid or not re.match(r'^PSF-\d{1,3}$', str(fid)):
            err(w, 'id חובה, בתבנית PSF-01: הנושא ונותן מסמן לפיו')
        elif fid in fix_ids:
            err(w, 'id כפול %s' % fid)
        fix_ids.add(fid)
        if p.get('status') not in FIX_STATUS:
            err(w, 'status חובה: open, resolved או accepted_as_concession (הרכיב כותב open; conceded כשם חלופי)')
        sc = p.get('clause_ref')
        if not sc:
            err(w, 'חסר clause_ref: מזהה הסעיף בקובץ המצב (numbering_map), שהנושא ונותן פותח לפיו')
        if p.get('state_clause_id') and sc and p.get('state_clause_id') != sc:
            err(w, 'state_clause_id (שדה של 3.5) שונה מ-clause_ref')
        if sc and RULE_ID_RE.match(str(sc)):
            err(w, 'clause_ref %s הוא מזהה כלל; נדרש מזהה סעיף' % sc)
        if state is not None and sc:
            if sc not in known_ids:
                err(w, 'clause_ref %s אינו בקובץ המצב' % sc)
            elif sc in waived and p.get('status') not in CONCEDED:
                # גרסה 1.2.0: תיקון לפני משלוח בסעיף שיש בו ויתור מכוון על נושא אחר מותר
                same = [c for c in concession_records(state, sc) if same_topic(p, c)]
                if same:
                    err(w, 'ויתור מכוון של הנושא ונותן (%s, %s): מקומו "סיכון שהתקבל", לא "לתיקון"'
                        % (sc, same[0]['topic']))
            nm = nmap.get(sc)
            if nm and p.get('where') and not numbering_consistent(p['where'], nm):
                err(w, 'where %r אינו תואם למספור התגובה שלנו לפי numbering_map (%s)' % (p['where'], nm))
    # סיכון שהתגובה שלנו יצרה נכנס לרשימה בלי קשר לחומרה (השותף הבכיר, ממצא 12)
    created = [r.get('id') for r in R if r.get('created_by_response') and r.get('id') not in accepted]
    for rid in created:
        if rid not in in_fixes:
            err('risk %s' % rid, 'נוצר בתגובה שלנו ואינו ברשימה "לתיקון לפני שליחת התגובה" (בלי קשר לחומרה)')
    if len(created) > 6:
        err('pre_send_fixes', '%d סיכונים שהתגובה יצרה: לאחד לפי סעיף, עד שש שורות' % len(created))
    if ts == 'our_unsent_response' and [p for p in P if p.get('kind') != 'polish']:
        for b in bl:
            if 'אפשר לחתום' in b or 'can be signed' in b.lower():
                err('summary.bottom_line', 'בתגובה שטרם נשלחה: "אפשר לשלוח את התגובה רק אחרי התיקונים", לא "לחתום"')
    if state is not None and state.get('text_status'):
        if ts != state['text_status']:
            err('meta.source_version.text_status', '%s, אבל בקובץ המצב text_status הוא %s' % (ts, state['text_status']))
    if state is not None:
        # ויתור מכוון: clause_ref הוא מזהה סעיף, וכל ויתור מופיע כסיכון שהתקבל
        covered = set()
        for r in R:
            dec = r.get('decision') or {}
            if dec.get('basis') == 'deliberate_waiver':
                covered |= {x for x in [dec.get('state_clause_id')] + list(dec.get('state_clause_ids') or []) if x}
        for c in concessions(state):
            cr = c['clause_ref']
            if not cr:
                err('state.deliberate_concessions', 'ויתור בלי clause_ref: %s' % c['topic'])
                continue
            if cr not in known_ids:
                err('state.deliberate_concessions', 'clause_ref %s (%s) אינו מזהה סעיף בקובץ המצב%s' % (
                    cr, c['topic'], ' (זה מזהה כלל)' if RULE_ID_RE.match(str(cr)) else ''))
            if cr not in covered:
                err('state.deliberate_concessions', 'הוויתור המכוון %s (%s) אינו מופיע כסיכון שהתקבל' % (cr, c['topic']))
        for r in R:
            for a in r.get('anchors') or []:
                sc = a.get('state_clause_id')
                if sc and sc not in known_ids:
                    err('risk %s' % r.get('id'), 'state_clause_id %s אינו בקובץ המצב' % sc)
                nm = nmap.get(sc) if sc else None
                if nm and a.get('clause') and not numbering_consistent(a['clause'], nm):
                    err('risk %s' % r.get('id'), 'clause %r אינו תואם ל-numbering_map (%s)' % (a['clause'], nm))
            dec = r.get('decision') or {}
            for dsc in [dec.get('state_clause_id')] + list(dec.get('state_clause_ids') or []):
                if dsc and dsc not in waived:
                    err('risk %s' % r.get('id'), 'decision.state_clause_id %s אינו ויתור מכוון בקובץ המצב' % dsc)
        # מקור אמת אחד לפלייבוק: כשתנאי ההפעלה אינם מתקיימים, אין סימון (מנכ"ל, ממצא 11)
        # המקום הקנוני: שורש קובץ המצב (state_builder 1.2.0); קובץ מצב ישן: playbook_status.playbook_resolution
        pr = state.get('playbook_resolution') or (state.get('playbook_status') or {}).get('playbook_resolution') or {}
        if pr.get('activation_ok') is False:
            for r in R:
                if r.get('playbook_flag') not in (None, 'none'):
                    err('risk %s' % r.get('id'), 'סימון פלייבוק, אבל בקובץ המצב activation_ok הוא false')

    # ---------- combos and defects ----------
    C = reg.get('dangerous_combinations') or []
    if len(C) > 5:
        err('combos', 'יותר מחמישה')
    for c in C:
        w = c.get('combo_id')
        if c.get('type') not in ('combination', 'chain', 'neutralizer'):
            err(w, 'type לא חוקי')
        if not c.get('clauses') or not c.get('breaking_fix') or not c.get('why_together'):
            err(w, 'clauses, why_together ו-breaking_fix חובה')
        if c.get('type') == 'neutralizer' and not c.get('neutralizes'):
            err(w, 'neutralizes חובה בנטרול')
        if 'why_dangerous_together' in c:
            err(w, 'שדה ישן why_dangerous_together')
        if any(x not in idset for x in c.get('risk_ids') or []):
            err(w, 'risk_ids לא קיים')
        for x in c.get('clauses') or []:
            if not clause_ref_ok(str(x)):
                err(w, 'הפניה לסעיף שלא בתבנית: %r' % x)
        for i, a in enumerate(c.get('anchors') or []):
            quote_ok(a, '%s anchor %d' % (w, i))
    for d in reg.get('document_defects') or []:
        w = d.get('id')
        if d.get('type') not in DEF_TYPES:
            err(w, 'type לא חוקי')
        if d.get('prevails') not in ('first', 'second', 'none'):
            err(w, 'prevails לא חוקי')
        if d.get('prevails') in ('first', 'second') and not d.get('prevails_basis'):
            err(w, 'prevails_basis חובה כשיש הכרעה')
        if d.get('type') == 'contradiction' and len([l for l in d.get('locations') or [] if l.get('quote')]) < 2:
            err(w, 'סתירה בלי שני מיקומים עם ציטוט')
        for i, l in enumerate(d.get('locations') or []):
            if l.get('quote'):
                quote_ok(l, '%s loc %d' % (w, i))
        if any(x not in idset for x in d.get('risk_ids') or []):
            err(w, 'risk_ids לא קיים')

    # ---------- page budget: cell limits ----------
    for key, where, val in _limit_paths(reg):
        if val and len(val) > LIMITS[key]:
            err(where, 'ארוך מ-%d תווים (%d): לקצר לפני הבנייה' % (LIMITS[key], len(val)))

    # ---------- research: sources, currency, status-dependent statutes ----------
    RS = reg.get('research') or {}
    if RS.get('mode') not in ('approved_sources', 'documents_only'):
        err('research', 'mode לא חוקי')
    conf = {c.get('source_id'): c for c in RS.get('confidence') or []}
    for c in RS.get('confidence') or []:
        if c.get('label') not in ('high', 'medium'):
            err('research.confidence', 'תווית לא חוקית')
        if c.get('label') == 'medium' and not c.get('why'):
            err('research.confidence', 'ודאות בינונית בלי why')
    raws = {}
    for rc in RS.get('raw_copies') or []:
        for k in ('final_url', 'typed_url'):
            if rc.get(k):
                raws[rc[k]] = rc
                if has_secret(rc[k]):
                    err('research.raw_copies', 'כתובת עם טוקן או חתימה: %s' % k)
    for s in RS.get('sources_checked') or []:
        w = s.get('id') or '?'
        for k in ('source', 'url', 'date'):
            if not s.get(k):
                err(w, 'חסר %s' % k)
        host = re.sub(r'^https?://([^/:]+).*$', r'\1', s.get('url') or '').lower()
        if not any(host == a or host.endswith('.' + a) for a in APPROVED_DOMAINS):
            err(w, 'דומיין שאינו ברשימה המורשית: %s' % host)
        if has_secret(s.get('url') or ''):
            err(w, 'כתובת עם טוקן או חתימה')
        for f in ('corroborations', 'verification', 'single_source_reason', 'signal', 'quotes'):
            if f in s:
                err(w, 'שדה אימות או אות שיצא: %s' % f)
        # עדכניות: נוסח קודם לתיקון ידוע
        vd = s.get('version_date')
        for am in load_amendments(known_amendments):
            if am.get('topic') and not am['topic'].search((s.get('subject') or '') + ' ' + (s.get('taken') or '')):
                continue
            if am.get('exclude') and am['exclude'].search(s.get('source') or ''):
                continue
            if vd and am['match'].search((s.get('source') or '') + ' ' + (s.get('subject') or '')) and vd < am['in_force']:
                c = conf.get(s.get('id')) or {}
                if c.get('label') != 'medium' or am['name'] not in (c.get('why') or ''):
                    err(w, 'נוסח מ-%s קודם ל%s (בתוקף מ-%s): ודאות בינונית עם הסיבה, ופרק 5' % (
                        vd, am['name'], am['in_force']))
                if 'אומת' in (s.get('taken') or '') + (s.get('finding') or ''):
                    err(w, '"אומת" על נוסח שקודם ל%s' % am['name'])
        if deal_dir:
            rc = raws.get(s.get('url'))
            if not rc:
                err(w, 'אין עותק גולמי')
                continue
            fp = os.path.join(deal_dir, rc.get('file') or '')
            if not os.path.exists(fp):
                err(w, 'העותק הגולמי לא נמצא')
                continue
            b = open(fp, 'rb').read()
            if hashlib.sha256(b).hexdigest() != rc.get('sha256'):
                err(w, 'הגיבוב אינו תואם')
            if rc.get('stored') == 'excerpt_window' and not (rc.get('full_sha256') and rc.get('full_size_bytes')):
                err(w, 'חלון מתוך מסמך גדול בלי full_sha256 ו-full_size_bytes של המסמך המלא')
            if s.get('excerpt'):
                # excerpt = מיקום בדף + הציטוט במירכאות ("סעיף 3(ז): "..."); נבדק מה שבין המירכאה הראשונה
                # לאחרונה; גרשיים בתוך מילה עברית אינם מירכאה (page_text.norm)
                t = None
                if rc.get('text_file'):
                    tp = os.path.join(deal_dir, rc['text_file'])
                    if not os.path.exists(tp):
                        err(w, 'text_file לא נמצא')
                    else:
                        tb = open(tp, 'rb').read()
                        if rc.get('text_sha256') and hashlib.sha256(tb).hexdigest() != rc['text_sha256']:
                            err(w, 'הגיבוב של text_file אינו תואם')
                        t = tb.decode('utf-8', 'replace')
                else:
                    try:
                        t = page_text(b)
                    except PdfTextUnavailable as e:
                        err(w, 'אין שכבת טקסט לעותק ה-PDF (%s): לשמור text_file לצדו' % e)
                if t is not None and not excerpt_in(s['excerpt'], t):
                    err(w, 'הקטע המילולי לא נמצא בעותק הגולמי')
    for i, q in enumerate(RS.get('search_log') or []):
        ua = q.get('user_agent')
        if ua is not None and ua_problem(ua):
            err('search_log[%d]' % i, ua_problem(ua))
        hit = client_detail_in_query(q.get('query') or '', [M.get('company')] if M.get('company') else ())
        if hit:   # גרסה 1.2.0: מזהה רשמי של חוק או תקנה אינו פרט של הלקוח
            err('search_log', 'פרט של הלקוח או מספר בשאילתה (%s)' % hit[:20])
    if len(RS.get('search_log') or []) > 10 * max(1, len(RS.get('question') or [])):
        err('search_log', 'יותר מעשר שאילתות לשאלה')
    if profile:
        facts = profile_facts(profile)
        for a in S.get('assumptions') or []:
            hit = [f for f in facts if f in a]
            if hit:
                err('summary.assumptions', 'הנחה על עובדה שהפרופיל קובע (%s): מה שבפרופיל אינו הנחה לאישור' % ', '.join(hit))

    # ---------- entity research ----------
    if ER.get('status') not in (None, 'not_requested', 'requested', 'done'):
        err('entity_research', 'status לא חוקי')
    for x in (ER.get('risks_up') or []) + (ER.get('risks_down') or []):
        if x not in idset:
            err('entity_research', 'risk id לא קיים %s' % x)
    if ER.get('status') == 'done' and deal_dir:
        rf = ER.get('report_file')
        if not rf or not os.path.exists(os.path.join(deal_dir, rf)):
            err('entity_research', 'report_file חסר')

    # ---------- displayed text: blocked phrases, codes, dashes, amounts ----------
    for p, s in _walk(reg):
        if p.startswith('.meta.branding'):
            continue
        for ph in APPROVAL_PHRASES:
            if _term(ph).search(s):   # 1.2.0: מילה שלמה, עם אותיות שימוש (common/terms.py)
                err(p, 'נוסח של שרשרת אישורים: %s (החלטה 1: סיכון שהתקבל הוא הכרעת המשתמש)' % ph)
        key = re.sub(r'\[\d+\]$', '', p).rsplit('.', 1)[-1]
        if TS_KEY.search(key) and s and 'T' in s and not ISO_TS.match(s):
            err(p, 'חותמת זמן בלי שניות או בלי היסט: %s (ISO 8601 מלא, למשל 2026-10-14T17:14:00+03:00)' % s)
        if '—' in s or '–' in s:
            if not (p.endswith('.quote') or p.endswith('.excerpt')):
                err(p, 'מקף ארוך')
        if SKIP_TEXT.search(p) or p.endswith('.quote'):
            continue
        for b in BLOCKED_PHRASES:
            if _term(b).search(s) and not p.startswith('.meta.playbook_ref'):
                err(p, 'ביטוי חסום: %s' % b)
        m = CODE_RE.search(s)
        if m:
            err(p, 'קוד פנימי או קוד מטבע בטקסט מוצג: %s' % m.group(0))
    vals = set()
    dv = (M.get('deal_value') or {}).get('amount')
    if dv is not None:
        vals.add(int(dv))
    for r in R:
        v = ((r.get('exposure') or {}).get('amount') or {}).get('value')
        if v is not None:
            vals.add(int(v))
    for p, s in _walk(reg):
        if SKIP_TEXT.search(p) or p.endswith('.quote') or '.research' in p:
            continue
        for m in re.finditer(r'(\d{1,3}(?:,\d{3})+|\d{4,})\s*ש"ח', s):
            v = int(m.group(1).replace(',', ''))
            if v not in vals:
                err(p, 'סכום בטקסט שאינו במרשם: %s' % m.group(0))

    # ---------- word budget ----------
    disp = []
    for r in R:
        disp += [r.get('name') or '', r.get('treatment_direction') or '']
        if r.get('anchors'):
            disp.append((r['anchors'][0].get('quote') or '')[:90])
        if r.get('severity_level') == 'critical':
            cd = r.get('critical_detail') or {}
            disp += [cd.get('what_happens') or '', cd.get('why_not_protected') or '']
    for d in reg.get('document_defects') or []:
        disp += [d.get('topic') or '', d.get('risk_created') or '', d.get('proposed_fix') or '',
                 d.get('prevails_basis') or ''] + [l.get('quote') or '' for l in d.get('locations') or []]
    for c in C:
        disp += [c.get('why_together') or '', c.get('breaking_fix') or '', c.get('neutralizes') or '']
    disp += bl + [S.get('deal_one_line') or ''] + [p.get('gap') or '' for p in P] + list(S.get('assumptions') or [])
    disp += [(k.get('what') or '') + ' ' + (k.get('consequence') or '') for k in KD]
    disp += [x.get('item') or '' for x in S.get('not_checked') or []]
    wc = len(' '.join(disp).split())
    if wc > WORDS_FAIL:
        err('words', 'גוף הדוח %d מילים, מעל %d' % (wc, WORDS_FAIL))
    elif wc > WORDS_WARN:
        warn('words', 'גוף הדוח %d מילים' % wc)
    return E, W


# ---------------- entity-report.json ----------------
BLOCKING_MATCH = ('registration_no', 'name_exact', 'alias', 'name_only')


def validate_entity_report(rep):
    """הערות 3.5, ההרחבה של שינוי 9: התאמת שם מוגדרת, חוסם רק בהתאמה, why חובה, בלי טוקנים, היעדר רישום
    של ישות זרה בישראל אינו ממצא, ומרשם שחסם (CAPTCHA, 403) הוא משימה לעורך הדין ולא עקיפה."""
    E = []
    meta = rep.get('meta') or {}
    country = ((meta.get('counterparty') or {}).get('country') or 'IL').upper()
    for i, c in enumerate(rep.get('confidence') or []):
        if c.get('label') not in ('high', 'medium'):
            E.append('confidence[%d]: תווית לא חוקית' % i)
        if not (c.get('why') or '').strip():
            E.append('confidence[%d]: why חובה, גם בוודאות גבוהה' % i)
    for i, f in enumerate(rep.get('red_flags') or []):
        mo = f.get('match_on')
        if f.get('blocking') and mo not in BLOCKING_MATCH:
            E.append('red_flags[%d]: חוסם רק בהתאמה (מספר רישום, שם זהה או כינוי רשמי), לא %r' % (i, mo))
        if mo == 'near' and f.get('blocking'):
            E.append('red_flags[%d]: התאמה קרובה אינה חוסמת' % i)
        if country != 'IL' and re.search(r'לא נמצא רישום', f.get('summary') or ''):
            E.append('red_flags[%d]: היעדר רישום בישראל של ישות זרה אינו ממצא' % i)
    for key in ('raw_copies', 'sources', 'lookups'):
        for i, x in enumerate(rep.get(key) or []):
            for f in ('url', 'typed_url', 'final_url'):
                if x.get(f) and has_secret(x[f]):
                    E.append('%s[%d].%s: כתובת עם טוקן או חתימה' % (key, i, f))
    for i, lk in enumerate(rep.get('lookups') or []):
        if lk.get('result') == 'blocked':
            hit = [n for n in rep.get('not_checked') or [] if (lk.get('source') or '\x00') in (n.get('item') or '')
                   or (n.get('why') or '').startswith('נחסם')]
            if not hit:
                E.append('lookups[%d]: מקור שנחסם בלי משימה לעורך הדין ב-not_checked' % i)
        if lk.get('bypass') or re.search(r'captcha.?solv|proxy|user.?agent.?spoof', json.dumps(lk), re.I):
            E.append('lookups[%d]: עקיפה של חסימה אסורה' % i)
        ua = lk.get('user_agent')
        if ua is not None and ua_problem(ua):
            E.append('lookups[%d]: %s' % (i, ua_problem(ua)))
    # סיכום C2, פער 4: הדומיין של כל מקור מול הרשימה המורשית, כמו ב-research.sources_checked
    for i, s in enumerate(rep.get('sources') or []):
        host = re.sub(r'^https?://([^/:]+).*$', r'\1', s.get('url') or '').lower()
        if not any(host == a or host.endswith('.' + a) for a in APPROVED_DOMAINS):
            E.append('sources[%d]: דומיין שאינו ברשימה המורשית: %s' % (i, host))
    # המהנדס, ממצא 15: חותמת זמן עם שעה היא ISO 8601 מלא עם היסט
    for p, s in _walk(rep):
        key = re.sub(r'\[\d+\]$', '', p).rsplit('.', 1)[-1]
        if TS_KEY.search(key) and s and 'T' in s and not ISO_TS.match(s):
            E.append('%s: חותמת זמן בלי שניות או בלי היסט: %s' % (p, s))
    for i, rc in enumerate(rep.get('raw_copies') or []):
        if rc.get('stored') not in (None, 'page', 'excerpt_window', 'match_window'):
            E.append('raw_copies[%d]: stored לא חוקי' % i)
        if (rc.get('full_size_bytes') or 0) > 200 * 1024 and rc.get('stored') in (None, 'page'):
            E.append('raw_copies[%d]: קובץ מלא גדול נשמר בתיקיית הלקוח' % i)
    return E


def _load(p):
    with io.open(p, encoding='utf-8') as fh:
        return json.load(fh)


def main(argv=None):
    ap = parser('בדיקת risk-register.json', out_required=False, out_help='דוח השגיאות (JSON); לא קובץ קלט')
    ap.add_argument('register')
    ap.add_argument('--corpus')
    ap.add_argument('--deal')
    ap.add_argument('--state')
    ap.add_argument('--profile')
    ap.add_argument('--playbook-status')
    ap.add_argument('--entity')
    ap.add_argument('--amendments', help='JSON: רשימת התיקונים הידועים (load_amendments)')
    a = ap.parse_args(argv)
    reg = _load(a.register)
    E, W = validate(reg, _load(a.corpus) if a.corpus else None, a.deal, _load(a.state) if a.state else None,
                    _load(a.profile) if a.profile else None, _load(a.playbook_status) if a.playbook_status else None,
                    _load(a.amendments) if a.amendments else None)
    if a.entity:
        E += ['entity ' + e for e in validate_entity_report(_load(a.entity))]
    sys.stdout.reconfigure(encoding='utf-8')
    for w in W:
        print('WARN', w)
    for e in E:
        print('ERR ', e)
    print('errors: %d warnings: %d' % (len(E), len(W)))
    if a.out:
        write_json(a.out, {'errors': E, 'warnings': W}, inputs=[x for x in (
            a.register, a.corpus, a.state, a.profile, a.playbook_status, a.entity, a.amendments) if x])
    return 1 if E else 0


if __name__ == '__main__':
    sys.exit(run(main))
