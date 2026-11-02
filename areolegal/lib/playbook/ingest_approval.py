# -*- coding: utf-8 -*-
"""playbook/ingest_approval.py: קליטת גיליון העמדות החתום, תא אחר תא, בלי אישור מתוך שתיקה.

הבעיה: בעותק החתום נשארה הערת Areo "בחירה נדרשת", והקליטה רשמה 69 מתוך 69 תאים כמאושרים;
חתימה בשם תפקיד; עמדה טעונת בדיקה משפטית אושרה לפני הבדיקה; אישור בסימולציה פתח את שער המדיניות.

הבעיה:
- הבחירות שהיועצת סימנה בשתי שאלות מכריעות וההנחה שאישרה לא נרשמו ברשומת האישור, ולכן Q-01 ו-Q-02
  נשארו "פתוחות" במודל של פלייבוק "מאושר".
- "נבדק בידי" נרשם בלי תאריך.
- קליטה חוזרת של אותו קובץ: save_record נכשל ב-SameFileError; ואותו קובץ נקלט פעם כ"מדומה" ופעם
  כ"מאושר" רק משום שהמחרוזת received_via שונתה.
- כתיבה בנתיב שמעבר לגבול האחיד (common.paths.PATH_LIMIT) במקום סירוב.
- טבלת "סמכויות והסלמה" יצאה מהגיליון. אין עוד תנאי
  "מאשר הסלמה" לקליטת עמודת הצהוב. החתימה של היועץ המשפטי לפי עמודה נשארת.

הכללים כאן:
1. שורה שבה נשארה הערת Areo פתוחה, או שאלה בשורה שלא נבחרה בה אפשרות אחת בדיוק: כל תאי השורה
   pending_choice, עם השורה והשאלה.
2. תא עם הנחה שלא סומנה: pending_choice. הנחה שסומנה נרשמת בתא: assumptions_confirmed[].
3. תא שטעון בדיקה משפטית: approved רק כשנרשמו שם ותאריך ("נבדק בידי:", "תאריך הבדיקה:").
4. עמודה נקלטת רק כשסומנה "מאשר" ונרשם שם מלא של אדם (לא שם תפקיד).
5. הבחירות נרשמות ברשומה: choices{question_id: {row, index, text, tag}}.
6. ראיה: received_via (user_upload | chat_attachment) וגם upload_ref (נתיב הקובץ בתיקיית ההעלאות של
   השיחה, שהגיבוב שלו זהה לקובץ שנקלט, או מזהה צרופה של המארח). בלעדיהם, או כשהקובץ זהה בייט
   לבייט לגיליון שהופק, הרשומה simulated=True, וכל התאים policy_claim=False.
7. נתיב ארוך: קריאה דרך long_path(); כתיבה רק בנתיב שעובר את common.paths.check_write_path.
   העותק החתום נשמר בשם קצר: 12 תווי גיבוב. קליטה חוזרת של אותו קובץ עם אותה ראיה מחזירה את
   הרשומה הקיימת; עם ראיה אחרת, רק עם supersedes ונימוק.
8. גיליון באנגלית (manifest.lang = en) נקלט באותה דרך: הקידומות הקבועות ותוויות החתימה נקראות משני המילונים
   של approval_sheet (HE ו-EN), והתאים, התגיות והמניפסט זהים בשתי השפות.
9. תא שנשארו בו סוגריים של ערך שלא נקבע (approval_sheet.decision_slots, ו-decision_slots של התא במניפסט),
   למשל "[מכפיל]" או "[number] hours": pending_choice, עם הסוגריים שנשארו. העמדה אינה שלמה עד שנקבע הערך
   (דף "החלטות הנהלה"). סוגריים שמתארים פרט של עסקה ("[נקודת המסירה]") אינם חוסמים.

אישור בצ'אט במנות: נמצא שגיליון של כ-7,000 מילים ו-58 עמדות לא ייחתם, ולכן
לקוחות נשארו לעד עם "פלייבוק מוצע". תור האישור (החלק השני של הקובץ) מציג מנה של עד 8 עמדות בכל פעם, ורושם כל
תשובה ברשומת אישור מאותו סוג (APR-NNNN, kind: chat), עם שם המאשר, התאריך והתשובה כלשונה. הגיליון נשאר אפשרות,
ושתי הדרכים כותבות לאותם תאים, ולכן לאותו מעמד. merge_prior שומר בקליטת גיליון את מה שכבר אושר בצ'אט.
"""
import datetime as _dt
import hashlib
import io
import json
import os
import re
import shutil
import zipfile

from lxml import etree

try:
    from playbook.approval_sheet import fingerprint, norm_text, decision_slots, AREO_AUTHOR, HE, EN
    from playbook import approval_sheet as A
    from playbook import status as S
    from common import paths as P
except ImportError:  # pragma: no cover
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from playbook.approval_sheet import fingerprint, norm_text, decision_slots, AREO_AUTHOR, HE, EN
    from playbook import approval_sheet as A
    from playbook import status as S
    from common import paths as P

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
W14 = 'http://schemas.microsoft.com/office/word/2010/wordml'
W15 = 'http://schemas.microsoft.com/office/word/2012/wordml'
DC = 'http://purl.org/dc/elements/1.1/'
TRACKS = ('green', 'yellow', 'red')
MAX_UNZIPPED = 60 * 1024 * 1024
ROLE_WORDS = ('היועץ', 'היועצת', 'המשפטי', 'המשפטית', 'מנכ"ל', 'מנכ״ל', 'סמנכ"ל', 'הלשכה', 'המחלקה',
              'general counsel', 'legal counsel', 'ceo')
EVIDENCE_KINDS = ('user_upload', 'chat_attachment')
_ATTACHMENT_ID = re.compile(r'^[A-Za-z0-9_\-:.]{6,128}$')
_DATE = re.compile(r'\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{4}-\d{2}-\d{2}')


class IngestRefused(ValueError):
    """הקליטה סורבה: אותו קובץ חתום כבר נקלט עם ראיה אחרת, בלי supersedes ונימוק."""


def q(tag, ns=W):
    return '{%s}%s' % (ns, tag)


def long_path(path):
    """נתיב לקריאה של קובץ קיים, גם מעל 260 תווים ב-Windows. לכתיבה: check_write_path."""
    return P.long_path(path)


def _para_text(p):
    return ''.join(t.text or '' for t in p.iter(q('t')))


def sha256_file(path):
    with open(long_path(path), 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


class SignedDoc:
    PARSER = etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=False)

    def __init__(self, path):
        with zipfile.ZipFile(long_path(path)) as z:
            if sum(i.file_size for i in z.infolist()) > MAX_UNZIPPED:
                raise ValueError('הקובץ גדול מדי לקליטה')
            names = set(z.namelist())
            self.parts = {n: z.read(n) for n in ('word/document.xml', 'word/comments.xml',
                                                  'word/commentsExtended.xml', 'docProps/core.xml') if n in names}
        self.doc = self._xml('word/document.xml')
        if self.doc is None:
            raise ValueError('זה אינו קובץ Word תקין')
        self.comments = self._xml('word/comments.xml')
        self.cext = self._xml('word/commentsExtended.xml')
        self.core = self._xml('docProps/core.xml')

    def _xml(self, name):
        data = self.parts.get(name)
        return etree.fromstring(data, self.PARSER) if data else None

    def token(self):
        if self.core is not None:
            el = self.core.find(q('identifier', DC))
            if el is not None and el.text:
                return el.text.strip()
        m = re.search(r'ISS-\d{4}\|[^|\s]+\|[0-9a-f]{12}', ''.join(self.doc.itertext()))
        return m.group(0) if m else None

    def checkboxes(self, root=None):
        out = {}
        for sdt in (root if root is not None else self.doc).iter(q('sdt')):
            pr = sdt.find(q('sdtPr'))
            tag = pr.find(q('tag')) if pr is not None else None
            cb = pr.find(q('checkbox', W14)) if pr is not None else None
            if tag is None or cb is None:
                continue
            chk = cb.find(q('checked', W14))
            glyph = ''.join(t.text or '' for t in sdt.iter(q('t')))
            out[tag.get(q('val'))] = bool((chk is not None and chk.get(q('val', W14)) in ('1', 'true')) or
                                          '☒' in glyph)
        return out

    def open_areo_comment_ids(self):
        """הערות Areo שעדיין קיימות ולא סומנו "נפתרה"."""
        done = {}
        if self.cext is not None:
            for e in self.cext.iter(q('commentEx', W15)):
                done[e.get(q('paraId', W15))] = e.get(q('done', W15)) in ('1', 'true')
        out = set()
        if self.comments is None:
            return out
        for c in self.comments.iter(q('comment')):
            if (c.get(q('author')) or '') != AREO_AUTHOR:
                continue
            pids = [p.get(q('paraId', W14)) for p in c.iter(q('p'))]
            if not any(done.get(pid) for pid in pids if pid):
                out.add(c.get(q('id')))
        return out

    def tables(self):
        return list(self.doc.iter(q('tbl')))


def _rows_by_code(sd, manifest):
    """שורה בטבלת העמדות לפי הקוד שבפסקה הראשונה של תא הנושא."""
    out = {}
    for tbl in sd.tables():
        for tr in tbl.iter(q('tr')):
            tcs = tr.findall(q('tc'))
            if len(tcs) != 4:
                continue
            paras = list(tcs[0].iter(q('p')))
            code = norm_text(_para_text(paras[0])) if paras else ''
            if code in manifest['rows']:
                out[code] = tcs
    return out


def _cell_parts(tc):
    """(עמדה, נוסח, שורות השפעה, שם הבודק, תאריך הבדיקה) מתוך תא, לפי הקידומות הקבועות (עברית או אנגלית)."""
    position, wording, effects, legal_by, legal_at = None, None, [], None, None
    both = (HE, EN)
    prefixes = [norm_text(T[k]) for T in both for k in ('wording', 'cure')]
    no_wording = {norm_text(T['no_wording']) for T in both}
    legal_lines = [norm_text(T['legal_line']) for T in both]
    legal_dates = [norm_text(T['legal_date']) for T in both]
    skip = tuple(norm_text(T[k]) for T in both for k in ('flags', 'assume'))
    for p in tc.iter(q('p')):
        s = norm_text(_para_text(p))
        if not s:
            continue
        pre = next((x for x in prefixes if s.startswith(x)), None)
        lline = next((x for x in legal_lines if s.startswith(x)), None)
        ldate = next((x for x in legal_dates if s.startswith(x)), None)
        if pre:
            wording = s[len(pre):].strip()
            if wording in no_wording:
                wording = ''
        elif s.startswith(('כשהחברה', 'מה זה מטיל', 'When the company', 'What this imposes')):
            effects.append(s.split(':', 1)[1].strip() if ':' in s else s)
        elif lline:
            legal_by = s[len(lline):].strip(' _.') or None
        elif ldate:
            m = _DATE.search(s[len(ldate):])
            legal_at = m.group(0) if m else None
        elif s.startswith(skip) or '☐' in s or '☒' in s:
            continue
        elif position is None:
            position = s
    return position, wording, effects, legal_by, legal_at


def _is_person_name(name):
    n = norm_text(name)
    if len(n.split()) < 2:
        return False
    low = n.lower()
    return not any(w.lower() in low for w in ROLE_WORDS)


def _signers(sd, boxes):
    """{track: {'name','role','date'}} מטבלת החתימה (5 עמודות)."""
    labels = {norm_text(v): k for T in (HE, EN) for k, v in T['track_label'].items()}
    out = {}
    for tbl in sd.tables():
        for tr in tbl.iter(q('tr')):
            tcs = tr.findall(q('tc'))
            if len(tcs) != 5:
                continue
            track = labels.get(norm_text(''.join(_para_text(p) for p in tcs[0].iter(q('p')))))
            if not track:
                continue
            vals = [norm_text(' '.join(_para_text(p) for p in tc.iter(q('p')))) for tc in tcs[2:5]]
            out[track] = {'checked': bool(boxes.get('chk:sign:%s' % track)), 'name': vals[0], 'role': vals[1],
                          'date': vals[2]}
    return out


def _row_has_comment(tcs, ids):
    for tc in tcs:
        for el in tc.iter(q('commentRangeStart'), q('commentReference')):
            if el.get(q('id')) in ids:
                return True
    return False


def _row_choices(manifest, row_meta, boxes):
    """(בחירות שנעשו, סיבות חסימה) לשורה. בכל שאלה בדיוק אפשרות אחת."""
    chosen, reasons = {}, []
    for qid in row_meta.get('questions') or []:
        qm = (manifest.get('questions') or {}).get(qid) or {}
        ticked = [o for o in qm.get('options') or [] if boxes.get(o['tag'])]
        if not ticked:
            reasons.append('לא נבחרה אפשרות בשאלה %s' % qid)
        elif len(ticked) > 1:
            reasons.append('נבחרה יותר מאפשרות אחת בשאלה %s' % qid)
        else:
            o = ticked[0]
            chosen[qid] = {'row': qm.get('row'), 'index': o['index'], 'text': o['text'], 'tag': o['tag'],
                           'question': qm.get('question') or ''}
    if not row_meta.get('questions') and row_meta.get('choices') and not any(
            boxes.get(t) for t in row_meta['choices']):
        reasons.append('לא נבחרה אפשרות')
    return chosen, reasons


def evidence_status(received_via, upload_ref, signed_sha, issued_sha=None):
    """(simulated, warnings). ראיה = ערוץ מוכר + הפניה לאירוע ההעלאה, וקובץ ששונה מהגיליון שהופק."""
    warnings = []
    if received_via not in EVIDENCE_KINDS:
        warnings.append('אין ראיה שהקובץ הגיע מהמשתמש (received_via: %s). הרשומה מסומנת simulated, ושער '
                        'המדיניות לא יתיר "מדיניות" על סמכה.' % (received_via or 'חסר'))
        return True, warnings
    if not upload_ref:
        warnings.append('חסרה הפניה לאירוע ההעלאה (upload_ref). הרשומה מסומנת simulated.')
        return True, warnings
    if os.path.exists(long_path(upload_ref)):
        if sha256_file(upload_ref) != signed_sha:
            warnings.append('הקובץ שב-upload_ref אינו הקובץ שנקלט. הרשומה מסומנת simulated.')
            return True, warnings
    elif not _ATTACHMENT_ID.match(str(upload_ref)):
        warnings.append('upload_ref אינו נתיב קיים ואינו מזהה צרופה. הרשומה מסומנת simulated.')
        return True, warnings
    if issued_sha and issued_sha == signed_sha:
        warnings.append('הקובץ זהה בייט לבייט לגיליון שהופק: אין בו חתימה. הרשומה מסומנת simulated.')
        return True, warnings
    return False, warnings


def ingest(signed_path, manifest, received_via=None, upload_ref=None, today=None):
    """קולט את העותק החתום מול המניפסט של אותה הפקה. מחזיר {'cells', 'record', 'warnings'}."""
    today = today or _dt.date.today().isoformat()
    sd = SignedDoc(signed_path)
    if sd.token() != manifest['token']:
        raise ValueError('המסמך שייך להפקה אחרת, ולא לגיליון הזה')
    boxes = sd.checkboxes()
    if not boxes.get('chk:final'):
        return {'cells': {}, 'record': None, 'warnings': ['לא סומן "זו הגרסה הסופית לחתימה"']}
    warnings = []
    signers = _signers(sd, boxes)
    signed = {}
    for track, s in signers.items():
        if not s['checked']:
            continue
        if not _is_person_name(s['name']):
            warnings.append('עמודת %s: "%s" אינו שם מלא של אדם. העמודה לא נקלטה.' % (track, s['name']))
            continue
        signed[track] = s
    sha = sha256_file(signed_path)
    simulated, ev_warn = evidence_status(received_via, upload_ref, sha, manifest.get('issued_sha256'))
    warnings += ev_warn
    open_ids = sd.open_areo_comment_ids()
    rows = _rows_by_code(sd, manifest)
    choices, row_block = {}, {}
    for code, row_meta in manifest['rows'].items():
        tcs = rows.get(code)
        reasons = []
        if tcs is not None and _row_has_comment(tcs, open_ids):
            reasons.append('הערת Areo פתוחה בשורה %s (%s)' % (code, ', '.join(
                x for x in row_meta.get('questions') or [] if x) or 'בחירה נדרשת'))
        chosen, why = _row_choices(manifest, row_meta, boxes)
        reasons += ['%s בשורה %s' % (w, code) for w in why]
        choices.update(chosen)
        if reasons:
            row_block[code] = reasons
    cells = {}
    for key, issued in manifest['cells'].items():
        track = key.split('|')[2]
        out = {'status': 'not_signed', 'policy_claim': False, 'reason': None, 'approved_text': None,
               'simulated': simulated, 'legal_review_required': issued['legal_review'],
               'legal_review_done_by': None, 'legal_review_done_at': None, 'approved_at': None,
               'issued_fp': issued['fp'], 'assumptions_confirmed': []}
        cells[key] = out
        if track not in signed:
            out['reason'] = 'העמודה לא נחתמה'
            continue
        tcs = rows.get(issued['row'])
        if tcs is None:
            out.update(status='open', reason='השורה %s לא נמצאה בקובץ' % issued['row'])
            continue
        reasons = list(row_block.get(issued['row']) or [])
        cell_boxes = sd.checkboxes(tcs[issued['col']])
        texts = {a['tag']: a['text'] for a in issued.get('assumption_texts') or []}
        for tag in issued.get('assumptions') or []:
            if cell_boxes.get(tag):
                out['assumptions_confirmed'].append({'tag': tag, 'text': texts.get(tag, ''),
                                                     'confirmed_by': signed[track]['name'], 'at': today})
            else:
                reasons.append('הנחה שלא אושרה בתא')
        if reasons:
            out.update(status='pending_choice', reason='; '.join(reasons))
            continue
        position, wording, effects, legal_by, legal_at = _cell_parts(tcs[issued['col']])
        if not position:
            out.update(status='open', reason='תוכן התא נמחק: לא מאשרים את המסלול, או דורשים נוסח אחר?')
            continue
        # סוגריים של ערך שלא נקבע ("[מכפיל]", "[number]") שנשארו בתא: העמדה אינה שלמה, ואינה נספרת כמאושרת
        # סוגריים שמתארים פרט של עסקה נשארים מותרים
        text = ' '.join([position, wording or ''] + effects)
        left = decision_slots(text) + [s for s in issued.get('decision_slots') or []
                                       if s in text and s not in decision_slots(text)]
        if left:
            out.update(status='pending_choice',
                       reason='נשאר ערך שלא נקבע: %s. יש לכתוב את הערך במקום הסוגריים (דף "החלטות הנהלה"), '
                              'ולחתום שוב' % ', '.join(left))
            continue
        fp = fingerprint([position, wording or ''] + effects)
        status = 'approved' if fp == issued['fp'] else 'approved_modified'
        out.update(approved_text={'position': position, 'wording': wording, 'effects': effects},
                   approved_fp=fp, approved_at=today, signer=signed[track]['name'], role=signed[track]['role'])
        if issued['legal_review'] and not (legal_by and legal_at):
            out.update(status='pending_legal_review', legal_review_done_by=legal_by, legal_review_done_at=legal_at,
                       reason='טעון בדיקה משפטית: לא נרשמו שם הבודק ותאריך הבדיקה ("נבדק בידי:", '
                              '"תאריך הבדיקה:")')
            continue
        out.update(status=status, legal_review_done_by=legal_by, legal_review_done_at=legal_at,
                   policy_claim=not simulated)
    record = {'kind': 'signature', 'token': manifest['token'], 'signed_sha256': sha,
              'signed_copy': sha[:12] + '.docx', 'received_at': today,
              'evidence': {'received_via': received_via, 'upload_ref': upload_ref},
              'simulated': simulated, 'signers': signed, 'choices': choices, 'warnings': warnings,
              'counts': {s: sum(1 for c in cells.values() if c['status'] == s) for s in
                         ('approved', 'approved_modified', 'pending_choice', 'pending_legal_review', 'open',
                          'not_signed')}}
    return {'cells': cells, 'record': record, 'warnings': warnings}


def _existing_records(records_dir):
    out = []
    d = long_path(records_dir)
    if not os.path.isdir(d):
        return out
    for x in sorted(os.listdir(d)):
        if re.match(r'APR-\d{4}\.json$', x):
            with io.open(os.path.join(d, x), encoding='utf-8') as fh:
                out.append((os.path.join(records_dir, x), json.load(fh)))
    return out


def save_record(records_dir, signed_path, result, supersedes=None, reason=None):
    """שומר עותק של הקובץ החתום בשם קצר ואת הרשומה. מחזיר את נתיב הרשומה.

    - העותק אינו מועתק כשהמקור הוא כבר העותק השמור, או כשקובץ באותו שם ובאותו גיבוב כבר קיים
      (קליטה חוזרת: בלי SameFileError).
    - אותו קובץ חתום, אותה ראיה: מוחזרת הרשומה הקיימת, ולא נוצרת רשומה כפולה.
    - אותו קובץ חתום, ראיה אחרת: IngestRefused, אלא אם supersedes (מזהה הרשומה הקודמת) ונימוק.
    - כל כתיבה עוברת את common.paths.check_write_path."""
    rec = result['record']
    prior = _existing_records(records_dir)
    same = [(p, r) for p, r in prior if r.get('signed_sha256') == rec['signed_sha256']
            and not r.get('superseded_by')]
    # 1.2.0: העלאה חוזרת של הגיליון אחרי רשומה ישנה (בלי ראיה) מחליפה אותה, בלי supersedes ידני
    legacy = [r for p, r in same if S.is_legacy_record(r)]
    if legacy and not S.is_legacy_record(rec) and not supersedes and len(legacy) == len(same):
        supersedes, reason = legacy[-1].get('record_id'), reason or 'העלאה חוזרת אחרי רשומה ישנה בלי ראיה'
    for p, r in same:
        if r.get('evidence') == rec.get('evidence') and r.get('simulated') == rec.get('simulated'):
            return p
    if same and not (supersedes and reason):
        raise IngestRefused('הקובץ החתום הזה כבר נקלט (%s) עם ראיה אחרת. קליטה חוזרת רק עם supersedes '
                            'ונימוק.' % ', '.join(r.get('record_id') or os.path.basename(p) for p, r in same))
    copy_path = os.path.join(records_dir, rec['signed_copy'])
    P.check_write_path(copy_path)
    os.makedirs(records_dir, exist_ok=True)
    src, dst = os.path.abspath(signed_path), os.path.abspath(copy_path)
    if os.path.normcase(src) != os.path.normcase(dst):
        if not (os.path.exists(dst) and sha256_file(dst) == rec['signed_sha256']):
            shutil.copyfile(long_path(signed_path), dst)
    n = 1 + len(prior)
    path = os.path.join(records_dir, 'APR-%04d.json' % n)
    P.check_write_path(path)
    data = dict(rec, record_id='APR-%04d' % n, cells=result['cells'])
    if supersedes:
        data.update(supersedes=supersedes, supersede_reason=reason)
        for p, r in prior:
            if r.get('record_id') == supersedes:
                r['superseded_by'] = data['record_id']
                with io.open(p, 'w', encoding='utf-8') as fh:
                    json.dump(r, fh, ensure_ascii=False, indent=1)
    with io.open(path, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    return path


def current_record(records_dir):
    """(נתיב, רשומה) של הרשומה האחרונה שאינה superseded, או (None, None). מקור התאים לגזירת המעמד."""
    live = [(p, r) for p, r in _existing_records(records_dir) if not r.get('superseded_by')]
    return live[-1] if live else (None, None)


def record_cells(record):
    """התאים של רשומה כפי שהם נספרים: אותו כלל של status.effective_cells (רשומה ישנה: אף תא אינו מאושר)."""
    return S.effective_cells(record)


def migrate_legacy_record(path):
    """עזר ההמרה (גרסה 1.2.0): רשומת אישור ישנה (בלי received_via או upload_ref) מסומנת legacy: simulated=True,
    וכל תא legacy, policy_claim=False ו-simulated=True; ההודעה למשתמש (status.REUPLOAD_NOTICE) נרשמת פעם אחת.
    רשומה תקינה אינה משתנה. מחזיר (changed, notice או None). הכתיבה עוברת את common.paths.check_write_path."""
    with io.open(long_path(path), encoding='utf-8') as fh:
        rec = json.load(fh)
    if not S.is_legacy_record(rec) or rec.get('reupload_notice'):
        return False, None
    rec['legacy'] = True
    rec['simulated'] = True
    rec['cells'] = S.effective_cells(rec)
    rec['reupload_notice'] = S.REUPLOAD_NOTICE
    rec.setdefault('evidence', {'received_via': rec.get('received_via'), 'upload_ref': rec.get('upload_ref')})
    P.check_write_path(path)
    tmp = path + '.tmp'
    with io.open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(rec, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, path)
    return True, S.REUPLOAD_NOTICE


def merge_prior(result, prior_cells):
    """קליטת גיליון אחרי אישור בצ'אט: תא שעמודתו לא נחתמה (not_signed), ושהיה נספר כמאושר ברשומה הקודמת על אותו
    נוסח בדיוק (approved_fp שווה ל-fp שהגיליון הוציא), נשאר מאושר. בלי זה גיליון שנחתם בעמודה אחת מחק את מה שאושר
    בצ'אט. מחזיר את מספר התאים שנשמרו, ומעדכן את counts ברשומה."""
    n = 0
    for key, c in (result.get('cells') or {}).items():
        p = (prior_cells or {}).get(key)
        if c.get('status') == 'not_signed' and p and S.cell_counts(p) and p.get('approved_fp') == c.get('issued_fp'):
            result['cells'][key] = dict(p, carried_forward=True)
            n += 1
    if n and result.get('record'):
        result['record']['counts'] = _counts(result['cells'])
        result['record']['carried_forward'] = n
    return n


# ============================================================================ אישור בצ'אט במנות
# התור נגזר בכל פעם מהמודל ומהתאים של הרשומה האחרונה, בארבעה שלבים, וכל קריאה מחזירה מנה אחת:
# 1. batch: עמדות ירוקות שנשענות על מסמכי החברה (מאגר חתום או נוסחים שהחברה מציגה), בשני מסמכים לפחות, בלי
#    בדיקה משפטית, בלי הנחה, בלי ערך שלא נקבע ובלי ממצא לא מאומת. מאושרות במנה אחת; מה שהוצא ("חוץ מ") עובר
#    לבדיקה אחת אחת.
# 2. decisions: החלטות הנהלה במספרים (approval_sheet.management_decisions), עם בעל החלטה. הערך נכתב בנוסח
#    במקום הסוגריים, ונרשם ב-change_log. העמדה עצמה מאושרת אחר כך, בשלב 4.
# 3. questions: שאלות מכריעות פתוחות שיש להן אפשרויות. שאלה בלי אפשרויות מוצגת כמידע בלבד.
# 4. topics: כל השאר, נושא אחר נושא לפי החשיבות, עד 8 עמדות במנה: הצעת Areo, צהוב ואדום, ראיה חלשה, בדיקה משפטית.
# ומצב חמישי, updates ("עדכון פלייבוק מעסקה"): הצעות עדכון מקובץ המצב של עסקה (deal_updates).
# כל מנה נשמרת בקובץ התור (approval-queue-<family_id>.json) עם טביעת האצבע של כל תא, והתשובה נקלטת מול אותה מנה
# בלבד. תשובה שאינה מובנת עוצרת את כל הקליטה (ReplyError): אין פירוש חלקי של תשובה של מאשר.

CHAT_VIA = 'chat_reply'
BATCH_MAX = 8
STRONG_CORPUS = ('signed', 'company_forms')
MIN_STRONG_DOCS = 2
STAGES = ('batch', 'decisions', 'questions', 'topics')
QUEUE_FILE = 'approval-queue-%s.json'
TEXT_KINDS = ('text_edited', 'text_added', 'text_deleted', 'our_change_rejected')
APPROVED_STATUSES = ('approved', 'approved_modified')
_TRACK_WORDS = {'green': ('ירוק', 'green', 'נדרוש'), 'yellow': ('צהוב', 'yellow', 'נסכים'), 'red': ('אדום', 'red')}
# גם צורות טבעיות ("אישור", "מאשרים", "accept"). המודל מנרמל תשובה חופשית ומאשר אותה עם המשתמש לפני ההרצה
# (b6-approval.md); הצורות האלה רק חוסכות סבב כשהמשתמש כתב אחת מהן
_APPROVE = ('לאשר', 'מאשרת', 'מאשר', 'מאושר', 'אישור', 'approve', 'approved', 'accept', 'accepted')
_NEGATE = ('לא לאשר', 'לא מאשר', 'אל תאשר', 'לא אישור', 'not approve', "don't approve", 'do not approve', 'reject',
           'not accept', "don't accept", 'do not accept')
_REVIEWED = ('נבדק', 'נבדקה', 'reviewed')
_SKIP = ('לדלג', 'דלג', 'skip')
_ALL = ('הכול', 'הכל', 'כל המנה', 'all')
_EXCEPT = ('חוץ מ', 'למעט', 'except')
_CHANGE = re.compile(r'^(?:לשנות|שינוי|change)\s*([^:]{0,20}):\s*(.+)$', re.S | re.I)
_NUM = re.compile(r'^\s*(\d{1,2})\s*[.):\-]?\s+(.+)$', re.S)
_SPLIT = re.compile(r'\s*[,;]\s*(?=\d{1,2}\s*[.):\-]?\s+\S)')

Q = {
    'he': {
        'head': 'אישור המדיניות',
        'batch': ('עמדות ירוקות שנשענות על המסמכים שלכם, כל אחת לפחות בשני מסמכים ({n} עמדות). ההמלצה: לאשר את '
                  'כולן במנה אחת. הנוסח של כל עמדה הוא הנוסח שחוזר במסמכים שלכם, והוא מופיע במלואו בפלייבוק.'),
        'batch_line': '{n}. {topic} (סעיף {num}) · {pos} · {docs} מסמכים',
        'reply_batch': 'לתשובה: "לאשר הכול", "לאשר הכול חוץ מ-3, 7" (מה שהוצא עובר לבדיקה אחת אחת), או "לדלג על המנה".',
        'decisions': ('מספרים שההנהלה צריכה לקבוע ({n}). אלה ערכים עסקיים, ולא נוסח משפטי, ולכל אחד מוצע מי מחליט. '
                      'הערך נכתב בנוסח במקום הסוגריים, ואת העמדה עצמה מאשרים אחר כך עם שאר העמדות.'),
        'proposal': '   מה המדיניות מציעה: {p}', 'owner': '   מי מחליט, לפי ההצעה: {o}',
        'decision_head': '{n}. {q} (סעיף {num})',
        'reply_decisions': 'לתשובה, שורה לכל ערך: "1 לשנות: <הערך>", "2 לאשר" (כשאין ערך לקבוע), או "3 לדלג".',
        'questions': 'שאלות פתוחות שחוסמות את אישור הנושא שלהן ({n}).',
        'option': '   {k}) {o}', 'rec': '   ההמלצה של Areo: {r}',
        'reply_questions': 'לתשובה, שורה לכל שאלה: "1 אפשרות 2", או "1 לדלג".',
        'topics': 'נושאים לבדיקה אחת אחת ({n} נושאים, {m} עמדות).',
        'topic_head': '{n}. {topic} (סעיף {num}) · חשיבות: {imp}',
        'tracks': {'green': 'מקובל עלינו (ירוק)', 'yellow': 'אפשר להתגמש (צהוב)', 'red': 'לא מסכימים (אדום)'},
        'track': '   {label}: {pos}', 'wording': '   הנוסח שיוחל, מילה במילה: {w}',
        'cure': '   הנוסח שנשיב, מילה במילה: {w}', 'flags': '   לתשומת לבכם: {f}',
        'legal': '   כדאי שעורך דין יעבור על זה', 'assume': '   הנחה (אישור העמדה מאשר גם אותה): {a}',
        'reply_topics': ('לתשובה, שורה לכל נושא: "1 לאשר", "2 לשנות צהוב: <הנוסח>", "3 לדלג", ובנושא שעורך דין '
                         'צריך לעבור עליו, אחרי שעבר: "4 נבדק ולאשר". אפשר גם "לאשר הכול".'),
        'updates': ('עדכונים למדיניות מהעסקאות ({n}): מה שעורך הדין שינה ביד לפני המשלוח, ומה שהוחלט מעבר '
                    'למדיניות. עדכון שמאשרים נכנס למדיניות כעמדה מאושרת.'),
        'update_head': '{n}. {topic} (סעיף {num}) · {label}',
        'event': '   {deal}, {clause}: {what}', 'current': '   היום במדיניות: {w}', 'proposed': '   מוצע: {w}',
        'no_proposed': '   אין נוסח מוצע מילה במילה: לעדכון כתבו "לשנות: <הנוסח>".',
        'reply_updates': 'לתשובה, שורה לכל עדכון: "1 לאשר", "2 לשנות: <הנוסח>", או "3 לדלג".',
        'waiting': '{n} עמדות מחכות למספר שההנהלה תקבע במקום הסוגריים.',
        'info_q': 'שאלה פתוחה שנסגרת רק בעדכון המדיניות, ועד אז אי אפשר לאשר את המדיניות כולה: {q}',
        'more': 'אחרי המנה הזו ממתינים עוד {n} פריטים.',
        'empty': 'אין עמדות שממתינות לאישור.',
        'ignored': 'לא הוצעו: {a} שינויים שאינם נוגעים בכלל של הפלייבוק, {b} שינויים בהערות לצד השני.',
        'rec_company': 'לאשר: העמדה חוזרת ב-{k} מסמכים שלכם.',
        'rec_areo': 'לאשר רק אם הנוסח משקף את מה שאתם מוכנים לתת: זו המלצה של Areo, ולא נוסח מהמסמכים שלכם.',
        'rec_market': 'לאשר אם הנקודה בשוק מתאימה לכם: העמדה נגזרה ממקורות שוק ציבוריים.',
        'rec_weak': 'לבדוק לפני אישור: יש מעט דוגמאות מההסכמים שלכם ({why}).',
        'rec_statute': 'לאשר אחרי שמוודאים שהדרישה בדין חלה עליכם.',
        'rec_legal': 'לאשר אחרי שעורך דין עבר על זה, בתשובה "נבדק ולאשר".',
        'weak_docs': 'פחות משני מסמכים', 'weak_unverified': 'מקור שעוד לא אימתנו', 'weak_assume': 'נשענת על הנחה',
        'weak_corpus': 'המסמכים אינם הסכמים חתומים של החברה',
        'rec_update': 'חזר ב-{k} עסקאות, ולכן מועמד לעדכון. כדאי לכתוב נוסח כללי, בלי פרטי העסקה ("לשנות").',
        'rec_update_skip': ('עסקה אחת היא נקודת מידע אחת, ולא מדיניות: מומלץ לדלג, ולחזור לזה אם יחזור בעסקה '
                            'נוספת.'),
        'rec_adapt': 'התאמה של הנוסח לעסקה הזו (דין, מטבע, כינויים), ולא שינוי מדיניות: מומלץ לדלג.',
        'ev_text_edited': 'שונה ביד לפני המשלוח. הופק: {b}. נשלח: {a}',
        'ev_text_added': 'נוסף ביד לפני המשלוח: {a}', 'ev_text_deleted': 'נמחק ביד לפני המשלוח: {b}',
        'ev_our_change_rejected': 'השינוי שלנו בוטל ביד לפני המשלוח. הופק: {b}. נשלח: {a}',
        'ev_accepted_red': 'התקבל נוסח שהפלייבוק מסווג כאדום: {a}',
        'ev_decided_outside': 'הכרעה מפורשת בנושא שהפלייבוק לא הכריע בו: {a}',
        'ev_red_line_exception': 'חריגה מקו אדום שאושרה בעסקה: {a}',
        'ev_adaptation': 'התאמה של נוסח הפלייבוק לעסקה: {a}',
    },
    'en': {
        'head': 'Policy approval',
        'batch': ('Green positions that rest on your own documents, each in at least two documents ({n} positions). '
                  'Recommendation: approve them all in one batch. The wording of each position is the wording that '
                  'recurs in your documents, and it appears in full in the playbook.'),
        'batch_line': '{n}. {topic} (clause {num}) · {pos} · {docs} documents',
        'reply_batch': ('To answer: "approve all", "approve all except 3, 7" (what is excluded moves to one-by-one '
                        'review), or "skip the batch".'),
        'decisions': ('Numbers for management to set ({n}). These are business values, not legal wording, and each '
                      'has a proposed owner. The value goes into the wording in place of the brackets, and you '
                      'approve the position itself later with the other positions.'),
        'proposal': '   What the policy proposes: {p}', 'owner': '   Who decides, as proposed: {o}',
        'decision_head': '{n}. {q} (clause {num})',
        'reply_decisions': ('To answer, one line per value: "1 change: <the value>", "2 approve" (when there is no '
                            'value to set), or "3 skip".'),
        'questions': 'Open questions that block approval of their topic ({n}).',
        'option': '   {k}) {o}', 'rec': '   Areo recommendation: {r}',
        'reply_questions': 'To answer, one line per question: "1 option 2", or "1 skip".',
        'topics': 'Topics for one-by-one review ({n} topics, {m} positions).',
        'topic_head': '{n}. {topic} (clause {num}) · Importance: {imp}',
        'tracks': {'green': 'We accept (green)', 'yellow': 'We can flex (yellow)', 'red': "We don't agree (red)"},
        'track': '   {label}: {pos}', 'wording': '   Wording to apply, verbatim: {w}',
        'cure': '   Wording we answer with, verbatim: {w}', 'flags': '   Note: {f}',
        'legal': '   A lawyer should review this', 'assume': '   Assumption (approving the position confirms it): {a}',
        'reply_topics': ('To answer, one line per topic: "1 approve", "2 change yellow: <the wording>", "3 skip", and '
                         'for a topic a lawyer needs to review, once they have: "4 reviewed and approve". "approve all" '
                         'also works.'),
        'updates': ('Policy updates from deals ({n}): what the lawyer changed by hand before sending, and what was '
                    'decided beyond the policy. An update you approve enters the policy as an approved position.'),
        'update_head': '{n}. {topic} (clause {num}) · {label}',
        'event': '   {deal}, {clause}: {what}', 'current': '   In the policy today: {w}', 'proposed': '   Proposed: {w}',
        'no_proposed': '   No verbatim wording proposed: to update, write "change: <the wording>".',
        'reply_updates': 'To answer, one line per update: "1 approve", "2 change: <the wording>", or "3 skip".',
        'waiting': '{n} positions are waiting for management to set the number in brackets.',
        'info_q': ('An open question that closes only in a policy update, and until then the whole policy cannot be '
                   'approved: {q}'),
        'more': '{n} more items are waiting after this batch.',
        'empty': 'No positions are waiting for approval.',
        'ignored': 'Not proposed: {a} changes that touch no playbook rule, {b} changes to comments to the other side.',
        'rec_company': 'Approve: the position recurs in {k} of your documents.',
        'rec_areo': ('Approve only if the wording reflects what you are prepared to give: this is an Areo '
                     'recommendation, not wording from your documents.'),
        'rec_market': 'Approve if the market point suits you: the position was derived from public market sources.',
        'rec_weak': 'Check before approving: there are few examples from your agreements ({why}).',
        'rec_statute': 'Approve after confirming the legal requirement applies to you.',
        'rec_legal': 'Approve once a lawyer has reviewed it, by answering "reviewed and approve".',
        'weak_docs': 'fewer than two documents', 'weak_unverified': 'a source we have not verified yet',
        'weak_assume': 'rests on an assumption', 'weak_corpus': "the documents are not the company's signed agreements",
        'rec_update': ('Recurred in {k} deals, so it is a candidate for an update. Write general wording, without the '
                       'deal details ("change").'),
        'rec_update_skip': ('One deal is one data point, not a policy: skipping is recommended, and coming back to it if '
                            'it recurs in another deal.'),
        'rec_adapt': ('An adaptation of the wording to this deal (law, currency, defined terms), not a policy change: '
                      'skipping is recommended.'),
        'ev_text_edited': 'Edited by hand before sending. Produced: {b}. Sent: {a}',
        'ev_text_added': 'Added by hand before sending: {a}', 'ev_text_deleted': 'Deleted by hand before sending: {b}',
        'ev_our_change_rejected': 'Our change was undone by hand before sending. Produced: {b}. Sent: {a}',
        'ev_accepted_red': 'Wording the playbook classifies as red was accepted: {a}',
        'ev_decided_outside': 'An explicit decision on a topic the playbook did not decide: {a}',
        'ev_red_line_exception': 'A red-line exception approved in the deal: {a}',
        'ev_adaptation': 'An adaptation of the playbook wording to the deal: {a}',
    },
}


class ReplyError(ValueError):
    """תשובה שאינה מובנת, או שאינה מתאימה למנה. שום דבר אינו נקלט."""


def _ql(lang):
    return 'en' if str(lang or '').lower().startswith('en') else 'he'


def _counts(cells):
    return {s: sum(1 for c in cells.values() if c.get('status') == s) for s in
            ('approved', 'approved_modified', 'pending_choice', 'pending_legal_review', 'open', 'not_signed',
             'skipped')}


def _rules(model):
    return {r['rule_id']: r for r in model.get('rules') or [] if r.get('rule_id')}


def _views(model, lang):
    """{cell_key: view} לכל תא בפלייבוק (בלי סגמנטים: התור עובד על שלושת המסלולים של כל כלל)."""
    roles = A.role_lines(model, lang)
    index = A.unverified_index(model)
    decisions = A.management_decisions(model, lang)
    out = {}
    for rule in model.get('rules') or []:
        for t in S.TRACKS:
            out[S.cell_key(rule['rule_id'], t)] = A.cell_view(model, rule, t, lang, index, roles, decisions)
    return out


def _cell_done(cell, view):
    """התא נספר כמאושר, על הנוסח שבמודל עכשיו."""
    return bool(S.cell_counts(cell) and cell.get('approved_fp') in (None, view['fp']))


def _unverified(view):
    return any(f.startswith(('ממצא לא מאומת', 'Unverified finding')) for f in view['flags'])


def _weak_reasons(model, rule, track, view, lang):
    T = Q[_ql(lang)]
    t = (rule.get('traffic_light') or {}).get(track) or {}
    why = []
    if len(t.get('evidence') or []) < MIN_STRONG_DOCS:
        why.append(T['weak_docs'])
    if _unverified(view):
        why.append(T['weak_unverified'])
    if view['assumptions']:
        why.append(T['weak_assume'])
    if S.corpus_status(model) not in STRONG_CORPUS:
        why.append(T['weak_corpus'])
    return why


def is_strong(model, rule, track, view, blocked_rules=()):
    """עמדה שמאושרת במנה אחת: ירוק, basis של מסמך החברה, מאגר חתום או נוסחים שהחברה מציגה, שני מסמכים לפחות, בלי
    בדיקה משפטית, הנחה, ערך שלא נקבע, ממצא לא מאומת או שאלה מכריעה פתוחה בכלל."""
    t = (rule.get('traffic_light') or {}).get(track) or {}
    basis = t.get('basis')
    return bool(track == 'green' and basis and basis not in S.NON_COMPANY_BASES and basis != 'statute'
                and S.corpus_status(model) in STRONG_CORPUS and len(t.get('evidence') or []) >= MIN_STRONG_DOCS
                and not (view['legal'] or view['slots'] or view['assumptions'] or _unverified(view))
                and rule['rule_id'] not in blocked_rules)


def _recommendation(model, rule, track, view, lang):
    T = Q[_ql(lang)]
    t = (rule.get('traffic_light') or {}).get(track) or {}
    basis = t.get('basis')
    if view['legal']:
        return 'legal', T['rec_legal']
    why = _weak_reasons(model, rule, track, view, lang)
    if basis == 'areo_proposal':
        return 'review', T['rec_areo']
    if basis == 'statute':
        return 'review', T['rec_statute']
    if basis == 'market_standard' and not _unverified(view):
        return 'review', T['rec_market']
    if why:
        return 'review', T['rec_weak'].format(why=', '.join(why))
    return 'approve', T['rec_company'].format(k=len(t.get('evidence') or []))


def _decision_done(model, d, rules):
    """החלטה שכבר נרשמה (change_log, field: management_decision), או שאין עוד בנוסח את הסוגריים שלה."""
    if any(c.get('field') == 'management_decision' and c.get('rule_id') == d.get('rule_id')
           for c in model.get('change_log') or []):
        return True
    if d.get('slots'):
        text = json.dumps((rules.get(d.get('rule_id')) or {}).get('traffic_light') or {}, ensure_ascii=False)
        return not any(s in text for s in d['slots'])
    return False


def queue_state(model, cells, lang='he', revisit=False, demoted=(), skipped=()):
    """התור כולו: {batch, decisions, questions, topics, info, waiting, views}. מה שכבר נספר כמאושר על הנוסח הנוכחי
    אינו בתור; תא שדולג (skipped) חוזר רק עם revisit, וכך גם החלטה או שאלה שדולגו (skipped: "decision:<rule_id>",
    "question:<id>" מקובץ התור); תא שהוצא ממנת הירוקים (demoted) עובר לנושאים."""
    lang = _ql(lang)
    rules = _rules(model)
    views = _views(model, lang)
    oq = S.open_decisive(model)
    blocked = {q.get('rule_id') for q in oq if q.get('rule_id') and q.get('rule_id') != 'GLOBAL'}
    pending, waiting = [], 0
    for key, view in views.items():
        cell = (cells or {}).get(key) or {}
        if _cell_done(cell, view):
            continue
        if cell.get('status') == 'skipped' and not revisit:
            continue
        if view['slots']:
            waiting += 1
            continue
        pending.append(key)
    batch, topics = [], {}
    for key in pending:
        rid, _, track = key.split('|')
        if key not in demoted and is_strong(model, rules[rid], track, views[key], blocked):
            batch.append(key)
        else:
            topics.setdefault(rid, []).append(key)
    skip = set() if revisit else set(skipped or ())
    decisions = [d for d in A.management_decisions(model, lang) if not _decision_done(model, d, rules)
                 and 'decision:%s' % d.get('rule_id') not in skip]
    questions = [q for q in oq if q.get('options') and 'question:%s' % (q.get('id') or q.get('queue_id')) not in skip]
    info = [q for q in oq if not q.get('options')]
    rank = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
    order = {rid: i for i, rid in enumerate(rules)}
    topic_list = sorted(topics.items(), key=lambda kv: (rank.get(str(rules[kv[0]].get('importance') or '').lower(), 4),
                                                         order[kv[0]]))
    return {'batch': batch, 'decisions': decisions, 'questions': questions, 'topics': topic_list, 'info': info,
            'waiting': waiting, 'views': views}


def _cell_item(model, key, view, lang):
    rid, _, track = key.split('|')
    rule = _rules(model)[rid]
    code, rec = _recommendation(model, rule, track, view, lang)
    return {'key': key, 'track': track, 'fp': view['fp'], 'position': view['position'], 'wording': view['wording'],
            'effects': view['effects'], 'flags': view['flags'], 'legal': view['legal'],
            'assumptions': view['assumptions'], 'rec_code': code, 'recommendation': rec}


def make_batch(model, cells, lang='he', stage=None, revisit=False, demoted=(), skipped=()):
    """המנה הבאה בתור: {stage, items[], waiting, info, more}. stage מכריח שלב; בלעדיו השלב הראשון שאינו ריק לפי
    STAGES. None: התור ריק."""
    qs = queue_state(model, cells, lang, revisit, demoted, skipped)
    rules = _rules(model)
    for st in ([stage] if stage else STAGES):
        items, more = [], 0
        if st == 'batch' and qs['batch']:
            for n, key in enumerate(qs['batch'], 1):
                rid = key.split('|')[0]
                t = (rules[rid].get('traffic_light') or {}).get('green') or {}
                items.append({'n': n, 'kind': 'cell', 'rule_id': rid, 'topic': rules[rid].get('topic_name') or '',
                              'key': key, 'track': 'green', 'fp': qs['views'][key]['fp'],
                              'position': qs['views'][key]['position'], 'docs': len(t.get('evidence') or [])})
        elif st == 'decisions' and qs['decisions']:
            for n, d in enumerate(qs['decisions'][:BATCH_MAX], 1):
                items.append(dict(d, n=n, kind='decision'))
            more = max(0, len(qs['decisions']) - BATCH_MAX)
        elif st == 'questions' and qs['questions']:
            for n, qi in enumerate(qs['questions'][:BATCH_MAX], 1):
                items.append({'n': n, 'kind': 'question', 'qid': qi.get('id') or qi.get('queue_id'),
                              'rule_id': qi.get('rule_id'), 'question': qi.get('question') or '',
                              'options': list(qi.get('options') or []), 'recommendation': qi.get('recommendation') or ''})
            more = max(0, len(qs['questions']) - BATCH_MAX)
        elif st == 'topics' and qs['topics']:
            used = 0
            for rid, keys in qs['topics']:
                if items and used + len(keys) > BATCH_MAX:
                    break
                rule = rules[rid]
                cis = [_cell_item(model, k, qs['views'][k], lang) for k in keys]
                items.append({'n': len(items) + 1, 'kind': 'topic', 'rule_id': rid,
                              'topic': rule.get('topic_name') or '', 'importance': rule.get('importance') or '',
                              'cells': cis})
                used += len(keys)
            more = len(qs['topics']) - len(items)
        if items:
            return {'stage': st, 'items': items, 'waiting': qs['waiting'], 'more': more,
                    'info': [q.get('question') or '' for q in qs['info']]}
    return None


# ---------------------------------------------------------------------------- עדכון פלייבוק מעסקה
def _event_key(tid, source, ev):
    raw = '|'.join(str(x) for x in (tid, source, ev.get('clause_id'), ev.get('kind'), ev.get('round'),
                                     ev.get('before'), ev.get('after')))
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:12]


def deal_events(state, model):
    """אירועים מקובץ המצב של עסקה שעשויים לעדכן את הפלייבוק: (events, ignored).
    - lawyer_overrides מסוג שינוי נוסח (TEXT_KINDS) בכלל של הפלייבוק. שינוי בהערה לצד השני, או בלי כלל, אינו מוצע.
    - exception_log: חריגה מקו אדום שאושרה, והתאמה של נוסח לעסקה (type: adaptation).
    - סעיף שבו התקבל נוסח אדום (op: accept, track_match: red), או הכרעה מפורשת בנושא שהפלייבוק לא הכריע בו.
    המסלול המוצע לעדכון: הנוסח שעורך הדין שינה הוא הנוסח שלנו (המסלול שהוחל, וירוק כשהנוסח שלהם היה אדום); מה
    שהתקבל מעבר לפלייבוק הוא מועמד לצהוב."""
    meta = state.get('meta') or {}
    tid = meta.get('transaction_id') or ''
    rules = _rules(model)
    clauses = {c.get('clause_id'): c for c in state.get('clauses') or [] if isinstance(c, dict)}
    events, ignored = [], {'no_rule': 0, 'comment': 0}

    def add(source, kind, rid, track, cl_id, before, after, proposed, rnd=None, date=None):
        ev = {'source': source, 'kind': kind, 'rule_id': rid, 'track': track, 'clause_id': cl_id,
              'round': rnd, 'date': date, 'before': before or '', 'after': after or '',
              'proposed': (proposed or '').strip() or None, 'transaction_id': tid}
        ev['key'] = _event_key(tid, source, ev)
        events.append(ev)

    for o in state.get('lawyer_overrides') or []:
        if not isinstance(o, dict):
            continue
        rids = [r for r in o.get('rule_ids') or [] if r in rules]
        if not rids:
            ignored['no_rule'] += 1
            continue
        if o.get('kind') not in TEXT_KINDS:
            ignored['comment'] += 1
            continue
        tm = (clauses.get(o.get('clause_id')) or {}).get('track_match')
        add('lawyer_override', o['kind'], rids[0], tm if tm in ('green', 'yellow') else 'green', o.get('clause_id'),
            o.get('produced_text') or o.get('before'), o.get('sent_text') or o.get('after'),
            o.get('sent_text') if o['kind'] != 'our_change_rejected' else None, o.get('round'), o.get('date'))
    seen = set()
    for e in state.get('exception_log') or []:
        if not isinstance(e, dict):
            continue
        cl = clauses.get(e.get('clause_id')) or {}
        rids = [r for r in (e.get('rule_ids') or cl.get('rule_ids') or []) if r in rules]
        if not rids:
            ignored['no_rule'] += 1
            continue
        kind = 'adaptation' if e.get('type') == 'adaptation' else 'red_line_exception'
        add('exception_log', kind, rids[0], 'yellow', e.get('clause_id'), cl.get('playbook_default'),
            e.get('what') or e.get('inserted') or '', cl.get('agreed_text') if kind != 'adaptation' else None,
            None, e.get('date'))
        seen.add(e.get('clause_id'))
    for cid, cl in clauses.items():
        rids = [r for r in cl.get('rule_ids') or [] if r in rules]
        if not rids or cid in seen:
            continue
        ud = cl.get('user_decision') or {}
        text = cl.get('agreed_text') or cl.get('current_text') or ''
        if cl.get('op') == 'accept' and cl.get('track_match') == 'red':
            add('clause', 'accepted_red', rids[0], 'yellow', cid, cl.get('playbook_default'), text, text,
                cl.get('accepted_in_round') or cl.get('decided_in_round'))
        elif ud.get('answer_kind') == 'explicit' and cl.get('track_match') not in ('green', 'yellow', 'red'):
            add('clause', 'decided_outside', rids[0], 'yellow', cid, cl.get('playbook_default'), text, text,
                cl.get('decided_in_round'), str(ud.get('recorded_at') or '')[:10] or None)
    return events, ignored


def deal_updates(states, model, lang='he'):
    """המנה של "עדכון פלייבוק מעסקה": פריט לכל כלל ומסלול, עם כל האירועים מכל העסקאות שנמסרו. אירוע שכבר הוצג
    (model.deal_feedback) אינו מוצע שוב, אבל נספר בהיסטוריה. ההמלצה: עדכון כשהאירוע חזר בשתי עסקאות או יותר
    (כמו בסיכום של הנושא ונותן), ודילוג כשהוא בעסקה אחת או כשהוא התאמה לעסקה. עסקה של משפחה אחרת אינה נקראת.
    מחזיר (batch או None, notes)."""
    lang = _ql(lang)
    T = Q[lang]
    fid = model.get('family_id')
    seen = {f.get('key') for f in model.get('deal_feedback') or []}
    history = {}
    for f in model.get('deal_feedback') or []:
        history.setdefault((f.get('rule_id'), f.get('track')), set()).add(f.get('transaction_id'))
    groups, notes, ign = {}, [], {'no_rule': 0, 'comment': 0}
    for st in states:
        fam = ((st.get('meta') or {}).get('position') or {}).get('playbook_family')
        tid = (st.get('meta') or {}).get('transaction_id') or ''
        if fam and fid and fam != fid:
            notes.append('%s: %s' % (tid, fam))
            continue
        evs, ig = deal_events(st, model)
        for k in ign:
            ign[k] += ig[k]
        for ev in evs:
            history.setdefault((ev['rule_id'], ev['track']), set()).add(ev['transaction_id'])
            if ev['key'] not in seen:
                groups.setdefault((ev['rule_id'], ev['track']), []).append(ev)
    rules = _rules(model)
    order = {rid: i for i, rid in enumerate(rules)}
    items = []
    for (rid, track), evs in sorted(groups.items(), key=lambda kv: (order[kv[0][0]], S.TRACKS.index(kv[0][1]))):
        t = (rules[rid].get('traffic_light') or {}).get(track) or {}
        k = len({x for x in history.get((rid, track), ()) if x})
        if all(e['kind'] == 'adaptation' for e in evs):
            code, rec = 'skip', T['rec_adapt']
        elif k >= 2:
            code, rec = 'update', T['rec_update'].format(k=k)
        else:
            code, rec = 'skip', T['rec_update_skip']
        proposed = next((e['proposed'] for e in reversed(evs) if e.get('proposed')), None)
        items.append({'n': len(items) + 1, 'kind': 'update', 'rule_id': rid, 'track': track,
                      'topic': rules[rid].get('topic_name') or '', 'events': evs, 'proposed': proposed,
                      'current': A.track_wording(track, t, lang), 'deals': k, 'rec_code': code, 'recommendation': rec,
                      'key': S.cell_key(rid, track)})
    if ign['no_rule'] or ign['comment']:
        notes.append(T['ignored'].format(a=ign['no_rule'], b=ign['comment']))
    if not items:
        return None, notes
    return {'stage': 'updates', 'items': items[:BATCH_MAX], 'waiting': 0, 'info': [],
            'more': max(0, len(items) - BATCH_MAX)}, notes


# ---------------------------------------------------------------------------- קובץ התור
def queue_path(records_dir, model):
    return os.path.join(records_dir, QUEUE_FILE % (model.get('family_id') or 'family'))


def load_queue(records_dir, model):
    p = queue_path(records_dir, model)
    if os.path.exists(long_path(p)):
        with io.open(long_path(p), encoding='utf-8') as fh:
            return json.load(fh)
    return {'family_id': model.get('family_id'), 'batches': [], 'demoted': []}


def save_queue(records_dir, model, data):
    p = queue_path(records_dir, model)
    P.check_write_path(p)
    os.makedirs(records_dir, exist_ok=True)
    with io.open(p, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    return p


def open_batch(queue):
    live = [b for b in queue.get('batches') or [] if b.get('status') == 'open']
    return live[-1] if live else None


def issue_batch(queue, batch, lang, today=None):
    """רושם מנה חדשה בקובץ התור, ומחליף מנה פתוחה קודמת (status: replaced). מחזיר את המנה עם batch_id."""
    for b in queue.get('batches') or []:
        if b.get('status') == 'open':
            b['status'] = 'replaced'
    bid = 'Q-%04d' % (1 + len(queue.get('batches') or []))
    batch = dict(batch, batch_id=bid, lang=_ql(lang), status='open',
                 issued_at=today or _dt.date.today().isoformat())
    queue.setdefault('batches', []).append(batch)
    return batch


# ---------------------------------------------------------------------------- הצגה
# הסימונים של הגיליון (approval_sheet.flags_for) הם תוויות קבועות בתוך המסמך. בצ'אט הם נאמרים במילים של
# areo-voice.md, בלי לשנות את התווית שבגיליון ואת הבדיקות שנשענות עליה (_unverified)
_PLAIN_FLAGS = {'he': (('הצעת Areo', 'המלצה של Areo'), ('ממצא לא מאומת', 'מקור שעוד לא אימתנו')),
                'en': (('Areo proposal', 'Areo recommendation'),
                       ('Unverified finding', 'A source we have not verified yet'))}


def _plain_flag(flag, lang):
    for a, b in _PLAIN_FLAGS[_ql(lang)]:
        flag = flag.replace(a, b)
    return flag


def _short(s, n=220):
    s = norm_text(s)
    return s if len(s) <= n else s[:n - 1].rstrip() + '…'


def render_batch(batch, model=None, lang='he'):
    """המנה כטקסט לצ'אט, בשפת הממשק. הנוסח שמאשרים מוצג במלואו; תיאור אירוע מעסקה מקוצר."""
    lang = _ql(lang)
    T, SH = Q[lang], A.SHEETS[lang]
    roles = A.role_lines(model, lang) if model else []
    st = batch['stage']
    items = batch['items']
    out = [T['head']]
    num = lambda it: it.get('num') or (A.display_num(model, it.get('rule_id')) if model else '') or '-'
    if st == 'batch':
        out.append(T['batch'].format(n=len(items)))
        for it in items:
            out.append(T['batch_line'].format(n=it['n'], num=num(it), topic=it['topic'],
                                              pos=it['position'], docs=it['docs']))
        out.append(T['reply_batch'])
    elif st == 'decisions':
        out.append(T['decisions'].format(n=len(items)))
        for it in items:
            # השאלה כוללת את המשפט המלא שבו הסוגריים ואת היחידה (approval_sheet.decision_question)
            out.append(T['decision_head'].format(n=it['n'], q=it['question'], num=num(it)))
            if it.get('proposal'):
                out.append(T['proposal'].format(p=' / '.join(it['proposal'].split('\n'))))
            out.append(T['owner'].format(o=it.get('owner') or ''))
        out.append(T['reply_decisions'])
    elif st == 'questions':
        out.append(T['questions'].format(n=len(items)))
        for it in items:
            out.append('%d. %s' % (it['n'], it['question']))
            for k, o in enumerate(it['options'], 1):
                out.append(T['option'].format(k=k, o=o))
            if it.get('recommendation'):
                out.append(T['rec'].format(r=it['recommendation']))
        out.append(T['reply_questions'])
    elif st == 'topics':
        out.append(T['topics'].format(n=len(items), m=sum(len(it['cells']) for it in items)))
        for it in items:
            imp = SH['importance'].get(str(it.get('importance') or '').lower(), it.get('importance') or '')
            out.append(T['topic_head'].format(n=it['n'], num=num(it), topic=it['topic'], imp=imp))
            recs = []
            for c in it['cells']:
                out.append(T['track'].format(label=T['tracks'][c['track']], pos=c['position']))
                out.append(T['cure' if c['track'] == 'red' else 'wording'].format(w=c['wording'] or SH['no_wording']))
                for role, label in roles:
                    if (c.get('effects') or {}).get(role):
                        out.append('   ' + label + c['effects'][role])
                if c.get('flags'):
                    out.append(T['flags'].format(f=' · '.join(_plain_flag(f, lang) for f in c['flags'])))
                if c.get('legal'):
                    out.append(T['legal'])
                for a in c.get('assumptions') or []:
                    out.append(T['assume'].format(a=a))
                if c['recommendation'] not in recs:
                    recs.append(c['recommendation'])
            out.append(T['rec'].format(r=' '.join(recs)))
        out.append(T['reply_topics'])
    elif st == 'updates':
        out.append(T['updates'].format(n=len(items)))
        for it in items:
            out.append(T['update_head'].format(n=it['n'], num=num(it), topic=it['topic'],
                                               label=T['tracks'][it['track']]))
            for e in it['events']:
                what = T['ev_' + e['kind']].format(b=_short(e.get('before')), a=_short(e.get('after')))
                out.append(T['event'].format(deal=e.get('transaction_id') or '', clause=e.get('clause_id') or '',
                                             what=what))
            out.append(T['current'].format(w=it.get('current') or SH['no_wording']))
            out.append(T['proposed'].format(w=it['proposed']) if it.get('proposed') else T['no_proposed'])
            out.append(T['rec'].format(r=it['recommendation']))
        out.append(T['reply_updates'])
    if batch.get('more'):
        out.append(T['more'].format(n=batch['more']))
    if batch.get('waiting'):
        out.append(T['waiting'].format(n=batch['waiting']))
    for qtext in batch.get('info') or []:
        out.append(T['info_q'].format(q=qtext))
    return '\n'.join(out)


# ---------------------------------------------------------------------------- פירוש התשובה
def _track_of(s):
    s = (s or '').lower()
    hits = [t for t, words in _TRACK_WORDS.items() if any(w in s for w in words)]
    return hits[0] if len(hits) == 1 else None


def _has(s, words):
    low = s.lower()
    return any(w in low for w in words)


def _classify(cmd, item, lang='he'):
    """פקודה אחת לפריט אחד: {action: approve|change|skip|choose, ...}. ReplyError כשאינה מובנת."""
    cmd = cmd.strip().strip('"״\'').strip()
    m = _CHANGE.match(cmd)
    if m:
        text = m.group(2).strip().strip('"״').strip()
        if not text:
            raise ReplyError('"לשנות" בלי נוסח בפריט %d' % item['n'])
        if item.get('kind') == 'decision' and '=' not in text:
            # יחידה שונה מזו שבמשפט נעצרת כבר כאן, לפני ששומרים גרסה או כותבים דבר
            for c in item.get('context') or ():
                value_for_slot(text, c, lang)
        return {'action': 'change', 'track': _track_of(m.group(1)), 'text': text}
    if item['kind'] == 'question':
        mm = re.match(r'^(?:אפשרות|option)?\s*(\d{1,2})$', cmd, re.I)
        if mm:
            k = int(mm.group(1))
            if not 1 <= k <= len(item['options']):
                raise ReplyError('אין אפשרות %d בשאלה %d' % (k, item['n']))
            return {'action': 'choose', 'option': k}
        for k, o in enumerate(item['options'], 1):
            if norm_text(cmd) == norm_text(o):
                return {'action': 'choose', 'option': k}
    if _has(cmd, _NEGATE):
        raise ReplyError('תשובה שלילית בפריט %d: כדי לא לאשר, "לשנות: <הנוסח>" או "לדלג"' % item['n'])
    if _has(cmd, _SKIP):
        return {'action': 'skip'}
    if _has(cmd, _APPROVE):
        return {'action': 'approve', 'reviewed': _has(cmd, _REVIEWED), 'track': _track_of(cmd)}
    raise ReplyError('לא הבנתי את התשובה לפריט %d: "%s"' % (item['n'], _short(cmd, 60)))


def parse_reply(reply, batch):
    """{n: answer}. שורה לכל פריט ("2 לשנות צהוב: ..."), כמה פריטים בשורה מופרדים בפסיק ("1 לאשר, 3 לדלג"), או
    תשובה לכל המנה ("לאשר הכול", "לאשר הכול חוץ מ-3, 7", "לדלג על המנה"). כל שגיאה: ReplyError, ושום דבר אינו
    נקלט. פריט שלא נענה נשאר בתור. בתשובה לכל המנה, מה שהוצא ("חוץ מ") מסומן except."""
    items = {it['n']: it for it in batch['items']}
    lines = [ln.strip() for ln in (reply or '').splitlines() if ln.strip()]
    if not lines:
        raise ReplyError('תשובה ריקה')
    if len(lines) == 1 and not _NUM.match(lines[0]):
        cmd = norm_text(lines[0])
        whole = _has(cmd, _ALL) or 'המנה' in cmd or 'batch' in cmd.lower()
        if whole and not _CHANGE.match(cmd):
            if _has(cmd, _NEGATE):
                raise ReplyError('תשובה שלילית לכל המנה: "לדלג על המנה", או תשובה לכל פריט')
            if _has(cmd, _SKIP):
                return {n: {'action': 'skip'} for n in items}
            if _has(cmd, _APPROVE):
                excluded = set()
                for w in _EXCEPT:
                    i = cmd.lower().find(w)
                    if i >= 0:
                        excluded = {int(x) for x in re.findall(r'\d{1,2}', cmd[i:])}
                bad = sorted(excluded - set(items))
                if bad:
                    raise ReplyError('אין במנה פריט %s' % ', '.join(map(str, bad)))
                rev = _has(cmd, _REVIEWED)
                return {n: ({'action': 'except'} if n in excluded else
                            {'action': 'approve', 'reviewed': rev, 'track': None}) for n in items}
        if len(items) == 1:
            return {1: _classify(cmd, items[1], batch.get('lang') or 'he')}
        raise ReplyError('לא ברור לאיזה פריט התשובה מתייחסת. כתבו את מספר הפריט בתחילת השורה, או "לאשר הכול"')
    out = {}
    for ln in lines:
        segs, buf = [], None
        for seg in _SPLIT.split(ln):
            # מרגע שמתחילה פקודת "לשנות", שאר השורה הוא הנוסח שלה, גם כשיש בו פסיק ומספר
            if buf is not None:
                buf += ', ' + seg
                continue
            m = _NUM.match(seg)
            if m and _CHANGE.match(m.group(2).strip()):
                buf = seg
            else:
                segs.append(seg)
        if buf is not None:
            segs.append(buf)
        for seg in segs:
            m = _NUM.match(seg)
            if not m:
                raise ReplyError('שורה בלי מספר פריט: "%s"' % _short(seg, 60))
            n = int(m.group(1))
            if n not in items:
                raise ReplyError('אין במנה פריט %d' % n)
            if n in out:
                raise ReplyError('שתי תשובות לפריט %d' % n)
            out[n] = _classify(m.group(2), items[n], batch.get('lang') or 'he')
    return out


# ---------------------------------------------------------------------------- כתיבה למודל
def set_track_wording(t, track, text, lang='he'):
    """כותב נוסח למסלול, באותו שדה ש-approval_sheet.track_wording קורא ממנו. מחזיר (field, previous)."""
    if track == 'yellow':
        fw = t.get('fallback_wording')
        if isinstance(fw, dict) and fw.get('text'):
            prev = fw['text']
            fw['text'] = text
            return 'fallback_wording.text', prev
        if isinstance(fw, str) and fw.strip():
            t['fallback_wording'] = text
            return 'fallback_wording', fw
    pc = t.get('proposed_clause')
    if isinstance(pc, dict):
        prev = A.track_wording('green', {'proposed_clause': pc}, lang)
        tl = 'he' if re.search('[֐-׿]', text) else 'en'
        # הנוסח בשפה האחרת היה תרגום של הנוסח הקודם, ולכן אינו נשאר מאחור
        t['proposed_clause'] = {'he': text if tl == 'he' else '', 'en': text if tl == 'en' else '',
                                'source_language': tl}
        return 'proposed_clause', prev
    if not pc and t.get('preferred_wording'):
        prev = t['preferred_wording']
        t['preferred_wording'] = text
        return 'preferred_wording', prev
    t['proposed_clause'] = text
    return 'proposed_clause', pc or ''


def _replace_slots(obj, mapping):
    """מחליף סוגריים בערך בכל מחרוזת בתוך obj (dict או list). מחזיר את מספר ההחלפות."""
    n = 0
    if isinstance(obj, dict):
        pairs = list(obj.items())
    elif isinstance(obj, list):
        pairs = list(enumerate(obj))
    else:
        return 0
    for k, v in pairs:
        if isinstance(v, str):
            new = v
            for s, val in mapping.items():
                new = new.replace(s, val)
            if new != v:
                obj[k] = new
                n += 1
        else:
            n += _replace_slots(v, mapping)
    return n


_SLOT_TEXT_FIELDS = ('position', 'proposed_clause', 'fallback_wording', 'preferred_wording', 'company_effect',
                     'role_effects')


_VALUE = re.compile(r'^\s*([-+]?\d+(?:[.,]\d+)?)\s*(.*)$', re.S)
_UNIT_CONFLICT = {
    'he': 'הערך "{v}" ביחידה אחרת מהמשפט: "{s}". היחידה בו היא {u}. כתבו את המספר ב{u}, או שנו את הנוסח ("לשנות ירוק: <הנוסח>")',
    'en': 'The value "{v}" uses a different unit from the sentence: "{s}". Its unit is {u}. Write the number in {u}, '
          'or change the wording ("change green: <the wording>")'}


def value_for_slot(value, ctx, lang='he'):
    """הערך שנכתב במקום סוגריים אחד, לפי היחידה שלהם (approval_sheet.slot_context): כשהיחידה כתובה אחרי הסוגריים
    ("[מספר] ימים") נכתב המספר בלבד, ויחידה זהה שהמשתמש הוסיף יורדת (בלי "72 ימים ימים"); כשהיחידה בתוך הסוגריים
    ("[number of days]") היא נכתבת עם המספר; ויחידה אחרת מזו שבמשפט ("72 שעות" מול "[מספר] ימים") אינה נכתבת:
    ReplyError, ושום דבר אינו נקלט. ערך במילים, או סוגריים בלי יחידה ידועה: כפי שנכתב."""
    unit = (ctx or {}).get('unit')
    m = _VALUE.match(value or '')
    if not unit or not m:
        return value
    num, rest = m.group(1), m.group(2).strip()
    given = A.unit_of(rest) if rest else None
    if given and given != unit:
        raise ReplyError(_UNIT_CONFLICT[_ql(lang)].format(v=value, s=ctx.get('sentence') or ctx.get('slot'),
                                                          u=A.UNIT_NAMES[unit][_ql(lang)]))
    if rest and not given:
        return value
    if ctx.get('unit_where') == 'after':
        return num
    if unit == 'percent':
        return num + '%'
    if unit == 'multiple':
        return num
    text = ctx.get('sentence') or ctx.get('slot') or ''
    return '%s %s' % (num, A.UNIT_NAMES[unit]['he' if re.search('[֐-׿]', text) else 'en'])


def apply_decision_value(rule, slots, value, context=None, lang='he'):
    """כותב את הערך שנקבע במקום הסוגריים, בעמדה, בנוסח ובשורות ההשפעה של כל שלושת המסלולים. value: ערך אחד
    כשיש סוגריים מסוג אחד או כשהערך מספר, או "[x]=v; [y]=w". context: המשפט והיחידה של כל סוגריים (מההחלטה,
    approval_sheet.slot_context), והערך מותאם ליחידה (value_for_slot). מחזיר [(track, field, previous, new)].
    ReplyError כשאינו חד-משמעי, או כשהיחידה שנכתבה שונה מזו שבמשפט."""
    slots = list(dict.fromkeys(slots or []))
    value = (value or '').strip()
    if '=' in value:
        mapping = {}
        for part in re.split(r'\s*;\s*', value):
            if '=' not in part:
                continue
            k, v = (x.strip() for x in part.split('=', 1))
            k = k if k.startswith('[') else '[%s]' % k
            if k not in slots or not v:
                raise ReplyError('אין בהחלטה סוגריים %s' % k)
            mapping[k] = v
    elif len(slots) == 1 or not re.search(r'[^\W\d_]', value):
        # ערך בלי אותיות ("2", "72", "1.5") נכון לכל הסוגריים, גם כשהם אותו ערך בעברית ובאנגלית ("[מכפיל]",
        # "[multiple]"); ערך במילים נכתב לכל סוגריים בנפרד
        mapping = {s: value for s in slots}
    else:
        raise ReplyError('בהחלטה כמה ערכים (%s): כתבו "לשנות: [x]=ערך; [y]=ערך"' % ', '.join(slots))
    ctx = {c.get('slot'): c for c in context or () if isinstance(c, dict)}
    mapping = {s: value_for_slot(v, ctx.get(s), lang) for s, v in mapping.items()}
    changes = []
    for track, t in (rule.get('traffic_light') or {}).items():
        if not isinstance(t, dict):
            continue
        for f in _SLOT_TEXT_FIELDS + tuple(k for k in t if k.startswith('as_') and k.endswith('_effect')):
            if f not in t:
                continue
            before = json.loads(json.dumps(t[f], ensure_ascii=False))
            if isinstance(t[f], str):
                new = t[f]
                for s, v in mapping.items():
                    new = new.replace(s, v)
                if new != t[f]:
                    t[f] = new
                    changes.append((track, f, before, new))
            elif _replace_slots(t[f], mapping):
                changes.append((track, f, before, t[f]))
    return changes


def _bump(version):
    try:
        major, minor = str(version or '1.0').split('.')[:2]
        return '%d.%d' % (int(major), int(minor) + 1)
    except ValueError:
        return str(version or '1.0') + '.1'


def _approved_cell(view, roles, name, role, today, reviewed, modified, answer):
    effects = [view['effects'][r] for r, _ in roles]
    out = {'status': 'approved_modified' if modified else 'approved', 'policy_claim': True, 'reason': None,
           'approved_text': {'position': view['position'], 'wording': view['wording'], 'effects': effects},
           'approved_fp': view['fp'], 'issued_fp': view['fp'], 'approved_at': today, 'signer': name, 'role': role,
           'simulated': False, 'legal_review_required': view['legal'],
           'legal_review_done_by': name if (view['legal'] and reviewed) else None,
           'legal_review_done_at': today if (view['legal'] and reviewed) else None,
           'assumptions_confirmed': [{'tag': 'chat', 'text': a, 'confirmed_by': name, 'at': today}
                                     for a in view['assumptions']],
           'via': 'chat', 'answer': answer}
    if view['slots']:
        out.update(status='pending_choice', policy_claim=False,
                   reason='נשאר ערך שלא נקבע: %s (החלטות הנהלה)' % ', '.join(view['slots']))
    elif view['legal'] and not reviewed:
        out.update(status='pending_legal_review', policy_claim=False,
                   reason='טעון בדיקה משפטית: התשובה לא אמרה "נבדק"')
    return out


def apply_answers(model, batch, answers, approver, role=None, reply='', today=None, prior_cells=None, lang='he'):
    """מחיל את התשובות על המודל ועל התאים. מחזיר {cells, record, warnings, wording_changed, summary, changes}.
    כותב למודל: נוסח שהשתנה (לשנות, ערך של החלטת הנהלה, עדכון מעסקה) עם שורה ב-change_log; deal_feedback;
    שם ותאריך הבדיקה ב-legal_review_required. תא שאושר קודם ושהנוסח שלו השתנה עכשיו חוזר להיות פתוח.
    ReplyError לפני כל כתיבה כשהמאשר אינו שם מלא של אדם."""
    today = today or _dt.date.today().isoformat()
    if not _is_person_name(approver or ''):
        raise ReplyError('"%s" אינו שם מלא של אדם. כל תשובה נרשמת בשם המאשר' % (approver or ''))
    lang = _ql(lang)
    rules = _rules(model)
    roles = A.role_lines(model, lang)
    before_views = _views(model, lang)
    cells = {k: dict(v) for k, v in (prior_cells or {}).items()}
    touched, warnings, choices, decisions, updates, skipped, changes = set(), [], {}, [], [], [], []
    vfrom = str(model.get('version') or '1.0')
    vto = _bump(vfrom)
    summary = {'approved': 0, 'changed': 0, 'skipped': 0, 'pending': 0, 'decided': 0, 'chosen': 0}

    def log(rid, track, field, prev, new, reason, trigger, refs=()):
        changes.append({'change_id': 'CH-%s-%d' % (batch.get('batch_id') or 'Q', len(changes) + 1), 'date': today,
                        'version_from': vfrom, 'version_to': vto, 'rule_id': rid, 'segment_id': None,
                        'track': track, 'field': field, 'previous': prev, 'new': new, 'evidence_refs': list(refs),
                        'reason': reason, 'trigger': trigger, 'decided_by': approver, 'decided_role': role,
                        'via': batch.get('batch_id')})

    def stale(item_fp, key):
        if before_views[key]['fp'] != item_fp:
            warnings.append('%s: הנוסח השתנה מאז שהמנה הוצגה, ולכן התשובה לא נקלטה. הנושא יוצג שוב.' % key)
            return True
        return False

    def approve_key(key, reviewed, modified, ans):
        view = _views(model, lang)[key]
        cells[key] = _approved_cell(view, roles, approver, role, today, reviewed, modified, ans)
        touched.add(key)
        if cells[key]['status'] in APPROVED_STATUSES:
            summary['approved'] += 1
            if view['legal'] and reviewed:
                rid, _, track = key.split('|')
                for lr in rules[rid].get('legal_review_required') or []:
                    if isinstance(lr, dict) and (lr.get('track') == track or track in (lr.get('tracks') or [])):
                        lr.update(checked_by=approver, checked_at=today)
        else:
            summary['pending'] += 1

    def skip_key(key, ans):
        if not S.cell_counts(cells.get(key) or {}):
            cells[key] = {'status': 'skipped', 'policy_claim': False, 'simulated': False, 'skipped_by': approver,
                          'skipped_at': today, 'via': 'chat', 'answer': ans, 'reason': 'דולג בתור האישור'}
            touched.add(key)
        skipped.append(key)
        summary['skipped'] += 1

    for n, it in sorted(((it['n'], it) for it in batch['items']), key=lambda x: x[0]):
        ans = answers.get(n)
        if not ans or ans['action'] == 'except':
            continue
        act = ans['action']
        verbatim = ans.get('text') or act
        if it['kind'] == 'cell':
            if stale(it['fp'], it['key']):
                continue
            if act == 'approve':
                approve_key(it['key'], False, False, verbatim)
            elif act == 'skip':
                skip_key(it['key'], verbatim)
            else:
                raise ReplyError('במנת הירוקים: "לאשר הכול", "חוץ מ" או "לדלג". שינוי נוסח נעשה בבדיקה אחת אחת')
        elif it['kind'] == 'topic':
            keys = [c['key'] for c in it['cells']]
            if any(stale(c['fp'], c['key']) for c in it['cells']):
                continue
            if act == 'skip':
                for k in keys:
                    skip_key(k, verbatim)
                continue
            if act == 'approve':
                sel = [k for k in keys if not ans.get('track') or k.endswith('|' + ans['track'])]
                if not sel:
                    raise ReplyError('בפריט %d אין מסלול %s' % (n, ans['track']))
                for k in sel:
                    approve_key(k, ans.get('reviewed'), False, verbatim)
                continue
            if act != 'change':
                raise ReplyError('תשובה שאינה מתאימה לנושא בפריט %d' % n)
            track = ans.get('track') or (it['cells'][0]['track'] if len(keys) == 1 else None)
            key = S.cell_key(it['rule_id'], track) if track else None
            if key not in keys:
                raise ReplyError('בפריט %d כמה מסלולים: כתבו "לשנות ירוק:", "לשנות צהוב:" או "לשנות אדום:"' % n)
            t = rules[it['rule_id']]['traffic_light'][track]
            field, prev = set_track_wording(t, track, ans['text'], lang)
            log(it['rule_id'], track, field, prev, ans['text'], 'שינוי נוסח בתור האישור', 'client_request')
            approve_key(key, True, True, ans['text'])
            summary['changed'] += 1
        elif it['kind'] == 'decision':
            rule = rules.get(it.get('rule_id'))
            if act == 'skip':
                skipped.append('decision:%s' % it.get('rule_id'))
                summary['skipped'] += 1
                continue
            if act == 'approve':
                if it.get('slots'):
                    raise ReplyError('בהחלטה %d יש ערך לקבוע (%s): "לשנות: <הערך>"' % (n, ', '.join(it['slots'])))
                value = None
            elif act == 'change':
                value = ans['text']
            else:
                raise ReplyError('תשובה שאינה מתאימה להחלטה %d' % n)
            if rule is None:
                raise ReplyError('ההחלטה %d אינה שייכת לכלל בפלייבוק' % n)
            if value is not None and not it.get('slots'):
                # החלטה על מספר שכבר כתוב בעמדה: יחידה אחרת מזו שבמשפט נדחית, גם כשאין סוגריים להחליף
                for c in it.get('context') or ():
                    if isinstance(c, dict):
                        value_for_slot(value, c, lang)
            if value is not None and it.get('slots'):
                for track, f, prev, new in apply_decision_value(rule, it['slots'], value, it.get('context'), lang):
                    log(rule['rule_id'], track, f, prev, new, 'החלטת הנהלה: %s' % it['question'], 'client_request')
            log(rule['rule_id'], None, 'management_decision', it.get('proposal') or '',
                value if value is not None else 'אושר כפי שהוצע', it['question'], 'client_request')
            changes[-1].update(question=it['question'], owner=it.get('owner'))
            decisions.append({'rule_id': rule['rule_id'], 'question': it['question'], 'value': value,
                              'owner': it.get('owner'), 'decided_by': approver, 'role': role, 'at': today})
            summary['decided'] += 1
        elif it['kind'] == 'question':
            if act == 'skip':
                skipped.append('question:%s' % it['qid'])
                summary['skipped'] += 1
                continue
            if act != 'choose':
                raise ReplyError('בשאלה %d בוחרים אפשרות: "%d אפשרות 1"' % (n, n))
            k = ans['option']
            choices[it['qid']] = {'row': it.get('rule_id'), 'index': k - 1, 'text': it['options'][k - 1],
                                  'tag': 'chat:%s' % batch.get('batch_id'), 'question': it['question']}
            summary['chosen'] += 1
        elif it['kind'] == 'update':
            rid, track = it['rule_id'], ans.get('track') or it['track']
            refs = ['%s:%s' % (e.get('transaction_id'), e.get('clause_id')) for e in it['events']]
            decision = 'skipped'
            if act == 'approve' and not it.get('proposed'):
                raise ReplyError('בעדכון %d אין נוסח מוצע מילה במילה: "%d לשנות: <הנוסח>"' % (n, n))
            if act in ('approve', 'change'):
                text = it['proposed'] if act == 'approve' else ans['text']
                t = rules[rid]['traffic_light'][track]
                field, prev = set_track_wording(t, track, text, lang)
                t.setdefault('deal_refs', []).extend(
                    {'transaction_id': e.get('transaction_id'), 'clause_id': e.get('clause_id'),
                     'kind': e.get('kind'), 'round': e.get('round')} for e in it['events'])
                log(rid, track, field, prev, text, 'עדכון פלייבוק מעסקה: %s' % ', '.join(
                    sorted({e['kind'] for e in it['events']})), 'negotiation_beyond_playbook', refs)
                approve_key(S.cell_key(rid, track), True, True, text)
                decision = 'approved' if act == 'approve' else 'changed'
                summary['changed'] += 1
            elif act == 'skip':
                summary['skipped'] += 1
            else:
                raise ReplyError('תשובה שאינה מתאימה לעדכון %d' % n)
            fb = model.setdefault('deal_feedback', [])
            for e in it['events']:
                fb.append({'key': e['key'], 'transaction_id': e.get('transaction_id'), 'clause_id': e.get('clause_id'),
                           'kind': e.get('kind'), 'rule_id': rid, 'track': track, 'decision': decision,
                           'by': approver, 'role': role, 'at': today, 'via': batch.get('batch_id')})
            updates.append({'rule_id': rid, 'track': track, 'decision': decision,
                            'events': [e['key'] for e in it['events']]})
    # תא שנספר כמאושר ושהנוסח שלו השתנה במנה הזו (החלטת הנהלה, עדכון) אינו נשאר מאושר על נוסח שאינו קיים עוד
    after_views = _views(model, lang)
    for key, v in after_views.items():
        c = cells.get(key)
        if key not in touched and c and S.cell_counts(c) and before_views[key]['fp'] != v['fp']:
            cells[key] = dict(c, status='open', policy_claim=False,
                              reason='הנוסח השתנה אחרי האישור (%s). יש לאשר מחדש' % batch.get('batch_id'))
    if changes:
        model.setdefault('change_log', []).extend(changes)
        model['version'] = vto
        model['last_updated'] = today
    rsha = hashlib.sha256((reply or '').encode('utf-8')).hexdigest()
    record = {'kind': 'chat', 'batch_id': batch.get('batch_id'), 'stage': batch.get('stage'),
              'token': 'CHAT|%s|%s' % (model.get('family_id') or '', batch.get('batch_id')), 'signed_sha256': None,
              'reply_verbatim': reply, 'reply_sha256': rsha, 'received_at': today,
              'evidence': {'received_via': CHAT_VIA, 'upload_ref': 'chat:%s:%s' % (batch.get('batch_id'), rsha[:12])},
              'simulated': False, 'signers': {'chat': {'name': approver, 'role': role, 'date': today}},
              'choices': choices, 'decisions': decisions, 'updates': updates, 'skipped': skipped,
              'warnings': warnings, 'counts': _counts(cells)}
    return {'cells': cells, 'record': record, 'warnings': warnings, 'summary': summary, 'changes': changes,
            'wording_changed': any(c['field'] != 'management_decision' for c in changes)}


def save_chat_record(records_dir, result, supersedes=None):
    """שומר את רשומת המנה (APR-NNNN.json, kind: chat) עם כל התאים: הקודמים, ועליהם התשובות של המנה. הרשומה
    הקודמת מסומנת superseded_by. מחזיר את הנתיב. כל כתיבה עוברת את common.paths.check_write_path."""
    prior = _existing_records(records_dir)
    n = 1 + len(prior)
    path = os.path.join(records_dir, 'APR-%04d.json' % n)
    P.check_write_path(path)
    os.makedirs(records_dir, exist_ok=True)
    data = dict(result['record'], record_id='APR-%04d' % n, cells=result['cells'])
    if supersedes:
        data.update(supersedes=supersedes, supersede_reason=(
            'קובץ ההערות מאשף ההערות; התאים הקודמים נמזגו' if result['record'].get('kind') == 'wizard'
            else 'מנה %s בתור האישור; התאים הקודמים נמזגו' % result['record'].get('batch_id')))
        result['record']['supersedes'] = supersedes
        for p, r in prior:
            if r.get('record_id') == supersedes and not r.get('superseded_by'):
                r['superseded_by'] = data['record_id']
                with io.open(p, 'w', encoding='utf-8') as fh:
                    json.dump(r, fh, ensure_ascii=False, indent=1)
    with io.open(path, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    return path


# ---------------------------------------------------------------------------- שורת הסיכום אחרי תשובה
_SUMMARY = {
    'he': ('נקלט: {a} אושרו, {c} שונו ואושרו, {s} דולגו, {d} מספרים נקבעו, {q} שאלות נענו. {p} עמדות מחכות לעורך '
           'דין או לערך בסוגריים.'),
    'en': ('Recorded: {a} approved, {c} changed and approved, {s} skipped, {d} numbers set, {q} questions answered. '
           '{p} positions are waiting for a lawyer or for a value in brackets.')}


def summary_line(sm, lang='he'):
    """שורת הסיכום אחרי תשובה למנה, בשפת הממשק ובלי מונחים פנימיים (areo-voice.md). הסקריפט מדפיס אותה."""
    return _SUMMARY[_ql(lang)].format(a=sm['approved'] - sm['changed'], c=sm['changed'], s=sm['skipped'],
                                      d=sm['decided'], q=sm['chosen'], p=sm['pending'])


# ============================================================================ אישור מאשף ההערות
# אישור באשף ההערות ("אישור הסעיף") נקלט ב-apply_decisions.py, אחרי שהמשתמש אישר בצ'אט את סיכום הקובץ. קודם
# הוא נכתב רק ל-rules[].decision, ולכן סביבת העבודה, תור האישור ו"שאלו את המדיניות" אמרו "0 מתוך N" אחרי
# חמישה אישורים. עכשיו הוא נרשם כאן, באותם תאים, באותו _approved_cell ובאותה רשומת APR כמו אישור בצ'אט, ולכן
# אותו מעמד בכל השכבות: עמדה עם ערך פתוח בסוגריים נשארת pending_choice, עמדה שעורך דין צריך לעבור עליה נשארת
# pending_legal_review (האשף אינו רושם בדיקה משפטית), ושם שאינו שם מלא של אדם אינו נספר.
WIZARD_VIA = 'wizard_file'


def wizard_approvals(model, approvals, by_rule, source, source_sha=None, at_rule=None, today=None,
                     prior_cells=None, lang='he'):
    """approvals: {rule_id: [tracks]}, רק מסלולים שהנוסח שלהם נבדק מול המודל (טביעת האצבע של האשף). by_rule: {rule_id:
    השם שבאשף}. at_rule: {rule_id: זמן הרשומה באשף}, לתאריך האישור. מחזיר {cells, record, warnings, summary}
    באותו מבנה של apply_answers, כדי ש-save_chat_record ו-after_ingest.apply_ingest יחולו כמו שהם."""
    today = today or _dt.date.today().isoformat()
    lang = _ql(lang)
    roles = A.role_lines(model, lang)
    views = _views(model, lang)
    cells = {k: dict(v) for k, v in (prior_cells or {}).items()}
    warnings, names = [], []
    summary = {'approved': 0, 'already': 0, 'pending_value': 0, 'pending_legal': 0, 'not_person': 0}
    by_status = {'pending_value': [], 'pending_legal': [], 'not_person': []}
    for rid in sorted(approvals):
        who = norm_text((by_rule or {}).get(rid) or '')
        if not _is_person_name(who):
            summary['not_person'] += 1
            by_status['not_person'].append(rid)
            continue
        if who not in names:
            names.append(who)
        when = str((at_rule or {}).get(rid) or today)[:10]
        for track in approvals[rid]:
            key = S.cell_key(rid, track)
            view = views.get(key)
            if view is None:
                continue
            if _cell_done(cells.get(key) or {}, view):
                summary['already'] += 1
                continue
            cell = _approved_cell(view, roles, who, None, when, False, False, 'wizard:%s' % source)
            cell['via'] = 'wizard'
            cells[key] = cell
            if cell['status'] in APPROVED_STATUSES:
                summary['approved'] += 1
            elif cell['status'] == 'pending_choice':
                summary['pending_value'] += 1
                if rid not in by_status['pending_value']:
                    by_status['pending_value'].append(rid)
            else:
                summary['pending_legal'] += 1
                if rid not in by_status['pending_legal']:
                    by_status['pending_legal'].append(rid)
    sha = source_sha or hashlib.sha256(str(source).encode('utf-8')).hexdigest()
    record = {'kind': 'wizard', 'token': 'WIZARD|%s|%s' % (model.get('family_id') or '', sha[:12]),
              'signed_sha256': None, 'source_file': source, 'source_sha256': sha, 'received_at': today,
              'evidence': {'received_via': WIZARD_VIA, 'upload_ref': 'wizard:%s:%s' % (source, sha[:12])},
              'simulated': False,
              'signers': {'wizard': {'name': ', '.join(names), 'role': None, 'date': today}} if names else {},
              'choices': {}, 'decisions': [], 'updates': [], 'skipped': [], 'warnings': warnings,
              'counts': _counts(cells)}
    return {'cells': cells, 'record': record, 'warnings': warnings, 'summary': summary, 'rules': by_status,
            'changes': [], 'wording_changed': False}
