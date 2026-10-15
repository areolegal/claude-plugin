#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""מחלץ את סעיפי ההסכמים לקובץ ביניים אחד, במקום להכניס את ההסכמים להקשר.

הבעיה שהוא פותר: עשרים הסכמים הם כמאה ושישים אלף טוקנים. כשהם נקראים אל תוך
השיחה, כל צעד שאחריהם איטי יותר, והמודל נדרש לחזור אליהם כדי לאמת ציטוט.
הסקריפט קורא אותם **מחוץ להקשר** ומפיק קובץ אחד עם הפסקאות בלבד, בנוסחן המדויק,
כדי שהציטוטים יישארו מילוליים ולא יידרש מעבר שני על המקור.

    python3 extract_corpus.py <תיקיית ההסכמים> --out corpus-extract.json

**הקריאה עצמה היא של ספריית הייחוס** (`areolegal/lib/risk/extract_corpus.py`,
שנכתב כדי להחליף את הגרסה הקודמת של הקובץ הזה): הטקסט של כל פסקה בנוסח "קבל
הכול" וגם "דחה הכול", טקסט מוסתר, תיבות טקסט, הערות עם הנוסח שהן מעוגנות בו,
ו-PDF. **המבנה נשמר מהגרסה הקודמת**, כי ההוראות לסקילים נשענות עליו: טבלה
נשמרת לפי טבלה, שורה ועמודה, ולא כפסקאות מנותקות, כי "5,000" בלי "מחיר"
ובלי "ייעוץ" אינו אומר דבר.

מה נשמר לכל מסמך: שם, משפחה משוערת משם הקובץ, מספר פסקאות, האם יש בו עקוב
אחר שינויים או הערות (כלומר טיוטה ולא נוסח חתום), טביעת אצבע לזיהוי כפילויות,
ומעכשיו גם: `format`, ספירת השינויים במעקב לפי סוג, ההערות עצמן, וכמה קטעים
מוסתרים נמצאו.

מה נשמר לכל פסקה: מספר הסעיף אם אותר, והנוסח **כלשונו** (`text`, "קבל
הכול"). כשהנוסח שונה ב"דחה הכול", גם `text_reject_all`. כשיש בה טקסט מוסתר,
`hidden` עם אופן ההסתרה: גופן לבן, גופן זעיר, או טקסט מוסתר של Word.

**PDF.** נקרא כשמותקן pymupdf. בלעדיו, ועם pypdf בלבד, PDF בעברית **אינו
נקרא**: pypdf מחזיר עברית בסדר חזותי, הפוך, וציטוט ממנו לא יהיה מילולי. PDF
סרוק בלי שכבת טקסט, DOC ו-RTF גם הם אינם נקראים. כולם מדווחים תחת
`unreadable` עם הסיבה, ואת אלה יש לקרוא ישירות. אל תניח שהקורפוס מכוסה במלואו
בלי לבדוק את הרשימה הזו.
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

import areo_lib  # noqa: F401  מוסיף את areolegal/lib לנתיב הייבוא

from common.cli import OutputRefused, guard_out  # noqa: E402

try:
    from lxml import etree  # noqa: E402
    from risk.extract_corpus import (anchored_ranges, comments_of, extract_pdf,  # noqa: E402
                                     para_texts, q)
    from risk.page_text import PdfTextUnavailable, pdf_text  # noqa: E402
except ImportError as _exc:                   # lxml מגיע עם python-docx
    sys.exit("נדרשת הספרייה lxml (מגיעה עם python-docx): pip install python-docx. "
             "בלעדיה החילוץ אינו רץ. (%s)" % _exc)

SKIP_DIRS = {"Areo-נתונים", "דוגמאות-נראות", "__MACOSX", ".git", "node_modules"}
# מספר סעיף בתחילת פסקה. מספר מורכב ("8.2", "8.2.1") מזוהה גם בלי סימן פיסוק
# אחריו, כי כך נכתבים רוב תתי-הסעיפים, ושם יושבות ההוראות המהותיות. מספר בודד
# או אות דורשים פיסוק, אחרת כל פסקה שנפתחת בשנה או בסכום הייתה נספרת כסעיף.
CLAUSE_RE = re.compile(
    r"^\s*\(?(?:(\d+(?:\.\d+)+)\)?[.):]?|(\d+|[א-ת])\)?[.):])\s+")
HEBREW = re.compile(r"[א-ת]")
TRACK_KINDS = ("ins", "del", "moveFrom", "moveTo")
SIDE_PARTS = re.compile(r"^word/(footnotes|endnotes|header\d*|footer\d*)\.xml$")


def clause_of(text: str) -> str:
    m = CLAUSE_RE.match(text or "")
    return (m.group(1) or m.group(2)) if m else ""


def _rec(kind, acc, rej, hidden, **extra):
    rec = {"kind": kind, "text": acc}
    rec.update(extra)
    if rej != acc:
        rec["text_reject_all"] = rej
    if hidden:
        rec["hidden"] = hidden
    return rec


def _walk(container, out, tables):
    """הפסקאות והטבלאות לפי הסדר. תוכן בבקר תוכן (sdt) נקרא כאילו היה במקום."""
    for el in container:
        if el.tag == q("p"):
            acc, rej, hid = para_texts(el)
            if acc or rej:
                out.append(_rec("p", acc, rej, hid))
            # פסקה בתוך תיבת טקסט אינה חלק מהפסקה העוטפת (para_texts מדלג
            # עליה), ולכן היא נשמרת לבד, פעם אחת
            for tx in el.iter(q("txbxContent")):
                for ip in tx.iter(q("p")):
                    a, r, h = para_texts(ip)
                    if a or r:
                        out.append(_rec("textbox", a, r, h))
        elif el.tag == q("tbl"):
            tables[0] += 1
            t = tables[0]
            for r_idx, tr in enumerate(el.findall(q("tr"))):
                for c_idx, tc in enumerate(tr.findall(q("tc"))):
                    accs, rejs, hids = [], [], []
                    for p in tc.iter(q("p")):
                        a, r, h = para_texts(p)
                        accs.append(a)
                        rejs.append(r)
                        hids += h
                    acc = " ".join(x for x in accs if x).strip()
                    rej = " ".join(x for x in rejs if x).strip()
                    if acc or rej:
                        out.append(_rec("cell", acc, rej, hids,
                                        table=t, row=r_idx, col=c_idx))
        elif el.tag == q("sdt"):
            content = el.find(q("sdtContent"))
            if content is not None:
                _walk(content, out, tables)


def read_docx(path: Path):
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        if "word/document.xml" not in names:
            raise ValueError("no document.xml")
        doc = etree.fromstring(z.read("word/document.xml"))
        body = doc.find(q("body"))
        items, tables = [], [0]
        _walk(body if body is not None else doc, items, tables)

        counts = {k: len(doc.findall(".//" + q(k))) for k in TRACK_KINDS}
        comments = comments_of(z)
        for k, v in anchored_ranges(doc).items():
            if k in comments:
                comments[k]["anchored_text"] = v
        # הערות שוליים נושאות לעיתים סייג מהותי לסעיף, וכותרת עליונה ותחתונה
        # נושאות לעיתים את שמות הצדדים ומספר הגרסה, ולכן גם הן נשמרות ומסומנות
        for part in sorted(n for n in names if SIDE_PARTS.match(n)):
            x = etree.fromstring(z.read(part))
            for k in TRACK_KINDS:
                counts[k] += len(x.findall(".//" + q(k)))
            for k, v in anchored_ranges(x).items():
                if k in comments and not comments[k].get("anchored_text"):
                    comments[k]["anchored_text"] = v
            side = []
            if "notes" in part:
                for note in x:
                    _walk(note, side, tables)
            else:
                _walk(x, side, tables)
            kind = "footnote" if "notes" in part else "header_footer"
            for b in side:
                if len(b["text"]) > 3:
                    if b["kind"] == "p":
                        b["kind"] = kind
                    items.append(b)
        settings = (z.read("word/settings.xml").decode("utf-8", "replace")
                    if "word/settings.xml" in names else "")
    info = {"format": "docx", "tracked_counts": counts,
            "track_revisions_on": "<w:trackRevisions" in settings,
            "comments": [{"author": c.get("author"), "date": c.get("date"),
                          "text": c.get("text"), "anchored_text": c.get("anchored_text") or ""}
                         for c in comments.values()]}
    return items, info


def pdf_engine():
    for mod in ("pymupdf", "fitz"):
        try:
            __import__(mod)
            return "pymupdf"
        except ImportError:
            pass
    try:
        __import__("pypdf")
        return "pypdf"
    except ImportError:
        return None


def read_pdf(path: Path, engine):
    """(פסקאות, מידע) או ValueError עם הסיבה שבגללה ה-PDF אינו נקרא."""
    raw = path.read_bytes()
    if engine is None:
        raise ValueError("אין בסביבה ספרייה לקריאת PDF. התקנה: pip install pymupdf")
    if engine == "pymupdf":
        d = extract_pdf(str(path), raw)
        if d.get("no_text_layer"):
            raise ValueError("PDF סרוק, בלי שכבת טקסט")
        items = []
        for part, paras in d["parts"].items():
            page = int(part.rsplit("-", 1)[-1])
            items += [{"kind": "p", "text": p["text_accept_all"], "page": page} for p in paras]
        return items, {"format": "pdf", "pdf_engine": engine}
    try:
        text = pdf_text(raw)
    except PdfTextUnavailable as exc:
        raise ValueError(str(exc).split(":")[0])
    if HEBREW.search(text):
        # pypdf מחזיר עברית בסדר חזותי. ציטוט ממנו אינו מילולי, וזה בדיוק
        # מה שהקובץ הזה מבטיח, ולכן עדיף "לא נקרא" על "נקרא הפוך"
        raise ValueError("PDF בעברית, ואין pymupdf: הטקסט יוצא בסדר הפוך. "
                         "התקנה: pip install pymupdf")
    items = [{"kind": "p", "text": re.sub(r"\s+", " ", l).strip()}
             for l in text.splitlines() if l.strip()]
    return items, {"format": "pdf", "pdf_engine": engine}


def family_guess(stem: str) -> str:
    s = re.sub(r"[_\-]+", " ", stem)
    s = re.sub(r"\b(v|ver|version|rev|draft|final|signed|חתום|טיוטה)\s*\d*\b", " ", s, flags=re.I)
    s = re.sub(r"\b20\d{2}[.\-_ ]?\d{0,2}[.\-_ ]?\d{0,2}\b", " ", s)
    return " ".join(s.split())[:80]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--out", required=True,
                    help="קובץ הפלט (JSON). חובה ומפורש: ברירת מחדל שקטה "
                         "כותבת לתיקייה שממנה הריצו")
    ap.add_argument("--max-paragraphs", type=int, default=1200,
                    help="תקרה לכל מסמך; פסקאות מעבר לה נספרות ואינן נשמרות")
    args = ap.parse_args()

    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print("לא נמצאה תיקייה: %s" % root); return 1

    engine = pdf_engine()
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
        if ext in (".doc", ".rtf"):
            unreadable.append("%s (פורמט %s אינו נקרא; שמרו כ-docx)" % (rel, ext[1:].upper()))
            continue
        try:
            if ext == ".docx":
                paras, info = read_docx(f)
            elif ext == ".pdf":
                paras, info = read_pdf(f, engine)
            else:
                paras = [{"kind": "p", "text": l.strip()} for l in
                         io.open(f, encoding="utf-8", errors="ignore").read().splitlines()
                         if l.strip()]
                info = {"format": ext[1:]}
        except ValueError as e:                       # סיבה ידועה: נאמרת כמו שהיא
            unreadable.append("%s (%s)" % (rel, e)); continue
        except Exception as e:                       # קובץ פגום אינו עוצר את הריצה
            unreadable.append("%s (%s)" % (rel, type(e).__name__)); continue

        digest = hashlib.sha256("\n".join(b["text"] for b in paras).encode("utf-8")).hexdigest()
        if digest in seen:                            # אותו תוכן בדיוק, שם קובץ אחר
            docs[seen[digest]]["duplicates"].append(rel); continue
        seen[digest] = len(docs)

        counts = info.get("tracked_counts") or {}
        tracked = any(counts.values())
        has_comments = bool(info.get("comments"))
        kept = paras[: args.max_paragraphs]
        doc = {
            "doc_id": "d%03d" % (len(docs) + 1),
            "path": rel,
            "format": info.get("format"),
            "family_guess": family_guess(f.stem),
            "paragraph_count": len(paras),
            "truncated": len(paras) > len(kept),
            "has_tracked_changes": tracked,
            "has_comments": has_comments,
            "looks_like_draft": tracked or has_comments,
            "content_sha256": digest[:16],
            "duplicates": [],
            "table_count": len({b["table"] for b in kept if b["kind"] == "cell"}),
            "hidden_total": sum(len(b.get("hidden") or []) for b in paras),
            "paragraphs": [
                dict(b, i=i,
                     clause=(clause_of(b["text"]) if b["kind"] == "p" else ""))
                for i, b in enumerate(kept)
            ],
        }
        for key in ("tracked_counts", "track_revisions_on", "comments", "pdf_engine"):
            if key in info:
                doc[key] = info[key]
        docs.append(doc)

    drafts = sum(1 for d in docs if d["looks_like_draft"])
    hidden_docs = [d["path"] for d in docs if d["hidden_total"]]
    out = {
        "root": str(root),
        "document_count": len(docs),
        "duplicate_count": sum(len(d["duplicates"]) for d in docs),
        "draft_like_count": drafts,
        "pdf_count": sum(1 for d in docs if d["format"] == "pdf"),
        "hidden_text_documents": hidden_docs,
        "unreadable": unreadable,
        "documents": docs,
    }
    # הקורפוס הוא ההסכמים של הלקוח, ו-`--out` שמצביע על אחד מהם דורס
    # אותו ב-JSON. `common/cli.guard_out` מסרב על קובץ קלט, על תיקיית
    # מקור ועל מסמך Word או PDF קיים
    try:
        out_path = guard_out(args.out,
                             inputs=[str(f) for f in root.rglob("*") if f.is_file()])
    except OutputRefused as exc:
        print("סירוב: %s" % exc)
        return 1
    io.open(out_path, "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))

    print("נכתב %s" % out_path)
    print("  מסמכים ייחודיים : %d (מהם PDF: %d)" % (len(docs), out["pdf_count"]))
    print("  כפילויות מדויקות: %d" % out["duplicate_count"])
    print("  נחזים כטיוטות   : %d" % drafts)
    print("  עם טקסט מוסתר   : %d" % len(hidden_docs))
    print("  לא נקראו כאן    : %d" % len(unreadable))
    for u in unreadable[:10]:
        print("    - %s" % u)
    if len(unreadable) > 10:
        print("    ועוד %d" % (len(unreadable) - 10))
    if unreadable:
        print("  את אלה יש לקרוא ישירות; הם אינם בקובץ.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
