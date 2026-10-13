#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""בונה את מניפסט הקורפוס, וסופר בקוד כמה הסכמים יש בכל סוג.

הספירה אינה הערכה של המודל, כי המסלול נגזר ממנה: 20 ומעלה (`full`),
7 עד 19 (`below20`), 1 עד 6 (`below7`) ואפס (`none`). טעות של שני קבצים
מזיזה מסלול. השמות והמבנה כאן הם אלה של `corpus_basis` ב-`playbook-schema.md`,
כדי שהבונה יעתיק מספרים ולא יתרגם אותם.

מה שאינו נספר כהסכם: עותק זהה (בבתים או בתוכן), גרסה אחרת של אותו משא ומתן,
תיקון להסכם (נספר עם ההסכם שהוא מתקן), ותבנית של החברה.

שני מהלכים, כי הסיווג לסוגים נעשה לפי הכותרת והפתיח ואינו עבודה של קוד:
  1. python3 build_corpus_manifest.py <תיקייה> --out corpus-manifest.json
     מחזיר לכל קובץ `title_hint`, ולפיו מסווגים לסוגים.
  2. python3 build_corpus_manifest.py <תיקייה> --families families.json --out ...
     מחזיר `by_family`, ובו בלוק `corpus_basis` לכל סוג.

families.json:
  {"families": [{"contract_family_id": "nda_receiving", "label": "הסכם סודיות",
                 "company_role_code": "receiving", "paths": ["a.docx", ...]}]}
"""
import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
TEXT_EXT = {".txt", ".md", ".csv", ".json"}
# סימני תבנית (`corpus-pipeline.md`, פרק 2): מצייני מקום, היעדר חתימה,
# או שם קובץ שאומר זאת
TEMPLATE_NAME = re.compile(r"תבנית|נוסח סטנדרטי|נוסח אחיד|template|master form|standard form", re.I)
PLACEHOLDER = re.compile(r"_{4,}|\.{6,}|\[[^\]]{0,40}(שם|תאריך|סכום|להשלים|insert|name|date|amount)[^\]]{0,40}\]"
                         r"|<<[^>]{1,40}>>|\{\{[^}]{1,40}\}\}", re.I)
SIGNED = re.compile(r"ולראיה באו הצדדים על החתום|חתימת הצדדים|/s/|signature of the parties", re.I)
AMENDMENT = re.compile(r"תיקון\s*(מס'?\s*)?\d*\s*ל|נספח תיקון|תוספת להסכם"
                       r"|amendment\s*(no\.?\s*\d+)?\s*to|addendum\s*to", re.I)
# חידוש אינו גרסה של ההסכם הקודם אלא משא ומתן חדש
RENEWAL_TOKENS = {"חידוש", "מחודש", "הארכה", "הארכת", "renewal", "renewed",
                  "extension", "extended", "new"}
BANDS = [(20, None, "full"), (7, 19, "below20"), (1, 6, "below7"), (0, 0, "none")]


def band_of(units):
    return next(name for lo, hi, name in BANDS if units >= lo and (hi is None or units <= hi))


def sha256_bytes(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_text(path):
    """טקסט לצורך השוואה. docx וקבצי טקסט נקראים; השאר מדווחים כלא נקראים."""
    try:
        if path.suffix.lower() == ".docx":
            root = ET.fromstring(zipfile.ZipFile(path).read("word/document.xml"))
            return "\n".join("".join(t.text or "" for t in p.iter(W + "t"))
                             for p in root.iter(W + "p"))
        if path.suffix.lower() in TEXT_EXT:
            return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None
    return None


def normalize(text):
    """מוריד רווחים ותאריכים, כדי ששני עותקים עם עימוד שונה ייראו זהים."""
    t = re.sub(r"[‎‏‪-‮]", "", text or "")
    t = re.sub(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b", " ", t)
    return re.sub(r"\s+", " ", t).strip().lower()


def title_hint(text, name):
    """הכותרת והפתיח, ולפיהם המודל מסווג לסוג בלי לקרוא את ההסכם."""
    if not text:
        return Path(name).stem
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return " / ".join(lines[:3])[:300] if lines else Path(name).stem


def shingles(text, size=9, step=3):
    words = text.split()
    return {hashlib.md5(" ".join(words[i:i + size]).encode("utf-8")).digest()[:8]
            for i in range(0, max(1, len(words) - size), step)}


def similarity(a, b):
    return len(a & b) / float(len(a | b)) if a and b else 0.0


def normalized_stem(name):
    s = Path(name).stem.lower()
    s = re.sub(r"\b(v|ver|version|rev|draft|final|signed)[-_ ]?\d*[a-z]?\b", " ", s)
    s = re.sub(r"\b20\d{2}[-_. ]\d{1,2}[-_. ]\d{1,2}\b", " ", s)
    s = re.sub(r"\b(copy|עותק)\b", " ", s)
    s = re.sub(r"[^a-z0-9֐-׿]+", " ", s)
    return " ".join(s.split())


def same_negotiation(a, b):
    """האם שני השמות הם אותו משא ומתן: אותם אסימונים, או שאחד פותח את השני.
    השוואת אסימונים ולא מחרוזות, כדי ש"nda 1" לא ייראה כמו תחילת "nda 10".
    חידוש או הארכה הוא משא ומתן חדש (`corpus-pipeline.md`, פרק 2), ולכן
    תוספת כזאת בשם מפרידה בין השניים."""
    x, y = a.split(), b.split()
    if not x or not y:
        return False
    if x[:len(y)] == y:
        extra = x[len(y):]
    elif y[:len(x)] == x:
        extra = y[len(x):]
    else:
        return False
    return not (set(extra) & RENEWAL_TOKENS)


def looks_like_template(name, text):
    hits = []
    if TEMPLATE_NAME.search(name):
        hits.append("file name")
    if text:
        if len(PLACEHOLDER.findall(text)) >= 3:
            hits.append("placeholders")
        if not SIGNED.search(text):
            hits.append("no signature block")
    # שם הקובץ לבדו מספיק; אחרת דרושים שני סימנים, כדי לא לפסול הסכם חתום
    return ("file name" in hits) or (len(hits) >= 2), hits


def scan(root):
    rows = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.name.startswith("~$") or p.name == ".DS_Store":
            continue
        text = read_text(p)
        norm = normalize(text) if text else None
        row = {
            "path": str(p.relative_to(root)), "size": p.stat().st_size,
            "extension": p.suffix.lower(), "sha256": sha256_bytes(p),
            "normalized_stem": normalized_stem(p.name),
            "text_read": text is not None,
            "text_sha256": hashlib.sha256(norm.encode("utf-8")).hexdigest() if norm else None,
            "title_hint": title_hint(text, p.name),
            "doc_role": "agreement",
        }
        is_tpl, signs = looks_like_template(p.name, text)
        if is_tpl:
            row["doc_role"], row["template_signs"] = "template", signs
        if AMENDMENT.search(p.name) or (text and AMENDMENT.search(text[:400])):
            row["doc_role"] = "amendment"
        row["_shingles"] = shingles(norm) if norm else None
        rows.append(row)
    return rows


def count(rows, near_threshold):
    """בלוק `corpus_basis` לקבוצת קבצים אחת, בשמות של playbook-schema.md."""
    removed, merged, attached, templates = [], [], [], []
    # תבנית אינה הסכם, והיא נרשמת בנפרד כדי שאפשר יהיה להצביע עליה בשלב 2ו
    pool = []
    for r in rows:
        if r["doc_role"] == "template":
            templates.append({"path": r["path"], "signs": r.get("template_signs", [])})
        else:
            pool.append(r)

    # עותק זהה: אותם בתים, או אותו תוכן אחרי נרמול. נשמר השם הקצר מבין
    # הזהים, כי "הסכם - עותק" הוא העותק וההסכם הוא המקור
    seen, uniq = {}, []
    for r in sorted(pool, key=lambda x: (len(x["path"]), x["path"])):
        key = r["text_sha256"] or r["sha256"]
        if key in seen:
            removed.append({"kept": seen[key], "removed": r["path"],
                            "same": "text" if r["text_sha256"] else "bytes"})
        else:
            seen[key] = r["path"]
            uniq.append(r)
    uniq.sort(key=lambda x: x["path"])

    # גרסאות של אותו משא ומתן: אותו שם קובץ וגם טקסט כמעט זהה. שני התנאים
    # נדרשים, כי הסכמים מאותו סוג מול צדדים שונים דומים זה לזה מאוד, ונוסח
    # שחוזר על עצמו הוא הראיה החזקה לירוק ולא כפילות (`corpus-pipeline.md`,
    # פרק 2). השם נבדק ראשון, כי הוא זול ופוסל את רוב הזוגות
    gone = {}
    for i, a in enumerate(uniq):
        if a["path"] in gone or not a["_shingles"]:
            continue
        for b in uniq[i + 1:]:
            if b["path"] in gone or not b["_shingles"]:
                continue
            if not same_negotiation(a["normalized_stem"], b["normalized_stem"]):
                continue
            sim = similarity(a["_shingles"], b["_shingles"])
            if sim >= near_threshold:
                gone[b["path"]] = True
                merged.append({"kept": a["path"], "merged": b["path"], "similarity": round(sim, 3)})
    uniq = [r for r in uniq if r["path"] not in gone]

    # תיקון נספר עם ההסכם שהוא מתקן: שם ההסכם מופיע בתוך שם התיקון,
    # ולכן מחפשים הכלה ולא שוויון
    bases = [r for r in uniq if r["doc_role"] == "agreement" and r["normalized_stem"]]
    counted, orphan_amendments = [], []
    for r in uniq:
        if r["doc_role"] != "amendment":
            counted.append(r["path"])
            continue
        cands = [x for x in bases if x["normalized_stem"] == r["normalized_stem"]
                 or x["normalized_stem"] in r["normalized_stem"]]
        if cands:
            base = max(cands, key=lambda x: len(x["normalized_stem"]))
            attached.append({"path": r["path"], "amends": base["path"]})
        else:
            # תיקון שההסכם שהוא מתקן אינו בתיקייה נספר כמשא ומתן אחד ומסומן
            # (`corpus-pipeline.md`, פרק 2)
            orphan_amendments.append(r["path"])
            counted.append(r["path"])

    units = len(counted)
    return {
        "files": len(rows), "agreement_units": units, "band": band_of(units),
        "counted_agreements": counted,
        "removed_duplicates": removed, "merged_versions": merged,
        "amendments_attached": attached, "excluded_templates": templates,
        # שניהם עשויים להזיז את הרצועה, ולכן מדווחים ולא מוכרעים בשקט
        "needs_review": {
            "unreadable": [r["path"] for r in rows if not r["text_read"]],
            "amendments_without_base": orphan_amendments},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--out", default="corpus-manifest.json")
    ap.add_argument("--families", help="קובץ סיווג לסוגים, אחרי שלב 2א")
    ap.add_argument("--near", type=float, default=0.92, help="סף דמיון לאיחוד גרסאות")
    a = ap.parse_args()
    root = Path(a.root).resolve()
    if not root.is_dir():
        sys.exit("אין תיקייה כזאת: %s" % root)
    rows = scan(root)
    if not rows:
        sys.exit("התיקייה ריקה: %s" % root)

    out = {"root": str(root), "file_count": len(rows),
           "corpus_basis_all_files": count(rows, a.near)}
    if a.families:
        spec = json.loads(Path(a.families).read_text(encoding="utf-8"))
        by_path, fams = {r["path"]: r for r in rows}, []
        claimed = set()
        for f in spec.get("families", []):
            picked, missing = [], []
            for p in f.get("paths", []):
                (picked if p in by_path else missing).append(p)
                claimed.add(p)
            fam = {k: f.get(k) for k in ("contract_family_id", "label", "company_role_code")}
            fam["corpus_basis"] = count([by_path[p] for p in picked], a.near) if picked else None
            if missing:
                fam["paths_not_found"] = missing
                print("אזהרה: בסוג %s יש %d נתיבים שאינם בתיקייה: %s"
                      % (f.get("label") or f.get("contract_family_id"), len(missing),
                         ", ".join(missing[:4])))
            fams.append(fam)
        out["by_family"] = fams
        out["unclassified"] = [r["path"] for r in rows if r["path"] not in claimed]
    for r in rows:
        r.pop("_shingles", None)
    out["files"] = rows
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    def report(name, b):
        print("%s: %d קבצים, %d הסכמים, רצועה %s" % (name, b["files"], b["agreement_units"], b["band"]))
        print("   נוכו: %d כפילויות, %d גרסאות, %d תיקונים, %d תבניות"
              % (len(b["removed_duplicates"]), len(b["merged_versions"]),
                 len(b["amendments_attached"]), len(b["excluded_templates"])))
        for k, label in (("unreadable", "לא נקרא טקסט"),
                         ("amendments_without_base", "תיקון בלי הסכם בסיס"),
                         ):
            v = b["needs_review"][k]
            if not v:
                continue
            names = [x if isinstance(x, str) else " ו-".join(x["files"]) for x in v[:3]]
            print("   דורש בדיקה, %s: %s" % (label, "; ".join(names)))

    print("נכתב %s" % a.out)
    if "by_family" in out:
        for f in out["by_family"]:
            if f["corpus_basis"]:
                report(f.get("label") or f.get("contract_family_id") or "סוג", f["corpus_basis"])
        if out["unclassified"]:
            print("לא סווגו לסוג: %d קבצים" % len(out["unclassified"]))
    else:
        report("כל הקבצים", out["corpus_basis_all_files"])
        print("הסיווג לסוגים נעשה לפי title_hint, ואז מריצים שוב עם --families")


if __name__ == "__main__":
    main()
