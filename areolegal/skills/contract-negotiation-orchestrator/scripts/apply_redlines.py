#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""סימון ההסכם של הצד שכנגד בעקוב אחר שינויים אמיתי, עם הערות Word.

זהו התוצר שנשלח לצד שכנגד. הוא נבנה על הקובץ **שלהם**, ולא כמסמך חדש:
השינויים מבוצעים בגוף ההסכם כ-w:ins/w:del, וההסבר נכנס כהערת Word אמיתית.

שלושה כללי ברזל:

1. **שום תוכן פנימי אינו נכנס לקובץ הזה.** לא קודי הכרעה, לא נוסח הנסיגה
   ולא שיקול טקטי. ההערה לצד שכנגד מורכבת מהעמדה, ממספר הכלל במדיניות
   ומההסבר שב-`external_comment`, ומשום מקום אחר. **זהו התוצר היחיד של הרכיב**;
   תיעוד ההכרעות נשמר ב-negotiation_state.json ואינו מופק כמסמך.
   מותר ורצוי להסביר לצד שכנגד מה המדיניות שלנו קובעת בסעיף; אסור לחשוף
   עד היכן אנחנו מוכנים לרדת.

2. **לא מנחשים היכן לסמן.** סעיף שלא אותר בוודאות אינו מסומן, והוא מדווח
   כ"לא אותר" כדי שעורך הדין יטפל בו ידנית. סימון שינוי בסעיף הלא נכון
   בהסכם שנשלח לצד שכנגד גרוע בהרבה מסעיף שלא סומן.

3. **הטיוטה נקלטת לפני שמסמנים עליה.** השינויים שהצד שכנגד הציע מתקבלים
   והופכים לנוסח הבסיס, וההערות שהיו בקובץ מוסרות. זו הקליטה שעורך דין עושה
   ביד לפני שהוא פותח סבב, והיא מה שמאפשר לסמן מעליה: בלעדיה הציטוט שבהכרעה
   והטקסט שהסקריפט רואה אינם אותו טקסט, והנוסח נכפל כשמקבלים את השינויים.
   מה שנקלט ומה שהוסר מדווח בסוף הריצה. הנימוק המלא ב-track_changes_helpers.

שימוש:
    python3 apply_redlines.py --draft <קובץ הצד שכנגד.docx> \\
        --decisions decisions.json --out marked.docx --author "שם עורך הדין"
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
import unicodedata

try:
    from docx import Document
    from docx.enum.text import WD_COLOR_INDEX
    from docx.oxml.ns import qn
except ImportError:
    sys.exit("נדרש python-docx. התקנה: pip install python-docx")

import track_changes_helpers as tc

# יחס דמיון מזערי להתאמת ציטוט. נבחר גבוה בכוונה: מוטב לדווח שסעיף לא אותר
# מאשר לסמן שינוי בסעיף שכן. בבדיקות, ניסוח חוזי שונה יורד הרבה מתחת לזה.
MIN_RATIO = 0.82

# שלושת המסלולים. הפתיח קבוע ואינו נתון לניסוח חופשי: הצד שכנגד קורא עשרות
# הערות, ועמדת החברה חייבת להיקרא באותה מילה בכל אחת מהן.
TRACKS = {
    "green":  ("מוסכם",                  WD_COLOR_INDEX.BRIGHT_GREEN),
    "yellow": ("מוסכם בכפוף להערות",     WD_COLOR_INDEX.YELLOW),
    "red":    ("לא מוסכם",               WD_COLOR_INDEX.RED),
}

# מספר סעיף בתחילת פסקה: "5.", "5.1", "5.1.2", "(א)" ועוד
CLAUSE_RE = re.compile(r"^\s*\(?([0-9]+(?:\.[0-9]+)*|[א-ת])\)?[.):]?\s")

RLM = "‏"
BIDI = "".join(chr(c) for c in (0x200E, 0x200F, 0x202A, 0x202B, 0x202C, 0x202D, 0x202E))

# ילדי w:p שנושאים טקסט. אלה שיורדים כשמחליפים נוסח פסקה.
CONTENT_TAGS = {qn(t) for t in ('w:r', 'w:hyperlink', 'w:ins', 'w:del',
                                'w:moveTo', 'w:moveFrom', 'w:smartTag')}


def norm(s: str) -> str:
    """נרמול להשוואה: סימני כיווניות, גרשיים, רווחים וניקוד."""
    s = unicodedata.normalize("NFKC", s or "")
    s = s.translate({ord(c): None for c in BIDI})
    s = re.sub(r"[֑-ׇ]", "", s)          # ניקוד וטעמים
    s = s.replace("״", '"').replace("”", '"').replace("“", '"')
    s = s.replace("׳", "'").replace("’", "'").replace("‘", "'")
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def clause_of(text: str) -> str:
    m = CLAUSE_RE.match(text or "")
    return m.group(1) if m else ""


def locate(paragraphs, decision):
    """מאתר את הפסקה שאליה מתייחסת ההכרעה.

    מחזיר (index, method) או (None, reason). הסדר מכוון: ציטוט קודם למספר
    סעיף, מפני שמספור משתנה בין טיוטות ואילו הנוסח נשאר.
    """
    anchor = norm(decision.get("anchor_quote") or decision.get("clause_text") or "")
    want_clause = str(decision.get("clause_number") or "").strip()

    if anchor and len(anchor) >= 12:
        # 1. הכלה מדויקת
        hits = [i for i, p in enumerate(paragraphs) if anchor in norm(p.text)]
        if len(hits) == 1:
            return hits[0], "ציטוט מדויק"
        if len(hits) > 1:
            # ריבוי התאמות: הכרע רק אם מספר הסעיף מפריד ביניהן
            if want_clause:
                narrowed = [i for i in hits if clause_of(paragraphs[i].text) == want_clause]
                if len(narrowed) == 1:
                    return narrowed[0], "ציטוט + מספר סעיף"
            return None, "הציטוט מופיע ב-%d פסקאות ולא ניתן להכריע" % len(hits)

        # 2. התאמה מקורבת, לניסוח שהשתנה קלות
        scored = []
        for i, p in enumerate(paragraphs):
            t = norm(p.text)
            if len(t) < 12:
                continue
            r = difflib.SequenceMatcher(None, anchor, t).ratio()
            if r >= MIN_RATIO:
                scored.append((r, i))
        scored.sort(reverse=True)
        if len(scored) == 1:
            return scored[0][1], "התאמה מקורבת %.2f" % scored[0][0]
        if len(scored) > 1 and scored[0][0] - scored[1][0] >= 0.05:
            return scored[0][1], "התאמה מקורבת %.2f" % scored[0][0]
        if scored:
            return None, "כמה פסקאות דומות במידה זהה; לא ניתן להכריע"

    # 3. נפילה למספר סעיף בלבד
    if want_clause:
        hits = [i for i, p in enumerate(paragraphs) if clause_of(p.text) == want_clause]
        if len(hits) == 1:
            return hits[0], "מספר סעיף"
        if len(hits) > 1:
            return None, "מספר הסעיף %s מופיע %d פעמים" % (want_clause, len(hits))

    if anchor and len(anchor) < 12:
        return None, "הציטוט קצר מדי (%d תווים). נדרשים 12 לפחות" % len(anchor)
    if anchor:
        return None, "הציטוט לא נמצא בטיוטה. ודא שהוא הועתק מנוסח המקור ולא מתמצית"
    return None, ("אין ציטוט. מספר סעיף לבדו אינו מספיק ברוב ההסכמים, "
                  "מפני שהמספור נוצר אוטומטית ב-Word ואינו חלק מהטקסט")


def build_comment(decision, author):
    """מרכיב את בועת ההערה בנוסח אחיד, כאילו עורך הדין של החברה כותב לצד שכנגד.

        <שם עורך הדין>:
        מוסכם בכפוף להערות (סעיף 8.2 למדיניות שלנו)

        <ההסבר שנכתב עבור הסעיף הזה>

    הפתיח, שם החותם ומספר הכלל מורכבים כאן ולא נכתבים בכל פעם מחדש, כדי שכל
    ההערות במסמך ייראו כמסמך אחד. ההסבר בלבד מגיע מההכרעה.

    **המילה "פלייבוק" אינה מופיעה לעולם.** כלפי חוץ זו "המדיניות שלנו".
    """
    track = (decision.get("track") or "").lower()
    if track not in TRACKS:
        return None, None
    verdict, color = TRACKS[track]
    ref = str(decision.get("policy_ref") or "").strip()
    head = "%s (סעיף %s למדיניות שלנו)" % (verdict, ref) if ref else verdict
    body = (decision.get("external_comment") or "").strip()
    lines = ["%s:" % author if author else "", head]
    if body:
        lines.append("")
        lines.append(body)
    return "\n".join(x for x in lines if x is not None), color


def highlight(par, color):
    """מסמן את הסעיף בצבע המסלול, כדי שהעמדה תיקרא בסריקה של הדף."""
    if color is None:
        return
    for r in par.runs:
        r.font.highlight_color = color


def apply_edit(par, decision, author):
    """מוחק את הנוסח הישן ומכניס את החדש, כשינוי מעקב אמיתי."""
    old = decision.get("original_text") or par.text
    new = decision.get("replacement_text") or ""
    if not new or norm(new) == norm(old):
        return False
    # הנוסח הישן יורד כמחיקה מסומנת. מוסרים כל נושא טקסט ולא רק par.runs:
    # runs מחזיר w:r ישירים בלבד, ונוסח שנשאר בעטיפה אחרת היה נכפל בתוצר.
    # סימניות ורכיבי pPr נשארים, כדי לא לשבור הפניות וסגנון.
    for el in list(par._p):
        if el.tag in CONTENT_TAGS:
            par._p.remove(el)
    tc.add_del(par, old, ltr=False)
    tc.add_ins(par, new, ltr=False)
    return True


def all_paragraphs(doc):
    """כל הפסקאות במסמך, כולל אלה שבתוך טבלאות.

    `doc.paragraphs` מדלג על תאי טבלה, ובהסכם אמיתי יושבים שם פרטי הצדדים,
    התמורה ולעיתים נספחים שלמים. סעיף שנמצא בטבלה פשוט לא היה נמצא.
    """
    out = list(doc.paragraphs)
    for tbl in doc.tables:
        for row in tbl.rows:
            for cell in row.cells:
                out.extend(cell.paragraphs)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--draft", required=True, help="ההסכם של הצד שכנגד")
    ap.add_argument("--decisions", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--author", default="", help="שם עורך הדין, לבועות ההערה")
    ap.add_argument("--report", default="", help="קובץ JSON לדיווח מה אותר ומה לא")
    args = ap.parse_args()

    if args.author:
        tc.AUTHOR = args.author

    data = json.load(open(args.decisions, encoding="utf-8"))
    decisions = data.get("decisions", data if isinstance(data, list) else [])

    doc = Document(args.draft)
    # קליטת הטיוטה: מקבלים את מה שהצד שכנגד הציע ומסירים את ההערות שבקובץ,
    # ורק אז מאתרים. סדר הפוך היה מאתר לפי טקסט חלקי. ראה כלל 3 למעלה.
    intake = tc.accept_revisions(doc)
    intake["comments_removed"] = tc.strip_comments(doc)
    tc.enable_track_changes(doc)
    paragraphs = all_paragraphs(doc)

    applied, commented, missed = [], [], []
    for d in decisions:
        idx, how = locate(paragraphs, d)
        ident = d.get("clause_number") or (d.get("anchor_quote") or "")[:40] or "?"
        if idx is None:
            missed.append({"clause": ident, "reason": how})
            continue
        par = paragraphs[idx]
        changed = apply_edit(par, d, args.author)

        # ההערה לצד שכנגד נלקחת משדה ייעודי בלבד. אין ליפול חזרה על
        # legal_reasoning או policy_position -- אלה פנימיים.
        note, color = build_comment(d, args.author)
        if note is None:
            missed.append({"clause": ident,
                           "reason": "אין track תקין (green/yellow/red); לא סומן ולא הוער"})
            continue
        tc.add_comment(par, note)
        highlight(par, color)
        commented.append(ident)
        if changed:
            applied.append({"clause": ident, "matched_by": how})

    tc.attach_comments(doc)
    doc.save(args.out)

    print("נבנה %s" % args.out)
    print("  נקלט מהטיוטה   : %d הוספות ו-%d מחיקות של הצד שכנגד התקבלו כנוסח הבסיס"
          % (intake["accepted_insertions"], intake["accepted_deletions"]))
    print("  שינויים שסומנו : %d" % len(applied))
    print("  הערות לצד שכנגד: %d" % len(commented))
    print("  לא אותרו       : %d" % len(missed))
    for m in missed:
        print("     · %s - %s" % (m["clause"], m["reason"]))
    if missed:
        print("  יש לטפל בהם ידנית. הם לא סומנו, ולא נוחשה עבורם פסקה.")

    dropped = intake["comments_removed"]
    if dropped:
        print("  הערות שהוסרו   : %d. הן אינן יוצאות לצד שכנגד:" % len(dropped))
        for c in dropped:
            print("     · %s: %s" % (c["author"] or "ללא שם", (c["text"] or "")[:70]))
        print("  בדוק אם יש ביניהן הערה פנימית שלנו שדורשת טיפול בסבב הזה.")
    if intake["paragraph_marks_deleted"]:
        print("  שים לב: ב-%d פסקאות הצד שכנגד מחק את סימן הפסקה, כלומר ביקש "
              "לאחד פסקאות. האיחוד לא בוצע, מפני שהוא משנה את מבנה ההסכם."
              % intake["paragraph_marks_deleted"])

    if args.report:
        json.dump({"intake": intake, "applied": applied,
                   "commented": commented, "missed": missed},
                  open(args.report, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
