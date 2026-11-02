# -*- coding: utf-8 -*-
"""obligations/store.py: שמירת המרשם בתיקיית הלקוח.

  <data>/obligations/<agreement_id>/obligations.json   מקור האמת להסכם אחד (הטיוטה המאומתת + המועדים המחושבים)
  <data>/obligations/<agreement_id>/history/           כל גרסה קודמת, לפני כל כתיבה. אין דריסה
  <data>/obligations/register.json                     מרשם הישות, נגזר תמיד מקובצי ההסכמים (נבנה מחדש)

<data> הוא תיקיית הנתונים של הישות: התיקייה שבה יושב הפרופיל שלה (profile_path ב-ישויות.json);
בישות ברירת המחדל, השורש של Areo-נתונים.
מזהה חובה ייחודי בכל המרשם של הישות (foreign_ids), ולכן עדכון מעמד לפי מזהה אינו נוחת על הסכם אחר.
המועדים מחושבים מחדש בכל בנייה, נכון ליום הבנייה, כי חידוש אוטומטי מזיז את תום התקופה.
"""
import datetime as dt
import json
import os
import shutil

from common.paths import long_path

from . import dates as D
from . import model as M

REGISTER_SCHEMA = 'areo-obligations-register/1'
COMPUTED_KEYS = ('computed',)


def obl_dir(data):
    return os.path.join(data, 'obligations')


def agreement_path(data, aid):
    return os.path.join(obl_dir(data), aid, 'obligations.json')


def register_path(data):
    return os.path.join(obl_dir(data), 'register.json')


def _read(p):
    with open(long_path(p), encoding='utf-8') as fh:
        return json.load(fh)


def _write(p, data):
    """כתיבה אטומית. הנתיבים עוברים long_path: תיקיית לקוח ב-OneDrive עם שמות בעברית עוברת בקלות 260 תווים."""
    lp = long_path(p)
    os.makedirs(os.path.dirname(lp), exist_ok=True)
    tmp = lp + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, lp)


def _backup(p):
    """מעתיק את הגרסה הקיימת להיסטוריה לפני כתיבה. מחזיר את נתיב הגיבוי או None."""
    if not os.path.isfile(long_path(p)):
        return None
    h = os.path.join(os.path.dirname(long_path(p)), 'history')
    os.makedirs(h, exist_ok=True)
    stamp = dt.datetime.now().strftime('%Y%m%d-%H%M%S')
    out = os.path.join(h, 'obligations-%s.json' % stamp)
    k = 1
    while os.path.exists(out):
        out = os.path.join(h, 'obligations-%s-%d.json' % (stamp, k))
        k += 1
    shutil.copy2(long_path(p), out)
    return out


def agreement_files(data):
    root = obl_dir(data)
    if not os.path.isdir(long_path(root)):
        return []
    out = []
    for name in sorted(os.listdir(long_path(root))):
        p = os.path.join(root, name, 'obligations.json')
        if os.path.isfile(long_path(p)):
            out.append(p)
    return out


def with_computed(rec, as_of, lang):
    """מחשב מחדש את המועדים של רשומת הסכם, נכון ליום as_of."""
    res, term = D.compute_all(rec['agreement'], rec['obligations'], as_of, lang)
    for o in rec['obligations']:
        o['computed'] = res[o['id']]
    rec['term'] = term
    rec.setdefault('meta', {})['computed_as_of'] = D.iso(D.parse(as_of) or dt.date.today())
    return rec


def add(data, draft, as_of=None, lang='he', today=None):
    """רושם או מעדכן הסכם. מחזיר dict עם הנתיבים, החובות שהוסרו ומעמדים שנשמרו."""
    today = D.iso(D.parse(today) or dt.date.today())
    aid = draft['agreement']['agreement_id']
    p = agreement_path(data, aid)
    old = _read(p) if os.path.isfile(long_path(p)) else None
    rec = {'schema': M.SCHEMA, 'agreement': draft['agreement'],
           'obligations': [dict((k, v) for k, v in o.items() if k not in COMPUTED_KEYS)
                           for o in draft['obligations']],
           'meta': {'registered_at': (old or {}).get('meta', {}).get('registered_at', today),
                    'updated_at': today, 'lang': M.lang_key(lang)}}
    kept, removed = [], []
    if old:
        prev = {o['id']: o for o in old.get('obligations', [])}
        for o in rec['obligations']:
            po = prev.get(o['id'])
            if po and o.get('status', 'open') == 'open' and not o.get('status_log') and po.get('status_log'):
                o['status'], o['status_log'] = po.get('status', 'open'), po['status_log']
                kept.append(o['id'])
        new_ids = {o['id'] for o in rec['obligations']}
        removed = [i for i in prev if i not in new_ids]
    with_computed(rec, as_of, lang)
    backup = _backup(p)
    _write(p, rec)
    reg = rebuild(data, as_of, lang)
    return {'path': p, 'backup': backup, 'kept_status': kept, 'removed': removed, 'record': rec,
            'register': register_path(data), 'register_data': reg}


def foreign_ids(data, aid, ids):
    """מזהי חובה מתוך ids שכבר רשומים בהסכם אחר במרשם (לא aid). מחזיר {מזהה: agreement_id של ההסכם האחר}."""
    want, out = set(ids), {}
    for p in agreement_files(data):
        rec = _read(p)
        other = (rec.get('agreement') or {}).get('agreement_id')
        if other == aid:
            continue
        for o in rec.get('obligations', []):
            if o.get('id') in want and o['id'] not in out:
                out[o['id']] = other
    return out


class AmbiguousId(Exception):
    """אותו מזהה חובה רשום ביותר מהסכם אחד (מרשם ישן): עדכון מעמד דורש --agreement."""


def set_status(data, oid, status, by, date, note='', as_of=None, lang='he', agreement=None):
    """עדכון מעמד, רק על פי אמירה מפורשת של המשתמש: מי ומתי נרשמים תמיד.
    agreement מצמצם את החיפוש להסכם אחד. בלעדיו, מזהה שנמצא ביותר מהסכם אחד אינו מעודכן (AmbiguousId)."""
    if status not in M.STATUS:
        raise ValueError(M.msg('STATUS', lang, oid, status))
    if not by or not D.parse(date):
        raise ValueError(M.msg('STATUS', lang, oid, status))
    hits = []
    for p in agreement_files(data):
        rec = _read(p)
        if agreement and (rec.get('agreement') or {}).get('agreement_id') != agreement:
            continue
        for o in rec['obligations']:
            if o.get('id') == oid:
                hits.append((p, rec, o))
                break
    if not hits:
        raise KeyError(oid)
    if len(hits) > 1:
        raise AmbiguousId(', '.join(h[1]['agreement']['agreement_id'] for h in hits))
    p, rec, o = hits[0]
    o['status'] = status
    o.setdefault('status_log', []).append(
        {'status': status, 'by': by, 'date': D.iso(D.parse(date)), 'note': note or ''})
    rec['meta']['updated_at'] = D.iso(dt.date.today())
    with_computed(rec, as_of, lang)
    _backup(p)
    _write(p, rec)
    rebuild(data, as_of, lang)
    return p, o


def load_records(data, as_of=None, lang='he'):
    return [with_computed(_read(p), as_of, lang) for p in agreement_files(data)]


def rebuild(data, as_of=None, lang='he'):
    """בונה את register.json מכל קובצי ההסכמים. אינו נוגע בקובצי ההסכמים."""
    recs = load_records(data, as_of, lang)
    reg = {'schema': REGISTER_SCHEMA, 'updated_at': D.iso(dt.date.today()),
           'as_of': D.iso(D.parse(as_of) or dt.date.today()), 'agreements': [], 'obligations': []}
    for rec in recs:
        a = rec['agreement']
        reg['agreements'].append({
            'agreement_id': a['agreement_id'], 'title': a.get('title', ''), 'counterparty': a.get('counterparty', ''),
            'family': a.get('family', ''), 'our_side': a.get('our_side', ''), 'language': a.get('language', ''),
            'documents': a.get('documents', []), 'dates': a.get('dates', {}), 'notices': a.get('notices', {}),
            'term': rec['term'], 'obligation_count': len(rec['obligations']),
            'updated_at': rec.get('meta', {}).get('updated_at')})
        for o in rec['obligations']:
            reg['obligations'].append(dict(o, agreement_id=a['agreement_id']))
    _write(register_path(data), reg)
    return reg


def occurrences(data, frm, to, lang='he'):
    """כל המועדים בטווח [frm, to], כולל מופעים של חובות חוזרות. מחזיר רשימת (תאריך, רשומת הסכם, חובה, חישוב)."""
    frm, to = D.parse(frm), D.parse(to)
    out = []
    for rec in load_records(data, frm, lang):
        ctx = D.Ctx(rec['agreement'], frm, lang, rec['obligations'])
        for o in rec['obligations']:
            tm = o.get('timing') or {}
            if tm.get('kind') == 'recurring':
                occ, calc, _ = ctx.occurrences(tm, frm, to)
                for d in occ:
                    out.append((d, rec, o, calc))
            else:
                d = D.parse(o['computed'].get('due_date'))
                if d and frm <= d <= to and tm.get('kind') not in ('ongoing',):
                    out.append((d, rec, o, o['computed'].get('calc', '')))
    out.sort(key=lambda x: (x[0], x[1]['agreement']['agreement_id'], x[2]['id']))
    return out


def overdue(data, as_of, lang='he'):
    """חובות פתוחות שמועדן חלף."""
    as_of = D.parse(as_of)
    out = []
    for rec in load_records(data, as_of, lang):
        for o in rec['obligations']:
            d = D.parse(o['computed'].get('due_date'))
            if d and d < as_of and o.get('status', 'open') == 'open' and (o.get('timing') or {}).get('kind') not in (
                    'recurring', 'ongoing', 'term_end'):
                out.append((d, rec, o))
    out.sort(key=lambda x: x[0])
    return out
