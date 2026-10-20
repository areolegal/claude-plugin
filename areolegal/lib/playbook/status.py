# -*- coding: utf-8 -*-
"""playbook/status.py: מעמד אחד ותווית אחת לפלייבוק, נגזרים בקוד, ומשמשים בכל מקום.

הבעיה (סבב 2): אחרי החתימה היו שלושה מעמדות סותרים, והתווית "מבוסס הסכמים" הופיעה כשמספר ההסכמים 0.

הבעיה (סבב 3, הערות 5.5, שינוי 79):
- אחרי הקליטה, המודל, הגרעין והאינדקס אמרו "מדיניות מאושרת", ובאותה רשומה presentation_label אמר
  "טעון אישור"; התאים (ingest_result) נשארו מהרשומה המדומה; validation_queue נשאר פתוח; ה-handoff
  נשאר Draft; וה-Word וה-Workspace לא הופקו מחדש.
- check_consistency בדק רק שלושה שדות ברמה העליונה, ולכן החזיר [].
- התווית המאושרת לא נקבה בשם מי שאישר.

הכלל: שדה תווית אחד בלבד, status_label. presentation_label אינו נשמר בשום מקום (stamp מוחק אותו,
ו-check_consistency מסמן אותו). התווית הבסיסית (לפני אישור) נגזרת ב-base_label ומשמשת רק בתוך
status_label:
- 0 הסכמים, ואף מסלול אינו נשען על מסמך של החברה -> "פלייבוק מוצע, מבוסס מחקר שוק, טעון אישור"
- נספרו הסכמים, ומסלול נשען על מסמך של החברה, ויש מחקר שוק -> "פלייבוק מוצע, מבוסס הסכמים ומחקר שוק, טעון אישור"
- אין מחקר שוק -> "פלייבוק מוצע, מבוסס הסכמי החברה, טעון אישור"
- כל התאים נספרים כמאושרים, ואין שאלה מכריעה פתוחה -> "מדיניות מאושרת, <DD.MM.YYYY>, בידי <שם, תפקיד>"
- חלק מהתאים -> "<התווית הבסיסית>; <N> מתוך <M> עמדות מאושרות"

תא נספר כמאושר רק כש: המעמד שלו מאושר; policy_claim; הראיה אינה מדומה; כשהוא טעון בדיקה משפטית
נרשמו שם ותאריך; הוא אינו מסומן needs_amendment; ואין שאלה מכריעה פתוחה (חומרה גבוהה או קריטית)
בכלל שלו.

stamp() כותב את אותה תוצאה לכל השכבות: המודל, הגרעין, האינדקס, ה-handoff, התאים
(traffic_light.<track>.ingest_result), policy_status של כל כלל ושל כל סעיף בגרעין.
check_consistency() בודק את כל השכבות האלה, וגם את ה-Word ואת ה-Workspace כשהנתיבים נמסרים
(playbook.surfaces_render.check_surfaces).
"""
import datetime as _dt

TRACKS = ('green', 'yellow', 'red')
APPROVED = ('approved', 'approved_modified')

LABEL_MARKET = 'פלייבוק מוצע, מבוסס מחקר שוק, טעון אישור'
LABEL_MIXED = 'פלייבוק מוצע, מבוסס הסכמים ומחקר שוק, טעון אישור'
LABEL_OWN = 'פלייבוק מוצע, מבוסס הסכמי החברה, טעון אישור'
APPROVED_PREFIX = 'מדיניות מאושרת'
PARTIAL_FMT = '{base}; {n} מתוך {m} עמדות מאושרות'
BASE_LABELS = (LABEL_MARKET, LABEL_MIXED, LABEL_OWN)

LABEL_FIELD = 'status_label'
DUAL_FIELDS = ('presentation_label',)
HIGH_SEVERITY = ('high', 'critical', 'גבוהה', 'קריטית')

# basis של מסלול שנשען על מסמך של החברה (playbook-core-schema.md: own|own_plus_market|market_built)
COMPANY_BASES = ('company_agreement', 'company_template', 'agreement', 'template', 'established',
                 'company_policy', 'signed_deviation')
MARKET_ORIGINS = ('own_plus_market', 'market_built')

STATUS_DRAFT, STATUS_PARTIAL, STATUS_APPROVED = 'Draft', 'PartiallyApproved', 'Approved'

# ---- רשומת אישור ישנה (גרסה 1.2.0): כלל אחד, כאן, ו-ingest_approval משתמש בו ----
# רשומה בלי received_via או בלי upload_ref (ב-evidence או בשורש הרשומה) היא רשומה ישנה: אין בה ראיה שהגיליון
# החתום הגיע מהמשתמש. התאים שלה אינם נספרים כמאושרים, והמשתמש מתבקש פעם אחת להעלות שוב את הגיליון החתום.
REUPLOAD_NOTICE = ('רשומת האישור נקלטה בגרסה קודמת, בלי ראיה להעלאת הגיליון החתום. העמדות שבה אינן נספרות '
                   'כמאושרות. יש להעלות שוב את גיליון העמדות החתום.')


def is_legacy_record(record):
    """True כשלרשומת האישור חסרים received_via או upload_ref."""
    if not record:
        return False
    ev = record.get('evidence') or {}
    via = ev.get('received_via') or record.get('received_via')
    ref = ev.get('upload_ref') or record.get('upload_ref')
    return not (via and ref)


def effective_cells(record, cells=None):
    """התאים כפי שהם נספרים: ברשומה ישנה כל תא legacy, policy_claim=False ו-simulated=True (בלי לשנות את
    הרשומה עצמה). cells: התאים, כשאינם בתוך הרשומה."""
    cells = cells if cells is not None else (record or {}).get('cells') or {}
    if not is_legacy_record(record):
        return cells
    return {k: dict(c, legacy=True, policy_claim=False, simulated=True) for k, c in cells.items()}


def _latest_record(model):
    recs = [r for r in (model or {}).get('approval_records') or [] if not r.get('superseded_by')]
    return recs[-1] if recs else None


def cell_key(rule_id, track, segment=None):
    return '%s|%s|%s' % (rule_id, segment or '-', track)


def iter_cell_keys(model):
    """כל התאים בפלייבוק: שלושה מסלולים לכל כלל, וגרסאות סגמנט שמגדירות מסלול."""
    for rule in model.get('rules') or []:
        for t in TRACKS:
            yield cell_key(rule['rule_id'], t)
        for var in rule.get('segment_variants') or []:
            for t in TRACKS:
                if (var.get('traffic_light') or {}).get(t) and var.get('segment_id'):
                    yield cell_key(rule['rule_id'], t, var['segment_id'])


def agreements_counted(model):
    """מספר ההסכמים מהסוג שנספרו (corpus_basis), ולא מספר הקבצים בתיקייה."""
    cb = model.get('corpus_basis') or {}
    for k in ('agreements_counted', 'agreement_units', 'counted'):
        if isinstance(cb.get(k), int):
            return cb[k]
    ss = model.get('scope_summary') or {}
    if isinstance(ss.get('total_document_count'), int):
        return ss['total_document_count']
    return 0


NON_COMPANY_BASES = ('market_standard', 'areo_proposal')


def company_backed_tracks(model):
    """מסלולים שנשענים על מסמך של החברה: כל basis שאינו שוק ואינו הצעת Areo.

    תיקון מקומי של ניל, לדיווח לענבל: COMPANY_BASES לא הכיר את own_paper_repeated, own_evidence, single,
    client_answer ועוד ערכים של playbook-schema.md, ולכן פלייבוק שנבנה מהסכמי החברה קיבל בהרצה חיה את התווית
    "מבוסס מחקר שוק" (20.10.2026). רשימה של ערכי חברה נשחקת עם כל ערך חדש; רשימת הערכים שאינם של החברה קצרה
    וסגורה."""
    n = 0
    for rule in model.get('rules') or []:
        for t in TRACKS:
            basis = ((rule.get('traffic_light') or {}).get(t) or {}).get('basis')
            if basis and basis not in NON_COMPANY_BASES:
                n += 1
    return n


def uses_market(model):
    if model.get('corpus_origin') in MARKET_ORIGINS:
        return True
    mr = model.get('market_research') or {}
    return any(f.get('client_choice') == 'include' for f in mr.get('findings') or [])


def base_label(model):
    """התווית לפני אישור. "מבוסס הסכמים" רק כשנספרו הסכמים וגם מסלול נשען על מסמך של החברה."""
    own = agreements_counted(model) > 0 and company_backed_tracks(model) > 0
    if uses_market(model):
        return LABEL_MIXED if own else LABEL_MARKET
    return LABEL_OWN


def _he_date(iso):
    d = _dt.date.fromisoformat(str(iso)[:10])
    return '%02d.%02d.%04d' % (d.day, d.month, d.year)


def open_decisive(model):
    """שאלות מכריעות פתוחות (חומרה גבוהה או קריטית) ב-validation_queue."""
    out = []
    for qi in model.get('validation_queue') or []:
        st = qi.get('status') or ('closed' if qi.get('answered') else 'open')
        if st == 'open' and not qi.get('answered') and str(qi.get('severity') or '').lower() in HIGH_SEVERITY:
            out.append(qi)
    return out


def _rule_of(key):
    return key.split('|')[0]


def cell_counts(cell):
    """האם תא נספר כמאושר: מעמד מאושר, policy_claim, ראיה שאינה מדומה, בדיקה משפטית שנרשמה בשם ובתאריך
    כשנדרשה, ובלי סימון needs_amendment (פגם שהנושא ונותן מצא בנוסח מאושר)."""
    if not cell or cell.get('status') not in APPROVED:
        return False
    if not cell.get('policy_claim') or cell.get('simulated') or cell.get('needs_amendment') or cell.get('legacy'):
        return False
    if cell.get('legal_review_required') and not (cell.get('legal_review_done_by') and
                                                  cell.get('legal_review_done_at', True)):
        return False
    return True


def _signed_by(cells, keys):
    seen = []
    for k in keys:
        c = cells.get(k) or {}
        who = ', '.join(x for x in (c.get('signer'), c.get('role')) if x)
        if who and who not in seen:
            seen.append(who)
    return '; '.join(seen)


def derive_status(model, cells=None, record=None):
    """cells: {cell_key: {status, policy_claim, simulated, legal_review_required, legal_review_done_by,
    legal_review_done_at, approved_at, signer, role}} מרשומת הקליטה. record: רשומת האישור (בלעדיה: האחרונה
    ב-model.approval_records). רשומה ישנה (is_legacy_record): אף תא אינו נספר, ו-notices מכיל את REUPLOAD_NOTICE
    פעם אחת. מחזיר dict אחד שכל הרכיבים קוראים ממנו."""
    rec = record if record is not None else _latest_record(model)
    legacy = is_legacy_record(rec)
    cells = effective_cells(rec, cells or {}) if legacy else (cells or {})
    keys = list(iter_cell_keys(model))
    oq = open_decisive(model)
    blocked_rules = {q.get('rule_id') for q in oq if q.get('rule_id') and q.get('rule_id') != 'GLOBAL'}
    global_open = [q.get('id') for q in oq if not q.get('rule_id') or q.get('rule_id') == 'GLOBAL']
    approved = [k for k in keys if cell_counts(cells.get(k)) and _rule_of(k) not in blocked_rules]
    blocked = sorted(k for k in keys if (cells.get(k) or {}).get('status') in
                     ('pending_choice', 'pending_legal_review', 'open') or
                     (cell_counts(cells.get(k)) and _rule_of(k) in blocked_rules))
    base = base_label(model)
    n, m = len(approved), len(keys)
    if m and n == m and not global_open:
        dates = sorted(str(cells[k].get('approved_at') or '')[:10] for k in approved if cells[k].get('approved_at'))
        when = dates[-1] if dates else _dt.date.today().isoformat()
        by = _signed_by(cells, approved)
        code = STATUS_APPROVED
        label = '%s, %s' % (APPROVED_PREFIX, _he_date(when)) + (', בידי %s' % by if by else '')
    elif n:
        code, label = STATUS_PARTIAL, PARTIAL_FMT.format(base=base, n=n, m=m)
    else:
        code, label = STATUS_DRAFT, base
    return {'playbook_status': code, 'label': label, 'base_label': base, 'approved_count': n,
            'positions_count': m, 'approved_keys': approved, 'blocked_keys': blocked,
            'open_questions': [q.get('id') for q in oq], 'agreements_counted': agreements_counted(model),
            'legacy_record': legacy, 'notices': [REUPLOAD_NOTICE] if legacy else []}


def policy_claim(model, cells, rule_id, track, segment=None, wording_fp=None):
    """שער המדיניות: מותר לומר "מדיניות החברה" על התא רק כשהתא נספר כמאושר באותה גזירה.

    wording_fp: טביעת האצבע של הנוסח שהנושא ונותן עומד להחיל (approval_sheet.fingerprint). כשהיא שונה
    מ-approved_fp של התא, הנוסח אינו הנוסח שאושר: policy_claim=False, והסטייה מוצגת למשתמש כ"נדרשת הכרעתך"."""
    key = cell_key(rule_id, track, segment)
    if segment and key not in (cells or {}):
        key = cell_key(rule_id, track)
    cell = (cells or {}).get(key)
    st = derive_status(model, cells)
    ok = key in st['approved_keys']
    reason = None
    if not ok:
        reason = 'open_decisive_question' if cell_counts(cell) else 'not_approved'
    if ok and wording_fp and cell.get('approved_fp') and wording_fp != cell['approved_fp']:
        ok, reason = False, 'wording_differs_from_approved'
    return {'policy_claim': ok, 'key': key, 'reason': reason, 'status_label': st['label'],
            'playbook_status': st['playbook_status']}


def cell_result(cell, record_id=None):
    """התא כפי שנכתב למודל (traffic_light.<track>.ingest_result): אותם ערכים כמו ברשומה."""
    if not cell:
        return None
    out = {k: cell.get(k) for k in ('status', 'policy_claim', 'simulated', 'legal_review_done_by',
                                    'legal_review_done_at', 'approved_at', 'signer')}
    out['counts_as_approved'] = cell_counts(cell)
    if record_id:
        out['record_id'] = record_id
    return out


def _rule_policy_status(rule, cells, st):
    keys = [cell_key(rule['rule_id'], t) for t in TRACKS]
    if all(k in st['approved_keys'] for k in keys):
        return 'Confirmed'
    return rule.get('policy_status_from_evidence') or rule.get('policy_status') or 'Inferred'


def stamp(model, core, index_entry, cells=None, record_id=None):
    """כותב את אותה תוצאה לכל השכבות. הבונה אינו כותב את השדות האלה בשום דרך אחרת."""
    st = derive_status(model, cells)
    holders = [model, core, index_entry]
    if model is not None and isinstance(model.get('handoff'), dict):
        holders.append(model['handoff'])
    for holder in holders:
        if holder is None:
            continue
        for f in DUAL_FIELDS:
            holder.pop(f, None)
        holder['playbook_status'] = st['playbook_status']
        holder[LABEL_FIELD] = st['label']
        holder['approved_count'] = st['approved_count']
        holder['positions_count'] = st['positions_count']
    if model is not None and cells is not None:
        for rule in model.get('rules') or []:
            if 'policy_status_from_evidence' not in rule:
                rule['policy_status_from_evidence'] = rule.get('policy_status') or 'Inferred'
            for t in TRACKS:
                tl = (rule.get('traffic_light') or {}).get(t)
                if isinstance(tl, dict):
                    res = cell_result(cells.get(cell_key(rule['rule_id'], t)), record_id)
                    if res is None:
                        tl.pop('ingest_result', None)
                    else:
                        tl['ingest_result'] = res
            rule['policy_status'] = _rule_policy_status(rule, cells, st)
        if core is not None:
            by_id = {r['rule_id']: r for r in model.get('rules') or []}
            for c in core.get('clauses') or []:
                r = by_id.get(c.get('id') or c.get('rule_id'))
                if r is not None:
                    c['policy_status'] = r['policy_status']
    return st


def surfaces(st):
    """הטקסט שכל משטח מציג. כולם נגזרים מאותו st, ולכן זהים."""
    return {
        'word_header': st['label'],
        'workspace': {'label_now': st['label'], 'approved_count': st['approved_count'],
                      'positions_count': st['positions_count']},
        'chat_first_line': st['label'],
        'gate': st['label'],
        'model': st['label'],
    }


def check_consistency(model, core=None, index_entry=None, cells=None, word_path=None, workspace_path=None):
    """מחזיר רשימת סטיות בין הערך המחושב לבין מה שנשמר ומה שמוצג. ריקה = עקבי."""
    st = derive_status(model, cells)
    out = []
    holders = [('model', model), ('core', core), ('index', index_entry)]
    if isinstance(model.get('handoff'), dict):
        holders.append(('handoff', model['handoff']))
    for name, holder in holders:
        if holder is None:
            continue
        for f in DUAL_FIELDS:
            if f in holder:
                out.append('%s.%s: שדה תווית כפול. התווית היחידה היא status_label' % (name, f))
        for field, want in (('playbook_status', st['playbook_status']), (LABEL_FIELD, st['label'])):
            if field in holder and holder.get(field) != want:
                out.append('%s.%s="%s", המחושב: "%s"' % (name, field, holder.get(field), want))
    if cells is not None:
        for rule in model.get('rules') or []:
            for t in TRACKS:
                tl = (rule.get('traffic_light') or {}).get(t) or {}
                key = cell_key(rule['rule_id'], t)
                got, want = tl.get('ingest_result'), cells.get(key)
                if want is None:
                    continue
                if not got or got.get('status') != want.get('status') or \
                        bool(got.get('policy_claim')) != bool(want.get('policy_claim')) or \
                        bool(got.get('simulated')) != bool(want.get('simulated')):
                    out.append('%s: ingest_result במודל אינו התא שברשומה הנוכחית' % key)
            if rule.get('policy_status') != _rule_policy_status(rule, cells, st):
                out.append('%s.policy_status="%s", המחושב: "%s"' % (
                    rule['rule_id'], rule.get('policy_status'), _rule_policy_status(rule, cells, st)))
    for qi in open_decisive(model):
        rid = qi.get('rule_id')
        if rid and any(cell_counts((cells or {}).get(cell_key(rid, t))) for t in TRACKS):
            out.append('%s: שאלה מכריעה פתוחה (%s) בכלל שתאיו נחתמו. הבחירה בגיליון לא נרשמה' % (rid, qi.get('id')))
    if word_path or workspace_path:
        from playbook import surfaces_render as R
        out += R.check_surfaces(st, word_path=word_path, workspace_path=workspace_path, model=model)
    return out
