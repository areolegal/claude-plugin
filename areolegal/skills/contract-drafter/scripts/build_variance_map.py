# -*- coding: utf-8 -*-
"""מפת השונות: מה קבוע ומה משתנה בין ההסכמים הקיימים של החברה מאותו סוג ובאותו צד.

המנסח קורא את ההסכמים, מבין אילו נתונים משתנים מהסכם להסכם ואילו לא, ושואל את הלקוח רק על מה שמשתנה. הסקריפט
כללי לכל סוג הסכם ולכל דין: אין בו אוצר מילים של סוג מסוים. הסעיפים מפוצלים לפי כותרות ונושאים בכלים הקיימים
(split_clauses ו-topic_of של בנק הסעיפים), והשונות נמדדת בהשוואת מילים בין ההסכמים.

    python3 build_variance_map.py --registry Areo-נתונים/template-registry.json --family "<משפחה>" \\
        --role <company_role_code> --profile "<פרופיל-לקוח.json>" \\
        --out "Areo-נתונים/תבניות/<משפחה>/variance-map.json" [--skeleton <skeleton.json>] [--force]

הפלט:
  constants             סעיפים שהנוסח שלהם זהה בכל ההסכמים (אחרי נרמול, ופרט לשדות הנתונים). נשמרים ואינם נשאלים.
  data_fields           ערכים שמשתנים מהסכם להסכם (שמות, סכומים, תאריכים, תקופות, שיעורים, מקומות, תפקידים),
                        עם הערכים שנמצאו והספירה. כולל את מה ש-derive_deal_defaults ו-skeleton.json כבר מזהים.
  optional_clauses      סעיף או נושא שמופיע רק בחלק מההסכמים: באילו כן ובאילו לא, הסימנים שמבדילים ביניהם
                        (מילה בכותרת או במבוא, ערך של שדה, טווח סכומים, סוג הצד שכנגד), והנוסח של הלקוח.
  alternative_wordings  אותו נושא בנוסחים שונים מהותית: הנוסחים מקובצים, ולכל אחד ההסכמים והסימנים.
  questions             טיוטת טופס השאלות (עד שמונה), שנגזרה מהמפה; השאר ב-defaults_for_approval.
כל פריט נושא הפניות למסמכים (DOC-<n>) ולמספר הסעיף בהם.

מסמכים: מהמרשם, ממשפחת ההסכם ומהצד של החברה; מסמך על נייר החברה (paper: company) ומסמך של צד שלישי, שמסומן
כך (paper: counterparty). במסלול המחקר, מרשם של הסכמים שפורסמו ונאספו בדרך המאושרת, כל אחד עם "paper": "published"
(טקסט שנשמר בתיקייה זמנית): כל סעיף אופציונלי ונוסח חלופי מהם מסומן areo_proposal. מסמך שנכתב בצד ההפוך אינו נכלל. פחות משני מסמכים: אין שונות למדוד, והסקריפט אומר זאת.

קוד יציאה: 0 הצלחה; 2 אין מרשם, אין מסמכים או פלט אסור.
"""
import argparse
import difflib
import io
import json
import os
import re
import sys
from collections import Counter, OrderedDict
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_template_registry import (docx_paragraphs, guard_out, family_matches, normalize_role,  # noqa: E402
                                     pdf_text, word_count)
from build_clause_bank import (HEADING_INLINE, HEADING_SPLIT, NOT_A_HEADING, looks_like_bare_heading,  # noqa: E402
                               topic_of)

try:                                   # פלט עברי במסוף של Windows
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):   # pragma: no cover
    pass

SAME = 0.86          # דמיון מילים שמעליו שני נוסחים הם "אותו נוסח, עם נתונים שונים"
DATA_SPAN = 8        # אורך מרבי (במילים) של קטע שונה שנחשב לשדה נתונים ולא לשינוי נוסח
MAX_QUESTIONS = 8    # טופס אחד, עד שמונה שאלות (template-flow.md, פרק 3)
TOKEN = re.compile(r"[\w֐-׿][\w֐-׿'\"״׳.,/%\-]*|[^\s\w]", re.U)
NUM = re.compile(r"^\d[\d,./%\-]*$")
DATE = re.compile(r"\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{4}-\d{2}-\d{2}")
CUR = re.compile(r"₪|ש\"ח|ש״ח|\$|€|£|(?<![A-Za-z])(?:ILS|NIS|USD|EUR|GBP|CHF|JPY|CAD|AUD)(?![A-Za-z])")
PERIOD = re.compile(r"(?:יום|ימים|חודש|חודשים|שנה|שנים|שבוע|שבועות|day|days|month|months|year|years|week|weeks)\b", re.I)
PCT = re.compile(r"%|אחוז|percent", re.I)
ORG = re.compile(r"בע\"מ|בע״מ|\(ע\"ר\)|\bLtd\b|\bInc\b|\bLLC\b|\bGmbH\b|\bplc\b|\bLLP\b|University|אוניברסיט|עמותה|"
                 r"רשות|עיריית|משרד|Council|Ministry|Authority", re.I)
STOP = set("""של את על עם או גם כי אם לא כל זה זו זאת הוא היא הם הן אשר יהיה תהיה יהיו בין לבין לפי עד מן מ ב ל ה ו
the a an of to and or in on for by with as at be is are this that shall will may any all such from its their it
""".split())


def tok_spans(s):
    """(מילה, התחלה, סוף), כשפיסוק בסוף מילה ("180,000," או "בסוד.") הוא אסימון נפרד."""
    out = []
    for m in TOKEN.finditer(s or ""):
        t, a = m.group(0), m.start()
        core = t.rstrip(".,;:")
        if core and core != t and not re.match(r"^[א-ת]\.[א-ת]\.?$", t):   # ת.ז. נשאר אסימון אחד
            out.append((core, a, a + len(core)))
            for k, ch in enumerate(t[len(core):]):
                out.append((ch, a + len(core) + k, a + len(core) + k + 1))
        else:
            out.append((t, a, m.end()))
    return out


def toks(s):
    return [t for t, _, _ in tok_spans(s)]


def norm_tok(t):
    t = t.strip("\"'״׳.,;:()").lower()
    return "<n>" if NUM.match(t) else t


def ratio(a, b):
    return difflib.SequenceMatcher(None, [norm_tok(x) for x in a], [norm_tok(x) for x in b], autojunk=False).ratio()


def kind_of(value):
    v = value or ""
    if DATE.search(v):
        return "date"
    if CUR.search(v):
        return "amount"
    if re.search(r"\d", v) and PCT.search(v):
        return "rate"
    if re.search(r"\d", v) and PERIOD.search(v):
        return "period"
    if re.search(r"\d", v):
        return "number"
    if ORG.search(v):
        return "party"
    return "text"


def amounts(text):
    """הסכומים במסמך (מספר עם מטבע לפניו או אחריו), לטווח סכומים כסימן מבדיל."""
    out = []
    for m in re.finditer(r"(?:(?:₪|\$|€|£|ILS|NIS|USD|EUR|GBP)\s?(\d[\d,]*(?:\.\d+)?))|(?:(\d[\d,]*(?:\.\d+)?)\s?"
                         r"(?:₪|ש\"ח|ש״ח|ILS|NIS|USD|EUR|GBP|\$|€|£))", text):
        v = (m.group(1) or m.group(2) or "").replace(",", "")
        try:
            out.append(float(v))
        except ValueError:
            pass
    return out


# ------------------------------------------------------------------ קריאת המסמכים
def split_all(paras):
    """כמו split_clauses של בנק הסעיפים, באותם ביטויים, אבל בלי סף אורך: גם סעיף קצר ("חובת הסודיות תחול 3 שנים")
    הוא סעיף, ואם הוא נשמט מהמפה הוא נשמט גם מהטיוטה."""
    heads = []
    for i, p in enumerate(paras):
        t = p.strip()
        if NOT_A_HEADING.search(t):
            continue
        m = HEADING_INLINE.match(t)
        if m and not re.match(r"^\d{1,2}\.\d{1,2}\.\d{4}", t):
            heads.append((i, m.group(1), m.group(2).strip(" :.-"), ""))
            continue
        m = HEADING_SPLIT.match(t)
        if m:
            heads.append((i, m.group(1), m.group(2).strip(" :.-"), m.group(3).strip()))
            continue
        if looks_like_bare_heading(p) and i + 1 < len(paras) and len(paras[i + 1]) > 40:
            heads.append((i, None, t.rstrip(".:"), ""))
    # במסמך שיש בו סעיפים ממוספרים, שורה קצרה בלי מספר לפני הסעיף הממוספר הראשון היא מבוא (צדדים, כתובת), לא סעיף
    first_num = next((i for i, num, _, _ in heads if num), None)
    if first_num is not None:
        heads = [h for h in heads if h[1] or h[0] > first_num]
    out = []
    for j, (i, num, head, inline) in enumerate(heads):
        end = heads[j + 1][0] if j + 1 < len(heads) else len(paras)
        body = re.sub(r"\s+", " ", " ".join([inline] + paras[i + 1:end])).strip()
        if len(head) >= 2 and body:
            out.append((num, head, body))
    return out


def unreadable(text):
    """הסיבה כשהטקסט אינו טקסט קריא (בייטים של PDF, קידוד שבור, PDF סרוק), אחרת None."""
    t = (text or "").strip()
    if len(t) < 200:
        return "אין בו טקסט שאפשר לקרוא (מסמך סרוק או ריק)"
    if t.startswith("%PDF") or "\x00" in t[:2000]:
        return "הקובץ נקרא כבייטים ולא כטקסט"
    sample = re.sub(r"\s+", "", t[:20000])
    letters = len(re.findall(r"[A-Za-z\u0590-\u05FF]", sample))
    if not sample or letters / float(len(sample)) < 0.55:
        return "הטקסט שחולץ אינו קריא"
    return None


def read_paras(d):
    """פסקאות המסמך באותו חילוץ כמו בשאר המערכת: docx_paragraphs ל-Word, pdf_text ל-PDF (pymupdf), וטקסט."""
    path = os.path.join(d.get("folder", ""), d["file"])
    low = path.lower()
    if low.endswith(".docx"):
        mode = "base" if d.get("approved_current_basis") == "redline_base" else "final"
        return docx_paragraphs(path, limit=20000, mode=mode), None
    if low.endswith(".pdf"):
        text, why = pdf_text(path)
        if not text.strip():
            return [], why or "אין בו טקסט שאפשר לקרוא (מסמך סרוק)"
        return [x.strip() for x in text.split("\n") if x.strip()], None
    if low.endswith((".txt", ".md")):
        return [x.strip() for x in io.open(path, encoding="utf-8", errors="ignore").read().split("\n") if x.strip()], None
    return [], "סוג קובץ שאינו נקרא (%s)" % (os.path.splitext(path)[1] or "בלי סיומת")


HEAD_PREFIX = re.compile(r"^(?:[\u05d0-\u05ea]|[A-Za-z]|\d{1,3})[.)]\s*(?=\S)")


SIGN_START = re.compile(r"^\s*(?:IN\s+WITNESS|ולראי{1,2}ה|ובאו\s+הצדדים\s+על\s+החתום)", re.I)


def read_doc(d, paras=None):
    if paras is None:
        paras, _ = read_paras(d)
    # בלוק החתימות אינו חלק מהסעיף האחרון: בלעדיו הוא נספר כשונות של הסעיף
    cut = next((i for i, p in enumerate(paras) if i > 3 and SIGN_START.match(p)), None)
    paras = paras[:cut] if cut else paras
    clauses = [(n, HEAD_PREFIX.sub("", h).strip() or h, b) for n, h, b in split_all(paras)]
    first_head = None
    for i, p in enumerate(paras):
        if clauses and clauses[0][1] and clauses[0][1] in p:
            first_head = i
            break
    preamble = paras[:first_head] if first_head else paras[:6]
    by_key = OrderedDict()
    for num, head, body in clauses:
        topic, _ = topic_of(head, body)
        key = topic or "כותרת: " + re.sub(r"\s+", " ", head.strip().lower())
        if key in by_key:
            by_key[key]["text"] += " " + body
            by_key[key]["numbers"].append(num)
        else:
            by_key[key] = {"topic": topic, "heading": head.strip(), "numbers": [num], "text": body}
    return {"title": (paras[0] if paras else ""), "preamble": " ".join(preamble), "clauses": by_key,
            "text": " ".join(paras)}


# ------------------------------------------------------------------ שונות בתוך נוסח זהה
def data_spans(ref, other):
    """קטעים קצרים שונים בין שני נוסחים כמעט זהים: [(הקשר לפני, ערך בהפניה, ערך במסמך האחר)]."""
    a, b = toks(ref), toks(other)
    sm = difflib.SequenceMatcher(None, [norm_tok(x) for x in a], [norm_tok(x) for x in b], autojunk=False)
    out, big = [], False
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            # מספרים מנורמלים ל-<n>: שני ערכים שונים באותו מקום הם שדה נתונים
            for k in range(i2 - i1):
                if a[i1 + k] != b[j1 + k] and NUM.match(a[i1 + k].strip("\"'.,;:()")):
                    ctx = " ".join(a[max(0, i1 + k - 4):i1 + k])
                    out.append((ctx, a[i1 + k], b[j1 + k], i1 + k))
            continue
        if max(i2 - i1, j2 - j1) > DATA_SPAN:
            big = True
            continue
        ctx = " ".join(a[max(0, i1 - 4):i1])
        out.append((ctx, " ".join(a[i1:i2]), " ".join(b[j1:j2]), i1))
    return out, big


def template_of(ref, spans_at):
    """הנוסח הקבוע, כלשונו, עם מציין לכל שדה: {{F<n>}} במקום הערך בהסכם ההפניה. ההחלפה לפי מיקום התווים
    במקור, כך שהפיסוק והרווחים נשארים כמו בנוסח של הלקוח."""
    sp = tok_spans(ref)
    out, last = [], 0
    for pos, n, fid in sorted(spans_at):
        if pos >= len(sp):
            continue
        a, b = sp[pos][1], sp[min(len(sp), pos + max(1, n)) - 1][2]
        if a < last:
            continue
        out.append(ref[last:a])
        out.append("{{%s}}" % fid)
        last = b
    out.append(ref[last:])
    return "".join(out)


# ------------------------------------------------------------------ סימנים מבדילים
def words_of(s):
    return {w for w in (norm_tok(x) for x in toks(s)) if len(w) > 2 and w not in STOP and w != "<n>"}


def signals(ids, yes, no, docs, fields):
    """מה מבדיל בין המסמכים שבקבוצה yes לאלה שב-no: מילים בכותרת או במבוא שמופיעות רק בקבוצה אחת, ערכי שדה
    שאינם חופפים, טווח סכומים וסוג הצד שכנגד. כללי: הכול נלמד מהמסמכים עצמם."""
    out = []
    if not yes or not no:
        return out
    for label, part in (("כותרת", "title"), ("מבוא", "preamble")):
        wy = [words_of(docs[i][part]) for i in yes]
        wn = [words_of(docs[i][part]) for i in no]
        # מילה שמשותפת לשני מסמכים לפחות בקבוצה, ואינה בקבוצה השנייה; במסמך יחיד כל מילה "ייחודית" (שם, כתובת)
        only_y = set.intersection(*wy) - set.union(*wn) if len(wy) > 1 and wn else set()
        only_n = set.intersection(*wn) - set.union(*wy) if len(wn) > 1 and wy else set()
        if only_y or only_n:
            out.append({"kind": label, "with": sorted(only_y)[:6], "without": sorted(only_n)[:6]})
    for f in fields:
        if f.get("per_deal") or f.get("type") not in ("amount", "rate", "period", "number") or not f.get("by_doc"):
            continue   # ערך שונה בכל הסכם (שם, תאריך, מספר זהות) אינו סימן: הוא נתון של העסקה
        vy = {f["by_doc"].get(i) for i in yes} - {None, ""}
        vn = {f["by_doc"].get(i) for i in no} - {None, ""}
        if vy and vn and not (vy & vn):
            out.append({"kind": "שדה", "field": f["id"], "context": f["context"], "with": sorted(vy)[:4],
                        "without": sorted(vn)[:4]})
    ay = [max(amounts(docs[i]["text"]) or [0]) for i in yes]
    an = [max(amounts(docs[i]["text"]) or [0]) for i in no]
    if len([x for x in ay if x]) > 1 and len([x for x in an if x]) > 1 and (min(ay) > max(an) or max(ay) < min(an)):
        out.append({"kind": "טווח סכומים", "with": [min(ay), max(ay)], "without": [min(an), max(an)]})
    oy = {bool(ORG.search(docs[i]["preamble"])) for i in yes}
    on = {bool(ORG.search(docs[i]["preamble"])) for i in no}
    if len(oy) == 1 and len(on) == 1 and oy != on:
        out.append({"kind": "סוג הצד שכנגד", "with": ["תאגיד או גוף" if True in oy else "אדם פרטי"],
                    "without": ["תאגיד או גוף" if True in on else "אדם פרטי"]})
    return out


SOURCE_WORDS = {"he": {"company": "בהסכמים שלכם", "third_party": "בנוסחים שנמצאו", "published": "בהסכמים שפורסמו"},
                "en": {"company": "in your agreements", "third_party": "in the forms we found",
                       "published": "in the published agreements"}}
SOURCE = ["company"]


def signal_phrase(sig, lang):
    """הסימן המבדיל במשפט קצר, בלשון הלקוח: " (בדרך כלל כש<שדה> הוא <ערך>)". רק סימנים שהלקוח מבין: ערך של שדה,
    טווח סכומים, סוג הצד שכנגד; מילים מהכותרות והמבוא אינן סימן שמציגים."""
    en = lang == "en"
    sig = [x for x in (sig or []) if x.get("with") and x["kind"] in ("שדה", "טווח סכומים", "סוג הצד שכנגד")]
    if not sig:
        return ""
    order = {"שדה": 0, "טווח סכומים": 1, "סוג הצד שכנגד": 2}
    s = sorted(sig, key=lambda x: order[x["kind"]])[0]
    if s["kind"] == "שדה":
        return (" Usually when %s is %s." if en else " בדרך כלל כש%s הוא %s.") % (
            s["context"] or ("the value" if en else "הערך"), " / ".join(str(x) for x in s["with"]))
    if s["kind"] == "טווח סכומים":
        lo, hi = "{:,.0f}".format(s["with"][0]), "{:,.0f}".format(s["with"][1])
        if lo == hi:
            return (" Usually when the amounts reach %s." if en else " בדרך כלל כשהסכומים מגיעים ל-%s.") % hi
        return (" Usually for amounts of %s to %s." if en else " בדרך כלל בסכומים של %s עד %s.") % (lo, hi)
    return (" Usually when the other side is %s." if en else " בדרך כלל כשהצד השני הוא %s.") % " / ".join(s["with"][:2])


# ------------------------------------------------------------------ המפה
def build(docs_meta, docs, profile, skeleton=None, defaults=None):
    lang = "en" if sum(1 for d in docs_meta if (d.get("language") or "")[:2] == "en") > len(docs_meta) / 2 else "he"
    ids = list(range(len(docs)))
    ref_of = lambda i: "DOC-%d" % (i + 1)
    keys = OrderedDict()
    for i, d in enumerate(docs):
        for k in d["clauses"]:
            keys.setdefault(k, []).append(i)
    constants, fields, optional, alternatives = [], [], [], []
    fno = [0]

    def new_field(topic, heading, ctx, by_doc, refs):
        by_doc = {i: v.strip(" ,;:.") if v.strip(" ,;:.") else v for i, v in by_doc.items()}
        fno[0] += 1
        vals = Counter(v for v in by_doc.values())
        f = {"id": "F%d" % fno[0], "topic": topic, "heading": heading, "context": ctx.strip(),
             "type": kind_of(next(iter(by_doc.values()), "")),
             "values": [{"value": v, "count": n, "documents": [ref_of(i) for i, x in by_doc.items() if x == v]}
                        for v, n in vals.most_common()],
             "default": vals.most_common(1)[0][0] if vals and vals.most_common(1)[0][1] > 1 else None,
             "per_deal": not vals or vals.most_common(1)[0][1] == 1, "by_doc": by_doc, "refs": refs}
        fields.append(f)
        return f

    def refs_for(k, members):
        return [{"doc": ref_of(i), "clause": ", ".join(x for x in docs[i]["clauses"][k]["numbers"] if x) or None}
                for i in members]

    # המבוא (שמות הצדדים, מספרי רישום, כתובות, תאריכים) הוא שדות נתונים, לא נוסח
    pre_ref = max(ids, key=lambda i: len(docs[i]["preamble"]))
    pre_spans = {}
    for i in ids:
        if i == pre_ref:
            continue
        sp, _ = data_spans(docs[pre_ref]["preamble"], docs[i]["preamble"])
        for ctx, rv, ov, pos in sp:
            pre_spans.setdefault((pos, ctx, rv), {pre_ref: rv})[i] = ov
    for (pos, ctx, rv), by_doc in sorted(pre_spans.items()):
        if len(set(by_doc.values())) > 1:
            new_field("מבוא", "המבוא והצדדים" if lang == "he" else "Preamble and parties", ctx, by_doc,
                      [{"doc": ref_of(i), "clause": None} for i in by_doc])

    for k, members in keys.items():
        sample = docs[members[0]]["clauses"][k]
        topic, heading = sample["topic"], sample["heading"]
        # הנוסח המייצג: זה שהכי דומה לשאר (ולא הארוך ביותר)
        ref = max(members, key=lambda i: sum(ratio(toks(docs[i]["clauses"][k]["text"]),
                                                   toks(docs[j]["clauses"][k]["text"])) for j in members))
        rtext = docs[ref]["clauses"][k]["text"]
        # קיבוץ הנוסחים: נוסח שדומה לנציג הקבוצה מעל הסף הוא אותו נוסח, עם נתונים שונים
        groups = [[ref]]
        for i in members:
            if i == ref:
                continue
            for g in groups:
                if ratio(toks(docs[g[0]]["clauses"][k]["text"]), toks(docs[i]["clauses"][k]["text"])) >= SAME:
                    g.append(i)
                    break
            else:
                groups.append([i])
        # שדות הנתונים בתוך הקבוצה של ההפניה
        spans, local_fields = {}, []
        for i in groups[0][1:]:
            sp, _big = data_spans(rtext, docs[i]["clauses"][k]["text"])
            for ctx, rv, ov, pos in sp:
                spans.setdefault((pos, ctx, rv), {ref: rv})[i] = ov
        marks = []
        for (pos, ctx, rv), by_doc in sorted(spans.items()):
            if len(set(by_doc.values())) > 1:
                f = new_field(topic, heading, ctx, by_doc, refs_for(k, list(by_doc)))
                local_fields.append(f)
                marks.append((pos, len(toks(rv)) or 1, f["id"]))
        variants = [{"variant": "V%d" % (n + 1), "documents": [ref_of(i) for i in g],
                     "text": docs[g[0]]["clauses"][k]["text"], "refs": refs_for(k, g)} for n, g in enumerate(groups)]
        if len(members) == len(docs) and len(groups) == 1:
            constants.append({"id": "C%d" % (len(constants) + 1), "topic": topic, "heading": heading,
                              "text": rtext, "text_template": template_of(rtext, marks),
                              "fields": [f["id"] for f in local_fields], "refs": refs_for(k, members)})
            continue
        if len(members) < len(docs):
            yes, no = members, [i for i in ids if i not in members]
            optional.append({"id": "O%d" % (len(optional) + 1), "topic": topic, "heading": heading,
                             "with": [ref_of(i) for i in yes], "without": [ref_of(i) for i in no],
                             "signals": [], "_yes": yes, "_no": no, "wording": rtext,
                             "variants": variants if len(groups) > 1 else [], "refs": refs_for(k, members)})
        else:
            for v, g in zip(variants, groups):
                v["_yes"], v["_no"] = g, [i for i in members if i not in g]
            alternatives.append({"id": "A%d" % (len(alternatives) + 1), "topic": topic, "heading": heading,
                                 "variants": variants, "refs": refs_for(k, members)})

    # הסימנים המבדילים מחושבים אחרי שכל השדות נמצאו, כדי ששדה מסעיף מאוחר ייחשב גם כסימן לסעיף מוקדם
    for item in optional + [v for a in alternatives for v in a["variants"]]:
        if "_yes" in item:
            item["signals"] = signals(ids, item.pop("_yes"), item.pop("_no"), docs, fields)

    # מה שהכלים הקיימים כבר מזהים: ברירות המחדל המסחריות (derive_deal_defaults) ומשתני השלד (skeleton.json)
    have = [{str(v["value"]).replace(",", "") for v in f["values"]} for f in fields]
    for p in defaults or []:
        pv = {str(x["value"]).split()[0].replace(",", "") for x in p.get("distribution") or []}
        if any(pv <= h for h in have):
            continue   # אותו פרמטר כבר נמצא כשדה בהשוואת הנוסחים
        if p.get("value") is not None and len(p.get("distribution") or []) > 1:
            fno[0] += 1
            fields.append({"id": "F%d" % fno[0], "topic": None, "heading": p["parameter"], "context": p.get("question"),
                           "type": kind_of(str(p["value"])), "source": "derive_deal_defaults",
                           "values": [{"value": x["value"], "count": x["documents"]} for x in p["distribution"]],
                           "default": p["value"], "by_doc": {}, "refs": [{"doc": None, "file": p.get("source_file")}]})
    for v in (skeleton or {}).get("variables") or []:
        fno[0] += 1
        fields.append({"id": "F%d" % fno[0], "topic": None, "heading": v.get("label") or v.get("id"),
                       "context": v.get("id"), "type": v.get("type") or "text", "source": "skeleton",
                       "values": [{"value": v.get("found_value"), "count": 1}] if v.get("found_value") else [],
                       "default": v.get("found_value"), "by_doc": {}, "refs": []})

    # שדה שהפרופיל קובע (שם החברה, מספר הרישום) אינו נשאל
    prof_vals = {str(x).strip() for x in ((profile or {}).get("organization_name"), (profile or {}).get(
        "organization_name_en"), (profile or {}).get("registration_number")) if x}
    for f in fields:
        if any(any(pv and pv in str(x["value"]) for pv in prof_vals) for x in f["values"]):
            f["derivable_from"] = "profile"
    return lang, constants, fields, optional, alternatives


def excerpt(t, n=70):
    t = re.sub(r"\s+", " ", t or "").strip()
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + "..."


COUNT_WORDS = {"he": {"company": "ההסכמים שלכם", "third_party": "הנוסחים שנמצאו", "published": "ההסכמים שפורסמו"},
               "en": {"company": "of your agreements", "third_party": "of the forms we found",
                      "published": "of the published agreements"}}
YES_NO = {"he": ("כן, להוסיף", "לא, בלי הסעיף"), "en": ("Yes, add it", "No, leave it out")}
# סעיף שמופיע ברוב המסמכים (לפחות 60% מהמסמכים, ולפחות שלושה מסמכים) הוא סעיף ליבה: נכלל, ואינו נשאל
CORE_SHARE = 0.6
END_WORDS = set("של על את לפני אחרי עם או ו כי אם כגון לרבות לפי בין the of to and or in on for by with a an such "
                "including".split())
HEADING_OK = re.compile(r"^[A-Za-z\u05d0-\u05ea][A-Za-z\u05d0-\u05ea ,'\-&]*$")


def _bare(w):
    w = w.strip(".,:;'").lower()
    return w[1:] if len(w) > 3 and w[0] == "ה" else w


def clean_heading(o):
    """כותרת שאפשר להציג ללקוח. PDF אמיתי נותן קטעי משפט במקום כותרות ("ימים מראש לפחות לפני תום תקופת", "הא
    השוכר", "ובכפוף לכך שז"), והם אינם נשאלים. כותרת קריאה: אותיות בלבד (בלי ספרות, קו תחתון, סוגריים, מירכאות או
    לוכסן), עד חמש מילים, מילה ראשונה של שלוש אותיות לפחות שאינה מתחילה ב"ו" החיבור, ולא נגמרת במילת קישור. כותרת
    של מילה אחת צריכה להופיע בשם הנושא. מופיעה לפחות בשני מסמכים כשהנושא אינו מוכר."""
    h = " ".join(str(o.get("heading") or "").split()).strip(" :.-")
    if not h or not HEADING_OK.match(h):
        return None
    w = h.split()
    first = w[0]
    if len(w) > 5 or len(first) < 3 or (first[0] == "ו" and len(first) > 3 and not first.startswith("ו/")) \
            or w[-1].strip(".,:;").lower() in END_WORDS or first.endswith(","):
        return None
    known = bool(o.get("topic")) and o["topic"] != "שונות"
    if len(w) == 1:
        if known and h.isascii() and len(h) >= 6:
            return h          # כותרת באנגלית ("Confidentiality"): שם הנושא מהבנק בעברית
        if not (known and _bare(h) in {_bare(x) for x in re.split(r"[\s,]+", o["topic"])}):
            return None
        return h
    if known:
        return h
    return h if len(h) >= 8 and len(o["with"]) >= 2 else None


def askable_field(f):
    """שדה נתונים שאפשר לשאול עליו ללקוח. שדות המבוא (שמות הצדדים, כתובות, מספרי רישום) הם עובדות העסקה, ואינם
    שאלה בטופס; הקשר שחולץ מ-PDF בלי מילים קריאות (קווים, סוגריים, מירכאות, כתובות מייל) אינו שאלה."""
    if f.get("derivable_from") or f.get("topic") == "מבוא" or f.get("heading") in ("המבוא והצדדים", "Preamble and parties"):
        return False
    ctx = " ".join((f.get("context") or f.get("heading") or "").split())
    words = re.findall(r"[A-Za-zא-ת]{3,}", ctx)
    return len(words) >= 2 and not re.search(r"[_@()\"]", ctx)


def questions(lang, fields, optional, alternatives):
    """טיוטת טופס השאלות: סעיף אופציונלי ונוסח חלופי כשאלת בחירה, ואחריהם שדות שאינם נגזרים מהפרופיל. עד שמונה;
    השאר ברירת מחדל (הערך או הנוסח השכיח), להצגה ולאישור. הניסוח בלשון הלקוח: "להוסיף סעיף בנושא X? מופיע ב-3 מתוך
    4 ההסכמים שלכם", בלי קודים, בלי מילים מהכותרות ובלי DOC. סעיף ליבה (ברוב המסמכים) אינו אופציונלי: נכלל. כותרת
    שאינה קריאה (קטע משפט מ-PDF) אינה נשאלת. ברירת המחדל לפי השכיחות. סעיף ליבה אינו אופציונלי, ולכן לא נשאל בכלל, וכך לא "נשללים" כל הסעיפים."""
    en = lang == "en"
    t = "en" if en else "he"
    yes, no = YES_NO[t]
    n_docs = max([len(o["with"]) + len(o["without"]) for o in optional] or [0])
    who = COUNT_WORDS[t][SOURCE[0]]
    qs, core = [], []
    for o in sorted([x for x in optional if not x.get("playbook_topic")], key=lambda x: -len(x["with"])):
        total = len(o["with"]) + len(o["without"])
        o["core"] = total >= 3 and len(o["with"]) / float(total) >= CORE_SHARE
        head = clean_heading(o)
        o["askable"] = bool(head)
        if not head:
            continue
        if o["core"]:
            core.append((o, head, total))
            continue
        sig = [x for x in o["signals"] if x["kind"] in ("שדה", "טווח סכומים", "סוג הצד שכנגד")]
        qs.append({"id": "Q-" + o["id"], "about": o["id"], "kind": "optional",
                   "text": ("Add a clause on %s? It appears in %d of %d %s.%s" if en else
                            "להוסיף סעיף בנושא %s? מופיע ב-%d מתוך %d %s.%s") % (
                       head, len(o["with"]), total, who, signal_phrase(sig, lang)),
                   "options": [yes, no], "default": yes if len(o["with"]) >= len(o["without"]) else no})
    for a in alternatives:
        if not clean_heading({"heading": a.get("heading"), "topic": a.get("topic"),
                              "with": [d for v in a["variants"] for d in v["documents"]]}):
            a["askable"] = False
            continue
        # תחילת כל נוסח מהמקום שבו הנוסחים נפרדים, כדי שההבדל ייראה באפשרות עצמה
        words = [re.sub(r"\s+", " ", v["text"]).split(" ") for v in a["variants"]]
        k = 0
        while all(len(w) > k for w in words) and len({w[k] for w in words}) == 1:
            k += 1
        k = max(0, k - 3)
        for v, w in zip(a["variants"], words):
            v["_from"] = ("..." if k else "") + " ".join(w[k:])
        qs.append({"id": "Q-" + a["id"], "about": a["id"], "kind": "alternative",
                   "text": ("Which wording do you want for the clause on %s?" if en else
                            "איזה נוסח אתם רוצים לסעיף בנושא %s?") % a["heading"],
                   # האפשרויות הן הנוסחים עצמם, בתחילתם, ולא קודים: הלקוח בוחר לפי מה שכתוב
                   "options": ["\"%s\"%s" % (excerpt(v.pop("_from", v["text"])),
                                              signal_phrase([x for x in (v.get("signals") or [])
                                                             if x["kind"] in ("שדה", "טווח סכומים", "סוג הצד שכנגד")],
                                                            lang))
                               for v in a["variants"]],
                   "option_values": [v["variant"] for v in a["variants"]],
                   "default": max(a["variants"], key=lambda v: len(v["documents"]))["variant"]})
    # נתון של העסקה (שם, סכום, תאריך שונים בכל הסכם): שאלה פתוחה, בלי להציע ערכים של עסקאות אחרות
    per_deal = [f for f in fields if askable_field(f) and f.get("per_deal")]
    shared = [f for f in fields if askable_field(f) and not f.get("per_deal")]
    for f in per_deal + shared:
        label = " ".join((f.get("context") or f.get("heading") or "").split())
        qs.append({"id": "Q-" + f["id"], "about": f["id"], "kind": "data",
                   "text": ("What goes in the agreement for: %s?" if en else "מה לרשום בהסכם הזה: %s?") % label,
                   "options": [] if f.get("per_deal") else [x["value"] for x in f["values"][:4] if x["value"]],
                   "free_text": True, "default": f.get("default")})
    ask, rest = qs[:MAX_QUESTIONS], qs[MAX_QUESTIONS:]
    # נושא שיש עליו עמדה בפלייבוק אינו נשאל: הוא נכלל, והעמדה מהפלייבוק (מוצג לאישור בשורה אחת)
    rest += [{"id": "Q-" + o["id"], "about": o["id"], "kind": "optional", "status": "playbook_topic",
              "text": ("%s: included, you already have a position on it" if en else "%s: נכלל, כבר יש לכם עמדה בנושא")
              % o["heading"], "default": yes} for o in optional if o.get("playbook_topic")]
    rest += [{"id": "Q-" + o["id"], "about": o["id"], "kind": "optional", "status": "core_included",
              "text": ("%s: included, it appears in %d of %d %s" if en else "%s: נכלל, מופיע ב-%d מתוך %d %s")
              % (head, len(o["with"]), total, who), "default": yes} for o, head, total in core]
    # מעבר לשמונה: מה שיש לו ברירת מחדל מוצג לאישור; נתון של עסקה בלי ברירת מחדל נשאר [להשלים]
    return ask, [dict(q, status=q.get("status") or ("default_for_approval" if q.get("default") not in (None, "")
                                                    else "to_complete")) for q in rest]


def main():
    ap = argparse.ArgumentParser(description="מפת השונות בין ההסכמים הקיימים של החברה מאותו סוג ובאותו צד")
    ap.add_argument("--registry", required=True, help="template-registry.json")
    ap.add_argument("--family", required=True, nargs="+",
                    help="משפחת ההסכם: family_id של הפלייבוק, שם המשפחה במרשם, או שם או כינוי שלה (אפשר כמה)")
    ap.add_argument("--playbook", help="playbook-core.json: שם המשפחה והכינויים שלה (family_aliases), ונושאי העמדות. "
                                       "נושא שיש עליו עמדה בפלייבוק אינו נשאל")
    ap.add_argument("--role", help="התפקיד של החברה בהסכם (company_role_code מהפלייבוק)")
    ap.add_argument("--profile", help="פרופיל-לקוח.json: שדות שהפרופיל קובע אינם נשאלים")
    ap.add_argument("--skeleton", help="skeleton.json של המשפחה, כשיש תבנית אב: המשתנים שלו נכנסים כשדות")
    ap.add_argument("--out", required=True)
    ap.add_argument("--force", action="store_true", help="לדרוס מפה קיימת")
    a = ap.parse_args()
    guard_out(a.out, [a.registry, a.profile, a.skeleton, a.playbook], a.force)
    if not os.path.isfile(a.registry):
        print("המרשם לא נמצא: %s" % a.registry)
        sys.exit(2)
    reg = json.load(io.open(a.registry, encoding="utf-8"))
    want = normalize_role(a.role) if a.role else None
    core = {}
    if a.playbook and os.path.isfile(a.playbook):
        try:
            core = json.load(io.open(a.playbook, encoding="utf-8-sig"))
        except (OSError, ValueError):
            core = {}
    # שמות המשפחה: מה שנמסר, ומהפלייבוק family_id, שם המשפחה והכינויים. מסמך מתאים לפי המשפחה במרשם, לפי אחת
    # המשפחות המועמדות שלו, או לפי כינוי בשם הקובץ ובכותרת. כך אותו סוג הסכם שהמרשם פיצל לכמה משפחות נמצא כולו
    names = list(a.family)
    if not want and core.get("company_role_code"):
        want = normalize_role(core.get("company_role_code"))
    for f in core.get("contract_families") or []:
        names += [f.get("contract_family_name")] + list(f.get("family_aliases") or [])
    names += [core.get("family_id"), core.get("family_code")]
    names = [re.sub(r"^fam_", "", str(x)).replace("_", " ") for x in names if x]
    # family_id כמו fam_lease_tenant: גם כל מילה בו בנפרד ("<מילה>"), בלי מילות התפקיד
    role_words = {w for w in re.split(r"[\s_]+", str(core.get("company_role_code") or "").lower()) if w}
    names += [w for n in list(names) for w in n.split() if len(w) > 3 and w.lower() not in role_words and w not in names]

    def fam_ok(d):
        if family_matches(d.get("family"), names) or any(family_matches(c, names) for c in d.get("family_candidates") or []):
            return True
        title = (d.get("file") or "") + " " + (d.get("title") or "")
        return any(len(n) > 2 and word_count(n.lower(), title.lower()) for n in names)

    sel, skipped = [], []
    for d in reg.get("documents") or []:
        if not fam_ok(d):
            continue
        if d.get("doc_class") in ("redline",) and not d.get("user_approved"):
            skipped.append((d["file"], "טיוטה עם עקוב אחר שינויים, לא נוסח סופי"))
            continue
        if d.get("paper") == "counterparty":
            skipped.append((d["file"], "הנייר של הצד השני בעסקה"))
            continue
        role = d.get("company_role") or (d.get("company_role_candidates") or [None])[0]
        if want and role and normalize_role(role) != want:
            skipped.append((d["file"], "נכתב בצד ההפוך"))
            continue      # נכתב בצד ההפוך: אינו מקור לשונות של הצד שלנו
        d = dict(d)
        d["paper"] = d.get("paper") or ("company" if d.get("company_paper") or d.get("user_approved") else "third_party")
        sel.append(d)
    # קריאה, ובדיקה שהטקסט קריא: מסמך שאינו נקרא אינו נכנס למפה, ונאמר למה
    readable, paras_of = [], {}
    for d in sel:
        paras, why = read_paras(d)
        why = why or unreadable("\n".join(paras))
        if why:
            skipped.append((d["file"], why))
            continue
        readable.append(d)
        paras_of[id(d)] = paras
    sel = readable
    for f, why in skipped:
        print("  לא נכלל: %s (%s)" % (f, why))
    if len(sel) < 2:
        print("נמצאו %d הסכמים קריאים מהסוג ומהצד הזה. מפת שונות צריכה לפחות שניים; עם הסכם אחד עובדים לפי השלד "
              "(template-flow.md, פרקים 1 עד 4).\nFound %d readable agreements of this type and side. A variance map "
              "needs at least two; with one agreement, work from the skeleton." % (len(sel), len(sel)))
        sys.exit(2)
    profile = json.load(io.open(a.profile, encoding="utf-8")) if a.profile and os.path.isfile(a.profile) else {}
    skeleton = json.load(io.open(a.skeleton, encoding="utf-8")) if a.skeleton and os.path.isfile(a.skeleton) else None
    docs = [read_doc(d, paras_of[id(d)]) for d in sel]
    papers = {d["paper"] for d in sel}
    SOURCE[0] = "company" if papers == {"company"} or "company" in papers else (
        "published" if "published" in papers else "third_party")
    try:
        from derive_deal_defaults import derive
        defaults = derive([(d["file"], d.get("family"), x["text"], d.get("company_role")) for d, x in zip(sel, docs)])
    except Exception:  # noqa: BLE001  ברירות המחדל הן תוספת; בלעדיהן המפה נבנית
        defaults = []
    lang, constants, fields, optional, alternatives = build(sel, docs, profile, skeleton, defaults)
    # מסלול המחקר: הסכמים שפורסמו (paper: published, research-flow.md) אינם נוסח של החברה. כל אפשרות שנלמדה מהם
    # היא המלצה של Areo, ומסומנת בטיוטה בתווית הקבועה
    # נושא שיש עליו עמדה בפלייבוק: לא נשאל, נכלל
    pb_topics = []
    for c in core.get("clauses") or core.get("rules") or []:
        if isinstance(c, dict):
            pb_topics += [str(c.get("title") or ""), str(c.get("clause_issue") or "")] + [str(x) for x in c.get("topic_ids") or []]
    pb_topics = [x.lower() for x in pb_topics if len(x) > 2]
    for o in optional:
        h = (o.get("heading") or "").lower()
        tp = (o.get("topic") or "").lower()
        if any(word_count(h, x) or word_count(x, h) or (tp and (tp in x or x in tp)) for x in pb_topics if h):
            o["playbook_topic"] = True
    # נוסחים של צד שלישי והסכמים שפורסמו אינם נוסח של החברה: כל אפשרות שנלמדה מהם היא המלצה של Areo
    if any(d.get("paper") in ("published", "third_party") for d in sel) and "company" not in papers:
        label = "Areo proposal (not based on the client's documents)" if lang == "en" else             "הצעת Areo (לא מבוסס על מסמכי הלקוח)"
        for it in optional + alternatives:
            it["areo_proposal"], it["label"] = True, label
    qs, rest = questions(lang, fields, optional, alternatives)
    for f in fields:
        f["by_doc"] = {"DOC-%d" % (i + 1): v for i, v in f["by_doc"].items()}
    out = {
        "generated_at": date.today().isoformat(),
        "family": a.family[0], "family_names": names, "company_role": want or a.role, "language": lang,
        "not_included": [{"file": f, "why": w} for f, w in skipped],
        "documents": [{"id": "DOC-%d" % (i + 1), "file": d["file"], "doc_class": d.get("doc_class"),
                       "paper": d["paper"],
                       "title": x["title"][:120]} for i, (d, x) in enumerate(zip(sel, docs))],
        "constants": constants, "data_fields": fields, "optional_clauses": optional,
        "alternative_wordings": alternatives, "questions": qs, "defaults_for_approval": rest,
    }
    d = os.path.dirname(os.path.abspath(a.out))
    if d and not os.path.isdir(d):
        os.makedirs(d)
    io.open(a.out, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=2))
    print("מפת השונות: %s" % a.out)
    print("הסכמים: %d · קבועים: %d · שדות נתונים: %d · סעיפים אופציונליים: %d · נוסחים חלופיים: %d · שאלות: %d (+%d "
          "ברירות מחדל לאישור)" % (len(sel), len(constants), len(fields), len(optional), len(alternatives), len(qs),
                                   len(rest)))


if __name__ == "__main__":
    main()
