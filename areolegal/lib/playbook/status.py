# -*- coding: utf-8 -*-
"""playbook/status.py: מעמד אחד ותווית אחת לפלייבוק, נגזרים בקוד, ומשמשים בכל מקום.

הבעיה: אחרי החתימה היו שלושה מעמדות סותרים, והתווית "מבוסס הסכמים" הופיעה כשמספר ההסכמים 0.

הבעיה:
- אחרי הקליטה, המודל, הגרעין והאינדקס אמרו "מדיניות מאושרת", ובאותה רשומה presentation_label אמר
  "טעון אישור"; התאים (ingest_result) נשארו מהרשומה המדומה; validation_queue נשאר פתוח; ה-handoff
  נשאר Draft; וה-Word וה-Workspace לא הופקו מחדש.
- check_consistency בדק רק שלושה שדות ברמה העליונה, ולכן החזיר [].
- התווית המאושרת לא נקבה בשם מי שאישר.

הכלל: שדה תווית אחד בלבד, status_label. presentation_label אינו נשמר בשום מקום (stamp מוחק אותו,
ו-check_consistency מסמן אותו). התווית הבסיסית (לפני אישור) נגזרת ב-base_label ומשמשת רק בתוך
status_label. היא נכתבת בקול של Areo (areo-voice.md: "טיוטת מדיניות, מחכה לאישור שלכם"), ואומרת במילים פשוטות
ממה המדיניות נבנתה:
- נקראו מסמכים של החברה מהסוג (corpus_read: נספרו הסכמים, או מסלול נשען על מסמך של החברה), בלי מחקר שוק ->
  "טיוטת מדיניות מההסכמים שלכם, מחכה לאישור שלכם"; עם מחקר שוק -> "טיוטת מדיניות מההסכמים שלכם וממחקר שוק, ..."
- לא נקרא מסמך של החברה, ויש מחקר שוק -> "טיוטת מדיניות ממחקר שוק, מחכה לאישור שלכם"
- לא נקרא מסמך של החברה, ואין מחקר שוק -> "טיוטת מדיניות בהמלצת Areo, בלי דוגמה מההסכמים שלכם, מחכה לאישור שלכם"
- מאגר חתום שרובו נייר של הצד שכנגד (source_log[].paper: theirs) -> "מנוסחים של הצד השני שחתמתם עליהם"
- כשהמאגר אינו הסכמים חתומים של החברה (scope_summary.corpus_status), "ההסכמים שלכם" מוחלף בשם המסמכים, כמו
  בשורת הבסיס (basis_line.DOCS): "מהנוסחים שאתם מציגים לצד השני", "מהמסמכים שלכם (רובם טיוטות)" או "מנוסחים
  שאינם הסכמים חתומים שלכם". corpus_status() כאן הוא מקור האמת של המעמד, ושורת הבסיס, ה-Word וסביבת העבודה
  קוראים ממנו
- כל התאים נספרים כמאושרים, ואין שאלה מכריעה פתוחה -> "מדיניות מאושרת, <DD.MM.YYYY>, בידי <שם, תפקיד>"
- חלק מהתאים -> "<התווית הבסיסית>; <N> מתוך <M> עמדות מאושרות"

התווית נגזרת רק מעובדות של המאגר שאינן משתנות באישור: corpus_origin, מספר ההסכמים שנספרו, corpus_status, נייר
הצד שכנגד ומחקר השוק. היא אינה נגזרת מה-basis של המסלולים, כי basis משתנה באישור (תשובת הלקוח, נוסח ששונה),
ובניסוי ארבעת הסוגים התווית התהפכה כך בין "מבוסס הסכמי החברה" ל"לא מבוסס על הסכמי החברה", וסתרה את
corpus_origin: own. כשנקראו מסמכים של החברה ואף מסלול אינו נשען עליהם (no_company_position), זה נאמר בשורת
הבסיס (basis_line.honesty_tail) ובאזהרות של playbook/validity.py, ולא בתווית. label_findings() בודק שהתווית
שנשמרה במודל, בגרעין, באינדקס וב-handoff היא התווית הנגזרת, ושהשכבות אינן סותרות זו את זו.

תא נספר כמאושר רק כש: המעמד שלו מאושר; policy_claim; הראיה אינה מדומה; כשהוא טעון בדיקה משפטית
נרשמו שם ותאריך; הוא אינו מסומן needs_amendment; ואין שאלה מכריעה פתוחה (חומרה גבוהה או קריטית)
בכלל שלו.

שפת התווית היא שפת התוצר (deliverable_language): status_label נכתב בשפה של הפלייבוק (model_lang), וכל
משטח מציג את התווית בשפה שלו (label_for, in_lang), מאותה גזירה. בתוצר באנגלית:
- "Draft policy from your agreements, awaiting your approval" והמקבילות;
- "Approved policy, <D.M.YYYY>, by <name, role>"; "<base>; <N> of <M> positions approved".

stamp() כותב את אותה תוצאה לכל השכבות: המודל, הגרעין, האינדקס, ה-handoff, התאים
(traffic_light.<track>.ingest_result), policy_status של כל כלל ושל כל סעיף בגרעין.
check_consistency() בודק את כל השכבות האלה, וגם את ה-Word ואת ה-Workspace כשהנתיבים נמסרים
(playbook.surfaces_render.check_surfaces).
"""
import datetime as _dt
import io
import json
import os

TRACKS = ('green', 'yellow', 'red')
APPROVED = ('approved', 'approved_modified')

APPROVED_PREFIX = 'מדיניות מאושרת'
PARTIAL_FMT = '{base}; {n} מתוך {m} עמדות מאושרות'
# התווית הבסיסית בקול של Areo (areo-voice.md, המילון: "פלייבוק מוצע, טעון אישור" -> "טיוטת מדיניות, מחכה לאישור
# שלכם"). כל קוד אומר במילים פשוטות ממה המדיניות נבנתה: ההסכמים שלכם, הנוסחים שלכם, מחקר שוק, המלצה של Areo או נייר
# הצד השני. הקודים (market, mixed, own, areo והסיומות) ושמות השדות לא השתנו. אותן תוויות בתוצר באנגלית
# (localization-he.md, "המעמד והתווית")
LABEL_MARKET = 'טיוטת מדיניות ממחקר שוק, מחכה לאישור שלכם'
LABEL_MIXED = 'טיוטת מדיניות מההסכמים שלכם וממחקר שוק, מחכה לאישור שלכם'
LABEL_OWN = 'טיוטת מדיניות מההסכמים שלכם, מחכה לאישור שלכם'
LABELS = {
    'he': {'market': LABEL_MARKET, 'mixed': LABEL_MIXED, 'own': LABEL_OWN, 'approved': APPROVED_PREFIX,
           'partial': PARTIAL_FMT, 'by': ', בידי %s'},
    'en': {'market': 'Draft policy from market research, awaiting your approval',
           'mixed': 'Draft policy from your agreements and market research, awaiting your approval',
           'own': 'Draft policy from your agreements, awaiting your approval',
           'approved': 'Approved policy', 'partial': '{base}; {n} of {m} positions approved', 'by': ', by %s'},
}
# מעמד המאגר (playbook-schema.md, scope_summary.corpus_status; workflow.md, שלב 2ח)
CORPUS_STATUSES = ('signed', 'mostly_drafts', 'company_forms', 'third_party_forms', 'unknown')
# הסיומת של קוד התווית לפי מעמד המאגר: אותם שמות מסמכים כמו basis_line.DOCS
CORPUS_SUFFIX = {'signed': '', 'mostly_drafts': '_drafts', 'company_forms': '_forms',
                 'third_party_forms': '_other', 'unknown': '_other'}
LABELS['he'].update({
    'own_drafts': 'טיוטת מדיניות מהמסמכים שלכם (רובם טיוטות), מחכה לאישור שלכם',
    'mixed_drafts': 'טיוטת מדיניות מהמסמכים שלכם (רובם טיוטות) וממחקר שוק, מחכה לאישור שלכם',
    'own_forms': 'טיוטת מדיניות מהנוסחים שאתם מציגים לצד השני, מחכה לאישור שלכם',
    'mixed_forms': 'טיוטת מדיניות מהנוסחים שאתם מציגים לצד השני וממחקר שוק, מחכה לאישור שלכם',
    'own_other': 'טיוטת מדיניות מנוסחים שאינם הסכמים חתומים שלכם, מחכה לאישור שלכם',
    'mixed_other': 'טיוטת מדיניות מנוסחים שאינם הסכמים חתומים שלכם וממחקר שוק, מחכה לאישור שלכם'})
LABELS['en'].update({
    'own_drafts': 'Draft policy from your documents (most of them drafts), awaiting your approval',
    'mixed_drafts': 'Draft policy from your documents (most of them drafts) and market research, '
                    'awaiting your approval',
    'own_forms': 'Draft policy from the forms you present to counterparties, awaiting your approval',
    'mixed_forms': 'Draft policy from the forms you present to counterparties and market research, '
                   'awaiting your approval',
    'own_other': 'Draft policy from forms that are not your signed agreements, awaiting your approval',
    'mixed_other': 'Draft policy from forms that are not your signed agreements and market research, '
                   'awaiting your approval'})
# areo: לא נקרא מסמך של החברה ואין מחקר שוק (המילון: "המלצה של Areo. לא נמצאה אצלכם דוגמה"); _theirs: מאגר חתום
# שרובו נייר של הצד שכנגד (source_log[].paper: theirs)
LABELS['he'].update({
    'areo': 'טיוטת מדיניות בהמלצת Areo, בלי דוגמה מההסכמים שלכם, מחכה לאישור שלכם',
    'own_theirs': 'טיוטת מדיניות מנוסחים של הצד השני שחתמתם עליהם, מחכה לאישור שלכם',
    'mixed_theirs': 'טיוטת מדיניות מנוסחים של הצד השני שחתמתם עליהם וממחקר שוק, מחכה לאישור שלכם'})
LABELS['en'].update({
    'areo': 'Draft policy recommended by Areo, with no example from your agreements, awaiting your approval',
    'own_theirs': 'Draft policy from counterparty paper you signed, awaiting your approval',
    'mixed_theirs': 'Draft policy from counterparty paper you signed and market research, awaiting your approval'})
BASE_CODES = ('market', 'mixed', 'own', 'areo') + tuple(b + s for b in ('own', 'mixed')
                                                         for s in ('_drafts', '_forms', '_other', '_theirs'))
# התוויות הקודמות ("פלייבוק מוצע, ..., טעון אישור" ונוסחי "ללקוחותיה"): עדיין מזוהות כתווית בסיס, כדי שמשטח או
# שכבה שנכתבו בהן יעודכנו בהפקה הבאה (surfaces_render), ו-label_findings מסמן אותן כתווית ישנה
OLD_LABELS = {
    'he': {'market': 'פלייבוק מוצע, מבוסס מחקר שוק, טעון אישור',
           'mixed': 'פלייבוק מוצע, מבוסס הסכמים ומחקר שוק, טעון אישור',
           'own': 'פלייבוק מוצע, מבוסס הסכמי החברה, טעון אישור',
           'own_drafts': 'פלייבוק מוצע, מבוסס מסמכי החברה שרובם טיוטות, טעון אישור',
           'mixed_drafts': 'פלייבוק מוצע, מבוסס מסמכי החברה שרובם טיוטות ומחקר שוק, טעון אישור',
           'own_forms': 'פלייבוק מוצע, מבוסס נוסחים שהחברה מציגה לצד שכנגד, טעון אישור',
           'mixed_forms': 'פלייבוק מוצע, מבוסס נוסחים שהחברה מציגה לצד שכנגד ומחקר שוק, טעון אישור',
           'own_other': 'פלייבוק מוצע, מבוסס נוסחים שאינם הסכמים חתומים של החברה, טעון אישור',
           'mixed_other': 'פלייבוק מוצע, מבוסס נוסחים שאינם הסכמים חתומים של החברה ומחקר שוק, טעון אישור',
           'areo': 'פלייבוק מוצע, הצעת Areo, לא מבוסס על הסכמי החברה, טעון אישור',
           'own_theirs': 'פלייבוק מוצע, מבוסס נוסחים של הצד שכנגד, טעון אישור',
           'mixed_theirs': 'פלייבוק מוצע, מבוסס נוסחים של הצד שכנגד ומחקר שוק, טעון אישור'},
    'en': {'market': 'Proposed playbook, based on market research, subject to approval',
           'mixed': 'Proposed playbook, based on agreements and market research, subject to approval',
           'own': "Proposed playbook, based on the company's agreements, subject to approval",
           'own_drafts': "Proposed playbook, based on the company's documents, most of them drafts, subject to "
                         "approval",
           'mixed_drafts': "Proposed playbook, based on the company's documents, most of them drafts, and market "
                           "research, subject to approval",
           'own_forms': 'Proposed playbook, based on forms the company presents to its counterparties, subject to '
                        'approval',
           'mixed_forms': 'Proposed playbook, based on forms the company presents to its counterparties and market '
                          'research, subject to approval',
           'own_other': 'Proposed playbook, based on forms that are not signed agreements of the company, subject '
                        'to approval',
           'mixed_other': 'Proposed playbook, based on forms that are not signed agreements of the company and '
                          'market research, subject to approval',
           'areo': "Proposed playbook, an Areo proposal, not based on the company's agreements, subject to approval",
           'own_theirs': 'Proposed playbook, based on counterparty paper, subject to approval',
           'mixed_theirs': 'Proposed playbook, based on counterparty paper and market research, subject to '
                           'approval'},
}
LEGACY_BASE_LABELS = tuple(OLD_LABELS[g][k] for g in ('he', 'en') for k in BASE_CODES) + (
    'פלייבוק מוצע, מבוסס נוסחים שהחברה מציגה ללקוחותיה, טעון אישור',
    'פלייבוק מוצע, מבוסס נוסחים שהחברה מציגה ללקוחותיה ומחקר שוק, טעון אישור',
    'Proposed playbook, based on forms the company presents to its customers, subject to approval',
    'Proposed playbook, based on forms the company presents to its customers and market research, '
    'subject to approval')
CURRENT_BASE_LABELS = tuple(LABELS[g][k] for g in ('he', 'en') for k in BASE_CODES)
BASE_LABELS = CURRENT_BASE_LABELS + LEGACY_BASE_LABELS
APPROVED_PREFIXES = (LABELS['he']['approved'], LABELS['en']['approved'])

LABEL_FIELD = 'status_label'
DUAL_FIELDS = ('presentation_label',)
HIGH_SEVERITY = ('high', 'critical', 'גבוהה', 'קריטית')

# basis של מסלול שנשען על מסמך של החברה (playbook-core-schema.md: own|own_plus_market|market_built)
COMPANY_BASES = ('company_agreement', 'company_template', 'agreement', 'template', 'established',
                 'company_policy', 'signed_deviation')
MARKET_ORIGINS = ('own_plus_market', 'market_built')

STATUS_DRAFT, STATUS_PARTIAL, STATUS_APPROVED = 'Draft', 'PartiallyApproved', 'Approved'

# ---- רשומת אישור ישנה (גרסה 1.2.0): כלל אחד, כאן, ו-ingest_approval משתמש בו ----
# רשומה בלי received_via או בלי upload_ref (ב-evidence או בשורש הרשומה) היא רשומה ישנה: אין בה ראיה שהגיליון
# החתום הגיע מהמשתמש. התאים שלה אינם נספרים כמאושרים, והמשתמש מתבקש פעם אחת להעלות שוב את הגיליון החתום.
REUPLOAD_NOTICE = ('רשומת האישור נקלטה בגרסה קודמת, בלי ראיה להעלאת הגיליון החתום. העמדות שבה אינן נספרות '
                   'כמאושרות. יש להעלות שוב את גיליון העמדות החתום.')


def norm_lang(v):
    """he, en או None. "both" ושאר הערכים: None, כדי שהמקור הבא יכריע."""
    v = str(v or '').strip().lower()
    if v.startswith('en'):
        return 'en'
    if v.startswith('he') or v in ('iw', 'עב', 'עברית'):
        return 'he'
    return None


def deliverable_lang(model=None, profile=None, lang=None):
    """שפת התוצר: lang מפורש, deliverable_language בפרופיל, במודל (scope_summary או השורש), ואז
    display_language בפרופיל ("both": התוצר הראשי בשפת הממשק). ברירת מחדל: he."""
    model, prof = model or {}, profile or {}
    for v in (lang, prof.get('deliverable_language'),
              (model.get('scope_summary') or {}).get('deliverable_language'), model.get('deliverable_language'),
              prof.get('display_language')):
        got = norm_lang(v)
        if got:
            return got
    return 'he'


def model_lang(model):
    """שפת הפלייבוק כפי שנרשמה במודל. בה נכתב status_label בכל השכבות."""
    return deliverable_lang(model)


def is_legacy_record(record):
    """True כשלרשומת האישור חסרים received_via או upload_ref."""
    if not record:
        return False
    ev = record.get('evidence') or {}
    via = ev.get('received_via') or record.get('received_via')
    ref = ev.get('upload_ref') or record.get('upload_ref')
    return not (via and ref)


def effective_cells(record, cells=None):
    """התאים כפי שהם נספרים: ברשומה ישנה כל תא legacy, policy_claim=False ו-simulated=True (בלי לשנות את
    הרשומה עצמה). cells: התאים, כשאינם בתוך הרשומה."""
    cells = cells if cells is not None else (record or {}).get('cells') or {}
    if not is_legacy_record(record):
        return cells
    return {k: dict(c, legacy=True, policy_claim=False, simulated=True) for k, c in cells.items()}


def _latest_record(model):
    recs = [r for r in (model or {}).get('approval_records') or [] if not r.get('superseded_by')]
    return recs[-1] if recs else None


def cell_key(rule_id, track, segment=None):
    return '%s|%s|%s' % (rule_id, segment or '-', track)


def iter_cell_keys(model):
    """כל התאים בפלייבוק: שלושה מסלולים לכל כלל, וגרסאות סגמנט שמגדירות מסלול."""
    for rule in model.get('rules') or []:
        for t in TRACKS:
            yield cell_key(rule['rule_id'], t)
        for var in rule.get('segment_variants') or []:
            for t in TRACKS:
                if (var.get('traffic_light') or {}).get(t) and var.get('segment_id'):
                    yield cell_key(rule['rule_id'], t, var['segment_id'])


def agreements_counted(model):
    """מספר ההסכמים מהסוג שנספרו (corpus_basis), ולא מספר הקבצים בתיקייה."""
    cb = model.get('corpus_basis') or {}
    for k in ('agreements_counted', 'agreement_units', 'counted'):
        if isinstance(cb.get(k), int):
            return cb[k]
    ss = model.get('scope_summary') or {}
    if isinstance(ss.get('total_document_count'), int):
        return ss['total_document_count']
    return 0


# סוגי צד שכנגד שהנוסח שלהם הוא נייר של הגוף עצמו (הליך תחרותי, חוזה אחיד): טופס שלו אינו הסכם של החברה
PUBLIC_KINDS = ('public_body', 'government_company', 'university')


def _base(p):
    return os.path.basename(str(p or '').replace(chr(92), '/'))


def is_counterparty_form(row, listed=()):
    """האם מקור ב-source_log הוא טופס של הצד שכנגד או של גוף ציבורי, ולא הסכם של החברה: מסמך מסוג form (doc_role)
    על נייר הצד שכנגד (paper: theirs), מול צד שכנגד שהוא גוף ציבורי (counterparty_kind), או שהבונה רשם אותו ב-
    corpus_basis.needs_review.counterparty_forms. הסכם חתום (doc_role: signed) נשאר הסכם גם על נייר שלהם: החברה חתמה
    עליו."""
    if str(row.get('doc_role') or '') != 'form':
        return False
    return (row.get('paper') == 'theirs' or row.get('counterparty_kind') in PUBLIC_KINDS
            or _base(row.get('file')) in listed)


# doc_role שאינו הסכם: הנחיה פנימית, מדיניות או טבלה של החברה, תבנית, תכתובת. מסמך כזה אינו נספר כהסכם בשום
# מונה ובשום מכנה (ביקורת 31.10, כלל 3): הוא שכבת ראיות נפרדת, ומשקלו בקביעת עמדה גבוה משל טיוטה
NON_AGREEMENT_ROLES = ('template', 'guidance', 'policy', 'table', 'correspondence')


def is_agreement_row(row):
    """האם שורת source_log היא הסכם (חתום, טיוטה, תיקון, נוסח) ולא הנחיה, מדיניות, טבלה או תבנית."""
    if not isinstance(row, dict) or row.get('included') is False or row.get('exclusion_reason') == 'not_agreement':
        return False
    if row.get('is_agreement') is False or row.get('doc_kind') in ('guidance', 'policy', 'table'):
        return False
    return str(row.get('doc_role') or '') not in NON_AGREEMENT_ROLES


def company_agreements_counted(model):
    """כמה מהמסמכים שנספרו הם הסכמים או נוסחים של החברה עצמה, בלי טפסים של הצד שכנגד ושל גופים ציבוריים. מקור
    האמת של "נבנה מ-N" ושל הקביעה שנקראו מסמכים של החברה (corpus_read). נגזר מעובדות המאגר (source_log,
    corpus_basis), ולכן אינו משתנה באישור. במודל בלי source_log: הספירה הכללית (agreements_counted)."""
    total = agreements_counted(model)
    rows = [r for r in model.get('source_log') or [] if isinstance(r, dict) and r.get('included', True)]
    if not rows:
        return total
    nr = ((model.get('scope_summary') or {}).get('corpus_basis') or {}).get('needs_review') or {}
    listed = {_base(x) for x in nr.get('counterparty_forms') or []}
    own = sum(1 for r in rows if is_agreement_row(r) and not is_counterparty_form(r, listed))
    return min(total, own)


NON_COMPANY_BASES = ('market_standard', 'areo_proposal')


def company_backed_tracks(model):
    """מסלולים שנשענים על מסמך של החברה: כל basis שאינו שוק ואינו הצעת Areo.

    רשימה של ערכי חברה נשחקת עם כל ערך חדש (own_paper_repeated, single, client_answer); רשימת הערכים שאינם של
    החברה קצרה וסגורה."""
    n = 0
    for rule in model.get('rules') or []:
        for t in TRACKS:
            basis = ((rule.get('traffic_light') or {}).get(t) or {}).get('basis')
            if basis and basis not in NON_COMPANY_BASES:
                n += 1
    return n


def corpus_origin(model):
    """corpus_origin מהשורש, ובמודל שכתב אותו רק ב-scope_summary, משם."""
    return model.get('corpus_origin') or (model.get('scope_summary') or {}).get('corpus_origin')


def corpus_read(model):
    """האם המדיניות נבנתה ממסמכים של החברה מהסוג: נספר לפחות מסמך אחד של החברה עצמה (company_agreements_counted),
    כלומר לא טופס של הצד שכנגד או של גוף ציבורי. לעולם לא כש-corpus_origin הוא market_built. נגזר מעובדות המאגר בלבד:
    ה-basis של המסלולים משתנה באישור (תשובת לקוח, נוסח ששונה), ולכן אינו נשקל כאן, והתווית אינה מתהפכת בין "מבוסס
    הסכמי החברה" ל"לא מבוסס" לפני ואחרי אישור."""
    if corpus_origin(model) == 'market_built':
        return False
    return company_agreements_counted(model) > 0


def no_company_position(model):
    """True כשנקראו מסמכים של החברה (corpus_read), ואף מסלול אינו נשען עליהם (כולם הצעת Areo או שוק). התווית
    אומרת ממה המדיניות נבנתה; את זה אומרות שורת הבסיס (basis_line.honesty_tail) והאזהרות (playbook/validity.py)."""
    if not corpus_read(model) or company_backed_tracks(model):
        return False
    return any(((r.get('traffic_light') or {}).get(t) or {}).get('basis')
               for r in model.get('rules') or [] if isinstance(r, dict) for t in TRACKS)


def uses_market(model):
    if corpus_origin(model) in MARKET_ORIGINS:
        return True
    mr = model.get('market_research') or {}
    return any(f.get('client_choice') == 'include' for f in mr.get('findings') or [])


def mostly_drafts(model):
    """האם רוב המקורות שנכללו הם טיוטות (source_log[].doc_role)."""
    rows = [r for r in model.get('source_log') or [] if isinstance(r, dict) and r.get('included')]
    return bool(rows) and sum(1 for r in rows if r.get('doc_role') == 'draft') * 2 > len(rows)


def corpus_status(model):
    """מעמד המאגר, ממקום אחד לכל המשטחים: scope_summary.corpus_status, ובמודל שלא כתב אותו mostly_drafts
    כשרוב המקורות טיוטות, ואחרת signed (לפני כן הגזירה ישבה רק ב-basis_line.py, והתווית לא קראה אותה)."""
    st = (model.get('scope_summary') or {}).get('corpus_status')
    if st in CORPUS_STATUSES:
        return st
    return 'mostly_drafts' if mostly_drafts(model) else 'signed'


def theirs_paper(model):
    """האם רוב המסמכים שנכללו הם נייר של הצד שכנגד (source_log[].paper: theirs)."""
    rows = [r for r in model.get('source_log') or [] if isinstance(r, dict) and r.get('included', True)]
    return bool(rows) and sum(1 for r in rows if r.get('paper') == 'theirs') * 2 > len(rows)


def base_code(model):
    """market, mixed, own או areo, ואחרי mixed ו-own הסיומת של מעמד המאגר (_drafts, _forms, _other) או של נייר
    הצד שכנגד (_theirs): הבסיס של התווית, בלי שפה. הגזירה היחידה של התווית, וכל קורא (המודל, הגרעין, האינדקס,
    ה-Word, נתוני סביבת העבודה, שורת הבסיס ושער המדיניות) מקבל אותה מכאן.

    נגזר מעובדות המאגר שאינן משתנות באישור (corpus_read, corpus_status, theirs_paper, uses_market): נקראו מסמכים
    של החברה -> own או mixed; לא נקראו, ויש מחקר שוק -> market; לא נקראו ואין מחקר שוק -> areo. ה-basis של
    המסלולים קובע רק את corpus_read כשאין ספירה, ולא את הקוד, ולכן אישור שמשנה basis אינו הופך את התווית."""
    read = corpus_read(model)
    status = corpus_status(model)
    suffix = '_theirs' if status == 'signed' and theirs_paper(model) else CORPUS_SUFFIX[status]
    if uses_market(model):
        return 'mixed' + suffix if read else 'market'
    return 'own' + suffix if read else 'areo'


def base_label(model, lang=None):
    """התווית לפני אישור, מ-base_code. "ההסכמים שלכם" רק כשהמאגר הוא הסכמים חתומים של החברה (corpus_status)."""
    return LABELS[norm_lang(lang) or model_lang(model)][base_code(model)]


def code_of_label(text):
    """(base_code, lang, old) של תווית בסיס, או של החלק הראשון של תווית חלקית ("<בסיס>; N מתוך M"). old=True
    לתווית מהניסוח הקודם. (None, None, False) כשאינה תווית בסיס (למשל "מדיניות מאושרת, ...")."""
    t = str(text or '').split(';')[0].strip()
    for old, table in ((False, LABELS), (True, OLD_LABELS)):
        for g in ('he', 'en'):
            for k in BASE_CODES:
                if table[g].get(k) == t:
                    return k, g, old
    return None, None, False


def label_findings(model, core=None, index_entry=None):
    """הבדיקה שהתווית לא נסחפה: [(code, message)], ריקה = עקבי. בכל שכבה שנשמרה בה תווית (model, core, index,
    handoff):
    - LABEL_MISMATCH: בסיס התווית אינו base_code של המודל (התווית "התהפכה"), או שהמעמד אינו תואם את התווית
      (Draft עם "מדיניות מאושרת", Approved עם תווית בסיס).
    - LABEL_OLD_WORDING: התווית בניסוח הקודם ("פלייבוק מוצע, ..., טעון אישור"). ההפקה הבאה כותבת אותה מחדש.
    - LABEL_DRIFT: שתי שכבות שומרות תוויות שונות לאותו פלייבוק.
    אינה צריכה את רשומת האישור: מספר העמדות המאושרות נבדק ב-check_consistency."""
    out = []
    want = base_code(model)
    holders = [('model', model), ('core', core), ('index', index_entry)]
    if isinstance(model.get('handoff'), dict):
        holders.append(('handoff', model['handoff']))
    seen = {}
    for name, holder in holders:
        if not isinstance(holder, dict) or not holder.get(LABEL_FIELD):
            continue
        lbl = str(holder.get(LABEL_FIELD))
        status = holder.get('playbook_status') or STATUS_DRAFT
        seen[name] = lbl
        code, _lang, old = code_of_label(lbl)
        approved_lbl = lbl.startswith(APPROVED_PREFIXES)
        if approved_lbl:
            if status != STATUS_APPROVED:
                out.append(('LABEL_MISMATCH', '%s.status_label="%s" אומר "מדיניות מאושרת", והמעמד %s.'
                            % (name, lbl, status)))
            continue
        if code is None:
            out.append(('LABEL_MISMATCH', '%s.status_label="%s" אינו תווית שנגזרת ב-status.py. הנגזרת: "%s".'
                        % (name, lbl, base_label(model))))
            continue
        if status == STATUS_APPROVED:
            out.append(('LABEL_MISMATCH', '%s.status_label="%s", והמעמד Approved.' % (name, lbl)))
        if code != want:
            out.append(('LABEL_MISMATCH', '%s.status_label="%s" (%s), ולפי corpus_origin=%s, %d הסכמים שנספרו, '
                        'corpus_status=%s ומחקר השוק התווית היא "%s" (%s).'
                        % (name, lbl, code, corpus_origin(model), agreements_counted(model), corpus_status(model),
                           base_label(model), want)))
        elif old:
            out.append(('LABEL_OLD_WORDING', '%s.status_label בניסוח הקודם ("%s"). התווית בקול של Areo: "%s".'
                        % (name, lbl, base_label(model))))
    if len(set(seen.values())) > 1:
        out.append(('LABEL_DRIFT', 'התווית שונה בין השכבות: %s.'
                    % '; '.join('%s="%s"' % (k, v) for k, v in sorted(seen.items()))))
    return out


def label_for(st, lang=None):
    """התווית של st בשפה lang, מאותה גזירה (בלי לגזור מחדש). כל משטח מציג את התווית בשפה שלו."""
    lang = norm_lang(lang) or st.get('lang') or 'he'
    L = LABELS[lang]
    base = L[st.get('base_code') or 'own']
    if st['playbook_status'] == STATUS_APPROVED:
        return '%s, %s' % (L['approved'], fmt_date(st.get('approved_on') or _dt.date.today().isoformat(), lang)) + \
            (L['by'] % st['approved_by'] if st.get('approved_by') else '')
    if st['playbook_status'] == STATUS_PARTIAL:
        return L['partial'].format(base=base, n=st['approved_count'], m=st['positions_count'])
    return base


# יחידה אחת בכל מונה: עמדות. נושאים אינם נספרים ללקוח (הם נשארים ב-status לשימוש פנימי)
PROGRESS = {'he': 'אושרו {n} מתוך {m} עמדות.',
            'en': '{n} of {m} positions approved.'}


def progress_line(st, lang=None):
    """שורת ההתקדמות של תור האישור, מאותה גזירה: נושאים ועמדות שאושרו בפועל. אינה מחליפה את status_label, שהוא
    מונח המעמד היחיד; היא באה אחריו."""
    lang = norm_lang(lang) or st.get('lang') or 'he'
    return PROGRESS[lang].format(t=st.get('approved_topics', 0), tm=st.get('topics_count', 0),
                                 n=st.get('approved_count', 0), m=st.get('positions_count', 0))


def in_lang(st, lang):
    """עותק של st שהתווית שלו בשפה lang. כשהשפה זהה (או לא נמסרה), st עצמו."""
    lang = norm_lang(lang)
    if not lang or lang == st.get('lang'):
        return st
    out = dict(st, lang=lang)
    out['label'] = label_for(out, lang)
    out['base_label'] = LABELS[lang][out.get('base_code') or 'own']
    return out


EN_MONTHS = ('January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December')


def fmt_date(iso, lang='he'):
    """תאריך בטקסט שהמשתמש קורא, לפי השפה (הכללים המשותפים 3.6): בעברית D.M.YYYY, ובאנגלית "3 April 2027".
    ב-JSON התאריך נשאר ISO."""
    d = _dt.date.fromisoformat(str(iso)[:10])
    if norm_lang(lang) == 'en':
        return '%d %s %d' % (d.day, EN_MONTHS[d.month - 1], d.year)
    return '%d.%d.%d' % (d.day, d.month, d.year)


def _he_date(iso):
    return fmt_date(iso, 'he')


def open_decisive(model):
    """שאלות מכריעות פתוחות (חומרה גבוהה או קריטית) ב-validation_queue."""
    out = []
    for qi in model.get('validation_queue') or []:
        st = qi.get('status') or ('closed' if qi.get('answered') else 'open')
        if st == 'open' and not qi.get('answered') and str(qi.get('severity') or '').lower() in HIGH_SEVERITY:
            out.append(qi)
    return out


def _rule_of(key):
    return key.split('|')[0]


def cell_counts(cell):
    """האם תא נספר כמאושר: מעמד מאושר, policy_claim, ראיה שאינה מדומה, בדיקה משפטית שנרשמה בשם ובתאריך
    כשנדרשה, ובלי סימון needs_amendment (פגם שהנושא ונותן מצא בנוסח מאושר)."""
    if not cell or cell.get('status') not in APPROVED:
        return False
    if not cell.get('policy_claim') or cell.get('simulated') or cell.get('needs_amendment') or cell.get('legacy'):
        return False
    if cell.get('legal_review_required') and not (cell.get('legal_review_done_by') and
                                                  cell.get('legal_review_done_at', True)):
        return False
    return True


def _signed_by(cells, keys):
    seen = []
    for k in keys:
        c = cells.get(k) or {}
        who = ', '.join(x for x in (c.get('signer'), c.get('role')) if x)
        if who and who not in seen:
            seen.append(who)
    return '; '.join(seen)


def derive_status(model, cells=None, record=None, lang=None):
    """cells: {cell_key: {status, policy_claim, simulated, legal_review_required, legal_review_done_by,
    legal_review_done_at, approved_at, signer, role}} מרשומת הקליטה. record: רשומת האישור (בלעדיה: האחרונה
    ב-model.approval_records). רשומה ישנה (is_legacy_record): אף תא אינו נספר, ו-notices מכיל את REUPLOAD_NOTICE
    פעם אחת. lang: שפת התווית (he|en); בלעדיו שפת הפלייבוק שבמודל (model_lang). מחזיר dict אחד שכל הרכיבים
    קוראים ממנו."""
    rec = record if record is not None else _latest_record(model)
    legacy = is_legacy_record(rec)
    cells = effective_cells(rec, cells or {}) if legacy else (cells or {})
    keys = list(iter_cell_keys(model))
    oq = open_decisive(model)
    blocked_rules = {q.get('rule_id') for q in oq if q.get('rule_id') and q.get('rule_id') != 'GLOBAL'}
    global_open = [q.get('id') for q in oq if not q.get('rule_id') or q.get('rule_id') == 'GLOBAL']
    approved = [k for k in keys if cell_counts(cells.get(k)) and _rule_of(k) not in blocked_rules]
    blocked = sorted(k for k in keys if (cells.get(k) or {}).get('status') in
                     ('pending_choice', 'pending_legal_review', 'open') or
                     (cell_counts(cells.get(k)) and _rule_of(k) in blocked_rules))
    lang = norm_lang(lang) or model_lang(model)
    bcode = base_code(model)
    n, m = len(approved), len(keys)
    when = by = None
    if m and n == m and not global_open:
        dates = sorted(str(cells[k].get('approved_at') or '')[:10] for k in approved if cells[k].get('approved_at'))
        when = dates[-1] if dates else _dt.date.today().isoformat()
        by = _signed_by(cells, approved)
        code = STATUS_APPROVED
    elif n:
        code = STATUS_PARTIAL
    else:
        code = STATUS_DRAFT
    # נושא מאושר: כל התאים שלו נספרים כמאושרים (התקדמות תור האישור, progress_line). התווית אינה משתנה
    topic_keys = {}
    for k in keys:
        topic_keys.setdefault(_rule_of(k), []).append(k)
    approved_set = set(approved)
    topics_ok = sum(1 for ks in topic_keys.values() if all(k in approved_set for k in ks))
    st = {'playbook_status': code, 'base_code': bcode, 'lang': lang, 'approved_on': when, 'approved_by': by,
          'base_label': LABELS[lang][bcode], 'approved_count': n,
          'positions_count': m, 'approved_topics': topics_ok, 'topics_count': len(topic_keys),
          'approved_keys': approved, 'blocked_keys': blocked,
          'open_questions': [q.get('id') for q in oq], 'agreements_counted': agreements_counted(model),
          'legacy_record': legacy, 'notices': [REUPLOAD_NOTICE] if legacy else []}
    st['label'] = label_for(st, lang)
    return st


def policy_claim(model, cells, rule_id, track, segment=None, wording_fp=None):
    """שער המדיניות: מותר לומר "מדיניות החברה" על התא רק כשהתא נספר כמאושר באותה גזירה.

    wording_fp: טביעת האצבע של הנוסח שהנושא ונותן עומד להחיל (approval_sheet.fingerprint). כשהיא שונה
    מ-approved_fp של התא, הנוסח אינו הנוסח שאושר: policy_claim=False, והסטייה מוצגת למשתמש כ"נדרשת הכרעתך"."""
    key = cell_key(rule_id, track, segment)
    if segment and key not in (cells or {}):
        key = cell_key(rule_id, track)
    cell = (cells or {}).get(key)
    st = derive_status(model, cells)
    ok = key in st['approved_keys']
    reason = None
    if not ok:
        reason = 'open_decisive_question' if cell_counts(cell) else 'not_approved'
    if ok and wording_fp and cell.get('approved_fp') and wording_fp != cell['approved_fp']:
        ok, reason = False, 'wording_differs_from_approved'
    return {'policy_claim': ok, 'key': key, 'reason': reason, 'status_label': st['label'],
            'playbook_status': st['playbook_status']}


def cell_result(cell, record_id=None):
    """התא כפי שנכתב למודל (traffic_light.<track>.ingest_result): אותם ערכים כמו ברשומה."""
    if not cell:
        return None
    out = {k: cell.get(k) for k in ('status', 'policy_claim', 'simulated', 'legal_review_done_by',
                                    'legal_review_done_at', 'approved_at', 'signer')}
    out['counts_as_approved'] = cell_counts(cell)
    if record_id:
        out['record_id'] = record_id
    return out


def _rule_policy_status(rule, cells, st):
    keys = [cell_key(rule['rule_id'], t) for t in TRACKS]
    if all(k in st['approved_keys'] for k in keys):
        return 'Confirmed'
    return rule.get('policy_status_from_evidence') or rule.get('policy_status') or 'Inferred'


def stamp(model, core, index_entry, cells=None, record_id=None):
    """כותב את אותה תוצאה לכל השכבות. הבונה אינו כותב את השדות האלה בשום דרך אחרת."""
    st = derive_status(model, cells)
    holders = [model, core, index_entry]
    if model is not None and isinstance(model.get('handoff'), dict):
        holders.append(model['handoff'])
    for holder in holders:
        if holder is None:
            continue
        for f in DUAL_FIELDS:
            holder.pop(f, None)
        holder['playbook_status'] = st['playbook_status']
        holder[LABEL_FIELD] = st['label']
        holder['approved_count'] = st['approved_count']
        holder['positions_count'] = st['positions_count']
    if model is not None and cells is not None:
        for rule in model.get('rules') or []:
            if 'policy_status_from_evidence' not in rule:
                rule['policy_status_from_evidence'] = rule.get('policy_status') or 'Inferred'
            for t in TRACKS:
                tl = (rule.get('traffic_light') or {}).get(t)
                if isinstance(tl, dict):
                    res = cell_result(cells.get(cell_key(rule['rule_id'], t)), record_id)
                    if res is None:
                        tl.pop('ingest_result', None)
                    else:
                        tl['ingest_result'] = res
            rule['policy_status'] = _rule_policy_status(rule, cells, st)
        if core is not None:
            by_id = {r['rule_id']: r for r in model.get('rules') or []}
            for c in core.get('clauses') or []:
                r = by_id.get(c.get('id') or c.get('rule_id'))
                if r is not None:
                    c['policy_status'] = r['policy_status']
    return st


def surfaces(st):
    """הטקסט שכל משטח מציג. כולם נגזרים מאותו st, ולכן זהים."""
    return {
        'word_header': st['label'],
        'workspace': {'label_now': st['label'], 'approved_count': st['approved_count'],
                      'positions_count': st['positions_count']},
        'chat_first_line': st['label'],
        'gate': st['label'],
        'model': st['label'],
    }


def record_cells_for(model, model_path=None):
    """התאים של רשומת האישור האחרונה שהמודל מפנה אליה (approval_records), כמו ש-policy_gate.py קורא אותם בלי
    --records. בלי רשומה, או כשהקובץ שלה אינו נמצא: {}."""
    entry = _latest_record(model)
    if not entry or not entry.get('record'):
        return {}
    path = entry['record']
    if not os.path.isabs(path):
        if not model_path:
            return {}
        path = os.path.join(os.path.dirname(os.path.abspath(model_path)), path)
    if not os.path.exists(path):
        return {}
    from playbook import ingest_approval as IA   # ייבוא מקומי: ingest_approval מייבא את המודול הזה
    with io.open(path, encoding='utf-8') as fh:
        return IA.record_cells(json.load(fh))


def gate_status(model, model_path=None, lang=None):
    """המעמד והתווית כפי ששער המדיניות (policy_gate.py) מחזיר אותם: derive_status עם התאים של הרשומה האחרונה.
    זו הפונקציה האחת שממנה נכתבת התווית לאינדקס (register_playbook.py) ולגרעין (build_playbook_core.py), ושמולה
    הנושא ונותן בודק את שניהם (check_playbook_contract.py), כדי שהשער, האינדקס והגרעין יאמרו אותה תווית."""
    return derive_status(model, record_cells_for(model, model_path), lang=lang)


def label_gap(model, model_path=None, core=None, index_entry=None):
    """הפער בין התווית של שער המדיניות לבין מה שנשמר בגרעין ובאינדקס (ובמודל). מחזיר dict: label (של השער),
    playbook_status, stored ({שכבה: תווית}) ו-mismatch (רשימת השכבות שאומרות אחרת)."""
    st = gate_status(model, model_path)
    stored = {}
    for name, holder in (('model', model), ('core', core), ('index', index_entry)):
        if isinstance(holder, dict) and holder.get(LABEL_FIELD):
            stored[name] = holder.get(LABEL_FIELD)
    return {'label': st['label'], 'playbook_status': st['playbook_status'], 'stored': stored,
            'mismatch': sorted(k for k, v in stored.items() if v != st['label'])}


def check_consistency(model, core=None, index_entry=None, cells=None, word_path=None, workspace_path=None):
    """מחזיר רשימת סטיות בין הערך המחושב לבין מה שנשמר ומה שמוצג. ריקה = עקבי."""
    st = derive_status(model, cells)
    out = []
    holders = [('model', model), ('core', core), ('index', index_entry)]
    if isinstance(model.get('handoff'), dict):
        holders.append(('handoff', model['handoff']))
    for name, holder in holders:
        if holder is None:
            continue
        for f in DUAL_FIELDS:
            if f in holder:
                out.append('%s.%s: שדה תווית כפול. התווית היחידה היא status_label' % (name, f))
        for field, want in (('playbook_status', st['playbook_status']), (LABEL_FIELD, st['label'])):
            if field in holder and holder.get(field) != want:
                out.append('%s.%s="%s", המחושב: "%s"' % (name, field, holder.get(field), want))
    if cells is not None:
        for rule in model.get('rules') or []:
            for t in TRACKS:
                tl = (rule.get('traffic_light') or {}).get(t) or {}
                key = cell_key(rule['rule_id'], t)
                got, want = tl.get('ingest_result'), cells.get(key)
                if want is None:
                    continue
                if not got or got.get('status') != want.get('status') or \
                        bool(got.get('policy_claim')) != bool(want.get('policy_claim')) or \
                        bool(got.get('simulated')) != bool(want.get('simulated')):
                    out.append('%s: ingest_result במודל אינו התא שברשומה הנוכחית' % key)
            if rule.get('policy_status') != _rule_policy_status(rule, cells, st):
                out.append('%s.policy_status="%s", המחושב: "%s"' % (
                    rule['rule_id'], rule.get('policy_status'), _rule_policy_status(rule, cells, st)))
    for qi in open_decisive(model):
        rid = qi.get('rule_id')
        if rid and any(cell_counts((cells or {}).get(cell_key(rid, t))) for t in TRACKS):
            out.append('%s: שאלה מכריעה פתוחה (%s) בכלל שתאיו נחתמו. הבחירה בגיליון לא נרשמה' % (rid, qi.get('id')))
    if word_path or workspace_path:
        from playbook import surfaces_render as R
        out += R.check_surfaces(st, word_path=word_path, workspace_path=workspace_path, model=model)
    return out
