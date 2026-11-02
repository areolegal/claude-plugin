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
# סטטוס סעיף (n7-rounds.md, שלב ב). ACCEPTED_PENDING: קיבלנו את הנוסח שלהם (A1), או שהם קיבלו את
# שלנו, אבל הצד השני עוד לא הגיב לסבב שבו זה נשלח. CLOSED רק כשהנוסח הוסכם על ידי שני הצדדים: אחרי סבב שבו הצד השני
# לא שינה אותו (counterparty_unchanged) או קיבל אותו (counterparty_accepted). בדיקה עצמאית S1c, H2, 28.10.2026: כל
# 224 הכרעות A1 נרשמו CLOSED כבר בסבב 1, וביניהן 15.2, שהוא גם נקודה לשיחה
CLAUSE_STATUSES = ('CLOSED', 'ACCEPTED_PENDING', 'MOVING', 'STUCK', 'WALK-AWAY', 'OPENED')
CLOSED_BASES = ('counterparty_unchanged', 'counterparty_accepted')
# שינוי שקט (מצב 9): ההכרעה שלנו מסומנת בעותק למשלוח בעקוב אחר שינויים: החזרה, קבלה עם בועה, או קבלה בתנאי (הנוסח
# שלהם עם תוספת שלנו בעקוב אחר שינויים, למשל "such approval not to be unreasonably withheld or delayed": kind:
# accept_with_condition בקובץ ההכרעות; פאנל S1e-R3, 6(h))
SILENT_DECISIONS = ('revert', 'accept_with_comment', 'accept_with_condition')
REVERT_OPS = ('replace', 'replace_span', 'insert_paragraph', 'delete_paragraph')
# סיווגים של compare_rounds שבהם הצד שכנגד שינה את הנוסח או דחה את ההצעה שלנו
THEIR_CHANGE = ('their_silent', 'their_tracked', 'their_rejected_our_insert', 'our_rejected', 'our_accepted_partial')
THEIR_REJECTION = ('our_rejected', 'their_rejected_our_insert')
# תזוזה שלהם באותו סבב, לצד הדחייה: שינוי משלהם בנוסח, או קבלה של חלק מההצעה. דחייה כזו אינה נספרת ל-STUCK
THEIR_MOVEMENT = ('their_tracked', 'our_accepted_partial')
# הצד השני כתב שהעמדה סופית או שאינה נתונה למשא ומתן: המקרה היחיד, לצד הוראת המשתמש, שבו הסלמה בסבב 2 מותרת
FINAL_POSITION = re.compile(r'final position|final offer|non[- ]?negotiable|not negotiable|not (?:open to|subject to|'
                            r'up for) (?:negotiation|discussion)|will not (?:agree|accept) (?:to )?any (?:change|'
                            r'amendment)|עמדה סופית|עמדתנו הסופית|אינ[והםן] נתונ[הים]* למשא ומתן|לא נתונ[הים]* למשא ומתן|'
                            r'אין מקום למשא ומתן', re.I)
# נקודות לשיחה של הכלי (talking_points.py) שמשאירות סעיף פתוח: מה שנשאר לשיחה, והסלמה מוקדמת
OPEN_POINT_KINDS = ('for_call', 'escalation')
# בועה חדשה של הצד השני, או תשובה שלו בשרשור, עם בקשה, על סעיף שהתקבל: הסעיף נשאר פתוח כבקשה שלהם ואינו נסגר
# (S1d-R2, 28.10.2026: בלוק הצדדים נסגר אף שהצד שכנגד ביקש בו בבועה חדשה את השם באנגלית). סגירה במילה אחת
# ("Agreed.") אינה בקשה
CLOSING_REPLY = re.compile(r'^\s*(?:agreed|accepted|noted|thank you|thanks|ok|מוסכם|מקובל|תודה)[.!]?\s*$', re.I)
REQUEST = re.compile(r'\bplease\b|\bkindly\b|\bwe (?:would )?(?:ask|request)\b|\bcould you\b|\bcan you\b|\bwould you\b|'
                     r'\bprovide\b|\bsend us\b|\bconfirm\b|\bclarify\b|\blet us know\b|\?|\bcannot (?:accept|agree|'
                     r'execute|sign)\b|נא\s|אבקש|נבקש|מבקשים|בבקשה|יש להשלים|להשלים|לספק|לשלוח|האם|הבהרה|לא נוכל',
                     re.I)
SITUATIONS = range(1, 10)  # תשעת המצבים של "נדרשת הכרעתך"
CONFIDENTIAL_EN = 'Privileged and confidential: prepared for the purpose of obtaining legal advice'
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
            'policy_claim_allowed',
            # שדה ישן (הלולאה שהוסרה): מתקבל בקובץ קיים ואינו נכתב
            'pre_send_fixes',
            # 1.2.0: המקום הקנוני של איתור הפלייבוק (מעריך הסיכונים קורא אותו כאן)
            'playbook_resolution',
            # (n8b-state-notes.md, "בקובץ המצב"): בשורש, ולא ב-meta. content_checks
            # והשער קוראים אותם רק מכאן (באג 4, הרצה S1b, 28.10.2026)
            'time_anchors', 'post_checks_done', 'checks_reviewed',
            # מפת הסעיפים (הרצה S1c, 28.10.2026): כל מזהה הכרעה לפסקה, לרכיב במפתח הכיסוי ולמספר הסעיף בהסכם
            'clause_map',
            # שינויים שקטים שזוהו בהשוואת הסבב, וההכרעה שמסמנת כל אחד בעותק למשלוח (בדיקה עצמאית S1c, H6)
            'silent_changes')
ROOT_ONLY = ('time_anchors', 'post_checks_done', 'checks_reviewed')
TIME_ANCHOR_ISSUES = ('past', 'empty')
TIME_ANCHOR_STATUS = ('answered', 'accepted', 'fixed')
TEXT_STATUS = ('counterparty_draft', 'their_draft', 'our_unsent_response', 'our_sent_response', 'our_draft', 'agreed')
# הערך הקנוני משותף למעריך הסיכונים (risk/validate_register.TEXT_STATUS): counterparty_draft. their_draft נשאר נרדף
# שמתקבל, כי קובצי מצב קיימים נכתבו בו. our_draft: טיוטה שלנו שטרם נשלחה, ואינה תגובה לטיוטה שלהם (ריצה S2b)
TEXT_STATUS_SYNONYMS = {'their_draft': 'counterparty_draft'}


def canonical_text_status(v):
    return TEXT_STATUS_SYNONYMS.get(v, v)


# הפניה לבונה להשלמת נושאים במחקר (positions_source.market_research_asks, החלטת מוצר 28.10.2026): המקום שבו
# נשאלה השאלה והתשובה. נושא אינו נשאל פעמיים באותה עסקה; השדה בתוך positions_source, ולכן עובר מסבב לסבב
MR_ASKED_AT = ('negotiator_batch', 'negotiator_round_end')
MR_ANSWERS = ('yes', 'no', 'not_now')
# הגישה להחלת הפלייבוק בעסקה (דרישת מוצר 28.10.2026): meta.deal_context.stance = {value, round, answer_kind,
# recorded_at, history[]}. playbook: כמו תמיד (n3b-matrix.md); stricter: מחזיקים בירוק ומעלים יותר; lenient:
# מקבלים צהוב שעומד בתנאי הפלייבוק ומתמקדים באדום. הגישה אינה משנה את הפלייבוק, ואינה מתירה חציית קו אדום בלי
# הכרעה מפורשת או סטייה מדין כופה
STANCES = ('playbook', 'stricter', 'lenient')


def stance_of(state):
    """הגישה שנרשמה בעסקה (playbook, stricter או lenient), או None כשלא נרשמה."""
    s = (((state or {}).get('meta') or {}).get('deal_context') or {}).get('stance')
    return s.get('value') if isinstance(s, dict) else None


def record_stance(state, value, round_number, answer_kind):
    """רושם את הגישה ב-meta.deal_context.stance, עם הסבב שבו נקבעה. גישה קודמת עוברת ל-history. מחזיר את הרשומה."""
    if value not in STANCES:
        raise ValueError('stance הוא playbook, stricter או lenient: %r' % (value,))
    if answer_kind not in ANSWER_KINDS:
        raise ValueError('answer_kind הוא explicit או delegated')
    dc = state.setdefault('meta', {}).setdefault('deal_context', {})
    prev = dc.get('stance') if isinstance(dc.get('stance'), dict) else None
    history = list((prev or {}).get('history') or [])
    if prev:
        history.append({k: prev.get(k) for k in ('value', 'round', 'answer_kind', 'recorded_at')})
    rec = {'value': value, 'round': int(round_number or 1), 'answer_kind': answer_kind, 'recorded_at': now_iso(),
           'history': history}
    dc['stance'] = rec
    return rec


def current_round(state):
    """הסבב שהעבודה בו עכשיו, לפי קובץ המצב (S1d-R2, 28.10.2026: מנת השאלות והגישה נרשמו בסבב 2 כסבב 1, כי
    meta.round_number מתעדכן רק ב-write שבסוף הסבב). הסבב הגבוה מבין meta.round_number והסבב האחרון ב-received_documents;
    וכשהקובץ של הסבב הזה כבר נרשם כנשלח (sent_documents), העבודה היא על הסבב הבא. בלי קובץ מצב: 1."""
    meta = (state or {}).get('meta') or {}

    def rounds(key):
        return [int(d['round']) for d in meta.get(key) or () if isinstance(d, dict)
                and str(d.get('round', '')).isdigit()]
    cur = max([int(meta.get('round_number') or 0)] + rounds('received_documents'))
    sent = rounds('sent_documents')
    if cur and sent and max(sent) >= cur:
        cur = max(sent) + 1
    return cur or 1


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


# מעמד העותק למשלוח ב-quality_gate.send_copy (S1d-R2, 28.10.2026: write --sent רשם אותו כנשלח לפני שעורכת הדין שלחה):
# produced_pending_send מהשער ועד אישור המשתמש; sent אחרי negotiation_state.py sent, או round_tools.py basis בסבב הבא
SEND_COPY_STATUSES = ('produced_pending_send', 'sent')


def send_copy_pending(rec):
    """רשומת העותק למשלוח במעמד "הופק, ממתין לשליחה": {path (יחסי), sha256, recorded_at, status}."""
    out = {k: rec.get(k) for k in ('path', 'sha256', 'recorded_at') if rec.get(k)}
    out['status'] = 'produced_pending_send'
    return out


def produced_document(path, deal_dir, kind):
    """רשומת תוצר אחת: סוג (work / send / as_produced / decisions / state), נתיב יחסי לתיקיית העסקה, ו-sha256."""
    rel = os.path.relpath(os.path.abspath(path), os.path.abspath(deal_dir))
    return {'kind': kind, 'path': rel.replace('\\', '/'), 'sha256': sha256_file(path) if os.path.exists(path) else '',
            'produced_at': now_iso()}


EN_MONTHS = ('January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
             'November', 'December')


def display_date(d=None, lang='he'):
    """תאריך בטקסט למשתמש ובשם קובץ (כלל 3.6): D.M.YYYY בעברית, "3 April 2027" באנגלית. ב-JSON תמיד ISO.
    d: date, datetime או מחרוזת ISO (YYYY-MM-DD); בלעדיו: היום."""
    if d is None:
        d = _dt.date.today()
    elif isinstance(d, str):
        d = _dt.date.fromisoformat(d[:10])
    if str(lang or 'he').lower()[:2] == 'en':
        return '%d %s %d' % (d.day, EN_MONTHS[d.month - 1], d.year)
    return '%d.%d.%d' % (d.day, d.month, d.year)


def skeleton():
    """שלד קובץ המצב, כל המפתחות העליונים, בלי שדות אישור."""
    return {
        'meta': {'transaction_id': '', 'schema_version': SCHEMA_VERSION, 'refs_version': REFS_VERSION,
                 'confidential': 'חסוי: הוכן לצורך קבלת ייעוץ משפטי', 'client_name': '', 'counterparty_name': '',
                 'position': {}, 'contract_type': '', 'our_role': '', 'paper_type': '', 'governing_law': '', 'round_number': 1,
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
        'summary': {'closed': 0, 'accepted_pending': 0, 'moving': 0, 'stuck': 0, 'walk_away': 0, 'opened': 0,
                    'red_line_conflicts': []},
        'user_decisions': [], 'question_batches': [], 'review_table': [], 'internal_summary': '',
        'produced_documents': [], 'playbook_resolution': {},
        'time_anchors': [], 'post_checks_done': [], 'checks_reviewed': [], 'silent_changes': [],
    }


# תשובה כללית אינה אישור (פאנל S1d-R2 ו-S1e-R3, 28.10.2026: "תציגו לנו לאישור" החיל קבלה של 48 שעות, שהאסטרטג סימן
# כגבול הקו האדום). פריט שדורש תשובה מפורשת (question_batch.requires_explicit: מצב 2, counter_tighter, הכרעה על סכום,
# גבול הקו האדום של האסטרטג, התחייבות תפעולית) ונענה בתשובה כללית נשאר פתוח: outcome held_requires_explicit, וההמלצה
# אינה מוחלת. השער חוסם הכרעה כזו שהוחלה (decision_required.requires_explicit עם answer_kind delegated)
HELD_REQUIRES_EXPLICIT = 'held_requires_explicit'


def record_user_decision(state, question_id, situation, answer, answer_kind, applies_to=(), recommendation=None,
                         requires_explicit=False):
    """רושם את תשובת המשתמש כהכרעת המשתמש. situation: אחד מתשעת המצבים (1 עד 9), או None לשאלה שאינה
    "נדרשת הכרעתך" (כרטיס עסקה, רכיבים משלימים). אין מאשר בשם ואין "ממתין לאישור".
    requires_explicit: הפריט דורש תשובה מפורשת. תשובה כללית (delegated) נרשמת, אבל אינה מחילה את ההמלצה: outcome
    held_requires_explicit, והפריט נשאל שוב במפורש."""
    if situation is not None and situation not in SITUATIONS:
        raise ValueError('אין מצב עשירי ל"נדרשת הכרעתך": %r' % (situation,))
    if answer_kind not in ANSWER_KINDS:
        raise ValueError('answer_kind הוא explicit או delegated')
    held = bool(requires_explicit) and answer_kind != 'explicit'
    rec = {'id': question_id, 'situation': situation, 'answer': answer, 'answer_kind': answer_kind,
           'applies_to': list(applies_to), 'recommendation': recommendation,
           'outcome': HELD_REQUIRES_EXPLICIT if held else (
               'user_decided' if answer_kind == 'explicit' else 'applied_recommendation'),
           'recorded_at': now_iso()}
    if requires_explicit:
        rec['requires_explicit'] = True
    state.setdefault('user_decisions', []).append(rec)
    for cl in state.get('clauses', []):
        if cl.get('clause_id') in rec['applies_to']:
            cl['user_decision'] = {'question_id': question_id, 'answer': answer, 'answer_kind': answer_kind,
                                   'recorded_at': rec['recorded_at']}
            if requires_explicit:
                cl['user_decision'].update(requires_explicit=True, outcome=rec['outcome'])
    return rec


def held_for_explicit(state):
    """מזהי השאלות שנענו בתשובה כללית ודורשות תשובה מפורשת, בלי תשובה מפורשת מאוחרת יותר: נשאלות שוב."""
    out = {}
    for q in (state or {}).get('user_decisions') or ():
        if not isinstance(q, dict) or not q.get('id'):
            continue
        if q.get('outcome') == HELD_REQUIRES_EXPLICIT:
            out[q['id']] = q
        elif q.get('answer_kind') == 'explicit':
            out.pop(q['id'], None)
    return set(out)


def _sent_rounds(state):
    return sorted({int(d.get('round')) for d in ((state or {}).get('meta') or {}).get('sent_documents') or ()
                   if isinstance(d, dict) and str(d.get('round', '')).lstrip('-').isdigit()})


def premature_closed(state, c):
    """הסיבה שסעיף CLOSED אינו מוסכם עדיין, או None. CLOSED דורש closed_basis (counterparty_unchanged או
    counterparty_accepted), closed_in_round, ומסמך שנשלח בסבב מוקדם יותר: בלי משלוח הצד השני לא ראה את הנוסח."""
    if c.get('status') != 'CLOSED':
        return None
    if c.get('closed_basis') not in CLOSED_BASES:
        return 'אין closed_basis: counterparty_unchanged או counterparty_accepted'
    if not isinstance(c.get('closed_in_round'), int):
        return 'אין closed_in_round'
    if not any(r < c['closed_in_round'] for r in _sent_rounds(state)):
        return 'אין ב-sent_documents מסמך שנשלח לפני סבב %s' % c['closed_in_round']
    return None


def open_point_clauses(state):
    """מזהי הסעיפים שיש עליהם נקודה לשיחה פתוחה (talking_points שאינה closed_in_call), או ויתור מכוון שעומד
    לשיחה (for_call). סעיף כזה אינו נסגר."""
    out = set()
    for p in (state or {}).get('talking_points') or ():
        # נקודה שעודכנה לפי מצב הסעיף (superseded, talking_points.merge_points) אינה פתוחה עוד
        if not isinstance(p, dict) or p.get('status') in ('closed_in_call', 'closed', 'superseded'):
            continue
        pid = str(p.get('id') or '')
        # נקודה של הכלי היא מידע (חיכוך צפוי, ויתור, נסיגה אחרונה), חוץ מ"נשאר לשיחה" ומהסלמה
        if pid.startswith('auto:') and (p.get('kind') or pid.split(':')[1]) not in OPEN_POINT_KINDS:
            continue
        ids = list(p.get('clause_ids') or ())
        if not ids and pid.startswith('auto:'):
            ids = [pid.split(':', 2)[2].split('#')[0]]
        out.update(ids)
    for w in (state or {}).get('deliberate_concessions') or ():
        if isinstance(w, dict) and w.get('for_call') and w.get('clause_ref'):
            out.add(w['clause_ref'])
    return out


def delivered(state, round_number):
    """האם נשלח לצד השני מסמך בסבב הזה. ויתור, או קבלה (ACCEPTED_PENDING), "ניתן" רק כשנשלח."""
    return int(round_number or 0) in _sent_rounds(state)


def normalize_statuses(state, log=None):
    """CLOSED שאינו מוסכם (premature_closed) הופך ל-ACCEPTED_PENDING, וכך גם CLOSED שיש עליו נקודה פתוחה לשיחה.
    הנוסח שנרשם ב-agreed_text עובר ל-pending_text. מחזיר את מזהי הסעיפים שהומרו."""
    log = log if log is not None else []
    rnd = int(((state or {}).get('meta') or {}).get('round_number') or 1)
    held = open_point_clauses(state)
    done = []
    for c in (state or {}).get('clauses') or ():
        if c.get('status') != 'CLOSED' or not (premature_closed(state, c) or c.get('clause_id') in held):
            continue
        c['status'] = 'ACCEPTED_PENDING'
        c['accepted_in_round'] = c.pop('closed_in_round', None) or c.get('decided_in_round') or rnd
        if c.get('agreed_text'):
            c['pending_text'] = c.pop('agreed_text')
        c.pop('closed_basis', None)
        if c.get('clause_id') in held:
            c['held_for'] = 'talking_point'
        done.append(c.get('clause_id'))
    if done:
        log.append('CLOSED -> ACCEPTED_PENDING (%d): הצד השני עוד לא הגיב, או שיש נקודה פתוחה לשיחה' % len(done))
    return done


def summarize(state):
    """ספירת הסטטוסים ב-summary, כולל accepted_pending. red_line_conflicts נשאר כמו שהוא."""
    sm = state.setdefault('summary', {})
    keys = {'CLOSED': 'closed', 'ACCEPTED_PENDING': 'accepted_pending', 'MOVING': 'moving', 'STUCK': 'stuck',
            'WALK-AWAY': 'walk_away', 'OPENED': 'opened'}
    for k in keys.values():
        sm[k] = 0
    for c in state.get('clauses') or ():
        if c.get('status') in keys:
            sm[keys[c['status']]] += 1
    sm.setdefault('red_line_conflicts', [])
    return sm


def in_fight_list(c):
    """סעיף מרשימת המאבק: tier deal_breaker, או fight_list: true בהכרעה."""
    return c.get('tier') == 'deal_breaker' or bool(c.get('fight_list'))


def _norm(s):
    return re.sub(r'\s+', ' ', re.sub(r'[‎‏‪-‮]', '', s or '')).strip()


def apply_compare(state, compare, round_number):
    """מעדכן את הסטטוסים לפי השוואת הסבב (compare_rounds.py), בסבב round_number, לפני שההכרעות החדשות נכתבות:
    - ACCEPTED_PENDING שהצד השני לא שינה: CLOSED, counterparty_unchanged, agreed_text. נקודה פתוחה לשיחה מחריגה.
    - הצעה שלנו שהתקבלה במלואה (our_accepted): CLOSED, counterparty_accepted.
    - שינוי שלהם (מסומן, שקט, דחייה, קבלה חלקית): MOVING, ו-last_round_changes. סעיף CLOSED שהם שינו נשאר CLOSED,
      ומקבל reopened_by_counterparty: פתיחתו היא הכרעה של עורך הדין (reopen).
    - דחייה שלהם נרשמת ב-rejections (round, by: them, moved). ברירת המחדל אחרי דחייה היא MOVING: מדרגה אחת, בנימוק
      חדש. STUCK רק כשאותה הצעה שלנו, או המדרגה שאחריה, נדחתה בשני סבבים בלי תזוזה שלהם (stuck_reason). הדחייה שלנו
      את הנוסח המקורי שלהם אינה דחייה של הצעה שלנו, ורשימת המאבק או user_focus אינם סיבה ל-STUCK (S1d, 28.10.2026:
      11 ו-13(ii) סומנו STUCK בסבב 2 אחרי דחייה אחת). הסלמה מוקדמת בסבב 2 רק כשהצד השני כתב שהעמדה סופית או שאינה
      נתונה למשא ומתן (FINAL_POSITION, בשרשור שלהם על הסעיף), או בהוראת המשתמש (status: STUCK בקובץ ההכרעות).
    - סעיף שהצד השני שינה בסבב מקבל their_change_round, כדי שהשער ידע מה השתנה בסבב הזה.
    - בועה חדשה של הצד השני, או תשובה שלו בשרשור, עם בקשה (their_requests), על סעיף שהתקבל: MOVING, עם
      their_request, ולא CLOSED. אין צורך ב-reopen. סעיף שאין לו פריט בהשוואה מוצמד לשרשור לפי para_map.
    - כל שינוי שקט נרשם ב-silent_changes, עם decision ריק עד שההכרעה מסומנת בעותק למשלוח.
    ההצמדה לסעיף: לפי clause_map (para מול base_para) לסעיף שהוכרע בסבב הקודם, ולפי הנוסח (pending_text,
    agreed_text, current_text) מול we_sent. מחזיר רשימת שורות לתיעוד."""
    rnd = int(round_number)
    prev = rnd - 1
    items = (compare or {}).get('clauses') or []
    cm = state.get('clause_map') or {}
    held = open_point_clauses(state)
    log = []

    def hits_of(c):
        cid = c.get('clause_id')
        m = cm.get(cid) or {}
        texts = {_norm(c.get(k)) for k in ('pending_text', 'agreed_text', 'current_text') if c.get(k)}
        same_round = int(c.get('decided_in_round') or prev) == prev
        out = []
        for it in items:
            if same_round and isinstance(m.get('para'), int) and it.get('base_para') == m['para']:
                out.append(it)
            elif same_round and isinstance(m.get('after_para'), int) and it.get('base_para') is None \
                    and it.get('after_base_para') == m['after_para']:
                out.append(it)
            elif texts and _norm(it.get('we_sent')) in texts:
                out.append(it)
        return out

    owners = {}
    threads = (compare or {}).get('threads') or []
    # הפסקה בטיוטה של הסבב הקודם לכל פסקה בטיוטה שחזרה (compare_rounds.py, para_map), לסעיף שלא השתנה ואין לו פריט
    recv2base = {pm.get('received_para'): pm.get('base_para') for pm in (compare or {}).get('para_map') or ()
                 if isinstance(pm, dict) and isinstance(pm.get('base_para'), int)}
    requests = their_requests(threads)
    for c in state.get('clauses') or ():
        cid, status = c.get('clause_id'), c.get('status')
        hits = hits_of(c)
        for h in hits:
            owners.setdefault(id(h), cid)
        paras = {h.get('received_para') for h in hits if h.get('received_para') is not None}
        m = cm.get(cid) or {}
        if isinstance(m.get('para'), int) and int(c.get('decided_in_round') or prev) == prev:
            paras |= {j for j, b in recv2base.items() if b == m['para']}
        req = next((requests[j] for j in sorted(paras) if j in requests), None)
        kinds = sorted({h['classification'] for h in hits})
        if kinds:
            c['last_round_changes'] = kinds
            # הנוסח כפי שחזר: אם לא נגענו בסעיף בסבב הזה, זה מה שיישלח, ומולו מוצמד הסעיף בהשוואה הבאה
            c['current_text'] = next((h.get('now') for h in reversed(hits) if h.get('now')), c.get('current_text'))
        changed = [k for k in kinds if k in THEIR_CHANGE]
        if changed:
            c['their_change_round'] = rnd
        if status == 'CLOSED':
            if changed:
                c['reopened_by_counterparty'] = {'round': rnd, 'classification': changed}
                log.append('%s: סעיף מוסכם שהצד השני שינה (%s)' % (cid, ', '.join(changed)))
            continue
        if changed:
            if any(k in THEIR_REJECTION for k in kinds):
                rej = c.setdefault('rejections', [])
                # השוואה שמוחלת פעמיים (תצוגה מקדימה במנת השאלות, ואחריה write) אינה רושמת את הדחייה פעמיים
                if not any(isinstance(r, dict) and r.get('round') == rnd and r.get('by') == 'them' for r in rej):
                    rej.append({'round': rnd, 'by': 'them', 'moved': any(k in THEIR_MOVEMENT for k in kinds)})
            c['status'] = 'MOVING'
            c.pop('held_for', None)
            why = stuck_reason(c, rnd, final_position_said(hits, threads))
            if why:
                c['status'] = 'STUCK'
                c['escalation'] = {'round': rnd, 'proposed': 'call', 'basis': why[0], 'why': why[1]}
                log.append('%s: STUCK בסבב %d (%s), מוצעת שיחה' % (cid, rnd, why[0]))
            continue
        if req and status in ('MOVING', 'ACCEPTED_PENDING', 'OPENED'):
            # בקשה חדשה שלהם, בבועה או בשרשור, על סעיף שהתקבל: נשאר פתוח כבקשה שלהם, ואין צורך ב-reopen
            c['status'] = 'MOVING'
            c['their_request'] = {'round': rnd, 'thread': req.get('root_id'), 'text': req.get('text', '')[:300]}
            c.pop('held_for', None)
            log.append('%s: בקשה חדשה של הצד השני (בועה %s): נשאר פתוח' % (cid, req.get('root_id')))
            continue
        if kinds == ['our_accepted'] and status in ('MOVING', 'ACCEPTED_PENDING', 'OPENED'):
            if cid in held:
                c['status'], c['held_for'] = 'ACCEPTED_PENDING', 'talking_point'
                c.setdefault('accepted_in_round', rnd)
                continue
            c.update(status='CLOSED', closed_in_round=rnd, closed_basis='counterparty_accepted',
                     agreed_text=next((h.get('now') or h.get('we_sent') for h in hits), c.get('pending_text') or ''))
            c.pop('held_for', None)
            continue
        if status == 'ACCEPTED_PENDING' and not hits and int(c.get('accepted_in_round') or prev) <= prev:
            if cid in held:
                c['held_for'] = 'talking_point'
                continue
            c.update(status='CLOSED', closed_in_round=rnd, closed_basis='counterparty_unchanged')
            if c.get('pending_text'):
                c['agreed_text'] = c.pop('pending_text')
            c.pop('held_for', None)
    # שינויים שקטים: רשומה לכל אחד, וההכרעה שמסמנת אותו בעותק למשלוח נקשרת ב-link_silent_decisions
    by_id = {x.get('id'): x for x in state.setdefault('silent_changes', [])}
    for it in items:
        if it.get('classification') != 'their_silent':
            continue
        sid = 'S%d-%s' % (rnd, it.get('received_para') if it.get('received_para') is not None
                          else 's%s' % it.get('sent_para'))
        rec = by_id.get(sid) or {'id': sid, 'round': rnd, 'decision': None, 'decision_ref': None}
        rec.update(clause=it.get('clause'), clause_id=owners.get(id(it)), sent_para=it.get('sent_para'),
                   received_para=it.get('received_para'), we_sent=it.get('we_sent') or '',
                   they_opened_with=it.get('they_opened_with') or '', reopens_closed=it.get('reopens_closed'))
        if sid not in by_id:
            state['silent_changes'].append(rec)
            by_id[sid] = rec
        log.append('שינוי שלא סומן: %s (סעיף %s)' % (sid, it.get('clause') or '?'))
    return log


def their_requests(threads):
    """{פסקה בטיוטה שחזרה: {root_id, text}} לכל שרשור שבו הרשומה החדשה האחרונה של הצד השני היא בקשה (בועה חדשה שלהם,
    או תשובה שלהם בשרשור שלנו), ולא סגירה במילה אחת. שרשור שסומן "בוצע" אינו בקשה."""
    out = {}
    for t in threads or ():
        if t.get('done') or not isinstance(t.get('para'), int):
            continue
        new = [e for e in t.get('entries') or () if e.get('new') and not e.get('ours')]
        if not new or not (t.get('their_new_thread') or t.get('their_reply_to_ours')):
            continue
        text = new[-1].get('text') or ''
        if CLOSING_REPLY.match(text) or not REQUEST.search(text):
            continue
        out.setdefault(t['para'], {'root_id': t.get('root_id'), 'text': text})
    return out


def final_position_said(hits, threads):
    """הצד השני כתב, בשרשור על אחת הפסקאות של הסעיף (תשובה חדשה שלהם או בועה חדשה שלהם), שהעמדה סופית או שאינה
    נתונה למשא ומתן. מחזיר את הביטוי שנמצא, או ''."""
    roots = {r for h in hits for r in h.get('threads') or ()}
    paras = {h.get('received_para') for h in hits if h.get('received_para') is not None}
    for t in threads or ():
        if t.get('root_id') not in roots and t.get('para') not in paras:
            continue
        for e in t.get('entries') or ():
            if e.get('ours') or not e.get('new'):
                continue
            m = FINAL_POSITION.search(e.get('text') or '')
            if m:
                return m.group(0)
    return ''


def stuck_reason(c, round_number, final_said=''):
    """(basis, why) כשהסעיף STUCK, או None. ברירת המחדל אחרי דחייה היא MOVING.
    - final_position: הצד השני כתב שהעמדה סופית או שאינה נתונה למשא ומתן. מותר כבר בסבב 2.
    - rejected_twice: הצעה שלנו, או המדרגה שאחריה, נדחתה בידי הצד השני בשני סבבים שונים, בלי תזוזה שלהם באותו סבב
      (moved). הדחייה שלנו את הנוסח המקורי שלהם (by: us) אינה נספרת.
    רשימת המאבק (tier, fight_list) ו-user_focus אינם סיבה ל-STUCK. הוראת המשתמש נכתבת בקובץ ההכרעות (status: STUCK)."""
    if final_said:
        return ('final_position', 'הצד השני כתב שהעמדה סופית ("%s"): הסלמה מוקדמת, שיחה לפני סבב נוסף' % final_said)
    rounds = sorted({int(r.get('round') or 0) for r in c.get('rejections') or ()
                     if isinstance(r, dict) and r.get('by') == 'them' and not r.get('moved')})
    if len(rounds) >= 2 and rounds[-1] == int(round_number):
        return ('rejected_twice', 'ההצעה שלנו, או המדרגה שאחריה, נדחתה בשני סבבים (%s) בלי תזוזה שלהם: שיחה לפני סבב '
                                  'נוסף' % ', '.join(map(str, rounds[-2:])))
    return None


def link_silent_decisions(state, decisions):
    """הכרעה בקובץ ההכרעות שנושאת silent_change (מזהה מ-silent_changes) היא הסימון שלה בעותק למשלוח: החזרה בעקוב
    אחר שינויים (revert), או קבלה עם בועה (accept_with_comment: comment_only עם external_comment)."""
    by_id = {x.get('id'): x for x in state.get('silent_changes') or ()}
    decs = (decisions or {}).get('decisions', []) if isinstance(decisions, dict) else (decisions or [])
    clauses = {c.get('clause_id'): c for c in state.get('clauses') or ()}
    for d in decs:
        rec = by_id.get(d.get('silent_change'))
        if rec is None:
            continue
        if d.get('op') in REVERT_OPS and d.get('kind') == 'accept_with_condition':
            # קבלה בתנאי: הנוסח שלהם נשאר, והתנאי שלנו מסומן עליו. בסעיף מוסכם זו פתיחה מחדש (reopen), ולא החזרה
            rec['decision'] = 'accept_with_condition'
        elif d.get('op') in REVERT_OPS:
            rec['decision'] = 'revert'
            # שינוי שקט בסעיף מוסכם שהוחזר לנוסח המוסכם: נרשם כשינוי שקט שהוחזר, ואינו פתיחה מחדש (S1e-R3)
            cl = clauses.get(d.get('id')) or clauses.get(rec.get('clause_id')) or {}
            if d.get('kind') == 'restore_agreed' or (cl.get('restore_agreed') or {}).get('silent_change') == rec['id']:
                rec['kind'] = 'restore_agreed'
        elif d.get('op') == 'comment_only' and d.get('external_comment'):
            rec['decision'] = 'accept_with_comment'
        else:
            rec['decision'] = None
        rec['decision_ref'] = d.get('id') if rec['decision'] else None


def unresolved_silent_changes(state, round_number=None):
    """שינויים שקטים של הסבב שאין להם הכרעה מסומנת בעותק למשלוח (decision: revert או accept_with_comment, עם
    decision_ref). שער האיכות חוסם משלוח כשהרשימה אינה ריקה."""
    rnd = int(round_number or ((state or {}).get('meta') or {}).get('round_number') or 0)
    return [x for x in (state or {}).get('silent_changes') or ()
            if int(x.get('round') or 0) == rnd
            and (x.get('decision') not in SILENT_DECISIONS or not x.get('decision_ref'))]


# --------------------------------------------------------------------------- open_items מתעדכן בכל סבב (פאנל S1e-R3)
# בסבב 3 נשארו ב-open_items "בדיקה משפטית, blocks_sending: true" אחרי שהשער עבר, ו"התקרה תלויה בהסכם השירותים"
# אחרי שהתקרה נקבעה בסכום. כמו בנקודות לשיחה (talking_points.merge_points), כל פריט מוערך מחדש מול הסטטוס הנוכחי של
# הסעיפים שלו, ופריט שהתיישן נסגר עם הסיבה (status: closed, closed: {round, why}). הפריט אינו נמחק
OPEN_ITEM_DONE = ('closed', 'done', 'superseded')
LEGAL_ITEM = re.compile(r'בדיקה משפטית|legal review|"נבדק"|"Reviewed"', re.I)


def _clause_text(c, decision=None):
    d = decision or {}
    return ' '.join(str(x or '') for x in (d.get('new'), d.get('new_text'), d.get('text'), c.get('current_text'),
                                            c.get('agreed_text'), c.get('pending_text'), c.get('sent_text')))


def refresh_open_items(state, round_number=None, decisions=None):
    """מעריך מחדש את open_items מול הסטטוס הנוכחי של כל סעיף, ומחזיר שורות לתיעוד. פריט נסגר (status: closed, עם
    closed: {round, why}) כש: (א) הכרעה בסבב סוגרת אותו במפורש (resolves_open_items בקובץ ההכרעות: ה-source של
    הפריט, או תחילת הטקסט שלו); (ב) כל הסעיפים שלו CLOSED; (ג) depends_on (הנוסח שהפריט תלוי בו) אינו עוד בנוסח
    הנוכחי של הסעיף; (ד) פריט בדיקה משפטית שכל הסעיפים שלו סומנו "נבדק". פריט בדיקה משפטית שחוסם משלוח, אחרי שהשער
    עבר במצב משלוח בסבב, מפסיק לחסום (blocks_sending: false, updated: {round, why}) ונשאר על הסעיפים שעוד לא נבדקו.
    פריט שהסעיף שלו השתנה בסבב (אצלם או אצלנו) אחרי שנפתח מסומן recheck: {round, clause_ids}, כדי שייבדק בסיכום."""
    st = state or {}
    rnd = int(round_number or current_round(st))
    by = {c.get('clause_id'): c for c in st.get('clauses') or () if isinstance(c, dict)}
    decs = (decisions or {}).get('decisions', []) if isinstance(decisions, dict) else list(decisions or [])
    dec_by = {d.get('id'): d for d in decs if isinstance(d, dict)}
    resolves = [(str(k), d) for d in decs if isinstance(d, dict) for k in d.get('resolves_open_items') or () if k]
    send_ok = ((st.get('quality_gate') or {}).get('send') or {}).get('passed') is True
    log = []
    for o in st.get('open_items') or ():
        if not isinstance(o, dict) or o.get('status') in OPEN_ITEM_DONE:
            continue
        ids = [i for i in o.get('clause_ids') or () if i]
        cls = [by.get(i) or {} for i in ids]
        text = str(o.get('item') or '')
        why = None
        hit = next((d for k, d in resolves if k == o.get('source') or text.startswith(k)), None)
        if hit is not None:
            why = 'נסגר בהכרעה %s בסבב %d%s' % (hit.get('id'), rnd, (': %s' % (hit.get('reason') or hit.get(
                'summary'))[:160]) if (hit.get('reason') or hit.get('summary')) else '')
        elif cls and all(c.get('status') == 'CLOSED' for c in cls):
            why = 'כל הסעיפים שלו הוסכמו (CLOSED)'
        elif o.get('depends_on') and cls and not any(
                _norm(o['depends_on']).lower() in _norm(_clause_text(c, dec_by.get(i))).lower() for i, c in zip(ids, cls)):
            why = 'הנוסח הנוכחי של הסעיף אינו כולל עוד את "%s"' % o['depends_on']
        elif o.get('kind') == 'legal_review' or LEGAL_ITEM.search(text):
            # אין סימון "נבדק" (כלל יסוד 6): פריט ישן של בדיקה משפטית אינו חוסם משלוח, ונסגר כשהשער עבר במצב משלוח
            o['blocks_sending'] = False
            if send_ok:
                why = 'בדיקה משפטית אינה מעכבת משלוח, והשער עבר במצב משלוח בסבב %d' % rnd
        if why:
            o['status'] = 'closed'
            o['closed'] = {'round': rnd, 'why': why}
            log.append('open_items: נסגר "%s": %s' % (text[:60], why))
            continue
        opened = int(o.get('from_round') or o.get('round') or 0)
        changed = [i for i, c in zip(ids, cls) if opened < rnd and (
            int(c.get('their_change_round') or 0) == rnd
            or (int(c.get('decided_in_round') or 0) == rnd and c.get('op') in REVERT_OPS))]
        if changed:
            o['recheck'] = {'round': rnd, 'clause_ids': changed}
            log.append('open_items: לבדוק "%s": הסעיף השתנה בסבב %d (%s)' % (text[:60], rnd, ', '.join(changed)))
    return log


def open_items_to_recheck(state, round_number=None):
    """פריטים פתוחים שהסעיף שלהם השתנה בסבב: לבדוק בסיכום אם הם עדיין רלוונטיים, ולסגור ב-resolves_open_items."""
    rnd = int(round_number or current_round(state))
    return [o for o in (state or {}).get('open_items') or () if isinstance(o, dict)
            and o.get('status') not in OPEN_ITEM_DONE and int((o.get('recheck') or {}).get('round') or 0) == rnd]


# --------------------------------------------------------------------------- עדכון הפלייבוק מהעסקה (פאנל S1e-R3)
# בסוף סבב שבו נרשמו lawyer_overrides או הכרעות שחרגו מהפלייבוק, שורה אחת בסיכום. מילת ההפעלה מוגדרת בבונה הפלייבוק
PLAYBOOK_UPDATE_TRIGGER = 'עדכון פלייבוק מעסקה'
PLAYBOOK_UPDATE_LINE = {'he': 'בעסקה הזו הוכרעו %d עמדות שונות מהפלייבוק. לעדכון הפלייבוק כתבו "' +
                              PLAYBOOK_UPDATE_TRIGGER + '".',
                        'en': 'In this deal, %d positions were decided differently from the playbook. To update the '
                              'playbook, write "' + PLAYBOOK_UPDATE_TRIGGER + '" (update playbook from deal).'}


def playbook_deviations(state, round_number=None):
    """(כל העמדות בעסקה שהוכרעו שונה מהפלייבוק, אלה שנרשמו בסבב round_number). עמדה היא סעיף (clause_id), או מזהה
    הרשומה כשאין סעיף: lawyer_overrides (הסבב שבו נשלח הקובץ, או הסבב שאחריו, שבו ההבדלים נרשמים), exception_log,
    הכרעה מפורשת של המשתמש במצב 2, ו-counter_tighter שהתקבל בהכרעה מפורשת."""
    st = state or {}
    rnd = int(round_number or current_round(st))
    by = {c.get('clause_id'): c for c in st.get('clauses') or () if isinstance(c, dict)}
    all_ids, now = [], []

    def add(x, recent):
        if not x:
            return
        if x not in all_ids:
            all_ids.append(x)
        if recent and x not in now:
            now.append(x)
    for o in st.get('lawyer_overrides') or ():
        if isinstance(o, dict):
            add(o.get('clause_id') or o.get('clause') or 'override:%s' % (o.get('para') if o.get('para') is not None
                                                                       else o.get('after_para')),
                int(o.get('round') or 0) in (rnd, rnd - 1))
    for e in st.get('exception_log') or ():
        if isinstance(e, dict):
            add(e.get('clause_id') or e.get('clause_ref') or e.get('id') or e.get('topic'),
                int(e.get('round') or 0) == rnd)
    for q in st.get('user_decisions') or ():
        if isinstance(q, dict) and q.get('situation') == 2 and q.get('answer_kind') == 'explicit':
            for cid in q.get('applies_to') or [q.get('id')]:
                add(cid, int((by.get(cid) or {}).get('decided_in_round') or 0) == rnd)
    for cid, c in by.items():
        for h in c.get('concession_history') or ():
            if isinstance(h, dict) and h.get('kind') == 'counter_tighter' and \
                    (h.get('user_decision') or {}).get('answer_kind') == 'explicit':
                add(cid, int(h.get('round') or 0) == rnd)
    return all_ids, now


AREO_CLAUSES_LINE = {'he': 'סעיפי AREO, שאין להם עמדה בפלייבוק והוכרעו כהצעת Areo: %d (%s).',
                     'en': 'Areo clauses, with no position in the playbook, decided as Areo proposals: %d (%s).'}
AREO_UPDATE_TAIL = {'he': ' לעדכון הפלייבוק כתבו "' + PLAYBOOK_UPDATE_TRIGGER + '".',
                    'en': ' To update the playbook, write "' + PLAYBOOK_UPDATE_TRIGGER + '" (update playbook from deal).'}


def areo_clauses_line(state, round_number=None, lang='he', with_trigger=True):
    """שורה אחת בסיכום: סעיפי AREO שהוכרעו בסבב (source_label: areo_proposal), במספר ובמספרי הסעיפים, עם ההצעה לעדכן
    את הפלייבוק (כשהיא לא נאמרה כבר בשורת העדכון). None כשאין."""
    st = state or {}
    rnd = int(round_number or current_round(st))
    nm = st.get('numbering_map') or {}
    ids = [c.get('clause_id') for c in st.get('clauses') or () if isinstance(c, dict)
           and (c.get('source_label') in ('areo_proposal', 'הצעת Areo', 'Areo proposal') or c.get('areo_clause') is True)
           and c.get('op') != 'accept' and int(c.get('decided_in_round') or 0) == rnd]
    if not ids:
        return None
    L = 'en' if str(lang or '').lower()[:2] == 'en' else 'he'
    refs = ', '.join(nm.get(i) or i for i in ids)
    return AREO_CLAUSES_LINE[L] % (len(ids), refs) + (AREO_UPDATE_TAIL[L] if with_trigger else '')


def playbook_update_line(state, round_number=None, lang='he'):
    """השורה לסיכום, או None כשבסבב הזה לא נרשמה עמדה שונה מהפלייבוק."""
    all_ids, now = playbook_deviations(state, round_number)
    if not now:
        return None
    return PLAYBOOK_UPDATE_LINE['en' if str(lang or '').lower()[:2] == 'en' else 'he'] % len(all_ids)


# --------------------------------------------------------------------------- פריט קריטי פתוח בראש הסיכום (פאנל S1e-R3)
CRITICAL_OPEN = ('MOVING', 'STUCK', 'WALK-AWAY', 'OPENED')


def critical_open_clauses(state):
    """סעיפים קריטיים שעוד לא הוסכמו (tier deal_breaker או importance CRITICAL, בסטטוס פתוח), עם ההמלצה האחרונה שנרשמה
    להם (user_decisions), להצגה בשורות הראשונות של הסיכום בסבב סגירה."""
    st = state or {}
    nm = st.get('numbering_map') or {}
    recs = {}
    for q in st.get('user_decisions') or ():
        for cid in (q or {}).get('applies_to') or ():
            if q.get('recommendation'):
                recs[cid] = q['recommendation']
    out = []
    for c in st.get('clauses') or ():
        if not isinstance(c, dict) or c.get('status') not in CRITICAL_OPEN:
            continue
        if c.get('tier') != 'deal_breaker' and str(c.get('importance') or '').upper() != 'CRITICAL':
            continue
        cid = c.get('clause_id')
        rec = recs.get(cid) or ((c.get('escalation') or {}).get('why')) or ''
        ref = nm.get(cid) or c.get('contract_ref') or cid
        dup = next((x for x in out if x['ref'] == ref), None)
        if dup is not None:
            # כמה הכרעות על אותו סעיף בהסכם: שורה אחת, עם ההמלצה הראשונה שנרשמה
            dup['recommendation'] = dup['recommendation'] or rec
            continue
        out.append({'clause_id': cid, 'ref': nm.get(cid) or c.get('contract_ref') or cid, 'status': c.get('status'),
                    'recommendation': rec})
    return out


def record_reopen(state, clause_id, instruction, reason='', round_number=None):
    """הוראה רשומה של עורך הדין לפתוח מחדש סעיף מוסכם, קבלה שנשלחה, או ויתור שנמסר (phase3, כלל 5). נרשמת
    ב-reopen_log וב-concession_history, עם התאריך והסיבה, והסטטוס הופך ל-MOVING. בלי הוראה אין פתיחה."""
    instruction = (instruction or '').strip()
    if not instruction:
        raise ValueError('פתיחה מחדש דורשת את ההוראה של עורך הדין, במילים שלו')
    # הסבב הנוכחי, ולא meta.round_number, שמתעדכן רק ב-write שבסוף הסבב (S1e-R3: נרשם הסבב הקודם)
    rnd = int(round_number or current_round(state))
    c = next((x for x in state.get('clauses') or () if x.get('clause_id') == clause_id), None)
    if c is None:
        raise ValueError('אין בקובץ המצב סעיף %s' % clause_id)
    when = now_iso()
    rec = {'round': rnd, 'instruction': instruction, 'reason': reason or '', 'previous_status': c.get('status'),
           'recorded_at': when}
    c.setdefault('reopen_log', []).append(rec)
    c.setdefault('concession_history', []).append({
        'round': rnd, 'who': 'us', 'kind': 'reopen', 'what': 'פתיחה מחדש בהוראת עורך הדין: %s' % instruction,
        'in_exchange_for': reason or '', 'user_decision': {'answer_kind': 'explicit', 'recorded_at': when}})
    c['status'] = 'MOVING'
    c.pop('held_for', None)
    for w in state.get('deliberate_concessions') or ():
        if w.get('clause_ref') == clause_id:
            w['reopened_in_round'] = rnd
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


def clause_map_entry(d, clause_numbers=None):
    """הרשומה של הכרעה אחת במפת הסעיפים: para (מספר הפסקה בטיוטה שהתקבלה, מ-0) או after_para (סעיף חדש),
    element_id (כמו במפתח הכיסוי), clause_number (המספר בהסכם, מהטיוטה שהתקבלה, כשנמסרה) ו-clause_label.
    מזהה ההכרעה עצמו אינו מקודד את מספר הפסקה: בהרצה S1c, A-n היה פסקה n-1 בתחילת המסמך ו-n-5 בהמשך. המפה הזו היא
    המיפוי היחיד, ורכיב אחר (מעריך הסיכונים) מוצא בה כל סעיף בלי לנחש."""
    e = {'clause_label': d.get('clause_label') or ''}
    if d.get('op') == 'insert_paragraph' or not isinstance(d.get('para'), int):
        e.update(after_para=d.get('after_para') if isinstance(d.get('after_para'), int) else None,
                 element_id='N-%s' % d['id'], clause_number=None)
    else:
        p = d['para']
        e.update(para=p, element_id='E-%03d' % (p + 1),
                 clause_number=(clause_numbers[p] if clause_numbers and p < len(clause_numbers) else None))
    return e


def fill_clause_map(state):
    """משלים במפת הסעיפים כל סעיף שאין לו רשומה (למשל מסבב קודם, בקובץ שנכתב לפני שהמפה נוספה), לפי מפתח
    הכיסוי של אותו קובץ. מחזיר את המזהים שנשארו בלי מיפוי."""
    cm = state.setdefault('clause_map', {})
    by_id = {}
    for c in state.get('coverage_index') or ():
        for cid in list(c.get('clause_ids') or ()) + [c.get('clause_id')]:
            if cid and cid not in by_id:
                by_id[cid] = c
    missing = []
    for cl in state.get('clauses') or ():
        cid = cl.get('clause_id')
        if not cid or cid in cm:
            continue
        c = by_id.get(cid)
        if c and isinstance(c.get('para'), int):
            cm[cid] = {'para': c['para'], 'element_id': c.get('element_id'), 'clause_number': None,
                       'clause_label': (state.get('numbering_map') or {}).get(cid, '')}
        elif c and isinstance(c.get('after_para'), int):
            cm[cid] = {'after_para': c['after_para'], 'element_id': c.get('element_id'), 'clause_number': None,
                       'clause_label': (state.get('numbering_map') or {}).get(cid, '')}
        else:
            missing.append(cid)
    return missing


def initial_status(d):
    """הסטטוס של הכרעה בסבב שבו היא נכתבת. קבלה (A1) היא ACCEPTED_PENDING, ולעולם לא CLOSED: הצד השני עוד לא
    הגיב. CLOSED נקבע רק ב-apply_compare, בסבב הבא. סטטוס מפורש בקובץ ההכרעות (STUCK, WALK-AWAY, OPENED) נשמר."""
    st = d.get('status')
    if st in CLAUSE_STATUSES and st not in ('CLOSED', 'ACCEPTED_PENDING'):
        return st
    if d.get('coverage') == 'for_call':
        return 'MOVING'
    if d.get('decision_code') == 'A1' or d.get('op') == 'accept':
        return 'ACCEPTED_PENDING'
    return 'MOVING'


def counter_tighter_concession(d, round_number):
    """הרשומה ב-concession_history להכרעה שמקבלת הצעה נגדית שלהם שהדוקה מהנסיגה (kind: counter_tighter,
    n7-rounds.md): ויתור שלנו, עם מה שהם נתנו בתמורה (concession בהכרעה) וסוג התשובה של המשתמש.
    None כשההכרעה אינה כזו. בהרצה S1d-R2 write לא רשם אותה, והיא נכתבה ביד (28.10.2026). אין בה חותמת זמן של
    ההרצה, כדי ש-write חוזר באותו סבב לא ירשום אותה פעמיים."""
    if d.get('kind') != 'counter_tighter':
        return None
    if not (d.get('op') == 'accept' or str(d.get('decision_code') or '').startswith('A')
            or d.get('their_changes') == 'accept' or d.get('offered_now') == 'their_wording'):
        return None
    con = d.get('concession') if isinstance(d.get('concession'), dict) else {}
    ud = d.get('user_decision') if isinstance(d.get('user_decision'), dict) else {}
    dr = d.get('decision_required') if isinstance(d.get('decision_required'), dict) else {}
    rec = {'round': int(round_number), 'who': 'us', 'kind': 'counter_tighter', 'decision_id': d.get('id'),
           'what': con.get('what') or d.get('summary') or d.get('plain_effect') or
           'קבלת הצעה נגדית שלהם, הדוקה מהנסיגה',
           'in_exchange_for': con.get('in_exchange_for') or d.get('in_exchange_for') or ''}
    kind = ud.get('answer_kind') or dr.get('answer_kind')
    if kind in ANSWER_KINDS:
        rec['user_decision'] = {'answer_kind': kind}
        if ud.get('recorded_at'):
            rec['user_decision']['recorded_at'] = ud['recorded_at']
    if kind != 'explicit':
        # קבלה של הצעה נגדית הדוקה מהנסיגה דורשת תשובה מפורשת (requires_explicit): בלעדיה הוויתור אינו מוחל, והשער
        # חוסם את המשלוח (פאנל S1d-R2, 48 השעות)
        rec['status'] = HELD_REQUIRES_EXPLICIT
    return rec


# פסקה בתוספת או בנספח: "תוספת 2, פסקה 4", ולא "סעיף 4" (S1d-R2, 28.10.2026). המילה בעברית לפי המילה בהסכם
SCHEDULE_WORD_HE = {'Schedule': 'תוספת', 'Annex': 'נספח', 'Appendix': 'נספח', 'Exhibit': 'נספח', 'Attachment': 'נספח'}


def schedule_label(schedules, para, number, lang='he'):
    """שם הסעיף לפסקה ממוספרת שבתוך תוספת או נספח, או None כשהפסקה בגוף ההסכם."""
    if not schedules or not isinstance(para, int) or para >= len(schedules) or not schedules[para] or not number:
        return None
    word, ident = schedules[para][0], schedules[para][1]
    if str(lang or '').lower()[:2] == 'en':
        return '%s %s, paragraph %s' % (word, ident, number)
    return '%s %s, פסקה %s' % (SCHEDULE_WORD_HE.get(word, word), ident, number)


def build_state(transaction_id, round_number, profile=None, decisions=None, deal_dir=None, produced=(),
                resolution=None, gate=None, concessions=(), entity_details=None, lang='he', text_status=None,
                counterparty_name='', contract_type='', clause_labels=None, para_count=None, clause_numbers=None,
                received_texts=None, clause_schedules=None):
    """בונה קובץ מצב לפי המבנה האחד. decisions: קובץ ההכרעות (dict). clause_labels: {decision_id: "סעיף 3"}.
    concessions: ויתורים מכוונים במבנה של proportionality.waiver_handoff (clause_ref הוא clause_id).
    para_count: מספר הפסקאות בטיוטה שהתקבלה, למפתח הכיסוי (גרסה 1.2.0). received_texts: הטקסט של כל פסקה בטיוטה
    שהתקבלה (קבל הכול), לנוסח שקיבלנו (pending_text), שמולו נבדק בסבב הבא אם הצד השני שינה אותו. clause_schedules:
    לכל פסקה (המילה, המזהה) של התוספת או הנספח שהיא בו, או None (content_checks.schedule_of_paragraphs)."""
    st = skeleton()
    m = st['meta']
    m.update(transaction_id=transaction_id, round_number=int(round_number), round_stage=stage_for_round(round_number),
             generated_at=now_iso(), last_updated=now_iso(), lang=lang, client_name=(profile or {}).get(
                 'organization_name', ''), counterparty_name=counterparty_name, contract_type=contract_type)
    # סימון החיסיון בשפת התוצר (דרישת מוצר 28.10.2026): בעסקה באנגלית, בלי עברית קבועה
    if str(lang or '').lower()[:2] == 'en':
        m['confidential'] = CONFIDENTIAL_EN
    if text_status:
        st['text_status'] = text_status
    labels = clause_labels or {}
    for d in (decisions or {}).get('decisions', []):
        cl = {'clause_id': d['id'], 'decision_code': d.get('decision_code'), 'op': d.get('op'),
              'rule_ids': list(d.get('rule_ids', [])), 'policy_gate': _as_list(d.get('policy_gate')),
              'structural': bool(d.get('structural')), 'conforming': bool(d.get('conforming'))}
        for k in ('safe_wording', 'legal_review_required', 'legal_review', 'user_decision',
                  'tier', 'importance', 'fight_list', 'silent_change', 'dependents', 'conforms_to', 'carried_from',
                  'source_label', 'areo_clause'):
            if k in d:
                cl[k] = copy.deepcopy(d[k])
        if d.get('kind') in ('restore_agreed', 'accept_with_condition'):
            # החזרה לנוסח המוסכם אחרי שינוי שקט שלהם: אינה פתיחה מחדש (negotiation_state.restores_agreed, S1e-R3).
            # קבלה בתנאי של שינוי שקט: אינה החזרה, ובסעיף מוסכם היא פתיחה מחדש
            cl['decision_kind'] = d['kind']
        cl['status'] = initial_status(d)
        cl['decided_in_round'] = int(round_number)
        if cl.get('legal_review_required'):
            # הסבב שבו נפתחה הבדיקה המשפטית (merge_clauses שומר את המוקדם). סעיף שלא השתנה מאז אינו חוסם (השער)
            cl['legal_review_round'] = int(round_number)
        if cl['status'] == 'STUCK' and not d.get('escalation'):
            # STUCK בקובץ ההכרעות הוא הוראת המשתמש להסלים, או עמדה סופית שלהם; round_violations בודק שיש לו בסיס
            cl['escalation'] = {'round': int(round_number), 'proposed': 'call',
                                'basis': d.get('escalation_basis') or 'user_instruction'}
        if cl['status'] == 'ACCEPTED_PENDING':
            cl['accepted_in_round'] = int(round_number)
            p = d.get('para')
            if received_texts and isinstance(p, int) and p < len(received_texts):
                cl['pending_text'] = received_texts[p]
        if str(d.get('decision_code') or '').startswith('R'):
            cl['rejections'] = [{'round': int(round_number), 'by': 'us'}]
        ch = counter_tighter_concession(d, round_number)
        if ch:
            cl['concession_history'] = [ch]
        st['clauses'].append(cl)
        # מפה מלאה: לכל מזהה פסקה ומספר סעיף (clause_map), ו-numbering_map לכל מזהה, ולא רק לסעיפים ששונו
        cme = clause_map_entry(d, clause_numbers)
        st.setdefault('clause_map', {})[d['id']] = cme
        st['numbering_map'][d['id']] = labels.get(d['id']) or (
            schedule_label(clause_schedules, cme.get('para'), cme['clause_number'], lang) or
            ('Clause %s' if str(lang or '').lower()[:2] == 'en' else 'סעיף %s') % cme['clause_number']
            if cme.get('clause_number') else cme['clause_label'])
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
        # העותק למשלוח שהשער הפיק: "הופק, ממתין לשליחה", ולא "נשלח" (S1d-R2: send_copy נשאר null). הוא עובר
        # ל"נשלח" רק באישור המשתמש (negotiation_state.py sent) או בתחילת הסבב הבא (round_tools.py basis)
        rec = gate.get('send_copy_record')
        if gate.get('passed') and isinstance(rec, dict) and rec.get('path'):
            st['quality_gate']['send_copy'] = send_copy_pending(rec)
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
    for k in ROOT_ONLY:
        if k in meta:
            e('STATE_MISPLACED_KEY', '%s יושב בשורש קובץ המצב, ולא ב-meta (n8-state-schema.md). השער אינו '
              'קורא אותו מ-meta; להעביר לשורש (negotiation_state.py migrate)' % k, 'meta/' + k)
    for i, a in enumerate(st.get('time_anchors') or []):
        if not isinstance(a, dict) or not isinstance(a.get('para'), int) or a.get('issue') not in TIME_ANCHOR_ISSUES                 or a.get('status') not in TIME_ANCHOR_STATUS:
            e('STATE_TIME_ANCHOR', 'עוגן זמן: {"para": <מספר>, "issue": "past|empty", "status": '
              '"answered|accepted|fixed", "answer"}', 'time_anchors[%d]' % i)
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
    held = open_point_clauses(st)
    for c in st.get('clauses', []):
        cid, status = c.get('clause_id'), c.get('status')
        if status is not None and status not in CLAUSE_STATUSES:
            e('STATE_CLAUSE_STATUS', 'status חייב להיות אחד מ: %s: %r' % (', '.join(CLAUSE_STATUSES), status), cid)
        why = premature_closed(st, c)
        if why:
            e('STATE_PREMATURE_CLOSED', 'CLOSED רק כשהנוסח הוסכם על ידי שני הצדדים (%s). עד אז ACCEPTED_PENDING '
              '(negotiation_state.py migrate ממיר)' % why, cid)
        elif status == 'CLOSED' and cid in held:
            e('STATE_CLOSED_OPEN_POINT', 'סעיף CLOSED שיש עליו נקודה פתוחה לשיחה: הוא נשאר ACCEPTED_PENDING עד '
              'שהנקודה נסגרה בשיחה (closed_in_call)', cid)
        # תיקון עקבי (conforming עם conforms_to) שנדרש כדי שההסכם לא יסתור את עצמו, בעקבות הכרעה בנושא פתוח, אינו
        # פתיחה מחדש (S1d-R2: 19.1 ותוספת 2 נשארו סותרים את 13(ii) מחשש לפתיחה מחדש)
        conforming = c.get('conforming') and c.get('conforms_to') and \
            int(c.get('decided_in_round') or 0) >= int(c.get('closed_in_round') or 0)
        # החזרה לנוסח המוסכם אחרי שינוי שקט שלהם (restore_agreed) אינה פתיחה מחדש מצדנו (S1e-R3, 6(h))
        restored = int((c.get('restore_agreed') or {}).get('round') or 0) >= int(c.get('closed_in_round') or 0) > 0
        if isinstance(c.get('closed_in_round'), int) and status != 'CLOSED' and not conforming and not restored \
                and not any(
                isinstance(r, dict) and r.get('recorded_at') and int(r.get('round') or 0) >= c['closed_in_round']
                for r in c.get('reopen_log') or ()):
            e('STATE_REOPEN_WITHOUT_INSTRUCTION', 'סעיף מוסכם (closed_in_round %s) שאינו CLOSED בלי הוראה רשומה של '
              'עורך הדין (negotiation_state.py reopen)' % c['closed_in_round'], cid)
    if 'clause_map' in st:
        cm = st.get('clause_map') or {}
        for cid in sorted(c for c in clause_ids if c):
            e_ = cm.get(cid)
            if not isinstance(e_, dict) or not (isinstance(e_.get('para'), int) or isinstance(e_.get('after_para'), int)):
                e('STATE_CLAUSE_UNMAPPED', 'מזהה הכרעה בלי מיפוי לפסקה ב-clause_map: %s. כל מזהה ממופה לפסקה '
                  '(para) או למקום שאחריו נכנס סעיף חדש (after_para)' % cid, cid)
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
    stance = (meta.get('deal_context') or {}).get('stance') if isinstance(meta.get('deal_context'), dict) else None
    if stance is not None:
        if not isinstance(stance, dict) or stance.get('value') not in STANCES or not isinstance(stance.get('round'), int) \
                or stance.get('answer_kind') not in ANSWER_KINDS:
            e('STATE_STANCE', 'meta.deal_context.stance: {"value": "playbook|stricter|lenient", "round": <מספר>, '
              '"answer_kind": "explicit|delegated", "recorded_at", "history": []}', 'meta/deal_context/stance')
    ps = st.get('positions_source') if isinstance(st.get('positions_source'), dict) else {}
    asked_topics = set()
    for i, a in enumerate(ps.get('market_research_asks') or []):
        where = 'positions_source/market_research_asks[%d]' % i
        if a.get('asked_at') not in MR_ASKED_AT:
            e('STATE_MR_ASK', 'asked_at חייב להיות negotiator_batch או negotiator_round_end: %r' % a.get('asked_at'),
              where)
        if a.get('answer') not in MR_ANSWERS:
            e('STATE_MR_ASK', 'answer חייב להיות yes, no או not_now (תשובה שאינה בוחרת היא not_now): %r'
              % a.get('answer'), where)
        topics = a.get('topics') or []
        if not topics:
            e('STATE_MR_ASK', 'הפניה לבונה בלי רשימת נושאים', where)
        for t in topics:
            if t in asked_topics:
                e('STATE_MR_ASK_REPEATED', 'הנושא כבר נשאל בעסקה הזו, ואינו נשאל שוב: %s' % t, where)
        asked_topics.update(topics)
    for d in st.get('produced_documents', []):
        p = d.get('path', '')
        if os.path.isabs(p) or re.match(r'^[A-Za-z]:', p) or p.startswith('\\\\'):
            e('STATE_PRODUCED_PATH', 'נתיב תוצר חייב להיות יחסי לתיקיית העסקה: %s' % p, d.get('kind'))
        if not re.fullmatch(r'[0-9a-f]{64}', d.get('sha256') or ''):
            e('STATE_PRODUCED_SHA', 'תוצר בלי sha256', d.get('kind'))
    sc = (st.get('quality_gate') or {}).get('send_copy')
    if isinstance(sc, dict) and sc.get('status') is not None and sc['status'] not in SEND_COPY_STATUSES:
        e('STATE_SEND_COPY_STATUS', 'quality_gate.send_copy.status: produced_pending_send או sent: %r' % sc['status'],
          'quality_gate/send_copy')
    return E
