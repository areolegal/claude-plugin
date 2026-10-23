# -*- coding: utf-8 -*-
"""שער האיכות של הנושא ונותן, במצב עבודה ובמצב משלוח (מימוש ייחוס, הערות הנושא ונותן 4.8,
שינויים 16, 64א, 66 עד 70, 74 ו-75; 4.9, שינויים 80, 81, 83, 84, 86 ו-88).

כל כשל מקבל קוד קבוע (code), כך שאפשר לבדוק אותו ב-pytest ולהציג אותו בשורה אחת ללקוחה. הקודים זהים בעברית
ובאנגלית: נייר באנגלית נבדק באותן מחלקות, עם אוצר ביטויים באנגלית (lang).
קבוצות הבדיקה:
  PKG_*  החבילה: trackRevisions, מרחבי שמות, תאריכים, מחבר, צבע, מאפיינים, סדר סכמה, אורך נתיב (paths.PATH_LIMIT).
  RT_*   "דחה הכול" שווה לטיוטה שהתקבלה, ו"קבל הכול" שווה לנוסחי היעד.
  BUB_*  הבועות החיצוניות: מונחים אסורים, פסיקה, מקף ארוך, אורך, מספר שאינו בגוף, פתיח שחוזר; ולמה (4.9):
         BUB_WHY_MISSING (רכיב שמרע או מזיז את עמדת הצד שכנגד בלי משפט נימוק שקשור אליו) ו-BUB_CLAIM_FALSE
         (טענה בבועה שאינה נכונה מול הנוסח).
  COV_*  כל שינוי שהצד שכנגד רואה נמצא בבועה חיצונית של אותה פסקה (COV_CHANGE_WITHOUT_BUBBLE), וכל רכיב מהותי
         בשינוי נקרא בה בשמו (COV_UNCOVERED_CHANGE). גם שינוי טכני (כותרת, בלוק החתימה) מקבל בועה קצרה.
  CON_*  בועות שסותרות זו את זו, או את הנוסח.
  PH_*   מצייני מקום: שלנו חוסמים משלוח, שלהם מדווחים, ושדה ריק לחתימה (בעברית או באנגלית) אינו חוסם כשהמשתמש
         ענה "נשלים לפני החתימה".
  ID_*   מספר תאגיד שנכשל בבדיקה אינו נכנס לנוסח כאילו הוא תקין.
  GAP_*  פערים שהתגובה יוצרת בעצמה (כלל 2.22), מהמודול המשותף common/gap_checks.py, בעברית ובאנגלית.
  SAFE_*, LEGAL_*  נוסח בטוח שהרכיב אישר לעצמו, ופריט "טעון בדיקה משפטית" פתוח.
  STATE_* קובץ המצב (state_builder.validate_state), כשהוא נמסר במבנה המלא.
  RISK_FIX_*  שורות "לתיקון לפני שליחת התגובה" ממעריך הסיכונים שלא נסגרו (orchestrator/pre_send.py).
  STRUCT_* פסקה ריקה שהוספנו, ומספר מוקלד כפול בפרק.

אין בשער בדיקת אישורים ואין "מאשר" (החלטת מוצר 1, 14.10.2026).

    from orchestrator.qa_gate import run_gate, build_send_copy
    res = run_gate(work_path, received_path, mode='work', profile=profile, state=state, expected_accept=exp)
    res['passed'], res['failures']  # [{'code': ..., 'message': ..., 'where': ...}]

Python 3, lxml. בלי פנייה לרשת.
"""
import datetime as _dt
import json
import os
import re

from lxml import etree

from common import docx_tracked as dt
from common import gap_checks
from common import ids
from common import paths
from common.terms import terms_re
from orchestrator import pre_send

W = dt.W
LONG_DASH = re.compile('[\u2013\u2014]')
CASE_LAW = {'he': re.compile(r'ע"א|רע"א|בג"ץ|ע"ע|בש"א|דנ"א|ת"א\s*\d|פס"ד|הלכת\s'),
            'en': re.compile(r'\b[A-Z][A-Za-z]+ v\.? [A-Z][A-Za-z]+|\bU\.S\.C\.|\bF\.\s?(2d|3d|4th)\b|\bCal\. App\.')}
# 1.2.0: מונחים אסורים נמצאים רק כמילה שלמה, עם אותיות שימוש בעברית (common/terms.py): "ירוק" אינו נמצא
# בתוך "ירוקנו" או "פירוק". קודים וכתובות נבדקים כביטוי.
FORBIDDEN_TERMS = ('פלייבוק', 'playbook', 'קו אדום', 'red line', 'fallback', 'עמדת נסיגה', 'נסיגה', 'רזרבה',
                   'פלייבוק מוצע', 'מחקר שוק', 'industry standard', 'ירוק', 'צהוב', 'נדרשת הכרעתך', 'לאישורך',
                   'לא מוסכם', 'כלל קבוע', 'בכל ההתקשרויות שלנו')
FORBIDDEN_TERM_RE = terms_re(FORBIDDEN_TERMS, regex_terms=(r'market (practice|standard)',))
FORBIDDEN_CODES = re.compile(r'\b(R|V|Q|SEG|DS|LG|PB|OS|EMP)-?\d+\b|\b[AR][123]\b|\bN1\b|https?://|APR-|'
                             r'קטגוריה\s*\d', re.I)


class _Either:
    # search() על שני ביטויים: המונחים (גבולות מילה) והקודים

    def __init__(self, *rxs):
        self.rxs = rxs

    def search(self, text):
        hits = [m for m in (rx.search(text) for rx in self.rxs) if m]
        return min(hits, key=lambda m: m.start()) if hits else None


FORBIDDEN_ALWAYS = _Either(FORBIDDEN_TERM_RE, FORBIDDEN_CODES)
FORBIDDEN_UNLESS_CLAIM = terms_re(('מדיניות', 'policy'))
PRACTICE_OPENING = {'he': re.compile(r'^\s*(אנחנו נוהגים|אנו נוהגים|כמקובל|בהתאם לנוהג|כנהוג)'),
                    'en': re.compile(r'^\s*(As is customary|In line with (our|market) practice|As standard|'
                                     r'We (normally|usually|always) )', re.I)}
OUR_PH = re.compile(r'\[להשלים\]|\[to be completed\]|\[●\]|\[\s*\d[\d,.\s]*\]|\[[^\]\n]{1,40}\]')
UNDERSCORES = re.compile(r'_{3,}')
THEIR_PH = re.compile(r'_{3,}|\[[^\]\n]{0,40}\]')
COMPANY_NO = {'he': re.compile(r'(ח\.?\s?פ\.?|ע\.?\s?מ\.?|מספר (?:חברה|תאגיד))\s*:?\s*\[?\s*(?P<num>\d[\d\s\-]{5,12}\d)\s*\]?'),
              'en': re.compile(r'(company (?:number|no\.?)|registration (?:number|no\.?)|reg\. no\.)\s*:?\s*\[?\s*'
                               r'(?P<num>\d[\d\s\-]{5,12}\d)\s*\]?', re.I)}
SENT_END = re.compile(r'[.?!](\s|$)')

# ------------------------------------------------------------------------------------------------ תפקידי סעיף
# טקסונומיה כללית של תפקידי סעיף, שחלה בכל סוג הסכם (שירותים, סודיות, SaaS ורישוי, אספקה ורכש, הפצה, שכירות,
# העסקה, מיקור חוץ, הלוואה). היא משמשת רק את מנגנון הבועות: מה נקרא בשמו בבועה, ומה דורש משפט נימוק. אין בה שיקול
# משפטי של סוג הסכם מסוים, ואין בה עובדה של לקוחה (החלטה 22).
# שם: (טריגר בעברית, שם בבועה בעברית, טריגר באנגלית, שם בבועה באנגלית, האם שינוי בו מרע או מזיז את עמדת הצד שכנגד)
FUNCTIONS = {
    'מחיר ותמורה': (r'תמורה|מחיר|דמי (שכירות|רישיון|מנוי|תחזוקה|ניהול|שימוש)|תעריף|הוצאות',
                    r'תמור|מחיר|דמי|תעריפ|תעריף|הוצא|עלות|תשלום|ישול|תשלמו',
                    r'\bfees?\b|\bprice|\brent\b|\bcharges?\b|consideration|expenses',
                    r'fee|price|rent|charge|consideration|expens|cost', True),
    'מועד התשלום': (r'(ישולם|ישולמו|תשולם|משולמת|ישלם|לשלם)[^.\n]{0,60}\d+\s*(יום|ימים|ימי עסקים)|שוטף',
                    r'\d+\s*(יום|ימים)|ימי עסקים|ימים|שוטף',
                    r'(payable|paid|pay)[^.\n]{0,60}\d+\s*(calendar |business )?days|net\s*\d+',
                    r'\d+\s*(calendar |business )?days|\bdays\b|\bnet\b', True),
    'ריבית והצמדה': (r'ריבית|פיגורים|הצמדה', r'ריבית|פיגור|הצמד',
                     r'interest|late (payment )?(fee|charge)|indexation', r'interest|late|index', True),
    'קיזוז ועיכבון': (r'לקזז|קיזוז|עיכבון|לעכב', r'קיז|לקזז|עיכבון|לעכב',
                      r'set[- ]?off|withhold|\blien\b', r'set[- ]?off|withhold|lien', True),
    'מס': (r'מע"מ|מס ערך מוסף|ניכוי מס', r'מע"מ|מס', r'\bVAT\b|\btax', r'VAT|tax', True),
    'הגבלת אחריות': (r'תקרה|מוגבלת לסכום|לא תעלה על|נזק עקיף|תוצאתי|לא יישא באחריות',
                     r'תקר|הגבל|מוגבל|לא תעלה|עקיף|תוצאתי|אחריות|פטור',
                     r'liabilit[^.\n]{0,60}(limited|exceed|cap)|indirect|consequential|not be liable',
                     r'cap|limit|liab|indirect|consequential', True),
    'שיפוי וערבות': (r'ישפה|שיפוי|ערבות|ערובה|דרישה ראשונה|בטוחה|פיקדון',
                     r'שיפוי|ישפה|לשפות|ערבות|ערובה|דרישה|בטוחה|פיקדון',
                     r'indemnif|guarantee|security deposit|first demand|letter of credit',
                     r'indemn|guarant|deposit|demand|security', True),
    'ביטוח': (r'ביטוח|פוליסה', r'ביטוח|פוליס', r'insurance|policy of insurance', r'insur', True),
    'קניין רוחני': (r'קניין רוחני|זכויות יוצרים|בעלות|מרגע היווצרם|ימחה',
                    r'קניין|זכויות|בעלות|שייכ|המח|שלו|שלכם',
                    r'intellectual property|ownership|\bowns?\b|assigns? all', r'intellectual|own|assign', True),
    'היקף הרישיון': (r'להעברה|רישיונות משנה|רישיון משנה|בלתי חוזר|לצמיתות|כלל-עולמי',
                     r'להעביר|להעברה|רישיונות משנה|רישיון משנה|בלתי חוזר|לצמיתות|כלל-עולמי',
                     r'transferable|sublicens|irrevocable|perpetual|worldwide',
                     r'transfer|sublicens|irrevocab|perpetual|worldwide', True),
    'סודיות': (r'ישמור בסוד|חובת (ה)?סודיות|ישמור על סודיות|לא יגלה', r'סוד',
               r'in confidence|confidentiality obligations|shall not disclose|keep[^.\n]{0,30}confidential', r'confiden',
               False),
    'מידע אישי ואבטחת מידע': (r'מידע אישי|פרטיות|אבטחת (ה)?מידע|הסכם עיבוד|מחוץ ל(מדינה|ישראל)|לחו"ל',
                              r'מידע אישי|פרטיות|אבטח|עיבוד|מחוץ ל|חו"ל|העבר',
                              r'personal data|privacy|data processing|security incident|de-identif|outside the country',
                              r'personal|privacy|data|security|de-identif|transfer|abroad|outside', False),
    'מחיקה והחזרה': (r'ימחק|ישמיד|מחיקת|השמדת|יחזיר', r'מחק|השמד|יושמד|יוחזר|החזר',
                     r'\bdelete|\bdestroy|\breturn (or|all)', r'delet|destroy|return', True),
    'הגבלת תחרות ובלעדיות': (r'מתחרה|תחרות|(?<!לא )בלעדי', r'מתחר|תחרות|בלעדי|ניגוד עניינים',
                             r'\bcompet(e|es|ing|itor|itors|ition)\b|(?<!non-)exclusiv', r'compet|exclusiv|conflict',
                             True),
    'איסור שידול': (r'ישדל|שידול', r'שידול|ישדל|לגייס', r'solicit', r'solicit', True),
    'הסבה וקבלני משנה': (r'להסב|הסבה|להמחות|המחאה|קבלני? משנה', r'הסב|המח|קבלנ',
                         r'\bassign|subcontract', r'assign|subcontract', True),
    'סיום ותקופה': (r'רשאי לסיים|לבטל את ההסכם|בתוקפו|הארכ|חידוש|הודעה מוקדמת',
                    r'סיום|לסיים|לבטל|תקופ|הארכ|חידוש|הודעה',
                    r'terminat|renew|term of this|notice period|prior notice', r'terminat|renew|term|notice', True),
    'דין ושיפוט': (r'יחול (ה)?דין|סמכות (ה)?שיפוט|בוררות|סעד (זמני|דחוף)|צו מניעה',
                   r'דין|שיפוט|בורר|סעד|בית משפט|בתי המשפט',
                   r'governed by|jurisdiction|venue|arbitrat|injunctive|interim relief',
                   r'law|jurisdiction|venue|court|arbitrat|relief', True),
    'שפה גוברת': (r'הנוסח (העברי|האנגלי)', r'נוסח|שפה|גובר', r'prevail|translation', r'prevail|translat', False),
    'טיב ורמת שירות': (r'אחריות ל(טיב|תקינות)|רמת (ה)?שירות|פיצוי מוסכם|קנס|כמות שהוא|במיומנות',
                       r'טיב|תקינות|רמת|פיצוי|קנס|כמות שהוא|מיומנות|מקצועיות',
                       r'warrant|"as is"|service level|liquidated damages|penalt',
                       r'warrant|as is|service level|liquidated|penalt', True),
    'שימוש במידע וכלים': (r'בינה מלאכותית|לאימון', r'בינה מלאכותית|אימון|כלי',
                          r'artificial intelligence|\bAI\b|\btrain', r'artificial|AI|train|tool', True),
    'ביקורת ופיקוח': (r'ישתף פעולה|זכות ביקורת|לערוך ביקורת|לבקר את', r'מבקר|ביקורת|רשו|פיקוח|שיתוף פעולה|תשתפו',
                      r'right to (audit|inspect)|shall cooperate|audit rights', r'audit|inspect|regulat|cooperat', True),
}
CONCEPTS_HE = {k: (v[0], v[1], v[4]) for k, v in FUNCTIONS.items()}
CONCEPTS_EN = {k: (v[2], v[3], v[4]) for k, v in FUNCTIONS.items()}
CONCEPTS = CONCEPTS_HE  # תאימות לאחור
# תפקיד שהשינוי בו יכול להיות מספר בלבד (30 שהפך ל-60): הטריגר נבדק גם במשפט שהשתנה, ולא רק בטקסט שהוכנס
NUMERIC_FUNCTIONS = ('מועד התשלום',)
REASON = {'he': re.compile(r'(?<![\u05d0-\u05ea])ו?(כדי|כי|שכן|לכן|בשל|בגלל|נועד\w*)(?![\u05d0-\u05ea])|'
                           r'מאחר ש|מאחר ו|משום ש|מפני ש|הואיל ו|על כן|כך ש|כדי ש'),
          'en': re.compile(r'\b(because|so that|since|in order to|to ensure|to avoid|so as to|given that|otherwise)\b|'
                           r'\bas (the|this|it|we|you|our|your|these|those|a|an)\b', re.I)}
REASON_LEAD = {'he': re.compile(r'^\s*(זאת\s+)?(כדי|כי|מאחר|משום|מפני|הואיל|שכן|לכן|הסיבה)'),
               'en': re.compile(r'^\s*(This is |That is |This )?(because|so that|since|in order|to ensure|the reason)', re.I)}
RIGHT_WORDS = {'he': r'רשאי|זכאי|תהיה זכות', 'en': r'\bmay\b|entitled|right to'}
DELETION_CLAIM = {'he': re.compile(r'^\s*(מחקנו|הסרנו)'), 'en': re.compile(r'^\s*We (have )?(deleted|removed)', re.I)}
KNOWN_CLAIM = {'he': re.compile(r'ידוע(ה|ים|ות)? מראש|סכום קבוע מראש'),
               'en': re.compile(r'known in advance|fixed in advance|known up front|a fixed amount', re.I)}
# תקרה שבסיסה "התמורה הכוללת" או "המחיר המוסכם" בלי סכום: טענה שהבסיס "ידוע מראש" אינה נכונה מול הנוסח
CAP_RX = {'he': (r'אחריות', r'מוגבלת|תקרה|לא תעלה|לא יעלה',
                 r'(ה)?(תמורה|מחיר|דמי \S+) (ה)?(כוללת|כולל|מוסכמת|מוסכם)',
                 r'\d[\d,]*\s*(ש"ח|₪|שקלים|אלף|דולר|אירו)|(הנקוב|הנקובה|הקבוע|הקבועה)[^.\n]{0,15}בסעיף'),
          'en': (r'liabilit', r'limited to|shall not exceed|capped at',
                 r'(total|agreed|aggregate) (fees|consideration|contract value|price|rent|charges)',
                 r'(\$|USD|NIS|ILS|EUR|€|£)\s?\d|\d[\d,]*\s*(USD|NIS|ILS|EUR)|(set out|stated|specified) in (Section|Clause)')}


def _f(code, message, where=None):
    return {'code': code, 'message': message, 'where': where}


def _sentences(text):
    return [s.strip() for s in re.split(r'(?<=[.?!;])\s+', text) if s.strip()]


def _parse_local(s):
    return _dt.datetime.strptime(s, dt.DATE_FMT)


def concepts_for(lang):
    return CONCEPTS_EN if lang == 'en' else CONCEPTS_HE


def author_for(profile, lang):
    """מחבר הסימונים והבועות. בנייר באנגלית, lawyer_name_en מהפרופיל כשיש (צש3-14)."""
    if lang == 'en' and profile.get('lawyer_name_en'):
        return profile['lawyer_name_en']
    return profile['lawyer_name']


def initials_for(profile, lang='he'):
    """ראשי התיבות של הבועות: lawyer_initials מהפרופיל, ואחרת האות הראשונה של כל מילה בשם המחבר (סנ1-4)."""
    if profile.get('lawyer_initials'):
        return profile['lawyer_initials']
    words = [w for w in author_for(profile, lang).replace('"', ' ').split() if w and w[0].isalpha()]
    return ''.join(w[0] for w in words[:3]).upper() or 'X'


# --------------------------------------------------------------------------------------- חבילה
def check_package(parts, root, profile, received_comment_ids, window, work_path=None, author=None, received_authors=()):
    F, info = [], {}
    author = author or profile['lawyer_name']
    st = etree.fromstring(parts['word/settings.xml'])
    if st.find(W + 'trackRevisions') is None:
        F.append(_f('PKG_TRACK_REVISIONS', 'w:trackRevisions חסר ב-settings.xml'))
    if st.find(W + 'trackChanges') is not None:
        F.append(_f('PKG_TRACK_CHANGES_INVALID', 'w:trackChanges אינו רכיב בסכמה'))
    for name, data in parts.items():
        if not name.endswith('.xml') or not name.startswith('word/'):
            continue
        try:
            r = etree.fromstring(data)
        except etree.XMLSyntaxError as e:
            F.append(_f('PKG_XML', 'XML פגום: %s' % e, name))
            continue
        ign = (r.get(dt.MC_IGNORABLE) or '').split()
        missing = [p for p in ign if p not in r.nsmap]
        if missing:
            F.append(_f('PKG_NAMESPACE_UNDECLARED', 'קידומות ב-mc:Ignorable שאינן מוצהרות: %s' % missing, name))
    revs = [e for e in root.iter(W + 'ins', W + 'del')]
    ours = [e for e in revs if e.get(W + 'author') == author]
    # השינויים הפתוחים של הצד שכנגד מגיעים עם הטיוטה, ונשארים בקובץ שלנו כמו שהם. מחבר אחר הוא תקלה רק כשאינו
    # בטיוטה שהתקבלה. תיקון מקומי של ניל, לדיווח לענבל: לפני כן כל טיוטה עם שינויים פתוחים נכשלה כאן (20.10.2026)
    others = {e.get(W + 'author') for e in revs} - {author} - set(received_authors or ())
    if others:
        F.append(_f('PKG_AUTHOR', 'סימוני מעקב במחבר אחר: %s' % sorted(x for x in others if x)))
    lo, hi = window
    tz_off = None
    for e in ours:
        d, u = e.get(W + 'date'), e.get(dt.DATE_UTC_ATTR)
        if not d or not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ', d):
            F.append(_f('PKG_DATE_FORMAT', 'w:date בתבנית לא נכונה: %r' % d))
            break
        if not u or not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ', u):
            F.append(_f('PKG_DATE_UTC', 'w16du:dateUtc חסר או לא תקין: %r' % u))
            break
        loc = _parse_local(d)
        if not lo <= loc <= hi:
            F.append(_f('PKG_DATE_RANGE', 'תאריך שאינו של ההרצה: %s' % d))
            break
        off = loc - _parse_local(u)
        if tz_off is None:
            tz_off = off
        expected = _dt.datetime.now().astimezone().utcoffset()
        if abs((off - expected).total_seconds()) > 60 or off != tz_off:
            F.append(_f('PKG_DATE_UTC', 'הפרש בין w:date ל-dateUtc אינו הפרש השעון המקומי: %s / %s' % (d, u)))
            break
    info['revisions'] = len(ours)
    info['distinct_dates'] = len({e.get(W + 'date') for e in ours})
    hl_ins = [h for e in ours if local_tag(e) == 'ins' for h in e.iter(W + 'highlight')]
    if hl_ins:
        F.append(_f('PKG_HIGHLIGHT', 'צבע בטקסט שהוכנס: %d' % len(hl_ins)))
    core = parts.get('docProps/core.xml', b'').decode('utf-8')
    app = parts.get('docProps/app.xml', b'').decode('utf-8')
    if 'python-docx' in core + app:
        F.append(_f('PKG_METADATA', '"python-docx" במאפייני הקובץ'))
    if dt.esc(author) not in core and author not in core:
        F.append(_f('PKG_METADATA', 'המחבר במאפייני הקובץ אינו עורך הדין מהפרופיל'))
    for m in re.finditer(r'<dcterms:(created|modified)[^>]*>([^<]+)<', core):
        try:
            when = _dt.datetime.strptime(m.group(2)[:19], '%Y-%m-%dT%H:%M:%S')
            if when < lo - _dt.timedelta(days=1):
                F.append(_f('PKG_METADATA', 'תאריך %s במאפיינים קודם להרצה: %s' % (m.group(1), m.group(2))))
        except ValueError:
            pass
    if dt.audit_schema_order(root):
        F.append(_f('PKG_SCHEMA_ORDER', 'סדר סכמה שגוי ב-%d מכלים' % dt.audit_schema_order(root)))
    if work_path and len(os.path.abspath(work_path)) > paths.PATH_LIMIT:
        F.append(_f('PKG_PATH_LENGTH', 'נתיב של %d תווים (הגבול %d)' % (len(os.path.abspath(work_path)),
                                                                       paths.PATH_LIMIT)))
    comments = dt.read_comments(parts)
    for c in comments:
        if c['id'] in received_comment_ids:
            continue
        if c['author'] not in (author, dt.INTERNAL_AUTHOR):
            F.append(_f('BUB_UNKNOWN_AUTHOR', 'בועה במחבר לא מוכר: %s' % c['author'], c['id']))
        if c['author'] == author and profile.get('lawyer_initials') and c['initials'] != profile['lawyer_initials']:
            F.append(_f('BUB_INITIALS', 'ראשי תיבות שאינם מהפרופיל: %s' % c['initials'], c['id']))
    return F, info


def local_tag(e):
    return dt.local(e.tag)


# --------------------------------------------------------------------------------------- בועות
def check_bubbles(ext, accept_text, state, reject_text='', lang='he'):
    F = []
    body_text = accept_text + '\n' + reject_text
    claim = bool((state or {}).get('policy_claim_allowed'))
    facts = list((state or {}).get('deal_context', {}).get('facts', [])) if state else []
    facts += list(((state or {}).get('meta') or {}).get('deal_context', {}).get('facts', [])) if state else []
    hidden = [str(f.get('fact')) for f in facts if f.get('disclosure') in ('drafting_only', 'internal_only')]
    openers = {}
    for c in ext:
        t = c['text']
        m = FORBIDDEN_ALWAYS.search(t)
        if m:
            F.append(_f('BUB_FORBIDDEN', 'מונח פנימי בבועה: "%s"' % m.group(0), c['id']))
        m = None if claim else FORBIDDEN_UNLESS_CLAIM.search(t)
        if m:
            F.append(_f('BUB_FORBIDDEN', '"%s" בבועה בלי טענת מדיניות מאושרת' % m.group(0), c['id']))
        if CASE_LAW['he'].search(t) or CASE_LAW['en'].search(t):
            F.append(_f('BUB_CASE_LAW', 'הפניה לפסיקה בבועה', c['id']))
        if LONG_DASH.search(t):
            F.append(_f('BUB_LONG_DASH', 'מקף ארוך בבועה', c['id']))
        if len(SENT_END.findall(t + ' ')) > 5:
            F.append(_f('BUB_SENTENCES', 'יותר מחמישה משפטים', c['id']))
        if PRACTICE_OPENING[lang].search(t) or PRACTICE_OPENING['he'].search(t):
            F.append(_f('BUB_PRACTICE_OPENING', 'בועה שנפתחת במשפט נוהג', c['id']))
        for num in re.findall(r'\d[\d,]*', t):
            if num.strip(',') not in body_text:
                F.append(_f('BUB_NUMBER_NOT_IN_BODY', 'המספר %s אינו בנוסח' % num, c['id']))
        for h in hidden:
            if h and h in t:
                F.append(_f('BUB_DISCLOSURE', 'עובדה שסווגה לנוסח בלבד או פנימית מופיעה בבועה', c['id']))
        k = ' '.join(t.split()[:2])
        openers[k] = openers.get(k, 0) + 1
    limit = max(2, len(ext) // 3)
    rep = {k: v for k, v in openers.items() if v > limit}
    if rep:
        F.append(_f('BUB_REPEATED_OPENER', 'פתיח זהה ביותר משליש מהבועות: %s' % rep))
    return F


def _para_accept(p):
    return ''.join(dt._node_text(n) for n, anc in dt._text_nodes(p) if dt.local(n.tag) != 'delText' and 'del' not in anc)


def _tied_reason(sents, idx, lang):
    if REASON[lang].search(sents[idx]):
        return True
    return idx + 1 < len(sents) and bool(REASON_LEAD[lang].search(sents[idx + 1]))


def _changed_sentences(p, author):
    """המשפטים בהטלת "קבל הכול" שיש בהם קטע שהכנסנו (גם כשהקטע הוא רק מספר, למשל 30 שהפך ל-60)."""
    pieces = []
    for el in p.iter(W + 'ins'):
        if el.getparent() is not None and dt.local(el.getparent().tag) == 'rPr' or el.get(W + 'author') != author:
            continue
        txt = ''.join(n.text or '' for n in el.iter(W + 't')).strip()
        if len(txt) >= 2:
            pieces.append(txt)
    acc = _para_accept(p)
    return '\n'.join(s for s in _sentences(acc) if any(x in s for x in pieces))


def changed_paragraphs(root, author):
    """(אינדקס, פסקה, טקסט שהוכנס, טקסט שנמחק, המשפטים שהשתנו) לכל פסקה שיש בה שינוי שלנו. טריגר של רכיב שמרע נבדק
    בנוסח שהוכנס, בנוסח שנמחק, ובמשפטים שהשתנו, כך שגם שינוי של מספר בלבד (30 ימים שהפכו ל-60) נתפס."""
    out = []
    for i, p in enumerate(dt.body_paragraphs(root)):
        ins, dele = dt.revision_text(p, 'ins', author), dt.revision_text(p, 'del', author)
        if ins.strip() or dele.strip():
            if _is_heading(p):
                ins, dele = '', ''  # כותרת: שינוי טכני. הבועה הקצרה נבדקת, ולא תפקידי סעיף
            out.append((i, p, ins, dele, _changed_sentences(p, author)))
    return out


def _is_heading(p):
    """פסקה שהוספנו כולה, קצרה ובלי סימן פיסוק של משפט: כותרת פרק (structural)."""
    acc = _para_accept(p).strip()
    return dt._mark(p) == 'ins' and 0 < len(acc) < 60 and not re.search(r'[.;:]', acc)


def check_coverage(root, ext_by_para, author, lang='he'):
    """(1) כל שינוי שהצד שכנגד רואה נמצא בבועה חיצונית של אותה פסקה, גם שינוי טכני (החלטת מוצר 2).
    (2) כל רכיב מהותי שהוכנס או נמחק בפסקה נקרא בבועה בשמו."""
    F = []
    conc = concepts_for(lang)
    for i, p, ins, dele, ctx in changed_paragraphs(root, author):
        bubble = ' '.join(ext_by_para.get(i, []))
        hit = [name for name, (trig, _, worse) in conc.items()
               if re.search(trig, ins) or re.search(trig, dele) or (name in NUMERIC_FUNCTIONS and re.search(trig, ctx))]
        if not bubble:
            what = ', '.join(hit) if hit else 'שינוי טכני (%s)' % (_para_accept(p) or dele)[:40]
            F.append(_f('COV_CHANGE_WITHOUT_BUBBLE', 'שינוי בלי בועה חיצונית: %s' % what, i))
            continue
        missing = [name for name in hit if not re.search(conc[name][1], bubble, re.I if lang == 'en' else 0)]
        if missing:
            F.append(_f('COV_UNCOVERED_CHANGE', 'הבועה אינה מתארת: %s' % ', '.join(missing), i))
    return F


def check_bubble_why(root, ext_by_para, author, accept_text, lang='he', context=None):
    """החלטת מוצר 2 (14.10.2026): כל בועה חיצונית מסבירה למה, ולא רק מה.
    - BUB_WHY_MISSING: רכיב שמרע או מזיז את עמדת הצד שכנגד נקרא בבועה, ואין משפט נימוק שקשור אליו (מחבר נימוק
      באותו משפט, או משפט הבא שנפתח בנימוק). כך גם זכות שלהם שמחקנו.
    - BUB_CLAIM_FALSE: טענה בבועה שאינה נכונה מול הנוסח: "ידוע מראש" על בסיס תקרה שאינו סכום; "מחקנו" כשלא נמחק
      דבר. הבדיקה כללית לכל סוג הסכם: היא משווה את הטענה לנוסח, ואינה שוקלת את התוכן המשפטי."""
    F = []
    conc = concepts_for(lang)
    I = re.I if lang == 'en' else 0
    for i, p, ins, dele, ctx in changed_paragraphs(root, author):
        bubbles = ext_by_para.get(i, [])
        if not bubbles:
            continue
        sents = [s for b in bubbles for s in _sentences(b)]
        hit = [name for name, (trig, _, worse) in conc.items()
               if worse and (re.search(trig, ins) or re.search(trig, dele) or
                             (name in NUMERIC_FUNCTIONS and re.search(trig, ctx)))]
        if dt._mark(p) in ('del', 'both') and re.search(RIGHT_WORDS[lang], dele, I):
            hit.append('__deleted_right__')
        for name in hit:
            rx = (r'מחקנו|הסרנו|נמחק|deleted|removed|struck') if name == '__deleted_right__' else conc[name][1]
            idx = [k for k, s in enumerate(sents) if re.search(rx, s, I)]
            if not idx:
                continue  # לא נקרא בשמו: COV_UNCOVERED_CHANGE
            if not any(_tied_reason(sents, k, lang) for k in idx):
                label = 'זכות שלהם שנמחקה' if name == '__deleted_right__' else name
                F.append(_f('BUB_WHY_MISSING', 'אין משפט נימוק ל: %s' % label, i))
        acc = _para_accept(p)
        L, M, B, R = CAP_RX[lang]
        for s in sents:
            if KNOWN_CLAIM[lang].search(s) and re.search(r'תקר|cap|limit', s, I):
                cap_sents = [x for x, _, _ in gap_checks.sentences(acc) if re.search(L, x, I) and re.search(M, x, I)]
                if any(re.search(B, x, I) and not re.search(R, x, I) for x in cap_sents):
                    F.append(_f('BUB_CLAIM_FALSE', 'הבועה אומרת שבסיס התקרה ידוע מראש, והנוסח קובע רק תקרה ולא סכום', i))
            if DELETION_CLAIM[lang].search(s) and not dele.strip():
                F.append(_f('BUB_CLAIM_FALSE', 'הבועה אומרת שמחקנו, ובפסקה לא נמחק דבר', i))
    return F


def check_contradictions(ext, accept_text, lang='he'):
    F = []
    all_b = '\n'.join(c['text'] for c in ext)
    if (re.search(r'(טעות|שגיאה)[^.\n]{0,20}תרגום|תרגום (שגוי|לקוי|מכונה)|תורגם בטעות', all_b)
            and re.search(r'הנוסח העברי[^.\n]{0,80}(המחייב|גובר)', accept_text + '\n' + all_b)):
        F.append(_f('CON_CONTRADICTION', 'בועה טוענת לתרגום שגוי, ובאותו סבב הנוסח העברי נקבע מחייב או גובר'))
    if (re.search(r'mistranslat|translation error|incorrectly translated', all_b, re.I)
            and re.search(r'prevails over any[^.\n]{0,60}translation', accept_text, re.I)):
        F.append(_f('CON_CONTRADICTION', 'בועה טוענת לתרגום שגוי, והנוסח החתום גובר על כל תרגום'))
    if (re.search(r'מוגן ב(תנאי התשלום|הסכם)', all_b)
            and re.search(r'(שלילת|ישלול)[^.\n]{0,10}עיכבון|לא יעכב[^.\n]{0,80}מחלוקת', accept_text)
            and not re.search(r'רשאי להשהות|זכות (ה)?השהי', accept_text)):
        F.append(_f('CON_CONTRADICTION', 'בועה נשענת על הגנת תשלום שהתגובה עצמה הסירה'))
    if (re.search(r'protected by the payment terms', all_b, re.I) and re.search(r'shall not (withhold|suspend)', accept_text, re.I)
            and not re.search(r'may suspend|right to suspend', accept_text, re.I)):
        F.append(_f('CON_CONTRADICTION', 'בועה נשענת על הגנת תשלום שהתגובה עצמה הסירה'))
    return F


def check_reasoning_warnings(ext):
    W_ = []
    for c in ext:
        if re.search(r'הדין (מטיל|קובע)[^.\n]{0,20}ממילא|חלה ממילא', c['text']) or \
                re.search(r'(law|statute) (already )?(requires|imposes)[^.]{0,40}(anyway|in any event)|applies anyway',
                          c['text'], re.I):
            W_.append(_f('BUB_LAW_ANYWAY', 'נימוק "חובה שהדין מטיל ממילא" מזמין את התשובה שאין צורך בסעיף', c['id']))
    return W_


# --------------------------------------------------------------------------------------- מצייני מקום וזיהוי
def check_placeholders(root, ext, author, state, mode):
    F, report = [], {'ours': [], 'theirs': [], 'signing_blanks': []}
    allowed_blank = any((v or {}).get('status') == 'signing_blank'
                        for v in ((state or {}).get('entity_details') or {}).values())
    blanks = tuple(ids.SIGNING_BLANKS.values())
    for i, p in enumerate(dt.body_paragraphs(root)):
        ins = dt.revision_text(p, 'ins', author)
        rest = ins
        for blank in blanks:
            while blank in rest:
                if allowed_blank:
                    report['signing_blanks'].append({'para': i, 'text': blank})
                else:
                    report['ours'].append({'para': i, 'text': blank, 'why': 'אין תשובה "נשלים לפני החתימה"'})
                rest = rest.replace(blank, '', 1)
        for m in OUR_PH.finditer(rest):
            report['ours'].append({'para': i, 'text': m.group(0)})
        for m in UNDERSCORES.finditer(rest):
            report['ours'].append({'para': i, 'text': m.group(0)})
        plain = ''.join(n.text or '' for n in p.iter(W + 't')
                        if not any(dt.local(a.tag) == 'ins' for a in n.iterancestors()))
        for m in THEIR_PH.finditer(plain):
            report['theirs'].append({'para': i, 'text': m.group(0)})
    for c in ext:
        for m in OUR_PH.finditer(c['text']):
            report['ours'].append({'comment': c['id'], 'text': m.group(0)})
    if mode == 'send' and report['ours']:
        F.append(_f('PH_OURS', 'מציין מקום שלנו בעותק למשלוח: %s' % [x['text'] for x in report['ours']]))
    return F, report


def check_identifiers(root, author, profile, lang='he'):
    F, W_ = [], []
    prof = ids.validate_company_number(profile.get('organization_id')) if profile.get('organization_id') else None
    rx = COMPANY_NO[lang]
    for i, p in enumerate(dt.body_paragraphs(root)):
        ins = dt.revision_text(p, 'ins', author)
        for m in rx.finditer(ins):
            v = ids.validate_company_number(m.group('num'))
            if not v['valid']:
                F.append(_f('ID_COMPANY_NUMBER', 'מספר תאגיד שנכשל בבדיקה (%s) הוכנס לנוסח: %s'
                            % (v['reason'], m.group('num')), i))
            elif prof and prof['valid'] and v['number'] != prof['number']:
                F.append(_f('ID_COMPANY_NUMBER', 'מספר תאגיד שונה מהפרופיל: %s' % m.group('num'), i))
        plain = ''.join(dt._node_text(n) for n, anc in dt._text_nodes(p)
                        if 'ins' not in anc and 'del' not in anc and dt.local(n.tag) != 'delText')
        for m in rx.finditer(plain):
            if not ids.validate_company_number(m.group('num'))['valid']:
                W_.append(_f('ID_THEIR_NUMBER', 'מספר תאגיד בנוסח שלהם נכשל בבדיקה: %s' % m.group('num'), i))
    return F, W_


# --------------------------------------------------------------------------------------- פערים שהתגובה יוצרת
def touched_paragraphs(root, author):
    """הפסקאות (בהטלת "קבל הכול") שיש בהן נוסח שהכנסנו."""
    out = []
    for p in dt.body_paragraphs(root):
        if dt.revision_text(p, 'ins', author).strip():
            out.append(_para_accept(p))
    return out


def check_self_created_gaps(root, author, accept_text, lang='he', context=None):
    """כלל 2.22 מהמודול המשותף (common/gap_checks.py): על כל פסקה שהכנסנו, ועל ההסכם כולו."""
    F, seen = [], set()
    ctx = dict(context or {})
    ctx['accept_text'] = accept_text
    ours = touched_paragraphs(root, author)
    for t in ours:
        for x in gap_checks.check_wording(t, lang, context=ctx):
            k = (x['code'], x['message_he'], t[:60])
            if k not in seen:
                seen.add(k)
                F.append(_f(x['code'], x['message_he'], t[:60]))
    for x in gap_checks.check_document(accept_text, ours, lang, ctx):
        k = (x['code'], x['message_he'], None)
        if k not in seen:
            seen.add(k)
            F.append(_f(x['code'], x['message_he']))
    return F


def waived_gap_codes(state):
    """קודי פער שהמשתמש הכריע במפורש לוותר עליהם (ויתור מכוון עם user_decision מפורש ו-gap_codes)."""
    out = set()
    for w in (state or {}).get('deliberate_concessions', []):
        if (w.get('user_decision') or {}).get('answer_kind') == 'explicit':
            out.update(w.get('gap_codes', []))
    return out


def check_state(state, mode):
    F, W_ = [], []
    for cl in (state or {}).get('clauses', []):
        cid = cl.get('clause_id')
        sw = cl.get('safe_wording') or {}
        if sw:
            flags = (sw.get('not_worse_than_position'), sw.get('not_worse_than_default'))
            ref = sw.get('statute_ref') or {}
            if True in flags and not (ref.get('source_id') and ref.get('url') and ref.get('verified_in') == 'playbook'):
                F.append(_f('SAFE_WORDING_SELF_CERTIFIED', 'נוסח בטוח סומן "אינו מרע" בלי מקור מאומת בפלייבוק', cid))
        lr = cl.get('legal_review') or {}
        if cl.get('legal_review_required') and not (lr.get('done_by') and lr.get('done_at')):
            (F if mode == 'send' else W_).append(_f('LEGAL_REVIEW_OPEN', 'נוסח "טעון בדיקה משפטית" שלא נבדק', cid))
    if state and 'meta' in state:
        from orchestrator.state_builder import validate_state
        for e in validate_state(state):
            (F if mode == 'send' else W_).append(_f(e['code'], e['message'], e['where']))
    return F, W_


def check_structure(root, author):
    F = []
    for i, p in enumerate(dt.body_paragraphs(root)):
        if dt._mark(p) == 'ins':
            if not _para_accept(p).strip():
                F.append(_f('STRUCT_EMPTY_PARAGRAPH', 'פסקה ריקה שהוספנו', i))
    num = re.compile(r'^\s*(\d+[\u05d0-\u05ea]?)[.)]\u200f?\s')
    for view in ('accept', 'reject_del_only'):
        seen = set()
        for t in dt.paragraph_views(root, view):
            m = num.match(t)
            if m:
                if m.group(1) in seen:
                    F.append(_f('STRUCT_DUP_NUMBER', 'מספר מוקלד כפול בפרק (%s): %s' % (view, m.group(1))))
                    break
                seen.add(m.group(1))
            elif t.strip() and len(t.strip()) < 60:
                seen = set()  # כותרת פרק: המספור המוקלד מתחיל מחדש
    return F


# --------------------------------------------------------------------------------------- השער
def run_gate(path, received, mode, profile, state=None, expected_accept=None, window=None, work_path=None,
             lang=None, register=None, context=None, decisions=None):
    """mode: work / send. lang: 'he' / 'en' (בלי: לפי הטיוטה שהתקבלה). register: המרשם של מעריך הסיכונים
    (dict), כשיש. decisions: קובץ ההכרעות של הסבב (dict), לאימות שורה resolved (גרסה 1.2.0). context: הקשר לבדיקות 2.22 (our_terms, home_country). מחזיר dict עם passed, failures, warnings, info."""
    assert mode in ('work', 'send')
    parts = dt.read_package(path)
    root = etree.fromstring(parts['word/document.xml'])
    rparts = dt.read_package(received)
    rroot = etree.fromstring(rparts['word/document.xml'])
    orig = [dt.para_text(p) for p in dt.body_paragraphs(rroot)]
    lang = lang or gap_checks.detect_lang('\n'.join(orig))
    received_ids = {c['id'] for c in dt.read_comments(rparts)}
    now = _dt.datetime.now()
    window = window or (now - _dt.timedelta(days=2), now + _dt.timedelta(minutes=5))
    author = author_for(profile, lang)
    F, Wn = [], []
    received_authors = {e.get(W + 'author') for e in rroot.iter(W + 'ins', W + 'del')}
    f, info = check_package(parts, root, profile, received_ids, window, work_path or path, author,
                            received_authors=received_authors)
    F += f
    # דחיית השינויים שלנו בלבד, ולא "דחה הכול": השינויים הפתוחים של הצד שכנגד נשארים כפי שהתקבלו
    rej = dt.reject_ours_view(root, author)
    # בפסקה שבה הוכרעו השינויים הפתוחים שלהם (דחייה וסימון שלנו), הבסיס הוא הנוסח שלפני השינויים שלהם,
    # ובקבלה הוא הנוסח שהתקבל. כל פסקה צריכה להתאים לאחד מהשניים
    orig_rej = [dt.received_reject_text(p) for p in dt.body_paragraphs(rroot)]
    if len(rej) == len(orig):
        rej_ok = all(a == b or a == c for a, b, c in zip(rej, orig, orig_rej))
    else:
        rej_ok = rej == orig
    if not rej_ok:
        F.append(_f('RT_REJECT', '"דחה הכול" אינו מחזיר את הטיוטה שהתקבלה'))
    acc = dt.paragraph_views(root, 'accept')
    if expected_accept is not None and acc != expected_accept:
        F.append(_f('RT_ACCEPT', '"קבל הכול" אינו נותן את נוסחי היעד'))
    accept_text = '\n'.join(acc)
    comments = [c for c in dt.read_comments(parts) if c['id'] not in received_ids]
    ext = [c for c in comments if c['author'] == author]
    intc = [c for c in comments if c['author'] == dt.INTERNAL_AUTHOR]
    # בועה של אשכול (כלל 8, הערות ענבל 22.10.2026) נפרשת על כמה פסקאות, ומכסה כל אחת מהן
    spans = dt.comment_paragraph_spans(root)
    ext_by_para = {}
    for c in ext:
        first, last = spans.get(c['id'], (None, None))
        for i in (range(first, last + 1) if first is not None else (None,)):
            ext_by_para.setdefault(i, []).append(c['text'])
    ctx = dict(context or {})
    ctx.setdefault('waived', sorted(waived_gap_codes(state)))
    F += check_bubbles(ext, accept_text, state, '\n'.join(rej), lang)
    F += check_coverage(root, ext_by_para, author, lang)
    F += check_bubble_why(root, ext_by_para, author, accept_text, lang, ctx)
    F += check_contradictions(ext, accept_text, lang)
    Wn += check_reasoning_warnings(ext)
    f, ph = check_placeholders(root, ext, author, state, mode)
    F += f
    f, w_ = check_identifiers(root, author, profile, lang)
    F += f
    Wn += w_
    F += check_self_created_gaps(root, author, accept_text, lang, ctx)
    f, w_ = check_state(state, mode)
    F += f
    Wn += w_
    if register is not None:
        rf = pre_send.check(register, state, decisions)
        (F if mode == 'send' else Wn).extend(rf)
        Wn += pre_send.polish_warnings(register)
    F += check_structure(root, author)
    headers = ''.join(parts[n].decode('utf-8', 'ignore') for n in parts if n.startswith('word/header'))
    # הכותרת הפנימית נדרשת רק כשבקובץ העבודה יש שכבה פנימית (בועות פנימיות). מאז 18.10.2026 השכבה הפנימית
    # אינה מופקת כברירת מחדל (apply_redlines --internal-layer), ולכן הדרישה הגורפת הכשילה כל קובץ עבודה.
    # תיקון מקומי של ניל, לדיווח לענבל
    has_internal = any(c['author'] == dt.INTERNAL_AUTHOR for c in dt.read_comments(parts) if c['id'] not in received_ids)
    if mode == 'work' and has_internal and dt.INTERNAL_HEADER_TEXT not in headers:
        F.append(_f('INT_HEADER_MISSING', 'חסרה הכותרת הפנימית בקובץ העבודה'))
    if mode == 'send':
        if dt.INTERNAL_HEADER_TEXT in headers:
            F.append(_f('INT_IN_SEND', 'הכותרת הפנימית נשארה בעותק למשלוח'))
        if intc:
            F.append(_f('INT_IN_SEND', 'בועה פנימית בעותק למשלוח: %d' % len(intc)))
    info.update(lang=lang, external_comments=len(ext), internal_comments=len(intc), placeholders=ph,
                signing_checklist=[dict(item='signing_blank', **x) for x in ph['signing_blanks']]
                + [dict(item='their_placeholder', **x) for x in ph['theirs']])
    return {'mode': mode, 'passed': not F, 'failures': F, 'warnings': Wn, 'info': info}


def build_send_copy(work_path, received, send_path, profile, state=None, expected_accept=None, window=None,
                    lang=None, deal_dir=None, register=None, context=None, decisions=None):
    """גוזר עותק זמני בלי השכבה הפנימית, מריץ עליו את השער במצב משלוח, ומשנה את שמו רק כשעבר.
    כשנכשל: הקובץ הזמני נמחק, ואין בתיקייה קובץ "למשלוח". עותק "למשלוח" ישן שכבר נמצא בנתיב מקבל את הסיומת
    " - לא למשלוח" (pre_send.retract_send_copy). deal_dir: תיקיית העסקה; ממנה נקרא risk-register.json (שינוי 80)."""
    if register is None and deal_dir:
        register = pre_send.load_register(deal_dir)
    if decisions is None and deal_dir and (state or {}).get('decisions_file'):
        dp = os.path.join(deal_dir, state['decisions_file'])
        if os.path.exists(dp):
            with open(dp, encoding='utf-8') as fh:
                decisions = json.load(fh)
    tmp = send_path[:-5] + '.tmp.docx' if send_path.endswith('.docx') else send_path + '.tmp'
    paths.check_write_path(tmp)
    dt.strip_internal(work_path, tmp)
    res = run_gate(tmp, received, 'send', profile, state, expected_accept, window, work_path=send_path, lang=lang,
                   register=register, context=context, decisions=decisions)
    if res['passed']:
        os.replace(tmp, send_path)
        res['send_copy'] = send_path
        if state is not None:   # גרסה 1.2.0: העותק למשלוח (נתיב ו-sha256) נרשם בקובץ המצב
            res['send_copy_record'] = pre_send.record_send_copy(state, send_path, deal_dir)
    else:
        os.remove(tmp)
        res['send_copy'] = None
        res['retracted'] = pre_send.retract_send_copy(send_path, state, res['info'].get('lang', 'he'),
                                                      deal_dir=deal_dir)
    return res
