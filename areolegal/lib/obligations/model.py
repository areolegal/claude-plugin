# -*- coding: utf-8 -*-
"""obligations/model.py: טקסונומיית החובות, בדיקת הטיוטה שהמודל כתב, ותוויות בעברית ובאנגלית.

הטיוטה (draft) היא קובץ JSON שהמודל כותב לתיקייה זמנית אחרי קריאת ההסכם החתום:
  {"schema": "areo-obligations/1", "agreement": {...}, "obligations": [{...}, ...]}
הסכמה המלאה ב-o4-register-schema.md (תוכן מהשרת). כאן רק מה שהקוד אוכף.

check_draft מחזיר (errors, warnings). שגיאה עוצרת את הרישום (קוד יציאה 3); אזהרה נרשמת בגיליון "להשלמה".
"""
import re
import unicodedata

from . import dates as D

SCHEMA = 'areo-obligations/1'
OBLIGORS = ('us', 'them', 'both')
STATUS = ('open', 'done', 'waived', 'not_applicable')
DOC_KINDS = ('main', 'annex', 'amendment', 'side_letter', 'consent')
TYPES = ('payment', 'milestone', 'deliverable', 'insurance', 'guarantee', 'reporting', 'notice',
         'renewal_notice', 'term_end', 'option', 'audit', 'consent_approval', 'data_return_deletion',
         'confidentiality', 'compliance', 'price_adjustment', 'other')
EXEC_BASIS = ('signed_copy', 'user_confirmed', 'negotiation_state')

LABELS = {
    'he': {
        'type': {'payment': 'תשלום', 'milestone': 'אבן דרך', 'deliverable': 'מסירה', 'insurance': 'ביטוח',
                 'guarantee': 'ערבות', 'reporting': 'דיווח', 'notice': 'הודעה', 'renewal_notice': 'הודעת אי חידוש',
                 'term_end': 'תום תקופה', 'option': 'אופציה', 'audit': 'ביקורת', 'consent_approval': 'הסכמה או אישור',
                 'data_return_deletion': 'החזרה ומחיקה של מידע', 'confidentiality': 'סודיות',
                 'compliance': 'ציות', 'price_adjustment': 'עדכון מחיר', 'other': 'אחר'},
        'obligor': {'us': 'אנחנו', 'them': 'הצד השני', 'both': 'שני הצדדים'},
        'status': {'open': 'פתוחה', 'done': 'בוצעה', 'waived': 'ויתור', 'not_applicable': 'לא רלוונטית'},
        'date_status': {'computed': 'מחושב', 'to_complete': '[להשלים]', 'needs_verification': 'טעון אימות',
                        'needs_legal_review': 'טעון בדיקה משפטית', 'event_driven': 'תלוי באירוע',
                        'ongoing': 'מתמשכת'},
    },
    'en': {
        'type': {'payment': 'Payment', 'milestone': 'Milestone', 'deliverable': 'Deliverable', 'insurance': 'Insurance',
                 'guarantee': 'Guarantee', 'reporting': 'Reporting', 'notice': 'Notice',
                 'renewal_notice': 'Non-renewal notice', 'term_end': 'End of term', 'option': 'Option',
                 'audit': 'Audit', 'consent_approval': 'Consent or approval',
                 'data_return_deletion': 'Data return and deletion', 'confidentiality': 'Confidentiality',
                 'compliance': 'Compliance', 'price_adjustment': 'Price adjustment', 'other': 'Other'},
        'obligor': {'us': 'Us', 'them': 'Counterparty', 'both': 'Both parties'},
        'status': {'open': 'Open', 'done': 'Done', 'waived': 'Waived', 'not_applicable': 'Not applicable'},
        'date_status': {'computed': 'Computed', 'to_complete': '[to complete]', 'needs_verification': 'Needs verification',
                        'needs_legal_review': 'Needs legal review', 'event_driven': 'Event driven',
                        'ongoing': 'Continuing'},
    },
}

MSG = {
    'SCHEMA': ('הקובץ אינו טיוטת מרשם תקינה: %s', 'Not a valid register draft: %s'),
    'NOT_EXECUTED': ('ההסכם לא סומן כחתום (agreement.executed). המרשם רושם רק הסכם שנחתם; '
                     'בטיוטה או בהסכם במשא ומתן אין רישום', 'The agreement is not marked as executed '
                     '(agreement.executed). Only a signed agreement is registered'),
    'EXEC_BASIS': ('חסר בסיס לקביעה שההסכם חתום (agreement.execution_basis: %s)',
                   'Missing basis for treating the agreement as signed (agreement.execution_basis: %s)'),
    'AGREEMENT_ID': ('agreement_id חסר או מכיל תווים שאסורים בשם תיקייה: %r',
                     'agreement_id missing or has characters not allowed in a folder name: %r'),
    'OBL_ID': ('מזהה חובה לא תקין או כפול: %r (נדרש obl_ וייחודי)', 'Invalid or duplicate obligation id: %r (obl_, unique)'),
    'OBL_ID_EXISTS': ('%s: המזהה כבר רשום במרשם, בהסכם %s. מזהה חובה ייחודי בכל המרשם: יש לבחור קיצור הסכם אחר',
                      '%s: the id is already registered, in agreement %s. Obligation ids are unique across the '
                      'register: choose another agreement abbreviation'),
    'OBLIGOR': ('%s: obligor חייב להיות us, them או both', '%s: obligor must be us, them or both'),
    'TYPE': ('%s: סוג לא מוכר %r', '%s: unknown type %r'),
    'SOURCE': ('%s: חסר עוגן מקור (source.clause ו-source.quote)', '%s: missing source anchor (source.clause and source.quote)'),
    'QUOTE_NOT_FOUND': ('%s: הציטוט אינו מופיע מילה במילה בהסכם שחולץ: "%s"',
                        '%s: the quote is not verbatim in the extracted agreement: "%s"'),
    'TIMING': ('%s: timing לא תקין: %s', '%s: invalid timing: %s'),
    'HAND_DATE': ('%s: תאריך יעד נכתב ביד (%s). המועד מחושב רק מ-timing', '%s: due date written by hand (%s). '
                  'Dates are computed from timing only'),
    'ANCHOR': ('%s: עוגן לא מוכר %r', '%s: unknown anchor %r'),
    'STATUS': ('%s: מעמד %r בלי רישום מי ומתי (status_log עם by ו-date)',
               '%s: status %r without a record of who and when (status_log with by and date)'),
    'DATE': ('%s: תאריך לא תקין %r (נדרש YYYY-MM-DD)', '%s: invalid date %r (YYYY-MM-DD)'),
    # אזהרות
    'W_DEPARTMENT': ('%s: אין מחלקה אחראית', '%s: no responsible department'),
    'W_DELIVERY': ('%s: הודעה בלי סעיף הודעות, אופן מסירה או כתובת (agreement.notices: %s)',
                   '%s: notice without a notices clause, delivery method or address (agreement.notices: %s)'),
    'W_TRACKED': ('במסמך %s יש שינויים במעקב או הערות. ודאו שזה הנוסח החתום', 'Document %s has tracked changes or '
                  'comments. Make sure this is the signed version'),
    'W_NO_CORPUS': ('הציטוטים לא אומתו מול ההסכם (לא סופק --corpus)', 'Quotes were not verified (no --corpus)'),
}

ANCHORS = ('signing_date', 'effective_date', 'end_date', 'term_end', 'renewal_date')
_BAD_ID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def lang_key(lang):
    return 'en' if str(lang or '').lower().startswith('en') else 'he'


def msg(code, lang, *args):
    t = MSG[code][1 if lang_key(lang) == 'en' else 0]
    return t % args if args else t


def label(kind, value, lang):
    return LABELS[lang_key(lang)][kind].get(value, value or '')


def norm(s):
    """נרמול להשוואת ציטוט: NFKC, מרכאות ומקפים אחידים, בלי תווי כיווניות, רווח אחד."""
    s = unicodedata.normalize('NFKC', s or '')
    s = re.sub('[‎‏‪-‮⁦-⁩­]', '', s)
    s = re.sub('[‘’׳`]', "'", s)
    s = re.sub('[“”״„]', '"', s)
    s = re.sub('[‐-―−]', '-', s)
    return re.sub(r'\s+', ' ', s).strip().lower()


def corpus_text(corpus):
    """נוסח ההסכם מקובץ החילוץ (extract_corpus.py): documents[].paragraphs[], בנוסח 'קבל הכול' (text) וגם
    'דחה הכול' (text_reject_all). הערות וטקסט מוסתר הם מידע ולא נוסח (כלל 1.3): הערות אינן נאספות, וקטע
    מוסתר (hidden) מוסר מהפסקה, כך שציטוט שנמצא רק בהם אינו מאומת."""
    out = []
    docs = corpus.get('documents') if isinstance(corpus, dict) else None
    for d in docs if isinstance(docs, list) else []:
        for p in (d.get('paragraphs') or []) if isinstance(d, dict) else []:
            if not isinstance(p, dict):
                continue
            hidden = [norm(h.get('text')) for h in p.get('hidden') or [] if isinstance(h, dict)]
            for k in ('text', 'text_reject_all'):
                v = p.get(k)
                if not isinstance(v, str) or not v:
                    continue
                v = norm(v)
                for h in hidden:
                    if h:
                        v = v.replace(h, ' ', 1)
                out.append(v)
    return norm(' \n '.join(out))


PLACEHOLDERS = ('[להשלים]', '[to complete]')


def delivery_gaps(notices):
    """מה חסר למסירת הודעה (agreement.notices): clause, method, to_them. ערך ריק או [להשלים] נחשב חסר."""
    n = notices if isinstance(notices, dict) else {}
    return [k for k in ('clause', 'method', 'to_them')
            if not str(n.get(k) or '').strip() or str(n.get(k)).strip().lower() in PLACEHOLDERS]


def tracked_docs(corpus):
    return [d.get('path') for d in (corpus or {}).get('documents', [])
            if d.get('has_tracked_changes') or d.get('has_comments')]


def _date_ok(v):
    return v in (None, '') or D.parse(v) is not None


def _check_off(off):
    return isinstance(off, dict) and off.get('unit') in D.UNITS and str(off.get('n', '')).lstrip('-').isdigit() \
        and off.get('direction', 'after') in ('after', 'before')


def _check_timing(tm, ids, custom):
    """מחזיר (תיאור שגיאה או None, עוגן לא מוכר או None)."""
    if not isinstance(tm, dict) or tm.get('kind') not in D.KINDS:
        return 'kind', None
    k = tm['kind']
    if tm.get('qualifier') and tm['qualifier'] not in D.QUALIFIERS:
        return 'qualifier', None

    def anchor_ok(a):
        if a is None:
            return True
        if D.parse(a):
            return True
        if a in ANCHORS:
            return True
        if isinstance(a, str) and a.startswith('custom:'):
            return a[7:] in custom
        if isinstance(a, str) and a.startswith('obl:'):
            return a[4:] in ids
        return False
    if k == 'fixed' and not D.parse(tm.get('date')):
        return 'fixed.date', None
    if k == 'relative':
        if not tm.get('anchor'):
            return 'relative.anchor', None
        if not _check_off(tm.get('offset')):
            return 'relative.offset', None
    if k == 'recurring':
        ev = tm.get('every')
        if not isinstance(ev, dict) or ev.get('unit') not in D.UNITS or not str(ev.get('n', '')).isdigit() \
                or int(ev['n']) < 1 or not tm.get('start'):
            return 'recurring.every/start', None
        if tm.get('start_offset') and not _check_off(tm['start_offset']):
            return 'recurring.start_offset', None
    if k == 'event' and not tm.get('event'):
        return 'event.event', None
    if k == 'event' and tm.get('offset') and not _check_off(tm['offset']):
        return 'event.offset', None
    if k == 'survival' and tm.get('period') not in (None, 'indefinite') and not (
            isinstance(tm['period'], dict) and tm['period'].get('unit') in D.UNITS):
        return 'survival.period', None
    for key in ('anchor', 'start', 'until'):
        if key in tm and not anchor_ok(tm[key]):
            return None, tm[key]
    return None, None


def check_draft(draft, corpus=None, lang='he'):
    errors, warnings = [], []
    E = lambda code, *a: errors.append((code, msg(code, lang, *a)))
    W = lambda code, *a: warnings.append((code, msg(code, lang, *a)))
    if not isinstance(draft, dict) or draft.get('schema') != SCHEMA:
        E('SCHEMA', 'schema != %s' % SCHEMA)
        return errors, warnings
    a, obls = draft.get('agreement'), draft.get('obligations')
    if not isinstance(a, dict) or not isinstance(obls, list):
        E('SCHEMA', 'agreement / obligations')
        return errors, warnings
    aid = a.get('agreement_id')
    if not aid or not isinstance(aid, str) or _BAD_ID.search(aid) or aid.strip() != aid or aid in ('.', '..'):
        E('AGREEMENT_ID', aid)
    if a.get('executed') is not True:
        E('NOT_EXECUTED')
    if a.get('execution_basis') not in EXEC_BASIS:
        E('EXEC_BASIS', a.get('execution_basis'))
    dd = a.get('dates') or {}
    for k in ('signing_date', 'effective_date', 'end_date'):
        if not _date_ok(dd.get(k)):
            E('DATE', 'agreement.dates.' + k, dd.get(k))
    custom = {}
    for k, v in (dd.get('anchors') or {}).items():
        dv = v.get('date') if isinstance(v, dict) else v
        if not _date_ok(dv):
            E('DATE', 'anchors.' + k, dv)
        custom[k] = dv
    if dd.get('initial_term') and not (isinstance(dd['initial_term'], dict)
                                       and dd['initial_term'].get('unit') in D.UNITS):
        E('TIMING', 'agreement', 'dates.initial_term')
    ar = dd.get('auto_renewal')
    if ar and not (isinstance(ar, dict) and isinstance(ar.get('period'), dict)
                   and ar['period'].get('unit') in D.UNITS
                   and (ar.get('notice') is None or _check_off(dict(ar['notice'], direction='before')))):
        E('TIMING', 'agreement', 'dates.auto_renewal')
    # הגדרת "יום עסקים" שבהסכם: ימי מנוחה בשמם (friday, שבת), ולוחות חגים במילים
    bd = a.get('business_days')
    if bd is not None and not (isinstance(bd, dict) and isinstance(bd.get('weekend', []), list)
                               and all(str(x).strip().casefold() in D.DAY_NAMES for x in bd.get('weekend', []))
                               and isinstance(bd.get('calendars', []), list)):
        E('TIMING', 'agreement', 'business_days')
    # המסירה הנחשבת שבסעיף ההודעות
    nd = a.get('notice_delivery')
    if nd is not None:
        da = nd.get('deemed_after') if isinstance(nd, dict) else None
        if not isinstance(nd, dict) or (da is not None and not (
                isinstance(da, dict) and da.get('unit') in D.UNITS and str(da.get('n', '')).isdigit())) or (
                nd.get('cutoff_time') and not re.match(r'^\d{1,2}:\d{2}$', str(nd['cutoff_time']))):
            E('TIMING', 'agreement', 'notice_delivery')
    for doc in a.get('documents') or []:
        if doc.get('kind') not in DOC_KINDS:
            E('SCHEMA', 'documents.kind %r' % doc.get('kind'))
    text = corpus_text(corpus) if corpus else None
    if corpus is None:
        W('W_NO_CORPUS')
    else:
        for p in tracked_docs(corpus):
            W('W_TRACKED', p)
    ids, seen = {o.get('id') for o in obls if isinstance(o, dict)}, set()
    notices = a.get('notices') or {}
    for o in obls:
        if not isinstance(o, dict):
            E('SCHEMA', 'obligation is not an object')
            continue
        oid = o.get('id')
        if not isinstance(oid, str) or not oid.startswith('obl_') or oid in seen:
            E('OBL_ID', oid)
        seen.add(oid)
        if o.get('obligor') not in OBLIGORS:
            E('OBLIGOR', oid)
        if o.get('type') not in TYPES:
            E('TYPE', oid, o.get('type'))
        src = o.get('source') or {}
        q = src.get('quote')
        if not src.get('clause') or not q:
            E('SOURCE', oid)
        elif text is not None and norm(q) not in text:
            E('QUOTE_NOT_FOUND', oid, q[:90])
        if o.get('due_date'):
            E('HAND_DATE', oid, o.get('due_date'))
        bad, unknown = _check_timing(o.get('timing'), ids, custom)
        if bad:
            E('TIMING', oid, bad)
        if unknown is not None:
            E('ANCHOR', oid, unknown)
        st = o.get('status', 'open')
        if st not in STATUS:
            E('STATUS', oid, st)
        elif st != 'open':
            log = o.get('status_log') or []
            if not log or not log[-1].get('by') or not D.parse(log[-1].get('date')):
                E('STATUS', oid, st)
        if not o.get('department'):
            W('W_DEPARTMENT', oid)
        gaps = delivery_gaps(notices)
        if o.get('type') in ('notice', 'renewal_notice') and o.get('obligor') in ('us', 'both') and gaps:
            W('W_DELIVERY', oid, ', '.join(gaps))
    return errors, warnings
