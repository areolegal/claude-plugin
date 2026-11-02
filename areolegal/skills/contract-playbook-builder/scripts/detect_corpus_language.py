# -*- coding: utf-8 -*-
"""
מזהה את שפת ההסכמים בתיקיות שחוברו, כדי שאפשר יהיה לשאול את הלקוח שאלה מבוססת
במקום לנחש באיזו שפה הוא רוצה את הפלייבוק, את חומרי המשא ומתן ואת יתר התוצרים.

הסקריפט אינו מכריע ואינו כותב לפרופיל. הוא מדווח פיזור, והרכיב הקורא שואל.

הרצה:
  python3 detect_corpus_language.py --folders <תיקייה> [<תיקייה> ...] [--json out.json]
"""
import argparse
import io
import json
import os
import re
import sys
import zipfile
from collections import Counter
from datetime import date

for _s in (sys.stdout, sys.stderr):  # עברית בקונסולה שאינה UTF-8 (cp1252): בלי UnicodeEncodeError
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):   # לא TextIOWrapper (לכידה בבדיקות, pythonw)
        pass

HEB = re.compile(r"[֐-׿]")
LAT = re.compile(r"[A-Za-z]")
SKIP_DIRS = {"Areo-נתונים", "__pycache__", ".git", "node_modules"}
EXTS = (".docx", ".doc", ".pdf", ".txt", ".md", ".rtf")


def docx_text(path, limit=60000):
    try:
        with zipfile.ZipFile(path) as z:
            if "word/document.xml" not in z.namelist():
                return ""
            xml = z.read("word/document.xml").decode("utf-8", "ignore")
        txt = " ".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", xml, re.S))
        return re.sub(r"<[^>]+>|\s+", " ", txt)[:limit]
    except Exception:
        return ""


def pdf_text(path, limit=60000):
    """טקסט מ-PDF עם שכבת טקסט: PyMuPDF, ואם אינו מותקן, pypdf. PDF סרוק מחזיר "" ונספר כלא נקרא.

    לזיהוי השפה סופרים אותיות, ולכן סדר התווים אינו משנה: גם כשמנוע מחזיר עברית הפוכה, הספירה נכונה."""
    out = []
    try:
        try:
            import pymupdf as fitz  # PyMuPDF; השם fitz נשאר בגרסאות ישנות
        except ImportError:
            import fitz
        with fitz.open(path) as doc:
            for page in doc:
                out.append(page.get_text())
                if sum(len(x) for x in out) >= limit:
                    break
    except ImportError:
        try:
            from pypdf import PdfReader
            for page in PdfReader(path).pages:
                out.append(page.extract_text() or "")
                if sum(len(x) for x in out) >= limit:
                    break
        except Exception:
            return ""
    except Exception:
        return ""
    return re.sub(r"\s+", " ", " ".join(out))[:limit]


def text_of(path):
    """הטקסט לזיהוי, לפי סוג הקובץ. doc ו-rtf אינם נקראים כאן."""
    low = path.lower()
    if low.endswith(".docx"):
        return docx_text(path)
    if low.endswith(".pdf"):
        return pdf_text(path)
    if low.endswith((".txt", ".md")):
        try:
            return io.open(path, encoding="utf-8", errors="ignore").read()[:60000]
        except Exception:
            return ""
    return ""


def action_for(result, display_language):
    """מה עושים לפי `language-policy.md`, שלב 2, מלמעלה למטה. None כשלא נמסרה שפת הממשק."""
    if not display_language:
        return None
    if result.get("unreadable", 0) > result.get("readable", 0):
        return "ask_direct"
    if result.get("readable", 0) < 5:
        return "no_ask_small_corpus"
    if result.get("verdict") == "מובהק":
        return "no_ask_match" if result.get("dominant") == display_language else "ask"
    return "ask"


def classify(text):
    """שפת המסמך לפי היחס בין אותיות עבריות ללטיניות.

    הסף 15 אחוז אינו שרירותי: הסכם עברי כמעט תמיד מכיל שמות חברות, מונחי
    תוכנה וסעיפי דין באנגלית, ולכן נוכחות אנגלית אינה עושה אותו דו לשוני.
    מסמך נחשב דו לשוני רק כששתי השפות נושאות משקל ממשי.
    """
    he = len(HEB.findall(text))
    la = len(LAT.findall(text))
    tot = he + la
    if tot < 200:
        return None, 0.0
    share_he = float(he) / tot
    if share_he >= 0.85:
        return "he", share_he
    if share_he <= 0.15:
        return "en", share_he
    return "bilingual", share_he


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folders", nargs="+", required=True)
    ap.add_argument("--json")
    ap.add_argument("--max-files", type=int, default=400)
    ap.add_argument("--display-language", choices=("he", "en"),
                    help="שפת הממשק מהפרופיל; כשנמסרת, הפלט כולל את הפעולה לפי language-policy.md, שלב 2")
    args = ap.parse_args()

    counts = Counter()
    per_file = []
    scanned = 0
    for folder in args.folders:
        if not os.path.isdir(folder):
            print("תיקייה לא נמצאה: %s" % folder)
            continue
        for root, dirs, files in os.walk(folder):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for f in sorted(files):
                if scanned >= args.max_files:
                    break
                if not f.lower().endswith(EXTS) or f.startswith("~$"):
                    continue
                p = os.path.join(root, f)
                t = text_of(p)      # doc ו-rtf, ו-PDF סרוק, אינם נקראים כאן
                if not t:
                    counts["unreadable"] += 1
                    continue
                lang, share = classify(t)
                scanned += 1
                if not lang:
                    counts["too_short"] += 1
                    continue
                counts[lang] += 1
                per_file.append({"file": f, "folder": root, "language": lang,
                                 "hebrew_share": round(share, 2)})

    readable = counts["he"] + counts["en"] + counts["bilingual"]
    if not readable:
        print("לא נקרא אף מסמך שאפשר לזהות את שפתו. אם ההסכמים הם DOC, RTF או PDF סרוק, "
              "הסקריפט אינו קורא אותם, ויש לשאול את המשתמש ישירות.")
        result = {"readable": 0, "dominant": None, "unreadable": counts["unreadable"]}
    else:
        ranked = [(counts[k], k) for k in ("he", "en", "bilingual") if counts[k]]
        ranked.sort(reverse=True)
        top_n, top = ranked[0]
        share = float(top_n) / readable
        if share >= 0.8:
            verdict = "מובהק"
        elif share >= 0.6:
            verdict = "רוב, לא מובהק"
        else:
            verdict = "מעורב, אין שפה דומיננטית"
        result = {
            "generated_at": date.today().isoformat(),   # ISO ב-JSON (הכללים המשותפים 3.6)
            "folders": args.folders,
            "readable": readable,
            "unreadable": counts["unreadable"],
            "too_short": counts["too_short"],
            "distribution": {"he": counts["he"], "en": counts["en"],
                             "bilingual": counts["bilingual"]},
            "dominant": top,
            "dominant_share": round(share, 2),
            "verdict": verdict,
            "files": per_file,
            "usage_rule": ("הממצא מוצג למשתמש ואינו מכריע. שפת התוצר נקבעת בתשובת המשתמש "
                           "ונשמרת בפרופיל בשדה deliverable_language."),
        }
        names = {"he": "עברית", "en": "אנגלית", "bilingual": "דו לשוני"}
        print("נסרקו %d מסמכים קריאים" % readable)
        for k in ("he", "en", "bilingual"):
            if counts[k]:
                print("  %-12s %d מסמכים (%d%%)" % (
                    names[k], counts[k], round(100.0 * counts[k] / readable)))
        if counts["unreadable"]:
            print("  %d מסמכים לא נקראו (DOC, RTF, PDF סרוק או קובץ פגום)" % counts["unreadable"])
        print("שפה דומיננטית: %s, %s" % (names[result["dominant"]], verdict))

    act = action_for(result, args.display_language)
    if act:
        result["action"] = act
        print("פעולה לפי language-policy.md: %s" % act)

    if args.json:
        # הפלט לעולם אינו נכתב על אחד ההסכמים שנסרקו, או על מסמך קיים מסוג שהסקריפט קורא (EXTS)
        k = os.path.normcase(os.path.realpath(args.json))
        if os.path.isfile(k) and k.lower().endswith(EXTS):
            print("refused: --json הוא קובץ קלט או מסמך קיים: %s" % args.json, file=sys.stderr)
            sys.exit(2)
        d = os.path.dirname(os.path.abspath(args.json))
        if d and not os.path.isdir(d):
            os.makedirs(d)
        io.open(args.json, "w", encoding="utf-8").write(
            json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
