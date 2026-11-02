# -*- coding: utf-8 -*-
"""שער האיכות של הנושא ונותן, במצב עבודה ובמצב משלוח.

כל כשל מקבל קוד קבוע (code), כך שאפשר לבדוק אותו ב-pytest ולהציג אותו בשורה אחת ללקוחה. הקודים זהים בעברית
ובאנגלית: נייר באנגלית נבדק באותן מחלקות, עם אוצר ביטויים באנגלית (lang).
קבוצות הבדיקה:
  PKG_*  החבילה: trackRevisions, מרחבי שמות, תאריכים, מחבר, צבע, מאפיינים, סדר סכמה, אורך נתיב (paths.PATH_LIMIT).
  RT_*   "דחה הכול" שווה לטיוטה שהתקבלה, ו"קבל הכול" שווה לנוסחי היעד. בסבב 2 ואילך הטיוטה שהתקבלה היא המקור כמו
         שהיא, כולל הסימונים הפתוחים שלנו מסבבים קודמים (docx_tracked.prior_revisions), ו"דחה הכול" דוחה רק את
         הסימונים של הסבב הזה. כך גם כל בדיקה אחרת של "השינויים שלנו". RT_DUPLICATE: הוספה שלנו מהסבב הזה שמכפילה
         בפסקה נוסח שכבר בה (docx_tracked.duplicated_insertions).
  BUB_*  הבועות החיצוניות: מונחים אסורים, פסיקה, מקף ארוך, אורך, מספר שאינו בגוף, פתיח שחוזר; ולמה:
         BUB_WHY_MISSING (רכיב שמרע או מזיז את עמדת הצד שכנגד בלי משפט נימוק שקשור אליו) ו-BUB_CLAIM_FALSE
         (טענה בבועה שאינה נכונה מול הנוסח).
  COV_*  כל שינוי שהצד שכנגד רואה נמצא בבועה חיצונית של אותה פסקה (COV_CHANGE_WITHOUT_BUBBLE), וכל רכיב מהותי
         בשינוי נקרא בה בשמו (COV_UNCOVERED_CHANGE). גם שינוי טכני (כותרת, בלוק החתימה) מקבל בועה קצרה. מחיקה של
         טקסט מוסתר עם הבועה הניטרלית (kind: hidden_text_removal בהכרעה) היא שינוי מכוסה; הסימון על טווח שאינו
         מוסתר בטיוטה שהתקבלה הוא COV_HIDDEN_KIND_INVALID.
  CON_*  בועות שסותרות זו את זו, או את הנוסח.
  PH_*   מצייני מקום: שלנו חוסמים משלוח, שלהם מדווחים, ושדה ריק לחתימה (בעברית או באנגלית) אינו חוסם כשהמשתמש
         ענה "נשלים לפני החתימה".
  ID_*   מספר תאגיד שנכשל בבדיקה אינו נכנס לנוסח כאילו הוא תקין.
  GAP_*  פערים שהתגובה יוצרת בעצמה, מהמודול המשותף common/gap_checks.py, בעברית ובאנגלית.
         הסייג "או המועד המרבי שבדין, לפי המוקדם" מותר רק בנוסח מהפלייבוק כלשונו (playbook_verbatim_texts).
  SAFE_*  נוסח בטוח שהרכיב אישר לעצמו. אין LEGAL_REVIEW_OPEN (כלל יסוד 6: עורך דין מאשר את הפלייבוק בלבד):
         סעיף "טעון בדיקה משפטית" הוא NO_APPROVED_SOURCE, פריט גלוי שאינו חוסם. STATE_NO_CLAUSES: במצב משלוח, קובץ מצב
         חסר או בלי סעיפים הוא כשל.
  STATE_* קובץ המצב (state_builder.validate_state), כשהוא נמסר במבנה המלא.
  STRUCT_* פסקה ריקה שהוספנו, ומספר מוקלד כפול בפרק.
  LANG_*, ROUND_*  בדיקה עצמאית S1c (28.10.2026): LANG_HEBREW_IN_EN, אות עברית בנוסח שהכנסנו או בבועה בהסכם באנגלית
          (כשל, חוץ מציטוט של נוסח קיים); BUB_LENGTH לפי שלב הסבב (מטריצת הסבבים, question_batch.ROUND_MATRIX:
          אזהרה מעל max_words או max_sentences, כשל מעל פי 1.5) ו-BUB_PASSIVE_VOICE; BUB_TEXT_MISMATCH,
          בועה שאומרת שמשהו הוסר כשהוא נשאר בנוסח; וכללי הסבבים על שדות קובץ המצב (check_round_rules):
          ROUND_REOPEN_CLOSED, ROUND_CONCESSION_WITHDRAWN, ROUND_RESTORE_NO_BUBBLE (כשלים), ROUND_LAST_FALLBACK_EARLY,
          BUB_REPEATS_REJECTED ו-BUB_REPEATS_REJECTED_ARGUMENT (אזהרות). תיקון עקבי (conforming, conforms_to) אינו
          פתיחה מחדש.
  SILENT_CHANGE_UNDECIDED  שינוי שקט של הסבב (silent_changes, state_builder.unresolved_silent_changes) בלי הכרעה
          מסומנת, או שההכרעה ב-decision_ref אינה בקובץ ההכרעות או לא סומנה בפועל: כשל במצב משלוח, אזהרה במצב עבודה.
          ארבעת קודי הסטטוס של validate_state (STATE_PREMATURE_CLOSED, STATE_CLOSED_OPEN_POINT,
          STATE_REOPEN_WITHOUT_INSTRUCTION, STATE_CLAUSE_STATUS) הם כשל במצב משלוח, כמו כל STATE_*.
  DEC_*   כל הכרעה שאינה accept בקובץ ההכרעות סומנה בקובץ בפועל (DEC_NOT_APPLIED), ובמצב משלוח קובץ ההכרעות
          חובה (DEC_FILE_MISSING). נוסחי היעד (expected_accept) נגזרים ממה שהוחל, ולכן אינם מגלים הכרעה שנשמטה.

אין בשער בדיקת אישורים ואין "מאשר" (החלטת מוצר 1, 14.10.2026). השער אינו קורא את המרשם של מעריך הסיכונים, ושום
ממצא שלו אינו חוסם משלוח; הפרמטר register נשאר בחתימה לתאימות, ואינו בשימוש.

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
from common.case_law import case_law_mentions
from common.terms import terms_re
from orchestrator import pre_send
from orchestrator import state_builder as SB
from orchestrator.question_batch import ROUND_MATRIX, REPLACES_SENT, _sentences as qb_sentences

W = dt.W
LONG_DASH = re.compile('[\u2013\u2014]')
# פסיקה בבועה: המודול המשותף common/case_law.py (הבודק היחיד; חוק, כמו U.S.C., אינו פסיקה)
def case_law_in_text(text):
    """אזכורי פסיקה בטקסט שיוצא לצד שכנגד (רשימה, ריקה כשאין)."""
    return case_law_mentions(text or '')


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
# "policy" אסור במובן "מדיניות החברה" (טענת מדיניות בלי אישור). פוליסת ביטוח ("insurance policy", "the policy and the
# premium receipt") היא מונח של הסעיף, ומותרת: במשפט שיש בו הקשר ביטוחי, או בצירוף "policy of insurance" (S1d-R2)
INSURANCE_CONTEXT = re.compile(r'insur|\bpremiums?\b|underwrit|policyholder', re.I)
INSURANCE_POLICY = re.compile(r'\b(insurance|insurer\W?s?|liability|indemnity|cyber|E&O|D&O)\s+polic(y|ies)\b|'
                              r'\bpolic(y|ies)\s+(of|for)\s+insurance\b', re.I)


def policy_claim_term(text):
    """המונח "מדיניות" או "policy" במובן מדיניות החברה, או None. "policy" שהוא פוליסת ביטוח אינו נספר."""
    for m in FORBIDDEN_UNLESS_CLAIM.finditer(text or ''):
        if m.group(0).lower().startswith('polic'):
            s0 = max(text.rfind('.', 0, m.start()), text.rfind(';', 0, m.start())) + 1
            e0 = min([x for x in (text.find('.', m.end()), text.find(';', m.end())) if x >= 0] or [len(text)])
            if INSURANCE_POLICY.search(text[s0:e0]) or INSURANCE_CONTEXT.search(text[s0:e0]):
                continue
        return m
    return None
PRACTICE_OPENING = {'he': re.compile(r'^\s*(אנחנו נוהגים|אנו נוהגים|כמקובל|בהתאם לנוהג|כנהוג)'),
                    'en': re.compile(r'^\s*(As is customary|In line with (our|market) practice|As standard|'
                                     r'We (normally|usually|always) )', re.I)}
# מציין המקום של השם הרשום באנגלית (S1d, 28.10.2026): כשהכרעה צריכה את שם החברה בהסכם באנגלית ואין בפרופיל
# organization_name_en, apply_redlines.py כותב אותו במקום השם העברי, ו-PH_OURS ו-ENTITY_NAME_EN_MISSING חוסמים משלוח
ENTITY_NAME_EN_PLACEHOLDER = '[Company registered English name]'
# מציין המקום האחיד (כלל 3.5): "[להשלים]", ובאנגלית "[to complete]". הצורה הישנה "[to be completed]" עדיין נתפסת
OUR_PH = re.compile(r'\[להשלים\]|\[to complete\]|\[to be completed\]|\[●\]|\[\s*\d[\d,.\s]*\]|\[[^\]\n]{1,40}\]')
UNDERSCORES = re.compile(r'_{3,}')
THEIR_PH = re.compile(r'_{3,}|\[[^\]\n]{0,40}\]')
COMPANY_NO = {'he': re.compile(r'(ח\.?\s?פ\.?|ע\.?\s?מ\.?|מספר (?:חברה|תאגיד))\s*:?\s*\[?\s*(?P<num>\d[\d\s\-]{5,12}\d)\s*\]?'),
              'en': re.compile(r'(company (?:number|no\.?)|registration (?:number|no\.?)|reg\. no\.)\s*:?\s*\[?\s*'
                               r'(?P<num>\d[\d\s\-]{5,12}\d)\s*\]?', re.I)}
SENT_END = re.compile(r'[.?!](\s|$)')
_REF_NUM = r'\d{1,3}(?:\.\d{1,3})*[א-ת]?(?:\s?\([a-zA-Z0-9א-ת]{1,4}\))*'
CLAUSE_REF = re.compile(r'(?:(?<![א-ת])[ובלמהש]{0,2}(?:סעיפים|סעיף|ס\'|תת-סעיף|נספחים|נספח|פרקים|פרק|תקנה|פסקה)|'
                        r'\b(?:[Cc]lauses?|[Ss]ections?|[Pp]aragraphs?|[Pp]aras?\.?|[Aa]nnex(?:es)?|[Ss]chedules?|'
                        r'[Aa]ppendi(?:x|ces)|[Aa]rticles?|[Ee]xhibits?))\s*' + _REF_NUM +
                        r'(?:\s*(?:,|ו-?|and|or|או|to|עד|-)\s*' + _REF_NUM + r')*')

# ------------------------------------------------------------------------------------------------ תפקידי סעיף
# טקסונומיה כללית של תפקידי סעיף, שחלה בכל סוג הסכם. היא משמשת רק את מנגנון הבועות: מה נקרא בשמו בבועה, ומה דורש משפט נימוק. אין בה שיקול
# משפטי של סוג הסכם מסוים, ואין בה עובדה של לקוחה.
# שם: (טריגר בעברית, שם בבועה בעברית, טריגר באנגלית, שם בבועה באנגלית, האם שינוי בו מרע או מזיז את עמדת הצד שכנגד)
# "own" אחרי כינוי שייכות (its own, their own, the Supplier's own) הוא "עצמי", ולא בעלות
OWN_NOT_POSSESSIVE = (r"(?<!\bits )(?<!\btheir )(?<!\bour )(?<!\byour )(?<!\bhis )(?<!\bher )(?<!\bmy )(?<!'s )"
                      r"(?<!’s )(?<!\bone's )\bowns?\b")
# מתחרה בשלילה ("שאינו מתחרה", "not a competitor"): תנאי כשירות של מבקר או של צד שלישי, ולא הגבלת תחרות
NOT_COMPETITOR_HE = r'(?<!אינו )(?<!אינה )(?<!אינם )(?<!אין )(?<!ולא )(?<! לא )'
NOT_COMPETITOR_EN = r'(?<!not a )(?<!not an )(?<!nor a )(?<!\bno )(?<!non-)'
# "בלעדי" שאינו בלעדיות: "האחראי הבלעדי", "שיקול דעתו הבלעדי", "סמכות שיפוט בלעדית", "הבעלים הבלעדי", "הסעד הבלעדי";
# ובאנגלית exclusive jurisdiction, sole and exclusive remedy, exclusive property or owner. רק בלעדיות מסחרית נספרת
_NOT_EXCL = ('לא', 'אחראי', 'אחראית', 'האחראי', 'האחראית', 'דעתו', 'דעתה', 'דעתם', 'דעתנו', 'הדעת', 'שיפוט', 'השיפוט',
             'בעלים', 'הבעלים', 'סעד', 'הסעד', 'תרופה', 'התרופה', 'רכושו', 'רכושה', 'רכוש')
EXCLUSIVE_HE = r'בלעדיות|' + ''.join(r'(?<!%s )(?<!%s ה)' % (w, w) for w in _NOT_EXCL) + r'(?<![א-ת])ה?בלעדי(?:ת|ים|ות)?(?![א-ת])'
EXCLUSIVE_EN = (r'\bexclusivity\b|(?<!non-)\bexclusive\b(?!\s+(?:and\s+\w+\s+)?(?:jurisdiction|remed(?:y|ies)|property|'
                r'owner(?:ship)?|venue|forum|courts?))')
FUNCTIONS = {
    'מחיר ותמורה': (r'תמורה|מחיר|דמי (רישיון|שימוש|תחזוקה|ניהול)|תעריף|הוצאות',
                    r'תמור|מחיר|דמי|תעריפ|תעריף|הוצא|עלות|תשלום|ישול|תשלמו',
                    r'\bfees?\b|\bprice|\brent\b|\bcharges?\b|consideration|expenses',
                    r'fee|price|rent|charge|consideration|expens|cost', True),
    # "שוטף" הוא מועד תשלום רק כ"שוטף + 30" או אחרי מילת תשלום, ולא "באופן שוטף" או "דיווח שוטף"
    'מועד התשלום': (r'(ישולם|ישולמו|תשולם|משולמת|ישלם|לשלם)[^.\n]{0,60}\d+\s*(יום|ימים|ימי עסקים)|'
                    r'שוטף\s*(\+|פלוס)|(תשלום|ישולם|ישולמו|תשולם|ישלם|לשלם|בתנאי)[:\s]{1,3}שוטף(?![\u05d0-\u05ea])',
                    r'\d+\s*(יום|ימים)|ימי עסקים|ימים|שוטף',
                    r'(payable|paid|pay)[^.\n]{0,60}\d+\s*(calendar |business )?days|net\s*\d+',
                    r'\d+\s*(calendar |business )?days|\bdays\b|\bnet\b', True),
    'ריבית והצמדה': (r'ריבית|פיגורים|הצמדה', r'ריבית|פיגור|הצמד',
                     r'interest|late (payment )?(fee|charge)|indexation', r'interest|late|index', True),
    'קיזוז ועיכבון': (r'לקזז|קיזוז|עיכבון|לעכב', r'קיז|לקזז|עיכבון|לעכב|עיכוב',
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
                    # "own" כשם תואר ("its own costs", "at its own expense") אינו בעלות (S1d-R2)
                    r'intellectual property|ownership|' + OWN_NOT_POSSESSIVE + r'|assigns? all',
                    r'intellectual|own|assign', True),
    'היקף הרישיון': (r'להעברה|רישיונות משנה|רישיון משנה|בלתי חוזר|לצמיתות|כלל-עולמי',
                     r'להעביר|העבר|רישיונות משנה|רישיון משנה|בלתי חוזר|לצמיתות|כלל-עולמי',
                     r'transferable|sublicens|irrevocable|perpetual|worldwide',
                     r'transfer|sublicens|irrevocab|perpetual|worldwide', True),
    'סודיות': (r'ישמור בסוד|חובת (ה)?סודיות|ישמור על סודיות|לא יגלה', r'סוד',
               r'in confidence|confidentiality obligations|shall not disclose|keep[^.\n]{0,30}confidential', r'confiden',
               False),
    'מידע אישי ואבטחת מידע': (r'מידע אישי|פרטיות|אבטחת (ה)?מידע|מחוץ ל(מדינה|ישראל)|לחו"ל',
                              r'מידע אישי|פרטיות|אבטח|עיבוד|מחוץ ל|חו"ל|העבר',
                              r'personal data|privacy|data processing|security incident|de-identif|outside the country',
                              r'personal|privacy|data|security|de-identif|transfer|abroad|outside', False),
    'מחיקה והחזרה': (r'ימחק|ישמיד|מחיקת|השמדת|יחזיר', r'מחק|מחיק|השמד|יושמד|יוחזר|החזר',
                     r'\bdelete|\bdestroy|\breturn (or|all)', r'delet|destroy|return', True),
    # "מבקר שאינו מתחרה" (not a competitor) הוא תנאי כשירות של מבקר, ולא הגבלת תחרות (S1d-R2)
    'הגבלת תחרות ובלעדיות': (NOT_COMPETITOR_HE + r'מתחרה|תחרות|' + EXCLUSIVE_HE, r'מתחר|תחרות|בלעדי|ניגוד עניינים',
                             r'\bcompet(e|es|ing|ition)\b|' + NOT_COMPETITOR_EN + r'\bcompetitors?\b|' + EXCLUSIVE_EN,
                             r'compet|exclusiv|conflict', True),
    'איסור שידול': (r'ישדל|שידול', r'שידול|ישדל|לגייס', r'solicit', r'solicit', True),
    'הסבה וקבלני משנה': (r'להסב|הסבה|להמחות|המחאה|קבלני? משנה', r'הסב|המח|קבלנ',
                         r'\bassign|subcontract', r'assign|subcontract', True),
    'סיום ותקופה': (r'רשאי לסיים|לבטל את ההסכם|בתוקפו|הארכ|חידוש|הודעה מוקדמת',
                    r'סיום|לסיים|לבטל|ביטול|תקופ|הארכ|חידוש|הודעה',
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
                          r'artificial intelligence|\bAI\b|\btrain', r'artificial|(?-i:\bAI\b)|\btrain|\btool', True),
    'ביקורת ופיקוח': (r'ישתף פעולה|זכות ביקורת|לערוך ביקורת|לבקר את', r'מבקר|ביקורת|רשו|פיקוח|שיתוף פעולה|תשתפו',
                      r'right to (audit|inspect)|shall cooperate|audit rights', r'audit|inspect|regulat|cooperat', True),
}
CONCEPTS_HE = {k: (v[0], v[1], v[4]) for k, v in FUNCTIONS.items()}
CONCEPTS_EN = {k: (v[2], v[3], v[4]) for k, v in FUNCTIONS.items()}
CONCEPTS = CONCEPTS_HE  # תאימות לאחור
# תפקיד שהשינוי בו יכול להיות מספר בלבד (30 שהפך ל-60): הטריגר נבדק גם במשפט שהשתנה, ולא רק בטקסט שהוכנס
NUMERIC_FUNCTIONS = ('מועד התשלום',)
# S1d-R2 (28.10.2026): "so the", "given", "as" ומקבילותיהן בעברית הם נימוק. "so" לבדו רק כמילת קישור (אחרי פסיק או
# נקודה-פסיק, או לפני נושא של משפט), ולא "do so", "if so", "or so", "so far" או "so long as" (תנאי)
REASON = {'he': re.compile(r'(?<![\u05d0-\u05ea])ו?(כדי|כי|שכן|לכן|בשל|בגלל|נועד\w*|לפיכך|עקב|לאור|לנוכח|נוכח|'
                           r'בהינתן|שהרי|היות|לצורך|במטרה|מחמת|מטעמי)(?![\u05d0-\u05ea])|'
                           r'מאחר ש|מאחר ו|משום ש|מפני ש|הואיל ו|על כן|כך ש|כדי ש|מכיוון ש|מכיוון ו|על מנת|'
                           r'משום כך|בשל כך|מטעם זה|בשים לב ל|בהתחשב ב'),
          'en': re.compile(r'\b(because|so that|since|in order to|to ensure|to avoid|so as to|given that|otherwise|'
                           r'therefore|hence|thus|as a result|for this reason|due to|owing to|in light of|in view of|'
                           r'which means|this means)\b|'
                           r'\bas (the|this|it|we|you|our|your|these|those|a|an|they|its|their|there|each|both)\b|'
                           r'\bgiven (the|its|their|our|this|these|those|how)\b|'
                           r'(?:[,;]\s*|^\s*)so\b(?!\s+(?:far|long as|much|many)\b)|'
                           r'(?<!\bdo )(?<!\bif )(?<!\bor )(?<!\bdone )(?<!\bdoing )\bso (the|that|it|we|you|they|each|'
                           r'both|any|its|their|our|your|neither|no|this|these|those|a|an)\b', re.I)}
REASON_LEAD = {'he': re.compile(r'^\s*(זאת\s+)?(כדי|כי|מאחר|משום|מפני|הואיל|שכן|לכן|הסיבה|היות|מכיוון|לאור|נוכח|'
                                r'לנוכח|בהינתן|לפיכך|על מנת)'),
               'en': re.compile(r'^\s*(This is |That is |This )?(because|so that|since|in order|to ensure|the reason|'
                                r'given|as a result|for this reason|therefore|hence|this means|otherwise)', re.I)}
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


# מחבר הבועות הפנימיות: בעברית, ובהסכם באנגלית גם השם האנגלי (כשהספרייה המשותפת מגדירה אותו)
INTERNAL_AUTHORS = tuple(x for x in (dt.INTERNAL_AUTHOR, getattr(dt, 'INTERNAL_AUTHOR_EN', None),
                                     'Internal, delete before sending') if x)


def _f(code, message, where=None):
    return {'code': code, 'message': message, 'where': where}


def _sentences(text):
    return [s.strip() for s in re.split(r'(?<=[.?!;])\s+', text) if s.strip()]


def _parse_local(s):
    return _dt.datetime.strptime(s, dt.DATE_FMT_LOCAL if not s.endswith('Z') else dt.DATE_FMT)


def concepts_for(lang):
    return CONCEPTS_EN if lang == 'en' else CONCEPTS_HE


def check_entity_name_en(profile, lang, mode, accept_text=''):
    """ENTITY_NAME_EN_MISSING: בהסכם באנגלית, בלי שם רשום באנגלית לחברה בפרופיל, קובץ העבודה מופק תמיד. השם החסר
    חוסם משלוח רק כשהנוסח צריך אותו בפועל (מציין המקום בנוסח המתקבל או בבועות); כשהסימון אינו משתמש בשם החברה, הוא
    אזהרה בלבד. השם העברי אינו מתועתק ואינו מתורגם."""
    if lang != 'en' or not profile.get('organization_name') or profile.get('organization_name_en'):
        return [], []
    ph = ENTITY_NAME_EN_PLACEHOLDER in (accept_text or '')
    tail = ('העותק למשלוח אינו מופק עד שהשם נמסר ונשמר בפרופיל אצל סוכן ההקמה, וקובץ העבודה מופק מחדש מאותן הכרעות'
            if ph else 'הנוסח שלנו אינו משתמש בשם, ולכן העותק למשלוח מופק; כדאי לשמור את השם בפרופיל לסבב הבא')
    f = _f('ENTITY_NAME_EN_MISSING', 'הסכם באנגלית, ובפרופיל אין שם רשום באנגלית לחברה (organization_name_en)%s. %s. '
           'השם העברי אינו מתועתק ואינו מתורגם' % ('; בנוסח יש מציין מקום %s' % ENTITY_NAME_EN_PLACEHOLDER if ph else '',
                                                    tail))
    return ([f], []) if mode == 'send' and ph else ([], [f])


# תוכן פנימי שאסור שיגיע לצד השני, בעברית ובאנגלית: נספח או פרק פנימי, הוראה למחוק לפני המשלוח, ואזכור של
# הפלייבוק או של מדיניות פנימית. נבדק בגוף, בכותרות העליונות והתחתונות ובכל הבועות של העותק למשלוח
INTERNAL_MARK = re.compile(
    r"sources annex|נספח (?:ה)?מקורות|remove before sending|delete before sending|למחיקה לפני (?:ה)?משלוח|"
    r"(?<![א-ת])לא למשלוח|not for sending|internal only|for internal use|לשימוש פנימי בלבד|טיוטת עבודה פנימית|"
    r"internal work(?:ing)? draft|^\s*(?:internal|פנימי)\s*[.:]?\s*$|:\s*internal\s*\.", re.I | re.M)
PLAYBOOK_MENTION = re.compile(r"(?<![א-ת])[ובלמהש]{0,2}פלייבוק|\bplaybooks?\b|מדיניות(?: ה)?(?:חוזית|פנימית)|"
                              r"\bour (?:internal |contracting )?polic(?:y|ies)\b|\binternal polic(?:y|ies)\b", re.I)


def check_internal_leak(parts, root, comments, mode, ext_ids=()):
    """INTERNAL_LEAK: תוכן פנימי בעותק שהצד השני רואה. במצב משלוח: הגוף, הכותרות והבועות כולן, כשל. במצב עבודה
    (שבו השכבה הפנימית מותרת): רק הגוף והבועות החיצוניות, אזהרה, כדי שהבעיה תיראה כבר בבדיקה הראשונה."""
    F, W_ = [], []
    texts = [('גוף', i, dt.para_text(p)) for i, p in enumerate(dt.body_paragraphs(root))]
    if mode == 'send':
        for name in parts:
            if re.match(r'word/(header|footer)\d*\.xml$', name):
                try:
                    hx = etree.fromstring(parts[name])
                except etree.XMLSyntaxError:
                    continue
                texts.append(('כותרת', name, ''.join(t.text or '' for t in hx.iter(W + 't'))))
    for c in comments:
        if mode == 'send' or c['id'] in set(ext_ids):
            texts.append(('בועה', c['id'], c['text']))
    for where, ref, t in texts:
        m = INTERNAL_MARK.search(t or '') or PLAYBOOK_MENTION.search(t or '')
        if m:
            (F if mode == 'send' else W_).append(_f('INTERNAL_LEAK', 'תוכן פנימי ב%s שהצד השני רואה: "%s"' % (
                where, m.group(0).strip()[:60]), ref))
    return F, W_


def check_lawyer_name_en(profile, lang, mode):
    """LAWYER_NAME_EN_MISSING: הסכם באנגלית, ובפרופיל אין שם באנגלית לעורך הדין. קובץ העבודה מופק בשם מהפרופיל,
    והעותק למשלוח חסום עד שהשם נשמר (build_profile.py של רכיב ההקמה, --set branding.lawyer_name_en)."""
    name = profile.get('lawyer_name') or ''
    if lang != 'en' or profile.get('lawyer_name_en') or not re.search('[֐-׿]', name):
        return [], []
    f = _f('LAWYER_NAME_EN_MISSING', 'הסכם באנגלית, ובפרופיל אין שם באנגלית לעורך הדין (lawyer_name_en): הבועות '
           'חתומות בשם העברי. העותק למשלוח אינו מופק עד שהשם נשמר אצל סוכן ההקמה')
    return ([f], []) if mode == 'send' else ([], [f])


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
    # בטיוטה שהתקבלה. לפני כן כל טיוטה עם שינויים פתוחים נכשלה כאן (20.10.2026)
    others = {e.get(W + 'author') for e in revs} - {author} - set(received_authors or ())
    if others:
        F.append(_f('PKG_AUTHOR', 'סימוני מעקב במחבר אחר: %s' % sorted(x for x in others if x)))
    lo, hi = window
    tz_off = None
    for e in ours:
        d, u = e.get(W + 'date'), e.get(dt.DATE_UTC_ATTR)
        if not d or not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d', d):
            F.append(_f('PKG_DATE_FORMAT', 'w:date בתבנית לא נכונה (שעה מקומית בלי Z): %r' % d))
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
    # סעיף AREO: המירקור הצהוב בקובץ העבודה, בטווח של הבועה הפנימית עם התווית, הוא מכוון. בעותק למשלוח הבועה הוסרה,
    # ולכן כל מירקור שנשאר הוא כשל
    cx = etree.fromstring(parts[dt.COMMENTS_PART]) if dt.COMMENTS_PART in parts else None
    areo_ps = dt.areo_paragraphs(root, dt._areo_comment_ids(cx))
    # הזיהוי לפי הנתיב של הפסקה בעץ, ולא לפי id() של אובייקט lxml: אובייקט כזה נוצר מחדש בכל מעבר, ו-id() שלו
    # אינו יציב, כך שמירקור מכוון של סעיף AREO נספר לפעמים כצבע בטקסט שהוכנס
    tree = root.getroottree()
    areo_paths = {tree.getpath(p) for p in areo_ps}

    def _in_areo(h):
        p = next(h.iterancestors(W + 'p'), None)
        return p is not None and tree.getpath(p) in areo_paths and h.get(W + 'val') == dt.AREO_HIGHLIGHT
    hl_ins = [h for e in ours if local_tag(e) == 'ins' for h in e.iter(W + 'highlight') if not _in_areo(h)]
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
        if c['author'] != author and c['author'] not in INTERNAL_AUTHORS:
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
        m = None if claim else policy_claim_term(t)
        if m:
            F.append(_f('BUB_FORBIDDEN', '"%s" בבועה בלי טענת מדיניות מאושרת' % m.group(0), c['id']))
        cl = case_law_in_text(t)
        if cl:
            # פסיקה לעולם אינה בבועה לצד שכנגד, גם כשהגיעה ממחבר פסיקה סגור: היא בשכבה הפנימית בלבד
            F.append(_f('BUB_CASE_LAW', 'הפניה לפסיקה בבועה: %s' % '; '.join(cl[:3]), c['id']))
        if LONG_DASH.search(t):
            F.append(_f('BUB_LONG_DASH', 'מקף ארוך בבועה', c['id']))
        if len(SENT_END.findall(t + ' ')) > 5:
            F.append(_f('BUB_SENTENCES', 'יותר מחמישה משפטים', c['id']))
        if PRACTICE_OPENING[lang].search(t) or PRACTICE_OPENING['he'].search(t):
            F.append(_f('BUB_PRACTICE_OPENING', 'בועה שנפתחת במשפט נוהג', c['id']))
        # הפניה לסעיף, לנספח או לפרק ("סעיף 13א", "clauses 5.3 and 5.6") אינה סכום: במספור אוטומטי המספר אינו בטקסט
        for num in re.findall(r'\d[\d,]*', CLAUSE_REF.sub(' ', t)):
            if num.strip(',') not in body_text:
                F.append(_f('BUB_NUMBER_NOT_IN_BODY', 'המספר %s אינו בנוסח' % num, c['id']))
        for h in hidden:
            if h and h in t:
                F.append(_f('BUB_DISCLOSURE', 'עובדה שסווגה לנוסח בלבד או פנימית מופיעה בבועה', c['id']))
        # בקול פעיל ("We have replaced", "We have deleted") הפתיח הוא הפועל שאחרי "We have", ולא "We have" עצמו
        words = t.split()
        k = ' '.join(words[:3] if words[:1] and words[0].lower() in ('we', 'אנו', 'אנחנו') else words[:2])
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
            # הוספה אחת שחוצה גבול משפט (סימון רציף מ-docx_tracked) נבדקת לפי כל משפט שבה, אחרת המשפט שבו רק
            # המספר השתנה (30 שהפך ל-45) אינו נחשב "משפט שהשתנה", ובדיקת הכיסוי והנימוק מחמיצה אותו
            pieces.extend(x.strip() for x in _sentences(txt) if len(x.strip()) >= 2 and x.strip() != txt)
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


def _strip_removed(dele, texts):
    """הנוסח שמחקנו בפסקה, בלי טקסט מוסתר שהוסר (kind: hidden_text_removal): הוא אינו תנאי בין הצדדים, והבועה
    הניטרלית אינה קוראת בשמם מושגים שבו."""
    for t in texts or ():
        for x in (t, t.strip()):
            if x and x in dele:
                dele = dele.replace(x, ' ')
                break
    return dele


def check_coverage(root, ext_by_para, author, lang='he', removed=None):
    """(1) כל שינוי שהצד שכנגד רואה נמצא בבועה חיצונית של אותה פסקה, גם שינוי טכני (החלטת מוצר 2).
    (2) כל רכיב מהותי שהוכנס או נמחק בפסקה נקרא בבועה בשמו. removed: {פסקה: [טקסט מוסתר שהוסר]}: מחיקה כזו, עם
    הבועה הניטרלית, היא שינוי מכוסה, ומה שכתוב בטקסט המוסתר אינו נדרש בבועה (check_hidden_removals)."""
    F = []
    conc = concepts_for(lang)
    for i, p, ins, dele, ctx in changed_paragraphs(root, author):
        dele = _strip_removed(dele, (removed or {}).get(i))
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


def check_bubble_why(root, ext_by_para, author, accept_text, lang='he', context=None, removed=None):
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
        trig_dele = _strip_removed(dele, (removed or {}).get(i))
        hit = [name for name, (trig, _, worse) in conc.items()
               if worse and (re.search(trig, ins) or re.search(trig, trig_dele) or
                             (name in NUMERIC_FUNCTIONS and re.search(trig, ctx)))]
        if dt._mark(p) in ('del', 'both') and re.search(RIGHT_WORDS[lang], trig_dele, I):
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


# --------------------------------------------------------------------------------------- שפה, אורך וקול (S1c)
HEB_RUN = re.compile('[֐-׿](?:[֐-׿"\'׳״\\-. ]*[֐-׿])?')


def check_language(root, ext, author, lang, received_text):
    """H1 (בדיקה עצמאית S1c, 28.10.2026): בהסכם באנגלית אין אות עברית בנוסח שהכנסנו (w:ins שלנו) ובבועה החיצונית.
    החריג היחיד: ציטוט של נוסח קיים, כלומר קטע עברי שמופיע כלשונו בטיוטה שהתקבלה. כשל בשני המצבים."""
    F = []
    if lang != 'en':
        return F
    seen = (received_text or '').translate(dt.QUOTE_FOLD)

    def leaks(text):
        return [m.group(0) for m in HEB_RUN.finditer(text or '') if m.group(0).translate(dt.QUOTE_FOLD) not in seen]

    for i, p in enumerate(dt.body_paragraphs(root)):
        bad = leaks(dt.revision_text(p, 'ins', author))
        if bad:
            F.append(_f('LANG_HEBREW_IN_EN', 'אותיות עבריות בנוסח שהכנסנו להסכם באנגלית: "%s". בהסכם באנגלית הישות '
                        'נכתבת בשם הרשום באנגלית (organization_name_en בפרופיל)' % bad[0][:40], i))
    for c in ext:
        bad = leaks(c['text'])
        if bad:
            F.append(_f('LANG_HEBREW_IN_EN', 'אותיות עבריות בבועה בהסכם באנגלית: "%s"' % bad[0][:40], c['id']))
    return F


# תקרת האורך של בועה חיצונית לפי שלב הסבב. המקור האחד הוא מטריצת הסבבים (question_batch.ROUND_MATRIX: max_words,
# max_sentences): אזהרה מעל התקרה של השלב, וכשל מעל פי 1.5 ממנה (BUBBLE_FAIL_FACTOR). (אזהרה מעל, כשל מעל)
BUBBLE_FAIL_FACTOR = 1.5
BUBBLE_WORDS = {s: (r['max_words'], int(r['max_words'] * BUBBLE_FAIL_FACTOR)) for s, r in ROUND_MATRIX.items()}
BUBBLE_SENTENCES = {s: (r['max_sentences'], int(r['max_sentences'] * BUBBLE_FAIL_FACTOR))
                    for s, r in ROUND_MATRIX.items()}
PASSIVE = {'en': re.compile(r'\b(?:is|are|was|were|has been|have been)\s+(?:now\s+)?(?:replaced|deleted|removed|amended|'
                            r'added|inserted|changed|limited|extended|reduced|qualified|completed|incorporated)\b|'
                            r'\bthe (?:revised |amended )?(?:clause|section|provision|paragraph|item|schedule|agreement) '
                            r'now (?:provides|states|covers|requires|says|includes)\b|\bunder the revised (?:clause|section)\b|'
                            r'\bnow replaces?\b', re.I),
           'he': re.compile(r'(?<![א-ת])(?:הוחלפ(?:ה|ו)?|הוחלף|נמחק(?:ה|ו)?|תוקנ(?:ה|ו)|תוקן|הוסף|הוספה|הושלמ(?:ה|ו)|'
                            r'הושלם)(?![א-ת])|הסעיף (?:קובע|כולל|מחייב) כעת')}
ACTIVE = {'en': re.compile(r'\b[Ww]e\b'),
          'he': re.compile(r'(?<![א-ת])ו?(?:שינינו|הוספנו|מחקנו|השארנו|החלפנו|ביקשנו|צמצמנו|הרחבנו|קיבלנו|'
                           r'תיקנו|השלמנו|הסרנו|אנו|אנחנו|נבקש|נשמח|נציע)(?![א-ת])')}


def _round_of(state, decisions=None):
    """מספר הסבב שנבדק: round בקובץ ההכרעות של הסבב, ובלעדיו meta.round_number בקובץ המצב."""
    rnd = (decisions or {}).get('round') if isinstance(decisions, dict) else None
    rnd = rnd or ((state or {}).get('meta') or {}).get('round_number')
    try:
        return int(rnd) if rnd is not None else None
    except (TypeError, ValueError):
        return None


def round_stage(state, decisions=None):
    """שלב הסבב, מאותו מקור ש-state_builder כותב אותו: stage_for_round על מספר הסבב (round בקובץ ההכרעות, או
    meta.round_number), ובלעדיו meta.round_stage. meta.stage ו-stage בשורש נשארים רק כגיבוי לקובץ ישן."""
    st = state or {}
    meta = st.get('meta') or {}
    rnd = _round_of(st, decisions)
    if rnd:
        return SB.stage_for_round(rnd)
    stage = meta.get('round_stage') or meta.get('stage') or st.get('stage')
    return stage if stage in BUBBLE_WORDS else 'opening'


def check_bubble_style(ext, lang, stage):
    """M1 (בדיקה עצמאית S1c): בועה ארוכה מהתקרה של שלב הסבב (BUB_LENGTH: אזהרה מעל max_words או max_sentences של
    השלב במטריצת הסבבים, כשל מעל פי 1.5), ובועה בגוף שלישי סביל ("is replaced with", "the clause now provides")
    בלי "We" (BUB_PASSIVE_VOICE, אזהרה). המשפטים נספרים כמו ב-round_violations. מחזיר (כשלים, אזהרות)."""
    F, W_ = [], []
    stage = stage if stage in BUBBLE_WORDS else 'opening'
    soft, hard = BUBBLE_WORDS[stage]
    s_soft, s_hard = BUBBLE_SENTENCES[stage]
    for c in ext:
        t = c['text'] or ''
        # "This replaces our earlier proposal." (ובעברית "זה מחליף את ההצעה הקודמת שלנו.") אינו נספר באורך, כמו ב-round_violations
        body = re.sub(REPLACES_SENT, ' ', t, flags=re.I).strip() or t
        n, s = len(body.split()), qb_sentences(body)
        if n > hard or s > s_hard:
            F.append(_f('BUB_LENGTH', 'בועה של %d מילים ו-%d משפטים (הגבול בשלב %s: %d מילים, %d משפטים). לקצר: מה '
                        'שינינו, למה, ומה נשאר' % (n, s, stage, hard, s_hard), c['id']))
        elif n > soft or s > s_soft:
            W_.append(_f('BUB_LENGTH', 'בועה של %d מילים ו-%d משפטים (התקרה בשלב %s: %d מילים, %d משפטים)'
                         % (n, s, stage, soft, s_soft), c['id']))
        bl = 'en' if len(re.findall('[A-Za-z]', t)) > len(re.findall('[א-ת]', t)) else 'he'
        m = PASSIVE[bl].search(t)
        if m and not ACTIVE[bl].search(t):
            W_.append(_f('BUB_PASSIVE_VOICE', 'בועה בגוף שלישי סביל ("%s"). קול פעיל: "We have replaced..." / '
                         '"החלפנו..."' % m.group(0), c['id']))
    return F, W_


# M3: בועה שאומרת שמשהו כבר אינו נדרש או הוסר, והביטוי שהיא מתארת נשאר בנוסח אחרי "קבל הכול"
GONE_CLAIM = {'en': [re.compile(r'(?:^|[.;]\s*)(?P<x>[^.;]{3,140}?)\s+(?:is|are)\s+no longer\s+(?:required|needed|necessary|'
                                r'applicable|a condition)', re.I),
                     re.compile(r'\bno longer requires?\s+(?P<x>[^.;,]{3,100})', re.I),
                     re.compile(r'\b(?:removed|deleted|struck out|struck)\s+(?:the (?:words?|phrase|reference to|'
                                r'requirement (?:for|of|that))\s+)?(?P<x>"[^"]{3,100}"|“[^”]{3,100}”)', re.I),
                     re.compile(r'(?P<x>"[^"]{3,100}"|“[^”]{3,100}”)\s+(?:has|have) been (?:removed|deleted)',
                                re.I)],
              'he': [re.compile(r'(?P<x>[^.;]{3,100}?)\s+(?:אינה|אינו|אינם|אינן)\s+נדרש(?:ת|ים|ות)?\s+עוד'),
                     re.compile(r'(?:מחקנו|הסרנו)\s+את\s+(?:הדרישה ל|המילים\s+)?(?P<x>"[^"]{3,100}"|״[^״]{3,100}״|'
                                r'[^.;,]{3,60})')]}
# שם הצד נפתח באות גדולה (בלי re.I, כדי ש-"<Party> to" לא ייתפס כשם), ומילות ההסכמה בכל רישיות
APPROVAL = {'en': re.compile(r'(?i:consent|approval|authori[sz]ation|agreement)\s+of\s+(?:the\s+)?'
                             r'(?P<p>[A-Z][\w-]+(?: [A-Z][\w-]+)?)|'
                             r'(?P<q>[A-Z][\w-]+)\'s\s+(?i:prior\s+)?(?i:written\s+)?(?i:consent|approval)'),
            'he': re.compile(r'(?:הסכמת|אישור|הסכמתה של|אישורו של)\s+(?:ה)?(?P<p>[א-ת]{2,})')}
LIST_LABEL = re.compile(r'^\s*(\(?[ivx]{1,4}\)|\(?[a-z]{1,2}\)|\(?\d{1,2}\)|\(?[א-י]\))\s', re.I)


def _approval_rx(party, lang):
    P = re.escape(party)
    if lang == 'he':
        return re.compile(r'(?:הסכמת|אישור|לפי שיקול דעת|כפי שי?קבע|כפי שתקבע|להנחת דעת)\s+(?:של\s+)?ה?' + P)
    return re.compile(r'(?:consent|approval|authori[sz]ation)\s+of\s+(?:the\s+)?' + P + r'|' + P +
                      r'\'s\s+(?:prior\s+)?(?:written\s+)?(?:consent|approval)|(?:as\s+)?determined\s+by\s+(?:the\s+)?' + P +
                      r'|(?:sole\s+)?discretion\s+of\s+(?:the\s+)?' + P + r'|approved\s+by\s+(?:the\s+)?' + P +
                      r'|to\s+the\s+satisfaction\s+of\s+(?:the\s+)?' + P, re.I)


def _scope(acc, first, last):
    """הפסקאות שהבועה מתארת: הטווח שלה, ואחרי פסקת פתיחה שמסתיימת בנקודתיים, הפריטים שאחריה עד שתווית חוזרת."""
    out = list(range(first, last + 1))
    if acc[last].rstrip().endswith(':'):
        seen = set()
        for j in range(last + 1, min(len(acc), last + 16)):
            m = LIST_LABEL.match(acc[j])
            if not m or m.group(1).strip('()').lower() in seen:
                break
            seen.add(m.group(1).strip('()').lower())
            out.append(j)
    return out


def check_bubble_text_match(root, ext, spans, lang):
    """M3 (בדיקה עצמאית S1c, בועה 143): בועה שאומרת ש-X "is no longer required" או שהוסר, כשהביטוי X נשאר בנוסח
    אחרי "קבל הכול" בפסקאות שהבועה מתארת; ובהסכמה או אישור של צד, גם כשנשאר ניסוח שקול ("as determined by the
    <Party>"). אזהרה (BUB_TEXT_MISMATCH): הבדיקה מכנית, ועורך הדין מכריע אם הבועה או הנוסח מתוקנים."""
    W_ = []
    acc = [_para_accept(p) for p in dt.body_paragraphs(root)]
    fold = lambda s: _norm_ws(s).translate(dt.QUOTE_FOLD).lower()
    for c in ext:
        if c['id'] not in spans:
            continue
        first, last = spans[c['id']]
        scope = fold(' '.join(acc[j] for j in _scope(acc, first, last)))
        raw = ' '.join(acc[j] for j in _scope(acc, first, last))
        bl = 'en' if len(re.findall('[A-Za-z]', c['text'])) > len(re.findall('[א-ת]', c['text'])) else 'he'
        for rx in GONE_CLAIM[bl]:
            hit = None
            for m in rx.finditer(c['text']):
                x = m.group('x').strip().strip('"“”״')
                x = re.sub(r'^(?:the requirement (?:for|of|that)|the reference to|הדרישה ל)\s*', '', x, flags=re.I)
                if len(x) >= 3 and fold(x) in scope:
                    hit = 'הביטוי "%s" נשאר בנוסח' % x[:60]
                else:
                    a = APPROVAL[bl].search(x)
                    party = a and (a.group('p') or (a.groupdict().get('q')))
                    if party:
                        k = _approval_rx(party.strip(), bl).search(raw)
                        if k:
                            hit = 'הבועה אומרת ש-"%s" כבר אינו נדרש, ובנוסח נשאר "%s"' % (x[:50], k.group(0))
                if hit:
                    break
            if hit:
                W_.append(_f('BUB_TEXT_MISMATCH', 'הבועה מתארת תוצאה שהנוסח אינו נותן: %s. לתקן את הנוסח או את הבועה'
                             % hit, c['id']))
                break
    return W_


# --------------------------------------------------------------------------------------- כללי הסבבים בקוד (H3)
MODIFYING_OPS = ('replace', 'replace_span', 'delete_paragraph', 'insert_paragraph')
REOPEN_KINDS = ('reopen', 'reopened', 'reopen_instruction', 'withdraw', 'withdraw_concession')
REOPEN_WHAT = 'פתיחה מחדש בהוראת עורך הדין'   # state_builder.record_reopen, ברשומה ב-concession_history
LAST_OFFERED = ('last_fallback', 'fallback_2', 'reserve', 'last')
NO_TEXT = re.compile(r'^\s*(?:אין|none|n/?a)\b', re.I)


def _is_reopen(h):
    return bool(h.get('reopen') or any(h.get(k) in REOPEN_KINDS for k in ('kind', 'type', 'action'))
                or str(h.get('what') or '').startswith(REOPEN_WHAT))


def _instructed(cl, d, st, cid, since=None):
    """הוראה רשומה של עורך הדין לפתוח מחדש סעיף מוסכם, קבלה שנשלחה או ויתור שנמסר (state_builder.record_reopen,
    "negotiation_state.py reopen"): רשומה ב-reopen_log של הסעיף עם recorded_at, מסבב since ואילך, או התשובה
    שהיא רושמת ב-user_decisions (reopen-<clause_id>-<סבב>, applies_to). reopen_instruction, רשומה ב-concession_history
    מסוג reopen, ו-user_decisions עם reopen או kind, נשארים כגיבוי לקובץ ישן."""
    since = since or 0
    for r in (cl or {}).get('reopen_log') or ():
        if isinstance(r, dict) and r.get('recorded_at') and int(r.get('round') or 0) >= since:
            return True
    if (cl or {}).get('reopen_instruction') or (d or {}).get('reopen_instruction'):
        return True
    for h in (cl or {}).get('concession_history') or ():
        if isinstance(h, dict) and _is_reopen(h) and int(h.get('round') or 0) >= since:
            return True
    for q in (st or {}).get('user_decisions') or ():
        if cid not in (q.get('applies_to') or ()) or q.get('answer_kind') != 'explicit':
            continue
        if str(q.get('id') or '').startswith('reopen-%s-' % cid) or q.get('reopen') or q.get('kind') in REOPEN_KINDS \
                or q.get('situation') in REOPEN_KINDS:
            return True
    return False


def _agreed(st, cl):
    """סעיף מוסכם באמת (CLOSED אמיתי): closed_in_round ו-closed_basis (counterparty_unchanged או
    counterparty_accepted), וכשהוא עדיין CLOSED, גם מסמך שנשלח לפני סבב הסגירה (state_builder.premature_closed).
    הכרעה מאוחרת שמשנה אותו הופכת את הסטטוס ל-MOVING (negotiation_state.merge_clauses), והשדות נשארים."""
    if not isinstance(cl.get('closed_in_round'), int) or cl.get('closed_basis') not in SB.CLOSED_BASES:
        return False
    return not SB.premature_closed(st, cl)


def _delivered_concessions(st, clauses, rnd):
    """{clause_id: הסבב שבו נמסר} לוויתור שנמסר לצד השני לפני הסבב הזה: ויתור מכוון עם delivered_in_round
    (negotiation_state.record_sent), קבלה (accepted_in_round) בסבב שיש לו רשומה ב-sent_documents, ורשומה
    ב-concession_history (who: us) בסבב כזה. ויתור שעוד לא נשלח ניתן לשינוי."""
    out = {}

    def add(cid, r):
        if cid and isinstance(r, int) and r < rnd:
            out[cid] = min(out.get(cid, r), r)

    for w in st.get('deliberate_concessions') or ():
        if isinstance(w, dict) and w.get('clause_ref') and not w.get('reopened_in_round'):
            add(w['clause_ref'], w.get('delivered_in_round'))
    for cid, cl in clauses.items():
        acc = cl.get('accepted_in_round')
        if isinstance(acc, int) and SB.delivered(st, acc) and not _agreed(st, cl):
            add(cid, acc)
        for h in cl.get('concession_history') or ():
            if isinstance(h, dict) and h.get('who') == 'us' and not _is_reopen(h) and isinstance(h.get('round'), int) \
                    and SB.delivered(st, h['round']):
                add(cid, h['round'])
    return out


def _sent_norm(s):
    return re.sub(r'\s+', ' ', (s or '').translate(dt.QUOTE_FOLD)).strip().lower()


def check_round_rules(state, decisions, rroot, root, authors, spans, our_ids, prev_bubbles=(), mode='work'):
    """H3 ופער 9 (בדיקה עצמאית S1c): כללי הסבבים נאכפים בקוד, על השדות ש-state_builder ו-negotiation_state.py
    כותבים בפועל: closed_in_round, closed_basis ו-agreed_text (CLOSED אמיתי), accepted_in_round ו-sent_documents
    (קבלה שנשלחה), delivered_in_round בוויתור המכוון, concession_history (who: us), reopen_log,
    user_decisions.applies_to, last_round_changes ו-meta.deal_context.stance.value; ומקובץ ההכרעות: round,
    offered_now, at_last_fallback, fallback_1, fallback_2 ו-reserve (בסעיף שבקובץ המצב, כגיבוי):
    - ROUND_REOPEN_CLOSED (כשל): הכרעה שמשנה נוסח בסעיף מוסכם (CLOSED אמיתי), בלי הוראה רשומה (reopen_log).
    - ROUND_CONCESSION_WITHDRAWN (כשל): הכרעה שמשנה נוסח בסעיף שוויתרנו עליו, כשהוויתור נמסר בסבב קודם, בלי הוראה.
    - ROUND_LAST_FALLBACK_EARLY (אזהרה): נוסח הנסיגה האחרון כבר בסבב 1, בגישת playbook או stricter.
    - BUB_REPEATS_REJECTED (אזהרה): בועה שחוזרת מילה במילה על משפט מבועה שלנו מסבב קודם, בסעיף שבו ההצעה נדחתה.
    - ROUND_RESTORE_NO_BUBBLE (כשל): מחיקה של הצד שכנגד בתוך הוספה שלנו, שהחזרנו, בלי בועה שלנו על הפסקה.
    - תיקון עקבי (conforming: true עם conforms_to: <הכרעה או סעיף פתוח>) אינו נספר כפתיחה מחדש או כלקיחה בחזרה.
    - BUB_REPEATS_REJECTED_ARGUMENT ו-ROUND_REJECTED_COMPONENT_REOFFERED (אזהרות): רכיב שהצד השני דחה במפורש
      (their_rejected) חוזר בבועה או בנוסח (question_batch.rejected_argument_findings).
    authors: השמות שלנו, המחבר הנוכחי ראשון ואחריו הכינויים מהפרופיל. our_ids: מזהי הבועות החיצוניות שלנו בקובץ.
    prev_bubbles: הבועות שלנו מסבבים קודמים (בשמנו בטיוטה שחזרה). מחזיר (כשלים, אזהרות)."""
    F, W_ = [], []
    st = state or {}
    meta = st.get('meta') or {}
    items = decisions.get('decisions', []) if isinstance(decisions, dict) else (decisions or [])
    rnd = _round_of(st, decisions) or 1
    clauses = {c.get('clause_id'): c for c in st.get('clauses') or () if isinstance(c, dict)}
    conceded = _delivered_concessions(st, clauses, rnd)
    names = {a for a in authors or () if a}
    rparas = dt.body_paragraphs(rroot) if rroot is not None else []

    def their_now(d, cl, cid):
        # הצד שכנגד שינה את הסעיף בסבב הזה (שינוי שקט, שינוי מסומן שלהם בפסקה, דחייה, או פתיחה של סעיף מוסכם):
        # הכרעה שעונה לשינוי, למשל החזרה לנוסח שנשלח או לנוסח המוסכם, אינה פתיחה מחדש ואינה לקיחה בחזרה
        j = d.get('para')
        if any(isinstance(x, dict) and int(x.get('round') or 0) == rnd and (x.get('clause_id') == cid or (
                isinstance(j, int) and x.get('received_para') == j)) for x in st.get('silent_changes') or ()):
            return True
        if (cl.get('reopened_by_counterparty') or {}).get('round') == rnd or any(
                isinstance(r, dict) and r.get('by') == 'them' and r.get('round') == rnd for r in cl.get('rejections') or ()):
            return True
        return isinstance(j, int) and 0 <= j < len(rparas) and any(
            e.get(W + 'author') not in names for e in rparas[j].iter(W + 'ins', W + 'del'))

    stance = (meta.get('deal_context') or {}).get('stance')
    stance = (stance.get('value') if isinstance(stance, dict) else stance) or 'playbook'
    by_id = {d.get('id'): d for d in items}

    def conforming_ok(d):
        # תיקון עקבי (conforming, conforms_to) בעקבות הכרעה בנושא פתוח, כדי שההסכם לא יסתור את עצמו: אינו פתיחה
        # מחדש ואינו לקיחה בחזרה (S1d-R2). conforms_to הוא הכרעה בקובץ הזה שמשנה נוסח או משיבה בבועה, או סעיף פתוח
        if not (d.get('conforming') and d.get('conforms_to')):
            return False
        ref = d['conforms_to']
        main = by_id.get(ref)
        if main is not None and main is not d:
            return main.get('op') in MODIFYING_OPS + ('comment_only',)
        ref_cl = clauses.get(ref)
        return bool(ref_cl) and ref_cl.get('status') not in ('CLOSED',) and not _agreed(st, ref_cl)

    for d in items:
        cid = d.get('clause_id') or d.get('id')
        cl = clauses.get(cid) or {}
        changes = d.get('op') in MODIFYING_OPS and not their_now(d, cl, cid) and not conforming_ok(d)
        closed = cl.get('closed_in_round')
        if changes and _agreed(st, cl) and closed <= rnd and not _instructed(cl, d, st, cid, closed):
            F.append(_f('ROUND_REOPEN_CLOSED', 'ההכרעה משנה נוסח בסעיף שהוסכם בסבב %d, בלי הוראה רשומה לפתוח אותו מחדש. '
                        'פתיחה מחדש רק בהוראת עורך הדין: negotiation_state.py reopen --clause %s --instruction '
                        '"<ההוראה>" --reason "<הסיבה>" (reopen_log, עם התאריך)' % (closed, cid), d.get('id')))
        elif changes and cid in conceded and not _instructed(cl, d, st, cid, conceded[cid]):
            F.append(_f('ROUND_CONCESSION_WITHDRAWN', 'ההכרעה משנה נוסח בסעיף שוויתרנו עליו, והוויתור נמסר לצד השני בסבב '
                        '%d: ויתור שנמסר אינו נלקח בחזרה בלי הוראה רשומה של עורך הדין (negotiation_state.py reopen)'
                        % conceded[cid], d.get('id')))
        if rnd == 1 and stance in ('playbook', 'stricter'):
            opts = []
            for o in (d, cl):
                opts = [x for x in [o.get('fallback_1'), o.get('fallback_2')] + list(o.get('reserve') or ())
                        if isinstance(x, str) and x.strip() and not NO_TEXT.match(x)]
                if opts:
                    break
            last = opts[-1] if opts else None
            new = _sent_norm(' '.join(str(d.get(k) or '') for k in ('new', 'new_text', 'text')))
            on = d.get('offered_now') or cl.get('offered_now')
            if d.get('at_last_fallback') or on in LAST_OFFERED or (last and len(last) >= 20 and _sent_norm(last) in new):
                W_.append(_f('ROUND_LAST_FALLBACK_EARLY', 'נוסח הנסיגה האחרון מוצע כבר בסבב 1, בגישת %s: לא נשאר '
                             'מרווח לסבבים הבאים' % stance, d.get('id')))
    # בועות שלנו מסבבים קודמים: הבועות בשמנו בטיוטה שחזרה (המקור בפועל). אין כותב לשדות ההיסטוריה בקובץ המצב
    # (external_comment_history, previous_external_comments), והם נקראים רק כגיבוי לקובץ שנכתב ביד
    prev = list(prev_bubbles or ())
    for cl in clauses.values():
        for k in ('external_comment_history', 'previous_external_comments'):
            prev += [x if isinstance(x, str) else (x or {}).get('text', '') for x in cl.get(k) or ()]
    old_sents = {_sent_norm(s) for t in prev for s in _sentences(t or '') if len(s.split()) >= 8}
    if rnd > 1:
        # רכיב שהצד השני דחה במפורש (their_rejected): הבועה אינה חוזרת על הטיעון בו, והנוסח אינו מציע אותו שוב
        # (S1d-R2). מול הבועות שלנו מסבבים קודמים בטיוטה שחזרה; round_tools.py round-rules בודק מול השרשור עצמו
        from orchestrator.question_batch import rejected_argument_findings
        for d in items:
            for x in rejected_argument_findings(d, previous=prev):
                W_.append(_f('BUB_REPEATS_REJECTED_ARGUMENT' if x['code'] == 'ROUND_REPEATS_REJECTED_ARGUMENT'
                             else x['code'], x['message'], d.get('id')))
    if old_sents and rnd > 1:
        for d in items:
            bub = d.get('external_comment') or ''
            rep = [s for s in _sentences(bub) if len(s.split()) >= 8 and _sent_norm(s) in old_sents]
            if rep:
                cl = clauses.get(d.get('clause_id') or d.get('id')) or {}
                why = ' (ההצעה נדחתה בסבב הקודם)' if any(k in SB.THEIR_REJECTION for k in cl.get('last_round_changes')
                                                            or ()) else ''
                W_.append(_f('BUB_REPEATS_REJECTED', 'הבועה חוזרת מילה במילה על נימוק מסבב קודם%s: "%s". נימוק שנדחה '
                             'אינו חוזר בלי חידוש: עונים לנימוק שלהם, או מוסיפים נימוק חדש' % (why, rep[0][:80]),
                             d.get('id')))
    # פער 9: מחיקה של הצד שכנגד בתוך הוספה שלנו מסבב קודם, שהחזרנו (דחינו את המחיקה), בלי בועה
    if rroot is not None:
        work = _received_groups(root, authors[0]) if authors else []
        wpos = {id(p): k for k, p in enumerate(dt.body_paragraphs(root))}
        covered = {k for cid, (a, b) in spans.items() if cid in our_ids for k in range(a, b + 1)}
        by_para = {d.get('para'): d for d in items if isinstance(d.get('para'), int)}
        for j, p in enumerate(rparas):
            gone = []
            for e in p.iter(W + 'del'):
                if e.get(W + 'author') in names or e.getparent().tag == W + 'rPr':
                    continue
                if any(a.tag == W + 'ins' and a.get(W + 'author') in names for a in e.iterancestors()):
                    gone.append(''.join(t.text or '' for t in e.iter(W + 'delText')))
            gone = [g for g in gone if g.strip()]
            if not gone or j >= len(work):
                continue
            wp = work[j]
            acc = _para_accept(wp)
            their_del = ''.join(t.text or '' for e in wp.iter(W + 'del') if e.get(W + 'author') not in names
                                for t in e.iter(W + 'delText'))
            restored = [g for g in gone if g in acc and g not in their_del]
            if not restored:
                continue
            d = by_para.get(j) or {}
            if wpos.get(id(wp)) in covered or d.get('external_comment'):
                continue
            F.append(_f('ROUND_RESTORE_NO_BUBBLE', 'החזרנו נוסח שלנו שהצד שכנגד מחק ("%s") בלי בועה: דחייה ב-Word אינה '
                        'משאירה סימון, ולכן הבועה אומרת מה מחקו, מה החזרנו ולמה' % restored[0].strip()[:60], j))
    return F, W_


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


def _digits(s):
    return re.sub(r'\D', '', s or '')


def _our_names(profile):
    return [str(x).strip().lower() for x in (profile.get('organization_name'), profile.get('organization_name_en'))
            if x and len(str(x).strip()) > 2]


def check_identifiers(root, author, profile, lang='he', received_text=''):
    # ספרת ביקורת רק ברישום ישראלי (ids.israeli_registry). מספר זר נבדק רק מול הפרופיל. כשהפרופיל אינו
    # מכריע אם הרישום ישראלי, מספר שנכשל בבדיקה הישראלית הוא אזהרה ולא כשל.
    # בדיקת הפורמט וההשוואה לפרופיל חלות רק על מספר שלנו: בפסקה שבה שם החברה שלנו (או בשתי הפסקאות שלפניה, בבלוק
    # הצדדים), או מספר זהה לזה שבפרופיל. מספר אחר שהכנסנו (של הצד שכנגד או של צד שלישי, בכל מדינה) נבדק רק מול
    # המסמך שהתקבל: כשאינו שם, אזהרה.
    F, W_ = [], []
    israeli = ids.israeli_registry(profile)
    raw_prof = profile.get('organization_id') or profile.get('registration_number')
    prof = ids.validate_company_number(raw_prof, israeli=israeli is not False) if raw_prof else None
    names = _our_names(profile)
    paras = dt.body_paragraphs(root)
    # הנוסח הגלוי של כל פסקה אחרי קבלה (w:t, בלי w:delText), במספור של קובץ העבודה
    acc_views = [''.join(t.text or '' for t in p.iter(W + 't')) for p in paras]
    src_digits = _digits(received_text)
    rx = COMPANY_NO[lang]
    for i, p in enumerate(paras):
        ins = dt.revision_text(p, 'ins', author)
        here = acc_views[i].lower()
        prev = acc_views[i - 1].lower() if i else ''
        # שלנו: שם החברה שלנו באותה פסקה, או בפסקה שלפניה כשהפסקה הזו היא שורת המספר בלבד ("ח.פ. ...")
        label_only = bool(re.match(r'\s*\(?\s*(?:ח\.?\s?פ|ע\.?\s?מ|מספר|company|registration|reg\.)', here, re.I))
        mine = any(n in here for n in names) or (label_only and any(n in prev for n in names))
        for m in rx.finditer(ins):
            num_d = _digits(m.group('num'))
            ours = mine or (bool(raw_prof) and num_d == _digits(raw_prof))
            if not ours:
                if src_digits and num_d not in src_digits:
                    W_.append(_f('ID_NUMBER_NOT_IN_SOURCE', 'מספר רישום שהוכנס לנוסח, שאינו של החברה שלנו, אינו '
                                 'במסמך שהתקבל: %s' % m.group('num'), i))
                continue
            v = ids.validate_company_number(m.group('num'), israeli=israeli is not False)
            same = bool(prof) and v['number'] == prof['number']
            if not v['valid']:
                (F if israeli else W_).append(_f('ID_COMPANY_NUMBER', 'מספר תאגיד שנכשל בבדיקה (%s) הוכנס לנוסח: %s'
                                                 % (v['reason'], m.group('num')), i))
                if israeli is None and prof and not same:
                    F.append(_f('ID_COMPANY_NUMBER', 'מספר תאגיד שונה מהפרופיל: %s' % m.group('num'), i))
            elif prof and (prof['valid'] or israeli is not True) and not same:
                F.append(_f('ID_COMPANY_NUMBER', 'מספר תאגיד שונה מהפרופיל: %s' % m.group('num'), i))
            elif not prof and israeli is False:
                W_.append(_f('ID_COMPANY_NUMBER', 'אין מספר רישום בפרופיל להשוואה: %s' % m.group('num'), i))
        plain = ''.join(dt._node_text(n) for n, anc in dt._text_nodes(p)
                        if 'ins' not in anc and 'del' not in anc and dt.local(n.tag) != 'delText')
        for m in rx.finditer(plain):
            # מספר של הצד שכנגד: מדינת ההתאגדות שלו אינה ידועה, ולכן אזהרה רק על מספר בן 9 ספרות שנכשל
            v = ids.validate_company_number(m.group('num'))
            if not v['valid'] and v['reason'] not in ('wrong_length', 'not_digits'):
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


NUM_PREFIX = re.compile(r'^\s*(\d+(\.\d+)*\.?|\(?[\dא-תa-z]{1,2}\))\s+', re.I)


def _norm_ws(s):
    return re.sub(r'\s+', ' ', s or '').strip()


def _norm_cmp(s):
    return _norm_ws(s).translate(dt.QUOTE_FOLD)


def playbook_verbatim_texts(state):
    """נוסחים שנלקחו מהפלייבוק כלשונם, מקובץ המצב: נוסחי הפלייבוק שבהכרעה PolicyDerived (בלי
    deviation_from_approved ובלי safe_wording, שהוא נוסח של הרכיב), ורכיבי basis_elements מסוג PolicyDerived
    (התאמה לעסקה נרשמת כרכיב ExpertJudgment נפרד, n8-state-schema.md)."""
    out = []
    for cl in (state or {}).get('clauses', []):
        texts = [b.get('element') for b in cl.get('basis_elements') or [] if b.get('source') == 'PolicyDerived']
        if cl.get('decision_basis') == 'PolicyDerived' and not cl.get('deviation_from_approved') \
                and not cl.get('safe_wording'):
            texts += [cl.get(k) for k in ('playbook_default', 'fallback_1', 'fallback_2')] + list(cl.get('reserve') or [])
        out += [_norm_ws(x) for x in texts if isinstance(x, str) and x.strip()]
    return out


def _cap_from_playbook(t, lang, verbatim):
    """הסייג "או המועד המרבי שבדין, לפי המוקדם" מותר רק כשכל משפט בפסקה שמפנה למועד בדין נמצא כלשונו בנוסח
    מהפלייבוק (הבונה כותב אותו רק כשהדין החל קובע מועד מרבי, evidence-policy.md). נוסח שהרכיב כתב: אסור."""
    X = gap_checks.P.get(lang) or gap_checks.P[gap_checks.detect_lang(t)]
    I = re.I if lang == 'en' else 0
    # משפט מסתיים בסימן פיסוק ורווח (_sentences), כדי ש-"5.1" לא יפצל אותו; מספור בראש הפסקה אינו חלק מהנוסח
    hits = [NUM_PREFIX.sub('', s) for s in _sentences(t) if re.search(X['pay_latest'], s, I)]
    return bool(verbatim and hits) and all(any(_norm_ws(s) in v for v in verbatim) for s in hits)


def check_self_created_gaps(root, author, accept_text, lang='he', context=None, state=None):
    """פערים שהתגובה יוצרת בעצמה, מהמודול המשותף (common/gap_checks.py): על כל פסקה שהכנסנו, ועל ההסכם כולו.
    state: קובץ המצב. ממנו נגזר allow_statutory_cap לכל פסקה בנפרד (_cap_from_playbook), ולעולם לא גורף."""
    F, seen = [], set()
    ctx = dict(context or {})
    ctx['accept_text'] = accept_text
    ctx.pop('allow_statutory_cap', None)
    verbatim = playbook_verbatim_texts(state)
    ours = touched_paragraphs(root, author)
    for t in ours:
        pctx = dict(ctx, allow_statutory_cap=True) if _cap_from_playbook(t, lang, verbatim) else ctx
        for x in gap_checks.check_wording(t, lang, context=pctx):
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
    if state and 'meta' in state:
        from orchestrator.state_builder import validate_state
        for e in validate_state(state):
            (F if mode == 'send' else W_).append(_f(e['code'], e['message'], e['where']))
    return F, W_


CHANGE_OPS = ('replace', 'replace_span', 'insert_paragraph', 'delete_paragraph')


def check_legal_review(state, decisions, core, mode):
    """אין חסימה של עורך דין (כלל יסוד 6): עורך דין מאשר את הפלייבוק בלבד, והנושא ונותן שואל את רשימת השאלות שלו
    ומוסר. סעיף שהפלייבוק או ההכרעה מסמנים "טעון בדיקה משפטית" אינו חוסם ואינו מחכה ל"נבדק": הוא פריט גלוי ללקוח,
    NO_APPROVED_SOURCE, "AREO לא מצאה מקור מורשה לנקודה זו", עם צעד אחד הלאה (כלל יסוד 5), ואינו ממולא מהזיכרון.
    נשאר חוסם רק STATE_NO_CLAUSES: במצב משלוח קובץ מצב חסר או בלי סעיפים הוא כשל של שלמות מבנית, כי השער אינו יכול
    לדעת מה הוכרע. לכן write רץ לפני השער."""
    F, W_ = [], []
    st = state or {}
    items = decisions.get('decisions', []) if isinstance(decisions, dict) else (decisions or [])
    flagged = []
    for cid in [c.get('clause_id') for c in st.get('clauses') or () if c.get('legal_review_required')] +             [d.get('id') for d in items if isinstance(d, dict) and d.get('legal_review_required')]:
        if cid and cid not in flagged:
            flagged.append(cid)
    if flagged:
        nm = st.get('numbering_map') or {}
        W_.append(_f('NO_APPROVED_SOURCE',
                     'AREO לא מצאה מקור מורשה לנקודה זו: %s. הצעד הבא: להוסיף לתיקיית ההסכמים של החברה הסכם שמסדיר '
                     'אותה, או לאשר עמדה בפלייבוק. אינו מעכב את המשלוח' % ', '.join(nm.get(c) or c for c in flagged),
                     ','.join(flagged)))
    if not st.get('clauses'):
        (F if mode == 'send' else W_).append(_f(
            'STATE_NO_CLAUSES', 'קובץ המצב חסר או בלי סעיפים. השער במצב משלוח צריך את קובץ המצב של הסבב: הריצו קודם '
            'negotiation_state.py write עם קובץ ההכרעות, ואחריו את השער עם --deal (או --state)'))
    return F, W_


def _our_ins_mark(p, author):
    rpr = p.find(W + 'pPr/' + W + 'rPr')
    m = rpr.find(W + 'ins') if rpr is not None else None
    return m is not None and m.get(W + 'author') == author


def _our_del_mark(p, author):
    """פסקה שסימן הפסקה שלה במחיקה שלנו, ואין בה טקסט גלוי שאינו במחיקה שלנו (פסקה שמחקנו כולה)."""
    rpr = p.find(W + 'pPr/' + W + 'rPr')
    m = rpr.find(W + 'del') if rpr is not None else None
    if m is None or m.get(W + 'author') != author:
        return False
    for t in p.iter(W + 't'):
        if (t.text or '').strip() and not any(dt.local(a.tag) == 'del' for a in t.iterancestors()):
            return False
    return True


def _received_groups(root, author):
    """לכל פסקה בטיוטה שהתקבלה, הפסקה המקבילה בקובץ העבודה, באותו מיפוי כמו reject_ours_view: פסקה שהוספנו
    (סימן פסקה בהוספה שלנו) מתמזגת עם הבאה. מכל קבוצה נבחרת הפסקה שיש בה טקסט שאינו הוספה שלנו."""
    out, group = [], []
    for p in dt.body_paragraphs(root):
        group.append(p)
        if _our_ins_mark(p, author):
            continue
        out.append(group)
        group = []
    if group:
        out.append(group)

    def theirs(q):
        return any(('ins', author) not in dt._revision_of(n, q) for n, anc in dt._text_nodes(q))

    return [next((q for q in reversed(g) if theirs(q)), g[-1]) for g in out]


def check_decisions_applied(root, received_texts, decisions, author, our_comment_ids=(), received_paras=None,
                            prior=(), received_rej=None):
    """באג 3 (הרצה S1b, 28.10.2026): השער משווה את ההכרעות עצמן, ולא את נוסחי היעד שנגזרו ממה שהוחל בפועל.
    כל הכרעה שאינה accept חייבת להופיע בקובץ: replace_span ו-replace בנוסח המתקבל, מחיקת פסקה כפסקה שכל הטקסט
    שלה נמחק בשמנו, הוספת פסקה כפסקה שהוספנו, ובועה בלבד כבועה חיצונית בשמנו באותה פסקה. הכרעה שלא סומנה היא
    DEC_NOT_APPLIED, כשל בשני המצבים: העותק למשלוח אינו מופק, וקובץ העבודה אינו מסומן כתקין.
    received_rej: הנוסח של כל פסקה אחרי דחיית השינויים של הצד שכנגד (received_reject_text, הסימונים שלנו מסבבים
    קודמים נשארים). הכרעה שדוחה את השינויים שלהם בפסקה (their_changes: reject) נכתבת מול הנוסח הזה, ו-old נספר בו
    (S1d-R2, 13(ii): old מתוך ההוספה שלנו שחזרה בדחייה נספר בנוסח הגלוי, שבו הוא מחוק, ו-replace_span שסומן נכשל)."""
    F = []
    # הגרשיים בנוסח שסומן מותאמים למסמך (docx_tracked.match_quotes, L3), ולכן ההשוואה בלי הבדל ביניהם
    items = decisions.get('decisions', []) if isinstance(decisions, dict) else (decisions or [])
    work = _received_groups(root, author)
    if len(work) != len(received_texts):
        return [_f('DEC_NOT_APPLIED', 'קובץ העבודה אינו מתמפה לטיוטה שהתקבלה (%d פסקאות מול %d): אי אפשר לאמת '
                   'שההכרעות סומנו' % (len(work), len(received_texts)))]
    spans = dt.comment_paragraph_spans(root)
    paras = dt.body_paragraphs(root)
    pos = {id(p): k for k, p in enumerate(paras)}

    def ours(p, kind):
        return bool(dt.revision_text(p, kind, author)) or (kind == 'del' and any(
            e.get(W + 'author') == author for e in p.iter(W + 'del')))

    for d in items:
        op, did, j = d.get('op'), d.get('id', '?'), d.get('para')
        if op in (None, 'accept'):
            continue
        ok, why = True, ''
        if op in ('replace_span', 'replace', 'delete_paragraph', 'comment_only'):
            if not isinstance(j, int) or not 0 <= j < len(work):
                F.append(_f('DEC_NOT_APPLIED', '%s: אין פסקה %s בטיוטה' % (did, j), did))
                continue
            p = work[j]
            acc = _norm_cmp(_para_accept(p))
        if op == 'replace_span':
            old, new = _norm_cmp(d.get('old')), _norm_cmp(d.get('new'))
            changed = ours(p, 'ins') or ours(p, 'del')
            base = received_texts[j]
            if received_rej is not None and j < len(received_rej) and dt.their_changes_mode(d) == 'reject':
                base = received_rej[j]
            ok = changed and (not new or new in acc) and (old in new or acc.count(old) < _norm_cmp(base).count(old))
            if not ok and received_paras is not None and prior and j < len(received_paras):
                # למחוק מחדש טקסט שהמחיקה הפתוחה שלנו מסבב קודם עדיין עליו: ההכרעה קיימת בטיוטה שהתקבלה
                # (docx_tracked.prior_edit_exists), ו-apply_redlines מדווח אותה "קיימת מסבב קודם"
                try:
                    ok = bool(dt.prior_edit_exists(received_paras[j], d.get('old'), dt.match_quotes(
                        d.get('new') or '', dt.quote_style(received_texts)), prior)) and (not new or new in acc)
                except dt.UnsupportedEdit:
                    ok = False
            why = 'הטווח "%s" לא סומן' % (d.get('old') or '')[:40]
        elif op == 'replace':
            ok = acc == _norm_cmp(d.get('new_text'))
            why = 'נוסח היעד לא סומן'
        elif op == 'delete_paragraph':
            ok = not acc and (ours(p, 'del') or not _norm_cmp(received_texts[j]))
            why = 'הפסקה לא נמחקה'
        elif op == 'insert_paragraph':
            want = _norm_cmp(d.get('text'))[-60:]
            ok = bool(want) and any(want in _norm_cmp(_para_accept(q)) for q in paras if dt._mark(q) == 'ins'
                                    or ('ins', author) in [r for n, _ in dt._text_nodes(q)
                                                           for r in dt._revision_of(n, q)])
            why = 'הפסקה החדשה לא נוספה'
        elif op == 'comment_only' and d.get('external_comment'):
            k = pos.get(id(p))
            ok = k is not None and any(first <= k <= last for cid, (first, last) in spans.items()
                                       if cid in our_comment_ids)
            why = 'הבועה לא נוספה'
        if not ok:
            F.append(_f('DEC_NOT_APPLIED', '%s (%s): %s. ההכרעה לא סומנה בקובץ, ולכן אינה מוכנה למשלוח'
                        % (did, op, why), did))
    return F


def hidden_text(p):
    """הטקסט המוסתר בפסקה: ריצות עם w:vanish או w:webHidden ב-rPr שלהן (ולא בסימן הפסקה)."""
    out = ''
    for r in p.iter(W + 'r'):
        rpr = r.find(W + 'rPr')
        marks = [] if rpr is None else [rpr.find(W + 'vanish'), rpr.find(W + 'webHidden')]
        if any(m is not None and m.get(W + 'val') not in ('0', 'false', 'off') for m in marks):
            out += ''.join(t.text or '' for t in r.iter(W + 't', W + 'delText'))
    return out


def check_hidden_removals(rroot, decisions):
    """בדיקה עצמאית S1c (28.10.2026): מחיקה של טקסט מוסתר בטיוטה שלהם, עם הבועה הניטרלית (external_comments_guide.md,
    "טקסט מוסתר שהוסר"), מסומנת בהכרעה kind: hidden_text_removal, והיא שינוי מכוסה: בדיקת הכיסוי אינה דורשת שהבועה
    תקרא בשמם מושגים שבטקסט המוסתר (בהרצה, "AI" בטקסט המוסתר הכשיל את הבועה התקנית ב-COV_UNCOVERED_CHANGE).
    הסימון תקף רק על מחיקה (replace_span עם new ריק, או delete_paragraph) של טקסט שמוסתר בטיוטה שהתקבלה; אחרת
    COV_HIDDEN_KIND_INVALID (כשל). מחזיר ({פסקה: [הטקסט שהוסר]}, כשלים)."""
    items = decisions.get('decisions', []) if isinstance(decisions, dict) else (decisions or [])
    paras = dt.body_paragraphs(rroot)
    removed, F = {}, []
    for d in items:
        if d.get('kind') != 'hidden_text_removal':
            continue
        j, op = d.get('para'), d.get('op')
        if not isinstance(j, int) or not 0 <= j < len(paras) or not (
                (op == 'replace_span' and not (d.get('new') or '').strip()) or op == 'delete_paragraph'):
            F.append(_f('COV_HIDDEN_KIND_INVALID', '%s: kind: hidden_text_removal רק על מחיקה של טקסט מוסתר '
                        '(replace_span עם new ריק, או delete_paragraph)' % d.get('id'), d.get('id')))
            continue
        old = d.get('old') if op == 'replace_span' else dt.para_text(paras[j])
        if not _norm_ws(old) or _norm_ws(old) not in _norm_ws(hidden_text(paras[j])):
            F.append(_f('COV_HIDDEN_KIND_INVALID', '%s: הטווח "%s" אינו טקסט מוסתר בטיוטה שהתקבלה, ולכן הבועה צריכה '
                        'לתאר אותו כמו כל שינוי' % (d.get('id'), (old or '')[:50]), d.get('id')))
            continue
        removed.setdefault(j, []).append(old)
    return removed, F


def check_silent_changes(state, decisions, not_applied, mode):
    """H6 (בדיקה עצמאית S1c): כל שינוי שקט של הסבב (silent_changes בקובץ המצב, state_builder.apply_compare) מוכרע
    ומסומן בעותק למשלוח. SILENT_CHANGE_UNDECIDED: שינוי בלי הכרעה (state_builder.unresolved_silent_changes, אחרי
    קישור קובץ ההכרעות של הסבב ב-link_silent_decisions), או שההכרעה ש-decision_ref מצביע עליה אינה בקובץ ההכרעות,
    לא סומנה בקובץ בפועל (DEC_NOT_APPLIED), או מסומנת בפסקה אחרת מהשינוי. כשל במצב משלוח, אזהרה במצב עבודה.
    not_applied: מזהי ההכרעות שלא סומנו (None: אי אפשר לאמת אף הכרעה). מחזיר (כשלים, אזהרות)."""
    st = state or {}
    if not st.get('silent_changes'):
        return [], []
    rnd = _round_of(st, decisions)
    view = {'meta': {'round_number': rnd}, 'silent_changes': [dict(x) for x in st['silent_changes'] if isinstance(x, dict)]}
    items = {}
    if decisions is not None:
        SB.link_silent_decisions(view, decisions)
        items = {d.get('id'): d for d in (decisions.get('decisions', []) if isinstance(decisions, dict) else decisions)}
    out = []
    for x in SB.unresolved_silent_changes(view, rnd):
        out.append(_f('SILENT_CHANGE_UNDECIDED', 'שינוי שלא סומן בסעיף %s (%s) בלי הכרעה מסומנת: החזרה בעקוב אחר שינויים, '
                      'או קבלה עם בועה, בהכרעה שנושאת silent_change: %s. נדרשת הכרעתך (מצב 9)'
                      % (x.get('clause') or '?', x.get('id'), x.get('id')), x.get('id')))
    for x in view['silent_changes']:
        ref = x.get('decision_ref')
        if int(x.get('round') or 0) != (rnd or 0) or x.get('decision') not in SB.SILENT_DECISIONS or not ref:
            continue
        d = items.get(ref)
        why = None
        if decisions is None:
            why = 'קובץ ההכרעות לא נמסר לשער, ולכן לא נבדק שההכרעה %s סומנה' % ref
        elif d is None:
            why = 'ההכרעה %s אינה בקובץ ההכרעות של הסבב' % ref
        elif not_applied is None or ref in not_applied:
            why = 'ההכרעה %s לא סומנה בקובץ בפועל (DEC_NOT_APPLIED)' % ref
        elif isinstance(d.get('para'), int) and isinstance(x.get('received_para'), int) \
                and d['para'] != x['received_para']:
            why = 'ההכרעה %s מסומנת בפסקה %s, והשינוי השקט בפסקה %s' % (ref, d['para'], x['received_para'])
        if why:
            out.append(_f('SILENT_CHANGE_UNDECIDED', 'שינוי שלא סומן בסעיף %s (%s): %s' % (x.get('clause') or '?',
                                                                                          x.get('id'), why), x.get('id')))
    return (out, []) if mode == 'send' else ([], out)


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
def sent_prior_keys(state, deal_dir):
    """מפתחות הסימונים שלנו בקבצים שנשלחו (meta.sent_documents), בלי הסימונים שכבר היו בטיוטות שהתקבלו. כך סימון
    פתוח שלנו מסבב קודם מזוהה כשלנו גם כשנחתם בשם שאינו בפרופיל. אותו כלל כמו apply_redlines.prior_history."""
    meta = (state or {}).get('meta') or {}
    sent = [d for d in meta.get('sent_documents') or () if isinstance(d, dict)]
    if not (deal_dir and sent):
        return set()

    def where(rec):
        f = rec.get('file_name') or rec.get('path') or ''
        return f if os.path.isabs(f) else os.path.join(deal_dir, f)
    last = max(int(d.get('round') or 0) for d in sent)
    recv = [where(d) for d in meta.get('received_documents') or () if isinstance(d, dict)
            and int(d.get('round') or 0) <= last]
    return dt.sent_revision_keys([where(d) for d in sent], recv)


def run_gate(path, received, mode, profile, state=None, expected_accept=None, window=None, work_path=None,
             lang=None, register=None, context=None, decisions=None, core=None, deal_dir=None):
    """mode: work / send. lang: 'he' / 'en' (בלי: לפי הטיוטה שהתקבלה). register: נשאר לתאימות, ואינו
    בשימוש. decisions: קובץ ההכרעות של הסבב (dict). context: הקשר לבדיקת הפערים של common/gap_checks.py (our_terms, home_country). מחזיר dict עם passed, failures, warnings, info."""
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
    ours_names = [author] + [x for x in [profile.get('lawyer_name'), profile.get('lawyer_name_en')]
                             + list(profile.get('lawyer_aliases') or []) if x and x != author]
    # סבב 2 ואילך: הסימונים הפתוחים שלנו מסבבים קודמים הם חלק מהטיוטה שהתקבלה, ולא מהסבב הזה. בעץ שנבדק הם
    # מקבלים מחבר נפרד, כך שכל בדיקה של "השינויים שלנו" (הלוך ושוב, כיסוי, תאריכים, מיפוי הפסקאות) רואה רק את הסבב
    prior_keys = dt.prior_revisions(rroot, ours_names)
    # deal_dir: גם סימון שלנו שנחתם בסבב קודם בשם אחר, לפי הקבצים שנשלחו
    present = {dt.revision_key(e) for e in rroot.iter(W + 'ins', W + 'del')}
    prior_keys |= sent_prior_keys(state, deal_dir) & present
    prior_names = dt.set_aside_prior(root, prior_keys)
    received_authors = {e.get(W + 'author') for e in rroot.iter(W + 'ins', W + 'del')} | prior_names
    f, info = check_package(parts, root, profile, received_ids, window, work_path or path, author,
                            received_authors=received_authors)
    F += f
    # דחיית השינויים שלנו בלבד, ולא "דחה הכול": השינויים הפתוחים של הצד שכנגד נשארים כפי שהתקבלו
    rej = dt.reject_ours_view(root, author)
    # בפסקה שבה הוכרעו השינויים הפתוחים שלהם (דחייה וסימון שלנו), הבסיס הוא הנוסח שלפני השינויים שלהם,
    # ובקבלה הוא הנוסח שהתקבל. כל פסקה צריכה להתאים לאחד מהשניים
    # הסימונים הפתוחים שלנו מסבבים קודמים נשארים גם כאן: רק השינויים של הצד שכנגד נדחים
    orig_rej = [dt.received_reject_text(p, set(ours_names)) for p in dt.body_paragraphs(rroot)]
    if len(rej) == len(orig):
        rej_ok = all(a == b or a == c for a, b, c in zip(rej, orig, orig_rej))
    else:
        rej_ok = rej == orig
    if not rej_ok:
        F.append(_f('RT_REJECT', '"דחה הכול" אינו מחזיר את הטיוטה שהתקבלה'))
    acc = dt.paragraph_views(root, 'accept')
    if expected_accept is not None and acc != expected_accept:
        F.append(_f('RT_ACCEPT', '"קבל הכול" אינו נותן את נוסחי היעד'))
    # כפילות שההכרעה יצרה: הוספה שלנו מהסבב הזה שחוזרת על נוסח שכבר בפסקה (למשל ההוספה שלנו מסבב קודם, שחזרה כשהמחיקה
    # שלהם בתוכה נדחתה). נוסחי היעד נגזרים מאותה הכרעה, ולכן RT_ACCEPT אינו מגלה אותה (S1d-R2, 13(ii))
    for k, p in enumerate(dt.body_paragraphs(root)):
        dup = dt.duplicated_insertions(p, lambda e: e is not None and e.get(W + 'author') == author)
        if dup:
            F.append(_f('RT_DUPLICATE', 'נוסח כפול בפסקה אחרי "קבל הכול": "%s..." מופיע יותר מפעם אחת, ואחת ההופעות '
                        'בהוספה שלנו. ההוספה הישנה והחדשה עומדות זו לצד זו' % dup[0][:60], k))
    accept_text = '\n'.join(acc)
    comments = [c for c in dt.read_comments(parts) if c['id'] not in received_ids]
    ext = [c for c in comments if c['author'] == author]
    intc = [c for c in comments if c['author'] in INTERNAL_AUTHORS]
    # בועה של אשכול נפרשת על כמה פסקאות, ומכסה כל אחת מהן
    spans = dt.comment_paragraph_spans(root)
    # פסקה שמחקנו כולה בסוף אשכול: הבועה של האשכול נסגרת בפסקה האחרונה שנשארת (docx_tracked.span_clusters), ולכן
    # פסקאות מחוקות שצמודות לסוף הטווח שייכות לאותה בועה
    bparas = dt.body_paragraphs(root)
    ext_ids = {c['id'] for c in ext}
    for cid, (first, last) in list(spans.items()):
        if cid not in ext_ids or first is None:
            continue
        k = last
        while k + 1 < len(bparas) and _our_del_mark(bparas[k + 1], author):
            k += 1
        if k != last:
            spans[cid] = (first, k)
    ext_by_para = {}
    for c in ext:
        first, last = spans.get(c['id'], (None, None))
        for i in (range(first, last + 1) if first is not None else (None,)):
            ext_by_para.setdefault(i, []).append(c['text'])
    ctx = dict(context or {})
    ctx.setdefault('waived', sorted(waived_gap_codes(state)))
    F += check_bubbles(ext, accept_text, state, '\n'.join(rej), lang)
    # בדיקה עצמאית S1c (28.10.2026): עברית בהסכם באנגלית (H1), אורך וקול לפי שלב הסבב (M1), בועה מול נוסח (M3),
    # וכללי הסבבים על שדות קובץ המצב (H3, פער 9)
    F += check_language(root, ext, author, lang, '\n'.join(orig + orig_rej))
    f, w_ = check_bubble_style(ext, lang, round_stage(state, decisions))
    F += f
    Wn += w_
    Wn += check_bubble_text_match(root, ext, spans, lang)
    prev = [c['text'] for c in dt.read_comments(rparts) if c['author'] in ours_names]
    f, w_ = check_round_rules(state, decisions, rroot, root, ours_names + sorted(prior_names), spans,
                              {c['id'] for c in ext}, prev, mode)
    F += f
    Wn += w_
    # טקסט מוסתר שהוסר עם הבועה הניטרלית (kind: hidden_text_removal) הוא שינוי מכוסה
    removed, f = check_hidden_removals(rroot, decisions) if decisions is not None else ({}, [])
    F += f
    # המפתחות הם פסקאות בטיוטה שהתקבלה; בדיקת הכיסוי סופרת פסקאות בקובץ העבודה, שבו גם הפסקאות שהוספנו
    wpos = {id(p): k for k, p in enumerate(dt.body_paragraphs(root))}
    groups = _received_groups(root, author)
    to_work = {j: wpos[id(g)] for j, g in enumerate(groups)} if len(groups) == len(orig) else {}
    removed = {to_work.get(j, j): v for j, v in removed.items()}
    cov = check_coverage(root, ext_by_para, author, lang, removed)
    hidden_at = {to_work.get(j, j) for j, rp in enumerate(dt.body_paragraphs(rroot)) if hidden_text(rp).strip()}
    for x in cov:
        if x['code'] == 'COV_UNCOVERED_CHANGE' and x['where'] in hidden_at and x['where'] not in removed:
            x['message'] += ('. בפסקה יש טקסט מוסתר בטיוטה שהתקבלה: כשהמחיקה היא של הטקסט המוסתר, עם הבועה הניטרלית, '
                             'ההכרעה נושאת kind: hidden_text_removal')
    F += cov
    F += check_bubble_why(root, ext_by_para, author, accept_text, lang, ctx, removed)
    F += check_contradictions(ext, accept_text, lang)
    Wn += check_reasoning_warnings(ext)
    f, ph = check_placeholders(root, ext, author, state, mode)
    F += f
    f, w_ = check_identifiers(root, author, profile, lang, '\n'.join(orig))
    F += f
    Wn += w_
    F += check_self_created_gaps(root, author, accept_text, lang, ctx, state=state)
    f, w_ = check_state(state, mode)
    F += f
    Wn += w_
    # "טעון בדיקה משפטית": מקובץ המצב, מקובץ ההכרעות ומהפלייבוק (core), ובמצב משלוח קובץ מצב בלי סעיפים הוא כשל
    f, w_ = check_legal_review(state, decisions, core, mode)
    F += f
    Wn += w_
    f, w_ = check_entity_name_en(profile, lang, mode, accept_text + '\n' + '\n'.join(c['text'] for c in ext))
    F += f
    Wn += w_
    f, w_ = check_lawyer_name_en(profile, lang, mode)
    F += f
    Wn += w_
    f, w_ = check_internal_leak(parts, root, comments, mode, [c['id'] for c in ext])
    F += f
    Wn += w_
    F += check_structure(root, author)
    # באג 3: ההכרעות מול מה שסומן בפועל. בלי קובץ ההכרעות אי אפשר לדעת שלא נשמטה הכרעה, ולכן במצב משלוח זה כשל
    not_applied = set()
    if decisions is not None:
        f = check_decisions_applied(root, orig, decisions, author, {c['id'] for c in ext},
                                    received_paras=dt.body_paragraphs(rroot), prior=prior_keys,
                                    received_rej=orig_rej)
        F += f
        not_applied = None if any(x['where'] is None for x in f) else {x['where'] for x in f}
    elif mode == 'send':
        F.append(_f('DEC_FILE_MISSING', 'השער רץ בלי קובץ ההכרעות (--decisions), ולכן אינו יכול לוודא שכל הכרעה '
                    'סומנה בקובץ'))
    else:
        Wn.append(_f('DEC_FILE_MISSING', 'בלי קובץ ההכרעות לא נבדק שכל הכרעה סומנה בקובץ'))
    # H6: שינוי שקט של הסבב בלי הכרעה מסומנת (כשל במצב משלוח, אזהרה במצב עבודה)
    f, w_ = check_silent_changes(state, decisions, not_applied, mode)
    F += f
    Wn += w_
    headers =''.join(parts[n].decode('utf-8', 'ignore') for n in parts if n.startswith('word/header'))
    # הכותרת הפנימית נדרשת רק כשבקובץ העבודה יש שכבה פנימית (בועות פנימיות). מאז 18.10.2026 השכבה הפנימית
    # אינה מופקת כברירת מחדל (apply_redlines --internal-layer), ולכן הדרישה הגורפת הכשילה כל קובץ עבודה.
    # בועה פנימית של סעיף AREO לבדה אינה שכבה פנימית: היא נכתבת תמיד בקובץ העבודה, גם בלי --internal-layer
    has_internal = any(c['author'] in INTERNAL_AUTHORS and not c['text'].strip().startswith(dt.AREO_LABEL_PREFIXES)
                       for c in dt.read_comments(parts) if c['id'] not in received_ids)
    # הכותרת הפנימית נכתבת בשפת התוצר (docx_tracked.internal_identity): בעברית INTERNAL_HEADER_TEXT, באנגלית
    # INTERNAL_HEADER_TEXT_EN. הבדיקה מקבלת כל אחת מהן (בהסכם אנגלי השער במצב עבודה נכשל תמיד)
    header_texts = (dt.INTERNAL_HEADER_TEXT, getattr(dt, 'INTERNAL_HEADER_TEXT_EN', dt.INTERNAL_HEADER_TEXT))
    has_header = any(h in headers for h in header_texts)
    if mode == 'work' and has_internal and not has_header:
        F.append(_f('INT_HEADER_MISSING', 'חסרה הכותרת הפנימית בקובץ העבודה'))
    if mode == 'send':
        if has_header:
            F.append(_f('INT_IN_SEND', 'הכותרת הפנימית נשארה בעותק למשלוח'))
        if intc:
            F.append(_f('INT_IN_SEND', 'בועה פנימית בעותק למשלוח: %d' % len(intc)))
        # סעיף AREO: התווית והמירקור הצהוב הם לעורך הדין בלבד
        visible = ' '.join(dt.para_text(p) for p in dt.body_paragraphs(root)) + ' ' + \
            ' '.join(c['text'] for c in dt.read_comments(parts))
        if any(x in visible for x in dt.AREO_LABEL_PREFIXES):
            F.append(_f('AREO_IN_SEND', 'התווית של סעיף AREO נשארה בעותק למשלוח'))
        hl = [h for rev in root.iter(W + 'ins', W + 'del') if rev.get(W + 'author') == author
              for h in rev.iter(W + 'highlight') if h.get(W + 'val') == dt.AREO_HIGHLIGHT]
        if hl:
            F.append(_f('AREO_IN_SEND', 'מירקור צהוב בנוסח שלנו בעותק למשלוח: %d' % len(hl)))
    info.update(lang=lang, external_comments=len(ext), internal_comments=len(intc), placeholders=ph,
                signing_checklist=[dict(item='signing_blank', **x) for x in ph['signing_blanks']]
                + [dict(item='their_placeholder', **x) for x in ph['theirs']])
    return {'mode': mode, 'passed': not F, 'failures': F, 'warnings': Wn, 'info': info}


RUNS_DIR = 'runs'


def run_report_path(deal_dir, round_no, name):
    """השם הקנוני של דוח בתיקיית העסקה, כש---out או --report לא ניתנו (29.10.2026): <deal>/runs/round-<N>/<name>,
    למשל apply.json, gate-work.json ו-gate-send.json. בלי תיקיית עסקה או בלי מספר סבב: None (אין דוח, כמו קודם)."""
    try:
        n = int(round_no)
    except (TypeError, ValueError):
        return None
    if not deal_dir or n < 1:
        return None
    return os.path.join(deal_dir, RUNS_DIR, 'round-%d' % n, name)


def write_run_report(path, data):
    """כותב דוח בשם הקנוני. הרצה חוזרת מחליפה את הקובץ, והדוח הקודם עובר ל-history/<שם>.<חותמת>.json באותה תיקייה,
    במקום gate-work-2, gate-work-3 וכן הלאה ליד קובץ המצב."""
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)
    if os.path.exists(path):
        hist = os.path.join(d, 'history')
        os.makedirs(hist, exist_ok=True)
        stem, ext = os.path.splitext(os.path.basename(path))
        stamp = _dt.datetime.fromtimestamp(os.path.getmtime(path)).strftime('%Y%m%dT%H%M%S')
        target = os.path.join(hist, '%s.%s%s' % (stem, stamp, ext))
        k = 2
        while os.path.exists(target):
            target = os.path.join(hist, '%s.%s-%d%s' % (stem, stamp, k, ext))
            k += 1
        os.replace(path, target)
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2, default=str)
    return path


def build_send_copy(work_path, received, send_path, profile, state=None, expected_accept=None, window=None,
                    lang=None, deal_dir=None, register=None, context=None, decisions=None, core=None):
    """גוזר עותק זמני בלי השכבה הפנימית, מריץ עליו את השער במצב משלוח, ומשנה את שמו רק כשעבר.
    כשנכשל: הקובץ הזמני נמחק, ואין בתיקייה קובץ "למשלוח". עותק "למשלוח" ישן שכבר נמצא בנתיב מקבל את הסיומת
    " - לא למשלוח" (pre_send.retract_send_copy). deal_dir: תיקיית העסקה. register: נשאר לתאימות, ואינו בשימוש."""
    if decisions is None and deal_dir and (state or {}).get('decisions_file'):
        dp = os.path.join(deal_dir, state['decisions_file'])
        if os.path.exists(dp):
            with open(dp, encoding='utf-8') as fh:
                decisions = json.load(fh)
    tmp = send_path[:-5] + '.tmp.docx' if send_path.endswith('.docx') else send_path + '.tmp'
    paths.check_write_path(tmp)
    dt.strip_internal(work_path, tmp)
    res = run_gate(tmp, received, 'send', profile, state, expected_accept, window, work_path=send_path, lang=lang,
                   register=register, context=context, decisions=decisions, core=core, deal_dir=deal_dir)
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
