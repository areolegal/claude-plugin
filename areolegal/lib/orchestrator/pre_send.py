# -*- coding: utf-8 -*-
"""העותק למשלוח ורשומת ההפקה של הסבב.

- **עותק למשלוח שהשער לא העביר:** עותק שכבר נמצא בנתיב מקבל את הסיומת " - לא למשלוח" (mark_superseded, דרך
  retract_send_copy), ובקובץ המצב נרשם שאין עותק למשלוח (quality_gate.send_copy: null, ופריט ב-open_items שחוסם
  משלוח). עותק שעבר את השער נרשם בקובץ המצב (record_send_copy).
- **הפקה מחדש באותה ריצה:** רשומת ההפקה של הסבב (apply-report-round-<N>.json), reusable_path ו-update_run_record.

מעריך הסיכונים אינו חוסם את המשלוח: אין כאן קריאה של risk-register.json ואין שורות "לתיקון".

    from orchestrator import pre_send
    pre_send.retract_send_copy(send_path, state, 'he', deal_dir=deal_dir)
"""
import datetime as _dt
import hashlib
import io
import json
import os
import re

from common import paths


def _now():
    return _dt.datetime.now().astimezone().replace(microsecond=0).isoformat()


def _write_json_atomic(path, data):
    paths.check_write_path(path)
    tmp = path + '.tmp'
    with io.open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    return tmp


def mark_superseded(path, state=None, deal_dir=None, reason='', superseded_by=None, lang='he'):
    """סימון עותק שהוחלף: הקובץ אינו נמחק, ומקבל את הסיומת " - לא למשלוח" (paths.stale_path);
    בקובץ המצב: הרשומה שלו ב-produced_documents מסומנת superseded (עם הנתיב החדש, הסיבה ומה החליף אותו),
    ואם הוא היה העותק למשלוח, quality_gate.send_copy מתאפס ונפתח פריט שחוסם משלוח. מחזיר את הנתיב החדש."""
    if not path or not os.path.exists(path):
        return None
    new = paths.stale_path(path, lang)
    paths.check_write_path(new)
    os.replace(path, new)
    if state is not None:
        base = deal_dir or os.path.dirname(os.path.abspath(path))

        def rel(p):
            return os.path.relpath(os.path.abspath(p), os.path.abspath(base)).replace('\\', '/')
        old_rel, new_rel = rel(path), rel(new)
        rec = {'superseded': True, 'superseded_at': _now(), 'superseded_reason': reason or 'gate_failed',
               'superseded_by': superseded_by, 'path': new_rel, 'original_path': old_rel}
        hit = False
        for d in state.setdefault('produced_documents', []):
            if d.get('path') == old_rel:
                d.update(rec)
                hit = True
        if not hit:
            state['produced_documents'].append(dict(rec, kind='superseded', sha256=_sha256(new),
                                                    produced_at=rec['superseded_at']))
        qg = state.setdefault('quality_gate', {})
        sc = qg.get('send_copy')
        if sc is None or (isinstance(sc, dict) and sc.get('path') == old_rel) or sc == old_rel or \
                (isinstance(sc, str) and os.path.basename(sc) == os.path.basename(path)):
            qg['send_copy'] = None
        state.setdefault('open_items', []).append({'item': 'עותק שהוחלף: %s' % os.path.basename(new),
                                                   'kind': 'send_copy_retracted', 'blocks_sending': True})
    return new


def retract_send_copy(send_path, state=None, lang='he', deal_dir=None):
    """עותק "למשלוח" שכבר קיים כשהשער במצב משלוח נכשל: mark_superseded (סיומת " - לא למשלוח" ורשומה בקובץ המצב).
    הקורא שומר את קובץ המצב אחרי ההסרה (save_state)."""
    return mark_superseded(send_path, state, deal_dir=deal_dir, reason='gate_failed', lang=lang)


def save_state(state, state_path):
    """כותב את קובץ המצב אחרי הסרת העותק למשלוח, כתיבה אטומית. מחזיר את הנתיב, או None כשאין מה לכתוב."""
    if state is None or not state_path:
        return None
    state.setdefault('meta', {})['last_updated'] = _now()
    tmp = _write_json_atomic(state_path, state)
    os.replace(tmp, state_path)
    return state_path


def _sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b''):
            h.update(chunk)
    return h.hexdigest()


# ---- הפקה מחדש באותה ריצה (הרצה S1c, 28.10.2026: הפקה חוזרת באותה ריצה השאירה כפולים עם " (2)") ----
# רשומת ההפקה של הסבב, <תיקיית העסקה>/apply-report-round-<N>.json: {round, run_id, delivered, files: {kind: {path
# (יחסי), sha256}}}. apply_redlines.py ו-qa_gate.py כותבים אותה כשמועבר --run-id. הפקה מחדש באותה ריצה (אותו run_id),
# לפני מסירה, מחליפה את הקובץ שנוצר באותה ריצה, ולא יוצרת " (2)". קובץ שנמסר או נשלח לעולם אינו נדרס.
RUN_RECORD = 'apply-report-round-%d.json'


def run_record_path(deal_dir, rnd):
    return os.path.join(deal_dir, RUN_RECORD % int(rnd))


def load_run_record(deal_dir, rnd):
    p = run_record_path(deal_dir, rnd)
    if not os.path.exists(p):
        return None
    try:
        with io.open(p, encoding='utf-8') as fh:
            return json.load(fh)
    except ValueError:
        return None


def _sent_shas(state):
    meta = (state or {}).get('meta') or {}
    return {d.get('sha256') for d in meta.get('sent_documents') or () if d.get('sha256')}


def reusable_path(deal_dir, rnd, run_id, kind, state=None):
    """הנתיב של קובץ מסוג kind שנוצר באותה ריצה, כשמותר להחליף אותו: אותו run_id, הרשומה אינה delivered, הקובץ
    קיים וזהה למה שהופק (sha256; קובץ שעורך הדין שינה אינו נדרס), והוא אינו ב-meta.sent_documents. אחרת None,
    והמפיק נותן שם חדש (paths.unique_path)."""
    if not (deal_dir and rnd and run_id):
        return None
    rec = load_run_record(deal_dir, rnd)
    if not rec or rec.get('run_id') != run_id or rec.get('delivered'):
        return None
    # ריצה שמשהו ממנה נשלח (sha256 ב-meta.sent_documents) נמסרה, ואף קובץ שלה אינו מוחלף
    if any((x or {}).get('sha256') in _sent_shas(state) for x in (rec.get('files') or {}).values()):
        return None
    f = (rec.get('files') or {}).get(kind) or {}
    if not f.get('path') or not f.get('sha256'):
        return None
    p = os.path.join(deal_dir, f['path'])
    if not os.path.exists(p) or _sha256(p) != f['sha256'] or f['sha256'] in _sent_shas(state):
        return None
    return p


def update_run_record(deal_dir, rnd, run_id, files):
    """files: {kind: נתיב}. ריצה אחרת (run_id אחר) מתחילה רשומה חדשה; באותה ריצה הקבצים מתעדכנים. מחזיר את הנתיב."""
    rec = load_run_record(deal_dir, rnd) or {}
    if rec.get('run_id') != run_id:
        rec = {'round': int(rnd), 'run_id': run_id, 'delivered': False, 'files': {}}
    for kind, p in (files or {}).items():
        if p:
            rel = os.path.relpath(os.path.abspath(p), os.path.abspath(deal_dir)).replace('\\', '/')
            rec['files'][kind] = {'path': rel, 'sha256': _sha256(p) if os.path.exists(p) else None}
    rec['updated_at'] = _now()
    path = run_record_path(deal_dir, rnd)
    tmp = _write_json_atomic(path, rec)
    os.replace(tmp, path)
    return path


def refresh_run_record(path):
    """קובץ שנרשם ברשומת ההפקה של הסבב ושונה אחר כך בכלי של אותה ריצה (round_tools.py resolve-threads כותב על קובץ
    העבודה): טביעת האצבע ברשומה מתעדכנת, כדי שהפקה חוזרת באותה ריצה תחליף אותו ולא תיצור " (2)" (S1d-R2,
    28.10.2026). הרשומות נמצאות בתיקייה של הקובץ. מחזיר את הסוגים שעודכנו."""
    deal_dir = os.path.dirname(os.path.abspath(path))
    rel = os.path.basename(path)
    done = []
    for name in sorted(os.listdir(deal_dir)):
        m = re.match(r'^apply-report-round-(\d+)\.json$', name)
        rec = load_run_record(deal_dir, int(m.group(1))) if m else None
        if not rec or rec.get('delivered'):
            continue
        hit = [k for k, f in (rec.get('files') or {}).items() if isinstance(f, dict) and f.get('path') == rel]
        if not hit:
            continue
        for k in hit:
            rec['files'][k]['sha256'] = _sha256(path)
        rec['updated_at'] = _now()
        p = run_record_path(deal_dir, int(m.group(1)))
        os.replace(_write_json_atomic(p, rec), p)
        done += hit
    return done


def record_send_copy(state, send_path, deal_dir=None):
    """רושם את העותק למשלוח בקובץ המצב (גרסה 1.2.0): quality_gate.send_copy = {path (יחסי), sha256,
    recorded_at, status}, ורשומת send ב-produced_documents. status: produced_pending_send ("הופק, ממתין לשליחה");
    הוא עובר ל-sent רק באישור המשתמש (negotiation_state.py sent) או בתחילת הסבב הבא (round_tools.py basis)."""
    base = deal_dir or os.path.dirname(os.path.abspath(send_path))
    rel = os.path.relpath(os.path.abspath(send_path), os.path.abspath(base)).replace('\\', '/')
    rec = {'path': rel, 'sha256': _sha256(send_path), 'recorded_at': _now(), 'status': 'produced_pending_send'}
    state.setdefault('quality_gate', {})['send_copy'] = rec
    docs = [d for d in state.setdefault('produced_documents', []) if not (d.get('kind') == 'send'
                                                                          and d.get('path') == rel)]
    docs.append({'kind': 'send', 'path': rel, 'sha256': rec['sha256'], 'produced_at': rec['recorded_at']})
    state['produced_documents'] = docs
    return rec
