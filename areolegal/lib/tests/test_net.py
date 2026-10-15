# -*- coding: utf-8 -*-
"""בדיקות ל-common/net.py (הערות מעריך הסיכונים 3.6; הכללים המשותפים 3.5): מזהה גלוי בכל בקשה, קצב,
עצירה על 403, 429 ו-CAPTCHA עם משימה לעורך הדין, ניסיון חוזר אחד אחרי שגיאת רשת, ושמירה רק דרך
EntityStore. שרת HTTP מקומי בלבד (127.0.0.1); אין בבדיקות גישה לרשת."""
import http.server
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common import net  # noqa: E402
from risk.entity_store import EntityStore  # noqa: E402

SEEN = []
PDF = (ROOT / 'tests' / 'fixtures' / 'risk' / 'reshumot_sample.pdf').read_bytes()


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        SEEN.append({'path': self.path, 'headers': dict(self.headers)})
        p = self.path
        if p.startswith('/ok'):
            body, code, ct = 'דף רשמי: חוק לדוגמה, התשע"ז'.encode('cp1255'), 200, 'text/html; charset=windows-1255'
        elif p.startswith('/pdf'):
            body, code, ct = PDF, 200, 'application/pdf'
        elif p.startswith('/forbidden'):
            body, code, ct = b'IP blocked', 403, 'text/html'
        elif p.startswith('/slow-down'):
            self.send_response(429)
            self.send_header('Retry-After', '120')
            self.end_headers()
            return
        elif p.startswith('/challenge'):
            body, code, ct = b'<html><head><title>Just a moment...</title></head><body>cf-chl</body></html>', 200, \
                'text/html'
        elif p.startswith('/ddg'):
            body, code, ct = (b'<html><body><div class="anomaly-modal__title">Unfortunately, bots use DuckDuckGo '
                              b'too.</div></body></html>'), 202, 'text/html'
        elif p.startswith('/knesset247'):
            body, code, ct = b'<html><body>ok?</body></html>', 247, 'text/html'
        elif p.startswith('/human'):
            body, code, ct = b'<html><body><h1>Please verify you are human</h1></body></html>', 200, 'text/html'
        else:
            body, code, ct = b'not found', 404, 'text/plain'
        self.send_response(code)
        self.send_header('Content-Type', ct)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        n = int(self.headers.get('Content-Length') or 0)
        SEEN.append({'path': self.path, 'headers': dict(self.headers), 'method': 'POST',
                     'body': self.rfile.read(n).decode('utf-8')})
        body = 'תוצאות חיפוש: חוק לדוגמה'.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture(scope='module')
def server():
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), H)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield 'http://127.0.0.1:%d' % srv.server_address[1]
    srv.shutdown()


CONTACT = 'research-desk@example.org'


@pytest.fixture(autouse=True)
def fresh(monkeypatch):
    net.configure(CONTACT)
    net.reset_session()
    SEEN.clear()
    slept = []
    monkeypatch.setattr(net, '_sleep', lambda s: slept.append(s))
    yield slept
    net.reset_session()


def test_user_agent_is_areo_and_never_a_browser(server):
    r = net.fetch(server + '/ok', 'בדיקת נוסח חוק')
    assert r['status'] == 200 and not r['blocked']
    ua = SEEN[-1]['headers']['User-Agent']
    assert ua == net.USER_AGENT and ua.startswith('AreoLegal-research/')
    assert ua == 'AreoLegal-research/%s (AreoLegal automated legal research; contact: %s)' % (net.VERSION, CONTACT)
    assert net.assert_honest_headers(SEEN[-1]['headers'])
    assert not net.BROWSER_UA.search(ua)
    assert r['log']['user_agent'] == net.USER_AGENT and r['log']['via'] == 'common.net'
    with pytest.raises(AssertionError):
        net.assert_honest_headers({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0) Chrome/120'})


def test_no_way_to_override_headers():
    import inspect
    params = inspect.signature(net.fetch).parameters
    assert not any(p in params for p in ('headers', 'user_agent', 'ua'))


def test_charset_of_page_is_respected(server):
    r = net.fetch(server + '/ok', 'בדיקת נוסח חוק')
    assert 'התשע"ז' in r['text']


def test_403_stops_and_creates_lawyer_task_without_retry(server):
    r = net.fetch(server + '/forbidden', 'נוסח תקנות')
    assert r['blocked'] and r['status'] == 403 and r['text'] is None
    assert r['lawyer_task']['why'].startswith('נחסם') and r['lawyer_task']['task'] == 'עורך הדין'
    n = len(SEEN)
    again = net.fetch(server + '/ok', 'בקשה אחרת לאותו מארח')
    assert again['blocked'] and len(SEEN) == n, 'אחרי חסימה, שום בקשה נוספת אינה יוצאת לאותו מארח'


def test_429_is_a_block(server):
    r = net.fetch(server + '/slow-down', 'רשימה')
    assert r['blocked'] and r['status'] == 429 and 'Retry-After 120' in r['reason']


def test_captcha_page_is_a_block_even_with_200(server):
    r = net.fetch(server + '/challenge', 'מרשם')
    assert r['blocked'] and r['status'] is None or r['blocked']
    assert 'CAPTCHA' in r['lawyer_task']['why']


def test_rate_limit_between_requests_to_same_host(server, fresh):
    net.fetch(server + '/ok', 'ראשונה')
    net.fetch(server + '/ok', 'שנייה')
    assert fresh and fresh[-1] > 0 and fresh[-1] <= net.MIN_INTERVAL


def test_nevo_only_legislation_paths_and_slow():
    r = net.fetch('https://www.nevo.co.il/PsikaSearch.aspx?q=x', 'פסיקה')
    assert r['reason'].startswith('refused') and not r['blocked']
    assert net.HOST_POLICY['nevo.co.il']['min_interval'] >= 10


def test_allowed_domains_checked_before_request(server):
    r = net.fetch(server + '/ok', 'בדיקה', allowed_domains=('knesset.gov.il',))
    assert r['reason'].startswith('refused') and not SEEN


def test_one_retry_after_network_error():
    calls = []

    class Opener:
        def open(self, req, timeout=None):
            calls.append(req.get_header('User-agent'))
            raise OSError('connection reset')

    r = net.fetch('https://knesset.gov.il/x', 'בדיקה', _opener=Opener())
    assert len(calls) == 2 and r['reason'].startswith('network_error') and not r['blocked']
    assert all(c == net.USER_AGENT for c in calls)


def test_purpose_required():
    assert net.fetch('https://knesset.gov.il/x', '')['reason'].startswith('refused')


def test_tokens_are_stripped_from_logged_url(server):
    r = net.fetch(server + '/ok?q=law&X-Amz-Signature=abc&token=zz', 'בדיקה')
    assert 'abc' not in r['log']['url'] and 'zz' not in r['log']['url'] and 'q=law' in r['log']['url']


class _Resp:
    """תשובה מדומה לדף גדול (העברה גדולה דרך loopback אינה יציבה בכל סביבת בדיקה)."""

    def __init__(self, body, ctype, url):
        self.body, self.headers, self.url = body, {'Content-Type': ctype}, url

    def getcode(self):
        return 200

    def geturl(self):
        return self.url

    def read(self, n=-1):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _BigOpener:
    def __init__(self):
        self.ua = []

    def open(self, req, timeout=None):
        self.ua.append(req.get_header('User-agent'))
        body = ('<p>' + 'x' * 300000 + ' הקטע המבוקש כאן ' + 'y' * 300000 + '</p>').encode('utf-8')
        return _Resp(body, 'text/html; charset=utf-8', req.full_url)


def test_store_through_entity_store_caps(server, tmp_path):
    st = EntityStore(str(tmp_path))
    r = net.fetch(server + '/pdf', 'נוסח חוק', store=st, source_id='SRC-001')
    assert r['text'] is None and r['stored']['file'] == 'sources/SRC-001.pdf' and r['stored']['stored'] == 'page'
    op = _BigOpener()
    big = net.fetch('https://knesset.gov.il/big', 'דף גדול', store=st, source_id='SRC-002',
                    excerpt='הקטע המבוקש כאן', _opener=op)
    assert big['stored']['stored'] == 'excerpt_window' and big['stored']['file'].endswith('.txt')
    assert big['stored']['full_size_bytes'] > 600000 and op.ua == [net.USER_AGENT]
    nostore = net.fetch('https://knesset.gov.il/big2', 'דף גדול בלי קטע', store=st, source_id='SRC-003',
                        _opener=_BigOpener())
    assert nostore['stored'] is None and 'not stored' in nostore['reason']
    assert not (tmp_path / 'sources' / 'SRC-003.htm').exists() and not (tmp_path / 'raw').exists()


# ------------------------------------------------------------------ גרסה 1.2.0 (סבב בדיקה 4)
def test_user_agent_has_org_and_configurable_contact_only(monkeypatch, tmp_path):
    """רגרסיה: מזהה לפי בקשת הגישה ההוגנת של SEC EDGAR: שם הארגון וכתובת קשר. רק הכתובת נקבעת, מהתצורה."""
    assert 'AreoLegal' in net.USER_AGENT and 'contact: ' + CONTACT in net.USER_AGENT
    with pytest.raises(AssertionError):
        net.assert_honest_headers({'User-Agent': 'AreoLegal-research/1.1.1 (automated legal research; no browser)'})
    cfg = tmp_path / 'config.json'
    cfg.write_text('{"contact_email": "legal-ops@example.com"}', encoding='utf-8')
    monkeypatch.delenv(net.CONTACT_ENV, raising=False)
    assert net.configure(config_path=str(cfg)).endswith('contact: legal-ops@example.com)')
    monkeypatch.setenv(net.CONTACT_ENV, 'env-desk@example.com')
    assert net.configure(config_path=str(cfg)).endswith('contact: env-desk@example.com)')
    # אי אפשר להזריק דרך כתובת הקשר מזהה אחר או דפדפן
    assert net.configure('x@y.com) Mozilla/5.0 (') is None
    assert net.fetch('https://knesset.gov.il/x', 'בדיקה')['reason'].startswith('refused')
    monkeypatch.delenv(net.CONTACT_ENV, raising=False)
    assert net.configure(config_path=str(tmp_path / 'missing.json')) is None


def test_2xx_challenge_pages_are_blocks(server):
    """רגרסיה: דף ה-anomaly של DuckDuckGo (202), קוד 247 של הכנסת, ו-"verify you are human" בקוד 200."""
    for path in ('/ddg', '/knesset247', '/human'):
        net.reset_session()
        r = net.fetch(server + path, 'חיפוש')
        assert r['blocked'] and r['text'] is None and r['lawyer_task']['why'].startswith('נחסם'), path


def test_block_by_registrable_domain():
    assert net.registrable_domain('main.knesset.gov.il') == 'knesset.gov.il'
    assert net.registrable_domain('fs.knesset.gov.il') == 'knesset.gov.il'
    assert net.registrable_domain('www.nevo.co.il') == 'nevo.co.il'
    assert net.registrable_domain('efts.sec.gov') == 'sec.gov'
    assert net.registrable_domain('127.0.0.1') == '127.0.0.1'

    class Op:
        def __init__(self):
            self.calls = []

        def open(self, req, timeout=None):
            import urllib.error
            self.calls.append(req.full_url)
            raise urllib.error.HTTPError(req.full_url, 403, 'Forbidden', {}, None)

    op = Op()
    assert net.fetch('https://main.knesset.gov.il/a', 'נוסח', _opener=op)['blocked']
    again = net.fetch('https://fs.knesset.gov.il/b', 'נוסח אחר', _opener=op)
    assert again['blocked'] and 'earlier' in again['reason'] and len(op.calls) == 1


def test_block_state_persists_per_run_directory(server, tmp_path):
    run = str(tmp_path / 'run')
    net.start_run(run)
    assert net.fetch(server + '/forbidden', 'נוסח')['blocked']
    assert (tmp_path / 'run' / net.BLOCKS_FILE).exists()
    n = len(SEEN)
    net.reset_session()                    # תהליך חדש באותה הרצה
    net.start_run(run)
    r = net.fetch(server + '/ok', 'בקשה אחרת')
    assert r['blocked'] and len(SEEN) == n
    net.reset_session()                    # הרצה אחרת: אין חסימה
    net.start_run(str(tmp_path / 'other-run'))
    assert not net.fetch(server + '/ok', 'בקשה')['blocked']
    net.reset_session()
    assert net.fetch(server + '/ok', 'בקשה', run_dir=run)['blocked']


def test_post_only_to_official_search_form_under_same_rules(server, monkeypatch):
    r = net.fetch(server + '/search', 'חיפוש', form={'q': 'חוק'})
    assert r['reason'].startswith('refused') and not SEEN
    monkeypatch.setitem(net.HOST_POLICY, '127.0.0.1', {'paths': ('/search',), 'post_paths': ('/search',),
                                                       'min_interval': 10.0})
    r = net.fetch(server + '/search', 'חיפוש חקיקה', form={'q': 'חוק החוזים', 'token': 'zz'})
    assert r['status'] == 200 and r['method'] == 'POST' and 'חוק לדוגמה' in r['text']
    assert SEEN[-1]['method'] == 'POST' and SEEN[-1]['headers']['User-Agent'] == net.USER_AGENT
    assert r['log']['method'] == 'POST' and 'zz' not in r['log']['form'] and 'q=' in r['log']['form']
    assert net.fetch('https://www.nevo.co.il/PsikaSearch.aspx', 'פסיקה', form={'q': 'x'})['reason'].startswith(
        'refused')


def test_official_identifiers_are_not_client_details():
    ok = ['CELEX 32016R0679', 'LawItemId=2000171', 'ס"ח 2563 חוק החוזים', 'ק"ת 85430', 'תקנות הגנת הפרטיות 78090',
          '42 U.S.C. 19830', '17 CFR 24010', 'Public Law 117-328', 'חוק החברות התשנ"ט-1999']
    for q in ok:
        assert net.client_detail_in_query(q) == '', q
    bad = ['513456789 חוזה', 'ח.פ. 516789012', '050-1234567 ספק', 'הזמנה 9876543', 'בע"מ חברה בדיקה']
    found = [net.client_detail_in_query(q, ['חברה בדיקה']) for q in bad]
    assert all(found), list(zip(bad, found))
