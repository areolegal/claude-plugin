#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""מחלץ את סעיפי ההסכמים לקובץ ביניים אחד, במקום להכניס את ההסכמים להקשר.

הבעיה שהוא פותר: עשרים הסכמים הם כמאה ושישים אלף טוקנים. כשהם נקראים אל תוך
השיחה, כל צעד שאחריהם איטי יותר, והמודל נדרש לחזור אליהם כדי לאמת ציטוט.
הסקריפט קורא אותם **מחוץ להקשר** ומפיק קובץ אחד עם הפסקאות בלבד, בנוסחן המדויק,
כדי שהציטוטים יישארו מילוליים ולא יידרש מעבר שני על המקור.

    python3 extract_corpus.py <תיקיית ההסכמים> --out corpus-extract.json

מה נשמר לכל מסמך: שם, משפחה משוערת משם הקובץ, מספר פסקאות, האם יש בו עקוב אחר
שינויים או הערות (כלומר טיוטה ולא נוסח חתום), וטביעת אצבע לזיהוי כפילויות.
מה נשמר לכל פסקה: מספר הסעיף אם אותר, והנוסח **כלשונו**.

מגבלה שיש לומר עליה: קובצי PDF ו-DOC אינם נקראים כאן. הם מדווחים תחת
`unreadable`, ואת אלה יש לקרוא ישירות. אל תניח שהקורפוס מכוסה במלואו בלי לבדוק
את המספר הזה.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
import zipfile
from pathlib import Path

SKIP_DIRS = {"Areo-נתונים", "דוגמאות-נראות", "__MACOSX", ".git", "node_modules"}
# מספר סעיף בתחילת פסקה. מספר מורכב ("8.2", "8.2.1") מזוהה גם בלי סימן פיסוק
# אחריו, כי כך נכתבים רוב תתי-הסעיפים, ושם יושבות ההוראות המהותיות. מספר בודד
# או אות דורשים פיסוק, אחרת כל פסקה שנפתחת בשנה או בסכום הייתה נספרת כסעיף.
CLAUSE_RE = re.compile(
    r"^\s*\(?(?:(\d+(?:\.\d+)+)\)?[.):]?|(\d+|[א-ת])\)?[.):])\s+")


def clause_of(text: str) -> str:
    m = CLAUSE_RE.match(text or "")
    return (m.group(1) or m.group(2)) if m else ""
PARA_RE = re.compile(r"<w:p[ >].*?</w:p>|<w:p/>", re.S)
TBL_RE = re.compile(r"<w:tbl>.*?</w:tbl>", re.S)
ROW_RE = re.compile(r"<w:tr[ >].*?</w:tr>", re.S)
CELL_RE = re.compile(r"<w:tc[ >].*?</w:tc>", re.S)
DEL_RE = re.compile(r"<w:del\b.*?</w:del>", re.S)
INS_RE = re.compile(r"<w:ins\b.*?</w:ins>", re.S)
TAG_RE = re.compile(r"<[^>]+>")


def _text(fragment: str, mode: str) -> str:
    q = DEL_RE.sub("", fragment) if mode == "final" else INS_RE.sub("", fragment)
    t = TAG_RE.sub("", q)
    t = (t.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
          .replace("&quot;", '"').replace("&apos;", "'"))
    return re.sub(r"[ \t\u00a0]+", " ", t).strip()


def blocks(xml: str, mode: str = "final"):
    """פסקאות הגוף לפי הסדר, **עם שמירת מבנה הטבלאות**.

    טבלה בחוזה נושאת תמורה, לוחות זמנים, תקרות אחריות ופרטי צדדים. פירוקה
    לפסקאות בודדות מנתק את הערך מהכותרת שלו: "5,000" בלי "מחיר" ובלי "ייעוץ"
    אינו אומר דבר, ומודל שמנסה לשחזר את הקשר עלול לשייך מספר לשורה הלא נכונה.
    לכן כל תא מוחזר עם מספר הטבלה, השורה והעמודה שלו.
    """
    out = []
    pos, t_idx = 0, 0
    for m in TBL_RE.finditer(xml):
        for p in PARA_RE.findall(xml[pos:m.start()]):
            t = _text(p, mode)
            if t:
                out.append({"kind": "p", "text": t})
        t_idx += 1
        for r_idx, row in enumerate(ROW_RE.findall(m.group(0))):
            for c_idx, cell in enumerate(CELL_RE.findall(row)):
                t = _text(cell, mode)
                if t:
                    out.append({"kind": "cell", "table": t_idx,
                                "row": r_idx, "col": c_idx, "text": t})
        pos = m.end()
    for p in PARA_RE.findall(xml[pos:]):
        t = _text(p, mode)
        if t:
            out.append({"kind": "p", "text": t})
    return out


def read_docx(path: Path):
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        if "word/document.xml" not in names:
            raise ValueError("no document.xml")
        xml = z.read("word/document.xml").decode("utf-8", "ignore")
        tracked = ("<w:ins " in xml) or ("<w:del " in xml)
        comments = "word/comments.xml" in names
        items = blocks(xml)
        # הערות שוליים נושאות לעיתים סייג מהותי לסעיף, ולכן הן נשמרות ומסומנות
        for part in ("word/footnotes.xml", "word/endnotes.xml"):
            if part in names:
                fx = z.read(part).decode("utf-8", "ignore")
                for b in blocks(fx):
                    if len(b["text"]) > 3:
                        b["kind"] = "footnote"
                        items.append(b)
        # כותרת עליונה ותחתונה: לעיתים שם הצדדים ומספר הגרסה יושבים רק שם
        for part in [n for n in names if re.match(r"word/(header|footer)\d*\.xml$", n)]:
            hx = z.read(part).decode("utf-8", "ignore")
            for b in blocks(hx):
                if len(b["text"]) > 3:
                    b["kind"] = "header_footer"
                    items.append(b)
    return items, tracked, comments


def family_guess(stem: str) -> str:
    s = re.sub(r"[_\-]+", " ", stem)
    s = re.sub(r"\b(v|ver|version|rev|draft|final|signed|חתום|טיוטה)\s*\d*\b", " ", s, flags=re.I)
    s = re.sub(r"\b20\d{2}[.\-_ ]?\d{0,2}[.\-_ ]?\d{0,2}\b", " ", s)
    return " ".join(s.split())[:80]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--out", default="corpus-extract.json")
    ap.add_argument("--max-paragraphs", type=int, default=1200,
                    help="תקרה לכל מסמך; פסקאות מעבר לה נספרות ואינן נשמרות")
    args = ap.parse_args()

    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print("לא נמצאה תיקייה: %s" % root); return 1

    docs, unreadable, seen = [], [], {}
    for f in sorted(root.rglob("*")):
        if not f.is_file() or f.name.startswith((".", "~$")):
            continue
        if any(part in SKIP_DIRS for part in f.parts):
            continue
        ext = f.suffix.lower()
        if ext not in (".docx", ".txt", ".md", ".pdf", ".doc", ".rtf"):
            continue
        rel = str(f.relative_to(root))
        if ext in (".pdf", ".doc", ".rtf"):
            unreadable.append(rel); continue
        try:
            if ext == ".docx":
                paras, tracked, comments = read_docx(f)
            else:
                paras = [{"kind": "p", "text": l.strip()} for l in
                         io.open(f, encoding="utf-8", errors="ignore").read().splitlines()
                         if l.strip()]
                tracked = comments = False
        except Exception as e:                       # קובץ פגום אינו עוצר את הריצה
            unreadable.append("%s (%s)" % (rel, type(e).__name__)); continue

        digest = hashlib.sha256("\n".join(b["text"] for b in paras).encode("utf-8")).hexdigest()
        if digest in seen:                            # אותו תוכן בדיוק, שם קובץ אחר
            docs[seen[digest]]["duplicates"].append(rel); continue
        seen[digest] = len(docs)

        kept = paras[: args.max_paragraphs]
        docs.append({
            "doc_id": "d%03d" % (len(docs) + 1),
            "path": rel,
            "family_guess": family_guess(f.stem),
            "paragraph_count": len(paras),
            "truncated": len(paras) > len(kept),
            "has_tracked_changes": tracked,
            "has_comments": comments,
            "looks_like_draft": tracked or comments,
            "content_sha256": digest[:16],
            "duplicates": [],
            "table_count": len({b["table"] for b in kept if b["kind"] == "cell"}),
            "paragraphs": [
                dict(b, i=i,
                     clause=(clause_of(b["text"]) if b["kind"] == "p" else ""))
                for i, b in enumerate(kept)
            ],
        })

    drafts = sum(1 for d in docs if d["looks_like_draft"])
    out = {
        "root": str(root),
        "document_count": len(docs),
        "duplicate_count": sum(len(d["duplicates"]) for d in docs),
        "draft_like_count": drafts,
        "unreadable": unreadable,
        "documents": docs,
    }
    io.open(args.out, "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))

    print("נכתב %s" % args.out)
    print("  מסמכים ייחודיים : %d" % len(docs))
    print("  כפילויות מדויקות: %d" % out["duplicate_count"])
    print("  נחזים כטיוטות   : %d" % drafts)
    print("  לא נקראו כאן    : %d" % len(unreadable))
    for u in unreadable[:10]:
        print("     · %s" % u)
    if unreadable:
        print("  את אלה יש לקרוא ישירות; הם אינם בקובץ.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
