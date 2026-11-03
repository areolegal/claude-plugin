# -*- coding: utf-8 -*-
"""playbook/after_ingest.py: מה קורה מיד אחרי כל קליטה מוצלחת של גיליון העמדות, בפונקציה אחת.

הבעיה: אחרי הקליטה המודל אמר "מדיניות מאושרת", ובאותו זמן: Q-01 ו-Q-02 נשארו פתוחות אף
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

save_local_copy() הוא הצעד שאחרי כתיבת הקבצים לתיקייה שהלקוח חיבר (כלל מייסד 6): עותק מקומי של הפלייבוק המאושר במחשב של
הלקוח. שום דבר מהפלייבוק אינו נשלח לשרת של Areo: אין כאן כתובת רשת, והעותק נכתב רק לדיסק.
"""
import io
import json
import os
import re
import shutil

try:
    from playbook import status as S
    from playbook import surfaces_render as R
except ImportError:  # pragma: no cover
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from playbook import status as S
    from playbook import surfaces_render as R


LOCAL_COPY_DIRNAME = 'Areo-playbooks-local'


def local_copy_dir(family_id, base=None):
    """תיקיית העותק המקומי: base (אם נמסר), או <בית המשתמש>/Areo-playbooks-local, ובתוכה תיקייה למשפחה."""
    fam = re.sub(r'[^\w.-]+', '_', str(family_id or 'playbook'), flags=re.U).strip('._') or 'playbook'
    # AREO_LOCAL_COPY_BASE: לבדיקות בלבד, כדי שקליטה בבדיקה לא תכתוב לתיקיית הבית של מי שמריץ אותה
    base = base or os.environ.get('AREO_LOCAL_COPY_BASE') or os.path.join(os.path.expanduser('~'), LOCAL_COPY_DIRNAME)
    return os.path.join(base, fam)


def save_local_copy(paths, family_id, base=None):
    """מעתיק את קובצי הפלייבוק (מודל, גרעין, Word, סביבת עבודה) לעותק המקומי. מחזיר {dir, copied[], errors[]}.
    נתיב שהוא כתובת רשת, או קובץ שחסר, נרשם ב-errors ואינו נכתב. כשהתיקייה אינה ניתנת לכתיבה: errors, בלי חריגה,
    כדי שהאישור שנכתב לתיקיית הלקוח לא ייפול, והקורא אומר שהעותק המקומי לא נשמר (ולא טוען לשמירה שלא התקיימה)."""
    target = local_copy_dir(family_id, base)
    out = {'dir': target, 'copied': [], 'errors': []}
    if '://' in str(base or ''):
        out['errors'].append('העותק המקומי נכתב לדיסק בלבד: %s' % base)
        return out
    try:
        os.makedirs(target, exist_ok=True)
    except OSError as exc:
        out['errors'].append('%s: %s' % (target, exc))
        return out
    for p in paths:
        if not p:
            continue
        if not os.path.isfile(p):
            out['errors'].append('חסר: %s' % p)
            continue
        try:
            shutil.copy2(p, os.path.join(target, os.path.basename(p)))
            out['copied'].append(os.path.basename(p))
        except OSError as exc:
            out['errors'].append('%s: %s' % (p, exc))
    return out


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


LEGAL_Q_PREFIXES = ('טעון בדיקה משפטית', 'Legal review required', 'Needs legal review')


def close_legal_questions(model, cells, record, record_id):
    """נעילה אחת לבדיקה משפטית. שאלת תור מסוג "טעון בדיקה משפטית" על כלל (rule_id או rule_ids) נסגרת כשכל
    התאים הטעונים בדיקה משפטית בכללים שלה נספרים כמאושרים ונרשם בהם מי בדק ומתי. בלי זה עורך דין שענה
    "נבדק ולאשר" פתח רק את התא, והשאלה המכריעה על אותה בדיקה המשיכה לחסום את הנושא. מחזיר את מזהי השאלות."""
    closed = []
    for qi in model.get('validation_queue') or []:
        st = qi.get('status') or ('closed' if qi.get('answered') else 'open')
        if st != 'open' or qi.get('answered'):
            continue
        if not str(qi.get('question') or '').strip().startswith(LEGAL_Q_PREFIXES):
            continue
        rids = [r for r in (qi.get('rule_ids') or [qi.get('rule_id')]) if r and r != 'GLOBAL']
        if not rids:
            continue
        legal = [(k, c) for k, c in cells.items() if k.split('|')[0] in rids and (c or {}).get('legal_review_required')]
        if not legal or set(k.split('|')[0] for k, _ in legal) != set(rids):
            continue
        if not all(S.cell_counts(c) and c.get('legal_review_done_by') for _, c in legal):
            continue
        by = sorted({c.get('legal_review_done_by') for _, c in legal})
        at = max(str(c.get('legal_review_done_at') or record.get('received_at') or '') for _, c in legal)
        qi.update(status='closed', answered=True, answered_via=record_id, answered_by=', '.join(by), answered_at=at,
                  answer_verbatim='נבדק בידי %s ואושר כפי שהוא' % ', '.join(by), closed_by='legal_review')
        closed.append(qi.get('id') or qi.get('queue_id'))
    return closed


def record_entry(record, record_id, record_path, cells):
    """הרשומה כפי שהיא נשמרת במודל (approval_records[]): הראיה, הבחירות וההנחות שאושרו."""
    assumptions = []
    for key, c in sorted(cells.items()):
        for a in c.get('assumptions_confirmed') or []:
            assumptions.append(dict(a, cell=key))
    out = {'record_id': record_id, 'record': record_path, 'token': record.get('token'),
           'signed_sha256': record.get('signed_sha256'), 'evidence': record.get('evidence'),
           'simulated': record.get('simulated'), 'counts': record.get('counts'),
           'choices': record.get('choices') or {}, 'assumptions_confirmed': assumptions,
           'signers': {t: {k: s.get(k) for k in ('name', 'role', 'date')} for t, s in
                       (record.get('signers') or {}).items()},
           'warnings': record.get('warnings') or [], 'supersedes': record.get('supersedes')}
    # רשומה של תור האישור בצ'אט (ingest_approval.apply_answers): סוג, מנה, החלטות הנהלה ועדכונים מעסקה
    if record.get('kind') == 'chat':
        out.update({k: record.get(k) for k in ('kind', 'batch_id', 'stage', 'reply_sha256', 'decisions',
                                                'updates', 'skipped')})
    # רשומה של אישור מאשף ההערות (ingest_approval.wizard_approvals, דרך apply_decisions.py): הקובץ שממנו נקלטה
    if record.get('kind') == 'wizard':
        out.update({k: record.get(k) for k in ('kind', 'source_file', 'source_sha256')})
    return out


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
    closed += close_legal_questions(model, cells, rec, record_id)
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
