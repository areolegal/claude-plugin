# -*- coding: utf-8 -*-
"""common/voice_check.py: הקול של Areo (areo-voice.md) בקוד: מונחים פנימיים שאסור שיגיעו ללקוח.

שימוש:
  python voice_check.py --text "<הודעת המסירה>"          בודק הודעה אחת לפני שהיא נשלחת (מצב ui, מחמיר)
  python voice_check.py --files a.md b.html                בודק נוסחים מתוסרטים בקבצים (מצב ui)
  python voice_check.py --docx out.docx                    בודק מסמך Word (מצב document)
  <script> | python voice_check.py --text -                בודק פלט של סקריפט שנמסר ללקוח כפי שהוא
  --mode ui | document | external                         קובע את המצב במפורש
קוד יציאה: 0 כשאין ממצא, 3 כשיש, 2 בשגיאת קלט.

שני מצבים:
- ui (ברירת המחדל ל---text ולקבצי md ו-html): נוסח שהלקוח קורא בצ'אט ובממשק. כל המילון: קודים פנימיים, מילים
  של המערכת, וכללי הסגנון ("בהתאם ל", "יש לציין", please).
- document (ברירת המחדל ל-Word): מסמך משפטי. נבדקים רק קודים פנימיים ומילים של המערכת (R01, A70, DOC-1, AGR-1,
  VQ-GLOBAL-1, profile_id, ערכי מנייה כמו SEND_BLOCKED או UserDeclared, "mode 4", "מצב 4", "Red lines", "קווים
  אדומים", שמות של מנועים). תווית המעמד "פלייבוק מוצע" מותרת במסמך (כלל 1.13). כללי הסגנון אינם חלים, כי לשון משפטית כמו "בהתאם ל" או "ולראיה" היא חלק מההסכם. במסמך עם מעקב שינויים נבדק רק מה שאנחנו
  כתבנו: הוספות במעקב (w:ins) והערות; הנוסח המקורי של הצד שכנגד אינו נבדק.

- external: עותק שיוצא לצד שכנגד. כמו document, ובנוסף "פלייבוק" ו"מדיניות החברה" (כלל 1.17: תוכן פנימי אינו
  יוצא החוצה). מריצים אותו על עותק המשלוח בלבד.

בקבצים נבדקים רק נוסחים שהלקוח רואה: בקבצי md, קטעים בתוך גרש הפוך או מירכאות שיש בהם אות עברית או אנגלית;
בקבצי html, מחרוזות בתוך מירכאות ותוכן תגיות, בלי ספריות JavaScript מוטמעות. מונח בתוך שם קובץ, כתובת או
מזהה טכני אינו נבדק. התוויות הקבועות של כלל 3.5 מותרות כסימון בתוך מסמך, ולכן אינן במילון האסור.
"""
import argparse
import io
import json
import re
import sys
import zipfile

if __name__ == '__main__':
    sys.dont_write_bytecode = True

# (ביטוי, מה אומרים במקומו, סוג). ביטוי בעברית נבדק כמילה שלמה, עם תחיליות (ה, ו, ב, ל, מ, ש, כ).
# סוג: code (קוד פנימי, רגיש לרישיות, בכל מצב), sys (מילה של המערכת, בכל מצב), ui (רק בנוסח ממשק וצ'אט)
_P = r"(?<![\w֐-׿])(?:[והבלמשכ]{0,3})"
_E = r"(?![\w֐-׿])"
_CODE = "קוד פנימי: אף פעם לא מוצג"
_STD = r"(?!(?:ISO|IEC|AES|SHA|RSA|TLS|SSL|SOC|PCI|GPT|COVID|CVE|EN|BS|NIST|SP|UTF|HTTP|IPV|WCAG|W|I|K)-)"
FORBIDDEN = (
    (_P + r"מצב\s*\d+" + _E, "אף פעם לא מוצג: אמרו מה צריך לעשות", "code"),
    (r"\bmode\s*\d+\b", "never shown: say what needs to be done", "code"),
    # מזהה כלל (R1, R26), ומזהה עם אות ושתי ספרות ומעלה (A70, S01, Q12). "A4" ו-"Q4" (נייר, רבעון) אינם קוד
    (r"\b(?:R\d{1,3}|[ANQSK]\d{2,3}[a-z]?)\b", _CODE, "code"),
    # אותיות, מקף וספרות (Q-0004, DOC-1, AGR-1, RSK-011), ומזהה מורכב (VQ-GLOBAL-1). תקנים מוכרים אינם קוד
    # מספר מסמך של צד שלישי (INV-2026-0412, Order No. DD-2025-118) אינו קוד שלנו: אחריו עוד מקף וספרות
    (r"\b" + _STD + r"[A-Z]{1,6}(?:-[A-Z]{2,12})*-\d{1,6}\b(?!-\d)", _CODE, "code"),
    (r"\b[A-Z]{1,4}\d{1,4}#[A-Za-z]{0,2}\d+\b", _CODE, "code"),
    # שם שדה או ערך מנייה (profile_id, our_unsent_response, tender_awarded), לא בתוך כתובת או נתיב
    (r"(?<![\w/\\.@:-])[a-z]+(?:_[a-z0-9]+)+(?![\w/\\.@-])", "שם שדה או ערך פנימי: אמרו אותו במילים", "code"),
    # ערך מנייה באותיות גדולות (ENTITY_NAME_EN_MISSING, SEND_BLOCKED) וקוד מעמד של רגולטור (UserDeclared).
    # שם משתנה של JavaScript בשימוש (${RUNG_SUB[k]}, RUNG_SUB.x, RUNG_SUB(...)) הוא קוד ולא נוסח ללקוח
    (r"(?<![\w/\\.@:${-])[A-Z][A-Z0-9]+(?:_[A-Z0-9]+)+(?![\w/\\.@\[(-])", "ערך פנימי: אמרו אותו במילים", "code"),
    (r"\bUserDeclared\b", "הוצהר על ידכם / Declared by you", "code"),
    # "פלייבוק מוצע" היא תווית המעמד שהקוד גוזר (status_label, כלל 1.13): מותרת כסימון במסמך, לא בצ'אט ובממשק
    (_P + r"פלייבוק מוצע" + _E, "טיוטת מדיניות, מחכה לאישור שלכם", "ui"),
    (r"\bproposed playbook\b", "draft policy, awaiting your approval", "ui"),
    (_P + r"מציינ(?:י|ים) חוסר" + _E, "פרטים להשלים", "sys"),
    (_P + r"הנושא ונותן" + _E, "Areo, או התוצר עצמו: התגובה, הטיוטה, המדיניות", "sys"),
    # במסמך משפטי "המנסח" הוא מי שניסח את ההסכם (כלל הפרשנות נגד המנסח), ולכן רק בנוסח ממשק
    (_P + r"המנסח" + _E, "Areo, או התוצר עצמו: הטיוטה", "ui"),
    (_P + r"סקיל(?:ים)?" + _E, "סוכן / סוכנים", "sys"),
    (_P + r"רכיבי המערכת" + _E, "סוכן / סוכנים, או התוצר עצמו", "sys"),
    (_P + r"הפעולה נספרה" + _E, "אף פעם לא מוצג ללקוח", "sys"),
    (r"\bexit code\b|קוד יציאה", "הבדיקה הממוחשבת עברה / לא עברה", "sys"),
    (r"\bred[ -]lines?\b", "what we won't accept / לא מסכימים", "sys"),
    (_P + r"קווים אדומים" + _E, "מה שלא מקבלים", "sys"),
    (_P + r"טעון אישור" + _E, "מחכה לאישור שלכם", "ui"),
    (_P + r"סבב\s*\d+" + _E, "התגובה הראשונה / התגובה לטיוטה שלהם", "ui"),
    (r"\d+\s+(?:החלטות|הכרעות)" + _E, "מספר רק כשהוא עוזר להחליט: 'X סעיפים מחכים לך'", "ui"),
    (_P + r"כירורגי(?:ים|ות|ת)?" + _E, "תיקונים בתוך הנוסח שלהם, בלי לשנות את המבנה", "ui"),
    (_P + r"חסו(?:ם|מה|מים|מות)" + _E, "לפני שליחה צריך עוד אישור אחד", "ui"),
    (r"[\"״“”]נבדק[\"״“”]", "אישור עורך דין, לאשר", "ui"),
    (_P + r"שער(?:\s+(?:ה)?איכות)?" + _E, "בדיקה לפני שליחה", "ui"),
    (r"\bgate\b", "בדיקה לפני שליחה / check before sending", "ui"),
    # עותק שיוצא לצד שכנגד (כלל 1.17): המדיניות הפנימית אינה מוזכרת בו בשום צורה
    (_P + r"פלייבוק(?:ים)?" + _E, "אין להזכיר מדיניות פנימית בעותק לצד שכנגד", "ext"),
    (r"\bplaybooks?\b", "internal policy is never mentioned in a copy for the counterparty", "ext"),
    (_P + r"מדיניות\s+(?:ה)?חברה" + _E, "אין להזכיר מדיניות פנימית בעותק לצד שכנגד", "ext"),
    (r"\b(?:company|our)\s+polic(?:y|ies)\b", "internal policy is never mentioned in a copy for the counterparty", "ext"),
    (_P + r"מסלול(?:ים)?" + _E, "מקובל עלינו / אפשר להתגמש / לא מסכימים", "ui"),
    (_P + r"ראי(?:ה|ות)" + _E, "דוגמאות מההסכמים שלכם", "ui"),
    (_P + r"קורפוס" + _E, "ההסכמים שלכם", "ui"),
    (_P + r"פוזיציה" + _E, "הצד שלכם בהסכם", "ui"),
    (_P + r"פרופורציונליות" + _E, "כמה לבקש, ביחס לגודל העסקה", "ui"),
    (_P + r"אשכול(?:ות)?" + _E, "סעיפים שקשורים זה לזה", "ui"),
    (_P + r"נגזר(?:ה|ו)?" + _E, "למדנו מההסכמים שלכם", "ui"),
    (_P + r"גזירה" + _E, "למדנו מההסכמים שלכם", "ui"),
    (_P + r"רכיב(?:ים)?" + _E, "סוכן / סוכנים, או התוצר עצמו", "ui"),
    (r"\bskills?\b", "agent / agents", "ui"),
    (_P + r"יש לציין" + _E, "בלי 'יש לציין'", "ui"),
    (_P + r"בהתאם ל", "בלי 'בהתאם ל'", "ui"),
    (r"\b(?:successfully|please)\b", "in English: no 'please', no 'successfully'", "ui"),
)
_RX = [(re.compile(p) if kind == "code" else re.compile(p, re.I), fix, kind) for p, fix, kind in FORBIDDEN]
MODES = ("ui", "document", "external")


_FILE_EXT = r"\.(?:docx?|xlsx?|pptx?|pdf|json|jsonl|md|html?|py|js|css|txt|csv|zip|png|jpe?g)\b"
# שמות קבצים ונתיבים אינם נוסח ללקוח: הכלים קובעים אותם (למשל "... - סבב 1 - <תאריך>.docx"), והלקוח אינו קורא
# אותם כמשפט. מוסרים לפני הבדיקה: (א) קטע בגרש הפוך או במירכאות שיש בו סיומת קובץ או מפריד נתיב;
# (ב) נתיב עם מפרידים (C:\..., Areo-נתונים\drafts\..., ./x, a/b/c), עד סיומת הקובץ כשיש כזו, כולל רווחים בשם
#     הקובץ. לוכסן יחיד ("ו/או", "הספק/הלקוח") אינו נתיב;
# (ג) שם קובץ חשוף עם רווחים, מתחילת השורה או מאחרי נקודתיים, סוגריים או מירכאות, עד הסיומת, בלי לחצות סוף משפט.
_SEG = r"(?:(?!\.\s)[^\n`\"”'():;])*?"
_PATH_RX = re.compile(
    r"[`\"“'][^`\"”'\n]*?(?:\\|://|" + _FILE_EXT + r")[^`\"”'\n]*[`\"”']|"
    r"(?:[A-Za-z]:[\\/]|\\\\|\.\.?[\\/]|(?<![\w\u0590-\u05FF])[\w\u0590-\u05FF.-]+\\|(?<![\w\u0590-\u05FF])(?:[\w\u0590-\u05FF.-]+/){2,})"
    r"(?:" + _SEG + _FILE_EXT + r"|[^\s`\"”'()]*)|"
    + _SEG + _FILE_EXT)


def strip_paths(text):
    """מחזיר את הטקסט בלי שמות קבצים ונתיבים (מונח בתוך שם קובץ אינו נבדק)."""
    return _PATH_RX.sub(" ", text or "")


def check_text(text, mode="ui"):
    """רשימת ממצאים: [{"term", "say_instead"}]. mode: ui (הכול) או document (קודים ומילים של המערכת בלבד).
    mode external: כמו document, ובנוסף מונחי מדיניות פנימית. התאמה שכלולה בהתאמה ארוכה יותר (S01 בתוך S01#p3) נספרת פעם אחת.
    שמות קבצים ונתיבים מוסרים לפני הבדיקה (strip_paths)."""
    text = strip_paths(text)
    hits = []
    for rx, fix, kind in _RX:
        if kind == "ext" and mode != "external":
            continue
        if mode in ("document", "external") and kind == "ui":
            continue
        for m in rx.finditer(text or ""):
            hits.append((m.start(), m.end(), m.group(0).strip(), fix))
    out = []
    for s, e, term, fix in hits:
        if any(s2 <= s and e <= e2 and (e2 - s2) > (e - s) for s2, e2, _, _ in hits):
            continue
        out.append({"term": term, "say_instead": fix})
    return out


_HEB_OR_LAT = re.compile(r"[A-Za-z֐-׿]")
# ערכי מנייה וסימונים פנימיים שמופיעים במירכאות בהוראות למודל, ואינם מגיעים ללקוח כלשונם
INTERNAL_VALUES = {"טעון אישור", "edge of the red line", "פוזיציה", "position"}
# ספרייה מוטמעת (chart.js וכו'): קוד של צד שלישי, ולא נוסח שלנו
_LIBRARY = re.compile(r"^\s*/\*!|Chart\.js|@license|\bsourceMappingURL\b")


def scripted_segments(path, text):
    """הנוסחים שהלקוח רואה בקובץ: md, קטעים מצוטטים; html, מחרוזות ותוכן תגיות, בלי ספריות JavaScript."""
    segs = []
    if path.lower().endswith((".html", ".htm")):
        def script(m):
            code = m.group(1)
            return "" if (len(code) > 150000 or _LIBRARY.search(code[:4000])) else code
        body = re.sub(r"<script\b[^>]*>(.*?)</script>", script, text, flags=re.S | re.I)
        segs += re.findall(r'"([^"\n]{2,400})"', body)
        segs += re.findall(r">([^<>{}\n]{2,400})<", body)
    else:
        segs += re.findall(r"`([^`\n]{3,600})`", text)
        segs += re.findall(r'"([^"\n]{3,600})"', text)
        segs += re.findall(r"“([^”\n]{3,600})”", text)
    # מזהים טכניים, שמות קבצים ופקודות אינם נוסח ללקוח
    keep = []
    for s in segs:
        # ערך מנייה פנימי שעומד לבדו (סטטוס במרשם, מחרוזת סימון שהנתונים חייבים להכיל) אינו נוסח ללקוח
        if s.strip().strip(".").casefold() in INTERNAL_VALUES:
            continue
        if not _HEB_OR_LAT.search(s) or re.search(r"\.(py|json|md|html|docx|xlsx)\b|--\w|^\s*[\w./\\-]+\s*$|get_resource|AREO_RT", s):
            continue
        # בקובץ html, קטע של קוד JavaScript (בין שתי מחרוזות) אינו נוסח ללקוח: ${, ===, =>, ||, סוגריים מסולסלים,
        # קריאה לפונקציה, מפתח של אובייקט ("as_obligor:"), או רשימת ערכים מופרדת בקו (a|b|c)
        if path.lower().endswith((".html", ".htm")) and _JS.search(s):
            continue
        keep.append(s)
    return keep


_JS = re.compile(r"\$\{|===|!==|=>|\|\||&&|[{};]|\b[A-Za-z_$][\w$]*\(|^\s*[,:)\]]|[,:(]\s*$|\b\w+:\s*[\w'\"]|"
                 r"\w\|\w|\b(?:const|let|var|function|return)\b")


DOCX_PARTS = re.compile(r"^word/(?:document|header\d*|footer\d*|comments|footnotes|endnotes)\.xml$")
_T = re.compile(r"<w:t(?: [^>]*)?>([^<]*)</w:t>")


def _unxml(s):
    return s.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&apos;", "'").replace("&amp;", "&")


# מזהה ההפקה בגיליון העמדות לאישור (approval_sheet.py) הוא עוגן שהקוד קורא חזרה ומסומן "אין לשנות": אינו נוסח
_ANCHOR = re.compile(r"^\s*(?:מזהה הפקה|Issue ID) \((?:אין לשנות|do not change)\):")


def docx_segments(path, ours_only=None):
    """הטקסט שהלקוח רואה ב-Word, פסקה אחר פסקה: הגוף, הכותרות העליונות והתחתונות, ההערות, הערות השוליים.
    טקסט שנמחק במעקב (w:delText) אינו נבדק. ours_only (ברירת מחדל: כשיש במסמך מעקב שינויים): בגוף נבדקות
    רק ההוספות במעקב, כלומר מה שאנחנו כתבנו; הערות, כותרות והערות שוליים נבדקות כולן."""
    segs = []
    with zipfile.ZipFile(path) as z:
        doc = z.read("word/document.xml").decode("utf-8", "replace") if "word/document.xml" in z.namelist() else ""
        tracked = bool(re.search(r"<w:(?:ins|del) ", doc)) if ours_only is None else ours_only
        for name in z.namelist():
            if not DOCX_PARTS.match(name):
                continue
            xml = doc if name == "word/document.xml" else z.read(name).decode("utf-8", "replace")
            for para in re.findall(r"<w:p[ >].*?</w:p>", xml, flags=re.S):
                if tracked and name == "word/document.xml":
                    txt = " ".join("".join(_T.findall(ins)) for ins in re.findall(r"<w:ins [^>]*>(.*?)</w:ins>", para,
                                                                                    flags=re.S))
                else:
                    txt = "".join(_T.findall(para))
                txt = _unxml(txt)
                if txt.strip() and not _ANCHOR.match(txt):
                    segs.append(txt)
    return segs


def check_docx(paths, mode="document"):
    out = []
    for p in paths:
        for seg in docx_segments(p):
            for f in check_text(seg, mode):
                out.append(dict(f, file=p, text=seg[:160]))
    return out


def check_files(paths, mode=None):
    out = []
    docx = [p for p in paths if p.lower().endswith(".docx")]
    if docx:
        out += check_docx(docx, mode or "document")
    for p in paths:
        if p.lower().endswith(".docx"):
            continue
        with io.open(p, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        for seg in scripted_segments(p, text):
            for f in check_text(seg, mode or "ui"):
                out.append(dict(f, file=p, text=seg[:160]))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="בדיקת הקול של Areo: מונחים פנימיים בנוסח ללקוח (areo-voice.md)")
    ap.add_argument("--text", help="הודעה אחת לבדיקה, למשל הודעת המסירה, או פלט של סקריפט שנמסר ללקוח; "
                                   "'-' קורא מהקלט הסטנדרטי")
    ap.add_argument("--files", nargs="+", help="קבצי md, html או docx לבדיקת הנוסחים שהלקוח רואה")
    ap.add_argument("--docx", nargs="+", help="קובצי Word (מצב document): קודים ומילים של המערכת; במסמך עם מעקב "
                                              "שינויים, רק מה שאנחנו הוספנו")
    ap.add_argument("--mode", choices=MODES, help="ui: נוסח ממשק וצ'אט (מחמיר); document: מסמך משפטי; external: עותק לצד שכנגד. ברירת "
                                                 "מחדל: ui ל---text ולקבצי md ו-html, document ל-Word")
    ap.add_argument("--json", action="store_true", help="פלט JSON")
    a = ap.parse_args(argv)
    try:   # גם ב-python -I, שמתעלם מ-PYTHONIOENCODING
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    if not a.text and not a.files and not a.docx:
        ap.error("נדרש --text, --files או --docx")
    if a.text == "-":
        a.text = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace").read()
    found = check_text(a.text, a.mode or "ui") if a.text else []
    try:
        if a.files:
            found += check_files(a.files, a.mode)
        if a.docx:
            found += check_docx(a.docx, a.mode or "document")
    except (OSError, zipfile.BadZipFile) as exc:
        print("לא נקרא כ-Word: %s" % exc)
        return 2
    if a.json:
        print(json.dumps(found, ensure_ascii=False, indent=1))
    else:
        for f in found:
            print("%s%s -> %s" % (("%s: " % f["file"]) if f.get("file") else "", f["term"], f["say_instead"]))
        print("ממצאים: %d (findings: %d)" % (len(found), len(found)))
    return 3 if found else 0


if __name__ == "__main__":
    sys.exit(main())
