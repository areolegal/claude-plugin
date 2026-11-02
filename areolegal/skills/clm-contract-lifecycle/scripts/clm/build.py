"""הזרקת clm-data.json לתבנית הקפואה. התבנית אינה נקראת להקשר ואינה משתנה בהפקה.

עותק לקהל מצומצם (audience="restricted"): ההסכמים המוסתרים ושאר הנגזר מהם מוסרים פיזית מהנתונים לפני ההטמעה
(restrict). הסתרה בתצוגה בלבד אינה הסתרה, כי הנתונים נשארים בקובץ. העותק המלא המקומי נבנה בלי הסינון ונשאר שלם.
"""
import copy
import json
import os

FULL, RESTRICTED = "full", "restricted"
# רשימות שכל רשומה בהן נושאת agreementId
BY_AGREEMENT = ("events", "commercials", "guarantees", "key_clauses", "footnotes", "timeline", "review_queue")


class AudienceError(ValueError):
    pass


def _hidden_ids(data, hide_ids, hide_types):
    ids, types = set(hide_ids or ()), set(hide_types or ())
    out = {a["id"] for a in data.get("agreements") or []
           if a.get("id") in ids or (a.get("type_code") in types and a.get("type_code"))}
    missing = ids - {a.get("id") for a in data.get("agreements") or []}
    if missing:
        raise AudienceError("מזהי הסכם להסתרה שאינם בנתונים: " + ", ".join(sorted(missing)))
    if not out:
        raise AudienceError("עותק מצומצם בלי אף הסכם להסתרה אינו מצומצם. יש לציין --hide-id או --hide-type שמתאימים להסכם")
    return out


def _scrub(x, hidden, hidden_events):
    """מסיר מכל מבנה מוטמע (גם ברישומים, ברשימות ובמילונים) מזהי הסכם ומועד מוסתרים ורשומות שנושאות אותם."""
    if isinstance(x, dict):
        return {k: _scrub(v, hidden, hidden_events) for k, v in x.items() if k not in hidden and k not in hidden_events}
    if isinstance(x, list):
        out = []
        for v in x:
            if isinstance(v, str) and (v in hidden or v in hidden_events):
                continue
            if isinstance(v, dict) and (v.get("agreementId") in hidden or v.get("eventId") in hidden_events
                                        or v.get("id") in hidden_events):
                continue
            out.append(_scrub(v, hidden, hidden_events))
        return out
    return x


def restrict(data, hide_ids=(), hide_types=()):
    """עותק של הנתונים בלי ההסכמים המוסתרים וכל מה שנגזר מהם: מסמכים, מועדים, תמורות, ציטוטים, רישומים,
    פריטי אימות, צדדים שכנגד וסכומיהם. הנתונים שהתקבלו אינם משתנים. נכשל אם נשאר זכר להסכם מוסתר."""
    from clm import money
    data = copy.deepcopy(data)
    hidden = _hidden_ids(data, hide_ids, hide_types)
    gone = [a for a in data["agreements"] if a["id"] in hidden]
    keep = [a for a in data["agreements"] if a["id"] not in hidden]
    hidden_events = {e["id"] for e in data.get("events") or [] if e.get("agreementId") in hidden and e.get("id")}
    hidden_docs = {d for a in gone for d in a.get("doc_ids") or []}
    hidden_files = {a.get("file") for a in gone if a.get("file")}
    kept_docs = {d for a in keep for d in a.get("doc_ids") or []}
    out = {}
    for k, v in data.items():
        if k == "agreements":
            out[k] = keep
        elif k == "documents":
            out[k] = [d for d in v if d.get("id") not in hidden_docs or d.get("id") in kept_docs]
        elif k in BY_AGREEMENT:
            out[k] = [r for r in v if r.get("agreementId") not in hidden and r.get("id") not in hidden_events]
        elif k == "counterparties":
            cps = []
            for c in v:
                ags = [i for i in c.get("agreements") or [] if i not in hidden]
                if not ags:
                    continue
                by = {}
                for a in keep:
                    if a["id"] in ags and (a.get("value") or {}).get("in_portfolio"):
                        for cur, n in ((a.get("value") or {}).get("annual_by_currency") or {}).items():
                            by[cur] = by.get(cur, 0) + n
                cps.append(dict(c, agreements=ags, annual_by_currency=money.tidy(by)))
            out[k] = cps
        elif k in ("catalog", "key_clause_labels", "meta"):
            out[k] = v
        else:
            out[k] = _scrub(v, hidden, hidden_events)
    meta = dict(out.get("meta") or {})
    meta["audience"] = RESTRICTED
    if isinstance(meta.get("files_scanned"), int):
        meta["files_scanned"] = max(0, meta["files_scanned"] - len(hidden_docs - kept_docs))
    out["meta"] = meta
    _assert_clean(out, gone, keep, hidden_docs - kept_docs, hidden_files)
    return out


def _assert_clean(out, gone, keep, docs, files):
    """בדיקת בטחון אחרונה: אף מזהה, מספר, קובץ, מסמך או גיבוב של הסכם מוסתר לא נשאר בנתונים המוטמעים."""
    blob = json.dumps(out, ensure_ascii=False)
    kept_titles = {a.get("title") for a in keep}
    kept_cps = {a.get("counterparty") for a in keep}
    kept_files = {a.get("file") for a in keep}
    tokens = set()
    for a in gone:
        tokens |= {a.get("id"), a.get("number")}
        if a.get("file") not in kept_files:
            tokens.add(a.get("file"))
        if a.get("title") not in kept_titles:
            tokens.add(a.get("title"))
        if a.get("counterparty") not in kept_cps:
            tokens.add(a.get("counterparty"))
    tokens |= set(docs) | (set(files) - kept_files)
    tokens.discard(None)
    tokens.discard("")
    left = sorted(tk for tk in tokens if isinstance(tk, str) and tk in blob)
    if left:
        raise AudienceError("נשאר זכר להסכם מוסתר בנתונים המוטמעים (%d ערכים). הבנייה נעצרה" % len(left))


def build(data_path, template_path, out_path, audience=FULL, hide_ids=(), hide_types=()):
    folder = os.path.dirname(os.path.abspath(out_path))
    os.makedirs(folder, exist_ok=True)
    with open(data_path, encoding="utf-8-sig") as f:
        data = json.load(f)
    if audience == RESTRICTED:
        data = restrict(data, hide_ids, hide_types)
    elif audience != FULL:
        raise AudienceError("קהל לא מוכר: %r" % (audience,))
    elif hide_ids or hide_types:
        raise AudienceError("הסתרת הסכמים מחייבת --audience restricted")
    with open(template_path, encoding="utf-8") as f:
        tpl = f.read()
    if "__DATA__" not in tpl:
        raise ValueError("המציין __DATA__ לא נמצא בתבנית")
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(tpl.replace("__DATA__", payload))
