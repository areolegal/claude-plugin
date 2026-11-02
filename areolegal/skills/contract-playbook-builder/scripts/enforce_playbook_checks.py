#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""שכבת האכיפה של בונה הפלייבוק: שש בדיקות אוטומטיות על playbook-model.json, לפני בניית סביבת העבודה.

כלל שאין לו בדיקה הוא בפועל המלצה. הבדיקות כאן אוכפות כללים שכבר כתובים ב-b3-derivation וב-playbook-qa,
ושלושה כללים שנוספו (שתיקה אינה ראיה, ייחוס ברמת המשפט, אין קביעות דין בלי מחקר).

    python3 enforce_playbook_checks.py <playbook-model.json> [--extract <corpus-extract.json>] [--json <out.json>]

קוד יציאה 0: אין כשלים. 3: יש כשל אחד או יותר (הבנייה נעצרת עד לתיקון). אזהרות אינן עוצרות.
הבדיקות:
  1 quote      כל ציטוט נמצא מילה במילה במסמך המקור (קטעי [...] נבדקים בנפרד); ציטוט שנחתך בלי סימון נכשל
  2 evidence   עמדה שאינה הצעת Areo נשענת על ציטוט, והצעת Areo אינה נושאת ציטוטים
  3 silence    עמדה שנגזרה מהיעדר הוראה, כשמסמך אחר בנושא מסדיר אותו במפורש
  4 law        שם חוק, תקנה או רשות בנוסח בלי מחקר רגולטורי ובלי ציטוט שמכיל אותו
  5 duplicates אותו מסמך ואותו סעיף יותר מפעם אחת בתוך נושא
  6 fields     תנאי התאמה זהה לכותרת העמדה, או נוסח חלופי שהוא הפניה ("נוסח הירוק שלמעלה")
בדיקות שנוספו לפי הביקורת (31.10), ממומשות ב-evidence_kind.py ונקראות גם מ-validate_playbook_model.py:
  7 kind       ירוק שכל ציטוטיו הם נוסח של הצד שכנגד שלא שונה (ev_kind: counterparty_unchanged): שתיקה אינה עמדה.
               יהפוך לצהוב או לשאלה פתוחה (כלל 2)
  8 red        עמדה אדומה בלי נוסח תגובה ובלי fallback_pointer לנוסח החלופי היא פער, לא עמדה (כלל 5)
  9 rationale  נימוק ליבה ריק או חוזר על נוסח העמדה: כשל כש-rationale_status הוא Confirmed, אזהרה ב-Draft (כלל 4)
 10 names      שם צד קונקרטי בנוסח מדיניות, או source_language שאינו שפת הטקסט בפועל (כלל 7)
 11 legal      שובר עסקה שנימוקו טענת דין, בלי מקור רגולטורי: אינו מאושר בלי עיגון (כלל 8)
 12 integrity  נוסח מוצע עם מילים דבוקות, ביטוי כפול או משפט שנפתח באמצע: אזהרה לבדיקה אנושית (כלל 21)
 13 sources    מסמך שאינו הסכם (guidance/policy/table/template) שנספר ב-counted_agreements; תווית "נוסח שאתם
               מציגים" על מסמך שאינו נייר החברה; מאגר מתחת לסף המספיקות בלי שהמגבלה נרשמה
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # גם ב-python -I
import areo_lib  # noqa: F401,E402  מוסיף את areolegal/lib לנתיב: בלעדיו בדיקת המספיקות (playbook.sufficiency) לא רצה
import evidence_kind as E  # noqa: E402

if __name__ == "__main__":
    sys.dont_write_bytecode = True

LAW_RX = re.compile(r"(חוק\s+[֐-׿\"'״׳]|תקנות\s+[֐-׿]|תקנה\s+\d+|הרשות\s+ל|רשות\s+(?:ה|ל)[֐-׿]+|"
                    r"\bGDPR\b|\bDirective\b|\bRegulation\b|\bPrivacy\s+Protection\s+(?:Law|Act)\b|\bAct\s+\d{4})", re.I)
SILENCE_RX = re.compile(r"(אינו מזכיר|אינם מזכירים|לא מוזכר|שותק|שתיקה|מסמך אחד בלבד אינו|does not mention|silent)", re.I)
REFERRAL_RX = re.compile(r"(נוסח הירוק|כמו בירוק|חזרה לנוסח|כנוסח הירוק|same as green|see green|as in green)", re.I)
AREO_RX = re.compile(r"(הצעת\s+Areo|Areo proposal|areo_proposal|הצעת מערכת|ניסוח של המערכת)", re.I)
ELLIPSIS_RX = re.compile(r"\s*(?:\[\s*\.{3}\s*\]|\[…\]|…|\.{3})\s*")
DONE = {"Performed", "Completed", "Partial", "ApplicableSourcesFound", "NoSpecificSourceIdentified"}


def norm(s):
    s = str(s or "")
    s = s.replace("‎", "").replace("‏", "").replace(" ", " ")
    s = re.sub(r"[‘’‚‛׳']", "'", s)
    s = re.sub(r"[“”„״\"]", '"', s)
    s = re.sub(r"[‐-―]", "-", s)
    return re.sub(r"\s+", " ", s).strip().lower()


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def doc_texts(extract):
    out = {}
    if not extract:
        return out
    for d in extract.get("documents", []):
        paras = [norm(p.get("text", "")) for p in d.get("paragraphs", []) if isinstance(p, dict)]
        out[d.get("doc_id") or d.get("path")] = {"path": d.get("path", ""), "paras": paras, "all": " ".join(paras)}
    return out


def find_doc(texts, source_log, source_id):
    """מסמך המקור של ציטוט, לפי שם הקובץ ב-source_log; כשאין התאמה, None (ייבדק מול כל המסמכים)."""
    name = ""
    for s in source_log or []:
        if s.get("source_id") == source_id:
            name = norm(s.get("agreement_name", ""))
    if not name:
        return None
    base = name.rsplit("\\", 1)[-1].rsplit("/", 1)[-1]
    for k, v in texts.items():
        p = norm(v["path"]).rsplit("\\", 1)[-1].rsplit("/", 1)[-1]
        if p == base or base in p or p in base:
            return k
    return None


def quote_findings(rule, model, texts, errors, warnings):
    rid = rule.get("rule_id")
    for ev in rule.get("evidence") or []:
        q = ev.get("quote") or ""
        if not q.strip():
            continue
        key = find_doc(texts, model.get("source_log"), ev.get("source_id"))
        segs = [norm(x) for x in ELLIPSIS_RX.split(q) if norm(x)]
        pool = [texts[key]] if key else list(texts.values())
        for seg in segs:
            hit = None
            for d in pool:
                for para in d["paras"]:
                    if seg in para:
                        hit = para
                        break
                if hit or seg in d["all"]:
                    hit = hit or d["all"]
                    break
            if hit is None:
                where = "במסמך המקור" if key else "באף מסמך בקורפוס"
                errors.append("%s %s: הציטוט אינו נמצא מילה במילה %s: «%s»" % (rid, ev.get("cite_id"), where, seg[:70]))
            elif not ELLIPSIS_RX.search(q) and hit.endswith(seg) is False and not re.search(r"[.;:!?)\"']\s*$", seg) \
                    and len(hit) > len(seg) + 25:
                errors.append("%s %s: הציטוט נחתך באמצע משפט בלי סימון [...]: «%s…»" % (rid, ev.get("cite_id"), seg[:50]))


def evidence_findings(rule, errors, warnings):
    rid = rule.get("rule_id")
    for color in ("green", "yellow", "red"):
        c = (rule.get("traffic_light") or {}).get(color) or {}
        ev = c.get("evidence") or []
        blob = " ".join(str(c.get(k, "")) for k in ("notes", "comments", "position"))
        is_areo = bool(AREO_RX.search(blob))
        if is_areo and ev:
            errors.append("%s %s: הצעת Areo נושאת ציטוטים מהקורפוס. הצעת מערכת אינה נשענת על ראיה" % (rid, color))
        if not is_areo and not ev and (c.get("position") or "").strip():
            errors.append("%s %s: עמדה בלי ציטוט שאינה מסומנת כהצעת Areo" % (rid, color))


def silence_findings(rule, errors, warnings):
    rid = rule.get("rule_id")
    quotes = [e for e in rule.get("evidence") or [] if (e.get("quote") or "").strip()]
    sources = {e.get("source_id") for e in quotes}
    for color in ("green", "yellow", "red"):
        c = (rule.get("traffic_light") or {}).get(color) or {}
        blob = " ".join(str(c.get(k, "")) for k in ("notes", "comments", "position"))
        if SILENCE_RX.search(blob) and len(sources) >= 1 and color == "green":
            for e in quotes:
                if e.get("track") in ("green", "context") and SILENCE_RX.search(blob):
                    errors.append("%s %s: העמדה נשענת על שתיקה של מסמך, אך מסמך אחר (%s) מסדיר את הנושא. השתיקה אינה ראיה" %
                                  (rid, color, e.get("source_id")))
                    break


def law_findings(rule, model, errors, warnings):
    rid = rule.get("rule_id")
    status = (model.get("regulatory_research") or {}).get("status") or rule.get("regulatory_status") or "NotResearched"
    if status in DONE and rule.get("regulatory_status") in DONE:
        return
    quotes = " ".join(norm(e.get("quote", "")) for e in rule.get("evidence") or [])
    for color in ("green", "yellow", "red"):
        c = (rule.get("traffic_light") or {}).get(color) or {}
        for key in ("position", "proposed_clause", "notes", "comments"):
            for m in LAW_RX.finditer(str(c.get(key, ""))):
                tok = norm(m.group(0))
                if tok and tok not in quotes:
                    errors.append("%s %s.%s: קביעת דין («%s») בלי מחקר רגולטורי ובלי ציטוט מקביל" % (rid, color, key, m.group(0)[:30]))
                    break


def duplicate_findings(rule, errors, warnings):
    rid = rule.get("rule_id")
    seen = {}
    for e in rule.get("evidence") or []:
        k = (e.get("source_id"), norm(e.get("clause_ref", "")))
        seen.setdefault(k, []).append(e.get("cite_id"))
    for k, ids in seen.items():
        if len(ids) > 1 and k[1]:
            errors.append("%s: ציטוט כפול (מסמך %s, %s): %s. כל מניין מחושב על ייחודיים בלבד" % (rid, k[0], k[1], ", ".join(map(str, ids))))


def field_findings(rule, errors, warnings):
    rid = rule.get("rule_id")
    for color in ("green", "yellow", "red"):
        c = (rule.get("traffic_light") or {}).get(color) or {}
        pos = norm(c.get("position", ""))
        for mc in c.get("match_criteria") or []:
            if pos and norm(mc) == pos:
                errors.append("%s %s: תנאי ההתאמה זהה לכותרת העמדה. צריך מבחן שאפשר להחיל על טיוטה" % (rid, color))
                break
        if color != "green" and REFERRAL_RX.search(str(c.get("proposed_clause", "")) + " " + str(c.get("fallback_wording", ""))):
            errors.append("%s %s: הנוסח החלופי הוא הפניה למסלול אחר ולא נוסח" % (rid, color))
        for k in ("fallback_wording",):
            if isinstance(c.get(k), dict) and REFERRAL_RX.search(str(c[k].get("text", ""))):
                errors.append("%s %s: fallback_wording הוא הפניה למסלול אחר" % (rid, color))
    imp = str(rule.get("importance") or rule.get("priority") or "").lower()
    if imp in ("critical", "high") and not ((rule.get("traffic_light") or {}).get("yellow") or {}).get("fallback_2"):
        # שתי מדרגות נסיגה: רק כשהמודל מחזיק מדרגה שנייה במפורש, אחרת אזהרה
        warnings.append("%s: נושא %s בלי מדרגת נסיגה שנייה" % (rid, imp))


GREEN_OWN_BASES = ("template", "own_paper_repeated", "documents_majority", "client_answer", "company_request",
                   "areo_proposal", "market_standard")
OWN_LABEL_RX = re.compile(r"(נוסח(?:ים)? שאתם מציגים|הנוסח שלכם|התבנית שלכם|your (?:form|template|wording)|form you present)", re.I)


def kind_findings(rule, model, ex_idx, src_rows, errors, warnings):
    """כלל 2: ירוק שנשען רק על נוסח של הצד שכנגד שלא שונה אינו ירוק. הסיווג מקובץ החילוץ או מרשומת הראיה;
    כשאין לא זה ולא זה, הבדיקה אינה מכריעה ואומרת זאת."""
    rid = rule.get("rule_id")
    green = (rule.get("traffic_light") or {}).get("green") or {}
    if not (green.get("position") or "").strip() or green.get("basis") in ("areo_proposal", "market_standard"):
        return
    kinds = []
    for ev in rule.get("evidence") or []:
        if ev.get("track") != "green":
            continue
        sid = str(ev.get("source_ref") or ev.get("source_id") or "").split("#")[0]
        row = src_rows.get(sid) or {}
        kinds.append(E.ev_kind(ev, row, E.doc_for_source(row, ex_idx)))
    if not kinds:
        return
    known = [k for k in kinds if k != "unknown"]
    if known and all(k == "counterparty_unchanged" for k in known):
        errors.append("%s green: כל הציטוטים התומכים הם נוסח של הצד שכנגד שלא שונה. אי-מחיקה אינה עמדה של החברה: "
                      "העמדה תירשם כצהוב או כשאלה פתוחה, עם הסבר שהחברה לא הביעה עמדה" % rid)
    elif not known and not ex_idx:
        warnings.append("%s green: סיווג הראיה (ev_kind) לא ידוע בלי קובץ חילוץ, ולכן כלל 2 לא נבדק" % rid)


def red_findings(rule, errors, warnings):
    """כלל 5: אדום בלי נוסח תגובה ובלי הפניה מפורשת לנוסח החלופי הוא פער."""
    rid = rule.get("rule_id")
    red = (rule.get("traffic_light") or {}).get("red") or {}
    if not (red.get("position") or "").strip():
        return
    kind, _ = E.red_response(red)
    if kind is None:
        errors.append("%s red: אין נוסח תגובה (proposed_clause / response_wording) ואין fallback_pointer: yellow. "
                      "עמדה בלי נוסח היא פער, לא עמדה" % rid)


def rationale_findings(rule, errors, warnings):
    """כלל 4: נימוק שחוזר על נוסח העמדה הוא נימוק ריק."""
    rid = rule.get("rule_id")
    rat = rule.get("policy_rationale") or {}
    if not rat:
        return
    ok, why = E.rationale_complete(rule)
    if ok:
        return
    rep = [w.split(":", 1)[1] for w in why if w.startswith("repeats_position:")]
    msg = "%s: שכבת הנימוקים אינה שלמה (%s)" % (rid, ", ".join(why)[:160])
    if rep:
        msg += ". נימוק שחוזר על נוסח העמדה אינו נימוק"
    if rat.get("rationale_status") == "Confirmed" and (rep or any(w.startswith("empty:") for w in why)):
        errors.append(msg + ". rationale_status: Confirmed אינו אפשרי")
    else:
        warnings.append(msg + ". השכבה מוסתרת בתוצרים עד שתושלם")


def name_findings(rule, names, company, errors, warnings):
    """כלל 7: שמות צדדים קונקרטיים בנוסח מדיניות; שפת הנוסח נגזרת מהטקסט."""
    rid = rule.get("rule_id")
    for color in ("green", "yellow", "red"):
        c = (rule.get("traffic_light") or {}).get(color) or {}
        pc = c.get("proposed_clause")
        texts = {"position": c.get("position") or ""}
        if isinstance(pc, dict):
            for g in ("he", "en"):
                if pc.get(g):
                    texts["proposed_clause." + g] = pc[g]
                    real = E.detect_lang(pc[g])
                    if real and real != g:
                        errors.append("%s %s: proposed_clause.%s כתוב בשפה אחרת (%s) מהמפתח" % (rid, color, g, real))
            if pc.get("source_language") and not any(str(pc.get(g) or "").strip() for g in ("he", "en")):
                errors.append("%s %s: source_language נכתב בלי נוסח. שפה נגזרת מהטקסט, לא מברירת מחדל" % (rid, color))
        elif isinstance(pc, str) and pc:
            texts["proposed_clause"] = pc
        for key, t in texts.items():
            hits = E.name_hits(t, names, company)
            if hits:
                errors.append("%s %s.%s: שם צד קונקרטי בנוסח מדיניות (%s). יוחלף בתווית גנרית (%s)" %
                              (rid, color, key, ", ".join(h["name"] for h in hits[:3]), ", ".join(sorted({h["generic"] for h in hits}))))


def legal_findings(rule, model, errors, warnings):
    """כלל 8: שובר עסקה מטעם משפטי אינו מאושר בלי עיגון; טענת דין אחרת מסומנת טעונה אימות (אזהרה)."""
    rid = rule.get("rule_id")
    red = (rule.get("traffic_light") or {}).get("red") or {}
    blob = " ".join(str(red.get(k) or "") for k in ("position", "red_why", "notes", "meaning"))
    rat = rule.get("policy_rationale") or {}
    blob += " " + str(rat.get("legal_risk_and_legal_framework") or "")
    if not E.legal_claim(blob):
        return
    grounded = bool(rule.get("regulatory_sources")) and rule.get("regulatory_status") in DONE
    if rule.get("walk_away") is True and not grounded:
        errors.append("%s: שובר עסקה שנימוקו טענת דין, בלי מקור רגולטורי (regulatory_sources). אינו מאושר בלי עיגון" % rid)
    elif not grounded:
        warnings.append("%s: טענת דין במדיניות בלי מקור. תסומן \"טעונה אימות\" ותופנה למקור" % rid)


def integrity_findings(rule, errors, warnings):
    """כלל 21: תקינות הנוסח לפני שהוא נוסח מוצע."""
    rid = rule.get("rule_id")
    for color in ("green", "yellow", "red"):
        c = (rule.get("traffic_light") or {}).get(color) or {}
        pc = c.get("proposed_clause")
        for t in ([pc] if isinstance(pc, str) else [pc.get("he"), pc.get("en")] if isinstance(pc, dict) else []):
            flags = E.integrity_flags(t)
            if flags:
                warnings.append("%s %s: הנוסח המוצע טעון בדיקה אנושית (%s): «%s…»" % (rid, color, ", ".join(flags), str(t)[:50]))
                break


def source_findings(model, errors, warnings):
    """כלל 3 וסף הקורפוס: מסמך שאינו הסכם אינו נספר כהסכם; תווית נוסח של החברה רק על נייר החברה; מאגר מתחת
    לסף המספיקות נרשם במגבלות."""
    rows = [r for r in model.get("source_log") or [] if isinstance(r, dict)]
    cb = (model.get("scope_summary") or {}).get("corpus_basis") or {}
    counted = {str(x).replace("\\", "/").rsplit("/", 1)[-1] for x in cb.get("counted_agreements") or []}
    for r in rows:
        if not E.is_agreement(r) and r.get("included", True):
            f = str(r.get("file") or "").replace("\\", "/").rsplit("/", 1)[-1]
            if f and f in counted:
                errors.append("%s: מסמך שאינו הסכם (doc_role %s) נספר ב-counted_agreements. הוא שכבת ראיות נפרדת, לא הסכם" %
                              (r.get("source_id"), r.get("doc_role")))
        lab = " ".join(str(r.get(k) or "") for k in ("status", "source_label", "label", "short_name"))
        if OWN_LABEL_RX.search(lab) and r.get("paper") != "ours":
            errors.append("%s: תווית שאומרת שהנוסח של החברה על מסמך שאינו נייר החברה (paper: %s)" % (r.get("source_id"), r.get("paper") or "ריק"))
    for rule in model.get("rules") or []:
        for color in ("green", "yellow", "red"):
            c = (rule.get("traffic_light") or {}).get(color) or {}
            if OWN_LABEL_RX.search(str(c.get("source_label") or "")):
                sids = {str(e.get("source_ref") or "").split("#")[0] for e in rule.get("evidence") or [] if e.get("track") == color}
                papers = {(next((r for r in rows if r.get("source_id") == s), {}) or {}).get("paper") for s in sids}
                if sids and "ours" not in papers:
                    errors.append("%s %s: source_label אומרת שהנוסח של החברה, ואף מקור מצוטט אינו על נייר החברה" % (rule.get("rule_id"), color))
    # בדיקה שלא רצה אינה בדיקה שעברה: כשהספרייה אינה זמינה או נכשלה, זה נאמר כאזהרה ולא נבלע
    try:
        from playbook import sufficiency as SF
        res = SF.assess(rows, model.get("rules") or [])
        level = res.get("level") if isinstance(res, dict) else getattr(res, "level", None)
    except Exception as exc:  # noqa: BLE001
        level = None
        warnings.append("בדיקת המספיקות לא רצה (playbook.sufficiency): %s" % exc)
    if level in ("thin", "insufficient"):
        lim = json.dumps((model.get("scope_summary") or {}).get("limitations") or [], ensure_ascii=False)
        facts = json.dumps((model.get("scope_summary") or {}).get("client_facts") or [], ensure_ascii=False)
        if not re.search(r"(מספר|מדגם|הסכמים|agreements|sample|corpus|מאגר)", lim + facts, re.I):
            (errors if level == "insufficient" else warnings).append(
                "המאגר מתחת לסף המספיקות (%s) והמגבלה אינה רשומה ב-scope_summary.limitations" % level)


def run_checks(model, extract=None):
    """כל הבדיקות על מודל טעון: (errors, warnings). נקרא גם מ-validate_playbook_model.py, כך שכלל שנאכף כאן חוסם
    גם בקריאה לאימות."""
    texts = doc_texts(extract) if extract else {}
    ex_idx = E.doc_index(extract) if extract else {}
    src_rows = {r.get("source_id"): r for r in model.get("source_log") or [] if isinstance(r, dict)}
    names = E.party_names(model)
    company = model.get("company_name") or ""
    errors, warnings = [], []
    if not texts:
        warnings.append("לא נמסר --extract: בדיקת הציטוטים מול המקור וסיווג הראיה (ev_kind) לא רצו")
    for rule in model.get("rules") or []:
        if texts:
            quote_findings(rule, model, texts, errors, warnings)
        evidence_findings(rule, errors, warnings)
        silence_findings(rule, errors, warnings)
        law_findings(rule, model, errors, warnings)
        duplicate_findings(rule, errors, warnings)
        field_findings(rule, errors, warnings)
        kind_findings(rule, model, ex_idx, src_rows, errors, warnings)
        red_findings(rule, errors, warnings)
        rationale_findings(rule, errors, warnings)
        name_findings(rule, names, company, errors, warnings)
        legal_findings(rule, model, errors, warnings)
        integrity_findings(rule, errors, warnings)
    source_findings(model, errors, warnings)
    return errors, warnings


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--extract")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    model = load(a.model)
    extract = load(a.extract) if a.extract else E.find_extract(model, a.model)
    errors, warnings = run_checks(model, extract)
    res = {"errors": errors, "warnings": warnings, "rules": len(model.get("rules") or [])}
    if a.json:
        with open(a.json, "w", encoding="utf-8", newline="\n") as f:
            json.dump(res, f, ensure_ascii=False, indent=1)
    for e in errors[:60]:
        print("כשל:", e)
    for w in warnings[:20]:
        print("אזהרה:", w)
    print("%d נושאים נבדקו: %d כשלים, %d אזהרות" % (res["rules"], len(errors), len(warnings)))
    return 3 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
