#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""השוואת סבב: מה קרה לכל הצעה שלנו, ומה הם שינו בשקט.

`n7b-round-steps.md`, שלב א: **ההשוואה היא מילה במילה,
טקסט מול טקסט, ולא רשימת שינויים מול רשימת שינויים.** רשימת שינויים
מול רשימת שינויים מפספסת את הממצא החשוב ביותר, כי צד שכנגד שכיבה את
המעקב, או ש"קיבל" אצלו שינויים לפני השליחה, אינו מופיע באף רשימה.

כל הבדל מסווג לאחת הקבוצות של `last_round_changes`
(`n8-state-schema.md`):

| סיווג | מה קרה |
|---|---|
| `our_accepted` | הסימון שלנו נעלם, והנוסח שהצענו נשאר |
| `our_accepted_partial` | בפסקה כמה סימונים שלנו: חלקם התקבלו וחלקם נדחו (או עוד פתוחים). לכל סימון הגורל שלו |
| `our_rejected` | הסימון שלנו נעלם, והנוסח חזר למה שהיה לפניו |
| `their_rejected_our_insert` | הם מחקו בעקוב אחר שינויים את מה שהוספנו: דחייה של ההצעה שלנו, במעקב. סיווג אחד |
| `our_open` | ההצעה שלנו עוד מסומנת: לא קיבלו ולא דחו |
| `their_tracked` | שינוי חדש שלהם, במעקב |
| `their_silent` | הנוסח השתנה בלי סימון. הממצא החשוב ביותר |

**שלוש ההטלות שעליהן הכול נשען.** קובץ Word עם סימוני מעקב אינו טקסט
אחד אלא כמה, לפי מי מקבלים ומי דוחים. לכל פסקה בקובץ שחזר נגזרות:

* **מה הם פתחו בו** - מקבלים את הסימונים שלנו ודוחים את שלהם. זה אמור
  להיות, מילה במילה, צירוף של מה ששלחנו: כל סימון שלנו התקבל או נדחה.
  כל פער שאינו צירוף כזה הוא שינוי בלי מעקב.
* **מה הנוסח עכשיו** - מקבלים הכול.
* **האם הסימון שלנו עוד שם** - אם כן, ההצעה פתוחה ואין לגעת בה.

**גורל כל סימון בנפרד** (בדיקה עצמאית S1c, H4, 28.10.2026): פסקה עם כמה סימונים שלנו,
שהצד שכנגד קיבל חלק מהם ודחה חלק, אינה שינוי שקט. הכלי מחפש את צירוף הקבלות והדחיות
שנותן בדיוק את "מה הם פתחו בו", ומדווח לכל סימון: התקבל, נדחה או עדיין פתוח.

**ההצמדה היא לפי סעיף ונוסח, ולא לפי מיקום הפסקה**, כדי שפסקה שנוספה
לא תזיז את כל ההשוואה: קודם לפי מספר הסעיף שבתחילת הפסקה, ומה שנשאר
לפי קרבת נוסח, גם לנוסח שהיה לפני ההצעה שלנו (פסקה שכתבנו מחדש ונדחתה).

**השמות שלנו.** `--profile` קורא מהפרופיל את כל השמות של עורך הדין: lawyer_name,
lawyer_name_en ו-lawyer_aliases (כולל החותם המלא, "עו"ד <שם>, <תפקיד> (<English Name>)").
`--author` אפשר להעביר כמה פעמים. סימון של כל אחד מהשמות האלה הוא שלנו.

**בועות.** הכלי קורא את הבועות של שני הקבצים, כולל commentsExtended ו-paraIdParent,
ומחזיר את השרשורים: תשובה של הצד שכנגד לבועה שלנו, בועה חדשה שלהם, ובועה שסומנה
"בוצע". לכל סיווג נרשמים השרשורים שבאותה פסקה.

**מפת הפסקאות** (`para_map`, S1d-R2): לכל פסקה שהוצמדה, גם בלי שינוי: sent_para, base_para ו-received_para.
base_para הוא מספר הפסקה בטיוטה של הסבב הקודם, כפי שהצד השני ראה אותה: הסימונים הפתוחים שלנו מסבבים קודמים
(`docx_tracked.prior_revisions`) הם חלק ממנה, ורק פסקה שכולה הוספה שלנו מהסבב הקודם אינה נספרת (S1e-R3: הוספה פתוחה
שלנו מסבב 1, 18.4, הזיזה את כל המפה בפסקה אחת). הסימונים הקודמים נלקחים מהטיוטה שהתקבלה באותו סבב, וכשאינה בתיקייה,
מהקבצים שנשלחו בסבבים שלפניו (`prior_keys`). `base_paragraphs` נותן את אותה תצוגה גם ל-`round_tools.py carry`.

**עריכה של עורך הדין לפני המשלוח** (S1e-R3): `edits_before_sending` משווה את העותק שהופק לקובץ שנשלח בפועל, פסקה
מול פסקה ובועה מול בועה, ולכל הבדל: הפסקה בטיוטה של אותו סבב, הנוסח שהופק והנוסח שנשלח (`negotiation_state.py sent`
רושם אותם ב-`lawyer_overrides`). כשההשוואה היא מול קובץ כזה, השורות הראשונות של הסיכום אומרות זאת בשורה אחת.

**מונח שהגדרתו נמחקה** (פער 12): מונח מוגדר שהוגדר במה ששלחנו, ואינו מוגדר עוד
בנוסח שחזר אבל עדיין משמש בו, נרשם ב-`orphaned_terms` ונשאל במנת השאלות.

**בסיס ההשוואה** (H5): `--sent` הוא מה שנשלח בפועל. בלעדיו, עם `--deal`, הכלי לוקח את
הרשומה האחרונה ב-`meta.sent_documents`; כשאין, את קובץ העבודה האחרון שהופק, ומסמן
"בסיס משוער" (`base: assumed`). `--assumed-base` מסמן כך גם `--sent` שהמשתמש לא אישר.

    python "AREO_RT/skills/contract-negotiation-orchestrator/scripts/compare_rounds.py" --sent <מה שהחברה שלחה>.docx \\
        --received <מה שחזר>.docx --profile Areo-נתונים/פרופיל-לקוח.json \\
        [--deal Areo-נתונים/transactions/<id>] \\
        --out Areo-נתונים/transactions/<id>/round-compare.json

קריאת ה-DOCX היא `areolegal/lib/common/docx_tracked.py` מקוד הייחוס.
ההטלות לפי מחבר והסיווג הם כאן. קוד יציאה: **0** תקין, **2** קלט חסר, **1** נתיב פלט שסורב.
"""
import copy
import datetime as _dt
import difflib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # גם ב-python -I, שאינו מוסיף את תיקיית הסקריפט
import areo_lib  # noqa: F401  מוסיף את areolegal/lib לנתיב הייבוא

from common.cli import OutputRefused, guard_out, load_docx_or_explain, no_bytecode, parser  # noqa: E402
import common.docx_tracked as dt  # noqa: E402
import lawyer  # noqa: E402
import threads as TH  # noqa: E402
from orchestrator import state_builder as SB  # noqa: E402

try:  # אותם דפוסי הגדרה כמו בדיקות התוכן של השער
    from content_checks import DEF_PATTERNS  # noqa: E402
except Exception:  # noqa: BLE001  בלי בדיקות התוכן: אותם דפוסים, מועתקים
    DEF_PATTERNS = [re.compile(r"\(\s*(?:להלן:?\s*|the\s+|hereinafter\s+)?[\"״“]([^\"״”]{2,50})[\"״”]"
                               r"(?:\s*(?:או|or)\s*[\"״“]([^\"״”]{2,50})[\"״”])?\s*\)"),
                    re.compile(r"\(להלן:?\s*[\"״“]([^\"״”]{2,50})[\"״”]"),
                    re.compile(r"[\"״“]([^\"״”]{2,50})[\"״”]\s*(?:-|פירושו|פירושה|משמעו|משמעה|יהיה פירושו)"),
                    re.compile(r"[\"“]([A-Z][^\"”]{1,50})[\"”]\s+(?:means|shall mean|has the meaning)"),
                    re.compile(r"\((?:the|hereinafter)?\s*[\"“]([A-Z][^\"”]{1,50})[\"”]\)")]

W = dt.W
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
BIDI = re.compile(r"[‎‏‪-‮]")
# מספר סעיף בתחילת פסקה: "4.", "4.1", "4.1.2", וגם "סעיף 4.1"
CLAUSE = re.compile(r"^\s*(?:סעיף\s+)?(\d+(?:\.\d+)*)\s*[.)\s]")
# מספור נוסף, כמו CLAUSE_RE של בונה הפלייבוק (AREO_RT/skills/contract-playbook-builder/scripts/extract_corpus.py), ובאותו נוסח: (a), (iv), A., IV.,
# Section 5.2, Clause 7, Article IV, (1), ו-(א) או א. בעברית. נבדק רק כש-CLAUSE לא מצא, כדי שתוצאה קיימת לא תשתנה.
# "Section 5.2 of the Agreement" הוא הפניה ולא סעיף, ואות סופית אינה מספור
CLAUSE_EXTRA = re.compile(
    r"^\s*(?:"
    r"(?i:section|clause|article|sec\.|art\.)\s*(\d+(?:\.\d+)*|[IVX]{1,6}|[A-Z])\b[.):]?"
    r"(?=\s*$|\s*[\-:.]|\s+[A-Z\"“(\[]|\s+[א-ת])"
    r"|\(?(\d+(?:\.\d+)+)\)?[.):]?"
    r"|\(?(\d+)\)?[.):]"
    r")(?:\s+|$)"
    r"|^\s*\(?(?:([אבגדהוזחטיכלמנסעפצקרשת])\)?[.):]|([ivx]{1,6}|[IVX]{1,6}|[A-Za-z])\)?[.)])\s+")
# מספור שחוזר בכל סעיף ((a), (iv), א.) אינו מזהה: הוא נרשם ב-clause, אבל ההצמדה לפיו היא לפי קרבת נוסח
# בלבד, כי פסקה (a) שנוספה מזיזה את כל האותיות שאחריה
REPEATING = re.compile(r"^(?:[A-Za-z]|[ivx]{1,6}|[IVX]{1,6}|[א-ת])$")
# קרבת נוסח שמעליה שתי פסקאות הן אותה פסקה שהשתנתה, ולא שתי פסקאות שונות
NEAR = 0.72
KINDS = ("their_silent", "their_rejected_our_insert", "their_tracked", "our_accepted", "our_accepted_partial",
         "our_rejected", "our_open")


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[‎‏‪-‮]", "", s or "")).strip()


def clause_of(text):
    t = norm(text)
    m = CLAUSE.match(t)
    if m:
        return m.group(1)
    m = CLAUSE_EXTRA.match(t)
    return next((g for g in m.groups() if g), None) if m else None


def project(para, accept_authors=None, reject_authors=None, accept_rest=True):
    """הטקסט של הפסקה כשמקבלים מחברים מסוימים ודוחים אחרים.

    accept_authors: מחברים שהסימון שלהם מתקבל (ins נשאר, del יוצא).
    reject_authors: מחברים שהסימון שלהם נדחה (ins יוצא, del חוזר).
    accept_rest:    מה עושים למחבר שאינו באף רשימה.
    """
    p = copy.deepcopy(para)
    acc = set(accept_authors or ())
    rej = set(reject_authors or ())

    def keeps(el):
        a = el.get(W + "author")
        if a in acc:
            return True
        if a in rej:
            return False
        return accept_rest

    for el in list(p.iter(W + "ins")):
        if el.getparent() is None:
            continue
        par = el.getparent()
        if keeps(el):
            for ch in list(el):
                par.insert(list(par).index(el), ch)
        par.remove(el)
    for el in list(p.iter(W + "del")):
        if el.getparent() is None:
            continue
        par = el.getparent()
        if keeps(el):
            par.remove(el)
            continue
        for ch in list(el):
            for node in ch.iter(W + "delText"):
                node.tag = W + "t"
                node.set(XML_SPACE, "preserve")
            par.insert(list(par).index(el), ch)
        par.remove(el)
    return dt.para_text(p)


def _revs(p):
    """סימוני המעקב בטקסט הפסקה (ins ו-del שאינם על סימן הפסקה), לפי הסדר."""
    return [el for el in p.iter(W + "ins", W + "del")
            if el.getparent() is not None and dt.local(el.getparent().tag) != "rPr"]


def _full_text(el):
    """כל הטקסט שבתוך סימון, כולל טקסט שנמחק בתוכו (מחיקה שלהם בתוך הוספה שלנו)."""
    out = []
    for n in el.iter(W + "t", W + "delText", W + "tab"):
        out.append("\t" if dt.local(n.tag) == "tab" else (n.text or ""))
    return "".join(out)


def marked_by(para, ours):
    return any(el.get(W + "author") in ours for el in _revs(para))


def marked_by_others(para, ours):
    return any(el.get(W + "author") not in ours for el in _revs(para))


def _innermost(node, p):
    for a in node.iterancestors():
        if a is p:
            return None
        if a.tag in (W + "ins", W + "del") and a.getparent() is not None and dt.local(a.getparent().tag) != "rPr":
            return a
    return None


def mark_fates(para, target, revs):
    """הצירוף של קבלה או דחייה לכל סימון בפסקה ששלחנו, שנותן בדיוק את target ("מה הם פתחו בו").
    revs: _revs(para), שמוחזק בידי הקורא כל עוד התוצאה בשימוש (המפתח הוא המיקום ברשימה, ולא id של אובייקט lxml).
    מחזיר {מיקום הסימון ב-revs: 'accepted' | 'rejected'}, או None כשאין צירוף כזה (שינוי בלי מעקב).
    חיפוש לעומק לפי קטעים, עם גיזום לפי תחילית: ליניארי כמעט תמיד, גם בפסקה עם עשרות סימונים."""
    segs = []
    for n, _anc in dt._text_nodes(para):
        m = _innermost(n, para)
        t = BIDI.sub("", dt._node_text(n))
        if segs and segs[-1][0] is m:
            segs[-1][1] += t
        else:
            segs.append([m, t])
    target = BIDI.sub("", target or "")
    pos_of = {id(e): k for k, e in enumerate(revs)}
    stack, seen = [(0, 0, ())], set()
    while stack:
        i, pos, ch = stack.pop()
        if (i, pos, ch) in seen:
            continue
        seen.add((i, pos, ch))
        if i == len(segs):
            if pos == len(target):
                return {pos_of[k]: v for k, v in ch if k in pos_of}
            continue
        m, t = segs[i]
        if m is None:
            if target.startswith(t, pos):
                stack.append((i + 1, pos + len(t), ch))
            continue
        chd = dict(ch)
        # נדחף אחרון נבדק ראשון: קודם "התקבל"
        for c in ([chd[id(m)]] if id(m) in chd else ["rejected", "accepted"]):
            include = (c == "accepted") == (dt.local(m.tag) == "ins")
            if include and not target.startswith(t, pos):
                continue
            nch = ch if id(m) in chd else tuple(sorted(ch + ((id(m), c),)))
            stack.append((i + 1, pos + (len(t) if include else 0), nch))
    return None


def pair_up(a, b, a_alt=None):
    """מצמיד פסקאות: קודם לפי מספר סעיף, והשאר לפי קרבת נוסח. a_alt: נוסח חלופי לכל פסקה ב-a (הנוסח
    שלפני ההצעה שלנו), כדי שפסקה שכתבנו מחדש והם דחו תוצמד לנוסח שחזר.

    מחזיר (זוגות, רק_ב-a, רק_ב-b). פסקה בלי מספר סעיף שאין לה מקבילה
    קרובה נשארת לבד, וזו התשובה הנכונה: פסקה שנוספה או שנמחקה.
    """
    a_alt = a_alt or a
    pairs, left, right = [], list(range(len(a))), list(range(len(b)))
    by_clause = {}
    for j in right:
        c = clause_of(b[j])
        if c:
            by_clause.setdefault(c, []).append(j)
    for i in list(left):
        c = clause_of(a[i]) or clause_of(a_alt[i])
        if c and by_clause.get(c) and not REPEATING.match(c):
            j = by_clause[c].pop(0)
            pairs.append((i, j))
            left.remove(i)
            right.remove(j)
    for i in list(left):
        best, score = None, 0.0
        for j in right:
            r = difflib.SequenceMatcher(None, norm(a[i]), norm(b[j])).ratio()
            if a_alt[i] != a[i]:
                r = max(r, difflib.SequenceMatcher(None, norm(a_alt[i]), norm(b[j])).ratio())
            if r > score:
                best, score = j, r
        if best is not None and score >= NEAR:
            pairs.append((i, best))
            left.remove(i)
            right.remove(best)
    # פסקה שנכתבה מחדש כולה (למשל הוחזרה לנוסח ישן שאינו קרוב למה ששלחנו) ושתי שכנותיה הוצמדו: זו אותה פסקה
    # שהשתנתה, ולא מחיקה ועוד הוספה. בלי ההצמדה הזו שינוי שקט אחד נרשם פעמיים (פסקה שנעלמה ופסקה שנוספה)
    paired = dict(pairs)
    for i in list(left):
        prev_j = paired.get(i - 1)
        next_j = paired.get(i + 1)
        j = None
        if prev_j is not None and next_j is not None and next_j - prev_j == 2:
            j = prev_j + 1
        elif prev_j is not None and i == len(a) - 1 and prev_j + 1 == len(b) - 1:
            j = prev_j + 1
        elif next_j is not None and i == 0 and next_j == 1:
            j = 0
        if j is not None and j in right and norm(a[i]) and norm(b[j]):
            pairs.append((i, j))
            paired[i] = j
            left.remove(i)
            right.remove(j)
    return sorted(pairs), left, right


def authors_of(a):
    """כל השמות שלנו: --author (כמה פעמים), והשמות שבפרופיל (lawyer_name, lawyer_name_en, lawyer_aliases)."""
    names = list(a.author or [])
    if a.profile:
        with open(a.profile, encoding="utf-8") as fh:
            prof = lawyer.lawyer_view(json.load(fh))
        names += [prof.get("lawyer_name"), prof.get("lawyer_name_en")] + list(prof.get("lawyer_aliases") or [])
    out = []
    for n in names:
        if n and n.strip() and n.strip() not in out:
            out.append(n.strip())
    return out


def resolve_sent(a):
    """(הקובץ שנשלח, בסיס). --sent כמו שהוא; בלעדיו, מקובץ המצב: הרשומה האחרונה ב-sent_documents, ואחריה
    קובץ העבודה (או העותק למשלוח) האחרון שהופק, כ"בסיס משוער"."""
    if a.sent:
        return a.sent, ("assumed" if a.assumed_base else "sent")
    path = os.path.join(a.deal or "", "negotiation_state.json")
    if not a.deal or not os.path.exists(path):
        return None, None
    with open(path, encoding="utf-8") as fh:
        st = json.load(fh)
    sent = sorted((st.get("meta") or {}).get("sent_documents") or [], key=lambda d: d.get("round") or 0)
    if sent:
        rec = sent[-1]
        f = rec.get("file_name") or rec.get("path") or ""
        f = f if os.path.isabs(f) else os.path.join(a.deal, f)
        return f, ("assumed" if rec.get("basis") == "assumed_last_work" else "sent")
    for kind in ("send", "work"):
        docs = [d for d in st.get("produced_documents") or [] if d.get("kind") == kind]
        if docs:
            f = docs[-1].get("path") or ""
            return (f if os.path.isabs(f) else os.path.join(a.deal, f)), "assumed"
    return None, None


def snippet(a, b, width=150):
    """הקטע שבו שני נוסחים נבדלים, לשורה בסיכום: מעט לפני ההבדל הראשון, עד סוף ההבדל."""
    a, b = norm(a), norm(b)
    k = 0
    while k < min(len(a), len(b)) and a[k] == b[k]:
        k += 1
    e = 0
    while e < min(len(a), len(b)) - k and a[len(a) - 1 - e] == b[len(b) - 1 - e]:
        e += 1
    start = max(0, k - 40)
    cut = lambda s: ("…" if start else "") + s[start:min(len(s) - e + 20, start + width)] + (  # noqa: E731
        "…" if len(s) - e + 20 < len(s) else "")
    return cut(a), cut(b)


def defined_terms(paras):
    out = {}
    for i, t in enumerate(paras):
        for rx in DEF_PATTERNS:
            for m in rx.finditer(t or ""):
                for g in m.groups():
                    if g:
                        out.setdefault(g.strip(), i)
    return out


def orphaned_terms(proposed, now):
    """מונח שהוגדר במה ששלחנו, ואינו מוגדר עוד בנוסח שחזר, אבל עדיין משמש בו (פער 12)."""
    before, after = defined_terms(proposed), defined_terms(now)
    out = []
    for term, at in before.items():
        if term in after:
            continue
        rx = re.compile(r"(?<![\w֐-׿])" + re.escape(term) + r"(?![\w֐-׿])")
        used = [j for j, t in enumerate(now) if rx.search(t or "")]
        if used:
            out.append({"term": term, "defined_in": clause_of(proposed[at]) or "", "defined_text": proposed[at][:300],
                        "used_in": [clause_of(now[j]) or "" for j in used], "used_paras": used,
                        "note": "ההגדרה נמחקה בנוסח שחזר, והמונח עדיין משמש. שאלה במנת השאלות: להחזיר את ההגדרה "
                                "בעקוב אחר שינויים, או לתקן את הסעיף שמשתמש בו"})
    return out


def thread_view(sent_path, recv_path, ours, now):
    """השרשורים בקובץ שחזר. בועה "חדשה" היא בועה שאינה בקובץ ששלחנו (לפי מחבר, תאריך ונוסח)."""
    try:
        sent_c, recv_c = TH.read_threads(sent_path), TH.read_threads(recv_path)
    except Exception as exc:  # noqa: BLE001  קובץ בלי בועות תקינות: ההשוואה רצה בלי שרשורים
        print("הבועות לא נקראו (%s). ההשוואה רצה בלי שרשורים" % exc)
        return []
    known = {(c["author"], c["date"], norm(c["text"])) for c in sent_c}
    by_root = {}
    for c in recv_c:
        by_root.setdefault(c["root_id"], []).append(c)
    out = []
    for rid, entries in by_root.items():
        root = next((c for c in entries if c["id"] == rid), entries[0])
        rows = [{"id": c["id"], "author": c["author"], "date": c["date"], "text": c["text"][:600],
                 "ours": c["author"] in ours, "new": (c["author"], c["date"], norm(c["text"])) not in known,
                 "done": c["done"]} for c in sorted(entries, key=lambda c: (c["id"] != rid, c["date"] or ""))]
        para = root.get("para")
        out.append({"root_id": rid, "root_author": root["author"], "root_ours": root["author"] in ours,
                    "para": para, "clause": clause_of(now[para]) if isinstance(para, int) and para < len(now) else None,
                    "done": root["done"], "entries": rows,
                    "their_reply_to_ours": root["author"] in ours and any(r["new"] and not r["ours"] for r in rows),
                    "their_new_thread": root["author"] not in ours and rows[0]["new"],
                    "last_is_theirs": not rows[-1]["ours"]})
    return out


def _state(deal):
    path = os.path.join(deal or "", "negotiation_state.json")
    if not deal or not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _sha(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _deal_path(deal, f):
    return f if not f or os.path.isabs(f) else os.path.join(deal, f)


def sent_round(st, sent_path):
    """הסבב שבו נשלח הקובץ (לפי טביעת האצבע ב-sent_documents), ובלעדיו הסבב שבקובץ המצב."""
    meta = (st or {}).get("meta") or {}
    try:
        sha = _sha(sent_path)
    except OSError:
        sha = None
    rec = next((d for d in meta.get("sent_documents") or () if isinstance(d, dict) and sha
                and d.get("sha256") == sha and str(d.get("round") or "").isdigit()), None)
    return int(rec["round"]) if rec else int(meta.get("round_number") or 0)


def prior_keys(sent_path, ours, deal=None, round_number=None):
    """הסימונים הפתוחים שלנו (revision_key) שכבר היו בטיוטה שהתקבלה בסבב שבו נשלח הקובץ: הצעות שלנו מסבבים
    קודמים, שהצד השני לא קיבל ולא דחה, והן חלק מהטיוטה שהוא ראה (docx_tracked.prior_revisions). כשהטיוטה של אותו סבב
    אינה בתיקייה: כל סימון שלנו שכבר היה בקובץ שנשלח בסבב קודם (sent_documents). בלי קובץ מצב: קבוצה ריקה."""
    st = _state(deal)
    if not st:
        return set()
    names = {n for n in ours or () if n}
    rnd = int(round_number or sent_round(st, sent_path))
    meta = st.get("meta") or {}
    rec = next((d for d in meta.get("received_documents") or () if isinstance(d, dict)
                and str(d.get("round")) == str(rnd)), None)
    p = _deal_path(deal, (rec or {}).get("file_name"))
    if p and os.path.exists(p):
        try:
            return dt.prior_revisions(dt.document_root(p), names)
        except Exception:  # noqa: BLE001  טיוטה שאינה נקראת: לפי הקבצים שנשלחו
            pass
    out = set()
    for d in meta.get("sent_documents") or ():
        if not isinstance(d, dict) or int(d.get("round") or 0) >= rnd:
            continue
        p = _deal_path(deal, d.get("file_name"))
        if p and os.path.exists(p) and os.path.abspath(p) != os.path.abspath(sent_path):
            try:
                root = dt.document_root(p)
            except Exception:  # noqa: BLE001  קובץ פגום: הסימונים ממנו אינם זמינים
                continue
            out |= {dt.revision_key(e) for e in root.iter(W + "ins", W + "del") if e.get(W + "author") in names}
    return out


def base_paragraphs(sent_paras, ours, prior=(), before=None):
    """(base_idx, base_texts): לכל פסקה בקובץ ששלחנו, מספר הפסקה בטיוטה שממנה הופק (None לפסקה שכולה הוספה שלנו
    מהסבב הזה), והטקסט של כל פסקה בטיוטה ההיא: השינויים שלנו מהסבב דחויים, והסימונים הפתוחים שלנו מסבבים קודמים
    (prior) ושל הצד השני נשארים כמו בטיוטה (docx_tracked._reject_ours_para). before: הנוסח אחרי דחיית כל השינויים
    שלנו, ומשמש כשאין סימונים קודמים (כמו קודם)."""
    prior = set(prior or ())
    names = set(ours or ())

    def now_ours(e):
        return e is not None and e.get(W + "author") in names and dt.revision_key(e) not in prior

    texts = [before[i] if (before is not None and not prior) else dt._reject_ours_para(p, now_ours)
             for i, p in enumerate(sent_paras)]
    idx, k = [], 0
    for p, t in zip(sent_paras, texts):
        new = now_ours(p.find(W + "pPr/" + W + "rPr/" + W + "ins")) and not norm(t)
        idx.append(None if new else k)
        k += 0 if new else 1
    return idx, [t for t, i in zip(texts, idx) if i is not None]


def _pair_blocks(a, b):
    """(זוגות, רק ב-a, רק ב-b, מפה b->a): פסקאות שהשתנו בין שתי רשימות. בתוך בלוק שהוחלף, קודם ההתאמה הקרובה
    ביותר, ומה שנשאר בבלוק לפי הסדר (פסקה שנוסחה מחדש כמעט כולה היא עדיין אותה פסקה)."""
    na, nb = [norm(x) for x in a], [norm(x) for x in b]
    pairs, only_a, only_b, b2a = [], [], [], {}
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, na, nb, autojunk=False).get_opcodes():
        if tag == "equal":
            b2a.update({j1 + k: i1 + k for k in range(i2 - i1)})
            continue
        used, left = set(), []
        for i in range(i1, i2):
            cand = [j for j in range(j1, j2) if j not in used]
            best = max(cand, key=lambda j: difflib.SequenceMatcher(None, na[i], nb[j]).ratio(), default=None)
            if best is not None and difflib.SequenceMatcher(None, na[i], nb[best]).ratio() >= 0.5:
                pairs.append((i, best))
                used.add(best)
            else:
                left.append(i)
        rest = [j for j in range(j1, j2) if j not in used]
        for i, j in zip([i for i in left if na[i]], [j for j in rest if nb[j]]):
            pairs.append((i, j))
            used.add(j)
            left.remove(i)
        only_a += left
        only_b += [j for j in range(j1, j2) if j not in used]
    b2a.update({j: i for i, j in pairs})
    return sorted(pairs), only_a, only_b, b2a


def edits_before_sending(produced_path, sent_path, ours, prior=()):
    """ההבדלים בין העותק שהופק לקובץ שנשלח בפועל (S1e-R3). לפסקאות: {kind (text_edited, text_deleted, text_added),
    para (בטיוטה של אותו סבב), after_para, sent_para, produced_text, sent_text}, בנוסח "קבל הכול" של כל פסקה. לבועות
    שלנו: {kind (external_comment_rewritten, external_comment_deleted, external_comment_added), para, author,
    produced_text, sent_text}, לפי מחבר ותאריך (Word שומר אותם כשעורך הדין מתקן את הנוסח). בועה פנימית אינה נבדקת."""
    p_root, s_root = dt.document_root(produced_path), dt.document_root(sent_path)
    p_paras, s_paras = dt.body_paragraphs(p_root), dt.body_paragraphs(s_root)
    p_txt, s_txt = [dt.para_text(p) for p in p_paras], [dt.para_text(p) for p in s_paras]
    p_base, _ = base_paragraphs(p_paras, ours, prior)

    def base_of(i):
        if i is None or i >= len(p_base):
            return None, None
        if p_base[i] is not None:
            return p_base[i], None
        return None, next((p_base[x] for x in range(i - 1, -1, -1) if p_base[x] is not None), None)

    out = []
    pairs, only_p, only_s, s2p = _pair_blocks(p_txt, s_txt)
    for i, j in pairs:
        b, after = base_of(i)
        out.append({"kind": "text_edited", "para": b, "after_para": after, "sent_para": j,
                    "produced_text": p_txt[i], "sent_text": s_txt[j]})
    for i in only_p:
        if norm(p_txt[i]):
            b, after = base_of(i)
            out.append({"kind": "text_deleted", "para": b, "after_para": after, "sent_para": None,
                        "produced_text": p_txt[i], "sent_text": ""})
    for j in only_s:
        if norm(s_txt[j]):
            prev_i = max((i for i, jj in pairs if jj < j), default=None)
            b, after = base_of(prev_i)
            out.append({"kind": "text_added", "para": None, "after_para": b if b is not None else after,
                        "sent_para": j, "produced_text": "", "sent_text": s_txt[j]})
    names = set(ours or ())
    pc = [c for c in dt.read_comments(produced_path) if c["author"] in names]
    sc = [c for c in dt.read_comments(sent_path) if c["author"] in names]
    p_at, s_at = dt.comment_paragraphs(p_root), dt.comment_paragraphs(s_root)
    for c in pc:
        c["base"] = base_of(p_at.get(c["id"]))[0]
    for x in sc:
        x["base"] = base_of(s2p.get(s_at.get(x["id"])))[0]
    left, gone = list(sc), []
    for c in pc:
        same = next((x for x in left if norm(x["text"]) == norm(c["text"]) and (
            x["date"] == c["date"] or x["base"] == c["base"])), None)
        if same is not None:
            left.remove(same)
        else:
            gone.append(c)
    for c in gone:
        # אותה בועה בנוסח אחר: אותו מחבר ותאריך (Word שומר אותם), ובלעדיהם אותה פסקה
        alt = next((x for x in left if x["date"] and x["date"] == c["date"]), None) or \
            next((x for x in left if c["base"] is not None and x["base"] == c["base"]), None)
        if alt is not None:
            left.remove(alt)
            out.append({"kind": "external_comment_rewritten", "para": c["base"], "author": c["author"],
                        "produced_text": c["text"], "sent_text": alt["text"]})
        else:
            out.append({"kind": "external_comment_deleted", "para": c["base"], "author": c["author"],
                        "produced_text": c["text"], "sent_text": ""})
    for x in left:
        out.append({"kind": "external_comment_added", "para": x["base"], "author": x["author"], "produced_text": "",
                    "sent_text": x["text"]})
    return out


def sent_edits_line(sent_path, deal):
    """שורה לסיכום, כשההשוואה היא מול קובץ שעורך הדין ערך לפני המשלוח: כמה הבדלים מול העותק שהופק, ובאילו סעיפים."""
    st = _state(deal)
    if not st:
        return None
    try:
        sha = _sha(sent_path)
    except OSError:
        return None
    rec = next((d for d in (st.get("meta") or {}).get("sent_documents") or () if isinstance(d, dict)
                and d.get("sha256") == sha), None)
    if not rec or not rec.get("edited_before_sending"):
        return None
    rows = [o for o in st.get("lawyer_overrides") or () if isinstance(o, dict)
            and o.get("source") == "edited_before_sending" and str(o.get("round")) == str(rec.get("round"))]
    nm = st.get("numbering_map") or {}
    where = []
    for o in rows:
        lab = o.get("clause") or nm.get(o.get("clause_id")) or ""
        if lab and lab not in where:
            where.append(lab)
    return ("ההשוואה היא מול הקובץ שנשלח בפועל בסבב %s, %s, שעורך הדין ערך לפני המשלוח: %d הבדלים מול העותק שהופק%s, "
            "רשומים ב-lawyer_overrides" % (rec.get("round"), os.path.basename(rec.get("file_name") or sent_path),
                                          len(rows), " (%s)" % ", ".join(where[:8]) if where else ""))


def state_clauses(path):
    if not path or not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        st = json.load(fh)
    return {c.get("clause_id"): c for c in st.get("clauses") or []}


def main(argv=None):
    no_bytecode()
    ap = parser(__doc__.split("\n")[0], out_required=False)
    ap.add_argument("--sent", help="הקובץ שהחברה שלחה בסבב הקודם. בלעדיו: מקובץ המצב (--deal)")
    ap.add_argument("--received", required=True, help="הקובץ שחזר מהצד שכנגד")
    ap.add_argument("--author", action="append",
                    help="שם עורך הדין של החברה, כפי שהוא בסימונים שלנו. אפשר כמה פעמים")
    ap.add_argument("--profile", help="פרופיל-לקוח.json: כל השמות שלנו (lawyer_name, lawyer_name_en, lawyer_aliases)")
    ap.add_argument("--deal", help="תיקיית העסקה: בסיס ההשוואה כשאין --sent, וסעיפים CLOSED שנפתחו")
    ap.add_argument("--assumed-base", action="store_true",
                    help="--sent לא אושר כקובץ שנשלח בפועל: התוצאה מסומנת בסיס משוער")
    a = ap.parse_args(argv)
    ours = authors_of(a)
    if not ours:
        print("חסר שם עורך הדין שלנו: --profile, או --author (אפשר כמה פעמים)")
        return 2
    sent_path, base = resolve_sent(a)
    if not sent_path or not os.path.exists(sent_path):
        print("אין קובץ שנשלח להשוואה%s. כתוב בסיכום: \"לא ניתן לאתר שינויים שלא סומנו: הקובץ שנשלח אינו זמין.\""
              % (" (%s)" % sent_path if sent_path else ""))
        return 2
    if not os.path.exists(a.received):
        print("הקובץ שחזר מהצד שכנגד אינו קיים: %s" % a.received)
        return 2
    # Word פגום, DOC, מוצפן או Strict: הודעה דו-לשונית וקוד 2, ולא traceback של zipfile
    for p in (sent_path, a.received):
        ok, msg, code = load_docx_or_explain(p, loader=False)
        if ok is None:
            print(msg)
            return code
    if a.out:
        try:   # לפני ההשוואה: --out שהוא אחד הקבצים, או מסמך קיים, נדחה לפני כל עבודה
            guard_out(a.out, inputs=[sent_path, a.received])
        except OutputRefused as exc:
            print("סירוב: %s" % exc)
            return 1

    sent_paras =dt.body_paragraphs(dt.document_root(sent_path))
    proposed = [project(p, accept_authors=ours, accept_rest=True) for p in sent_paras]
    before = [project(p, reject_authors=ours, accept_rest=True) for p in sent_paras]
    # מספר הפסקה בטיוטה שממנה הופק הקובץ ששלחנו, כפי שהצד השני ראה אותה: פסקה שכולה הוספה שלנו מהסבב הקודם אינה
    # נספרת, והוספה פתוחה שלנו מסבב שלפניו נספרת, כי היא בטיוטה (clause_map של אותו סבב; S1e-R3)
    base_idx, _base = base_paragraphs(sent_paras, ours, prior_keys(sent_path, ours, a.deal), before)

    recv_paras = dt.body_paragraphs(dt.document_root(a.received))
    # מה הם פתחו בו: הסימונים שלנו מתקבלים, שלהם נדחים
    opened = [project(p, accept_authors=ours, accept_rest=False) for p in recv_paras]
    now = [project(p, accept_rest=True) for p in recv_paras]

    out = {"sent": sent_path, "received": a.received, "author": ours[0], "authors": ours, "base": base,
           "clauses": [], "counts": {}}

    def add(kind, para_text_, **extra):
        item = {"classification": kind, "clause": clause_of(para_text_)}
        item.update(extra)
        out["clauses"].append(item)

    def where(i, j):
        loc = {"sent_para": i, "base_para": base_idx[i] if i is not None else None, "received_para": j,
               "we_sent": proposed[i] if i is not None else ""}
        if i is not None and base_idx[i] is None:   # פסקה שהוספנו: אחרי איזו פסקה בטיוטה (after_para ב-clause_map)
            loc["after_base_para"] = next((base_idx[x] for x in range(i - 1, -1, -1) if base_idx[x] is not None), None)
        return loc

    def new_theirs(sp, rp):
        """סימונים של הצד שכנגד שאינם בקובץ ששלחנו, ושאינם מחיקה שלהם בתוך הוספה שלנו."""
        had = [(dt.local(e.tag), e.get(W + "author"), norm(_full_text(e))) for e in _revs(sp)
               if e.get(W + "author") not in ours]
        res = []
        for e in _revs(rp):
            if e.get(W + "author") in ours:
                continue
            if any(x.tag == W + "ins" and x.get(W + "author") in ours for x in e.iterancestors(W + "ins")):
                continue
            key = (dt.local(e.tag), e.get(W + "author"), norm(_full_text(e)))
            if key in had:
                had.remove(key)
                continue
            res.append(e)
        return res

    pairs, only_sent, only_recv = pair_up(proposed, opened, before)

    for i, j in pairs:
        sp, rp = sent_paras[i], recv_paras[j]
        revs = _revs(sp)
        # קודם הצירופים השלמים (הכול התקבל, הכול נדחה): סימונים ברמת מילה יכולים לתת אותו נוסח בכמה צירופים
        if norm(opened[j]) in (norm(proposed[i]), norm(before[i])):
            whole = "accepted" if norm(opened[j]) == norm(proposed[i]) else "rejected"
            fates = {k: whole for k in range(len(revs))}
        else:
            fates = mark_fates(sp, opened[j], revs)
        explained = fates is not None
        loc = where(i, j)
        if not explained:
            # שינוי בלי מעקב: מה שהם פתחו בו אינו שום צירוף של קבלה ודחייה של הסימונים ששלחנו
            add("their_silent", proposed[i], they_opened_with=opened[j],
                note="הנוסח השתנה בלי סימון מעקב. נדרשת הכרעתך (מצב 9), ומוצג בשורות הראשונות של הסיכום", **loc)
            if marked_by(rp, ours):
                add("our_open", proposed[i], we_proposed=proposed[i], now=now[j],
                    note="ההצעה עוד מסומנת: לא קיבלו ולא דחו. אין לגעת בה", **loc)
        else:
            recv_ours = [(dt.local(e.tag), norm(_full_text(e)), e) for e in _revs(rp) if e.get(W + "author") in ours]
            used, marks = set(), []
            for k_, e in enumerate(revs):
                if e.get(W + "author") not in ours:
                    continue
                kind, txt = dt.local(e.tag), norm(_full_text(e))
                if not txt:
                    continue
                fate = fates.get(k_, "accepted")
                hit = next((x for x in recv_ours if id(x[2]) not in used and x[0] == kind and x[1] == txt), None)
                if hit is not None:
                    used.add(id(hit[2]))
                    fate = "open"
                marks.append({"kind": kind, "text": txt, "fate": fate})
            killed = [(e, [d for d in e.iter(W + "del") if d.get(W + "author") not in ours])
                      for e in _revs(rp) if e.tag == W + "ins" and e.get(W + "author") in ours]
            killed = [(e, ds) for e, ds in killed if ds]
            if killed:
                gone = "".join(_full_text(d) for _e, ds in killed for d in ds)
                add("their_rejected_our_insert", proposed[i], we_proposed=proposed[i], now=now[j], marks=marks,
                    they_deleted=gone, fully=all(norm("".join(_full_text(d) for d in ds)) == norm(_full_text(e))
                                                 for e, ds in killed),
                    note="הם מחקו בעקוב אחר שינויים את מה שהוספנו: דחייה של ההצעה שלנו, במעקב. סיווג אחד; "
                         "המחיקה שלהם מוכרעת לפי מספר הזיהוי שלה (their_changes)", **loc)
            elif marks:
                fs = {m["fate"] for m in marks}
                if fs == {"open"}:
                    add("our_open", proposed[i], we_proposed=proposed[i], now=now[j],
                        note="ההצעה עוד מסומנת: לא קיבלו ולא דחו. אין לגעת בה", **loc)
                elif fs == {"accepted"}:
                    add("our_accepted", proposed[i], we_proposed=proposed[i], now=now[j],
                        note="ההצעה נשארה. הסעיף עובר ל-CLOSED כשאין בו נקודה פתוחה (negotiation_state.py write "
                             "--compare)", **loc)
                elif fs == {"rejected"}:
                    add("our_rejected", proposed[i], we_proposed=proposed[i], was_before=before[i], now=now[j],
                        note="הנוסח חזר למה שהיה. הסעיף מוכרע מחדש לפי הפלייבוק", **loc)
                else:
                    add("our_accepted_partial", proposed[i], we_proposed=proposed[i], now=now[j], marks=marks,
                        note="קבלה חלקית: לכל סימון הגורל שלו (accepted, rejected, open). אינה שינוי שקט", **loc)
        theirs = new_theirs(sp, rp)
        if theirs:
            add("their_tracked", now[j], now=now[j],
                they_added="".join(_full_text(e) for e in theirs if e.tag == W + "ins"),
                they_deleted="".join(_full_text(e) for e in theirs if e.tag == W + "del"),
                note="מוכרע לפי מספר הזיהוי שלו, כמו בסבב הראשון", **loc)

    for i in only_sent:
        if not norm(proposed[i]):
            if norm(before[i]):
                add("our_accepted", before[i], we_proposed="", now="",
                    note="מחקנו את הפסקה, והיא אינה בקובץ שחזר: המחיקה התקבלה", **where(i, None))
            continue
        if not norm(before[i]):
            add("our_rejected", proposed[i], we_proposed=proposed[i], was_before="", now="",
                note="פסקה שהוספנו אינה בקובץ שחזר: ההוספה נדחתה", **where(i, None))
            continue
        add("their_silent", proposed[i], they_opened_with="",
            note="פסקה ששלחנו אינה בקובץ שחזר, ואין סימון מחיקה", **where(i, None))
    for j in only_recv:
        if not norm(opened[j]) and not norm(now[j]):
            continue
        loc = {"sent_para": None, "base_para": None, "received_para": j, "we_sent": ""}
        if marked_by_others(recv_paras[j], ours) and not norm(opened[j]):
            add("their_tracked", now[j], now=now[j],
                they_added=dt.revision_text(recv_paras[j], "ins"),
                note="פסקה שהם הוסיפו במעקב", **loc)
        else:
            add("their_silent", opened[j] or now[j], they_opened_with=opened[j],
                note="פסקה שאינה במה ששלחנו, ואין סימון הוספה", **loc)

    # סעיף CLOSED שנפתח: הנוסח המוסכם (agreed_text) הוא מה ששלחנו בפסקה שהשתנתה
    closed = {norm(c.get("agreed_text")): cid for cid, c in state_clauses(
        os.path.join(a.deal, "negotiation_state.json") if a.deal else None).items()
        if c.get("status") == "CLOSED" and c.get("agreed_text")}
    for c in out["clauses"]:
        if c["classification"] in ("their_silent", "their_tracked", "their_rejected_our_insert") \
                and closed.get(norm(c.get("we_sent"))):
            c["reopens_closed"] = closed[norm(c["we_sent"])]

    # מפת הפסקאות (S1d-R2): לכל פסקה שהוצמדה, גם בלי שינוי, הפסקה ששלחנו, הפסקה בטיוטה של הסבב הקודם והפסקה בטיוטה
    # שחזרה. בקשה חדשה שלהם על סעיף שלא השתנה (state_builder.apply_compare) והעברת ההכרעות (round_tools.py carry)
    # נשענות עליה
    out["para_map"] = [{"sent_para": i, "base_para": base_idx[i], "received_para": j} for i, j in pairs]
    out["threads"] = thread_view(sent_path, a.received, ours, now)
    for c in out["clauses"]:
        c["threads"] = [t["root_id"] for t in out["threads"] if t["para"] is not None and t["para"] == c["received_para"]]
    out["orphaned_terms"] = orphaned_terms(proposed, now)

    for c in out["clauses"]:
        k = c["classification"]
        out["counts"][k] = out["counts"].get(k, 0) + 1
    out["counts"]["their_replies"] = sum(1 for t in out["threads"] if t["their_reply_to_ours"])
    out["counts"]["their_new_comments"] = sum(1 for t in out["threads"] if t["their_new_thread"])

    # השורות הראשונות של הסיכום הפנימי (H6): כל שינוי שקט, כל סעיף מוסכם שנפתח, וכל מונח שהגדרתו נמחקה
    head = []
    edited = sent_edits_line(sent_path, a.deal)
    if edited:
        head.append(edited)
    if base == "assumed":
        head.append("בסיס משוער: ההשוואה היא מול %s, ולא מול קובץ שאושר כנשלח. שינוי \"שקט\" עשוי להיות עריכה "
                    "שלנו לפני המשלוח" % os.path.basename(sent_path))
    for c in out["clauses"]:
        if c.get("reopens_closed"):
            head.append("פתיחה מחדש של סעיף מוסכם: %s (%s)" % (c.get("clause") or c["reopens_closed"],
                                                               c["classification"]))
        if c["classification"] == "their_silent":
            sent_s, back_s = snippet(c.get("we_sent"), c.get("they_opened_with"))
            head.append("שינוי שלא סומן: סעיף %s. נשלח: \"%s\". חזר: \"%s\"" % (c.get("clause") or "?", sent_s, back_s))
    for t in out["orphaned_terms"]:
        head.append("מונח בלי הגדרה: \"%s\" (ההגדרה ב-%s נמחקה; משמש ב-%s)" % (
            t["term"], t["defined_in"] or "?", ", ".join(x for x in t["used_in"] if x) or "?"))
    # אזהרה בקליטה, לא חוסמת (S1d-R2): בועות או סימונים של הצד השני שמתוארכים אחרי היום. התאריכים אינם משתנים;
    # התשובות שלנו יתוארכו היום, ולכן יופיעו לפני הבועות שהן עונות להן, ועורך הדין צריך לדעת זאת
    fut = dt.future_dated(a.received, ours)
    out["intake_warnings"] = []
    if fut:
        n_c = sum(1 for x in fut if x["kind"] == "comment")
        last = max(x["date"] for x in fut)
        msg = ("אזהרה (לא חוסמת): בטיוטה שחזרה %d בועות ו-%d סימוני מעקב של הצד השני מתוארכים אחרי היום (%s), עד %s "
               "(%s). התשובות שלנו מתוארכות היום, ולכן יופיעו לפני הבועות שלהם. התאריכים לא שונו"
               % (n_c, len(fut) - n_c, SB.display_date(None, "he"), SB.display_date(last[:10], "he"),
                  ", ".join(sorted({x["author"] or "?" for x in fut}))))
        out["intake_warnings"].append({"code": "THEIR_DATES_IN_FUTURE", "message": msg, "items": fut})
        head.append(msg)
    out["summary_head"] = head
    if head:
        print("לשורות הראשונות של הסיכום:")
        for line in head:
            print("  " + line)

    for k in KINDS:
        n = out["counts"].get(k, 0)
        mark = "  <-- הממצא החשוב ביותר" if k == "their_silent" and n else ""
        print("  %-26s %3d%s" % (k, n, mark))
    print("  %-26s %3d" % ("their_replies (שרשור)", out["counts"]["their_replies"]))
    print("  %-26s %3d" % ("their_new_comments", out["counts"]["their_new_comments"]))
    if not out["clauses"]:
        print("  אין הבדל בין מה ששלחנו למה שחזר.")

    if a.out:
        try:
            path = guard_out(a.out, inputs=[sent_path, a.received])
        except OutputRefused as exc:
            print("סירוב: %s" % exc)
            return 1
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=2)
        print("נכתב %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
