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
* `start` / `stop` - מושב מחקר. בזמן המושב ה-hook של התוסף (`hooks/research_guard.py`)
  בודק כל WebSearch לפני שהוא נשלח, ועוצר WebFetch: הקריאה רק דרך `fetch`.
* `query` - אותה בדיקה, ידנית, לפני כל חיפוש (גם בסביבה שאין בה hooks). השאילתה
  נרשמת ב-`market-research/query-log.jsonl` (רק הוספה), ו-`fetch` מסרב לשאילתה שלא עברה כאן.
* `fetch` - בקשה אחת לרשת, דרך `common/net.py`. במחקר שוק עם סוג המקור
  (`--source-type`), והאתר נבדק מול הרשימה של הסוג לפני הבקשה ואחרי כל הפניה. אחרי בדיקת השאילתה: אין בה
  רצף מילים מההסכמים, שם צד, שם הלקוח, שם מוצר או פרויקט מהפרופיל, או מספר
  מההסכמים. שם חוק מהרשימה הסגורה מותר רק ב-`--purpose legal`. העותק נשמר
  ב-`market-research/sources/` של המשפחה.

    python3 scripts/market_research.py ranges  --model playbook-model.json
    python3 scripts/market_research.py check   --model playbook-model.json [--word <הפלייבוק>.docx] [--final]
    python3 scripts/market_research.py links   --model playbook-model.json --family-dir <playbooks/<family>>
    python3 scripts/market_research.py message --model playbook-model.json [--out הודעה.md]
    python3 scripts/market_research.py start   --family-dir <...> --corpus <חילוץ.json> --profile <פרופיל-לקוח.json>
    python3 scripts/market_research.py query   --query "<השאילתה>" --purpose market
    python3 scripts/market_research.py fetch   --family-dir <...> --source-id W1 --url <...> --purpose market \\
        --source-type public_filing --query "<השאילתה>" --corpus <חילוץ.json> --profile <פרופיל-לקוח.json>
    python3 scripts/market_research.py stop

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

# ---- ארבעת סוגי המקורות של מחקר השוק, בקוד (market-research.md, "סוגי המקורות") ----
# עד עכשיו הם היו רק בהוראות, ו-fetch קרא כל כתובת שנמסרה לו. עכשיו כל קריאה במחקר שוק
# מצהירה על סוג המקור, והאתר נבדק מול הסוג לפני הבקשה ואחרי כל הפניה (net.fetch,
# allowed_domains). הוספת גוף לרשימה היא החלטה של בעלי המערכת, כמו במפרט.
SOURCE_DOMAINS = {
    # 1. מכרזים ציבוריים בישראל וטבלאות ההבהרה שלהם, מהאתר הרשמי של הגוף המזמין
    "tender": ("gov.il", "muni.il", "clalit.co.il", "maccabi4u.co.il", "meuhedet.co.il", "leumit.co.il",
               "sheba.co.il", "tasmc.org.il", "hadassah.org.il", "rambam.org.il", "iec.co.il",
               "mekorot.co.il", "rail.co.il", "israelpost.co.il"),
    # 2. הסכמים שצורפו לדיווחים פומביים: EDGAR, מאיה, מגנ"א
    "public_filing": ("sec.gov", "tase.co.il", "isa.gov.il"),
    # 3. תנאים שספק מפרסם באתר שלו: כל אתר, חוץ מהאסורים, ועם שם הספק
    "vendor_terms": None,
    # 4. הסכמי מודל של גופים מוכרים
    "model_agreement": ("gov.il", "innovationisrael.org.il", "ac.il", "yissum.co.il", "ramot.org",
                        "commonpaper.com", "bonterms.com", "crowncommercial.gov.uk", "gov.uk", "nhs.uk"),
}
# המספר שנרשם ב-source_refs[].source_type (market-research.md: "1 עד 4, לפי סוגי המקורות")
SOURCE_TYPE_NUM = {"tender": 1, "public_filing": 2, "vendor_terms": 3, "model_agreement": 4}
# "ניסח / לטובת מי" בהודעה ללקוח: בעברית, ולא קוד המודל ("negotiated")
DRAFTED_HE = {"same_side": "הצד שלנו", "other_side": "הצד שכנגד", "negotiated": "נוהל עליו משא ומתן",
              "neutral_model": "מודל מאוזן", "unknown": "לא ידוע"}
SOURCE_TYPE_HE = {"tender": "מכרז ציבורי", "public_filing": "דיווח פומבי", "vendor_terms": "תנאים של ספק",
                  "model_agreement": "הסכם מודל"}
# אסורים כמקור בכל סוג: מאגר מצרף (לאיתור בלבד; המסמך נקרא במקור המקורי), אתרי תבניות,
# אנציקלופדיות ואתרי חדשות
DENIED_DOMAINS = ("lawinsider.com", "wikipedia.org", "rocketlawyer.com", "legalzoom.com", "pandadoc.com",
                  "templatelab.com", "docracy.com", "lawdepot.com", "jdsupra.com", "lexology.com",
                  "law.com", "ynet.co.il", "globes.co.il", "calcalist.co.il", "themarker.com", "reuters.com")
# שם של חוק, תקנות, צו או פקודה, כמו שהוא מצוטט בהסכם: "תקנות הגנת הפרטיות (אבטחת מידע), התשע"ז-2017".
# שם כזה הוא שם רשמי ופומבי, ולא פרט של הלקוח. בשאילתה רגולטורית הוא מותר גם כשאינו ברשימה שנמסרה; בהרצה
# חיה ה-hook עצר את החיפוש של תקנות אבטחת המידע, כי השם מופיע בהסכמים (20.10.2026)
STATUTE_RX = re.compile(r'(?:חוק|תקנות|צו|פקודת)(?:\s+(?!ו?(?:ה?ספק|ה?לקוח|ה?מזמין)\b)[^\s,;:.()"״]+){1,6}'
                        r'(?:\s*\([^)]{1,40}\))?(?:,?\s*ה?תש[א-ת"״׳]{1,5})?(?:\s*-?\s*\d{4})?')
# יומן השאילתות: שורת JSON לכל שאילתה, ורק מוסיפים לו (append). בגרסה הראשונה הוא נכתב מחדש כולו בכל
# שאילתה, ו-Claude מריץ פקודות במקביל (וגם ה-hook): בהרצה החיה כתיבות מקבילות מחקו זו את זו, וכל
# השאילתות המשפטיים, כולל זו שה-hook עצר, נעלמו מהיומן (20.10.2026). יומן ביקורת שמאבד שורות אינו יומן
QUERY_LOG = "query-log.jsonl"
QUERY_LOG_OLD = "query-log.json"
SESSION_FILE = "research-session.json"
SESSION_HOURS = 6


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
    used = {c["source_id"] for c in coding if c.get("source_id") in refs and counted_ref(refs[c["source_id"]])}
    mr["counts"] = {"found": len(refs),
                    "opened": sum(1 for r in refs.values() if r.get("read_status") not in ("located_not_read",)),
                    "read": sum(1 for r in refs.values() if r.get("read_status") not in NOT_READ),
                    "counted": len({(refs[s].get("template_family") or s).strip().lower() for s in used}),
                    "excluded": sum(1 for r in refs.values() if r.get("read_status") in NOT_READ),
                    # הגופים של המקורות שנספרו, כמו "counted": גם כשאף נקודה לא הגיעה לשלושה מקורות.
                    # לפני כן נספרו רק גופים של נקודות, וההודעה אמרה "7 מסמכים מ-0 גופים"
                    "bodies": len({(refs[s].get("issuing_body") or "").strip().lower() for s in used} - {""})}
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
    for r in mr.get("source_refs") or []:
        if r.get("source_type") in (3, "3") and r.get("drafted_by") in BALANCED:
            errs.append("VENDOR_TERMS_AS_BALANCED %s: תנאים שספק מפרסם הם העמדה של אותו ספק, ואינם נספרים "
                        "לנקודת המפגש (drafted_by=%s)" % (r.get("source_id"), r.get("drafted_by")))
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
            # מקור שלא נקרא אינו נספר ואינו מקושר, ו-links מדלג עליו; לכן אין לדרוש לו בדיקת קישור
            # (בהרצה החיה הבדיקה הזו עצרה מסירה על מקור שהחזיר 404, 20.10.2026)
            if r.get("read_status") in NOT_READ:
                continue
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
    # "שנקראו" צמוד למספר המסמכים: בלעדיו market_counts קורא אותו כמספר שנספר, וההודעה נכשלה
    # בבדיקה של עצמה בכל מחקר שבו לא כל מה שנקרא נספר (הבדיקה החיה, 20.10.2026)
    lines.append("המקורות שעליהם נשענות העמדות (%d מסמכים שנקראו, מ-%d גופים; נמצאו %d, נקראו %d, נספרו %d; תאריך המחקר %s):"
                 % (c.get("read", 0), c.get("bodies", 0), c.get("found", 0), c.get("read", 0), c.get("counted", 0),
                    he_date(mr.get("research_date"))))
    lines.append("| # | גוף | מסמך | תאריך | ניסח / לטובת מי | קישור | נושאים ועמדות שהוא תומך בהם |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in refs:
        if r.get("read_status") in NOT_READ:
            continue
        lines.append("| %s | %s | %s | %s | %s / %s | [פתיחה](%s) | %s |" % (
            r.get("source_id"), r.get("issuing_body") or "", r.get("document") or "", he_date(r.get("doc_date")),
            r.get("drafter_role") or "", DRAFTED_HE.get(r.get("drafted_by"), r.get("drafted_by") or ""),
            r.get("url") or "",
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
        for m in STATUTE_RX.finditer(q):
            allowed = allowed or m.group(0).strip()
        q = STATUTE_RX.sub(" ", q)
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


def url_problem(url, corpus, profile):
    """פרט של הלקוח בכתובת המסמך: שם מהפרופיל, מספר חברה או זהות, או רצף מילים מההסכמים.

    הכתובת אינה שאילתה, ולכן היא אינה עוברת את בדיקת "מספר בן 5 ספרות ומעלה": בכתובת של
    EDGAR יש תמיד מספר החברה המדווחת ב-SEC (CIK) ומספר ההגשה, ובדיקת השאילתה עצרה בגללם
    כל מסמך EDGAR (נמצא בבדיקה החיה, 20.10.2026). מה שכן אסור בכתובת אסור גם כאן.
    """
    from urllib.parse import unquote
    from common import net
    u = unquote(url or "")
    names = []
    if profile:
        names = [profile.get("organization_name"), profile.get("registered_legal_name")]
        names += list(profile.get("products") or []) + list(profile.get("projects") or [])
        names += [e.get("name") if isinstance(e, dict) else e for e in profile.get("related_entities") or ()]
    for name in names:
        if name and name.lower() in u.lower():
            return "פרט של הלקוח בכתובת (%s)" % name
    m = re.search(r"(?<!\d)\d{9}(?!\d)", u)
    if m and net._id_check_digit(m.group(0)):
        return "מספר חברה או זהות בכתובת (%s)" % m.group(0)
    if corpus:
        seqs, _ = agreement_phrases(corpus)
        words = re.findall(r"[^\W\d_]+", u.lower())
        for i in range(len(words) - 3):
            if " ".join(words[i:i + 4]) in seqs:
                return "רצף מילים מההסכמים בכתובת (%s)" % " ".join(words[i:i + 4])
    return None


def source_type_problem(url, source_type, vendor=None):
    """(בעיה, הדומיינים המותרים) לקריאה במחקר שוק. בעיה None = מותר."""
    from common import net
    host = (re.sub(r"^[a-z]+://", "", url or "", flags=re.I).split("/")[0].split(":")[0]).lower()
    if not host:
        return "אין כתובת", None
    if any(host == d or host.endswith("." + d) for d in DENIED_DOMAINS):
        return ("%s אינו מקור למחקר שוק (מאגר מצרף, אתר תבניות, אנציקלופדיה או חדשות). מסמך שאותר במאגר "
                "נקרא במקור המקורי שלו" % host), None
    if source_type not in SOURCE_DOMAINS:
        return "סוג המקור חסר או אינו אחד מארבעת הסוגים (%s)" % " | ".join(SOURCE_DOMAINS), None
    allowed = SOURCE_DOMAINS[source_type]
    if allowed is None:
        if not (vendor or "").strip():
            return "תנאים של ספק: חסר שם הספק (--vendor). הם נספרים רק כעמדה של אותו ספק", None
        return None, (net.registrable_domain(host),)
    if not any(host == d or host.endswith("." + d) for d in allowed):
        return ("%s אינו אתר של %s ברשימה המורשית. הוספת גוף לרשימה היא החלטה של בעלי המערכת"
                % (host, SOURCE_TYPE_HE[source_type])), None
    return None, allowed


# ---- שלב החיפוש: השאילתה נבדקת לפני שהיא יוצאת למנוע החיפוש, ולא רק בקריאה ----
# החיפוש עצמו נעשה בכלי החיפוש של Claude, ולכן הוא עבר עד עכשיו בלי בדיקה בקוד. עכשיו:
# `start` פותח מושב מחקר; ה-hook של התוסף (hooks/research_guard.py) בודק כל WebSearch
# בזמן המושב ועוצר שאילתה פסולה לפני שהיא נשלחת; `query` עושה את אותה בדיקה ידנית
# (בסביבה בלי hooks); ו-`fetch` מסרב לקרוא מסמך שהשאילתה שלו לא נבדקה ועברה.
def reading_dir():
    """עותקי קריאה של מסמכים גדולים: מחוץ לתיקיית הלקוח, בתיקייה הזמנית, ונמחקים ב-stop."""
    return os.path.join(tempfile.gettempdir(), "areo-research", "reading")


def write_copy(source_id, res):
    from risk.page_text import PdfTextUnavailable, page_text
    body = res.get("content") or b""
    try:
        text = page_text(body)
    except PdfTextUnavailable:
        return None
    d = reading_dir()
    os.makedirs(d, exist_ok=True)
    ext = "pdf" if body[:5] == b"%PDF-" else "htm"
    with open(os.path.join(d, "%s.%s" % (source_id, ext)), "wb") as fh:
        fh.write(body)
    meta = {"url": res.get("url"), "final_url": res.get("final_url"), "status": res.get("status"),
            "ext": ext, "log": res.get("log")}
    save(os.path.join(d, "%s.json" % source_id), meta)
    path = os.path.join(d, "%s.txt" % source_id)
    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


def read_copy(source_id, url):
    """עותק הקריאה של המסמך, כשנשמר לאותה כתובת בשלב הראשון. אחרת None."""
    from common import net
    d = reading_dir()
    try:
        with io.open(os.path.join(d, "%s.json" % source_id), encoding="utf-8") as fh:
            meta = json.load(fh)
        with open(os.path.join(d, "%s.%s" % (source_id, meta["ext"])), "rb") as fh:
            content = fh.read()
    except (OSError, ValueError, KeyError):
        return None
    if meta.get("url") != net.strip_secrets(net.to_uri(url))[0]:
        return None
    return dict(meta, content=content)


def session_path():
    return os.path.join(tempfile.gettempdir(), "areo-research", SESSION_FILE)


def load_session(now=None):
    """המושב הפעיל, או None כשאין או שפג."""
    try:
        with io.open(session_path(), encoding="utf-8") as fh:
            s = json.load(fh)
    except (OSError, ValueError):
        return None
    now = now or _dt.datetime.now(_dt.timezone.utc)
    try:
        if _dt.datetime.fromisoformat(s.get("expires_at")) < now:
            return None
    except (TypeError, ValueError):
        return None
    return s


def _log_path(family_dir):
    return os.path.join(family_dir, "market-research", QUERY_LOG)


def read_query_log(family_dir):
    out = []
    old = os.path.join(family_dir, "market-research", QUERY_LOG_OLD)
    try:
        with io.open(old, encoding="utf-8") as fh:
            out += json.load(fh)
    except (OSError, ValueError):
        pass
    try:
        with io.open(_log_path(family_dir), encoding="utf-8") as fh:
            for line in fh:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue      # שורה שנקטעה באמצע כתיבה
    except OSError:
        pass
    return out


def log_query(family_dir, entry):
    os.makedirs(os.path.dirname(_log_path(family_dir)), exist_ok=True)
    line = json.dumps(dict(entry, at=now_iso()), ensure_ascii=False) + "\n"
    # כתיבה אחת במצב append: במערכות POSIX היא אטומית לשורה קצרה, ואינה מוחקת שורות של תהליך אחר
    fd = os.open(_log_path(family_dir), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(fd, line.encode("utf-8"))
    finally:
        os.close(fd)


def query_passed(family_dir, query):
    q = " ".join((query or "").split())
    return any(e.get("precheck") in ("passed", "passed_statute_name") and " ".join((e.get("query") or "").split()) == q
               for e in read_query_log(family_dir))


def check_query(query, purpose, family_dir, corpus=None, profile=None, statutes=(), via="query"):
    """בודק שאילתה ורושם אותה ביומן השאילתות. מחזיר את הבעיה, או None כשמותר לחפש."""
    problem, allowed = query_problem(query, purpose, corpus, profile, statutes)
    entry = {"query": query, "purpose": purpose, "via": via,
             "precheck": "failed" if problem else ("passed_statute_name" if allowed else "passed")}
    if problem:
        entry["reason"] = problem
    if allowed:
        entry["statute_name"] = allowed
    log_query(family_dir, entry)
    return problem


# --------------------------------------------------------------------------- הפקודות
def cmd_start(a):
    for p, what in ((a.corpus, "החילוץ"), (a.profile, "הפרופיל")):
        if p and not os.path.exists(p):
            print("%s אינו קיים: %s" % (what, p))
            return 2
    until = _dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(hours=SESSION_HOURS)
    s = {"family_dir": os.path.abspath(a.family_dir),
         "corpus": os.path.abspath(a.corpus) if a.corpus else None,
         "profile": os.path.abspath(a.profile) if a.profile else None,
         "statutes": a.statute or [], "started_at": now_iso(), "expires_at": until.isoformat()}
    os.makedirs(os.path.dirname(session_path()), exist_ok=True)
    save(session_path(), s)
    print("מושב מחקר נפתח עד %s. כל חיפוש ברשת נבדק לפני שהוא נשלח, וקריאה רק דרך fetch. "
          "בסוף המחקר: stop." % until.astimezone().strftime("%H:%M"))
    return 0


def cmd_stop(a):
    import shutil
    try:
        os.remove(session_path())
    except OSError:
        pass
    shutil.rmtree(reading_dir(), ignore_errors=True)
    print("מושב המחקר נסגר.")
    return 0


def cmd_query(a):
    s = load_session() or {}
    family = a.family_dir or s.get("family_dir")
    if not family:
        print("אין מושב מחקר פעיל ולא נמסר --family-dir. התחל ב-start.")
        return 2
    corpus = load(a.corpus or s.get("corpus"), "החילוץ") if (a.corpus or s.get("corpus")) else None
    profile = load(a.profile or s.get("profile"), "הפרופיל") if (a.profile or s.get("profile")) else None
    problem = check_query(a.query, a.purpose, family, corpus, profile, a.statute or s.get("statutes") or ())
    if problem:
        print("השאילתה נעצרה ולא תישלח: %s" % problem)
        return 3
    print("מותר לחפש, בדיוק בנוסח הזה: %s" % a.query)
    return 0


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
        same = bool(r.get("file_sha256") and res.get("sha256") == r["file_sha256"])
        if ok and not same and r.get("document") and res.get("text"):
            # מסמך זהה לעותק שנשמר הוא אותו מסמך, מה שלא תהיה הכותרת. בלי גיבוב: שם המסמך בכותרת או
            # בפתיחת הטקסט, בלי תלות ברישיות. ב-EDGAR הכותרת היא שם הקובץ ("ny20050730x1_exd2.htm"), ולכן
            # בדיקה לפי הכותרת בלבד הוציאה מהספירה הסכמים תקינים (הבדיקה החיה, 20.10.2026)
            title = re.search(r"<title[^>]*>(.*?)</title>", res["text"], re.S | re.I)
            head = ((title.group(1) if title else "") + " " +
                    re.sub(r"<[^>]+>", " ", res["text"])[:20000]).lower()
            if not any(w.lower() in head for w in re.findall(r"\w{4,}", r["document"])[:3]):
                ok, res["reason"] = False, "שם המסמך אינו מופיע בדף"
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
    s = load_session() or {}
    corpus_p, profile_p = a.corpus or s.get("corpus"), a.profile or s.get("profile")
    corpus = load(corpus_p, "החילוץ") if corpus_p else None
    profile = load(profile_p, "הפרופיל") if profile_p else None

    def refuse(reason, precheck="failed"):
        print(json.dumps({"sent": False, "precheck": precheck, "reason": reason, "query": a.query},
                         ensure_ascii=False, indent=1))
        return 3

    # השאילתה שהביאה את המסמך נבדקה לפני שיצאה למנוע החיפוש (start + hook, או query)
    if not query_passed(a.family_dir, a.query):
        return refuse("השאילתה לא נבדקה לפני החיפוש. הרץ query על השאילתה לפני החיפוש, וחפש בדיוק בנוסח שעבר",
                      "not_prechecked")
    problem, allowed = query_problem(a.query, a.purpose, corpus, profile, a.statute or ())
    problem = problem or url_problem(a.url, corpus, profile)
    if problem:
        return refuse(problem)
    if a.purpose == "legal":
        from risk.validate_register import APPROVED_DOMAINS
        allowed_domains = APPROVED_DOMAINS
    else:
        problem, allowed_domains = source_type_problem(a.url, a.source_type, a.vendor)
        if problem:
            return refuse(problem, "source_type")
    store = EntityStore(os.path.join(a.family_dir, "market-research"))
    cached = read_copy(a.source_id, a.url) if a.excerpt else None
    if cached:
        # השלב השני של מסמך גדול: הקטע נבחר מעותק הקריאה, ונשמר בלי בקשה נוספת לאתר
        res = {"status": cached["status"], "blocked": False, "lawyer_task": None, "log": cached["log"]}
        try:
            res["stored"], _ = store.store_page(a.source_id, cached["final_url"], cached["content"],
                                                ext=cached["ext"], excerpt=a.excerpt)
            res["reason"] = "ok: נשמר חלון סביב הקטע, מעותק הקריאה (בלי בקשה נוספת)"
        except Exception as exc:  # noqa: BLE001  StoreError: הקטע לא נמצא בדף
            res["stored"], res["reason"] = None, "ok, not stored: %s" % exc
    else:
        run_dir = os.path.join(tempfile.gettempdir(), "areo-net", os.path.basename(os.path.normpath(a.family_dir)))
        os.makedirs(run_dir, exist_ok=True)
        res = net.fetch(a.url, a.topic or a.purpose, allowed_domains=allowed_domains, store=store,
                        source_id=a.source_id, excerpt=a.excerpt, run_dir=run_dir)
    log = dict(res["log"], query=a.query, purpose=a.purpose, topic=a.topic,
               precheck="passed_statute_name" if allowed else "passed")
    if allowed:
        log["statute_name"] = allowed
    out = {"sent": True, "status": res.get("status"), "blocked": res.get("blocked"), "reason": res.get("reason"),
           "lawyer_task": res.get("lawyer_task"), "stored": res.get("stored"), "search_log": log}
    if a.purpose == "market":
        # נכנס כמו שהוא ל-source_refs[]: סוג המקור קובע לאיזו נקודה בטווח הוא נספר
        out["source_type"] = SOURCE_TYPE_NUM[a.source_type]
        if a.vendor:
            out["vendor"] = a.vendor
    if res.get("blocked"):
        out["read_status"] = "located_not_read"
        out["read_reason"] = "אותר, לא נקרא: נחסם"
    elif not res.get("stored") and res.get("content") and not a.excerpt:
        # מסמך גדול (PDF של מכרז, למשל) נשמר בתיקיית הלקוח רק כחלון סביב קטע מילולי. בלי עותק קריאה
        # אי אפשר היה לבחור את הקטע: הטקסט לא הגיע אל הבונה, ומסמכי המכרזים לא נקראו (הבדיקה החיה)
        path = write_copy(a.source_id, res)
        if path:
            out["reading_copy"] = path
            out["next"] = ("המסמך גדול מכדי להישמר כולו. קרא את reading_copy, ובחר את הקטע המילולי של הנושא. "
                           "אחר כך הרץ שוב fetch עם אותם פרטים ועם --excerpt \"<הקטע>\": החלון סביבו נשמר, "
                           "בלי בקשה נוספת לאתר. עותק הקריאה נמחק ב-stop.")
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0 if res.get("stored") or out.get("reading_copy") else 3


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
    f.add_argument("--source-type", choices=sorted(SOURCE_DOMAINS),
                   help="חובה במחקר שוק: tender | public_filing | vendor_terms | model_agreement")
    f.add_argument("--vendor", help="שם הספק, בתנאים שספק מפרסם באתר שלו (vendor_terms)")
    st = sub.add_parser("start", help="פותח מושב מחקר: מכאן כל חיפוש ברשת נבדק לפני שהוא נשלח")
    st.add_argument("--family-dir", required=True)
    st.add_argument("--corpus")
    st.add_argument("--profile")
    st.add_argument("--statute", action="append")
    sub.add_parser("stop", help="סוגר את מושב המחקר")
    q = sub.add_parser("query", help="בודק שאילתה לפני החיפוש, ורושם אותה ביומן")
    q.add_argument("--query", required=True)
    q.add_argument("--purpose", required=True, choices=("market", "legal"))
    q.add_argument("--family-dir", help="ברירת המחדל: של המושב הפעיל")
    q.add_argument("--corpus")
    q.add_argument("--profile")
    q.add_argument("--statute", action="append")
    a = ap.parse_args(argv)
    if a.cmd == "fetch" and a.purpose == "market" and not a.source_type:
        ap.error("במחקר שוק חובה --source-type (ארבעת סוגי המקורות של market-research.md)")
    return {"ranges": cmd_ranges, "check": cmd_check, "links": cmd_links, "message": cmd_message,
            "fetch": cmd_fetch, "start": cmd_start, "stop": cmd_stop, "query": cmd_query}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
