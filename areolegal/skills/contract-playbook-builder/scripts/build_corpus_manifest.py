#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""בונה את מניפסט הקורפוס, וסופר בקוד כמה הסכמים יש בכל סוג.

הספירה אינה הערכה של המודל, כי המסלול נגזר ממנה: 20 ומעלה (`full`),
7 עד 19 (`below20`), 1 עד 6 (`below7`) ואפס (`none`). טעות של שני קבצים
מזיזה מסלול. השמות והמבנה כאן הם אלה של `corpus_basis` ב-`playbook-schema.md`,
כדי שהבונה יעתיק מספרים ולא יתרגם אותם.

מה שאינו נספר כהסכם: עותק זהה (בבתים או בתוכן), גרסה אחרת של אותו משא ומתן,
תיקון להסכם (נספר עם ההסכם שהוא מתקן), ותבנית של החברה. תבנית של צד שכנגד (נספח של הליך תחרותי,
טופס של גוף ציבורי) נספרת כמסמך על הנייר של הצד שכנגד, ואינה מוצאת כתבנית.

שני מהלכים, כי הסיווג לסוגים נעשה לפי הכותרת והפתיח ואינו עבודה של קוד:
  1. python3 build_corpus_manifest.py <תיקייה> --out corpus-manifest.json
     מחזיר לכל קובץ `title_hint`, ולפיו מסווגים לסוגים.
  2. python3 build_corpus_manifest.py <תיקייה> --families families.json --out ...
     מחזיר `by_family`, ובו בלוק `corpus_basis` לכל סוג.

families.json:
  {"families": [{"contract_family_id": "<מזהה_משפחה>", "label": "<שם המשפחה כפי שהלקוח קורא לה>",
                 "company_role_code": "<תפקיד החברה>", "paths": ["a.docx", ...],
                 "counterparty_templates": ["b.pdf"], "company_templates": ["c.docx"]}]}
  counterparty_templates ו-company_templates אופציונליים: מי ניסח את הנוסח, כשקריאת הכותרת או תשובת
  הלקוח הכריעו אחרת מהזיהוי בקוד (corpus-pipeline.md, פרק 2).

--profile <פרופיל-לקוח.json> (רשות): שם החברה וסוג התאגיד. גוף ציבורי שנמצא בפתיח ושהוא החברה עצמה אינו סימן
לנייר של צד שכנגד; וכשהחברה היא גוף ציבורי, הליך תחרותי הוא שלה, אלא כשהיא המציעה (bidder).
"""
import argparse
import hashlib
import json
import os
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # גם ב-python -I, שאינו מוסיף את תיקיית הסקריפט
import areo_lib  # noqa: F401  מוסיף את areolegal/lib לנתיב הייבוא, ופלט UTF-8 בקונסולה

from common.cli import OutputRefused, docx_problem, guard_out  # noqa: E402

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
# Strict Open XML: אותו מבנה במרחב שמות אחר. בלעדיו המסמך נקרא כריק
STRICT_W = b"http://purl.oclc.org/ooxml/wordprocessingml/main"
NO_TEXT = "אין שכבת טקסט (סרוק?)"
DOCX_REASON = {"ole": "DOC ישן או קובץ מוצפן בסיסמה; שמרו כ-docx בלי סיסמה",
               "not_zip": "קובץ פגום: אינו ZIP תקין",
               "no_document": "אין בו word/document.xml: אינו מסמך Word"}
TEXT_EXT = {".txt", ".md", ".csv", ".json"}
# סימני תבנית (`corpus-pipeline.md`, פרק 2): מצייני מקום, היעדר חתימה,
# או שם קובץ שאומר זאת
TEMPLATE_NAME = re.compile(r"תבנית|נוסח סטנדרטי|נוסח אחיד|template|master form|standard form", re.I)
PLACEHOLDER = re.compile(r"_{4,}|\.{6,}|\[[^\]]{0,40}(שם|תאריך|סכום|להשלים|insert|name|date|amount)[^\]]{0,40}\]"
                         r"|<<[^>]{1,40}>>|\{\{[^}]{1,40}\}\}", re.I)
# בלוק חתימה. אותו ביטוי בדיוק ב-`build_template_registry.py` של המנסח (SIGN_DATE), כדי ששני
# הרכיבים יסווגו אותו מסמך באותה דרך; שינוי כאן נעשה גם שם. "Signed by" ו-"Executed by" רק
# בתחילת שורה, כי "deemed executed by the parties" בגוף ההסכם אינו בלוק חתימה; ו-/s/ לא
# בתוך כתובת אתר
SIGNED = re.compile(
    r"IN\s+WITNESS\s+WHEREOF"
    r"|ולראי{1,2}ה\s+(?:באו|באנו|חתמו|חתמנו)|ובאו\s+הצדדים\s+על\s+החתום|חתימת\s+הצדדים"
    r"|(?m:^)[ \t]*(?-i:Signed|SIGNED|Executed|EXECUTED)\s+(?:by|for\s+and\s+on\s+behalf)\b"
    r"|\b(?:have|has)\s+(?:duly\s+)?executed\s+this\b|(?<![\w/])/s/"
    r"|signature\s+of\s+the\s+parties"
    r"|(?:נחתם|תאריך\s+החתימה|Signed\s+on|Date\s+of\s+signature)\s*[:\-]?\s*\d", re.I)
# קו חתימה (`____` או שורת נקודות) בסוף המסמך אינו מציין מקום אלא המקום לחתום בו,
# ולכן אינו נספר בתוך 300 התווים האחרונים. כך גם במנסח
LINE_RUN = re.compile(r"_{4,}|\.{6,}")
SIGN_TAIL = 300
# תבנית של צד שכנגד (corpus-pipeline.md, פרק 2, "Whose template"): טופס סטנדרטי שהצד השני מגיש לחברה לחתימה,
# בכל סוג הסכם: חוזה של צד אחד, תנאים כלליים של צד או של פלטפורמה, טופס שצד מפרסם, נספח של הליך תחרותי של
# גוף ציבורי. סימני התבנית (מצייני מקום, בלי בלוק חתימה) נכונים גם לגביו, ולכן מסמכים כאלה עלולים להירשם
# כתבנית של החברה ולא להיספר. שני סימנים, והקוד אינו מכריע מי ניסח: הוא מסמן,
# והבונה מאשר או מתקן ב-families.json:
#   1. הסימן הכללי: הצד שפרטיו ריקים בפתיח ("________ (להלן: "<תפקיד>")") הוא הצד שהחברה ממלאת (company_role_code).
#      בתבנית של החברה ריקים פרטי הצד שכנגד; בטופס של הצד שכנגד, פרטי החברה. נבדק בסוג, כשהתפקיד ידוע.
#   2. מנפיק שאינו החברה: הליך תחרותי, או גוף ציבורי בשם הקובץ ובפתיח. לא כשהחברה היא המנפיקה: התפקיד שלה מזמין
#      (ISSUER_ROLES), או שהיא עצמה גוף ציבורי לפי הפרופיל (company_identity) ואינה המציעה, או שהגוף שנמצא הוא שמה
PROCEDURE_SIGN = re.compile(r"הליך תחרותי|המציע|\bcompetitive\s+procedure\b|\bbidders?\b|\bRFP\b|request\s+for\s+proposals?"
                         r"|invitation\s+to\s+(?:bid|tender)", re.I)
# גוף ציבורי לפי סוג הגוף, ולא לפי שם: משרד, רשות מקומית, חברה ממשלתית, תאגיד סטטוטורי, ובאנגלית ממשלה, משרד,
# רשות מקומית. אין שמות של גופים ספציפיים. גוף ששמו אינו מעיד על סוגו (למשל חברה
# ממשלתית בשם מסחרי) מוכרע בסוג מתשובת הלקוח (wf1-scope-corpus-extraction.md, שלב 2ח)
PUBLIC_BODY = re.compile(r"משרד\s+ה[א-ת]+|עיריית|המועצה\s+(?:האזורית|המקומית)"
                         r"|חברה\s+ממשלתית|תאגיד\s+סטטוטורי"
                         r"|Ministry\s+of|Municipality\s+of|Government\s+of"
                         r"|government\s+company|statutory\s+corporation"
                         r"|(?:City|County|Borough)\s+(?:of|Council)", re.I)
PUBLIC_HEAD = 1500
# מציין מקום שאחריו, בתוך 80 תווים, כינוי מוגדר: הצד שפרטיו ריקים. מדלג על שורות הכותרת
BLANK_PARTY = re.compile(r'(?:_{4,}|\.{6,}|\[[^\]]{0,40}\]|<<[^>]{1,40}>>|\{\{[^}]{1,40}\}\})[^"״“()\n]{0,60}[()]\s*'
                         r'(?:להלן\s*[:\-]?\s*|hereinafter(?:\s+(?:referred\s+to\s+as|called))?\s*[:,]?\s*(?:the\s+)?'
                         r'|the\s+)?["״“]([^"״”()]{2,40})["״”]', re.I)
# תיקון מזוהה רק בשורות הכותרת (שלוש השורות הראשונות שאינן ריקות) ובשם הקובץ, ולא בגוף:
# "תיקון 13 לחוק" בפתיח, או "Data Processing Addendum to the Agreement", אינם תיקון להסכם.
# Addendum נחשב תיקון רק כשהוא פותח את הכותרת ("Addendum No. 2 to"). כשלפניו שם (Data
# <נושא> Addendum), זה שמו של הסכם עומד בפני עצמו
AMENDMENT = re.compile(r"תיקון\s*(?:מס(?:פר|['׳])?\.?\s*)?\d*\s*ל(?!חוק|תקנות|פקודת|פקודה|צו\b)"
                       r"|נספח\s+תיקון|תוספת\s+להסכם|הסכם\s+תיקון"
                       r"|\bamendment\s*(?:no\.?\s*\d+\s*)?to\b"
                       r"|^\s*(?:(?:first|second|third|\d+(?:st|nd|rd|th)?)\s+)?addendum\b"
                       r"\s*(?:(?:no\.?|number|#)\s*\d+\s*)?to\b", re.I)
# חידוש אינו גרסה של ההסכם הקודם אלא משא ומתן חדש
RENEWAL_TOKENS = {"חידוש", "מחודש", "הארכה", "הארכת", "renewal", "renewed",
                  "extension", "extended", "new"}
BANDS = [(20, None, "full"), (7, 19, "below20"), (1, 6, "below7"), (0, 0, "none")]
# כינויי הצדדים, מהפתיח של ההסכם: הגדרה בסוגריים ("<תפקיד>"), או כינוי מוכר.
# מהם הבונה לומד מה סוגי הצדדים בסוג ההסכם (כפי שהמסמכים קוראים להם), ורק אז שואל
# את המשתמש איזה צד הוא מייצג. הצורות: (להלן: "X"), (להלן - "X"), (hereinafter referred
# to as the "X"), (the "X"), ("X"). ב-PDF בעברית הסוגריים יוצאים לעיתים הפוכים, ולכן
# כל סוגר מתקבל בשני הצדדים
DEFINED_PARTY = re.compile(r'[()]\s*(?:להלן\s*[:\-\u2013\u2014]?\s*'
                           r'|hereinafter(?:\s+(?:referred\s+to\s+as|called|named|defined\s+as))?\s*[:,]?\s*(?:the\s+)?'
                           r'|the\s+)?["״“]([^"״”()]{2,40})["״”]'
                           r'(?:\s*(?:או|or)\s*(?:the\s+)?["״“]([^"״”()]{2,40})["״”])?\s*[()]', re.I)
# אין רשימת תפקידים בקוד. כינוי שהוגדר בפתיח ("להלן: X") נחשב תפקיד כשהוא נראה כתפקיד (_role_like): בעברית מיודע,
# באנגלית שם בעל סיומת של תפקיד. התפקיד של החברה בא מ-company_role_code, כטקסט חופשי, ולא ממילון.
NOT_A_ROLE = re.compile(r"^(?:ההסכם|הסכם|החוזה|חוזה|המוצר|השירותים|השירות|המידע|הנכס|הצדדים|הצד|"
                        r"ההצעה|הנספח|נספח|Agreement|Services|Product|Effective Date|Term|"
                        r"Confidential Information|Purpose|Parties|Party|Addendum|Clauses|"
                        r"Schedule|Annex|Exhibit|Proposal|החוק|התקנות|"
                        # רבים שאינם צד: עובדים, משתמשים, חברות קשורות ונציגים של צד
                        r"העובדים|המשתמשים|המשתמשים הסופיים|החברות הקשורות|הנציגים|Employees|Personnel|Users|"
                        r"End Users|Affiliates|Representatives)$", re.I)


def _alias(g):
    """כינוי נקי: רווחים מכווצים, קו מילוי ("האוניברסיטה ____") מוסר, ואות שימוש שנותקה מהמילה ב-PDF ("ה רשות")
    מוחזרת אליה."""
    g = re.sub(r"\s+", " ", re.sub(r"_{2,}|\.{3,}", " ", g or "")).strip(" .,:;")
    return re.sub(r"^([הוכלבמש]) (?=[א-ת])", r"\1", g)


def parties_hint(text):
    """כינויי הצדדים בפתיח (עד 2500 תווים), עד ארבעה: קודם הגדרות בסוגריים שהן תפקיד מוכר,
    אחריהן כינויים מוכרים מהפתיח, ובסוף שאר ההגדרות (שם מקוצר של חברה, למשל). מונח שיש בו ראשי תיבות
    (ראשי תיבות באותיות רישיות) והגדרה שיש בה ספרה הם חוק או מונח, ולא צד."""
    head = (text or "")[:2500]
    roles, others = [], []
    for m in DEFINED_PARTY.finditer(head):
        for g in m.groups():
            g = _alias(g)
            if (not g or NOT_A_ROLE.match(g) or len(g.split()) > 3 or g in roles + others
                    or re.search(r"\b[A-Z]{2,8}\b", g) or re.search(r"\d", g)
                    or re.match(r"(?:חוק|תקנות|פקודת)\s|.*\b(?:Act|Law|Regulations?)$", g, re.I)):
                continue
            (roles if _role_like(g) else others).append(g)
    return (roles + others)[:4]


# אין אוצר תפקידים לפי company_role_code ואין זוגות "צד מול צד שכנגד": התפקיד של החברה הוא טקסט חופשי בלשון
# המסמכים (company_role_code), והצד שכנגד נקבע רק ממה שהפתיח אומר (כינוי ריק מול כינוי מלא).
# החברה היא שמזמינה הצעות בהליך תחרותי: סימן ההליך אינו מלמד שהנוסח של צד שכנגד
ISSUER_ROLES = {"contracting_authority", "issuer", "inviting_party", "מזמין", "הגוף המזמין"}
# החברה עצמה גוף ציבורי, לפי organization_type בפרופיל (בעברית או באנגלית, כפי שרכיב ההקמה כותב אותו). "חברה ציבורית"
# (נסחרת) ו"חברה לתועלת הציבור" אינן גוף ציבורי
PUBLIC_ORG = re.compile(r"ממשלתי|ממשלתית|גוף\s+ציבורי|רשות\s+מקומית|תאגיד\s+סטטוטורי|השכלה\s+גבוהה|אוניברסיט"
                        r"|Government|Public\s+body|Local\s+authority|Statutory\s+corporation|Universit|higher\s+education", re.I)
LEGAL_SUFFIX = re.compile(r"\b(?:בע[\"״']?מ|\(?ע[\"״']?ר\)?|חל[\"״']?צ|Ltd\.?|Limited|Inc\.?|LLC|L\.L\.C\.|plc|GmbH|B\.V\.)(?=\s|$|[,.)])", re.I)
NO_COMPANY = {"names": [], "public": False}


def _name_key(t):
    return re.sub(r"\s+", " ", re.sub(r"[\"״'׳`.,()\-]", " ", t or "")).strip().lower()


def company_identity(profile_path):
    """{names, public} מהפרופיל: שמות החברה בלי סיומת משפטית (organization_name, organization_name_en), והאם היא
    גוף ציבורי (organization_type). בלי פרופיל: אין שם, ואינה גוף ציבורי, כמו לפני כן."""
    if not profile_path:
        return dict(NO_COMPANY)
    try:
        prof = json.loads(Path(profile_path).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        print("אזהרה: הפרופיל לא נקרא (%s). הזיהוי ממשיך בלי שם החברה" % profile_path, file=sys.stderr)
        return dict(NO_COMPANY)
    names = []
    for k in ("organization_name", "organization_name_en"):
        n = _name_key(LEGAL_SUFFIX.sub(" ", str(prof.get(k) or "")))
        if len(n) >= 4 and n not in names:
            names.append(n)
    return {"names": names, "public": bool(PUBLIC_ORG.search(str(prof.get("organization_type") or "")))}


def company_issues(role_code, own):
    """True כשההליך התחרותי או הטופס הציבורי הם של החברה: התפקיד שלה מזמין, או שהיא גוף ציבורי ואינה המציעה."""
    role = str(role_code or "").strip().lower()
    return role in ISSUER_ROLES or (bool((own or {}).get("public")) and role != "bidder")


def role_terms(role_code):
    """(הכינויים של החברה, הכינויים של הצד שכנגד) לפי company_role_code: הטקסט עצמו, עם ובלי ה' הידיעה; הצד שכנגד
    אינו נגזר ממילון ולכן ריק."""
    r = str(role_code or "").strip()
    if not r or r.lower() in ("other", "mutual"):
        return [], []
    return [r, "ה" + r], []


def _norm_role(g):
    return re.sub(r"^the\s+", "", (g or "").strip().lower())


def _role_like(g):
    """כינוי שנראה כתפקיד ולא כשם של חברה: בעברית מיודע ("המפעיל"), באנגלית שם של תפקיד ("Operator").
    שם מקוצר של חברה אינו כפתור צד."""
    if re.search(r"[א-ת]", g):
        return g.startswith("ה")
    return bool(re.search(r"(?:or|er|ee|ant|ent|ist|ary|ier)$", g.split()[-1], re.I))


def family_roles(rows, role_code):
    """כינויי הצדדים של הסוג: התפקידים המוכרים מכל מסמכי הסוג, לפי מספר המסמכים שבהם הופיעו (עד ארבעה);
    כינוי אחר משני המסמכים הראשונים רק כשנמצאו פחות משני תפקידים מוכרים, ורק כשהוא נראה כתפקיד; ואחריהם
    (אין השלמה מאוצר מילים: רק כינויים שנמצאו במסמכים). לפני כן
    נקראו רק שני המסמכים הראשונים, ושם של צד ו"נושאי המידע" הוצגו כתפקידים. מחזיר (roles, read_from, added_from_vocabulary)."""
    freq, first, others, read = {}, {}, [], []
    for r in rows:
        if r["doc_role"] not in ("agreement", "form", "template"):
            continue
        read.append(r["path"])
        for g in r.get("parties_hint") or []:
            if _role_like(g):
                freq[g] = freq.get(g, 0) + 1
                first.setdefault(g, len(first))
            elif len(read) <= 2 and g not in others and _role_like(g):
                others.append(g)
    roles = sorted(freq, key=lambda g: (-freq[g], first[g]))[:4]
    if len(roles) < 2:
        roles += [g for g in others if g not in roles][:4 - len(roles)]
    added = []
    return roles, read, added


def third_party_signs(name, text, own=None):
    """סימני המנפיק, מקרה אחד של תבנית של צד שכנגד: סימן של הליך תחרותי בשם הקובץ או בטקסט, או גוף ציבורי בשם הקובץ ובפתיח.
    גוף ציבורי אינו סימן כששם החברה (own, מהפרופיל) מופיע בשם הקובץ או בפתיח: הגוף הוא החברה עצמה.
    הסימן הכללי, הצד הריק בפתיח, נבדק בסוג (whose_template), כי הוא תלוי בתפקיד של החברה."""
    signs = []
    m = PROCEDURE_SIGN.search(Path(name).stem) or PROCEDURE_SIGN.search(text or "")
    if m:
        signs.append("procedure: %s" % m.group(0))
    m = PUBLIC_BODY.search(Path(name).stem) or PUBLIC_BODY.search((text or "")[:PUBLIC_HEAD])
    if m:
        head = _name_key(Path(name).stem + " " + (text or "")[:PUBLIC_HEAD])
        if not any(n in head for n in (own or NO_COMPANY)["names"]):
            signs.append("public body: %s" % re.sub(r"\s+", " ", m.group(0)))
    return signs


def blank_parties(text):
    """כינויי הצדדים שפרטיהם ריקים בפתיח (עד 2500 תווים): "________ (להלן: "<תפקיד>")"."""
    out = []
    for m in BLANK_PARTY.finditer((text or "")[:2500]):
        g = _alias(m.group(1))
        if g and not NOT_A_ROLE.match(g) and g not in out:
            out.append(g)
    return out


def whose_template(row, role_code):
    """counterparty, company או None, לתבנית או לטופס בסוג שהתפקיד של החברה בו ידוע (הסימן הכללי, שבהערה מעל
    PROCEDURE_SIGN):
    הצד הריק הוא הצד של החברה, או הצד שכנגד. None כשהפתיח אינו מכריע."""
    ours, theirs = role_terms(role_code)
    blank = {_norm_role(g) for g in row.get("blank_parties") or ()}
    hit_ours = blank & {_norm_role(w) for w in ours}
    hit_theirs = blank & {_norm_role(w) for w in theirs}
    if hit_ours and not hit_theirs:
        return "counterparty"
    if hit_theirs and not hit_ours:
        return "company"
    return None


def decide_owner(row, role_code, own=None):
    """מי ניסח תבנית או טופס בסוג הזה, כשאין הכרעה ב-families.json: הצד הריק בפתיח קודם; אחריו סימני המנפיק
    (הליך תחרותי, גוף ציבורי), אלא כשהחברה היא המנפיקה (company_issues). טופס עם בלוק חתימה נשאר טופס, ורק מסומן כשל
    הצד שכנגד. בהסכם: רמז ההליך התחרותי לנייר של הצד שכנגד מוסר כשהחברה היא המנפיקה, ונוסף כשהיא גוף ציבורי והמציעה."""
    signs = row.get("third_party_signs") or ()
    tender = any(x.startswith("procedure") for x in signs)
    issuer = company_issues(role_code, own)
    if row["doc_role"] not in ("template", "form"):
        if tender and issuer and row.get("paper_hint") == "theirs":
            row = dict(row)
            row.pop("paper_hint", None)
        elif tender and not issuer and (own or {}).get("public") and not row.get("paper_hint"):
            row = dict(row, paper_hint="theirs")
        return row
    owner = whose_template(row, role_code)
    tp = bool(row.get("counterparty_template"))
    if owner == "counterparty":
        return row if tp else as_counterparty_form(row, ["blank party: company role"])
    if row["doc_role"] == "form" and not tp:
        return row
    if owner == "company":
        return as_company_template(row, "blank party: counterparty role")
    if tp and issuer:
        return as_company_template(row, "company issues the procedure" if tender else "company is the public body")
    if not tp and row["doc_role"] == "template" and signs and (own or {}).get("public") and not issuer:
        # גוף ציבורי שהוא המציע: הסימנים לא הפכו את התבנית בסריקה (התפקיד לא היה ידוע), והם מכריעים כאן
        return as_counterparty_form(row, ["company is the bidder"])
    return row


def as_counterparty_form(row, why):
    """תבנית שאינה של החברה: נספרת כמסמך על הנייר של הצד שכנגד (doc_role: form, paper_hint: theirs).
    הסכם ותיקון נשארים כמו שהם, ורק הרמז לנייר נוסף."""
    row = dict(row)
    if row["doc_role"] in ("template", "form"):
        row["doc_role"] = "form"
        row["form_signs"] = (["counterparty template"] + list(row.get("template_signs") or row.get("form_signs") or [])
                             + list(why))
        row["counterparty_template"] = True
    row["paper_hint"] = "theirs"
    return row


def as_company_template(row, why="client: company template"):
    """נוסח שהבונה או הלקוח קבעו שהוא התבנית של החברה: תבנית, שאינה נספרת."""
    row = dict(row)
    if row["doc_role"] != "amendment":
        row["doc_role"] = "template"
        row["template_signs"] = [x for x in row.get("template_signs") or [] if x != why] + [why]
    for k in ("counterparty_template", "paper_hint", "form_signs"):
        row.pop(k, None)
    return row


def band_of(units):
    return next(name for lo, hi, name in BANDS if units >= lo and (hi is None or units <= hi))


def sha256_bytes(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def pdf_text(path):
    """שכבת הטקסט של PDF, כמו ב-`extract_corpus.py`: PyMuPDF כשמותקן, בסדר לוגי גם בעברית.
    בלעדיו pdfplumber או pypdf, אבל רק כשאין בטקסט עברית: שניהם מחזירים עברית בסדר חזותי
    הפוך, ואז כפילות, כינויי צדדים וכותרת היו נגזרים מטקסט שגוי. מחזיר (טקסט, סיבה)."""
    try:
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz  # type: ignore
        with fitz.open(str(path)) as doc:
            text = "\n".join(pg.get_text() for pg in doc)
        return (text, None) if text.strip() else (None, "PDF סרוק, בלי שכבת טקסט")
    except ImportError:
        pass
    except Exception as e:
        return None, "PDF לא נקרא: %s" % type(e).__name__
    try:
        try:
            import pdfplumber
            with pdfplumber.open(str(path)) as pdf:
                text = "\n".join((pg.extract_text() or "") for pg in pdf.pages)
        except ImportError:
            import pypdf
            text = "\n".join((pg.extract_text() or "") for pg in pypdf.PdfReader(str(path)).pages)
    except ImportError:
        return None, "אין ספרייה לקריאת PDF. התקנה: pip install pymupdf"
    except Exception as e:
        return None, "PDF לא נקרא: %s" % type(e).__name__
    if not text.strip():
        return None, "PDF סרוק, בלי שכבת טקסט"
    if re.search(r"[א-ת]", text):
        return None, "PDF בעברית, ואין pymupdf: הטקסט יוצא בסדר הפוך. התקנה: pip install pymupdf"
    return text, None


def read_text(path):
    """טקסט לצורך השוואה: (טקסט, סיבה). docx, PDF וקבצי טקסט נקראים; השאר מדווחים כלא נקראים."""
    try:
        if path.suffix.lower() == ".docx":
            found = docx_problem(path, strict_ok=True)
            if found and found[0] in DOCX_REASON:
                return None, DOCX_REASON[found[0]]
            with zipfile.ZipFile(path) as z:
                xml = z.read("word/document.xml").replace(STRICT_W, W[1:-1].encode())
            root = ET.fromstring(xml)
            text = "\n".join("".join(t.text or "" for t in p.iter(W + "t")) for p in root.iter(W + "p"))
            # מסמך Word בלי טקסט (סריקה שהודבקה כתמונה) אינו "נקרא": הוא נרשם ב-needs_review.unreadable
            return (text, None) if text.strip() else (None, NO_TEXT)
        if path.suffix.lower() == ".pdf":
            return pdf_text(path)
        if path.suffix.lower() in TEXT_EXT:
            return path.read_text(encoding="utf-8", errors="ignore"), None
    except Exception as e:
        return None, "הקובץ לא נקרא: %s" % type(e).__name__
    return None, None


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
    if not lines:
        return Path(name).stem
    # שלוש שורות, ועוד שורות כל עוד יש פחות מ-80 תווים: ב-PDF הכותרת מתפרקת לשברי שורה
    n = 3
    while n < min(len(lines), 12) and len(" ".join(lines[:n])) < 80:
        n += 1
    return " / ".join(lines[:n])[:300]


def head_lines(text, n=3):
    """שורות הכותרת: שלוש השורות הראשונות שאינן ריקות, עד 200 תווים כל אחת."""
    return [l.strip()[:200] for l in (text or "").splitlines() if l.strip()][:n]


def is_amendment(name, text):
    """תיקון להסכם, לפי שם הקובץ או שורות הכותרת בלבד (ראה AMENDMENT)."""
    if AMENDMENT.search(Path(name).stem):
        return True
    return any(AMENDMENT.search(l) for l in head_lines(text))


def placeholder_count(text):
    """מצייני מקום, בלי קווי חתימה ב-300 התווים האחרונים (ראה LINE_RUN)."""
    cut = len(text) - SIGN_TAIL
    return sum(1 for m in PLACEHOLDER.finditer(text)
               if not (m.start() >= cut and LINE_RUN.fullmatch(m.group(0))))


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
    השוואת אסימונים ולא מחרוזות, כדי ש"x 1" לא ייראה כמו תחילת "x 10".
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
        if placeholder_count(text) >= 3:
            hits.append("placeholders")
        if not SIGNED.search(text):
            hits.append("no signature block")
    # שם הקובץ לבדו מספיק; אחרת דרושים שני סימנים, כדי לא לפסול הסכם חתום
    return ("file name" in hits) or (len(hits) >= 2), hits


# טופס לא חתום (corpus-pipeline.md, פרק 2, "Unsigned forms"): בלוק חתימה, וגם מצייני מקום ריקים בגוף, מחוץ
# לקו החתימה שבסוף. "שניים משלושה סימנים" של תבנית מסווג טופס כזה כהסכם, כי יש בו בלוק חתימה: בהרצה חיה
# טפסים ריקים של הליך תחרותי עלולים להיספר כהסכמים במסלול הרגיל. אין כאן הכרעה שהטופס אינו הסכם, כי טופס
# שנחתם ונסרק אחרי מילוי חלקי נראה אותו דבר: הוא נספר כמו קודם, מסומן doc_role: form, ונרשם ב-needs_review,
# ומעמד המאגר נקבע בשאלה ללקוח (workflow.md, שלב 2ח)
def looks_like_blank_form(text):
    if not text or not SIGNED.search(text):
        return False, []
    n = placeholder_count(text)
    return n >= 3, (["signature block", "%d placeholders" % n] if n >= 3 else [])


# התיקייה של Areo עצמה (הפרופיל, המודלים, החילוץ, סביבת העבודה) ותיקיות מוסתרות אינן הסכמים. בהרצה חיה
# הסריקה ספרה את קובצי ה-JSON שבתוך Areo-נתונים כהסכמים, וצריך היה להריץ אותה על עותק
AREO_DIRS = ("Areo-נתונים", "Areo-data")


def _skipped(rel):
    return any(part in AREO_DIRS or part.startswith(".") for part in rel.parts[:-1])


def scan(root, own=None):
    own = own or NO_COMPANY
    rows = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.name.startswith(("~$", ".")) or _skipped(p.relative_to(root)):
            continue
        text, why = read_text(p)
        norm = normalize(text) if text else None
        row = {
            "path": str(p.relative_to(root)), "size": p.stat().st_size,
            "extension": p.suffix.lower(), "sha256": sha256_bytes(p),
            "normalized_stem": normalized_stem(p.name),
            "text_read": text is not None,
            "text_sha256": hashlib.sha256(norm.encode("utf-8")).hexdigest() if norm else None,
            "title_hint": title_hint(text, p.name),
            "parties_hint": parties_hint(text),
            "doc_role": "agreement",
        }
        if why:
            row["unreadable_reason"] = why
        is_tpl, signs = looks_like_template(p.name, text)
        if is_tpl:
            row["doc_role"], row["template_signs"] = "template", signs
        else:
            is_form, signs = looks_like_blank_form(text)
            if is_form:
                row["doc_role"], row["form_signs"] = "form", signs
        blanks = blank_parties(text)
        if blanks:
            row["blank_parties"] = blanks
        tp = third_party_signs(p.name, text, own)
        if tp:
            row["third_party_signs"] = tp
            # תבנית עם סימני צד שכנגד אינה תבנית של החברה: היא נספרת, ומסומנת לבדיקה. בהסכם רק נוסח הליך תחרותי הוא רמז
            # לנייר של הצד שכנגד, כי גוף ציבורי מוזכר גם בפתיח של נוסח של ספק ("מדינת ישראל"). כשהחברה עצמה גוף
            # ציבורי, ההליך התחרותי והטופס הציבורי הם בדרך כלל שלה: הם נרשמים כסימן, ומוכרעים בסוג לפי התפקיד (decide_owner)
            if own["public"]:
                pass
            elif row["doc_role"] == "template":
                row = as_counterparty_form(row, [])
            elif any(x.startswith("procedure") for x in tp):
                row["paper_hint"] = "theirs"
        if is_amendment(p.name, text):
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
    bases = [r for r in uniq if r["doc_role"] in ("agreement", "form") and r["normalized_stem"]]
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
            "amendments_without_base": orphan_amendments,
            "unsigned_forms": [r["path"] for r in uniq if r["doc_role"] == "form" and not r.get("counterparty_template")],
            # תבנית של צד שכנגד: נספרת כמסמך על הנייר שלו. מי ניסח מאושר בכותרת או בשאלה (corpus-pipeline.md, פרק 2)
            "counterparty_forms": [r["path"] for r in uniq if r.get("counterparty_template")]},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--out", default="corpus-manifest.json",
                    help="ברירת המחדל: corpus-manifest.json. לעולם לא אחד מקובצי הקורפוס (common/cli.guard_out)")
    ap.add_argument("--families", help="קובץ סיווג לסוגים, אחרי שלב 2א")
    ap.add_argument("--near", type=float, default=0.92, help="סף דמיון לאיחוד גרסאות")
    ap.add_argument("--profile", help="פרופיל-לקוח.json של הישות (רשות): שם החברה, והאם היא גוף ציבורי. גוף ציבורי "
                                      "שהוא החברה עצמה אינו סימן לנייר של צד שכנגד")
    a = ap.parse_args()
    root = Path(a.root).resolve()
    if not root.is_dir():
        sys.exit("אין תיקייה כזאת: %s" % root)
    own = company_identity(a.profile)
    rows = scan(root, own)
    if not rows:
        sys.exit("התיקייה ריקה: %s" % root)
    # --out שמצביע על אחד מההסכמים היה דורס אותו ב-JSON
    try:
        out_path = guard_out(a.out, inputs=[str(root / r["path"]) for r in rows] + [a.families])
    except OutputRefused as exc:
        print("refused: %s" % exc, file=sys.stderr)
        return 2

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
            # מי ניסח את התבנית, כשהבונה או הלקוח הכריעו (corpus-pipeline.md, פרק 2): הצד שכנגד, או החברה
            theirs = set(f.get("counterparty_templates") or [])
            ours = set(f.get("company_templates") or [])
            code = f.get("company_role_code")
            fam_rows = [as_counterparty_form(by_path[p], ["client: counterparty template"]) if p in theirs
                        else as_company_template(by_path[p]) if p in ours else decide_owner(by_path[p], code, own)
                        for p in picked]
            fam["corpus_basis"] = count(fam_rows, a.near) if picked else None
            # רמז הנייר של הסכם נקבע בסוג, לפי התפקיד (decide_owner), ונכתב לשורה של הקובץ
            for p, r in zip(picked, fam_rows):
                if r["doc_role"] == "agreement" and r.get("paper_hint") != by_path[p].get("paper_hint"):
                    by_path[p]["paper_hint"] = r.get("paper_hint")
                    if not r.get("paper_hint"):
                        by_path[p].pop("paper_hint", None)
            # סוגי הצדדים בסוג הזה, מכל המסמכים שלו, ואוצר התפקידים של company_role_code (family_roles)
            roles, seen, added = family_roles(fam_rows, f.get("company_role_code"))
            fam["roles_hint"] = roles
            fam["roles_read_from"] = seen
            if added:
                fam["roles_from_vocabulary"] = added
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
    Path(out_path).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    def report(name, b):
        print("%s: %d קבצים, %d הסכמים, רצועה %s" % (name, b["files"], b["agreement_units"], b["band"]))
        print("   נוכו: %d כפילויות, %d גרסאות, %d תיקונים, %d תבניות"
              % (len(b["removed_duplicates"]), len(b["merged_versions"]),
                 len(b["amendments_attached"]), len(b["excluded_templates"])))
        for k, label in (("unreadable", "לא נקרא טקסט"),
                         ("amendments_without_base", "תיקון בלי הסכם בסיס"),
                         ("unsigned_forms", "טופס לא חתום (בלוק חתימה ומצייני מקום ריקים): מעמד המאגר "
                                            "נשאל בטופס"),
                         ("counterparty_forms", "תבנית של צד שכנגד (פרטי הצד של החברה ריקים, הליך תחרותי או גוף "
                                                "ציבורי): נספרה כמסמך על הנייר שלו; אשרו לפי הכותרת, או רשמו "
                                                "ב-families.json"),
                         ):
            v = b["needs_review"].get(k)
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
    sys.exit(main())
