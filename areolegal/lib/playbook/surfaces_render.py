# -*- coding: utf-8 -*-
"""playbook/surfaces_render.py: המעמד בכל משטח: ה-Word וה-Workspace מופקים מחדש אחרי כל קליטה.

הבעיה (סבב 3, ממצא 2 של המהנדס, 3 של מנכ"ל ארגון היועמ"שים, 5 של השותף): ה-Word וה-Workspace נכתבו
ב-17:18, הקליטה המוצלחת נעשתה ב-17:28, ואף אחד מהם לא הופק מחדש. הכותרת העליונה של ה-Word אמרה
"טעון אישור", ובגוף "0 מתוך 63 עמדות מאושרות" ו-63 פעמים "מעמד העמדה: לא מאושרת"; ה-Workspace אמר
label_now "טעון אישור" ו-approved_count 0; ושם הקובץ אמר "פלייבוק מוצע".
ובנוסף: השורה הראשונה אמרה "10 הסכמים מ-10 גופים" כשנספרו 6 משפחות (ממצא 9 של מנכ"ל ארגון היועמ"שים).

החוזה מול בונה ה-Word: כל טקסט מעמד נכתב בתוך בקר תוכן (w:sdt) עם תגית קבועה:
- areo:status_label  התווית (בכותרת העליונה, בשער, בכל מקום שהתווית מודפסת);
- areo:status_summary  "מעמד העמדות: ..." (פסקה אחת בתמונת המצב);
- areo:cell_status:<rule_id>|<segment>|<track>  "מעמד העמדה: ..." ליד כל מסלול.
add_status_control() הוא העזר שהבונה קורא לו. restamp_docx() מחליף את תוכן הבקרים לפי status.derive_status,
כך שאין צורך לבנות את כל המסמך מחדש כדי לעדכן מעמד. במסמך ישן בלי בקרים (כמו של סבב 3), הפונקציה מחליפה
לפי הקידומות הקבועות; וכשמספר שורות "מעמד העמדה" אינו מספר התאים, היא נכשלת (RerenderError): את המסמך
יש לבנות מחדש מהמודל.

ה-Workspace: הנתונים מוזרקים לתבנית כאובייקט JSON אחד (const D = {...}; או /*__DATA__*/{...}).
restamp_workspace() מעדכן את meta: status_label, label_now, status, approved_count, positions_count, ומוחק
presentation_label.

check_surfaces() קורא את שני הקבצים ומשווה למעמד המחושב, וגם בודק שהמספרים בשורת השקיפות תואמים
לספירת מחקר השוק (market_counts).
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
_PARTIAL_RE = re.compile(r'^(%s); \d+ מתוך \d+ עמדות מאושרות' % '|'.join(re.escape(x) for x in S.BASE_LABELS))
_DATA_MARKERS = (re.compile(r'const\s+D\s*=\s*'), re.compile(r'/\*__DATA__\*/'))

CELL_TEXT = {
    'approved': 'מאושרת, {date}',
    'approved_modified': 'מאושרת בשינוי שהיועץ המשפטי הכניס, {date}',
    'pending_choice': 'ממתינה לבחירה בגיליון ({reason})',
    'pending_legal_review': 'ממתינה לבדיקה משפטית ("נבדק בידי" ותאריך)',
    'open': 'פתוחה ({reason})',
    'not_signed': 'לא מאושרת: העמודה לא נחתמה',
}


class RerenderError(RuntimeError):
    """אי אפשר לעדכן את המעמד במסמך הקיים בלי לבנות אותו מחדש מהמודל."""


def _d(iso):
    try:
        return S._he_date(iso)
    except (ValueError, TypeError):
        return str(iso or '')


def cell_status_text(cell, st=None, key=None):
    """"מעמד העמדה: ..." לתא אחד, מאותה גזירה שהמעמד הכללי נשען עליה."""
    if not cell:
        return CELL_PREFIX + 'טעונה אישור'
    if cell.get('simulated'):
        return CELL_PREFIX + 'לא מאושרת (החתימה נקלטה בסימולציה)'
    s = cell.get('status')
    if s in S.APPROVED and st is not None and key is not None and key not in st['approved_keys']:
        if S.cell_counts(cell):
            return CELL_PREFIX + 'ממתינה להכרעה בשאלה מכריעה פתוחה'
        return CELL_PREFIX + 'לא מאושרת (%s)' % (cell.get('reason') or 'חסרה ראיה או בדיקה משפטית')
    fmt = CELL_TEXT.get(s, 'טעונה אישור')
    return CELL_PREFIX + fmt.format(date=_d(cell.get('approved_at')), reason=cell.get('reason') or '')


def summary_text(st):
    if st['playbook_status'] == S.STATUS_APPROVED:
        return SUMMARY_PREFIX + '%s. כל %d העמדות מאושרות.' % (st['label'], st['positions_count'])
    return SUMMARY_PREFIX + '%s. %d מתוך %d עמדות מאושרות.' % (st['label'], st['approved_count'],
                                                               st['positions_count'])


def status_texts(model, st, cells):
    cells = cells or {}
    return {'label': st['label'], 'summary': summary_text(st),
            'cells': {k: cell_status_text(cells.get(k), st, k) for k in S.iter_cell_keys(model)}}


# ------------------------------------------------------------------ Word
def add_status_control(paragraph, tag, text, size=None):
    """העזר של בונה ה-Word: טקסט מעמד בתוך בקר תוכן עם תגית, בריצה RTL."""
    sz = '<w:sz w:val="%d"/><w:szCs w:val="%d"/>' % (size * 2, size * 2) if size else ''
    xml = ('<w:sdt %s><w:sdtPr><w:tag w:val="%s"/></w:sdtPr><w:sdtContent><w:r><w:rPr>'
           '<w:rFonts w:ascii="David" w:hAnsi="David" w:cs="David"/>%s<w:rtl/></w:rPr><w:t xml:space="preserve">%s'
           '</w:t></w:r></w:sdtContent></w:sdt>') % (nsdecls('w'), tag, sz, _xml_escape(text))
    paragraph._p.append(parse_xml(xml))
    rtl.set_paragraph_rtl(paragraph)
    return paragraph


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
    return t in S.BASE_LABELS or t.startswith(S.APPROVED_PREFIX) or bool(_PARTIAL_RE.match(t))


def surface_filename(path, st):
    """שם הקובץ אומר את המעמד: "פלייבוק מוצע" כל עוד לא אושר, "מדיניות מאושרת" כשאושר."""
    d, base = os.path.split(path)
    words = {S.STATUS_DRAFT: 'פלייבוק מוצע', S.STATUS_PARTIAL: 'פלייבוק מאושר בחלקו',
             S.STATUS_APPROVED: 'מדיניות מאושרת'}
    want = words[st['playbook_status']]
    for w in words.values():
        if w in base:
            return os.path.join(d, base.replace(w, want))
    return path


def restamp_docx(src, model, st, cells, dst=None):
    """מעדכן כל טקסט מעמד ב-Word. מחזיר (נתיב חדש, ספירת החלפות)."""
    texts = status_texts(model, st, cells)
    doc = Document(src)
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
            elif s.startswith(SUMMARY_PREFIX.strip()):
                _set_runs_text(p, texts['summary'])
                done['summary'] += 1
            elif s.startswith(CELL_PREFIX.strip()):
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
    for root in _roots(doc):
        for p in root.iter(qn('w:p')):
            for r in p.iter(qn('w:r')):
                rtl._rpr_rtl(r)
    rtl.clean_metadata(doc, author=doc.core_properties.author or '', title=doc.core_properties.title)
    out = dst or surface_filename(src, st)
    doc.save(out)
    if os.path.abspath(out) != os.path.abspath(src) and dst is None and os.path.exists(src):
        os.remove(src)
    return out, done


def read_docx_status(path):
    """{'header': [...], 'labels': [...], 'summary': [...], 'cells': {...}, 'text': ...} מתוך Word שמור."""
    doc = Document(path)
    out = {'header': [], 'labels': [], 'summary': [], 'cells': {}, 'cell_lines': [], 'text': ''}
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
            elif s.startswith(SUMMARY_PREFIX.strip()):
                out['summary'].append(s)
            elif s.startswith(CELL_PREFIX.strip()):
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
    for f in S.DUAL_FIELDS:
        meta.pop(f, None)
    old_status = meta.get('status')
    meta.update({'status_label': st['label'], 'label_now': st['label'], 'status': st['label'],
                 'playbook_status': st['playbook_status'], 'approved_count': st['approved_count'],
                 'positions_count': st['positions_count']})
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
    stale = [x for x in S.BASE_LABELS if not st['label'].startswith(x)]
    if word_path:
        w = read_docx_status(word_path)
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
        if st['playbook_status'] != S.STATUS_DRAFT and 'נקלט בסימולציה' in w['text'] and not any(
                'סימולציה' in v for v in w['cells'].values()):
            out.append('Word: נשאר משפט על קליטה בסימולציה')
        if model is not None:
            out += ['Word: ' + p for p in MC.count_claims(w['text'], model)]
    if workspace_path:
        data = read_workspace_status(workspace_path)
        meta = data.get('meta') or {}
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
