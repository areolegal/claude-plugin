#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""בדיקת הקבלה של ה-Word של הפלייבוק, לפני מסירה.

`word-export-spec.md`, "בדיקת קבלה לפני מסירה": **מסמך שנכשל באחת
הבדיקות אינו נמסר.** תשע הבדיקות שבמפרט רצות כאן, בסדר שלו, וכל אחת
מדווחת בנפרד.

| # | מה נבדק | מי בודק |
|---|---|---|
| 1 | כיווניות: פסקאות, ריצות, טבלאות, מקטעים, כותרות | `common/rtl.audit_docx` |
| 2 | תוכן: מחזיקי מקום, אנגלית מהמודל, מבנה נתונים מודפס, שלושת המסלולים, מקפים (ציטוט מוחרג) | כאן |
| 3 | שוויון מול הארטיפקט: כרטיס לכל נושא, שורה לכל ציטוט | כאן, עם `--artifact` |
| 4 | בדיקה חזותית: המרה ל-PDF, כשיש כלי בסביבה | כאן, מדולגת בלעדיו |
| 5 | מקורות ותווית: פרק המקורות, והתווית מילה במילה | `surfaces_render` + כאן |
| 6 | מספור והפניות: מספרי נושאים זהים, אין הפניה לקובץ שלא נמסר | כאן |
| 7 | קישורים חיצוניים: `w:hyperlink` עם יחס חיצוני, והיעד כמו ברשומה | כאן |
| 8 | תווית ומעמד: אין "מאושר" כטענת מעמד (ציטוט מוחרג), ושורה לכל כלל ב"העמדות בקצרה" | כאן |
| 9 | מאפייני הקובץ: אין python-docx, התאריכים אינם מוקדמים, המחבר | `audit_docx` + כאן |

**שתי שפות.** שפת המסמך נקבעת ב-`--lang`, ובלעדיו מהמסמך עצמו (language במאפייני הקובץ, ובהיעדרו bidi
במקטע). מסמך עברי עובר את בדיקת ה-RTL הקיימת (`audit_docx`). מסמך באנגלית עובר את בדיקת ה-LTR: אין bidi,
rtl, bidiVisual או rtlGutter בשום פסקה, ריצה, טבלה או מקטע, ושאר בדיקות הקובץ (מספור, מאפיינים) כמו בעברית.
כותרות הפרקים, שמות המסלולים והתווית נבדקים בשפת המסמך.

**בדיקה שלא רצה אינה בדיקה שעברה.** המפרט מסיים ב"אל תכתוב שהמסמך
נבדק כשהבדיקה לא רצה", ולכן כל בדיקה שדולגה מודפסת כ"דולגה", עם הסיבה,
ונכנסת לשורת הסיכום שהמפרט מבקש להציג ללקוח.

    python3 scripts/verify_playbook_docx.py --docx "<הפלייבוק>.docx" \\
        --model playbook-model.json [--profile פרופיל-לקוח.json] \\
        [--artifact <סביבת העבודה>.html] [--run-date 2026-10-15] [--out <דוח>.json]

`--out` אופציונלי: נתיב לדוח JSON (`{"passed", "checks"}`), לצד ההדפסה. בלעדיו: הדפסה בלבד. נתיב
שאסור לכתוב אליו (קובץ קלט, תיקיית מקור) אינו נכתב, ומודפס הסירוב; קוד היציאה נקבע רק לפי הבדיקות.

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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # גם ב-python -I, שאינו מוסיף את תיקיית הסקריפט
import areo_lib  # noqa: F401  מוסיף את areolegal/lib לנתיב הייבוא

from common import rtl  # noqa: E402
from common.cli import OutputRefused, guard_out, load_docx_or_explain, no_bytecode, parser  # noqa: E402
from lxml import etree  # noqa: E402
from playbook import status as S, surfaces_render as R  # noqa: E402

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
PKG_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"

# מחזיקי מקום: הנוסח שהמפרט נוקב בו, וכל סוגריים מרובעים שנשארו ריקים
PLACEHOLDERS = ("טרם נכתב", "יושלם במעבר", "יושלם בהמשך", "TBD", "TODO", "[●]", "XXX")
# "להשלים" הוא מחזיק מקום רק כשהוא עומד לבד ("[להשלים]", "להשלים." בסוף שדה), ולא הפועל בתוך משפט
# ("מבקשים להשלים את ההתקנה").
PLACEHOLDER_RX = re.compile(r"\[\s*להשלים\s*\]|(?:^|:\s*)להשלים\s*[.]?\s*$|\[\s*to complete\s*\]", re.M | re.I)
# מבנה נתונים שהודפס במקום נוסח: "{'he'", "{\"he\"", "dict(", "None"
AS_DATA = (re.compile(r"\{\s*['\"]he['\"]"), re.compile(r"\{\s*['\"]en['\"]"),
           # None כערך שהודפס (שורה שכולה None, או אחרי נקודתיים, פסיק או סוגריים), ולא "None of" בפרוזה
           re.compile(r"\bdict\("), re.compile(r"(?:^|[:=,\[(]\s*)None(?=\s*(?:$|[,\]}).;]))", re.M),
           re.compile(r"\[\s*\{\s*['\"]"))
AREO_TAG = "הצעת Areo (לא מבוסס על מסמכי הלקוח)"
SOURCES_HEAD = "המקורות שעליהם נשען הפלייבוק"
BRIEF_HEAD = "העמדות בקצרה"
TRACKS = ("ירוק", "צהוב", "אדום")
W_ID = re.compile(r"\bW-\d+\b")
# אותם שמות במסמך באנגלית (build_playbook_docx.TX["en"])
NAMES = {"he": {"sources": SOURCES_HEAD, "brief": BRIEF_HEAD, "tracks": TRACKS,
                "approved": re.compile("מאושר")},
         "en": {"sources": "Sources the playbook relies on", "brief": "Positions at a glance",
                "tracks": ("Green", "Yellow", "Red"), "approved": re.compile(r"\bapproved\b", re.I)}}
# 8: האיסור הוא על טענת מעמד, ולא על המילה. "דוח שעות מאושר" בציטוט מהסכם, או בתיאור של סעיף
# בהסכם, אינו טענה שעמדה אושרה, ובהרצה חיה ה-Word נכשל עליו. טענת מעמד היא המילה
# לבדה (תא או תווית), או המילה בסמוך (עד שתי מילים) למה שיש לו מעמד: הפלייבוק, המדיניות, עמדה,
# מסלול, כרטיס, או "מעמד"/"סטטוס" עצמם
_APPR_HE = r"(?:[והשכלמב]{0,3})(?:מאושר(?:ת|ים|ות)?|אושר(?:ה|ו)?)"
_SUBJ_HE = r"(?:[והשכלמב]{0,3})(?:פלייבוק|מדיניות|עמד(?:ה|ת|ות)|מסלול(?:ים)?|כרטיס(?:ים)?|מעמד|סטטוס)"
_APPR_EN = r"approved"
_SUBJ_EN = r"(?:playbooks?|polic(?:y|ies)|positions?|tracks?|cards?|status)"
_GAP = r"(?:[^\w\n]+\w+){0,2}[^\w\n]+"
STATUS_CLAIM = {
    lang: re.compile(r"^\W*%(a)s\W*$|(?<!\w)%(s)s%(g)s%(a)s(?!\w)|(?<!\w)%(a)s%(g)s%(s)s(?!\w)"
                     % {"a": a, "s": s, "g": _GAP}, re.I)
    for lang, a, s in (("he", _APPR_HE, _SUBJ_HE), ("en", _APPR_EN, _SUBJ_EN))}
# ציטוט בתוך שורה שהמערכת כתבה: בין מירכאות, כשהפותחת אחרי רווח או תחילת שורה (ולא גרשיים של
# קיצור כמו בע"מ) והסוגרת לפני רווח, פיסוק או סוף שורה
INLINE_QUOTE = re.compile(r'(?:(?<=^)|(?<=[\s(\[:]))(?:"[^"\n]+"|“[^”\n]+”|„[^“”\n]+[“”]|«[^»\n]+»)(?=$|[\s.,;:)\]])')
# מקף ארוך וקצר אסורים בטקסט שהמערכת כותבת (output-rules.md, word-export-spec.md, "כללי נוסח").
# ציטוט מילולי ממסמך מקור נשאר כלשונו, כולל הפיסוק, ולכן מוחרג
DASHES = re.compile("[\u2013\u2014]")
# קודים מהמודל שאסור שיודפסו. באנגלית Draft, Approved וכו' הן מילים רגילות, ולכן נבדקים שם רק קודים מורכבים
MODEL_CODES = {"he": ("green", "yellow", "red", "Draft", "PartiallyApproved", "Approved", "Superseded", "Invalid"),
               "en": ("PartiallyApproved", "AgreeWithComments", "NotApproved", "own_plus_market", "market_built",
                      "areo_proposal", "market_standard", "NotResearched", "NotAssessed")}
# מחקר שוק שלא רץ: כל הערכים שבסכמה (playbook-schema.md: Performed | Partial | NotPerformed) ושמות קודמים
NOT_RUN = (None, "", "not_run", "skipped", "NotPerformed", "not_performed", "NotRun", "none")


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


def doc_lang(parts):
    """he או en: language ב-core.xml, ובהיעדרו bidi במקטע הראשון."""
    core = (parts.get("docProps/core.xml") or b"").decode("utf-8", "replace")
    m = re.search(r"<dc:language>([^<]*)</dc:language>", core)
    if m and m.group(1).strip():
        return "en" if m.group(1).strip().lower().startswith("en") else "he"
    doc = etree.fromstring(parts["word/document.xml"])
    sect = next(doc.iter(W + "sectPr"), None)
    return "he" if sect is not None and sect.find(W + "bidi") is not None else "en"


HEB = re.compile("[֐-׿]")
# מסמך באנגלית שרוב פסקאותיו בעברית אינו מסמך באנגלית. עד הסף הזה נסלח (שם החברה, ציטוט מעברית); מעליו המסמך
# חייב לומר ללקוח שהטקסט בעברית (LANG_NOTE), אחרת הוא נכשל
HEBREW_SHARE_LIMIT = 0.2
LANG_NOTE_EN = "written in Hebrew"


def audit_ltr(path, run_date=None):
    """1, במסמך באנגלית: LTR מלא לטקסט הלועזי, ו-RTL מלא לכל פסקה שיש בה עברית. פסקה עם עברית חייבת bidi וריצה עם
    אות עברית חייבת rtl (בלי זה Word מציג אותה משמאל לימין); פסקה בלי עברית אינה bidi, ובמסמך אין w:bidiVisual,
    ולא bidi או rtlGutter במקטע. בדיקות המספור ומאפייני הקובץ של audit_docx חלות כמו בעברית. וגם: מסמך באנגלית
    שיותר מחמישית מפסקאותיו בעברית חייב להגיד זאת (LANG_NOTE_EN), ואחרת הוא אינו תוצר באנגלית."""
    problems = [x for x in rtl.audit_docx(path, run_date=run_date, require_hebrew=False)
                if x.startswith(("מאפייני הקובץ", "מספור", "אין sectPr"))]
    total = heb = 0
    note = False
    with zipfile.ZipFile(path) as z:
        for part in ["word/document.xml"] + sorted(n for n in z.namelist() if re.match(
                r"word/(header|footer)\d*\.xml$|word/comments\.xml$|word/styles\.xml$", n)):
            x = etree.fromstring(z.read(part))
            missing_p = missing_r = 0
            for p in x.iter(W + "p"):
                ppr = p.find(W + "pPr")
                has_bidi = ppr is not None and ppr.find(W + "bidi") is not None
                t = "".join(n.text or "" for n in p.iter(W + "t"))
                is_heb = bool(HEB.search(t))
                heb_dom = is_heb and len(HEB.findall(t)) >= len(re.findall("[A-Za-z]", t))
                if part == "word/document.xml" and t.strip():
                    total += 1
                    heb += is_heb
                    note = note or LANG_NOTE_EN in t
                if has_bidi and not is_heb:
                    problems.append("%s: פסקה עם bidi במסמך באנגלית: %s" % (part, t[:40]))
                if heb_dom and not has_bidi:
                    missing_p += 1
                    if missing_p <= 3:
                        problems.append("%s: פסקה בעברית בלי bidi במסמך באנגלית: %s" % (part, t[:40]))
                for r in p.iter(W + "r"):
                    rt = "".join(n.text or "" for n in r.iter(W + "t"))
                    rpr = r.find(W + "rPr")
                    el = rpr.find(W + "rtl") if rpr is not None else None
                    on = el is not None and el.get(W + "val") not in ("0", "false")
                    if HEB.search(rt) and not on:
                        missing_r += 1
                    elif on and not HEB.search(rt):
                        # ריצה של רווח, פיסוק או מספר בתוך פסקה עברית היא חלק מהפסקה: מותרת
                        if not is_heb and rt.strip():
                            problems.append("%s: ריצה לטינית עם rtl במסמך באנגלית: %s" % (part, rt[:30]))
            if missing_p > 3:
                problems.append("%s: עוד %d פסקאות בעברית בלי bidi" % (part, missing_p - 3))
            if missing_r:
                problems.append("%s: %d ריצות בעברית בלי rtl במסמך באנגלית" % (part, missing_r))
            for _ in x.iter(W + "bidiVisual"):
                problems.append("%s: טבלה עם bidiVisual במסמך באנגלית" % part)
                break
            for sp in x.iter(W + "sectPr"):
                if sp.find(W + "bidi") is not None or sp.find(W + "rtlGutter") is not None:
                    problems.append("%s: מקטע עם bidi או rtlGutter במסמך באנגלית" % part)
    if total and heb / total > HEBREW_SHARE_LIMIT and not note:
        problems.append("מסמך באנגלית ש-%d%% מפסקאותיו בעברית, בלי הודעה ללקוח שהטקסט בעברית" % round(100 * heb / total))
    return problems


def _qkey(text):
    """מפתח השוואה לציטוט: אותיות וספרות בלבד. ה-Word מנרמל רווחים ושובר שורות, והמפתח לא."""
    return re.sub(r"[\W_]+", "", text or "")


def model_quotes(model):
    """המפתחות של כל ציטוט מילולי במודל: `quote` בכל מקום, ו-`text` בתוך evidence/citations
    (ה-Word מדפיס `quote` ובהיעדרו `text`, build_playbook_docx.ev_table)."""
    keys = set()

    def walk(v, parent=""):
        if isinstance(v, dict):
            for k, x in v.items():
                if isinstance(x, str) and (k in ("quote", "verbatim", "quote_text")
                                           or (k == "text" and parent in ("evidence", "citations"))):
                    q = _qkey(x)
                    if len(q) >= 4:
                        keys.add(q)
                else:
                    walk(x, k if isinstance(x, list) else parent)
        elif isinstance(v, list):
            for x in v:
                walk(x, parent)
    walk(model)
    return keys


def _is_quote_line(line, quotes, blob=None):
    """שורה שכולה ציטוט מהמודל, גם כשהודפסה מקוצרת."""
    k = _qkey(line)
    if not k or not quotes:
        return False
    if k in quotes:
        return True
    return len(k) >= 20 and blob is not None and k in blob


def written_text(lines, quotes):
    """מה שהמערכת כתבה: השורות שאינן ציטוט, ובלי קטעים שבין מירכאות."""
    blob = "\x00".join(quotes)
    return [INLINE_QUOTE.sub(" ", line) for line in lines if not _is_quote_line(line, quotes, blob)]


def check_content(lines, model, lang="he", quotes=None):
    """2. תוכן: מחזיקי מקום, אנגלית מהמודל, מבנה נתונים, שלושת המסלולים, ומקפים בטקסט שהמערכת
    כתבה (ציטוט מילולי מוחרג)."""
    bad = []
    joined = "\n".join(lines)
    quotes = model_quotes(model) if quotes is None else quotes
    written_lines = written_text(lines, quotes)
    # מחזיקי מקום, מבנה נתונים וקודים מהמודל נבדקים רק בטקסט שהמערכת כתבה: ציטוט מילולי מהסכם שנפתח
    # ב-"None of our employees" או שמכיל "TBD" אינו תקלה של ה-Word
    written = "\n".join(written_lines)
    for line in written_lines:
        if DASHES.search(line):
            bad.append("מקף ארוך או קצר בטקסט שאינו ציטוט: %s" % line.strip()[:70])
    for ph in PLACEHOLDERS:
        if ph in written:
            bad.append('מחזיק מקום במסמך: "%s"' % ph)
    if PLACEHOLDER_RX.search(written):
        bad.append('מחזיק מקום במסמך: "להשלים"')
    for rx in AS_DATA:
        m = rx.search(written)
        if m:
            bad.append("נוסח שהודפס כמבנה נתונים: %s" % m.group(0))
    # ערך באנגלית מהמודל: קוד מסלול או קוד מעמד שנשאר בטקסט שמוצג
    for code in MODEL_CODES[lang]:
        if re.search(r"(?<![\w-])%s(?![\w-])" % code, written):
            bad.append('ערך באנגלית מהמודל בטקסט: "%s"' % code)
    for t in NAMES[lang]["tracks"]:
        if t not in joined:
            bad.append('אין במסמך את המסלול "%s"' % t)
    return bad


def check_sources_and_label(parts, lines, model, st, docx=None, lang="he", quotes=None):
    """5 ו-8: פרק המקורות, התווית מילה במילה בכותרת העליונה ובגוף, ואין "מאושר" ליד עמדה.

    "מאושר" נבדק רק בטקסט שהמערכת כתבה, ורק כטענת מעמד (STATUS_CLAIM): ציטוט מילולי ממסמך מקור,
    ותיאור של סעיף בהסכם ("משולם לפי דוח שעות מאושר"), אינם טענה שעמדה או הפלייבוק אושרו.

    התווית נקראת מה-Word עצמו (`check_surfaces` עם `word_path`). בלי הנתיב
    הבדיקה הזו לא קראה את הכותרת העליונה כלל, ומסמך בלי תווית עבר אותה.
    """
    bad = list(R.check_surfaces(st, word_path=docx, model=model) or ())
    joined = "\n".join(lines)
    head = NAMES[lang]["sources"]
    research = (model.get("market_research") or {})
    if research and research.get("status") not in NOT_RUN:
        if head not in joined:
            bad.append('רץ מחקר שוק ואין פרק "%s"' % head)
    ids_in_sources = set()
    in_sources = False
    for line in lines:
        if head in line:
            in_sources = True
            continue
        if in_sources and line.strip().startswith("##"):
            in_sources = False
        if in_sources:
            ids_in_sources |= set(W_ID.findall(line))
    for line in lines:
        if head in line:
            break
        for wid in W_ID.findall(line):
            if ids_in_sources and wid not in ids_in_sources:
                bad.append("מזהה %s בשורת מקור ואינו בפרק המקורות" % wid)
    # 8: "מאושר" לא יופיע ליד עמדה, מסלול או כרטיס. שורת המעמד נגזרת בקוד ומוחרגת, וכך גם ציטוט
    quotes = model_quotes(model) if quotes is None else quotes
    for line in written_text([x for x in lines if not _is_status_line(x, st)], quotes):
        # STATUS_CLAIM קורא גם "אושרה" ו"אושרו" ("העמדה אושרה"), ולא רק "מאושר"
        if STATUS_CLAIM[lang].search(line):
            bad.append('המילה "%s" כטענת מעמד בשורה שאינה שורת המעמד: %s'
                       % ("approved" if lang == "en" else "מאושר", line.strip()[:70]))
    return bad


def _is_status_line(line, st):
    """שורת מעמד: התווית, "מעמד העמדות: ..." או "מעמד העמדה: ...". אלה נגזרים בקוד,
    ו-`check_surfaces` משווה אותם לגזירה, ולכן "מאושר" בהם הוא המעמד עצמו."""
    label = st.get("label") or ""
    t = line.strip()
    if t.startswith(R.SUMMARY_PREFIXES + R.CELL_PREFIXES):
        return True
    return bool(label) and (label in line or t in (label, label + "."))


def _rule_keys(model):
    """המפתח שבו כל כלל מופיע במסמך: שם הנושא. מזהה הכלל (R01) פנימי ואינו מודפס ללקוח (areo-voice.md), ולכן הבדיקות
    מזהות כלל לפי שמו, ורק כלל בלי שם נבדק לפי המזהה."""
    out = []
    for r in model.get("rules") or []:
        key = str(r.get("topic_name") or r.get("topic") or r.get("rule_id") or "").strip()
        if key:
            out.append(key)
    return out


def check_brief(lines, model, lang="he"):
    """8: ב"העמדות בקצרה" יש שורה לכל כלל במודל."""
    rules = _rule_keys(model)
    if not rules:
        return [], "אין כללים במודל"
    joined = "\n".join(lines)
    head = NAMES[lang]["brief"]
    if head not in joined:
        return ['אין פרק "%s"' % head], None
    after = joined.split(head, 1)[1]
    missing = [r for r in rules if r not in after]
    return (["אין שורה ב\"%s\" לכללים: %s" % (head, ", ".join(missing[:8]))]
            if missing else []), None


RED_TITLE = {"he": "אדום: לא מתקבל", "en": "Red: not acceptable"}


def _green_keys(model):
    keys = set()
    for r in model.get("rules") or []:
        pc = ((r.get("traffic_light") or {}).get("green") or {}).get("proposed_clause")
        for t in (pc.values() if isinstance(pc, dict) else [pc]):
            k = _qkey(t) if isinstance(t, str) else ""
            if len(k) >= 12:
                keys.add(k)
    return keys


def check_red(lines, model, lang="he"):
    """2: מתחת לכותרת האדום לא מודפס נוסח הירוק כאילו הוא נוסח האדום. הנוסח באדום הוא הנוסח החלופי,
    בכותרת משלו, ונוסח זהה לירוק מוחלף בהפניה לירוק (build_playbook_docx.track)."""
    title, greens, bad = RED_TITLE[lang], _green_keys(model), []
    for i, line in enumerate(lines):
        if not line.strip().startswith(title):
            continue
        for nxt in lines[i + 1:i + 5]:
            if nxt.strip() in RED_TITLE.values() or re.match(r"^\d+\.\s", nxt.strip()):
                break
            if _qkey(nxt) in greens:
                bad.append("נוסח הירוק מודפס מתחת לכותרת האדום: %s" % nxt.strip()[:70])
                break
    return bad


def check_numbering(lines, model):
    """6: מספרי הנושאים זהים בכל הפרקים."""
    rules = _rule_keys(model)
    joined = "\n".join(lines)
    return ["נושא שאינו במסמך: %s" % r for r in rules if r not in joined]


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
    # כתובת שהודפסה כטקסט בלבד. כתובת שהיא חלק מציטוט מילולי או מנוסח חוזי (למשל "the list at
    # https://...") היא טקסט ההסכם, ונשארת כלשונה: היא אינה קישור ואינה נבדקת כאן
    linked = {"".join(n.text or "" for n in l.iter(W + "t"))
              for l in doc.iter(W + "hyperlink")}
    quotes = _verbatim_texts(model)
    for p in doc.iter(W + "p"):
        t = "".join(n.text or "" for n in p.iter(W + "t"))
        for m in re.finditer(r"https?://\S+", t):
            if not any(m.group(0) in x for x in linked) and not _in_quote(t, m, quotes):
                bad.append("כתובת שמודפסת כטקסט בלבד: %s" % m.group(0)[:60])
    return bad


def _norm(text):
    """רווחים ומקפים כמו בבונה ה-Word (s(), track()), כדי שציטוט במודל יימצא כמו שהודפס."""
    return " ".join(DASHES.sub(lambda d: ", " if ord(d.group(0)) == 0x2014 else "-", str(text or "")).split())


def _verbatim_texts(model):
    """כל נוסח מילולי ממסמך שהמודל מחזיק: הציטוטים (citations, evidence), הנוסחים המוצעים ונוסחי הנסיגה בכל
    מסלול ובכל וריאנט, הסעיפים הייחודיים והתנאים המסחריים."""
    out = []

    def add(v):
        if isinstance(v, dict):
            for k in ("he", "en", "text"):
                add(v.get(k))
        elif isinstance(v, str) and "http" in v:
            out.append(_norm(v))

    for c in model.get("citations") or ():
        if isinstance(c, dict):
            add(c.get("quote")), add(c.get("text"))
    for r in model.get("rules") or ():
        if not isinstance(r, dict):
            continue
        for e in r.get("evidence") or ():
            if isinstance(e, dict):
                add(e.get("quote")), add(e.get("text"))
        for tl in [r.get("traffic_light") or {}] + [v.get("traffic_light") or {} for v in
                                                     r.get("segment_variants") or () if isinstance(v, dict)]:
            for blk in tl.values():
                if isinstance(blk, dict):
                    add(blk.get("proposed_clause")), add(blk.get("fallback_wording"))
    cov = model.get("coverage") or {}
    for u in cov.get("unique_clauses") or ():
        if isinstance(u, dict):
            add(u.get("quote"))
    for row in (model.get("commercial") or {}).get("rows") or ():
        if isinstance(row, dict):
            add(row.get("quote"))
    return out


def _in_quote(par, m, quotes):
    """האם הכתובת שבפסקה היא חלק מנוסח מילולי שבמודל: הכתובת מופיעה בנוסח, וגם הטקסט שסביבה בפסקה."""
    url = m.group(0).rstrip(".,;)\"'")
    t = _norm(par)
    for q in quotes:
        i = q.find(url)
        if i < 0:
            continue
        ctx = q[max(0, i - 40):i].strip() or q[i + len(url):i + len(url) + 40].strip()
        if not ctx or ctx in t:
            return True
    return False


def _iter_sources(model):
    """כל רשומות המקור שקישור במסמך יכול להוביל אליהן: מקורות השוק (source_refs, כולל final_url),
    מקורות הדין, ו-external_sources. לפני כן source_refs ומקורות הדין לא נקראו כאן, וכל קישור לחיץ
    בפרק המקורות נכשל כ"אינו ברשומה"."""
    research = model.get("market_research") or {}
    for key in ("sources", "external_sources", "findings", "source_refs"):
        for item in research.get(key) or ():
            if isinstance(item, dict):
                yield item
                if item.get("final_url"):
                    yield {"url": item["final_url"]}
    for item in (model.get("regulatory_research") or {}).get("sources") or ():
        if isinstance(item, dict):
            yield item
    for item in model.get("external_sources") or ():
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
        rid = r.get("topic_name") or r.get("topic") or r.get("rule_id") or r.get("id")
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


def check_properties(parts, model, company=""):
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
    company = (company or model.get("company_name") or model.get("organization_name")
               or (model.get("company") or {}).get("name") or "").strip()
    if not author:
        return [], None
    if not company:
        return [], 'המחבר בקובץ "%s", ואין במודל שם חברה להשוות אליו' % author
    if author != company:
        return ['המחבר בקובץ "%s", ולא שם החברה "%s" ולא ריק' % (author, company)], None
    return [], None


def main(argv=None):
    no_bytecode()
    ap = parser(__doc__.split("\n")[0], out_required=False,
                out_help="אופציונלי: נתיב לדוח הקבלה כ-JSON. בלעדיו: הדפסה בלבד")
    ap.add_argument("--docx", required=True, help="ה-Word שנבנה")
    ap.add_argument("--model", required=True, help="playbook-model.json")
    ap.add_argument("--artifact", help="סביבת העבודה, לבדיקת השוויון")
    ap.add_argument("--run-date", help="יום ההפקה (YYYY-MM-DD). ברירת מחדל: היום")
    ap.add_argument("--profile", help="פרופיל-לקוח.json: שם החברה, להשוואה למחבר הקובץ")
    ap.add_argument("--lang", choices=("he", "en"),
                    help="שפת המסמך. בלעדיו: מהמסמך עצמו (language במאפייני הקובץ, או bidi במקטע)")
    a = ap.parse_args(argv)

    for p, what in ((a.docx, "ה-Word"), (a.model, "המודל")):
        if not os.path.exists(p):
            print("%s אינו קיים: %s" % (what, p))
            return 2
    # Word פגום, DOC, מוצפן או Strict: הודעה דו-לשונית וקוד 2, ולא traceback של zipfile
    ok, msg, code = load_docx_or_explain(a.docx, loader=False)
    if ok is None:
        print(msg)
        return code
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
    lang = a.lang or doc_lang(parts)
    # אותה גזירה כמו בבנייה ובשער המדיניות (status.gate_status), עם התאים של רשומת האישור האחרונה
    st = S.gate_status(model, a.model, lang=lang)
    print("שפת המסמך: %s (%s)" % (lang, "LTR" if lang == "en" else "RTL"))

    res = Result()
    quotes = model_quotes(model)
    res.add(1, "כיווניות", audit_ltr(a.docx, run_date) if lang == "en"
            else rtl.audit_docx(a.docx, run_date=run_date))
    res.add(2, "תוכן", check_content(lines, model, lang, quotes) + check_red(lines, model, lang))
    par, skip = check_parity(lines, a.artifact)
    res.add(3, "שוויון מול הארטיפקט", par, skip)
    vis, skip = check_visual(a.docx, run_date)
    res.add(4, "בדיקה חזותית", vis, skip)
    res.add(5, "מקורות ותווית", check_sources_and_label(parts, lines, model, st, a.docx, lang, quotes))
    res.add(6, "מספור והפניות", check_numbering(lines, model))
    res.add(7, "קישורים חיצוניים", check_links(parts, model))
    brief, skip = check_brief(lines, model, lang)
    res.add(8, "תווית ומעמד", brief, skip)
    company = ""
    if a.profile:
        try:
            with open(a.profile, encoding="utf-8") as fh:
                prof = json.load(fh)
            # במסמך באנגלית המחבר הוא השם הרשום באנגלית, כמו בבנייה (build_playbook_docx.company_name)
            company = ((lang == "en" and str(prof.get("organization_name_en") or "").strip())
                       or prof.get("organization_name") or "").strip()
        except (OSError, ValueError):
            pass
        # כמו בשער: פרט שטרם הושלם בפרופיל ("ח.פ [●]") אינו חלק מהשם
        for sep in (", ח.פ", " ח.פ"):
            if sep in company and "[" in company.split(sep, 1)[1][:20]:
                company = company.split(sep, 1)[0].strip(" ,")
    props, skip = check_properties(parts, model, company)
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
            # תיקייה שאינה קיימת עוד נוצרת, ולא מפילה את הבדיקה אחרי שכבר רצה
            if os.path.dirname(path):
                os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(res.to_dict(), fh, ensure_ascii=False, indent=2)
            print("נכתב %s" % path)

    if res.failed:
        print("המסמך אינו נמסר: נכשל ב-%d בדיקות." % len(res.failed))
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
