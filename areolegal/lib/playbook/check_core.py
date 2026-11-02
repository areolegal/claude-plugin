# -*- coding: utf-8 -*-
"""playbook/check_core.py: בדיקה קצרה של הפלייבוק שבשימוש (playbook-core.json), לכל סוכן שמחיל פלייבוק.

    from playbook.check_core import core_problems
    for level, message in core_problems(core, counterparty_kind="public_body", lang="en"):
        ...

core_problems(core, counterparty_kind=None, lang="he") -> [(level, message)]. level: "warn" (כדאי לבדוק לפני שמסתמכים)
או "info" (מצב, לא תקלה). ההודעות בקול של Areo (areo-voice.md), בעברית או באנגלית. הבדיקה מזהירה ואינה עוצרת, אינה
זורקת חריגה, אינה צריכה את ההסכמים, ואינה כותבת קובץ. היא כוללת את הבדיקה המקומית של playbook_check.py (עמדות חסרות,
מקום ריק בנוסח המועדף, נושא כפול, סוג צד שכנגד שהפלייבוק לא נבנה מולו, טיוטה), ואת תוצאת הבדיקות של הפלייבוק עצמו
שהבונה כתב לגרעין (core["validity"], playbook/validity.py). כללי לכל סוג הסכם, לכל דין ולכל סוג חברה.
"""
import re

try:
    from playbook.validity import playbook_warnings
except ImportError:  # pragma: no cover
    playbook_warnings = None

PLACEHOLDER = re.compile(r"\[[^\[\]\n]{1,60}\]")
TXT = {
    "he": {"no_clauses": "בפלייבוק אין עמדות.", "no_family": "בפלייבוק לא נרשם סוג ההסכם.",
           "no_role": "בפלייבוק לא נרשם הצד של החברה בהסכם.", "no_position": "לנושא \"%s\" אין עמדה.",
           "dup": "אותו נושא מופיע פעמיים: %s.", "placeholder": "בנוסח המועדף של \"%s\" נשאר מקום ריק להשלמה: %s.",
           "kind": "הפלייבוק נבנה מהסכמים עם צד מסוג אחר (%s), ולא עם %s. כדאי לבדוק כל עמדה לפני שמחילים אותה.",
           "not_observed": "בהסכמים שמהם נבנה הפלייבוק לא היה צד מסוג %s. כדאי לבדוק כל עמדה לפני שמחילים אותה.",
           "draft": "הפלייבוק הוא עדיין טיוטת מדיניות, שמחכה לאישור שלכם."},
    "en": {"no_clauses": "The playbook has no positions.", "no_family": "The playbook does not record the agreement type.",
           "no_role": "The playbook does not record the company's side.", "no_position": "The topic \"%s\" has no position.",
           "dup": "The same topic appears twice: %s.",
           "placeholder": "The preferred wording of \"%s\" still has a blank to fill in: %s.",
           "kind": "The playbook was built from agreements with a different kind of counterparty (%s), not %s. Check "
                   "each position before applying it.",
           "not_observed": "None of the agreements behind the playbook was with a %s. Check each position before "
                           "applying it.",
           "draft": "The playbook is still a draft policy, awaiting your approval."},
}


def _s(v):
    return str(v or "").strip()


def _lang(lang):
    return "en" if _s(lang).lower().startswith("en") else "he"


def core_problems(core, counterparty_kind=None, lang="he"):
    """הערות על הפלייבוק שבשימוש, בשפת הלקוח: [(רמה, הודעה)]. רשימה ריקה כשאין מה לומר."""
    try:
        return _problems(core, counterparty_kind, _lang(lang))
    except Exception:  # noqa: BLE001  אזהרה אינה מפילה את הסוכן שקרא לה
        return []


def _problems(core, counterparty_kind, lang):
    t = TXT[lang]
    if not isinstance(core, dict):
        return [("warn", t["no_clauses"])]
    out = []
    clauses = core.get("clauses") or core.get("rules") or []
    if not clauses:
        out.append(("warn", t["no_clauses"]))
    if not (_s(core.get("family_id")) or core.get("contract_families")):
        out.append(("warn", t["no_family"]))
    if not (_s(core.get("company_role_code")) or _s(core.get("company_role"))):
        out.append(("warn", t["no_role"]))
    seen = {}
    for c in clauses:
        if not isinstance(c, dict):
            continue
        title = _s(c.get("title") or c.get("clause_issue") or c.get("id"))
        cid = _s(c.get("id"))
        if cid:
            seen[cid] = seen.get(cid, 0) + 1
        g = c.get("green") or {}
        pos = _s(g.get("position")) or _s(c.get("preferred_wording")) or _s((c.get("yellow") or {}).get("position")) \
            or _s((c.get("red") or {}).get("position")) or _s(c.get("red_line"))
        if not pos:
            out.append(("warn", t["no_position"] % title))
        hit = PLACEHOLDER.search(_s(g.get("preferred_wording")) or _s(c.get("preferred_wording")))
        if hit:
            out.append(("warn", t["placeholder"] % (title, hit.group(0))))
    dups = [k for k, n in seen.items() if n > 1]
    if dups:
        out.append(("warn", t["dup"] % ", ".join(dups[:5])))
    app = core.get("applicability") or {}
    kinds = [_s(k) for k in (app.get("counterparty_kinds") or []) if _s(k)]
    not_obs = [_s(k.get("kind") if isinstance(k, dict) else k) for k in (app.get("not_observed") or [])]
    ck = _s(counterparty_kind)
    if ck and ck in not_obs:
        out.append(("warn", t["not_observed"] % ck))
    elif ck and kinds and ck not in kinds:
        out.append(("warn", t["kind"] % (", ".join(kinds), ck)))
    if playbook_warnings is not None:
        out += [("warn", line) for line in playbook_warnings(None, core=core, lang=lang)]
    if _s(core.get("playbook_status")).lower() in ("draft", "partiallyapproved"):
        out.append(("info", t["draft"]))
    return out
