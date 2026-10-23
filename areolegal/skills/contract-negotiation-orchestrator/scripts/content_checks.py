#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""בדיקות התוכן של הסבב: מה שהשער בודק בנוסח שמתקבל אחרי כל התיקונים, ובהכרעות.

הבדיקות האלה ביקשה ענבל בהערות הנושא ונותן 4.0 עד 4.7, ואין להן מימוש בקוד
הייחוס, ולכן הן כתובות כאן, כלליות לכל סוג הסכם (החלטה 22): אין בהן נושא,
עמדה או חוק של סוג הסכם מסוים. כל מה שתלוי בעסקה מגיע מקובץ ההכרעות, מקובץ
המצב, מהפלייבוק או מהמניפסט של ההסכמים.

| קוד | שינוי | מה נבדק | חוסם משלוח |
|---|---|---|---|
| CON_REF_MISSING | 19, 39 | הפניה לסעיף או לנספח שאין לו יעד בנוסח המתקבל | בנוסח שהכנסנו |
| CON_TERM_* | 19, 39 | מונח מוגדר שלא מוגדר לפני השימוש, או שאינו בשימוש | לא |
| CON_TBA | 39 | "יוסכם", "יוסכמו", "to be agreed" בנוסח שהכנסנו | כן |
| CON_ANNEX_SHARED | 19 | פסקה בנספח שחולקת מונח או מספר סעיף עם פסקה שתוקנה | לא |
| CON_CLIENT_ANSWER | 19, 23 | תשובת לקוח שיושמה ואינה בנוסח, או רשומה בלי clause_ids ו-status | כן |
| PREC_ANNEX_PREVAILS | 23 | סעיף שקובע שנספח, נוהל או מסמך חיצוני גובר על ההסכם | כן |
| DEAL_DOCS_CONFLICT | 23 | סתירה בין מסמכי העסקה בלי הכרעה | כן |
| NEUTRALIZER | 24 | ביטוי מנטרל בנוסח שנשאר בלי שינוי | לא |
| REP_UNAPPROVED | 26 | מצג או התחייבות בנוסח שלנו בלי רשומה מאושרת, ולא בסוגריים | כן |
| CONFLICT_CHECK | 27 | "אין הסכם סותר", "החברה גילתה" בלי בדיקת התנגשות (`meta.deal_context.existing_agreements_with_counterparty`) | כן |
| EXISTING_AGREEMENT | 27 | סעיף מיצוי או עדיפות, והסכם קיים בתוקף בלי השפעה רשומה | לא |
| OTHER_PARTY_NAME | 28 | שם של צד מהסכם חתום אחר בבועה החיצונית | כן |
| PRICE_TERMS | 32 | Incoterms, מטבע או הצמדה בתיקון שלנו, בלי שינוי בנספח המחירים | לא |
| PRICE_CONFORMING | 32 | בועה "תיקון עקבי" בלבד, כשהשינוי נוגע במחיר | כן |
| COMPLIANCE | 34 | סעיף ציות (שוחד, סנקציות, יצוא, הלבנת הון) בלי הכרעה מפורשת של המשתמש | כן |
| BILINGUAL_* | 44 | הכרעה שמשנה גרסה אחת בלבד, או סתירה בין הגרסאות בלי הכרעה | כן |
| POSITION_MISMATCH | 1 | פלייבוק של משפחה אחרת או של הצד ההפוך | כן |
| PARTY_LABEL | 1 | כינוי צד בנוסח שלנו שאינו בהסכם (נוסח מהפלייבוק שלא עבר את מפת המונחים) | כן |
| RED_MARKER | 59 | סימן אדום של כלל שחל, בנוסח המתקבל, בלי הכרעה לאותו כלל | כן |
| HIDDEN_TEXT | 6 | טקסט מוסתר בטיוטה שלהם, בפסקה שאין בה הכרעה | כן |
| THEIR_INTERNAL_COMMENT | 11 | בועה שלהם שנראית פנימית, ואינה רשומה ב-`meta.exposed_comments` | כן |
| THEIR_COMMENT_UNANSWERED | 10 | בועה שלהם שאין לה מענה ואין לה הכרעה | לא |
| COMBO | 56 | שתי הכרעות באותו צירוף, בלי בדיקה רשומה ב-`meta.combo_checks` | לא |
| PARAGRAPH_REPLACED | ניל 18.10 | מחיקת פסקה והוספת פסקה במקומה, כשרוב המילים נשארו: לא כירורגי | כן |
| REPLACE_COLLAPSED | ניל 18.10 | replace שסימן את רוב הפסקה כשרוב המילים נשארו: להשתמש ב-replace_span | כן |
| STRUCT_ORPHAN_PROVISO | ענבל 22.10, 1 | הפניה לסייג ("הסייג שלהלן", "the foregoing proviso") בלי סייג בנוסח המתקבל | כשהסייג נמחק אצלנו |
| STRUCT_BACKREF | ענבל 22.10, 1 | הפסקה שאחרי פסקה שמחקנו נפתחת ב"כאמור לעיל" | כן |
| STRUCT_LIST_EMPTY | ענבל 22.10, 1 | כל פריטי רשימה נמחקו ונשאר משפט הפתיחה שלה | כן |
| STRUCT_DANGLING_CONJ | ענבל 22.10, 1 | "או", "and" לפני פריט שכבר אינו קיים | כן |
| STRUCT_PROVISO_ROLE | ענבל 22.10, 1 | סייג שהכנסנו ובו התחייבות או איסור | לא |
| DEPENDENT_UNDECIDED, DEPENDENT_KEEP_NO_REASON | ענבל 22.10, 2 | סעיף תלוי בהכרעה שמשנה משטר, בלי הכרעה או בלי נימוק להשארה | כן |
| POST_CHECK_FAILED, POST_CHECK_MANUAL | ענבל 22.10, 3 | בדיקת התוצאה של כלל שהוחל (post_checks בגרעין) | בכלל קריטי |
| TIME_ANCHOR | ענבל 22.10, 4 | מועד תחולה או התחלה שעבר, או עוגן ריק, שלא נרשם ב-time_anchors | כן |
| VAGUE_TERM | ענבל 22.10, 5 | מונח עמום בנוסח שלנו בלי מבחן מוגדר (common/vague_terms.py) | לא |
| FACT_WITHOUT_SOURCE | ענבל 22.10, 6 | בועה שנשענת על עובדה על צד, בלי fact_source | כן |
| ENTITY_PROFILE_FACT, ENTITY_RULE_UNCONFIRMED | ענבל 22.10, 7 | עובדה מהפרופיל או כלל של דין ורגולציה, כשהישות בנייר לא אושרה | כן |
| REF_BUBBLE, BUBBLE_SAME_TOPIC | ענבל 22.10, 8 | בועת הפניה, או כמה בועות לאותו כלל באותו סעיף | כן |
| WEAKNESS_IN_BUBBLE | ענבל 22.10, 9 | נימוק שחושף חולשה שלנו | לא |
| THEIR_GREEN_MARKED | ענבל 22.10, 10 | סימון של נוסח שלהם שכבר בירוק | כן |
| THEIR_YELLOW_NOT_CHIP, THEIR_TRACK_MISSING | ענבל 22.10, 10 | נוסח שלהם בצהוב שלא סומן כמטבע חליפין, או הכרעה בלי סיווג | לא |
| PROPORTIONALITY_UNASKED, FIGHT_LIST_MISSING | ענבל 22.10, 11 | יותר בקשות מרשימת המאבק, והמשתמש לא נשאל | כן |
| COUNTERPARTY_KIND_UNDECIDED | ענבל 22.10, 12 | כלל דין, שפה, מטבע או מס מול צד זר, בלי תנאי הפעלה לצד זר ובלי הכרעה | כן |

הפונקציה `run_checks` מחזירה רשימת ממצאים `{code, message, where, blocking}`.
`qa_gate.py` מריץ אותה בשני המצבים: ממצא חוסם הוא כשל בשער, והעותק למשלוח
אינו מופק.

    python3 scripts/content_checks.py --work <קובץ העבודה> --received <הטיוטה> \\
        --decisions decisions_round_<N>.json [--state ...] [--core ...] [--manifest corpus-manifest.json]

קוד יציאה: **0** אין ממצא חוסם, **3** יש, **2** קלט חסר.
"""
import argparse
import io
import json
import os
import re
import sys
import zipfile

import areo_lib  # noqa: F401  מוסיף את areolegal/lib לנתיב הייבוא

from lxml import etree  # noqa: E402

import common.docx_tracked as dt  # noqa: E402

W = dt.W
HERE = os.path.dirname(os.path.abspath(__file__))
HEB = re.compile(r"[֐-׿]")
LAT = re.compile(r"[A-Za-z]")

NEUTRALIZERS = ["יגברו", "מכריעים", "כמי שוויתר", "תתיישן", "לחלט", "לקזז", "שלטענתה", "זנח", "לא יושעו",
                "לאלתר", "ללא ספירה", "הסעד היחיד", "incorporated by reference", "conclusive",
                "sole and exclusive remedy", "deemed to have waived", "shall prevail"]
TBA = re.compile(r"יוסכ(?:ם|מו)(?![א-ת])|to be agreed|\bTBA\b|to be determined", re.I)
# מצג או התחייבות של החברה. בנוסח: פועל של מצג עם "that" או "hereby", או התחייבות לעמוד. בבועה: רק
# כשאנחנו מצהירים בה ("we confirm"). הסבר כמו "כדי שנוכל לעמוד בדין" אינו מצג
REPRESENT = re.compile(r"\b(?:represents?|warrants?|certif(?:y|ies)|confirms?)(?:\s+and\s+\w+)?\s+that\b|"
                       r"\bhereby\s+(?:represents?|warrants?|confirms?|certif(?:y|ies))\b|\bshall\s+comply\s+with\b|"
                       r"מצהיר(?:ה|ים)?\s+(?:כי|ש|בזאת)|מאשר(?:ת|ים)?\s+בזאת|מתחייב(?:ת|ים)?\s+לעמוד", re.I)
REPRESENT_BUBBLE = re.compile(r"\bwe\s+(?:represent|warrant|confirm|certify)\b|אנו\s+(?:מצהירים|מאשרים)|"
                              r"החברה\s+(?:מצהירה|מאשרת)", re.I)
CONFLICT_REP = re.compile(r"אין הסכם סותר|לא קיים הסכם (?:ה)?סותר|החברה גילתה|גילתה לצד|no conflicting agreement|"
                          r"has disclosed|is not (?:a )?party to any (?:other )?agreement", re.I)
EXHAUST = re.compile(r"מצה(?:ה|ים) את|מבטל(?:ים)? כל הסכם|כל ההסכמות|entire agreement|supersedes? (?:all|any) prior",
                     re.I)
PREVAILS = [re.compile(r"(?:הנספח|נספח|ההזמנה|הזמנת|הנוהל|נוהל|המדיניות|מדיניות|תנאי(?:ם)? (?:ה)?כללי|מסמך)[^.;]{0,70}"
                       r"(?:יגבר|יגברו|תגבר|תגברנה|יכריע|יכריעו)(?![^.;]{0,25}הסכם זה)"),
            re.compile(r"(?:annex|schedule|exhibit|appendix|order|statement of work|sow|policy|terms and conditions|"
                       r"purchase order)[^.;]{0,90}shall (?:prevail|govern|control)(?![^.;]{0,25}(?:this|the) agreement "
                       r"shall prevail)", re.I)]
INCOTERMS = re.compile(r"\b(EXW|FCA|FAS|FOB|CFR|CIF|CPT|CIP|DAP|DPU|DDP)\b")
CURRENCY = re.compile(r"ש\"ח|ש״ח|₪|\bNIS\b|\bILS\b|\bUSD\b|\$|€|\bEUR\b|דולר|יורו|הצמדה|צמוד|מדד|indexation|\bCPI\b",
                      re.I)
PRICE = re.compile(r"מחיר|מחירון|תעריף|תמורה|price|pricing|fee|tariff|rate card", re.I)
CONFORMING_ONLY = re.compile(r"^\s*(?:conforming change|תיקון עקבי|שינוי עקבי|התאמה)\s*[.]?\s*$", re.I)
COMPLIANCE = re.compile(r"bribery|corruption|FCPA|anti-?bribery|sanction|boycott|export control|money laundering|AML\b|"
                        r"שוחד|שחיתות|סנקציה|סנקציות|חרם|פיקוח על יצוא|יצוא בטחוני|הלבנת הון", re.I)
INTERNAL_HINT = re.compile(r"\b(internal|our client|client wants|between us|do not share|don'?t share|we can accept|"
                           r"fallback|walk.?away|bottom line|can live with)\b|פנימי|בינינו|הלקוח שלנו|הלקוח מוכן|"
                           r"אפשר לוותר|נוכל לוותר|מוכנים לוותר|עמדת נסיגה|לא להעביר|לא לשתף|נסתפק", re.I)
PARTY_LABELS = ["הספק", "הלקוח", "המזמין", "נותן השירותים", "מקבל השירותים", "הצד המגלה", "הצד המקבל", "המפיץ",
                "הזכיין", "המעסיק", "העובד", "היועץ", "הקבלן", "המשכיר", "השוכר", "המוכר", "הקונה", "המלווה", "הלווה",
                "Supplier", "Customer", "Provider", "Client", "Licensor", "Licensee", "Discloser", "Recipient", "Vendor",
                "Buyer", "Seller", "Contractor", "Consultant", "Distributor", "Lessor", "Lessee", "Employer"]
REF_HE = re.compile(r"(?<![א-ת])(?:ב|ל|מ|ו|ש)?סעי(?:ף|פים)\s+(\d+(?:\.\d+){0,4})")
REF_EN = re.compile(r"\b(?:Section|Clause|section|clause)s?\s+(\d+(?:\.\d+){0,4})")
ANNEX_HE = re.compile(r"(?<![א-ת])(?:ב|ל|מ|ו|ש)?נספח\s+([א-ת]['׳]?|\d+)(?![א-ת])")
ANNEX_EN = re.compile(r"\b(?:Annex|Schedule|Exhibit|Appendix)\s+([A-Z]|\d+)\b")
DEF_PATTERNS = [re.compile(r"\(\s*(?:להלן:?\s*|the\s+|hereinafter\s+)?[\"״“]([^\"״”]{2,50})[\"״”]"
                           r"(?:\s*(?:או|or)\s*[\"״“]([^\"״”]{2,50})[\"״”])?\s*\)"),
                re.compile(r"\(להלן:?\s*[\"״“]([^\"״”]{2,50})[\"״”]"),
                re.compile(r"[\"״“]([^\"״”]{2,50})[\"״”]\s*(?:-|פירושו|פירושה|משמעו|משמעה|יהיה פירושו)"),
                re.compile(r"[\"“]([A-Z][^\"”]{1,50})[\"”]\s+(?:means|shall mean|has the meaning)"),
                re.compile(r"\((?:the|hereinafter)?\s*[\"“]([A-Z][^\"”]{1,50})[\"”]\)")]


def finding(out, code, message, where="", blocking=False):
    out.append({"code": code, "message": message, "where": where, "blocking": bool(blocking)})


def load(path):
    if not path or not os.path.exists(path):
        return None
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------------------- מספור הסעיפים
def numbered_labels(path):
    """המספר של כל פסקת גוף: מספר מוקלד בראש הפסקה, או מספור אוטומטי לפי numId ו-ilvl."""
    root = dt.document_root(path)
    paras = dt.body_paragraphs(root)
    counters, out = {}, []
    for p in paras:
        text = dt.para_text(p).strip()
        m = re.match(r"^(\d+(?:\.\d+){0,4})[.)]?\s", text)
        if m:
            out.append(m.group(1))
            continue
        num = p.find(W + "pPr/" + W + "numPr")
        if num is not None:
            nid = num.find(W + "numId")
            lvl = num.find(W + "ilvl")
            nid = nid.get(W + "val") if nid is not None else "0"
            lvl = int(lvl.get(W + "val")) if lvl is not None else 0
            c = counters.setdefault(nid, [0] * 9)
            c[lvl] += 1
            for i in range(lvl + 1, 9):
                c[i] = 0
            out.append(".".join(str(x) for x in c[:lvl + 1] if x))
        else:
            out.append(None)
    return out


def annex_names(paras):
    names = set()
    for t in paras:
        s = t.strip()
        m = re.match(r"^נספח\s+([א-ת]['׳]?|\d+)(?![א-ת])", s) or re.match(r"^(?:Annex|Schedule|Exhibit|Appendix)\s+([A-Z]|\d+)\b", s)
        if m:
            names.add(m.group(1).replace("׳", "'"))
    return names


# --------------------------------------------------------------------------- טקסט מוסתר
def hidden_scan(path):
    """כל חלקי החבילה: גוף, כותרות, הערות שוליים וסיום, בועות ותיבות טקסט, ומאפייני הקובץ.
    לכל ממצא: חלק, מספר פסקה בחלק, טקסט, ואופן ההסתרה (vanish, specVanish, צבע, גודל)."""
    out = []
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        for name in names:
            if not re.match(r"^word/(document|header\d*|footer\d*|footnotes|endnotes|comments)\.xml$", name):
                continue
            root = etree.fromstring(z.read(name))
            for pi, p in enumerate(root.iter(W + "p")):
                for r in p.iter(W + "r"):
                    rpr = r.find(W + "rPr")
                    if rpr is None:
                        continue
                    text = "".join(t.text or "" for t in r.iter(W + "t", W + "delText"))
                    if not text.strip():
                        continue
                    how = []
                    for tag in ("vanish", "specVanish", "webHidden"):
                        el = rpr.find(W + tag)
                        if el is not None and el.get(W + "val") not in ("0", "false"):
                            how.append(tag)
                    col = rpr.find(W + "color")
                    if col is not None and str(col.get(W + "val", "")).upper() in ("FFFFFF", "FEFEFE", "FDFDFD", "FCFCFC"):
                        how.append("color")
                    sz = rpr.find(W + "sz")
                    if sz is not None and str(sz.get(W + "val", "99")).isdigit() and int(sz.get(W + "val")) <= 2:
                        how.append("font_size")
                    if how:
                        out.append({"part": name, "paragraph": pi, "text": text, "how": ",".join(how)})
        for name in names:
            if name.startswith("customXml/item") and name.endswith(".xml") or name == "docProps/custom.xml":
                txt = re.sub(r"<[^>]+>", " ", z.read(name).decode("utf-8", "ignore"))
                txt = re.sub(r"\s+", " ", txt).strip()
                if len(txt) > 20:
                    out.append({"part": name, "paragraph": None, "text": txt[:300], "how": "properties"})
    return out


# --------------------------------------------------------------------------- בועות שלהם
def comment_info(path):
    """הבועות בקובץ: id, author, text, paraId של הפסקה הראשונה, והאם יש להן מענה בשרשור."""
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        if "word/comments.xml" not in names:
            return []
        root = etree.fromstring(z.read("word/comments.xml"))
        ext = etree.fromstring(z.read("word/commentsExtended.xml")) if "word/commentsExtended.xml" in names else None
    W14 = "{http://schemas.microsoft.com/office/word/2010/wordml}"
    W15 = "{http://schemas.microsoft.com/office/word/2012/wordml}"
    parents = {}
    if ext is not None:
        for e in ext.iter(W15 + "commentEx"):
            if e.get(W15 + "paraIdParent"):
                parents[e.get(W15 + "paraId")] = e.get(W15 + "paraIdParent")
    out = []
    for c in root.iter(W + "comment"):
        ps = list(c.iter(W + "p"))
        pid = ps[-1].get(W14 + "paraId") if ps else None
        out.append({"id": c.get(W + "id"), "author": c.get(W + "author") or "", "paraId": pid,
                    "text": " ".join("".join(t.text or "" for t in p.iter(W + "t")) for p in ps).strip(),
                    "parent": parents.get(pid)})
    replied = {c["parent"] for c in out if c.get("parent")}
    for c in out:
        c["has_reply"] = c["paraId"] in replied
    return out


# --------------------------------------------------------------------------- הבדיקות
def our_texts(decisions):
    out = []
    for d in decisions or ():
        for k in ("new_text", "new", "text"):
            if d.get(k):
                out.append((d, d[k]))
    return out


def run_checks(work, received, decisions, state=None, core=None, manifest=None, profile=None):
    """הבדיקות על קובץ העבודה מול הטיוטה שהתקבלה. decisions: רשימת ההכרעות."""
    out = []
    state = state or {}
    meta = state.get("meta") or {}
    decisions = decisions or []
    accepted = dt.accept_all(work)
    theirs = dt.received_paragraphs(received)
    whole = "\n".join(accepted)
    labels = numbered_labels(work)
    existing_refs = {x for x in labels if x}
    annexes = annex_names(accepted)
    touched = {d.get("para") for d in decisions if d.get("para") is not None} | \
              {d.get("after_para") for d in decisions if d.get("after_para") is not None}
    by_para = {}
    for d in decisions:
        if d.get("para") is not None:
            by_para.setdefault(d["para"], []).append(d)

    # 19, 39: הפניות
    for i, t in enumerate(accepted):
        for rx, kind in ((REF_HE, "sec"), (REF_EN, "sec"), (ANNEX_HE, "annex"), (ANNEX_EN, "annex")):
            for m in rx.finditer(t):
                target = m.group(1).replace("׳", "'")
                ok = target in existing_refs if kind == "sec" else target in annexes
                if kind == "sec" and not existing_refs:
                    ok = True   # אין מספור שאפשר לשחזר: הבדיקה אינה רצה כאן
                if not ok:
                    ours = any(m.group(0) in txt for _, txt in our_texts(decisions))
                    finding(out, "CON_REF_MISSING", "הפניה ל%s %s, ואין לה יעד בנוסח המתקבל" %
                            ("סעיף" if kind == "sec" else "נספח", target), "פסקה %d" % i, blocking=ours)
    # מונחים מוגדרים
    defined = {}
    for i, t in enumerate(accepted):
        for rx in DEF_PATTERNS:
            for m in rx.finditer(t):
                for g in m.groups():
                    if g:
                        defined.setdefault(g.strip(), i)
    for term, at in defined.items():
        # "הקונה" נכתב בטקסט גם "לקונה" או "בקונה": ה' הידיעה נבלעת אחרי אות השימוש
        stem = term[1:] if term.startswith("ה") and len(term) > 3 else term
        if stem != term:
            trx = re.compile(r"(?<![א-ת])[ולבכמש]{0,2}ה?" + re.escape(stem) + r"(?![א-ת])")
        else:
            trx = re.compile(re.escape(term))
        uses = [i for i, t in enumerate(accepted) if trx.search(t)]
        if uses and uses[0] < at:
            finding(out, "CON_TERM_BEFORE_DEF", "המונח \"%s\" משמש לפני שהוגדר" % term, "פסקה %d" % uses[0])
        if len([i for i in uses if i != at]) == 0 and len(trx.findall(whole)) <= 1:
            finding(out, "CON_TERM_UNUSED", "המונח \"%s\" מוגדר ואינו בשימוש" % term, "פסקה %d" % at)
    # 39: "יוסכם" בנוסח שלנו
    for d, txt in our_texts(decisions):
        if TBA.search(txt):
            finding(out, "CON_TBA", "בנוסח שהכנסנו נשאר \"%s\": אין הסכמה על עניין שנשאר להסכמה" % TBA.search(txt).group(0),
                    d.get("id"), blocking=True)
    # 19: פסקאות בנספחים שחולקות מונח או מספר עם פסקה שתוקנה
    annex_start = next((i for i, t in enumerate(accepted) if re.match(r"^\s*(?:נספח|Annex|Schedule|Exhibit|Appendix)\s",
                                                                       t)), None)
    if annex_start is not None:
        for d in decisions:
            p = d.get("para")
            if p is None or p >= annex_start or p >= len(accepted):
                continue
            keys = set(re.findall(r"[\"״“]([^\"״”]{2,40})[\"״”]", accepted[p])) | set(re.findall(r"\d+(?:\.\d+)+",
                                                                                              accepted[p]))
            for j in range(annex_start, len(accepted)):
                if j not in touched and any(k in accepted[j] for k in keys):
                    finding(out, "CON_ANNEX_SHARED", "פסקה בנספח חולקת מונח או מספר עם הכרעה %s: לבדוק שהיא עקבית"
                            % d.get("id"), "פסקה %d" % j)
    # 19, 23: תשובות הלקוח
    for a in state.get("client_answers") or []:
        if not a.get("clause_ids") or not a.get("status"):
            finding(out, "CON_CLIENT_ANSWER", "רשומה ב-client_answers בלי clause_ids או status", a.get("question", ""),
                    blocking=True)
        elif a.get("status") == "applied" and a.get("value") and str(a["value"]) not in whole:
            finding(out, "CON_CLIENT_ANSWER", "התשובה \"%s\" יושמה, אבל אינה בנוסח המתקבל" % a["value"],
                    ", ".join(a["clause_ids"]), blocking=True)
    # 23: נספח שגובר על ההסכם
    for i, t in enumerate(accepted):
        for rx in PREVAILS:
            m = rx.search(t)
            if m:
                finding(out, "PREC_ANNEX_PREVAILS", "נשאר סעיף שקובע שמסמך אחר גובר על ההסכם: \"%s\"" % m.group(0)[:80],
                        "פסקה %d" % i, blocking=True)
    for c in ((meta.get("deal_documents") or state.get("deal_documents") or {}).get("conflicts") or []):
        if not c.get("decision"):
            finding(out, "DEAL_DOCS_CONFLICT", "סתירה בין מסמכי העסקה בלי הכרעה: %s" % c.get("conflict", ""),
                    ", ".join(c.get("documents") or []), blocking=True)
    # 24: מנטרלים בנוסח שנשאר בלי שינוי
    for i, t in enumerate(accepted):
        if i in touched or i >= len(theirs) or t != theirs[i]:
            continue
        for w in NEUTRALIZERS:
            if w.lower() in t.lower():
                finding(out, "NEUTRALIZER", "ביטוי מנטרל בנוסח שלא שונה: \"%s\". להכריע בו" % w, "פסקה %d" % i)
    # 26: מצגים
    reps = {r.get("clause_id"): r for r in state.get("company_representations") or []}
    for d, txt, rx in [(d, t, REPRESENT) for d, t in our_texts(decisions)] + \
            [(d, d.get("external_comment") or "", REPRESENT_BUBBLE) for d in decisions]:
        m = rx.search(txt or "")
        if not m:
            continue
        rec = reps.get(d.get("clause_id")) or reps.get(d.get("id"))
        bracketed = bool(re.search(r"\[[^\]]*" + re.escape(m.group(0)) + r"[^\]]*\]", txt))
        if not bracketed and not (rec and rec.get("status") in ("confirmed", "approved")):
            finding(out, "REP_UNAPPROVED", "מצג או התחייבות (\"%s\") בנוסח שלנו בלי רשומה מאושרת ב-company_representations,"
                    " ולא בסוגריים מרובעים" % m.group(0), d.get("id"), blocking=True)
    # 27: בדיקת התנגשות
    dc = meta.get("deal_context") or {}
    # בדיקת ההתנגשות רשומה ב-meta.deal_context.existing_agreements_with_counterparty (גם רשימה ריקה היא
    # בדיקה שנעשתה), כמו בסכמה
    conflict_done = "existing_agreements_with_counterparty" in dc or bool((dc.get("conflict_check") or {}).get("done"))
    for d, txt in our_texts(decisions):
        if CONFLICT_REP.search(txt) and not conflict_done:
            finding(out, "CONFLICT_CHECK", "מצג \"%s\" בלי בדיקת התנגשות רשומה (conflict_check)" %
                    CONFLICT_REP.search(txt).group(0), d.get("id"), blocking=True)
    if EXHAUST.search(whole):
        for e in dc.get("existing_agreements_with_counterparty") or state.get("existing_agreements_with_counterparty") or []:
            if e.get("in_force", True) and not e.get("effect_of_new_agreement"):
                finding(out, "EXISTING_AGREEMENT", "יש סעיף מיצוי או ביטול הסכמים קודמים, וההסכם הקיים \"%s\" בלי השפעה "
                        "רשומה" % (e.get("name") or e.get("file") or ""), "")
    # 28: שם של צד מהסכם אחר בבועה
    others = set()
    for doc in (manifest or {}).get("documents") or []:
        for k in ("counterparty", "parties"):
            v = doc.get(k)
            for name in (v if isinstance(v, list) else [v]):
                if name and len(str(name)) >= 3:
                    others.add(str(name))
    current = str(meta.get("counterparty_name") or "")
    for d in decisions:
        bub = d.get("external_comment") or ""
        for name in others:
            if name in bub and not (current and (name in current or current in name)):
                finding(out, "OTHER_PARTY_NAME", "בבועה החיצונית שם של צד מהסכם אחר: \"%s\"" % name, d.get("id"),
                        blocking=True)
    # 32: תנאי מסירה, מטבע והצמדה
    price_paras = {i for i, t in enumerate(accepted) if annex_start is not None and i >= annex_start and PRICE.search(t)}
    for d, txt in our_texts(decisions):
        if (INCOTERMS.search(txt) or CURRENCY.search(txt)) and price_paras and not (touched & price_paras):
            finding(out, "PRICE_TERMS", "התיקון משנה תנאי מסירה, מטבע או הצמדה, ונספח המחירים לא שונה", d.get("id"))
        if CONFORMING_ONLY.match(d.get("external_comment") or "x") and (PRICE.search(txt) or CURRENCY.search(txt)):
            finding(out, "PRICE_CONFORMING", "בועה \"תיקון עקבי\" בלבד על שינוי שנוגע במחיר", d.get("id"), blocking=True)
    # 34: ציות
    for i, t in enumerate(theirs):
        if not COMPLIANCE.search(t):
            continue
        ds = by_para.get(i) or []
        ok = any(((d.get("user_decision") or {}).get("answer_kind") == "explicit") or
                 (d.get("decision_required") or {}).get("required") for d in ds)
        if not ok:
            finding(out, "COMPLIANCE", "סעיף ציות (\"%s\") בלי הכרעה מפורשת של המשתמש" % COMPLIANCE.search(t).group(0),
                    "פסקה %d" % i, blocking=True)
    # 44: הסכם דו-לשוני
    bil = meta.get("bilingual") or {}
    he = sum(1 for t in theirs if len(HEB.findall(t)) > len(LAT.findall(t)) and len(t) > 30)
    en = sum(1 for t in theirs if len(LAT.findall(t)) > len(HEB.findall(t)) and len(t) > 30)
    detected = he >= 5 and en >= 5 and min(he, en) >= 0.3 * max(he, en)
    if detected and not bil.get("is_bilingual"):
        finding(out, "BILINGUAL_UNDECLARED", "ההסכם נראה דו-לשוני (%d פסקאות בעברית, %d באנגלית), ו-meta.bilingual אינו"
                " מסמן זאת" % (he, en), "", blocking=True)
    if bil.get("is_bilingual"):
        pairs = {int(k): int(v) for k, v in (bil.get("map") or {}).items()}
        pairs.update({v: k for k, v in list(pairs.items())})
        for d in decisions:
            p = d.get("para")
            if p is None or d.get("op") in ("accept", "comment_only"):
                continue
            mate = pairs.get(p)
            if mate is None or not by_para.get(mate):
                finding(out, "BILINGUAL_ONE_SIDE", "הכרעה שמשנה נוסח בגרסה אחת בלבד", d.get("id"), blocking=True)
        for mm in bil.get("mismatches") or []:
            if not mm.get("decision"):
                finding(out, "BILINGUAL_MISMATCH", "סתירה בין הגרסאות בלי הכרעה: %s" % mm.get("difference", ""),
                        mm.get("clause_ref_a", ""), blocking=True)
    # 1: התאמת הפלייבוק, ומפת המונחים
    res = state.get("playbook_resolution") or {}
    match = res.get("playbook_match") or meta.get("playbook_match")
    if match in ("side_mismatch", "family_mismatch", "mutuality_mismatch"):
        finding(out, "POSITION_MISMATCH", "הפלייבוק שהוחל אינו מתאים להסכם (%s)" % match, "", blocking=True)
    received_text = "\n".join(theirs)
    for d, txt in our_texts(decisions):
        for lab in PARTY_LABELS:
            # "Customer Data" הוא מונח מוגדר, ולא הכינוי של צד: מילה באות גדולה אחרי הכינוי מחברת אותו למונח
            rx = r"(?<![\w֐-׿'])" + re.escape(lab) + r"(?![\w֐-׿])(?!\s+[A-Z])(?!'s)"
            if re.search(rx, txt) and lab not in received_text:
                finding(out, "PARTY_LABEL", "בנוסח שלנו הכינוי \"%s\", שאינו בהסכם: הנוסח לא עבר את מפת המונחים" % lab,
                        d.get("id"), blocking=True)
    # 59: סימני האדום
    rule_decided = {}
    for d in decisions:
        for r in d.get("rule_ids") or []:
            rule_decided.setdefault(r, set()).update({d.get("para"), d.get("after_para")})
    for rule in (core or {}).get("clauses") or (core or {}).get("rules") or []:
        rid = rule.get("id") or rule.get("rule_id")
        red = ((rule.get("traffic_light") or {}).get("red") or rule.get("red") or {})
        markers = list(rule.get("red_flags") or []) + list(red.get("red_flags") or []) + \
            [x for x in red.get("match_criteria") or [] if isinstance(x, str)]
        for mk in markers:
            mk = str(mk).strip()
            if len(mk) < 4:
                continue
            for i, t in enumerate(accepted):
                if mk in t and i not in (rule_decided.get(rid) or set()):
                    finding(out, "RED_MARKER", "סימן אדום של הכלל %s (\"%s\") בנוסח המתקבל, בלי הכרעה לאותו כלל" % (rid, mk),
                            "פסקה %d" % i, blocking=True)
    # 6: טקסט מוסתר אצלם
    for h in hidden_scan(received):
        if h["part"] == "word/document.xml" and h["paragraph"] is not None:
            rroot = dt.document_root(received)        # ניתוח אחד: אותם אלמנטים בשתי הרשימות
            body = dt.body_paragraphs(rroot)
            all_p = list(rroot.iter(W + "p"))
            try:
                idx = body.index(all_p[h["paragraph"]])
            except (ValueError, IndexError):
                idx = None
            if idx is not None and not by_para.get(idx):
                finding(out, "HIDDEN_TEXT", "טקסט מוסתר (%s) בטיוטה שלהם, בלי הכרעה: \"%s\"" % (h["how"], h["text"][:80]),
                        "פסקה %d" % idx, blocking=True)
        elif h["how"] == "properties":
            finding(out, "HIDDEN_TEXT", "טקסט במאפייני הקובץ (%s): לבדוק שאינו הוראה" % h["part"], h["part"])
    # 10, 11: הבועות שלהם
    lawyer = {str(x).strip() for x in ((profile or {}).get("lawyer_names") or []) if x}
    exposed = {(e.get("quote") or "")[:40] for e in (meta.get("exposed_comments") or state.get("exposed_comments") or [])}
    replies_to = {d.get("reply_to_comment") for d in decisions if d.get("reply_to_comment")}
    for c in comment_info(received):
        if c["author"] in lawyer or c["author"] == dt.INTERNAL_AUTHOR:
            continue
        if INTERNAL_HINT.search(c["text"]) and c["text"][:40] not in exposed:
            finding(out, "THEIR_INTERNAL_COMMENT", "בועה של %s נראית פנימית, ואינה רשומה ב-exposed_comments: \"%s\"" %
                    (c["author"], c["text"][:100]), "בועה %s" % c["id"], blocking=True)
        if not c["has_reply"] and c["id"] not in replies_to:
            finding(out, "THEIR_COMMENT_UNANSWERED", "לבועה של %s אין מענה: \"%s\"" % (c["author"], c["text"][:80]),
                    "בועה %s" % c["id"])
    # 56: צירופים
    combos = load(os.path.join(HERE, "combos.json")) or []
    checked = {tuple(sorted(x.get("decisions") or [])) for x in (meta.get("combo_checks") or state.get("combo_checks") or [])}
    texts = {d.get("id"): " ".join(str(d.get(k) or "") for k in ("new_text", "new", "text")) for d in decisions}
    for combo in combos:
        a = sorted(i for i, t in texts.items() if t.strip() and re.search(combo["a"], t, re.I))
        b = sorted(i for i, t in texts.items() if t.strip() and re.search(combo["b"], t, re.I))
        pairs = {tuple(sorted((x, y))) for x in a for y in b if x != y}
        open_pairs = sorted(pr for pr in pairs if pr not in checked)
        if open_pairs:
            finding(out, "COMBO", "צירוף \"%s\": %s מול %s. לבדוק אותם יחד, ולרשום ב-meta.combo_checks" %
                    (combo["name"], ", ".join(a), ", ".join(b)), "")
    # כירורגי, ולא פסקה במקום פסקה (ניל, 18.10.2026): שינוי של כמה מילים מסומן רק בהן
    deleted = {d.get("para"): d for d in decisions if d.get("op") == "delete_paragraph"}
    for d in decisions:
        if d.get("op") != "insert_paragraph" or not isinstance(d.get("after_para"), int):
            continue
        for p in (d["after_para"], d["after_para"] + 1):
            old = deleted.get(p)
            if old is None or p >= len(theirs):
                continue
            tok_o = re.findall(r"\w+", theirs[p])
            tok_n = set(re.findall(r"\w+", d.get("text") or ""))
            if tok_o and sum(1 for t in tok_o if t in tok_n) / len(tok_o) >= 0.4:
                finding(out, "PARAGRAPH_REPLACED", "הפסקה נמחקה ונכתבה מחדש (%s ו-%s), ורוב המילים נשארו: לסמן "
                        "ב-replace_span רק את מה שמשתנה" % (old.get("id"), d.get("id")), "פסקה %d" % p, blocking=True)
    for d in decisions:
        if d.get("op") == "replace" and isinstance(d.get("para"), int) and d["para"] < len(theirs):
            orig, new = theirs[d["para"]], d.get("new_text") or ""
            ops = dt.char_ops(orig, new)
            marked = sum((o[2] - o[1]) for o in ops if o[0] == "delete") + sum(len(o[3]) for o in ops if o[0] == "insert")
            tok_o = re.findall(r"\w+", orig)
            tok_n = set(re.findall(r"\w+", new))
            overlap = (sum(1 for t in tok_o if t in tok_n) / len(tok_o)) if tok_o else 0.0
            if marked >= 0.8 * (len(orig) + len(new)) and overlap >= 0.4:
                finding(out, "REPLACE_COLLAPSED", "ההכרעה מסמנת את רוב הפסקה אף שרוב המילים נשארו: לסמן "
                        "ב-replace_span רק את מה שמשתנה", d.get("id"), blocking=True)
    for d in decisions:
        if d.get("op") in ("replace", "replace_span", "insert_paragraph") and not (d.get("plain_effect")
                                                                                  and d.get("position_effect")):
            finding(out, "EFFECT_FIELDS", "הכרעה שמכניסה נוסח בלי plain_effect ו-position_effect", d.get("id"))
    review_2210(out, theirs, decisions, state, core, received)
    return out


# --------------------------------------------------------------------------- הערות ענבל 22.10.2026
# כללים 1 עד 12 של ההערות לנושא ונותן. הבדיקות רצות על הנוסח שמתקבל אחרי ההכרעות (result_view), במספור של
# הטיוטה שהתקבלה, כך שידוע לכל פסקה אם היא שלנו. כל מה שתלוי בעסקה מגיע מקובץ ההכרעות, ממצב העסקה ומהגרעין.
PROVISO_REF = re.compile(r"הסייג (?:האמור|ה?נ[\"״]ל|שלעיל|שלהלן|הבא|דלעיל)|בכפוף לסייג|"
                         r"the (?:foregoing|above|following|said|preceding) proviso|subject to the proviso", re.I)
PROVISO_MARK = re.compile(r"ובלבד ש|בתנאי ש|ואולם|אלא אם|provided(?:,)? (?:however,? )?that|provided always that|"
                          r"except that", re.I)
BACKREF = re.compile(r"^\s*(?:\(?[א-תa-z0-9]{1,3}[.)]\s*)?(?:כאמור לעיל|האמור לעיל|על אף האמור לעיל|בנוסף לאמור לעיל|"
                     r"מבלי לגרוע מהאמור לעיל|The foregoing|Notwithstanding the foregoing|In addition to the foregoing|"
                     r"Without limiting the foregoing)", re.I)
LEAD_IN = re.compile(r"(?::|שלהלן|כדלקמן|as follows|the following)\s*:?\s*$", re.I)
LIST_ITEM = re.compile(r"^\s*(?:\(?[א-י]\)|\(?[a-z]\)|\(?\d{1,2}\)|[א-י]['׳]?[.)]|[a-z][.)]|\(?[ivx]{1,4}\))\s", re.I)
DANGLING_END = re.compile(r"(?:,|;|\s)(?:או|וכן|or|and)\s*[;:]?\s*$", re.I)
DANGLING_MID = re.compile(r"(?:,|\s)(?:או|or|and)\s*[.;](?:\s|$)", re.I)
TAIL_CONJ = re.compile(r"[;,]\s*(?:או|וכן|or|and)\s*$", re.I)
OBLIGATION = re.compile(r"\bshall\b|\bmust\b|יתחייב|מתחייב|תתחייב|מחויב|חייב(?:ת|ים)?\s|אסור|לא יהיה רשאי|לא תהיה רשאית",
                        re.I)
REF_BUBBLE = re.compile(r"רא(?:ו|ה) (?:את )?הערת(?:נו|י)|כאמור בהערת(?:נו|י)|כמפורט בהערת(?:נו|י)|ר' הערת|"
                        r"see (?:our )?(?:comment|note)|as per our (?:comment|note)|as noted above|"
                        r"part of the same change|same as (?:above|our comment)", re.I)
FACT_THEM = re.compile(r"מאחר ש(?:אתם|אתן|הנכם|החברה שלכם)|הואיל ואתם|בהיותכם|כפי שידוע(?: לנו)? ש|"
                       r"אתם (?:פועלים|נסחרים|מעסיקים|מפוקחים|רשומים|מתחרים)|לקוחותיכם|עובדיכם|מתחריכם|המתחרים שלכם|"
                       r"הרגולטור (?:שלכם|החל עליכם)|"
                       r"given that you|since you (?:are|operate|have)|as you (?:are|operate)|you operate|you employ|"
                       r"you are (?:a |an )?(?:public|listed|regulated|subject to)|"
                       r"your (?:customers|clients|employees|competitors|regulator)", re.I)
FACT_US = re.compile(r"(?:החברה|אנו|אנחנו) (?:היא )?(?:חברה ציבורית|נסחרת|נסחרים|פועלת ב(?!התאם|אופן|מסגרת|הקשר)|"
                     r"פועלים ב(?!התאם|אופן|מסגרת|הקשר)|מעסיקה|מעסיקים|"
                     r"מפוקחת|מפוקחים|כפופה לפיקוח|רשומה ב)|כחברה (?:ציבורית|נסחרת|בורסאית|זרה|מפוקחת)|"
                     r"we are (?:a )?(?:public|listed|regulated)|we operate in|we employ|as a (?:public|listed|regulated) "
                     r"(?:company|entity)|our (?:customers|employees|regulator)", re.I)
FACT_SOURCES = ("profile", "user_answer", "agreement")
WEAKNESS = re.compile(r"אין לנו ברירה|אין לנו חלופה|אין בידינו חלופה|קשה לנו לגבות|יקשה עלינו לגבות|קשה לגבות|"
                      r"אנו תלויים|אנחנו תלויים|תלויים בכם|לחץ זמנים|לוח הזמנים שלנו לחוץ|תזרים|"
                      r"we have no (?:choice|alternative)|we (?:depend|rely) (?:heavily )?on you|"
                      r"we are under (?:time )?pressure|cash ?flow|difficult (?:for us )?to collect|we cannot afford", re.I)
LAW_TOPIC = re.compile(r"דין|שיפוט|פורום|סמכות|בוררות|שפה|מטבע|מס(?:ים)?\b|מיסוי|ניכוי במקור|פרטיות|מידע אישי|ניירות ערך|"
                       r"רגולצ|governing law|jurisdiction|forum|arbitration|language|currency|tax|withholding|privacy|"
                       r"data protection|securities|regulat", re.I)
# כלל 12: נושאים שהעמדה בהם תלויה בזהות הצד שכנגד (דין ופורום, שפה גוברת, מטבע ומסים)
CP_TOPIC = re.compile(r"דין|שיפוט|פורום|סמכות|בוררות|שפה|מטבע|מס(?:ים)?\b|מיסוי|ניכוי במקור|governing law|"
                      r"jurisdiction|forum|arbitration|language|currency|tax|withholding", re.I)
HE_MONTHS = {"ינואר": 1, "פברואר": 2, "מרץ": 3, "מרס": 3, "אפריל": 4, "מאי": 5, "יוני": 6, "יולי": 7, "אוגוסט": 8,
             "ספטמבר": 9, "אוקטובר": 10, "נובמבר": 11, "דצמבר": 12}
EN_MONTHS = {m: i + 1 for i, m in enumerate(("january", "february", "march", "april", "may", "june", "july", "august",
                                              "september", "october", "november", "december"))}
ANCHOR_CTX = re.compile(r"תחילת|תחולת|יחול|ייכנס לתוקף|ייכנסו לתוקף|נכנס לתוקף|מועד התחילה|מועד התחולה|מועד הקובע|"
                        r"תקופת ההסכם|יתחיל|תתחיל|החל מיום|החל מתאריך|effective|commenc|start date|as of|"
                        r"term (?:of this agreement )?(?:shall )?(?:begin|start)", re.I)
DATE_RX = [
    (re.compile(r"(?<!\d)(\d{1,2})[./](\d{1,2})[./](\d{4})(?!\d)"), "dmy"),
    (re.compile(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)"), "ymd"),
    (re.compile(r"(?<!\d)(\d{1,2})\s+ב?(%s),?\s+(\d{4})" % "|".join(HE_MONTHS)), "d_he_y"),
    (re.compile(r"(?<!\d)(\d{1,2})(?:st|nd|rd|th)?\s+(%s),?\s+(\d{4})" % "|".join(EN_MONTHS), re.I), "d_en_y"),
    (re.compile(r"\b(%s)\s+(\d{1,2}),?\s+(\d{4})" % "|".join(EN_MONTHS), re.I), "en_d_y"),
]
EMPTY_ANCHOR = re.compile(r"(?:מיום|מתאריך|החל מיום|ביום|effective(?: as of)?|dated|as of|commencing on)\s*"
                          r"(?:_{2,}|\[\s*[•·.\s]*\]|\.{3,}|__\s*/\s*__)", re.I)


def result_view(theirs, decisions):
    """הנוסח שמתקבל אחרי ההכרעות, במספור של הטיוטה שהתקבלה. מחזיר רשימת (מקור, טקסט, שלנו): מקור הוא אינדקס
    הפסקה שלהם, או ("ins", after_para) לפסקה שהוספנו. פסקה שנמחקה אינה ברשימה."""
    res = list(theirs)
    ours = set()
    gone = set()
    ins = {}
    for d in decisions:
        p, op = d.get("para"), d.get("op")
        if op == "insert_paragraph" and isinstance(d.get("after_para"), int):
            ins.setdefault(d["after_para"], []).append(d.get("text") or "")
        if not isinstance(p, int) or not 0 <= p < len(res):
            continue
        if op == "replace" and d.get("new_text") is not None:
            res[p] = d["new_text"]
            ours.add(p)
        elif op == "replace_span" and d.get("old") and d["old"] in res[p]:
            res[p] = res[p].replace(d["old"], d.get("new") or "", 1)
            ours.add(p)
        elif op == "delete_paragraph":
            gone.add(p)
    out = []
    for i, t in enumerate(res):
        if i not in gone:
            out.append((i, t, i in ours))
        for t2 in ins.get(i, []):
            out.append((("ins", i), t2, True))
    return out, gone


def _dates(text):
    import datetime as _dt
    for rx, kind in DATE_RX:
        for m in rx.finditer(text):
            g = m.groups()
            try:
                if kind == "dmy":
                    d = _dt.date(int(g[2]), int(g[1]), int(g[0]))
                elif kind == "ymd":
                    d = _dt.date(int(g[0]), int(g[1]), int(g[2]))
                elif kind == "d_he_y":
                    d = _dt.date(int(g[2]), HE_MONTHS[g[1]], int(g[0]))
                elif kind == "d_en_y":
                    d = _dt.date(int(g[2]), EN_MONTHS[g[1].lower()], int(g[0]))
                else:
                    d = _dt.date(int(g[2]), EN_MONTHS[g[0].lower()], int(g[1]))
            except (ValueError, KeyError):
                continue
            yield m, d


def time_anchors(theirs, today=None):
    """כלל 4: עוגני זמן בנייר שלהם שנמצאים בעבר או ריקים. לכל ממצא: para, text, issue (past / empty), date."""
    import datetime as _dt
    today = today or _dt.date.today()
    out = []
    for i, t in enumerate(theirs):
        for m in EMPTY_ANCHOR.finditer(t):
            out.append({"para": i, "text": m.group(0), "issue": "empty", "date": None})
        for m, d in _dates(t):
            before = t[max(0, m.start() - 60):m.start()]
            if d < today and ANCHOR_CTX.search(before):
                out.append({"para": i, "text": t[max(0, m.start() - 40):m.end()].strip(), "issue": "past",
                            "date": d.isoformat()})
    return out


def _terms_in(text):
    out = set()
    for rx in DEF_PATTERNS:
        for m in rx.finditer(text or ""):
            out.update(g.strip() for g in m.groups() if g)
    return out


def _term_rx(term):
    stem = term[1:] if term.startswith("ה") and len(term) > 3 else term
    if stem != term:
        return re.compile(r"(?<![א-ת])[ולבכמש]{0,2}ה?" + re.escape(stem) + r"(?![א-ת])")
    return re.compile(re.escape(term))


def dependents_of(d, theirs, labels):
    """כלל 2: הסעיפים שתלויים בהכרעה שמשנה משטר. מחזיר רשימת אינדקסים בטיוטה שהתקבלה, בלי הפסקה עצמה.
    תלוי: פסקה שמפנה לסעיף ששונה, פסקה שמשתמשת במונח שהגדרתו שונתה, ופסקאות ש-same_topic מונה."""
    p = d.get("para")
    if not isinstance(p, int) or not 0 <= p < len(theirs):
        return []
    # רק הכרעה שהסקיל הצהיר שהיא משנה משטר (regime). השלמת שם או הוספת כינוי בפסקת הגדרות אינן משנות את
    # המשמעות, ולכן אין הנחה אוטומטית; הכרעה שנוגעת בהגדרה בלי regime מקבלת אזהרה (REGIME_UNDECLARED)
    regime = d.get("regime")
    terms = _terms_in(theirs[p])
    if regime in (None, "", "none"):
        return []
    deps = set()
    lab = labels[p] if p < len(labels) else None
    if lab:
        for j, t in enumerate(theirs):
            if j == p:
                continue
            for rx in (REF_HE, REF_EN):
                if any(m.group(1) == lab for m in rx.finditer(t)):
                    deps.add(j)
    if regime == "definition":
        for term in terms:
            trx = _term_rx(term)
            deps.update(j for j, t in enumerate(theirs) if j != p and trx.search(t))
    deps.update(x for x in d.get("same_topic") or [] if isinstance(x, int) and x != p)
    return sorted(deps)


def _rule_index(core):
    return {(r.get("id") or r.get("rule_id")): r for r in (core or {}).get("clauses") or (core or {}).get("rules") or []}


def _kinds(meta):
    v = ((meta.get("deal_context") or {}).get("counterparty_kind"))
    return set(v if isinstance(v, list) else [v] if v else [])


def _reviewed(state, code, para):
    """בדיקה מבנית היא היוריסטיקה. עורך הדין שבדק ומצא שההפניה תקינה רושם זאת ב-checks_reviewed, עם נימוק."""
    return any(isinstance(x, dict) and x.get("code") == code and x.get("para") == para and x.get("reason")
               for x in state.get("checks_reviewed") or [])


def review_2210(out, theirs, decisions, state, core, received):
    meta = state.get("meta") or {}
    by_para = {}
    for d in decisions:
        if isinstance(d.get("para"), int):
            by_para.setdefault(d["para"], []).append(d)
    view, gone = result_view(theirs, decisions)
    vtexts = [t for _, t, _ in view]

    # כלל 1: שלמות מבנית
    for k, (src, t, ours) in enumerate(view):
        if PROVISO_REF.search(t):
            window = " ".join(vtexts[max(0, k - 1):k + 2])
            if not PROVISO_MARK.search(window):
                i = src if isinstance(src, int) else src[1]
                before = " ".join(theirs[max(0, i - 1):i + 2])
                caused = (bool(PROVISO_MARK.search(before)) or ours) and not _reviewed(state, "STRUCT_ORPHAN_PROVISO", i)
                finding(out, "STRUCT_ORPHAN_PROVISO", "הפניה לסייג (\"%s\") בלי סייג שהיא מפנה אליו בנוסח המתקבל"
                        % PROVISO_REF.search(t).group(0), "פסקה %s" % (i,), blocking=caused)
        nxt_text = vtexts[k + 1] if k + 1 < len(vtexts) else ""
        if ours and (DANGLING_MID.search(t) or (DANGLING_END.search(t) and not LIST_ITEM.search(nxt_text))):
            finding(out, "STRUCT_DANGLING_CONJ", "בנוסח שלנו נשארה מילת חיבור (\"או\", \"and\") בלי פריט אחריה",
                    "פסקה %s" % (src if isinstance(src, int) else src[1],), blocking=True)
    alive = [i for i in range(len(theirs)) if i not in gone]
    for p in sorted(gone):
        nxt = next((i for i in alive if i > p), None)
        prv = next((i for i in reversed(alive) if i < p), None)
        if nxt is not None and BACKREF.search(theirs[nxt]) and not _reviewed(state, "STRUCT_BACKREF", nxt):
            finding(out, "STRUCT_BACKREF", "הפסקה שאחרי הפסקה שמחקנו מפנה \"לעיל\", ומה שהיא הפנתה אליו נמחק",
                    "פסקה %d" % nxt, blocking=True)
        last_item = nxt is None or not LIST_ITEM.search(theirs[nxt])
        if prv is not None and last_item and LIST_ITEM.search(theirs[p]):
            if LEAD_IN.search(theirs[prv]) and all(j in gone for j in range(prv + 1, p + 1)):
                finding(out, "STRUCT_LIST_EMPTY", "כל פריטי הרשימה נמחקו, ונשאר משפט הפתיחה שלה (\"%s\")"
                        % theirs[prv][-40:], "פסקה %d" % prv, blocking=True)
            elif TAIL_CONJ.search(theirs[prv]):
                finding(out, "STRUCT_DANGLING_CONJ", "מחקנו את הפריט האחרון ברשימה, ו\"או\" או \"and\" נשארו לפני "
                        "פריט שכבר אינו קיים", "פסקה %d" % prv, blocking=True)
    for d in decisions:
        txt = (d.get("text") if d.get("op") == "insert_paragraph" else d.get("new")) or ""
        if PROVISO_MARK.match(txt.strip()) and OBLIGATION.search(txt):
            finding(out, "STRUCT_PROVISO_ROLE", "נוסח שהכנסנו כסייג כולל התחייבות או איסור. התחייבות מקבלת פסקה "
                    "משלה, וסייג צריך לסייג", d.get("id"))

    # כלל 2: סעיפים תלויים
    labels = numbered_labels(received)
    for d in decisions:
        p = d.get("para")
        if d.get("regime") in (None, "") and d.get("op") in ("replace", "replace_span", "delete_paragraph") and \
                isinstance(p, int) and 0 <= p < len(theirs):
            spans = [m.span() for rx in DEF_PATTERNS for m in rx.finditer(theirs[p])]
            at = theirs[p].find(d.get("old") or "\x00") if d.get("op") == "replace_span" else -1
            touched_def = spans and (d.get("op") != "replace_span" or (
                at >= 0 and any(a0 < at + len(d["old"]) and at < b0 for a0, b0 in spans)))
            if touched_def:
                finding(out, "REGIME_UNDECLARED", "ההכרעה נוגעת בהגדרה: לקבוע regime (definition, או none כשהמשמעות "
                        "אינה משתנה), כדי שהסעיפים התלויים ייבדקו", d.get("id"))
        deps = dependents_of(d, theirs, labels)
        if not deps:
            continue
        handled, no_reason = set(), []
        for x in d.get("dependents") or []:
            if not isinstance(x, dict) or not isinstance(x.get("para"), int):
                continue
            if x.get("decision") or (x.get("keep") and x.get("reason")):
                handled.add(x["para"])
            elif x.get("keep"):
                no_reason.append(x["para"])
        missing = [j for j in deps if j not in handled and not any(e is not d for e in by_para.get(j, []))]
        missing = [j for j in missing if j not in no_reason]
        if no_reason:
            finding(out, "DEPENDENT_KEEP_NO_REASON", "סעיף תלוי שהוחלט להשאיר בלי נימוק: פסקאות %s"
                    % ", ".join(map(str, no_reason)), d.get("id"), blocking=True)
        if missing:
            finding(out, "DEPENDENT_UNDECIDED", "ההכרעה משנה משטר (%s), ויש סעיפים תלויים בלי הכרעה: פסקאות %s"
                    % (d.get("regime") or "definition", ", ".join(map(str, missing))), d.get("id"), blocking=True)

    # כלל 3: בדיקת התוצאה של כל כלל שהוחל
    rules = _rule_index(core)
    applied = {r for d in decisions for r in d.get("rule_ids") or []}
    done = {(x.get("rule_id"), x.get("id")): x for x in state.get("post_checks_done") or [] if isinstance(x, dict)}
    annex_at = next((k for k, t in enumerate(vtexts) if re.match(r"^\s*(?:נספח|Annex|Schedule|Exhibit|Appendix)\s", t)),
                    len(vtexts))
    for rid in sorted(applied):
        rule = rules.get(rid) or {}
        for pc in rule.get("post_checks") or []:
            if not isinstance(pc, dict):
                continue
            block = pc.get("on_fail") == "block" or (pc.get("on_fail") is None and
                                                      str(rule.get("importance", "")).lower() == "critical")
            scope = pc.get("scope") or "whole_agreement"
            if scope == "definitions":
                text = "\n".join(t for t in vtexts if _terms_in(t))
            elif scope == "annexes":
                text = "\n".join(vtexts[annex_at:])
            else:
                text = "\n".join(vtexts)
            cond = pc.get("pass_when")
            where = "%s/%s" % (rid, pc.get("id", "?"))
            if isinstance(cond, dict):
                bad = [x for x in cond.get("absent") or [] if re.search(x, text, re.I)]
                lack = [x for x in cond.get("present") or [] if not re.search(x, text, re.I)]
                if bad or lack:
                    finding(out, "POST_CHECK_FAILED", "בדיקת התוצאה של הכלל נכשלה (%s)%s%s" % (
                        pc.get("intent") or "", ": נמצא %s" % ", ".join(bad) if bad else "",
                        ": חסר %s" % ", ".join(lack) if lack else ""), where, blocking=block)
            else:
                rec = done.get((rid, pc.get("id")))
                if rec is None:
                    finding(out, "POST_CHECK_MANUAL", "בדיקת תוצאה שאינה אוטומטית, ולא נרשמה ב-post_checks_done: %s"
                            % (pc.get("intent") or cond or ""), where)
                elif rec.get("result") == "fail":
                    finding(out, "POST_CHECK_FAILED", "בדיקת התוצאה נרשמה כנכשלת: %s" % (pc.get("intent") or ""),
                            where, blocking=block)

    # כלל 4: עוגני זמן
    known = {(x.get("para"), x.get("issue")) for x in state.get("time_anchors") or []
             if isinstance(x, dict) and x.get("status") in ("answered", "accepted", "fixed")}
    for a in time_anchors(theirs):
        if (a["para"], a["issue"]) not in known:
            finding(out, "TIME_ANCHOR", "עוגן זמן %s בנייר שלהם (\"%s\"): שאלה לפני ההכרעה, ורישום ב-time_anchors"
                    % ("שכבר עבר" if a["issue"] == "past" else "ריק", a["text"][:80]), "פסקה %d" % a["para"],
                    blocking=True)

    # כלל 5: מונחים עמומים בנוסח שלנו
    from common import vague_terms
    for d, txt in our_texts(decisions):
        for f in vague_terms.undefined(txt):
            finding(out, "VAGUE_TERM", "מונח עמום בנוסח שלנו (\"%s\") בלי מבחן מוגדר: תקן, הוראות בכתב, רף מספרי או "
                    "נספח" % f["term"], d.get("id"))

    # כללים 6 ו-7: עובדה על הצדדים, והישות בנייר
    ent = meta.get("entity_check") or {}
    mismatch = ent.get("match") in ("related", "none") and not ent.get("facts_confirmed")
    for d in decisions:
        bub = d.get("external_comment") or ""
        m = FACT_THEM.search(bub) or FACT_US.search(bub)
        if m and d.get("fact_source") not in FACT_SOURCES:
            finding(out, "FACT_WITHOUT_SOURCE", "הבועה נשענת על עובדה על אחד הצדדים (\"%s\") בלי מקור ב-fact_source "
                    "(profile, user_answer או agreement)" % m.group(0), d.get("id"), blocking=True)
        if mismatch and d.get("fact_source") == "profile":
            finding(out, "ENTITY_PROFILE_FACT", "הישות בנייר אינה הישות שבפרופיל, והמשתמש לא אישר שהעובדות חלות עליה: "
                    "אין להשתמש בעובדה מהפרופיל", d.get("id"), blocking=True)
        if mismatch and not (d.get("decision_required") or {}).get("required"):
            for rid in d.get("rule_ids") or []:
                title = (rules.get(rid) or {}).get("title") or ""
                if LAW_TOPIC.search(title):
                    finding(out, "ENTITY_RULE_UNCONFIRMED", "כלל שתלוי במקום, בדין, ברגולציה או ברישום (%s), כשהישות "
                            "בנייר לא אושרה: נדרשת הכרעתך" % (title or rid), d.get("id"), blocking=True)

    # כלל 8: בועה אחת לכל נושא
    seen = {}
    for d in decisions:
        bub = d.get("external_comment") or ""
        if bub and REF_BUBBLE.search(bub):
            finding(out, "REF_BUBBLE", "בועת הפניה (\"%s\"). כל השינויים של אותו כלל באותו סעיף מקבלים בועה אחת "
                    "(cluster_id)" % REF_BUBBLE.search(bub).group(0), d.get("id"), blocking=True)
        if bub and isinstance(d.get("para"), int) and d.get("rule_ids") and not d.get("cluster_id"):
            seen.setdefault((d["para"], tuple(sorted(d["rule_ids"]))), []).append(d.get("id"))
    for (p, rids), ids in sorted(seen.items(), key=lambda kv: str(kv[0])):
        if len(ids) > 1:
            finding(out, "BUBBLE_SAME_TOPIC", "כמה בועות לאותו כלל באותו סעיף (%s): אשכול אחד עם בועה אחת"
                    % ", ".join(ids), "פסקה %d" % p, blocking=True)

    # כלל 9: חולשה שלנו בנימוק
    for d in decisions:
        m = WEAKNESS.search(d.get("external_comment") or "")
        if m:
            finding(out, "WEAKNESS_IN_BUBBLE", "הנימוק בבועה חושף חולשה שלנו (\"%s\"). לנסח כאינטרס של העסקה או "
                    "כהגינות, והחשש נשאר בשכבה הפנימית" % m.group(0), d.get("id"))

    # כלל 10: קודם מסווגים את הנוסח שלהם
    for d in decisions:
        changes = d.get("op") in ("replace", "replace_span", "delete_paragraph")
        if d.get("their_track") == "green" and changes and not d.get("mandatory"):
            finding(out, "THEIR_GREEN_MARKED", "הנוסח שלהם כבר בירוק, ובכל זאת סומן. נוסח בירוק אינו מסומן",
                    d.get("id"), blocking=True)
        elif d.get("their_track") == "yellow" and d.get("decision_code") in ("R1", "R2") and changes and not (
                d.get("tier") == "tradeable" and d.get("fallback") == "their_wording"):
            finding(out, "THEIR_YELLOW_NOT_CHIP", "הנוסח שלהם בצהוב וביקשנו יותר: ההכרעה היא מטבע חליפין "
                    "(tier: tradeable), ועמדת הנסיגה היא הנוסח שלהם (fallback: their_wording)", d.get("id"))
        elif changes and d.get("rule_ids") and not d.get("their_track"):
            finding(out, "THEIR_TRACK_MISSING", "הכרעה לפי כלל בלי סיווג של הנוסח שלהם (their_track)", d.get("id"))

    # כלל 11: רשימת המאבק, לפני הסימון
    from orchestrator import proportionality as P
    prop = (meta.get("deal_context") or {}).get("proportionality") or {}
    asks = P.count_asks(decisions)["asks"]
    size = prop.get("fight_list_size")
    if isinstance(size, int) and asks > size and prop.get("user_choice") in (None, "", "unanswered"):
        finding(out, "PROPORTIONALITY_UNASKED", "%d בקשות מול רשימת מאבק של %d, והמשתמש לא נשאל לפני הסימון (מצב 4, "
                "עם שלושה ויתורים מוצעים)" % (asks, size), "", blocking=True)
    elif not isinstance(size, int) and asks > 7:
        finding(out, "FIGHT_LIST_MISSING", "%d בקשות, ולא נרשם גודל רשימת המאבק (deal_context.proportionality."
                "fight_list_size)" % asks, "")

    # כלל 12: עמדה שתלויה בזהות הצד שכנגד
    if "foreign" in _kinds(meta):
        for d in decisions:
            if (d.get("decision_required") or {}).get("required") or \
                    (d.get("user_decision") or {}).get("answer_kind") == "explicit":
                continue
            for rid in d.get("rule_ids") or []:
                rule = rules.get(rid) or {}
                conds = [c for c in rule.get("activation_conditions") or [] if isinstance(c, dict)]
                kinds = {c.get("counterparty_kind") for c in conds if c.get("counterparty_kind")}
                dependent = bool(kinds) or bool(CP_TOPIC.search(rule.get("title") or ""))
                if dependent and not kinds & {"foreign", "any"}:
                    finding(out, "COUNTERPARTY_KIND_UNDECIDED", "הכלל %s תלוי בזהות הצד שכנגד, ואין לו תנאי הפעלה "
                            "לצד זר: נדרשת הכרעתך" % (rule.get("title") or rid), d.get("id"), blocking=True)


def main(argv=None):
    sys.dont_write_bytecode = True
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--work", help="קובץ העבודה (לא נדרש עם --hidden-only)")
    ap.add_argument("--received", required=True)
    ap.add_argument("--decisions", help="קובץ ההכרעות (לא נדרש עם --hidden-only)")
    ap.add_argument("--state")
    ap.add_argument("--core")
    ap.add_argument("--manifest", help="corpus-manifest.json: שמות הצדדים בהסכמים החתומים")
    ap.add_argument("--hidden-only", action="store_true", help="רק סריקת הטקסט המוסתר בטיוטה שהתקבלה")
    ap.add_argument("--anchors", action="store_true",
                    help="בקליטה: עוגני הזמן בנייר שלהם שכבר עברו או ריקים (כלל 4). כל ממצא הוא שאלה במנת השאלות")
    a = ap.parse_args(argv)
    if a.anchors:
        if not a.received or not os.path.exists(a.received):
            print("אינו קיים או חסר: %s" % a.received)
            return 2
        print(json.dumps(time_anchors(dt.received_paragraphs(a.received)), ensure_ascii=False, indent=1))
        return 0
    need = (a.received,) if a.hidden_only else (a.work, a.received, a.decisions)
    for p in need:
        if not p or not os.path.exists(p):
            print("אינו קיים או חסר: %s" % p)
            return 2
    if a.hidden_only:
        print(json.dumps(hidden_scan(a.received), ensure_ascii=False, indent=1))
        return 0
    dec = load(a.decisions)
    res = run_checks(a.work, a.received, dec.get("decisions", []) if isinstance(dec, dict) else dec,
                     load(a.state), load(a.core), load(a.manifest))
    for f in res:
        print("%s [%s] %s%s" % ("חוסם" if f["blocking"] else "לבדיקה", f["code"], f["message"],
                                "  (%s)" % f["where"] if f["where"] else ""))
    blocking = [f for f in res if f["blocking"]]
    print("ממצאים: %d, חוסמים: %d" % (len(res), len(blocking)))
    return 3 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
