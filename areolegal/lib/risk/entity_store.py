# -*- coding: utf-8 -*-
"""risk/entity_store.py: שמירת עותקים גולמיים של חקר ישות בתיקיית העסקה, בלי רשימות מלאות ובלי טוקנים.

הבעיה (סבב 2): חקר הישות על Google שמר 82 עד 84 מ"ב בתיקיית OneDrive של הלקוחה (הרשימה הבריטית 50 מ"ב,
האירופית 25 מ"ב), ושמר ב-entity-report.json כתובות חתומות (X-Amz-Security-Token של OFAC, sig= של האו"ם).
המהנדס 13, המנהל המסחרי 13, מנכ"ל 13, סיכום C2 פערים 13 ו-14.

הכללים (הערות מעריך הסיכונים 3.5, ההרחבה של שינוי 9):
1. מרשימה גדולה (סנקציות, מאגר פתוח) נשמרות רק השורות שהתאימו או הקרובות ביותר, עם מטא-נתוני השאילתה:
   המקור, הכתובת בלי טוקנים, תאריך הקובץ, הגודל המלא וה-SHA-256 של הקובץ המלא. הקובץ המלא אינו נשמר
   בתיקיית הלקוח לעולם; הוא נשאר בתיקייה הזמנית ונמחק בסוף ההרצה.
2. כל כתובת עוברת strip_secrets לפני שהיא נכתבת לקובץ כלשהו.
3. תקרות הגודל של הכללים המשותפים 3.4: עד 200 קילובייט לכל קטע שנשמר (EXTRACT_CAP), ועד 2 מגה-בייט
   לכל תיקיית המחקר של העסקה (DEAL_CAP). כתיבה שחורגת נכשלת.
4. מבנה אחד: sources/<source_id>.json (שורות) או sources/<source_id>.<ext> (דף קטן של מרשם). שם התיקייה הוא
   הקבוע SOURCES_DIR ("sources"), אחד לכל הרכיבים: מעריך הסיכונים (<תיקיית העסקה>/sources/) ובונה הפלייבוק
   (playbooks/<family_id>/market-research/sources/). עותק ישן ב-raw/ (עד גרסה 1.1.1) נקרא ונבדק, ואינו נכתב
   (גרסה 1.2.0).
5. התאמת שם מוגדרת: match_name() מחזיר exact / alias / near / none, ורק exact או alias הם "התאמה".

נוסף בהערות 3.6 (סבב 3):
6. אותו מבנה גם לעותקים של האימות הרגולטורי (סיכום C1, פער 5): store_page מחזיר רשומה שנכנסת כמו שהיא
   ל-research.raw_copies (source_id, final_url, file, stored, full_size_bytes, full_sha256, sha256, saved_at).
7. דף גדול נחתך לחלון סביב הקטע לפי הטקסט שלו (page_text): HTML בכל קידוד (windows-1255 של נבו), ו-PDF דרך
   שכבת הטקסט; החלון נשמר כ-txt (סיכום C2, פער 6; C1, פער 5).
8. מפענחים לרשימות הרשמיות (סיכום C2, פער 5): rows_from_csv_bytes עם מפריד, כותרות ושורות פתיחה;
   OFAC_SDN_FIELDS (קובץ בלי שורת כותרות); rows_from_un_xml (הרשימה המאוחדת של מועצת הביטחון).
9. חותמות זמן: ISO 8601 מלא עם היסט (המהנדס, ממצא 15).

תקן: Python 3, ספרייה סטנדרטית בלבד.
"""
import csv
import hashlib
import io
import json
import os
import re
import sys
import unicodedata

if __name__ == '__main__':
    sys.dont_write_bytecode = True   # הרצה משורת הפקודה אינה כותבת __pycache__ לתוך החבילה
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from xml.etree import ElementTree as ET

try:
    from .page_text import PdfTextUnavailable, is_pdf, page_text
    from .page_text import norm as _norm
except ImportError:  # pragma: no cover
    from page_text import PdfTextUnavailable, is_pdf, page_text
    from page_text import norm as _norm
try:
    from common.cli import guard_out, parser, run, write_json
except ImportError:  # pragma: no cover
    import sys as _sys
    _sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from common.cli import guard_out, parser, run, write_json


def now_iso():
    """חותמת זמן אחת לכל הרכיב: שניות והיסט (2026-10-14T17:14:00+03:00)."""
    return datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')

# הכללים המשותפים 3.4: עד 200 קילובייט לכל קטע שנשמר, ועד 2 מגה-בייט לכל תיקיית המחקר של העסקה.
EXTRACT_CAP = 200 * 1024          # קובץ אחד בתיקיית העותקים (חלון התאמה, קטע או דף קטן)
DEAL_CAP = 2 * 1024 * 1024        # כל קובצי העותקים של העסקה יחד
DEFAULT_CAP = DEAL_CAP            # תאימות לאחור
PAGE_CAP = EXTRACT_CAP            # דף מרשם בודד; מעל זה נשמר חלון סביב הקטע בלבד
MAX_ROWS = 25                     # שורות שנשמרות מרשימה אחת
NEAR_ROWS = 5                     # שורות "קרובות" כשאין התאמה

# התיקייה האחת של העותקים, בכל הרכיבים (גרסה 1.2.0). LEGACY_DIRS: נקראות ונבדקות בלבד.
SOURCES_DIR = 'sources'
LEGACY_DIRS = ('raw',)

# שמות פרמטרים בכתובת שהם סוד, חתימה או אסימון (גרסה 1.2.0: רשימת מילים, ולא ביטוי רחב).
# שם הפרמטר מפורק למילים לפי "-", "_" ו-"."; פרמטר מוסר כשאחת המילים ברשימה, או כשיש לו קידומת של חתימת ענן.
SECRET_TOKENS = frozenset((
    'token', 'secret', 'sig', 'signature', 'key', 'apikey', 'password', 'passwd', 'pwd', 'auth', 'authorization',
    'session', 'sessionid', 'sid', 'jsessionid', 'phpsessid', 'credential', 'credentials', 'otp', 'ticket'))
SECRET_PREFIXES = ('x-amz-', 'x-goog-')
# פרמטרים שהם סוד רק בהקשר שלהם, ובכל אתר אחר הם פרמטר רגיל (למשל st, state, code, expires):
SAS_PARAMS = frozenset(('sv', 'ss', 'srt', 'sp', 'se', 'st', 'spr', 'si', 'sr', 'sip', 'skoid', 'sktid', 'skt',
                        'ske', 'sks', 'skv', 'sdd'))            # Azure SAS: רק כשיש גם sig
OAUTH_PARAMS = frozenset(('code', 'state', 'session_state'))    # OAuth: רק כשיש client_id, redirect_uri או scope
SIGNED_URL_PARAMS = frozenset(('expires', 'policy'))           # CloudFront: רק כשיש signature או key-pair-id


def _secret_name(name, names):
    low = name.lower()
    if low.startswith(SECRET_PREFIXES):
        return True
    if any(t in SECRET_TOKENS for t in re.split(r'[-_.]', low) if t):
        return True
    if low in SAS_PARAMS and 'sig' in names:
        return True
    if low in OAUTH_PARAMS and names & {'client_id', 'redirect_uri', 'scope'}:
        return True
    if low in SIGNED_URL_PARAMS and names & {'signature', 'key-pair-id'}:
        return True
    return False


class StoreError(Exception):
    pass


def strip_secrets(url):
    """מסיר מהכתובת אסימונים, חתימות, מפתחות ופרטי משתמש. פרמטרים של שאילתה רגילה (q, resource_id) נשארים.
    מחזיר (url_נקי, רשימת_שמות_שהוסרו)."""
    if not url:
        return url, []
    parts = urlsplit(url)
    removed = []
    kept = []
    pairs = parse_qsl(parts.query, keep_blank_values=True)
    names = {k.lower() for k, _ in pairs}
    for k, v in pairs:
        if _secret_name(k, names):
            removed.append(k)
        else:
            kept.append((k, v))
    netloc = parts.netloc
    if '@' in netloc:  # user:pass@host
        removed.append('userinfo')
        netloc = netloc.split('@', 1)[1]
    frag = parts.fragment
    if frag and re.search(r'(token|key|sig)=', frag, re.I):
        removed.append('fragment')
        frag = ''
    clean = urlunsplit((parts.scheme, netloc, parts.path, urlencode(kept, doseq=True), frag))
    return clean, removed


def has_secret(url):
    return bool(strip_secrets(url)[1])


# ---------- התאמת שם ----------
LEGAL_SUFFIX = re.compile(
    r'\b(l\.?l\.?c|inc|incorporated|ltd|limited|corp|corporation|co|company|plc|gmbh|ag|s\.?a|b\.?v|n\.?v|'
    r'llp|lp|pte|pty|srl|spa|oy|ab|as)\.?$', re.I)
# סיומות משפטיות בעברית: חברה, שותפות (מוגבלת או רשומה), אגודה שיתופית. כל צד: חברה ישראלית או זרה, אדם, שותפות.
HE_SUFFIX = re.compile(r'\s*(בע"מ|בעמ|בע״מ|שותפות מוגבלת|שותפות רשומה|ש"מ|ש״מ|אגודה שיתופית בע"מ|\(ישראל\)|ישראל)\s*$')
PUNCT = re.compile(r'[^\w\s]', re.U)


def normalize_name(name):
    """נרמול להשוואה: אותיות קטנות, בלי ניקוד וסימני כיווניות, בלי פיסוק, בלי סיומת משפטית (LLC, Inc, בע"מ)."""
    s = unicodedata.normalize('NFKC', str(name or ''))
    s = re.sub(r'[֑-ׇ‎‏‪-‮]', '', s)
    s = s.replace('״', '"').replace('׳', "'")
    s = HE_SUFFIX.sub('', s.strip())
    s = s.casefold().replace('.', '')   # L.L.C. -> llc לפני הסרת הפיסוק
    s = PUNCT.sub(' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    prev = None
    while prev != s:
        prev = s
        s = LEGAL_SUFFIX.sub('', s).strip()
    return s


def entity_kind_compatible(query_type, record_type):
    """תאגיד מול אדם אינו התאמה לעולם. סוג לא ידוע אינו פוסל."""
    q = (query_type or '').lower()
    r = (record_type or '').lower()
    if not q or not r:
        return True
    person = ('individual', 'person', 'אדם', 'יחיד')
    q_person = any(p in q for p in person)
    r_person = any(p in r for p in person)
    return q_person == r_person


def match_name(query_name, record_name, aliases=(), query_type='entity', record_type=''):
    """ההגדרה המחייבת של "התאמה בשם" (הערות 3.5, ההרחבה של שינוי 9):
    - exact: שדה השם של הרשומה, אחרי נרמול, זהה לשם המבוקש אחרי נרמול, וסוג הישות תואם.
    - alias: אחד מהכינויים הרשמיים של הרשומה (שדה כינוי, לא הערות), אחרי נרמול, זהה לשם המבוקש.
    - near: כל מילות השם המבוקש מופיעות בשם או בכינוי, או שהשם מופיע רק בשדה הערות, או שסוג הישות שונה.
            זו אינה התאמה ואינה ממצא חוסם; היא נרשמת עם ההכרעה וסיבתה.
    - none: אחרת.
    מחזיר (kind, reason)."""
    q = normalize_name(query_name)
    if not q:
        return 'none', 'שם ריק'
    rn = normalize_name(record_name)
    kinds_ok = entity_kind_compatible(query_type, record_type)
    if rn == q:
        return ('exact', 'השם זהה אחרי נרמול') if kinds_ok else ('near', 'השם זהה אבל סוג הישות שונה (אדם מול תאגיד)')
    for al in aliases or ():
        if normalize_name(al) == q:
            return ('alias', 'כינוי רשמי זהה אחרי נרמול') if kinds_ok else ('near', 'כינוי זהה אבל סוג הישות שונה')
    qt = set(q.split())
    hay = set(rn.split())
    for al in aliases or ():
        hay |= set(normalize_name(al).split())
    if qt and qt <= hay:
        return 'near', 'כל מילות השם מופיעות, אבל השם אינו זהה'
    return 'none', ''


def scan_rows(rows, query_name, name_field, alias_fields=(), type_field=None, note_fields=(), query_type='entity'):
    """עובר על שורות של רשימה (dict לכל שורה) ומחזיר (matches, near) עם הסיבה לכל אחת.
    שם שמופיע רק בשדה הערות הוא near ולעולם לא התאמה (סיכום C2, פער 10: "GOOGLE, Mahdi")."""
    matches, near = [], []
    qn = normalize_name(query_name)
    for i, row in enumerate(rows):
        aliases = []
        for f in alias_fields:
            v = row.get(f)
            if v:
                aliases += [x.strip() for x in re.split(r'[;|]', str(v)) if x.strip()]
        kind, why = match_name(query_name, row.get(name_field, ''), aliases, query_type,
                               row.get(type_field, '') if type_field else '')
        if kind in ('exact', 'alias'):
            matches.append({'row_no': i, 'match': kind, 'why': why, 'row': row})
        elif kind == 'near':
            near.append({'row_no': i, 'match': 'near', 'why': why, 'row': row})
        elif qn and any(qn and qn in normalize_name(row.get(f, '')) for f in note_fields):
            near.append({'row_no': i, 'match': 'near', 'why': 'השם מופיע רק בשדה הערות, לא בשדה השם', 'row': row})
    return matches, near


# קובץ SDN.CSV של OFAC אינו כולל שורת כותרות (מבנה הקובץ לפי OFAC, sdn.ff)
OFAC_SDN_FIELDS = ['ent_num', 'SDN_Name', 'SDN_Type', 'Program', 'Title', 'Call_Sign', 'Vess_type', 'Tonnage', 'GRT',
                   'Vess_flag', 'Vess_owner', 'Remarks']
OFAC_ALT_FIELDS = ['ent_num', 'alt_num', 'alt_type', 'alt_name', 'alt_remarks']


def rows_from_csv_bytes(data, encoding='utf-8-sig', delimiter=None, fieldnames=None, header_startswith=None):
    """שורות מרשימה בפורמט CSV.
    delimiter: None לזיהוי אוטומטי (פסיק, נקודה-פסיק, טאב); הרשימה האירופית מופרדת בנקודה-פסיק.
    fieldnames: לקובץ בלי שורת כותרות (OFAC: OFAC_SDN_FIELDS).
    header_startswith: מדלג על שורות פתיחה עד השורה שמתחילה בטקסט הזה (הרשימה הבריטית: "Report Date"
    לפני הכותרות; למשל header_startswith='Name 6')."""
    text = data.decode(encoding, 'replace')
    lines = text.splitlines(True)
    if header_startswith:
        for i, ln in enumerate(lines):
            if ln.lstrip('﻿"').startswith(header_startswith):
                lines = lines[i:]
                break
    body = ''.join(lines)
    if delimiter is None:
        sample = body[:20000]
        try:
            delimiter = csv.Sniffer().sniff(sample, delimiters=',;	').delimiter
        except csv.Error:
            delimiter = ','
    rows = list(csv.DictReader(io.StringIO(body), fieldnames=fieldnames, delimiter=delimiter))
    return [{(k or '').strip(): (v.strip() if isinstance(v, str) else v) for k, v in r.items()} for r in rows]


def rows_from_un_xml(data):
    """הרשימה המאוחדת של מועצת הביטחון (consolidated.xml): שורה לכל INDIVIDUAL ו-ENTITY, עם name (השם המלא),
    type (individual/entity), aliases (מופרדים ב-;), reference ו-comments."""
    root = ET.fromstring(data)
    out = []
    for kind, tag in (('individual', 'INDIVIDUAL'), ('entity', 'ENTITY')):
        for el in root.iter(tag):
            parts = [(el.findtext(t) or '').strip() for t in ('FIRST_NAME', 'SECOND_NAME', 'THIRD_NAME', 'FOURTH_NAME')]
            aliases = [(a.findtext('ALIAS_NAME') or '').strip() for a in el.iter(tag + '_ALIAS')]
            out.append({'name': ' '.join(p for p in parts if p), 'type': kind,
                        'aliases': ';'.join(a for a in aliases if a),
                        'reference': (el.findtext('REFERENCE_NUMBER') or '').strip(),
                        'comments': (el.findtext('COMMENTS1') or '').strip()})
    return out


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for blk in iter(lambda: fh.read(chunk), b''):
            h.update(blk)
    return h.hexdigest()


class EntityStore:
    """כותב ל-<deal_dir>/sources/ בלבד (SOURCES_DIR). כל כתיבה נבדקת מול התקרה, וכל כתובת מנוקה מטוקנים.
    deal_dir: תיקיית העסקה (מעריך הסיכונים) או תיקיית מחקר השוק של המשפחה (בונה הפלייבוק)."""

    def __init__(self, deal_dir, cap_bytes=DEAL_CAP, max_rows=MAX_ROWS, extract_cap=EXTRACT_CAP):
        self.deal_dir = deal_dir
        self.raw_dir = os.path.join(deal_dir, SOURCES_DIR)   # השם raw_dir נשמר לתאימות
        self.cap = cap_bytes
        self.extract_cap = extract_cap
        self.max_rows = max_rows
        self.records = []   # נכנס ל-entity-report.json, ב-raw_copies

    # ----- עזר -----
    def used_bytes(self):
        if not os.path.isdir(self.raw_dir):
            return 0
        return sum(os.path.getsize(os.path.join(self.raw_dir, f)) for f in os.listdir(self.raw_dir))

    def _write(self, name, data):
        if not re.match(r'^[A-Za-z0-9_\-]+\.[a-z0-9]{2,5}$', name):
            raise StoreError('שם קובץ לא חוקי: %r (המבנה: <source_id>.<ext>)' % name)
        if len(data) > self.extract_cap:
            raise StoreError('קטע של %d בתים, מעל %d לכל קטע שנשמר: %s' % (len(data), self.extract_cap, name))
        if self.used_bytes() + len(data) > self.cap:
            raise StoreError('חריגה מתקרת תיקיית המחקר של העסקה (%d בתים): %s' % (self.cap, name))
        os.makedirs(self.raw_dir, exist_ok=True)
        path = os.path.join(self.raw_dir, name)
        with open(path, 'wb') as fh:
            fh.write(data)
        return path

    # ----- רשימה גדולה: רק שורות התאמה וקרובות -----
    def store_list_result(self, source_id, source, url, query, full_bytes=None, full_path=None, rows=None,
                          name_field='name', alias_fields=(), type_field=None, note_fields=(), file_date=None,
                          query_type='entity', looked_up_at=None):
        """שומר מרשימה מלאה רק את חלון ההתאמה. full_bytes או full_path הם הקובץ המלא (בתיקייה זמנית); הוא
        משמש לגיבוב ולגודל בלבד ואינו נשמר. rows: השורות שכבר פוענחו (אחרת CSV מ-full_bytes)."""
        if full_bytes is None and full_path is not None:
            full_size = os.path.getsize(full_path)
            full_sha = sha256_file(full_path)
            if rows is None:
                with open(full_path, 'rb') as fh:
                    rows = rows_from_csv_bytes(fh.read())
        else:
            full_bytes = full_bytes or b''
            full_size = len(full_bytes)
            full_sha = sha256_bytes(full_bytes)
            if rows is None:
                rows = rows_from_csv_bytes(full_bytes)
        matches, near = scan_rows(rows, query, name_field, alias_fields, type_field, note_fields, query_type)
        kept_near = near[:NEAR_ROWS]
        if len(matches) > self.max_rows:
            raise StoreError('יותר מ-%d התאמות לשם אחד: השאילתה רחבה מדי, אין שמירה של רשימה' % self.max_rows)
        clean_url, removed = strip_secrets(url)
        header = list(rows[0].keys()) if rows else []
        rec = {
            'source_id': source_id,
            'source': source,
            'url': clean_url,
            'url_params_removed': removed,
            'query': query,
            'query_type': query_type,
            'looked_up_at': looked_up_at or now_iso(),
            'file_date': file_date,
            'full_size_bytes': full_size,
            'full_sha256': full_sha,
            'rows_total': len(rows),
            'header': header,
            'result': 'match' if matches else 'no_match',
            'matches': matches,
            'near': kept_near,
            'near_total': len(near),
            'stored': 'match_window',
        }
        data = json.dumps(rec, ensure_ascii=False, indent=1).encode('utf-8')
        path = self._write(source_id + '.json', data)
        entry = {'source_id': source_id, 'final_url': clean_url, 'file': SOURCES_DIR + '/' + source_id + '.json',
                 'stored': 'match_window', 'full_size_bytes': full_size, 'full_sha256': full_sha,
                 'sha256': sha256_bytes(data), 'result': rec['result']}
        self.records.append(entry)
        return rec, path

    # ----- דף קטן של מרשם -----
    def store_page(self, source_id, url, content, ext='htm', excerpt=None, window=4000, title=None):
        """דף רשמי קטן נשמר כמו שהוא (HTML, PDF או JSON). דף גדול מ-PAGE_CAP: נשמר רק חלון טקסט סביב הקטע
        המילולי (txt), עם הגיבוב והגודל של הדף המלא; בלי קטע, הדף אינו נשמר (StoreError).
        הטקסט נקרא ב-page_text: HTML בכל קידוד, ו-PDF דרך שכבת הטקסט. מחזיר (רשומה ל-raw_copies, נתיב)."""
        if isinstance(content, str):
            content = content.encode('utf-8')
        clean_url, removed = strip_secrets(url)
        full_sha, full_size = sha256_bytes(content), len(content)
        stored = 'page'
        data = content
        if is_pdf(content) and ext in ('htm', 'html'):
            ext = 'pdf'
        if full_size > PAGE_CAP:
            if not excerpt:
                raise StoreError('דף של %d בתים בלי קטע מילולי: לא נשמר (מעל %d)' % (full_size, PAGE_CAP))
            try:
                text = page_text(content)
            except PdfTextUnavailable as e:
                raise StoreError('אין שכבת טקסט ל-PDF הגדול (%s): לא נשמר' % e)
            ntext, nex = _norm(text), _norm(excerpt)
            pos = ntext.find(nex)
            if pos < 0:
                raise StoreError('הקטע המילולי לא נמצא בדף; אין שמירה')
            lo, hi = max(0, pos - window), min(len(ntext), pos + len(nex) + window)
            data = ntext[lo:hi].encode('utf-8')
            stored = 'excerpt_window'
            ext = 'txt'
        path = self._write('%s.%s' % (source_id, ext), data)
        entry = {'source_id': source_id, 'final_url': clean_url, 'url_params_removed': removed,
                 'file': '%s/%s.%s' % (os.path.basename(self.raw_dir), source_id, ext), 'stored': stored,
                 'full_size_bytes': full_size, 'full_sha256': full_sha, 'sha256': sha256_bytes(data),
                 'saved_at': now_iso()}
        if title:
            entry['title'] = title
        self.records.append(entry)
        return entry, path


# ---------- בדיקה של תיקיית עסקה קיימת ----------
SANCTIONS_NAME = re.compile(r'(sdn|consolidated|sanction|ofsi|fsf|ent-0[3-7])', re.I)


def audit_deal_dir(deal_dir, cap_bytes=DEAL_CAP, report_json=None):
    """מחזיר רשימת הפרות: תיקיית העותקים (sources, וגם raw הישנה) מעל התקרה, קובץ יחיד גדול (רשימה מלאה),
    או כתובת עם טוקן ב-entity-report.json."""
    problems = []
    total = 0
    for name in (SOURCES_DIR,) + LEGACY_DIRS:
        raw = os.path.join(deal_dir, name)
        if not os.path.isdir(raw):
            continue
        for f in sorted(os.listdir(raw)):
            p = os.path.join(raw, f)
            sz = os.path.getsize(p)
            total += sz
            if sz > EXTRACT_CAP:
                problems.append('קובץ מעל 200 קילובייט ב-%s (נראה כרשימה או דף מלא): %s, %d בתים' % (name, f, sz))
    if total > cap_bytes:
        problems.append('תיקיית העותקים בתיקיית העסקה: %d בתים, מעל התקרה %d' % (total, cap_bytes))
    rj = report_json or os.path.join(deal_dir, 'entity-report.json')
    if os.path.exists(rj):
        with open(rj, encoding='utf-8') as fh:
            rep = json.load(fh)
        for key in ('raw_copies', 'sources', 'lookups'):
            for i, x in enumerate(rep.get(key) or []):
                for f in ('url', 'typed_url', 'final_url'):
                    if x.get(f) and has_secret(x[f]):
                        problems.append('%s[%d].%s: כתובת עם טוקן או חתימה' % (key, i, f))
    return problems


def main(argv=None):
    """python -I entity_store.py audit --deal <deal_dir> [--out report.json]. קריאה בלבד; --out רק לדוח."""
    ap = parser('בדיקת תיקיית העותקים של עסקה', out_required=False)
    ap.add_argument('command', choices=['audit'])
    ap.add_argument('--deal', required=True, help='תיקיית העסקה (קריאה בלבד)')
    a = ap.parse_args(argv)
    out = audit_deal_dir(a.deal)
    if a.out:
        rj = os.path.join(a.deal, 'entity-report.json')
        write_json(a.out, {'problems': out}, inputs=[rj] + [os.path.join(a.deal, SOURCES_DIR, f) for f in (
            os.listdir(os.path.join(a.deal, SOURCES_DIR)) if os.path.isdir(os.path.join(a.deal, SOURCES_DIR)) else [])])
    sys.stdout.reconfigure(encoding='utf-8')
    for p in out:
        print('ERR', p)
    print('problems:', len(out))
    return 1 if out else 0


if __name__ == '__main__':
    sys.exit(run(main))
