#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""כלי העסקה: השוואת מסמכי העסקה, הסכמים קיימים עם הצד שכנגד, צדדים בקורפוס, עובדות ומפת המונחים.

כולם קוראים קבצים במחשב של הלקוח בלבד, אינם כותבים לתיקיית הלקוח
(הפלט מודפס, או נכתב ב-`--out` לתיקייה זמנית), ואינם מכריעים: הם מחזירים
למודל את מה שצריך לקרוא ולהכריע בו.

* `compare-docs` (שינוי 23) - כמה מסמכים של אותה עסקה (מסמך ראשי
  ומסמכים נלווים שמפנים זה לזה): מונחים מוגדרים שמוגדרים אחרת, סעיפי עדיפות, תקרות,
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

    python "AREO_RT/skills/contract-negotiation-orchestrator/scripts/deal_tools.py" compare-docs <מסמך>.docx <מסמך>.docx
    python "AREO_RT/skills/contract-negotiation-orchestrator/scripts/deal_tools.py" existing --root <תיקיית ההסכמים> --counterparty "<שם>" [--related "<שם>"]
    python "AREO_RT/skills/contract-negotiation-orchestrator/scripts/deal_tools.py" parties --root <תיקיית ההסכמים> --out <זמני>/parties.json
    python "AREO_RT/skills/contract-negotiation-orchestrator/scripts/deal_tools.py" facts --data <Areo-נתונים> --transaction-id <id> --counterparty "<שם>"
    python "AREO_RT/skills/contract-negotiation-orchestrator/scripts/deal_tools.py" terms <הטיוטה>.docx

קוד יציאה: **0** תקין (גם כשנמצאו סתירות: הן תשובה), **2** קלט חסר, או Word פגום, DOC, מוצפן או Strict
(הודעה דו-לשונית; בסריקת תיקייה קובץ כזה מדולג), **1** `--out` שסורב.
"""
import argparse
import glob
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # גם ב-python -I, שאינו מוסיף את תיקיית הסקריפט
import areo_lib  # noqa: F401  מוסיף את areolegal/lib לנתיב הייבוא

import common.docx_tracked as dt  # noqa: E402
from common.cli import OutputRefused, guard_out, load_docx_or_explain  # noqa: E402
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
    "governing_law": r"הדין החל|הדין ה\S+ (?:יחול|חל)|יחול(?:ו)? (?:ה)?דין|יחולו (?:רק )?דיני|דיני מדינת|סמכות (?:ה)?שיפוט|governing law|"
                     r"governed by|construed in accordance with|jurisdiction|courts of",
}
# הדין והשיפוט כקוד אחיד (ISO 3166, ובמדינה עם כמה שיטות משפט קוד התחום: IL, GB-EAW, US-NY), אותם קודים כמו
# scope_summary.governing_laws בפלייבוק ו-meta.governing_law בטיוטה. הטבלה מקבילה לזו של המנסח (governing_law.py);
# אין דין ברירת מחדל, ומקום שלא זוהה מדווח "לא זוהה", ולא נבלע.
LAW_NAMES = {
    "IL": ("israel", "israeli", "state of israel", "ישראל", "מדינת ישראל", "ישראלי", "הישראלי", "ישראליים"),
    "GB-EAW": ("england", "england and wales", "english", "wales", "welsh", "אנגליה", "אנגליה ווילס",
               "אנגלי", "האנגלי", "ווילס"),
    "GB-SCT": ("scotland", "scottish", "scots", "סקוטלנד", "סקוטי", "הסקוטי"),
    "GB-NIR": ("northern ireland", "צפון אירלנד"),
    "GB": ("united kingdom", "UK", "U.K.", "british", "הממלכה המאוחדת", "בריטניה", "בריטי", "הבריטי"),
    "IE": ("ireland", "irish", "republic of ireland", "אירלנד", "אירי", "האירי"),
    "US": ("united states", "united states of america", "USA", "U.S.A.", "US", "U.S.", "federal law of the united states",
           "ארצות הברית", "ארה\"ב", "ארה״ב", "אמריקאי", "האמריקאי", "אמריקני", "האמריקני"),
    "US-NY": ("new york", "state of new york", "ניו יורק"),
    "US-DE": ("delaware", "state of delaware", "דלאוור", "דלאוואר"),
    "US-CA": ("california", "state of california", "קליפורניה"),
    "US-TX": ("texas", "state of texas", "טקסס"),
    "US-NJ": ("new jersey", "state of new jersey", "ניו ג'רזי", "ניו ג׳רזי"),
    "US-MA": ("massachusetts", "commonwealth of massachusetts", "מסצ'וסטס"),
    "US-FL": ("florida", "state of florida", "פלורידה"),
    "US-WA": ("state of washington", "וושינגטון"),
    "US-IL": ("illinois", "state of illinois", "אילינוי"),
    "CA": ("canada", "canadian", "קנדה", "קנדי", "הקנדי"),
    "CA-ON": ("ontario", "province of ontario", "אונטריו"),
    "DE": ("germany", "german", "federal republic of germany", "גרמניה", "גרמני", "הגרמני"),
    "FR": ("france", "french", "צרפת", "צרפתי", "הצרפתי"),
    "CH": ("switzerland", "swiss", "שווייץ", "שוויץ", "שווייצרי", "שוויצרי"),
    "NL": ("netherlands", "the netherlands", "dutch", "holland", "amsterdam", "הולנד", "הולנדי", "ההולנדי"),
    "BE": ("belgium", "belgian", "brussels", "בלגיה", "בלגי"),
    "LU": ("luxembourg", "לוקסמבורג"),
    "AT": ("austria", "austrian", "vienna", "אוסטריה", "אוסטרי"),
    "IT": ("italy", "italian", "milan", "rome", "איטליה", "איטלקי"),
    "ES": ("spain", "spanish", "madrid", "ספרד", "ספרדי"),
    "PT": ("portugal", "portuguese", "פורטוגל"),
    "SE": ("sweden", "swedish", "stockholm", "שוודיה", "שוודי"),
    "DK": ("denmark", "danish", "copenhagen", "דנמרק"),
    "NO": ("norway", "norwegian", "oslo", "נורווגיה"),
    "FI": ("finland", "finnish", "helsinki", "פינלנד"),
    "PL": ("poland", "polish", "warsaw", "פולין"),
    "CZ": ("czech republic", "czechia", "prague", "צ'כיה"),
    "GR": ("greece", "greek", "athens", "יוון"),
    "CY": ("cyprus", "cypriot", "nicosia", "קפריסין"),
    "MT": ("malta", "maltese", "מלטה"),
    "SG": ("singapore", "singaporean", "סינגפור", "סינגפורי"),
    "HK": ("hong kong", "הונג קונג"),
    "JP": ("japan", "japanese", "tokyo", "יפן"),
    "CN": ("china", "chinese", "people's republic of china", "PRC", "סין"),
    "IN": ("india", "indian", "הודו"),
    "AU": ("australia", "australian", "sydney", "אוסטרליה"),
    "NZ": ("new zealand", "ניו זילנד"),
    "AE": ("united arab emirates", "UAE", "dubai", "abu dhabi", "איחוד האמירויות", "דובאי"),
    "BR": ("brazil", "brazilian", "ברזיל"),
    "ZA": ("south africa", "south african", "דרום אפריקה"),
    "KR": ("south korea", "republic of korea", "דרום קוריאה"),
}
_LAW_RX = []
for _code, _names in LAW_NAMES.items():
    for _n in _names:
        if re.search(r"[א-ת]", _n):
            # בעברית: אותיות שימוש לפני המילה (ב, ל, מ, ה, ו, ש, כ), ולא אות עברית אחרי
            _rx = re.compile(r"(?<![א-ת])[ובלמהשכ]{0,2}" + re.escape(_n) + r"(?![א-ת])")
        elif len(_n.replace(".", "")) <= 3:
            _rx = re.compile(r"(?<![A-Za-z])" + re.escape(_n) + r"(?![A-Za-z])")   # US, UK, PRC: רק באותיות גדולות
        else:
            _rx = re.compile(r"(?<![A-Za-z])" + re.escape(_n) + r"(?![A-Za-z])", re.I)
        _LAW_RX.append((len(_n), _rx, _code))
_LAW_RX.sort(key=lambda x: -x[0])


def law_codes(text):
    """קודי הדין והשיפוט שבטקסט, מהשם הארוך לקצר (England and Wales לפני England). מדינה שיש לצדה תחום שלה
    (US ו-US-NY, GB ו-GB-EAW) נספרת כתחום בלבד."""
    t = text or ""
    found = set()
    for _, rx, c in _LAW_RX:
        def _take(m, c=c):
            found.add(c)
            return " " * len(m.group(0))
        t = rx.sub(_take, t)
    for c in list(found):
        if "-" in c and c.split("-")[0] in found:
            found.discard(c.split("-")[0])
    return found
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
        ok, msg, code = load_docx_or_explain(p, loader=False)
        if ok is None:
            print(msg)
            return code
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
                    cx = law_codes("\n".join(t for _, t in px))
                    cy = law_codes("\n".join(t for _, t in py))
                    if cx and cy and cx != cy:
                        conflicts.append({"topic": topic, "documents": [x, y], "codes": [sorted(cx), sorted(cy)],
                                          "conflict": "דין או שיפוט שונים (%s מול %s) / Different governing law or "
                                                      "forum (%s vs %s)" % (", ".join(sorted(cx)), ", ".join(sorted(cy)),
                                                                           ", ".join(sorted(cx)), ", ".join(sorted(cy)))})
                    elif not cx or not cy:
                        miss = [n for n, c in ((x, cx), (y, cy)) if not c]
                        conflicts.append({"topic": topic, "documents": [x, y], "status": "unrecognised",
                                          "conflict": "הדין או השיפוט לא זוהה ב-%s: לקרוא ולהשוות ביד / Governing "
                                                      "law or forum not recognised in %s: read and compare manually"
                                                      % (", ".join(miss), ", ".join(miss))})
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
    if a.out:
        try:   # לפני הסריקה: לא על מסמך קיים ולא בתיקיית מקור של הלקוח
            guard_out(a.out)
        except OutputRefused as exc:
            print("סירוב: %s" % exc)
            return 1
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


def _fact(x, source, text_keys=("text", "assumption", "fact", "question"), value_keys=("status", "value", "answer")):
    """עובדה אחת, כשהרשומה היא אובייקט או מחרוזת (S1d, 28.10.2026: assumptions במרשם הסיכונים היו מחרוזות,
    ו-facts קרס ב-AttributeError)."""
    if isinstance(x, dict):
        return {"fact": next((x[k] for k in text_keys if x.get(k)), json.dumps(x, ensure_ascii=False)),
                "value": next((x[k] for k in value_keys if x.get(k) is not None), None), "source": source}
    return {"fact": str(x), "value": None, "source": source}


def cmd_facts(a):
    facts = []
    for mp in glob.glob(os.path.join(a.data, "playbooks", "*", "playbook-model.json")) + \
            glob.glob(os.path.join(a.data, "playbook-model.json")):
        m = _load(mp) or {}
        src = "תשובות הקליטה של הפלייבוק (%s)" % os.path.relpath(mp, a.data)
        intake = (m.get("meta") or {}).get("intake_answers") or m.get("intake_answers") or {}
        for k, v in (intake.items() if isinstance(intake, dict) else enumerate(intake)):
            facts.append({"fact": k, "value": v, "source": src})
        # מה שהבונה רושם בפועל: scope_summary.client_facts[] ({fact, answer_verbatim, asked_at}) ו-client_facts[]
        # של meta.build_request (ps1-playbook-identity-scope.md)
        for x in list((m.get("scope_summary") or {}).get("client_facts") or []) + \
                list(((m.get("meta") or {}).get("build_request") or {}).get("client_facts") or []):
            facts.append(_fact(x, src, ("fact", "text", "question"), ("answer_verbatim", "answer", "value")))
    if a.transaction_id:
        rp = os.path.join(a.data, "transactions", a.transaction_id, "risk-register.json")
        reg = _load(rp) or {}
        for x in (reg.get("summary") or {}).get("assumptions") or []:
            facts.append(_fact(x, "מרשם הסיכונים של העסקה"))
    for sp in glob.glob(os.path.join(a.data, "transactions", "*", "negotiation_state.json")):
        st = _load(sp) or {}
        meta = st.get("meta") or {}
        if a.counterparty and a.counterparty not in str(meta.get("counterparty_name") or ""):
            continue
        for x in st.get("client_answers") or []:
            facts.append(_fact(x, "קובץ המצב, %s" % meta.get("transaction_id", os.path.basename(os.path.dirname(sp))),
                               ("question", "fact", "text"), ("answer", "value")))
        # deal_context.facts: רשימה של {fact, source, ...} (state_builder.skeleton), או מילון ישן {עובדה: ערך}
        dc_facts = (meta.get("deal_context") or {}).get("facts") or []
        for k, v in (dc_facts.items() if isinstance(dc_facts, dict) else ((x, None) for x in dc_facts)):
            if v is None:
                f = _fact(k, "deal_context, %s" % meta.get("transaction_id", ""))
                if isinstance(k, dict) and k.get("source"):
                    f["origin"] = k["source"]
                facts.append(f)
            else:
                facts.append({"fact": k, "value": v, "source": "deal_context, %s" % meta.get("transaction_id", "")})
    print(json.dumps({"facts": facts}, ensure_ascii=False, indent=1))
    return 0


def cmd_terms(a):
    if not os.path.exists(a.draft):
        print("אינו קיים: %s" % a.draft)
        return 2
    ok, msg, code = load_docx_or_explain(a.draft, loader=False)
    if ok is None:
        print(msg)
        return code
    paras = text_of(a.draft)
    whole = "\n".join(paras)
    # כינויי הצדדים (n1-intake.md, "מפת המונחים"): אין רשימה בקוד (content_checks.PARTY_LABELS ריק), ולכן הם נקראים
    # מההסכם עצמו: מונח מוגדר בסוגריים בפסקת הצדדים ("בין X ("הספק") לבין Y ("הלקוח")", "between X ("Supplier")")
    defs = definitions(paras)
    parties_rx = r"(?<![\w֐-׿])(?:ל?בין)(?![\w֐-׿])|\bbetween\b"
    found = list(CC.PARTY_LABELS) + [t for t, src in defs.items() if re.search(parties_rx, src, re.I)]
    labels = {lab: whole.count(lab) for lab in dict.fromkeys(found) if re.search(
        r"(?<![\w֐-׿])" + re.escape(lab) + r"(?![\w֐-׿])", whole)}
    print(json.dumps({"defined_terms": definitions(paras), "party_labels": labels}, ensure_ascii=False, indent=1))
    return 0


def main(argv=None):
    sys.dont_write_bytecode = True
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
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
