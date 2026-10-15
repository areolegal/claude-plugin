# -*- coding: utf-8 -*-
"""בניית קובץ המצב ובדיקתו, במבנה אחד לכל השרשראות (מימוש ייחוס, הערות הנושא ונותן 4.9, שינויים 83 ו-85).

בסבב 3 כל רץ בנה את negotiation_state.json בקוד הדבקה משלו, ושני הרצים כתבו מבנים שונים: round_stage בטקסט
חופשי ("response_produced_send_blocked"), numbering_map לפי מזהה הכרעה בשרשרת אחת ולפי מזהה רכיב בשנייה,
clause_ref של ויתורים לפי מזהה כלל, policy_gate פעם רשימה ופעם אובייקט, ותוצרים פעם ב-deliverables ופעם
ב-produced_documents עם נתיב מוחלט. המודול הזה הוא המקום היחיד שבונה את הקובץ ובודק אותו.

    from orchestrator.state_builder import build_state, validate_state, record_user_decision, produced_document
    state = build_state('deal_x_2026-10-14', 1, profile, decisions=dec, deal_dir=d, produced=[...])
    errors = validate_state(state)   # [] כשהקובץ תקין

אין שרשרת אישורים (החלטת מוצר 1, 14.10.2026): אין בקובץ approval, required_by, authority_table, approved_by או
מצב "ממתין לאישור". הכרעה שחוצה קו אדום או יורדת מתחת לנסיגה היא "נדרשת הכרעתך" (מצב 2, או מצב אחר מתשעת
המצבים), והתשובה נרשמת ב-user_decisions וב-user_decision של ההכרעה. אין מצב עשירי.

Python 3, ספרייה סטנדרטית בלבד.
"""
import copy
import datetime as _dt
import hashlib
import os
import re

SCHEMA_VERSION = '4.9'
REFS_VERSION = '4.9'
ROUND_STAGES = ('opening', 'response', 'closing')
SITUATIONS = range(1, 10)  # תשעת המצבים של "נדרשת הכרעתך"
ANSWER_KINDS = ('explicit', 'delegated')
ISO = re.compile(r'^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d([+-]\d\d:\d\d|Z)$')
NEW_CLAUSE_ID = re.compile(r'^N-?\d+[a-z]?$', re.I)   # סעיף חדש בתגובה שלנו (מפתח ב-numbering_map), 1.2.0
COVERAGE_DECISION = {'accept': 'accept_as_is', 'comment_only': 'comment_only', 'replace': 'tracked_change',
                     'replace_span': 'tracked_change', 'insert_paragraph': 'tracked_change',
                     'delete_paragraph': 'tracked_change'}
COVERAGE_DECISIONS = ('accept_as_is', 'tracked_change', 'comment_only', 'for_call')
RULE_ID = re.compile(r'^(R|V|Q|SEG|DS|LG|PB|OS|EMP)-?\d+$|^mandatory_list:', re.I)
FORBIDDEN_KEYS = ('approval', 'required_by', 'required_approver', 'authority_table', 'approval_required',
                  'approved_by', 'approved_at', 'approval_status', 'escalation_approver', 'approval_table',
                  'approved_by_user_in_chat', 'awaiting_approval')
TOP_KEYS = ('meta', 'playbook_source', 'positions_source', 'profile_gap', 'playbook_status', 'strategy_summary',
            'case_law', 'exception_log', 'clarification_questions', 'posture_confirmation', 'lawyer_overrides',
            'clauses', 'coverage_index', 'sources_log', 'client_answers', 'company_representations', 'open_items',
            'talking_points', 'commitments', 'packages', 'signing_checklist', 'deliberate_concessions',
            'numbering_map', 'text_status', 'entity_details', 'decisions_file', 'quality_gate', 'summary',
            # 4.9
            'user_decisions', 'question_batches', 'review_table', 'internal_summary', 'produced_documents',
            'pre_send_fixes', 'policy_claim_allowed',
            # 1.2.0: המקום הקנוני של איתור הפלייבוק (מעריך הסיכונים קורא אותו כאן)
            'playbook_resolution')
TEXT_STATUS = ('their_draft', 'our_unsent_response', 'our_sent_response', 'agreed')


def stage_for_round(round_number):
    """opening בסבב 1, response בסבב 2, closing מסבב 3 ואילך."""
    n = int(round_number or 1)
    return 'opening' if n <= 1 else ('response' if n == 2 else 'closing')


def now_iso():
    return _dt.datetime.now().astimezone().replace(microsecond=0).isoformat()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b''):
            h.update(chunk)
    return h.hexdigest()


def produced_document(path, deal_dir, kind):
    """רשומת תוצר אחת: סוג (work / send / as_produced / decisions / state), נתיב יחסי לתיקיית העסקה, ו-sha256."""
    rel = os.path.relpath(os.path.abspath(path), os.path.abspath(deal_dir))
    return {'kind': kind, 'path': rel.replace('\\', '/'), 'sha256': sha256_file(path) if os.path.exists(path) else '',
            'produced_at': now_iso()}


def skeleton():
    """שלד קובץ המצב, כל המפתחות העליונים, בלי שדות אישור."""
    return {
        'meta': {'transaction_id': '', 'schema_version': SCHEMA_VERSION, 'refs_version': REFS_VERSION,
                 'confidential': 'חסוי: הוכן לצורך קבלת ייעוץ משפטי', 'client_name': '', 'counterparty_name': '',
                 'position': {}, 'contract_type': '', 'our_role': '', 'paper_type': '', 'round_number': 1,
                 'round_stage': 'opening', 'generated_at': '', 'last_updated': '', 'lang': 'he',
                 'sent_documents': [], 'received_documents': [], 'deal_context': {'facts': []}},
        'playbook_source': '', 'positions_source': {}, 'profile_gap': {}, 'playbook_status': {},
        'strategy_summary': '', 'case_law': {'connector': '', 'rulings': []}, 'exception_log': [],
        'clarification_questions': [], 'posture_confirmation': {}, 'lawyer_overrides': [], 'clauses': [],
        'coverage_index': [], 'sources_log': [], 'client_answers': [], 'company_representations': [],
        'open_items': [], 'talking_points': [], 'commitments': [], 'packages': [],
        'signing_checklist': {'checks': [], 'passed': False}, 'deliberate_concessions': [], 'numbering_map': {},
        'text_status': 'our_unsent_response', 'entity_details': {}, 'decisions_file': '',
        'quality_gate': {'work': {}, 'send': {}, 'send_copy': None},
        'summary': {'closed': 0, 'moving': 0, 'stuck': 0, 'walk_away': 0, 'opened': 0, 'red_line_conflicts': []},
        'user_decisions': [], 'question_batches': [], 'review_table': [], 'internal_summary': '',
        'produced_documents': [], 'pre_send_fixes': [], 'playbook_resolution': {},
    }


def record_user_decision(state, question_id, situation, answer, answer_kind, applies_to=(), recommendation=None):
    """רושם את תשובת המשתמש כהכרעת המשתמש. situation: אחד מתשעת המצבים (1 עד 9), או None לשאלה שאינה
    "נדרשת הכרעתך" (כרטיס עסקה, רכיבים משלימים). אין מאשר בשם ואין "ממתין לאישור"."""
    if situation is not None and situation not in SITUATIONS:
        raise ValueError('אין מצב עשירי ל"נדרשת הכרעתך": %r' % (situation,))
    if answer_kind not in ANSWER_KINDS:
        raise ValueError('answer_kind הוא explicit או delegated')
    rec = {'id': question_id, 'situation': situation, 'answer': answer, 'answer_kind': answer_kind,
           'applies_to': list(applies_to), 'recommendation': recommendation,
           'outcome': 'user_decided' if answer_kind == 'explicit' else 'applied_recommendation',
           'recorded_at': now_iso()}
    state.setdefault('user_decisions', []).append(rec)
    for cl in state.get('clauses', []):
        if cl.get('clause_id') in rec['applies_to']:
            cl['user_decision'] = {'question_id': question_id, 'answer': answer, 'answer_kind': answer_kind,
                                   'recorded_at': rec['recorded_at']}
    return rec


def build_coverage(decisions, para_count=None):
    """מפתח הכיסוי (coverage_index) מקובץ ההכרעות, לפי סדר המסמך (גרסה 1.2.0). לכל פסקה: decision
    (accept_as_is / tracked_change / comment_only / for_call), clause_id (ההכרעה), reason ו-rule_ids. סעיף חדש
    (insert_paragraph) הוא רכיב missing_topic אחרי פסקת העוגן. para_count: מספר הפסקאות בטיוטה שהתקבלה; כשנמסר,
    כל פסקה בלי הכרעה נכנסת עם decision: None, ו-validate_state מחזיר עליה STATE_COVERAGE_GAP."""
    by_para, added = {}, []
    for d in (decisions or {}).get('decisions', []):
        dec = 'for_call' if d.get('coverage') == 'for_call' else COVERAGE_DECISION.get(d.get('op'))
        rec = {'clause_id': d['id'], 'decision': dec, 'reason': d.get('reason') or d.get('internal_comment') or '',
               'rule_ids': list(d.get('rule_ids', []))}
        if d.get('op') == 'insert_paragraph':
            added.append(dict(rec, element_id='N-%s' % d['id'], element_type='missing_topic',
                              after_para=d.get('after_para')))
        elif 'para' in d:
            cur = by_para.get(d['para'])
            if cur is None:
                by_para[d['para']] = dict(rec, element_id='E-%03d' % (d['para'] + 1), para=d['para'],
                                          clause_ids=[d['id']])
            else:
                cur['clause_ids'].append(d['id'])
                if cur['decision'] != 'tracked_change' and dec == 'tracked_change':
                    cur['decision'] = dec
    paras = range(para_count) if para_count is not None else sorted(by_para)
    out = []
    for i in paras:
        out.append(by_para.get(i) or {'element_id': 'E-%03d' % (i + 1), 'para': i, 'decision': None,
                                      'clause_id': None, 'clause_ids': [], 'reason': '', 'rule_ids': []})
        out += [a for a in added if a.get('after_para') == i]
    out += [a for a in added if a not in out]
    return out


def coverage_gaps(coverage):
    """רכיבים בלי הכרעה מפורשת."""
    return [c for c in coverage or [] if c.get('decision') not in COVERAGE_DECISIONS]


def build_state(transaction_id, round_number, profile=None, decisions=None, deal_dir=None, produced=(),
                resolution=None, gate=None, concessions=(), entity_details=None, lang='he', text_status=None,
                counterparty_name='', contract_type='', clause_labels=None, para_count=None):
    """בונה קובץ מצב לפי המבנה האחד. decisions: קובץ ההכרעות (dict). clause_labels: {decision_id: "סעיף 3"}.
    concessions: ויתורים מכוונים במבנה של proportionality.waiver_handoff (clause_ref הוא clause_id).
    para_count: מספר הפסקאות בטיוטה שהתקבלה, למפתח הכיסוי (גרסה 1.2.0)."""
    st = skeleton()
    m = st['meta']
    m.update(transaction_id=transaction_id, round_number=int(round_number), round_stage=stage_for_round(round_number),
             generated_at=now_iso(), last_updated=now_iso(), lang=lang, client_name=(profile or {}).get(
                 'organization_name', ''), counterparty_name=counterparty_name, contract_type=contract_type)
    if text_status:
        st['text_status'] = text_status
    labels = clause_labels or {}
    for d in (decisions or {}).get('decisions', []):
        cl = {'clause_id': d['id'], 'decision_code': d.get('decision_code'), 'op': d.get('op'),
              'rule_ids': list(d.get('rule_ids', [])), 'policy_gate': _as_list(d.get('policy_gate')),
              'structural': bool(d.get('structural')), 'conforming': bool(d.get('conforming'))}
        for k in ('safe_wording', 'legal_review_required', 'legal_review', 'reopened_from_fix', 'user_decision'):
            if k in d:
                cl[k] = copy.deepcopy(d[k])
        st['clauses'].append(cl)
        st['numbering_map'][d['id']] = labels.get(d['id'], '')
    if decisions is not None:
        st['coverage_index'] = build_coverage(decisions, para_count)
    if deal_dir:
        st['produced_documents'] = [produced_document(p, deal_dir, k) for k, p in produced]
        if decisions is not None:
            st['decisions_file'] = 'decisions_round_%d.json' % int(round_number)
    if resolution:
        # 1.2.0: המקום הקנוני הוא שורש קובץ המצב (מעריך הסיכונים קורא אותו כאן; קובץ ישן: playbook_status)
        st['playbook_resolution'] = {k: v for k, v in resolution.items() if k != 'candidates'}
        st['playbook_source'] = resolution.get('chosen', '')
    if gate:
        st['quality_gate'][gate.get('mode', 'work')] = {'passed': gate.get('passed'),
                                                        'codes': sorted({f['code'] for f in gate.get('failures', [])})}
    st['deliberate_concessions'] = [copy.deepcopy(c) for c in concessions]
    if entity_details:
        st['entity_details'] = copy.deepcopy(entity_details)
    return st


def _as_list(x):
    if x is None:
        return []
    return list(x) if isinstance(x, list) else [x]


def _walk_keys(o, path=''):
    if isinstance(o, dict):
        for k, v in o.items():
            yield k, path + '/' + str(k), v
            yield from _walk_keys(v, path + '/' + str(k))
    elif isinstance(o, list):
        for i, x in enumerate(o):
            yield from _walk_keys(x, '%s[%d]' % (path, i))


def validate_state(state):
    """מחזיר רשימת שגיאות [{'code', 'message', 'where'}]; ריקה כשהקובץ תקין."""
    E = []

    def e(code, msg, where=None):
        E.append({'code': code, 'message': msg, 'where': where})

    st = state or {}
    meta = st.get('meta', {})
    for k in st:
        if k not in TOP_KEYS:
            e('STATE_UNKNOWN_KEY', 'מפתח עליון שאינו במבנה: %s' % k, k)
    stage = meta.get('round_stage')
    if stage not in ROUND_STAGES:
        e('STATE_ROUND_STAGE', 'round_stage חייב להיות opening, response או closing: %r' % stage, 'meta/round_stage')
    elif meta.get('round_number') and stage != stage_for_round(meta['round_number']):
        e('STATE_ROUND_STAGE', 'round_stage %s אינו תואם לסבב %s' % (stage, meta['round_number']), 'meta/round_stage')
    if str(meta.get('schema_version', '')) != SCHEMA_VERSION:
        e('STATE_SCHEMA_VERSION', 'schema_version %r (נדרש %s; להמיר ב-state_migrate)' % (meta.get('schema_version'),
                                                                                          SCHEMA_VERSION))
    if st.get('text_status') and st['text_status'] not in TEXT_STATUS:
        e('STATE_TEXT_STATUS', 'text_status לא מוכר: %r' % st['text_status'])
    for k, path, v in _walk_keys(st):
        if k in FORBIDDEN_KEYS:
            e('STATE_APPROVAL_FIELD', 'שדה של שרשרת אישורים: %s (החלטת מוצר 1: אין שרשרת אישורים)' % k, path)
        if k in ('generated_at', 'last_updated', 'produced_at', 'received_at', 'sent_at', 'checked_at',
                 'recorded_at') and isinstance(v, str) and v and not ISO.match(v):
            e('STATE_TIMESTAMP', 'חותמת זמן שאינה ISO 8601 עם היסט: %s=%s' % (k, v), path)
    clause_ids = {c.get('clause_id') for c in st.get('clauses', [])}
    for c in st.get('clauses', []):
        if 'policy_gate' in c and not isinstance(c['policy_gate'], list):
            e('STATE_POLICY_GATE_TYPE', 'policy_gate חייב להיות רשימה', c.get('clause_id'))
        ud = c.get('user_decision')
        if ud and ud.get('answer_kind') not in ANSWER_KINDS:
            e('STATE_USER_DECISION', 'answer_kind לא מוכר', c.get('clause_id'))
    for k in (st.get('numbering_map') or {}):
        if clause_ids and k not in clause_ids and not NEW_CLAUSE_ID.match(k):
            e('STATE_NUMBERING_MAP_KEY', 'מפתח ב-numbering_map שאינו clause_id: %s' % k, k)
    known_refs = clause_ids | set(st.get('numbering_map') or {})   # 1.2.0: גם סעיף חדש (מזהה N) מ-numbering_map
    for c in coverage_gaps(st.get('coverage_index')):
        e('STATE_COVERAGE_GAP', 'רכיב בלי הכרעה מפורשת במפתח הכיסוי: %s' % c.get('element_id'), c.get('element_id'))
    for w in st.get('deliberate_concessions', []):
        ref = w.get('clause_ref') or ''
        if not ref or RULE_ID.match(ref) or (known_refs and ref not in known_refs):
            e('STATE_CLAUSE_REF', 'clause_ref של ויתור חייב להיות clause_id של סעיף בקובץ המצב, ולא מזהה כלל: %r'
              % ref, w.get('topic'))
        ud = w.get('user_decision') or {}
        if ud.get('answer_kind') not in ANSWER_KINDS:
            e('STATE_USER_DECISION', 'ויתור בלי הכרעת משתמש (user_decision.answer_kind)', w.get('topic'))
        if w.get('crosses_red_line') and ud.get('answer_kind') != 'explicit' and not w.get('cure_applied'):
            e('STATE_RED_LINE_WITHOUT_USER_DECISION', 'חציית קו אדום בלי הכרעה מפורשת של המשתמש (מצב 2)',
              w.get('topic'))
    for q in st.get('user_decisions', []):
        if q.get('situation') is not None and q['situation'] not in SITUATIONS:
            e('STATE_SITUATION', 'מצב שאינו אחד מתשעת המצבים: %r' % q['situation'], q.get('id'))
    for d in st.get('produced_documents', []):
        p = d.get('path', '')
        if os.path.isabs(p) or re.match(r'^[A-Za-z]:', p) or p.startswith('\\\\'):
            e('STATE_PRODUCED_PATH', 'נתיב תוצר חייב להיות יחסי לתיקיית העסקה: %s' % p, d.get('kind'))
        if not re.fullmatch(r'[0-9a-f]{64}', d.get('sha256') or ''):
            e('STATE_PRODUCED_SHA', 'תוצר בלי sha256', d.get('kind'))
    return E
