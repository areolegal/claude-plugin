#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""מחלץ את סעיפי ההסכמים לקובץ ביניים אחד, במקום להכניס את ההסכמים להקשר.

הבעיה שהוא פותר: עשרים הסכמים הם כמאה ושישים אלף טוקנים. כשהם נקראים אל תוך
השיחה, כל צעד שאחריהם איטי יותר, והמודל נדרש לחזור אליהם כדי לאמת ציטוט.
הסקריפט קורא אותם **מחוץ להקשר** ומפיק קובץ אחד עם הפסקאות בלבד, בנוסחן המדויק,
כדי שהציטוטים יישארו מילוליים ולא יידרש מעבר שני על המקור.

    python3 extract_corpus.py <תיקיית ההסכמים, או מסמך אחד> --out <תיקייה זמנית>/corpus.json

**הקריאה עצמה היא של ספריית הייחוס** (`areolegal/lib/risk/extract_corpus.py`,
שנכתב כדי להחליף את הגרסה הקודמת של הקובץ הזה): הטקסט של כל פסקה בנוסח "קבל
הכול" וגם "דחה הכול", טקסט מוסתר, תיבות טקסט, הערות עם הנוסח שהן מעוגנות בו,
ו-PDF. **המבנה נשמר מהגרסה הקודמת**, כי ההוראות לסקילים נשענות עליו: טבלה
נשמרת לפי טבלה, שורה ועמודה, ולא כפסקאות מנותקות, כי "5,000" בלי "מחיר"
ובלי "ייעוץ" אינו אומר דבר. העמודה היא עמודת הרשת (`w:gridSpan` ו-`w:gridBefore`
נספרים), ולא מספר התא בשורה. תא ממוזג לרוחב נושא `col_span`; תא שממוזג לגובה
(`w:vMerge`) נשמר פעם אחת, בשורה שבה המיזוג מתחיל, עם `row_span`. טבלה בתוך
תא נשמרת כטבלה משלה, עם `parent_table`, `parent_row` ו-`parent_col`, ואינה
משוטחת לתוך הטקסט של התא.

**מסמך בלי טקסט ו-Strict.** מסמך שאין בגוף שלו אף פסקה עם טקסט (בדרך כלל
סריקה שהודבקה ל-Word כתמונה) נרשם ב-`unreadable` עם "אין שכבת טקסט (סרוק?)",
ואינו נבדק לכפילות: טביעת האצבע של תוכן ריק זהה בכל המסמכים הריקים, ומסמך כזה
נבלע בעבר כ"כפילות" של אחר. מסמך Strict Open XML מנורמל ונקרא (`ooxml_strict`).
DOC ישן, קובץ מוצפן, ZIP פגום וקובץ בלי document.xml נרשמים ב-`unreadable`
עם הסיבה (`common/cli.docx_problem`); מסמך יחיד כזה: הודעה דו-לשונית וקוד 2.

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
`unreadable` עם הסיבה; הטיפול בהם לפי הוראות הרכיב שמריץ את החילוץ. אל תניח שהקורפוס מכוסה במלואו
בלי לבדוק את הרשימה הזו.

**נתיב ארוך וקובץ חסר.** תיקייה בנתיב ארוך מ-260 תווים נקראת ב-Windows דרך
`common/paths.long_path`. קובץ שנמצא ברשימת התיקייה ולא נפתח נרשם ב-`unreadable`,
והסקריפט מסתיים בקוד יציאה 1 עם הודעה; תיקייה או קובץ שלא נמצאו כלל: קוד יציאה 1.
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

import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # גם ב-python -I, שאינו מוסיף את תיקיית הסקריפט
import areo_lib  # noqa: F401  מוסיף את areolegal/lib לנתיב הייבוא

from common.cli import DOCX_BAD_EXIT, OutputRefused, docx_problem, guard_out  # noqa: E402
from common.paths import long_path, plain_path  # noqa: E402

try:
    from lxml import etree  # noqa: E402
    from risk.extract_corpus import (OoxmlZip, anchored_ranges, comments_of,  # noqa: E402
                                     extract_pdf, para_changes, para_texts, q)
    from risk.page_text import PdfTextUnavailable, pdf_text  # noqa: E402
except ImportError as _exc:                   # lxml מגיע עם python-docx
    sys.exit("נדרשת הספרייה lxml (מגיעה עם python-docx): pip install python-docx. "
             "בלעדיה החילוץ אינו רץ. (%s)" % _exc)

SKIP_DIRS = {"Areo-נתונים", "דוגמאות-נראות", "__MACOSX", ".git", "node_modules"}
# מספר סעיף בתחילת פסקה. מספר מורכב ("8.2", "8.2.1") מזוהה גם בלי סימן פיסוק
# אחריו, כי כך נכתבים רוב תתי-הסעיפים, ושם יושבות ההוראות המהותיות. מספר בודד
# או אות דורשים פיסוק, אחרת כל פסקה שנפתחת בשנה או בסכום הייתה נספרת כסעיף.
# באנגלית גם (a), (iv), A. ו-IV., ו-Section 5.2, Clause 7 או Article IV. אחרי מילת
# הסעיף נדרשים פיסוק או כותרת באות גדולה, כי "Section 5.2 of the Agreement" הוא הפניה
# ולא סעיף. ספרה רומית רק באותיות קטנות או רק בגדולות. פסקה שכולה מספר סעיף ("2.1.")
# נספרת גם היא, כי ב-PDF המספר יוצא לעיתים בשורה משלו; אות לבדה לא, כי ב-PDF בעברית
# סוף מילה ("ם.") יוצא בשורה משלו. אות סופית אינה מספור סעיף. מספור עברי בגימטריה כולל שתי אותיות (יא., טו., כג.).
CLAUSE_RE = re.compile(
    r"^\s*(?:"
    r"(?i:section|clause|article|sec\.|art\.)\s*(\d+(?:\.\d+)*|[IVX]{1,6}|[A-Z])\b[.):]?"
    r"(?=\s*$|\s*[\-:.]|\s+[A-Z\"“(\[]|\s+[א-ת])"
    r"|\(?(\d+(?:\.\d+)+)\)?[.):]?"
    r"|\(?(\d+)\)?[.):]"
    r")(?:\s+|$)"
    r"|^\s*\(?(?:(טו|טז|[יכלמנסעפצ][אבגדהוזחט]|[אבגדהוזחטיכלמנסעפצקרשת])\)?[.):]|([ivx]{1,6}|[IVX]{1,6}|[A-Za-z])\)?[.)])\s+")
HEBREW = re.compile(r"[א-ת]")
TRACK_KINDS = ("ins", "del", "moveFrom", "moveTo")
SIDE_PARTS = re.compile(r"^word/(footnotes|endnotes|header\d*|footer\d*)\.xml$")
NO_TEXT = "אין שכבת טקסט (סרוק?)"
BODY_KINDS = ("p", "cell", "textbox")
# הסיבה הקצרה ב-unreadable, לפי האבחון של common/cli.docx_problem
DOCX_REASON = {"ole": "DOC ישן או קובץ מוצפן בסיסמה; שמרו כ-docx בלי סיסמה",
               "not_zip": "קובץ פגום: אינו ZIP תקין",
               "no_document": "אין בו word/document.xml: אינו מסמך Word",
               "unreadable": "הקובץ אינו נפתח"}


# סוגי קבצים שלקוח מעלה כהסכמים ושהמחלץ אינו קורא: ירשמו ב-unreadable עם הסיבה
UNSUPPORTED_DOC_EXT = (".html", ".htm", ".eml", ".msg", ".odt", ".xls", ".xlsx", ".ppt", ".pptx", ".jpg", ".jpeg", ".png", ".tif", ".tiff")

def clause_of(text: str) -> str:
    m = CLAUSE_RE.match(text or "")
    return next((g for g in m.groups() if g), "") if m else ""


def _rec(kind, acc, rej, hidden, **extra):
    rec = {"kind": kind, "text": acc}
    rec.update(extra)
    if rej != acc:
        rec["text_reject_all"] = rej
    if hidden:
        rec["hidden"] = hidden
    return rec


def _changes(p):
    """קטעי השינויים במעקב של פסקה (risk.extract_corpus.para_changes), כשדה `changes` ברשומה: מהם נגזר סיווג
    הראיה של ציטוט (ev_kind) בבונה, בלי לנחש. ריק כשאין שינויים, ואז השדה אינו נכתב."""
    chg = para_changes(p)
    return {"changes": chg} if chg else {}


def _walk(container, out, tables):
    """הפסקאות והטבלאות לפי הסדר. תוכן בבקר תוכן (sdt) נקרא כאילו היה במקום."""
    for el in container:
        if el.tag == q("p"):
            acc, rej, hid = para_texts(el)
            if acc or rej:
                out.append(_rec("p", acc, rej, hid, **_changes(el)))
            # פסקה בתוך תיבת טקסט אינה חלק מהפסקה העוטפת (para_texts מדלג
            # עליה), ולכן היא נשמרת לבד, פעם אחת
            for tx in el.iter(q("txbxContent")):
                for ip in tx.iter(q("p")):
                    a, r, h = para_texts(ip)
                    if a or r:
                        out.append(_rec("textbox", a, r, h, **_changes(ip)))
        elif el.tag == q("tbl"):
            _table(el, out, tables)
        elif el.tag == q("sdt"):
            content = el.find(q("sdtContent"))
            if content is not None:
                _walk(content, out, tables)


def _kids(el, tag):
    """הילדים הישירים מסוג tag, גם כשבקר תוכן (sdt) או customXml עוטף שורה או תא."""
    for c in el:
        if c.tag == tag:
            yield c
        elif c.tag == q("sdt"):
            inner = c.find(q("sdtContent"))
            if inner is not None:
                yield from _kids(inner, tag)
        elif c.tag == q("customXml"):
            yield from _kids(c, tag)


def _val(el, default):
    try:
        return int(el.get(q("val")))
    except (AttributeError, TypeError, ValueError):
        return default


def _cell_of(el):
    """התא הקרוב ביותר שמכיל את el (ולא תא של טבלה חיצונית)."""
    a = el.getparent()
    while a is not None and a.tag != q("tc"):
        a = a.getparent()
    return a


def _table(tbl, out, tables, parent=None):
    """טבלה לפי שורה ועמודת רשת. gridBefore ו-gridSpan קובעים את העמודה; vMerge: התא נשמר פעם אחת, בשורה
    שבה המיזוג מתחיל, עם row_span. טבלה מקוננת נשמרת כטבלה משלה אחרי התא שמכיל אותה, ואינה נכנסת לטקסט שלו."""
    tables[0] += 1
    t = tables[0]
    origin = {}          # עמודה -> רשומת התא שפותח מיזוג אנכי בעמודה הזו (או None, כשהוא ריק)
    for r_idx, tr in enumerate(_kids(tbl, q("tr"))):
        trpr = tr.find(q("trPr"))
        col = max(0, _val(trpr.find(q("gridBefore")) if trpr is not None else None, 0))
        for tc in _kids(tr, q("tc")):
            tcpr = tc.find(q("tcPr"))
            span = max(1, _val(tcpr.find(q("gridSpan")) if tcpr is not None else None, 1))
            vm = tcpr.find(q("vMerge")) if tcpr is not None else None
            vm = None if vm is None else (vm.get(q("val")) or "continue")
            accs, rejs, hids, chg = [], [], [], []
            for p in tc.iter(q("p")):
                if _cell_of(p) is not tc:     # פסקה של טבלה מקוננת: נשמרת בטבלה שלה
                    continue
                a, r, h = para_texts(p)
                accs.append(a)
                rejs.append(r)
                hids += h
                chg += para_changes(p)
            acc = " ".join(x for x in accs if x).strip()
            rej = " ".join(x for x in rejs if x).strip()
            rec = None
            if vm == "continue" and not (acc or rej):
                if origin.get(col) is not None:
                    origin[col]["row_span"] = origin[col].get("row_span", 1) + 1
            else:
                if acc or rej:
                    extra = {"table": t, "row": r_idx, "col": col}
                    if span > 1:
                        extra["col_span"] = span
                    if parent:
                        extra.update(parent_table=parent[0], parent_row=parent[1], parent_col=parent[2])
                    if chg:
                        extra["changes"] = chg
                    rec = _rec("cell", acc, rej, hids, **extra)
                    out.append(rec)
                if vm == "restart":
                    origin[col] = rec
                elif vm is None:
                    origin.pop(col, None)
            for inner in tc.iter(q("tbl")):
                if _cell_of(inner) is tc:
                    _table(inner, out, tables, parent=(t, r_idx, col))
            col += span


def read_docx(path: Path):
    with zipfile.ZipFile(path) as zf:
        # Strict Open XML: מרחבי השמות מנורמלים, כדי שהפסקאות יימצאו (risk/extract_corpus.OoxmlZip)
        z = OoxmlZip(zf)
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
    info = {"format": "docx", "tracked_counts": counts, "ooxml_strict": z.strict,
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

    # נתיב ארוך מ-260 תווים ב-Windows נפתח רק עם הקידומת \\?\ (common/paths.long_path). בלעדיה is_file
    # מחזיר False, והתיקייה נראית ריקה: 0 מסמכים, בלי הודעה. הנתיב בפלט נשמר בלי הקידומת (plain_path)
    root = Path(long_path(str(Path(args.root).expanduser()))).resolve()
    if not root.exists():
        print("לא נמצאו תיקייה או קובץ: %s" % plain_path(root)); return 1
    # גם מסמך יחיד עובר חילוץ (הערות מעריך הסיכונים 3.6, שינוי 21.3)
    single = root.is_file()
    files = [root] if single else sorted(root.rglob("*"))
    if root.is_file():
        root = root.parent

    engine = pdf_engine()
    docs, unreadable, seen, missing, bad_docx = [], [], {}, [], []
    for f in files:
        if not f.is_file():
            # מה שנמצא ברשימת התיקייה ואינו קובץ וגם אינו תיקייה לא נפתח (נתיב, הרשאה, קובץ OneDrive
            # שלא הורד): מדווח, עם קוד יציאה 1, ולא מדולג בשקט
            if not f.is_dir() and not f.name.startswith((".", "~$")) and \
                    not any(part in SKIP_DIRS for part in f.parts):
                missing.append("%s (הקובץ לא נמצא או שאינו נגיש; נתיב של %d תווים)"
                               % (str(f.relative_to(root)), len(plain_path(f))))
            continue
        if f.name.startswith((".", "~$")):
            continue
        if any(part in SKIP_DIRS for part in f.parts):
            continue
        ext = f.suffix.lower()
        if ext not in (".docx", ".txt", ".md", ".pdf", ".doc", ".rtf"):
            # סוג שנראה כמסמך אך אינו נקרא כאן: מדווח, ולא מדולג בשקט (הלקוח חושב שנקרא)
            if ext in UNSUPPORTED_DOC_EXT:
                unreadable.append("%s (סוג הקובץ %s אינו נתמך; שמרו כ-docx או כ-PDF)" % (str(f.relative_to(root)), ext[1:].upper()))
            continue
        rel = str(f.relative_to(root))
        if ext in (".doc", ".rtf"):
            unreadable.append("%s (פורמט %s אינו נקרא; שמרו כ-docx)" % (rel, ext[1:].upper()))
            continue
        try:
            if ext == ".docx":
                found = docx_problem(f, strict_ok=True)
                if found:
                    unreadable.append("%s (%s)" % (rel, DOCX_REASON.get(found[0], found[0])))
                    bad_docx.append(found[1])
                    continue
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

        # מסמך בלי טקסט בגוף (סריקה שהודבקה כתמונה, או קובץ ריק) אינו נקרא, ואינו "כפילות": טביעת
        # האצבע של תוכן ריק זהה בכל המסמכים הריקים, ומסמך כזה נבלע בעבר בשקט
        if not any((b.get("text") or "").strip() or (b.get("text_reject_all") or "").strip()
                   for b in paras if b["kind"] in BODY_KINDS):
            unreadable.append("%s (%s)" % (rel, NO_TEXT if ext in (".docx", ".pdf") else "קובץ ריק"))
            continue
        text = "\n".join(b["text"] for b in paras)
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if text.strip() and digest in seen:           # אותו תוכן בדיוק, שם קובץ אחר
            docs[seen[digest]]["duplicates"].append(rel); continue
        if text.strip():
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
        if info.get("ooxml_strict"):
            doc["ooxml_strict"] = True
        docs.append(doc)

    drafts = sum(1 for d in docs if d["looks_like_draft"])
    hidden_docs = [d["path"] for d in docs if d["hidden_total"]]
    out = {
        "root": plain_path(root),
        "document_count": len(docs),
        "duplicate_count": sum(len(d["duplicates"]) for d in docs),
        "draft_like_count": drafts,
        "pdf_count": sum(1 for d in docs if d["format"] == "pdf"),
        "hidden_text_documents": hidden_docs,
        "unreadable": missing + unreadable,
        "documents": docs,
    }
    # הקורפוס הוא ההסכמים של הלקוח, ו-`--out` שמצביע על אחד מהם דורס
    # אותו ב-JSON. `common/cli.guard_out` מסרב על קובץ קלט, על תיקיית
    # מקור ועל מסמך Word או PDF קיים
    try:
        out_path = guard_out(args.out,
                             inputs=[plain_path(f) for f in root.rglob("*") if f.is_file()])
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
    unreadable = missing + unreadable
    print("  לא נקראו כאן    : %d" % len(unreadable))
    for u in unreadable[:10]:
        print("    - %s" % u)
    if len(unreadable) > 10:
        print("    ועוד %d" % (len(unreadable) - 10))
    if unreadable:
        print("  אלה אינם בקובץ; הטיפול בהם לפי הוראות הרכיב.")
    if missing:
        print("שגיאה: %d קבצים בתיקייה לא נמצאו או אינם נגישים, והחילוץ אינו מלא (קוד יציאה 1)." % len(missing))
        return 1
    if single and bad_docx:
        # מסמך יחיד שאינו נקרא כ-Word (DOC, מוצפן, פגום): הודעה דו-לשונית וקוד 2, כמו בשאר נקודות הכניסה
        print(bad_docx[0])
        return DOCX_BAD_EXIT
    return 0


if __name__ == "__main__":
    sys.exit(main())
