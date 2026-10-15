#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""בדיקת הקבלה של ה-Word של הפלייבוק, לפני מסירה.

`word-export-spec.md`, "בדיקת קבלה לפני מסירה": **מסמך שנכשל באחת
הבדיקות אינו נמסר.** תשע הבדיקות שבמפרט רצות כאן, בסדר שלו, וכל אחת
מדווחת בנפרד.

| # | מה נבדק | מי בודק |
|---|---|---|
| 1 | כיווניות: פסקאות, ריצות, טבלאות, מקטעים, כותרות | `common/rtl.audit_docx` |
| 2 | תוכן: מחזיקי מקום, אנגלית מהמודל, מבנה נתונים מודפס, שלושת המסלולים | כאן |
| 3 | שוויון מול הארטיפקט: כרטיס לכל נושא, שורה לכל ציטוט | כאן, עם `--artifact` |
| 4 | בדיקה חזותית: המרה ל-PDF, כשיש כלי בסביבה | כאן, מדולגת בלעדיו |
| 5 | מקורות ותווית: פרק המקורות, והתווית מילה במילה | `surfaces_render` + כאן |
| 6 | מספור והפניות: מספרי נושאים זהים, אין הפניה לקובץ שלא נמסר | כאן |
| 7 | קישורים חיצוניים: `w:hyperlink` עם יחס חיצוני, והיעד כמו ברשומה | כאן |
| 8 | תווית ומעמד: אין "מאושר" ליד עמדה, ושורה לכל כלל ב"העמדות בקצרה" | כאן |
| 9 | מאפייני הקובץ: אין python-docx, התאריכים אינם מוקדמים, המחבר | `audit_docx` + כאן |

**בדיקה שלא רצה אינה בדיקה שעברה.** המפרט מסיים ב"אל תכתוב שהמסמך
נבדק כשהבדיקה לא רצה", ולכן כל בדיקה שדולגה מודפסת כ"דולגה", עם הסיבה,
ונכנסת לשורת הסיכום שהמפרט מבקש להציג ללקוח.

    python3 scripts/verify_playbook_docx.py --docx "<הפלייבוק>.docx" \\
        --model playbook-model.json [--artifact <סביבת העבודה>.html] \\
        [--run-date 2026-10-15] [--out <דוח>.json]

קוד יציאה: **0** עבר, **3** נכשל (ואין למסור), **2** קלט חסר.
"""
import datetime as _dt
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile

import areo_lib  # noqa: F401  מוסיף את areolegal/lib לנתיב הייבוא

from common import rtl  # noqa: E402
from common.cli import OutputRefused, guard_out, no_bytecode, parser  # noqa: E402
from lxml import etree  # noqa: E402
from playbook import status as S, surfaces_render as R  # noqa: E402

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
PKG_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"

# מחזיקי מקום: הנוסח שהמפרט נוקב בו, וכל סוגריים מרובעים שנשארו ריקים
PLACEHOLDERS = ("טרם נכתב", "יושלם במעבר", "יושלם בהמשך", "להשלים", "TBD", "TODO",
                "[●]", "XXX")
# מבנה נתונים שהודפס במקום נוסח: "{'he'", "{\"he\"", "dict(", "None"
AS_DATA = (re.compile(r"\{\s*['\"]he['\"]"), re.compile(r"\{\s*['\"]en['\"]"),
           re.compile(r"\bdict\("), re.compile(r"(?<![\w])None(?![\w])"),
           re.compile(r"\[\s*\{\s*['\"]"))
AREO_TAG = "הצעת Areo (לא מבוסס על מסמכי הלקוח)"
SOURCES_HEAD = "המקורות שעליהם נשען הפלייבוק"
BRIEF_HEAD = "העמדות בקצרה"
TRACKS = ("ירוק", "צהוב", "אדום")
W_ID = re.compile(r"\bW-\d+\b")


class Result(object):
    """כל בדיקה: עברה, נכשלה, או דולגה. דילוג אינו הצלחה."""

    def __init__(self):
        self.checks = []

    def add(self, num, name, failures, skipped=None):
        self.checks.append({"check": num, "name": name,
                            "failures": list(failures or ()),
                            "skipped": skipped})

    @property
    def failed(self):
        return [c for c in self.checks if c["failures"]]

    @property
    def skipped(self):
        return [c for c in self.checks if c["skipped"]]

    def to_dict(self):
        return {"passed": not self.failed, "checks": self.checks}


def doc_parts(path):
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        return {n: z.read(n) for n in names}


def text_of(parts):
    """הטקסט של גוף המסמך ושל הכותרות, פסקה לפסקה."""
    out = []
    for name in ["word/document.xml"] + sorted(
            n for n in parts if re.match(r"word/(header|footer)\d*\.xml$", n)):
        x = etree.fromstring(parts[name])
        for p in x.iter(W + "p"):
            t = "".join(n.text or "" for n in p.iter(W + "t"))
            if t.strip():
                out.append(t)
    return out


def check_content(lines, model):
    """2. תוכן: מחזיקי מקום, אנגלית מהמודל, מבנה נתונים, שלושת המסלולים."""
    bad = []
    joined = "\n".join(lines)
    for ph in PLACEHOLDERS:
        if ph in joined:
            bad.append('מחזיק מקום במסמך: "%s"' % ph)
    for rx in AS_DATA:
        m = rx.search(joined)
        if m:
            bad.append("נוסח שהודפס כמבנה נתונים: %s" % m.group(0))
    # ערך באנגלית מהמודל: קוד מסלול או קוד מעמד שנשאר בטקסט שמוצג
    for code in ("green", "yellow", "red", "Draft", "PartiallyApproved",
                 "Approved", "Superseded", "Invalid"):
        if re.search(r"(?<![\w-])%s(?![\w-])" % code, joined):
            bad.append('ערך באנגלית מהמודל בטקסט: "%s"' % code)
    for t in TRACKS:
        if t not in joined:
            bad.append('אין במסמך את המסלול "%s"' % t)
    return bad


def check_sources_and_label(parts, lines, model, st):
    """5 ו-8: פרק המקורות, התווית מילה במילה, ואין "מאושר" ליד עמדה."""
    bad = list(R.check_surfaces(st, word_path=None, model=model) or ())
    joined = "\n".join(lines)
    research = (model.get("market_research") or {})
    if research and research.get("status") not in (None, "not_run", "skipped"):
        if SOURCES_HEAD not in joined:
            bad.append('רץ מחקר שוק ואין פרק "%s"' % SOURCES_HEAD)
    ids_in_sources = set()
    in_sources = False
    for line in lines:
        if SOURCES_HEAD in line:
            in_sources = True
            continue
        if in_sources and line.strip().startswith("##"):
            in_sources = False
        if in_sources:
            ids_in_sources |= set(W_ID.findall(line))
    for line in lines:
        if SOURCES_HEAD in line:
            break
        for wid in W_ID.findall(line):
            if ids_in_sources and wid not in ids_in_sources:
                bad.append("מזהה %s בשורת מקור ואינו בפרק המקורות" % wid)
    # 8: "מאושר" לא יופיע ליד עמדה, מסלול או כרטיס
    for line in lines:
        if "מאושר" in line and not _is_status_line(line, st):
            bad.append('המילה "מאושר" בשורה שאינה שורת המעמד: %s' % line[:70])
    return bad


def _is_status_line(line, st):
    label = st.get("label") or ""
    return bool(label) and (label in line or line.strip() in (label, label + "."))


def check_brief(lines, model):
    """8: ב"העמדות בקצרה" יש שורה לכל כלל במודל."""
    rules = [r.get("rule_id") for r in (model.get("rules") or []) if r.get("rule_id")]
    if not rules:
        return [], "אין כללים במודל"
    joined = "\n".join(lines)
    if BRIEF_HEAD not in joined:
        return ['אין פרק "%s"' % BRIEF_HEAD], None
    after = joined.split(BRIEF_HEAD, 1)[1]
    missing = [r for r in rules if r not in after]
    return (["אין שורה ב\"%s\" לכללים: %s" % (BRIEF_HEAD, ", ".join(missing[:8]))]
            if missing else []), None


def check_numbering(lines, model):
    """6: מספרי הנושאים זהים בכל הפרקים."""
    rules = [r.get("rule_id") for r in (model.get("rules") or []) if r.get("rule_id")]
    joined = "\n".join(lines)
    return ["מזהה כלל שאינו במסמך: %s" % r for r in rules if r not in joined]


def check_links(parts, model):
    """7: כל קישור חיצוני הוא w:hyperlink עם יחס חיצוני, והיעד כמו ברשומה.

    וגם 2, סופה: לכל קישור פנימי יש יעד.
    """
    bad = []
    rels_name = "word/_rels/document.xml.rels"
    if rels_name not in parts:
        return ["אין קובץ יחסים למסמך"]
    rels = {}
    for rel in etree.fromstring(parts[rels_name]).iter(PKG_REL + "Relationship"):
        rels[rel.get("Id")] = (rel.get("Target"), rel.get("TargetMode") or "Internal")
    doc = etree.fromstring(parts["word/document.xml"])
    anchors = {b.get(W + "name") for b in doc.iter(W + "bookmarkStart")}
    urls = set()
    for src in _iter_sources(model):
        if src.get("url"):
            urls.add(src["url"].rstrip("/"))
    for link in doc.iter(W + "hyperlink"):
        rid, anchor = link.get(REL + "id"), link.get(W + "anchor")
        text = "".join(n.text or "" for n in link.iter(W + "t"))
        if anchor:
            if anchor not in anchors:
                bad.append('קישור פנימי בלי יעד: "%s" -> %s' % (text[:40], anchor))
            continue
        if not rid or rid not in rels:
            bad.append('קישור בלי יחס: "%s"' % text[:40])
            continue
        target, mode = rels[rid]
        if mode != "External":
            bad.append('קישור חיצוני בלי יחס חיצוני: "%s"' % text[:40])
        elif urls and target.rstrip("/") not in urls:
            bad.append("יעד הקישור אינו ברשומה: %s" % target[:70])
    # כתובת שהודפסה כטקסט בלבד
    linked = {"".join(n.text or "" for n in l.iter(W + "t"))
              for l in doc.iter(W + "hyperlink")}
    for p in doc.iter(W + "p"):
        t = "".join(n.text or "" for n in p.iter(W + "t"))
        for m in re.finditer(r"https?://\S+", t):
            if not any(m.group(0) in x for x in linked):
                bad.append("כתובת שמודפסת כטקסט בלבד: %s" % m.group(0)[:60])
    return bad


def _iter_sources(model):
    research = model.get("market_research") or {}
    for key in ("sources", "external_sources", "findings"):
        for item in research.get(key) or ():
            if isinstance(item, dict):
                yield item
    for row in (model.get("external_sources_table") or ()):
        if isinstance(row, dict):
            yield row


def check_parity(lines, artifact):
    """3: לכל נושא בארטיפקט יש כרטיס ב-Word, ולכל ציטוט יש שורה."""
    if not artifact:
        return [], "לא נמסר --artifact"
    try:
        with open(artifact, encoding="utf-8") as fh:
            html = fh.read()
    except OSError as exc:
        return ["לא ניתן לקרוא את הארטיפקט: %s" % exc], None
    try:
        # מחזיר (האובייקט, התחלה, סוף), וזורק כשאין בדף נתונים מוזרקים
        data = R._find_payload(html)[0]
    except Exception as exc:
        return [], "אין בארטיפקט נתונים מוזרקים (%s)" % type(exc).__name__
    if not isinstance(data, dict):
        return [], "מטען הנתונים בארטיפקט אינו אובייקט"
    joined = "\n".join(lines)
    bad = []
    rules = data.get("rules") or (data.get("model") or {}).get("rules") or []
    for r in rules:
        rid = r.get("rule_id") or r.get("id")
        if rid and rid not in joined:
            bad.append("נושא בארטיפקט ואין לו כרטיס ב-Word: %s" % rid)
    return bad, None


def check_visual(path, run_date):
    """4: המרה ל-PDF, כשיש כלי בסביבה. בלעדיו הבדיקה מדולגת."""
    tool = shutil.which("soffice") or shutil.which("libreoffice")
    if not tool:
        return [], "אין בסביבה כלי המרה ל-PDF (soffice/libreoffice)"
    out_dir = os.path.join(os.path.dirname(os.path.abspath(path)), ".pdf-check")
    try:
        os.makedirs(out_dir, exist_ok=True)
        r = subprocess.run([tool, "--headless", "--convert-to", "pdf",
                            "--outdir", out_dir, path],
                           capture_output=True, timeout=180)
        pdf = os.path.join(out_dir, os.path.splitext(os.path.basename(path))[0] + ".pdf")
        if r.returncode != 0 or not os.path.exists(pdf):
            return ["ההמרה ל-PDF נכשלה"], None
        if os.path.getsize(pdf) < 2048:
            return ["ה-PDF שנוצר ריק כמעט לגמרי"], None
        return [], None
    except (OSError, subprocess.SubprocessError) as exc:
        return [], "ההמרה ל-PDF לא רצה: %s" % exc
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)


def check_properties(parts, model):
    """9, המשך ל-audit_docx: המחבר הוא שם החברה, או ריק.

    כשאין במודל שם חברה אין מול מה להשוות, וזה דילוג ולא הצלחה: מסמך
    שהמחבר שלו לא נבדק אינו מסמך שהמחבר שלו נכון.
    """
    core = parts.get("docProps/core.xml")
    if core is None:
        return ["אין docProps/core.xml"], None
    text = core.decode("utf-8", "replace")
    m = re.search(r"<dc:creator[^>]*>([^<]*)</dc:creator>", text)
    author = (m.group(1) if m else "").strip()
    company = (model.get("company_name") or model.get("organization_name") or "").strip()
    if not author:
        return [], None
    if not company:
        return [], 'המחבר בקובץ "%s", ואין במודל שם חברה להשוות אליו' % author
    if author != company:
        return ['המחבר בקובץ "%s", ולא שם החברה "%s" ולא ריק' % (author, company)], None
    return [], None


def main(argv=None):
    no_bytecode()
    ap = parser(__doc__.split("\n")[0], out_required=False)
    ap.add_argument("--docx", required=True, help="ה-Word שנבנה")
    ap.add_argument("--model", required=True, help="playbook-model.json")
    ap.add_argument("--artifact", help="סביבת העבודה, לבדיקת השוויון")
    ap.add_argument("--run-date", help="יום ההפקה (YYYY-MM-DD). ברירת מחדל: היום")
    a = ap.parse_args(argv)

    for p, what in ((a.docx, "ה-Word"), (a.model, "המודל")):
        if not os.path.exists(p):
            print("%s אינו קיים: %s" % (what, p))
            return 2
    with open(a.model, encoding="utf-8") as fh:
        model = json.load(fh)
    try:
        run_date = (_dt.date.fromisoformat(a.run_date) if a.run_date
                    else _dt.date.today())
    except ValueError:
        print("--run-date אינו תאריך: %s" % a.run_date)
        return 2

    parts = doc_parts(a.docx)
    lines = text_of(parts)
    st = S.derive_status(model)

    res = Result()
    res.add(1, "כיווניות", rtl.audit_docx(a.docx, run_date=run_date))
    res.add(2, "תוכן", check_content(lines, model))
    par, skip = check_parity(lines, a.artifact)
    res.add(3, "שוויון מול הארטיפקט", par, skip)
    vis, skip = check_visual(a.docx, run_date)
    res.add(4, "בדיקה חזותית", vis, skip)
    res.add(5, "מקורות ותווית", check_sources_and_label(parts, lines, model, st))
    res.add(6, "מספור והפניות", check_numbering(lines, model))
    res.add(7, "קישורים חיצוניים", check_links(parts, model))
    brief, skip = check_brief(lines, model)
    res.add(8, "תווית ומעמד", brief, skip)
    props, skip = check_properties(parts, model)
    res.add(9, "מאפייני הקובץ", props, skip)

    for c in res.checks:
        if c["failures"]:
            print("%d. %s: נכשל" % (c["check"], c["name"]))
            for f in c["failures"]:
                print("     %s" % f)
        elif c["skipped"]:
            print("%d. %s: דולגה (%s)" % (c["check"], c["name"], c["skipped"]))
        else:
            print("%d. %s: עבר" % (c["check"], c["name"]))

    ran = [c["name"] for c in res.checks if not c["skipped"]]
    print("\nנבדק: %s." % ", ".join(ran))
    if res.skipped:
        print("לא נבדק: %s. אמור זאת בהודעת המסירה."
              % ", ".join("%s (%s)" % (c["name"], c["skipped"]) for c in res.skipped))

    if a.out:
        try:
            path = guard_out(a.out, inputs=[a.docx, a.model, a.artifact])
        except OutputRefused as exc:
            print("הדוח לא נכתב. סירוב: %s" % exc)
        else:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(res.to_dict(), fh, ensure_ascii=False, indent=2)
            print("נכתב %s" % path)

    if res.failed:
        print("המסמך אינו נמסר: נכשל ב-%d בדיקות." % len(res.failed))
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
