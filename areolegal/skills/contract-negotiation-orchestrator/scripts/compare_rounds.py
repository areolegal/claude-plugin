#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""השוואת סבב: מה קרה לכל הצעה שלנו, ומה הם שינו בשקט.

`phase3_iteration_management.md`, שלב א: **ההשוואה היא מילה במילה,
טקסט מול טקסט, ולא רשימת שינויים מול רשימת שינויים.** רשימת שינויים
מול רשימת שינויים מפספסת את הממצא החשוב ביותר, כי צד שכנגד שכיבה את
המעקב, או ש"קיבל" אצלו שינויים לפני השליחה, אינו מופיע באף רשימה.

כל הבדל מסווג לאחת מחמש הקבוצות של `last_round_changes`
(`negotiation_state_schema.md`):

| סיווג | מה קרה |
|---|---|
| `our_accepted` | הסימון שלנו נעלם, והנוסח שהצענו נשאר |
| `our_rejected` | הסימון שלנו נעלם, והנוסח חזר למה שהיה לפניו |
| `our_open` | ההצעה שלנו עוד מסומנת: לא קיבלו ולא דחו |
| `their_tracked` | שינוי חדש שלהם, במעקב |
| `their_silent` | הנוסח השתנה בלי סימון. הממצא החשוב ביותר |

**שלוש ההטלות שעליהן הכול נשען.** קובץ Word עם סימוני מעקב אינו טקסט
אחד אלא כמה, לפי מי מקבלים ומי דוחים. לכל פסקה בקובץ שחזר נגזרות:

* **מה הם פתחו בו** - מקבלים את הסימונים שלנו ודוחים את שלהם. זה אמור
  להיות, מילה במילה, מה ששלחנו. כל פער כאן הוא שינוי בלי מעקב.
* **מה הנוסח עכשיו** - מקבלים הכול.
* **האם הסימון שלנו עוד שם** - אם כן, ההצעה פתוחה ואין לגעת בה.

**ההצמדה היא לפי סעיף ונוסח, ולא לפי מיקום הפסקה**, כדי שפסקה שנוספה
לא תזיז את כל ההשוואה: קודם לפי מספר הסעיף שבתחילת הפסקה, ומה שנשאר
לפי קרבת נוסח.

    python3 scripts/compare_rounds.py --sent <מה שהחברה שלחה>.docx \\
        --received <מה שחזר>.docx --author "עו\"ד <שם>" \\
        --out Areo-נתונים/transactions/<id>/round-compare.json

קריאת ה-DOCX היא `areolegal/lib/common/docx_tracked.py` מקוד הייחוס.
ההטלות לפי מחבר והסיווג הם כאן.
"""
import copy
import difflib
import json
import re
import sys

import areo_lib  # noqa: F401  מוסיף את areolegal/lib לנתיב הייבוא

from common.cli import OutputRefused, guard_out, no_bytecode, parser  # noqa: E402
import common.docx_tracked as dt  # noqa: E402

W = dt.W
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
# מספר סעיף בתחילת פסקה: "4.", "4.1", "4.1.2", וגם "סעיף 4.1"
CLAUSE = re.compile(r"^\s*(?:סעיף\s+)?(\d+(?:\.\d+)*)\s*[.)\s]")
# קרבת נוסח שמעליה שתי פסקאות הן אותה פסקה שהשתנתה, ולא שתי פסקאות שונות
NEAR = 0.72


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[‎‏‪-‮]", "", s or "")).strip()


def clause_of(text):
    m = CLAUSE.match(norm(text))
    return m.group(1) if m else None


def project(para, accept_authors=None, reject_authors=None, accept_rest=True):
    """הטקסט של הפסקה כשמקבלים מחברים מסוימים ודוחים אחרים.

    accept_authors: מחברים שהסימון שלהם מתקבל (ins נשאר, del יוצא).
    reject_authors: מחברים שהסימון שלהם נדחה (ins יוצא, del חוזר).
    accept_rest:    מה עושים למחבר שאינו באף רשימה.
    """
    p = copy.deepcopy(para)
    acc = set(accept_authors or ())
    rej = set(reject_authors or ())

    def keeps(el):
        a = el.get(W + "author")
        if a in acc:
            return True
        if a in rej:
            return False
        return accept_rest

    for el in list(p.iter(W + "ins")):
        if el.getparent() is None:
            continue
        par = el.getparent()
        if keeps(el):
            for ch in list(el):
                par.insert(list(par).index(el), ch)
        par.remove(el)
    for el in list(p.iter(W + "del")):
        if el.getparent() is None:
            continue
        par = el.getparent()
        if keeps(el):
            par.remove(el)
            continue
        for ch in list(el):
            for node in ch.iter(W + "delText"):
                node.tag = W + "t"
                node.set(XML_SPACE, "preserve")
            par.insert(list(par).index(el), ch)
        par.remove(el)
    return dt.para_text(p)


def marked_by(para, author=None):
    return bool(dt.revision_text(para, "ins", author)
                or dt.revision_text(para, "del", author))


def marked_by_others(para, ours):
    for kind in ("ins", "del"):
        for el in para.iter(W + kind):
            if el.getparent() is not None and dt.local(el.getparent().tag) == "rPr":
                continue
            if el.get(W + "author") != ours:
                return True
    return False


def pair_up(a, b):
    """מצמיד פסקאות: קודם לפי מספר סעיף, והשאר לפי קרבת נוסח.

    מחזיר (זוגות, רק_ב-a, רק_ב-b). פסקה בלי מספר סעיף שאין לה מקבילה
    קרובה נשארת לבד, וזו התשובה הנכונה: פסקה שנוספה או שנמחקה.
    """
    pairs, left, right = [], list(range(len(a))), list(range(len(b)))
    by_clause = {}
    for j in right:
        c = clause_of(b[j])
        if c:
            by_clause.setdefault(c, []).append(j)
    for i in list(left):
        c = clause_of(a[i])
        if c and by_clause.get(c):
            j = by_clause[c].pop(0)
            pairs.append((i, j))
            left.remove(i)
            right.remove(j)
    for i in list(left):
        best, score = None, 0.0
        for j in right:
            r = difflib.SequenceMatcher(None, norm(a[i]), norm(b[j])).ratio()
            if r > score:
                best, score = j, r
        if best is not None and score >= NEAR:
            pairs.append((i, best))
            left.remove(i)
            right.remove(best)
    return sorted(pairs), left, right


def main(argv=None):
    no_bytecode()
    ap = parser(__doc__.split("\n")[0], out_required=False)
    ap.add_argument("--sent", required=True, help="הקובץ שהחברה שלחה בסבב הקודם")
    ap.add_argument("--received", required=True, help="הקובץ שחזר מהצד שכנגד")
    ap.add_argument("--author", required=True,
                    help="שם עורך הדין של החברה, כפי שהוא בסימונים שלנו")
    a = ap.parse_args(argv)
    ours = a.author

    sent_paras = dt.body_paragraphs(dt.document_root(a.sent))
    proposed = [project(p, accept_authors=[ours], accept_rest=True) for p in sent_paras]
    before = [project(p, reject_authors=[ours], accept_rest=True) for p in sent_paras]

    recv_paras = dt.body_paragraphs(dt.document_root(a.received))
    # מה הם פתחו בו: הסימונים שלנו מתקבלים, שלהם נדחים
    opened = [project(p, accept_authors=[ours], accept_rest=False) for p in recv_paras]
    now = [project(p, accept_rest=True) for p in recv_paras]

    out = {"sent": a.sent, "received": a.received, "author": ours,
           "clauses": [], "counts": {}}

    def add(kind, para_text_, **extra):
        item = {"classification": kind, "clause": clause_of(para_text_)}
        item.update(extra)
        out["clauses"].append(item)

    pairs, only_sent, only_recv = pair_up(proposed, opened)
    paired_recv = {j for _i, j in pairs}

    for i, j in pairs:
        # 1. שינוי בלי מעקב: מה שהם פתחו בו אינו מה ששלחנו, וההבדל אינו
        # מוסבר בגורל הסימון שלנו. דחייה של סימון שלנו מסירה אותו ומחזירה
        # את הנוסח הקודם, וזה נראה מהקובץ בדיוק כמו שינוי בלי מעקב
        explained = norm(opened[j]) in (norm(proposed[i]), norm(before[i]))
        if norm(opened[j]) != norm(proposed[i]) and not explained:
            add("their_silent", proposed[i], we_sent=proposed[i],
                they_opened_with=opened[j],
                note="הנוסח השתנה בלי סימון מעקב. דורש הכרעת המשתמש")
        # 2. מה קרה להצעה שלנו בסעיף הזה
        if marked_by(recv_paras[j], ours):
            add("our_open", proposed[i], we_proposed=proposed[i], now=now[j],
                note="ההצעה עוד מסומנת: לא קיבלו ולא דחו. אין לגעת בה")
        elif norm(proposed[i]) != norm(before[i]):
            if norm(now[j]) == norm(proposed[i]):
                add("our_accepted", proposed[i], we_proposed=proposed[i], now=now[j],
                    note="ההצעה נשארה. כשאין בסעיף נקודה פתוחה, הוא עובר ל-CLOSED")
            elif norm(now[j]) == norm(before[i]):
                add("our_rejected", proposed[i], we_proposed=proposed[i],
                    was_before=before[i], now=now[j],
                    note="הנוסח חזר למה שהיה. הסעיף מוכרע מחדש לפי הפלייבוק")
            else:
                add("their_tracked", proposed[i], we_proposed=proposed[i], now=now[j],
                    note="הנוסח אינו ההצעה ואינו מה שהיה לפניה")
        # 3. שינוי חדש שלהם, במעקב
        if marked_by_others(recv_paras[j], ours):
            add("their_tracked", now[j], now=now[j],
                they_added=dt.revision_text(recv_paras[j], "ins"),
                they_deleted=dt.revision_text(recv_paras[j], "del"),
                note="מוכרע לפי מספר הזיהוי שלו, כמו בסבב הראשון")

    for i in only_sent:
        if norm(proposed[i]):
            add("their_silent", proposed[i], we_sent=proposed[i], they_opened_with="",
                note="פסקה ששלחנו אינה בקובץ שחזר, ואין סימון מחיקה")
    for j in only_recv:
        if not norm(opened[j]) and not norm(now[j]):
            continue
        if marked_by_others(recv_paras[j], ours) and not norm(opened[j]):
            add("their_tracked", now[j], now=now[j],
                they_added=dt.revision_text(recv_paras[j], "ins"),
                note="פסקה שהם הוסיפו במעקב")
        else:
            add("their_silent", opened[j] or now[j], we_sent="",
                they_opened_with=opened[j],
                note="פסקה שאינה במה ששלחנו, ואין סימון הוספה")

    for c in out["clauses"]:
        k = c["classification"]
        out["counts"][k] = out["counts"].get(k, 0) + 1

    for k in ("their_silent", "their_tracked", "our_accepted", "our_rejected", "our_open"):
        n = out["counts"].get(k, 0)
        mark = "  <-- הממצא החשוב ביותר" if k == "their_silent" and n else ""
        print("  %-14s %3d%s" % (k, n, mark))
    if not out["clauses"]:
        print("  אין הבדל בין מה ששלחנו למה שחזר.")

    if a.out:
        try:
            path = guard_out(a.out, inputs=[a.sent, a.received])
        except OutputRefused as exc:
            print("סירוב: %s" % exc)
            return 1
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=2)
        print("נכתב %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
