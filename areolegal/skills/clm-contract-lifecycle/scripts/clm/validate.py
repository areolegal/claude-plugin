"""ולידציה: קובץ חילוץ של מסמך אחד, ו-clm-data.json בגרסה 2.

כשל בקובץ חילוץ מוציא אותו מההרכבה ומעביר אותו לאימות נתונים. כשל ב-clm-data.json
עוצר את ההפקה. התיקון נעשה בנתונים, לעולם לא בתבנית.
"""
import datetime
import re

from clm import catalog, money
from clm.doc_kind import DOC_KINDS

ISO = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
LONG_DASH = re.compile("[\u2013\u2014]")
ROLE_SOURCES = {"playbook", "user", "suggested", "none"}
OBLIGORS = {"us", "them", "both"}
DIRECTIONS = {"given", "received", "policy", "unknown"}
VERSION_BY = {"us", "them", "unknown"}
COVERAGE = {"found", "none_found", "not_checked"}
IMPACTS = {"critical", "material", "administrative"}
TERM_KINDS = {"fixed", "indefinite", "until_event", "project", "none"}
TERM_STARTS = {"start", "signed", "other"}
RENEWAL_KINDS = {"auto", "option", "mutual", "none"}
PARTIES = {"counterparty", "contracting", "both", "unknown"}
EXIT_WHO = PARTIES | {"none"}
SIGN_PARTIES = {"counterparty", "contracting", "unknown"}
SIGN_STATUS = {"signed", "blank", "unknown"}
PAY_BASIS = {"invoice", "eom", "milestone", "other"}
FACT_CODES = {"negotiation_stopped", "other"}
VALUE_KINDS = {"monthly", "annual", "total", "max", "unit"}
VALUE_BASIS = {"fixed", "estimate", "usage"}
STANCES = {"set", "expressly_none"}
COC_REQUIRES = {"consent", "notice", "termination_right", "none"}
TERM_ROLES = {"initial_end", "extension_end", "max_end", "min_commitment_end"}
REQUIRED = ("file", "sha256", "doc_kind", "title", "counterparty", "our_role", "dates", "events", "coverage")
OBJECT_FIELDS = ("counterparty", "our_role", "dates")
LIST_FIELDS = ("events", "coverage")


def _strings(x):
    """כל המחרוזות, חוץ מציטוטים (quote): ציטוט מועתק מילה במילה, גם כשיש בו מקף ארוך."""
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for k, v in x.items():
            if k != "quote":
                yield from _strings(v)
    elif isinstance(x, list):
        for v in x:
            yield from _strings(v)


def _in(value, allowed):
    # ערך שאינו מחרוזת (רשימה, מספר, null) אינו מותר. בלי הבדיקה, set ו-dict זורקים TypeError.
    return isinstance(value, str) and value in allowed


def _date(p, where, value):
    if value is None:
        return
    text = str(value)
    if not ISO.fullmatch(text):
        p.append("%s: date %r אינו בפורמט YYYY-MM-DD" % (where, value))
        return
    try:
        datetime.date.fromisoformat(text)
    except ValueError:
        p.append("%s: date %r אינו תאריך קיים" % (where, value))


def _items(p, name, seq):
    out = []
    for i, x in enumerate(seq):
        if isinstance(x, dict):
            out.append((i, x))
        else:
            p.append("מבנה פגום: %s[%d] אינו אובייקט" % (name, i))
    return out


def _optional_list(p, ext, name):
    value = ext.get(name) or []
    if not isinstance(value, list):
        p.append("מבנה פגום: %s אינו בצורה הנכונה" % name)
        return []
    return _items(p, name, value)


def _whole(p, where, v):
    if v is not None and (isinstance(v, bool) or not isinstance(v, int) or v < 0):
        p.append("%s: חייב להיות מספר שלם לא שלילי" % where)


def _str_or_null(p, where, v):
    if v is not None and not isinstance(v, str):
        p.append("%s: חייב להיות מחרוזת או null" % where)


def _enum(p, where, v, allowed, nullable=True):
    if v is None and nullable:
        return
    if not _in(v, allowed):
        p.append("%s %r אינו מותר" % (where, v))


def _obj(p, ext, name):
    v = ext.get(name)
    if v is None:
        return None
    if not isinstance(v, dict):
        p.append("מבנה פגום: %s אינו אובייקט" % name)
        return None
    return v


def _check_extended(p, ext):
    t = _obj(p, ext, "term")
    if t is not None:
        _enum(p, "term.kind", t.get("kind"), TERM_KINDS, False)
        _whole(p, "term.initial_months", t.get("initial_months"))
        _enum(p, "term.starts_on", t.get("starts_on"), TERM_STARTS)
        _date(p, "term.max_end", t.get("max_end"))
        _str_or_null(p, "term.trigger", t.get("trigger"))
    r = _obj(p, ext, "renewal")
    if r is not None:
        _enum(p, "renewal.kind", r.get("kind"), RENEWAL_KINDS, False)
        for k in ("period_months", "max_count", "notice_days"):
            _whole(p, "renewal.%s" % k, r.get(k))
        _enum(p, "renewal.holder", r.get("holder"), PARTIES)
        _str_or_null(p, "renewal.holder_name", r.get("holder_name"))
    x = _obj(p, ext, "exit")
    if x is not None:
        _enum(p, "exit.who", x.get("who"), EXIT_WHO, False)
        for k in ("notice_days", "min_commitment_months"):
            _whole(p, "exit.%s" % k, x.get(k))
        _str_or_null(p, "exit.who_name", x.get("who_name"))
    for i, s in _optional_list(p, ext, "signatories"):
        w = "signatories[%d]" % i
        _enum(p, w + ".party", s.get("party"), SIGN_PARTIES, False)
        _enum(p, w + ".status", s.get("status"), SIGN_STATUS, False)
        _date(p, w, s.get("date"))
        for k in ("party_name", "name", "role"):
            _str_or_null(p, "%s.%s" % (w, k), s.get(k))
    j = _obj(p, ext, "jurisdiction")
    if j is not None:
        if j.get("exclusive") is not None and not isinstance(j["exclusive"], bool):
            p.append("jurisdiction.exclusive חייב להיות true, false או null")
        _str_or_null(p, "jurisdiction.court", j.get("court"))
    pt = _obj(p, ext, "payment_terms")
    if pt is not None:
        _whole(p, "payment_terms.days", pt.get("days"))
        _enum(p, "payment_terms.basis", pt.get("basis"), PAY_BASIS)
        _str_or_null(p, "payment_terms.text", pt.get("text"))
    for i, f in _optional_list(p, ext, "facts"):
        _enum(p, "facts[%d].code" % i, f.get("code"), FACT_CODES, False)
        if not isinstance(f.get("label"), str) or not f["label"].strip():
            p.append("facts[%d].label: חייב להיות מחרוזת לא ריקה" % i)
        _str_or_null(p, "facts[%d].value" % i, f.get("value"))
    for i, c in _optional_list(p, ext, "commercials"):
        _enum(p, "commercials[%d].value_kind" % i, c.get("value_kind"), VALUE_KINDS)
        _enum(p, "commercials[%d].basis" % i, c.get("basis"), VALUE_BASIS)
        _enum(p, "commercials[%d].operation" % i, c.get("operation"), money.OPERATIONS)
        eff = c.get("effective_date")
        if eff is not None and not (isinstance(eff, str) and money.ISO_DATE.match(eff)):
            p.append("commercials[%d].effective_date: חייב להיות YYYY-MM-DD או null" % i)


def _check_key_clause_extension(p, i, c):
    w = "key_clauses[%d]" % i
    _enum(p, w + ".bound_party", c.get("bound_party"), PARTIES)
    _enum(p, w + ".stance", c.get("stance"), STANCES)
    _str_or_null(p, w + ".bound_party_name", c.get("bound_party_name"))
    norm = c.get("norm")
    if norm is None:
        return
    if not isinstance(norm, dict):
        p.append("מבנה פגום: %s.norm אינו אובייקט" % w)
        return
    _date(p, w + ".norm.until", norm.get("until"))
    _enum(p, w + ".norm.requires", norm.get("requires"), COC_REQUIRES)
    _whole(p, w + ".norm.months", norm.get("months"))


def _check(ext):
    p = []
    if not isinstance(ext, dict):
        return ["מבנה פגום: השורש אינו אובייקט"]
    events_cat, kc = catalog.load_events(), catalog.load_key_clauses()
    for k in REQUIRED:
        if k not in ext:
            p.append("חסר שדה חובה: %s" % k)
    if p:
        return p
    for k in OBJECT_FIELDS:
        if not isinstance(ext[k], dict):
            p.append("מבנה פגום: %s אינו בצורה הנכונה" % k)
    for k in LIST_FIELDS:
        if not isinstance(ext[k], list):
            p.append("מבנה פגום: %s אינו בצורה הנכונה" % k)
    if p:
        return p
    if not _in(ext["doc_kind"], DOC_KINDS):
        p.append("doc_kind %r אינו ברשימה הסגורה" % ext["doc_kind"])
    source = ext["our_role"].get("source")
    if not _in(source, ROLE_SOURCES):
        p.append("our_role.source %r אינו מותר" % source)
    if not _in(ext.get("version_by", "unknown"), VERSION_BY):
        p.append("version_by %r אינו מותר" % ext.get("version_by"))
    if ext.get("playbook_family_id") is not None and not isinstance(ext["playbook_family_id"], str):
        p.append("playbook_family_id חייב להיות מחרוזת או null")
    for k in ("signed", "start", "end"):
        _date(p, "dates.%s" % k, ext["dates"].get(k))
    for i, e in _items(p, "events", ext["events"]):
        w = "events[%d]" % i
        if not _in(e.get("event_code"), events_cat):
            p.append("%s: event_code %r אינו בקטלוג" % (w, e.get("event_code")))
        for k in ("label", "clause"):
            if not e.get(k):
                p.append("%s: חסר %s" % (w, k))
        if not _in(e.get("consequence"), catalog.CONSEQUENCES):
            p.append("%s: consequence %r אינו מותר" % (w, e.get("consequence")))
        if not _in(e.get("obligor"), OBLIGORS):
            p.append("%s: obligor %r אינו מותר" % (w, e.get("obligor")))
        if not _in(e.get("impact"), IMPACTS):
            p.append("%s: impact %r אינו מותר" % (w, e.get("impact")))
        _date(p, w, e.get("date"))
        if e.get("relative") and not e.get("trigger"):
            p.append("%s: מועד יחסי חייב trigger" % w)
        if e.get("term_role") is not None:
            if e.get("event_code") != "term_end":
                p.append("%s: term_role מותר רק בתום תקופה" % w)
            elif not _in(e["term_role"], TERM_ROLES):
                p.append("%s: term_role %r אינו מותר" % (w, e["term_role"]))
    for i, g in _optional_list(p, ext, "guarantees"):
        if not _in(g.get("direction"), DIRECTIONS):
            p.append("guarantees[%d]: direction %r אינו מותר" % (i, g.get("direction")))
        _date(p, "guarantees[%d].expiry" % i, g.get("expiry"))
    for i, c in _optional_list(p, ext, "key_clauses"):
        if not _in(c.get("clause_code"), kc):
            p.append("key_clauses[%d]: clause_code %r אינו בקטלוג" % (i, c.get("clause_code")))
        _check_key_clause_extension(p, i, c)
    _check_extended(p, ext)
    coverage = _items(p, "coverage", ext["coverage"])
    names = {c.get("category") for _, c in coverage if isinstance(c.get("category"), str)}
    if names != set(catalog.CATEGORIES):
        p.append("coverage: חייב לכלול בדיוק את שש הקטגוריות")
    for _, c in coverage:
        if not _in(c.get("status"), COVERAGE):
            p.append("coverage: status %r אינו מותר" % c.get("status"))
        if c.get("status") in ("none_found", "not_checked") and not c.get("note"):
            p.append("coverage: %s בלי note" % c.get("category"))
    for k, v in (("counterparty.role", (ext.get("counterparty") or {}).get("role")), ("contracting_role", ext.get("contracting_role"))):
        _str_or_null(p, k, v)
    if any(LONG_DASH.search(s) for s in _strings(ext)):
        p.append("נמצא מקף ארוך בטקסט שאינו ציטוט (בציטוט מותר): להחליף במקף רגיל")
    return p


def check_extraction(ext):
    try:
        return _check(ext)
    except (TypeError, AttributeError, KeyError) as e:
        return ["מבנה פגום: %s" % type(e).__name__]


# ---------- clm-data.json גרסה 2 ----------
from clm import dates as _dates  # noqa: E402

TOP = ["meta", "documents", "agreements", "events", "commercials", "guarantees", "key_clauses",
       "footnotes", "timeline", "counterparties", "registers", "review_queue", "catalog"]
AGREEMENT_STATES = {"signed_not_effective", "in_force", "renewal_window", "extended", "ended", "ended_early",
                    "replaced", "survival_only", "term_passed_unverified", "status_unverified"}
END_STATUSES = {"extracted", "derived", "not_expected", "missing", "not_relevant"}
OVERDUE_BUCKETS = {"ours", "theirs", "role", "outcome", "old", "superseded"}
HANDLING_STAGES = {"request", "drafting", "with_cp", "comments", "final", "internal", "signing", "frozen", "abandoned"}


def _check_data(data):
    errors, warns = [], []
    for k in TOP:
        if k not in data:
            errors.append("חסר מפתח עליון: %s" % k)
    if errors:
        return errors, warns
    ev_cat = catalog.load_events()
    notes = {f["n"] for f in data["footnotes"]}
    ag_ids = {a["id"] for a in data["agreements"]}
    for label, values in (("מזהה הסכם", [a["id"] for a in data["agreements"]]),
                          ("מספר הסכם", [a["number"] for a in data["agreements"]]),
                          ("מזהה מועד", [e["id"] for e in data["events"]]),
                          ("מזהה פריט אימות", [r["id"] for r in data["review_queue"] if r.get("id")])):
        seen, dups = set(), set()
        for v in values:
            (dups if v in seen else seen).add(v)
        if dups:
            errors.append("%s כפול: %s" % (label, ", ".join(sorted(str(v) for v in dups))))
    regs = data["registers"] if isinstance(data["registers"], dict) else {}
    for k in ("restrictions", "restrictions_review", "change_of_control", "change_of_control_review"):
        if regs.get(k) is not None and not isinstance(regs[k], list):
            errors.append("registers/%s: חייב להיות רשימה או null" % k)
    if regs.get("restriction_details") is not None and not isinstance(regs["restriction_details"], dict):
        errors.append("registers/restriction_details: חייב להיות מילון או null")
    for d in data["documents"]:
        if d["doc_kind"] not in DOC_KINDS:
            errors.append("documents/%s: doc_kind %r אינו מותר" % (d["id"], d["doc_kind"]))
    for a in data["agreements"]:
        w = "agreements/%s" % a["number"]
        if a.get("agreement_state") and a["agreement_state"] not in AGREEMENT_STATES:
            errors.append("%s: agreement_state %r אינו מותר" % (w, a["agreement_state"]))
        if a.get("handling_stage") and a["handling_stage"] not in HANDLING_STAGES:
            errors.append("%s: handling_stage %r אינו מותר" % (w, a["handling_stage"]))
        if bool(a.get("agreement_state")) == bool(a.get("handling_stage")):
            errors.append("%s: חייב בדיוק אחד מ-agreement_state ו-handling_stage" % w)
        if {c.get("category") for c in a.get("coverage", [])} != set(catalog.CATEGORIES):
            errors.append("%s: coverage חייב לכלול את שש הקטגוריות" % w)
        end_status = (a.get("field_status") or {}).get("end_date")
        if end_status is not None and end_status not in END_STATUSES:
            errors.append("%s: field_status.end_date %r אינו מותר" % (w, end_status))
        for cur in ((a.get("value") or {}).get("annual_by_currency") or {}):
            if not money.explicit_code(cur):
                errors.append("%s: מטבע %r אינו מוכר" % (w, cur))
    owner = {f["n"]: f.get("agreementId") for f in data["footnotes"]}

    def check_refs(w, x, aid=None):
        for n in (x.get("refs") if isinstance(x, dict) else None) or []:
            if n not in notes:
                errors.append("%s: הפניה %s אינה קיימת בציטוטים" % (w, n))
            elif aid is not None and owner[n] != aid:
                errors.append("%s: הפניה %s שייכת להסכם אחר" % (w, n))
    for a in data["agreements"]:
        w = "agreements/%s" % a["number"]
        for k in ("term", "renewal", "exit", "jurisdiction", "payment_terms"):
            check_refs("%s/%s" % (w, k), a.get(k), a["id"])
        for k in ("signatories", "facts"):
            for i, x in enumerate(a.get(k) or []):
                check_refs("%s/%s[%d]" % (w, k, i), x, a["id"])
    for aid, items in ((regs.get("restriction_details") or {}).items() if isinstance(regs.get("restriction_details"), dict) else []):
        for i, x in enumerate(items or []):
            check_refs("registers/restriction_details/%s[%d]" % (aid, i), x, aid if aid in ag_ids else None)
    for e in data["events"]:
        w = "events/%s" % e["id"]
        if e["agreementId"] not in ag_ids:
            errors.append("%s: agreementId לא קיים" % w)
        if e["event_code"] not in ev_cat:
            errors.append("%s: event_code %r אינו בקטלוג" % (w, e["event_code"]))
        if e.get("overdue_bucket") is not None and e["overdue_bucket"] not in OVERDUE_BUCKETS:
            errors.append("%s: overdue_bucket %r אינו מותר" % (w, e["overdue_bucket"]))
        if e["state"] not in _dates.STATES:
            errors.append("%s: state %r אינו מותר (realized אסור)" % (w, e["state"]))
        for n in e.get("refs", []):
            if n not in notes:
                errors.append("%s: הפניה %s אינה קיימת בציטוטים" % (w, n))
        if not e.get("refs") and not e.get("verify"):
            errors.append("%s: מועד בלי ציטוט חייב verify" % w)
        if e["state"] in ("upcoming", "needs_action") and not e.get("action"):
            errors.append("%s: חסרה פעולה נדרשת" % w)
        if any(g in (e.get("action") or "") for g in _dates.GENERIC):
            errors.append("%s: פעולה כללית אסורה" % w)
        for k in ("date", "act_by"):
            if e.get(k) and not ISO.match(e[k]):
                errors.append("%s: %s אינו ISO" % (w, k))
        if not e.get("refs"):
            warns.append("%s: טעון אימות, אין ציטוט" % w)
    if any(LONG_DASH.search(s) for s in _strings({k: data[k] for k in TOP if k != "catalog"})):
        errors.append("נמצא מקף ארוך בנתונים מחוץ לציטוטים")
    # הסכם שקובץ החילוץ שלו נפסל אינו נכנס למאגר: זו שגיאה, לא שקט
    for r in data["review_queue"]:
        if r.get("kind") == "bad_extract":
            errors.append("קובץ החילוץ של %s נפסל, וההסכם לא נכנס למאגר: %s. לתקן את קובץ החילוץ ולהריץ assemble שוב"
                          % (r.get("source") or r.get("text"), "; ".join(r.get("detail") or [r.get("text") or ""])))
        elif r.get("kind") == "not_extracted":
            warns.append("ממתין לחילוץ: %s" % r.get("text"))
        elif r.get("kind") == "unsupported":
            warns.append("קובץ שלא נקרא (סוג שאינו נתמך): %s" % r.get("text"))
    return errors, warns


def check_data(data):
    if not isinstance(data, dict):
        return ["מבנה פגום: השורש אינו אובייקט"], []
    try:
        return _check_data(data)
    except (TypeError, AttributeError, KeyError, ValueError) as e:
        return ["מבנה פגום: %s" % type(e).__name__], []
