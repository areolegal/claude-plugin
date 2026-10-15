# -*- coding: utf-8 -*-
"""risk/render_check.py: בדיקת שחרור של דוח הסיכונים בדפדפן אמיתי (Chrome או Edge בלי ממשק).

הבעיות שהבדיקה סוגרת (סבב 2 ו-3.4):
- דוח שנפתח כעמוד ריק (הערה שלא נסגרה בראש התבנית) עבר את node --check ואת הסביבה המדומה.
- פס החיסיון (position:fixed) הסתיר כותרות פרקים ושורות כותרת של טבלאות בכל עמוד מודפס (C1ב פרק 7, C2 פרק 3).
- יעד 6 עד 8 העמודים הושג רק בקיצור ידני; אף בדיקה לא ספרה עמודים בהרצה.

מה נבדק, בפרופיל דפדפן חדש בתיקייה זמנית, דרך פרוטוקול DevTools:
  non_blank        טקסט ה-DOM המלא של גוף הדוח (בלי script ו-style), ולא הטקסט הגלוי של הלשונית הפתוחה
  title            document.title מתחיל ב-"Areo Workspace"
  markers          מחרוזות חובה (ברירת מחדל: "התמונה במבט אחד", "השורה התחתונה")
  js_exceptions    0
  external         0 בקשות של העמוד לכתובת שאינה file:, data:, blob: או about:
  pdf              הדפסה ל-PDF בגודל A4 (preferCSSPageSize), וקריאת מיקומי הטקסט מתוך ה-PDF:
    page_size      595 על 842 נקודות
    appendix_page  העמוד הראשון שבו "נספח: ציטוטים מילוליים"; body_pages = העמודים שלפניו
    body_pages     נכשל מעל 8 (קוד יציאה 2)
    band_overlap   מיקומי הטקסט של פס הסימון (לפי טקסט הסימון עצמו) מול מיקומי כל שאר הטקסט, ובפרט
                   הכותרות; כל חפיפה נכשלת, והכותרות שנחפפו מדווחות בשמן
  twice            (‎--twice) טעינה חוזרת באותו פרופיל והדפסה שנייה: אותו מספר עמודים, ועמוד ראשון לא ריק

שימוש:
  python -I render_check.py --template risk-report-template.html --register risk-register.json --out DIR [--twice]
  python -I render_check.py --html "Areo Workspace - סיכונים.html" --out DIR
קוד יציאה: 0 עבר; 1 נכשל; 2 גוף הדוח מעל 8 עמודים; 3 לא נמצא דפדפן.
תלויות: ספרייה סטנדרטית בלבד (מנתח PDF ולקוח WebSocket מינימליים בתוך הקובץ).
"""
import base64
import json
import os
import re
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request
import zlib
from pathlib import Path

if __name__ == '__main__':
    sys.dont_write_bytecode = True   # הרצה משורת הפקודה אינה כותבת __pycache__ לתוך החבילה
try:
    from common.cli import guard_out, parser, run, write_json
except ImportError:  # pragma: no cover
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from common.cli import guard_out, parser, run, write_json

BODY_PAGE_LIMIT = 8
A4 = (595, 842)
DEFAULT_MARKERS = ['Areo Workspace', 'התמונה במבט אחד', 'השורה התחתונה']
# דוח חקר הישות (הערות 3.6; המהנדס 17, סיכום C2 פער 3): סמנים, מציין וגבול עמודים משלו, בלי --markers ידני
ENTITY_MARKERS = ['Areo Workspace', 'חקר ישות', 'ממצאים חוסמים']
ENTITY_PLACEHOLDER = '__ENTITY_DATA__'
ENTITY_BODY_LIMIT = 2
KINDS = {'risk': {'placeholder': '__RISK_DATA__', 'markers': None, 'body_limit': BODY_PAGE_LIMIT, 'name': 'סיכונים'},
         'entity': {'placeholder': ENTITY_PLACEHOLDER, 'markers': ENTITY_MARKERS, 'body_limit': ENTITY_BODY_LIMIT,
                    'name': 'חקר ישות'}}
RESOURCES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources')
APPENDIX_TITLES = ['נספח: ציטוטים מילוליים', 'Appendix: verbatim quotes']
HEADINGS = ['התמונה במבט אחד', 'השורה התחתונה', 'לתיקון לפני שליחת התגובה', 'העדשות', 'מועדים קריטיים',
            'הסיכונים', 'סתירות בין ההסכם לנספחים', 'צירופים ושרשראות', 'הסיכונים הקריטיים בפירוט',
            'מה לא נבדק ומה חסר', 'נספח: ציטוטים מילוליים', 'נספחים שלא נמסרו', 'הנחות שהלקוח צריך לאשר',
            'מספר', 'עדשה', 'הסיכון בשורה אחת', 'סעיף', 'חומרה', 'כיוון טיפול', 'נושא', 'מה גובר', 'התיקון',
            'מסמך וסעיף', 'הנוסח המילולי']
HE_DRAFT = 'טיוטה, טעונה אישור'
HE_PRIV = 'חסוי: מסמך עבודה של המחלקה המשפטית, הוכן לבקשת עו״ד {counsel} לצורך מתן ייעוץ משפטי ל{company}'
HE_PRIV_NONE = 'לא צוין עורך דין שהדוח הוכן עבורו; קיים ספק אם יחול חיסיון'
BAND_PAD = 3.0      # נקודות סביב שורות הסימון
OVERLAP_MIN = 1.0   # חפיפה אנכית מינימלית שנחשבת הסתרה


# ======================================================================================
# בנייה
# ======================================================================================
def build_report(template_text, register, placeholder='__RISK_DATA__'):
    """אותה הזרקה כמו build_risk_report.py: מציין אחד בדיוק, ו-"</" מוברח.
    לדוח חקר הישות: placeholder='__ENTITY_DATA__' ו-entity-report.json."""
    n = template_text.count(placeholder)
    if n != 1:
        raise ValueError('מציין ההזרקה %s צריך להופיע פעם אחת בדיוק (נמצא %d)' % (placeholder, n))
    payload = json.dumps(register, ensure_ascii=False).replace('</', '<\\/')
    return template_text.replace(placeholder, payload)


def static_checks(html_text):
    """בדיקה סטטית: כל הערה נסגרת, אין טעינה מהרשת (link, @import, src/href חיצוני מחוץ לקישורי המקורות)."""
    problems = []
    if html_text.count('<!--') != html_text.count('-->'):
        problems.append('הערה שאינה נסגרת')
    if re.search(r'<link\b', html_text, re.I):
        problems.append('<link> בתבנית')
    if re.search(r'@import', html_text):
        problems.append('@import בתבנית')
    for m in re.finditer(r'\b(?:src|href)\s*=\s*["\'](https?:)?//', html_text, re.I):
        problems.append('טעינה חיצונית: %s' % html_text[m.start():m.start() + 60])
    if re.search(r'url\(\s*["\']?https?:', html_text, re.I):
        problems.append('url() חיצוני ב-CSS')
    return problems


def band_text_from_register(register):
    """טקסט הסימון כפי שהתבנית בונה אותו (HE.draft + HE.priv), כדי לזהות את שורות הפס ב-PDF."""
    m = register.get('meta') or {}
    counsel = str(m.get('prepared_for_counsel') or '').strip()
    priv = HE_PRIV.replace('{counsel}', counsel).replace('{company}', m.get('company') or '') if counsel else HE_PRIV_NONE
    return HE_DRAFT + ' · ' + priv


# ======================================================================================
# דפדפן
# ======================================================================================
def find_browser():
    env = os.environ.get('AREO_BROWSER')
    cands = [env] if env else []
    pf = [os.environ.get(k) for k in ('PROGRAMFILES', 'PROGRAMFILES(X86)', 'LOCALAPPDATA')]
    for base in [p for p in pf if p]:
        cands += [os.path.join(base, 'Google', 'Chrome', 'Application', 'chrome.exe'),
                  os.path.join(base, 'Microsoft', 'Edge', 'Application', 'msedge.exe')]
    cands += [r'C:\Program Files\Google\Chrome\Application\chrome.exe',
              r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe']
    for name in ('google-chrome', 'chromium', 'chromium-browser', 'microsoft-edge', 'msedge', 'chrome'):
        p = shutil.which(name)
        if p:
            cands.append(p)
    cands += ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
              '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge']
    for c in cands:
        if c and os.path.isfile(c):
            return c
    return None


class WS:
    """לקוח WebSocket מינימלי (RFC 6455) ל-DevTools: טקסט בלבד, בלי הרחבות, בלי Origin."""

    def __init__(self, url, timeout=60):
        m = re.match(r'ws://([^/:]+):(\d+)(/.*)', url)
        host, port, path = m.group(1), int(m.group(2)), m.group(3)
        self.sock = socket.create_connection((host, port), timeout=timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        req = ('GET %s HTTP/1.1\r\nHost: %s:%d\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n'
               'Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n') % (path, host, port, key)
        self.sock.sendall(req.encode())
        buf = b''
        while b'\r\n\r\n' not in buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError('handshake failed')
            buf += chunk
        head, self.rest = buf.split(b'\r\n\r\n', 1)
        if b' 101 ' not in head.split(b'\r\n')[0]:
            raise ConnectionError(head.decode('latin-1'))

    def _recv_exact(self, n):
        out = self.rest[:n]
        self.rest = self.rest[n:]
        while len(out) < n:
            chunk = self.sock.recv(max(65536, n - len(out)))
            if not chunk:
                raise ConnectionError('socket closed')
            out += chunk
        if len(out) > n:
            self.rest = out[n:] + self.rest
            out = out[:n]
        return out

    def send(self, text):
        data = text.encode('utf-8')
        hdr = bytearray([0x81])
        n = len(data)
        if n < 126:
            hdr.append(0x80 | n)
        elif n < 65536:
            hdr.append(0x80 | 126)
            hdr += struct.pack('>H', n)
        else:
            hdr.append(0x80 | 127)
            hdr += struct.pack('>Q', n)
        mask = os.urandom(4)
        self.sock.sendall(bytes(hdr) + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def recv(self):
        msg = b''
        while True:
            b0, b1 = self._recv_exact(2)
            op, n = b0 & 0x0F, b1 & 0x7F
            if n == 126:
                n = struct.unpack('>H', self._recv_exact(2))[0]
            elif n == 127:
                n = struct.unpack('>Q', self._recv_exact(8))[0]
            mask = self._recv_exact(4) if b1 & 0x80 else None
            payload = self._recv_exact(n)
            if mask:
                payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
            if op == 0x9:  # ping
                continue
            if op == 0x8:
                raise ConnectionError('closed by browser')
            msg += payload
            if b0 & 0x80:
                return msg.decode('utf-8')

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


class Browser:
    def __init__(self, exe, profile_dir):
        self.profile = profile_dir
        args = [exe, '--headless=new', '--remote-debugging-port=0', '--user-data-dir=' + profile_dir,
                '--no-first-run', '--no-default-browser-check', '--disable-extensions', '--disable-gpu',
                '--allow-file-access-from-files', 'about:blank']
        self.proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        port_file = os.path.join(profile_dir, 'DevToolsActivePort')
        for _ in range(150):
            if os.path.exists(port_file) and os.path.getsize(port_file) > 0:
                break
            time.sleep(0.1)
        port = int(open(port_file).read().split()[0])
        page = None
        for _ in range(100):
            try:
                with urllib.request.urlopen('http://127.0.0.1:%d/json/list' % port, timeout=5) as r:
                    lst = json.loads(r.read().decode())
                page = next((t for t in lst if t.get('type') == 'page'), None)
                if page:
                    break
            except OSError:
                pass
            time.sleep(0.1)
        self.ws = WS(page['webSocketDebuggerUrl'])
        self.id = 0
        self.events = []

    def call(self, method, params=None, timeout=90):
        self.id += 1
        mid = self.id
        self.ws.send(json.dumps({'id': mid, 'method': method, 'params': params or {}}))
        t0 = time.time()
        while time.time() - t0 < timeout:
            m = json.loads(self.ws.recv())
            if m.get('id') == mid:
                if 'error' in m:
                    raise RuntimeError('%s: %s' % (method, m['error']))
                return m.get('result') or {}
            self.events.append(m)
        raise TimeoutError(method)

    def wait_event(self, name, timeout=30):
        t0 = time.time()
        while time.time() - t0 < timeout:
            if any(e.get('method') == name for e in self.events):
                return True
            self.ws.sock.settimeout(1)
            try:
                self.events.append(json.loads(self.ws.recv()))
            except (socket.timeout, TimeoutError):
                pass
            finally:
                self.ws.sock.settimeout(60)
        return False

    def drain(self, seconds):
        t0 = time.time()
        self.ws.sock.settimeout(0.3)
        while time.time() - t0 < seconds:
            try:
                self.events.append(json.loads(self.ws.recv()))
            except (socket.timeout, TimeoutError):
                pass
        self.ws.sock.settimeout(60)

    def evaluate(self, expr):
        r = self.call('Runtime.evaluate', {'expression': expr, 'returnByValue': True})
        return (r.get('result') or {}).get('value')

    def close(self):
        try:
            self.call('Browser.close', timeout=5)
        except Exception:
            pass
        self.ws.close()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()


# ======================================================================================
# PDF: מנתח מינימלי למיקומי טקסט (Skia/Chrome: Type0 Identity-H עם ToUnicode)
# ======================================================================================
WS_BYTES = b' \t\r\n\f\x00'
DELIM = b'()<>[]{}/%'


class Ref(tuple):
    pass


class Name(str):
    pass


class Op(str):
    pass


class Lexer:
    def __init__(self, data, pos=0):
        self.d = data
        self.p = pos

    def skip_ws(self):
        d = self.d
        while self.p < len(d):
            c = d[self.p:self.p + 1]
            if c in (b' ', b'\t', b'\r', b'\n', b'\f', b'\x00'):
                self.p += 1
            elif c == b'%':
                while self.p < len(d) and d[self.p:self.p + 1] not in (b'\r', b'\n'):
                    self.p += 1
            else:
                break

    def token(self):
        self.skip_ws()
        d = self.d
        if self.p >= len(d):
            return None
        c = d[self.p:self.p + 1]
        if c == b'<' and d[self.p:self.p + 2] == b'<<':
            self.p += 2
            return '<<'
        if c == b'>' and d[self.p:self.p + 2] == b'>>':
            self.p += 2
            return '>>'
        if c in (b'[', b']', b'{', b'}'):
            self.p += 1
            return c.decode()
        if c == b'/':
            s = self.p + 1
            self.p = s
            while self.p < len(d) and d[self.p:self.p + 1] not in WS_BYTES and d[self.p:self.p + 1] not in DELIM:
                self.p += 1
            raw = d[s:self.p]
            raw = re.sub(rb'#([0-9A-Fa-f]{2})', lambda m: bytes([int(m.group(1), 16)]), raw)
            return Name(raw.decode('latin-1'))
        if c == b'(':
            return self._literal()
        if c == b'<':
            e = d.index(b'>', self.p)
            hx = re.sub(rb'\s', b'', d[self.p + 1:e])
            if len(hx) % 2:
                hx += b'0'
            self.p = e + 1
            return bytes.fromhex(hx.decode())
        s = self.p
        while self.p < len(d) and d[self.p:self.p + 1] not in WS_BYTES and d[self.p:self.p + 1] not in DELIM:
            self.p += 1
        if self.p == s:
            self.p += 1
            return Op(d[s:self.p].decode('latin-1'))
        w = d[s:self.p]
        try:
            return int(w)
        except ValueError:
            try:
                return float(w)
            except ValueError:
                return Op(w.decode('latin-1'))

    def _literal(self):
        d = self.d
        self.p += 1
        out = bytearray()
        depth = 1
        esc = {b'n': 10, b'r': 13, b't': 9, b'b': 8, b'f': 12, b'(': 40, b')': 41, b'\\': 92}
        while self.p < len(d):
            c = d[self.p:self.p + 1]
            if c == b'\\':
                n = d[self.p + 1:self.p + 2]
                if n in esc:
                    out.append(esc[n])
                    self.p += 2
                elif n in (b'\r', b'\n'):
                    self.p += 2
                    if n == b'\r' and d[self.p:self.p + 1] == b'\n':
                        self.p += 1
                elif re.match(rb'[0-7]', n):
                    m = re.match(rb'[0-7]{1,3}', d[self.p + 1:self.p + 4])
                    out.append(int(m.group(0), 8) & 0xFF)
                    self.p += 1 + len(m.group(0))
                else:
                    self.p += 1
            elif c == b'(':
                depth += 1
                out += c
                self.p += 1
            elif c == b')':
                depth -= 1
                self.p += 1
                if depth == 0:
                    break
                out += c
            else:
                out += c
                self.p += 1
        return bytes(out)

    def obj(self, tok=None):
        """אובייקט PDF שלם (מילון, מערך, הפניה N G R)."""
        t = self.token() if tok is None else tok
        if t == '<<':
            dct = {}
            while True:
                k = self.token()
                if k == '>>' or k is None:
                    return dct
                dct[k] = self.obj()
        if t == '[':
            arr = []
            while True:
                k = self.token()
                if k == ']' or k is None:
                    return arr
                arr.append(self.obj(k))
        if isinstance(t, int):
            save = self.p
            t2 = self.token()
            if isinstance(t2, int):
                t3 = self.token()
                if t3 == 'R':
                    return Ref((t, t2))
            self.p = save
        return t


class PDF:
    def __init__(self, data):
        self.d = data
        self.offsets = {}
        for m in re.finditer(rb'(?<![0-9])(\d+)\s+(\d+)\s+obj\b', data):
            self.offsets[int(m.group(1))] = m.end()
        self.cache = {}

    def get(self, ref):
        if isinstance(ref, Ref):
            n = ref[0]
            if n not in self.cache:
                lx = Lexer(self.d, self.offsets[n])
                o = lx.obj()
                if isinstance(o, dict):
                    lx.skip_ws()
                    if self.d[lx.p:lx.p + 6] == b'stream':
                        p = lx.p + 6
                        if self.d[p:p + 2] == b'\r\n':
                            p += 2
                        elif self.d[p:p + 1] in (b'\n', b'\r'):
                            p += 1
                        ln = self.get(o.get('Length'))
                        raw = self.d[p:p + ln] if isinstance(ln, int) else self.d[p:self.d.index(b'endstream', p)]
                        o = dict(o)
                        o['__stream__'] = raw
                self.cache[n] = o
            return self.cache[n]
        return ref

    def stream(self, o):
        o = self.get(o)
        raw = o.get('__stream__', b'')
        f = self.get(o.get('Filter'))
        filters = f if isinstance(f, list) else ([f] if f else [])
        for fl in filters:
            if fl == 'FlateDecode':
                raw = zlib.decompress(raw)
        return raw

    def pages(self):
        root = next(self.get(Ref((n, 0))) for n in self.offsets
                    if isinstance(self.get(Ref((n, 0))), dict) and self.get(Ref((n, 0))).get('Type') == 'Catalog')
        out = []

        def walk(node, inherited):
            node = self.get(node)
            res = node.get('Resources', inherited.get('Resources'))
            mb = node.get('MediaBox', inherited.get('MediaBox'))
            if node.get('Type') == 'Pages':
                for k in self.get(node.get('Kids')) or []:
                    walk(k, {'Resources': res, 'MediaBox': mb})
            else:
                out.append({'node': node, 'Resources': self.get(res) or {}, 'MediaBox': [self.get(x) for x in self.get(mb)]})
        walk(root.get('Pages'), {})
        return out


def _cmap(data):
    m = {}
    text = data.decode('latin-1')
    for blk in re.findall(r'beginbfchar(.*?)endbfchar', text, re.S):
        for a, b in re.findall(r'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>', blk):
            m[int(a, 16)] = bytes.fromhex(b).decode('utf-16-be', 'replace')
    for blk in re.findall(r'beginbfrange(.*?)endbfrange', text, re.S):
        for a, b, c in re.findall(r'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*(<[0-9A-Fa-f]+>|\[[^\]]*\])', blk):
            lo, hi = int(a, 16), int(b, 16)
            if c.startswith('['):
                vals = re.findall(r'<([0-9A-Fa-f]+)>', c)
                for i, v in enumerate(vals):
                    m[lo + i] = bytes.fromhex(v).decode('utf-16-be', 'replace')
            else:
                base = int(c[1:-1], 16)
                for i in range(hi - lo + 1):
                    m[lo + i] = chr(base + i) if base + i < 0x110000 else ''
    return m


class Font:
    def __init__(self, pdf, fd):
        fd = pdf.get(fd) or {}
        self.two_byte = fd.get('Subtype') == 'Type0'
        tu = fd.get('ToUnicode')
        self.cmap = _cmap(pdf.stream(tu)) if tu else {}
        self.widths = {}
        self.dw = 1000.0
        self.scale = 0.001
        self.asc, self.desc = 0.9, -0.22
        desc = None
        if self.two_byte:
            df = pdf.get((pdf.get(fd.get('DescendantFonts')) or [{}])[0])
            self.dw = float(df.get('DW', 1000))
            w = pdf.get(df.get('W')) or []
            i = 0
            while i < len(w):
                c0 = pdf.get(w[i])
                nxt = pdf.get(w[i + 1]) if i + 1 < len(w) else None
                if isinstance(nxt, list):
                    for k, v in enumerate(nxt):
                        self.widths[c0 + k] = float(pdf.get(v))
                    i += 2
                else:
                    c1, v = nxt, pdf.get(w[i + 2])
                    for k in range(c0, c1 + 1):
                        self.widths[k] = float(v)
                    i += 3
            desc = pdf.get(df.get('FontDescriptor'))
        else:
            fc = fd.get('FirstChar', 0)
            for k, v in enumerate(pdf.get(fd.get('Widths')) or []):
                self.widths[fc + k] = float(pdf.get(v))
            fm = pdf.get(fd.get('FontMatrix'))
            if fm:
                self.scale = float(pdf.get(fm[0]))
            desc = pdf.get(fd.get('FontDescriptor'))
        if isinstance(desc, dict):
            a, d = desc.get('Ascent'), desc.get('Descent')
            if isinstance(a, (int, float)) and a:
                self.asc = a / 1000.0
            if isinstance(d, (int, float)) and d:
                self.desc = d / 1000.0

    def codes(self, b):
        if self.two_byte:
            return [(b[i] << 8) | b[i + 1] for i in range(0, len(b) - 1, 2)]
        return list(b)

    def text(self, code):
        if code in self.cmap:
            return self.cmap[code]
        return '' if self.two_byte else chr(code)

    def width(self, code):
        return self.widths.get(code, self.dw if self.two_byte else 500.0) * self.scale


def _mul(m1, m2):
    a, b, c, d, e, f = m1
    A, B, C, D, E, F = m2
    return (a * A + b * C, a * B + b * D, c * A + d * C, c * B + d * D, e * A + f * C + E, e * B + f * D + F)


def _pt(m, x, y):
    return (m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5])


def page_runs(pdf, page):
    """רשימת ריצות טקסט: {text, x0, top, x1, bottom} בנקודות, ראשית בפינה השמאלית העליונה."""
    H = float(page['MediaBox'][3]) - float(page['MediaBox'][1])
    contents = pdf.get(page['node'].get('Contents'))
    parts = contents if isinstance(contents, list) else [contents]
    data = b'\n'.join(pdf.stream(c) for c in parts if c is not None)
    runs = []
    fonts = {}

    def font(res, name):
        key = (id(res), name)
        if key not in fonts:
            fd = (pdf.get(res.get('Font')) or {}).get(name)
            fonts[key] = Font(pdf, fd) if fd else None
        return fonts[key]

    def run_stream(data, res, ctm0):
        lx = Lexer(data)
        stack, ops = [], []
        gs = {'ctm': ctm0}
        gstack = []
        tm = tlm = (1, 0, 0, 1, 0, 0)
        f, size, tc, tw, th, tl, rise = None, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0
        marked = []
        while True:
            t = lx.token()
            if t is None:
                break
            if t in ('<<', '['):
                stack.append(lx.obj(t))
                continue
            if not isinstance(t, Op) or t in ('true', 'false', 'null'):
                stack.append(t)
                continue
            op = str(t)
            a = stack
            stack = []
            if op == 'q':
                gstack.append(dict(gs))
            elif op == 'Q':
                gs = gstack.pop() if gstack else gs
            elif op == 'cm':
                gs['ctm'] = _mul(tuple(float(x) for x in a[-6:]), gs['ctm'])
            elif op == 'BT':
                tm = tlm = (1, 0, 0, 1, 0, 0)
            elif op == 'Tf':
                f, size = font(res, a[-2]), float(a[-1])
            elif op == 'Tm':
                tm = tlm = tuple(float(x) for x in a[-6:])
            elif op in ('Td', 'TD'):
                tx, ty = float(a[-2]), float(a[-1])
                if op == 'TD':
                    tl = -ty
                tm = tlm = _mul((1, 0, 0, 1, tx, ty), tlm)
            elif op == 'T*':
                tm = tlm = _mul((1, 0, 0, 1, 0, -tl), tlm)
            elif op == 'TL':
                tl = float(a[-1])
            elif op == 'Tc':
                tc = float(a[-1])
            elif op == 'Tw':
                tw = float(a[-1])
            elif op == 'Tz':
                th = float(a[-1]) / 100.0
            elif op == 'Ts':
                rise = float(a[-1])
            elif op in ('BMC', 'BDC'):
                tag = a[0] if a else ''
                marked.append(tag)
            elif op == 'EMC':
                if marked:
                    marked.pop()
            elif op == 'Do' and a:
                xo = (pdf.get(res.get('XObject')) or {}).get(a[-1])
                xo_d = pdf.get(xo) if xo else None
                if isinstance(xo_d, dict) and xo_d.get('Subtype') == 'Form':
                    mtx = tuple(float(pdf.get(x)) for x in (pdf.get(xo_d.get('Matrix')) or [1, 0, 0, 1, 0, 0]))
                    run_stream(pdf.stream(xo), pdf.get(xo_d.get('Resources')) or res, _mul(mtx, gs['ctm']))
            elif op in ('Tj', 'TJ', "'", '"'):
                if op in ("'", '"'):
                    tm = tlm = _mul((1, 0, 0, 1, 0, -tl), tlm)
                items = a[-1] if op == 'TJ' else [a[-1]]
                if f is None or not isinstance(items, list):
                    continue
                txt, adv = [], 0.0
                for it in items:
                    if isinstance(it, (int, float)):
                        adv -= it / 1000.0 * size * th
                    elif isinstance(it, bytes):
                        for code in f.codes(it):
                            txt.append(f.text(code))
                            w = f.width(code) * size + tc
                            if not f.two_byte and code == 32:
                                w += tw
                            adv += w * th
                s = ''.join(txt)
                if 'ReversedChars' in marked:
                    s = s[::-1]
                m = _mul(tm, gs['ctm'])
                ys = (rise + f.desc * size, rise + f.asc * size)
                pts = [_pt(m, x, y) for x in (0, adv) for y in ys]
                xs = [p[0] for p in pts]
                yv = [p[1] for p in pts]
                if s.strip():
                    runs.append({'text': s, 'x0': min(xs), 'x1': max(xs), 'top': H - max(yv), 'bottom': H - min(yv)})
                tm = _mul((1, 0, 0, 1, adv, 0), tm)
            elif op == 'BI':
                e = data.find(b'EI', lx.p)
                lx.p = e + 2 if e >= 0 else len(data)

    run_stream(data, page['Resources'], (1, 0, 0, 1, 0, 0))
    return runs, H


def pdf_layout(pdf_bytes):
    pdf = PDF(pdf_bytes)
    out = []
    for pg in pdf.pages():
        runs, H = page_runs(pdf, pg)
        mb = [float(x) for x in pg['MediaBox']]
        out.append({'size': (round(mb[2] - mb[0]), round(mb[3] - mb[1])), 'runs': runs})
    return out


# ======================================================================================
# ניתוח הפריסה
# ======================================================================================
def _ns(s):
    s = re.sub(r'[\s\u200e\u200f\u202a-\u202e\u2066-\u2069]', '', s or '')
    return s.replace('"', '״').replace('״', '״').replace("'", '׳')


def lines_of(runs, tol=2.0):
    """קיבוץ ריצות לשורות לפי קו הבסיס."""
    lines = []
    for r in sorted(runs, key=lambda r: (r['bottom'], -r['x1'])):
        for ln in lines:
            if abs(ln['bottom'] - r['bottom']) <= tol:
                ln['runs'].append(r)
                ln['top'] = min(ln['top'], r['top'])
                break
        else:
            lines.append({'bottom': r['bottom'], 'top': r['top'], 'runs': [r]})
    for ln in lines:
        rtl = sorted(ln['runs'], key=lambda r: -r['x1'])
        ln['rtl'] = ''.join(r['text'] for r in rtl)
        ln['ltr'] = ''.join(r['text'] for r in reversed(rtl))
        ln['x0'] = min(r['x0'] for r in ln['runs'])
        ln['x1'] = max(r['x1'] for r in ln['runs'])
    return lines


def is_band_line(ln, marker_ns):
    for s in (ln['rtl'], ln['ltr']):
        v = _ns(s)
        if len(v) >= 12 and v in marker_ns:
            return True
    parts = [_ns(r['text']) for r in ln['runs'] if len(_ns(r['text'])) >= 2]
    return bool(parts) and sum(map(len, parts)) >= 20 and all(p in marker_ns for p in parts)


def analyse(layout, marker, headings=HEADINGS, appendix_titles=APPENDIX_TITLES):
    marker_ns = _ns(marker)
    heads_ns = {_ns(h): h for h in headings}
    app_ns = [_ns(a) for a in appendix_titles]
    res = {'pages': len(layout), 'page_sizes': sorted({tuple(p['size']) for p in layout}),
           'appendix_page': None, 'band_lines': 0, 'overlaps': [], 'heading_overlaps': [],
           'first_page_runs': len(layout[0]['runs']) if layout else 0, 'band_on_pages': 0}
    for pno, page in enumerate(layout, 1):
        lines = lines_of(page['runs'])
        if res['appendix_page'] is None and any(a in _ns(ln['rtl']) or a in _ns(ln['ltr'])
                                                for ln in lines for a in app_ns):
            res['appendix_page'] = pno
        # שורת סימון מזוהה ברמת הריצה: גם כשהפס יושב על אותו קו בסיס כמו תוכן (position:fixed), הריצות שהן
        # חלק מטקסט הסימון נפרדות משאר הריצות בשורה.
        band = []
        for ln in lines:
            cands = [r for r in ln['runs'] if len(_ns(r['text'])) >= 2 and _ns(r['text']) in marker_ns]
            if not cands:
                continue
            rtl = sorted(cands, key=lambda r: -r['x1'])
            pseudo = {'runs': cands, 'rtl': ''.join(r['text'] for r in rtl),
                      'ltr': ''.join(r['text'] for r in reversed(rtl)),
                      'top': min(r['top'] for r in cands), 'bottom': max(r['bottom'] for r in cands)}
            if is_band_line(pseudo, marker_ns):
                # ריצות של אות אחת (Skia מפצל לפעמים שם לטיני) שייכות לפס כשהן חלק מטקסט הסימון
                pseudo['runs'] = [r for r in ln['runs'] if _ns(r['text']) in marker_ns]
                band.append(pseudo)
        res['band_lines'] += len(band)
        if band:
            res['band_on_pages'] += 1
        # אזורי הפס: שורות סימון רצופות (מרווח עד 6 נקודות) הן אזור אחד
        zones = []
        for ln in sorted(band, key=lambda x: x['top']):
            if zones and ln['top'] - zones[-1][1] <= 6:
                zones[-1][1] = max(zones[-1][1], ln['bottom'])
            else:
                zones.append([ln['top'], ln['bottom']])
        zones = [(z0 - BAND_PAD, z1 + BAND_PAD) for z0, z1 in zones]
        band_ids = {id(r) for ln in band for r in ln['runs']}
        for ln in lines:
            for r in ln['runs']:
                if id(r) in band_ids:
                    continue
                for z0, z1 in zones:
                    ov = min(r['bottom'], z1) - max(r['top'], z0)
                    if ov >= OVERLAP_MIN:
                        item = {'page': pno, 'text': r['text'][:60], 'top': round(r['top'], 1),
                                'bottom': round(r['bottom'], 1), 'band': [round(z0, 1), round(z1, 1)]}
                        res['overlaps'].append(item)
                        lt = _ns(ln['rtl'])
                        for hn, h in heads_ns.items():
                            if hn and (hn == lt or hn == _ns(r['text']) or (len(hn) > 6 and hn in lt)):
                                res['heading_overlaps'].append({'page': pno, 'heading': h})
                                break
                        break
    res['body_pages'] = (res['appendix_page'] - 1) if res['appendix_page'] else res['pages']
    res['appendix_pages'] = (res['pages'] - res['body_pages'])
    return res


# ======================================================================================
# ההרצה
# ======================================================================================
JS_INFO = r"""(function(){
 const c=document.body?document.body.cloneNode(true):null;
 if(c) c.querySelectorAll('script,style,template').forEach(x=>x.remove());
 const full=c?c.textContent.replace(/\s+/g,' ').trim():'';
 return JSON.stringify({title:document.title, dom_text_chars:full.length,
   visible_text_chars:(document.body&&document.body.innerText||'').length, text:full.slice(0,200000)});
})()"""


def run_check(html_path, out_dir, marker, browser=None, markers=None, twice=False, body_limit=BODY_PAGE_LIMIT):
    exe = browser or find_browser()
    if not exe:
        return {'verdict': 'NO_BROWSER', 'exit': 3}
    os.makedirs(out_dir, exist_ok=True)
    prof = tempfile.mkdtemp(prefix='areo_rc_')
    url = Path(os.path.abspath(html_path)).as_uri()
    res = {'browser': os.path.basename(exe), 'url_scheme': url[:7]}
    br = None
    try:
        br = Browser(exe, prof)
        for m in ('Network.enable', 'Runtime.enable', 'Page.enable', 'Log.enable'):
            br.call(m)
        br.call('Page.navigate', {'url': url})
        br.wait_event('Page.loadEventFired', 30)
        br.drain(1.5)
        info = json.loads(br.evaluate(JS_INFO) or '{}')
        text = info.pop('text', '')
        res.update(info)
        want = markers if markers is not None else DEFAULT_MARKERS
        res['markers_missing'] = [m for m in want if m not in text]
        reqs = [e['params']['request']['url'] for e in br.events if e.get('method') == 'Network.requestWillBeSent']
        res['requests_total'] = len(reqs)
        res['external_requests'] = [u[:120] for u in reqs if not re.match(r'^(file|data|blob|about|chrome|devtools):', u)]
        res['js_exceptions'] = [((e['params'].get('exceptionDetails') or {}).get('exception') or {}).get('description')
                                or (e['params'].get('exceptionDetails') or {}).get('text')
                                for e in br.events if e.get('method') == 'Runtime.exceptionThrown']
        pdf = base64.b64decode(br.call('Page.printToPDF', {'preferCSSPageSize': True, 'printBackground': True,
                                                           'displayHeaderFooter': False}, timeout=120)['data'])
        pdf_path = os.path.join(out_dir, 'render_check.pdf')
        with open(pdf_path, 'wb') as fh:
            fh.write(pdf)
        res['pdf'] = pdf_path
        lay = analyse(pdf_layout(pdf), marker)
        res.update(lay)
        if twice:
            br.call('Page.reload', {'ignoreCache': False})
            br.drain(2.5)
            pdf2 = base64.b64decode(br.call('Page.printToPDF', {'preferCSSPageSize': True, 'printBackground': True},
                                            timeout=120)['data'])
            lay2 = analyse(pdf_layout(pdf2), marker)
            res['second_print'] = {'pages': lay2['pages'], 'body_pages': lay2['body_pages'],
                                   'first_page_runs': lay2['first_page_runs']}
    finally:
        if br:
            br.close()
        shutil.rmtree(prof, ignore_errors=True)
    fails = []
    if res.get('dom_text_chars', 0) < 500:
        fails.append('blank')
    if not str(res.get('title') or '').startswith('Areo Workspace'):
        fails.append('title')
    if res.get('markers_missing'):
        fails.append('markers')
    if res.get('js_exceptions'):
        fails.append('js_exceptions')
    if res.get('external_requests'):
        fails.append('external_requests')
    if res.get('page_sizes') and any(abs(w - A4[0]) > 2 or abs(h - A4[1]) > 2 for w, h in res['page_sizes']):
        fails.append('not_a4')
    if not res.get('first_page_runs'):
        fails.append('first_page_blank')
    if res.get('band_lines', 0) == 0:
        fails.append('no_band')
    if res.get('overlaps'):
        fails.append('band_overlap')
    sp = res.get('second_print')
    if sp and (sp['pages'] != res['pages'] or not sp['first_page_runs']):
        fails.append('second_print_differs')
    over = res.get('body_pages', 0) > body_limit
    if over:
        fails.append('body_pages>%d' % body_limit)
    res['fails'] = fails
    res['verdict'] = 'PASS' if not fails else 'FAIL'
    res['exit'] = 0 if not fails else (2 if over and fails == ['body_pages>%d' % body_limit] else 1)
    return res


def main(argv=None):
    ap = parser('Areo risk report render check', out_required=True,
                out_help='תיקיית הפלט (העמוד, render_check.json). לעולם לא תיקיית מקור של הלקוח')
    ap.add_argument('--template')
    ap.add_argument('--register')
    ap.add_argument('--html')
    ap.add_argument('--browser')
    ap.add_argument('--marker', help='טקסט הסימון; ברירת מחדל: נגזר מהמרשם')
    ap.add_argument('--twice', action='store_true')
    ap.add_argument('--kind', choices=sorted(KINDS), help='risk (ברירת מחדל) או entity: מציין, סמנים וגבול עמודים')
    ap.add_argument('--body-limit', type=int)
    ap.add_argument('--placeholder', help='בדוח חקר ישות: __ENTITY_DATA__ (או --kind entity)')
    ap.add_argument('--markers', help='מחרוזות חובה מופרדות בפסיק')
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding='utf-8')
    kind = a.kind or ('entity' if a.placeholder == ENTITY_PLACEHOLDER else 'risk')
    K = KINDS[kind]
    a.placeholder = a.placeholder or K['placeholder']
    a.body_limit = a.body_limit if a.body_limit is not None else K['body_limit']
    markers = [m.strip() for m in a.markers.split(',')] if a.markers else K['markers']
    inputs = [x for x in (a.template, a.register, a.html) if x]
    guard_out(a.out, inputs)
    if a.template and a.register:
        tpl = open(a.template, encoding='utf-8').read()
        reg = json.load(open(a.register, encoding='utf-8'))
        st = static_checks(tpl)
        html = build_report(tpl, reg, a.placeholder)
        os.makedirs(a.out, exist_ok=True)
        page = guard_out(os.path.join(a.out, 'Areo Workspace - %s.html' % K['name']), inputs)
        with open(page, 'w', encoding='utf-8') as fh:
            fh.write(html)
        marker = a.marker or band_text_from_register(reg)
    elif a.html:
        page = a.html
        html = open(page, encoding='utf-8').read()
        st = static_checks(html)
        m = re.search(r'const DATA = (\{.*?\});\n', html, re.S)
        marker = a.marker or (band_text_from_register(json.loads(m.group(1).replace('<\\/', '</'))) if m else HE_DRAFT)
    else:
        ap.error('--template ו---register, או --html')
    res = run_check(page, a.out, marker, browser=a.browser, markers=markers, twice=a.twice, body_limit=a.body_limit)
    res['static_problems'] = st
    if st and res.get('verdict') == 'PASS':
        res['verdict'], res['exit'] = 'FAIL', 1
        res['fails'] = res.get('fails', []) + ['static']
    show = {k: v for k, v in res.items() if k not in ('overlaps',)}
    show['overlaps_count'] = len(res.get('overlaps') or [])
    show['overlaps_sample'] = (res.get('overlaps') or [])[:8]
    print(json.dumps(show, ensure_ascii=False, indent=1))
    with open(guard_out(os.path.join(a.out, 'render_check.json'), inputs), 'w', encoding='utf-8') as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    return res['exit']


if __name__ == '__main__':
    sys.exit(run(main))
