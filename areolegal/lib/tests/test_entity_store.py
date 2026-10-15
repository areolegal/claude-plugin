# -*- coding: utf-8 -*-
"""בדיקות ל-risk/entity_store.py: רק שורות התאמה וקרובות נשמרות, כתובות בלי טוקנים, תקרות הגודל של
הכללים המשותפים 3.4 (200 קילובייט לקטע, 2 מגה-בייט לתיקיית המחקר של העסקה), ורשימה מלאה לעולם אינה נשמרת."""
import csv
import io
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from risk.entity_store import (DEAL_CAP, EXTRACT_CAP, EntityStore, StoreError, audit_deal_dir,  # noqa: E402
                               has_secret, match_name, normalize_name, strip_secrets)


def test_caps_are_the_shared_hard_rules_values():
    assert EXTRACT_CAP == 200 * 1024
    assert DEAL_CAP == 2 * 1024 * 1024


# ---------- tokens ----------
@pytest.mark.parametrize('url,gone', [
    ('https://sanctionslistservice.ofac.treas.gov/x/SDN.CSV?X-Amz-Algorithm=AWS4&X-Amz-Security-Token=AAA&X-Amz-Signature=BBB',
     ['X-Amz-Algorithm', 'X-Amz-Security-Token', 'X-Amz-Signature']),
    ('https://scsanctions.blob.core.windows.net/c.xml?sv=2020&se=2026-10-15&sr=b&sp=r&sig=ZZZ', ['sv', 'se', 'sr', 'sp', 'sig']),
    ('https://webgate.ec.europa.eu/fsd/fsf/public/files/csvFullSanctionsList_1_1/content?token=dG9rZW4', ['token']),
    ('https://user:pass@example.gov/list.csv?api_key=1', ['api_key', 'userinfo']),
])
def test_strip_secrets_removes_tokens(url, gone):
    clean, removed = strip_secrets(url)
    for g in gone:
        assert g in removed
    assert not has_secret(clean)
    assert 'pass@' not in clean and 'sig=' not in clean and 'Token' not in clean


def test_strip_secrets_keeps_query_parameters():
    url = 'https://data.gov.il/api/3/action/datastore_search?resource_id=f004176c&q=GOOGLE%20LLC&limit=50'
    clean, removed = strip_secrets(url)
    assert removed == []
    assert 'resource_id=f004176c' in clean and 'q=GOOGLE+LLC' in clean.replace('%20', '+')


# ---------- name matching ----------
def test_normalize_name_drops_legal_suffix_and_marks():
    assert normalize_name('Google LLC') == normalize_name('GOOGLE, L.L.C.') == 'google'
    assert normalize_name('אלפא טכנולוגיות בע"מ') == normalize_name('אלפא טכנולוגיות בע״מ')


def test_match_name_definition():
    assert match_name('Google LLC', 'GOOGLE LLC')[0] == 'exact'
    assert match_name('Google LLC', 'Alphabet Holdings', aliases=['Google LLC'])[0] == 'alias'
    # אדם מול תאגיד: לעולם לא התאמה (סבב 2: "GOOGLE, Mahdi")
    assert match_name('Google', 'GOOGLE, Mahdi', record_type='Individual')[0] in ('near', 'none')
    assert match_name('Google LLC', 'Google Payment Corp')[0] == 'near'
    assert match_name('Google LLC', 'Acme Trading')[0] == 'none'


# ---------- storing a list result ----------
def _big_list(n=40000):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=['ent_num', 'name', 'type', 'aliases', 'remarks'])
    w.writeheader()
    for i in range(n):
        w.writerow({'ent_num': i, 'name': 'Company Number %d Holdings' % i, 'type': 'Entity', 'aliases': '',
                    'remarks': 'filler text ' * 3})
    w.writerow({'ent_num': n + 1, 'name': 'GOOGLE, Mahdi', 'type': 'Individual', 'aliases': '', 'remarks': ''})
    w.writerow({'ent_num': n + 2, 'name': 'Other Org', 'type': 'Entity', 'aliases': '',
                'remarks': 'Email abc@google.com; Google LLC mentioned'})
    w.writerow({'ent_num': n + 3, 'name': 'Example Sanctioned Corp', 'type': 'Entity', 'aliases': 'ESC Ltd', 'remarks': ''})
    return buf.getvalue().encode('utf-8')


def test_list_result_stores_only_window(tmp_path):
    full = _big_list()
    assert len(full) > DEAL_CAP  # הרשימה המלאה גדולה מכל התקרה
    st = EntityStore(str(tmp_path))
    rec, path = st.store_list_result(
        'ENT-03', 'OFAC SDN', 'https://x.s3.amazonaws.com/SDN.CSV?X-Amz-Security-Token=QQQ', 'Google LLC',
        full_bytes=full, name_field='name', alias_fields=['aliases'], type_field='type', note_fields=['remarks'],
        file_date='2026-10-13', looked_up_at='2026-10-14T14:44')
    size = os.path.getsize(path)
    assert size <= EXTRACT_CAP and size < len(full) / 100
    assert rec['result'] == 'no_match' and rec['matches'] == []
    assert rec['near_total'] >= 1 and all(n['match'] == 'near' for n in rec['near'])
    assert rec['rows_total'] == 40003 and rec['full_size_bytes'] == len(full)
    assert 'X-Amz' not in rec['url'] and 'X-Amz-Security-Token' in rec['url_params_removed']
    saved = json.loads(Path(path).read_text(encoding='utf-8'))
    assert 'Company Number 17 Holdings' not in json.dumps(saved, ensure_ascii=False)
    assert st.records[0]['stored'] == 'match_window' and st.records[0]['file'] == 'sources/ENT-03.json'
    assert audit_deal_dir(str(tmp_path)) == []


def test_list_result_exact_match_is_stored(tmp_path):
    st = EntityStore(str(tmp_path))
    rec, _ = st.store_list_result('ENT-04', 'OFAC SDN', 'https://sanctionslistservice.ofac.treas.gov/SDN.CSV',
                                  'Example Sanctioned Corp', full_bytes=_big_list(200), name_field='name',
                                  alias_fields=['aliases'], type_field='type')
    assert rec['result'] == 'match' and rec['matches'][0]['match'] == 'exact'
    rec2, _ = st.store_list_result('ENT-05', 'OFAC SDN', 'https://sanctionslistservice.ofac.treas.gov/SDN.CSV',
                                   'ESC Ltd', full_bytes=_big_list(200), name_field='name', alias_fields=['aliases'])
    assert rec2['matches'][0]['match'] == 'alias'


# ---------- caps ----------
def test_large_page_needs_excerpt_and_stores_window(tmp_path):
    st = EntityStore(str(tmp_path))
    page = ('<html><body>' + 'x' * (EXTRACT_CAP + 5000) + '<p>החברה במעמד פעילה</p>' + 'y' * 5000 + '</body></html>')
    with pytest.raises(StoreError):
        st.store_page('ENT-06', 'https://ica.justice.gov.il/x', page)
    entry, path = st.store_page('ENT-06', 'https://ica.justice.gov.il/x?session=abc', page, excerpt='החברה במעמד פעילה')
    assert entry['stored'] == 'excerpt_window' and os.path.getsize(path) <= EXTRACT_CAP
    assert 'session' not in entry['final_url']


def test_extract_cap_and_deal_cap(tmp_path):
    st = EntityStore(str(tmp_path))
    st.store_page('SRC-001', 'https://www.nevo.co.il/law_html/law00/1.htm', 'a' * (150 * 1024))
    with pytest.raises(StoreError):
        st._write('ENT-99.json', b'z' * (EXTRACT_CAP + 1))
    small = EntityStore(str(tmp_path), cap_bytes=200 * 1024)
    with pytest.raises(StoreError):
        small.store_page('SRC-002', 'https://www.nevo.co.il/law_html/law00/2.htm', 'b' * (100 * 1024))


def test_bad_file_name_rejected(tmp_path):
    with pytest.raises(StoreError):
        EntityStore(str(tmp_path))._write('../escape.json', b'{}')


def test_audit_flags_round2_layout(tmp_path):
    raw = tmp_path / 'raw'
    raw.mkdir()
    (raw / 'ENT-07.csv').write_bytes(b'n' * (EXTRACT_CAP + 1))
    (tmp_path / 'entity-report.json').write_text(json.dumps({'raw_copies': [
        {'final_url': 'https://scsanctions.un.org/x.xml?sig=abc'}]}), encoding='utf-8')
    problems = audit_deal_dir(str(tmp_path))
    assert any('ENT-07.csv' in p for p in problems)
    assert any('טוקן' in p for p in problems)
