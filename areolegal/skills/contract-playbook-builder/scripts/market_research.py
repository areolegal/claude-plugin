#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""מחקר השוק של בונה הפלייבוק, בקוד ולא בשיקול דעת: הטווח, הבדיקות, הקישורים, ההודעה והרשת.

עד עכשיו המודל חישב את הטווח, בדק את הקישורים וכתב את הודעת המסירה בעצמו,
וכל הרצה יצאה קצת אחרת: "מקובל" על שני מקורות, "לטובתם" שהגנה על החברה יותר
מנקודת המפגש, צהוב זהה לירוק, ומספרים שונים בצ'אט וב-Word.

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
* `start` / `stop` - מושב מחקר: שומר את החילוץ, הפרופיל, העסקה ושמות החוקים לבדיקות שאחריו. אין
  בתוסף hook שבודק את כלי החיפוש והקריאה של Claude: הבדיקה היא `query` לפני כל חיפוש, והקריאה רק ב-`fetch`.
* `query` - הבדיקה, לפני כל חיפוש, חובה. השאילתה נרשמת ב-`market-research/query-log.jsonl` (רק הוספה),
  ו-`fetch` מסרב לשאילתה שלא עברה כאן.
* `fetch` - בקשה אחת לרשת, דרך `common/net.py`. במחקר שוק עם סוג המקור
  (`--source-type`), והאתר נבדק מול רשימת המקורות המאושרים לפני הבקשה ואחרי כל הפניה. אתר שאינו ברשימת המקורות המאושרים נדחה בכל סוג ובכל מטרה (AREO לא מצאה מקור מורשה לנקודה זו). אתר בית משפט, מאגר
  פסיקה או מדור פסיקה (`common/case_law.case_law_url`) נדחה תמיד. אחרי בדיקת השאילתה: אין בה
  רצף מילים מההסכמים, שם צד (מהחילוץ, מהמניפסט ומהעסקה), שם הלקוח או הישויות או מילה ייחודית מהם, שם
  מוצר או פרויקט מההסכמים, או מספר מההסכמים. שם חוק מותר רק ב-`--purpose legal`, ורק כשהוא אחד
  משמות `--statute` (הרשימה הסגורה של ההרצה). העותק נשמר ב-`market-research/sources/` של המשפחה.

    python3 scripts/market_research.py ranges  --model playbook-model.json
    python3 scripts/market_research.py check   --model playbook-model.json [--word <הפלייבוק>.docx] [--final]
    python3 scripts/market_research.py links   --model playbook-model.json --family-dir <playbooks/<family>> \
        [--approved-sources <מקורות-מאושרים.json>]
    python3 scripts/market_research.py message --model playbook-model.json [--out הודעה.md]
    python3 scripts/market_research.py start   --family-dir <...> --corpus <חילוץ.json> --profile <פרופיל-לקוח.json> \
        [--manifest <corpus-manifest.json>] [--deal <negotiation_state.json>]
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # גם ב-python -I, שאינו מוסיף את תיקיית הסקריפט
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

# ---- סוגי המקורות של מחקר השוק (market-research.md, "סוגי המקורות"): תווית בלבד ----
# כל קריאה במחקר שוק מצהירה על סוג המקור, אבל הסוג אינו קובע מי מותר. מותר רק מה שברשימת המקורות
# המאושרים (מקורות-מאושרים.json); אתר שאינו בה נדחה, והנקודה נושאת את ההערה "AREO לא מצאה מקור מורשה לנקודה זו". אין בקוד
# שום רשימת גופים לפי סוג הסכם או סוג מקור (הרשימות הקודמות הועברו ל-removed-catalogs).
SOURCE_TYPES = ("tender", "public_filing", "vendor_terms", "model_agreement")
MODEL_UNLISTED = "לא נבדק: המקור אינו ברשימת המקורות המאושרים"
NO_POSITION = "AREO לא מצאה מקור מורשה לנקודה זו"
# המספר שנרשם ב-source_refs[].source_type (market-research.md: "1 עד 4, לפי סוגי המקורות")
SOURCE_TYPE_NUM = {"tender": 1, "public_filing": 2, "vendor_terms": 3, "model_agreement": 4}
# "ניסח / לטובת מי" בהודעה ללקוח: בעברית, ולא קוד המודל ("negotiated")
DRAFTED_HE = {"same_side": "הצד שלנו", "other_side": "הצד שכנגד", "negotiated": "נוהל עליו משא ומתן",
              "neutral_model": "מודל מאוזן", "unknown": "לא ידוע"}
# "מי ניסח" בטבלת המקורות: התפקיד כפי שנרשם, והקודים הכלליים בעברית
DRAFTER_HE = {"public_body": "גוף ציבורי", "model_body": "גוף שמפרסם הסכם מודל", "negotiated": "נוהל עליו משא ומתן",
              "unknown": "לא ידוע", "same_side": "צד באותה פוזיציה כמו החברה", "other_side": "הצד שכנגד",
              "supplier": "הספק", "customer": "הלקוח"}
SOURCE_TYPE_HE = {"tender": "הליך תחרותי ציבורי", "public_filing": "דיווח פומבי", "vendor_terms": "תנאים שצד מפרסם",
                  "model_agreement": "הסכם מודל"}
# אסורים כמקור בכל סוג: מאגר מצרף (לאיתור בלבד; המסמך נקרא במקור המקורי), אתרי תבניות,
# אנציקלופדיות ואתרי חדשות
DENIED_DOMAINS = ("lawinsider.com", "wikipedia.org", "rocketlawyer.com", "legalzoom.com", "pandadoc.com",
                  "templatelab.com", "docracy.com", "lawdepot.com", "jdsupra.com", "lexology.com",
                  "law.com", "ynet.co.il", "globes.co.il", "calcalist.co.il", "themarker.com", "reuters.com")
# שם של חוק בשאילתה רגולטורית מותר רק כשהוא אחד משמות --statute, שהבונה מעביר מהרשימה הסגורה של ההרצה
# (rr2-checklist-report-boundary.md). אין זיהוי אוטומטי של "חוק ..." בשאילתה: ביטוי כזה בלע בעבר את שם
# הלקוח שאחריו ("חוק אקמה מערכות בעמ ..."), והשאילתה נרשמה כשם חוק שעבר.
# יומן השאילתות: שורת JSON לכל שאילתה, ורק מוסיפים לו (append). בגרסה הראשונה הוא נכתב מחדש כולו בכל
# שאילתה, ו-Claude מריץ פקודות במקביל: בהרצה החיה כתיבות מקבילות מחקו זו את זו, וכל
# השאילתות המשפטיות נעלמו מהיומן. יומן ביקורת שמאבד שורות אינו יומן
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


ENTITIES_FILE = "ישויות.json"


def load_profile(path):
    """הפרופיל, ולצדו שמות הישויות מ-ישויות.json (בתיקיית הפרופיל או בתיקיות שמעליה), לבדיקת הפרטיות של
    שאילתה וכתובת. השמות נשמרים במפתח פנימי, ואינם נכתבים לשום קובץ."""
    prof = load(path, "הפרופיל")
    folder = os.path.dirname(os.path.abspath(path))
    for _ in range(4):
        reg = os.path.join(folder, ENTITIES_FILE)
        if os.path.isfile(reg):
            try:
                with io.open(reg, encoding="utf-8") as fh:
                    data = json.load(fh)
            except (OSError, ValueError):
                break
            items = data.get("entities") if isinstance(data, dict) else data
            prof["_entity_names"] = [e.get("name") for e in items or () if isinstance(e, dict) and e.get("name")]
            break
        parent = os.path.dirname(folder)
        if parent == folder:
            break
        folder = parent
    return prof


# מילים כלליות שאינן מזהות צד, גם כשהן חלק מהשם ("<Name> Systems Ltd": רק <Name> מזהה)
GENERIC_NAME_WORDS = {w.casefold() for w in (
    "limited", "ltd", "inc", "incorporated", "llc", "llp", "corp", "corporation", "company", "holdings",
    "holding", "group", "gmbh", "plc", "the", "and", "services", "service", "systems", "system", "solutions",
    "technologies", "technology", "tech", "software", "international", "global", "industries", "industry",
    "enterprises", "partners", "partnership", "capital", "management", "consulting", "trading", "investments",
    "properties", "property", "networks", "digital", "data", "cloud", "medical", "health", "healthcare",
    "energy", "finance", "financial", "insurance", "bank", "media", "logistics", "development", "foundation",
    "association", "university", "college", "institute", "trust", "fund", "agency", "authority", "ministry",
    "council", "municipality", "state", "government", "national", "israel", "israeli", "europe", "america",
    "american", "british", "project", "product", "platform", "programme", "program", "solution",
    "agreement", "party", "parties", "online", "labs", "works", "pharma", "biotech", "foods", "retail", "estate",
    "realty", "telecom", "communications", "security", "analytics", "ventures", "equity", "advisors",
    "associates", "consultants", "engineering", "construction", "manufacturing", "supply", "supplies",
    "products", "resources", "operations", "united", "general", "standard", "public", "private", "terms",
    "rollout", "renewal", "phase", "deal", "תקשורת", "הנדסה", "בנייה", "אבטחה", "מזון", "נדלן", "נדל\"ן", "פיתוח", "ייזום", "מוצרים", "משאבים",
    "בעמ", "בע\"מ", "בע״מ", "חברה", "חברת", "החברה", "מערכות", "שירותים", "שירותי", "אחזקות", "החזקות",
    "טכנולוגיות", "תעשיות", "השקעות", "נכסים", "ניהול", "ייעוץ", "פתרונות", "קבוצת", "קבוצה", "ישראל",
    "בינלאומי", "בינלאומית", "גלובל", "דיגיטל", "מדינת", "המדינה", "משרד", "רשות", "הרשות", "עיריית",
    "העירייה", "מועצה", "עמותת", "עמותה", "אגודת", "אגודה", "שותפות", "קרן", "אוניברסיטת", "מכללת",
    "פרויקט", "הפרויקט", "מוצר", "המוצר", "מערכת", "המערכת", "בין",
    "לבין", "ובין", "להלן")}
LEGAL_SUFFIX_EN = (r"(?:Ltd\.?|Limited|Inc\.?|Incorporated|L\.?L\.?C\.?|L\.?L\.?P\.?|plc|PLC|Corp\.?|"
                   r"Corporation|GmbH|AG|S\.A\.?|SAS|S\.p\.A\.?|B\.V\.?|N\.V\.?|Pty|Co\.|Holdings)")
ENTITY_EN = re.compile(r"\b((?:[A-Z][\w&'\-]*\.?\s+){0,4}[A-Z][\w&'\-]*),?\s+" + LEGAL_SUFFIX_EN + r"(?!\w)")
ENTITY_HE = re.compile(r"((?:[א-ת][א-ת\"״'׳\-]*\s+){0,4}[א-ת][א-ת\"״'׳\-]*)\s+(?:בע[\"״]?מ|\(ע[\"״]?ר\)|"
                       r"\(חל[\"״]?צ\)|\(שותפות מוגבלת\))")
# שם פרויקט או מוצר: "Project Falcon", "the Falcon Platform", פרויקט "נשר"
PROJECT_EN = re.compile(r"\b(?:Project|Programme|Program|Product|Platform)\s+([A-Z][\w\-]{2,})"
                        r"|\b([A-Z][\w\-]{2,})\s+(?:Project|Programme|Platform)\b")
PROJECT_HE = re.compile(r"(?:פרויקט|מיזם|תוכנית|מוצר|מערכת|פלטפורמת)\s+[\"״“]([^\"״”]{2,30})[\"״”]")
QUOTED_ALIAS = re.compile(r"[(]\s*(?:להלן\s*:?\s*|hereinafter(?:\s+(?:referred\s+to\s+as|called))?\s*[:,]?\s*)?"
                          r"(?:the\s+)?[\"״“]([^\"״”()]{2,40})[\"״”]\s*[)]", re.I)
_HE_PREFIX = "והבכלמש"


def _role_words():
    """(בודק האם כינוי נראה כתפקיד, מה שאינו צד) מהמניפסט. אין רשימת תפקידים: כינוי מוגדר שנראה כתפקיד (מיודע בעברית,
    בעל סיומת של תפקיד באנגלית) אינו שם של צד. בלעדיו: רק המילים הכלליות."""
    try:
        import build_corpus_manifest as BCM
        return BCM._role_like, BCM.NOT_A_ROLE
    except Exception:  # noqa: BLE001
        return (lambda _n: False), None


def distinctive_tokens(name):
    """המילים הייחודיות בשם: 4 אותיות ומעלה, ולא מילה כללית (Ltd, Systems, בע"מ, מערכות). Globex מ-Globex Corporation."""
    out = []
    for w in re.findall(r"[^\W\d_][\w'\-]*", str(name or "")):
        w = w.strip("'-")
        if len(re.sub(r"\W", "", w)) >= 4 and w.casefold() not in GENERIC_NAME_WORDS:
            out.append(w)
    return out


def corpus_names(corpus=None, manifest=None, deal=None):
    """שמות הצדדים, הפרויקטים והמוצרים: שם עם סיומת של ישות (Ltd, Inc, GmbH, בע"מ, ע"ר) בפתיח של כל הסכם,
    כינוי מוגדר בסוגריים שאינו תפקיד ("Initech"), שם פרויקט או מוצר, הכינויים מהמניפסט (parties_hint), ושם
    הצד שכנגד, העסקה, הפרויקט או המוצר מהעסקה. נשמרים בזיכרון בלבד, לבדיקת השאילתה והכתובת."""
    roles, not_role = _role_words()
    found = []

    def add(n):
        n = re.sub(r"\s+", " ", str(n or "")).strip(" ,.;:()\"'״“”")
        # רק השם: מה שאחרי "בין", "לבין", "עם", "between" ("הסכם זה נערך בין אקמה מערכות" -> "אקמה מערכות")
        n = re.split(r"(?:^|\s)(?:ו?ל?בין|עם|between|and|by)\s+", n, flags=re.I)[-1].strip()
        if len(n) < 3 or re.search(r"\d", n):
            return
        low = re.sub(r"^the ", "", n.casefold())
        if roles(n) or low in GENERIC_NAME_WORDS or (not_role is not None and not_role.match(n)):
            return
        if re.match(r"(?:חוק|תקנות|פקודת|צו)\s|.*\b(?:Act|Law|Regulations?|Directive)$", n, re.I):
            return
        found.append(n)

    docs = corpus.get("documents") if isinstance(corpus, dict) else corpus
    for d in docs or ():
        if not isinstance(d, dict):
            continue
        paras = d.get("paragraphs") or [p for ps in (d.get("parts") or {}).values() for p in ps]
        text = " ".join((p.get("text") or p.get("text_accept_all") or "") for p in paras if isinstance(p, dict))
        head = text[:3000]
        for rx in (ENTITY_EN, ENTITY_HE):
            for m in rx.finditer(head):
                add(m.group(1))
        for m in QUOTED_ALIAS.finditer(head):
            g = m.group(1).strip()
            if not re.search(r"\b[A-Z]{2,8}\b", g) and len(g.split()) <= 3:
                add(g)
        for m in PROJECT_EN.finditer(text):
            add(m.group(1) or m.group(2))
        for m in PROJECT_HE.finditer(text):
            add(m.group(1))
    rows = (manifest.get("files") or manifest.get("documents") or []) if isinstance(manifest, dict) else manifest
    for r in rows if isinstance(rows, list) else ():
        for g in (r.get("parties_hint") or []) if isinstance(r, dict) else ():
            add(g)
    if isinstance(deal, dict):
        cp = deal.get("counterparty")
        for v in (deal.get("counterparty_name"), deal.get("counterparty_name_en"), deal.get("deal_name"),
                  deal.get("project_name"), deal.get("product_name"), cp.get("name") if isinstance(cp, dict) else cp):
            if isinstance(v, str):
                add(v)
        for p in deal.get("parties") or ():
            add(p.get("name") if isinstance(p, dict) else p)
        for k in ("meta", "deal", "deal_context"):
            if isinstance(deal.get(k), dict):
                found += corpus_names(deal=deal[k])
    return list(dict.fromkeys(found))


def client_names(profile, corpus=None, manifest=None, deal=None):
    """שמות שאסור שיופיעו בשאילתה או בכתובת: השם הרשום של הלקוח בעברית ובאנגלית, שמות הישויות שהוקמו, אתר
    הלקוח, ושמות הצדדים, הפרויקטים והמוצרים מההסכמים, מהמניפסט ומהעסקה. מפתח שאינו בפרופיל פשוט אינו נקרא."""
    names = []
    if profile:
        names += [profile.get("organization_name"), profile.get("organization_name_en")]
        names += list(profile.get("_entity_names") or ())
        br = profile.get("branding") if isinstance(profile.get("branding"), dict) else {}
        host = re.sub(r"^www\.", "", _host(br.get("website") or ""))
        if host:
            names.append(host)
    if corpus or manifest or deal:
        names += corpus_names(corpus, manifest, deal)
    seen, out = set(), []
    for n in names:
        n = str(n or "").strip()
        if n and n.lower() not in seen:
            seen.add(n.lower())
            out.append(n)
    return out


def name_tokens(names):
    """המילים הייחודיות מכל השמות (Globex, Initech, Falcon, אקמה), בלי כפילות. מאתר: התווית הראשונה."""
    out = []
    for n in names:
        if re.fullmatch(r"[\w\-]+(\.[\w\-]+)+", n):
            n = n.split(".")[0]
        out += distinctive_tokens(n)
    return list(dict.fromkeys(out))


def token_in(text, tokens):
    """המילה הייחודית הראשונה שמופיעה בטקסט כמילה שלמה (בעברית גם אחרי אות שימוש: לגלובקס), או ''."""
    t = " ".join(str(text or "").split())
    for tok in tokens:
        pre = "(?:[%s]{1,2})?" % _HE_PREFIX if re.match(r"[א-ת]", tok) else ""
        if re.search(r"(?<!\w)%s%s(?!\w)" % (pre, re.escape(tok)), t, re.I):
            return tok
    return ""


def save(path, data):
    with io.open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)


def now_iso():
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


EN_MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")


def he_date(iso, lang="he"):
    """תאריך בטקסט (הכללים המשותפים 3.6): בעברית D.M.YYYY, ובאנגלית "3 April 2027"."""
    try:
        d = _dt.date.fromisoformat(str(iso)[:10])
    except ValueError:
        return str(iso or "")
    if lang == "en":
        return "%d %s %d" % (d.day, EN_MONTHS[d.month - 1], d.year)
    return "%d.%d.%d" % (d.day, d.month, d.year)


def year_of(d):
    m = re.match(r"(\d{4})", str(d or ""))
    return int(m.group(1)) if m else None


# --------------------------------------------------------------------------- הטווח
def _host(url):
    return (re.sub(r"^[a-z]+://", "", url or "", flags=re.I).split("/")[0].split(":")[0]).lower()


def _approved_rules(path=None):
    """כללי הכתובת מרשימת המקורות המאושרים; ריק כשהקובץ לא נמסר או לא נקרא (אז אין מקור מאושר)."""
    try:
        from risk.validate_register import approved_domains
        return approved_domains(path)[0]
    except Exception:  # noqa: BLE001
        return ()


def model_body_unlisted(ref):
    """הסכם מודל (סוג 4, מנסח model_body או מודל מאוזן) מאתר שאינו ברשימת המקורות המאושרים, או בלי כתובת לבדיקה."""
    if not (ref.get("source_type") in (4, "4") or ref.get("drafter_role") == "model_body"
            or ref.get("drafted_by") == "neutral_model"):
        return False
    url = ref.get("final_url") or ref.get("url")
    if not _host(url):
        return True
    try:
        from risk.validate_register import domain_ok
    except Exception:  # noqa: BLE001
        return True
    return not domain_ok(url, _approved_rules())


def counted_ref(ref):
    """מקור נספר: נקרא, יש לו תאריך, ומקור ממאגר מצרף נבדק מול המקור המקורי. הסכם מודל רק מגוף ברשימה הסגורה."""
    if not ref or ref.get("read_status") in NOT_READ or not ref.get("doc_date"):
        return False
    if model_body_unlisted(ref):
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
        if r.get("read_status") not in NOT_READ and model_body_unlisted(r):
            errs.append("MODEL_BODY_NOT_LISTED %s: הסכם מודל מגוף שאינו ברשימה הסגורה (%s) אינו מקור, גם בהצהרה או "
                        "באישור של הלקוח. הוצא אותו מ-source_refs ומהקידוד, ורשום אותו ב-counts.screened_out[] "
                        "בסיבה \"%s\"" % (r.get("source_id"), _host(r.get("final_url") or r.get("url")) or "אין כתובת",
                                           MODEL_UNLISTED))
        if r.get("source_type") in (3, "3") and r.get("drafted_by") in BALANCED:
            errs.append("VENDOR_TERMS_AS_BALANCED %s: תנאים שספק מפרסם הם העמדה של אותו ספק, ואינם נספרים "
                        "לנקודת המפגש (drafted_by=%s)" % (r.get("source_id"), r.get("drafted_by")))
    if uses_market(model):
        disc = mr.get("disclosure") or {}
        if not (model.get("status_label") or model.get("presentation_label")):
            errs.append("MARKET_NO_LABEL: הפלייבוק נשען על מחקר שוק, ואין תווית")
        if not disc.get("chat_message"):
            errs.append("MARKET_NO_DISCLOSURE: הפלייבוק נשען על מחקר שוק, ואין הודעת שקיפות (market_research.disclosure)")
        greens_template = any(t == "green" and tl.get("basis") in TEMPLATE_BASIS + ("documents_majority",)
                              for _, t, tl in iter_tracks(model))
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
            # (הבדיקה הזו עוצרת מסירה על מקור שהחזיר 404)
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
    requested = ((model.get("meta") or {}).get("build_request") or {}).get("requested_by") not in (None, "", "user")
    if requested and n_own:
        return ("זו טיוטת מדיניות, שנבנתה לפי %d הסכמים שלכם ולפי %s (%s). העמדות שמקורן בשוק הן הצעה של Areo, "
                "ועוד לא אישרתם אותן." % (n_own, fam, read))
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
    # התווית מהגזירה האחת (status.derive_status), ולא מה שנשמר במודל, שעלול להיות מבנייה קודמת או בניסוח הקודם
    try:
        label = S.derive_status(model)["label"]
    except Exception:  # noqa: BLE001  מודל חלקי: התווית שנשמרה
        label = model.get("status_label") or ""
    sentence = fixed_sentence(model)
    lines = [label, sentence, ""] if label else [sentence, ""]
    requested = ((model.get("meta") or {}).get("build_request") or {}).get("requested_by") not in (None, "", "user")
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
    # בבדיקה של עצמה בכל מחקר שבו לא כל מה שנקרא נספר 
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
            DRAFTER_HE.get(r.get("drafter_role"), r.get("drafter_role") or ""), DRAFTED_HE.get(r.get("drafted_by"), r.get("drafted_by") or ""),
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


def query_problem(query, purpose, corpus, profile, statute_names=(), manifest=None, deal=None):
    """(בעיה, שם החוק שהותר). שם חוק מותר רק ב-legal, ורק כשהוא אחד משמות --statute (הרשימה הסגורה של
    ההרצה); אין זיהוי אוטומטי של "חוק ..." בשאילתה. שמות הלקוח, הישויות, הצדדים, הפרויקטים והמוצרים
    נבדקים בשם המלא וגם במילה הייחודית שבהם (Globex מ-Globex Corporation, אקמה מ-אקמה מערכות בע"מ)."""
    from common import net
    q = query or ""
    allowed = ""
    if purpose == "legal":
        for name in sorted(statute_names or (), key=len, reverse=True):
            name = " ".join(str(name or "").split())
            if name and name in " ".join(q.split()):
                q = " ".join(q.split()).replace(name, " ")
                allowed = allowed or name
    names = client_names(profile, corpus, manifest, deal)
    detail = net.client_detail_in_query(q, [x for x in names if x])
    if detail:
        return "פרט של הלקוח או של צד בשאילתה (%s)" % detail, allowed
    tok = token_in(q, name_tokens(names))
    if tok:
        return "שם של הלקוח, של צד, של פרויקט או של מוצר בשאילתה (%s)" % tok, allowed
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


def url_problem(url, corpus, profile, manifest=None, deal=None):
    """פרט של הלקוח בכתובת המסמך: שם מהפרופיל, מספר חברה או זהות, או רצף מילים מההסכמים.

    הכתובת אינה שאילתה, ולכן היא אינה עוברת את בדיקת "מספר בן 5 ספרות ומעלה": בכתובת של
    EDGAR יש תמיד מספר החברה המדווחת ב-SEC (CIK) ומספר ההגשה, ובדיקת השאילתה עצרה בגללם
    כל מסמך EDGAR. מה שכן אסור בכתובת אסור גם כאן.
    """
    from urllib.parse import unquote
    from common import net
    u = unquote(url or "")
    names = client_names(profile, corpus, manifest, deal)
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


def case_law_reason(url):
    """הסיבה כשהכתובת היא אתר בית משפט, מאגר פסיקה או מדור פסיקה (common/case_law.py), אחרת None."""
    try:
        from common.case_law import case_law_url
    except ImportError:  # ספרייה ישנה בלי המודול: הרשימה הקצרה שכאן
        h = _host(url)
        return ("%s הוא אתר בית משפט או מאגר פסיקה" % h) if re.search(r"(^|\.)(courts?|judiciary)\.", h + ".") else None
    return case_law_url(url)


def source_type_problem(url, source_type, vendor=None, approved_path=None):
    """(בעיה, הכללים המותרים) לקריאה במחקר שוק. בעיה None = מותר. מותר רק אתר שברשימת המקורות המאושרים;
    אתר בית משפט, מאגר פסיקה או מדור פסיקה נדחה תמיד; וסוג המקור הוא תווית בלבד."""
    from risk.validate_register import domain_ok
    host = _host(url)
    if not host:
        return "אין כתובת", None
    cl = case_law_reason(url)
    if cl:
        return cl, None
    if any(host == d or host.endswith("." + d) for d in DENIED_DOMAINS):
        return ("%s אינו מקור למחקר שוק (מאגר מצרף, אתר תבניות, אנציקלופדיה או חדשות). מסמך שאותר במאגר "
                "נקרא במקור המקורי שלו" % host), None
    if source_type not in SOURCE_TYPES:
        return "סוג המקור חסר או אינו אחד מארבעת הסוגים (%s)" % " | ".join(SOURCE_TYPES), None
    rules = _approved_rules(approved_path)
    if not rules or not domain_ok(url, rules):
        return ("%s אינו ברשימת המקורות המאושרים: המסמך אינו נקרא ואינו נספר. %s" % (host, NO_POSITION)), None
    if source_type == "vendor_terms" and not (vendor or "").strip():
        return "תנאים שצד מפרסם: חסר שם הצד המפרסם (--vendor). הם נספרים רק כעמדה של אותו צד", None
    return None, rules


# ---- שלב החיפוש: השאילתה נבדקת לפני שהיא יוצאת למנוע החיפוש, ולא רק בקריאה ----
# החיפוש עצמו נעשה בכלי החיפוש של Claude, ואין בתוסף hook שבודק אותו. לכן: `start` פותח מושב מחקר;
# `query` בודק כל שאילתה לפני החיפוש (חובה בהוראות); ו-`fetch` מסרב לקרוא מסמך שהשאילתה שלו לא
# נבדקה ועברה כאן. הקריאה רק דרך `fetch`, ולא בכלי הקריאה של Claude.
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


def check_query(query, purpose, family_dir, corpus=None, profile=None, statutes=(), via="query", manifest=None,
                deal=None):
    """בודק שאילתה ורושם אותה ביומן השאילתות. מחזיר את הבעיה, או None כשמותר לחפש."""
    problem, allowed = query_problem(query, purpose, corpus, profile, statutes, manifest, deal)
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
    for p, what in ((a.corpus, "החילוץ"), (a.profile, "הפרופיל"), (a.manifest, "המניפסט"), (a.deal, "העסקה")):
        if p and not os.path.exists(p):
            print("%s אינו קיים: %s" % (what, p))
            return 2
    until = _dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(hours=SESSION_HOURS)
    s = {"family_dir": os.path.abspath(a.family_dir),
         "corpus": os.path.abspath(a.corpus) if a.corpus else None,
         "profile": os.path.abspath(a.profile) if a.profile else None,
         "manifest": os.path.abspath(a.manifest) if a.manifest else None,
         "deal": os.path.abspath(a.deal) if a.deal else None,
         "statutes": a.statute or [], "started_at": now_iso(), "expires_at": until.isoformat()}
    os.makedirs(os.path.dirname(session_path()), exist_ok=True)
    save(session_path(), s)
    print("מושב מחקר נפתח עד %s. הרץ query על כל שאילתה לפני החיפוש, וחפש רק בנוסח שעבר; קריאה רק דרך fetch. "
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


def _opt(path, what):
    return load(path, what) if path else None


def cmd_query(a):
    s = load_session() or {}
    family = a.family_dir or s.get("family_dir")
    if not family:
        print("אין מושב מחקר פעיל ולא נמסר --family-dir. התחל ב-start.")
        return 2
    corpus = load(a.corpus or s.get("corpus"), "החילוץ") if (a.corpus or s.get("corpus")) else None
    profile = load_profile(a.profile or s.get("profile")) if (a.profile or s.get("profile")) else None
    manifest = _opt(a.manifest or s.get("manifest"), "המניפסט")
    deal = _opt(a.deal or s.get("deal"), "העסקה")
    problem = check_query(a.query, a.purpose, family, corpus, profile, a.statute or s.get("statutes") or (),
                          manifest=manifest, deal=deal)
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


SOURCE_TYPE_KEY = {v: k for k, v in SOURCE_TYPE_NUM.items()}


def ref_problem(r):
    """הבדיקות של fetch על מקור שוק שכבר נרשם, לפני שהקישור נפתח שוב: פסיקה, וסוג המקור ורשימת האתרים שלו."""
    st = r.get("source_type")
    key = SOURCE_TYPE_KEY.get(int(st)) if str(st or "").isdigit() else st
    problem, _ = source_type_problem(r.get("final_url") or r.get("url"), key, r.get("vendor") or r.get("issuing_body"))
    if not problem and r.get("final_url") and r.get("final_url") != r.get("url"):
        problem, _ = source_type_problem(r["url"], key, r.get("vendor") or r.get("issuing_body"))
    return problem


def legal_problem(url, rules):
    """מקור משפטי (L, X): לא פסיקה, ורק בדומיין ובנתיב שברשימת המקורות המאושרים."""
    from risk.validate_register import domain_ok
    cl = case_law_reason(url)
    if cl:
        return cl
    if not domain_ok(url, rules):
        return "דומיין או נתיב שאינו ברשימת המקורות המאושרים (%s)" % _host(url)
    return None


def cmd_links(a):
    from common import net
    from risk.validate_register import approved_domains
    model = load(a.model, "המודל")
    mr = model.get("market_research") or {}
    failed = []
    if a.approved_sources and not os.path.isfile(a.approved_sources):
        print("קובץ המקורות המאושרים אינו קיים: %s" % a.approved_sources)
        return 2
    rules = approved_domains(a.approved_sources)[0]
    run_dir = os.path.join(tempfile.gettempdir(), "areo-net", "links-" + os.path.basename(os.path.normpath(a.family_dir)))
    os.makedirs(run_dir, exist_ok=True)
    for r in mr.get("source_refs") or []:
        if not r.get("url") or r.get("read_status") in NOT_READ:
            continue
        # אותן בדיקות כמו ב-fetch, לפני הבקשה: כתובת שנפסלת אינה נפתחת שוב, והמקור יוצא מהספירה
        problem = ref_problem(r)
        r["link_checked_at"] = now_iso()
        if problem:
            r["read_status"] = "excluded"
            r["read_reason"] = "לא נבדק שוב: %s" % problem
            failed.append(r.get("source_id"))
            continue
        _, allowed = source_type_problem(r.get("url"), SOURCE_TYPE_KEY.get(int(r["source_type"]))
                                         if str(r.get("source_type") or "").isdigit() else r.get("source_type"),
                                         r.get("vendor") or r.get("issuing_body"))
        res = net.fetch(r["url"], "בדיקת קישור לפני המסירה", allowed_domains=allowed, run_dir=run_dir)
        ok = res.get("status") and 200 <= res["status"] < 300 and not res.get("blocked")
        same = bool(r.get("file_sha256") and res.get("sha256") == r["file_sha256"])
        if ok and not same and r.get("document") and res.get("text"):
            # מסמך זהה לעותק שנשמר הוא אותו מסמך, מה שלא תהיה הכותרת. בלי גיבוב: שם המסמך בכותרת או
            # בפתיחת הטקסט, בלי תלות ברישיות. ב-EDGAR הכותרת היא שם הקובץ ("ny20050730x1_exd2.htm"), ולכן
            # בדיקה לפי הכותרת בלבד הוציאה מהספירה הסכמים תקינים
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
    for s in model.get("external_sources") or []:
        if s.get("url") and str(s.get("ref", "")).startswith(("L", "X")):
            s["link_checked_at"] = now_iso()
            problem = legal_problem(s["url"], rules)
            if problem:
                s["verification"] = "לא אומת: %s" % problem
                failed.append(s.get("ref"))
                continue
            res = net.fetch(s["url"], "בדיקת קישור לפני המסירה", run_dir=run_dir,
                            allowed_domains=rules)   # Rules כמו שהוא: הנתיב נבדק שוב גם אחרי הפניה
            if not (res.get("status") and 200 <= res["status"] < 300 and not res.get("blocked")):
                s["verification"] = "לא אומת: הקישור לא נפתח ב-%s" % he_date(s["link_checked_at"])
                failed.append(s.get("ref"))
    if failed:
        compute_ranges(model)
    mr.setdefault("refresh", {})["last_link_check"] = now_iso()
    save(a.model, model)
    print("נבדקו הקישורים. נכשלו: %s" % (", ".join(str(x) for x in failed) if failed else "אף אחד"))
    if failed:
        print("הטווח חושב מחדש בלי המקורות שנכשלו. הרץ שוב message לפני המסירה.")
    return 3 if failed else 0


def cmd_message(a):
    path = None
    if a.out:
        # לפני כל כתיבה (גם למודל): --out לעולם אינו המודל או מסמך קיים
        from common.cli import OutputRefused, guard_out
        try:
            path = guard_out(a.out, inputs=[a.model])
        except OutputRefused as exc:
            print("refused: %s" % exc, file=sys.stderr)
            return 2
    model = load(a.model, "המודל")
    sentence, msg = build_message(model)
    mr = model.setdefault("market_research", {})
    mr["disclosure"] = {"fixed_sentence": sentence, "chat_message": msg, "shown_at": now_iso(), "word_chapter": True}
    if isinstance(model.get("handoff"), dict):
        model["handoff"]["counted_sources"] = (mr.get("counts") or {}).get("counted")
    save(a.model, model)
    errs = [e for e in check_model(model) if e.startswith(("MARKET_COUNT_MISMATCH", "ALL_AREO"))]
    if path:
        with io.open(path, "w", encoding="utf-8") as fh:
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
    profile = load_profile(profile_p) if profile_p else None
    manifest = _opt(a.manifest or s.get("manifest"), "המניפסט")
    deal = _opt(a.deal or s.get("deal"), "העסקה")

    def refuse(reason, precheck="failed"):
        print(json.dumps({"sent": False, "precheck": precheck, "reason": reason, "query": a.query},
                         ensure_ascii=False, indent=1))
        return 3

    # השאילתה שהביאה את המסמך נבדקה לפני שיצאה למנוע החיפוש (query)
    if not query_passed(a.family_dir, a.query):
        return refuse("השאילתה לא נבדקה לפני החיפוש. הרץ query על השאילתה לפני החיפוש, וחפש בדיוק בנוסח שעבר",
                      "not_prechecked")
    problem, allowed = query_problem(a.query, a.purpose, corpus, profile, a.statute or s.get("statutes") or (),
                                     manifest, deal)
    problem = problem or url_problem(a.url, corpus, profile, manifest, deal)
    if problem:
        return refuse(problem)
    cl = case_law_reason(a.url)
    if cl:
        # פסיקה רק ממחבר פסיקה סגור (כלל 1.1): בכל מטרה ובכל סוג, גם בדומיין שמאושר לחקיקה
        return refuse(cl, "case_law")
    if a.purpose == "legal":
        # המקורות הרגולטוריים מהקובץ המשותף מקורות-מאושרים.json (--approved-sources, משתנה הסביבה
        # AREO_APPROVED_SOURCES, או העותק שבתוסף), בלי רשימה תקפה אין מקור מאושר (אין רשימת נפילה): אותה פונקציה כמו בבודק ובמעריך הסיכונים
        from urllib.parse import urlsplit
        from risk.validate_register import approved_domains, domain_ok
        if a.approved_sources and not os.path.isfile(a.approved_sources):
            print("קובץ המקורות המאושרים אינו קיים: %s" % a.approved_sources)
            return 2
        rules = approved_domains(a.approved_sources)[0]
        if not domain_ok(a.url, rules):
            return refuse("דומיין או נתיב שאינו ברשימת המקורות המאושרים (%s)"
                          % urlsplit(a.url).hostname, "approved_sources")
        # הכללים כמו שהם (Rules, עם כללי הדחייה ב-refuse): שכבת הרשת בודקת שוב דומיין ונתיב גם אחרי הפניה
        allowed_domains = rules
    else:
        problem, allowed_domains = source_type_problem(a.url, a.source_type, a.vendor, a.approved_sources)
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
        # אי אפשר היה לבחור את הקטע: הטקסט לא הגיע אל הבונה, ומסמכי המכרזים לא נקראו
        path = write_copy(a.source_id, res)
        if path:
            out["reading_copy"] = path
            out["next"] = ("המסמך גדול מכדי להישמר כולו. קרא את reading_copy, ובחר את הקטע המילולי של הנושא. "
                           "אחר כך הרץ שוב fetch עם אותם פרטים ועם --excerpt \"<הקטע>\": החלון סביבו נשמר, "
                           "בלי בקשה נוספת לאתר. עותק הקריאה נמחק ב-stop.")
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0 if res.get("stored") or out.get("reading_copy") else 3


def cmd_lookup(a):
    """הרשומה של כתובת אחת ברשימת המקורות המאושרים, מהדיסק. המודל אינו קורא את הרשימה (157K תווים): הוא שואל את הקוד
    על כתובת אחת לפני fetch, ומקבל רק approved (עם הרשומה) או not_on_list / case_law_only / pending / no_list."""
    from common.approved_sources import lookup
    res = lookup(a.url, a.approved_sources)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0 if res["status"] == "approved" else (2 if res["status"] == "no_list" else 1)


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
    l.add_argument("--approved-sources", help="מקורות-מאושרים.json, לבדיקת המקורות המשפטיים (L, X) לפני הקריאה (ברירת מחדל: "
                                         "AREO_APPROVED_SOURCES, ואחריו העותק שבתוסף)")
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
    f.add_argument("--manifest", help="מניפסט הקורפוס: כינויי הצדדים (parties_hint) נבדקים בשאילתה")
    f.add_argument("--deal", help="קובץ העסקה (negotiation_state.json), כשהבנייה לבקשת הנושא ונותן: שם הצד שכנגד")
    f.add_argument("--statute", action="append", help="שם חוק או רגולטור מהרשימה הסגורה (רק ב-legal)")
    f.add_argument("--source-type", choices=sorted(SOURCE_TYPES),
                   help="חובה במחקר שוק: tender | public_filing | vendor_terms | model_agreement")
    f.add_argument("--vendor", "--publisher", dest="vendor",
                   help="שם הצד שמפרסם את התנאים באתר שלו (vendor_terms)")
    f.add_argument("--approved-sources", help="מקורות-מאושרים.json, לקריאה רגולטורית (ברירת מחדל: "
                                              "AREO_APPROVED_SOURCES, ואחריו העותק שבתוסף, lib/מקורות-מאושרים.json; "
                                              "אין רשימת נפילה בקוד)")
    st = sub.add_parser("start", help="פותח מושב מחקר: מכאן כל חיפוש ברשת נבדק לפני שהוא נשלח")
    st.add_argument("--family-dir", required=True)
    st.add_argument("--corpus")
    st.add_argument("--profile")
    st.add_argument("--manifest")
    st.add_argument("--deal")
    st.add_argument("--statute", action="append")
    sub.add_parser("stop", help="סוגר את מושב המחקר")
    lk = sub.add_parser("lookup", help="הרשומה של כתובת אחת ברשימת המקורות המאושרים, בלי לקרוא את הרשימה")
    lk.add_argument("--url", required=True)
    lk.add_argument("--approved-sources", help="מקורות-מאושרים.json (ברירת מחדל: AREO_APPROVED_SOURCES, ואחריו העותק שבתוסף, "
                                               "lib/מקורות-מאושרים.json)")
    q = sub.add_parser("query", help="בודק שאילתה לפני החיפוש, ורושם אותה ביומן")
    q.add_argument("--query", required=True)
    q.add_argument("--purpose", required=True, choices=("market", "legal"))
    q.add_argument("--family-dir", help="ברירת המחדל: של המושב הפעיל")
    q.add_argument("--corpus")
    q.add_argument("--profile")
    q.add_argument("--manifest")
    q.add_argument("--deal")
    q.add_argument("--statute", action="append")
    a = ap.parse_args(argv)
    if a.cmd == "fetch" and a.purpose == "market" and not a.source_type:
        ap.error("במחקר שוק חובה --source-type (ארבעת סוגי המקורות של market-research.md)")
    return {"ranges": cmd_ranges, "check": cmd_check, "links": cmd_links, "message": cmd_message,
            "fetch": cmd_fetch, "start": cmd_start, "stop": cmd_stop, "query": cmd_query,
            "lookup": cmd_lookup}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
