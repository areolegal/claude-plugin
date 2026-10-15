# -*- coding: utf-8 -*-
"""בדיקות ל-orchestrator/state_migrate.py: קובץ מצב בפורמט של לפני 4.7, כמו ב-C2 בסבב 2."""
import os

import orch_helpers  # noqa: F401
from orchestrator import state_migrate as sm

LEGACY = {
    'meta': {'round_stage': 'stopped_at_A2_awaiting_proposed_playbook', 'generated_at': '2026-10-12T12:42:00+03:00',
             'last_updated': '2026-10-14T14:17:38',
             'received_documents': [{'file': 'nda.docx', 'file_name': 'nda.docx', 'received': '12.10.2026',
                                     'received_at': '2026-10-12'}]},
    'work_document': {'produced_at': '2026-10-14T14:17:38'},
    'coverage_index': [{'element_id': 'E-001', 'decision': ''}, {'element_id': 'E-002', 'decision': ''}],
}


def test_migrate_legacy_awaiting_builder():
    new, log = sm.migrate_state(LEGACY)
    assert new['positions_source']['proposed_playbook']['build_state'] == 'awaiting_builder'
    assert {c['decision'] for c in new['coverage_index']} == {'awaiting_playbook'}
    doc = new['meta']['received_documents'][0]
    assert 'file' not in doc and 'received' not in doc and doc['file_name'] == 'nda.docx'
    assert new['meta']['schema_version'] == sm.SCHEMA_VERSION and new['meta']['migrated_from'] == 'legacy'
    assert sm.non_iso_timestamps(new) == []
    assert LEGACY['coverage_index'][0]['decision'] == ''  # הקלט לא השתנה
    assert log


def test_non_iso_detected():
    assert ('last_updated', '2026-10-14T14:17:38') in sm.non_iso_timestamps(LEGACY)


def test_history_path_is_separate_folder(tmp_path):
    p = sm.history_path(str(tmp_path), LEGACY)
    assert os.path.dirname(p) == os.path.join(str(tmp_path), 'history')
    assert os.path.basename(p).startswith('negotiation_state.') and p.endswith('.vlegacy.json')
