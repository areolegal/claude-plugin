# -*- coding: utf-8 -*-
"""playbook/approval_sheet.py: גיליון "עמדות משא ומתן לאישור" שהיועץ המשפטי חותם עליו לפי עמודה.

הבעיה (סבב 2): היועצת חתמה על תקציר עמדה, ולא על הנוסח שנכנס להסכם; לא ראתה מה כל עמדה מטילה
על החברה כמקבלת; לא ראתה "הצעת Areo", "טעון בדיקה משפטית" ו"לא אומת"; החשיבות והבסיס הוצגו
באנגלית; והגיליון נקרא "מאושרות" עוד לפני החתימה.

הבעיה (סבב 3, הערות 5.5):
- ב-6 מתוך 10 התאים שנשענים על שלושה מקורות שוק הודפס גם "3 מקורות שוק" וגם "לא אומת: 1 מקורות":
  ממצא לא מאומת של נקודה אחרת באותו כלל הודבק לכל שלושת המסלולים (שינוי 78).
- היועצת חתמה על נוסח ירוק שנכשל בבדיקות הפערים שהנושא ונותן מריץ (שינוי 80).
- עמודת האדום נקראה "לא נחתום" בכל השורות, אף שרק כלל אחד שובר עסקה; והנוסח באדום הוצג
  כ"הנוסח שיוחל" (שינוי 81).
- "טעון בדיקה משפטית" הודבק לשורת "נבדק בידי", ו"נבדק בידי" נרשם בלי תאריך (שינוי 81).
- טבלת "סמכויות והסלמה" יוצאת מהגיליון: אין שרשרת אישורים (החלטה מחייבת מ-14.10.2026, שינוי 76).
  החתימה של היועץ המשפטי על הפלייבוק המוצע נשארת.
- נוסח אנגלי הודפס בתוך ריצה RTL אחת עם הקידומת העברית: כל שורה מפוצלת לפי כתב, והקטע הלטיני
  נשאר LTR (w:rtl w:val="0").

מה הגיליון מציג בכל תא (ירוק, צהוב, אדום), בסדר קבוע:
1. העמדה (משפט אחד, מודגש).
2. בירוק ובצהוב: "הנוסח שיוחל, מילה במילה:" ואחריו הנוסח שהנושא ונותן מכניס להסכם (ירוק:
   proposed_clause; צהוב: fallback_wording.text, ואם אין, proposed_clause). באדום: "הנוסח שנשיב כשהצד
   השני מציע זאת (נוסח ריפוי), מילה במילה:". טביעת האצבע (fp) מחושבת על העמדה, הנוסח ושורות ההשפעה.
3. מה העמדה מטילה על החברה בכל תפקיד שיש לה בהסכם, בכל סוג הסכם: "כשהחברה <התפקיד>:" לכל תפקיד
   (scope_summary.company_roles[], למשל מגלה ומקבל, קונה ומוכר, משכיר ושוכר), או שורה אחת, "מה זה מטיל על
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
"""
import hashlib
import os
import re
import unicodedata
import uuid

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Cm, Pt

try:
    from common import rtl
except ImportError:  # pragma: no cover  הרצה מתוך playbook\
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from common import rtl

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
}

SINGLE_ROLE_LABEL = 'מה זה מטיל על החברה: '
ROLE_LINE = 'כשהחברה {label}: '
_EFFECT_FIELD = re.compile(r'^as_(\w+)_effect$')


def company_roles(model):
    """[(role, label)]: התפקידים שיש לחברה בהסכם. כללי לכל סוג הסכם.

    מקור ראשון: scope_summary.company_roles[] = [{role, label}] (למשל מגלה ומקבל, קונה ומוכר, מעניק רישיון
    ומקבל רישיון, משכיר ושוכר). בלי הרשימה, כשהחברה בכמה תפקידים (company_role_code: mutual), התפקידים
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


def role_effect(t, role):
    """שורת ההשפעה של תפקיד אחד: role_effects[role], או השדה as_<role>_effect; בתפקיד יחיד גם company_effect."""
    v = (t.get('role_effects') or {}).get(role) or t.get('as_%s_effect' % role)
    if not v and role == 'company':
        v = t.get('company_effect') or next((t[k] for k in sorted(t) if _EFFECT_FIELD.match(k) and t[k]), '')
    return (v or '').strip()


def role_lines(model):
    """[(role, הקידומת בגיליון)]."""
    roles = company_roles(model)
    if len(roles) == 1:
        return [(roles[0][0], SINGLE_ROLE_LABEL)]
    return [(r, ROLE_LINE.format(label=lbl)) for r, lbl in roles]


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


def legal_review_tracks(rule):
    lr = rule.get('legal_review_required')
    if lr is True:
        return set(TRACKS)
    if isinstance(lr, list):
        return {x.get('track') for x in lr if isinstance(x, dict)} | {x for x in lr if isinstance(x, str)}
    return set(rule.get('legal_review_tracks') or [])


# ------------------------------------------------------------------ סימונים
def count_he(n, noun='מקורות', one='מקור אחד', none='לא נמצאו מקורות'):
    """התאמה דקדוקית: "מקור אחד", "2 מקורות", "לא נמצאו מקורות". לעולם לא "1 מקורות"."""
    n = int(n or 0)
    if n == 0:
        return none
    if n == 1:
        return one
    return '%d %s' % (n, noun)


def unverified_label(n, ids, reason):
    """התבנית האחת לממצא שוק שלא אומת (localization-he.md, החלפה 77.5)."""
    ids = [i for i in (ids or []) if i]
    reason = re.sub(r'(?<!\d)1 מקורות', 'מקור אחד', (reason or 'הסיבה לא נרשמה').strip())
    return HE['unverified'].format(count=count_he(n), ids=(' (%s)' % ', '.join(ids)) if ids else '', reason=reason)


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


def _finding_label(u):
    ids = u.get('source_ids') or []
    n = u.get('sources_found', len(ids))
    if isinstance(n, (list, tuple)):
        ids, n = ids or list(n), len(n)
    if u.get('label') and not n and not ids and 'לא נבדק' in u['label']:
        return u.get('reason') or u['label']
    return unverified_label(n, ids, u.get('reason'))


def evidence_flag(track, t):
    """סימון הראיה האחד של התא, מה-basis ומספר המקורות. None כשאין."""
    basis = t.get('basis')
    if basis == 'areo_proposal':
        return HE['areo']
    if basis == 'market_standard':
        ids = market_ids(t)
        if len(ids) >= MIN_MARKET_SOURCES:
            return HE['market'].format(n=len(ids), ids=', '.join(ids))
        return unverified_label(len(ids), ids, t.get('verification_reason') or 'פחות משלושה מקורות לנקודה')
    if basis == 'statute':
        return HE['statute'].format(ids=', '.join(t.get('legal_source_ids') or t.get('source_ids') or []))
    if basis:
        return HE['company'].format(n=len(t.get('evidence') or []))
    return None


def flags_for(rule, track, t, index=None):
    """סימונים בעברית לתא. index: התוצאה של unverified_index(model), או None.

    סימון ראיה אחד (evidence_flag). "ממצא לא מאומת" מתווסף רק כשהממצא שייך לנקודה של המסלול הזה, ולעולם
    לא לתא שיש לו שלושה מקורות שוק לאותה נקודה. "טעון בדיקה משפטית" אינו כאן: הוא שורה נפרדת בתא."""
    out = []
    ev = evidence_flag(track, t)
    if ev:
        out.append(ev)
    verified_market = t.get('basis') == 'market_standard' and len(market_ids(t)) >= MIN_MARKET_SOURCES
    by_cell = (index or ({}, {}))[0]
    if not verified_market:
        for u in by_cell.get((rule['rule_id'], track)) or []:
            out.append(_finding_label(u))
        if t.get('verification') == 'not_verified':
            out.append(unverified_label(t.get('sources_found', 0), t.get('source_ids') or [],
                                        t.get('verification_reason')))
    seen, uniq = set(), []
    for f in out:
        if f not in seen:
            seen.add(f)
            uniq.append(f)
    return uniq


# ------------------------------------------------------------------ כתיבה ל-Word
def _checkbox(paragraph, tag):
    xml = ('<w:sdt %s xmlns:w14="%s"><w:sdtPr><w:tag w:val="%s"/><w14:checkbox><w14:checked w14:val="0"/>'
           '<w14:checkedState w14:val="2612" w14:font="MS Gothic"/><w14:uncheckedState w14:val="2610" '
           'w14:font="MS Gothic"/></w14:checkbox></w:sdtPr><w:sdtContent><w:r><w:rPr><w:rtl/></w:rPr>'
           '<w:t>☐</w:t></w:r></w:sdtContent></w:sdt>') % (nsdecls('w'), W14, tag)
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


def add_mixed_runs(paragraph, text, bold=False, size=9):
    """כותב טקסט מעורב: ריצה עברית עם rtl, וקטע לטיני בריצה נפרדת עם rtl=0. הטקסט עצמו אינו משתנה."""
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


def _cell_lines(cell, lines):
    """lines: [(text, bold)] לתא. הפסקה הראשונה של התא משמשת לשורה הראשונה."""
    first = not cell.paragraphs[0].runs
    paras = []
    for text, bold in lines:
        p = cell.paragraphs[0] if first else cell.add_paragraph()
        first = False
        add_mixed_runs(p, text, bold=bold, size=9)
        paras.append(p)
    return paras


def _check_hebrew_only(text):
    for word in ('market_built', 'own_plus_market', 'critical', 'areo_proposal', 'market_standard', 'Inferred'):
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


def opening_text(model, counts):
    parts = []
    if counts['market']:
        parts.append('%d עמדות נגזרו ממקורות שוק ציבוריים, שלושה מקורות לפחות לכל עמדה' % counts['market'])
    if counts.get('unverified'):
        parts.append('%d עמדות נשענות על פחות משלושה מקורות שוק, ומסומנות "ממצא לא מאומת"' % counts['unverified'])
    if counts['areo']:
        parts.append('%d עמדות נוסחו בידי Areo בלי נקודת שוק' % counts['areo'])
    if counts['company']:
        parts.append('%d עמדות נגזרו מהסכמי החברה' % counts['company'])
    if counts['statute']:
        parts.append('%d עמדות הן חובה בדין' % counts['statute'])
    walks = [r['rule_id'] for r in model.get('rules') or [] if r.get('walk_away') is True]
    n_rules = len(model.get('rules') or [])
    if walks:
        parts.append('שוברי עסקה: %s (%s); בשאר %d הכללים האדום הוא מה שלא מקבלים כמות שהוא, ומשיבים '
                     'עליו בנוסח הריפוי' % (count_he(len(walks), 'כללים', 'כלל אחד', 'אין'), ', '.join(walks),
                                           n_rules - len(walks)))
    else:
        parts.append('אין שובר עסקה; בכל הכללים האדום הוא מה שלא מקבלים כמות שהוא, ומשיבים עליו בנוסח הריפוי')
    return 'אני מאמץ/ת את העמדות שבמסמך כמדיניות החברה. ' + '; '.join(parts) + '.'


def _wording_gate(model):
    """בדיקות הפערים על כל נוסח לפני ההפקה. ייבוא מאוחר, כדי ש-validate_model ייבא את המודול הזה."""
    from playbook import validate_model as V
    hits = V.wording_findings(model)
    if hits:
        lines = ['%s %s: %s' % (h['rule_id'], h.get('track') or '', h['message']) for h in hits[:20]]
        raise SheetError('נוסח שנכשל בבדיקות הפערים (כלל 2.22). הגיליון אינו מופק עד שהנוסח יתוקן:\n'
                         + '\n'.join(lines))


def build_sheet(model, out_dir, company='', lang='he', token_uid=None, check_wording=True):
    """מפיק את הגיליון ואת המניפסט. מחזיר (נתיב ה-docx, manifest dict)."""
    T = HE
    if check_wording:
        _wording_gate(model)
    roles = role_lines(model)
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
    rtl.add_paragraph(doc, T['title'], bold=True, size=16)
    if company:
        add_mixed_runs(doc.add_paragraph(), company, size=10)

    counts = basis_counts(model)
    manifest = {'token': token, 'uid': uid, 'family_id': fid, 'lang': lang, 'rows': {}, 'cells': {},
                'counts': counts, 'questions': {}}
    p = doc.add_paragraph()
    _checkbox(p, 'chk:open:Q-00')
    add_mixed_runs(p, ' ' + opening_text(model, counts), size=10)

    table = doc.add_table(rows=1, cols=4)
    table.style = 'Table Grid'
    for i, h in enumerate(T['cols']):
        _cell_lines(table.rows[0].cells[i], [(h, True)])
    open_q = {}
    for qi in model.get('validation_queue') or []:
        if qi.get('rule_id') and not qi.get('answered') and (qi.get('status') or 'open') == 'open':
            open_q.setdefault(qi['rule_id'], []).append(qi)

    for rule in model.get('rules') or []:
        rid = rule['rule_id']
        code = rid
        cells = table.add_row().cells
        imp = T['importance'].get(str(rule.get('importance') or '').lower(), '')
        head = [(code, True), (rule.get('topic_name') or '', True), ('חשיבות: ' + imp, False)]
        if rule.get('walk_away') is True:
            head.append((T['walk_away'], True))
        for u in index[1].get(rid) or []:
            head.append((T['topic_unverified'] + _finding_label(u), False))
        for text, _ in head:
            _check_hebrew_only(text)
        _cell_lines(cells[0], head)
        row_meta = {'rule_id': rid, 'segment': None, 'choices': [], 'comment': False, 'questions': []}
        for qi in open_q.get(rid, []):
            qid = qi.get('id') or qi.get('queue_id') or 'Q'
            qlines = [(T['choice_head'] + (qi.get('question') or ''), True)]
            if qi.get('recommendation'):
                qlines.append((T['recommendation'] + qi['recommendation'], False))
            qhead = _cell_lines(cells[0], qlines)[0]
            options = []
            for n, opt in enumerate(qi.get('options') or []):
                cp = cells[0].add_paragraph()
                tag = 'chk:choice:%s:%s:%d' % (rid, qid, n)
                _checkbox(cp, tag)
                add_mixed_runs(cp, ' ' + opt, size=9)
                row_meta['choices'].append(tag)
                options.append({'tag': tag, 'index': n, 'text': opt})
            cm = doc.add_comment(qhead.runs[0], text=T['choice_head'] + (qi.get('question') or ''),
                                 author=AREO_AUTHOR, initials='AR')
            cm.add_paragraph(T['comment_tail'])
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
                val = role_effect(t, role)
                if not val:
                    raise SheetError('%s %s: חסרה שורת ההשפעה של התפקיד %s. כל תא מציג מה העמדה מטילה על '
                                     'החברה בכל תפקיד שיש לה בהסכם.' % (rid, track, role))
                effects[role] = val
            flags = flags_for(rule, track, t, index)
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
                _check_hebrew_only(text)
            _cell_lines(cells[1 + i], lines)
            assumptions = []
            for n, a in enumerate(t.get('assumptions') or []):
                ap = cells[1 + i].add_paragraph()
                tag = 'chk:assume:%s:%s:%d' % (rid, track, n)
                _checkbox(ap, tag)
                add_mixed_runs(ap, ' ' + T['assume'] + a, size=9)
                assumptions.append({'tag': tag, 'text': a})
            fp_parts = [position, wording] + [effects[r] for r, _ in roles]
            manifest['cells'][cell_key(rid, track)] = {
                'row': code, 'col': 1 + i, 'fp': fingerprint(fp_parts), 'position': position, 'wording': wording,
                'effects': effects, 'flags': flags, 'legal_review': legal,
                'assumptions': [a['tag'] for a in assumptions], 'assumption_texts': assumptions}
    rtl.set_table_rtl(table)

    rtl.add_paragraph(doc, T['sign_head'], bold=True, size=11)
    sign = doc.add_table(rows=1, cols=5)
    sign.style = 'Table Grid'
    for i, h in enumerate(T['sign_cols']):
        _cell_lines(sign.rows[0].cells[i], [(h, True)])
    for track in ('red', 'yellow', 'green'):
        cells = sign.add_row().cells
        _cell_lines(cells[0], [(T['track_label'][track], True)])
        _checkbox(cells[1].paragraphs[0], 'chk:sign:%s' % track)
    rtl.set_table_rtl(sign)

    p = doc.add_paragraph()
    _checkbox(p, 'chk:final')
    rtl.set_run_rtl(p.add_run(' ' + T['final']), size=11)
    rtl.set_paragraph_rtl(p)
    add_mixed_runs(doc.add_paragraph(), T['token'].format(token=token), size=7)

    settings = doc.settings.element
    if settings.find(qn('w:trackRevisions')) is None:
        settings.insert(0, OxmlElement('w:trackRevisions'))
    rtl.enforce_document(doc, author=company, title=T['title'])   # אינו נוגע בריצה שסומנה LTR מפורש
    doc.core_properties.identifier = token
    fam_label = re.sub(r'[\\/:*?"<>|]+', '-', model.get('family_label') or fid)[:40]
    name = '%s-%s-v1.docx' % (T['file'], fam_label)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, name)
    doc.save(path)
    with open(path, 'rb') as fh:
        manifest['issued_sha256'] = hashlib.sha256(fh.read()).hexdigest()
    return path, manifest
