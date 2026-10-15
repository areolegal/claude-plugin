# -*- coding: utf-8 -*-
"""קובץ המצב: גרסת סכמה, המרה מגרסה קודמת, תיקיית היסטוריה וחותמות זמן ISO 8601 עם היסט
(מימוש ייחוס, הערות הנושא ונותן 4.8, שינוי 78; 4.9, שינויים 83 ו-85).

בסבב 2 (C2) ההמשך ממצב "ממתין לרכיב הפלייבוק" נקרא מקובץ שנכתב לפני 4.7, והומר בסקריפט אד-הוק:
round_stage בטקסט חופשי, coverage_index עם decision ריק, מפתחות כפולים (file ו-file_name, received ו-received_at),
ותאריכים בשני פורמטים. הקובץ הישן נשאר בתיקיית העסקה ליד הקובץ החי.

4.9: round_stage שאינו opening, response או closing (למשל "awaiting_playbook_builder" או
"response_produced_send_blocked") נגזר מחדש ממספר הסבב, וערך של המתנה לרכיב הפלייבוק עובר ל-build_state.
שדות של שרשרת אישורים (approval, required_by, authority_table, approved_by, approved_by_user_in_chat) הופכים
להכרעת המשתמש (user_decision) או נמחקים, ו-deliverables עובר ל-produced_documents.

    from orchestrator.state_migrate import migrate_state, history_path, non_iso_timestamps
"""
import copy
import datetime as _dt
import os
import re

SCHEMA_VERSION = '4.9'
REFS_VERSION = '4.9'
ISO = re.compile(r'^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d([+-]\d\d:\d\d|Z)$')
TIME_KEYS = ('generated_at', 'last_updated', 'produced_at', 'received_at', 'sent_at', 'checked_at', 'recorded_at')
LEGACY_STAGE = {r'awaiting_proposed_playbook|awaiting_playbook_builder|awaiting_builder|ממתין לרכיב הפלייבוק':
                'awaiting_builder'}
ROUND_STAGES = ('opening', 'response', 'closing')
APPROVAL_KEYS = ('required_by', 'required_approver', 'approval_required', 'approved_by', 'approved_at',
                 'approval_status', 'escalation_approver', 'awaiting_approval')


def _stage_for_round(n):
    n = int(n or 1)
    return 'opening' if n <= 1 else ('response' if n == 2 else 'closing')


def _user_decision_from(old, fallback_kind=None):
    """approval ישן -> user_decision. "approved" עם שם בצ'אט, או approved_by_user_in_chat, הם תשובה מפורשת;
    proposed הוא החלת המלצה בתשובה כללית (delegated)."""
    if isinstance(old, dict):
        status = old.get('status')
        kind = 'explicit' if status in ('approved', 'changed', 'rejected') else 'delegated'
        return {'answer_kind': fallback_kind or kind, 'answer': old.get('by') or '', 'recorded_at': old.get('at') or ''}
    if old in ('approved', True):
        return {'answer_kind': fallback_kind or 'explicit', 'answer': ''}
    return {'answer_kind': fallback_kind or 'delegated', 'answer': ''}


def _strip_approval_chain(st, log):
    for cl in st.get('clauses', []) + st.get('exception_log', []):
        if 'approval' in cl:
            cl.setdefault('user_decision', _user_decision_from(cl.pop('approval')))
            log.append('approval -> user_decision (%s)' % cl.get('clause_id', cl.get('id', '')))
        if 'approved_by_user_in_chat' in cl:
            v = cl.pop('approved_by_user_in_chat')
            cl.setdefault('user_decision', {'answer_kind': 'explicit' if v else 'delegated', 'answer': ''})
            log.append('approved_by_user_in_chat -> user_decision')
    for w in st.get('deliberate_concessions', []):
        if 'approval' in w or 'answer_kind' in w:
            w.setdefault('user_decision', _user_decision_from(w.pop('approval', None), w.pop('answer_kind', None)))
            log.append('ויתור: approval/answer_kind -> user_decision (%s)' % w.get('topic'))

    def walk(o):
        if isinstance(o, dict):
            for k in list(o):
                if k in APPROVAL_KEYS or k == 'authority_table' or k == 'approval_table':
                    o.pop(k)
                    log.append('נמחק שדה של שרשרת אישורים: %s' % k)
                else:
                    walk(o[k])
        elif isinstance(o, list):
            for x in o:
                walk(x)
    walk(st)
    if 'deliverables' in st:
        st.setdefault('produced_documents', []).extend(
            d if isinstance(d, dict) else {'kind': '', 'path': d, 'sha256': ''} for d in st.pop('deliverables'))
        log.append('deliverables -> produced_documents')


def _iso(value):
    """ממיר "12.10.2026", "2026-10-12" או "2026-10-14T14:17:38" ל-ISO עם היסט מקומי."""
    if not value or ISO.match(str(value)):
        return value
    s = str(value)
    for fmt in ('%d.%m.%Y', '%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%d.%m.%Y %H:%M'):
        try:
            d = _dt.datetime.strptime(s, fmt)
            return d.astimezone().isoformat(timespec='seconds')
        except ValueError:
            continue
    return value


def migrate_state(old):
    """מחזיר (new_state, log). אינו משנה את הקלט. מכסה את ההמרות שהבדיקה של סבב 2 עשתה ביד."""
    st = copy.deepcopy(old)
    log = []
    ver = str(st.get('meta', {}).get('schema_version') or 'legacy')
    meta = st.setdefault('meta', {})
    stage = str(meta.get('round_stage', ''))
    pp = st.setdefault('positions_source', {}).setdefault('proposed_playbook', {})
    for rx, val in LEGACY_STAGE.items():
        if re.search(rx, stage) and not pp.get('build_state'):
            pp['build_state'] = val
            log.append('build_state=%s מתוך round_stage "%s"' % (val, stage))
    if pp.get('build_state') == 'awaiting_builder':
        for c in st.get('coverage_index', []):
            if not c.get('decision'):
                c['decision'] = 'awaiting_playbook'
                log.append('coverage %s: awaiting_playbook' % c.get('element_id'))
    if stage not in ROUND_STAGES:
        meta['round_stage'] = _stage_for_round(meta.get('round_number', 1))
        log.append('round_stage "%s" -> %s (לפי מספר הסבב)' % (stage, meta['round_stage']))
    _strip_approval_chain(st, log)
    for doc in st.get('meta', {}).get('received_documents', []) + st.get('meta', {}).get('sent_documents', []):
        if 'file' in doc and 'file_name' in doc:
            if doc['file'] == doc['file_name'] or not doc['file_name']:
                doc['file_name'] = doc.pop('file') or doc['file_name']
            else:
                doc.pop('file')
            log.append('מפתח כפול file/file_name אוחד')
        if 'received' in doc:
            doc.setdefault('received_at', doc['received'])
            doc.pop('received')
            log.append('מפתח כפול received/received_at אוחד')

    def walk(o):
        if isinstance(o, dict):
            for k, v in list(o.items()):
                if k in TIME_KEYS and isinstance(v, str):
                    nv = _iso(v)
                    if nv != v:
                        o[k] = nv
                        log.append('%s -> ISO' % k)
                else:
                    walk(v)
        elif isinstance(o, list):
            for x in o:
                walk(x)
    walk(st)
    meta['schema_version'] = SCHEMA_VERSION
    meta['refs_version'] = REFS_VERSION
    meta['migrated_from'] = ver
    return st, log


def history_path(transaction_dir, old_state, when=None):
    """הקובץ הישן נשמר בתיקיית history של העסקה, ולא ליד הקובץ החי."""
    when = when or _dt.datetime.now().astimezone()
    ver = str(old_state.get('meta', {}).get('schema_version') or 'legacy')
    return os.path.join(transaction_dir, 'history',
                        'negotiation_state.%s.v%s.json' % (when.strftime('%Y%m%dT%H%M%S'), ver))


def non_iso_timestamps(state):
    """כל חותמת זמן שאינה ISO 8601 עם היסט: רשימה של (מפתח, ערך)."""
    bad = []

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in TIME_KEYS and isinstance(v, str) and v and not ISO.match(v):
                    bad.append((k, v))
                else:
                    walk(v)
        elif isinstance(o, list):
            for x in o:
                walk(x)
    walk(state)
    return bad
