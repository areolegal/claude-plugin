#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""מחקר השוק של בונה הפלייבוק, בקוד ולא בשיקול דעת: הטווח, הבדיקות, הקישורים, ההודעה והרשת.

עד עכשיו המודל חישב את הטווח, בדק את הקישורים וכתב את הודעת המסירה בעצמו,
וכל הרצה יצאה קצת אחרת: "מקובל" על שני מקורות, "לטובתם" שהגנה על החברה יותר
מנקודת המפגש, צהוב זהה לירוק, ומספרים שונים בצ'אט וב-Word (הערות הפלייבוק 5.5,
שינויים 35, 38, 57, 60, 63, 72, 73, 82 ו-83; `market-research.md`).

* `ranges` - הטווח לכל נושא מ-`coding[]` ו-`source_refs[]`: שלוש נקודות
  (לטובתנו, באמצע, לטובתם), כל אחת רק עם שלושה מקורות נספרים מגופים שונים
  ומתבניות שונות; "לטובתם" נמדדת רק ממקור שיכול להעיד עליה, ואחרת "לא נמדד";
  שתיקה כדרגה; הצהוב כשנקודת המפגש שווה לירוק; תווית הוודאות לפי הטבלה; ומתי
  מותר לכתוב "מקובל". נכתב ל-`market_research.ranges[]` ול-`counts`.
* `check` - מה שהבודק פוסל: "מקובל" בלי נקודה שעומדת בכלל, אדום בבסיס שוק
  שנשען על "לטובתם" שלא נמדדה, פלייבוק שנשען על השוק בלי תווית ובלי הודעת
  שקיפות, המשפט "כל עמדה בו היא הצעה של Areo" כשיש ירוק מתבנית של החברה,
  מספרים בהודעה שאינם הספירה, קישורים שנבדקו לפני שה-Word נבנה, ומסירה סופית
  עם נימוק בטיוטה בלי `pass_b_stop_reason`.
* `links` - כל קישור נבדק שוב, אחרי שה-Word והארטיפקט נבנו ולפני ההודעה, דרך
  שכבת הרשת האחת. `link_checked_at` נרשם לכל רשומה; קישור שנכשל הופך את המקור
  ל"אותר, לא נקרא", והטווח מחושב מחדש.
* `message` - הודעת המסירה בתבנית הקבועה של `market-research.md`, "שקיפות":
  התווית, המשפט הקבוע לפי המסלול (מהספירה), בבנייה לבקשת הנושא ונותן "מה
  נבנה" ועד שלוש החלטות, ואז המקורות עם קישורים לחיצים, הטווח לכל נושא, מה לא
  נמצא, מה לא אומת והמגבלות. נשמרת ב-`market_research.disclosure`.
* `fetch` - בקשה אחת לרשת, דרך `common/net.py`, אחרי בדיקת השאילתה: אין בה
  רצף מילים מההסכמים, שם צד, שם הלקוח, שם מוצר או פרויקט מהפרופיל, או מספר
  מההסכמים. שם חוק מהרשימה הסגורה מותר רק ב-`--purpose legal`. העותק נשמר
  ב-`market-research/sources/` של המשפחה.

    python3 scripts/market_research.py ranges  --model playbook-model.json
    python3 scripts/market_research.py check   --model playbook-model.json [--word <הפלייבוק>.docx] [--final]
    python3 scripts/market_research.py links   --model playbook-model.json --family-dir <playbooks/<family>>
    python3 scripts/market_research.py message --model playbook-model.json [--out הודעה.md]
    python3 scripts/market_research.py fetch   --family-dir <...> --source-id W1 --url <...> --purpose market \\
        --query "<השאילתה>" --corpus <חילוץ.json> --profile <פרופיל-לקוח.json>

קוד יציאה: **0** תקין, **3** יש ממצא (בדיקה שנכשלה, קישור שנכשל, שאילתה
שנעצרה), **2** קלט חסר.
"""
import argparse
import datetime as _dt
import io
import json
import os
import re
import sys
import tempfile
from collections import Counter

import areo_lib  # noqa: F401  מוסיף את areolegal/lib לנתיב הייבוא

from playbook import market_counts as MC  # noqa: E402
from playbook import status as S  # noqa: E402

LEVELS = (2, 1, 0, -1, -2)
OURS_POOL = ("same_side", "negotiated", "neutral_model")
MIDDLE_POOL = ("negotiated", "neutral_model")
THEIRS_POOL = ("other_side", "negotiated", "neutral_model")
BALANCED = ("negotiated", "neutral_model")
NOT_READ = ("located_not_read", "excluded", "blocked")
MIN_SOURCES = 3
OLD_YEARS = 7
CERTAINTY = {"high": "ודאות גבוהה", "medium": "ודאות בינונית", "low": "ודאות נמוכה", "expert": "הערכת מומחה"}
NOT_MEASURED = "לא נמדד: אין מקור מהצד השני"
ALL_AREO = "כל עמדה בו היא הצעה של Areo"
TEMPLATE_BASIS = ("own_paper_repeated", "template")
MARKET_BASIS = ("market_standard",)
STOP_REASONS = ("client_stop", "switch_component", "cannot_continue", "build_request")


# --------------------------------------------------------------------------- עזר
def load(path, what):
    if not path or not os.path.exists(path):
        print("%s אינו קיים: %s" % (what, path))
        raise SystemExit(2)
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save(path, data):
    with io.open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)


def now_iso():
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def he_date(iso):
    try:
        return _dt.date.fromisoformat(str(iso)[:10]).strftime("%d.%m.%Y")
    except ValueError:
        return str(iso or "")


def year_of(d):
    m = re.match(r"(\d{4})", str(d or ""))
    return int(m.group(1)) if m else None


# --------------------------------------------------------------------------- הטווח
def counted_ref(ref):
    """מקור נספר: נקרא, יש לו תאריך, ומקור ממאגר מצרף נבדק מול המקור המקורי."""
    if not ref or ref.get("read_status") in NOT_READ or not ref.get("doc_date"):
        return False
    if ref.get("located_via") == "aggregator" and not ref.get("verified_against_original"):
        return False
    return ref.get("drafted_by") not in (None, "unknown")


def level_of(c, silence_rank):
    if c.get("special") == "silent" or c.get("level") == "silence":
        return "silence" if silence_rank is not None else None
    lv = c.get("level")
    return lv if lv in LEVELS else None


def rank(level, silence_rank):
    return silence_rank if level == "silence" else level


def pick(sources, refs):
    """מקורות מגופים שונים ומתבניות שונות: כל גוף וכל משפחת תבנית נספרים פעם אחת."""
    bodies, families, out = set(), set(), []
    for sid in sorted(sources):
        r = refs[sid]
        b = (r.get("issuing_body") or sid).strip().lower()
        f = (r.get("template_family") or sid).strip().lower()
        if b in bodies or f in families:
            continue
        bodies.add(b)
        families.add(f)
        out.append(sid)
    return out


def topic_points(topic, coding, refs, silence_rank=None):
    by_level, uncertain = {}, []
    for c in coding:
        if c.get("topic") != topic:
            continue
        ref = refs.get(c.get("source_id"))
        if not counted_ref(ref) or c.get("special") in ("redacted", "not_relevant"):
            continue
        if c.get("status") == "uncertain":
            uncertain.append(c["source_id"])
            continue
        if c.get("status") not in ("agreed", "resolved"):
            continue
        lv = level_of(c, silence_rank)
        if lv is None:
            continue
        by_level.setdefault(lv, []).append(c["source_id"])
    return by_level, uncertain


def point_for(by_level, refs, pool, order, silence_rank, mode=False):
    cands = []
    for lv, sids in by_level.items():
        chosen = pick([s for s in sids if refs[s].get("drafted_by") in pool], refs)
        if len(chosen) >= MIN_SOURCES:
            cands.append((lv, chosen))
    if not cands:
        return None
    if mode:   # השכיחה; בשוויון, הקרובה לאיזון
        cands.sort(key=lambda x: (-len(x[1]), abs(rank(x[0], silence_rank) or 0)))
    else:
        cands.sort(key=lambda x: rank(x[0], silence_rank) * (1 if order == "max" else -1), reverse=True)
    lv, sids = cands[0]
    return {"level": lv, "source_ids": sids}


def certainty(point, refs, question, research_year, uncertain, by_level, silence_rank):
    if not point or uncertain:
        return CERTAINTY["expert"]
    rs = [refs[s] for s in point["source_ids"]]
    flaws = 0
    if len({r.get("source_type") for r in rs}) < 2:
        flaws += 1
    juris = (question or {}).get("jurisdiction")
    if juris and any(r.get("jurisdiction") and r.get("jurisdiction") != juris for r in rs):
        flaws += 1
    if research_year and any((year_of(r.get("doc_date")) or research_year) < research_year - OLD_YEARS for r in rs):
        flaws += 1
    here = rank(point["level"], silence_rank)
    if any(lv != point["level"] and abs((rank(lv, silence_rank) or 0) - here) == 1 for lv in by_level):
        flaws += 1
    balanced = any(r.get("drafted_by") in BALANCED for r in rs)
    if flaws == 0 and balanced:
        return CERTAINTY["high"]
    if flaws <= 1:
        return CERTAINTY["medium"]
    return CERTAINTY["low"]


def accepted_ok(point, refs, question):
    """"מקובל": שלושה מקורות נספרים מגופים ומתבניות שונים, מאותו סוג הסכם, ואחד מהם מנוהל או מאוזן."""
    if not point:
        return False
    rs = [refs[s] for s in point["source_ids"]]
    types = {(question or {}).get("agreement_type_he"), (question or {}).get("agreement_type_en")} - {None}
    same_type = all(not types or r.get("agreement_type") in types for r in rs)
    return len(rs) >= MIN_SOURCES and same_type and any(r.get("drafted_by") in BALANCED for r in rs)


def compute_ranges(model):
    mr = model.setdefault("market_research", {})
    refs = {r["source_id"]: r for r in mr.get("source_refs") or [] if r.get("source_id")}
    coding = mr.get("coding") or []
    question = mr.get("question") or {}
    research_year = year_of(mr.get("research_date"))
    sheets = {s.get("topic"): s for s in mr.get("coding_sheets") or []}
    old = {r.get("topic"): r for r in mr.get("ranges") or []}
    topics = []
    for c in coding:
        if c.get("topic") and c["topic"] not in topics:
            topics.append(c["topic"])
    ranges = []
    for topic in topics:
        silence_rank = (sheets.get(topic) or {}).get("silence_level")
        silence_rank = silence_rank if silence_rank in LEVELS else None
        by_level, uncertain = topic_points(topic, coding, refs, silence_rank)
        ours = point_for(by_level, refs, OURS_POOL, "max", silence_rank)
        middle = point_for(by_level, refs, MIDDLE_POOL, None, silence_rank, mode=True)
        has_other = any(refs[s].get("drafted_by") == "other_side" for sids in by_level.values() for s in sids)
        theirs = point_for(by_level, refs, THEIRS_POOL if has_other else BALANCED, "min", silence_rank)
        theirs_note = None
        if not has_other:
            cap = middle or ours
            if theirs is None or (cap and rank(theirs["level"], silence_rank) > rank(cap["level"], silence_rank)):
                theirs, theirs_note = None, NOT_MEASURED
        if ours and middle and ours["level"] == middle["level"]:
            yellow = ("theirs" if theirs and rank(theirs["level"], silence_rank) ==
                      rank(ours["level"], silence_rank) - 1 else "areo_compromise")
        else:
            yellow = "middle" if middle else "areo_compromise"
        out = {"topic": topic,
               "distribution": {str(lv): sorted(s) for lv, s in sorted(by_level.items(), key=lambda x: str(x[0]))},
               "uncertain": sorted(uncertain), "yellow_from": yellow}
        for name, p in (("ours", ours), ("middle", middle), ("theirs", theirs)):
            if p:
                p = dict(p, position=name, certainty=certainty(p, refs, question, research_year, uncertain, by_level,
                                                                silence_rank),
                         accepted_ok=accepted_ok(p, refs, question))
            out[name] = p
        if theirs_note:
            out["theirs_note"] = theirs_note
        if not ours and not middle:
            out["certainty"] = CERTAINTY["expert"]
        if (old.get(topic) or {}).get("periods"):
            out["periods"] = old[topic]["periods"]
        ranges.append(out)
    mr["ranges"] = ranges
    counted = [refs[s] for r in ranges for p in ("ours", "middle", "theirs") if r.get(p) for s in r[p]["source_ids"]]
    used = {c["source_id"] for c in coding if c.get("source_id") in refs and counted_ref(refs[c["source_id"]])}
    mr["counts"] = {"found": len(refs),
                    "opened": sum(1 for r in refs.values() if r.get("read_status") not in ("located_not_read",)),
                    "read": sum(1 for r in refs.values() if r.get("read_status") not in NOT_READ),
                    "counted": len({(refs[s].get("template_family") or s).strip().lower() for s in used}),
                    "excluded": sum(1 for r in refs.values() if r.get("read_status") in NOT_READ),
                    "bodies": len({(r.get("issuing_body") or "").strip().lower() for r in counted} - {""})}
    return ranges


# --------------------------------------------------------------------------- הבדיקות
def iter_tracks(model):
    for rule in model.get("rules") or []:
        for t in ("green", "yellow", "red"):
            tl = (rule.get("traffic_light") or {}).get(t)
            if isinstance(tl, dict):
                yield rule, t, tl


def text_of(tl):
    return " ".join(str(tl.get(k) or "") for k in ("source_label", "rationale", "note", "proposed_clause",
                                                    "position", "summary"))


def range_for(model, rule):
    topic = rule.get("market_topic") or rule.get("topic") or rule.get("title")
    for r in (model.get("market_research") or {}).get("ranges") or []:
        if r.get("topic") == topic:
            return r
    return None


def uses_market(model):
    return any(tl.get("basis") in MARKET_BASIS for _, _, tl in iter_tracks(model)) or \
        model.get("corpus_origin") in ("own_plus_market", "market_built")


def docx_created(path):
    import zipfile
    try:
        with zipfile.ZipFile(path) as z:
            core = z.read("docProps/core.xml").decode("utf-8", "ignore")
    except (OSError, KeyError, zipfile.BadZipFile):
        return None
    m = re.search(r"<dcterms:(?:modified|created)[^>]*>([^<]+)<", core)
    return m.group(1) if m else None


def _ts(s):
    try:
        t = _dt.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return t if t.tzinfo else t.replace(tzinfo=_dt.timezone.utc)
    except ValueError:
        return None


def check_model(model, word=None, final=False):
    errs = []
    mr = model.get("market_research") or {}
    for rule, t, tl in iter_tracks(model):
        where = "%s/%s" % (rule.get("rule_id"), t)
        rng = range_for(model, rule)
        point = (rng or {}).get(tl.get("range_point") or {"green": "ours", "yellow": "middle", "red": "theirs"}[t])
        if "מקובל" in text_of(tl) and not (point and point.get("accepted_ok")):
            errs.append("MARKET_ACCEPTED_UNSUPPORTED %s: \"מקובל\" בלי נקודה של שלושה מקורות נספרים, מגופים ומתבניות "
                        "שונים, מאותו סוג הסכם ועם מקור מנוהל או מאוזן" % where)
        if t == "red" and tl.get("basis") in MARKET_BASIS and rng and not rng.get("theirs"):
            errs.append("RED_THEIRS_NOT_MEASURED %s: אדום בבסיס שוק, ו\"לטובתם\" לא נמדדה (%s)"
                        % (where, rng.get("theirs_note") or "פחות משלושה מקורות"))
    if uses_market(model):
        disc = mr.get("disclosure") or {}
        if not (model.get("status_label") or model.get("presentation_label")):
            errs.append("MARKET_NO_LABEL: הפלייבוק נשען על מחקר שוק, ואין תווית")
        if not disc.get("chat_message"):
            errs.append("MARKET_NO_DISCLOSURE: הפלייבוק נשען על מחקר שוק, ואין הודעת שקיפות (market_research.disclosure)")
        greens_template = any(t == "green" and tl.get("basis") in TEMPLATE_BASIS for _, t, tl in iter_tracks(model))
        for f in ("fixed_sentence", "chat_message"):
            txt = disc.get(f) or ""
            if greens_template and ALL_AREO in txt:
                errs.append("ALL_AREO_WITH_TEMPLATE: \"%s\" ב-%s, ויש ירוק מתבנית של החברה" % (ALL_AREO, f))
            for c in MC.count_claims(txt, model):
                errs.append("MARKET_COUNT_MISMATCH %s: %s" % (f, c))
    if word:
        built = _ts(docx_created(word))
        for r in mr.get("source_refs") or []:
            checked = _ts(r.get("link_checked_at"))
            if r.get("url") and built and (not checked or checked < built):
                errs.append("LINK_CHECK_BEFORE_WORD %s: הקישור נבדק לפני שה-Word נבנה (או לא נבדק)" % r.get("source_id"))
    if final:
        drafts = [r.get("rule_id") for r in model.get("rules") or [] if
                  (r.get("rationale") or {}).get("rationale_status", r.get("rationale_status")) == "Draft"]
        reason = (model.get("qa_summary") or {}).get("pass_b_stop_reason")
        if drafts and reason not in STOP_REASONS:
            errs.append("PASS_B_STOP_REASON: מסירה סופית עם %d כללים שהנימוק שלהם בטיוטה, בלי pass_b_stop_reason "
                        "(%s)" % (len(drafts), " | ".join(STOP_REASONS)))
    return errs


# --------------------------------------------------------------------------- ההודעה
def own_agreements(model):
    try:
        return S.agreements_counted(model) or 0
    except Exception:  # noqa: BLE001  מודל חלקי: אין ספירה
        return 0


def legal_facts(model):
    return sum(1 for s in model.get("external_sources") or [] if str(s.get("ref", "")).startswith("L")
               and not str(s.get("verification") or "").startswith("לא אומת"))


def fixed_sentence(model):
    """המשפט הקבוע לפי המסלול, והמספרים מ-market_research.counts (market_counts, יחיד ורבים)."""
    c = MC.counts(model)
    F, R = c.get("counted", 0), c.get("read", 0)
    L = legal_facts(model)
    fam, read = MC._families(F), MC._docs_read(R)
    legal = (", ולפי %s" % MC._legal(L)) if L else ""
    origin = model.get("corpus_origin")
    n_own = own_agreements(model)
    areo = sum(1 for _, _, tl in iter_tracks(model) if tl.get("basis") in ("market_standard", "areo_proposal"))
    templates = [tl for _, t, tl in iter_tracks(model) if t == "green" and tl.get("basis") in TEMPLATE_BASIS]
    role = (model.get("company_role_code") or (model.get("meta") or {}).get("company_role_code") or "")
    requested = ((model.get("meta") or {}).get("build_request") or {}).get("requested_by") == "negotiation_orchestrator"
    if requested and n_own:
        return ("זה פלייבוק מוצע, שנבנה לפי %d הסכמים שלכם ולפי %s (%s). העמדות שמקורן בשוק הן הצעה של Areo, "
                "ואינן מדיניות מאושרת של החברה." % (n_own, fam, read))
    if origin == "own_plus_market":
        return ("הפלייבוק נבנה מ-%d הסכמים שלכם. בנושאים שאין עליהם ראיה בהסכמים, הוא נבנה לפי %s (%s). %d עמדות "
                "הן הצעה של Areo, ואינן מבוססות על ההסכמים שלכם." % (n_own, fam, read, areo))
    if origin == "market_built" and templates:
        return ("הירוק נלקח מ-%d התבניות שלכם. הצהוב והאדום נבנו לפי %s (%s)%s. הם הצעה של Areo, ואינם מבוססים על "
                "ההסכמים שלכם, כי אין הסכם חתום מהסוג הזה." % (len(templates), fam, read, legal))
    if origin == "market_built" and role == "mutual":
        return ("אין לכם הסכם הדדי מהסוג הזה, ולכן הפלייבוק נבנה כולו לפי %s (%s)%s. התבניות החד-צדדיות שלכם סווגו "
                "לפי הכותרת והפתיח בלבד, ולא שימשו מקור לעמדות. %s." % (fam.replace("הסכמים", "הסכמים הדדיים", 1),
                                                                   read, legal, ALL_AREO))
    if origin == "market_built":
        return ("הפלייבוק נבנה לפי %s (%s)%s. %s, ואינה מבוססת על ההסכמים שלכם." % (fam, read, legal, ALL_AREO))
    findings = sum(1 for f in (model.get("market_research") or {}).get("findings") or [] if f.get("client_choice"))
    return ("המדיניות נגזרה מ-%d ההסכמים שלכם, והושוותה ל-%s (%s). %d ממצאים שבחרתם נכנסו לפלייבוק, מסומנים כהצעה של "
            "Areo." % (n_own, fam, read, findings))


POS_HE = {"ours": "לטובתנו", "middle": "באמצע", "theirs": "לטובתם"}


def build_message(model):
    mr = model.get("market_research") or {}
    refs = mr.get("source_refs") or []
    c = mr.get("counts") or {}
    label = model.get("status_label") or model.get("presentation_label") or ""
    sentence = fixed_sentence(model)
    lines = [label, sentence, ""] if label else [sentence, ""]
    requested = ((model.get("meta") or {}).get("build_request") or {}).get("requested_by") == "negotiation_orchestrator"
    if requested:
        h = model.get("handoff") or {}
        lines += ["מה נבנה: %d כללים, %d עמדות." % (len(model.get("rules") or []), sum(1 for _ in iter_tracks(model)))]
        for d in (h.get("decisions_now") or [])[:3]:
            lines.append("- %s (המלצה: %s)" % (d.get("question") or d.get("text") or "", d.get("recommendation") or ""))
        lines.append("")
    supports = {}
    for r in mr.get("ranges") or []:
        for p in ("ours", "middle", "theirs"):
            for s in (r.get(p) or {}).get("source_ids") or ():
                supports.setdefault(s, []).append("%s: %s" % (r["topic"], POS_HE[p]))
    lines.append("המקורות שעליהם נשענות העמדות (%d מסמכים מ-%d גופים; נמצאו %d, נקראו %d, נספרו %d; תאריך המחקר %s):"
                 % (c.get("read", 0), c.get("bodies", 0), c.get("found", 0), c.get("read", 0), c.get("counted", 0),
                    he_date(mr.get("research_date"))))
    lines.append("| # | גוף | מסמך | תאריך | ניסח / לטובת מי | קישור | נושאים ועמדות שהוא תומך בהם |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in refs:
        if r.get("read_status") in NOT_READ:
            continue
        lines.append("| %s | %s | %s | %s | %s / %s | [פתיחה](%s) | %s |" % (
            r.get("source_id"), r.get("issuing_body") or "", r.get("document") or "", he_date(r.get("doc_date")),
            r.get("drafter_role") or "", r.get("drafted_by") or "", r.get("url") or "",
            "; ".join(supports.get(r.get("source_id"), [])) or "לא נספר לנקודה"))
    lines += ["", "הטווח לכל נושא:"]
    for r in mr.get("ranges") or []:
        cert = next((r[p]["certainty"] for p in ("middle", "ours", "theirs") if r.get(p)), r.get("certainty") or
                    CERTAINTY["expert"])
        lines.append("**%s** (%s)" % (r["topic"], cert))
        for p in ("ours", "middle", "theirs"):
            pt = r.get(p)
            if pt:
                lines.append("- %s: דרגה %s. מקורות: %s." % (POS_HE[p], pt["level"], ", ".join(pt["source_ids"])))
            elif p == "theirs" and r.get("theirs_note"):
                lines.append("- %s: %s." % (POS_HE[p], r["theirs_note"]))
            else:
                lines.append("- %s: ממצא לא מאומת, פחות משלושה מקורות." % POS_HE[p])
    missing = [r for r in refs if r.get("read_status") in NOT_READ]
    if missing:
        lines += ["", "מה לא נמצא:"]
        lines += ["- %s: אותר, לא נקרא (%s), %s." % (r.get("document") or r.get("source_id"),
                                                    r.get("read_reason") or r.get("read_status"), r.get("url") or "")
                  for r in missing]
    unver = mr.get("unverified_findings") or []
    if unver:
        lines += ["", "מה לא אומת:"]
        lines += ["- %s" % (u.get("text") or u.get("label") or json.dumps(u, ensure_ascii=False)) for u in unver]
    lim = mr.get("limitations") or []
    if lim:
        lines += ["", "מגבלות:"] + ["- %s" % x for x in lim]
    if model.get("external_sources_table"):
        lines += ["", model["external_sources_table"]]
    return sentence, "\n".join(lines).strip() + "\n"


# --------------------------------------------------------------------------- הרשת
def agreement_phrases(corpus, n=4):
    """רצפים של n מילים מההסכמים, ומספרים שמופיעים בהם, לבדיקת השאילתה."""
    seqs, nums = set(), set()
    docs = corpus.get("documents") if isinstance(corpus, dict) else corpus
    for d in docs or ():
        paras = d.get("paragraphs") or [p for ps in (d.get("parts") or {}).values() for p in ps]
        for p in paras:
            t = p.get("text") or p.get("text_accept_all") or ""
            w = re.findall(r"\w+", t)
            for i in range(len(w) - n + 1):
                seqs.add(" ".join(w[i:i + n]).lower())
            nums |= {x for x in re.findall(r"\d[\d,.]*\d|\d", t) if len(x.replace(",", "").replace(".", "")) >= 2}
    return seqs, nums


def query_problem(query, purpose, corpus, profile, statute_names=()):
    from common import net
    q = query or ""
    allowed = ""
    if purpose == "legal":
        for name in sorted(statute_names or (), key=len, reverse=True):
            if name and name in q:
                q = q.replace(name, " ")
                allowed = name
    names = []
    if profile:
        names = [profile.get("organization_name"), profile.get("registered_legal_name")]
        names += list(profile.get("products") or []) + list(profile.get("projects") or [])
        names += [e.get("name") if isinstance(e, dict) else e for e in profile.get("related_entities") or ()]
    detail = net.client_detail_in_query(q, [x for x in names if x])
    if detail:
        return "פרט של הלקוח בשאילתה (%s)" % detail, allowed
    if corpus:
        seqs, nums = agreement_phrases(corpus)
        words = re.findall(r"\w+", q.lower())
        for i in range(len(words) - 3):
            if " ".join(words[i:i + 4]) in seqs:
                return "רצף מילים מההסכמים בשאילתה (%s)" % " ".join(words[i:i + 4]), allowed
        for x in re.findall(r"\d[\d,.]*\d|\d", q):
            if x in nums and len(x.replace(",", "").replace(".", "")) >= 2:
                return "מספר מההסכמים בשאילתה (%s)" % x, allowed
    return None, allowed


# --------------------------------------------------------------------------- הפקודות
def cmd_ranges(a):
    model = load(a.model, "המודל")
    ranges = compute_ranges(model)
    save(a.model, model)
    for r in ranges:
        pts = ", ".join("%s %s" % (POS_HE[p], r[p]["level"]) for p in ("ours", "middle", "theirs") if r.get(p))
        print("%s: %s%s; צהוב מ-%s" % (r["topic"], pts or "אין נקודה עם שלושה מקורות",
                                     "; לטובתם: " + r["theirs_note"] if r.get("theirs_note") else "", r["yellow_from"]))
    print("ספירה: %s" % json.dumps(model["market_research"]["counts"], ensure_ascii=False))
    return 0


def cmd_check(a):
    model = load(a.model, "המודל")
    errs = check_model(model, word=a.word, final=a.final)
    for e in errs:
        print("שגיאה: %s" % e)
    print("שגיאות: %d" % len(errs))
    return 3 if errs else 0


def cmd_links(a):
    from common import net
    from risk.entity_store import EntityStore
    model = load(a.model, "המודל")
    mr = model.get("market_research") or {}
    store = EntityStore(os.path.join(a.family_dir, "market-research"))
    failed = []
    run_dir = os.path.join(tempfile.gettempdir(), "areo-net", "links-" + os.path.basename(os.path.normpath(a.family_dir)))
    os.makedirs(run_dir, exist_ok=True)
    for r in mr.get("source_refs") or []:
        if not r.get("url") or r.get("read_status") in NOT_READ:
            continue
        res = net.fetch(r["url"], "בדיקת קישור לפני המסירה", run_dir=run_dir)
        r["link_checked_at"] = now_iso()
        ok = res.get("status") and 200 <= res["status"] < 300 and not res.get("blocked")
        if ok and r.get("document") and res.get("text"):
            title = re.search(r"<title[^>]*>(.*?)</title>", res["text"], re.S | re.I)
            if title and not any(w in title.group(1) for w in re.findall(r"\w{4,}", r["document"])[:3]):
                ok, res["reason"] = False, "הכותרת בדף אינה תואמת לשם המסמך"
        if ok and r.get("file_sha256") and res.get("sha256") and res["sha256"] != r["file_sha256"]:
            r["file_sha256_new"] = res["sha256"]
            r.setdefault("notes", []).append("המסמך השתנה מאז ההורדה (%s)" % he_date(r["link_checked_at"]))
        if not ok:
            r["read_status"] = "located_not_read"
            r["read_reason"] = "הקישור לא נפתח ב-%s (%s)" % (he_date(r["link_checked_at"]), res.get("reason"))
            failed.append(r["source_id"])
        _ = store  # השמירה של העותק החדש נעשית רק במחקר עצמו (fetch); כאן רק בדיקה
    for s in model.get("external_sources") or []:
        if s.get("url") and str(s.get("ref", "")).startswith(("L", "X")):
            res = net.fetch(s["url"], "בדיקת קישור לפני המסירה", run_dir=run_dir)
            s["link_checked_at"] = now_iso()
            if not (res.get("status") and 200 <= res["status"] < 300 and not res.get("blocked")):
                s["verification"] = "לא אומת: הקישור לא נפתח ב-%s" % he_date(s["link_checked_at"])
                failed.append(s.get("ref"))
    if failed:
        compute_ranges(model)
    mr.setdefault("refresh", {})["last_link_check"] = now_iso()
    save(a.model, model)
    print("נבדקו הקישורים. נכשלו: %s" % (", ".join(failed) if failed else "אף אחד"))
    if failed:
        print("הטווח חושב מחדש בלי המקורות שנכשלו. הרץ שוב message לפני המסירה.")
    return 3 if failed else 0


def cmd_message(a):
    model = load(a.model, "המודל")
    sentence, msg = build_message(model)
    mr = model.setdefault("market_research", {})
    mr["disclosure"] = {"fixed_sentence": sentence, "chat_message": msg, "shown_at": now_iso(), "word_chapter": True}
    if isinstance(model.get("handoff"), dict):
        model["handoff"]["counted_sources"] = (mr.get("counts") or {}).get("counted")
    save(a.model, model)
    errs = [e for e in check_model(model) if e.startswith(("MARKET_COUNT_MISMATCH", "ALL_AREO"))]
    if a.out:
        with io.open(a.out, "w", encoding="utf-8") as fh:
            fh.write(msg)
    print(msg)
    for e in errs:
        print("שגיאה: %s" % e)
    return 3 if errs else 0


def cmd_fetch(a):
    from common import net
    from risk.entity_store import EntityStore
    corpus = load(a.corpus, "החילוץ") if a.corpus else None
    profile = load(a.profile, "הפרופיל") if a.profile else None
    problem, allowed = query_problem(a.query + " " + a.url, a.purpose, corpus, profile, a.statute or ())
    if problem:
        print(json.dumps({"sent": False, "precheck": "failed", "reason": problem, "query": a.query},
                         ensure_ascii=False, indent=1))
        return 3
    allowed_domains = None
    if a.purpose == "legal":
        from risk.validate_register import APPROVED_DOMAINS
        allowed_domains = APPROVED_DOMAINS
    run_dir = os.path.join(tempfile.gettempdir(), "areo-net", os.path.basename(os.path.normpath(a.family_dir)))
    os.makedirs(run_dir, exist_ok=True)
    res = net.fetch(a.url, a.topic or a.purpose, allowed_domains=allowed_domains,
                    store=EntityStore(os.path.join(a.family_dir, "market-research")), source_id=a.source_id,
                    excerpt=a.excerpt, run_dir=run_dir)
    log = dict(res["log"], query=a.query, purpose=a.purpose, topic=a.topic,
               precheck="passed_statute_name" if allowed else "passed")
    if allowed:
        log["statute_name"] = allowed
    out = {"sent": True, "status": res.get("status"), "blocked": res.get("blocked"), "reason": res.get("reason"),
           "lawyer_task": res.get("lawyer_task"), "stored": res.get("stored"), "search_log": log}
    if res.get("blocked"):
        out["read_status"] = "located_not_read"
        out["read_reason"] = "אותר, לא נקרא: נחסם"
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0 if res.get("stored") else 3


def main(argv=None):
    sys.dont_write_bytecode = True
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("ranges", help="הטווח לכל נושא")
    r.add_argument("--model", required=True)
    c = sub.add_parser("check", help="הבדיקות של מחקר השוק")
    c.add_argument("--model", required=True)
    c.add_argument("--word", help="ה-Word שנבנה: הקישורים חייבים להיבדק אחריו")
    c.add_argument("--final", action="store_true", help="מסירה סופית: pass_b_stop_reason")
    l = sub.add_parser("links", help="בדיקת הקישורים לפני המסירה")
    l.add_argument("--model", required=True)
    l.add_argument("--family-dir", required=True)
    m = sub.add_parser("message", help="הודעת המסירה")
    m.add_argument("--model", required=True)
    m.add_argument("--out")
    f = sub.add_parser("fetch", help="בקשה אחת לרשת")
    f.add_argument("--family-dir", required=True, help="playbooks/<family_id>: העותק נשמר ב-market-research/sources/")
    f.add_argument("--source-id", required=True)
    f.add_argument("--url", required=True)
    f.add_argument("--query", required=True, help="השאילתה, מילה במילה, כפי שתירשם ביומן")
    f.add_argument("--purpose", required=True, choices=("market", "legal"))
    f.add_argument("--topic", help="הנושא שלשמו נשלחה")
    f.add_argument("--excerpt")
    f.add_argument("--corpus", help="החילוץ של ההסכמים: הבדיקה שאין בשאילתה רצף או מספר מהם")
    f.add_argument("--profile")
    f.add_argument("--statute", action="append", help="שם חוק או רגולטור מהרשימה הסגורה (רק ב-legal)")
    a = ap.parse_args(argv)
    return {"ranges": cmd_ranges, "check": cmd_check, "links": cmd_links, "message": cmd_message,
            "fetch": cmd_fetch}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
