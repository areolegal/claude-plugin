# -*- coding: utf-8 -*-
"""playbook/after_ingest.py: מה קורה מיד אחרי כל קליטה מוצלחת של גיליון העמדות, בפונקציה אחת.

הבעיה (סבב 3): אחרי הקליטה המודל אמר "מדיניות מאושרת", ובאותו זמן: Q-01 ו-Q-02 נשארו פתוחות אף
שהיועצת בחרה בגיליון; הבחירות וההנחה שאישרה לא נשמרו ברשומה; התאים במודל נשארו מהרשומה המדומה;
ה-handoff נשאר Draft; וה-Word וה-Workspace לא הופקו מחדש. את הקליטה השנייה עשה רץ של רכיב אחר,
בעזר שכתב בעצמו.

apply_ingest() הוא הצעד היחיד אחרי ingest_approval.ingest + save_record, ורק רכיב הפלייבוק מריץ אותו:
1. סוגר בתור האימות כל שאלה שנבחרה בה אפשרות בגיליון: status closed, answered, answer_verbatim (נוסח
   האפשרות), answer_index, answered_via (מזהה הרשומה), answered_by (החותמים), answered_at.
2. רושם ב-approval_records את הרשומה: הראיה, הבחירות, ההנחות שאושרו (תא, נוסח, מי ומתי) ו-supersedes.
3. status.stamp: אותו מעמד ואותה תווית במודל, בגרעין, באינדקס, ב-handoff, בתאים וב-policy_status.
4. surfaces_render: ה-Word וה-Workspace מקבלים את המעמד החדש, ושם ה-Word משתנה לפי המעמד.
5. status.check_consistency על כל השכבות ועל שני הקבצים. רשימה לא ריקה = הקליטה לא הושלמה.
"""
import io
import json
import os

try:
    from playbook import status as S
    from playbook import surfaces_render as R
except ImportError:  # pragma: no cover
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from playbook import status as S
    from playbook import surfaces_render as R


def close_questions(model, record, record_id):
    """סוגר את שאלות התור שנבחרה בהן אפשרות בגיליון. מחזיר את מזהי השאלות שנסגרו."""
    closed = []
    signers = sorted({s.get('name') for s in (record.get('signers') or {}).values() if s.get('name')})
    by_id = {qi.get('id') or qi.get('queue_id'): qi for qi in model.get('validation_queue') or []}
    for qid, ch in (record.get('choices') or {}).items():
        qi = by_id.get(qid)
        if qi is None:
            continue
        qi.update(status='closed', answered=True, answer_verbatim=ch.get('text') or '',
                  answer_index=ch.get('index'), answered_via=record_id, answered_by=', '.join(signers),
                  answered_at=record.get('received_at'))
        closed.append(qid)
    return closed


def record_entry(record, record_id, record_path, cells):
    """הרשומה כפי שהיא נשמרת במודל (approval_records[]): הראיה, הבחירות וההנחות שאושרו."""
    assumptions = []
    for key, c in sorted(cells.items()):
        for a in c.get('assumptions_confirmed') or []:
            assumptions.append(dict(a, cell=key))
    return {'record_id': record_id, 'record': record_path, 'token': record.get('token'),
            'signed_sha256': record.get('signed_sha256'), 'evidence': record.get('evidence'),
            'simulated': record.get('simulated'), 'counts': record.get('counts'),
            'choices': record.get('choices') or {}, 'assumptions_confirmed': assumptions,
            'signers': {t: {k: s.get(k) for k in ('name', 'role', 'date')} for t, s in
                        (record.get('signers') or {}).items()},
            'warnings': record.get('warnings') or [], 'supersedes': record.get('supersedes')}


def apply_ingest(model, core, index_entry, result, record_path, word_path=None, workspace_path=None):
    """מחיל את תוצאת הקליטה על כל השכבות ועל שני המשטחים. מחזיר {status, word, workspace, closed, problems}."""
    rec = dict(result['record'])
    cells = result['cells']
    record_id = os.path.splitext(os.path.basename(record_path))[0]
    if os.path.exists(record_path):
        with io.open(record_path, encoding='utf-8') as fh:
            saved = json.load(fh)
        rec['supersedes'] = saved.get('supersedes')
    closed = close_questions(model, rec, record_id)
    entries = [e for e in model.get('approval_records') or [] if e.get('record_id') != record_id]
    entries.append(record_entry(rec, record_id, record_path, cells))
    model['approval_records'] = entries
    st = S.stamp(model, core, index_entry, cells, record_id=record_id)
    new_word = new_ws = None
    if word_path:
        new_word, _ = R.restamp_docx(word_path, model, st, cells)
    if workspace_path:
        new_ws = R.restamp_workspace(workspace_path, st)
    paths = ((model.get('handoff') or {}).get('paths'))
    if isinstance(paths, dict) and new_word:
        paths['word'] = os.path.join(os.path.dirname(paths.get('word') or ''), os.path.basename(new_word)) \
            if paths.get('word') else new_word
    problems = S.check_consistency(model, core, index_entry, cells, word_path=new_word, workspace_path=new_ws)
    return {'status': st, 'word': new_word, 'workspace': new_ws, 'closed': closed, 'problems': problems}
