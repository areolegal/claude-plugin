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
    for d in decisions:
        if d.get("op") in ("replace", "replace_span", "insert_paragraph") and not (d.get("plain_effect")
                                                                                  and d.get("position_effect")):
            finding(out, "EFFECT_FIELDS", "הכרעה שמכניסה נוסח בלי plain_effect ו-position_effect", d.get("id"))
    return out


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
    a = ap.parse_args(argv)
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
