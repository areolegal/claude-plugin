#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""הכלים של הסבב: מנת השאלות, "לאישורך", נקודות לשיחה, הרשימה לפני חתימה ומידתיות.

חמשת הכלים האלה הם קוד הייחוס של ענבל (`areolegal/lib/orchestrator`, הערות
הנושא ונותן 4.8 ו-4.9, שינויים 70, 71, 82, 83, 85 ו-89). עד עכשיו המודל עשה
את כולם בעצמו, וכל הרצה יצאה קצת אחרת: "נדרשת הכרעתך" בלי מספר מצב, שאלה
שנשאלה פעמיים, "טעון אישור מנכ"ל" בטבלה שאין בה שרשרת אישורים, ספירת בקשות
שכללה כותרות. כאן הם רצים בקוד, בכל סבב, באותו אופן.

* `questions` - מנת השאלות האחת שלפני ההכרעות. "נדרשת הכרעתך" רק בתשעת
  המצבים, חוסם משלוח ראשון, ושאלה שכבר נשאלה אינה נשאלת שוב.
* `review` - טבלת "לאישורך" בסיכום הפנימי: סעיף, מה הוכרע, תווית מקור. אין בה
  עמודת מאשר, ונושא ציות אינו בה.
* `talking-points` - נקודות לשיחה, עד שבע: חיכוך צפוי, נסיגה אחרונה, ויתורים
  מכוונים ומה שנשאר לשיחה. פנימי בלבד.
* `signing` - הרשימה לפני חתימה, מתוצאת השער ומקובץ המצב. passed רק כשאין אף
  פריט פתוח.
* `proportionality` - ספירת הבקשות (R1 עד R3 ו-N1, בלי כותרות) מול רשימת
  המאבק. מעליה: "נדרשת הכרעתך" (מצב 4), עם שלושה ויתורים מוצעים.
* `clean-copy` - העותק הנקי לחתימה (שינוי 43): כל השינויים מתקבלים, ההערות
  והסימונים יוצאים, ו"עקוב אחר שינויים" כבוי. רק אחרי שהרשימה לפני חתימה
  עברה, ורק כשהטקסט שלו זהה לנוסח המוסכם מילה במילה.

עם `--deal`, התוצאה נכתבת גם לקובץ המצב של העסקה, דרך אותה בדיקה של
`negotiation_state.py`: קובץ שאינו תקין אינו נכתב במקום הקובץ החי.

קוד יציאה: **0** תקין, **3** יש ממצא (פריט פתוח לפני חתימה, הפרה בטבלה,
ספירה מעל רשימת המאבק שדורשת שאלה, או עותק נקי שאינו זהה לנוסח המוסכם),
**2** קלט חסר, **1** נתיב פלט שסורב.
"""
import argparse
import hashlib
import json
import os
import re
import sys

import areo_lib  # noqa: F401  מוסיף את areolegal/lib לנתיב הייבוא

from orchestrator import proportionality as P  # noqa: E402
from orchestrator import question_batch as QB  # noqa: E402
from orchestrator import review_table as RT  # noqa: E402
from orchestrator import signing_checklist as SC  # noqa: E402
from orchestrator import state_builder as SB  # noqa: E402
from orchestrator import talking_points as TP  # noqa: E402
import common.docx_tracked as dt  # noqa: E402
from common.cli import OutputRefused, guard_out  # noqa: E402
from lxml import etree  # noqa: E402

LIVE = "negotiation_state.json"
MAX_TALKING_POINTS = 7


def load(path, what, required=True):
    if not path:
        if required:
            print("חסר %s" % what)
            raise SystemExit(2)
        return None
    if not os.path.exists(path):
        print("%s אינו קיים: %s" % (what, path))
        raise SystemExit(2)
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def decisions_of(path):
    dec = load(path, "קובץ ההכרעות")
    return dec.get("decisions", []) if isinstance(dec, dict) else dec


def state_of(deal):
    if not deal:
        return None
    p = os.path.join(deal, LIVE)
    return load(p, "קובץ המצב") if os.path.exists(p) else None


def save_state(deal, state):
    """אותו כלל כמו negotiation_state.py: קובץ לא תקין אינו מחליף את החי."""
    errors = SB.validate_state(state)
    if errors:
        rej = os.path.join(deal, "negotiation_state.rejected.json")
        with open(rej, "w", encoding="utf-8") as fh:
            json.dump(state, fh, ensure_ascii=False, indent=1)
        print("קובץ המצב לא עודכן (%d שגיאות), והגרסה שנדחתה ב-%s:" % (len(errors), rej))
        for e in errors[:10]:
            print("  [%s] %s" % (e.get("code"), e.get("message")))
        return False
    state["meta"]["last_updated"] = SB.now_iso()
    with open(os.path.join(deal, LIVE), "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=1)
    print("קובץ המצב עודכן: %s" % os.path.join(deal, LIVE))
    return True


def cmd_questions(a):
    items = load(a.items, "רשימת הפריטים")
    st = state_of(a.deal)
    asked = set(a.asked_before or ())
    if st:
        for b in st.get("question_batches") or ():
            asked |= set(b.get("keys") or ())
    try:
        b = QB.build_batch(items, no_consideration=a.no_consideration, asked_before=asked,
                           max_questions=a.max, status_line=a.status_line)
    except ValueError as exc:
        print("המנה לא נבנתה: %s" % exc)
        return 2
    print(b["text"])
    for s in b["skipped"]:
        print("  (לא נשאלה: %s, %s)" % (s["key"], s["why"]))
    if st is not None:
        st.setdefault("question_batches", []).append({
            "round": st["meta"].get("round_number"), "asked_at": SB.now_iso(),
            "keys": [q.get("key") or q.get("text") for q in b["questions"]]})
        if not save_state(a.deal, st):
            return 3
    return 0


def cmd_review(a):
    decisions = decisions_of(a.decisions)
    st = state_of(a.deal)
    nm = (st or {}).get("numbering_map") or {}
    conc = load(a.concessions, "הוויתורים", required=False) or (st or {}).get("deliberate_concessions") or []
    rows = RT.build_review_table(decisions, numbering_map=nm, concessions=conc)
    print(RT.render_markdown(rows))
    # התווית מצטטת את תשובת המשתמש מילה במילה ('הכרעתך ("מאשרים...")'), והבדיקה
    # אוסרת את המילה "מאשר" כסימן לשרשרת אישורים. ציטוט של המשתמש אינו שרשרת
    # אישורים, ולכן הוא מוסר מהטקסט הנבדק בלבד; כל שאר הטבלה נבדקת כרגיל
    masked = [dict(r, **{"תווית מקור": re.sub(r'\("[^"]*"\)', '("…")', str(r.get("תווית מקור", "")))})
              for r in rows]
    bad = RT.check_review_table(masked, decisions)
    for v in bad:
        print("  הפרה בטבלה: %s" % v)
    if st is not None:
        st["review_table"] = rows
        if not save_state(a.deal, st):
            return 3
    return 3 if bad else 0


def cmd_talking_points(a):
    decisions = decisions_of(a.decisions)
    st = state_of(a.deal)
    conc = load(a.concessions, "הוויתורים", required=False) or (st or {}).get("deliberate_concessions") or []
    pts = TP.build_talking_points(decisions, conc)
    if len(pts) > MAX_TALKING_POINTS:
        print("  %d נקודות; בסיכום מוצגות שבע הראשונות" % len(pts))
    for n, p in enumerate(pts[:MAX_TALKING_POINTS], 1):
        print("%d. %s" % (n, p["text"]))
    if st is not None:
        # נקודה שנסגרה בשיחה בסבב קודם נשארת כמו שהיא, עם התוצאה שלה
        closed = [p for p in st.get("talking_points") or () if p.get("status") == "closed_in_call"]
        st["talking_points"] = closed + pts
        if not save_state(a.deal, st):
            return 3
    return 0


def cmd_signing(a):
    gate = load(a.gate, "דוח השער")
    st = state_of(a.deal)
    res = SC.build_signing_checklist(gate.get("info") or {}, state=st,
                                     profile=load(a.profile, "הפרופיל", required=False),
                                     register=load(a.register, "המרשם", required=False),
                                     decisions=decisions_of(a.decisions) if a.decisions else None)
    for c in res["checks"]:
        detail = c.get("detail") or c.get("text") or c.get("clause_id") or c.get("fix_id") or ""
        print("  [%s] %s %s" % ("פתוח" if c["status"] == "open" else "סגור", c["item"], detail))
    print("עובר: %s" % ("כן" if res["passed"] else "לא. העותק לחתימה אינו מופק"))
    if st is not None:
        sc = st.get("signing_checklist") or {}
        sc.update(res)
        st["signing_checklist"] = sc
        if not save_state(a.deal, st):
            return 3
    return 0 if res["passed"] else 3


def cmd_proportionality(a):
    decisions = decisions_of(a.decisions)
    res = P.assess(decisions, a.fight_list, value_band=a.value_band, value_text=a.value_text,
                   user_choice=a.user_choice, answer_kind=a.answer_kind)
    print(res["summary_line"])
    if res["question_required"]:
        print('נדרשת הכרעתך (מצב 4): יותר בקשות (%d) מרשימת המאבק (%d).'
              % (res["counts"]["asks"], a.fight_list))
        print("  ויתורים מוצעים: %s" % ", ".join(res["proposed_concessions"] or ["אין"]))
        print("  אפשרויות: %s" % " | ".join(res.get("options") or ()))
    for v in res["violations"]:
        print("  הפרה: %s" % v)
    return 3 if res["question_required"] or res["violations"] else 0


CLEAN_PARTS = re.compile(r"^word/(document|header\d*|footer\d*|footnotes|endnotes)\.xml$")
COMMENT_PARTS = re.compile(r"^word/comments(Extended|Ids|Extensible)?\.xml$")


def _merge_deleted_marks(root):
    """פסקה שסימן הפסקה שלה נמחק מתמזגת עם הפסקה הבאה, כמו "קבל הכול" ב-Word."""
    paras = dt.body_paragraphs(root)
    for i, p in enumerate(paras):
        rpr = p.find(dt.W + "pPr/" + dt.W + "rPr")
        if rpr is None or rpr.find(dt.W + "del") is None:
            continue
        if i + 1 >= len(paras):
            continue
        nxt = paras[i + 1]
        at = 1 if nxt.find(dt.W + "pPr") is not None else 0
        for child in [c for c in p if c.tag != dt.W + "pPr"]:
            nxt.insert(at, child)
            at += 1
        p.getparent().remove(p)


def _clean_part(root):
    """קבלת כל השינויים בחלק אחד: מחיקות יוצאות, הוספות נשארות בלי העטיפה."""
    if root.find(dt.W + "body") is not None:
        _merge_deleted_marks(root)
    for el in list(root.iter()):
        if not isinstance(el.tag, str):
            continue
        name = dt.local(el.tag)
        parent = el.getparent()
        if parent is None:
            continue
        if name in ("del", "moveFrom") and dt.local(parent.tag) != "rPr":
            parent.remove(el)
        elif name.endswith("PrChange") or name in ("commentRangeStart", "commentRangeEnd",
                                                     "moveFromRangeStart", "moveFromRangeEnd",
                                                     "moveToRangeStart", "moveToRangeEnd"):
            parent.remove(el)
        elif name in ("del", "ins", "moveTo") and dt.local(parent.tag) == "rPr":
            parent.remove(el)  # סימון שינוי על סימן הפסקה
    for el in list(root.iter(dt.W + "ins", dt.W + "moveTo")):
        parent = el.getparent()
        if parent is None:
            continue
        i = parent.index(el)
        for child in list(el):
            parent.insert(i, child)
            i += 1
        parent.remove(el)
    for ref in list(root.iter(dt.W + "commentReference")):
        run = ref.getparent()
        if run is not None and run.getparent() is not None:
            run.getparent().remove(run)
    return root


def cmd_clean_copy(a):
    st = state_of(a.deal)
    if st is None:
        print("אין קובץ מצב בתיקיית העסקה, ולכן אין רשימה לפני חתימה שעברה")
        return 2
    if not (st.get("signing_checklist") or {}).get("passed"):
        print("הרשימה לפני חתימה לא עברה (round_tools.py signing). העותק לחתימה אינו מופק.")
        return 3
    if not os.path.exists(a.agreed):
        print("הנוסח המוסכם אינו קיים: %s" % a.agreed)
        return 2
    try:
        out = guard_out(a.out, inputs=[a.agreed])
    except OutputRefused as exc:
        print("סירוב: %s" % exc)
        return 1
    # השכבה הפנימית (הכותרת והבועות של "פנימי") יוצאת קודם, גם אם נמסר קובץ העבודה
    parts = dt.read_package(dt.strip_internal(a.agreed))
    drop = {n for n in parts if COMMENT_PARTS.match(n)}
    for name in list(parts):
        if name in drop:
            del parts[name]
        elif CLEAN_PARTS.match(name):
            root = etree.fromstring(parts[name])
            parts[name] = etree.tostring(_clean_part(root), xml_declaration=True,
                                         encoding="UTF-8", standalone=True)
        elif name == "word/settings.xml":
            root = etree.fromstring(parts[name])
            for el in list(root.iter(dt.W + "trackRevisions")):
                el.getparent().remove(el)
            parts[name] = etree.tostring(root, xml_declaration=True, encoding="UTF-8",
                                         standalone=True)
        elif name == "word/_rels/document.xml.rels":
            txt = parts[name].decode("utf-8")
            txt = re.sub(r'<Relationship [^>]*Target="comments[^"]*"[^>]*/>', "", txt)
            parts[name] = txt.encode("utf-8")
        elif name == "[Content_Types].xml":
            txt = parts[name].decode("utf-8")
            txt = re.sub(r'<Override [^>]*PartName="/word/comments[^"]*"[^>]*/>', "", txt)
            parts[name] = txt.encode("utf-8")
    with open(out, "wb") as fh:
        fh.write(dt.write_package(parts))

    # הבדיקה: הטקסט של העותק הנקי זהה ל"קבל הכול" של הנוסח המוסכם, ואין בו סימון
    left = dt.read_package(out)
    marks = any(re.search(r"<w:(ins|del|moveFrom|moveTo)\b", left[n].decode("utf-8", "ignore"))
                for n in left if CLEAN_PARTS.match(n))
    if dt.accept_all(a.agreed) != dt.received_paragraphs(out) or marks:
        os.remove(out)
        print("העותק הנקי אינו זהה לנוסח המוסכם%s, ולא נשמר." % (" (נשאר בו סימון)" if marks else ""))
        return 3
    with open(a.agreed, "rb") as fh:
        sha = hashlib.sha256(fh.read()).hexdigest()
    print("העותק לחתימה: %s" % out)
    sc = st.setdefault("signing_checklist", {})
    sc["agreed_version_sha256"] = sha
    sc["clean_copy_path"] = out
    if not save_state(a.deal, st):
        return 3
    return 0


def main(argv=None):
    sys.dont_write_bytecode = True
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    q = sub.add_parser("questions", help="מנת השאלות")
    q.add_argument("--items", required=True,
                   help="JSON: [{key, text, situation (1-9 או null), recommendation, options, "
                        "blocks_sending, kind}]")
    q.add_argument("--deal", help="תיקיית העסקה: שאלות שכבר נשאלו אינן נשאלות שוב")
    q.add_argument("--asked-before", action="append")
    q.add_argument("--no-consideration", action="store_true", help="הסכם בלי תמורה: בלי שאלת שווי")
    q.add_argument("--max", type=int, default=8)
    q.add_argument("--status-line", help="שורת המעמד שבראש המנה")

    r = sub.add_parser("review", help='טבלת "לאישורך"')
    r.add_argument("--decisions", required=True)
    r.add_argument("--deal")
    r.add_argument("--concessions")

    t = sub.add_parser("talking-points", help="נקודות לשיחה")
    t.add_argument("--decisions", required=True)
    t.add_argument("--deal")
    t.add_argument("--concessions")

    s = sub.add_parser("signing", help="הרשימה לפני חתימה")
    s.add_argument("--gate", required=True, help="הדוח של qa_gate.py")
    s.add_argument("--deal")
    s.add_argument("--profile")
    s.add_argument("--register")
    s.add_argument("--decisions")

    p = sub.add_parser("proportionality", help="מידתיות")
    p.add_argument("--decisions", required=True)
    p.add_argument("--fight-list", type=int, required=True, help="מספר הפריטים ברשימת המאבק")
    p.add_argument("--value-band", default="לא ידוע", help="קטנה / בינונית / גדולה / לא ידוע")
    p.add_argument("--value-text", default="<שווי>", help="השווי במילים, לשורת הסיכום")
    p.add_argument("--user-choice", choices=("send_as_is", "concede_three", "focused", "full_response",
                                             "unanswered"))
    p.add_argument("--answer-kind", choices=("explicit", "delegated"))

    c = sub.add_parser("clean-copy", help="העותק הנקי לחתימה")
    c.add_argument("--agreed", required=True, help="הנוסח המוסכם, עם השינויים שעוד לא התקבלו")
    c.add_argument("--out", required=True, help="העותק לחתימה (docx)")
    c.add_argument("--deal", required=True, help="תיקיית העסקה: הרשימה לפני חתימה צריכה לעבור")

    a = ap.parse_args(argv)
    return {"questions": cmd_questions, "review": cmd_review, "talking-points": cmd_talking_points,
            "signing": cmd_signing, "proportionality": cmd_proportionality,
            "clean-copy": cmd_clean_copy}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
