# -*- coding: utf-8 -*-
"""בדיקת הטקסט שהלקוח רואה: הטיוטה והדף ליווי, כפי שנכתבו בפועל.

הכלל (areo-voice.md): אין קודים ואין מונחים פנימיים. בקוד ולא בהוראה:
- מזהה כלל (R01), מזהי מקור (DOC-1, AGR-1, REG-2, MAND-3, PB-, DEAL-), "מצב 4" / "mode 4";
- המילה "פלייבוק" בתוך נוסח ההסכם (הטיוטה נשלחת לצד השני);
- נתיב מקומי של קובץ במחשב (כונן, תיקיית משתמש, OneDrive, ../): נתיב אינו נכנס לטקסט שהלקוח רואה, רק שם הקובץ;
- בעסקה באנגלית: אות עברית בכל מקום, ושם צד שאינו השם הרשום באנגלית.
- נוסח של עצירה או של אישור עורך דין ("ממתין לאישור עורך דין", "pending legal review"): הטיוטה נמסרת נקייה, אחרי השאלות,
  ובלי שער אישור. זה סימון של שער, לא של בדיקת שלמות.
כשהספרייה המשותפת זמינה (common.voice_check, מצב document) היא נבדקת גם כן.
"""
import json
import re

HEB_CH = re.compile("[֐-׿]")
HEB_RUN = re.compile("[֐-׿][֐-׿\"'״׳ -]*")
CODE_RX = re.compile(r"(?<![\w-])(?:R\d{1,3}|(?:DOC|AGR|REG|MAND|PB|DEAL)-[\w.]*\d[\w.]*)(?![\w-])"
                     r"|\bmode\s*\d|מצב\s*\d|\bstate\s*\d", re.I)
LOCAL_PATH_RX = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/](?![\\/])\S{2,}|[\\/]Users[\\/]|OneDrive|(?<![\w.])\.\./")
PLAYBOOK_RX = re.compile("פלייבוק|פלי\"בוק|\\bplaybook\\b", re.I)
# נוסח של שער אישור או עצירה לפני משלוח. הטיוטה נמסרת נקייה (כלל 6): אין "ממתין לעורך דין" ואין "אל תשלחו עד ש..."
HOLD_RX = re.compile(
    r"ממתי(?:ן|נה|נים|נות)\s+ל(?:אישור|בדיקת)\s+(?:של\s+)?(?:עורך|עורכת|יועץ|היועץ|הממונה)|"
    r"טעונ?(?:ה|ים|ות|ן)\s+אישור\s+(?:של\s+)?(?:עורך|עורכת|יועץ|היועץ)|"
    r"טרם\s+(?:נבדק|אושר)\w*\s+(?:ב?יד[יי]|על[\s-]ידי)\s+(?:עורך|עורכת|יועץ)|"
    r"אל\s+תשלח\w*\s+(?:עד|לפני)\s+(?:ש|אישור)|אין\s+לשלוח\s+(?:עד|לפני)\s+(?:ש|אישור)|"
    r"\bpending\s+(?:lawyer|legal|counsel|attorney)\s+(?:review|approval)|"
    r"\bawait(?:s|ing)\s+(?:lawyer|legal|counsel|attorney)\b|"
    r"\bnot\s+(?:yet\s+)?(?:reviewed|approved)\s+by\s+(?:a\s+)?(?:lawyer|counsel|attorney)\b|"
    r"\bdo\s+not\s+send\s+(?:until|before)\b", re.I)
# הערה גלויה ללקוח כשאין מקור מורשה לנקודה (כלל 5): בעברית ובאנגלית, ובלי למלא מהזיכרון
NO_SOURCE_NOTE = "AREO לא מצאה מקור מורשה לנקודה זו"
NO_SOURCE_NOTE_EN = "AREO did not find an approved source for this point"
STYLE_ONLY = ("בהתאם ל", "יש לציין", "please", "successfully")
ANNEX_REF = re.compile(r"^[A-Z]-\d{1,2}$")   # מזהה נספח בהסכם (A-1) אינו קוד


def english_parties(d, prof, rtl, clean):
    """בעסקה באנגלית שם כל צד הוא השם הרשום באנגלית. שם עברי של החברה מוחלף ב-organization_name_en מהפרופיל כשהוא
    קיים; כל שם עברי אחר, או שם של החברה בלי שם אנגלי בפרופיל, מחזיר הודעה: שואלים את הלקוח מה השם הרשום
    באנגלית, ולא ממציאים תעתיק. מחזיר (עותק של d, [הודעות])."""
    if rtl:
        return d, []
    prof = prof or {}
    he, en = clean(prof.get("organization_name")), clean(prof.get("organization_name_en"))
    d = json.loads(json.dumps(d))
    bad = []
    for p in (d.get("meta") or {}).get("parties") or []:
        nm = clean(p.get("name"))
        if not HEB_CH.search(nm):
            continue
        if en and he and (nm == he or he in nm or nm in he):
            p["name"] = en
        else:
            bad.append(nm)
    if bad:
        return d, ["העסקה באנגלית, אבל השם הרשום באנגלית חסר: %s. שואלים את הלקוח מה השם הרשום של הצד באנגלית "
                   "(אצל החברה: organization_name_en בפרופיל), ולא מתעתקים." % ", ".join(bad)]
    return d, []


def client_text_problems(paths, rtl, docx_text, voice_check=None):
    """paths: (הטיוטה, דף הליווי או None). מחזיר רשימת ממצאים, ריקה כשהכול תקין."""
    out = []
    for k, path in enumerate(paths):
        if not path:
            continue
        which = ("הטיוטה", "דף הליווי")[k]
        text = docx_text(path, limit=2000000)[0]
        for m in LOCAL_PATH_RX.finditer(text):
            out.append("%s: נתיב מקומי של קובץ בטקסט: \"%s\". כותבים את שם הקובץ בלבד." % (which, m.group(0)[:60]))
            break
        for m in CODE_RX.finditer(text):
            out.append("%s: קוד או מונח פנימי בטקסט: \"%s\". מנסחים אותו במילים של הלקוח." % (which, m.group(0)))
        for m in (HOLD_RX.finditer(text) if k == 1 else ()):   # רק דף הליווי; גוף ההסכם נשלח לצד השני ואינו נסרק
            out.append("%s: נוסח של שער אישור או עצירה: \"%s\". הטיוטה נמסרת נקייה, אחרי השאלות, בלי המתנה לאישור."
                       % (which, m.group(0)))
        if k == 0:
            # השורה המלאה "AREO לא מצאה מקור מורשה..." היא לדף הליווי בלבד; בגוף ההסכם רק "[להשלמה]"
            for note in (NO_SOURCE_NOTE, NO_SOURCE_NOTE_EN):
                if note.lower() in text.lower():
                    out.append("הטיוטה: נוסח פנימי של Areo (\"%s\") בגוף ההסכם. בגוף ההסכם רק \"[להשלמה]\"; השורה המלאה "
                               "נשארת בדף הליווי." % note)
            for m in PLAYBOOK_RX.finditer(text):
                out.append("%s: המילה \"%s\" אינה נכנסת לטקסט ההסכם." % (which, m.group(0)))
        if voice_check:
            # הטיוטה נשלחת החוצה: רק קודים ומילים של המערכת. דף הליווי הוא הודעה ללקוח: כל המילון, חוץ מכללי הסגנון
            for h in voice_check(text, "document" if k == 0 else "ui"):
                if h["term"].lower().startswith(STYLE_ONLY):
                    continue
                if not ANNEX_REF.match(h["term"]) and not any(h["term"] in x for x in out):
                    out.append("%s: \"%s\" (%s)" % (which, h["term"], h["say_instead"]))
        if not rtl:
            heb = sorted({m.group(0).strip() for m in HEB_RUN.finditer(text)})
            if heb:
                out.append("%s: עסקה באנגלית, ובטקסט יש עברית: %s. מתרגמים או מורידים." % (which, ", ".join(heb[:6])))
    seen = []
    for x in out:
        if x not in seen:
            seen.append(x)
    return seen[:12]
