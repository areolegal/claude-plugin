#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""כללי המתודולוגיה שנאכפים בקוד, במקום אחד, לבונה (build_workspace_payload.py) ולמאמתים
(enforce_playbook_checks.py, validate_playbook_model.py):

- סיווג ראיה לכל ציטוט (ev_kind): תוספת של החברה, מחיקה של החברה, הערת שוליים, נוסח של הצד שכנגד שלא שונה,
  או לא ידוע. נגזר מקטעי השינויים במעקב שקובץ החילוץ שומר (paragraphs[].changes), ולעולם לא מניחוש: בלי קובץ
  חילוץ, או כשהפסקה אינה נמצאת, הסיווג הוא unknown.
- מסמך שאינו הסכם (הנחיה פנימית, מדיניות, טבלה, תבנית) אינו נספר כהסכם, והוא שכבת ראיות נפרדת.
- נימוק שחוזר על נוסח העמדה הוא נימוק ריק.
- עמדה אדומה בלי נוסח תגובה ובלי הפניה מפורשת לנוסח החלופי היא פער, לא עמדה.
- שמות צדדים קונקרטיים בנוסח מדיניות; שפת נוסח שנגזרת מהטקסט; טענת דין בנוסח; בדיקת תקינות נוסח.
- מוני הניסיון החוזי נגזרים ממעמד המסמך ומנוכחות שינויים במעקב, ולא נכתבים ביד.

הקובץ אינו יודע דבר על סוג הסכם, על צד שכנגד או על דין: כל שם וכל נושא מגיעים ממודל הלקוח.
"""
import json
import re
from pathlib import Path

EV_KINDS = ("company_added", "company_deleted", "footnote", "counterparty_unchanged", "unknown")

# doc_role שאינו הסכם: אינו נספר במוני ההסכמים ובמכנה של אחוזי השכיחות, ואינו שורה בטבלת ההשוואה.
# guidance / policy / table: מסמך הנחיה או מדיניות של החברה, שכבת ראיות נפרדת שמשקלה גבוה משל טיוטה
NON_AGREEMENT_ROLES = ("template", "guidance", "policy", "table", "correspondence")
# משקל שכבת הראיות לפי מעמד המסמך: הנחיה כתובה של החברה מעל טיוטה, חתום מעל הכול
LAYER_WEIGHT = {"signed": 3, "agreement": 3, "amendment": 3, "guidance": 2, "policy": 2, "table": 2,
                "draft": 1, "form": 1, "template": 1, "correspondence": 0}

_HEB = re.compile(r"[֐-׿]")
_LATIN = re.compile(r"[A-Za-z]")
LAW_RX = re.compile(r"(חוק\s+[֐-׿\"'״׳]|תקנות\s+[֐-׿]|תקנה\s+\d+|פקודת\s+[֐-׿]|"
                    r"צו\s+[֐-׿]+\s+[֐-׿]|הרשות\s+ל|רשות\s+(?:ה|ל)[֐-׿]+|"
                    r"מפר(?:ה|ים|ת)?\s+את\s+(?:ה)?דין|דיני\s+ה[֐-׿]+|בניגוד\s+לדין|אסור\s+(?:על\s+פי|לפי)\s+(?:ה)?(?:דין|חוק)|"
                    r"\bGDPR\b|\bDirective\b|\bRegulation\s+\(|\b[A-Z][a-z]+\s+(?:Law|Act)\b|\bAct\s+\d{4}|"
                    r"\bunlawful\b|\billegal\b|\bprohibited\s+by\s+law\b|\bviolates?\s+(?:the\s+)?law\b)", re.I)


def norm(s):
    s = str(s or "")
    s = s.replace("‎", "").replace("‏", "").replace(" ", " ")
    s = re.sub(r"[‘’‚‛׳']", "'", s)
    s = re.sub(r"[“”„״\"]", '"', s)
    s = re.sub(r"[‐-―]", "-", s)
    return re.sub(r"\s+", " ", s).strip().lower()


# ---------------------------------------------------------------- קובץ החילוץ

def find_extract(model, model_path=None, explicit=None):
    """קובץ החילוץ: --extract, coverage.extract_ref ליד המודל, או corpus-extract.json בתיקיית הנתונים. None כשאין."""
    cands = [explicit]
    cov = (model or {}).get("coverage") or {}
    cands.append(cov.get("extract_ref"))
    cands += ["../../corpus-extract.json", "../corpus-extract.json", "corpus-extract.json",
              "../../Areo-נתונים/corpus-extract.json"]
    base = Path(model_path).resolve().parent if model_path else Path(".")
    for c in cands:
        if not c:
            continue
        for q in (Path(c), base / c):
            try:
                if q.is_file():
                    return json.loads(q.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
    return None


def doc_index(extract):
    """doc_id ושם הקובץ (בלי תיקייה) -> רשומת המסמך בקובץ החילוץ."""
    idx = {}
    for d in (extract or {}).get("documents") or []:
        if not isinstance(d, dict):
            continue
        if d.get("doc_id"):
            idx[d["doc_id"]] = d
        p = str(d.get("path") or "").replace("\\", "/").rsplit("/", 1)[-1]
        if p:
            idx[norm(p)] = d
    return idx


def doc_for_source(row, idx):
    if not row or not idx:
        return None
    d = idx.get(row.get("doc_id"))
    if d:
        return d
    f = str(row.get("file") or row.get("agreement_name") or "").replace("\\", "/").rsplit("/", 1)[-1]
    return idx.get(norm(f))


def _segments(quote):
    """קטעי הציטוט שנבדקים מול המקור: בין סימוני [...] ; קטעים קצרים מאוד אינם מכריעים."""
    parts = re.split(r"\s*(?:\[\s*\.{3}\s*\]|\[…\]|…|\.{3})\s*", str(quote or ""))
    return [norm(p) for p in parts if len(norm(p)) >= 12] or [norm(quote)]


def _para_of(doc, ref, quote):
    paras = doc.get("paragraphs") or []
    m = re.search(r"#p(\d+)", str(ref or ""))
    if m:
        i = int(m.group(1))
        for p in paras:
            if isinstance(p, dict) and p.get("i") == i:
                return p
        if 0 <= i < len(paras) and isinstance(paras[i], dict):
            return paras[i]
    segs = _segments(quote)
    for p in paras:
        if not isinstance(p, dict):
            continue
        blob = norm(p.get("text", "")) + " " + norm(p.get("text_reject_all", ""))
        if all(s in blob for s in segs):
            return p
    return None


def ev_kind(ev, row, doc):
    """סיווג הראיה של ציטוט אחד. ערך מפורש ותקין ברשומת הראיה מתקבל; אחרת נגזר מקובץ החילוץ; אחרת unknown.
    שינוי במעקב מיוחס לחברה רק כשהמסמך הוא נייר של הצד שכנגד (paper: theirs): על נייר החברה, מי שסימן אינו
    ידוע בלי שם המחבר, והסיווג נשאר unknown."""
    explicit = str((ev or {}).get("ev_kind") or (ev or {}).get("evidence_kind") or "").strip()
    if explicit in EV_KINDS:
        return explicit
    if not doc or not row:
        return "unknown"
    quote = (ev or {}).get("quote") or (ev or {}).get("text") or ""
    para = _para_of(doc, (ev or {}).get("source_ref") or (ev or {}).get("source_id"), quote)
    if para is None:
        return "unknown"
    if para.get("kind") == "footnote":
        return "footnote"
    segs = _segments(quote)
    paper = row.get("paper")
    changes = para.get("changes") or []
    ins = norm(" ".join(c.get("text", "") for c in changes if c.get("kind") == "ins"))
    dele = norm(" ".join(c.get("text", "") for c in changes if c.get("kind") == "del"))
    # הציטוט בתוך קטע ששונה, או קטע ששונה (מילה ומעלה) בתוך הציטוט: בשני המקרים הציטוט נושא נוסח שסומן
    ins_parts = [norm(c.get("text", "")) for c in changes if c.get("kind") == "ins"]
    del_parts = [norm(c.get("text", "")) for c in changes if c.get("kind") == "del"]
    hit_ins = any(s in ins for s in segs) or any(len(x) >= 4 and any(x in s for s in segs) for x in ins_parts)
    hit_del = any(s in dele for s in segs) or any(len(x) >= 4 and any(x in s for s in segs) for x in del_parts)
    if hit_ins or hit_del:
        if paper == "theirs":
            return "company_deleted" if hit_del and not hit_ins else "company_added"
        return "unknown"
    accepted = norm(para.get("text", ""))
    if all(s in accepted for s in segs):
        if paper == "theirs":
            return "counterparty_unchanged"
        return "unknown"
    return "unknown"


# ---------------------------------------------------------------- מסמך שאינו הסכם

def is_agreement(row):
    """האם שורת source_log היא הסכם (חתום, טיוטה, תיקון, נוסח) ולא הנחיה, מדיניות, טבלה או תבנית."""
    if not isinstance(row, dict):
        return False
    if row.get("included") is False or row.get("exclusion_reason") == "not_agreement":
        return False
    if row.get("is_agreement") is False or row.get("doc_kind") in ("guidance", "policy", "table"):
        return False
    return str(row.get("doc_role") or "") not in NON_AGREEMENT_ROLES


def layer_of(row):
    """שכבת הראיות של המסמך: agreement | guidance | template | other, עם משקל (LAYER_WEIGHT)."""
    role = str((row or {}).get("doc_role") or "")
    if role in ("guidance", "policy", "table") or (row or {}).get("doc_kind") in ("guidance", "policy", "table"):
        return "guidance"
    if role == "template":
        return "template"
    return "agreement" if is_agreement(row) else "other"


def has_tracked(row):
    """האם המסמך נושא שינויים במעקב: לפי שדות הסריקה שנרשמו בשורה, או לפי doc_role: draft."""
    for k in ("has_tracked_changes", "tracked_changes", "negotiated"):
        if row.get(k) is True:
            return True
    tc = row.get("tracked_counts")
    if isinstance(tc, dict) and any(isinstance(v, int) and v > 0 for v in tc.values()):
        return True
    return str(row.get("doc_role") or "") == "draft"


def derived_counts(rule, source_log):
    """מוני הניסיון החוזי של הכלל, מהעובדות: משא ומתן עצמאי = מסמך הסכם מצוטט (track ירוק/צהוב/אדום) שנחתם,
    תוקן, או נושא שינויים במעקב; גרסאות של אותו negotiation_id נספרות פעם אחת. on_company_paper: מהם על נייר
    החברה. documents_addressing: כל מסמכי ההסכם המצוטטים."""
    rows = {r.get("source_id"): r for r in source_log or [] if isinstance(r, dict)}
    negs, own, docs = set(), set(), set()
    for ev in rule.get("evidence") or []:
        if ev.get("track") not in ("green", "yellow", "red"):
            continue
        sid = str(ev.get("source_ref") or ev.get("source_id") or "").split("#")[0]
        row = rows.get(sid)
        if not row or not is_agreement(row):
            continue
        docs.add(sid)
        role = str(row.get("doc_role") or "")
        if role in ("signed", "agreement", "amendment") or has_tracked(row):
            key = row.get("negotiation_id") or sid
            negs.add(key)
            if row.get("paper") == "ours":
                own.add(key)
    return {"independent_negotiations": len(negs), "on_company_paper": len(own), "documents_addressing": len(docs)}


# ---------------------------------------------------------------- נימוקים

RATIONALE_CORE = ("protected_interest_and_clause_purpose", "legal_risk_and_legal_framework", "tradeoff_statement",
                  "green_boundary_rationale", "yellow_boundary_rationale", "red_boundary_rationale")


def _positions(rule):
    out = []
    for c in ("green", "yellow", "red"):
        t = ((rule.get("traffic_light") or {}).get(c) or {})
        for k in ("position", "meaning"):
            if t.get(k):
                out.append(norm(t[k]))
    return [p for p in out if p]


def repeats_position(text, positions, topic=""):
    """נימוק שאחרי הסרת נוסח העמדה (וכותרת הנושא) נשאר ממנו פחות מ-40 תווים הוא חזרה, לא הנמקה."""
    t = norm(text)
    if not t:
        return True
    for p in positions + ([norm(topic)] if topic else []):
        if p and len(p) >= 8:
            t = t.replace(p, " ")
    t = re.sub(r"(בנושא|הירוק הוא|הצהוב הוא|האדום הוא|the green is|the yellow is|the red is|in the topic|is|הוא|היא)\b", " ", t)
    return len(re.sub(r"[\s:.,;\"'()\-]+", "", t)) < 40


def rationale_complete(rule):
    """(שלם?, סיבות). שלם: כל שדות הליבה כתובים ואינם חזרה על נוסח העמדה, ואין שדות ממתינים למעבר ב."""
    rat = rule.get("policy_rationale") or {}
    reasons = []
    if not isinstance(rat, dict) or not rat:
        return False, ["no_rationale"]
    positions = _positions(rule)
    topic = rule.get("topic_name") or ""
    for k in RATIONALE_CORE:
        v = rat.get(k)
        if not str(v or "").strip():
            reasons.append("empty:" + k)
        elif repeats_position(v, positions, topic):
            reasons.append("repeats_position:" + k)
    if rat.get("pass_b_pending"):
        reasons.append("pass_b_pending")
    return not reasons, reasons


# ---------------------------------------------------------------- האדום: נוסח תגובה או הפניה

def red_response(red):
    """מה האדום נותן לנושא ונותן: ("wording", טקסט) | ("pointer", "yellow"/"green") | (None, "")."""
    if not isinstance(red, dict):
        return None, ""
    for k in ("response_wording", "proposed_clause"):
        v = red.get(k)
        txt = v if isinstance(v, str) else (" ".join(str(v.get(g) or "") for g in ("he", "en")) if isinstance(v, dict) else "")
        if txt.strip():
            return "wording", txt.strip()
    ptr = str(red.get("fallback_pointer") or red.get("response_pointer") or "").strip().lower()
    if ptr in ("yellow", "green"):
        return "pointer", ptr
    return None, ""


# ---------------------------------------------------------------- נוסח: שמות, שפה, דין, תקינות

def party_names(model):
    """שמות הצדדים הקונקרטיים שמופיעים במודל: החברה, הישויות וכל צד שכנגד ב-source_log. מהם, לא מרשימה."""
    names = set()
    ss = model.get("scope_summary") or {}
    for v in ([model.get("company_name"), (ss.get("contracting_entity") or {}).get("name")]
              + list(ss.get("legal_entities") or []) + [r.get("counterparty") for r in model.get("source_log") or []]):
        if isinstance(v, dict):
            v = v.get("name")
        v = str(v or "").strip()
        if len(v) >= 3 and not v.isdigit():
            names.add(v)
    return sorted(names, key=len, reverse=True)


def _name_variants(name):
    base = re.sub(r"\s*(בע\"מ|בע״מ|בעמ|ltd\.?|inc\.?|llc|gmbh|limited|corp\.?|corporation|co\.)\s*$", "", name, flags=re.I).strip()
    out = {name}
    if len(base) >= 3:
        out.add(base)
    return out


def name_hits(text, names, company_name=""):
    """שמות קונקרטיים בנוסח מדיניות, ולכל אחד תווית גנרית מוצעת: החברה או הצד שכנגד. התווית אינה מניחה תפקיד."""
    hits = []
    t = str(text or "")
    for n in names:
        for v in _name_variants(n):
            if v and re.search(r"(?<![\w֐-׿])" + re.escape(v) + r"(?![\w֐-׿])", t):
                generic = "החברה" if company_name and v in _name_variants(company_name) else "הצד שכנגד"
                if _LATIN.search(v) and not _HEB.search(t):
                    generic = "the Company" if generic == "החברה" else "the Counterparty"
                hits.append({"name": v, "generic": generic})
                break
    return hits


def generic_text(text, hits):
    t = str(text or "")
    for h in hits:
        t = re.sub(r"(?<![\w֐-׿])" + re.escape(h["name"]) + r"(?![\w֐-׿])", h["generic"], t)
    return t


def detect_lang(text):
    """שפת הנוסח מהטקסט בפועל: he | en | "" (ריק כשאין טקסט). לעולם לא ברירת מחדל."""
    t = str(text or "")
    h, l = len(_HEB.findall(t)), len(_LATIN.findall(t))
    if not (h or l):
        return ""
    return "he" if h >= l else "en"


def legal_claim(text):
    """האם בנוסח יש טענת דין (שם חוק, תקנה, רשות, או קביעה שדבר אסור או מפר דין)."""
    return bool(LAW_RX.search(str(text or "")))


def integrity_flags(text):
    """בדיקת תקינות בסיסית לנוסח לפני שהוא עולה לדרגת נוסח מוצע: repeated_phrase (ביטוי של 3 מילים ומעלה
    שחוזר ברצף), stuck_words (מילים דבוקות: אות קטנה ואז גדולה בלטינית, או מילה ארוכה מ-28 תווים),
    starts_midway (פותח בסימן פיסוק, באות קטנה לטינית או במילת חיבור), unbalanced (סוגריים או מירכאות
    שאינם סגורים). רשימה ריקה כשהכול תקין."""
    t = re.sub(r"\s+", " ", str(text or "")).strip()
    flags = []
    if not t:
        return flags
    words = t.split(" ")
    low = [norm(w) for w in words]
    for n in (3, 4, 5):
        for i in range(len(low) - 2 * n + 1):
            if low[i:i + n] == low[i + n:i + 2 * n] and any(len(w) > 2 for w in low[i:i + n]):
                flags.append("repeated_phrase")
                break
        if "repeated_phrase" in flags:
            break
    if re.search(r"[a-z]{2,}[A-Z][a-z]{2,}", t) or any(len(w) > 28 and not re.search(r"[/\\:@]", w) for w in words):
        flags.append("stuck_words")
    if re.match(r"^[,;:)\]}]|^[a-z]|^(and|or|but|which|that|whereas)\b|^(ו|או|אבל|אשר|שבו|כאשר)\s", t):
        flags.append("starts_midway")
    for a, b in (("(", ")"), ("[", "]")):
        if t.count(a) != t.count(b):
            flags.append("unbalanced")
            break
    if "unbalanced" not in flags and t.count('"') % 2 == 1 and not re.search(r"\b\w\"\w\b", t):
        flags.append("unbalanced")
    return flags
