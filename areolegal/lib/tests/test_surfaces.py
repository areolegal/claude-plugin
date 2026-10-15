# -*- coding: utf-8 -*-
"""בדיקות ל-playbook/surfaces_render.py, playbook/after_ingest.py ו-playbook/market_counts.py: אחרי הקליטה,
ה-Word וה-Workspace מציגים את המעמד המחושב, תור האימות סגור, וכל השכבות עקביות (הערות 5.5, שינויים 79 ו-83)."""
import datetime as dt
import os

import pytest

import pb_helpers as H
from common import rtl
from playbook import after_ingest as AI
from playbook import approval_sheet as A
from playbook import ingest_approval as I
from playbook import market_counts as MC
from playbook import status as S
from playbook import surfaces_render as R

CHOICE_R22 = 'chk:choice:R-22:Q-02:0'
ASSUME_R20 = 'chk:assume:R-20:green:0'
LEGAL = {'R-22': ('עו"ד פלונית אלמונית', '14.10.2026'), 'R-15': ('עו"ד פלונית אלמונית', '14.10.2026')}


def _signed_result(tmp_path, m):
    path, manifest = A.build_sheet(m, str(tmp_path / 'sheet'), company='EXAMPLECO', token_uid='0123456789ab')
    signed = H.sign_sheet(path, str(tmp_path / 'signed.docx'), H.ALL_SIGNERS, choices=[CHOICE_R22],
                          assumptions=[ASSUME_R20], legal_by=LEGAL, remove_areo_comments=True)
    res = I.ingest(signed, manifest, received_via='chat_attachment', upload_ref=signed, today='2026-10-14')
    rec = I.save_record(str(tmp_path / 'records'), signed, res)
    return res, rec


def _surfaces(tmp_path, m, tagged=True, cell_lines=None):
    base = S.base_label(m)
    word = H.playbook_docx(str(tmp_path / ('פלייבוק - %s, EXAMPLECO, פלייבוק מוצע 14.10.2026.docx'
                                           % m['family_label'])), m, base, tagged=tagged, cell_lines=cell_lines)
    ws = H.workspace_html(str(tmp_path / 'Areo Workspace - פלייבוק.html'), m, base)
    return word, ws


@pytest.mark.parametrize('tagged', [True, False])
def test_word_and_workspace_are_restamped_after_ingest(tmp_path, tagged):
    """סבב 3: ה-Word וה-Workspace אמרו "טעון אישור" ו-"0 מתוך 63" אחרי קליטה מוצלחת."""
    m = H.good_model()
    core = {'clauses': [{'id': r['rule_id'], 'policy_status': 'Inferred'} for r in m['rules']],
            'status_label': m['status_label'], 'playbook_status': 'Draft'}
    index_entry = {'status_label': m['status_label'], 'playbook_status': 'Draft', 'presentation_label': m['status_label']}
    word, ws = _surfaces(tmp_path, m, tagged=tagged)
    st0 = S.derive_status(m)
    assert 'Workspace: meta.presentation_label: שדה תווית כפול' in R.check_surfaces(st0, word, ws)
    res, rec = _signed_result(tmp_path, m)
    out = AI.apply_ingest(m, core, index_entry, res, rec, word_path=word, workspace_path=ws)
    st = out['status']
    assert st['playbook_status'] == 'Approved'
    assert out['problems'] == [], out['problems']
    # שם הקובץ אומר את המעמד, והקובץ הישן אינו נשאר לצדו
    assert 'מדיניות מאושרת' in os.path.basename(out['word']) and not os.path.exists(word)
    w = R.read_docx_status(out['word'])
    assert w['header'] == [st['label']]
    assert all(v == R.CELL_PREFIX + 'מאושרת, 14.10.2026' for v in (w['cells'].values() if tagged else w['cell_lines']))
    assert 'טעון אישור' not in w['text'] and 'סימולציה' not in w['text']
    meta = R.read_workspace_status(out['workspace'])['meta']
    assert meta['label_now'] == st['label'] and meta['approved_count'] == st['positions_count']
    assert 'presentation_label' not in meta
    assert rtl.audit_docx(out['word'], run_date=dt.date.today()) == []
    assert S.check_consistency(m, core, index_entry, res['cells'], word_path=out['word'],
                               workspace_path=out['workspace']) == []


def test_stale_word_is_detected(tmp_path):
    m = H.good_model()
    word, ws = _surfaces(tmp_path, m)
    res, rec = _signed_result(tmp_path, m)
    AI.close_questions(m, res['record'], 'APR-0001')
    st = S.stamp(m, None, None, res['cells'])
    problems = S.check_consistency(m, None, None, res['cells'], word_path=word, workspace_path=ws)
    assert any(p.startswith('Word: הכותרת העליונה') for p in problems)
    assert any(p.startswith('Workspace: label_now') for p in problems)
    assert st['playbook_status'] == 'Approved'


def test_legacy_word_with_unknown_cell_lines_must_be_rebuilt(tmp_path):
    m = H.good_model()
    word, _ = _surfaces(tmp_path, m, tagged=False, cell_lines=5)
    res, _ = _signed_result(tmp_path, m)
    st = S.derive_status(m, res['cells'])
    with pytest.raises(R.RerenderError):
        R.restamp_docx(word, m, st, res['cells'])


def test_partial_status_is_named_in_the_file_and_cells(tmp_path):
    m = H.good_model()
    word, _ = _surfaces(tmp_path, m)
    res, _ = _signed_result(tmp_path, m)
    cells = dict(res['cells'])
    cells['R-07|-|red'] = dict(cells['R-07|-|red'], status='pending_choice', reason='הנחה שלא אושרה בתא',
                               policy_claim=False)
    AI.close_questions(m, res['record'], 'APR-0001')
    st = S.derive_status(m, cells)
    out, _ = R.restamp_docx(word, m, st, cells)
    assert 'פלייבוק מאושר בחלקו' in os.path.basename(out)
    w = R.read_docx_status(out)
    assert w['cells']['R-07|-|red'].startswith(R.CELL_PREFIX + 'ממתינה לבחירה')
    assert w['header'] == [st['label']] and st['label'].endswith('11 מתוך 12 עמדות מאושרות')


def test_market_counts_one_sentence_everywhere(tmp_path):
    """סבב 3: "10 הסכמים מ-10 גופים" בשורה הראשונה, ו"נספרו 6" באותו מסמך."""
    m = H.round3_model()
    bad = m['market_research']['disclosure']['fixed_sentence']
    assert MC.count_claims(bad, m)
    assert MC.count_claims('נמצאו 14, נפתחו 12, נקראו 10, נספרו 6 (מ-6 משפחות תבנית)', m) == []
    good = MC.basis_sentence(m, legal_sources=3)
    assert good.startswith('הפלייבוק נבנה לפי 6 משפחות תבנית') and '(מתוך 10 מסמכים שנקראו)' in good
    assert MC.count_claims(good, m) == []
    ws = H.workspace_html(str(tmp_path / 'ws.html'), m, S.base_label(m), disclaimer=bad)
    problems = R.check_surfaces(S.derive_status(m), workspace_path=ws, model=m)
    assert any('counted=6' in p for p in problems)
