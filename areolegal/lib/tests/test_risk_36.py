# -*- coding: utf-8 -*-
"""בדיקות לכללים החדשים של הערות מעריך הסיכונים 3.6 (ממצאי סבב 3):
PDF וגרשיים בקטעים מילוליים; ויתור מכוון לפי מזהה סעיף, וכיסוי של כל ויתור; החלטה 1 (אין שרשרת אישורים);
הלולאה לפני משלוח שיצאה (מרשם ישן נקרא בלי שגיאה); סיכון שהתגובה יצרה; חותמות זמן; user_agent ביומן; playbook_resolution; עזר הלוגו; תבנית חקר הישות כקובץ מוגש; בנייה
לתיקיית העסקה; חילוץ PDF ומפענחי הרשימות הרשמיות."""
import copy
import hashlib
import io
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from risk import page_text as PT  # noqa: E402
from risk.build import BuildError, write_report  # noqa: E402
from risk.entity_store import (OFAC_SDN_FIELDS, EntityStore, rows_from_csv_bytes, rows_from_un_xml,  # noqa: E402
                               scan_rows)
from risk.extract_corpus import extract  # noqa: E402
from risk.logo import LogoError, logo_data_uri, uri_bytes  # noqa: E402
from risk.validate_register import validate, validate_entity_report  # noqa: E402

FX = ROOT / 'tests' / 'fixtures' / 'risk'
PDF = FX / 'reshumot_sample.pdf'


def load(name):
    return json.loads((FX / name).read_text(encoding='utf-8'))


def errs(reg, **kw):
    return validate(reg, **kw)[0]


def has_pdf_lib():
    try:
        PT.pdf_text(PDF.read_bytes())
        return True
    except PT.PdfTextUnavailable:
        return False


needs_pdf = pytest.mark.skipif(not has_pdf_lib(), reason='אין pymupdf או pypdf')


# ---------------------------------------------------------------- normalisation: gershayim and geresh
def test_gershayim_inside_hebrew_word_is_not_a_quote_mark():
    assert PT.norm('התשע"ז') == PT.norm('התשע״ז') == 'התשע״ז'
    assert PT.norm("פרק ח'1") == PT.norm('פרק ח׳1')
    assert PT.quote_segments('ספר החוקים, סעיף 2: "חוק מוסר תשלומים לספקים, התשע"ז-2017"') == [
        'חוק מוסר תשלומים לספקים, התשע״ז-2017']
    # ציטוט בתוך ציטוט נשאר שלם
    assert PT.quote_segments('סעיף 104: "במקום "הפרשי הצמדה וריבית" יבוא"') == ['במקום "הפרשי הצמדה וריבית" יבוא']
    assert PT.excerpt_in('מיקום: "ס"ח 2622, התשע״ז"', '<p>ס״ח 2622, התשע"ז</p>')


def test_round2_validator_split_the_excerpt_on_gershayim():
    """הבאג של 3.5: הקטע "...התשע"ז" נחתך במירכאה שבתוך המילה. עכשיו הוא נמצא בעותק."""
    html = '<html><body><p>חוק מוסר תשלומים לספקים, התשע"ז-2017, סעיף 3(ז)</p></body></html>'.encode('utf-8')
    assert PT.excerpt_in('סעיף 1: "חוק מוסר תשלומים לספקים, התשע"ז-2017"', PT.page_text(html))


# ---------------------------------------------------------------- PDF raw copies
@needs_pdf
def test_pdf_text_layer_and_excerpts():
    t = PT.page_text(PDF.read_bytes())
    assert PT.excerpt_in('סעיף 3(ז): "מזמין שהוא עסק ישלם לספק את התמורה"', t)
    assert PT.excerpt_in('כותרת: "חוק לדוגמה בעניין תשלומים, התשע״ז"', t)
    assert PT.excerpt_in('סעיף 104: "במקום "הפרשי הצמדה וריבית" יבוא "ריבית שקלית"', t)
    assert not PT.excerpt_in('"נוסח שאינו בפרסום"', t)


def _reg_with_pdf_source(tmp_path, excerpt, text_file=False):
    reg = load('c1b_register.json')
    deal = tmp_path / 'deal_yoetz_2026-10-14'
    (deal / 'raw').mkdir(parents=True)
    shutil.copy(PDF, deal / 'raw' / 'SRC-001.pdf')
    b = PDF.read_bytes()
    url = 'https://fs.knesset.gov.il/20/law/sample.pdf'
    rc = {'source_id': 'SRC-001', 'typed_url': url, 'final_url': url, 'saved_at': '2026-10-14T17:14:00+03:00',
          'file': 'raw/SRC-001.pdf', 'title': 'רשומות לדוגמה', 'sha256': hashlib.sha256(b).hexdigest(),
          'stored': 'page', 'full_size_bytes': len(b), 'full_sha256': hashlib.sha256(b).hexdigest()}
    if text_file:
        t = 'מזמין שהוא עסק ישלם לספק את התמורה לא יאוחר מתום החודש.'.encode('utf-8')
        (deal / 'raw' / 'SRC-001.txt').write_bytes(t)
        rc.update(text_file='raw/SRC-001.txt', text_sha256=hashlib.sha256(t).hexdigest())
    reg['research']['raw_copies'] = [rc]
    reg['research']['sources_checked'] = [{
        'id': 'SRC-001', 'source': 'הכנסת, רשומות: ספר החוקים לדוגמה', 'url': url, 'subject': 'מועד תשלום',
        'taken': 'מועד תשלום לעסק', 'date': '2026-10-14', 'version_date': '2024-12-01', 'finding': '',
        'excerpt': excerpt}]
    reg['research']['confidence'] = [{'source_id': 'SRC-001', 'label': 'high', 'why': 'נוסח החוק ברשומות'}]
    for r in reg['risks']:
        r['external_source_ids'] = []
    return reg, str(deal)


@needs_pdf
def test_validator_reads_pdf_raw_copy(tmp_path):
    reg, deal = _reg_with_pdf_source(tmp_path, 'ספר החוקים לדוגמה, סעיף 3(ז): "מזמין שהוא עסק ישלם לספק את התמורה"')
    assert not [e for e in errs(reg, deal_dir=deal) if 'SRC-001' in e]
    reg, deal = _reg_with_pdf_source(tmp_path / 'b', 'כותרת: "חוק לדוגמה בעניין תשלומים, התשע״ז"')
    assert not [e for e in errs(reg, deal_dir=deal) if 'SRC-001' in e]
    reg, deal = _reg_with_pdf_source(tmp_path / 'c', 'סעיף 9: "נוסח שאינו בפרסום הזה בכלל"')
    assert any('SRC-001' in e and 'הקטע המילולי לא נמצא' in e for e in errs(reg, deal_dir=deal))


def test_text_file_beside_pdf_is_read_when_no_text_layer(tmp_path, monkeypatch):
    import risk.validate_register as V

    def boom(b):
        raise PT.PdfTextUnavailable('סריקה')
    monkeypatch.setattr(V, 'page_text', boom)
    reg, deal = _reg_with_pdf_source(tmp_path, 'סעיף 3(ז): "מזמין שהוא עסק ישלם לספק את התמורה"', text_file=True)
    assert not [e for e in errs(reg, deal_dir=deal) if 'SRC-001' in e]
    reg, deal = _reg_with_pdf_source(tmp_path / 'b', 'סעיף 3(ז): "מזמין שהוא עסק ישלם לספק את התמורה"')
    assert any('text_file' in e for e in errs(reg, deal_dir=deal))


@needs_pdf
def test_extract_corpus_reads_pdf_document():
    d = extract(str(PDF))
    assert d['format'] == 'pdf' and 'pdf/page-1' in d['parts']
    texts = [p['text_accept_all'] for p in d['parts']['pdf/page-1']]
    assert any('מזמין שהוא עסק' in t for t in texts)
    assert all(p['text_accept_all'] == p['text_reject_all'] for p in d['parts']['pdf/page-1'])


# ---------------------------------------------------------------- deliberate concessions by clause id
def _state(concessions, clause_ids=('E-028', 'E-004', 'D07', 'D12', 'D13', 'D01')):
    return {'text_status': 'our_unsent_response', 'deliberate_concessions': concessions,
            'numbering_map': {c: 'סעיף 6' for c in clause_ids},
            'clauses': [{'clause_id': c} for c in clause_ids]}


def _c2_accepting(reg, pairs):
    reg['pre_send_fixes'] = reg['pre_send_fixes'][2:]
    for rid, sc in pairs:
        r = next(x for x in reg['risks'] if x['id'] == rid)
        r['decision'] = {'status': 'accepted', 'basis': 'deliberate_waiver', 'state_clause_id': sc, 'note': '',
                         'decided_at': '2026-10-14'}
    for p in reg['pre_send_fixes']:
        p['where'] = 'סעיף 6'
    return reg


def test_concession_with_rule_id_fails():
    st = _state([{'topic': 'ביטוח', 'clause_ref': 'R11', 'report_as': 'accepted_risk'}])
    E = errs(load('c2_register.json'), state=st)
    assert any('R11' in e and 'מזהה כלל' in e for e in E)


def test_every_concession_appears_as_accepted_risk():
    st = _state([{'topic': 'סודיות קיום המגעים', 'clause_ref': 'E-028', 'report_as': 'accepted_risk'},
                 {'topic': 'צמצום המטרה', 'clause_ref': 'E-004', 'report_as': 'accepted_risk'}])
    reg = _c2_accepting(load('c2_register.json'), [('RSK-001', 'E-028')])
    E = errs(reg, state=st)
    assert any('E-004' in e and 'אינו מופיע כסיכון שהתקבל' in e for e in E)
    reg = _c2_accepting(load('c2_register.json'), [('RSK-001', 'E-028'), ('RSK-002', 'E-004')])
    assert errs(reg, state=st) == []


def test_two_concessions_merged_into_one_risk_with_state_clause_ids():
    st = _state([{'topic': 'סודיות קיום המגעים', 'clause_ref': 'E-028', 'report_as': 'accepted_risk'},
                 {'topic': 'צמצום המטרה', 'clause_ref': 'E-004', 'report_as': 'accepted_risk'}])
    reg = _c2_accepting(load('c2_register.json'), [('RSK-001', 'E-028')])
    reg['risks'][0]['decision']['state_clause_ids'] = ['E-004']
    assert errs(reg, state=st) == []


def test_decision_with_rule_id_fails():
    reg = load('c2_register.json')
    reg['pre_send_fixes'] = reg['pre_send_fixes'][2:]
    reg['risks'][0]['decision'] = {'status': 'accepted', 'basis': 'deliberate_waiver', 'state_clause_id': 'R11'}
    assert any('מזהה כלל' in e for e in errs(reg))


# ---------------------------------------------------------------- decision 1: no approval chains
@pytest.mark.parametrize('dec', [
    {'status': 'accepted_pending_approval', 'basis': 'deliberate_waiver', 'state_clause_id': 'E-028'},
    {'status': 'accepted', 'basis': 'deliberate_waiver', 'state_clause_id': 'E-028', 'approval_required_by': 'מנכ"ל'},
    {'status': 'accepted', 'basis': 'deliberate_waiver', 'state_clause_id': 'E-028', 'required_by': 'CEO'},
    {'status': 'accepted', 'basis': 'deliberate_waiver', 'state_clause_id': 'E-028', 'note': 'ממתין לאישור מנכ"ל'},
])
def test_no_approval_fields_or_wording(dec):
    reg = load('c2_register.json')
    reg['pre_send_fixes'] = reg['pre_send_fixes'][2:]
    reg['risks'][0]['decision'] = dec
    assert any('אישור' in e for e in errs(reg))


def test_accepted_risk_without_approval_passes():
    reg = load('c2_register.json')
    reg['pre_send_fixes'] = reg['pre_send_fixes'][2:]
    reg['risks'][0]['decision'] = {'status': 'accepted', 'basis': 'deliberate_waiver', 'state_clause_id': 'E-028',
                                   'note': 'הכרעת המשתמש בסבב 1', 'decided_at': '2026-10-14'}
    assert errs(reg, corpus=load('c2_corpus.json')) == []


# ---------------------------------------------------------------- pre-send loop contract
# הלולאה לפני משלוח יצאה (risk-register-schema.md:251: "pre_send_fixes יצא, ובמרשם ישן השדה נקרא ומתעלמים ממנו";
# orchestrator/pre_send.py: "מעריך הסיכונים אינו חוסם את המשלוח"). מה שנשאר: מרשם ישן נקרא בלי שגיאה, קובץ מצב ישן
# עם השדה עובר, ושער המשלוח של הנושא ונותן אינו קורא את המרשם.
def test_legacy_pre_send_rows_are_ignored_by_the_validator():
    reg = load('c2_register.json')
    st = _state([{'topic': 'סודיות קיום המגעים', 'clause_ref': 'E-028', 'report_as': 'accepted_risk'}])
    reg['pre_send_fixes'][0].pop('id')
    reg['pre_send_fixes'][1]['status'] = 'pending'
    reg['pre_send_fixes'][2]['clause_ref'] = 'R-04'
    reg['pre_send_fixes'][3]['clause_ref'] = 'NOT-IN-STATE'
    E, W = validate(reg, state=st)
    assert not any('pre_send' in x for x in E + W), E + W
    bare = copy.deepcopy(reg)
    bare.pop('pre_send_fixes')
    assert validate(bare, state=st) == (E, W)


def test_legacy_pre_send_fixes_in_the_state_file_is_accepted():
    from orchestrator import state_builder as SB
    st = SB.skeleton()
    base = SB.validate_state(copy.deepcopy(st))
    st['pre_send_fixes'] = [{'id': 'PSF-01', 'clause_ref': 'D07', 'status': 'open'}]
    assert SB.validate_state(st) == base


def test_the_negotiation_send_gate_does_not_read_the_risk_register():
    from orchestrator import pre_send as ops
    src = Path(ops.__file__).read_text(encoding='utf-8')
    assert 'risk-register' not in src.replace('אין כאן קריאה של risk-register.json', '')
    assert not hasattr(ops, 'check') and not hasattr(ops, 'concede_fix')


def test_anchor_on_a_new_clause_from_numbering_map_is_known():
    """סעיף חדש בתגובה שלנו (מזהה N מ-numbering_map, שאינו בטיוטה שהתקבלה) הוא מזהה סעיף תקין לעוגן."""
    reg = load('c2_register.json')
    st = _state([])
    st['numbering_map']['N01'] = 'סעיף 6'
    reg['risks'][2]['anchors'][0]['state_clause_id'] = 'N01'
    assert not any('N01' in e for e in errs(reg, state=st))
    reg['risks'][2]['anchors'][0]['state_clause_id'] = 'N02'
    assert any('N02' in e and 'אינו בקובץ המצב' in e for e in errs(reg, state=st))


def test_created_by_response_only_in_text_we_propose():
    """created_by_response: רק בנוסח שאנחנו מציעים (risk-register-schema.md, בלוק הסיכון)."""
    reg = load('c2_register.json')
    reg['risks'][3]['created_by_response'] = True
    assert not any('created_by_response' in e for e in errs(reg))
    reg['meta']['source_version']['text_status'] = 'counterparty_draft'
    assert any('created_by_response' in e for e in errs(reg))


def test_bottom_line_does_not_repeat_the_sign_label():
    """השורה התחתונה אינה חוזרת על התווית שהתבנית בוחרת מ-sign_as_is (risk-register-schema.md, summary):
    אזהרה, לא שגיאה. "לשלוח רק אחרי התיקונים" יצא עם הלולאה לפני משלוח."""
    reg = load('c2_register.json')
    reg['summary']['bottom_line'][0] = 'אפשר לחתום רק אחרי התיקונים שברשימה.'
    E, W = validate(reg)
    assert not any('bottom_line' in e for e in E)
    assert any('bottom_line' in w and 'חוזר על התווית' in w for w in W)

def test_playbook_resolution_read_from_root_and_from_playbook_status():
    """רגרסיה (סבב 4): state_builder כותב playbook_resolution בשורש קובץ המצב (קנוני); קובץ מצב ישן מחזיק אותו
    ב-playbook_status. הוולידטור קורא את שניהם."""
    reg = load('c2_register.json')
    reg['risks'][0]['playbook_flag'] = 'deviates_from_benchmark'
    for st in ({'playbook_resolution': {'activation_ok': False}},
               {'playbook_status': {'playbook_resolution': {'activation_ok': False}}}):
        st.update(numbering_map={}, clauses=[])
        assert any('activation_ok' in e for e in errs(reg, state=st)), st


# ---------------------------------------------------------------- timestamps, user agent, playbook resolution
def test_naive_timestamp_fails():
    reg = load('c2_register.json')
    reg['research']['raw_copies'][0]['saved_at'] = '2026-10-14T14:29'
    assert any('חותמת זמן' in e for e in errs(reg))
    rep = {'raw_copies': [{'looked_up_at': '2026-10-14T14:29', 'stored': 'match_window'}]}
    assert any('חותמת זמן' in e for e in validate_entity_report(rep))


def test_browser_user_agent_in_search_log_fails():
    reg = load('c2_register.json')
    reg['research']['search_log'][0]['user_agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0'
    assert any('user_agent' in e for e in errs(reg))
    reg['research']['search_log'][0]['user_agent'] = 'AreoLegal-research/1.1.0 (automated legal research)'
    assert any('כתובת קשר' in e for e in errs(reg)), 'גרסה 1.2.0: מזהה בלי שם הארגון וכתובת קשר נכשל'
    reg['research']['search_log'][0]['user_agent'] = ('AreoLegal-research/1.2.0 (AreoLegal automated legal research; '
                                                      'contact: research-desk@example.org)')
    assert not any('user_agent' in e for e in errs(reg))


def test_official_statute_identifier_in_query_is_not_a_client_detail():
    # רגרסיה (סבב 4): הבדיקה של חמש ספרות ומעלה חסמה מזהה רשמי של חוק או תקנה. מספר חברה עדיין נכשל.
    reg = load('c2_register.json')
    q = reg['research']['search_log'][0]
    for ok in ('LawItemId=2000171', 'CELEX 32016R0679', 'ק"ת 85430 תקנות'):
        q['query'] = ok
        assert not any('פרט של הלקוח' in e for e in errs(reg)), ok
    q['query'] = 'ספק 513456782'
    assert any('פרט של הלקוח' in e for e in errs(reg))


def test_no_playbook_flag_when_state_says_activation_failed():
    reg = load('c2_register.json')
    flagged = [r for r in reg['risks'] if r.get('playbook_flag') not in (None, 'none')]
    if not flagged:
        reg['risks'][0]['playbook_flag'] = 'deviates_from_benchmark'
    st = {'playbook_resolution': {'activation_ok': False}, 'numbering_map': {}, 'clauses': []}
    assert any('activation_ok' in e for e in errs(reg, state=st))


def test_entity_sources_domain_checked():
    rep = {'sources': [{'url': 'https://www.example-news.com/google'}]}
    assert any('דומיין' in e for e in validate_entity_report(rep))


# ---------------------------------------------------------------- logo helper
def _png(w, h, noisy=False):
    from PIL import Image
    import random
    img = Image.new('RGBA', (w, h), (20, 60, 120, 255))
    if noisy:
        rnd = random.Random(7)
        px = img.load()
        for x in range(0, w, 1):
            for y in range(0, h, 3):
                px[x, y] = (rnd.randrange(256), rnd.randrange(256), rnd.randrange(256), 255)
    buf = io.BytesIO()
    img.save(buf, 'PNG')
    return buf.getvalue()


def test_small_logo_embedded_as_is(tmp_path):
    pytest.importorskip('PIL')
    p = tmp_path / 'logo.png'
    p.write_bytes(_png(120, 60))
    u = logo_data_uri(str(p))
    assert u.startswith('data:image/png;base64,') and uri_bytes(u) <= 150 * 1024


def test_large_logo_is_downscaled_under_the_cap(tmp_path):
    pytest.importorskip('PIL')
    p = tmp_path / 'logo.png'
    p.write_bytes(_png(1600, 1600, noisy=True))
    assert p.stat().st_size > 150 * 1024
    u = logo_data_uri(str(p))
    assert uri_bytes(u) <= 150 * 1024
    reg = load('c2_register.json')
    reg['meta']['branding'] = {'logo': u}
    assert not any('logo' in e for e in errs(reg))


def test_large_logo_without_pillow_is_a_clear_error(tmp_path, monkeypatch):
    p = tmp_path / 'logo.png'
    p.write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00' * (400 * 1024))
    import builtins
    real = builtins.__import__

    def no_pil(name, *a, **k):
        if name == 'PIL' or name.startswith('PIL.'):
            raise ImportError('no PIL')
        return real(name, *a, **k)
    monkeypatch.setattr(builtins, '__import__', no_pil)
    with pytest.raises(LogoError):
        logo_data_uri(str(p))


# ---------------------------------------------------------------- entity template served as a resource
def test_entity_template_is_a_served_resource():
    res = ROOT / 'risk' / 'resources' / 'entity-report-template.html'
    t = res.read_text(encoding='utf-8')
    assert '__ENTITY_DATA__' in t and t.count('__ENTITY_DATA__') == 1
    assert '<title>Areo Workspace | חקר ישות</title>' in t


def test_entity_template_in_lib_is_a_byte_identical_copy_of_the_skill_asset():
    """lib/README.md: risk/resources/entity-report-template.html הוא עותק זהה של התבנית שהמעריך בונה ממנה
    (skills/contract-risk-assessor/assets). עותק שנשאר מאחור הוא תבנית ישנה בלי ערכת הגופנים המוטמעת."""
    asset = ROOT.parent / 'skills' / 'contract-risk-assessor' / 'assets' / 'entity-report-template.html'
    res = ROOT / 'risk' / 'resources' / 'entity-report-template.html'
    assert asset.read_bytes() == res.read_bytes()


def test_render_check_entity_defaults():
    from risk import render_check as rc
    assert rc.KINDS['entity']['placeholder'] == '__ENTITY_DATA__'
    assert rc.KINDS['entity']['body_limit'] == 2 and 'חקר ישות' in rc.KINDS['entity']['markers']


# ---------------------------------------------------------------- build into the deal folder
def test_write_report_refuses_other_deal_and_writes_two_files(tmp_path):
    reg = load('c2_register.json')
    tpl = FX / 'risk-report-template.html'
    deal = tmp_path / reg['meta']['transaction_id']
    deal.mkdir()
    h, j = write_report(str(deal), str(tpl), reg)
    assert Path(h).name == 'Areo Workspace - סיכונים.html' and Path(j).name == 'risk-register.json'
    assert json.loads(Path(j).read_text(encoding='utf-8'))['meta']['transaction_id'] == reg['meta']['transaction_id']
    other = copy.deepcopy(reg)
    other['meta']['transaction_id'] = 'deal_other_2026-10-14'
    with pytest.raises(BuildError):
        write_report(str(deal), str(tpl), other)
    wrong = tmp_path / 'deal_other_2026-10-14'
    wrong.mkdir()
    with pytest.raises(BuildError):
        write_report(str(wrong), str(tpl), reg)


# ---------------------------------------------------------------- official list parsers
def test_ofac_without_header_eu_semicolon_uk_preamble_un_xml():
    sdn = b'36,"GOOGLE TRADING CO.","-0-","SDGT","-0-","-0-","-0-","-0-","-0-","-0-","-0-","a.k.a. X"\n'
    rows = rows_from_csv_bytes(sdn, fieldnames=OFAC_SDN_FIELDS)
    assert rows[0]['SDN_Name'] == 'GOOGLE TRADING CO.' and rows[0]['Program'] == 'SDGT'
    eu = 'Entity_LogicalId;NameAlias_WholeName;Subject_Type\n1;Example Corp LLC;enterprise\n'.encode('utf-8')
    assert rows_from_csv_bytes(eu)[0]['NameAlias_WholeName'] == 'Example Corp LLC'
    uk = b'Report Date: 14-Oct-2026\n\nName 6,Name 1,Group Type\nCorp,Example,Entity\n'
    assert rows_from_csv_bytes(uk, header_startswith='Name 6')[0]['Name 6'] == 'Corp'
    un = ('<CONSOLIDATED_LIST><ENTITIES><ENTITY><FIRST_NAME>EXAMPLE CORP</FIRST_NAME>'
          '<REFERENCE_NUMBER>QDe.1</REFERENCE_NUMBER><ENTITY_ALIAS><ALIAS_NAME>EX CORP</ALIAS_NAME></ENTITY_ALIAS>'
          '</ENTITY></ENTITIES></CONSOLIDATED_LIST>').encode('utf-8')
    r = rows_from_un_xml(un)
    assert r[0]['name'] == 'EXAMPLE CORP' and r[0]['aliases'] == 'EX CORP'
    m, _ = scan_rows(r, 'Example Corp LLC', 'name', alias_fields=('aliases',), type_field='type')
    assert m and m[0]['match'] == 'exact'


def test_store_page_decodes_windows_1255(tmp_path):
    st = EntityStore(str(tmp_path))
    page = ('<html><head><meta charset="windows-1255"></head><body>' + 'א' * 210000 +
            ' חוק מוסר תשלומים לספקים, התשע"ז ' + 'ב' * 1000 + '</body></html>').encode('cp1255')
    entry, path = st.store_page('SRC-001', 'https://www.nevo.co.il/law_html/law00/1.htm', page,
                                excerpt='חוק מוסר תשלומים לספקים, התשע״ז')
    assert entry['stored'] == 'excerpt_window'
    assert 'מוסר תשלומים' in Path(path).read_text(encoding='utf-8')
    assert entry['saved_at'][-6] in '+-' and entry['saved_at'].count(':') == 3
