# -*- coding: utf-8 -*-
"""playbook/surfaces_render.py: המעמד בכל משטח: ה-Word וה-Workspace מופקים מחדש אחרי כל קליטה.

הבעיה: ה-Word וה-Workspace נכתבו
ב-17:18, הקליטה המוצלחת נעשתה ב-17:28, ואף אחד מהם לא הופק מחדש. הכותרת העליונה של ה-Word אמרה
"טעון אישור", ובגוף "0 מתוך 63 עמדות מאושרות" ו-63 פעמים "מעמד העמדה: לא מאושרת"; ה-Workspace אמר
label_now "טעון אישור" ו-approved_count 0; ושם הקובץ אמר "פלייבוק מוצע".
ובנוסף: השורה הראשונה אמרה "10 הסכמים מ-10 גופים" כשנספרו 6 משפחות (ממצא 9 של מנכ"ל ארגון היועמ"שים).

החוזה מול בונה ה-Word: כל טקסט מעמד נכתב בתוך בקר תוכן (w:sdt) עם תגית קבועה:
- areo:status_label  התווית (בכותרת העליונה, בשער, בכל מקום שהתווית מודפסת);
- areo:status_summary  "מעמד העמדות: ..." (פסקה אחת בתמונת המצב);
- areo:cell_status:<rule_id>|<segment>|<track>  "מעמד העמדה: ..." ליד כל מסלול.
add_status_control() הוא העזר שהבונה קורא לו. restamp_docx() מחליף את תוכן הבקרים לפי status.derive_status,
כך שאין צורך לבנות את כל המסמך מחדש כדי לעדכן מעמד. במסמך ישן בלי בקרים, הפונקציה מחליפה
לפי הקידומות הקבועות; וכשמספר שורות "מעמד העמדה" אינו מספר התאים, היא נכשלת (RerenderError): את המסמך
יש לבנות מחדש מהמודל.

ה-Workspace: הנתונים מוזרקים לתבנית כאובייקט JSON אחד (const D = {...}; או /*__DATA__*/{...}).
restamp_workspace() מעדכן את meta: status_label, label_now, status, approved_count, positions_count, ומוחק
presentation_label.

check_surfaces() קורא את שני הקבצים ומשווה למעמד המחושב, וגם בודק שהמספרים בשורת השקיפות תואמים
לספירת מחקר השוק (market_counts).

שתי שפות: כל משטח מוצג בשפה שלו. ה-Word נושא את שפתו במאפייני הקובץ (core.xml, language: he-IL או en-US,
ובהיעדרם bidi במקטע), וה-Workspace ב-meta.lang. restamp ו-check_surfaces ממירים את המעמד לשפת המשטח
(status.in_lang), כך שהתווית זהה במשמעות ובמספרים, בעברית או באנגלית. ב-Word באנגלית כל טקסט מעמד נכתב
בריצה LTR, בלי bidi ובלי rtl ("Position status: ...", "Status of positions: ...").
"""
import io
import json
import os
import re

from docx import Document
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls, qn

try:
    from common import rtl
    from playbook import status as S
    from playbook import market_counts as MC
except ImportError:  # pragma: no cover
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from common import rtl
    from playbook import status as S
    from playbook import market_counts as MC

STATUS_TAG = 'areo:status_label'
SUMMARY_TAG = 'areo:status_summary'
CELL_TAG = 'areo:cell_status:'
SUMMARY_PREFIX = 'מעמד העמדות: '
CELL_PREFIX = 'מעמד העמדה: '
PREFIXES = {'he': {'summary': SUMMARY_PREFIX, 'cell': CELL_PREFIX},
            'en': {'summary': 'Status of positions: ', 'cell': 'Position status: '}}
SUMMARY_PREFIXES = tuple(PREFIXES[g]['summary'].strip() for g in ('he', 'en'))
CELL_PREFIXES = tuple(PREFIXES[g]['cell'].strip() for g in ('he', 'en'))
_PARTIAL_RE = re.compile(r'^(%s); \d+ (?:מתוך|of) \d+ (?:עמדות מאושרות|positions approved)'
                         % '|'.join(re.escape(x) for x in S.BASE_LABELS))
_DATA_MARKERS = (re.compile(r'const\s+D\s*=\s*'), re.compile(r'/\*__DATA__\*/'))

CELL_TEXT = {
    'approved': 'מאושרת, {date}',
    'approved_modified': 'מאושרת בשינוי שהיועץ המשפטי הכניס, {date}',
    'pending_choice': 'ממתינה לבחירה בגיליון ({reason})',
    'pending_legal_review': 'ממתינה לבדיקה משפטית ("נבדק בידי" ותאריך)',
    'open': 'פתוחה ({reason})',
    'not_signed': 'לא מאושרת: העמודה לא נחתמה',
}
CELL_TEXT_EN = {
    'approved': 'approved, {date}',
    'approved_modified': 'approved with a change made by legal counsel, {date}',
    'pending_choice': 'awaiting a choice in the sheet ({reason})',
    'pending_legal_review': 'awaiting legal review ("Reviewed by" and date)',
    'open': 'open ({reason})',
    'not_signed': 'not approved: the column was not signed',
}
CELL_WORDS = {
    'he': {'none': 'מחכה לאישור שלכם', 'simulated': 'לא מאושרת (החתימה נקלטה בסימולציה)',
           'blocked': 'ממתינה להכרעה בשאלה מכריעה פתוחה', 'not_approved': 'לא מאושרת (%s)',
           'missing': 'חסרה דוגמה מההסכמים, או שעורך דין עוד לא עבר עליה', 'summary_all': '%s. כל %d העמדות מאושרות.',
           'summary_part': '%s. %d מתוך %d עמדות מאושרות.'},
    'en': {'none': 'awaiting your approval', 'simulated': 'not approved (the signature was ingested in a simulation)',
           'blocked': 'awaiting a decision on an open decisive question', 'not_approved': 'not approved (%s)',
           'missing': "no example from your agreements, or a lawyer hasn't reviewed it yet", 'summary_all': '%s. All %d positions are approved.',
           'summary_part': '%s. %d of %d positions approved.'},
}
# הסיבות שהקליטה רושמת בתא (ingest_approval) נכתבות בעברית. בתוצר באנגלית הן מוצגות באנגלית; סיבה שאינה
# ברשימה מוחלפת בסיבה הכללית, כדי שלא תדלוף עברית לתוצר אנגלי
REASON_EN = [
    (re.compile(r'^העמודה לא נחתמה$'), 'the column was not signed'),
    (re.compile(r'^השורה (\S+) לא נמצאה בקובץ$'), r'row \1 was not found in the file'),
    (re.compile(r'^תוכן התא נמחק'), 'the cell content was deleted: reject the track, or require other wording?'),
    (re.compile(r'^טעון בדיקה משפטית'), 'legal review required: reviewer name and review date were not recorded'),
    (re.compile(r'^הנחה שלא אושרה בתא'), 'an assumption in the cell was not confirmed'),
    (re.compile(r'^הערת Areo פתוחה בשורה (\S+)'), r'an open Areo comment in row \1'),
    (re.compile(r'^לא נבחרה אפשרות בשאלה (\S+)'), r'no option was chosen in question \1'),
    (re.compile(r'^נבחרה יותר מאפשרות אחת בשאלה (\S+)'), r'more than one option was chosen in question \1'),
    (re.compile(r'^לא נבחרה אפשרות'), 'no option was chosen'),
]
_HEB = re.compile('[\u0590-\u05ff]')


def reason_text(reason, lang='he'):
    """הסיבה שבתא, בשפת המשטח. כמה סיבות מופרדות ב-"; "."""
    if lang != 'en' or not reason or not _HEB.search(reason):
        return reason or ''
    out = []
    for part in [x.strip() for x in reason.split(';') if x.strip()]:
        for rx, en in REASON_EN:
            if rx.search(part):
                part = rx.sub(en, part) if '\\' in en else en
                break
        out.append(part if not _HEB.search(part) else CELL_WORDS['en']['missing'])
    return '; '.join(out)


def surface_lang(st=None, lang=None):
    return S.norm_lang(lang) or (st or {}).get('lang') or 'he'


class RerenderError(RuntimeError):
    """אי אפשר לעדכן את המעמד במסמך הקיים בלי לבנות אותו מחדש מהמודל."""


def _d(iso, lang='he'):
    try:
        return S.fmt_date(iso, lang)
    except (ValueError, TypeError):
        return str(iso or '')


def cell_status_text(cell, st=None, key=None, lang=None):
    """"מעמד העמדה: ..." לתא אחד, מאותה גזירה שהמעמד הכללי נשען עליה. lang: שפת המשטח (ברירת מחדל: של st)."""
    lang = surface_lang(st, lang)
    pre, W = PREFIXES[lang]['cell'], CELL_WORDS[lang]
    if not cell:
        return pre + W['none']
    if cell.get('simulated'):
        return pre + W['simulated']
    s = cell.get('status')
    reason = reason_text(cell.get('reason'), lang)
    if s in S.APPROVED and st is not None and key is not None and key not in st['approved_keys']:
        if S.cell_counts(cell):
            return pre + W['blocked']
        return pre + W['not_approved'] % (reason or W['missing'])
    fmt = (CELL_TEXT_EN if lang == 'en' else CELL_TEXT).get(s, W['none'])
    return pre + fmt.format(date=_d(cell.get('approved_at'), lang), reason=reason)


def summary_text(st, lang=None):
    lang = surface_lang(st, lang)
    st = S.in_lang(st, lang)
    W = CELL_WORDS[lang]
    if st['playbook_status'] == S.STATUS_APPROVED:
        return PREFIXES[lang]['summary'] + W['summary_all'] % (st['label'], st['positions_count'])
    return PREFIXES[lang]['summary'] + W['summary_part'] % (st['label'], st['approved_count'], st['positions_count'])


def status_texts(model, st, cells):
    cells = cells or {}
    return {'label': st['label'], 'summary': summary_text(st),
            'cells': {k: cell_status_text(cells.get(k), st, k) for k in S.iter_cell_keys(model)}}


# ------------------------------------------------------------------ Word
def add_status_control(paragraph, tag, text, size=None, lang='he'):
    """העזר של בונה ה-Word: טקסט מעמד בתוך בקר תוכן עם תגית. בעברית בריצה RTL, באנגלית בריצה LTR."""
    sz = '<w:sz w:val="%d"/><w:szCs w:val="%d"/>' % (size * 2, size * 2) if size else ''
    if lang == 'en':
        fonts, mark = '<w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/>', ''
    else:
        fonts, mark = '<w:rFonts w:ascii="David" w:hAnsi="David" w:cs="David"/>', '<w:rtl/>'
    xml = ('<w:sdt %s><w:sdtPr><w:tag w:val="%s"/></w:sdtPr><w:sdtContent><w:r><w:rPr>'
           '%s%s%s</w:rPr><w:t xml:space="preserve">%s'
           '</w:t></w:r></w:sdtContent></w:sdt>') % (nsdecls('w'), tag, fonts, sz, mark, _xml_escape(text))
    paragraph._p.append(parse_xml(xml))
    if lang == 'en':
        set_paragraph_ltr(paragraph)
    else:
        rtl.set_paragraph_rtl(paragraph)
    return paragraph


# ------------------------------------------------------------------ Word באנגלית: LTR מלא
# common/rtl אוכף RTL; מסמך באנגלית צריך את ההפך, בלי שום שארית של bidi או rtl (language-policy.md: "en: LTR,
# בלי אכיפת RTL"). העזרים כאן משמשים את גיליון העמדות, את בונה הפלייבוק ואת restamp_docx.
def _ltr_el(el):
    """מסיר w:bidi מפסקה, w:rtl מריצה, w:bidiVisual מטבלה, ו-bidi ו-rtlGutter ממקטע."""
    for tag in ('w:bidi', 'w:rtl', 'w:bidiVisual', 'w:rtlGutter'):
        for x in el.iter(qn(tag)):
            x.getparent().remove(x)


def set_paragraph_ltr(paragraph):
    _ltr_el(paragraph._p)
    return paragraph


def is_ltr_doc(doc):
    """True כשהמסמך באנגלית: language במאפייני הקובץ, ובהיעדרו מקטע בלי bidi."""
    lang = (doc.core_properties.language or '').lower()
    if lang:
        return lang.startswith('en')
    sect = doc.element.body.find(qn('w:sectPr'))
    return sect is not None and sect.find(qn('w:bidi')) is None


def doc_lang(doc):
    return 'en' if is_ltr_doc(doc) else 'he'


def enforce_ltr_document(doc, author='', title=None, language='en-US'):
    """המקבילה של rtl.enforce_document למסמך באנגלית: אין bidi, rtl, bidiVisual או rtlGutter בשום מקום (גוף,
    טבלאות, כותרות, הערות), סגנון Normal בלי rtl, ומאפייני קובץ נקיים עם language=en-US."""
    roots = [doc.element.body]
    for sec in doc.sections:
        for hf in (sec.header, sec.footer):
            roots.append(hf._element)
    try:
        roots.append(doc.part._comments_part.element)
    except Exception:  # pragma: no cover  אין הערות
        pass
    for root in roots:
        _ltr_el(root)
        keep_hebrew_rtl(root)
    _ltr_el(doc.styles.element)
    rtl.clean_metadata(doc, author=author, title=title)
    doc.core_properties.language = language
    return doc


_HEB_RE = re.compile('[֐-׿]')


def hebrew_dominant(text):
    """True כשיש בטקסט לפחות כמו אותיות עבריות כמו אותיות לטיניות: פסקה כזו RTL. פסקה לטינית עם מילה עברית אחת
    ("Company's side: הלקוח") נשארת LTR, והמילה העברית בה היא ריצת rtl."""
    heb = len(_HEB_RE.findall(text))
    return heb > 0 and heb >= len(re.findall('[A-Za-z]', text))


def keep_hebrew_rtl(root):
    """בתוך מסמך באנגלית, פסקה שיש בה עברית (ציטוט מקור, שם נושא, נימוק שנכתב בעברית) נשארת RTL: bidi בפסקה ו-rtl
    בכל ריצה עם אות עברית. בלי זה Word מציג אותה משמאל לימין, עם הפיסוק והמספרים במקום הלא נכון. פסקה בלי עברית
    נשארת LTR כמו שהיא. מחזיר את מספר הפסקאות העבריות."""
    n = 0
    for p in root.iter(qn('w:p')):
        text = _p_text(p)
        if not _HEB_RE.search(text):
            continue
        n += 1
        if hebrew_dominant(text):
            rtl._ppr_rtl(p)
        for r in p.iter(qn('w:r')):
            if _HEB_RE.search(''.join(t.text or '' for t in r.iter(qn('w:t')))):
                rtl._rpr_rtl(r)
    return n


def _xml_escape(s):
    return (s or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def _p_text(p_el):
    return ''.join(t.text or '' for t in p_el.iter(qn('w:t')))


def _set_runs_text(container_el, text):
    """שם text בריצה הראשונה שבמכל, ומרוקן את שאר הריצות. העיצוב של הריצה הראשונה נשמר."""
    ts = list(container_el.iter(qn('w:t')))
    if not ts:
        return False
    ts[0].text = text
    ts[0].set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    for t in ts[1:]:
        t.text = ''
    return True


def _roots(doc):
    roots = [doc.element.body]
    for sec in doc.sections:
        for hf in (sec.header, sec.footer, sec.first_page_header, sec.even_page_header):
            try:
                if not hf.is_linked_to_previous or hf is sec.header:
                    roots.append(hf._element)
            except Exception:  # pragma: no cover
                pass
    seen, out = set(), []
    for r in roots:
        if id(r) not in seen:
            seen.add(id(r))
            out.append(r)
    return out


def _is_label(text):
    t = text.strip()
    return t in S.BASE_LABELS or t.startswith(S.APPROVED_PREFIXES) or bool(_PARTIAL_RE.match(t))


FILE_WORDS = {
    'he': {S.STATUS_DRAFT: 'פלייבוק מוצע', S.STATUS_PARTIAL: 'פלייבוק מאושר בחלקו',
           S.STATUS_APPROVED: 'מדיניות מאושרת'},
    'en': {S.STATUS_DRAFT: 'Proposed playbook', S.STATUS_PARTIAL: 'Partially approved playbook',
           S.STATUS_APPROVED: 'Approved policy'},
}


def surface_filename(path, st):
    """שם הקובץ אומר את המעמד: "פלייבוק מוצע" כל עוד לא אושר, "מדיניות מאושרת" כשאושר. באנגלית: "Proposed
    playbook", "Partially approved playbook", "Approved policy". המילים מוחלפות בשפה שבה הן כתובות בשם."""
    d, base = os.path.split(path)
    for words in FILE_WORDS.values():
        want = words[st['playbook_status']]
        for w in words.values():
            if w in base:
                return os.path.join(d, base.replace(w, want))
    return path


def restamp_docx(src, model, st, cells, dst=None):
    """מעדכן כל טקסט מעמד ב-Word. מחזיר (נתיב חדש, ספירת החלפות)."""
    doc = Document(src)
    lang = doc_lang(doc)
    st = S.in_lang(st, lang)       # כל משטח בשפה שלו
    texts = status_texts(model, st, cells)
    done = {'label': 0, 'summary': 0, 'cells': 0}
    tagged = set()
    for root in _roots(doc):
        for sdt in root.iter(qn('w:sdt')):
            tag_el = sdt.find(qn('w:sdtPr') + '/' + qn('w:tag'))
            tag = tag_el.get(qn('w:val')) if tag_el is not None else ''
            content = sdt.find(qn('w:sdtContent'))
            if content is None:
                continue
            if tag == STATUS_TAG:
                _set_runs_text(content, texts['label'])
                done['label'] += 1
            elif tag == SUMMARY_TAG:
                _set_runs_text(content, texts['summary'])
                done['summary'] += 1
            elif tag.startswith(CELL_TAG) and tag[len(CELL_TAG):] in texts['cells']:
                _set_runs_text(content, texts['cells'][tag[len(CELL_TAG):]])
                done['cells'] += 1
            else:
                continue
            tagged.add(content)
    legacy_cells = []
    old_labels = [x for x in S.BASE_LABELS]
    for root in _roots(doc):
        for p in root.iter(qn('w:p')):
            if any(a in tagged for a in p.iterancestors()) or \
                    any(c in tagged for c in p.iter(qn('w:sdtContent'))):
                continue
            text = _p_text(p)
            s = text.strip()
            if not s:
                continue
            if _is_label(s):
                _set_runs_text(p, texts['label'])
                done['label'] += 1
            elif s.startswith(SUMMARY_PREFIXES):
                _set_runs_text(p, texts['summary'])
                done['summary'] += 1
            elif s.startswith(CELL_PREFIXES):
                legacy_cells.append(p)
            else:
                for r in p.iter(qn('w:t')):
                    for old in old_labels:
                        if r.text and old in r.text and old != texts['label'] and not \
                                texts['label'].startswith(old):
                            r.text = r.text.replace(old, texts['label'])
                            done['label'] += 1
    if legacy_cells:
        keys = list(S.iter_cell_keys(model))
        if len(legacy_cells) != len(keys):
            raise RerenderError('במסמך %d שורות "מעמד העמדה" ובפלייבוק %d תאים: יש לבנות את ה-Word מחדש מהמודל'
                                % (len(legacy_cells), len(keys)))
        for p, k in zip(legacy_cells, keys):
            _set_runs_text(p, texts['cells'][k])
            done['cells'] += 1
    if lang == 'en':
        for root in _roots(doc):
            _ltr_el(root)
    else:
        for root in _roots(doc):
            for p in root.iter(qn('w:p')):
                for r in p.iter(qn('w:r')):
                    rtl._rpr_rtl(r)
    rtl.clean_metadata(doc, author=doc.core_properties.author or '', title=doc.core_properties.title)
    doc.core_properties.language = 'en-US' if lang == 'en' else 'he-IL'
    out = dst or surface_filename(src, st)
    doc.save(out)
    if os.path.abspath(out) != os.path.abspath(src) and dst is None and os.path.exists(src):
        os.remove(src)
    return out, done


def read_docx_status(path):
    """{'header': [...], 'labels': [...], 'summary': [...], 'cells': {...}, 'text': ...} מתוך Word שמור."""
    doc = Document(path)
    out = {'header': [], 'labels': [], 'summary': [], 'cells': {}, 'cell_lines': [], 'text': '',
           'lang': doc_lang(doc)}
    texts = []
    for i, root in enumerate(_roots(doc)):
        for sdt in root.iter(qn('w:sdt')):
            tag_el = sdt.find(qn('w:sdtPr') + '/' + qn('w:tag'))
            tag = tag_el.get(qn('w:val')) if tag_el is not None else ''
            val = ''.join(t.text or '' for t in sdt.iter(qn('w:t'))).strip()
            if tag.startswith(CELL_TAG):
                out['cells'][tag[len(CELL_TAG):]] = val
        for p in root.iter(qn('w:p')):
            s = _p_text(p).strip()
            if not s:
                continue
            texts.append(s)
            if _is_label(s):
                out['labels'].append(s)
                if i > 0:
                    out['header'].append(s)
            elif s.startswith(SUMMARY_PREFIXES):
                out['summary'].append(s)
            elif s.startswith(CELL_PREFIXES):
                out['cell_lines'].append(s)
    out['text'] = '\n'.join(texts)
    return out


# ------------------------------------------------------------------ Workspace
def _find_payload(html):
    for rx in _DATA_MARKERS:
        m = rx.search(html)
        if not m:
            continue
        start = m.end()
        if html[start:start + 4] == 'null':
            continue
        obj, end = json.JSONDecoder().raw_decode(html, start)
        return obj, start, end
    raise RerenderError('לא נמצאו נתוני הדף (const D = {...} או /*__DATA__*/) ב-Workspace')


def restamp_workspace(src, st, dst=None):
    """מעדכן את המעמד בנתוני הדף. מחזיר את הנתיב."""
    with io.open(src, encoding='utf-8') as fh:
        html = fh.read()
    data, start, end = _find_payload(html)
    meta = data.setdefault('meta', {})
    st = S.in_lang(st, meta.get('lang'))      # התווית בשפת הדף
    for f in S.DUAL_FIELDS:
        meta.pop(f, None)
    old_status = meta.get('status')
    meta.update({'status_label': st['label'], 'label_now': st['label'], 'status': st['label'],
                 'playbook_status': st['playbook_status'], 'approved_count': st['approved_count'],
                 'positions_count': st['positions_count']})
    if 'labels' in meta:   # התווית בשתי השפות (build_workspace_payload.py), מאותה גזירה
        meta['labels'] = {g: S.label_for(st, g) for g in ('he', 'en')}
    for k in ('evidence_disclaimer',):
        v = meta.get(k)
        if isinstance(v, str):
            for old in [x for x in S.BASE_LABELS + ((old_status,) if old_status else ()) if x]:
                if old in v and old != st['label']:
                    v = v.replace(old, st['label'])
            meta[k] = v
    blob = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    html = html[:start] + blob + html[end:]
    out = dst or src
    with io.open(out, 'w', encoding='utf-8', newline='') as fh:
        fh.write(html)
    return out


def read_workspace_status(path):
    with io.open(path, encoding='utf-8') as fh:
        html = fh.read()
    data, _, _ = _find_payload(html)
    return data


# ------------------------------------------------------------------ בדיקה
def check_surfaces(st, word_path=None, workspace_path=None, model=None):
    """סטיות בין המעמד המחושב לבין מה שה-Word וה-Workspace מציגים. ריקה = עקבי."""
    out = []
    st0 = st
    if word_path:
        w = read_docx_status(word_path)
        st = S.in_lang(st0, w['lang'])    # ה-Word מושווה למעמד בשפה שלו
        stale = [x for x in S.BASE_LABELS if not st['label'].startswith(x)]
        if not w['header']:
            out.append('Word: אין תווית בכותרת העליונה')
        for h in w['header']:
            if h != st['label']:
                out.append('Word: הכותרת העליונה "%s", המחושב: "%s"' % (h, st['label']))
        for lbl in w['labels']:
            if lbl != st['label']:
                out.append('Word: תווית "%s" בגוף המסמך, המחושב: "%s"' % (lbl, st['label']))
        for s in w['summary']:
            if s != summary_text(st):
                out.append('Word: "%s" אינו המעמד המחושב' % s[:80])
        for old in stale:
            if old in w['text']:
                out.append('Word: נשארה התווית הישנה "%s"' % old)
        if st['playbook_status'] != S.STATUS_DRAFT and ('נקלט בסימולציה' in w['text'] or
                                                       'ingested in a simulation' in w['text']) and not any(
                'סימולציה' in v or 'simulation' in v for v in w['cells'].values()):
            out.append('Word: נשאר משפט על קליטה בסימולציה')
        if model is not None:
            out += ['Word: ' + p for p in MC.count_claims(w['text'], model)]
    if workspace_path:
        data = read_workspace_status(workspace_path)
        meta = data.get('meta') or {}
        st = S.in_lang(st0, meta.get('lang'))
        for f in S.DUAL_FIELDS:
            if f in meta:
                out.append('Workspace: meta.%s: שדה תווית כפול' % f)
        if meta.get('label_now') != st['label']:
            out.append('Workspace: label_now="%s", המחושב: "%s"' % (meta.get('label_now'), st['label']))
        if meta.get('approved_count') != st['approved_count']:
            out.append('Workspace: approved_count=%s, המחושב: %d' % (meta.get('approved_count'), st['approved_count']))
        if model is not None:
            out += ['Workspace: ' + p for p in MC.count_claims(meta.get('evidence_disclaimer') or '', model)]
    return out
