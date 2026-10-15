# -*- coding: utf-8 -*-
"""לולאת "לתיקון לפני שליחת התגובה": מה שמעריך הסיכונים מוצא בתגובה שלנו חוזר לנושא ונותן, ושער המשלוח מסרב
עד שכל שורה נסגרה (מימוש ייחוס, הערות הנושא ונותן 4.9, שינוי 80).

בסבב 3, ב-C1, העותק למשלוח הופק ב-16:57, ומעריך הסיכונים מצא ב-17:20 שלוש שורות "לתיקון" באותו עותק (בסיס
התקרה, מונח הריבית, הסייג לייעוץ רשלני). העותק נשאר בתיקייה בשם הסופי.

החוזה בין הרכיבים (אותם שמות שדות בהערות מעריך הסיכונים 3.6):
- **המרשם:** `<תיקיית העסקה>/risk-register.json` (אותה תיקייה של negotiation_state.json).
- **השורות:** `pre_send_fixes[]`. כל שורה: `id` (למשל "PSF-01"), `kind` (missing / incomplete / created_by_response /
  polish), `gap`, `where`, `risk_ids`, `clause_ref` ו-`status`.
  - `clause_ref`: מזהה הסעיף בקובץ המצב (`clauses[].clause_id`, כמו "D22" או "E-013"), ולא מזהה כלל. שדה ישן
    בשם `state_clause_id` נקרא כ-clause_ref. פער של סעיף חסר מצביע על הסעיף שבו הוא היה צריך לשבת. אותו כלל חל
    על `deliberate_concessions[].clause_ref`: מזהה סעיף בהסכם (מפתח ב-`numbering_map`), לעולם לא מזהה כלל כמו
    "R11" או "mandatory_list:...".
  - `status`: `open` (כך מעריך הסיכונים כותב כל שורה), `resolved` או `conceded`. רק הנושא ונותן משנה אותו.
  - `resolution`: `{"how": "reopened", "decision_id", "at"}` או `{"how": "deliberate_concession", "at"}`.
- **סגירה בפתיחה מחדש של ההכרעה:** הכרעה ששינתה נוסח בקובץ ההכרעות של הסבב (או סבב "1א") עם
  `reopened_from_fix: <id>` (או רשימת מזהים, כששתי שורות חלות על אותו סעיף), שנרשמת ב-`clauses[]` של קובץ המצב,
  ואז `status: resolved` עם `resolution.decision_id` של אותה הכרעה (גרסה 1.2.0: הסימון לבדו אינו מספיק).
- **סגירה בוויתור מכוון:** רשומה ב-`deliberate_concessions[]` עם `clause_ref` זהה, `from_pre_send_fix: <id>`
  ו-`user_decision` עם `answer_kind: explicit` (הכרעה מפורשת של המשתמש, "נדרשת הכרעתך" מצב 2 או 5; תשובה כללית,
  delegated, אינה סוגרת שורה), ואז `status: conceded`. מעריך הסיכונים מציג אותה
  כסיכון שהתקבל.
- **השער:** במצב משלוח, כל שורה שאינה סגורה (או שסגירתה אינה נתמכת בקובץ המצב) היא כשל: RISK_FIX_OPEN,
  RISK_FIX_RESOLUTION_UNVERIFIED או RISK_FIX_CONCESSION_MISSING. שורה מסוג polish מדווחת כאזהרה ואינה חוסמת.
  במצב עבודה כולן אזהרות.
- **אין עותק למשלוח בזמן שיש שורה פתוחה:** עותק שכבר הופק מקבל את הסיומת " - לא למשלוח" (mark_superseded,
  דרך retract_send_copy), ונרשם בקובץ המצב שאין עותק למשלוח. עותק שעבר את השער נרשם בקובץ המצב (record_send_copy).
- **כתיבת הסגירה:** close_fixes(deal_dir, state_path, closures, decisions) היא הפונקציה האחת שכותבת את הסטטוסים,
  במרשם וב-`pre_send_fixes` של קובץ המצב, הכול או כלום (גרסה 1.2.0).

    from orchestrator import pre_send
    reg = pre_send.load_register(deal_dir)
    pre_send.check(reg, state)            # [{'code', 'message', 'where'}]
"""
import copy
import datetime as _dt
import hashlib
import io
import json
import os

from common import paths

REGISTER_NAME = 'risk-register.json'
OPEN, RESOLVED, CONCEDED = 'open', 'resolved', 'conceded'
CLOSED = (RESOLVED, CONCEDED)


def _now():
    return _dt.datetime.now().astimezone().replace(microsecond=0).isoformat()


def register_path(deal_dir):
    return os.path.join(deal_dir, REGISTER_NAME)


def load_register(deal_dir):
    p = register_path(deal_dir)
    if not os.path.exists(p):
        return None
    with io.open(p, encoding='utf-8') as fh:
        return json.load(fh)


def save_register(deal_dir, register):
    p = register_path(deal_dir)
    paths.check_write_path(p)
    with io.open(p, 'w', encoding='utf-8') as fh:
        json.dump(register, fh, ensure_ascii=False, indent=1)
    return p


def fixes(register):
    out = []
    for i, fx in enumerate((register or {}).get('pre_send_fixes') or []):
        fx.setdefault('id', 'PSF-%02d' % (i + 1))
        fx.setdefault('status', OPEN)
        out.append(fx)
    return out


def clause_ref(fx):
    return fx.get('clause_ref') or fx.get('state_clause_id') or ''


CHANGE_OPS = ('replace', 'replace_span', 'insert_paragraph', 'delete_paragraph')   # הכרעה ששינתה נוסח


def fix_ids_of(value):
    """reopened_from_fix: מזהה אחד או רשימה (גרסה 1.2.0: שתי שורות על אותו סעיף בלי לפצל את ההכרעה)."""
    if not value:
        return []
    return [value] if isinstance(value, str) else [x for x in value if x]


def changed_decisions(decisions, fix_id):
    """מזהי ההכרעות בקובץ ההכרעות (decisions_round_N.json) ששינו נוסח ונפתחו בגלל השורה הזו."""
    return [d.get('id') for d in (decisions or {}).get('decisions', [])
            if d.get('op') in CHANGE_OPS and fix_id in fix_ids_of(d.get('reopened_from_fix'))]


def _resolution_ok(fx, state, decisions=None):
    st = state or {}
    if fx.get('status') == RESOLVED:
        # גרסה 1.2.0: לא מספיק הסימון. resolution.decision_id הוא הכרעה ששינתה נוסח בקובץ ההכרעות, עם
        # reopened_from_fix של השורה, והיא רשומה ב-clauses[] של קובץ המצב.
        did = (fx.get('resolution') or {}).get('decision_id')
        if not did or did not in changed_decisions(decisions, fx['id']):
            return False
        return any(c.get('clause_id') == did and fx['id'] in fix_ids_of(c.get('reopened_from_fix'))
                   for c in st.get('clauses', []))
    if fx.get('status') == CONCEDED:
        # שינוי 80: ויתור על שורה "לתיקון" רק בהכרעה מפורשת של המשתמש. תשובה כללית (delegated) אינה סוגרת שורה.
        return any(w.get('from_pre_send_fix') == fx['id'] and w.get('clause_ref') == clause_ref(fx)
                   and (w.get('user_decision') or {}).get('answer_kind') == 'explicit'
                   for w in st.get('deliberate_concessions', []))
    return False


def open_fixes(register, state=None, decisions=None):
    """שורות שאינן סגורות, או שהסגירה שלהן אינה נתמכת בקובץ המצב ובקובץ ההכרעות. שורת polish אינה נכללת."""
    return [fx for fx in fixes(register) if fx.get('kind') != 'polish'
            and (fx['status'] not in CLOSED or not _resolution_ok(fx, state, decisions))]


def check(register, state=None, decisions=None):
    """decisions: קובץ ההכרעות של הסבב (dict). בלעדיו שורה resolved אינה מאומתת."""
    F = []
    for fx in fixes(register):
        where = '%s (%s)' % (fx['id'], clause_ref(fx) or '?')
        if not clause_ref(fx):
            F.append({'code': 'RISK_FIX_NO_CLAUSE_REF', 'message': 'שורת "לתיקון" בלי clause_ref', 'where': where})
        if fx.get('kind') == 'polish':
            continue
        if fx['status'] not in CLOSED:
            F.append({'code': 'RISK_FIX_OPEN', 'message': 'לתיקון לפני שליחת התגובה: %s' % (fx.get('gap') or ''),
                      'where': where})
        elif fx['status'] == RESOLVED and not _resolution_ok(fx, state, decisions):
            F.append({'code': 'RISK_FIX_RESOLUTION_UNVERIFIED',
                      'message': 'השורה סומנה resolved, ואין הכרעה ששינתה נוסח בקובץ ההכרעות (resolution.decision_id '
                                 'עם reopened_from_fix) שרשומה בקובץ המצב', 'where': where})
        elif fx['status'] == CONCEDED and not _resolution_ok(fx, state, decisions):
            F.append({'code': 'RISK_FIX_CONCESSION_MISSING',
                      'message': 'השורה סומנה conceded, ואין ויתור מכוון עם אותו clause_ref והכרעה מפורשת של המשתמש',
                      'where': where})
    return F


def polish_warnings(register):
    return [{'code': 'RISK_FIX_POLISH_OPEN', 'message': fx.get('gap') or '', 'where': fx['id']}
            for fx in fixes(register) if fx.get('kind') == 'polish' and fx['status'] not in CLOSED]


def to_reopen(register):
    """ההכרעות שצריך לפתוח מחדש (סבב "1א"): לכל שורה פתוחה, clause_ref והפער."""
    return [{'fix_id': fx['id'], 'clause_ref': clause_ref(fx), 'gap': fx.get('gap'), 'risk_ids': fx.get('risk_ids', [])}
            for fx in fixes(register) if fx['status'] not in CLOSED and fx.get('kind') != 'polish']


def resolve_fix(register, fix_id, decision_id, decisions=None):
    """סגירה בפתיחה מחדש. כשנמסר קובץ ההכרעות, decision_id חייב להיות הכרעה ששינתה נוסח עם reopened_from_fix
    של השורה (ValueError אחרת)."""
    if decisions is not None and decision_id not in changed_decisions(decisions, fix_id):
        raise ValueError('ההכרעה %s אינה הכרעה ששינתה נוסח עם reopened_from_fix: %s' % (decision_id, fix_id))
    for fx in fixes(register):
        if fx['id'] == fix_id:
            fx['status'] = RESOLVED
            fx['resolution'] = {'how': 'reopened', 'decision_id': decision_id, 'at': _now()}
            return fx
    raise KeyError(fix_id)


def concede_fix(register, state, fix_id, reason, user_decision):
    """ויתור מכוון על שורה: רק בהכרעה מפורשת של המשתמש (answer_kind: explicit, שינוי 80). תשובה כללית
    (delegated) אינה סוגרת שורה "לתיקון". ההכרעה נרשמת בקובץ המצב."""
    if (user_decision or {}).get('answer_kind') != 'explicit':
        raise ValueError('ויתור על שורת "לתיקון" דורש הכרעה מפורשת של המשתמש (explicit); תשובה כללית אינה מספיקה')
    for fx in fixes(register):
        if fx['id'] == fix_id:
            fx['status'] = CONCEDED
            fx['resolution'] = {'how': 'deliberate_concession', 'at': _now()}
            state.setdefault('deliberate_concessions', []).append({
                'topic': fx.get('gap'), 'clause_ref': clause_ref(fx), 'rule_ids': [], 'reason': reason,
                'user_decision': dict(user_decision, recorded_at=user_decision.get('recorded_at') or _now()),
                'from_pre_send_fix': fix_id, 'risk_ids': fx.get('risk_ids', []), 'report_as': 'accepted_risk',
                'recorded_at': _now()})
            return fx
    raise KeyError(fix_id)


def _state_rows(register):
    """השורות כפי שהן נרשמות ב-pre_send_fixes של קובץ המצב: id, clause_ref, status, resolution."""
    return [{'id': fx['id'], 'clause_ref': clause_ref(fx), 'status': fx['status'],
             'resolution': copy.deepcopy(fx.get('resolution'))} for fx in fixes(register)]


def _write_json_atomic(path, data):
    paths.check_write_path(path)
    tmp = path + '.tmp'
    with io.open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    return tmp


def close_fixes(deal_dir, state_path, closures, decisions=None):
    """הפונקציה האחת שכותבת סגירה של שורות "לתיקון", במרשם ובקובץ המצב יחד (גרסה 1.2.0).

    closures: [{'fix_id', 'how': 'resolved', 'decision_id'} | {'fix_id', 'how': 'conceded', 'reason',
    'user_decision'}]. decisions: קובץ ההכרעות של הסבב (חובה לסגירה resolved).
    הכול או כלום: הסגירות מוחלות על עותקים, כל שורה נבדקת (_resolution_ok); כשאחת נכשלת, או כשהכתיבה נכשלת,
    שני הקבצים נשארים כמו שהיו (גלגול לאחור). מחזיר (register, state) המעודכנים."""
    reg_path = register_path(deal_dir)
    register = load_register(deal_dir)
    if register is None:
        raise FileNotFoundError(reg_path)
    with io.open(state_path, encoding='utf-8') as fh:
        state = json.load(fh)
    reg2, st2 = copy.deepcopy(register), copy.deepcopy(state)
    for c in closures:
        if c.get('how') == RESOLVED:
            resolve_fix(reg2, c['fix_id'], c['decision_id'], decisions if decisions is not None else {})
        elif c.get('how') == CONCEDED:
            concede_fix(reg2, st2, c['fix_id'], c.get('reason') or '', c.get('user_decision'))
        else:
            raise ValueError('how הוא resolved או conceded: %r' % c.get('how'))
    st2['pre_send_fixes'] = _state_rows(reg2)
    bad = [fx['id'] for fx in fixes(reg2) if fx['id'] in {c['fix_id'] for c in closures}
           and not _resolution_ok(fx, st2, decisions)]
    if bad:
        raise ValueError('הסגירה אינה נתמכת בקובץ המצב או בקובץ ההכרעות: %s' % ', '.join(bad))
    with io.open(reg_path, 'rb') as fh:
        reg_backup = fh.read()
    tmp_reg = tmp_st = None
    try:
        tmp_reg = _write_json_atomic(reg_path, reg2)
        tmp_st = _write_json_atomic(state_path, st2)
        os.replace(tmp_reg, reg_path)
        tmp_reg = None
        os.replace(tmp_st, state_path)
        tmp_st = None
    except Exception:
        with io.open(reg_path, 'wb') as fh:   # גלגול לאחור: המרשם חוזר למצבו הקודם
            fh.write(reg_backup)
        raise
    finally:
        for t in (tmp_reg, tmp_st):
            if t and os.path.exists(t):
                os.remove(t)
    return reg2, st2


def mark_superseded(path, state=None, deal_dir=None, reason='', superseded_by=None, lang='he'):
    """סימון עותק שהוחלף (גרסה 1.2.0): הקובץ אינו נמחק, ומקבל את הסיומת " - לא למשלוח" (paths.stale_path);
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
        rec = {'superseded': True, 'superseded_at': _now(), 'superseded_reason': reason or 'pre_send_fix',
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
                                                   'kind': 'pre_send_fix', 'blocks_sending': True})
    return new


def retract_send_copy(send_path, state=None, lang='he', deal_dir=None):
    """עותק "למשלוח" שכבר קיים בזמן שיש שורה פתוחה: mark_superseded (סיומת " - לא למשלוח" ורשומה בקובץ המצב)."""
    return mark_superseded(send_path, state, deal_dir=deal_dir, reason='pre_send_fix_open', lang=lang)


def _sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b''):
            h.update(chunk)
    return h.hexdigest()


def record_send_copy(state, send_path, deal_dir=None):
    """רושם את העותק למשלוח בקובץ המצב (גרסה 1.2.0): quality_gate.send_copy = {path (יחסי), sha256,
    recorded_at}, ורשומת send ב-produced_documents."""
    base = deal_dir or os.path.dirname(os.path.abspath(send_path))
    rel = os.path.relpath(os.path.abspath(send_path), os.path.abspath(base)).replace('\\', '/')
    rec = {'path': rel, 'sha256': _sha256(send_path), 'recorded_at': _now()}
    state.setdefault('quality_gate', {})['send_copy'] = rec
    docs = [d for d in state.setdefault('produced_documents', []) if not (d.get('kind') == 'send'
                                                                          and d.get('path') == rel)]
    docs.append({'kind': 'send', 'path': rel, 'sha256': rec['sha256'], 'produced_at': rec['recorded_at']})
    state['produced_documents'] = docs
    return rec
