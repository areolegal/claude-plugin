# -*- coding: utf-8 -*-
"""בדיקות רגרסיה לגרסה 1.2.0 של החבילה (סבב בדיקה 4, וריצות C1 ו-C3 של הלולאה שלפני המשלוח). בדיקה אחת לפחות לכל
תקלה. הבדיקות של שכבת הרשת ב-tests\\test_net.py, של חילוץ הקורפוס ב-tests\\test_extract.py, ושל הוולידטור של
מעריך הסיכונים ב-tests\\test_risk_36.py."""
import copy
import io
import json
import os
import subprocess
import sys

import pytest

import orch_helpers as H
import pb_helpers as PB
from common import docx_tracked as dt
from common.cli import OutputRefused, guard_out
from common.terms import terms_re
from orchestrator import pre_send, qa_gate, resolve_playbook as rp, review_table as rt, state_builder as sb
from playbook import ingest_approval as I
from playbook import market_counts as MC
from playbook import status as S
from risk.entity_store import EntityStore, strip_secrets

ROOT = H.ROOT
S2 = os.path.join(H.FIX, 'services2_counterparty_draft.docx')
SIGNING = {'entity_details': {'company_number': {'status': 'signing_blank', 'answer': 'נשלים לפני החתימה'}}}
ENTRY_POINTS = ('risk/extract_corpus.py', 'risk/validate_register.py', 'risk/render_check.py', 'risk/entity_store.py',
                'risk/logo.py', 'risk/pre_send.py')


# ------------------------------------------------------------------------- 1. נקודות כניסה
@pytest.mark.parametrize('script', ENTRY_POINTS)
def test_every_entry_point_uses_argparse_with_explicit_out_and_writes_no_pycache(script):
    """כל main: argparse עם --out מפורש. הרצה משורת הפקודה (בלי -B) אינה כותבת __pycache__ לתוך החבילה."""
    def caches():
        return {r for r, d, f in os.walk(ROOT) if os.path.basename(r) == '__pycache__'}
    before = caches()
    env = {k: v for k, v in os.environ.items() if k != 'PYTHONDONTWRITEBYTECODE'}
    env['PYTHONIOENCODING'] = 'utf-8'
    p = subprocess.run([sys.executable, os.path.join(ROOT, script), '--help'], capture_output=True, env=env,
                       cwd=ROOT, timeout=120)
    assert p.returncode == 0, p.stderr.decode('utf-8', 'replace')
    assert b'--out' in p.stdout
    assert caches() == before, 'נוצר __pycache__ בתוך החבילה: %s' % (caches() - before)


def test_guard_out_refuses_inputs_and_client_source_folders(tmp_path):
    doc = tmp_path / 'הסכם.docx'
    doc.write_bytes(b'PK')
    with pytest.raises(OutputRefused):
        guard_out(str(doc), [str(doc)])
    with pytest.raises(OutputRefused):
        guard_out(str(tmp_path / 'לקוח' / 'מהצד-שכנגד' / 'out.json'))
    with pytest.raises(OutputRefused):
        guard_out(str(doc))                      # מסמך קיים
    with pytest.raises(OutputRefused):
        guard_out('')
    assert guard_out(str(tmp_path / 'out.json'), [str(doc)]).endswith('out.json')


def test_validate_register_main_out_never_overwrites_the_register(tmp_path):
    from risk.validate_register import main
    reg = tmp_path / 'risk-register.json'
    reg.write_text(open(os.path.join(ROOT, 'tests', 'fixtures', 'risk', 'c2_register.json'), encoding='utf-8').read(),
                   encoding='utf-8')
    before = reg.read_bytes()
    with pytest.raises(OutputRefused):
        main([str(reg), '--out', str(reg)])
    assert reg.read_bytes() == before
    main([str(reg), '--out', str(tmp_path / 'report.json')])
    assert 'errors' in json.loads((tmp_path / 'report.json').read_text(encoding='utf-8'))


# ------------------------------------------------------------------------- 3. איתור הפלייבוק
def test_resolve_accepts_path_or_core_path_and_role_synonyms(tmp_path):
    fx = json.load(io.open(os.path.join(H.FIX, 'resolve', 'fixtures.json'), encoding='utf-8'))
    folder = tmp_path / 'client'
    data = folder / 'Areo-נתונים'
    fam = data / 'playbooks' / 'fam_services'
    fam.mkdir(parents=True)
    core = dict(fx['indexed_valid_core'], company_role_code='customer')
    (fam / 'playbook-core.json').write_text(json.dumps(core, ensure_ascii=False), encoding='utf-8')
    (fam / 'playbook-model.json').write_text(json.dumps(fx['indexed_valid_model'], ensure_ascii=False),
                                             encoding='utf-8')
    for entry in ({'path': 'playbooks/fam_services/playbook-core.json'}, {'path': 'playbooks/fam_services'},
                  {'core_path': 'playbooks/fam_services/playbook-core.json'}):
        entry.update(family_code='services', company_role_code='customer', language='he', last_updated='2026-10-01')
        (data / 'playbooks' / 'index.json').write_text(json.dumps({'playbooks': [entry]}), encoding='utf-8')
        res = rp.resolve(str(data), str(folder), 'services', 'service_recipient', 'he')
        assert res['result'] == 'match' and 'fam_services' in res['chosen'], (entry, res['candidates'])
    assert rp.same_role('buyer', 'licensee') and rp.same_role('Service Recipient', 'customer')
    assert not rp.same_role('customer', 'supplier') and rp.role_side('mutual') == 'mutual'


# ------------------------------------------------------------------------- 4. גבולות מילה
def test_forbidden_terms_use_hebrew_word_boundaries():
    def codes(text):
        return [f for f in qa_gate.check_bubbles([{'id': '1', 'text': text}], '', {}) if f['code'] == 'BUB_FORBIDDEN']
    assert not codes('הצעת המחיר ירוקנו אותה בהסכמה, ועלות הפירוק עלינו.')
    assert codes('לפי הנוסח הירוק שלנו.') and codes('זה הנוסח הצהוב.')
    assert not codes('המדיניותנו')            # לא מילה שלמה
    assert terms_re(['מאשר']).search('הם מאשרים') and not terms_re(['מאשר']).search('המאשררים')
    for lst in (rt.BANNED, S.__dict__.get('BANNED', ())):
        for t in lst:
            assert terms_re([t]).search('x %s y' % t)


# ------------------------------------------------------------------------- 5. playbook_resolution
def test_state_builder_writes_playbook_resolution_at_root():
    st = sb.build_state('deal_x', 1, resolution={'result': 'match', 'chosen': 'a.json', 'activation_question': False,
                                                  'candidates': [{'x': 1}]})
    assert st['playbook_resolution']['chosen'] == 'a.json' and 'candidates' not in st['playbook_resolution']
    assert 'playbook_resolution' not in st['playbook_status']
    assert not [e for e in sb.validate_state(st) if e['code'] == 'STATE_UNKNOWN_KEY']


# ------------------------------------------------------------------------- 6. סעיף חדש (מזהה N)
def test_validate_state_accepts_new_clause_id_from_numbering_map():
    st = sb.skeleton()
    st['clauses'] = [{'clause_id': 'S01'}]
    st['numbering_map'] = {'S01': 'סעיף 1', 'N01': 'סעיף 1א (חדש)'}
    st['deliberate_concessions'] = [{'topic': 't', 'clause_ref': 'N01', 'reason': 'r',
                                     'user_decision': {'answer_kind': 'explicit'}}]
    codes = {e['code'] for e in sb.validate_state(st)}
    assert not {'STATE_NUMBERING_MAP_KEY', 'STATE_CLAUSE_REF'} & codes


# ------------------------------------------------------------------------- 7. accept וכיסוי
def test_accept_op_gives_untouched_elements_a_clause_id_and_coverage(tmp_path):
    draft = H.small_draft(str(tmp_path / 'd.docx'), ['כותרת', 'סעיף אחד', 'סעיף שניים'])
    dec = H.decisions({'id': 'A01', 'op': 'accept', 'para': 0, 'decision_code': 'A1'},
                      {'id': 'C02', 'op': 'replace', 'para': 1, 'new_text': 'סעיף אחד מתוקן', 'decision_code': 'R1',
                       'external_comment': 'מבהירים את הסעיף.'})
    assert dt.validate_decisions(dec) == []
    res = dt.apply_decisions(draft, dec, out_path=str(tmp_path / 'w.docx'))
    assert res['ok'] and res['expected_accept'][0] == 'כותרת'
    bad = H.decisions({'id': 'A01', 'op': 'accept', 'para': 0, 'decision_code': 'R1'})
    assert dt.validate_decisions(bad)
    st = sb.build_state('deal_x', 1, decisions=dec, para_count=3)
    cov = {c['element_id']: c for c in st['coverage_index']}
    assert cov['E-001']['decision'] == 'accept_as_is' and cov['E-001']['clause_id'] == 'A01'
    assert cov['E-002']['decision'] == 'tracked_change'
    assert cov['E-003']['decision'] is None
    assert 'STATE_COVERAGE_GAP' in {e['code'] for e in sb.validate_state(st)}
    dec['decisions'].append({'id': 'A03', 'op': 'accept', 'para': 2, 'decision_code': 'A1'})
    st = sb.build_state('deal_x', 1, decisions=dec, para_count=3)
    assert sb.coverage_gaps(st['coverage_index']) == []


# ------------------------------------------------------------------------- 8. רשומת אישור ישנה
def test_legacy_approval_record_is_one_rule_in_status_and_ingest(tmp_path):
    m = PB.good_model()
    for q in m.get('validation_queue') or []:
        q.update(status='closed', answered=True)
    cells = {k: {'status': 'approved', 'policy_claim': True, 'approved_at': '2026-10-14'} for k in S.iter_cell_keys(m)}
    good = {'record_id': 'APR-0002', 'cells': cells,
            'evidence': {'received_via': 'user_upload', 'upload_ref': 'att_7f3a9c21'}}
    legacy = {'record_id': 'APR-0001', 'cells': cells}
    assert S.derive_status(m, cells, record=good)['playbook_status'] == 'Approved'
    st = S.derive_status(m, cells, record=legacy)
    assert st['playbook_status'] == 'Draft' and st['notices'] == [S.REUPLOAD_NOTICE]
    assert not any(S.cell_counts(c) for c in I.record_cells(legacy).values())
    assert all(S.cell_counts(c) for c in I.record_cells(good).values())
    m['approval_records'] = [{'record_id': 'APR-0001', 'evidence': {'received_via': 'user_upload'}}]
    assert S.derive_status(m, cells)['legacy_record'] is True       # גם מהמודל, בלי upload_ref
    path = tmp_path / 'APR-0001.json'
    path.write_text(json.dumps(legacy, ensure_ascii=False), encoding='utf-8')
    changed, notice = I.migrate_legacy_record(str(path))
    assert changed and notice == S.REUPLOAD_NOTICE
    assert I.migrate_legacy_record(str(path)) == (False, None)    # ההודעה פעם אחת
    saved = json.loads(path.read_text(encoding='utf-8'))
    assert saved['legacy'] and saved['simulated'] and not any(c['policy_claim'] for c in saved['cells'].values())


# ------------------------------------------------------------------------- 9. טבלת "לאישורך"
def test_review_table_shows_hebrew_answer_kind():
    rows = rt.build_review_table([], concessions=[{'topic': 'סודיות', 'user_decision': {'answer_kind': 'delegated'}},
                                                  {'topic': 'שיפוט', 'user_decision': {'answer_kind': 'explicit'}}])
    txt = rt.render_markdown(rows)
    assert 'delegated' not in txt and 'explicit' not in txt
    assert 'תשובה כללית' in txt and 'הכרעה מפורשת' in txt
    assert rt.check_review_table(rows) == []
    assert 'english_label' in rt.check_review_table([{'סעיף': '1', 'מה הוכרע': 'x', 'תווית מקור': 'delegated'}])


# ------------------------------------------------------------------------- 10. פריטים קטנים
def test_basis_sentence_singular_and_plural():
    m = {'market_research': {'counts': {'found': 1, 'opened': 1, 'read': 1, 'counted': 1}}}
    s = MC.basis_sentence(m, legal_sources=1)
    assert '1 משפחות' not in s and 'משפחת תבנית אחת' in s and 'עובדת דין אחת' in s
    assert MC.count_claims(s, m) == []
    m3 = {'market_research': {'counts': {'read': 4, 'counted': 3}}}
    assert '3 משפחות תבנית' in MC.basis_sentence(m3) and 'מתוך 4 מסמכים שנקראו' in MC.basis_sentence(m3)
    assert MC.count_claims('הפלייבוק נבנה לפי משפחת תבנית אחת של הסכמים.', m3)


def test_entity_store_writes_to_the_one_documented_folder(tmp_path):
    st = EntityStore(str(tmp_path))
    entry, path = st.store_page('SRC-001', 'https://www.gov.il/x', b'<html>x</html>')
    assert entry['file'] == 'sources/SRC-001.htm' and os.path.dirname(path) == str(tmp_path / 'sources')
    assert not (tmp_path / 'raw').exists()


def test_strip_secrets_keeps_benign_st_and_uses_a_token_list():
    clean, removed = strip_secrets('https://www.gov.il/he/search?q=law&st=2&state=active&author=x&skip=10')
    assert removed == [] and 'st=2' in clean and 'author=x' in clean
    clean, removed = strip_secrets('https://a.blob.core.windows.net/c/f.pdf?sv=2022&st=2026&se=2026&sp=r&sig=abc')
    assert set(removed) == {'sv', 'st', 'se', 'sp', 'sig'} and '?' not in clean.rstrip('?')
    _, removed = strip_secrets('https://x.org/a?X-Amz-Security-Token=t&access_token=1&api_key=2&q=ok')
    assert set(removed) == {'X-Amz-Security-Token', 'access_token', 'api_key'}
    _, removed = strip_secrets('https://login.x.org/cb?code=abc&state=xyz&client_id=1')
    assert {'code', 'state'} <= set(removed)


# ------------------------------------------------------------------------- הלולאה שלפני המשלוח (C1, C3)
def _register(*ids, clause='S04'):
    return {'pre_send_fixes': [{'id': i, 'kind': 'created_by_response', 'gap': 'פער %s' % i, 'where': 'סעיף 4',
                                'risk_ids': ['RSK-001'], 'clause_ref': clause, 'status': 'open'} for i in ids]}


def _deal(tmp_path, reg, state):
    deal = tmp_path / 'deal'
    deal.mkdir(exist_ok=True)
    pre_send.save_register(str(deal), reg)
    sp = deal / 'negotiation_state.json'
    sp.write_text(json.dumps(state, ensure_ascii=False), encoding='utf-8')
    return str(deal), str(sp)


def _dec_with(fix_ids):
    dec = copy.deepcopy(H.load_decisions('services2_decisions_clean.json'))
    next(d for d in dec['decisions'] if d['id'] == 'S04')['reopened_from_fix'] = fix_ids
    return dec


def test_reopened_from_fix_accepts_a_list_for_two_fixes_on_one_clause():
    dec = _dec_with(['PSF-1', 'PSF-2'])
    assert dt.validate_decisions(dec) == []
    reg = _register('PSF-1', 'PSF-2')
    st = {'clauses': [{'clause_id': 'S04', 'reopened_from_fix': ['PSF-1', 'PSF-2']}]}
    pre_send.resolve_fix(reg, 'PSF-1', 'S04', decisions=dec)
    pre_send.resolve_fix(reg, 'PSF-2', 'S04', decisions=dec)
    assert pre_send.check(reg, st, dec) == []
    bad = _dec_with(['PSF-1', 7])
    assert dt.validate_decisions(bad)


def test_resolved_requires_an_actual_changed_decision():
    dec = _dec_with('PSF-1')
    reg = _register('PSF-1')
    reg['pre_send_fixes'][0].update(status='resolved', resolution={'how': 'reopened', 'decision_id': 'S04'})
    st = {'clauses': [{'clause_id': 'S04', 'reopened_from_fix': 'PSF-1'}]}
    assert pre_send.check(reg, st, dec) == []
    assert [f['code'] for f in pre_send.check(reg, st)] == ['RISK_FIX_RESOLUTION_UNVERIFIED']   # בלי קובץ ההכרעות
    reg['pre_send_fixes'][0]['resolution']['decision_id'] = 'S99'
    assert [f['code'] for f in pre_send.check(reg, st, dec)] == ['RISK_FIX_RESOLUTION_UNVERIFIED']
    comment = copy.deepcopy(dec)
    for d in comment['decisions']:
        if d['id'] == 'S04':
            d['op'] = 'comment_only'
    reg['pre_send_fixes'][0]['resolution']['decision_id'] = 'S04'
    assert [f['code'] for f in pre_send.check(reg, st, comment)] == ['RISK_FIX_RESOLUTION_UNVERIFIED']


def test_concession_from_a_general_answer_is_rejected():
    reg = _register('PSF-1')
    st = {}
    with pytest.raises(ValueError):
        pre_send.concede_fix(reg, st, 'PSF-1', 'תשובה כללית', {'answer_kind': 'delegated'})
    reg['pre_send_fixes'][0]['status'] = 'conceded'
    st = {'deliberate_concessions': [{'clause_ref': 'S04', 'from_pre_send_fix': 'PSF-1',
                                      'user_decision': {'answer_kind': 'delegated'}}]}
    assert [f['code'] for f in pre_send.check(reg, st)] == ['RISK_FIX_CONCESSION_MISSING']


def test_close_fixes_writes_register_and_state_atomically(tmp_path):
    dec = _dec_with(['PSF-1'])
    state = {'clauses': [{'clause_id': 'S04', 'reopened_from_fix': ['PSF-1']}], 'pre_send_fixes': []}
    deal, sp = _deal(tmp_path, _register('PSF-1', 'PSF-2'), state)
    reg, st = pre_send.close_fixes(deal, sp, [
        {'fix_id': 'PSF-1', 'how': 'resolved', 'decision_id': 'S04'},
        {'fix_id': 'PSF-2', 'how': 'conceded', 'reason': 'הסיכון מקובל',
         'user_decision': {'answer_kind': 'explicit', 'answer': 'מקבלים'}}], decisions=dec)
    on_disk = json.loads(open(sp, encoding='utf-8').read())
    assert [r['status'] for r in on_disk['pre_send_fixes']] == ['resolved', 'conceded']
    assert [f['status'] for f in pre_send.load_register(deal)['pre_send_fixes']] == ['resolved', 'conceded']
    assert on_disk['deliberate_concessions'][0]['from_pre_send_fix'] == 'PSF-2'
    assert pre_send.check(pre_send.load_register(deal), on_disk, dec) == []


def test_close_fixes_rolls_back_on_invalid_closure_and_on_write_failure(tmp_path, monkeypatch):
    dec = _dec_with(['PSF-1'])
    state = {'clauses': [{'clause_id': 'S04', 'reopened_from_fix': ['PSF-1']}]}
    deal, sp = _deal(tmp_path, _register('PSF-1', 'PSF-2'), state)
    reg_path = pre_send.register_path(deal)
    before = (open(reg_path, 'rb').read(), open(sp, 'rb').read())
    with pytest.raises(ValueError):    # השורה השנייה: ויתור בתשובה כללית. גם הראשונה אינה נכתבת
        pre_send.close_fixes(deal, sp, [{'fix_id': 'PSF-1', 'how': 'resolved', 'decision_id': 'S04'},
                                        {'fix_id': 'PSF-2', 'how': 'conceded', 'reason': 'x',
                                         'user_decision': {'answer_kind': 'delegated'}}], decisions=dec)
    assert (open(reg_path, 'rb').read(), open(sp, 'rb').read()) == before
    real = os.replace
    calls = []

    def flaky(a, b):
        calls.append(b)
        if len(calls) == 2:
            raise OSError('disk full')
        return real(a, b)
    monkeypatch.setattr(os, 'replace', flaky)
    with pytest.raises(OSError):
        pre_send.close_fixes(deal, sp, [{'fix_id': 'PSF-1', 'how': 'resolved', 'decision_id': 'S04'}], decisions=dec)
    monkeypatch.setattr(os, 'replace', real)
    assert (open(reg_path, 'rb').read(), open(sp, 'rb').read()) == before
    assert not [f for f in os.listdir(deal) if f.endswith('.tmp')]


def test_mark_superseded_renames_and_records_in_state(tmp_path):
    deal = tmp_path / 'deal'
    deal.mkdir()
    work = deal / 'הסכם - סבב 1 - פנימי.docx'
    work.write_bytes(b'PK')
    st = {'produced_documents': [{'kind': 'work', 'path': work.name, 'sha256': 'a' * 64}],
          'quality_gate': {'send_copy': None}}
    new = pre_send.mark_superseded(str(work), st, deal_dir=str(deal), reason='replaced', superseded_by='round_1a')
    assert not work.exists() and os.path.exists(new) and 'לא למשלוח' in os.path.basename(new)
    rec = st['produced_documents'][0]
    assert rec['superseded'] and rec['path'] == os.path.basename(new) and rec['original_path'] == work.name
    assert rec['superseded_by'] == 'round_1a' and st['quality_gate']['send_copy'] is None


def test_build_send_copy_records_path_and_sha256_in_state(tmp_path):
    dec = H.load_decisions('services2_decisions_clean.json')
    out = str(tmp_path / 'work.docx')
    res = dt.apply_decisions(S2, dec, out_path=out)
    deal = tmp_path / 'deal'
    deal.mkdir()
    send = str(deal / 'הסכם תחזוקה - סבב 1 - 14.10.2026.docx')
    st = copy.deepcopy(SIGNING)
    g = qa_gate.build_send_copy(out, S2, send, H.PROFILE, st, res['expected_accept'], deal_dir=str(deal))
    assert g['passed'] and os.path.exists(send)
    sc = st['quality_gate']['send_copy']
    assert sc['path'] == os.path.basename(send) and sc['sha256'] == pre_send._sha256(send)
    assert any(d['kind'] == 'send' and d['sha256'] == sc['sha256'] for d in st['produced_documents'])
