# -*- coding: utf-8 -*-
"""בדיקה קצרה של הפלייבוק שבשימוש (playbook-core.json), לפני שמנסחים או מכינים שיחה לפיו.

הבדיקה מזהירה ואינה עוצרת: הפלייבוק הוא של הלקוח, וההחלטה אם לעבוד לפיו שלו. כשהספרייה המשותפת ניתנת לייבוא
(AREO_RT/lib, הבדיקה של סוכן הפלייבוק), משתמשים בה; אחרת בבדיקה המקומית המינימלית שכאן, כי סקריפט שרץ מהתוסף
אינו יכול לייבא את הספרייה.

    python3 playbook_check.py --core "<playbook-core.json>" [--counterparty-kind <סוג הצד שכנגד>] [--lang he|en]
        [--document "<ההסכם שעל השולחן>" --profile "<פרופיל-לקוח.json>"]

הצד שלנו: עם --document ו---profile, התפקיד שהפלייבוק נותן לחברה נבדק מול התפקיד שהמסמך עצמו מגדיר לה (השם שלה
בבלוק הצדדים, והכינוי שמוגדר לה: (להלן: "הספק"), (the "Customer")). כשהם סותרים, הצד נשאר פתוח: הלקוח נשאל,
ואין עבודה לפי הפלייבוק עד התשובה.

קוד יציאה: 0 כשהקובץ נקרא (גם כשיש אזהרות); 3 כשהצד בפלייבוק סותר את הצד במסמך; 2 כשקובץ אינו נקרא.
הספרייה נמצאת דרך areo_rt.py (AREO_RT, אחר כך <temp>/areo-runtime). אזהרות התקינות של הפלייבוק מגיעות מ-
playbook.validity.playbook_warnings, מ-core["validity"] שהבונה כתב לגרעין.
"""
import argparse
import io
import json
import os
import re
import sys

try:                                   # פלט עברי במסוף של Windows
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):   # pragma: no cover
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from areo_rt import ensure_lib  # noqa: E402
ensure_lib()

PLACEHOLDER = re.compile(r"\[[^\[\]\n]{1,60}\]")
TXT = {
    "he": {"no_clauses": "בפלייבוק אין עמדות.", "no_family": "בפלייבוק לא נרשם סוג ההסכם.",
           "no_role": "בפלייבוק לא נרשם הצד של החברה בהסכם.", "no_position": "לנושא \"%s\" אין עמדה.",
           "dup": "אותו נושא מופיע פעמיים: %s.", "placeholder": "בנוסח המועדף של \"%s\" נשאר מקום ריק להשלמה: %s.",
           "kind": "הפלייבוק נבנה מהסכמים עם צד מסוג אחר (%s), ולא עם %s. כדאי לבדוק כל עמדה לפני שמחילים אותה.",
           "draft": "הפלייבוק הוא עדיין טיוטת מדיניות, שמחכה לאישור שלכם.",
           "invalid": "הפלייבוק לא עבר את הבדיקות שלו. כדאי שעורך דין יעבור עליו לפני שמסתמכים עליו.",
           "head": "בדיקת הפלייבוק: %d הערות.", "ok": "בדיקת הפלייבוק: אין הערות.",
           "side": "הצד לא ברור: לפי הפלייבוק החברה היא %s, ובמסמך היא מוגדרת \"%s\". הצד נשאר פתוח עד שתאשרו מה "
                   "הצד שלכם בהסכם הזה.", "gives": "הצד שנותן את השירות, הנכס או המידע",
           "gets": "הצד שמקבל את השירות, הנכס או המידע", "one": "בדיקת הפלייבוק: הערה אחת."},
    "en": {"no_clauses": "The playbook has no positions.", "no_family": "The playbook does not record the agreement type.",
           "no_role": "The playbook does not record the company's side.", "no_position": "The topic \"%s\" has no position.",
           "dup": "The same topic appears twice: %s.",
           "placeholder": "The preferred wording of \"%s\" still has a blank to fill in: %s.",
           "kind": "The playbook was built from agreements with a different kind of counterparty (%s), not %s. Check "
                   "each position before applying it.",
           "draft": "The playbook is still a draft policy, awaiting your approval.",
           "invalid": "The playbook did not pass its own checks. A lawyer should review it before you rely on it.",
           "head": "Playbook check: %d notes.", "ok": "Playbook check: no notes.",
           "side": "Your side is unclear: the playbook makes the company %s, but the document defines it as \"%s\". "
                   "Your side stays open until you confirm it for this agreement.",
           "gives": "the side that provides the service, asset or information",
           "gets": "the side that receives the service, asset or information", "one": "Playbook check: 1 note."},
}


def _s(v):
    return str(v or "").strip()


def local_problems(core, counterparty_kind=None, lang="he"):
    """הערות על הפלייבוק, בשפת הלקוח: [(רמה, הודעה)]. רמה: warn או info."""
    t = TXT["en" if str(lang)[:2] == "en" else "he"]
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
        pref = _s(g.get("preferred_wording")) or _s(c.get("preferred_wording"))
        hit = PLACEHOLDER.search(pref)
        if hit:
            out.append(("warn", t["placeholder"] % (title, hit.group(0))))
    dups = [k for k, n in seen.items() if n > 1]
    if dups:
        out.append(("warn", t["dup"] % ", ".join(dups[:5])))
    kinds = [_s(k) for k in ((core.get("applicability") or {}).get("counterparty_kinds") or []) if _s(k)]
    if counterparty_kind and kinds and _s(counterparty_kind) not in kinds:
        out.append(("warn", t["kind"] % (", ".join(kinds), counterparty_kind)))
    if _s(core.get("playbook_status")).lower() in ("draft", "partiallyapproved"):
        out.append(("info", t["draft"]))
    return out


# הצד של החברה מושווה כטקסט חופשי: תפקיד החברה בפלייבוק (company_role_code) מול הכינוי שהמסמך מגדיר לה. אין רשימת
# תפקידים ואין חלוקה ל"צד נותן" ו"צד מקבל": כינוי שונה בשפה אחרת אינו נבדק ("לא ניתן להשוות"), ושונה באותה שפה
# הוא אי-התאמה שנשאלת.
DEFINED = re.compile(r'\(\s*(?:להלן\s*[:\-]?\s*|hereinafter\s*(?:referred\s+to\s+as\s*)?|the\s+)?["“״\']'
                     r'([^"”״\'\)]{2,40})["”״\']\s*\)', re.I)


def doc_text(path):
    """הטקסט של המסמך: Word, PDF (pymupdf) או טקסט. ריק כשאינו נקרא."""
    low = (path or "").lower()
    try:
        with open(path, "rb") as fh:
            head = fh.read(5)
    except OSError:
        return ""
    if head.startswith(b"%PDF"):
        try:
            try:
                import pymupdf as fitz
            except ImportError:
                import fitz
            with fitz.open(path) as d:
                return "\n".join(pg.get_text() for pg in d)
        except Exception:  # noqa: BLE001
            return ""
    if head.startswith(b"PK"):
        import zipfile
        try:
            with zipfile.ZipFile(path) as z:
                xml = z.read("word/document.xml").decode("utf-8", "ignore")
        except Exception:  # noqa: BLE001
            return ""
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", xml.replace("</w:p>", "\n")))
    if low.endswith((".txt", ".md")):
        return io.open(path, encoding="utf-8", errors="ignore").read()
    return ""


def _key(v):
    t = re.sub(r"[\s_\-]+", " ", _s(v).strip().lower()).strip(" .,:;\"'״")
    if t.startswith("ה") and len(t) > 3:
        t = t[1:]
    return t


def side_of_role(code):
    return _key(code) or None


def side_in_document(text, names):
    """(הכינוי המנורמל, הכינוי) שהמסמך מגדיר לחברה: הכינוי שבסוגריים אחרי שמה בבלוק הצדדים. (None, None) כשלא נמצא."""
    head = (text or "")[:6000]
    for n in [x for x in names if x and len(x) > 2]:
        for m in re.finditer(re.escape(n), head, re.I):
            win = head[m.end():m.end() + 260]
            d = DEFINED.search(win)
            if d:
                term = d.group(1).strip()
                return _key(term), term
    return None, None


def side_problem(core, text, names, lang="he"):
    """הודעה כשתפקיד החברה בפלייבוק שונה מהכינוי שהמסמך מגדיר לה (באותה שפה), אחרת None."""
    t = TXT["en" if str(lang)[:2] == "en" else "he"]
    role = _s(core.get("company_role_code")) or next((_s(f.get("company_role_code")) for f in core.get("contract_families")
                                                     or [] if isinstance(f, dict)), "")
    want = side_of_role(role)
    got, term = side_in_document(text, names)
    he = lambda v: bool(re.search(r"[֐-׿]", v or ""))  # noqa: E731
    if want and got and want != got and he(want) == he(got) and "mutual" not in (want, got):
        return t["side"] % ('"%s"' % role, term)
    return None


def validity_lines(core, lang="he"):
    """אזהרות התקינות של הפלייבוק (playbook.validity.playbook_warnings), או הודעה כללית אחת כשהספרייה חסרה."""
    try:
        from playbook.validity import playbook_warnings
        return [_s(x) for x in playbook_warnings(core=core, lang=lang) if _s(x)]
    except Exception:  # noqa: BLE001  אין ספרייה: הודעה כללית כשהגרעין עצמו אומר שאינו תקין
        v = core.get("validity") if isinstance(core, dict) else None
        if isinstance(v, dict) and _s(v.get("status")).lower() == "invalid":
            return [TXT["en" if str(lang)[:2] == "en" else "he"]["invalid"]]
        return []


def problems(core, counterparty_kind=None, lang="he"):
    """הבדיקה של הספרייה המשותפת כשהיא קיימת (playbook.check_core.core_problems), אחרת המקומית; ואחריה אזהרות
    התקינות של הפלייבוק (validity.playbook_warnings)."""
    res = None
    try:
        from playbook.check_core import core_problems  # noqa: E402
        r = core_problems(core, counterparty_kind=counterparty_kind, lang=lang)
        if isinstance(r, list):
            res = [(x[0], x[1]) if isinstance(x, (list, tuple)) else ("warn", _s(x)) for x in r]
    except Exception:  # noqa: BLE001  אין בדיקה משותפת: הבדיקה המקומית
        res = None
    if res is None:
        res = local_problems(core, counterparty_kind, lang)
    known = {m for _, m in res}
    res += [("warn", m) for m in validity_lines(core, lang) if m not in known]
    return res


def main():
    ap = argparse.ArgumentParser(description="בדיקה קצרה של playbook-core.json לפני שמנסחים או מכינים שיחה לפיו")
    ap.add_argument("--core", required=True, help="playbook-core.json")
    ap.add_argument("--counterparty-kind", help="סוג הצד שכנגד בעסקה (למשל גוף ציבורי, חברה זרה)")
    ap.add_argument("--lang", choices=("he", "en"), default="he")
    ap.add_argument("--document", help="ההסכם שעל השולחן (Word, PDF או טקסט): בדיקת הצד שלנו מול הצדדים במסמך")
    ap.add_argument("--profile", help="פרופיל-לקוח.json: שם החברה (בעברית ובאנגלית) לאיתור שלה בבלוק הצדדים")
    a = ap.parse_args()
    try:
        core = json.load(io.open(a.core, encoding="utf-8-sig"))
    except (OSError, ValueError) as e:
        print(("The playbook could not be read (%s)." if a.lang == "en" else "לא הצלחנו לקרוא את הפלייבוק (%s).")
              % type(e).__name__)
        sys.exit(2)
    found = problems(core, a.counterparty_kind, a.lang)
    side = None
    if a.document:
        names = []
        if a.profile:
            try:
                prof = json.load(io.open(a.profile, encoding="utf-8-sig"))
                names = [prof.get("organization_name"), prof.get("organization_name_en")] + \
                    list((prof.get("organization_aliases") or []))
            except (OSError, ValueError):
                names = []
        text = doc_text(a.document)
        if not text.strip():
            print(("The document could not be read: %s" if a.lang == "en" else "לא הצלחנו לקרוא את המסמך: %s")
                  % os.path.basename(a.document))
            sys.exit(2)
        side = side_problem(core, text, [str(x) for x in names if x], a.lang)
        if side:
            found.insert(0, ("side", side))
    t = TXT[a.lang]
    warns = [m for lvl, m in found if lvl in ("warn", "side")]
    print((t["one"] if len(warns) == 1 else t["head"] % len(warns)) if warns else t["ok"])
    for lvl, m in found:
        print("  " + m)
    sys.exit(3 if side else 0)


if __name__ == "__main__":
    main()
