"""מדדי הקבלה של שלב 1, כפי שנקבעו בפרק 19 באפיון 1.1."""
from clm import catalog, dates

QUOTED = ("events", "key_clauses", "guarantees", "commercials")


def metrics(data):
    docs = {d["id"]: d for d in data["documents"]}
    ags, evs = data["agreements"], data["events"]
    tpl = [a for a in ags if a["doc_ids"] and all(docs.get(i, {}).get("doc_kind") in ("template", "non_agreement") for i in a["doc_ids"])]
    other = [a for a in ags if a.get("type_code") is None]
    return {
        "agreements": len(ags),
        "templates_in_register": len(tpl),
        "other_pct": round(100.0 * len(other) / len(ags), 1) if ags else 0.0,
        "events_without_quote": sum(1 for e in evs if not e.get("refs")),
        "items_without_quote": sum(1 for k in QUOTED for x in data.get(k) or [] if not x.get("refs")),
        "bad_coverage": sum(1 for a in ags if {c["category"] for c in a.get("coverage", [])} != set(catalog.CATEGORIES)),
        "generic_actions": sum(1 for e in evs if any(g in (e.get("action") or "") for g in dates.GENERIC)),
        "auto_closed": sum(1 for e in evs if e.get("state") not in dates.STATES),
    }


CRITERIA = [
    ("agreements", lambda v: v > 0, "יותר מ-0 הסכמים"),
    ("templates_in_register", lambda v: v == 0, "אפס תבניות ומסמכים שאינם הסכמים במאגר"),
    ("other_pct", lambda v: v < 5, "פחות מ-5% הסכמים מסוג שאינו בקטלוג"),
    ("items_without_quote", lambda v: v == 0, "ציטוט לכל פריט: מועדים, סעיפי מפתח, בטוחות ותנאים מסחריים"),
    ("bad_coverage", lambda v: v == 0, "היקף בדיקה לשש הקטגוריות בכל הסכם"),
    ("generic_actions", lambda v: v == 0, "אפס פעולות כלליות"),
    ("auto_closed", lambda v: v == 0, "אפס מועדים שנסגרו אוטומטית"),
]


def report(data):
    m = metrics(data)
    lines, ok = [], True
    for key, test, label in CRITERIA:
        passed = test(m[key])
        ok = ok and passed
        lines.append("%s %s: %s" % ("עבר" if passed else "נכשל", label, m[key]))
    return ok, lines
