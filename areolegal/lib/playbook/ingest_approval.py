# -*- coding: utf-8 -*-
"""playbook/ingest_approval.py: קליטת גיליון העמדות החתום, תא אחר תא, בלי אישור מתוך שתיקה.

הבעיה (סבב 2): בעותק החתום נשארה הערת Areo "בחירה נדרשת", והקליטה רשמה 69 מתוך 69 תאים כמאושרים;
חתימה בשם תפקיד; עמדה טעונת בדיקה משפטית אושרה לפני הבדיקה; אישור בסימולציה פתח את שער המדיניות.

הבעיה (סבב 3, הערות 5.5):
- הבחירות שהיועצת סימנה בשתי שאלות מכריעות וההנחה שאישרה לא נרשמו ברשומת האישור, ולכן Q-01 ו-Q-02
  נשארו "פתוחות" במודל של פלייבוק "מאושר" (שינוי 79).
- "נבדק בידי" נרשם בלי תאריך (שינוי 81).
- קליטה חוזרת של אותו קובץ: save_record נכשל ב-SameFileError; ואותו קובץ נקלט פעם כ"מדומה" ופעם
  כ"מאושר" רק משום שהמחרוזת received_via שונתה (שינוי 79).
- כתיבה בנתיב שמעבר לגבול האחיד (common.paths.PATH_LIMIT) במקום סירוב (שינוי 79).
- טבלת "סמכויות והסלמה" יצאה מהגיליון (החלטה מחייבת: אין שרשרת אישורים, שינוי 76). אין עוד תנאי
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
    from playbook.approval_sheet import fingerprint, norm_text, AREO_AUTHOR, HE
    from playbook import status as S
    from common import paths as P
except ImportError:  # pragma: no cover
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from playbook.approval_sheet import fingerprint, norm_text, AREO_AUTHOR, HE
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
    """(עמדה, נוסח, שורות השפעה, שם הבודק, תאריך הבדיקה) מתוך תא, לפי הקידומות הקבועות."""
    position, wording, effects, legal_by, legal_at = None, None, [], None, None
    prefixes = [norm_text(HE['wording']), norm_text(HE['cure'])]
    for p in tc.iter(q('p')):
        s = norm_text(_para_text(p))
        if not s:
            continue
        pre = next((x for x in prefixes if s.startswith(x)), None)
        if pre:
            wording = s[len(pre):].strip()
            if wording == norm_text(HE['no_wording']):
                wording = ''
        elif s.startswith('כשהחברה') or s.startswith('מה זה מטיל'):
            effects.append(s.split(':', 1)[1].strip() if ':' in s else s)
        elif s.startswith(norm_text(HE['legal_line'])):
            legal_by = s[len(norm_text(HE['legal_line'])):].strip(' _.') or None
        elif s.startswith(norm_text(HE['legal_date'])):
            m = _DATE.search(s[len(norm_text(HE['legal_date'])):])
            legal_at = m.group(0) if m else None
        elif s.startswith(norm_text(HE['flags'])) or s.startswith(norm_text(HE['assume'])) or '☐' in s \
                or '☒' in s:
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
    labels = {norm_text(v): k for k, v in HE['track_label'].items()}
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
