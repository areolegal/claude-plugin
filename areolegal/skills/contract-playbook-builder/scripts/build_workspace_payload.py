#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ממיר את playbook-model.json לנתוני הדף של סביבת העבודה.

נתוני הדף נבנים בסקריפט בלבד (`dashboard_spec.md`, "מאיפה נבנים נתוני הדף").
אין לכתוב אותם ביד, ואין לנחש שדה שאין לו מקור במודל: שדה חסר נשאר ריק,
והתבנית מסתירה את מה שנשען עליו. כל ההמרות כאן הן העברה או צמצום של מה
שכתוב במודל, ואין כאן חישוב מדיניות.

  python3 build_workspace_payload.py playbook-model.json payload.json

**סביבת עבודה אחת לכל הפלייבוקים של החברה** (`dashboard_spec.md`, "בורר
סוג ההסכם"): עם `--data` הסקריפט קורא את `playbooks/index.json`, ממיר כל
פלייבוק בנפרד, ומחזיר דף אחד ובו `books{}`, פלייבוק לכל סוג הסכם ופוזיציה,
ו-`playbooks[]` לבורר. כל סוג נשאר שלם ונפרד, ואין מיזוג עמדות בין סוגים:
הבורר מחליף את כל מה שמוצג, ולא מסנן רשימה אחת מעורבבת.

  python3 build_workspace_payload.py --data Areo-נתונים payload.json \
      [--current <family_id>]

**לפני הרישום אין עדיין אינדקס** (register_playbook.py רץ אחרון): עם `--data` ומודל יחד, המודל שנמסר
מצטרף לפלייבוקים שבאינדקס, ומחליף את הרשומה של אותו family_id אם יש; בלי אינדקס הוא הפלייבוק היחיד
בדף, והוא גם זה שנפתח ראשון. `--data` בלי אינדקס ובלי מודל: המודלים שב-playbooks/*/playbook-model.json.

  python3 build_workspace_payload.py playbooks/<family_id>/playbook-model.json \
      --data Areo-נתונים payload.json

שפת הדף (`meta.lang`, he או en) היא שפת התוצר: `--lang`, ואם אין, `deliverable_language`
מ-`--profile`, ואם אין, `scope_summary.deliverable_language` מהמודל, וברירת המחדל עברית
(`both` הוא שפת הממשק, `display_language`). התבנית קוראת את `meta.lang` וקובעת לפיו כיוון, שפה
וכל טקסט קבוע. הנתונים עצמם (נושא, עמדה, נוסח) אינם מתורגמים כאן.

ואחר כך:
  python3 validate_data.py --data payload.json
  python3 build_dashboard.py <תבנית> payload.json dashboard.html
"""
import argparse
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # גם ב-python -I, שאינו מוסיף את תיקיית הסקריפט
import areo_lib  # noqa: F401  מוסיף את areolegal/lib לנתיב הייבוא
import basis_line
import evidence_kind as E
import voice_scrub
from common.cli import OutputRefused, guard_out  # noqa: E402
from playbook import approval_sheet as A  # noqa: E402
from playbook import status as S  # noqa: E402

LIGHTS = ("green", "yellow", "red")
# המסלול שבו נבנה הפלייבוק, לפס הבסיס
ORIGIN_TO_PATH = {"own": "own", "own_plus_market": "own_plus_market",
                  "market_built": "market_built"}
STATUS = {"Draft": "Draft", "PartiallyApproved": "PartiallyApproved", "Approved": "Approved",
          "Superseded": "Superseded"}
# התווית שמסמנת עמדה שאינה מההסכמים של החברה
AREO_LABEL = "הצעת Areo (לא מבוסס על מסמכי הלקוח)"
# הטקסט הקבוע שהסקריפט כותב לנתוני הדף, בשתי שפות התוצר (localization-he.md)
TXT = {"he": {"title": "פלייבוק חוזי", "areo": AREO_LABEL, "units": "%d הסכמים", "files": "מתוך %d קבצים"},
       "en": {"title": "Contract playbook", "areo": "Areo proposal (not based on the client's documents)",
              "units": "%d agreements", "files": "out of %d files"}}


def norm_lang(v):
    """he, en או None. "both" ושאר הערכים: None, כדי שהבא בתור יכריע."""
    v = str(v or "").strip().lower()
    if v.startswith("en"):
        return "en"
    if v.startswith("he") or v in ("iw", "עב", "עברית"):
        return "he"
    return None


def resolve_lang(m, profile=None, lang=None):
    """שפת התוצר: --lang, deliverable_language בפרופיל, במודל, ואז display_language. ברירת מחדל: he."""
    prof = profile or {}
    for v in (lang, prof.get("deliverable_language"),
              (m.get("scope_summary") or {}).get("deliverable_language"), m.get("deliverable_language"),
              prof.get("display_language")):
        got = norm_lang(v)
        if got:
            return got
    return "he"


def warn(msg):
    sys.stderr.write("אזהרה: %s\n" % msg)


def ls_key(text):
    """מפתח לשמירת סימונים בדפדפן: אותיות לטיניות, ספרות וקו תחתון בלבד."""
    k = re.sub(r"[^A-Za-z0-9_]+", "_", str(text or "")).strip("_")
    return k or "playbook"


def first_line(text, limit=160):
    s = re.sub(r"\s+", " ", str(text or "")).strip()
    return s[:limit]


def pick(d, *names):
    """הערך הראשון שקיים מבין השמות. המודל התפתח, ושמות ישנים עוד בשימוש."""
    for n in names:
        if isinstance(d, dict) and d.get(n) not in (None, "", [], {}):
            return d[n]
    return None


def build_meta(m, lang="he", st=None, profile=None):
    scope = m.get("scope_summary") or {}
    basis = scope.get("corpus_basis") or {}
    fams = scope.get("contract_families") or []
    fam = fams[0] if fams else {}
    fam = family_in_lang(fam, lang)
    family = pick(fam, "contract_family_name", "label") or ""
    role = pick(fam, "company_role") or ""
    # השם בסכמה הוא company_name (playbook-schema.md); company.name ו-meta.company הם שמות קודמים
    comp = m.get("company")
    company = (pick(m, "company_name") or (comp if isinstance(comp, str) else pick(comp or {}, "name"))
               or pick(m.get("meta") or {}, "company_name", "company") or "")
    # בדף באנגלית שם החברה באנגלית, כשהוא ידוע (המודל או organization_name_en בפרופיל), ולא בעברית. שני השמות
    # נשמרים (company_by_lang), ו-build_dashboard.py --lang בוחר לפיהם
    company_en = (pick(m, "company_name_en") or pick(m.get("meta") or {}, "company_name_en")
                  or pick(profile or {}, "organization_name_en") or company)
    company_by_lang = {"he": company, "en": company_en}
    company = company_by_lang[lang]
    pid = pick(m, "playbook_id", "family_id") or "playbook"
    meta = {
        "id": pid,
        "slug": ls_key(pick(m, "family_id", "playbook_id")),
        "ls_key": ls_key(pid),
        "company": company,
        "title": (family + (" · " + role if role else "")) or TXT[lang]["title"],
        "lang": lang,
        "version": str(pick(m, "version") or "1.0"),
        "created": pick(m, "generated_at") or "",
        "updated": pick(m, "last_updated", "generated_at") or "",
        # השם בסכמה הוא playbook_status (ps1-playbook-identity-scope.md); status הוא השם הקודם
        "status": STATUS.get(pick(m, "playbook_status", "status") or "Draft", "Draft"),
    }
    # פס הבסיס: המספר נספר בקוד בבונה, וכאן הוא רק מועבר
    units = basis.get("agreement_units")
    if isinstance(units, int) and S is not None:
        units = S.company_agreements_counted(m)   # בלי טפסים של הצד שכנגד ושל גופים ציבוריים
    origin = scope.get("corpus_origin")
    if isinstance(units, int) and origin in ORIGIN_TO_PATH:
        meta["build_path"] = {"n": units, "path": ORIGIN_TO_PATH[origin]}
    else:
        warn("אין corpus_basis.agreement_units או corpus_origin במודל, "
             "ולכן פס הבסיס לא יוצג")
    # המעמד והתווית נגזרים במודל, והדף רק מציג אותם מילה במילה. הדף אינו
    # מחשב תווית, ואינו ממציא אותה כשהמודל לא כתב אותה
    gate = m.get("policy_gate") or {}
    for key in ("status_label", "label_now"):
        v = pick(m, key) or pick(gate, key)
        if v:
            meta[key] = v
    for key in ("approved_count", "positions_count"):
        v = gate.get(key)
        if isinstance(v, int):
            meta[key] = v
    # התווית הנוכחית והמונה נגזרים בקוד (playbook/status.derive_status), כמו בשער ה-Word, ולא רק
    # מ-policy_gate שנכתב במודל ועלול להיות מגרסה קודמת. התאים נקראים מרשומת האישור האחרונה
    # (status.record_cells_for, ב-convert): בלעדיהם המונה היה 0 גם אחרי אישור. התווית בשפת הדף, גם
    # ב-status_label, כדי שדף באנגלית לא יציג את התווית העברית שבמודל
    st = st or S.derive_status(m, lang=lang)
    meta["label_now"] = st["label"]
    meta["status_label"] = st["label"]
    meta["playbook_status"] = st["playbook_status"]
    # התווית בשתי השפות, מאותה גזירה: build_dashboard.py --lang מחליף לפיה את label_now ו-status_label, כך
    # שדף שנבנה בשפה אחרת מהנתונים מציג את התווית בשפת הדף
    meta["labels"] = {g: S.label_for(st, g) for g in ("he", "en")}
    meta["company_by_lang"] = company_by_lang
    meta["approved_count"] = st["approved_count"]
    meta["positions_count"] = st["positions_count"]
    # מעמד המאגר, לפס הבסיס: איך המסמכים נקראים בשורה (basis_line.py, corpus_status)
    # docs_status: גם theirs_paper, כשהמאגר חתום ורובו נייר של הצד שכנגד, כמו בשורת הבסיס שב-Word
    meta["corpus_status"] = basis_line.docs_status(m)
    mr = m.get("market_research") or {}
    date = pick(mr, "research_date", "date", "performed_at")
    if date:
        meta["market_research_date"] = date
    # התפקידים הם נתון של הפלייבוק, ולא רשימה קבועה של הסקיל
    roles = [x for x in (scope.get("company_roles") or []) if isinstance(x, dict)]
    if roles:
        meta["company_roles"] = [{"role": pick(x, "role") or "",
                                  "label": pick(x, "label") or ""} for x in roles]
    main = pick(scope, "main_role")
    if main:
        meta["main_role"] = main
    short = []
    if isinstance(units, int):
        # שם המסמכים לפי מעמד המאגר, כמו בשורת הבסיס (basis_line.docs): "19 הסכמים" נכתב קודם גם על נוסחים
        # שספקים אחרים פרסמו ברשת
        short.append("%d %s" % (units, basis_line.docs(meta["corpus_status"], lang)))
    if basis.get("files"):
        short.append(TXT[lang]["files"] % basis["files"])
    if short:
        meta["evidence_short"] = ", ".join(short) + "."
    return meta


_LATIN_ONLY = re.compile(r"^[A-Za-z0-9 ,.&()/'+\-]+$")
_PAREN_LATIN = re.compile(r"\(([A-Za-z][A-Za-z ,./'\-]*)\)")


def family_in_lang(fam, lang):
    """סוג ההסכם והצד בשפת הדף, מתוך מה שכבר כתוב במודל ולא בתרגום: בדף באנגלית, contract_family_name_en או
    השם החלופי הראשון שכתוב באנגלית (family_aliases), ו-company_role_en, או מה שבסוגריים באנגלית ("הלקוח
    (Customer)"), או קוד הצד (customer). בלי שם כזה נשאר השם שבמודל. הכותרת, הבורר והאשף קוראים מכאן."""
    if lang != "en" or not isinstance(fam, dict):
        return fam
    out = dict(fam)
    name = fam.get("contract_family_name_en") or next(
        (a for a in fam.get("family_aliases") or [] if isinstance(a, str) and _LATIN_ONLY.match(a.strip())), None)
    if name:
        out["contract_family_name"] = name.strip()
    role = fam.get("company_role") or ""
    m = _PAREN_LATIN.search(role)
    code = str(fam.get("company_role_code") or "").replace("_", " ").strip()
    role_en = fam.get("company_role_en") or (m.group(1).strip() if m else "") or (code.capitalize() if code else "")
    if role_en and not _LATIN_ONLY.match(role.strip() or "-"):
        out["company_role"] = role_en
    return out


def scope_block(m, lang="he"):
    sc = m.get("scope_summary") or {}
    out = {"contract_families": [family_in_lang(f, lang) for f in sc.get("contract_families") or []]}
    for a, b in (("limitations", "limitations"), ("date_range", "date_range"),
                 ("locations", "source_locations"), ("corpus_status", "corpus_status")):
        v = pick(sc, b)
        if v is not None:
            out[a] = v
    return out


def src_id(ref):
    """מזהה המקור של ראיה: source_ref של המודל הוא source_id, ולעיתים עם עוגן פסקה (S01#p19, playbook-schema.md,
    "ראיה"). התבנית מחפשת את המקור ב-sources לפי המזהה בלבד, ולכן העוגן נשמר בנפרד (cite.para)."""
    return str(ref or "").split("#")[0]


def _plain_name(f):
    """שם קובץ בלי סיומת ובלי מספר סידורי מוביל: קורא לא אמור לראות ".pdf" על תווית של הסכם."""
    import re
    s = re.sub(r"\.(pdf|docx?|rtf|txt|eml|msg)$", "", str(f or "").strip(), flags=re.I)
    return re.sub(r"^\d{1,3}[\s._-]+", "", s).strip()


ORIGIN_LABELS = {
    "he": {"guidance": "הנחיה פנימית של החברה", "template": "תבנית של החברה", "signed": "הסכם חתום",
           "amendment": "תיקון להסכם", "draft_ours": "טיוטה שלכם במשא ומתן", "draft_theirs": "טיוטה של הצד שכנגד במשא ומתן",
           "form_ours": "נוסח שאתם מציגים", "form_theirs": "נוסח של הצד שכנגד", "form_public": "נוסח ציבורי",
           "unknown_paper": "מסמך שמקורו לא נקבע"},
    "en": {"guidance": "Company internal guidance", "template": "Company template", "signed": "Signed agreement",
           "amendment": "Amendment", "draft_ours": "Your draft in negotiation", "draft_theirs": "Counterparty draft in negotiation",
           "form_ours": "Form you present", "form_theirs": "Counterparty form", "form_public": "Public form",
           "unknown_paper": "Document of undetermined origin"}}


def origin_label_key(row):
    """מפתח תווית המקור, מהעובדות בלבד: מעמד המסמך ונייר של מי. תווית שאומרת שהנוסח של החברה (form_ours,
    draft_ours, template, guidance) יוצאת רק כשהנייר אינו של הצד שכנגד."""
    role, paper = str(row.get("doc_role") or ""), row.get("paper")
    if E.layer_of(row) == "guidance":
        return "guidance" if paper != "theirs" else "form_theirs"
    if role == "template":
        return "template" if paper != "theirs" else "form_theirs"
    if role in ("signed", "agreement"):
        return "signed"
    if role == "amendment":
        return "amendment"
    if paper == "ours":
        return "draft_ours" if role == "draft" else "form_ours"
    if paper == "theirs":
        if row.get("counterparty_kind") in S.PUBLIC_KINDS:
            return "form_public"
        return "draft_theirs" if role == "draft" else "form_theirs"
    return "unknown_paper"


def origin_label(row):
    k = origin_label_key(row)
    return {"key": k, "he": ORIGIN_LABELS["he"][k], "en": ORIGIN_LABELS["en"][k]}


def build_sources(m):
    """מפתח המקור ← מה שהתבנית מציגה עליו. `paper` מגיע מהמודל ולא מהשם."""
    out, friendly = {}, {}
    for row in m.get("source_log") or []:
        sid = pick(row, "source_id")
        if not sid:
            continue
        name = pick(row, "title") or _plain_name(pick(row, "file")) or sid
        src = {"label": name, "name": name, "kind": "internal"}
        src["title"] = name
        for a, b in (("paper", "paper"), ("doc_role", "doc_role"),
                     ("date", "signed_at"), ("counterparty", "counterparty"),
                     ("url", "url"), ("channel", "channel"),
                     ("acceptance_mode", "acceptance_mode"),
                     ("role", "company_role_in_source"), ("status", "status"),
                     ("path", "path"), ("loc", "folder")):
            v = pick(row, b)
            # paper: ours או theirs, וריק כשלא ניתן לקבוע (playbook-schema.md). unknown, השם הישן, אינו נכתב
            if a == "paper" and v not in ("ours", "theirs"):
                continue
            if v is not None:
                src[a] = v
        if row.get("doc_role") == "template":
            src["kind"] = "internal"
        # מסמך שאינו הסכם (הנחיה, מדיניות, טבלה, תבנית) אינו נספר כהסכם בשום מונה ואינו שורה בטבלת ההשוואה:
        # הדף קורא is_agreement, ומציג אותו בשכבת ראיות נפרדת (layer, weight: הנחיה מעל טיוטה)
        src["is_agreement"] = E.is_agreement(row)
        src["layer"] = E.layer_of(row)
        src["weight"] = E.LAYER_WEIGHT.get(str(row.get("doc_role") or ""), 1)
        cp, yr = pick(row, "counterparty"), str(pick(row, "signed_at", "date") or "")[:4]
        friendly[sid] = (pick(row, "short_name")
                         or ((cp + (" · " + yr if yr.isdigit() else "")) if cp else "")
                         or first_line(name, 60))
        src["short"] = friendly[sid]      # תווית קצרה, לעולם לא שם קובץ עם סיומת
        # תווית המקור: "נוסח שאתם מציגים" רק כשהמסמך הוא נייר של החברה; מסמך של צד שלישי מקבל תווית משלו
        src["origin_label"] = origin_label(row)
        out[sid] = src
    # מקורות השוק הם חיצוניים, ונשמרים בנפרד כדי שלא ייספרו באחוז ההסכמים
    for row in ((m.get("market_research") or {}).get("sources") or []) + (m.get("market") or []):
        sid = pick(row, "source_id", "id")
        if sid and sid not in out:
            out[sid] = {"label": pick(row, "title") or sid,
                        "name": pick(row, "title") or sid, "kind": "external",
                        "url": pick(row, "url") or "", "date": pick(row, "checked_at", "date") or ""}
    return out, friendly


def build_market(m):
    rows = []
    for row in ((m.get("market_research") or {}).get("sources") or []) + (m.get("market") or []):
        sid = pick(row, "source_id", "id")
        if not sid:
            continue
        out = {"id": sid, "title": pick(row, "title") or sid,
               "body": pick(row, "issuer", "body") or "",
               "url": pick(row, "url") or "",
               "date": pick(row, "doc_date", "checked_at", "date") or ""}
        for a, b in (("retrieved_at", "retrieved_at"), ("drafter_role", "drafter_role"),
                     ("drafted_by", "drafted_by")):
            v = pick(row, b)
            if v:
                out[a] = v
        sup = row.get("supports") or row.get("topics")
        if isinstance(sup, list) and sup:
            out["supports"] = sup
        rows.append(out)
    return rows


def light(obj, rule_id, color, lang="he"):
    """עמדה אחת בשלוש העמדות. `label` נקבע לפי `basis` ולא לפי מספר הציטוטים."""
    if not isinstance(obj, dict):
        return None
    out = {}
    # בדף באנגלית, ניסוח באנגלית של העמדה אם המודל כתב אחד; אחרת הניסוח שבמודל, והדף מסמן אותו "מקור בעברית"
    pos = (pick(obj, "position_en", "pos_en") if lang == "en" else None) or pick(obj, "position", "pos", "text")
    if pos:
        out["pos"] = pos
    # הקריטריונים הם מערך שהתבנית חותכת, ולכן הם תמיד מערך
    crit = obj.get("match_criteria") or obj.get("crit") or []
    out["crit"] = [str(c) for c in crit] if isinstance(crit, list) else [str(crit)]
    out["evidence"] = obj.get("evidence") or []
    for a, b in (("basis", "basis"), ("basis_note", "basis_note"),
                 ("why", "meaning"), ("notes", "notes"), ("comments", "comments"),
                 ("source_label", "source_label")):
        v = pick(obj, b)
        if v is not None:
            out[a] = v
    pc = obj.get("proposed_clause")
    if isinstance(pc, dict) or (isinstance(pc, str) and pc):
        # כלל אחד לנוסח שמוצג ולטביעת האצבע שלו (approval_sheet.clause_text): שפת הדף, ובלעדיה השפה האחרת.
        # clause_lang עובר לאשף, וקליטת ההערות מחשבת את טביעת האצבע על אותו טקסט
        out["clause"], out["clause_lang"] = A.clause_text(pc, lang)
    refs = obj.get("basis_refs")
    if isinstance(refs, list) and refs:
        out["basis_refs"] = refs
    if obj.get("basis") in ("areo_proposal", "market_standard"):
        out["label"] = pick(obj, "label") or TXT[lang]["areo"]
        ids = obj.get("market_source_ids")
        if isinstance(ids, list) and ids:
            out["market_source_ids"] = ids
            if obj.get("basis") == "market_standard" and len(ids) < 3:
                warn("%s %s: market_standard עם %d מקורות, נדרשים שלושה"
                     % (rule_id, color, len(ids)))
        elif obj.get("basis") == "market_standard":
            warn("%s %s: market_standard בלי market_source_ids" % (rule_id, color))
    # מה המסלול מטיל על החברה, שורה לכל תפקיד שיש לה בהסכם. `role_effects`
    # הוא הנוסח הכללי; שמות as_*_effect נשמרים לפלייבוק הדדי שנכתב לפניו
    eff = obj.get("role_effects")
    if isinstance(eff, dict):
        eff = {k: v for k, v in eff.items() if v}
        if eff:
            out["role_effects"] = eff
    for a in ("as_discloser_effect", "as_recipient_effect", "company_effect"):
        v = obj.get(a)
        if v:
            out[a] = v
    if color == "yellow":
        fw = obj.get("fallback_wording")
        if isinstance(fw, dict) and fw.get("text"):
            out["fallback_wording"] = {"text": fw["text"], "source": fw.get("source") or ""}
    return out or None


def build_rules(m, cites, lang="he", extract=None):
    """כלל ← סעיף בדף. הציטוטים נאספים לרשימה אחת שהדף סופר לפיה."""
    rules, seen = [], set()
    src_rows = {r.get("source_id"): r for r in m.get("source_log") or [] if isinstance(r, dict)}
    ex_idx = E.doc_index(extract) if extract else {}
    names = E.party_names(m)
    company = pick(m, "company_name") or ""
    rule_ids_all = {x.get("rule_id") for x in m.get("rules") or [] if isinstance(x, dict)}
    for r in m.get("rules") or []:
        rid = pick(r, "rule_id", "id")
        if not rid:
            warn("כלל בלי rule_id נדלג")
            continue
        if rid in seen:
            warn("rule_id כפול: %s" % rid)
        seen.add(rid)
        rat = r.get("policy_rationale") or {}
        row = {"id": rid, "topic": (pick(r, "topic_name_en") if lang == "en" else None) or pick(r, "topic_name", "topic") or rid,
               "issue": (pick(r, "clause_issue_en") if lang == "en" else None) or pick(r, "clause_issue") or ""}
        for a, b in (("num", "clause_number"), ("kind", "clause_kind"),
                     ("they", "counterparty_objective"), ("pb", "playbook_id"),
                     ("conf", "confidence"), ("why", "why_address_topic"),
                     ("reg", "regulatory_status"), ("policy", "policy_status"),
                     ("topic_en", "topic_name_en")):
            v = pick(r, b)
            if v is not None:
                row[a] = v
        if r.get("walk_away") is True:
            row["walk_away"] = True     # "שוברי עסקה" בתמונת המצב, וסינון "קו אדום" באשף
        if r.get("client_concern") is True:
            row["client_concern"] = True    # נושא שהלקוח אמר שמדאיג אותו (scope_summary.client_concerns)
        # שכבת הנימוקים: נימוק שחוזר על נוסח העמדה הוא נימוק ריק, ושכבה שאינה שלמה אינה מוצגת (כלל 4)
        complete, why = E.rationale_complete(r)
        row["rationale_complete"] = complete
        if rat and complete:
            row["rat"] = rat
        elif rat:
            row["rat_hidden"] = why
        tl = {}
        src_tl = r.get("traffic_light") or r.get("tl") or {}
        for c in LIGHTS:
            one = light(src_tl.get(c), rid, c, lang)
            if one:
                wording_checks(one, src_tl.get(c) or {}, rid, c, names, company)
                tl[c] = one
        if tl:
            row["tl"] = tl
        pc = r.get("proposed_clause") or {}
        if pc:
            row["clause"] = pick(pc, "he", "en") or ""
            row["clause_en"] = pc.get("en") or ""
            row["clause_lang"] = pc.get("source_language") or ""
        norms = []
        for n in r.get("legal_basis_layers") or []:
            if n.get("statute"):
                norms.append({"law": n.get("statute") or "", "ref": n.get("section") or "",
                              "meaning": first_line(pick(n, "meaning", "effect") or "", 220)})
        if norms:
            row["norms"] = norms
        impacts = []
        for i in r.get("related_clause_impacts") or r.get("related_clauses") or r.get("impacts") or []:
            rel_id = pick(i, "related_rule_id", "rule_id", "ref") or ""
            # סעיף קשור מוצג רק כשהנושא קיים, אינו הנושא עצמו, ויש הסבר (ps3-rule-and-evidence.md, "סעיפים קשורים")
            if not rel_id or rel_id == r.get("rule_id") or rel_id not in rule_ids_all or not (pick(i, "impact", "relation", "effect") or "").strip():
                continue
            ev = [e for e in (i.get("evidence") or []) if isinstance(e, dict) and (e.get("quote") or "").strip()]
            direction = pick(i, "direction") or "mutual"
            impacts.append({"related_rule_id": rel_id,
                            "direction": direction if direction in ("affects", "affected_by", "mutual") else "mutual",
                            "impact": pick(i, "impact", "relation", "effect") or "",
                            "action": pick(i, "action") or "",
                            "basis": "areo_proposal" if (i.get("basis") == "areo_proposal" or not ev) else "corpus",
                            "evidence": [{"clause": e.get("clause_ref") or "", "quote": first_line(e.get("quote") or "", 400),
                                          "count": e.get("count") or 1} for e in ev[:2]]})
        if impacts:
            row["impacts"] = impacts
        # סעיפים קשורים בלי הסבר: מודל שמציין רק את המזהים (related_rule_ids) מציג אותם בכל זאת
        rel_ids = [x for x in (r.get("related_rule_ids") or []) if x and x != r.get("rule_id")]
        if rel_ids:
            row["rel"] = rel_ids
        presence = r.get("presence_rule") or r.get("presence")
        if isinstance(presence, dict) and presence:
            row["presence"] = {"requirement": pick(presence, "requirement") or "",
                               "missing_clause_color": pick(presence, "missing_clause_color") or ""}
        elif isinstance(presence, str) and presence:
            row["presence"] = {"requirement": presence, "missing_clause_color": ""}
        else:
            warn("%s: אין presence_rule. הסינון לפי נחיצות הסעיף לא יראה אותו" % rid)
        trig = r.get("activation_conditions")
        if isinstance(trig, list) and trig:
            row["trig"] = {"he": [str(x) for x in trig], "en": []}
        # התמונה הראייתית בכרטיס: שורה למקור, ולא שורה לציטוט
        ev_rows, by_src = [], {}
        for e in r.get("evidence") or []:
            sid = src_id(pick(e, "source_ref", "source_id"))
            if not sid or sid in by_src:
                continue
            by_src[sid] = True
            ev_rows.append({"source_id": sid, "weight": pick(e, "weight") or "",
                            "note": pick(e, "note", "tag") or ""})
        if ev_rows:
            row["ev"] = ev_rows
        # מוני הניסיון החוזי נגזרים ממעמד המסמך ומנוכחות שינויים במעקב, ולא נכתבים ביד (כלל 6)
        row["ec"] = E.derived_counts(r, m.get("source_log") or [])
        fb = r.get("fallback_origin") or {}
        if isinstance(fb, dict) and fb:
            # השורה נבנית בקוד מ-baseline, כמו בכרטיס ב-Word (basis_line.fallback_label)
            label = {g: basis_line.fallback_label(fb, m, g) for g in ("he", "en")}
            if label["he"] or label["en"]:
                row["fallback_origin"] = {"label_he": label["he"], "label_en": label["en"],
                                          "baseline": fb.get("baseline") or ""}
        # ראיות: כל אחת נכנסת לרשימת הציטוטים עם המסלול שהיא תומכת בו
        for ev in r.get("evidence") or []:
            cid = pick(ev, "evidence_id", "id") or ("c%d" % (len(cites) + 1))
            track = pick(ev, "track")
            if not track:
                warn("%s: ראיה %s בלי track, לא תיספר באחוז" % (rid, cid))
            ref = pick(ev, "source_ref", "source_id") or ""
            cite = {"id": cid, "rules": [rid], "src": src_id(ref),
                    "text": pick(ev, "quote", "text") or "",
                    "ref": pick(ev, "clause_ref", "ref") or "",
                    "tag": pick(ev, "tag") or "",
                    "side": pick(ev, "side") or "pro"}
            if track:
                cite["track"] = track
            if "#" in ref:
                cite["para"] = ref
            for a, b in (("weight", "weight"), ("segment_id", "segment_id")):
                v = pick(ev, b)
                if v:
                    cite[a] = v
            # סיווג הראיה (כלל 1): מקובץ החילוץ, ולעולם לא מניחוש. paper נלווה כדי שהדף יסביר unknown על נייר החברה
            srow = src_rows.get(cite["src"]) or {}
            cite["ev_kind"] = E.ev_kind(ev, srow, E.doc_for_source(srow, ex_idx))
            paper = pick(ev, "paper") or srow.get("paper")
            if paper in ("ours", "theirs"):
                cite["paper"] = paper
            cites.append(cite)
        rules.append(row)
    prune_constants(rules, cites)
    return rules


def wording_checks(one, raw, rid, color, names, company):
    """בדיקות הנוסח של עמדה אחת (כללים 2, 5, 7, 8, 21). הנוסח עצמו אינו משתנה (טביעת האצבע של האישור
    מחושבת עליו); הדף מציג את ההצעות ואת הדגלים."""
    clause = one.get("clause") or ""
    # שפת הנוסח מהטקסט בפועל; בלי נוסח אין שפה (כלל 7)
    lang_real = E.detect_lang(clause)
    if lang_real:
        one["clause_lang"] = lang_real
    else:
        one.pop("clause_lang", None)
    # שמות צדדים קונקרטיים -> תווית גנרית, כהצעה הניתנת לביטול (כלל 7)
    hits = E.name_hits(clause, names, company)
    for h in E.name_hits(one.get("pos") or "", names, company):
        if h not in hits:
            hits.append(h)
    if hits:
        one["name_hits"] = hits
        if clause:
            one["clause_generic"] = E.generic_text(clause, hits)
        if one.get("pos"):
            one["pos_generic"] = E.generic_text(one["pos"], hits)
    # טענת דין בנוסח: "טעונה אימות", עם הפניה למקור כשיש (כלל 8)
    blob = " ".join(str(one.get(k) or "") for k in ("pos", "clause", "why", "notes"))
    if E.legal_claim(blob):
        one["legal_claim"] = True
        refs = [x for x in (raw.get("regulatory_refs") or raw.get("sources") or []) if x]
        one["needs_verification"] = not refs
        if refs:
            one["verify_refs"] = refs
    # תקינות הנוסח לפני שהוא מוצג כנוסח מוצע (כלל 21)
    flags = E.integrity_flags(clause)
    if flags:
        one["integrity"] = flags
    if color == "red":
        kind, val = E.red_response(raw)
        if kind == "pointer":
            one["response"] = {"kind": "pointer", "to": val}
        elif kind == "wording":
            one["response"] = {"kind": "wording"}
        else:
            one["gap"] = True      # עמדה אדומה בלי נוסח תגובה היא פער, לא עמדה (כלל 5)
            warn("%s red: אין נוסח תגובה ואין הפניה לנוסח החלופי. מוצג כפער" % rid)


# שדות שערכם קבוע בכל הרשומות אינם מחושבים, ואינם מוצגים ואינם יוצרים מסנן (כלל 6)
CONSTANT_CANDIDATES = ("conf", "reg", "policy")


def prune_constants(rules, cites):
    if len(rules) > 1:
        for key in CONSTANT_CANDIDATES:
            vals = {json.dumps(r.get(key), ensure_ascii=False, sort_keys=True) for r in rules}
            if len(vals) == 1 and key in rules[0]:
                for r in rules:
                    r.pop(key, None)
                warn("השדה %s זהה בכל הכללים ולכן אינו מוצג" % key)
    if len(cites) > 1:
        vals = {c.get("weight") for c in cites}
        if len(vals) == 1 and "weight" in cites[0]:
            for c in cites:
                c.pop("weight", None)
            warn("משקל הציטוט זהה בכל הציטוטים ולכן אינו מוצג")


def build_segments(m, rules_by_id, lang="he"):
    """הסגמנטים לדף, והווריאנט נתלה על הכלל שהוא משנה: התבנית קוראת
    `r.variants[].seg` ולא מחפשת בתוך הסגמנט."""
    out = []
    for s in (m.get("segmentation_model") or {}).get("segments") or []:
        sid = pick(s, "segment_id", "id")
        if not sid:
            continue
        out.append({"segment_id": sid, "label": pick(s, "segment_name", "label", "name") or sid,
                    "criteria": pick(s, "criteria", "criterion") or "",
                    "status": pick(s, "status") or ""})
        for v in s.get("variants") or []:
            rid = pick(v, "rule_id")
            row = rules_by_id.get(rid)
            if not row:
                warn("ווריאנט בסגמנט %s מפנה לכלל %s שאינו בפלייבוק" % (sid, rid))
                continue
            vr = {"seg": sid, "mode": pick(v, "negotiation_mode") or ""}
            tl = {}
            for c in LIGHTS:
                one = light((v.get("traffic_light") or {}).get(c), sid, c, lang)
                if one:
                    tl[c] = one
            if tl:
                vr["tl"] = tl
            rat = v.get("segment_rationale") or v.get("policy_rationale")
            if rat:
                vr["rat"] = rat
            # סגמנט בלי משא ומתן אינו רמזור אלא שלוש שכבות (segmentation.md,
            # §12). התבנית יודעת להציג אותן, וקודם הן לא הועברו, ולכן סגמנט
            # של הליך תחרותי הוצג עם הכותרת "אין משא ומתן" ובלי שום תוכן מתחתיה
            for key in ("imposed_regime", "clarification_positions", "bid_conditions",
                        "clarification_record"):
                if v.get(key) not in (None, "", [], {}):
                    vr[key] = v[key]
            row.setdefault("variants", []).append(vr)
    return out


def build_queue(m):
    out = []
    for q in m.get("validation_queue") or []:
        out.append({"item_id": pick(q, "id", "item_id") or "",
                    "issue": pick(q, "topic", "issue") or "",
                    "question": pick(q, "question") or "",
                    "impact": pick(q, "why", "impact") or "",
                    "scope": pick(q, "scope") or "", "rule_id": pick(q, "rule_id") or "",
                    "segment_id": pick(q, "segment_id") or "",
                    "severity": pick(q, "severity") or "",
                    "rec": pick(q, "recommendation") or ""})
    return out


# urgency בסכמה הוא טקסט חופשי; התבנית מכירה high, medium ו-low בלבד
URGENCY = {"high": "high", "critical": "high", "urgent": "high", "immediate": "high",
           "גבוהה": "high", "גבוה": "high", "דחוף": "high", "דחופה": "high", "קריטית": "high", "מיידי": "high",
           "medium": "medium", "בינונית": "medium", "בינוני": "medium",
           "low": "low", "נמוכה": "low", "נמוך": "low"}


def build_findings(m):
    """ממצאים על החברה עצמה. השמות בסכמה (playbook-schema.md, company_findings[]) הם
    {topic, source_refs[], required_action, urgency}; title/detail/severity/clause_refs הם שמות
    קודמים, ונקראים כשאין את שמות הסכמה. השמות בנתוני הדף (title, body, severity, refs) הם של התבנית."""
    out = []
    for f in (m.get("company_findings") or []) + (m.get("template_findings") or []):
        if not isinstance(f, dict):
            continue
        sev = [URGENCY.get(str(f.get(k) or "").strip().lower()) for k in ("urgency", "severity")]
        out.append({"title": pick(f, "topic", "title", "finding") or "",
                    "body": pick(f, "required_action", "detail", "body") or "",
                    "severity": next((x for x in sev if x), "medium"),
                    "refs": pick(f, "source_refs", "clause_refs", "refs") or []})
    return out


def build_departments(m):
    """המחלקות האחראיות ושיוך החיובים (departments_and_responsibilities.md), כמו שהם במודל, ללשונית
    "מחלקות אחראיות" שלקריאה בלבד. None כשאין אף אחד מהשדות: הלשונית אינה מוצגת."""
    resp = [str(x).strip() for x in m.get("responsible_departments") or () if str(x or "").strip()]
    prop = [{"name": x.get("name") or "", "quote": x.get("quote") or "", "source": x.get("source") or ""}
            for x in m.get("departments_proposed") or () if isinstance(x, dict) and x.get("name")]
    asg = [{"type": x.get("type") or "", "department": x.get("department") or "",
            "summary": x.get("summary") or "", "source": x.get("source") or "",
            "needs_verification": bool(x.get("needs_verification"))}
           for x in m.get("obligation_assignments") or () if isinstance(x, dict) and x.get("type")]
    if not (resp or prop or asg):
        return None
    return {"responsible": resp, "proposed": prop, "assignments": asg}


def build_playbooks(m):
    """התצוגה הרוחבית. רק מה שהמודל יודע על פלייבוקים אחרים של החברה."""
    out = []
    for b in m.get("company_playbooks") or m.get("playbooks") or []:
        bid = pick(b, "playbook_id", "id")
        if not bid:
            continue
        out.append({"id": bid, "family": pick(b, "family", "contract_family_name") or "",
                    "role": pick(b, "role", "company_role") or "",
                    "rules": b.get("rules") or 0, "segments": b.get("segments") or 0,
                    "scanned": b.get("scanned") or b.get("agreement_units") or 0,
                    "updated": pick(b, "updated", "last_updated") or "",
                    "current": bool(b.get("current"))})
    return out


def approval_flags(m, rules, cells, st):
    """לכל עמדה: approved (התא נספר כמאושר, status.derive_status), legal_review_open (עורך דין צריך לעבור עליה
    ועוד לא נרשמה בדיקה) ו-slots (סוגריים של ערך שלא נקבע, approval_sheet.decision_slots). "שאלו את המדיניות"
    קורא את approved, והאשף חוסם אישור של עמדה שיש בה slots."""
    ok = set(st.get("approved_keys") or ())
    src = {pick(r, "rule_id", "id"): r for r in m.get("rules") or []}
    for row in rules:
        legal = A.legal_review_tracks(src.get(row["id"]) or {})
        for k, t in (row.get("tl") or {}).items():
            key = S.cell_key(row["id"], k)
            t["approved"] = key in ok
            c = (cells or {}).get(key) or {}
            if t["approved"] and isinstance(c, dict):
                if c.get("signer"):
                    t["approved_by"] = str(c.get("signer"))
                if c.get("approved_at"):
                    t["approved_at"] = str(c.get("approved_at"))
            if k in legal and key not in ok:
                t["legal_review_open"] = True
            slots = A.decision_slots("%s %s" % (t.get("pos") or "", t.get("clause") or ""))
            if slots:
                t["slots"] = slots


# ---- מילון התצוגה: מונח של הבונה ← מילה של הלקוח (areo-voice.md). קודים (R19, S07) מנוקים ב-voice_scrub ---------
_GLOSSARY_HE = [
    (re.compile(r"(?<![א-ת])(ו?[בלמשכ]?)ה?קורפוס(?![א-ת])"),
     lambda m: m.group(1) + ("הסכמים" if m.group(1) else "ההסכמים")),
    (re.compile("(?<![א-ת])([ושהכלב]{0,2})נגזר(ה|ת|ים|ות)? מ(ה?)"),
     lambda m: "%sמבוסס%s על %s" % (m.group(1), {"ה": "ת", "ת": "ת"}.get(m.group(2) or "", m.group(2) or ""),
                                    "ה" if m.group(3) else "")),
    (re.compile("(?<![א-ת])([ושהכלב]{0,2})נגזר(ה|ת|ים|ות)?(?![א-ת])"),
     lambda m: "%sמבוסס%s" % (m.group(1), {"ה": "ת", "ת": "ת"}.get(m.group(2) or "", m.group(2) or ""))),
    (re.compile("(?<![א-ת])טעונה (אישור|בדיקה)"), lambda m: "ממתינה ל" + m.group(1)),
    (re.compile("(?<![א-ת])טעונות (אישור|בדיקה)"), lambda m: "ממתינות ל" + m.group(1)),
    (re.compile("(?<![א-ת])טעונים (אישור|בדיקה)"), lambda m: "ממתינים ל" + m.group(1)),
    (re.compile("(?<![א-ת])טעון (אישור|בדיקה)"), lambda m: "ממתין ל" + m.group(1)),
    (re.compile("(?<![א-ת])הטעונים (אישור|בדיקה)"), lambda m: "הממתינים ל" + m.group(1)),
    (re.compile("(?<![א-ת])הטעונות (אישור|בדיקה)"), lambda m: "הממתינות ל" + m.group(1)),
    (re.compile("(?<![א-ת])(ה?)מסלולים(?![א-ת])"), lambda m: m.group(1) + "עמדות"),
    (re.compile("(?<![א-ת])(ו?[בלמשכ]?ה?)מסלול(?![א-ת])"), lambda m: m.group(1) + "עמדה"),
]
_GLOSSARY_EN = [
    (re.compile(r"corpus", re.I), "agreements"),
    (re.compile(r"derived from", re.I), "based on"),
    (re.compile(r"needs approval", re.I), "awaiting approval"),
]
# מזהים, ציטוטים מילוליים ונוסח מוצע (טביעת האצבע של האישור מחושבת עליו) אינם משתנים
_SKIP = {"id", "rule_id", "src", "source_id", "source_ref", "refs", "related_rule_id", "rules", "seg", "segment_id",
         "item_id", "evidence", "ev", "quote", "text", "basis_refs", "market_source_ids", "supports", "pb", "source",
         "baseline", "clause", "clause_en", "clause_lang", "fallback_wording", "slots", "url", "path", "loc",
         "proposed_clause", "family_id", "playbook_id", "ls_key", "slug", "h"}


def voice_text(s, lang="he"):
    """ישויות HTML שנשארו בטקסט (&quot;) הופכות לתו עצמו, ואז מילון התצוגה."""
    import html as _h
    if not isinstance(s, str) or not s:
        return s
    if "&" in s:
        s = _h.unescape(s)
    if re.search("[א-ת]", s):
        for rx, rep in _GLOSSARY_HE:
            s = rx.sub(rep, s)
    if lang == "en":
        for rx, rep in _GLOSSARY_EN:
            s = rx.sub(rep, s)
    return s


def _walk_voice(v, lang, key=""):
    if isinstance(v, dict):
        return {k: (x if k in _SKIP else _walk_voice(x, lang, k)) for k, x in v.items()}
    if isinstance(v, list):
        return [x if key in _SKIP else _walk_voice(x, lang, key) for x in v]
    return voice_text(v, lang) if isinstance(v, str) else v


def _norm_ws(t):
    return re.sub(r"\s+", " ", str(t or "")).strip()


def finish_payload(payload, lang="he"):
    """ניסוח ללקוח ועמדת האדום. clause_dup / pos_dup: האדום זהה לירוק או לצהוב, והדף אינו מציג אותו כאדום
    (עמדת אדום משלה, או בלי). הנוסח עצמו אינו משתנה, כי טביעת האצבע של האישור מחושבת עליו."""
    for r in payload.get("rules") or []:
        tl = r.get("tl") or {}
        red = tl.get("red")
        if not red:
            continue
        for other in ("green", "yellow"):
            o = tl.get(other) or {}
            if _norm_ws(red.get("clause")) and _norm_ws(red.get("clause")) == _norm_ws(o.get("clause")):
                red.setdefault("clause_dup", other)
            if _norm_ws(red.get("pos")) and _norm_ws(red.get("pos")) == _norm_ws(o.get("pos")):
                red.setdefault("pos_dup", other)
    for key in ("rules", "queue", "templateFindings", "coverage", "assumptions", "departments", "reg", "scope", "meta"):
        if key in payload:
            payload[key] = _walk_voice(payload[key], lang, key)
    return payload


def build_gaps(m, rules, lang="he"):
    """נושאי ליבה שאין להם ביטוי באף מסמך שנסרק: פער, לא היעדר (כלל 9). רשימת הנושאים היא של הלקוח בלבד:
    profile_topics שהמחקר המאושר או ההקמה פתחו ולא נמצאו בקורפוס (evidence_in_corpus: false),
    scope_summary.core_topics[] שאין להם כלל, וכלל שכל עמדותיו הצעת Areo בלי ציטוט. אין רשימה קבועה בסקיל."""
    gaps, seen = [], set()
    by_id = {r["id"]: r for r in rules}
    for t in m.get("profile_topics") or []:
        if isinstance(t, dict) and t.get("evidence_in_corpus") is False and t.get("topic"):
            key = norm_key(t["topic"])
            if key not in seen:
                seen.add(key)
                gaps.append({"topic": t["topic"], "rule_id": t.get("rule_id") or "", "origin": "profile",
                             "trigger": t.get("trigger") or ""})
    for t in (m.get("scope_summary") or {}).get("core_topics") or []:
        name = t.get("topic") if isinstance(t, dict) else t
        rid = (t.get("rule_id") if isinstance(t, dict) else "") or ""
        if name and norm_key(name) not in seen and (not rid or rid not in by_id):
            seen.add(norm_key(name))
            gaps.append({"topic": name, "rule_id": rid,
                         "origin": (t.get("origin") if isinstance(t, dict) else "") or "client"})
    for r in m.get("rules") or []:
        rid = pick(r, "rule_id", "id")
        tl = r.get("traffic_light") or {}
        bases = {(tl.get(c) or {}).get("basis") for c in LIGHTS if tl.get(c)}
        cited = any(e.get("track") in LIGHTS for e in r.get("evidence") or [])
        if bases and bases <= {"areo_proposal", "market_standard"} and not cited:
            name = pick(r, "topic_name", "topic") or rid
            if norm_key(name) not in seen:
                seen.add(norm_key(name))
                gaps.append({"topic": name, "rule_id": rid, "origin": "no_evidence"})
    return gaps


def norm_key(t):
    return re.sub(r"\s+", " ", str(t or "")).strip().lower()


def convert(m, lang="he", model_path=None, profile=None, extract=None):
    cites = []
    sources, friendly = build_sources(m)
    if extract is None and model_path:
        extract = E.find_extract(m, model_path)
    if not extract:
        warn("אין קובץ חילוץ (--extract): סיווג הראיה של הציטוטים (ev_kind) הוא unknown")
    rules = build_rules(m, cites, lang, extract)
    by_id = {r["id"]: r for r in rules}
    cells = S.record_cells_for(m, model_path) if model_path else {}
    st = S.derive_status(m, cells, lang=lang)
    approval_flags(m, rules, cells, st)
    meta = build_meta(m, lang, st, profile)
    meta["gaps"] = build_gaps(m, rules, lang)
    meta["sources_counted"] = {"agreements": sum(1 for v in sources.values() if v.get("is_agreement")),
                               "non_agreements": sum(1 for v in sources.values()
                                                     if v.get("kind") == "internal" and not v.get("is_agreement"))}
    payload = {
        "meta": meta,
        "scope": scope_block(m, lang),
        "sources": sources,
        "friendly": friendly,
        "rules": rules,
        "cites": cites,
        "segments": build_segments(m, by_id, lang),
        "precedents": m.get("previous_agreements_where_language_accepted") or [],
        "templateFindings": build_findings(m),
        "queue": build_queue(m),
    }
    for key, value in (("reg", m.get("regulatory_research")),
                       ("commercial", m.get("commercial")),
                       ("coverage", m.get("coverage")),
                       ("market", build_market(m)),
                       ("playbooks", build_playbooks(m)),
                       ("external_sources", m.get("external_sources")),
                       ("external_sources_table", m.get("external_sources_table")),
                       ("assumptions", m.get("assumptions")),
                       ("departments", build_departments(m)),
                       ("cross", m.get("cross_family_links"))):
        if value:
            payload[key] = value
    return finish_payload(_scrub_payload(payload, m, lang), lang)


# שדות שמחזיקים נוסח מקור מילולי או מזהים: אינם נוגעים בהם (ציטוט נשאר כלשונו)
_KEEP = ("quote", "text", "q", "clause_text", "verbatim", "excerpt", "id", "rid", "rule_id", "ref", "refs")


def _scrub_payload(payload, m, lang):
    """מזהים פנימיים (R19, S07#p12) בטקסט חופשי שהלקוח קורא בסביבת העבודה: שם הנושא או המסמך במקומם (voice_scrub).
    רק מחרוזת שיש בה רווח (טקסט, לא מזהה), ולא שדות של ציטוט ומזהים."""
    sc = voice_scrub.Scrubber(m, lang)

    def walk(o):
        if isinstance(o, dict):
            return {k: (v if k in _KEEP else walk(v)) for k, v in o.items()}
        if isinstance(o, list):
            return [walk(x) for x in o]
        if isinstance(o, str) and " " in o.strip():
            return sc.text(o)
        return o
    return walk(payload)


def index_models(data_dir):
    """כל הפלייבוקים שבאינדקס, כ-(רשומה, נתיב המודל). פלייבוק שהמודל שלו
    חסר אינו נבלע בשקט: הוא מדווח, כי בורר שחסר בו סוג נראה כמו מדיניות
    שאינה קיימת."""
    path = os.path.join(data_dir, "playbooks", "index.json")
    if not os.path.exists(path):
        # הרישום (register_playbook.py) רץ אחרון, ולכן בבנייה הראשונה אין עדיין אינדקס.
        # זה אינו כישלון: הקורא מוסיף את המודל שנמסר, או את המודלים שבתיקיות הסוגים
        warn("אין %s (הרישום רץ אחרון). הדף נבנה מהמודל שנמסר, או מ-playbooks/*/playbook-model.json"
             % path)
        return None
    idx = json.load(io.open(path, encoding="utf-8"))
    entries = idx.get("playbooks") if isinstance(idx, dict) else idx
    out = []
    for e in entries or []:
        rel = e.get("core_path") or e.get("path")
        if not rel:
            warn("רשומה באינדקס בלי core_path: %s" % json.dumps(e, ensure_ascii=False)[:100])
            continue
        mp = os.path.join(data_dir, os.path.dirname(rel), "playbook-model.json")
        if not os.path.exists(mp):
            warn("לרשומה %s אין playbook-model.json (%s), והיא אינה בסביבת העבודה"
                 % (e.get("family_id") or rel, mp))
            continue
        out.append((e, mp))
    return out


def folder_models(data_dir):
    """בלי אינדקס ובלי מודל: כל playbooks/<family_id>/playbook-model.json, ברשומה ריקה."""
    root = os.path.join(data_dir, "playbooks")
    out = []
    for name in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        mp = os.path.join(root, name, "playbook-model.json")
        if os.path.isfile(mp):
            out.append(({"family_id": name}, mp))
    return out


def book_id(m, entry=None):
    return (pick(m, "family_id", "playbook_id")
            or pick(entry or {}, "family_id") or "playbook")


def build_book(m, entry=None, lang="he", model_path=None, profile=None, extract=None):
    """פלייבוק אחד, שלם, כפי שהדף מציג סוג הסכם אחד. `pb` מזהה אותו לבורר
    ולאשף, ו-rules[].pb משייך אליו כל סעיף."""
    b = convert(m, lang, model_path, profile, extract)
    bid = book_id(m, entry)
    fam = (pick(b.get("scope") or {}, "contract_families") or [{}])[0] or {}
    b["pb"] = {"id": bid,
               "family": pick(fam, "contract_family_name", "label")
               or pick(entry or {}, "family_name") or bid,
               "role": pick(fam, "company_role") or pick(entry or {}, "company_role_code") or ""}
    for r in b["rules"]:
        r["pb"] = bid
    b.pop("playbooks", None)
    return b


def merge_books(books, current=None, company_key=None):
    """הדף כולו: הפלייבוק שנבחר כברירת מחדל בשורש (כך כל קורא ישן של הדף
    רואה דף שלם ותקין), ולצדו כל הספרים והרשימה לבורר."""
    if not books:
        sys.exit("אין אף פלייבוק להציג")
    ids = [b["pb"]["id"] for b in books]
    if current and current not in ids:
        sys.exit("--current %s אינו באינדקס. הקיימים: %s" % (current, ", ".join(ids)))
    if not current:
        current = max(books, key=lambda b: str(b["meta"].get("updated") or ""))["pb"]["id"]
    cur = next(b for b in books if b["pb"]["id"] == current)
    payload = json.loads(json.dumps(cur))
    payload["books"] = {b["pb"]["id"]: b for b in books}
    payload["playbooks"] = [{
        "id": b["pb"]["id"], "family": b["pb"]["family"], "role": b["pb"]["role"],
        "rules": len(b["rules"]), "segments": len(b.get("segments") or []),
        "scanned": (b["meta"].get("build_path") or {}).get("n") or 0,
        "updated": b["meta"].get("updated") or "",
        "status_label": b["meta"].get("status_label") or "",
        "current": b["pb"]["id"] == current} for b in books]
    # המפתח של הדף כולו (הבחירה בבורר, יום ולילה) הוא של החברה, ולא של
    # פלייבוק אחד. ההערות נשמרות לכל פלייבוק במפתח שלו, שבתוך הספר
    company = payload["meta"].get("company") or company_key or "company"
    payload["meta"]["page_key"] = "playbooks_" + ls_key(company)
    return payload


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model", nargs="?", help="playbook-model.json, לפלייבוק אחד. עם --data: מצטרף "
                                             "לפלייבוקים שבאינדקס, וכשאין אינדקס הוא היחיד בדף")
    ap.add_argument("out")
    ap.add_argument("--data", help="תיקיית Areo-נתונים: כל הפלייבוקים שבאינדקס, בדף אחד")
    ap.add_argument("--current", help="family_id של הפלייבוק שנפתח ראשון. "
                                      "ברירת מחדל: זה שעודכן אחרון")
    ap.add_argument("--meta", help="שדות הצגה שאינם במודל, למשל הודעת הדגמה או docAccess")
    ap.add_argument("--lang", choices=("he", "en"),
                    help="שפת הדף. בלעדיו: deliverable_language מהפרופיל או מהמודל, וברירת המחדל עברית")
    ap.add_argument("--profile", help="פרופיל-לקוח.json: deliverable_language ו-display_language")
    ap.add_argument("--extract", help="corpus-extract.json: ממנו נגזר סיווג הראיה של כל ציטוט (ev_kind). "
                                      "בלעדיו: coverage.extract_ref ליד המודל, ואחרת unknown")
    # intermixed: "<model> --data <dir> <out>" מתפרש נכון גם כשהדגל בין שני הארגומנטים המיקומיים
    a = ap.parse_intermixed_args()
    profile = json.load(io.open(a.profile, encoding="utf-8")) if a.profile else None
    extract = json.load(io.open(a.extract, encoding="utf-8")) if a.extract else None
    if not a.model and not a.data:
        sys.exit("יש לתת מודל אחד, או --data לכל הפלייבוקים")
    # הפלט (out) לעולם אינו נכתב על המודל, על הפרופיל, על קובץ התוספות או על מסמך קיים
    try:
        guard_out(a.out, inputs=[a.model, a.profile, a.meta, a.extract])
    except OutputRefused as exc:
        print("refused: %s" % exc, file=sys.stderr)
        sys.exit(2)
    if a.data:
        books = []
        indexed = index_models(a.data)
        if indexed is None and not a.model:
            indexed = folder_models(a.data)
            if not indexed:
                sys.exit("אין playbooks/index.json ואין playbook-model.json בתיקיות הסוגים של %s. "
                         "תן את המודל שנבנה: build_workspace_payload.py <model> --data %s <out>"
                         % (a.data, a.data))
        models = [(entry, json.load(io.open(mp, encoding="utf-8")), mp) for entry, mp in indexed or []]
        current = a.current
        if a.model:
            # המודל שנמסר הוא הגרסה העדכנית: הוא מחליף את הרשומה של אותו סוג באינדקס,
            # או מצטרף אליה כשהסוג טרם נרשם, ונפתח ראשון כשלא נבחר אחר
            given = json.load(io.open(a.model, encoding="utf-8"))
            gid = book_id(given)
            entry = next((e for e, m, _ in models if book_id(m, e) == gid), None)
            models = [(e, m, p) for e, m, p in models if book_id(m, e) != gid] + [(entry, given, a.model)]
            current = current or gid
        # שפה אחת לדף כולו: היא של הפרופיל, ולא של פלייבוק אחד
        lang = resolve_lang(models[0][1] if models else {}, profile, a.lang)
        for entry, m, mp in models:
            books.append(build_book(m, entry, lang, mp, profile, extract))
        payload = merge_books(books, current=current)
    else:
        m = json.load(io.open(a.model, encoding="utf-8"))
        payload = convert(m, resolve_lang(m, profile, a.lang), a.model, profile, extract)
    if a.meta:
        extra = json.loads(io.open(a.meta, encoding="utf-8").read())
        # תוספות הצגה בלבד. הן אינן יוצרות עמדה, ראיה או מספר. בדף של כמה
        # פלייבוקים הן חלות על כולם, כי הן של הדף ולא של סוג הסכם
        # זהות הספר אינה תוספת הצגה: מפתח שמירה משותף לשני ספרים היה
        # מציג הערה על סעיף בהסכמי סודיות גם בהסכמי שירותים
        identity = ("id", "slug", "ls_key", "title", "wizard_href", "page_key")
        books = list((payload.get("books") or {}).values())
        for k, v in (extra.get("meta") or extra).items():
            if not books or k not in identity:
                payload["meta"][k] = v
            for b in books:
                if k not in identity:
                    b["meta"][k] = v
    io.open(a.out, "w", encoding="utf-8").write(
        json.dumps(payload, ensure_ascii=False, indent=2))
    print("נכתב %s: %d סעיפים, %d ציטוטים, %d מקורות, %d סגמנטים"
          % (a.out, len(payload["rules"]), len(payload["cites"]),
             len(payload["sources"]), len(payload["segments"])))
    if payload.get("books"):
        print("פלייבוקים בדף: %d" % len(payload["books"]))
        for p in payload["playbooks"]:
            print("  %s %s · %s (%d סעיפים)" % ("*" if p["current"] else " ",
                                                p["family"], p["role"], p["rules"]))
    print("שפת הדף: %s" % payload["meta"].get("lang"))
    bp = payload["meta"].get("build_path")
    if bp:
        print("פס הבסיס: %d %s, מסלול %s" % (bp["n"], basis_line.docs(payload["meta"].get("corpus_status")),
                                              bp["path"]))
    print("הבא: python3 validate_data.py --data %s" % a.out)


if __name__ == "__main__":
    main()
