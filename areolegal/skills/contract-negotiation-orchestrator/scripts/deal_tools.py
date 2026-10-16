#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""כלי העסקה: השוואת מסמכי העסקה, הסכמים קיימים עם הצד שכנגד, צדדים בקורפוס, עובדות ומפת המונחים.

הכלים האלה ביקשה ענבל בהערות הנושא ונותן 4.0 עד 4.7, ואין להם מימוש בקוד
הייחוס. כולם קוראים קבצים במחשב של הלקוח בלבד, אינם כותבים לתיקיית הלקוח
(הפלט מודפס, או נכתב ב-`--out` לתיקייה זמנית), ואינם מכריעים: הם מחזירים
למודל את מה שצריך לקרוא ולהכריע בו.

* `compare-docs` (שינוי 23) - כמה מסמכים של אותה עסקה (הסכם מסגרת, הזמנה, הסכם
  עיבוד מידע, מכתב צד): מונחים מוגדרים שמוגדרים אחרת, סעיפי עדיפות, תקרות,
  תקופות ומועדי סיום, ודין ושיפוט. כל סתירה נרשמת ב-`meta.deal_documents.conflicts`
  עם הכרעה, ושער האיכות נכשל על סתירה בלי הכרעה.
* `existing` (שינוי 27) - הסכמים חתומים בקורפוס, לפי שם הצד שכנגד והישויות
  הקשורות אליו, ולפי משפחת ההסכם: לכל אחד, הסעיפים לקריאה (בלעדיות, תקופה
  וחידוש, הודעות ומועדים, סיום, סודיות). נכנס ל-`existing_agreements_with_counterparty`.
* `parties` (שינוי 28) - שמות הצדדים בפתיח של כל הסכם חתום בקורפוס. שער האיכות
  בודק מולם שאין בבועה החיצונית שם של צד מהסכם אחר (`qa_gate.py --manifest`).
* `facts` (שינוי 54) - עובדות שכבר נמסרו: תשובות הקליטה בפלייבוקים, המרשם של
  אותה עסקה, וקובצי מצב של עסקאות עם אותו צד שכנגד. לכל עובדה המקור שלה.
* `terms` (שינוי 1) - מפת המונחים של ההסכם: המונחים המוגדרים, וכינויי הצדדים
  שבו. נוסח מהפלייבוק נכתב דרכה לפני שהוא נכנס לגוף.

    python3 scripts/deal_tools.py compare-docs <מסמך>.docx <מסמך>.docx
    python3 scripts/deal_tools.py existing --root <תיקיית ההסכמים> --counterparty "<שם>" [--related "<שם>"]
    python3 scripts/deal_tools.py parties --root <תיקיית ההסכמים> --out <זמני>/parties.json
    python3 scripts/deal_tools.py facts --data <Areo-נתונים> --transaction-id <id> --counterparty "<שם>"
    python3 scripts/deal_tools.py terms <הטיוטה>.docx

קוד יציאה: **0** תקין (גם כשנמצאו סתירות: הן תשובה), **2** קלט חסר.
"""
import argparse
import glob
import io
import json
import os
import re
import sys

import areo_lib  # noqa: F401  מוסיף את areolegal/lib לנתיב הייבוא

import common.docx_tracked as dt  # noqa: E402
import content_checks as CC  # noqa: E402

SIGNED = re.compile(r"ולראיה באו הצדדים על החתום|חתימת הצדדים|/s/|signature of the parties|IN WITNESS WHEREOF", re.I)
KEY_CLAUSES = {
    "exclusivity": r"בלעדי|בלעדיות|exclusiv",
    "term_renewal": r"תקופת ההסכם|יתחדש|חידוש|הארכה|term of this agreement|renew",
    "notice_deadlines": r"הודעה מוקדמת|ימים מראש|לא יאוחר מ|prior written notice|days.? notice|no later than",
    "termination": r"סיום|לסיים|ביטול|terminat",
    "confidentiality": r"סודיות|מידע סודי|confidential",
    "minimum": r"מינימום|כמות מזערית|minimum",
}
TOPICS = {
    "precedence": r"יגבר|יגברו|עדיפות|prevail|precedence|order of priority",
    "liability_cap": r"תקרת|הגבלת אחריות|limitation of liability|aggregate liability|liability cap",
    "term_termination": r"תקופת ההסכם|סיום|termination|term of",
    "governing_law": r"הדין החל|דיני מדינת|סמכות השיפוט|governing law|jurisdiction|courts of",
}
PARTY_RX = [re.compile(r"(?:^|\n)\s*(?:בין|ל?בין)\s*:?\s*([^\n,;]{3,80}?)(?:\s*,|\s*\(|\s*ח\.?פ|\s*מספר|\n)"),
            re.compile(r"\bbetween\s+([A-Z][^,\n(]{2,80}?)\s*(?:,|\(|a company|incorporated)", re.I),
            re.compile(r"\band\s+([A-Z][^,\n(]{2,80}?)\s*(?:,|\(|a company|incorporated)")]
NUM = re.compile(r"\d[\d,.]*")


def text_of(path):
    try:
        return dt.accept_all(path)
    except Exception:  # noqa: BLE001  קובץ שאינו docx: אין טקסט
        return []


def paras_matching(paras, rx):
    return [(i, t) for i, t in enumerate(paras) if re.search(rx, t, re.I)]


def definitions(paras):
    out = {}
    for i, t in enumerate(paras):
        for rx in CC.DEF_PATTERNS:
            for m in rx.finditer(t):
                for g in m.groups():
                    if g:
                        out.setdefault(g.strip(), t.strip()[:300])
    return out


def cmd_compare(a):
    docs = {}
    for p in a.docs:
        if not os.path.exists(p):
            print("אינו קיים: %s" % p)
            return 2
        docs[os.path.basename(p)] = text_of(p)
    conflicts = []
    defs = {n: definitions(ps) for n, ps in docs.items()}
    names = list(docs)
    for i, x in enumerate(names):
        for y in names[i + 1:]:
            for term in set(defs[x]) & set(defs[y]):
                if re.sub(r"\W+", "", defs[x][term]) != re.sub(r"\W+", "", defs[y][term]):
                    conflicts.append({"topic": "definitions", "documents": [x, y],
                                      "conflict": "המונח \"%s\" מוגדר אחרת בשני המסמכים" % term})
            for topic, rx in TOPICS.items():
                px, py = paras_matching(docs[x], rx), paras_matching(docs[y], rx)
                if not px or not py:
                    continue
                if topic in ("liability_cap", "term_termination"):
                    nx = {n for _, t in px for n in NUM.findall(t)}
                    ny = {n for _, t in py for n in NUM.findall(t)}
                    if nx and ny and not (nx & ny):
                        conflicts.append({"topic": topic, "documents": [x, y],
                                          "conflict": "מספרים שונים (%s מול %s)" % (", ".join(sorted(nx)[:4]),
                                                                                     ", ".join(sorted(ny)[:4]))})
                elif topic == "governing_law":
                    wx = {w for _, t in px for w in re.findall(r"[A-Z][a-z]{3,}|[א-ת]{4,}", t)}
                    wy = {w for _, t in py for w in re.findall(r"[A-Z][a-z]{3,}|[א-ת]{4,}", t)}
                    places = {"ישראל", "אביב", "ירושלים", "חיפה", "England", "Delaware", "York", "California",
                              "Israel", "Wales", "Ireland", "Germany"}
                    if (wx & places) and (wy & places) and (wx & places) != (wy & places):
                        conflicts.append({"topic": topic, "documents": [x, y],
                                          "conflict": "דין או שיפוט שונים (%s מול %s)" % (
                                              ", ".join(sorted(wx & places)), ", ".join(sorted(wy & places)))})
                else:
                    conflicts.append({"topic": topic, "documents": [x, y],
                                      "conflict": "בשני המסמכים סעיף עדיפות: לבדוק שאינם סותרים"})
    out = {"documents": names, "conflicts": conflicts}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


def corpus_files(root):
    return [p for p in sorted(glob.glob(os.path.join(root, "**", "*.docx"), recursive=True))
            if not os.path.basename(p).startswith("~$") and "Areo-נתונים" not in p]


def party_names(paras):
    head = "\n".join(paras[:12])
    names = []
    for rx in PARTY_RX:
        for m in rx.finditer(head):
            n = re.sub(r"\s+", " ", m.group(1)).strip(" :")
            if 3 <= len(n) <= 80 and n not in names:
                names.append(n)
    return names


def cmd_existing(a):
    wanted = [x for x in [a.counterparty] + list(a.related or []) if x]
    out = []
    for p in corpus_files(a.root):
        paras = text_of(p)
        whole = "\n".join(paras)
        if not SIGNED.search(whole):
            continue
        hit_party = [w for w in wanted if w and w in whole]
        hit_family = a.family and re.search(a.family, whole[:2000], re.I)
        if not hit_party and not hit_family:
            continue
        clauses = {k: [t[:400] for _, t in paras_matching(paras, rx)][:4] for k, rx in KEY_CLAUSES.items()}
        out.append({"file": os.path.relpath(p, a.root), "matched_by": "counterparty" if hit_party else "family",
                    "parties": party_names(paras), "clauses": clauses})
    res = {"counterparty": a.counterparty, "found": out}
    if not out:
        res["line"] = "לא נמצאו בתיקייה המחוברת הסכמים קודמים עם %s." % (a.counterparty or "הצד שכנגד")
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


def cmd_parties(a):
    names = []
    for p in corpus_files(a.root):
        paras = text_of(p)
        if SIGNED.search("\n".join(paras)):
            for n in party_names(paras):
                if n not in names:
                    names.append(n)
    if a.out:
        with io.open(a.out, "w", encoding="utf-8") as fh:
            json.dump({"documents": [{"counterparty": n} for n in names]}, fh, ensure_ascii=False, indent=1)
    print(json.dumps(names, ensure_ascii=False, indent=1))
    return 0


def _load(p):
    try:
        with io.open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def cmd_facts(a):
    facts = []
    for mp in glob.glob(os.path.join(a.data, "playbooks", "*", "playbook-model.json")) + \
            glob.glob(os.path.join(a.data, "playbook-model.json")):
        m = _load(mp) or {}
        intake = (m.get("meta") or {}).get("intake_answers") or m.get("intake_answers") or {}
        for k, v in (intake.items() if isinstance(intake, dict) else enumerate(intake)):
            facts.append({"fact": k, "value": v, "source": "תשובות הקליטה של הפלייבוק (%s)" % os.path.relpath(mp, a.data)})
    if a.transaction_id:
        rp = os.path.join(a.data, "transactions", a.transaction_id, "risk-register.json")
        reg = _load(rp) or {}
        for x in (reg.get("summary") or {}).get("assumptions") or []:
            facts.append({"fact": x.get("text") or x.get("assumption") or str(x), "value": x.get("status"),
                          "source": "מרשם הסיכונים של העסקה"})
    for sp in glob.glob(os.path.join(a.data, "transactions", "*", "negotiation_state.json")):
        st = _load(sp) or {}
        meta = st.get("meta") or {}
        if a.counterparty and a.counterparty not in str(meta.get("counterparty_name") or ""):
            continue
        for x in st.get("client_answers") or []:
            facts.append({"fact": x.get("question"), "value": x.get("answer"),
                          "source": "קובץ המצב, %s" % meta.get("transaction_id", os.path.basename(os.path.dirname(sp)))})
        for k, v in ((meta.get("deal_context") or {}).get("facts") or {}).items():
            facts.append({"fact": k, "value": v, "source": "deal_context, %s" % meta.get("transaction_id", "")})
    print(json.dumps({"facts": facts}, ensure_ascii=False, indent=1))
    return 0


def cmd_terms(a):
    paras = text_of(a.draft)
    whole = "\n".join(paras)
    labels = {lab: whole.count(lab) for lab in CC.PARTY_LABELS if re.search(
        r"(?<![\w֐-׿])" + re.escape(lab) + r"(?![\w֐-׿])", whole)}
    print(json.dumps({"defined_terms": definitions(paras), "party_labels": labels}, ensure_ascii=False, indent=1))
    return 0


def main(argv=None):
    sys.dont_write_bytecode = True
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("compare-docs")
    c.add_argument("docs", nargs="+")
    e = sub.add_parser("existing")
    e.add_argument("--root", required=True)
    e.add_argument("--counterparty")
    e.add_argument("--related", action="append")
    e.add_argument("--family", help="ביטוי לזיהוי משפחת ההסכם בכותרת ובפתיח")
    p = sub.add_parser("parties")
    p.add_argument("--root", required=True)
    p.add_argument("--out", help="קובץ לשער האיכות (qa_gate.py --manifest), בתיקייה זמנית")
    f = sub.add_parser("facts")
    f.add_argument("--data", required=True)
    f.add_argument("--transaction-id")
    f.add_argument("--counterparty")
    t = sub.add_parser("terms")
    t.add_argument("draft")
    a = ap.parse_args(argv)
    return {"compare-docs": cmd_compare, "existing": cmd_existing, "parties": cmd_parties, "facts": cmd_facts,
            "terms": cmd_terms}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
