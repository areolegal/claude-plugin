# -*- coding: utf-8 -*-
"""
בודק שלמות פנימית של טיוטה לפני מסירה: מונחים מוגדרים, הפניות פנימיות,
נספחים, מספור, מצייני חוסר, סכומים ותאריכים; ובדיקה סמנטית של המנגנונים: הפניה
לתעריפים, למחירון או להיקף ההתקשרות שאינם מעוגנים בהסכם, סתירה בין מנגנוני התמורה,
הארכה בלי מחיר, סיום בלי חישוב יחסי, פיצוי מוסכם ריק בלי תקרה, הצעת הצד השני כנספח
בלי החרגה, ושאריות של טופס ציבורי כשאף אחד מהצדדים אינו גוף ציבורי (--profile, --draft-json).
אזכור פסיקה בטיוטה או בדף הליווי, כשאין מחבר פסיקה סגור (--case-law-connector), הוא ממצא חוסם (כלל 1.1).
מפת השונות (--variance-map, עם --draft-json): כל סעיף אופציונלי ונוסח חלופי בטיוטה נשען על תשובה או על ברירת
מחדל (variance.answers), וקבוע לא השתנה ולא נשמט בשקט (רק ב-variance.overrides, למשל עמדת פלייבוק).

הבדיקה הזאת היא מה שעורך דין עושה בקריאה שנייה, והיא מה שנופל ראשון בלחץ זמן.
הסקריפט אינו מחליף שיקול דעת: הוא מוצא את מה שאפשר למצוא מכנית, ומשאיר את ההכרעה.

הרצה:
  python3 check_draft_integrity.py <draft.docx> [--json out.json] [--strict]
      [--profile "<profile_path של הישות>"] [--cover "<דף ליווי>.docx" "<סיכום>.md"] [--keep-public-form]
      [--draft-json Areo-נתונים/draft-<slug>.json] [--counterparty-public-body] [--role <company_role_code>]
      [--case-law-connector] [--variance-map Areo-נתונים/תבניות/<משפחה>/variance-map.json]
      [--deal-card <כרטיס העסקה: draft.json או negotiation_state.json>] [--core <playbook-core.json>]

מספר מצייני החוסר (placeholders בדוח ה-JSON) נספר כאן בלבד (count_placeholders), ו---cover בודק שדף הליווי
והסיכום מציגים את אותו מספר.

קוד יציאה: 0 אם אין ממצא חוסם, 1 אם יש. --strict הופך גם אזהרה לחוסמת.
"""
import argparse
import io
import json
import os
import re
import sys
from collections import Counter, OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_template_registry import docx_text, docx_paragraphs, guard_out  # noqa: E402
from client_text_gate import CODE_RX, HOLD_RX, NO_SOURCE_NOTE, NO_SOURCE_NOTE_EN  # noqa: E402
from derive_deal_defaults import CUR  # noqa: E402  מטבע: סימן, קוד ISO 4217 או שם, לפני הסכום או אחריו

try:                                   # פלט עברי במסוף של Windows
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):   # pragma: no cover
    pass


# ------------------------------------------------------------------ פסיקה (כלל 1.1)
# common.case_law מהספרייה המשותפת (הסקריפט רץ מתוך AREO_RT): הבודק היחיד של אזכורי פסיקה
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from areo_rt import ensure_lib  # noqa: E402
ensure_lib()
try:
    from common.case_law import case_law_mentions as _lib_case_law_hits  # noqa: E402
except ImportError:                    # pragma: no cover
    _lib_case_law_hits = None
# הבודק היחיד של אזכורי פסיקה הוא common.case_law (הספרייה המשותפת). אין כאן תבניות משלו
_CITE_RX = ()


def case_law_hits(text):
    hits = [m.group(0).strip() for rx in _CITE_RX for m in rx.finditer(text or "")]
    for h in (_lib_case_law_hits(text) if _lib_case_law_hits else []):
        if not any(h in x or x in h for x in hits):
            hits.append(h)
    return hits


_VTOK = re.compile(r"[\w\u0590-\u05FF]+", re.U)


def _vtoks(t):
    return [w.lower() for w in _VTOK.findall(t or "") if not w.isdigit()]


def _coverage(needle, hay):
    """החלק של מילות needle (בלי ספרות) שנמצאות ב-hay באותו סדר: 1.0 כשהנוסח נמצא כלשונו."""
    import difflib
    if not needle:
        return 1.0
    sm = difflib.SequenceMatcher(None, needle, hay, autojunk=False)
    return sum(b.size for b in sm.get_matching_blocks()) / float(len(needle))


INCLUDE_ANS = ("include", "לכלול", "yes", "כן", "כן, להוסיף", "yes, add it", "include it")
EXCLUDE_ANS = ("exclude", "לא לכלול", "no", "לא", "לא, בלי הסעיף", "no, leave it out", "leave it out")


def check_variance(text, draft_json, vmap, rep):
    """עקיבות למפת השונות. variance.answers: {O1: include|exclude, A1: V2, F3: ערך}; variance.defaults: מזהים שנקבעו
    בברירת מחדל ולא נשאלו; variance.overrides: {C4: הסיבה} לקבוע ששונה במכוון (עמדת פלייבוק, בקשת הלקוח)."""
    var = (draft_json or {}).get("variance") or {}
    answers, overrides = var.get("answers") or {}, var.get("overrides") or {}
    defaults = set(var.get("defaults") or [])
    hay = _vtoks(text)
    clause_ids = set()

    def walk(cs):
        for c in cs or []:
            v = str(c.get("variance_id") or "")
            if v:
                clause_ids.add(v.split(":")[0])
            walk(c.get("children") or c.get("subclauses"))
    walk((draft_json or {}).get("clauses"))
    for a in (draft_json or {}).get("annexes") or []:
        walk(a.get("clauses"))
    bad = []
    for o in vmap.get("optional_clauses") or []:
        oid = o["id"]
        if o.get("askable") is False:
            continue          # כותרת שאינה קריאה (קטע משפט מ-PDF): לא נשאלה, ואינה סעיף
        ans = str(answers.get(oid, "")).lower()
        present = oid in clause_ids or _coverage(_vtoks(o.get("wording")), hay) >= 0.9
        # סעיף ליבה (ברוב ההסכמים) אינו אופציונלי: נכלל בלי שאלה, והיעדרו מהטיוטה חוסם
        implicit = bool(o.get("core")) and oid not in answers and oid not in defaults
        if implicit:
            ans = "include"
        if oid not in answers and oid not in defaults and not implicit:
            if present:
                bad.append("%s (%s): בטיוטה, בלי תשובה ובלי ברירת מחדל" % (oid, o.get("heading")))
            else:
                bad.append("%s (%s): לא נשאל ולא נקבע בברירת מחדל" % (oid, o.get("heading")))
        elif ans in INCLUDE_ANS and not present:
            bad.append("%s (%s): התשובה לכלול, והסעיף אינו בטיוטה" % (oid, o.get("heading")))
        elif ans in EXCLUDE_ANS and present:
            bad.append("%s (%s): התשובה לא לכלול, והסעיף בטיוטה" % (oid, o.get("heading")))
    for a in vmap.get("alternative_wordings") or []:
        if a.get("askable") is False:
            continue          # כותרת שאינה קריאה (קטע משפט מ-PDF): לא נשאלה
        if a["id"] not in answers and a["id"] not in defaults:
            bad.append("%s (%s): נוסח חלופי בלי תשובה ובלי ברירת מחדל" % (a["id"], a.get("heading")))
    if bad:
        rep.add("חוסם", "מפת השונות", "סעיף אופציונלי או נוסח חלופי שאינו נשען על תשובה של הלקוח או על ברירת מחדל",
                bad[:10])
    changed = []
    for c in vmap.get("constants") or []:
        if c["id"] in overrides:
            continue
        tmpl = re.sub(r"\{\{F\d+\}\}", " ", c.get("text_template") or c.get("text") or "")
        cov = _coverage(_vtoks(tmpl), hay)
        if cov < 0.97:
            changed.append("%s (%s): %s (%.0f%% מהנוסח נמצא)" % (c["id"], c.get("heading"),
                                                               "נשמט" if cov < 0.6 else "שונה", cov * 100))
    if changed:
        rep.add("חוסם", "מפת השונות", "סעיף קבוע, שזהה בכל ההסכמים של הלקוח, שונה או נשמט בשקט. שינוי במכוון "
                "נרשם ב-variance.overrides עם הסיבה", changed[:10])


def check_case_law(sources, rep, connector=False):
    """אזכור פסק דין בטיוטה או בדף הליווי כשאין מחבר פסיקה סגור בהרצה: ממצא חוסם. sources: [(שם, טקסט)]."""
    if connector:
        return
    found = []
    for name, t in sources:
        for h in case_law_hits(t):
            found.append("%s: %s" % (name, h))
    if found:
        rep.add("חוסם", "פסיקה",
                "אזכור פסיקה בלי מחבר פסיקה סגור (כלל 1.1). פסיקה אינה נכתבת מהזיכרון או מהרשת: הסר את האזכור, "
                "וסמן את הסעיף \"טעון בדיקה משפטית\"", found[:10])



# ------------------------------------------------------------------ מקור גלוי, ללא שער אישור, ניסוח מבחוץ (כללים 3, 5, 6, 12)

def _src_ids(v):
    if isinstance(v, str):
        return [x.strip() for x in v.split(",") if x.strip()]
    return [str(x).strip() for x in (v or []) if str(x).strip()]


def _leaf_sources(clauses, inherited, out):
    """[(מספר סעיף, [מזהי מקור])] לכל סעיף שיש בו טקסט; תת-סעיף בלי source יורש מהסעיף שמעליו."""
    for c in clauses or []:
        if not isinstance(c, dict):
            continue
        own = _src_ids(c.get("source"))
        eff = own or inherited
        if (c.get("text") or "").strip():
            out.append((str(c.get("number") or c.get("heading") or "?"), eff))
        _leaf_sources(c.get("children"), eff, out)
    return out


def draft_clause_sources(dj):
    out = _leaf_sources(dj.get("clauses"), [], [])
    for an in dj.get("annexes") or []:
        out += _leaf_sources((an or {}).get("clauses"), [], [])
    return out


def is_outside_draft(dj):
    """טיוטה שנבנתה מבחוץ (מחקר והסכמים פומביים): מקור REG-, MAND-, AGR-, או sources, או notice שאינו של נוסחים
    של צד שלישי מתיקיית הלקוח (meta.source_mode: third_party_paper)."""
    m = dj.get("meta") or {}
    if dj.get("sources") or any(i.upper().startswith(("REG-", "MAND-", "AGR-"))
                                for _n, ids in draft_clause_sources(dj) for i in ids):
        return True
    return bool(m.get("notice")) and m.get("source_mode") != "third_party_paper"


def check_hold_and_codes(sources, rep, cover_names):
    """דף הליווי והטיוטה: בלי קודים פנימיים, בלי נוסח של שער אישור או עצירה, ובלי מילים של המערכת (voice_check,
    מצב document). הטיוטה נמסרת נקייה אחרי השאלות (כלל 6), ודף הליווי מדבר בלשון הלקוח (כלל 10)."""
    try:
        from common.voice_check import check_text as _vc
    except ImportError:
        _vc = None
    for name, t in sources:
        codes = sorted({m.group(0) for m in CODE_RX.finditer(t)})
        if codes:
            rep.add("חוסם", "קודים פנימיים", "%s: %d קודים פנימיים בטקסט שהלקוח רואה. מנסחים בשם ההסכם ובמספר הסעיף" % (name, len(codes)), codes[:10])
        holds = sorted({m.group(0) for m in HOLD_RX.finditer(t)}) if name in cover_names else []   # לא גוף ההסכם
        if holds:
            rep.add("חוסם", "שער אישור", "%s: נוסח של עצירה או של אישור עורך דין. הטיוטה נמסרת נקייה, בלי המתנה לאישור" % name, holds[:6])
        if name not in cover_names:
            leaks = [n for n in (NO_SOURCE_NOTE, NO_SOURCE_NOTE_EN) if n.lower() in t.lower()]
            if leaks:
                rep.add("חוסם", "דליפת נוסח פנימי", "%s: השורה הפנימית של Areo בגוף ההסכם, שעלול להגיע לצד השני. בגוף "
                        "ההסכם רק \"[להשלמה]\"; השורה המלאה בדף הליווי" % name, leaks)
        if _vc and name in cover_names:
            hits = [h["term"] for h in _vc(t, "document") if not re.match(r"^[A-Z]-\d{1,2}$", h["term"])]
            if hits:
                rep.add("חוסם", "ניסוח ללקוח", "%s: מילים של המערכת בטקסט שהלקוח רואה (voice_check, מצב document)" % name, sorted(set(hits))[:10])


def check_sources_shown(dj, cover_text, rep):
    """כלל 12: כל סעיף שנלקח מתיקיית הלקוח נושא את שם ההסכם (DOC-) או הפלייבוק (PB-) שעליו נשען, ושם זה מופיע בדף
    הליווי. כלל 5: סעיף בלי מקור כלל מקבל הערה גלויה "AREO לא מצאה מקור מורשה לנקודה זו" עם צעד הבא, ולא מולא מהזיכרון."""
    cv = dj.get("cover") or {}
    docs = {}
    for d in cv.get("documents") or []:
        if isinstance(d, dict) and d.get("no") is not None:
            docs[str(d.get("no"))] = (d.get("title") or "").strip()
    pb_name = ((cv.get("playbook") or {}).get("name") or "").strip()
    leaves = draft_clause_sources(dj)
    used_docs, used_pb, bare = {}, [], []
    for num, ids in leaves:
        if not ids:
            bare.append(num)
        for i in ids:
            u = i.upper()
            if u.startswith("DOC-"):
                used_docs.setdefault(u[4:], []).append(num)
            elif u.startswith("PB-"):
                used_pb.append(num)
    for no, nums in sorted(used_docs.items()):
        if not docs.get(no):
            rep.add("חוסם", "מקור גלוי", "סעיפים %s נשענים על נוסח %s, ואין לו שם ב-cover.documents. דף הליווי חייב לומר "
                    "על איזה הסכם הסעיף נשען" % (", ".join(nums[:6]), no), nums[:10])
        elif cover_text is not None and docs[no] not in cover_text:
            rep.add("חוסם", "מקור גלוי", "שם ההסכם \"%s\" אינו מופיע בדף הליווי, והסעיפים %s נשענים עליו"
                    % (docs[no], ", ".join(nums[:6])), nums[:10])
    if used_pb and not pb_name:
        rep.add("חוסם", "מקור גלוי", "סעיפים נשענים על הפלייבוק, ואין cover.playbook.name. דף הליווי חייב לומר על איזה "
                "פלייבוק", used_pb[:10])
    if bare and any(ids for _n, ids in leaves):      # יש מעקב מקורות בטיוטה, ויש סעיפים בלי מקור
        notes = " ".join(str(x) for x in (cv.get("notes") or []))
        seen = (cover_text or "") + " " + notes
        if NO_SOURCE_NOTE not in seen and NO_SOURCE_NOTE_EN not in seen:
            rep.add("אזהרה", "מקור גלוי", "לסעיפים %s אין מקור. סעיף כזה נשען על מקור, או שדף הליווי אומר "
                    "\"%s\" ומציע צעד הבא אחד; לא ממלאים מהזיכרון" % (", ".join(bare[:8]), NO_SOURCE_NOTE), bare[:12])


def check_outside_basis(dj, cover_text, rep):
    """כלל 3: ניסוח מבחוץ (הסכמים ברשת ופרקטיקת שוק) רק כשאין ללקוח פלייבוק ואין הסכמי טיוטה, והלקוח ביקש זאת במפורש,
    ורק ממקורות מורשים. הטיוטה אומרת זאת במפורש (meta.notice, בדף הליווי)."""
    if not is_outside_draft(dj):
        return
    m = dj.get("meta") or {}
    ob = m.get("outside_basis") or {}
    miss = [k for k in ("no_playbook", "no_client_agreements", "client_asked") if ob.get(k) is not True]
    if miss:
        rep.add("חוסם", "ניסוח מבחוץ", "טיוטה שנבנתה מהסכמים ברשת ומפרקטיקת שוק מותרת רק כשאין ללקוח פלייבוק, אין הסכמים, "
                "והוא ביקש זאת במפורש. חסר ב-meta.outside_basis: %s" % ", ".join(miss), miss)
    if not (m.get("notice") or "").strip():
        rep.add("חוסם", "ניסוח מבחוץ", "הטיוטה נבנתה מבחוץ, ואין meta.notice שאומר זאת בדף הליווי בבירור")
    elif cover_text is not None and (m.get("notice") or "").strip()[:25] not in cover_text:
        rep.add("אזהרה", "ניסוח מבחוץ", "ה-notice שאומר שהטיוטה נבנתה מבחוץ אינו מופיע בדף הליווי")


# ------------------------------------------------------------------ כרטיס העסקה וגרעין הפלייבוק (--deal-card, --core)

_NUM_RX = re.compile(r"\d[\d,./-]*\d|\d")


def _norm_num(s):
    return re.sub(r"[,\s]", "", s)


def _text_norm(text):
    return re.sub(r"[,\s]+", " ", (text or "").lower())


def deal_card_facts(path):
    """עובדות העסקה מכרטיס העסקה: קובץ הטיוטה (cover.facts, meta.parties), negotiation_state.json (facts[].fact),
    או {"facts": [...]} פשוט. מחזיר רשימת מחרוזות; None כשהקובץ לא נקרא."""
    try:
        d = json.load(io.open(path, encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    facts = []

    def _add(v):
        if isinstance(v, str) and v.strip():
            facts.append(v.strip())
        elif isinstance(v, dict):
            f = v.get("fact") or v.get("text") or v.get("value")
            if isinstance(f, str) and f.strip():
                facts.append(f.strip())

    def _walk(o, depth=0):
        if depth > 6:
            return
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "facts" and isinstance(v, list):
                    for x in v:
                        _add(x)
                elif k == "parties" and isinstance(v, list):
                    for x in v:
                        if isinstance(x, dict) and (x.get("name") or "").strip():
                            facts.append(x["name"].strip())
                else:
                    _walk(v, depth + 1)
        elif isinstance(o, list):
            for x in o:
                _walk(x, depth + 1)
    if isinstance(d, list):
        for x in d:
            _add(x)
    else:
        _walk(d)
    return list(OrderedDict.fromkeys(facts))


def fact_in_text(fact, text):
    """עובדה נמצאת בטיוטה: כל מספר שבה מופיע בטקסט (אחרי נרמול פסיקים ורווחים), וכשאין בה מספר, רוב מילותיה
    (בלי התווית שלפני הנקודתיים) מופיעות בסדרן."""
    tn = _text_norm(text)
    value = fact.split(":", 1)[1] if ":" in fact else fact
    nums = [_norm_num(n) for n in _NUM_RX.findall(value)]
    nums = [n for n in nums if len(n) >= 2 or not n.isdigit()]
    if nums:
        flat = _norm_num(tn)
        return all(n.lower() in flat for n in nums)
    toks = _vtoks(value)
    return not toks or _coverage(toks, _vtoks(tn)) >= 0.6


def check_deal_card(path, text, rep):
    """core-contract פרק 3 וכלל 12: כל עובדה בכרטיס העסקה מופיעה בטיוטה. עובדה שחסרה היא ממצא חוסם."""
    facts = deal_card_facts(path)
    if facts is None:
        rep.add("חוסם", "עובדות העסקה", "כרטיס העסקה לא נקרא: %s" % os.path.basename(path))
        return
    if not facts:
        rep.add("מידע", "עובדות העסקה", "בכרטיס העסקה אין עובדות (facts) לבדיקה")
        return
    missing = [f for f in facts if not fact_in_text(f, text)]
    if missing:
        rep.add("חוסם", "עובדות העסקה", "%d מתוך %d עובדות העסקה אינן מופיעות בטיוטה. עובדה מהכרטיס נכנסת לסעיף, "
                "או מסומנת [להשלים] במקומה" % (len(missing), len(facts)), missing[:12])
    else:
        rep.add("מידע", "עובדות העסקה", "כל %d עובדות העסקה מופיעות בטיוטה" % len(facts))


def core_required(core):
    """[(id, title, preferred_wording)] לכל כלל בגרעין שבו presence.requirement הוא Required."""
    out = []
    for c in (core or {}).get("clauses") or []:
        if not isinstance(c, dict):
            continue
        req = ((c.get("presence") or {}).get("requirement") or "").strip().lower()
        if req == "required":
            out.append((str(c.get("id") or c.get("policy_ref") or ""),
                        (c.get("title") or c.get("clause_issue") or "").strip(),
                        (c.get("preferred_wording") or (c.get("green") or {}).get("preferred_wording") or "").strip()))
    return out


def check_core(core_path, text, dj, sources, rep):
    """כלל 7 ו-12: כל סעיף ליבה (Required) בגרעין הפלייבוק מכוסה בטיוטה, בסעיף שמקורו PB-<כלל> או בנוסח (כותרת
    הכלל או הנוסח המועדף); ואף מזהה כלל מהגרעין אינו מופיע בטקסט שהלקוח רואה (קודים פנימיים)."""
    try:
        core = json.load(io.open(core_path, encoding="utf-8-sig"))
    except (OSError, ValueError):
        rep.add("חוסם", "סעיפי ליבה", "גרעין הפלייבוק לא נקרא: %s" % os.path.basename(core_path))
        return
    pb_ids = set()
    if isinstance(dj, dict):
        for _n, ids in draft_clause_sources(dj):
            for i in ids:
                if i.upper().startswith("PB-"):
                    pb_ids.add(i[3:].strip().lower())
    hay = _vtoks(text)
    tl = (text or "").lower()
    required = core_required(core)
    missing = []
    for rid, title, wording in required:
        covered = rid.lower() in pb_ids
        if not covered and title:
            covered = title.lower() in tl or _coverage(_vtoks(title), hay) >= 0.6
        if not covered and wording:
            covered = _coverage(_vtoks(wording)[:40], hay) >= 0.5
        if not covered:
            missing.append("%s%s" % (title or "(בלי כותרת)", " [%s]" % rid if rid else ""))
    if missing:
        rep.add("חוסם", "סעיפי ליבה", "%d מתוך %d סעיפי הליבה של הפלייבוק (Required) אינם בטיוטה. סעיף ליבה נכלל "
                "תמיד, עם source: PB-<הכלל>" % (len(missing), len(required)), missing[:12])
    elif required:
        rep.add("מידע", "סעיפי ליבה", "כל %d סעיפי הליבה של הפלייבוק מכוסים" % len(required))
    ids = [str(c.get("id")) for c in (core.get("clauses") or []) if isinstance(c, dict) and c.get("id")]
    for name, src_text in sources:
        leaked = sorted({i for i in ids if re.search(r"(?<![\w-])%s(?![\w-])" % re.escape(i), src_text)})
        if leaked:
            rep.add("חוסם", "קודים פנימיים", "%s: מזהי כללים מהפלייבוק בטקסט שהלקוח רואה. כותבים את שם הנושא" % name,
                    leaked[:10])


# ------------------------------------------------------------------ איתור

DEF_RX = [
    re.compile(r'\(\s*להלן\s*:?\s*[""״"]([^""״"]{2,60})[""״"]\s*\)'),
    re.compile(r'[""״"]([^""״"]{2,60})[""״"]\s*[-–—]\s*(?=[א-תA-Za-z])'),
    re.compile(r'\(\s*hereinafter[:,]?\s+(?:the\s+)?["“]([^"”]{2,60})["”]\s*\)', re.I),
    re.compile(r'\(\s*the\s+["“]([^"”]{2,60})["”]\s*\)', re.I),
]

XREF_RX = re.compile(r"(?:סעיף|סעיפים|ס['׳]|clause|section)\s+(\d+(?:\.\d+)*)", re.I)
# אות הנספח עומדת לבדה: "נספח זה" או "נספח הבא" אינם "נספח ז" או "נספח ה"; גם Annex A ולא "Annex Agreement"
ANNEX_REF_RX = re.compile(r"נספח\s+([אבגדהוזחט](?:['׳](?![א-ת])|(?![א-ת]))|\d+)|(?:Exhibit|Schedule|Annex)\s+([A-H](?![A-Za-z])|\d+)")
ANNEX_HEAD_RX = re.compile(
    r"^\s*(?:נספח\s+([אבגדהוזחט](?:['׳](?![א-ת])|(?![א-ת]))|\d+)|(?:Exhibit|Schedule|Annex)\s+([A-H]|\d+))\s*[:\-–]?\s*(.{0,60})$",
    re.I)
# מספר סעיף בתחילת פסקה: "9." ו-"9.1." (כך כותב build_draft_docx), וגם "9.1" בלי נקודה, כמו בטיוטות שנבנו
# לפני האחדה. מספר ברמה אחת בלי סימן ("5 ימים") אינו מספר סעיף
CLAUSE_NUM_RX = re.compile(r"^(?:סעיף\s+)?(\d+(?:\.\d+)*)\s*[:\.\)]\s|^(?:סעיף\s+)?(\d+(?:\.\d+)+)\s")
# פתיח של פרק ההגדרות שחל גם על המבוא: מונח שמופיע במבוא לפני הפתיח מוגדר גם שם
DEF_SCOPE_RX = re.compile(r"לרבות\s+במבוא|ובמבוא\s+לו|including\s+(?:in\s+)?the\s+recitals", re.I)


def clause_num(p):
    m = CLAUSE_NUM_RX.match(p.strip())
    return (m.group(1) or m.group(2)) if m else None
# ציין חוסר: כל טקסט בסוגריים מרובעים, כמו שבונה הטיוטה מסמן ברקע ("[להשלים]", "[להשלים: כתובת]", "[שם]",
# "[ ]"), ו-TBD, XXX, קווים תחתונים ו-Lorem ipsum. גם "[להשלים: סכום]" נספר, ולא רק "[להשלים]" מדויק
# "[להשלים: ...]" בכל אורך (הסבר ארוך על נספח שיצורף הוא עדיין חוסר); סוגריים אחרים עד 80 תווים
PLACEHOLDER_RX = re.compile(
    r"\[(?:להשלים|to\s+complete)[^\[\]\n]*\]|\[[^\[\]\n]{0,80}\]|_{3,}|X{3,}|\bTBD\b|\bLorem ipsum\b|"
    r"<[^>\n]{0,30}>", re.I)
# תוויות קבועות בסוגריים שאינן חוסר: סימון "טעון בדיקה משפטית" של בונה הטיוטה, "לא אותר" בנספח המקורות,
# וסעיף שבוטל במכוון ("[Not Used]", "[בוטל]")
NON_GAP_LABELS = ("טעון בדיקה משפטית", "needs legal review", "להשלמה", "to be completed", NO_SOURCE_NOTE.lower(), NO_SOURCE_NOTE_EN.lower(), "לא אותר", "not found", "not used", "reserved",
                  "intentionally left blank", "intentionally omitted", "deleted", "בוטל", "נמחק", "שמור")
MONEY_RX = re.compile(CUR + r"\s*([\d,]+(?:\.\d+)?)|"
                      r"([\d,]{4,}(?:\.\d+)?)\s*" + CUR)
DATE_RX = re.compile(r"\b(\d{1,2})[./](\d{1,2})[./](\d{2,4})\b")
EMDASH_RX = re.compile(r"[—–]")
STALE_RX = re.compile(r"(?:להסכם|הסכם)\s+[א-ת]{2,}\s+מיום\s+\d{1,2}\.\d{1,2}\.\d{4}")


class Report(object):
    def __init__(self):
        self.items = []

    def add(self, level, area, msg, detail=None):
        self.items.append({"level": level, "area": area, "message": msg,
                           "detail": detail or []})

    def blocking(self):
        return [i for i in self.items if i["level"] == "חוסם"]

    def warnings(self):
        return [i for i in self.items if i["level"] == "אזהרה"]


# ------------------------------------------------------------------ בדיקות

def collect_definitions(text):
    """מחזיר את המונחים המוגדרים לפי סדר הופעתם, עם מיקום ההגדרה."""
    defs = OrderedDict()
    for rx in DEF_RX:
        for m in rx.finditer(text):
            term = m.group(1).strip()
            if 2 <= len(term) <= 60 and term not in defs:
                defs[term] = m.start()
    return defs


def check_definitions(text, rep):
    defs = collect_definitions(text)
    if not defs:
        rep.add("אזהרה", "מונחים מוגדרים",
                "לא אותרו מונחים מוגדרים במסמך. אם זה מסמך קצר זה תקין, אחרת יש לבדוק.")
        return defs
    unused, used_before, in_preamble = [], [], []
    scope = DEF_SCOPE_RX.search(text)
    if scope:
        # פרק ההגדרות: מהפתיח ועד ההגדרה האחרונה ברשימה ('"מונח" - פירוש')
        items = [m.start() for m in DEF_RX[1].finditer(text, scope.start())]
        sec = (scope.start(), (max(items) if items else scope.end()) + 200)
    for term, pos in defs.items():
        # ספירת שימושים מחוץ להגדרה עצמה
        hits = [m.start() for m in re.finditer(re.escape(term), text)]
        after = [h for h in hits if h > pos + len(term)]
        before = [h for h in hits if h < pos - 80]
        if not after:
            unused.append(term)
        # המונח מוגדר בפרק ההגדרות שחל גם על המבוא: כל שימוש לפני ההגדרה הוא במבוא או ברשימת ההגדרות
        if before and scope and sec[0] < pos <= sec[1]:
            in_preamble.append(term)
        elif before:
            used_before.append(term)
    if unused:
        rep.add("אזהרה", "מונחים מוגדרים",
                "%d מונחים הוגדרו ואינם משמשים בהמשך" % len(unused), unused[:20])
    if used_before:
        rep.add("אזהרה", "מונחים מוגדרים",
                "%d מונחים משמשים לפני שהוגדרו" % len(used_before), used_before[:20])
    if in_preamble:
        rep.add("מידע", "מונחים מוגדרים",
                "%d מונחים משמשים לפני הגדרתם, במבוא או ברשימת ההגדרות, והפתיח של פרק ההגדרות חל גם על המבוא"
                % len(in_preamble), in_preamble[:20])
    # מונח שהוגדר פעמיים בנוסחים שונים
    dup = [t for t, n in Counter(
        [m.group(1).strip() for rx in DEF_RX for m in rx.finditer(text)]).items() if n > 1]
    if dup:
        rep.add("חוסם", "מונחים מוגדרים",
                "מונח מוגדר יותר מפעם אחת. הגדרה כפולה יוצרת סתירה פרשנית", dup[:20])
    return defs


def check_crossrefs(paras, text, rep):
    existing = set()
    for p in paras:
        n = clause_num(p)
        if n:
            existing.add(n)
    if not existing:
        rep.add("אזהרה", "הפניות פנימיות",
                "לא אותר מספור סעיפים בטקסט. אם המספור אוטומטי ב-Word, "
                "יש לאמת את ההפניות ידנית.")
        return
    refs = Counter(m.group(1) for m in XREF_RX.finditer(text))
    dangling = sorted([r for r in refs if r not in existing],
                      key=lambda x: [int(y) for y in x.split(".")])
    if dangling:
        rep.add("חוסם", "הפניות פנימיות",
                "%d הפניות לסעיפים שאינם קיימים במסמך" % len(dangling),
                ["סעיף %s (מוזכר %d פעמים)" % (d, refs[d]) for d in dangling[:20]])
    dups = [n for n, c in Counter(
        [clause_num(p) for p in paras if clause_num(p)]).items() if c > 1]
    if dups:
        rep.add("חוסם", "מספור", "מספר סעיף מופיע יותר מפעם אחת", sorted(dups)[:20])
    # רצף המספור הראשי
    tops = sorted({int(e.split(".")[0]) for e in existing})
    gaps = [n for n in range(tops[0], tops[-1] + 1) if n not in tops] if tops else []
    if gaps:
        rep.add("אזהרה", "מספור", "פערים ברצף הסעיפים הראשיים",
                ["חסר סעיף %d" % g for g in gaps[:20]])


def check_annexes(paras, text, rep):
    referenced = set()
    for m in ANNEX_REF_RX.finditer(text):
        referenced.add((m.group(1) or m.group(2) or "").strip("'׳"))
    present = set()
    for p in paras:
        m = ANNEX_HEAD_RX.match(p.strip())
        if m:
            present.add((m.group(1) or m.group(2) or "").strip("'׳"))
    missing = sorted(referenced - present)
    orphan = sorted(present - referenced)
    if missing and present:
        # נספחים אחרים מצורפים בתוך המסמך: נספח שמוזכר ואין לו כותרת הוא הפניה שאינה מעוגנת
        rep.add("אזהרה", "נספחים",
                DECIDE + "נספחים מוזכרים בגוף ההסכם ואינם במסמך, אף שנספחים אחרים מצורפים בו. "
                         "יש לצרף אותם, או לקבוע במפורש שהם מסמך נפרד",
                ["נספח %s" % x for x in missing[:20]])
    elif missing:
        # נספח עשוי להיות קובץ נפרד, ולכן זו אזהרה ולא ממצא חוסם
        rep.add("אזהרה", "נספחים",
                "נספחים מוזכרים בגוף ההסכם ואין להם כותרת במסמך. "
                "אם הם קבצים נפרדים, יש לוודא שהם מצורפים למשלוח ושהשמות תואמים",
                ["נספח %s" % x for x in missing[:20]])
    if orphan:
        rep.add("אזהרה", "נספחים", "נספחים שמצורפים ואינם מוזכרים בגוף ההסכם",
                ["נספח %s" % x for x in orphan[:20]])


SIGBLOCK_RX = re.compile(r"ולראיה|על\s+החתום|חתימה|חותמת|שם\s*:|תפקיד\s*:|"
                         r"IN\s+WITNESS|signature|title\s*:|name\s*:", re.I)


def placeholder_matches(text):
    """כל מצייני החוסר בטקסט, אחד אחד. שורות חתימה ריקות אינן מצייני חוסר: מסמך חתום ידנית תמיד יכיל קווים
       תחתונים בבלוק החתימה, וסימונם כחוסר מייצר רעש שמכסה על חוסר אמיתי. גם תווית קבועה בסוגריים
       (NON_GAP_LABELS) ומספר בסוגריים ("[3]") אינם חוסר."""
    out = []
    for m in PLACEHOLDER_RX.finditer(text):
        tok = m.group(0)
        if tok.startswith("_"):
            ctx = text[max(0, m.start() - 90):m.start() + 90]
            if SIGBLOCK_RX.search(ctx):
                continue
        if tok.startswith("["):
            inner = tok[1:-1].strip()
            if inner.isdigit() or inner.lower() in NON_GAP_LABELS:
                continue
        out.append(m)
    return out


def count_placeholders(text):
    """**המקור היחיד למספר מצייני החוסר.** בונה הטיוטה, מילוי התבנית, דף הליווי ובקרת השלמות סופרים כאן,
       על הטקסט של הקובץ שהופק (docx_text), כך שכל דוח מציג את אותו מספר. סיכום שנכתב ביד מעתיק אותו
       מ-placeholders בדוח ה-JSON, ואינו סופר בעצמו."""
    return len(placeholder_matches(text))


def check_placeholders(text, rep):
    """הממצא מונה כל ציין חוסר (count_placeholders); הפירוט ממזג ציינים סמוכים להקשר אחד, כדי שיהיה קריא.
       פרט להשלים הוא של הלקוח ואינו חוסם את המסירה (core-contract.md, פרק 9: אחרי השאלות הטיוטה נמסרת נקייה,
       והפרטים הפתוחים מסומנים בצהוב ורשומים בדף הליווי). לכן הדרגה היא אזהרה, והמספר נכתב בדף הליווי ובצ'אט.
       חוסם נשאר רק מה שאסור שיימסר: קוד פנימי, שגיאת מבנה, עובדת עסקה חסרה, נוסח פנימי ונתיב מקומי."""
    ms = placeholder_matches(text)
    hits, last = [], -999
    for m in ms:
        if m.start() - last < 100:      # מיזוג ממצאים סמוכים להקשר אחד בפירוט
            continue
        last = m.start()
        hits.append(re.sub(r"\s+", " ", text[max(0, m.start() - 50):m.start() + 60]).strip())
    if ms:
        rep.add("אזהרה", "מצייני חוסר",
                "%d פרטים להשלים נותרו בטיוטה, מסומנים בצהוב. הם של הלקוח: נרשמים בדף הליווי ובהודעת המסירה, "
                "ואינם עוצרים את המסירה" % len(ms),
                hits[:15])
    return len(ms)


# חובה שדורשת מועד: המועד נאמר במספר (ימים, שעות, חודשים, תאריך) או מסומן להשלמה, ולעולם אינו נשמט בשקט בלשון
# עמומה ("ללא דיחוי", "בהקדם", "בזמן סביר", "promptly", "without undue delay"). כלל כללי לכל סוג חובה: הודעה, תיקון,
# תגובה, תשלום, מסירה, החזרה, דיווח. "מיד" לבדו ("מיד עם סיום ההסכם") הוא מועד תלוי אירוע ואינו נתפס.
VAGUE_TIME_RX = re.compile(
    r"(?:ללא|בלי|ובלי|וללא)\s+(?:כל\s+)?(?:דיחוי|שיהוי|עיכוב)|בהקדם(?:\s+האפשרי)?|(?:ב|תוך|בתוך)\s*זמן\s+סביר|"
    r"מוקדם\s+ככל\s+(?:ה)?(?:אפשר|ניתן)|בתוך\s+(?:פרק\s+)?זמן\s+(?:קצר|מתאים)|"
    r"\bwithout\s+(?:undue\s+|unreasonable\s+|any\s+)?delay\b|\bpromptly\b|\bas\s+soon\s+as\s+(?:reasonably\s+)?"
    r"(?:practicable|possible)\b|\bwithin\s+a\s+reasonable\s+(?:time|period)\b|\bin\s+a\s+timely\s+manner\b|"
    r"\bexpeditiously\b|\bforthwith\b", re.I)
_HE_NUM = (r"(?:אחד|אחת|שני|שתי|שניים|שתיים|שלוש|שלושה|ארבע|ארבעה|חמש|חמישה|שש|שישה|שבע|שבעה|שמונה|תשע|תשעה|עשר|עשרה|"
           r"(?:[א-ת]+\s+)?עשרה?|עשרים|שלושים|ארבעים|חמישים|שישים|שבעים|שמונים|תשעים|מאה)")
_EN_NUM = (r"(?:one|two|three|four|five|six|seven|eight|nine|ten|twelve|fourteen|fifteen|twenty|thirty|forty|forty-five|"
           r"sixty|ninety)")
TIME_BOUND_RX = re.compile(
    r"(?:\d+|" + _HE_NUM + r")\s*(?:\([^)]{1,12}\)\s*)?(?:ימים|ימי\s+עסקים|ימי\s+עבודה|יום|שעות|שעה|חודשים|חודש|שבועות|שבוע|שנים|שנה)\b|"
    r"\b(?:\d+|" + _EN_NUM + r")\s*(?:\([^)]{1,12}\)\s*)?(?:calendar\s+|business\s+|working\s+)?(?:days?|hours?|months?|weeks?|years?)\b|"
    r"\b\d{1,2}[./]\d{1,2}[./]\d{2,4}\b|עד\s+(?:ה)?יום\s|\bby\s+\d|\bno\s+later\s+than\b|לא\s+יאוחר\s+מ", re.I)


def check_time_bounds(paras, rep, template_paras=None):
    """פסקה שקובעת חובה בלשון זמן עמומה, בלי מועד במספר ובלי ציין חוסר: ממצא חוסם. התיקון ב-JSON: מספר
       (מתשובת הלקוח לשאלה אחת) או "[להשלים: המועד]" עם שורה בדף הליווי. בנוסח המאושר של תבנית האב (נוסח
       מאושר אינו משתנה) הממצא הוא אזהרה "נדרשת הכרעתך", כמו מקף ארוך בתבנית."""
    matchers = approved_matchers(template_paras) if template_paras else []
    new, approved = [], []
    for p in paras or []:
        # "[להשלמה]" (סימון "אין מקור", NON_GAP_LABELS) מסמן את החוסר בגלוי, כמו [להשלים], ולכן אינו ממצא
        if not VAGUE_TIME_RX.search(p) or TIME_BOUND_RX.search(p) or placeholder_matches(p) or "[להשלמה]" in p:
            continue
        snippet = re.sub(r"\s+", " ", p).strip()[:110]
        (approved if any(m.match(p) for m in matchers) else new).append(snippet)
    if new:
        rep.add("חוסם", "מועדים",
                "%d סעיפים קובעים חובה בלשון זמן עמומה (ללא דיחוי, בהקדם, בזמן סביר) בלי מספר ימים או שעות. "
                "מועד שהמקור לא קבע אינו נשמט בשקט: שאלה אחת ללקוח, או [להשלים: המועד] בגוף ושורה בדף הליווי" % len(new),
                new[:10])
    if approved:
        rep.add("אזהרה", "מועדים",
                "נדרשת הכרעתך: %d סעיפים מהנוסח המאושר של התבנית קובעים חובה בלשון זמן עמומה בלי מועד במספר. "
                "הנוסח לא שונה; לקבוע מועד או להשאיר" % len(approved), approved[:10])
    return len(new)


# ספירה שנכתבה בדף הליווי או בסיכום: "נותרו 25 מצייני [להשלים]", "25 פרטים [להשלים]", "12 placeholders"
COUNT_CLAIM_RX = re.compile(
    r"(\d+)\s+מצייני(?:\s+(?:חוסר|\[להשלים\]))?|"
    r"(\d+)\s+(?:פרטים|פריטים|שדות|מקומות)\s+(?:\[להשלים\]|להשלמה|חסרים)|"
    r"(\d+)\s+(?:open\s+)?placeholders?\b|"
    r"(\d+)\s+(?:items|fields|details|markers)\s+(?:\[to complete\]|to complete|missing)|"
    r"(?:מצייני\s+חוסר|placeholders)[^:\n\d]{0,20}:\s*(\d+)", re.I)


def check_cover_counts(paths, n, rep):
    """דף הליווי והסיכום מציגים את אותו מספר מצייני חוסר כמו הטיוטה. מספר אחר הוא ממצא חוסם: הדוחות
       סותרים זה את זה, והלקוח אינו יודע כמה פרטים עליו להשלים."""
    bad = []
    for p in paths or []:
        if not os.path.isfile(p):
            bad.append("%s: הקובץ לא נמצא" % os.path.basename(p))
            continue
        t = docx_text(p, limit=400000)[0] if p.lower().endswith(".docx") else \
            io.open(p, encoding="utf-8", errors="ignore").read()
        for m in COUNT_CLAIM_RX.finditer(t):
            k = int(next(g for g in m.groups() if g))
            if k != n:
                bad.append("%s: \"%s\" (בטיוטה %d)" % (os.path.basename(p), m.group(0).strip(), n))
    if bad:
        rep.add("חוסם", "מצייני חוסר",
                "ספירת מצייני החוסר בדף הליווי או בסיכום שונה מהספירה בטיוטה. המספר נלקח רק מ-placeholders "
                "בדוח הזה", bad[:10])


TEMPLATE_TAG_RX = re.compile(r"\{\{\s*([^{}]{1,60}?)\s*\}\}")


def check_template_tags(text, rep):
    """תגית {{...}} שנשארה בטיוטה היא משתנה של תבנית האב שלא קיבל ערך. בניגוד
       לקו תחתון, אין לה פירוש לגיטימי במסמך שיוצא, ולכן היא חוסמת תמיד, גם בבלוק החתימה."""
    tags = sorted(set(m.group(1) for m in TEMPLATE_TAG_RX.finditer(text)))
    if tags:
        rep.add("חוסם", "תגיות תבנית",
                "%d משתני תבנית נותרו בלי ערך. יש להשלים אותם בקובץ הערכים ולהריץ את המילוי שוב" % len(tags),
                ["{{%s}}" % t for t in tags[:20]])


# ------------------------------------------------------------------ בדיקה סמנטית: מנגנונים
# דוגמאות: "התמורה בגין שינוי תחושב לפי התעריפים שבהסכם", ואין בהסכם תעריפים; "כל מטלה אחרת
# בתמורה הקבועה" לצד תמורה נוספת בגין שינוי; הארכה עד חמש שנים בלי מחיר; סיום בלי חישוב יחסי באמצע אבן דרך;
# פיצוי מוסכם ריק בלי תקרה; הצעת הצד השני כנספח בלי החרגת תנאיה. הסקריפט מוצא את הדפוס; ההכרעה בידי עורך הדין.
DECIDE = "נדרשת הכרעתך: "

RATE_REF_RX = re.compile(
    r"(?:לפי|על\s+פי|בהתאם\s+ל|כמפורט\s+ב|כקבוע\s+ב)\s*(?:ה)?(?:תערי(?:ף|פ\w*)|מחירו(?:ן|נ\w*))|"
    r"(?:ה)?(?:תעריפים|תעריף|מחירון|מחירונים)\s+(?:ש(?:ב|נקבע|נקבעו)\w*|הקבוע\w*|המפורט\w*|המצור(?:ף|פ\w*))|"
    r"\b(?:in\s+accordance\s+with|according\s+to|per|at)\s+the\s+(?:applicable\s+)?"
    r"(?:rates?|price\s+list|fee\s+schedule|rate\s+card)\b", re.I)
RATE_WORD_RX = re.compile(r"תערי[פף]|מחירו[ןנ]|\brates?\b|price\s+list|fee\s+schedule|rate\s+card", re.I)
RATE_DEF_RX = re.compile(r'["“”״](?:ה)?(?:תערי(?:ף|פ\w*)|מחירו(?:ן|נ\w*)|Rates?|Price\s+List|Fee\s+Schedule)["“”״]', re.I)
RATE_HEAD_RX = re.compile(r"^\s*(?:נספח|Annex|Schedule|Exhibit)\b[^\n]{0,80}(?:תערי[פף]|מחירו[ןנ]|rate|price|fee)", re.I)
PER_UNIT_RX = re.compile(r"לשעה|לשעת\s+עבודה|ליום\s+עבודה|לחודש\s+עבודה|per\s+(?:hour|day|man[\s-]?day)|hourly",
                         re.I)
SCOPE_BASE_RX = re.compile(
    r"(?:\d+(?:\.\d+)?\s*%|אחוז\w*)\s*(?:מתוך\s+|מ)?(?:ה)?(?:היקף\s+ההתקשרות|ערך\s+(?:ה)?הסכם|ערך\s+ההתקשרות|"
    r"שווי\s+ההתקשרות)|(?:\d+(?:\.\d+)?\s*%|percent)\s+of\s+the\s+(?:total\s+)?contract\s+(?:value|price|sum)",
    re.I)
SCOPE_DEF_RX = re.compile(r'["“”״](?:היקף\s+ההתקשרות|ערך\s+(?:ה)?הסכם|ערך\s+ההתקשרות|שווי\s+ההתקשרות|'
                          r'Contract\s+(?:Value|Price|Sum))["“”״]', re.I)
SCOPE_TERM_RX = re.compile(r"היקף\s+ההתקשרות|ערך\s+(?:ה)?הסכם|ערך\s+ההתקשרות|שווי\s+ההתקשרות|contract\s+(?:value|"
                           r"price|sum)", re.I)
# "כל מטלה אחרת ... בתמורה הקבועה" מול "התמורה בגין שינוי ...": שני מנגנוני תמורה שאינם יכולים לחול יחד
ALL_IN_RX = re.compile(
    r"(?:כל|כלל)\s+(?:ה)?(?:מטלה|מטלות|שירות|שירותים|עבודה|עבודות)\s+(?:ה)?(?:אחרת|אחרים|אחרות|נוספת|נוספים|נוספות)"
    r"[^.]{0,200}?(?:בתמורה\s+הקבועה|ללא\s+(?:כל\s+)?תמורה\s+נוספת|בלי\s+(?:כל\s+)?תמורה\s+נוספת|"
    r"ללא\s+תוספת\s+(?:תשלום|תמורה)|בלי\s+תוספת\s+(?:תשלום|תמורה)|כלול\w*\s+בתמורה)|"
    r"any\s+(?:other|additional|further)\s+(?:tasks?|services|work)[^.]{0,200}?(?:at\s+no\s+(?:additional|extra)\s+"
    r"(?:cost|charge|fee)|(?:for|within)\s+the\s+fixed\s+(?:fee|price))", re.I)
EXTRA_PAY_RX = re.compile(
    r"(?:ה)?(?:תמורה|תשלום)\s+(?:בגין|עבור|בעד)\s+(?:ה)?(?:שינוי|הגדלה|תוספת|שירותים\s+נוספים|"
    r"עבוד(?:ה|ות)\s+נוספ(?:ת|ות)|מטל(?:ה|ות)\s+נוספ(?:ת|ות))|(?:תמורה|תשלום)\s+(?:נוסף|נוספת|נוספים)\s+"
    r"(?:בגין|עבור)|תחושב\s+לפי\s+(?:ה)?תערי[פף]|"
    r"(?:additional|extra)\s+(?:fees?|compensation|charges?|payment)\s+(?:for|in\s+respect\s+of)\s+(?:any\s+)?"
    r"(?:changes?|variations?|additional\s+services)", re.I)
RECONCILE_RX = re.compile(r"למעט|בכפוף\s+ל|except|subject\s+to|other\s+than", re.I)
FIXED_FEE_RX = re.compile(r"סכום\s+קבוע|תמורה\s+קבועה|(?:ה)?תמורה\s+הקבועה|מחיר\s+קבוע|fixed\s+(?:fee|price|sum)|"
                          r"lump[\s-]sum", re.I)
EXTENSION_RX = re.compile(r"(?:להאריך|הארכת|יוארך|יוארכו|תוארך)\s[^.]{0,120}?(?:תקופ|חודש|שנ)|"
                          r"(?:extend|renew)\w*\s[^.]{0,80}?(?:term|period)", re.I)
EXT_PRICE_RX = re.compile(
    r"(?:בתקופ(?:ת|ות)\s+(?:ה)?(?:הארכה|נוספות|ההארכה)|בכל\s+הארכה|לתקופ(?:ת|ות)\s+(?:ה)?הארכה|בהארכה)[^.]{0,200}?"
    r"(?:תמורה|תעריף|מחיר|הצמד|ישולם|תשולם)|(?:תמורה|תעריף|מחיר)[^.]{0,200}?(?:בתקופ(?:ת|ות)\s+(?:ה)?(?:הארכה|"
    r"נוספות|ההארכה)|לתקופ(?:ת|ות)\s+(?:ה)?הארכה|בהארכה)|(?:renewal|extension|extended)\s+(?:term|period)"
    r"[^.]{0,200}?(?:fees?|price|rates?|compensation)|(?:fees?|price|rates?|compensation)[^.]{0,200}?"
    r"(?:renewal|extension|extended)\s+(?:term|period)", re.I)
CONVENIENCE_RX = re.compile(
    r"(?:רשאית|רשאי|זכאית|זכאי)\s+(?:ל)?(?:סיים|לבטל|להביא\s+לסיום)[^.]{0,80}?(?:בכל\s+עת|לפי\s+שיקול\s+דעת|מכל\s+סיבה)|"
    r"terminat\w*[^.]{0,80}?(?:for\s+convenience|at\s+any\s+time|without\s+cause)", re.I)
MILESTONE_RX = re.compile(r"אב(?:ן|ני)\s+(?:ה)?דרך|milestones?", re.I)
# "יחסי" לבדו תופס גם "יחסי עובד ומעביד", ולכן רק בצירוף של חישוב
PRORATA_RX = re.compile(r"(?:באופן|חלק|בחלק|תמורה|תשלום|סכום)\s+יחסי\w*|יחסית\s+ל|לפי\s+החלק\s+(?:היחסי|שבוצע|"
                        r"שהושלם)|בשיעור\s+(?:ההתקדמות|הביצוע)|pro[\s-]?rata|proportion\w*", re.I)
LD_RX = re.compile(r"פיצוי(?:ים)?\s+מוסכ(?:ם|מ\w*)|liquidated\s+damages", re.I)
LD_OPERATIVE_RX = re.compile(r"ישלם|ישולם|תשלם|יחויב|ישולמו|\d|%|shall\s+pay|will\s+pay|payable", re.I)
CAP_RX = re.compile(r"תקר|לא\s+(?:י|ת)על(?:ה|ו)\s+על|לא\s+יותר\s+מ|עד\s+(?:ל)?(?:סך|סכום|שיעור)|"
                    r"בסך\s+(?:ה)?כול\s+לא|shall\s+not\s+exceed|\bcap(?:ped)?\b|maximum\s+aggregate|in\s+(?:the\s+)?aggregate",
                    re.I)
PROPOSAL_RX = re.compile(
    r"הצע(?:ת|תו)\s+(?:ה)?(?:יועץ|ספק|קבלן|נותן\s+השירות\w*|מציע|היועץ|הספק|הקבלן)?[^.]{0,80}?(?:מצורפת|כנספח|"
    r"חלק\s+בלתי\s+נפרד)|(?:ה)?הצעה[^.]{0,60}?(?:מצורפת|כנספח|חלק\s+בלתי\s+נפרד)|"
    r"(?:supplier|consultant|contractor|vendor|provider)['’]?s?\s+proposal[^.]{0,80}?(?:attached|schedule|annex|"
    r"exhibit|integral)", re.I)
PROPOSAL_WORD_RX = re.compile(r"הצע(?:ה|ת|תו)\b|proposal", re.I)
PROPOSAL_EXCL_RX = re.compile(
    r"לא\s+יחול\w*|אינ(?:ם|ו|ן|ה)\s+חלק|לא\s+יהי(?:ו|ה)\s+חלק|לא\s+יחייב\w*|(?:היקף|לוח\s+(?:ה)?זמנים|אנשי\s+"
    r"(?:ה)?צוות)[^.]{0,160}?בלבד|shall\s+not\s+apply|do(?:es)?\s+not\s+form\s+part|(?:is|are)\s+excluded|"
    r"shall\s+have\s+no\s+effect|solely\s+(?:for|as\s+to)", re.I)
BODY_PREVAILS_RX = re.compile(r"יגבר\s+(?:ה)?(?:אמור|נוסח)\s+ב(?:גוף\s+)?ההסכם|גוף\s+ההסכם\s+יגבר|הוראות\s+ההסכם\s+"
                              r"יגברו|(?:this\s+agreement|the\s+body\s+of\s+this\s+agreement)\s+shall\s+(?:prevail|govern)",
                              re.I)


def where(p):
    n = clause_num(p)
    body = re.sub(r"\s+", " ", p).strip()
    return ("סעיף %s: %s" % (n, body[len(n):].lstrip(". ")[:100])) if n else body[:110]


def check_mechanisms(paras, text, rep, role=None):
    """הפניה למנגנון שאינו מעוגן בהסכם, וסתירה בין מנגנוני התמורה, חוסמות מסירה. הסקריפט אינו קורא כוונה:
       הוא מוצא הפניה שאין לה עוגן ושני מנגנונים שאינם יכולים לחול יחד, וההכרעה בנוסח בידי עורך הדין.
       role: company_role_code של החברה (או None), לבדיקת הצעה שמצורפת כנספח."""
    # 1. "לפי התעריפים", "המחירון": עוגן הוא הגדרה, נספח שכותרתו תעריפים, או פסקה שבה התעריף עצמו (סכום, לשעה)
    rate_refs = [p for p in paras if RATE_REF_RX.search(p)]
    anchored = bool(RATE_DEF_RX.search(text)) or any(RATE_HEAD_RX.match(p) for p in paras) or any(
        RATE_WORD_RX.search(p) and (MONEY_RX.search(p) or PER_UNIT_RX.search(p)) for p in paras)
    if rate_refs and not anchored:
        rep.add("חוסם", "עיגון מנגנונים",
                "הפניה לתעריפים או למחירון שאינם קיימים בהסכם: אין הגדרה, נספח או סעיף שקובעים אותם. "
                "יש לקבוע את התעריפים (בגוף ההסכם או בנספח) או לנסח מנגנון אחר",
                [where(p) for p in rate_refs[:8]])
    # 2. אחוז מ"היקף ההתקשרות" כשהמונח אינו מוגדר ואינו נקוב בסכום
    base_refs = [p for p in paras if SCOPE_BASE_RX.search(p)]
    scope_anchored = bool(SCOPE_DEF_RX.search(text)) or any(
        SCOPE_TERM_RX.search(p) and MONEY_RX.search(p) and not SCOPE_BASE_RX.search(p) for p in paras)
    if base_refs and not scope_anchored:
        rep.add("אזהרה", "עיגון מנגנונים",
                DECIDE + "סכום שמחושב כאחוז מ\"היקף ההתקשרות\" או מערך ההסכם, והמונח אינו מוגדר. עם הארכות "
                         "ושינויי היקף הסכום אינו ניתן לקביעה. יש להגדיר את הבסיס (למשל סך התמורה לתקופה הראשונה)",
                [where(p) for p in base_refs[:8]])
    # 3. סתירה בין מנגנוני התמורה
    all_in = [p for p in paras if ALL_IN_RX.search(p) and not RECONCILE_RX.search(p)]
    extra = [p for p in paras if EXTRA_PAY_RX.search(p)]
    if all_in and [p for p in extra if p not in all_in]:
        rep.add("חוסם", "סתירה בין מנגנוני התמורה",
                "סעיף אחד קובע שכל מטלה אחרת או נוספת כלולה בתמורה הקבועה, וסעיף אחר מזכה בתמורה בגין שינוי "
                "או תוספת. יש להכריע ולנסח מנגנון אחד: מה כלול בתמורה, ומה מתומחר ולפי מה",
                [where(p) for p in (all_in + [p for p in extra if p not in all_in])[:8]])
    fixed = bool(FIXED_FEE_RX.search(text))
    # 4. הארכה בלי מחיר, כשהתמורה קבועה
    ext = [p for p in paras if EXTENSION_RX.search(p)]
    if fixed and ext and not any(EXT_PRICE_RX.search(p) for p in paras):
        rep.add("אזהרה", "עיגון מנגנונים",
                DECIDE + "ההסכם מאפשר הארכה, והתמורה קבועה לתקופה הראשונה, בלי מחיר או מנגנון מחיר לתקופת "
                         "ההארכה. יש לקבוע את התמורה בהארכה, או שההארכה מותנית בהסכמה בכתב על התמורה",
                [where(p) for p in ext[:6]])
    # 5. סיום מוקדם בלי חישוב יחסי, כשהתמורה לפי אבני דרך
    conv = [p for p in paras if CONVENIENCE_RX.search(p)]
    if conv and MILESTONE_RX.search(text) and not PRORATA_RX.search(text):
        rep.add("אזהרה", "עיגון מנגנונים",
                DECIDE + "סיום לפי שיקול דעת בלי מנגנון לחישוב יחסי של התמורה באמצע אבן דרך. יש לקבוע כיצד "
                         "משולמת אבן דרך שבביצוע (לפי החלק שהושלם ונמסר, או לא כלל)",
                [where(p) for p in conv[:6]])
    # 6. פיצוי מוסכם: לעולם לא ריק בלי תקרה
    for p in paras:
        q = re.sub(r"^\s*(?:סעיף\s+)?\d+(?:\.\d+)*\s*[.:)]?\s*", "", p)   # בלי מספר הסעיף: כותרת אינה סעיף אופרטיבי
        ph = placeholder_matches(q)
        if not LD_RX.search(q) or CAP_RX.search(q) or not (ph or LD_OPERATIVE_RX.search(q)):
            continue
        if ph:
            rep.add("חוסם", "פיצוי מוסכם",
                    "פיצוי מוסכם בלי סכום ובלי תקרה. כשהסכום לא נמסר: ציין מקום עם סכום מוצע ותקרה מוצעת, "
                    "והערה בדף הליווי: הוראת הדין החל על פיצוי מוסכם נבדקת במחקר העומק, מרשימת המקורות המאושרים", [where(p)])
        else:
            rep.add("אזהרה", "פיצוי מוסכם",
                    DECIDE + "פיצוי מוסכם בלי תקרה מצטברת", [where(p)])
    # 7. הצעת הצד השני כנספח: מה ממנה חל, ומה גובר. כשהחברה היא הצד שמגיש את ההצעה (נותן השירות, הספק,
    # היועץ), ההצעה היא שלנו, ואין להחריג ממנה את תנאינו שלנו
    prop = [p for p in paras if PROPOSAL_RX.search(p)]
    if prop and not company_gives(role):
        excl = any(PROPOSAL_WORD_RX.search(p) and PROPOSAL_EXCL_RX.search(p) for p in paras)
        prev = bool(BODY_PREVAILS_RX.search(text))
        if not (excl and prev):
            missing = ([] if excl else ["אין החרגה של התנאים הכלליים, ההסתייגויות והגבלת האחריות שבהצעה"]) + \
                      ([] if prev else ["אין הוראה שבסתירה גוף ההסכם גובר על ההצעה"])
            rep.add("אזהרה", "הצעת הצד השני כנספח",
                    DECIDE + "הצעה משולבת בהסכם. כשהיא של הצד השני, ממנה חלים רק ההיקף, הצוות ולוח הזמנים: "
                    + "; ".join(missing), [where(p) for p in prop[:6]])


# ------------------------------------------------------------------ שאריות של טופס ציבורי
# סעיף שמקורו בטופס של גוף ציבורי, או בדרישה שחלה רק על גוף ציבורי, נכנס רק כשאחד הצדדים הוא גוף ציבורי: החברה
# לפי הפרופיל או לפי התפקיד שלה (contracting_authority), או הצד שכנגד (meta.counterparty_public_body בטיוטה,
# --counterparty-public-body, או bidder: החברה מציעה בהליך תחרותי של הגוף המזמין), או כשהמשתמש ביקש אותו
# (--keep-public-form). "חברה ציבורית (נסחרת בבורסה)" **אינה** גוף ציבורי: כללי העסקאות של גופים ציבוריים חלים על
# המדינה, רשויות מקומיות, חברות ממשלתיות, תאגידים סטטוטוריים וגופים מתוקצבים (נקבע במחקר העומק)
PUBLIC_BODY_FORMS = {
    "חברה ממשלתית", "גוף ציבורי או משרד ממשלתי", "רשות מקומית", "תאגיד סטטוטורי",
    "מוסד להשכלה גבוהה או אוניברסיטה", "גוף ציבורי (משרד ממשלתי, רשות מקומית, תאגיד סטטוטורי)",
    "Government company", "Public body or government ministry", "Local authority (municipality or local council)",
    "Statutory corporation", "University or higher education institution",
    "Public body (government ministry, local authority, statutory corporation)"}
PUBLIC_STRONG = (
    (re.compile(r"הצהרה\s+לפי[^.\n]{0,60}גופים\s+ציבוריים|declaration\s+(?:under|pursuant\s+to)[^.\n]{0,60}"
                r"(?:public\s+bod|public\s+procurement|government\s+contract)", re.I),
     "הצהרה לפי כללי העסקאות של גופים ציבוריים"),
    (re.compile(r"ועדת\s+(?:ה)?מכרזים|ועדת\s+רכש|מסמכי\s+(?:ה)?מכרז|tender\s+committee|procurement\s+committee|"
                r"tender\s+documents", re.I), "הוראות של הליך תחרותי ציבורי"),
    (re.compile(r"נוהלי\s+רכש\s+(?:ממשלתי|ציבורי)|(?:government|public)\s+procurement\s+(?:circular|directive|manual|rules)",
                re.I), "נוהלי רכש של גוף ציבורי"),
)
# ערבות בנקאית לבדה אינה שארית: היא סעיף רגיל בהסכמים רבים. היא מדווחת רק לצד סימן חזק
PUBLIC_SOFT = (
    (re.compile(r"ערבות\s+(?:בנקאית|ביצוע|אוטונומית|מכרז)|(?:bank|performance)\s+guarantee", re.I),
     "ערבות בנקאית או ערבות ביצוע, לצד סימנים של טופס ציבורי"),
)
# company_role_code (ps1-playbook-identity-scope.md) שמלמד מי הגוף הציבורי: contracting_authority, החברה היא הגוף
# המזמין; bidder, החברה מציעה בהליך תחרותי, והגוף המזמין הוא הצד שכנגד
COMPANY_PUBLIC_ROLES = {"contracting_authority"}
COUNTERPARTY_PUBLIC_ROLES = {"bidder", "מציע"}
# הצד שמגיש הצעה (מבנה, לא סוג הסכם): bidder או מציע. אין רשימת תפקידים של "צד נותן" לפי סוגי הסכם
GIVING_ROLES = {"bidder", "מציע", "proposer", "submitting_party"}


def _role(role):
    return str(role or "").strip().lower()


def company_gives(role):
    """האם החברה היא הצד הנותן (מגיש ההצעה), לפי company_role_code או תווית המרשם. None או mutual: לא."""
    return _role(role) in GIVING_ROLES


def is_public_body(profile):
    """החברה גוף ציבורי לפי הפרופיל: organization_type מהצורות הציבוריות של ההקמה, או public_body מפורש."""
    p = profile or {}
    if p.get("public_body") is True:
        return True
    return str(p.get("organization_type") or "").strip() in PUBLIC_BODY_FORMS


def public_party(profile, counterparty_public=None, role=None):
    """האם אחד הצדדים הוא גוף ציבורי: החברה (הפרופיל, או contracting_authority) או הצד שכנגד
    (counterparty_public, או bidder)."""
    r = _role(role)
    return bool(is_public_body(profile) or r in COMPANY_PUBLIC_ROLES or counterparty_public
                or r in COUNTERPARTY_PUBLIC_ROLES)


def draft_facts(path):
    """(counterparty_public_body, company_role_code) מ-draft.json (meta) או מקובץ הערכים של התבנית (שורש).
    counterparty_public_body: True או False כשהקובץ נקרא (שדה חסר הוא False), None כשלא נקרא."""
    try:
        d = json.load(io.open(path, encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None, None
    if not isinstance(d, dict):
        return None, None
    meta = d.get("meta") if isinstance(d.get("meta"), dict) else {}
    cp = meta.get("counterparty_public_body", d.get("counterparty_public_body"))
    role = meta.get("company_role_code", d.get("company_role_code"))
    return bool(cp), (str(role).strip() if role else None)


def check_public_form(paras, rep, profile=None, keep=False, counterparty_public=None, role=None):
    """profile: פרופיל-לקוח.json (None כשלא נמסר). keep: המשתמש ביקש במפורש סעיף כזה.
    counterparty_public: True כשהצד שכנגד גוף ציבורי, False כשידוע שאינו, None כשלא נמסר. role: company_role_code."""
    if public_party(profile, counterparty_public, role):
        return
    strong = [(lbl, where(p)) for p in paras for rx, lbl in PUBLIC_STRONG if rx.search(p)]
    soft = [(lbl, where(p)) for p in paras for rx, lbl in PUBLIC_SOFT if rx.search(p)] if strong else []
    if keep:
        if strong:
            rep.add("מידע", "שאריות טופס ציבורי",
                    "סעיפים שמקורם בטופס של גוף ציבורי, ונשארו לבקשת המשתמש",
                    ["%s (%s)" % (w, l) for l, w in (strong + soft)[:10]])
        return
    if not strong:
        return
    detail = ["%s (%s)" % (w, l) for l, w in (strong + soft)[:10]]
    if profile is None:
        rep.add("אזהרה", "שאריות טופס ציבורי",
                DECIDE + "סעיפים שחלים רק כשאחד הצדדים גוף ציבורי. בלי --profile לא נבדק אם החברה גוף ציבורי; "
                         "אם אף צד אינו גוף ציבורי, הסעיפים אינם נכנסים ומוצעים כאפשרות בדף הליווי", detail)
    elif counterparty_public is None:
        rep.add("אזהרה", "שאריות טופס ציבורי",
                DECIDE + "סעיפים שחלים רק כשאחד הצדדים גוף ציבורי. החברה אינה גוף ציבורי לפי הפרופיל (%s), ולא נמסר "
                         "אם הצד שכנגד גוף ציבורי (--draft-json או --counterparty-public-body). אם הוא גוף ציבורי, "
                         "הסעיפים במקומם; אם לא, הם אינם נכנסים ומוצעים כאפשרות בדף הליווי"
                % (profile.get("organization_type") or "לא צוין"), detail)
    else:
        rep.add("חוסם", "שאריות טופס ציבורי",
                "סעיפים שמקורם בטופס של גוף ציבורי, או בדרישה שחלה רק על גוף ציבורי, ואף אחד מהצדדים אינו גוף "
                "ציבורי: החברה לפי הפרופיל (%s), והצד שכנגד לפי הטיוטה. הסעיף אינו נכנס: מוצע כאפשרות בדף "
                "הליווי, או נשאר רק לבקשת המשתמש" % (profile.get("organization_type") or "לא צוין"), detail)


def check_amounts_dates(text, rep):
    nums = [m.group(1) or m.group(2) for m in MONEY_RX.finditer(text)]
    norm = [n.replace(",", "") for n in nums if n]
    dupes = [n for n, c in Counter(norm).items() if c > 1]
    if dupes:
        rep.add("מידע", "סכומים",
                "סכומים החוזרים יותר מפעם אחת. יש לוודא שהחזרה מכוונת ואינה סתירה",
                [d for d in dupes[:12]])
    bad = []
    for m in DATE_RX.finditer(text):
        d, mo, y = int(m.group(1)), int(m.group(2)), m.group(3)
        if mo > 12 or d > 31:
            bad.append(m.group(0))
        elif len(y) == 2:
            bad.append(m.group(0) + " (שנה דו ספרתית)")
    if bad:
        rep.add("אזהרה", "תאריכים", "תאריכים בעייתיים או לא חד משמעיים", bad[:15])


def approved_matchers(template_paras):
    """פסקאות התבנית שיש בהן מקף ארוך, כתבניות התאמה: הטקסט כלשונו, ובמקום כל
       תגית {{...}} כל ערך שמולא בה. פסקה בטיוטה שתואמת אחת מהן היא נוסח מאושר."""
    out = []
    for tp in template_paras:
        if not EMDASH_RX.search(tp):
            continue
        parts = TEMPLATE_TAG_RX.split(tp)
        literal = [re.escape(x) for i, x in enumerate(parts) if i % 2 == 0]
        out.append(re.compile(r"\A" + ".*?".join(literal) + r"\Z", re.S))
    return out


def check_style(text, rep, hebrew, paras=None, template_paras=None):
    """מקף ארוך אסור בטקסט שאנחנו כותבים, **לא בנוסח המאושר של הלקוח.** טיוטה
       שמולאה מתבנית אב שומרת את נוסח התבנית כלשונו, ואם יש בו מקפים ארוכים,
       שינויים היה שבירה של הכלל שנוסח מאושר אינו משתנה. לכן, כשנמסרה התבנית:
       מקף בפסקה שתואמת את התבנית הוא אזהרה, ומקף בטקסט חדש (סעיף שהוחלף או נוסף)
       נשאר חוסם. בלי תבנית, כל מקף חוסם, כמו קודם."""
    if hebrew:
        n = len(EMDASH_RX.findall(text))
        if n and template_paras is not None and paras is not None:
            matchers = approved_matchers(template_paras)
            approved, new = 0, []
            for dp in paras:
                k = len(EMDASH_RX.findall(dp))
                if not k:
                    continue
                if any(m.match(dp) for m in matchers):
                    approved += k
                else:
                    new.append(dp)
            if new:
                rep.add("חוסם", "סגנון",
                        "%d מקפים ארוכים בטקסט שנכתב לטיוטה ואינו מהתבנית. יש להחליף בפסיק, בנקודה או בנקודתיים"
                        % sum(len(EMDASH_RX.findall(x)) for x in new),
                        [x[:90] for x in new[:8]])
            if approved:
                rep.add("אזהרה", "סגנון",
                        "%d מקפים ארוכים בנוסח המאושר של התבנית. לא שונו, כי נוסח מאושר אינו משתנה; "
                        "להסרתם יש לעדכן את התבנית עצמה" % approved)
        elif n:
            rep.add("חוסם", "סגנון",
                    "%d מקפים ארוכים במסמך עברי. יש להחליף בפסיק, בנקודה או בנקודתיים" % n)
    stale = [m.group(0) for m in STALE_RX.finditer(text)]
    if stale:
        rep.add("מידע", "שמות תקדים",
                "הפניות להסכמים אחרים בגוף המסמך. יש לוודא שאינן שריד מתבנית",
                list(dict.fromkeys(stale))[:12])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("draft")
    ap.add_argument("--json")
    ap.add_argument("--strict", action="store_true",
                    help="אזהרה נחשבת ממצא חוסם")
    ap.add_argument("--template",
                    help="master.docx שממנו מולאה הטיוטה: מקף ארוך בנוסח המאושר הוא אזהרה ולא חוסם")
    ap.add_argument("--profile", help="פרופיל-לקוח.json: האם החברה גוף ציבורי (שאריות של טופס ציבורי)")
    ap.add_argument("--draft-json", help="draft.json של הטיוטה (או קובץ הערכים של התבנית): "
                                         "meta.counterparty_public_body ו-meta.company_role_code")
    ap.add_argument("--counterparty-public-body", action="store_true",
                    help="הצד שכנגד גוף ציבורי (כשאין draft.json, למשל בטיוטה שמולאה מתבנית)")
    ap.add_argument("--role", help="company_role_code של החברה מהפלייבוק (bidder, contracting_authority, "
                                   "service_provider ...)")
    ap.add_argument("--cover", nargs="+", help="דף הליווי והסיכום (docx, md, txt): הספירה שבהם מול הטיוטה")
    ap.add_argument("--keep-public-form", action="store_true",
                    help="המשתמש ביקש במפורש סעיף מטופס של גוף ציבורי: הממצא יורד לרמת מידע")
    ap.add_argument("--variance-map", help="variance-map.json של המשפחה: עקיבות של סעיפים אופציונליים, נוסחים "
                                           "חלופיים וקבועים (דורש --draft-json)")
    ap.add_argument("--deal-card", help="כרטיס העסקה: קובץ הטיוטה (cover.facts, meta.parties), negotiation_state.json "
                                        "של העסקה, או {\"facts\": [...]}: כל עובדה בו חייבת להופיע בטיוטה")
    ap.add_argument("--core", help="playbook-core.json שבשימוש: כל כלל Required מכוסה בטיוטה, ואף מזהה כלל אינו "
                                   "בטקסט שהלקוח רואה")
    ap.add_argument("--case-law-connector", action="store_true",
                    help="מחבר פסיקה סגור שהלקוח חיבר זמין בהרצה (כלל 1.1). בלעדיו, אזכור פסיקה בטיוטה או "
                         "בדף הליווי הוא ממצא חוסם")
    args = ap.parse_args()
    if args.json:
        guard_out(args.json, [args.draft, args.template, args.profile, args.draft_json, args.deal_card, args.core]
                  + list(args.cover or []))
    profile = None
    if args.profile:
        try:
            profile = json.load(io.open(args.profile, encoding="utf-8-sig"))
        except (OSError, ValueError):
            print("הפרופיל לא נקרא: %s" % args.profile)
            sys.exit(2)

    counterparty_public, role = None, args.role
    if args.draft_json:
        counterparty_public, dj_role = draft_facts(args.draft_json)
        if counterparty_public is None:
            print("קובץ הטיוטה לא נקרא: %s" % args.draft_json)
            sys.exit(2)
        role = role or dj_role
    if args.counterparty_public_body:
        counterparty_public = True

    if not os.path.isfile(args.draft):
        print("הקובץ לא נמצא: %s" % args.draft)
        sys.exit(2)
    if args.draft.lower().endswith(".docx"):
        text = docx_text(args.draft, limit=400000)[0]
        paras = docx_paragraphs(args.draft, limit=20000)
    else:
        text = io.open(args.draft, encoding="utf-8", errors="ignore").read()
        paras = text.split("\n")
    if not text.strip():
        print("לא הופק טקסט מהמסמך.")
        sys.exit(2)

    hebrew = len(re.findall(r"[א-ת]", text)) > len(re.findall(r"[A-Za-z]", text))
    rep = Report()
    check_definitions(text, rep)
    check_crossrefs(paras, text, rep)
    check_annexes(paras, text, rep)
    n_gaps = check_placeholders(text, rep)
    if args.cover:
        check_cover_counts(args.cover, n_gaps, rep)
    check_template_tags(text, rep)
    check_mechanisms(paras, text, rep, role)
    check_public_form(paras, rep, profile, args.keep_public_form, counterparty_public, role)
    check_amounts_dates(text, rep)
    cl_sources = [(os.path.basename(args.draft), text)]
    for cp in args.cover or []:
        if os.path.isfile(cp):
            cl_sources.append((os.path.basename(cp), docx_text(cp, limit=400000)[0] if cp.lower().endswith(".docx")
                               else io.open(cp, encoding="utf-8", errors="ignore").read()))
    check_case_law(cl_sources, rep, args.case_law_connector)
    cover_names = {os.path.basename(cp) for cp in args.cover or []}
    check_hold_and_codes(cl_sources, rep, cover_names)
    djs = None
    if args.draft_json and os.path.isfile(args.draft_json):
        try:
            djs = json.load(io.open(args.draft_json, encoding="utf-8-sig"))
        except (OSError, ValueError):
            djs = None
    if isinstance(djs, dict) and djs.get("clauses"):
        cover_text = " ".join(t for n, t in cl_sources if n in cover_names) if cover_names else None
        check_sources_shown(djs, cover_text, rep)
        check_outside_basis(djs, cover_text, rep)
    if args.deal_card:
        check_deal_card(args.deal_card, text, rep)
    if args.core:
        check_core(args.core, text, djs, cl_sources, rep)
    if args.variance_map:
        try:
            vmap = json.load(io.open(args.variance_map, encoding="utf-8"))
            dj = json.load(io.open(args.draft_json, encoding="utf-8")) if args.draft_json else {}
        except (OSError, ValueError):
            print("מפת השונות או קובץ הטיוטה לא נקראו: %s" % args.variance_map)
            sys.exit(2)
        check_variance(text, dj, vmap, rep)
    template_paras = None
    if args.template:
        if not os.path.isfile(args.template):
            print("התבנית לא נמצאה: %s" % args.template)
            sys.exit(2)
        template_paras = docx_paragraphs(args.template, limit=20000)
    check_time_bounds(paras, rep, template_paras)
    check_style(text, rep, hebrew, paras, template_paras)

    print("בדיקת שלמות: %s" % os.path.basename(args.draft))
    order = {"חוסם": 0, "אזהרה": 1, "מידע": 2}
    for it in sorted(rep.items, key=lambda x: order.get(x["level"], 3)):
        print("  [%s] %s: %s" % (it["level"], it["area"], it["message"]))
        for d in it["detail"][:8]:
            print("        %s" % d)
    if not rep.items:
        print("  לא נמצאו ממצאים.")
    print("סיכום: %d חוסמים, %d אזהרות, %d מצייני חוסר" % (len(rep.blocking()), len(rep.warnings()), n_gaps))

    if args.json:
        io.open(args.json, "w", encoding="utf-8").write(json.dumps(
            {"file": os.path.basename(args.draft), "hebrew": hebrew,
             "findings": rep.items, "placeholders": n_gaps,
             "blocking": len(rep.blocking()), "warnings": len(rep.warnings())},
            ensure_ascii=False, indent=2))

    fail = len(rep.blocking()) or (args.strict and len(rep.warnings()))
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
