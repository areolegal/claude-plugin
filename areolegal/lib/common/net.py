# -*- coding: utf-8 -*-
"""common/net.py: שכבת הגישה האחת לרשת, לכל רכיב שיוצא לרשת (מעריך הסיכונים, בונה הפלייבוק).

הבעיה (סבב 3): אין בחבילה שכבת רשת, וכל רץ כתב שולף משלו (שבעה שולפים, שבע מדיניות). ב-C1 הבקשה הראשונה
לנבו נשלחה עם מחרוזת user-agent של דפדפן, והבקשה הבאה החזירה 403 "כתובת IP חסומה"; אחר כך גם C2 נחסם.
מהנדס הסקילים 13, המנהל המסחרי 7, מנכ"ל 12, השותף הבכיר 13; סיכום C1, פרק 7.

הכללים (הערות מעריך הסיכונים 3.6; הכללים המשותפים 3.5, איסור 2.25; גרסה 1.2.0 של החבילה):
1. מזהה אחד, גלוי ומזוהה, לכל בקשה, לפי בקשת הגישה ההוגנת של SEC EDGAR (שם הארגון וכתובת קשר):
   USER_AGENT = "AreoLegal-research/<גרסה> (AreoLegal automated legal research; contact: <email>)". לעולם לא
   מזהה דפדפן, ואין פרמטר לכותרות. הערך היחיד שאפשר לקבוע הוא כתובת הקשר, מהתצורה: configure(contact_email),
   משתנה הסביבה AREO_CONTACT_EMAIL, או "contact_email" בקובץ config.json שבשורש החבילה. בלי כתובת קשר
   תקינה אין בקשה יוצאת (refused).
2. קצב: מרווח מינימלי בין בקשות לאותו דומיין רשום (MIN_INTERVAL; בנבו 10 שניות), ותקרת בקשות לדומיין בהרצה.
3. חסימה: 401, 403, 407, 429, 451, או דף אתגר שחוזר בקוד 2xx (CAPTCHA, Cloudflare, Incapsula, "verify you are
   human", דף ה-anomaly של DuckDuckGo בקוד 202, וכל קוד 2xx חריג, כמו 247 של הכנסת) -> עוצרים. אין ניסיון
   חוזר, אין החלפת מזהה, אין שרת מתווך. הדומיין הרשום (registrable_domain: knesset.gov.il, ולא
   main.knesset.gov.il) מסומן חסום עד סוף ההרצה, ובקשה נוספת אליו, מכל מארח שלו, אינה יוצאת. כשנמסרה תיקיית
   הרצה (start_run(run_dir) או run_dir=), מצב החסימה נשמר בה (net-blocks.json), ותהליך אחר באותה הרצה קורא
   אותו. התוצאה blocked: True, עם lawyer_task מוכן לפרק 5 (why מתחיל ב"נחסם").
4. שגיאת רשת (ניתוק, פסק זמן): ניסיון חוזר אחד בלבד.
5. רישום: כל קריאה מחזירה log שנכנס כמו שהוא ל-research.search_log או ל-lookups: הזמן (ISO עם היסט),
   הכתובת בלי טוקנים, המטרה, השיטה, הקוד, user_agent, הגודל וה-SHA-256.
6. שמירה: רק דרך EntityStore (store=..., source_id=...), עם התקרות שלו (200 קילובייט לקטע, 2 מגה-בייט לעסקה).
   בלי store שום דבר אינו נכתב לדיסק (חוץ מ-net-blocks.json בתיקיית ההרצה).
7. דומיינים: allowed_domains (למשל הרשימה המורשית של הרכיב) נבדק לפני הבקשה ואחרי הפניות.
   נבו: רק נתיבי נוסח החקיקה (/law_html/, /HakikaSearch.aspx), בקצב איטי.
8. POST (form=...): רק לטופס חיפוש רשמי שמופיע ב-HOST_POLICY[...]['post_paths'] (למשל טופס חיפוש החקיקה של
   נבו), תחת אותם כללים: מזהה, קצב, חסימה, דומיינים מורשים ורישום.
9. client_detail_in_query(query): פרט של הלקוח בשאילתה (מספר חברה או זהות עם ספרת ביקורת תקינה, טלפון, מספר
   ארוך בלי הקשר רשמי). מזהה רשמי של חוק או תקנה (CELEX, LawItemId, ס"ח, ק"ת, U.S.C., CFR) אינו פרט של הלקוח.

הממשק: fetch(url, purpose, ...) -> dict(status, text|None, blocked, reason, ...). ספרייה סטנדרטית בלבד.
הבדיקות: שרת HTTP מקומי או opener מדומה בלבד; אין בהן גישה לרשת.
"""
import hashlib
import ipaddress
import json
import os
import re
import socket
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from urllib.parse import urlencode, urlsplit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _version():
    try:
        with open(os.path.join(ROOT, 'VERSION'), encoding='utf-8') as fh:
            return fh.read().strip() or '1.2.0'
    except OSError:
        return '1.2.0'


VERSION = _version()
ORG = 'AreoLegal'
UA_PREFIX = 'AreoLegal-research/'
UA_FORMAT = UA_PREFIX + '%s (' + ORG + ' automated legal research; contact: %s)'
BROWSER_UA = re.compile(r'Mozilla/|Chrome/|Safari/|Firefox/|Edg/|Gecko', re.I)
UA_CONTACT = re.compile(r'contact: [A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\)$')
CONTACT_ENV = 'AREO_CONTACT_EMAIL'
CONFIG_PATH = os.path.join(ROOT, 'config.json')
_EMAIL = re.compile(r'^[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}$')

MIN_INTERVAL = 2.0          # שניות בין בקשות לאותו דומיין רשום
MAX_PER_HOST = 30           # בקשות לכל דומיין רשום בהרצה אחת
MAX_BYTES = 100 * 1024 * 1024
TIMEOUT = 30
BLOCK_CODES = {401, 403, 407, 429, 451}
OK_2XX = {200, 201, 203, 204, 206}   # כל קוד 2xx אחר (202 של DuckDuckGo, 247 של הכנסת) הוא דף אתגר
HOST_POLICY = {
    'nevo.co.il': {'paths': ('/law_html/', '/HakikaSearch.aspx'), 'post_paths': ('/HakikaSearch.aspx',),
                   'min_interval': 10.0, 'max_requests': 10},
}
CHALLENGE = re.compile(
    r'cf-chl|challenge-platform|cf_chl_opt|Attention Required! \| Cloudflare|<title>\s*Just a moment|'
    r'_Incapsula_Resource|Incapsula incident|Request unsuccessful\. Incapsula|g-recaptcha|h-captcha|hcaptcha\.com|'
    r'<title>[^<]*(?:captcha|access denied|are you a robot)[^<]*</title>|perimeterx|px-captcha|datadome|'
    r'verify (?:that )?you(?: a|\')re (?:a )?human|are you a human|confirm you are human|i\'m not a robot|'
    r'(?:id|name|class)=["\'][^"\']*captcha|anomaly-modal|anomaly\.js|bots use DuckDuckGo too|'
    r'אנא אמת(?:ו)? שאינך רובוט|אימות אנושי',
    re.I)
BLOCKS_FILE = 'net-blocks.json'
# סיומות של שני רכיבים (רשימה מצומצמת, לחישוב הדומיין הרשום בלי ספרייה חיצונית)
MULTI_SUFFIX = {'co.il', 'org.il', 'gov.il', 'ac.il', 'net.il', 'muni.il', 'idf.il', 'k12.il',
                'co.uk', 'org.uk', 'gov.uk', 'ac.uk', 'ltd.uk', 'plc.uk', 'net.uk', 'sch.uk', 'nhs.uk', 'police.uk',
                'com.au', 'gov.au', 'org.au', 'net.au', 'edu.au', 'co.nz', 'govt.nz', 'co.jp', 'go.jp', 'or.jp',
                'com.br', 'gov.br', 'co.in', 'gov.in', 'co.za', 'gov.za', 'com.cn', 'gov.cn', 'com.sg', 'gov.sg',
                'com.hk', 'gov.hk', 'europa.eu'}

# מצב ההרצה: מתי נשלחה הבקשה האחרונה לכל דומיין רשום, כמה נשלחו, ואילו דומיינים חסמו
_last = {}
_count = {}
_blocked = {}
_run = {'dir': None}
_contact = {'email': None}
_clock = time.monotonic
_sleep = time.sleep
USER_AGENT = None


def _set_contact(email):
    global USER_AGENT
    email = (email or '').strip()
    _contact['email'] = email if _EMAIL.match(email) else None
    USER_AGENT = UA_FORMAT % (VERSION, _contact['email']) if _contact['email'] else None
    return USER_AGENT


def configure(contact_email=None, config_path=None):
    """קובע את כתובת הקשר של המזהה, הערך היחיד שאפשר לקבוע בו. הסדר: הארגומנט, משתנה הסביבה
    AREO_CONTACT_EMAIL, ואז "contact_email" (או net.contact_email) בקובץ התצורה. מחזיר את USER_AGENT, או None
    כשאין כתובת תקינה (ואז fetch מסרב)."""
    email = contact_email or os.environ.get(CONTACT_ENV)
    if not email:
        try:
            with open(config_path or CONFIG_PATH, encoding='utf-8') as fh:
                cfg = json.load(fh)
            email = cfg.get('contact_email') or (cfg.get('net') or {}).get('contact_email')
        except (OSError, ValueError, AttributeError):
            email = None
    return _set_contact(email)


def user_agent():
    return USER_AGENT


configure()


def registrable_domain(host):
    """הדומיין הרשום: main.knesset.gov.il -> knesset.gov.il; www.nevo.co.il -> nevo.co.il. כתובת IP: כמו שהיא."""
    host = (host or '').lower().strip('.')
    try:
        ipaddress.ip_address(host)
        return host
    except ValueError:
        pass
    labels = host.split('.')
    if len(labels) <= 2:
        return host
    n = 3 if '.'.join(labels[-2:]) in MULTI_SUFFIX else 2
    return '.'.join(labels[-n:])


def _blocks_path(run_dir):
    return os.path.join(run_dir, BLOCKS_FILE)


def _load_blocks(run_dir):
    if not run_dir:
        return
    try:
        with open(_blocks_path(run_dir), encoding='utf-8') as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return
    for dom, rec in (data.get('blocked') or {}).items():
        _blocked.setdefault(dom, rec.get('why') if isinstance(rec, dict) else str(rec))


def _save_blocks(run_dir):
    if not run_dir:
        return
    os.makedirs(run_dir, exist_ok=True)
    p = _blocks_path(run_dir)
    tmp = p + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump({'blocked': {d: {'why': w} for d, w in sorted(_blocked.items())}, 'updated_at': now_iso()},
                  fh, ensure_ascii=False, indent=1)
    os.replace(tmp, p)


def start_run(run_dir=None):
    """תחילת הרצה: מאפס את מצב התהליך, וכשנמסרה תיקיית הרצה, קורא ממנה את החסימות של התהליכים הקודמים."""
    reset_session()
    _run['dir'] = run_dir
    _load_blocks(run_dir)


def reset_session():
    """לתחילת הרצה חדשה (ולבדיקות). אינו מוחק את net-blocks.json שבתיקיית ההרצה."""
    _last.clear()
    _count.clear()
    _blocked.clear()
    _run['dir'] = None


def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')


try:  # strip_secrets אחד לכל החבילה
    from risk.entity_store import strip_secrets  # type: ignore
except ImportError:  # pragma: no cover - הרצה כשהשורש אינו ב-sys.path
    sys.path.insert(0, ROOT)
    from risk.entity_store import strip_secrets  # type: ignore


def _host(url):
    return (urlsplit(url).hostname or '').lower()


def _policy(host):
    for dom, pol in HOST_POLICY.items():
        if host == dom or host.endswith('.' + dom):
            return pol
    return {}


def _domain_ok(host, allowed):
    return any(host == a or host.endswith('.' + a) for a in allowed)


def _decode(b, ctype):
    m = re.search(r'charset=([A-Za-z0-9_\-]+)', ctype or '', re.I)
    m2 = re.search(rb'charset=["\']?([A-Za-z0-9_\-]+)', b[:4096])
    encs = ['utf-8'] + ([m.group(1)] if m else []) + ([m2.group(1).decode('ascii', 'ignore')] if m2 else []) + ['cp1255']
    for enc in encs:
        try:
            return b.decode(enc)
        except (LookupError, UnicodeDecodeError):
            continue
    return b.decode('utf-8', 'replace')


def _lawyer_task(host, purpose, why, url):
    return {'item': '%s: %s' % (host, purpose), 'why': why, 'task': 'עורך הדין', 'url': url}


# ---- פרט של הלקוח בשאילתה (גרסה 1.2.0: מזהה רשמי של חוק או תקנה אינו פרט של הלקוח) ----
OFFICIAL_ID = re.compile(
    r'\b[1-9CE]\d{4}[A-Z]{1,2}\d{3,4}\b|'                                  # CELEX
    r'(?:lawitemid|lawid|law_id|celex|docid|billid)\s*[=:]?\s*\d+|'         # מזהה חוק במאגר רשמי
    r'\d+\s*U\.?S\.?C\.?(?:\s*§*\s*\d+)?|\d+\s*C\.?F\.?R\.?(?:\s*(?:Part\s*)?\d+)?|'
    r'Pub(?:lic)?\.?\s*L(?:aw)?\.?\s*(?:No\.?\s*)?\d+[-–]\d+', re.I)
OFFICIAL_CONTEXT = re.compile(
    r'(?:חוק|תקנות|תקנה|צו|פקודת|פקודה|הצעת חוק|ס"ח|ס״ח|ק"ת|ק״ת|י"פ|י״פ|ה"ח|ה״ח|רשומות|קובץ התקנות|'
    r'ספר החוקים|statute|regulation|directive|act|law|section|§)[^\d]{0,25}$', re.I)
PHONE = re.compile(r'(?<!\d)(?:\+972[-\s]?|0)(?:[23489]|5\d|7\d)[-\s]?\d{3}[-\s]?\d{4}(?!\d)')


def _id_check_digit(num):
    if not re.fullmatch(r'\d{9}', num):
        return False
    total = 0
    for i, ch in enumerate(num):
        d = int(ch) * (1 if i % 2 == 0 else 2)
        total += d if d < 10 else d - 9
    return total % 10 == 0


def client_detail_in_query(query, company_names=()):
    """מחזיר את הפרט שנמצא (מחרוזת), או ''. פרט = שם החברה, טלפון, מספר בן 9 ספרות עם ספרת ביקורת תקינה (מספר
    חברה או זהות), או מספר בן 5 ספרות ומעלה בלי הקשר רשמי. מזהה רשמי (CELEX, LawItemId, "ס"ח 2563",
    "ק"ת 8543", "42 U.S.C. 1983", "17 CFR 240") אינו פרט של הלקוח."""
    q = str(query or '')
    for name in company_names or ():
        if name and name in q:
            return name
    m = PHONE.search(q)
    if m:
        return m.group(0)
    masked = OFFICIAL_ID.sub(lambda x: ' ' * len(x.group(0)), q)
    for m in re.finditer(r'\d{5,}', masked):
        num = m.group(0)
        if len(num) == 9 and _id_check_digit(num):
            return num
        if OFFICIAL_CONTEXT.search(masked[:m.start()]):
            continue
        return num
    return ''


def _block(dom, why):
    _blocked[dom] = why
    _save_blocks(_run['dir'])


def fetch(url, purpose, allowed_domains=None, store=None, source_id=None, excerpt=None, timeout=TIMEOUT,
          accept='text/html,application/pdf,application/json,text/csv,application/xml;q=0.9,*/*;q=0.5',
          max_bytes=MAX_BYTES, form=None, run_dir=None, _opener=None):
    """בקשה אחת לפי הכללים שבראש הקובץ: GET, או POST כשנמסר form (dict) לטופס חיפוש רשמי.
    purpose: למה (השאלה ביומן), בלי פרטי הלקוח. run_dir: תיקיית ההרצה, שבה נשמר מצב החסימה.
    מחזיר dict: status (קוד HTTP או None), text (טקסט HTML, JSON או CSV; None ב-PDF, בחסימה ובשגיאה),
    blocked, reason, content (בייטים, או None), content_type, url ו-final_url (בלי טוקנים), sha256, bytes,
    lawyer_task (בחסימה), stored (רשומה ל-raw_copies כשנשמר ב-store), log (שורה ליומן)."""
    if run_dir and run_dir != _run['dir']:
        _run['dir'] = run_dir
        _load_blocks(run_dir)
    clean, removed = strip_secrets(url)
    host = _host(url)
    dom = registrable_domain(host)
    pol = _policy(host)
    method = 'POST' if form is not None else 'GET'
    form_clean = strip_secrets('http://x/?' + urlencode(form, doseq=True))[0].split('?', 1)[-1] if form else ''
    res = {'status': None, 'text': None, 'blocked': False, 'reason': '', 'content': None, 'content_type': '',
           'url': clean, 'final_url': clean, 'url_params_removed': removed, 'sha256': None, 'bytes': 0,
           'lawyer_task': None, 'stored': None, 'method': method}

    def done():
        res['log'] = {'at': now_iso(), 'url': res['url'], 'final_url': res['final_url'], 'purpose': purpose,
                      'method': method, 'status': res['status'], 'blocked': res['blocked'], 'reason': res['reason'],
                      'user_agent': USER_AGENT, 'bytes': res['bytes'], 'sha256': res['sha256'], 'via': 'common.net'}
        if form_clean:
            res['log']['form'] = form_clean
        return res

    if not USER_AGENT:
        res['reason'] = ('refused: אין כתובת קשר במזהה. לקבוע contact_email בתצורה (configure, %s או config.json)'
                         % CONTACT_ENV)
        return done()
    if not purpose or not str(purpose).strip():
        res['reason'] = 'refused: חסרה מטרה (purpose)'
        return done()
    if urlsplit(url).scheme not in ('http', 'https') or not host:
        res['reason'] = 'refused: כתובת שאינה http או https'
        return done()
    if allowed_domains is not None and not _domain_ok(host, allowed_domains):
        res['reason'] = 'refused: דומיין שאינו ברשימה המורשית (%s)' % host
        return done()
    path = urlsplit(url).path
    if pol.get('paths') and not any(path.startswith(p) for p in pol['paths']):
        res['reason'] = 'refused: ב-%s רק הנתיבים %s' % (dom, ', '.join(pol['paths']))
        return done()
    if form is not None and not any(path.startswith(p) for p in pol.get('post_paths', ())):
        res['reason'] = 'refused: POST רק לטופס חיפוש רשמי שברשימה (HOST_POLICY post_paths)'
        return done()
    if dom in _blocked:
        res['blocked'] = True
        res['reason'] = 'blocked earlier in this run: %s (אין ניסיון חוזר)' % _blocked[dom]
        res['lawyer_task'] = _lawyer_task(dom, purpose, 'נחסם: ' + _blocked[dom], clean)
        return done()
    if _count.get(dom, 0) >= pol.get('max_requests', MAX_PER_HOST):
        res['reason'] = 'refused: תקרת הבקשות ל-%s בהרצה הזו' % dom
        return done()
    # קצב
    gap = pol.get('min_interval', MIN_INTERVAL)
    if dom in _last:
        wait = _last[dom] + gap - _clock()
        if wait > 0:
            _sleep(wait)
    headers = {'User-Agent': USER_AGENT, 'Accept': accept}
    data = None
    if form is not None:
        data = urlencode(form, doseq=True).encode('utf-8')
        headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=utf-8'
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    opener = _opener or urllib.request.build_opener()
    body, status, ctype, final = None, None, '', url
    for attempt in (1, 2):   # ניסיון חוזר אחד, רק אחרי שגיאת רשת
        _last[dom] = _clock()
        _count[dom] = _count.get(dom, 0) + 1
        try:
            with opener.open(req, timeout=timeout) as resp:
                status = resp.getcode()
                ctype = resp.headers.get('Content-Type', '')
                final = resp.geturl() or url
                body = resp.read(max_bytes + 1)
            break
        except urllib.error.HTTPError as e:
            status = e.code
            ctype = e.headers.get('Content-Type', '') if e.headers else ''
            try:
                body = e.read(200000)
            except Exception:
                body = b''
            # geturl() נכשל ב-KeyError כש-HTTPError נבנה בלי גוף תשובה
            # (fp=None), וזה בדיוק מצב החסימה שהפונקציה מטפלת בו.
            # תיקון מקומי של ניל, דווח לענבל
            final = getattr(e, 'filename', None) or url
            retry_after = e.headers.get('Retry-After') if e.headers else None
            if status in BLOCK_CODES:
                why = '%d%s' % (status, ', Retry-After %s' % retry_after if retry_after else '')
                _block(dom, why)
                res.update(status=status, blocked=True, reason='blocked: HTTP %s' % why,
                           lawyer_task=_lawyer_task(dom, purpose, 'נחסם (%s)' % why, clean))
                res['final_url'] = strip_secrets(final)[0]
                return done()
            res.update(status=status, reason='http_error: %d' % status)
            res['final_url'] = strip_secrets(final)[0]
            return done()
        except (urllib.error.URLError, socket.timeout, ConnectionError, OSError) as e:
            if attempt == 2:
                res['reason'] = 'network_error: %s' % (getattr(e, 'reason', None) or e)
                return done()
            _sleep(gap)
    res['status'] = status
    res['content_type'] = ctype
    res['final_url'] = strip_secrets(final)[0]
    fhost = _host(final)
    if allowed_domains is not None and not _domain_ok(fhost, allowed_domains):
        res['reason'] = 'refused: הפניה לדומיין שאינו ברשימה (%s)' % fhost
        return done()
    if body is not None and len(body) > max_bytes:
        res['reason'] = 'refused: מעל %d בתים' % max_bytes
        return done()
    body = body or b''
    if status is not None and 200 <= status < 300 and status not in OK_2XX:
        _block(dom, 'challenge %d' % status)
        res.update(blocked=True, reason='blocked: דף אתגר בקוד %d (קוד 2xx חריג)' % status,
                   lawyer_task=_lawyer_task(dom, purpose, 'נחסם (CAPTCHA, קוד %d)' % status, clean))
        return done()
    head = body[:300000].decode('utf-8', 'ignore') if not body[:5] == b'%PDF-' else ''
    if head and CHALLENGE.search(head):
        _block(dom, 'CAPTCHA')
        res.update(blocked=True, reason='blocked: דף אתגר (CAPTCHA או הגנת בוטים)',
                   lawyer_task=_lawyer_task(dom, purpose, 'נחסם (CAPTCHA)', clean))
        return done()
    res['content'] = body
    res['bytes'] = len(body)
    res['sha256'] = hashlib.sha256(body).hexdigest()
    if body[:5] == b'%PDF-' or 'pdf' in (ctype or '').lower():
        res['reason'] = 'ok: PDF (הטקסט דרך risk.page_text.page_text)'
    else:
        res['text'] = _decode(body, ctype)
        res['reason'] = 'ok'
    if store is not None and source_id:
        ext = 'pdf' if body[:5] == b'%PDF-' else 'json' if 'json' in ctype else 'txt' if 'text/plain' in ctype \
            else 'csv' if 'csv' in ctype else 'htm'
        try:
            entry, _ = store.store_page(source_id, res['final_url'], body, ext=ext, excerpt=excerpt)
            entry['typed_url'] = clean
            res['stored'] = entry
        except Exception as e:  # StoreError: תקרה, דף גדול בלי קטע
            res['reason'] = 'ok, not stored: %s' % e
    return done()


def assert_honest_headers(headers):
    """לבדיקות ולשער: כותרות של בקשה יוצאת. נכשל על מזהה שאינו של Areo, על מזהה דפדפן, או על מזהה בלי
    שם הארגון וכתובת קשר."""
    ua = {k.lower(): v for k, v in headers.items()}.get('user-agent', '')
    if not ua.startswith(UA_PREFIX) or BROWSER_UA.search(ua):
        raise AssertionError('user-agent שאינו המזהה של Areo: %r' % ua)
    if ORG not in ua or not UA_CONTACT.search(ua):
        raise AssertionError('user-agent בלי שם הארגון וכתובת קשר: %r' % ua)
    return True
