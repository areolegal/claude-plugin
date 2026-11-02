# -*- coding: utf-8 -*-
"""playbook/approval_sheet.py: גיליון "עמדות משא ומתן לאישור" שהיועץ המשפטי חותם עליו לפי עמודה.

הבעיה: היועצת חתמה על תקציר עמדה, ולא על הנוסח שנכנס להסכם; לא ראתה מה כל עמדה מטילה
על החברה כמקבלת; לא ראתה "הצעת Areo", "טעון בדיקה משפטית" ו"לא אומת"; החשיבות והבסיס הוצגו
באנגלית; והגיליון נקרא "מאושרות" עוד לפני החתימה.

הבעיה:
- ב-6 מתוך 10 התאים שנשענים על שלושה מקורות שוק הודפס גם "3 מקורות שוק" וגם "לא אומת: 1 מקורות":
  ממצא לא מאומת של נקודה אחרת באותו כלל הודבק לכל שלושת המסלולים.
- היועצת חתמה על נוסח ירוק שנכשל בבדיקות הפערים שהנושא ונותן מריץ.
- עמודת האדום נקראה "לא נחתום" בכל השורות, אף שרק כלל אחד שובר עסקה; והנוסח באדום הוצג
  כ"הנוסח שיוחל".
- "טעון בדיקה משפטית" הודבק לשורת "נבדק בידי", ו"נבדק בידי" נרשם בלי תאריך.
- טבלת "סמכויות והסלמה" יוצאת מהגיליון: אין שרשרת אישורים.
  החתימה של היועץ המשפטי על הפלייבוק המוצע נשארת.
- נוסח אנגלי הודפס בתוך ריצה RTL אחת עם הקידומת העברית: כל שורה מפוצלת לפי כתב, והקטע הלטיני
  נשאר LTR (w:rtl w:val="0").

מה הגיליון מציג בכל תא (ירוק, צהוב, אדום), בסדר קבוע:
1. העמדה (משפט אחד, מודגש).
2. בירוק ובצהוב: "הנוסח שיוחל, מילה במילה:" ואחריו הנוסח שהנושא ונותן מכניס להסכם (ירוק:
   proposed_clause; צהוב: fallback_wording.text, ואם אין, proposed_clause). באדום: "הנוסח שנשיב כשהצד
   השני מציע זאת (נוסח ריפוי), מילה במילה:". טביעת האצבע (fp) מחושבת על העמדה, הנוסח ושורות ההשפעה.
3. מה העמדה מטילה על החברה בכל תפקיד שיש לה בהסכם, בכל סוג הסכם: "כשהחברה <התפקיד>:" לכל תפקיד
   (scope_summary.company_roles[], כפי שהמסמכים קוראים להם), או שורה אחת, "מה זה מטיל על
   החברה:", כשיש לה תפקיד אחד.
4. "סימונים:" סימון ראיה אחד: "<N> מקורות שוק (W..)" רק כשיש שלושה מקורות לנקודה של המסלול;
   "הצעת Areo"; "חובה בדין (L..)"; "מבוסס הסכמי החברה (N)". ממצא לא מאומת מודפס רק בתא שהנקודה
   שלו היא הנקודה של הממצא (track, או level מול range_point), בתבנית "ממצא לא מאומת, <N> מקורות
   (<מזהים>): <הסיבה>", בהתאמה דקדוקית. ממצא שאינו שייך לאף מסלול מודפס פעם אחת, בתא הנושא.
5. כשהמסלול טעון בדיקה משפטית: "טעון בדיקה משפטית. נבדק בידי: " ו"תאריך הבדיקה: ", שתי שורות.
6. הנחות (assumptions[]), כל אחת עם תיבת סימון.

בתא הנושא: קוד, נושא, חשיבות בעברית, "שובר עסקה: לא נחתום" כש-walk_away, ולכל שאלה מכריעה פתוחה
של הכלל: ההמלצה, הערת Areo ותיבות בחירה. התגית של כל תיבה כוללת את מזהה השאלה, והמניפסט שומר את נוסח
כל אפשרות, כדי שהקליטה תרשום את הבחירה עצמה.

לפני ההפקה: בדיקות הפערים (common.gap_checks, דרך validate_model.wording_findings) על כל נוסח ירוק,
צהוב ונסיגה. ממצא אחד עוצר את ההפקה (SheetError).

שם הקובץ "עמדות-לאישור-...". רק העותק שנקלט בהצלחה נקרא "מאושרות" (ingest_approval).

שתי שפות (lang, מ-deliverable_language): עברית (HE, RTL מלא) או אנגלית (EN, LTR מלא, בלי bidi ובלי rtl בשום
פסקה, ריצה, טבלה או מקטע). כל כותרת, עמודה, קידומת, סימון, הנחה, חתימה ומזהה הפקה נלקחים מהמילון של השפה,
והמבנה זהה בשתיהן: אותן עמודות, אותן שורות, אותן תגיות תיבה, ולכן אותה קליטה. הנוסח (proposed_clause,
fallback_wording) ושורות ההשפעה הם נתונים, ומודפסים בשפת המקור שלהם. ingest_approval קורא את הקידומות לפי
manifest.lang.

הבעיה:
- פסקת האימוץ אמרה "29 עמדות נגזרו מהסכמי החברה" גם כשהמאגר היה נוסחים של צד שלישי. הנוסח נגזר עכשיו
  מ-status.corpus_status, כמו התווית ושורת הבסיס.
- היועצת התבקשה לחתום על נוסח עם "[מכפיל]" ו-"[number] hours": מספרים עסקיים שאינם החלטה משפטית. דף שער,
  "החלטות הנהלה" (management_decisions), מרכז עד 8 החלטות במספרים, לכל אחת בעל החלטה מוצע, ושאר הגיליון נשאר
  לחתימת היועץ המשפטי. סוגריים של ערך שלא נקבע (decision_slots) שנשארו בתא חוסמים את אישורו בקליטה.

הגיליון הוא אחת משתי דרכים לאשר. הדרך השנייה, תור האישור בצ'אט, נמצאת
ב-ingest_approval ("אישור בצ'אט במנות"), וקוראת את התא דרך cell_view כאן: אותה עמדה, אותו נוסח, אותן שורות
השפעה ואותה טביעת אצבע.
"""
import hashlib
import os
import re
import unicodedata
import uuid

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_BREAK
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Cm, Pt

try:
    from common import rtl
    from playbook import status as S
except ImportError:  # pragma: no cover  הרצה מתוך playbook\
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from common import rtl
    from playbook import status as S

TRACKS = ('green', 'yellow', 'red')
AREO_AUTHOR = 'Areo'
W14 = 'http://schemas.microsoft.com/office/word/2010/wordml'
MIN_MARKET_SOURCES = 3
POINT_NAMES = ('ours', 'middle', 'theirs')

HE = {
    'title': 'עמדות משא ומתן לאישור',
    'file': 'עמדות-לאישור',
    'cols': ['נושא', 'נדרוש (ירוק)', 'נסכים (צהוב)', 'אדום: לא מקבלים כמות שהוא, ומשיבים בנוסח ריפוי'],
    'importance': {'critical': 'קריטית', 'high': 'גבוהה', 'medium': 'בינונית', 'low': 'נמוכה'},
    'wording': 'הנוסח שיוחל, מילה במילה: ',
    'cure': 'הנוסח שנשיב כשהצד השני מציע זאת (נוסח ריפוי), מילה במילה: ',
    'no_wording': 'אין נוסח להחלה: העמדה מוחלת כתנאי בלבד.',
    'flags': 'סימונים: ',
    'areo': 'הצעת Areo',
    'legal': 'טעון בדיקה משפטית',
    'legal_line': 'טעון בדיקה משפטית. נבדק בידי: ',
    'legal_date': 'תאריך הבדיקה: ',
    'unverified': 'ממצא לא מאומת, {count}{ids}: {reason}',
    'topic_unverified': 'ממצא לא מאומת בנושא, שאינו נקודה של אף מסלול: ',
    'market': 'הצעת Areo מ-{n} מקורות שוק ({ids})',
    'statute': 'חובה בדין ({ids})',
    'company': 'מבוסס הסכמי החברה ({n})',
    # כשהמאגר אינו הסכמים חתומים (corpus_status, workflow.md שלב 2ח), כמו בתווית ובשורת הבסיס
    'company_drafts': 'מבוסס מסמכי החברה, רובם טיוטות ({n})',
    'company_forms': 'מבוסס נוסחים שהחברה מציגה ({n})',
    'company_other': 'מבוסס מסמכים שאינם הסכמים חתומים ({n})',
    'walk_away': 'שובר עסקה: לא נחתום',
    'assume': 'הנחה שיש לאשר (סמנו אם נכונה): ',
    'choice_head': 'בחירה נדרשת: ',
    'recommendation': 'המלצת Areo: ',
    'comment_tail': 'בחרו אפשרות אחת בתא הנושא. אחר כך פתרו או מחקו הערה זו. בלי בחירה, השורה לא תיקלט.',
    'sign_head': 'חתימה לפי עמודה',
    'sign_cols': ['עמודה', 'מאשר', 'שם מלא', 'תפקיד', 'תאריך'],
    'track_label': {'red': 'אדום: מה לא מקבלים כמות שהוא', 'yellow': 'נסכים (צהוב)', 'green': 'נדרוש (ירוק)'},
    'final': 'זו הגרסה הסופית לחתימה.',
    'token': 'מזהה הפקה (אין לשנות): {token}',
    'importance_label': 'חשיבות: ',
    'single_role': 'מה זה מטיל על החברה: ',
    'role_line': 'כשהחברה {label}: ',
    'no_reason': 'הסיבה לא נרשמה',
    'few_sources': 'פחות משלושה מקורות לנקודה',
    'count': ('מקורות', 'מקור אחד', 'לא נמצאו מקורות'),
    'rules_count': ('כללים', 'כלל אחד', 'אין'),
    'open_market': '%d עמדות נגזרו ממקורות שוק ציבוריים, שלושה מקורות לפחות לכל עמדה',
    'open_unverified': '%d עמדות נשענות על פחות משלושה מקורות שוק, ומסומנות "ממצא לא מאומת"',
    'open_areo': '%d עמדות נוסחו בידי Areo בלי נקודת שוק',
    'open_company': '%d עמדות נגזרו מהסכמי החברה',
    # לפי מעמד המאגר (status.corpus_status), כמו company_drafts/forms/other בסימון התא
    'open_company_drafts': '%d עמדות נגזרו ממסמכי החברה, שרובם טיוטות',
    'open_company_forms': '%d עמדות נגזרו מנוסחים שהחברה מציגה לצד שכנגד',
    'open_company_other': '%d עמדות נגזרו מנוסחים שאינם הסכמים חתומים של החברה',
    'open_statute': '%d עמדות הן חובה בדין',
    'open_walks': ('שוברי עסקה: %s (%s); בשאר %d הכללים האדום הוא מה שלא מקבלים כמות שהוא, ומשיבים '
                   'עליו בנוסח הריפוי'),
    'open_no_walks': 'אין שובר עסקה; בכל הכללים האדום הוא מה שלא מקבלים כמות שהוא, ומשיבים עליו בנוסח הריפוי',
    'open_head': 'אני מאמץ/ת את העמדות שבמסמך כמדיניות החברה. ',
    # דף השער: החלטות הנהלה במספרים
    'mgmt_title': 'החלטות הנהלה',
    'mgmt_intro': ('אלה החלטות עסקיות במספרים, ולא נוסח משפטי. לכל החלטה מוצע בעל החלטה. כתבו את הערך שנקבע, '
                   'והעבירו אותו לנוסח בגיליון במקום הסוגריים. תא שנשארו בו סוגריים של ערך שלא נקבע אינו נקלט '
                   'כמאושר. שאר הגיליון הוא לחתימת היועץ המשפטי.'),
    'mgmt_cols': ['#', 'ההחלטה', 'מה הפלייבוק מציע', 'הערך שנקבע', 'בעל החלטה מוצע', 'שם, תפקיד ותאריך'],
    # השאלה מציגה את המשפט המלא שבו הסוגריים ואת היחידה, כדי ש-72 שנכתב בכוונה לשעות לא ייכנס כ-72 ימים
    'mgmt_set': '{topic}: {slots}',
    'mgmt_in_sentence': 'מה הערך במקום {slot} במשפט "{sentence}"? {tail}',
    'mgmt_slot_only': 'מה הערך במקום {slot}? {tail}',
    'mgmt_unit': 'היחידה: {unit}. כתבו מספר בלבד.',
    'mgmt_no_unit': 'כתבו את הערך עם היחידה, למשל "72 שעות" או "30 ימים".',
    'mgmt_confirm': '{topic}: לאשר את המספרים בעמדה',
    'mgmt_confirm_in': '{topic}: האם {num} במשפט "{sentence}" מקובל? {tail}',
    'mgmt_confirm_tail': 'היחידה: {unit}. אשרו, או כתבו מספר אחר.',
    'clause_ref': 'סעיף {num} במדיניות',
    'mgmt_green': 'מקובל עלינו: ',
    'mgmt_yellow': 'אפשר להתגמש: ',
    'owners': {'finance': 'כספים', 'infosec': 'אבטחת מידע', 'technology': 'טכנולוגיה', 'management': 'הנהלה'},
    'owner_unverified': ' (כדאי לוודא)',
    'legal_head': 'עמדות לחתימת היועץ המשפטי',
}

# אותו גיליון באנגלית: אותם מפתחות, אותו מבנה (localization-he.md, "המונחים בתוצר באנגלית")
EN = {
    'title': 'Negotiation positions for approval',
    'file': 'Positions-for-approval',
    'cols': ['Topic', 'We require (green)', 'We accept (yellow)',
             'Red: not accepted as is, answered with cure wording'],
    'importance': {'critical': 'Critical', 'high': 'High', 'medium': 'Medium', 'low': 'Low'},
    'wording': 'Wording to apply, verbatim: ',
    'cure': 'Wording we answer with when the other side proposes this (cure wording), verbatim: ',
    'no_wording': 'No wording to apply: the position applies as a condition only.',
    'flags': 'Flags: ',
    'areo': 'Areo proposal',
    'legal': 'Needs legal review',
    'legal_line': 'Needs legal review. Reviewed by: ',
    'legal_date': 'Review date: ',
    'unverified': 'Unverified finding, {count}{ids}: {reason}',
    'topic_unverified': 'Unverified finding on the topic, not the point of any track: ',
    'market': 'Areo proposal from {n} market sources ({ids})',
    'statute': 'Required by law ({ids})',
    'company': "Based on the company's agreements ({n})",
    'company_drafts': "Based on the company's documents, most of them drafts ({n})",
    'company_forms': 'Based on forms the company presents ({n})',
    'company_other': "Based on documents that are not signed agreements ({n})",
    'walk_away': 'Deal breaker: we will not sign',
    'assume': 'Assumption to confirm (tick if correct): ',
    'choice_head': 'Choice required: ',
    'recommendation': 'Areo recommendation: ',
    'comment_tail': ('Choose one option in the topic cell. Then resolve or delete this comment. Without a choice, '
                     'the row will not be ingested.'),
    'sign_head': 'Signature by column',
    'sign_cols': ['Column', 'Approve', 'Full name', 'Role', 'Date'],
    'track_label': {'red': 'Red: what is not accepted as is', 'yellow': 'We accept (yellow)',
                    'green': 'We require (green)'},
    'final': 'This is the final version for signature.',
    'token': 'Issue ID (do not change): {token}',
    'importance_label': 'Importance: ',
    'single_role': 'What this imposes on the company: ',
    'role_line': 'When the company is the {label}: ',
    'no_reason': 'reason not recorded',
    'few_sources': 'fewer than three sources for the point',
    'count': ('sources', 'one source', 'no sources found'),
    'rules_count': ('rules', 'one rule', 'none'),
    'open_market': '%d positions were derived from public market sources, at least three sources per position',
    'open_unverified': '%d positions rest on fewer than three market sources, and are marked "Unverified finding"',
    'open_areo': '%d positions were drafted by Areo without a market point',
    'open_company': "%d positions were derived from the company's agreements",
    'open_company_drafts': "%d positions were derived from the company's documents, most of them drafts",
    'open_company_forms': '%d positions were derived from forms the company presents to its counterparties',
    'open_company_other': '%d positions were derived from forms that are not signed agreements of the company',
    'open_statute': '%d positions are required by law',
    'open_walks': ('Deal breakers: %s (%s); in the other %d rules, red is what is not accepted as is, and is '
                   'answered with the cure wording'),
    'open_no_walks': 'No deal breaker; in all rules, red is what is not accepted as is, and is answered with the '
                     'cure wording',
    'open_head': 'I adopt the positions in this document as company policy. ',
    'mgmt_title': 'Management decisions',
    'mgmt_intro': ('These are business decisions in numbers, not legal wording. Each decision has a proposed decision '
                   'owner. Write the value decided, and carry it into the wording in the sheet in place of the '
                   'brackets. A cell that still has brackets for a value not decided is not ingested as approved. The '
                   'rest of the sheet is for the legal counsel to sign.'),
    'mgmt_cols': ['#', 'Decision', 'What the playbook proposes', 'Value decided', 'Proposed decision owner',
                  'Name, role and date'],
    'mgmt_set': '{topic}: {slots}',
    'mgmt_in_sentence': 'What value goes in place of {slot} in the sentence "{sentence}"? {tail}',
    'mgmt_slot_only': 'What value goes in place of {slot}? {tail}',
    'mgmt_unit': 'Unit: {unit}. Write the number only.',
    'mgmt_no_unit': 'Write the value with its unit, for example "72 hours" or "30 days".',
    'mgmt_confirm': '{topic}: confirm the numbers in the position',
    'mgmt_confirm_in': '{topic}: is {num} in the sentence "{sentence}" acceptable? {tail}',
    'mgmt_confirm_tail': 'Unit: {unit}. Confirm, or write another number.',
    'clause_ref': 'Clause {num} of the policy',
    'mgmt_green': 'We accept: ',
    'mgmt_yellow': 'We can flex to: ',
    'owners': {'finance': 'Finance', 'infosec': 'Information security', 'technology': 'Technology',
               'management': 'Management'},
    'owner_unverified': ' (to confirm)',
    'legal_head': 'Positions for the legal counsel to sign',
}
SHEETS = {'he': HE, 'en': EN}

SINGLE_ROLE_LABEL = HE['single_role']
ROLE_LINE = HE['role_line']


def sheet_lang(lang):
    """he או en. כל ערך אחר: he."""
    return 'en' if str(lang or '').strip().lower().startswith('en') else 'he'
_EFFECT_FIELD = re.compile(r'^as_(\w+)_effect$')


def company_roles(model):
    """[(role, label)]: התפקידים שיש לחברה בהסכם. כללי לכל סוג הסכם.

    מקור ראשון: scope_summary.company_roles[] = [{role, label}] (למשל מגלה ומקבל, קונה ומוכר, מעניק רישיון
    כפי שהמסמכים קוראים להם). בלי הרשימה, כשהחברה בכמה תפקידים (company_role_code: mutual), התפקידים
    נגזרים משדות as_<role>_effect שבמסלולים; תפקיד אחד: שורה אחת, "מה זה מטיל על החברה"."""
    ss = model.get('scope_summary') or {}
    roles = ss.get('company_roles') or []
    if roles:
        return [(r['role'], r.get('label') or r['role']) for r in roles]
    if role_code(model) == 'mutual':
        found = []
        for rule in model.get('rules') or []:
            for t in (rule.get('traffic_light') or {}).values():
                for k in list((t or {}).get('role_effects') or {}) + [m.group(1) for m in map(
                        _EFFECT_FIELD.match, (t or {}).keys()) if m]:
                    if k not in found:
                        found.append(k)
        labels = ss.get('role_labels') or {}
        return [(r, labels.get(r) or r) for r in found] or [('company', None)]
    return [('company', None)]


def role_effect(t, role, single=False):
    """שורת ההשפעה של תפקיד אחד: role_effects[role], או השדה as_<role>_effect; בתפקיד יחיד גם company_effect.

    single: לחברה תפקיד אחד בהסכם (למשל תפקיד אחד שמוגדר במסמך). לפי playbook-schema.md זו שורה אחת, company_effect,
    ולכן כשאין role_effects לתפקיד הזה נקרא company_effect."""
    v = (t.get('role_effects') or {}).get(role) or t.get('as_%s_effect' % role)
    if not v and (role == 'company' or single):
        v = t.get('company_effect') or next((t[k] for k in sorted(t) if _EFFECT_FIELD.match(k) and t[k]), '')
    return (v or '').strip()


def role_lines(model, lang='he'):
    """[(role, הקידומת בגיליון)], בשפת הגיליון."""
    T = SHEETS[sheet_lang(lang)]
    roles = company_roles(model)
    if len(roles) == 1:
        return [(roles[0][0], T['single_role'])]
    return [(r, T['role_line'].format(label=lbl)) for r, lbl in roles]


_LATIN = re.compile(r'[A-Za-z][A-Za-z0-9/&.\-"\'(),;:]*(?:[ ][A-Za-z0-9/&.\-"\'(),;:]+)*')


class SheetError(ValueError):
    """הגיליון אינו מופק: חסר נוסח, חסרה שורת השפעה, תווית באנגלית, או נוסח שנכשל בבדיקות הפערים."""


def norm_text(s):
    s = unicodedata.normalize('NFKC', s or '')
    s = re.sub('[‎‏‪-‮⁦-⁩]', '', s)
    return re.sub(r'\s+', ' ', s).strip()


def fingerprint(parts):
    return hashlib.sha256('\n'.join(norm_text(p) for p in parts).encode('utf-8')).hexdigest()


def cell_key(rule_id, track, segment=None):
    return '%s|%s|%s' % (rule_id, segment or '-', track)


def role_code(model):
    fams = (model.get('scope_summary') or {}).get('contract_families') or [{}]
    return fams[0].get('company_role_code') or model.get('company_role_code') or 'mutual'


def track_wording(track, t, lang='he'):
    if track == 'yellow':
        fw = t.get('fallback_wording')
        if isinstance(fw, dict) and fw.get('text'):
            return fw['text']
        if isinstance(fw, str) and fw.strip():
            return fw
    pc = t.get('proposed_clause')
    if isinstance(pc, dict):
        return pc.get(lang) or pc.get(pc.get('source_language') or '') or pc.get('en') or pc.get('he') or ''
    return pc or t.get('preferred_wording') or ''


def clause_text(pc, lang='he'):
    """הנוסח של proposed_clause בשפה lang, ובלעדיו בשפה האחרת: (text, lang_used). זה הכלל האחד שלפיו סביבת
    העבודה והאשף מציגים נוסח, ושלפיו קליטת ההערות (apply_decisions.py) מחשבת את טביעת האצבע שלו, כדי שאישור
    באשף ייבדק מול אותו טקסט בשני הצדדים, בכל שפה. lang: שפת הדף (deliverable_language)."""
    lang = 'en' if str(lang or '').strip().lower().startswith('en') else 'he'
    if isinstance(pc, dict):
        for g in (lang, 'he' if lang == 'en' else 'en'):
            if str(pc.get(g) or '').strip():
                return pc[g], g
        return '', lang
    return (pc if isinstance(pc, str) else ''), lang


def wiz_hash(text):
    """טביעת האצבע של נוסח באשף, זהה ל-hash() שבתבנית האשף: h=(h*31+c)|0 על יחידות UTF-16 של הטקסט, ו-"h" ואחריו
    הערך הלא מסומן בהקסדצימלי. אותה פונקציה בבנייה (build_dashboard.py) ובקליטה (apply_decisions.py)."""
    h = 0
    data = str(text or '').encode('utf-16-le')
    for i in range(0, len(data), 2):
        h = (h * 31 + (data[i] | (data[i + 1] << 8))) & 0xFFFFFFFF
    return 'h%x' % h


def legal_review_tracks(rule):
    lr = rule.get('legal_review_required')
    if lr is True:
        return set(TRACKS)
    if isinstance(lr, list):
        # track הוא השם שבסכמה; tracks (רשימה) נקרא לתאימות, כמו בגרעין (build_playbook_core.py)
        return ({x.get('track') for x in lr if isinstance(x, dict) and x.get('track')} |
                {t for x in lr if isinstance(x, dict) for t in x.get('tracks') or ()} |
                {x for x in lr if isinstance(x, str)})
    return set(rule.get('legal_review_tracks') or [])


# ------------------------------------------------------------------ סימונים
def count_he(n, noun='מקורות', one='מקור אחד', none='לא נמצאו מקורות'):
    """התאמה דקדוקית: "מקור אחד", "2 מקורות", "לא נמצאו מקורות". לעולם לא "1 מקורות". באנגלית אותה פונקציה
    עם המילים של EN['count']: "one source", "2 sources", "no sources found"."""
    n = int(n or 0)
    if n == 0:
        return none
    if n == 1:
        return one
    return '%d %s' % (n, noun)


def unverified_label(n, ids, reason, lang='he'):
    """התבנית האחת לממצא שוק שלא אומת (localization-he.md, החלפה 77.5)."""
    T = SHEETS[sheet_lang(lang)]
    ids = [i for i in (ids or []) if i]
    reason = (reason or T['no_reason']).strip()
    if T is HE:
        reason = re.sub(r'(?<!\d)1 מקורות', 'מקור אחד', reason)
    return T['unverified'].format(count=count_he(n, *T['count']), ids=(' (%s)' % ', '.join(ids)) if ids else '',
                                  reason=reason)


def market_ids(t):
    return list(t.get('market_source_ids') or t.get('source_ids') or [
        r for e in t.get('evidence') or [] for r in [e.get('source_id')] if r])


def _point_levels(model):
    """{rule_id: {'ours': level, 'middle': level, 'theirs': level}} מ-market_research.ranges[]."""
    out = {}
    for rg in (model.get('market_research') or {}).get('ranges') or []:
        rid = rg.get('topic') or rg.get('rule_id')
        lv = {}
        for p in POINT_NAMES:
            v = rg.get(p)
            if isinstance(v, dict) and 'level' in v:
                lv[p] = v['level']
        if rid:
            out[rid] = lv
    return out


def unverified_index(model):
    """ממפה כל ממצא לא מאומת לתאים שהוא שייך להם בפועל.

    מחזיר (by_cell, by_rule): by_cell[(rule_id, track)] = [finding]; by_rule[rule_id] = [finding] לממצאים
    שאינם הנקודה של אף מסלול. ממצא שייך למסלול רק כש-track שלו הוא המסלול, או כש-level שלו שווה ל-level
    של הנקודה שממנה המסלול נגזר (range_point). ממצא ברמת הכלל לעולם אינו מודבק לכל המסלולים."""
    levels = _point_levels(model)
    rules = {r['rule_id']: r for r in model.get('rules') or []}
    by_cell, by_rule = {}, {}
    for u in (model.get('market_research') or {}).get('unverified_findings') or []:
        rid = u.get('rule_id') or u.get('topic_id')
        if not rid:
            continue
        if u.get('track'):
            by_cell.setdefault((rid, u['track']), []).append(u)
            continue
        placed = False
        rule = rules.get(rid) or {}
        for track in TRACKS:
            t = (rule.get('traffic_light') or {}).get(track) or {}
            rp = t.get('range_point')
            if rp and 'level' in u and levels.get(rid, {}).get(rp) == u['level']:
                by_cell.setdefault((rid, track), []).append(u)
                placed = True
        if not placed:
            by_rule.setdefault(rid, []).append(u)
    return by_cell, by_rule


def _finding_label(u, lang='he'):
    ids = u.get('source_ids') or []
    n = u.get('sources_found', len(ids))
    if isinstance(n, (list, tuple)):
        ids, n = ids or list(n), len(n)
    if u.get('label') and not n and not ids and ('לא נבדק' in u['label'] or 'not checked' in u['label'].lower()):
        return u.get('reason') or u['label']
    return unverified_label(n, ids, u.get('reason'), lang)


def evidence_flag(track, t, lang='he', corpus_status='signed'):
    """סימון הראיה האחד של התא, מה-basis ומספר המקורות. None כשאין. corpus_status: מעמד המאגר
    (status.corpus_status), שקובע איך נקראים מסמכי החברה בסימון."""
    T = SHEETS[sheet_lang(lang)]
    basis = t.get('basis')
    if basis == 'areo_proposal':
        return T['areo']
    if basis == 'market_standard':
        ids = market_ids(t)
        if len(ids) >= MIN_MARKET_SOURCES:
            return T['market'].format(n=len(ids), ids=', '.join(ids))
        return unverified_label(len(ids), ids, t.get('verification_reason') or T['few_sources'], lang)
    if basis == 'statute':
        return T['statute'].format(ids=', '.join(t.get('legal_source_ids') or t.get('source_ids') or []))
    if basis:
        key = 'company' + S.CORPUS_SUFFIX.get(corpus_status, '')
        return T[key].format(n=len(t.get('evidence') or []))
    return None


def flags_for(rule, track, t, index=None, lang='he', corpus_status='signed'):
    """סימונים בעברית לתא. index: התוצאה של unverified_index(model), או None.

    סימון ראיה אחד (evidence_flag). "ממצא לא מאומת" מתווסף רק כשהממצא שייך לנקודה של המסלול הזה, ולעולם
    לא לתא שיש לו שלושה מקורות שוק לאותה נקודה. "טעון בדיקה משפטית" אינו כאן: הוא שורה נפרדת בתא."""
    out = []
    ev = evidence_flag(track, t, lang, corpus_status)
    if ev:
        out.append(ev)
    verified_market = t.get('basis') == 'market_standard' and len(market_ids(t)) >= MIN_MARKET_SOURCES
    by_cell = (index or ({}, {}))[0]
    if not verified_market:
        for u in by_cell.get((rule['rule_id'], track)) or []:
            out.append(_finding_label(u, lang))
        if t.get('verification') == 'not_verified':
            out.append(unverified_label(t.get('sources_found', 0), t.get('source_ids') or [],
                                        t.get('verification_reason'), lang))
    seen, uniq = set(), []
    for f in out:
        if f not in seen:
            seen.add(f)
            uniq.append(f)
    return uniq


# ------------------------------------------------------------------ כתיבה ל-Word
def _checkbox(paragraph, tag, lang='he'):
    xml = ('<w:sdt %s xmlns:w14="%s"><w:sdtPr><w:tag w:val="%s"/><w14:checkbox><w14:checked w14:val="0"/>'
           '<w14:checkedState w14:val="2612" w14:font="MS Gothic"/><w14:uncheckedState w14:val="2610" '
           'w14:font="MS Gothic"/></w14:checkbox></w:sdtPr><w:sdtContent><w:r><w:rPr>%s</w:rPr>'
           '<w:t>☐</w:t></w:r></w:sdtContent></w:sdt>') % (nsdecls('w'), W14, tag,
                                                         '' if lang == 'en' else '<w:rtl/>')
    paragraph._p.append(parse_xml(xml))


def script_runs(text):
    """(קטע, לטיני?) לפי כתב. ספרות וסימנים בין שני קטעים עבריים נשארים עם העברית."""
    out, pos = [], 0
    for m in _LATIN.finditer(text):
        if m.start() > pos:
            out.append((text[pos:m.start()], False))
        out.append((m.group(), True))
        pos = m.end()
    if pos < len(text):
        out.append((text[pos:], False))
    return [x for x in out if x[0]]


def add_mixed_runs(paragraph, text, bold=False, size=9, lang='he'):
    """כותב טקסט מעורב: ריצה עברית עם rtl, וקטע לטיני בריצה נפרדת עם rtl=0. הטקסט עצמו אינו משתנה.
    בגיליון באנגלית: ריצה אחת LTR, בלי rtl ובלי bidi (קטע עברי מהנתונים מוצג בכיוונו לפי Unicode)."""
    if lang == 'en':
        r = paragraph.add_run(text)
        r.bold = bold
        r.font.size = Pt(size)
        return paragraph
    for chunk, latin in script_runs(text):
        r = paragraph.add_run(chunk)
        r.bold = bold
        if latin:
            r.font.size = Pt(size)
            rtl.set_run_ltr(r)
        else:
            rtl.set_run_rtl(r, size=size)
    rtl.set_paragraph_rtl(paragraph)
    return paragraph


def _cell_lines(cell, lines, lang='he'):
    """lines: [(text, bold)] לתא. הפסקה הראשונה של התא משמשת לשורה הראשונה."""
    first = not cell.paragraphs[0].runs
    paras = []
    for text, bold in lines:
        p = cell.paragraphs[0] if first else cell.add_paragraph()
        first = False
        add_mixed_runs(p, text, bold=bold, size=9, lang=lang)
        paras.append(p)
    return paras


def _hide_paragraph(p):
    """מסתיר פסקה (טקסט נסתר, גם סימן הפסקה): הקוד הפנימי של השורה נשאר בקובץ לצורך הקליטה, ואינו מוצג ללקוח."""
    for r in p.runs:
        r.font.hidden = True
    ppr = p._p.get_or_add_pPr()
    rpr = ppr.find(qn('w:rPr'))
    if rpr is None:
        rpr = OxmlElement('w:rPr')
        ppr.append(rpr)
    if rpr.find(qn('w:vanish')) is None:
        rpr.append(OxmlElement('w:vanish'))


def _check_hebrew_only(text, lang='he'):
    """קוד פנימי שדלף לגיליון. בגיליון באנגלית critical ו-Inferred הן מילים רגילות, ולכן נבדקים שם רק הקודים."""
    words = ('market_built', 'own_plus_market', 'areo_proposal', 'market_standard')
    if lang != 'en':
        words += ('critical', 'Inferred')
    for word in words:
        if word in text:
            raise SheetError('תווית באנגלית בגיליון: %s' % word)


def basis_counts(model):
    """ספירת התאים לפי סימון הראיה, אותה ספירה שבהחלטה הפותחת."""
    counts = {'market': 0, 'areo': 0, 'company': 0, 'statute': 0, 'unverified': 0}
    for rule in model.get('rules') or []:
        for track in TRACKS:
            t = (rule.get('traffic_light') or {}).get(track) or {}
            b = t.get('basis')
            if b == 'market_standard':
                counts['market' if len(market_ids(t)) >= MIN_MARKET_SOURCES else 'unverified'] += 1
            elif b == 'areo_proposal':
                counts['areo'] += 1
            elif b == 'statute':
                counts['statute'] += 1
            else:
                counts['company'] += 1
    return counts


def opening_text(model, counts, lang='he'):
    """פסקת האימוץ. שם המסמכים של החברה נגזר ממעמד המאגר (status.corpus_status), ולא "הסכמי החברה" תמיד."""
    T = SHEETS[sheet_lang(lang)]
    company_key = 'open_company' + S.CORPUS_SUFFIX.get(S.corpus_status(model), '')
    parts = []
    for key in ('market', 'unverified', 'areo', 'company', 'statute'):
        if counts.get(key):
            parts.append(T[company_key if key == 'company' else 'open_' + key] % counts[key])
    walks = [r['rule_id'] for r in model.get('rules') or [] if r.get('walk_away') is True]
    n_rules = len(model.get('rules') or [])
    if walks:
        parts.append(T['open_walks'] % (count_he(len(walks), *T['rules_count']), ', '.join(walks),
                                        n_rules - len(walks)))
    else:
        parts.append(T['open_no_walks'])
    return T['open_head'] + '; '.join(parts) + '.'


# ------------------------------------------------------------------ החלטות הנהלה
# סוגריים של ערך שהחברה קובעת (מספר, מכפיל, שעות, ימים, אחוז): המילה הראשונה בסוגריים, או סוגריים ריקים
# או ממולאים בסימנים. סוגריים שמתארים פרט של עסקה ("[נקודת המסירה]", "[הסעיף על הגבלת האחריות]",
# "[להשלים: <העובדה>]", playbook-qa.md 2 ו-18) אינם החלטה, ונשארים בנוסח המאושר.
SLOT_WORDS = ('מספר', 'מכפיל', 'שיעור', 'אחוז', 'ימים', 'שעות', 'חודשים', 'שנים',
              'number', 'multiple', 'multiplier', 'percentage', 'percent', 'days', 'hours', 'months', 'years',
              'x', 'n')
# "מספר" ו-number הם החלטה רק לבד או עם יחידה ("[מספר השעות]", "[number of days]"), ולא כמזהה ("[מספר הרישום]")
_COUNT_WORDS = ('מספר', 'number')
_UNITS = ('שעות', 'ימים', 'ימי', 'חודשים', 'שנים', 'פעמים', 'hours', 'days', 'months', 'years', 'times')
_SLOT = re.compile(r'\[([^\[\]]{0,40})\]')
_SLOT_FILLER = re.compile(r'^[\s_.\-•●*#xX?]*$')
MAX_DECISIONS = 8
# בעל ההחלטה נגזר מהמחלקות שהלקוח קבע בפלייבוק (departments_and_responsibilities.md): לכל נושא, סוגי החובה של
# מרשם ההתחייבויות שהוא נוגע להם, ומהם obligation_assignments[].department. בלי שיוך: מחלקה מ-responsible_departments
# שבשמה המילה של קוד הנפילה, ובלעדיה קוד הנפילה עצמו. קוד הנפילה כללי לכל סוג הסכם: כספים לנושא כספי, הנהלה לכל
# השאר. אין כאן נושא של סוג הסכם אחד, ולכן ביקורת או קבלני משנה בכל הסכם אינם נשלחים לאבטחת מידע.
# (קוד, קוד הנפילה, מילים בנושא בעברית, מילים באנגלית, אסימונים במזהה הכלל, סוגי החובה במרשם)
DECISION_TOPICS = (
    ('cap', 'finance', ('תקרה', 'תקרת', 'הגבלת אחריות', 'הגבלת החבות'), ('cap', 'liabilit'), ('LIAB', 'CAP'), ()),
    ('insurance', 'finance', ('ביטוח',), ('insur',), ('INS', 'INSUR'), ('insurance',)),
    ('indemnity', 'finance', ('שיפוי',), ('indemn',), ('INDEM', 'IND'), ()),
    ('guarantee', 'finance', ('ערבות', 'ערבויות', 'בטוחה', 'בטוחות', 'פיקדון', 'שעבוד'),
     ('guarantee', 'deposit', 'collateral', 'bond'), ('GUAR', 'DEPOSIT', 'COLL'), ('guarantee',)),
    ('payment', 'finance', ('תשלום', 'תמורה', 'מחיר', 'תעריף', 'ריבית', 'דמי ', 'עמלה', 'שכר טרחה', 'שכר עבודה'),
     ('payment', ' fee', 'price', 'interest', ' rent', 'commission'), ('PAY', 'FEES', 'PRICE'), ('payment',)),
    ('price_adjustment', 'finance', ('הצמדה', 'עדכון מחיר', 'עדכון תעריף'), ('indexation', 'price adjustment'),
     ('INDEX',), ('price_adjustment',)),
    ('audit', 'management', ('ביקורת',), ('audit', 'inspection'), ('AUDIT',), ('audit',)),
    ('notice', 'management', ('הודעה', 'דיווח'), ('notice', 'notif', 'report'), ('NOTIF', 'NOTICE', 'REPORT'),
     ('notice', 'reporting')),
    ('consent', 'management', ('הסכמה מראש', 'אישור מראש', 'קבלני משנה', 'המחאה'),
     ('consent', 'subcontract', 'assignment'), ('CONSENT', 'ASSIGN'), ('consent_approval',)),
    ('deliverable', 'management', ('זמינות', 'רמת שירות', 'רמות שירות', 'תמיכה', 'אבני דרך', 'אבן דרך', 'מסירה',
                                   'לוח זמנים'),
     ('availability', 'service level', 'support', 'milestone', 'delivery'), ('SLA', 'SUPPORT', 'MILESTONE'),
     ('deliverable', 'milestone')),
    ('return', 'management', ('מחיקה', 'מחיקת', 'השבת', 'החזרת'), ('deletion', 'return of'), ('DEL', 'RETURN'),
     ('data_return_deletion',)),
    ('confidentiality', 'management', ('סודיות',), ('confidential',), ('CONF',), ('confidentiality',)),
    ('termination', 'management', ('סיום', 'תקופת', 'ביטול', 'חידוש', 'שרידות', 'אופציה'),
     ('terminat', 'renewal', 'surviv', 'option'), ('TERM', 'EXIT', 'RENEW'), ('term_end', 'renewal_notice', 'option')),
    ('compliance', 'management', ('ציות', 'רגולצי', 'רישיון', 'היתר'), ('complian', 'regulat', 'licen', 'permit'),
     ('COMPL', 'REG'), ('compliance',)),
)
_IMPORTANCE_RANK = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}


def decision_slots(text):
    """הסוגריים של ערך שלא נקבע שבטקסט, כפי שהם ("[מכפיל]", "[number]"), לפי סדר ההופעה ובלי כפילות."""
    out = []
    for m in _SLOT.finditer(text or ''):
        inner = m.group(1).strip()
        first = (inner.split() or [''])[0].strip(':,.').lower()
        if first.startswith('ה') and first[1:] in SLOT_WORDS:
            first = first[1:]
        rest = inner.lower().split(None, 1)[1] if len(inner.split()) > 1 else ''
        if first in _COUNT_WORDS and rest and not any(u in rest for u in _UNITS):
            continue
        if (_SLOT_FILLER.match(inner) or first in SLOT_WORDS) and m.group(0) not in out:
            out.append(m.group(0))
    return out


def _decision_topic(rule):
    """(קוד הנושא, קוד הנפילה, סוגי החובה) לפי שם הנושא, הסוגיה ומזהה הכלל. None כשאין התאמה."""
    # רווח בתחילה: מילה באנגלית עם רווח לפניה (' rent') נתפסת גם בתחילת הנושא, ולא בתוך מילה (current)
    text = ' ' + ' '.join(str(rule.get(k) or '') for k in ('topic_name', 'clause_issue', 'topic_name_en')).lower()
    tokens = set(re.split(r'[_\-\s]+', str(rule.get('rule_id') or '').upper()))
    for code, owner, he, en, ids, types in DECISION_TOPICS:
        if tokens & set(ids) or any(w in text for w in he) or any(w in text for w in en):
            return code, owner, types
    return None


def _decision_owner(model, rule, topic, T):
    """(owner_code, owner): rule.decision_owner; המחלקה שהלקוח שייך לסוג החובה של הנושא (obligation_assignments,
    בתוספת "טעון אימות" כשהשיוך כזה); מחלקה מ-responsible_departments שבשמה המילה של קוד הנפילה; ואז קוד הנפילה."""
    fallback = topic[1] if topic else 'management'
    if rule.get('decision_owner'):
        return fallback, rule['decision_owner']
    for t in (topic[2] if topic else ()):
        for a in model.get('obligation_assignments') or ():
            if isinstance(a, dict) and a.get('type') == t and str(a.get('department') or '').strip():
                dept = str(a['department']).strip()
                return None, dept + (T['owner_unverified'] if a.get('needs_verification') else '')
    word = T['owners'][fallback].lower()
    for d in model.get('responsible_departments') or ():
        if isinstance(d, str) and word in d.lower():
            return fallback, d.strip()
    return fallback, T['owners'][fallback]


def _short(s, n=160):
    s = norm_text(s)
    return s if len(s) <= n else s[:n - 1].rstrip() + '…'


# היחידה של ערך בסוגריים: מילה בתוך הסוגריים ("[number of days]", "[מספר השעות]") או המילה שאחריהם
# ("[מספר] ימים", "[number] hours", "[X]%"). המפתח הוא קוד היחידה, והערך הוא השם שלה בכל שפה. כך השאלה אומרת
# "72 שעות" או "72 ימים" לפני שמקלידים, ולא אחרי שהערך כבר נכתב בנוסח ביחידה הלא נכונה.
UNIT_NAMES = {'hours': {'he': 'שעות', 'en': 'hours'}, 'business_days': {'he': 'ימי עבודה', 'en': 'business days'},
              'days': {'he': 'ימים', 'en': 'days'}, 'weeks': {'he': 'שבועות', 'en': 'weeks'},
              'months': {'he': 'חודשים', 'en': 'months'}, 'years': {'he': 'שנים', 'en': 'years'},
              'percent': {'he': 'אחוזים', 'en': 'percent'}, 'times': {'he': 'פעמים', 'en': 'times'},
              'multiple': {'he': 'מכפלה (פי כמה)', 'en': 'a multiple (times)'}}
_UNIT_FORMS = (('business_days', ('ימי עבודה', 'ימי עסקים', 'business days', 'working days')),
               ('hours', ('שעות', 'שעה', 'השעות', 'hours', 'hour')),
               ('days', ('ימים', 'יום', 'ימי', 'הימים', 'days', 'day', 'calendar days')),
               ('weeks', ('שבועות', 'שבוע', 'weeks', 'week')),
               ('months', ('חודשים', 'חודש', 'החודשים', 'months', 'month')),
               ('years', ('שנים', 'שנה', 'השנים', 'years', 'year')),
               ('percent', ('אחוזים', 'אחוז', '%', 'percent', 'per cent', 'percentage')),
               ('times', ('פעמים', 'פעם', 'times')),
               ('multiple', ('מכפיל', 'המכפיל', 'multiple', 'multiplier')))
_SENT_SPLIT = re.compile(r'(?<=[.;!?])\s+')


def unit_of(text, loose=False):
    """קוד היחידה שהטקסט פותח בה, או None: "ימים" → days, "hours" → hours, "%" → percent. loose: גם יחידה שמופיעה
    בתוך טקסט קצר (מה שכתוב בתוך הסוגריים, "[מספר השעות]")."""
    t = norm_text(text).lower().strip(' .,:;()')
    if not t:
        return None
    for code, forms in _UNIT_FORMS:
        for f in forms:
            if t == f or t.startswith(f + ' ') or (f == '%' and t.startswith('%')):
                return code
    words = t.split()
    if loose and len(words) <= 4:
        for code, forms in _UNIT_FORMS:
            if any(f in words for f in forms if f != 'פעם'):
                return code
    return None


def slot_context(texts, slot):
    """המשפט שבו מופיעים הסוגריים, והיחידה שלהם: {slot, sentence, unit, unit_where}. texts: הטקסטים לפי סדר העדפה
    (בשפת הממשק קודם). unit_where: inside (היחידה בתוך הסוגריים, ולכן היא נכתבת עם הערך) או after (היחידה כבר
    כתובה אחרי הסוגריים, ולכן כותבים מספר בלבד). בלי טקסט שמכיל את הסוגריים: sentence ריק."""
    for text in texts:
        text = norm_text(text)
        if slot not in text:
            continue
        sent = next((s for s in _SENT_SPLIT.split(text) if slot in s), text)
        if len(sent) > 320:
            i = sent.index(slot)
            a, b = max(0, i - 150), min(len(sent), i + len(slot) + 150)
            sent = ('…' if a else '') + sent[a:b].strip() + ('…' if b < len(sent) else '')
        words = slot.strip('[]').split()
        # "[מספר]", "[number]", "[X]" לבד אינם יחידה; "[מספר השעות]", "[number of days]", "[ימים]" כן
        cand = ' '.join(words[1:]) if len(words) > 1 else ' '.join(words)
        unit, where = unit_of(cand, loose=True), 'inside'
        if not unit:
            after = text[text.index(slot) + len(slot):]
            unit, where = unit_of(after[:24]), 'after'
        return {'slot': slot, 'sentence': sent, 'unit': unit, 'unit_where': where if unit else None}
    return {'slot': slot, 'sentence': '', 'unit': None, 'unit_where': None}


def _decision_texts(rule, lang):
    """הטקסטים של הכלל שבהם מחפשים את הסוגריים, בשפת הממשק קודם: בעברית העמדות ואז הנוסח, ובאנגלית הנוסח ואז
    העמדות (העמדות נכתבות בשפת הבנייה, והנוסח גם בשפת התוצר)."""
    tl = rule.get('traffic_light') or {}
    pos = [(tl.get(t) or {}).get('position') or '' for t in TRACKS]
    wor = [track_wording(t, tl.get(t) or {}, lang) for t in TRACKS]
    other = [track_wording(t, tl.get(t) or {}, 'he' if lang == 'en' else 'en') for t in TRACKS]
    return (wor + pos + other) if lang == 'en' else (pos + wor + other)


_NUM_UNIT = re.compile(r'(?<![\w.])(\d+(?:[.,]\d+)?)\s*(%|[^\W\d_]+(?:\s+[^\W\d_]+)?)?')


def number_context(texts):
    """המשפט והיחידה של המספר הראשון בעמדה (בלי סוגריים): {slot: המספר, sentence, unit, unit_where}. None כשאין מספר.
    השאלה על מספר תמיד מציגה את המשפט המלא ואת היחידה שלו (areo-voice.md), ולא "לאשר את המספרים"."""
    for text in texts:
        text = norm_text(text)
        for m in _NUM_UNIT.finditer(text):
            sent = next((x for x in _SENT_SPLIT.split(text) if m.group(0) in x), text)
            if len(sent) > 320:
                i = max(0, text.index(m.group(0)))
                sent = ('…' if i > 150 else '') + text[max(0, i - 150):i + 170].strip() + '…'
            unit = unit_of(m.group(2) or '') or (unit_of((m.group(2) or '').split()[0]) if m.group(2) else None)
            if not unit:
                continue        # מספר בלי יחידה (תקן, שנה, מספר סעיף) אינו החלטה
            return {'slot': m.group(1), 'sentence': sent, 'unit': unit, 'unit_where': 'after' if unit else None}
    return None


def decision_question(topic, contexts, lang):
    """השאלה של החלטת הנהלה, בשפת הממשק: הנושא, המשפט המלא שבו הסוגריים, והיחידה. בלי יחידה ידועה: בקשה לכתוב
    את הערך עם היחידה."""
    T = SHEETS[sheet_lang(lang)]
    parts = []
    for c in contexts:
        unit = (UNIT_NAMES.get(c.get('unit')) or {}).get(sheet_lang(lang))
        tail = T['mgmt_unit'].format(unit=unit) if unit else T['mgmt_no_unit']
        if c.get('sentence'):
            parts.append(T['mgmt_in_sentence'].format(slot=c['slot'], sentence=c['sentence'], tail=tail))
        else:
            parts.append(T['mgmt_slot_only'].format(slot=c['slot'], tail=tail))
    return T['mgmt_set'].format(topic=topic, slots='; '.join(parts))


def management_decisions(model, lang='he'):
    """עד MAX_DECISIONS החלטות במספרים לדף השער. [{n, rule_id, question, proposal, slots, owner_code, owner}].

    מקור ראשון: model.management_decisions[] כפי שהבונה כתב אותו ({rule_id, question, proposal, slots, owner}).
    בלעדיו, נגזר מהכללים: כלל שבנוסח או בעמדה שלו יש סוגריים של ערך שלא נקבע, או מספר בעמדה של מסלול ירוק או
    צהוב. הסדר: סוגריים קודם, ואז החשיבות. בעל ההחלטה: rule.decision_owner, ובלעדיו המחלקה שהלקוח שייך בפלייבוק
    לסוג החובה של הנושא (_decision_owner), ובלי שיוך כספים לנושא כספי והנהלה לכל השאר."""
    T = SHEETS[sheet_lang(lang)]
    explicit = model.get('management_decisions') or []
    out = []
    if explicit:
        by_id = {r.get('rule_id'): r for r in model.get('rules') or []}
        for d in explicit[:MAX_DECISIONS]:
            code = d.get('owner_code') or ''
            slots = list(d.get('slots') or [])
            rule = by_id.get(d.get('rule_id')) or {}
            ctx = [slot_context(_decision_texts(rule, sheet_lang(lang)), s) for s in slots]
            q = d.get('question') or ''
            if ctx and not any(c['sentence'] and c['sentence'] in q for c in ctx):
                # השאלה שהבונה כתב אינה מציגה את המשפט: נבנית מחדש, עם המשפט והיחידה
                q = decision_question(rule.get('topic_name') or q or d.get('rule_id') or '', ctx, lang)
            out.append({'rule_id': d.get('rule_id'), 'question': q,
                        'proposal': d.get('proposal') or '', 'slots': slots, 'context': ctx,
                        'owner_code': code or None,
                        'owner': d.get('owner') or d.get('decision_owner') or T['owners'].get(code, '')})
    else:
        cands = []
        for i, rule in enumerate(model.get('rules') or []):
            tl = rule.get('traffic_light') or {}
            slots, digits = [], False
            for track in TRACKS:
                t = tl.get(track) or {}
                for s in decision_slots((t.get('position') or '') + ' ' + track_wording(track, t, lang)):
                    if s not in slots:
                        slots.append(s)
                if track != 'red' and re.search(r'\d', t.get('position') or ''):
                    digits = True
            if not slots and not digits:
                continue
            topic = _decision_topic(rule)
            owner_code, owner = _decision_owner(model, rule, topic, T)
            name = rule.get('topic_name') or rule.get('rule_id') or ''
            ctx = [slot_context(_decision_texts(rule, sheet_lang(lang)), s) for s in slots]
            nctx = None if slots else number_context(
                [x for t, x in zip(TRACKS * 3, _decision_texts(rule, sheet_lang(lang))) if t != 'red'])
            if nctx:
                unit = (UNIT_NAMES.get(nctx['unit']) or {}).get(sheet_lang(lang))
                tail = T['mgmt_confirm_tail'].format(unit=unit)
                q = T['mgmt_confirm_in'].format(topic=name, num=nctx['slot'], sentence=nctx['sentence'], tail=tail)
                ctx = [nctx]
            else:
                q = decision_question(name, ctx, lang) if slots else T['mgmt_confirm'].format(topic=name)
            prop = []
            for track, key in (('green', 'mgmt_green'), ('yellow', 'mgmt_yellow')):
                pos = ((tl.get(track) or {}).get('position') or '').strip()
                if pos:
                    prop.append(T[key] + _short(pos))
            # הסדר: סוגריים, ואז החשיבות. נושא "מוכר" אינו קודם: בכל סוג הסכם ההחלטות שלו (תשלום תקופתי, ריבית,
            # פיקדון) עולות לפי החשיבות שלהן
            rank = (0 if slots else 1, _IMPORTANCE_RANK.get(str(rule.get('importance') or '').lower(), 4), i)
            cands.append((rank, {'rule_id': rule.get('rule_id'), 'question': q, 'proposal': '\n'.join(prop),
                                 'slots': slots, 'context': ctx, 'owner_code': owner_code,
                                 'owner': owner}))
        out = [d for _, d in sorted(cands, key=lambda x: x[0])[:MAX_DECISIONS]]
    for n, d in enumerate(out, 1):
        d['n'] = n
        d['num'] = display_num(model, d.get('rule_id'))
    return out


def display_num(model, rule_id):
    """מספר הסעיף כפי שהלקוח רואה אותו בסביבת העבודה ובאשף (rnum בתבנית): clause_number, ובלעדיו המקום ברשימה.
    המזהה הפנימי (R17) אינו מוצג ללקוח (areo-voice.md)."""
    for i, r in enumerate(model.get('rules') or []):
        if r.get('rule_id') == rule_id:
            return str(r.get('clause_number') or i + 1)
    return ''


def _decisions_page(doc, decisions, lang):
    """דף השער: כותרת, הסבר, וטבלה של 6 עמודות (הקליטה קוראת רק טבלאות של 4 ו-5 עמודות), ואז מעבר עמוד."""
    T = SHEETS[lang]
    en = lang == 'en'
    if en:
        _plain_para(doc, T['mgmt_title'], bold=True, size=13)
    else:
        rtl.add_paragraph(doc, T['mgmt_title'], bold=True, size=13)
    add_mixed_runs(doc.add_paragraph(), T['mgmt_intro'], size=10, lang=lang)
    table = doc.add_table(rows=1, cols=len(T['mgmt_cols']))
    table.style = 'Table Grid'
    for i, h in enumerate(T['mgmt_cols']):
        _cell_lines(table.rows[0].cells[i], [(h, True)], lang)
    for d in decisions:
        cells = table.add_row().cells
        _cell_lines(cells[0], [(str(d['n']), True)], lang)
        _cell_lines(cells[1], [(d['question'], True)] +
                    ([(T['clause_ref'].format(num=d['num']), False)] if d.get('num') else []), lang)
        _cell_lines(cells[2], [(x, False) for x in (d.get('proposal') or '-').split('\n')], lang)
        _cell_lines(cells[4], [(d.get('owner') or '', False)], lang)
    if not en:
        rtl.set_table_rtl(table)
    p = doc.add_paragraph()
    p.add_run().add_break(WD_BREAK.PAGE)
    if not en:
        rtl.set_paragraph_rtl(p)
    if en:
        _plain_para(doc, T['legal_head'], bold=True, size=13)
    else:
        rtl.add_paragraph(doc, T['legal_head'], bold=True, size=13)


def cell_view(model, rule, track, lang='he', index=None, roles=None, decisions=None):
    """התא כפי שהגיליון מציג אותו, בלי Word: {position, wording, effects{role: line}, flags, legal, assumptions[],
    slots[], fp}. אותה טביעת אצבע כמו ב-build_sheet (העמדה, הנוסח ושורות ההשפעה לפי סדר התפקידים), ולכן תא שאושר
    בצ'אט (ingest_approval, "אישור בצ'אט במנות") נבדק בשער המדיניות בדיוק כמו תא שנחתם בגיליון. שורת השפעה חסרה
    נשארת ריקה, ואינה עוצרת (הגיליון עוצר עליה בהפקה)."""
    lang = sheet_lang(lang)
    roles = roles if roles is not None else role_lines(model, lang)
    t = (rule.get('traffic_light') or {}).get(track) or {}
    position = (t.get('position') or '').strip()
    wording = (track_wording(track, t, lang) or '').strip()
    effects = {role: role_effect(t, role, single=len(roles) == 1) for role, _ in roles}
    parts = [position, wording] + [effects[r] for r, _ in roles]
    slots = decision_slots(' '.join(parts))
    for d in decisions if decisions is not None else management_decisions(model, lang):
        if d.get('rule_id') == rule.get('rule_id'):
            slots += [s for s in d.get('slots') or [] if s in ' '.join(parts) and s not in slots]
    return {'position': position, 'wording': wording, 'effects': effects,
            'flags': flags_for(rule, track, t, index if index is not None else unverified_index(model), lang,
                               S.corpus_status(model)),
            'legal': track in legal_review_tracks(rule), 'assumptions': list(t.get('assumptions') or []),
            'slots': slots, 'fp': fingerprint(parts)}


def _wording_gate(model):
    """בדיקות הפערים על כל נוסח לפני ההפקה. ייבוא מאוחר, כדי ש-validate_model ייבא את המודול הזה."""
    from playbook import validate_model as V
    hits = V.wording_findings(model)
    if hits:
        lines = ['%s %s: %s' % (h['rule_id'], h.get('track') or '', h['message']) for h in hits[:20]]
        raise SheetError('נוסח שנכשל בבדיקות הפערים (מודול בדיקות הפערים, common/gap_checks.py). הגיליון אינו מופק עד שהנוסח יתוקן:\n'
                         + '\n'.join(lines))


def _plain_para(doc, text, bold=False, size=11):
    """פסקה LTR לגיליון באנגלית (המקבילה של rtl.add_paragraph)."""
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold = bold
    r.font.size = Pt(size)
    return p


def build_sheet(model, out_dir, company='', lang='he', token_uid=None, check_wording=True):
    """מפיק את הגיליון ואת המניפסט. מחזיר (נתיב ה-docx, manifest dict). lang: he (RTL) או en (LTR)."""
    lang = sheet_lang(lang)
    T = SHEETS[lang]
    en = lang == 'en'
    if check_wording:
        _wording_gate(model)
    roles = role_lines(model, lang)
    index = unverified_index(model)
    fid = model.get('family_id') or 'family'
    uid = token_uid or uuid.uuid4().hex[:12]
    token = 'ISS-0001|%s|%s' % (fid, uid)

    doc = Document()
    sec = doc.sections[0]
    sec.orientation = WD_ORIENT.LANDSCAPE
    sec.page_width, sec.page_height = sec.page_height, sec.page_width
    for side in ('left_margin', 'right_margin', 'top_margin', 'bottom_margin'):
        setattr(sec, side, Cm(1.5))
    if en:
        _plain_para(doc, T['title'], bold=True, size=16)
    else:
        rtl.add_paragraph(doc, T['title'], bold=True, size=16)
    if company:
        add_mixed_runs(doc.add_paragraph(), company, size=10, lang=lang)

    counts = basis_counts(model)
    decisions = management_decisions(model, lang)
    manifest = {'token': token, 'uid': uid, 'family_id': fid, 'lang': lang, 'rows': {}, 'cells': {},
                'counts': counts, 'questions': {}, 'decisions': decisions}
    if decisions:
        _decisions_page(doc, decisions, lang)
    p = doc.add_paragraph()
    _checkbox(p, 'chk:open:Q-00', lang)
    add_mixed_runs(p, ' ' + opening_text(model, counts, lang), size=10, lang=lang)

    table = doc.add_table(rows=1, cols=4)
    table.style = 'Table Grid'
    for i, h in enumerate(T['cols']):
        _cell_lines(table.rows[0].cells[i], [(h, True)], lang)
    open_q = {}
    for qi in model.get('validation_queue') or []:
        if qi.get('rule_id') and not qi.get('answered') and (qi.get('status') or 'open') == 'open':
            open_q.setdefault(qi['rule_id'], []).append(qi)

    for rule in model.get('rules') or []:
        rid = rule['rule_id']
        code = rid
        cells = table.add_row().cells
        imp = T['importance'].get(str(rule.get('importance') or '').lower(), '')
        head = [(code, True), (rule.get('topic_name') or '', True), (T['importance_label'] + imp, False)]
        if rule.get('walk_away') is True:
            head.append((T['walk_away'], True))
        for u in index[1].get(rid) or []:
            head.append((T['topic_unverified'] + _finding_label(u, lang), False))
        for text, _ in head:
            _check_hebrew_only(text, lang)
        _hide_paragraph(_cell_lines(cells[0], head, lang)[0])   # הקוד נשאר שדה פנימי נסתר; הלקוח רואה את שם הנושא
        row_meta = {'rule_id': rid, 'segment': None, 'choices': [], 'comment': False, 'questions': []}
        for qi in open_q.get(rid, []):
            qid = qi.get('id') or qi.get('queue_id') or 'Q'
            qlines = [(T['choice_head'] + (qi.get('question') or ''), True)]
            if qi.get('recommendation'):
                qlines.append((T['recommendation'] + qi['recommendation'], False))
            qhead = _cell_lines(cells[0], qlines, lang)[0]
            options = []
            for n, opt in enumerate(qi.get('options') or []):
                cp = cells[0].add_paragraph()
                tag = 'chk:choice:%s:%s:%d' % (rid, qid, n)
                _checkbox(cp, tag, lang)
                add_mixed_runs(cp, ' ' + opt, size=9, lang=lang)
                row_meta['choices'].append(tag)
                options.append({'tag': tag, 'index': n, 'text': opt})
            cm = doc.add_comment(qhead.runs[0], text=T['choice_head'] + (qi.get('question') or ''),
                                 author=AREO_AUTHOR, initials='AR')
            cm.add_paragraph(T['comment_tail'])
            if not en:
                for cp_ in cm.paragraphs:
                    rtl.set_paragraph_rtl(cp_)
            row_meta['comment'] = True
            row_meta['questions'].append(qid)
            manifest['questions'][qid] = {'row': code, 'question': qi.get('question') or '', 'options': options,
                                          'severity': qi.get('severity')}
        manifest['rows'][code] = row_meta

        for i, track in enumerate(TRACKS):
            t = (rule.get('traffic_light') or {}).get(track) or {}
            position = (t.get('position') or '').strip()
            wording = (track_wording(track, t, lang) or '').strip()
            if track in ('green', 'yellow') and not wording:
                raise SheetError('%s %s: אין נוסח להחלה. הגיליון מציג את הנוסח שיוחל, ולא תקציר.' % (rid, track))
            effects = {}
            for role, label in roles:
                val = role_effect(t, role, single=len(roles) == 1)
                if not val:
                    raise SheetError('%s %s: חסרה שורת ההשפעה של התפקיד %s. כל תא מציג מה העמדה מטילה על '
                                     'החברה בכל תפקיד שיש לה בהסכם.' % (rid, track, role))
                effects[role] = val
            flags = flags_for(rule, track, t, index, lang, S.corpus_status(model))
            prefix = T['cure'] if track == 'red' else T['wording']
            lines = [(position, True), (prefix + (wording or T['no_wording']), False)]
            lines += [(label + effects[role], False) for role, label in roles]
            if flags:
                lines.append((T['flags'] + ' · '.join(flags), False))
            legal = track in legal_review_tracks(rule)
            if legal:
                lines.append((T['legal_line'], True))
                lines.append((T['legal_date'], True))
            for text, _ in lines:
                _check_hebrew_only(text, lang)
            _cell_lines(cells[1 + i], lines, lang)
            assumptions = []
            for n, a in enumerate(t.get('assumptions') or []):
                ap = cells[1 + i].add_paragraph()
                tag = 'chk:assume:%s:%s:%d' % (rid, track, n)
                _checkbox(ap, tag, lang)
                add_mixed_runs(ap, ' ' + T['assume'] + a, size=9, lang=lang)
                assumptions.append({'tag': tag, 'text': a})
            fp_parts = [position, wording] + [effects[r] for r, _ in roles]
            # סוגריים של ערך שלא נקבע בתא: הנגזרים, ואלה שהבונה רשם בהחלטת הנהלה של הכלל
            slots = decision_slots(' '.join(fp_parts))
            for d in decisions:
                if d.get('rule_id') == rid:
                    slots += [s for s in d.get('slots') or [] if s in ' '.join(fp_parts) and s not in slots]
            manifest['cells'][cell_key(rid, track)] = {
                'row': code, 'col': 1 + i, 'fp': fingerprint(fp_parts), 'position': position, 'wording': wording,
                'effects': effects, 'flags': flags, 'legal_review': legal,
                'assumptions': [a['tag'] for a in assumptions], 'assumption_texts': assumptions,
                'decision_slots': slots}
    if not en:
        rtl.set_table_rtl(table)

    if en:
        _plain_para(doc, T['sign_head'], bold=True, size=11)
    else:
        rtl.add_paragraph(doc, T['sign_head'], bold=True, size=11)
    sign = doc.add_table(rows=1, cols=5)
    sign.style = 'Table Grid'
    for i, h in enumerate(T['sign_cols']):
        _cell_lines(sign.rows[0].cells[i], [(h, True)], lang)
    for track in ('red', 'yellow', 'green'):
        cells = sign.add_row().cells
        _cell_lines(cells[0], [(T['track_label'][track], True)], lang)
        _checkbox(cells[1].paragraphs[0], 'chk:sign:%s' % track, lang)
    if not en:
        rtl.set_table_rtl(sign)

    p = doc.add_paragraph()
    _checkbox(p, 'chk:final', lang)
    if en:
        p.add_run(' ' + T['final']).font.size = Pt(11)
    else:
        rtl.set_run_rtl(p.add_run(' ' + T['final']), size=11)
        rtl.set_paragraph_rtl(p)
    add_mixed_runs(doc.add_paragraph(), T['token'].format(token=token), size=7, lang=lang)

    settings = doc.settings.element
    if settings.find(qn('w:trackRevisions')) is None:
        settings.insert(0, OxmlElement('w:trackRevisions'))
    if en:
        # LTR מלא: אין bidi, rtl, bidiVisual או rtlGutter בשום מקום, ו-language=en-US במאפייני הקובץ
        from playbook import surfaces_render as R
        R.enforce_ltr_document(doc, author=company, title=T['title'])
    else:
        rtl.enforce_document(doc, author=company, title=T['title'])   # אינו נוגע בריצה שסומנה LTR מפורש
        doc.core_properties.language = 'he-IL'
    doc.core_properties.identifier = token
    fam_label = re.sub(r'[\\/:*?"<>|]+', '-', model.get('family_label') or fid)[:40]
    name = '%s-%s-v1.docx' % (T['file'], fam_label)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, name)
    doc.save(path)
    with open(path, 'rb') as fh:
        manifest['issued_sha256'] = hashlib.sha256(fh.read()).hexdigest()
    return path, manifest
