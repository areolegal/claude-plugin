# -*- coding: utf-8 -*-
"""risk/validate_register.py: הבדיקה הממוחשבת של risk-register.json לפני בניית הדוח.

כל כלל כאן כללי לכל סוג הסכם, לכל דין ולכל לקוח: אין בקוד חוק, תיקון, רגולטור או סוג הסכם מסוים; מה שתלוי בסוג
ההסכם או בלקוח מגיע בזמן ריצה מהפרופיל, מקובץ המצב או מנתון חיצוני. הכללים:
  - תקציב עמודים: אורך מרבי לכל תא שמוצג (LIMITS), ותבנית אחת להפניה לסעיף (clause_ref_ok).
  - ויתור מכוון: סיכון שנובע מוויתור שהנושא ונותן רשם הוא "סיכון שהתקבל". ויתור שנפתח מחדש
    (reopened_in_round) אינו ויתור. clause_ref הוא מזהה סעיף מקובץ המצב; ויתורים באותה עדשה, בינוניים ונמוכים,
    הם סיכון "התקבל" אחד עם concession_refs[].
  - מספור סעיפים: כל עוגן נושא state_clause_id מקובץ המצב, וההפניה תואמת ל-numbering_map; רשומה במפה שאינה
    מספר סעיף, או ציטוט שאינו בטקסט הסעיף: אזהרה (map_entry_doubt). text_status הוא של המסמך שנסרק בפועל
    (meta.source_version.file או title); כשהוא שונה מהנוסח האחרון בקובץ המצב, אזהרה ולא שגיאה.
  - severity_level ו-display_language נגזרים בקוד (בבנייה); כשהם חסרים, אין שגיאה, וכשהם קיימים הם נבדקים.
  - meta.paper_type מקובץ המצב (tender_awarded: מכרז אחרי זכייה, התנאים ברובם אינם פתוחים למשא ומתן).
  - הסכם הדדי: side חובה בכל סיכון. מעמד הפלייבוק: benchmark_status נגזר ממעמד אחד (playbook/status.py).
  - עדכניות חוק: מקור שנוסחו קודם לתיקון ידוע אינו "ודאות גבוהה". רשימת התיקונים היא נתון (--amendments).
  - עובדה שהפרופיל קובע (רגולטור במעמד Confirmed, פעילות, מסחר בבורסה) אינה "הנחה לאישור".
  - עותק גולמי ב-PDF נקרא דרך שכבת הטקסט (risk/page_text.py); גרשיים בתוך מילה עברית אינם גבול של ציטוט.
  - אין שרשרת אישורים: סיכון שהתקבל הוא הכרעת המשתמש, בלי שדה אישור ובלי שם של מאשר.
  - pre_send_fixes יצא: שדה שנשאר במרשם ישן אינו נבדק ואינו מוצג.
  - חותמת זמן עם שעה: ISO מלא עם היסט; search_log עם user_agent של Areo בלבד.
  - text_status our_draft: טיוטה שלנו שטרם נשלחה. meta.user_focus הוא ציטוט של דברי המשתמש, פטור מבדיקות הנוסח.
  - research.mode: "not_permitted" בהרצה רגילה (המעריך יוצא לרשת רק לבדיקת רקע על הצד שכנגד, מטרה D).
  - מקורות: רק מהרשימה הסגורה מקורות-מאושרים.json (approved_domains, domain_ok), בדומיין, בנתיב ובתתי-הדומיינים
    שהרשימה מתירה. בלי הקובץ אין מקור מאושר (אין רשימת נפילה בקוד). כתובת פסיקה נדחית תמיד (common.case_law).
  - פסיקה בטקסט: בלי מחבר פסיקה סגור (--case-law-connector), אזכור פסק דין בטקסט המוצג הוא שגיאה.
  - סיכון גולמי ושיורי: סיכון שטופל בתוך הנוסח שנבדק נושא residual.treated ו-treated_how, בשיורי בינוני לכל היותר.
  - שווי העסקה והתמונה הכספית: סכום רק עם מקור (contract | client); עד שלוש חשיפות; בדיקה צולבת של ביטוח מול תקרה.
  - דוח בדיקת הרקע: validate_entity_report() (התאמת שם, ממצא חוסם, why חובה, כתובות בלי טוקנים, ממצא רשמי ואות
    תקשורתי נפרדים, בלי ייחוס כוונה ובלי ידיעה על הליך משפטי).

שימוש:
  python3 -B validate_register.py <risk-register.json> [--corpus corpus.json] [--deal DIR]
         [--state negotiation_state.json] [--profile פרופיל-לקוח.json] [--playbook-status status.json]
         [--entity entity-report.json] [--purpose entity] [--out report.json]
         [--approved-sources מקורות-מאושרים.json] [--case-law-connector <שם המחבר>]
         (--purpose entity: דוח בדיקת רקע נבדק מול מקורות בדיקת הרקע וכלל התקשורת; --entity מפעיל אותו גם בלעדיו)
         (כל הקלט קריאה בלבד; --out אופציונלי, רק לדוח השגיאות, ולעולם לא קובץ קלט)
קוד יציאה 1 על כל שגיאה. ספרייה סטנדרטית בלבד.
"""
import hashlib
import html as _html
import io
import json
import os
import re
import sys
from urllib.parse import urlsplit

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
    from common.case_law import case_law_hits, case_law_url
    from common.cli import guard_out, parser, run, write_json
    from common.net import client_detail_in_query, url_allowed
    from common.paths import long_path
    from common.terms import terms_re
except ImportError:  # pragma: no cover
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from common.case_law import case_law_hits, case_law_url
    from common.cli import guard_out, parser, run, write_json
    from common.net import client_detail_in_query, url_allowed
    from common.paths import long_path
    from common.terms import terms_re

LENS8 = ['legal', 'financial', 'operational', 'technology', 'regulatory', 'reputational', 'insurance', 'force_majeure']
KINDS = {'clause', 'silence', 'vague_term', 'back_to_back', 'external', 'hidden_text', 'untracked_change'}
META_KEYS = {'company', 'scope', 'transaction_id', 'party_terms', 'scope_label', 'source_ref', 'source_version',
             'annexes_reviewed', 'annexes_missing', 'deal_value', 'generated_at', 'last_updated', 'docAccess',
             'publishTarget', 'branding', 'display_language', 'prepared_for_counsel', 'user_focus', 'counterparty',
             'document_title', 'position', 'mutual_primary_role', 'playbook_ref', 'benchmark_status', 'paper_type'}
RISK_KEYS = {'id', 'risk_no', 'kind', 'name', 'description', 'hidden_text', 'primary_lens', 'lens', 'inherent',
             'severity_level', 'controls', 'residual', 'exposure', 'scenario', 'critical_detail', 'anchors',
             'treatment_direction', 'playbook_flag', 'certainty', 'external_source_ids', 'side', 'decision',
             'drafted_by', 'regulatory_basis', 'created_by_response', 'concession_refs',
             # סכמה 3.7: שלושה מצבים (נוכחי, מוצע, מוסכם) וזהות סיכון
             'states', 'event', 'impact', 'control_ref', 'exposure_state'}
FORBIDDEN_RISK = {'mitigation', 'feasibility_basis', 'leverage_window', 'owner', 'mitigation_channel', 'category',
                  'estimated_amount', 'ratio_to_deal_value'}
DEF_TYPES = {'contradiction', 'ambiguity', 'missing_annex', 'missing_agreement', 'undefined_term', 'inconsistent_term',
             'broken_reference', 'precedence_missing', 'version_mismatch', 'language_mismatch', 'leftover_text',
             'blank_field', 'unilateral_document', 'cumulative_requirement'}
TEXT_STATUS = {'agreed', 'counterparty_draft', 'their_draft', 'our_unsent_response', 'our_sent_response', 'our_draft'}
# הנוסח שאנחנו מציעים: התגובה שלנו (לפני שליחה או אחריה), או טיוטה שלנו (our_draft)
OUR_TEXT_STATUS = ('our_unsent_response', 'our_sent_response', 'our_draft')
# הרשימה המחייבת היא הקובץ המשותף מקורות-מאושרים.json. הוא נארז בתוסף (lib/מקורות-מאושרים.json) ואינו
# מורד מהשרת בזמן ריצה (Cowork חוסם הורדות). הסדר: הארגומנט --approved-sources, אחריו משתנה הסביבה
# AREO_APPROVED_SOURCES, ואחריהם העותק שבתוסף (default_sources_path). אין רשימת נפילה בקוד: כשנמסר נתיב שאינו
# קיים, או שהקובץ אינו נקרא, אף מקור אינו מאושר (הקבוע נשאר ריק לתאימות עם קוד שקורא אותו)
APPROVED_DOMAINS = ()
APPROVED_SOURCES_ENV = 'AREO_APPROVED_SOURCES'
APPROVED_SOURCES_FILE = 'מקורות-מאושרים.json'


def default_sources_path():
    """העותק של רשימת המקורות המאושרים שנארז בתוסף: <lib>/מקורות-מאושרים.json."""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), APPROVED_SOURCES_FILE)


def sources_path(path=None):
    """הנתיב שייקרא: הארגומנט, אחריו AREO_APPROVED_SOURCES, ואחריהם העותק שבתוסף."""
    return path or os.environ.get(APPROVED_SOURCES_ENV) or default_sources_path()

# בדיקת רקע על הצד שכנגד (מטרה D). המטרה היחידה שבה המעריך יוצא לרשת
ENTITY_PURPOSE = 'entity'
# מקורות בדיקת הרקע: רק entity_check שבקובץ המשותף. אין רשימת נפילה (הקבוע נשאר ריק לתאימות)
ENTITY_DOMAINS = ()
# כלל התקשורת: לא רשימה סגורה של כלי תקשורת, אלא מה שאינו תקשורת. נקרא מ-entity_check.media.excluded_domains
# כשהקובץ נמסר; הרשימה כאן נוספת עליה. בתי משפט ומאגרי פסיקה אסורים תמיד (כלל 1.1): common.case_law.case_law_url
MEDIA_EXCLUDED = ('facebook.com', 'fb.com', 'instagram.com', 'x.com', 'twitter.com', 'linkedin.com', 'tiktok.com',
                  'youtube.com', 'youtu.be', 'reddit.com', 't.me', 'telegram.org', 'whatsapp.com', 'threads.net',
                  'medium.com', 'substack.com', 'blogspot.com', 'wordpress.com', 'wix.com', 'tumblr.com',
                  'quora.com', 'wikipedia.org', 'fxp.co.il', 'rotter.net', 'tapuz.co.il', 'glassdoor.com',
                  'trustpilot.com', 'google.com', 'bing.com', 'duckduckgo.com', 'yahoo.com', 'dnb.com', 'bdi.co.il',
                  'opencorporates.com', 'creditsafe.com', 'zoominfo.com', 'crunchbase.com', 'coface.com')
# מאגרים מסחריים ומערכות תיקים, בנוסף ל-common.case_law (שבודק כל כתובת קודם)
COURT_DOMAINS = ('court.gov.il', 'takdin.co.il', 'psakdin.co.il', 'nevo.co.il', 'courtlistener.com', 'bailii.org',
                 'pacer.gov', 'uscourts.gov', 'judiciary.uk', 'rechtspraak.nl', 'justia.com', 'casetext.com',
                 'curia.europa.eu', 'hudoc.echr.coe.int', 'lexisnexis.com', 'westlaw.com')
MEDIA_MARKERS = re.compile(r'(?:^|[.\-/])(?:blogs?|forums?|community|talk|board)(?:[.\-/]|$)', re.I)
# מקור רגולטורי שלא נפתח בהרצה: תועד במחקר הרגולטורי של הפלייבוק, או במסמך רשמי שצורף לתיק (לא טענה בהסכם)
SOURCE_ORIGINS = ('playbook', 'documents')
MEDIA_LABEL = {'he':'אות לא מאומת, מהתקשורת', 'en': 'Unverified signal, from the media'}
# ייחוס כוונה אסור בדוח בדיקת הרקע: מה שהמקור אומר, ולא מה הצד שכנגד "התכוון"
INTENT_PHRASES = ['בכוונה', 'במזיד', 'בזדון', 'ביודעין', 'בכוונת מכוון', 'במתכוון', 'במכוון', 'בכוונו', 'בחוסר תום לב', 'בכוונה תחילה',
                  'ניסה להונות', 'ניסתה להונות', 'מתכוון להונות', 'מתכוונת להונות', 'כוונה פלילית', 'intentionally',
                  'deliberately', 'wilfully', 'willfully', 'knowingly', 'in bad faith', 'with intent', 'intended to',
                  'tried to defraud', 'fraudulent intent', 'malicious']
# ידיעה על הליך משפטי אינה אות: משימה לעורך הדין (כלל 1.1). מילים שמסמנות פסיקה בתוך אות תקשורתי; אזכור פסק
# דין בכל טקסט מוצג נבדק גם ב-common.case_law.case_law_hits
CASE_LAW_WORDS = ['פסק דין', 'פסק הדין', 'בית המשפט קבע', 'בית הדין קבע', 'נפסק', 'ruling', 'judgment',
                  'the court held', 'court ruled', 'verdict']
BLOCKED_PHRASES = ['תוחלת נזק', 'סיכון מצטבר', 'תיאבון סיכון', 'אינו ייעוץ משפטי', 'מודל שפה', 'קו אדום',
                   'חבילת ויתורים', 'חלון מינוף', 'ישימות', 'אם הצד השני ידחה', 'ודאית', 'מהיום הראשון', 'אין בקרה',
                   'מופר', 'הפרנו', 'לא נעמוד', 'לא תקוים', 'אינה ניתנת לקיום', 'לחץ פנימי', 'יודע ש',
                   'עמדת נסיגה', 'פלייבוק באחוזים', 'להתעקש', 'לדרוש', 'הצד שכנגד יטען', 'אומדן', 'משוער',
                   'חלוקת השווי',
                   # אותם איסורים בתוצר אנגלי
                   'expected loss', 'aggregate risk', 'cumulative risk', 'risk appetite', 'not legal advice',
                   'language model', 'red line', 'concession package', 'leverage window', 'feasibility',
                   'if the other side rejects', 'if the counterparty rejects', 'certainly', 'from day one',
                   'no control in place', 'no controls in place', 'is breached', 'we breached', 'we will not comply',
                   'cannot be complied with', 'internal pressure', 'knows that', 'fallback position',
                   '% compliance', 'compliance %', 'percent compliance', 'insist on', 'to demand',
                   'the counterparty will argue', 'the other side will argue', 'estimate', 'estimated',
                   'value split', 'split of value', 'allocation of value']
# מילים של עצת משא ומתן: חסומות רק בשדות שנותנים כיוון ("לדרוש", "להתעקש"), ולא בתיאור של סעיף ("הספק רשאי לדרוש")
ADVICE_ONLY = {'לדרוש', 'להתעקש', 'to demand', 'insist on'}
ADVICE_PATH = re.compile(r'treatment_direction|bottom_line|breaking_fix|proposed_fix|neutralizes|deal_one_line')
CODE_RE = re.compile(r'\b(?:R-?\d{2}|Q\d+|V-\d+|REG\d+|SEG-\d+|APR-\d+|RSK-\d+|DEF-\d+|CMB-\d+|ENT-\d+|SRC-\d+)\b'
                     r'|כלל \d|\bסבב \d|\d+\s*[xX×]\s*\d+')
# שם מסמך וכותרת של מסמך מקור: "סבב 3" הוא חלק מהשם, ולא קוד פנימי. שאר הקודים חסומים גם כאן
DOC_NAME_PATH = re.compile(r'^\.documents\[\d+\]\.title$|^\.meta\.source_version\.title$|^\.meta\.document_title$|'
                           r'\.anchors\[\d+\]\.document$|\.locations\[\d+\]\.document$|\.caps\[\d+\]\.document$|'
                           r'\.imported_from$|\.shared_with\[\d+\]$|'
                           r'\.states\.current\.version$|\.states\.proposed\[\d+\]\.markup_version$|'
                           r'\.states\.agreed\.accepted_version$')
ROUND_RE = re.compile(r'\bסבב \d')
# קוד מטבע (ISO 4217) בטקסט מוצג אסור רק בתוצר עברי, שבו הסכום נכתב בסימן או במילה; בתוצר אנגלי "USD 100,000" תקין
CURRENCY_CODE_RE = re.compile(r'\b(?:ILS|NIS|USD|EUR|GBP|CHF|JPY|CNY|CAD|AUD|NZD|SGD|HKD|INR|AED|SEK|NOK|DKK|PLN|'
                              r'CZK|HUF|RON|TRY|BRL|MXN|ZAR|KRW)\b')
SKIP_TEXT = re.compile(r'(\.id$|_id$|\.file$|source_ref$|source_version|\.logo$|\.url$|typed_url|final_url|\.sha256|'
                       r'risk_ids|\.lens(\[\d+\])?$|\.kind$|\.type$|\.status$|\.combo_id|\.currency|primary_lens|'
                       r'playbook_flag|certainty|drafted_by|\.mode$|\.role$|urlSource|text_status|sign_as_is|\.label$|'
                       r'\.result$|\.prevails$|missing_identifiers|\.question\[\d+\]|external_source_ids|transaction_id|'
                       r'\.scope$|display_language|benchmark_status|\.saved_at|\.at$|\.date$|defined_at|generated_at|'
                       r'last_updated|set_at|offered_at|\.country$|\.excerpt$|search_log|raw_copies|\.query|'
                       r'state_clause_id|regulatory_basis|\.basis$|version_date|\.side$|docAccess|deal_value\.source|'
                       r'\.meta\.user_focus$|cross_checks|concession_refs)')
# meta.user_focus הוא ציטוט של דברי המשתמש כלשונו ("שלא נעמוד בלוח הזמנים"): נשמר ומוצג כציטוט, ולכן פטור מבדיקות
# הנוסח (ביטויים חסומים, קודים, מקפים, סכומים ונוסח של שרשרת אישורים)
QUOTED_USER_TEXT = ('.meta.user_focus',)
# ציטוט מההסכם עצמו (עוגן, מיקום) אינו פסיקה מהרשת: פטור מבדיקת אזכורי הפסיקה
CASE_LAW_EXEMPT = re.compile(r'\.quote$|\.quotes\[\d+\]$|\.excerpt$|\.anchors\[\d+\]\.text$')

# ---- תקציב העמודים: אורך מרבי בתווים לכל תא שמוצג. ----
LIMITS = {
    'risks[].name': 70, 'risks[].treatment_direction': 70, 'risks[].anchors[].clause': 30,
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
    'risks[].residual.treated_how': 70,
    'summary.money_picture.exposures[].what': 60, 'summary.money_picture.exposures[].reason': 80,
}
MAX_KEY_DATES = 5

# ---- סיכון שיורי: סיכון שטופל בתוך הנוסח שנבדק ----
# "טופל" רק בנוסח שלנו או בנוסח מוסכם; בטיוטה של הצד השני שום דבר עוד לא טופל
TREATED_STATUS = ('our_unsent_response', 'our_sent_response', 'our_draft', 'agreed')
TREATED_MAX_SCORE = 8   # הדירוג השיורי של סיכון שטופל: בינוני לכל היותר
DELETED_RE = re.compile(r'נמחק|נמחקה|נמחקו|הוסר|הוסרה|הוסרו|הוחזר לנוסח|\bdeleted\b|\bremoved\b|\bstruck\b', re.I)
HIDDEN_ASKS = ('approve_terms', 'send_information')
# ---- שווי העסקה והתמונה הכספית ----
AMOUNT_SOURCES = ('contract', 'client')
DEAL_VALUE_FILES = ('negotiation_state.json', 'strategy-data.json')
ISO_CURRENCIES = ('ILS|NIS|USD|EUR|GBP|CHF|JPY|CNY|CAD|AUD|NZD|SGD|HKD|INR|AED|SAR|QAR|KWD|BHD|OMR|EGP|JOD|SEK|NOK|DKK|'
                  'ISK|PLN|CZK|HUF|RON|BGN|TRY|RUB|BRL|MXN|ARS|CLP|COP|PEN|ZAR|KRW|TWD|THB|MYR|IDR|PHP|VND')
# מטבע: קוד ISO 4217, סימן או שם בעברית, לפני הסכום או אחריו ("USD 2,000,000", "$2,000,000", "2,000,000 פרנק")
_CUR = (r'(?:ש"ח|ש״ח|שקלים|שקל|₪|ליש"ט|ליש״ט|לירות שטרלינג|לירה שטרלינג|דולר(?:ים)?|אירו|יורו|פרנק(?:ים)?|ין|'
        r'דירהם|£|\$|€|¥|Fr\.|S\$|A\$|C\$|HK\$|\b(?:' + ISO_CURRENCIES + r')\b)')
_AMT = r'(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?\s*(?:אלף|מיליון|מיליארד|[kKmM]|bn|million|billion)\b|\d{4,})'
_VALUE_AMT = re.compile(r'(?:' + _AMT + r'\s*' + _CUR + r'|' + _CUR + r'\s*' + _AMT + r')')
_VALUE_CTX = re.compile(r'לשנה|בשנה|שנתי|לחודש|בחודש|תמורה|שווי|ההסכם המסחרי|היקף ההתקשרות|per year|annual|'
                        r'per month|monthly|consideration|contract value|deal value|\bfees?\b', re.I)
MONEY_MAX = None  # אין תקרה על מספר החשיפות העצמאיות (סכמה 3.7)
INS_CAP_RATIO = 2   # ביטוח מול תקרה: פי שניים ומעלה לכל כיוון הוא ממצא
WORDS_WARN, WORDS_FAIL = 2800, 3200

# ---- הפניה לסעיף: תבנית אחת ----
FIXED_REFS = {'פתיח', 'מבוא', 'הגדרות', 'חתימות', 'בלוק החתימות', 'בלוק הצדדים', 'כותרת', 'נספחים',
              'preamble', 'recitals', 'definitions', 'signatures', 'signature page', 'signature block', 'cover page',
              'order form', 'title', 'annexes', 'schedules', 'exhibits', 'parties'}
# נספח בשמו, בעברית ובאנגלית: "נספח ב", "Annex II", "Schedule 3", "Exhibit A", "Appendix 1"
_ANNEX_RE = re.compile(r'^(?:נספח|annex|schedule|exhibit|appendix|attachment|addendum)\s+[^\s;]{1,20}(\s[^\s;]{1,20})?$', re.I)
_NUM = r'\d+[א-ת]?(?:\.\d+[א-ת]?)*(?:\([א-תa-z0-9]{1,3}\))*'
_REF_RE = re.compile(r'^(?:[^\d;,]{1,30}?,?\s)?(?:סעיף |סעיפים |פסקה |section |sections |clause |clauses |article |'
                     r'para |paragraph |§\s?)?' + _NUM +
                     r'(?:\s*(?:,|ו-?)\s*' + _NUM + r')*$', re.I)


def clause_ref_ok(s):
    """"סעיף 7.2(א)", "תמורה 1", "היקף הייעוץ, סעיף 1", "6, 9", "פתיח", "נספח ב", "חדש אחרי סעיף 5";
    כמה הפניות מופרדות ב-"; ". לא: משפט, ציטוט, "פסקה 5 בטיוטה" או מספור של הנוסח המוצע בלי הסבר."""
    s = (s or '').strip()
    if not s:
        return False
    for part in re.split(r'\s*;\s*', s):
        for pre in ('חדש אחרי ', 'new after ', 'New after '):
            if part.startswith(pre):
                part = part[len(pre):].strip()
        if part.lower() in FIXED_REFS or _ANNEX_RE.match(part):
            continue
        if all(x.strip().lower() in FIXED_REFS or _ANNEX_RE.match(x.strip()) for x in part.split(',')):
            continue
        if not _REF_RE.match(part):
            return False
    return True


# ---- עדכניות: תיקונים ידועים שאחריהם נוסח קודם אינו "ודאות גבוהה" ----
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


# ---- אין שרשרת אישורים. הכרעת המשתמש נרשמת כהכרעה, בלי מאשר ובלי מצב "ממתין" ----
DECISION_KEYS = {'status', 'basis', 'state_clause_id', 'state_clause_ids', 'note', 'decided_at'}
APPROVAL_PHRASES = ['ממתין לאישור', 'ממתינה לאישור', 'ממתינים לאישור', 'טעון אישור מנכ', 'אישור מנכ"ל', 'אישור מנכ״ל',
                    'אישור המנכ"ל', 'אישור המנכ״ל', 'טבלת הסמכויות', 'מוצע לקבלה', 'awaiting approval',
                    'pending approval', 'subject to CEO approval']
SIDES = ('as_obligor', 'as_beneficiary', 'both', 'as_discloser', 'as_recipient')  # שני האחרונים: מרשם ישן
RULE_ID_RE = re.compile(r'^(?:R-?\d+|mandatory_list:.*|rule:.*)$')   # רק לנוסח השגיאה; ההכרעה: מזהה בקובץ המצב
AREO_UA_PREFIX = 'AreoLegal-research/'
# המזהה כולל את שם הארגון וכתובת קשר, ואינו מזהה דפדפן
AREO_UA_CONTACT = re.compile(r'AreoLegal\b.*contact: [A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\)$')
BROWSER_UA = re.compile(r'Mozilla/|Chrome/|Safari/|Firefox/|Edg/|Gecko', re.I)


_TERM_CACHE = {}


def _term(phrase):
    if phrase not in _TERM_CACHE:
        _TERM_CACHE[phrase] = terms_re([phrase])
    return _TERM_CACHE[phrase]


def _load_sources_file(path):
    path = sources_path(path)
    if not path or not os.path.isfile(long_path(path)):
        return None, None
    try:
        with io.open(long_path(path), encoding='utf-8-sig') as fh:
            return json.load(fh), path
    except (OSError, ValueError):
        return None, None


def _norm_dom(d):
    d = (d or '').strip().lower().rstrip('/').rstrip('.')
    return d[4:] if d.startswith('www.') else d


def _src_rules(src):
    """כללי הכתובת של מקור אחד (התחביר של common.net.rule_matches), או [] כשהמקור נדחה: לא approved, או עם הגבלת
    שימוש בלי נתיבים במכונה (allowed_paths) ובלי restriction_kind "content"."""
    dom, _, dpath = _norm_dom(src.get('domain')).partition('/')
    if src.get('status') != 'approved' or not dom:
        return []
    paths = [x for x in (src.get('allowed_paths') or []) if (x or '').strip('/')]
    if dpath:
        paths = paths or ['/' + dpath]
    restricted = any((src.get(k) or '').strip() for k in src if k.startswith('usage_restriction'))
    kind = src.get('restriction_kind')
    if (restricted or kind == 'paths') and not paths and kind != 'content':
        return []   # הגבלה כתובה בלי נתיבים במכונה: לא מאשרים את כל הדומיין
    base = ('' if src.get('include_subdomains') else '=') + dom
    rules = [base + '/' + x.strip().lstrip('/') for x in paths] or [base]
    rules += ['=' + _norm_dom(h) for h in src.get('include_hosts') or [] if _norm_dom(h)]
    return rules


def _page_rule(pg):
    """דף מאושר: הכתובת והנתיבים שמתחתיה, במארח עצמו. מזהה של גוף בשאילתה (OfficeId, TopicId, Type) נשמר."""
    if pg.get('status') != 'approved' or not pg.get('url'):
        return None
    sp = urlsplit(pg['url'])
    host = _norm_dom(sp.hostname)
    if not host:
        return None
    keep = [kv for kv in sp.query.split('&') if re.match(r'(?i)(officeid|topicid|type)=', kv)]
    return '=' + host + (sp.path.rstrip('/') or '') + ('?' + '&'.join(keep) if keep else '')


def _case_law_entries(block):
    """case_law_only כרשימה; מקבל גם {sources|domains: [...]} או {jurisdictions: [{sources: [...]}]}."""
    if isinstance(block, list):
        return block
    if isinstance(block, dict):
        if block.get('sources') or block.get('domains'):
            return list(block.get('sources') or []) + list(block.get('domains') or [])
        return [s for j in block.get('jurisdictions') or [] for s in (j.get('sources') or [])]
    return []


def _case_law_rules(data):
    """כללי דחייה ("!") מהבלוק case_law_only: מדורי פסיקה ואתרי בתי משפט, שנדחים בכל מטרה."""
    out = []
    for c in _case_law_entries((data or {}).get('case_law_only')):
        if isinstance(c, str):
            c = {'domain': c}
        dom = _norm_dom(c.get('domain'))
        if not dom:
            continue
        paths = [x for x in c.get('paths') or [] if (x or '').strip('/')]
        out += ['!' + dom + '/' + x.lstrip('/') for x in paths] or ['!' + dom]
    return out


def _rules_of(jurisdictions, pages=True):
    rules = []
    for j in jurisdictions or []:
        for src in j.get('sources') or []:
            rules += _src_rules(src)
        for pg in (j.get('pages') or []) if pages else []:
            r = _page_rule(pg)
            if r:
                rules.append(r)
    return rules


class Rules(tuple):
    """כללי הכתובת המורשים (tuple של מחרוזות, כמו קודם), וכללי הדחייה של case_law_only במאפיין refuse. כך קוד
    שבונה מהכללים רשימת דומיינים (r.partition("/")[0]) אינו הופך כלל דחייה של נתיב לדחייה של כל הדומיין."""
    refuse = ()


def _rules_obj(allowed, refuse):
    r = Rules(allowed)
    r.refuse = tuple(refuse)
    return r


def approved_domains(path=None, purpose=None):
    """כללי הכתובת המורשים מהקובץ המשותף מקורות-מאושרים.json (התחביר של common.net.rule_matches): רק מקור שהסטטוס
    שלו approved; include_subdomains, include_hosts ו-allowed_paths נאכפים; דף מאושר הוא כלל משלו; ו-case_law_only
    נכנס ככללי דחייה ("!") במאפיין refuse של התוצאה (Rules). path: הארגומנט, ואחריו משתנה הסביבה. מחזיר (כללים, הנתיב שנקרא); בלי קובץ, או כשאינו
    נקרא: ((), None), כלומר אף מקור אינו מאושר.
    purpose="entity" (בדיקת רקע על הצד שכנגד, ורק בה): נוספים מקורות entity_check שבקובץ (מרשמים, רשימות
    סנקציות). בלי purpose: רק הרשימה הרגילה."""
    data, path = _load_sources_file(path)
    if not data:
        return (), None
    rules = _rules_of(data.get('jurisdictions'))
    if purpose == ENTITY_PURPOSE:
        rules += _rules_of((data.get('entity_check') or {}).get('jurisdictions'), pages=False)
    if not rules:
        return (), None
    return _rules_obj(dict.fromkeys(rules), _case_law_rules(data)), path


def media_rule(path=None):
    """כלל התקשורת מהקובץ המשותף (entity_check.media), עם רשימת הנפילה של מה שאינו תקשורת."""
    data, _ = _load_sources_file(path)
    m = ((data or {}).get('entity_check') or {}).get('media') or {}
    excl = tuple(dict.fromkeys([d.strip().lower() for d in m.get('excluded_domains') or ()] + list(MEDIA_EXCLUDED)))
    return {'excluded': excl, 'label': {'he': m.get('label_he') or MEDIA_LABEL['he'],
                                        'en': m.get('label_en') or MEDIA_LABEL['en']}}


def _host_in(host, doms):
    return any(host == d or host.endswith('.' + d) for d in doms)


def media_problem(url, path=None, purpose=ENTITY_PURPOSE):
    """'' כשהכתובת יכולה להיות מקור תקשורתי בבדיקת רקע; אחרת הסיבה. כלל, לא רשימה: כתובת https או http של
    כלי תקשורת, ולא רשת חברתית, בלוג, פורום, מנוע חיפוש, מאגר מסחרי, בית משפט או מאגר פסיקה."""
    if purpose != ENTITY_PURPOSE:
        return 'תקשורת רק בבדיקת רקע על הצד שכנגד (--purpose entity)'
    p = urlsplit(url or '')
    host = (p.hostname or '').lower()
    if p.scheme not in ('http', 'https') or not host:
        return 'כתובת שאינה http או https'
    why = case_law_url(url)
    if why:
        return 'בית משפט או מאגר פסיקה: אסור תמיד (כלל 1.1); הליכים משפטיים הם משימה לעורך הדין. %s' % why
    if _host_in(host, COURT_DOMAINS) or re.search(r'(?:^|\.)courts?\.', host):
        return 'בית משפט או מאגר פסיקה: אסור תמיד (כלל 1.1); הליכים משפטיים הם משימה לעורך הדין'
    if _host_in(host, media_rule(path)['excluded']):
        return 'אינו כלי תקשורת מבוסס (רשת חברתית, בלוג, פורום, מנוע חיפוש או מאגר מסחרי): %s' % host
    if MEDIA_MARKERS.search(host) or MEDIA_MARKERS.search('/' + (p.path or '').strip('/').split('/')[0] + '/'):
        return 'בלוג או פורום: %s' % host
    return ''


def source_class(url, path=None, purpose=None):
    """'official' (מקור רשמי ברשימה), 'media' (רק בבדיקת רקע, לפי כלל התקשורת), או None (אסור). כתובת פסיקה
    נבדקת לפני ההכרעה, בכל מטרה, ולעולם אינה רשמית ואינה תקשורתית."""
    if case_law_url(url):
        return None
    if domain_ok(url, approved_domains(path, purpose)[0]):
        return 'official'
    return 'media' if purpose == ENTITY_PURPOSE and not media_problem(url, path, purpose) else None


def domain_ok(url, rules):
    """הכתובת מותרת לפי הכללים (common.net.url_allowed): במארח שהכלל מתיר (בלי תתי-דומיינים כשהכלל מתחיל ב-"="),
    ובנתיב שבכלל, בגבול של מקטע ואחרי נרמול. כתובת פסיקה (common.case_law.case_law_url) או כתובת שמתאימה לכלל
    דחייה ("!", מ-case_law_only) נדחית בכל מטרה."""
    return url_allowed(url, tuple(rules or ()) + tuple(getattr(rules, 'refuse', ())))


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

# ---- עובדות שהפרופיל קובע: רגולטורים במעמד Confirmed, פעילויות, ומקומות מסחר. מה שהפרופיל
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
    for r in reg.get('risks') or []:
        yield 'risks[].residual.treated_how', 'risk %s.residual.treated_how' % r.get('id'), \
            (r.get('residual') or {}).get('treated_how')
    for i, x in enumerate((S.get('money_picture') or {}).get('exposures') or []):
        yield 'summary.money_picture.exposures[].what', 'money_picture.exposures[%d].what' % i, x.get('what')
        yield 'summary.money_picture.exposures[].reason', 'money_picture.exposures[%d].reason' % i, x.get('reason')


def concessions(state):
    """הוויתורים המכוונים בקובץ המצב, כרשימה (שני ויתורים יכולים לחול על אותו סעיף).
    לפי הערות הנושא ונותן 4.9: deliberate_concessions[] עם clause_ref, שהוא מזהה הסעיף בקובץ המצב
    (clauses[].clause_id או מפתח ב-numbering_map), ו-report_as: "accepted_risk". שדה אישור, אם נשאר בקובץ
    מצב ישן (approval, required_by), אינו נקרא."""
    out = []
    for d in (state or {}).get('deliberate_concessions') or []:
        if d.get('report_as', 'accepted_risk') != 'accepted_risk' or d.get('reopened_in_round'):
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
        if d.get('report_as', 'accepted_risk') != 'accepted_risk' or d.get('reopened_in_round'):
            continue
        cid = d.get('clause_ref') or d.get('clause_id')
        if cid:
            out[cid] = d.get('topic') or d.get('what') or ''
    reopened = reopened_refs(state)
    for c in state.get('clauses') or []:
        if c.get('clause_id') in reopened:
            continue
        for h in c.get('concession_history') or []:
            if h.get('kind') == 'reopen':
                # פתיחה מחדש בהוראת עורך הדין מבטלת ויתור קודם באותו סעיף
                out.pop(c.get('clause_id'), None)
            elif h.get('who') == 'us' and (h.get('deliberate') is True or
                                            str(h.get('in_exchange_for') or '').startswith('ויתור מכוון')):
                out[c.get('clause_id')] = h.get('what') or ''
    return out


def reopened_refs(state):
    """מזהי הסעיפים שבהם ויתור מכוון נפתח מחדש (reopened_in_round), עם מספר הסבב."""
    return {(d.get('clause_ref') or d.get('clause_id')): d.get('reopened_in_round')
            for d in (state or {}).get('deliberate_concessions') or [] if d.get('reopened_in_round')}


def state_clause_ids(state):
    ids = {c.get('clause_id') for c in (state or {}).get('clauses') or [] if c.get('clause_id')}
    return ids | set(((state or {}).get('numbering_map') or {}).keys())


def numbering_consistent(where, mapped):
    """ההפניה ב-where (קצרה, עד 30 תווים) תואמת לשם הסעיף בתגובה שלנו לפי numbering_map: כל מספר
    שב-where מופיע בשם המלא ("סעיף 2 בפרק 'תמורה ותנאי תשלום'" מול "תמורה 2")."""
    nums = re.findall(r'\d+[א-ת]?(?:\.\d+[א-ת]?)*', where or '')
    have = set(re.findall(r'\d+[א-ת]?(?:\.\d+[א-ת]?)*', mapped or ''))
    return all(n in have for n in nums)


# פסקה שנפתחת בתת-סעיף מוקלד: "(a)", "(ii)", "(aa)", "(ב)"
_TYPED_SUB = re.compile(r'^\s*\(([a-z]{1,3}|[ivxlc]{1,5}|\d{1,2}|[א-ת]{1,2})\)', re.I)
CLAUSE_TEXT_KEYS = ('current_text', 'agreed_text', 'pending_text')


def map_entry_doubt(state, sc, mapped, quote=''):
    """הרשומה ב-numbering_map אינה בסיס לשגיאה, ולכן אי-התאמה היא אזהרה ולא שגיאה. מחזיר את
    הסיבה, או '' כשהרשומה היא מספר סעיף שאפשר לסמוך עליו:
      - הרשומה אינה מספר סעיף ("פסקה 5 בטיוטה", "בועה בראש המסמך", ריקה);
      - הסעיף בקובץ המצב נפתח בתת-סעיף מוקלד ("(a)"), והרשומה בלי תת-סעיף ("סעיף 20"): המונה של הרשימה, לא המספר;
      - הציטוט שבעוגן אינו בטקסט הסעיף שבקובץ המצב: הוא מפסקה אחרת, והמזהה הוא של הסעיף הקרוב."""
    mapped = (mapped or '').strip()
    if not re.search(r'\d', mapped) or not clause_ref_ok(mapped):
        return 'הרשומה במפה אינה מספר סעיף (%r)' % mapped
    texts = [str(c.get(k) or '') for c in (state or {}).get('clauses') or [] if c.get('clause_id') == sc
             for k in CLAUSE_TEXT_KEYS if c.get(k)]
    if any(_TYPED_SUB.match(t) for t in texts) and '(' not in mapped:
        return 'הסעיף נפתח בתת-סעיף מוקלד, והרשומה במפה (%s) היא מונה של רשימה' % mapped
    q = norm(quote or '')
    if q and texts and not any(q in norm(t) for t in texts):
        return 'הציטוט אינו בטקסט הסעיף %s שבקובץ המצב: הוא מפסקה אחרת' % sc
    return ''


def deal_value_hint(deal_dir, state=None):
    """נתון על שווי העסקה שכבר בתיקיית העסקה: בקובץ המצב (meta.deal_context.estimated_value,
    client_answers) ובתוצרי האסטרטג (strategy-data.json). מחזיר (קובץ, קטע) או None. סכום עם מטבע ליד מילה של
    תמורה או תקופה ("120,000 ליש"ט לשנה"); אינו מכריע מהו השווי, רק שיש מקור שלא נגזר ממנו."""
    docs = []
    if state is not None:
        docs.append(('negotiation_state.json', state))
    for name in DEAL_VALUE_FILES:
        if state is not None and name == 'negotiation_state.json':
            continue
        p = os.path.join(deal_dir or '', name)
        if deal_dir and os.path.isfile(long_path(p)):
            try:
                with io.open(long_path(p), encoding='utf-8-sig') as fh:
                    docs.append((name, json.load(fh)))
            except (OSError, ValueError):
                continue
    for name, data in docs:
        ev = str((((data.get('meta') or {}).get('deal_context') or {}).get('estimated_value')) or '').strip()
        if ev and ev not in ('לא ידוע', 'unknown', 'Unknown') and _VALUE_AMT.search(ev):
            return name, ev[:80]
        for _p, s in _walk(data):
            for m in _VALUE_AMT.finditer(s):
                st = max(0, m.start() - 40)
                win = s[st:m.end() + 40]
                if _VALUE_CTX.search(win):
                    if st and ' ' in win[:m.start() - st]:
                        win = win.split(' ', 1)[1]   # בלי חצי מילה בתחילת הקטע ובסופו
                    if m.end() + 40 < len(s) and ' ' in win[-20:]:
                        win = win.rsplit(' ', 1)[0]
                    return name, win.strip()[:90]
    return None


def money_problem(a, where):
    """סכום אחד בתמונה הכספית (סכום, קצה טווח, תקרה, ביטוח): רק מההסכם או מהלקוח, עם הפניה; מההסכם גם חישוב.
    מחזיר רשימת בעיות."""
    if not isinstance(a, dict) or a.get('value') is None:
        return []
    out = []
    if a.get('source') not in AMOUNT_SOURCES:
        out.append('%s: סכום בלי מקור מההסכם או מהלקוח (אין אומדן של המודל)' % where)
    if not (a.get('source_ref') or '').strip():
        out.append('%s: סכום בלי source_ref (הסעיף, או התשובה של הלקוח)' % where)
    if a.get('source') == 'contract' and not (a.get('calc') or '').strip():
        out.append('%s: סכום מההסכם בלי calc (החישוב בשורה אחת, או "כלשון הסעיף")' % where)
    try:
        float(a.get('value'))
    except (TypeError, ValueError):
        out.append('%s: value אינו מספר' % where)
    return out


def _num(a):
    try:
        return float((a or {}).get('value'))
    except (TypeError, ValueError):
        return None


def money_size(x):
    """גודל חשיפה למיון התמונה הכספית: בלתי מוגבל ראשון, אחריו הקצה העליון או הסכום, ובסוף חשיפה בלי סכום."""
    rg = x.get('range') or {}
    if rg.get('high_unlimited'):
        return float('inf')
    for v in (_num(rg.get('high')), _num(x.get('amount')), _num(rg.get('low'))):
        if v is not None:
            return v
    return -1.0


def check_money_picture(reg, idset, err, warn):
    """summary.money_picture: עד שלוש חשיפות, כל סכום עם מקור, בלי סכימה; ובדיקה
    צולבת של הביטוח שההסכם מחייב מול התקרה, ושל תקרות מיותר ממסמך אחד."""
    S = reg.get('summary') or {}
    MP = S.get('money_picture')
    if MP is None:
        warn('summary.money_picture', 'חסר: התמונה הכספית בראש הדוח נבנית רק מסכומים שבסיכונים ומשווי העסקה '
                                      '(מרשם ישן). בהרצה חדשה: עד שלוש החשיפות הגדולות, הביטוח ושווי העסקה')
        return
    X = MP.get('exposures') or []
    for i, x in enumerate(X):
        w = 'money_picture.exposures[%d]' % i
        rids = x.get('risk_ids') or []
        if not rids or any(r not in idset for r in rids):
            err(w, 'risk_ids חסר או לא קיים')
        if not (x.get('what') or '').strip():
            err(w, 'what חובה: החשיפה במילים')
        am, rg = x.get('amount') or {}, x.get('range') or {}
        for p in money_problem(am, w + '.amount') + money_problem(rg.get('low'), w + '.range.low') + \
                money_problem(rg.get('high'), w + '.range.high'):
            err(w, p)
        has_amt = am.get('value') is not None
        has_rg = _num(rg.get('low')) is not None or _num(rg.get('high')) is not None or bool(rg.get('high_unlimited'))
        if has_amt and has_rg:
            err(w, 'סכום מדויק וטווח יחד: טווח רק כשאין סכום מדויק')
        if not has_amt and not has_rg and not (x.get('reason') or '').strip():
            err(w, 'בלי סכום, בלי טווח ובלי reason: כשאין סכום מהמסמכים, הסיבה במשפט אחד')
        lo, hi = _num(rg.get('low')), _num(rg.get('high'))
        if lo is not None and hi is not None and lo > hi:
            err(w, 'קצה תחתון גדול מהעליון')
        if rg.get('high_unlimited') and hi is not None:
            err(w, 'high_unlimited יחד עם high')
        curs = {c for c in ((rg.get('low') or {}).get('currency'), (rg.get('high') or {}).get('currency')) if c}
        if len(curs) > 1:
            err(w, 'שני קצות הטווח במטבעות שונים')
    sizes = [money_size(x) for x in X]
    if sizes != sorted(sizes, reverse=True):
        warn('money_picture.exposures', 'לא לפי הגודל: בלתי מוגבל ראשון, אחריו הסכום או הקצה העליון')
    INS = MP.get('insurance') or {}
    for k in ('required', 'held'):
        for p in money_problem(INS.get(k), 'money_picture.insurance.' + k):
            err('money_picture.insurance', p)
    if (INS.get('held') or {}).get('value') is not None and (INS['held'].get('source') == 'contract'):
        err('money_picture.insurance.held', 'הכיסוי שבידינו אינו נלמד מההסכם: מסמך מבטח או מסירת הלקוח (client)')
    CAPS = MP.get('caps') or []
    for i, c in enumerate(CAPS):
        for p in money_problem(c, 'money_picture.caps[%d]' % i):
            err('money_picture.caps', p)
        if c.get('unlimited') and c.get('value') is not None:
            err('money_picture.caps[%d]' % i, 'unlimited יחד עם value')
    CC = MP.get('cross_checks') or {}
    for k in ('insurance_vs_cap', 'cap_aggregation'):
        # מזהי סיכונים בלבד, כמו כל risk_ids במרשם: "RSK-018", ולא "RSK-018: הממצא"
        for r in CC.get(k) or []:
            if isinstance(r, str) and r not in idset and re.match(r'^\s*[A-Z]+-\d+\s*[:,\s]', r):
                err('money_picture.cross_checks.' + k, 'מזהה סיכון בלבד, בלי טקסט אחריו: %r' % r[:40])
            elif r not in idset:
                err('money_picture.cross_checks.' + k, 'risk id לא קיים: %r' % str(r)[:40])
    # בדיקה צולבת 1: הביטוח שההסכם מחייב מול התקרה
    req = INS.get('required') or {}
    xv = _num(req)
    for c in CAPS:
        yv = _num(c)
        same_cur = not (req.get('currency') and c.get('currency')) or req.get('currency') == c.get('currency')
        gap = None
        if xv is not None and c.get('unlimited'):
            gap = 'ביטוח בסך %s מול אחריות בלתי מוגבלת' % format(xv, ',.0f')
        elif xv and yv and same_cur and max(xv, yv) / min(xv, yv) >= INS_CAP_RATIO:
            gap = 'ביטוח בסך %s מול תקרה של %s' % (format(xv, ',.0f'), format(yv, ',.0f'))
        if gap and not CC.get('insurance_vs_cap'):
            err('money_picture.cross_checks.insurance_vs_cap',
                '%s (%s): פער של פי %d ומעלה הוא ממצא; נדרש סיכון או צירוף, ומספרו כאן' % (
                    gap, c.get('clause') or c.get('document') or '', INS_CAP_RATIO))
            break
    # בדיקה צולבת 2: תקרות מיותר ממסמך אחד, או תקרה שמיובאת ממסמך אחר
    docs = {c.get('document') for c in CAPS if c.get('document')}
    imported = [c for c in CAPS if c.get('imported_from')]
    if (len(docs) > 1 or imported) and not CC.get('cap_aggregation'):
        err('money_picture.cross_checks.cap_aggregation',
            'תקרות ב-%s%s: היחס ביניהן (נצברות או תקרה אחת) הוא ממצא; נדרש סיכון או צירוף, ומספרו כאן' % (
                ', '.join(sorted(docs)), ' (מיובאת מ-%s)' % imported[0].get('imported_from') if imported else ''))


def validate(reg, corpus=None, deal_dir=None, state=None, profile=None, playbook_status=None, known_amendments=None,
             approved_sources=None, case_law_connector=None):
    E, W = [], []
    # pre_send_fixes יצא: במרשם ישן השדה נקרא ומתעלמים ממנו, בלי שגיאה ובלי אזהרה
    reg = {k: v for k, v in (reg or {}).items() if k != 'pre_send_fixes'}

    def err(where, msg):
        E.append('%s: %s' % (where, msg))

    def warn(where, msg):
        W.append('%s: %s' % (where, msg))

    domains, dom_file = approved_domains(approved_sources)
    if not dom_file and ((reg or {}).get('research') or {}).get('sources_checked'):
        err('research', 'קובץ המקורות המאושרים (מקורות-מאושרים.json) לא נקרא: אין רשימת נפילה, ולכן אף מקור אינו '
                        'מאושר. לשמור את הקובץ ולהעביר --approved-sources')

    M = reg.get('meta') or {}
    S = reg.get('summary') or {}
    sv = M.get('source_version') or {}
    ts = sv.get('text_status')

    # ---------- meta ----------
    for k in M:
        if k not in META_KEYS:
            err('meta', 'שדה לא מוכר: %s' % k)
    # display_language נכתב בבנייה (build_risk_report.py), ולכן אינו חובה במרשם
    for k in ('company', 'scope', 'generated_at', 'source_version', 'counterparty'):
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
    if set(br) - {'logo', 'theme'}:
        err('meta.branding', 'שדות נוספים תחת branding')
    if 'theme' in br:
        from common.branding import valid_tokens
        if not valid_tokens(br['theme']):
            err('meta.branding.theme', 'צבעי המותג: שמונה ערכי #RRGGBB מהפרופיל (branding.theme.tokens), כמו שהם')
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
    # שווי העסקה: מכל מקור שבתיקייה, עם ציון המקור; שאלה רק כשאין מקור
    DV = M.get('deal_value') or {}
    if DV.get('amount') is not None:
        for p in money_problem({'value': DV.get('amount'), 'source': DV.get('source'),
                                'source_ref': DV.get('source_ref'), 'calc': DV.get('calc') or 'כלשון הסעיף'},
                               'meta.deal_value'):
            err('meta.deal_value', p)
        if (DV.get('basis') or '').strip() in ('', 'לא ידוע', 'unknown'):
            err('meta.deal_value', 'סכום בלי basis (שנתי או כולל)')
    else:
        if DV.get('source') in AMOUNT_SOURCES:
            warn('meta.deal_value', 'מקור %s בלי סכום' % DV.get('source'))
        hint = deal_value_hint(deal_dir, state) if (deal_dir or state is not None) else None
        if hint:
            warn('meta.deal_value', 'ריק, אבל בתיקיית העסקה יש נתון על התמורה (%s: "%s"). לגזור ממנו, עם ציון '
                                    'המקור (source: client או contract, ו-source_ref); השאלה רק כשאין מקור' % hint)
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
        st = r.get('states')
        if isinstance(st, dict):
            # סכמה 3.7: הציון שבתוקף הוא המוסכם (עם ראיית קבלה ואפקטיביות), ואחרת הנוכחי; מוצע אינו נספר
            ag = st.get('agreed') or {}
            if ag.get('score') is not None and ag.get('acceptance_evidence') and \
                    ag.get('effectiveness') in ('effective', 'partial', 'not_effective'):
                return ag['score']
            if (st.get('current') or {}).get('score') is not None:
                return st['current']['score']
            return (r.get('inherent') or {}).get('score') or 0
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
        # severity_level נגזר בקוד (r3, הסכמה): חסר, אין שגיאה; קיים, חייב להתאים לניקוד
        if r.get('severity_level') is not None and r.get('severity_level') != exp:
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
            if c.get('basis') == 'proposed_text' and ts not in OUR_TEXT_STATUS:
                err(w, 'proposed_text בנוסח שאינו התגובה שלנו או הטיוטה שלנו')
        # סיכון גולמי וסיכון שיורי
        if r.get('kind') == 'hidden_text' and inh.get('score') is not None:
            asks = (r.get('hidden_text') or {}).get('asks_for')
            if inh['score'] < (16 if asks in HIDDEN_ASKS else 9):
                err(w, 'טקסט מוסתר: הגולמי %s לפחות (%s)' % (
                    'קריטי' if asks in HIDDEN_ASKS else 'גבוה', 'מבקש לאשר תנאים או להעביר מידע' if asks in
                    HIDDEN_ASKS else 'r1-intake.md, טקסט מוסתר'))
        live = [c for c in r.get('controls') or [] if c.get('in_place') is not False]
        if res.get('treated'):
            if ts not in TREATED_STATUS:
                err(w, '"טופל" רק בנוסח שלנו או בנוסח מוסכם; בטיוטה של הצד השני הסיכון עוד לא טופל')
            if not live:
                err(w, '"טופל" בלי בקרה קיימת שמתעדת את הטיפול (controls)')
            if not (res.get('treated_how') or '').strip():
                err(w, '"טופל" בלי treated_how: מה נעשה ובאיזה סעיף, במשפט אחד')
            if inh.get('score') is not None and (res.get('score') or 0) >= inh['score']:
                err(w, '"טופל", אבל הדירוג השיורי אינו נמוך מהגולמי')
            if (res.get('score') or 0) > TREATED_MAX_SCORE:
                err(w, '"טופל" בדרגה שיורית %s: מה שטופל במסמך הוא בינוני לכל היותר; אם החשיפה נשארת, היא '
                       'אינה "טופל" (controls ו-residual בלבד)' % {'critical': 'קריטי', 'high': 'גבוה'}.get(
                           lvl(res.get('score') or 0), lvl(res.get('score') or 0)))
        elif ts in TREATED_STATUS and inh.get('score') is not None and res.get('score') == inh.get('score') and \
                any(DELETED_RE.search(c.get('description') or '') for c in live):
            warn(w, 'בקרה קיימת אומרת שהמקור נמחק בנוסח שנבדק, אבל הדירוג השיורי זהה לגולמי (%s). סיכון שטופל '
                    'בתוך המסמך: residual נמוך, treated: true ו-treated_how (r3-scoring.md, סיכון גולמי וסיכון שיורי)'
                    % {'critical': 'קריטי', 'high': 'גבוה', 'medium': 'בינוני', 'low': 'נמוך'}.get(
                        r.get('severity_level'), r.get('severity_level')))
        am = (r.get('exposure') or {}).get('amount') or {}
        if am.get('value') is not None:
            if am.get('source') not in ('contract', 'client'):
                err(w, 'סכום בלי מקור מההסכם או מהלקוח')
            if am.get('source') == 'contract' and not (am.get('source_ref') and am.get('calc')):
                err(w, 'סכום מההסכם בלי סעיף וחישוב')
        if r.get('playbook_flag') not in ('none', 'red_line', 'deviates_from_benchmark'):
            err(w, 'playbook_flag לא חוקי')
        if r.get('playbook_flag') == 'red_line' and M.get('benchmark_status') != 'approved':
            err(w, 'playbook_flag red_line ("מעבר למה שאנחנו מקבלים") רק מול פלייבוק מאושר')
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
        # ויתורים מאוחדים: סיכון "התקבל" אחד לכמה ויתורים באותה עדשה, בינוניים ונמוכים
        crefs = r.get('concession_refs')
        if crefs is not None:
            if not isinstance(crefs, list) or not crefs or not all(isinstance(x, str) and x.strip() for x in crefs):
                err(w, 'concession_refs: רשימה של מזהי סעיפים מקובץ המצב (clause_ref של כל ויתור)')
                crefs = []
            if dec.get('basis') != 'deliberate_waiver':
                err(w, 'concession_refs רק בסיכון שהתקבל בוויתור מכוון (decision.basis: deliberate_waiver)')
            if len(set(crefs)) > 1 and r.get('severity_level') in ('critical', 'high'):
                err(w, 'ויתור מכוון קריטי או גבוה נשאר סיכון נפרד; האיחוד רק לבינוניים ולנמוכים באותה עדשה')
            for x in crefs:
                if RULE_ID_RE.match(x):
                    err(w, 'concession_refs: %s הוא מזהה כלל; נדרש מזהה הסעיף בקובץ המצב' % x)
            if dec.get('state_clause_id') and crefs and dec['state_clause_id'] not in crefs:
                err(w, 'decision.state_clause_id %s אינו ב-concession_refs' % dec['state_clause_id'])
            # הסעיף של כל ויתור מוצג ברשימת הסעיפים בפרק 1, מהעוגן שלו
            have = {a.get('state_clause_id') for a in r.get('anchors') or []}
            miss = sorted({x for x in crefs if x not in have})
            if len(set(crefs)) > 1 and miss:
                err(w, 'concession_refs בלי עוגן משלו (anchors[].state_clause_id): %s. לכל ויתור עוגן עם הסעיף '
                       'והציטוט, כדי שהסעיף יופיע ברשימה בפרק 1' % ', '.join(miss))
        if r.get('created_by_response') and ts not in OUR_TEXT_STATUS:
            err(w, 'created_by_response רק בנוסח שאנחנו מציעים (התגובה או הטיוטה שלנו)')
        src_ids = {s.get('id') for s in (reg.get('research') or {}).get('sources_checked') or []}
        for sid in r.get('external_source_ids') or []:
            if sid not in src_ids:
                err(w, 'external_source_id לא קיים: %s' % sid)
        if r.get('certainty') == 'fact':
            warn(w, 'certainty fact: לוודא שזה רק תיאור הסעיף')
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

    # ---------- deliberate waivers, numbering ----------
    waived = deliberate_waivers(state)
    reopened = reopened_refs(state)
    known_ids = state_clause_ids(state)
    nmap = (state or {}).get('numbering_map') or {}
    # בקשה מפורשת של המשתמש לבדוק את הטיוטה של הצד השני כפי שהתקבלה, גם כשבקובץ המצב יש תגובה שלנו שטרם
    # נשלחה: source_version.user_requested = true, ו-text_status הוא counterparty_draft (r1-intake.md)
    user_req = bool(sv.get('user_requested')) and ts in ('counterparty_draft', 'their_draft')
    if state is not None and state.get('text_status') and not user_req:
        # their_draft (שם ישן בקובץ המצב של הנושא ונותן) נרדף ל-counterparty_draft. text_status הוא של המסמך
        # שנסרק בפועל: כשנמסר המסמך (file או title) והוא שונה מהנוסח האחרון בקובץ המצב, אזהרה; בלי מסמך, שגיאה
        if {'their_draft': 'counterparty_draft'}.get(ts, ts) != {'their_draft': 'counterparty_draft'}.get(
                state['text_status'], state['text_status']):
            if sv.get('file') or sv.get('title'):
                warn('meta.source_version.text_status', 'נסרק %s (%s), והנוסח האחרון בקובץ המצב הוא %s: שורת הכותרת '
                     'אומרת איזה נוסח נבדק' % (ts, sv.get('title') or sv.get('file'), state['text_status']))
            else:
                err('meta.source_version.text_status', '%s, אבל בקובץ המצב text_status הוא %s, ולא צוין איזה מסמך '
                    'נסרק (source_version.file או title)' % (ts, state['text_status']))
    # סוג הנייר מקובץ המצב (למשל tender_awarded): הדוח אומר אותו, ולכן הוא עובר ל-meta.paper_type כמו שהוא
    st_pt = ((state or {}).get('meta') or {}).get('paper_type') or (state or {}).get('paper_type')
    if st_pt and M.get('paper_type') != st_pt:
        err('meta.paper_type', 'בקובץ המצב paper_type הוא %s, ובמרשם %s: להעתיק אותו כמו שהוא (במכרז אחרי זכייה '
                               'התנאים ברובם אינם פתוחים למשא ומתן, והדוח אומר זאת)' % (st_pt, M.get('paper_type')))

    def reopen_note(ref):
        return (' (הוויתור נפתח מחדש בסבב %s: הסיכון אינו "התקבל")' % reopened[ref]) if ref in reopened else ''

    if state is not None:
        # ויתור מכוון: clause_ref הוא מזהה סעיף, וכל ויתור שלא נפתח מחדש מופיע כסיכון שהתקבל
        covered = set()
        for r in R:
            dec = r.get('decision') or {}
            if dec.get('basis') == 'deliberate_waiver':
                covered |= {x for x in [dec.get('state_clause_id')] + list(dec.get('state_clause_ids') or []) +
                            [c for c in r.get('concession_refs') or [] if isinstance(c, str)] if x}
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
                if sc in nmap and a.get('clause') and not numbering_consistent(a['clause'], nm):
                    # רשומה שאינה מספר סעיף, או ציטוט מפסקה אחרת: אזהרה, ו-state_clause_id נשאר
                    why = map_entry_doubt(state, sc, nm, a.get('quote'))
                    (warn if why else err)('risk %s' % r.get('id'), 'clause %r אינו תואם ל-numbering_map (%s)%s' % (
                        a['clause'], nm, ': %s. state_clause_id נשאר; המפה של הנושא ונותן טעונה תיקון' % why
                        if why else ''))
            dec = r.get('decision') or {}
            for dsc in [dec.get('state_clause_id')] + list(dec.get('state_clause_ids') or []):
                if dsc and dsc not in waived:
                    err('risk %s' % r.get('id'), 'decision.state_clause_id %s אינו ויתור מכוון בקובץ המצב%s' % (
                        dsc, reopen_note(dsc)))
            for dsc in r.get('concession_refs') or []:
                if isinstance(dsc, str) and dsc not in waived:
                    err('risk %s' % r.get('id'), 'concession_refs: %s אינו ויתור מכוון בקובץ המצב%s' % (
                        dsc, reopen_note(dsc)))
        # ויתורים מכוונים באותה עדשה, בינוניים ונמוכים: סיכון "התקבל" אחד עם concession_refs[].
        # מרשם קודם עם סיכון לכל ויתור עובר, באזהרה: שורה לכל ויתור תופסת את רוב עמודי הדוח
        by_lens = {}
        for r in R:
            if (r.get('decision') or {}).get('basis') == 'deliberate_waiver' and \
                    r.get('severity_level') not in ('critical', 'high'):
                by_lens.setdefault(r.get('primary_lens'), []).append(r.get('id'))
        for L, rids in sorted(by_lens.items(), key=lambda x: str(x[0])):
            if len(rids) > 1:
                warn('risks', 'ויתורים מכוונים בעדשה %s בכמה סיכונים (%s): לאחד לסיכון "התקבל" אחד, עם '
                              'concession_refs של כל הוויתורים (r3-scoring.md, ויתורים מכוונים)' % (L, ', '.join(rids)))
        # מקור אמת אחד לפלייבוק: כשתנאי ההפעלה אינם מתקיימים, אין סימון
        # המקום הקנוני: שורש קובץ המצב (state_builder 1.2.0); קובץ מצב ישן: playbook_status.playbook_resolution
        pr = state.get('playbook_resolution') or (state.get('playbook_status') or {}).get('playbook_resolution') or {}
        if pr.get('activation_ok') is False:
            for r in R:
                if r.get('playbook_flag') not in (None, 'none'):
                    err('risk %s' % r.get('id'), 'סימון פלייבוק, אבל בקובץ המצב activation_ok הוא false')

    # ---------- combos and defects ----------
    C = reg.get('dangerous_combinations') or []
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

    # ---------- the money picture and the insurance-vs-cap cross-check ----------
    check_money_picture(reg, idset, err, warn)

    # ---------- case law in the text shown (rule 1.1): only from a closed connector ----------
    if not case_law_connector:
        for pth, s in _walk(reg):
            if SKIP_TEXT.search(pth) or pth in QUOTED_USER_TEXT or CASE_LAW_EXEMPT.search(pth):
                continue
            hits = case_law_hits(s)
            if hits:
                err(pth, 'אזכור פסיקה בלי מחבר פסיקה סגור (כלל 1.1): %s. פסיקה רק ממה שמחבר סגור החזיר; '
                         'בלעדיו "טעון בדיקה משפטית"' % '; '.join(hits[:2]))

    # ---------- page budget: cell limits ----------
    for key, where, val in _limit_paths(reg):
        if val and len(val) > LIMITS[key]:
            err(where, 'ארוך מ-%d תווים (%d): לקצר לפני הבנייה' % (LIMITS[key], len(val)))

    # ---------- research: sources, currency, status-dependent statutes ----------
    RS = reg.get('research') or {}
    # אין אימות רגולטורי ברשת. not_permitted הוא הערך של הרצה רגילה; documents_only ו-
    # approved_sources נשארים קריאים במרשם ישן, והאחרון באזהרה
    if RS.get('mode') not in ('not_permitted', 'approved_sources', 'documents_only'):
        err('research', 'mode לא חוקי')
    if RS.get('mode') == 'approved_sources':
        warn('research.mode', 'ערך ישן: אין אימות רגולטורי ברשת, ובהרצה חדשה הערך הוא not_permitted')
    elif RS.get('mode') in ('not_permitted', 'documents_only'):
        # מקור רגולטורי בלי יציאה לרשת: רק מה שתועד במחקר הפלייבוק או במסמך רשמי שצורף (origin), בלי יומן ובלי עותק
        for k in ('search_log', 'raw_copies'):
            if RS.get(k):
                err('research.' + k, 'יציאה לרשת במרשם שאינו מתיר אותה (mode %s). דרישה שלא אומתה במסמכים או '
                                     'בפלייבוק מסומנת "טעון בדיקה משפטית"' % RS.get('mode'))
        for s in RS.get('sources_checked') or []:
            if s.get('origin') not in SOURCE_ORIGINS:
                err(s.get('id') or 'research.sources_checked',
                    'מקור שנבדק ברשת במרשם שאינו מתיר אותה (mode %s): רק מקור מהפלייבוק או מהמסמכים (origin: '
                    'playbook | documents)' % RS.get('mode'))
    conf = {c.get('source_id'): c for c in RS.get('confidence') or []}
    origin_ids = {s.get('id') for s in RS.get('sources_checked') or [] if s.get('origin') in SOURCE_ORIGINS}
    for c in RS.get('confidence') or []:
        if c.get('label') not in ('high', 'medium'):
            err('research.confidence', 'תווית לא חוקית')
        if c.get('label') == 'high' and c.get('source_id') in origin_ids:
            err('research.confidence', 'ודאות גבוהה למקור שלא נפתח בהרצה (%s): בינונית, עם הסיבה' % c.get('source_id'))
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
        if not domain_ok(s.get('url') or '', domains):
            err(w, 'דומיין או נתיב שאינו ברשימה המורשית: %s' % host)
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
        if s.get('origin') not in (None,) + SOURCE_ORIGINS:
            err(w, 'origin לא חוקי (playbook | documents)')
        if deal_dir and s.get('origin') not in SOURCE_ORIGINS:
            rc = raws.get(s.get('url'))
            if not rc:
                err(w, 'אין עותק גולמי')
                continue
            fp = long_path(os.path.join(deal_dir, rc.get('file') or ''))
            if not os.path.exists(fp):
                err(w, 'העותק הגולמי לא נמצא')
                continue
            with open(fp, 'rb') as fh:
                b = fh.read()
            if hashlib.sha256(b).hexdigest() != rc.get('sha256'):
                err(w, 'הגיבוב אינו תואם')
            if rc.get('stored') == 'excerpt_window' and not (rc.get('full_sha256') and rc.get('full_size_bytes')):
                err(w, 'חלון מתוך מסמך גדול בלי full_sha256 ו-full_size_bytes של המסמך המלא')
            if s.get('excerpt'):
                # excerpt = מיקום בדף + הציטוט במירכאות ("סעיף 3(ז): "..."); נבדק מה שבין המירכאה הראשונה
                # לאחרונה; גרשיים בתוך מילה עברית אינם מירכאה (page_text.norm)
                t = None
                if rc.get('text_file'):
                    tp = long_path(os.path.join(deal_dir, rc['text_file']))
                    if not os.path.exists(tp):
                        err(w, 'text_file לא נמצא')
                    else:
                        with open(tp, 'rb') as fh:
                            tb = fh.read()
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
        if not rf or not os.path.exists(long_path(os.path.join(deal_dir, rf))):
            err('entity_research', 'report_file חסר')

    # ---------- displayed text: blocked phrases, codes, dashes, amounts ----------
    he_out = str(M.get('display_language') or 'he').strip().lower()[:2] in ('he', 'iw', 'עב')
    for p, s in _walk(reg):
        if p.startswith('.meta.branding') or p in QUOTED_USER_TEXT:
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
            if b in ADVICE_ONLY and not ADVICE_PATH.search(p):
                continue
            if _term(b).search(s) and not p.startswith('.meta.playbook_ref'):
                err(p, 'ביטוי חסום: %s' % b)
        doc_name = bool(DOC_NAME_PATH.search(p))
        m = next((x for x in CODE_RE.finditer(s) if not (doc_name and ROUND_RE.fullmatch(x.group(0)))), None) or \
            (he_out and CURRENCY_CODE_RE.search(s))
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
    MPV = (S.get('money_picture') or {})
    for a in ([x.get('amount') for x in MPV.get('exposures') or []] +
              [(x.get('range') or {}).get(k) for x in MPV.get('exposures') or [] for k in ('low', 'high')] +
              [(MPV.get('insurance') or {}).get(k) for k in ('required', 'held')] + list(MPV.get('caps') or [])):
        if _num(a) is not None:
            vals.add(int(_num(a)))
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
    disp += bl + [S.get('deal_one_line') or ''] + list(S.get('assumptions') or [])
    disp += [(k.get('what') or '') + ' ' + (k.get('consequence') or '') for k in KD]
    disp += [x.get('item') or '' for x in S.get('not_checked') or []]
    disp += [(x.get('what') or '') + ' ' + (x.get('reason') or '') for x in MPV.get('exposures') or []]
    wc = len(' '.join(disp).split())
    if wc > WORDS_FAIL:
        err('words', 'גוף הדוח %d מילים, מעל %d' % (wc, WORDS_FAIL))
    elif wc > WORDS_WARN:
        warn('words', 'גוף הדוח %d מילים' % wc)
    return E, W


# ---------------- entity-report.json ----------------
BLOCKING_MATCH = ('registration_no', 'name_exact', 'alias', 'name_only')


def validate_entity_report(rep, approved_sources=None, purpose=ENTITY_PURPOSE, case_law_connector=None):
    """התאמת שם מוגדרת, חוסם רק בהתאמה, why חובה, בלי טוקנים, היעדר רישום
    של ישות זרה בישראל אינו ממצא, ומרשם שחסם (CAPTCHA, 403) הוא משימה לעורך הדין ולא עקיפה.
    purpose="entity" (ברירת המחדל: דוח בדיקת רקע הוא תמיד מטרה D) מתיר את מקורות בדיקת
    הרקע ואת כלל התקשורת; בכל מטרה אחרת אין מקור תקשורתי. ממצא רשמי ואות תקשורתי נפרדים: sources[].class,
    media_signals[]. אות תקשורתי אינו בסיס יחיד לדגל אדום, לזהות או לשינוי בדרגה; אין ייחוס כוונה, אין אות על
    אדם פרטי, ואין ידיעה על הליך משפטי (משימה לעורך הדין)."""
    E = []
    domains, dom_file = approved_domains(approved_sources, purpose)
    if not dom_file and rep.get('sources'):
        E.append('sources: קובץ המקורות המאושרים לא נקרא: אין רשימת נפילה, ולכן אף מקור רשמי אינו מאושר')
    meta = rep.get('meta') or {}
    country = ((meta.get('counterparty') or {}).get('country') or '').upper()   # בלי ברירת מחדל ישראלית
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
        if country and country != 'IL' and re.search(r'לא נמצא רישום', f.get('summary') or ''):
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
    # הדומיין של כל מקור מול הרשימה המורשית, כמו ב-research.sources_checked. מקור תקשורתי
    # (class: media) נבדק לפי כלל התקשורת, ורק בבדיקת רקע
    cls = {}
    for i, s in enumerate(rep.get('sources') or []):
        host = re.sub(r'^https?://([^/:]+).*$', r'\1', s.get('url') or '').lower()
        c = s.get('class') or 'official'
        cls[s.get('no')] = c
        if c not in ('official', 'media'):
            E.append('sources[%d]: class לא חוקי (official | media)' % i)
        elif case_law_url(s.get('url') or ''):
            E.append('sources[%d]: %s' % (i, case_law_url(s.get('url') or '')))
        elif c == 'official' and not domain_ok(s.get('url') or '', domains):
            E.append('sources[%d]: דומיין או נתיב שאינו ברשימה המורשית: %s' % (i, host))
        elif c == 'media':
            why = media_problem(s.get('url') or '', approved_sources, purpose)
            if why:
                E.append('sources[%d]: %s' % (i, why))
            for f in ('outlet', 'url', 'published', 'date'):
                if not s.get(f):
                    E.append('sources[%d]: מקור תקשורתי בלי %s (כלי התקשורת, קישור, תאריך פרסום ותאריך בדיקה)' % (i, f))

    def official_in(nos):
        return any(cls.get(n) == 'official' for n in nos or ())

    for i, f in enumerate(rep.get('red_flags') or []):
        if not official_in(f.get('source_nos')):
            E.append('red_flags[%d]: דגל אדום בלי מקור רשמי: אות מהתקשורת אינו בסיס יחיד לממצא' % i)
    if (rep.get('who') or {}).get('source_nos') and not official_in(rep['who']['source_nos']):
        E.append('who: הזהות רק ממקור רשמי, לא מהתקשורת')
    for i, e in enumerate(rep.get('effect_on_risks') or []):
        if e.get('change') in ('up', 'down') and e.get('source_nos') and not official_in(e['source_nos']):
            E.append('effect_on_risks[%d]: שינוי בדרגה רק מממצא רשמי, לא מאות תקשורתי' % i)
    for i, m in enumerate(rep.get('media_signals') or []):
        nos = m.get('source_nos') or []
        if not nos or any(cls.get(n) != 'media' for n in nos):
            E.append('media_signals[%d]: אות תקשורתי נשען רק על מקור תקשורתי ב-sources (class: media)' % i)
        if m.get('blocking'):
            E.append('media_signals[%d]: אות תקשורתי אינו חוסם; ממצא חוסם רק ממקור רשמי' % i)
        if m.get('subject', 'entity') != 'entity':
            E.append('media_signals[%d]: אות רק על הצד שכנגד כתאגיד; אין מידע על אדם פרטי מעבר למרשם הרשמי' % i)
        for w in CASE_LAW_WORDS:
            if _term(w).search(m.get('summary') or ''):
                E.append('media_signals[%d]: ידיעה על הליך משפטי אינה אות (%s): משימה לעורך הדין' % (i, w))
                break
    if rep.get('media_signals') and purpose != ENTITY_PURPOSE:
        E.append('media_signals: תקשורת רק בבדיקת רקע על הצד שכנגד (--purpose entity)')
    # אין ייחוס כוונה: מה שהמקור אומר, לא מה הצד שכנגד התכוון
    texts = [('who', (rep.get('who') or {}).get('text'))]
    texts += [('red_flags[%d]' % i, f.get('summary')) for i, f in enumerate(rep.get('red_flags') or [])]
    texts += [('media_signals[%d]' % i, m.get('summary')) for i, m in enumerate(rep.get('media_signals') or [])]
    texts += [('effect_on_risks[%d]' % i, e.get('why')) for i, e in enumerate(rep.get('effect_on_risks') or [])]
    for where, t in texts:
        hits = [] if case_law_connector else case_law_hits(t or '')
        if hits:
            E.append('%s: אזכור פסיקה בלי מחבר פסיקה סגור (כלל 1.1): %s' % (where, '; '.join(hits[:2])))
        for ph in INTENT_PHRASES:
            if t and _term(ph).search(t):
                E.append('%s: ייחוס כוונה (%s): מתארים מה המקור אומר, ולא כוונה' % (where, ph))
                break
    # חותמת זמן עם שעה היא ISO 8601 מלא עם היסט
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
    with io.open(long_path(p), encoding='utf-8') as fh:
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
    ap.add_argument('--approved-sources', help='מקורות-מאושרים.json שנשמר לדיסק (ברירת מחדל: %s)'
                    % APPROVED_SOURCES_ENV)
    ap.add_argument('--case-law-connector', help='שם מחבר הפסיקה הסגור שהלקוח חיבר בהפעלה הזו (כלל 1.1). בלעדיו, '
                                                 'אזכור פסק דין בטקסט המוצג הוא שגיאה')
    ap.add_argument('--purpose', choices=(ENTITY_PURPOSE,),
                    help='entity: בדיקת רקע על הצד שכנגד, המטרה היחידה שמתירה את מקורות בדיקת הרקע ואת התקשורת '
                         '(דוח בדיקת הרקע נבדק כך גם בלעדיו)')
    a = ap.parse_args(argv)
    reg = _load(a.register)
    E, W = validate(reg, _load(a.corpus) if a.corpus else None, a.deal, _load(a.state) if a.state else None,
                    _load(a.profile) if a.profile else None, _load(a.playbook_status) if a.playbook_status else None,
                    _load(a.amendments) if a.amendments else None, a.approved_sources, a.case_law_connector)
    if a.entity:
        E += ['entity ' + e for e in validate_entity_report(_load(a.entity), a.approved_sources,
                                                            a.purpose or ENTITY_PURPOSE, a.case_law_connector)]
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
