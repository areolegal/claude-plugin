#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""בונה את גרעין ההפעלה (playbook-core.json) מהמודל, בקוד.

`playbook-core-schema.md`: הגרעין "נגזר במלואו מהמודל", "לעולם אינו נערך ידנית ואינו
מקור אמת", ונבנה מחדש בכל שמירה של המודל. עד עכשיו לא היה לו סקריפט: בכל הרצה הבונה כתב
את הגרעין בעצמו, וכל הרצה יצאה אחרת. בהרצה חיה הגרעין הראשון נכשל בחוזה מול
הנושא ונותן (`check_playbook_contract.py`): בלי קוד צד ומשפחה, בלי מספר כלל ובלי נוסח להחלה.
הסקריפט הזה הוא הדרך היחידה לבנות גרעין.

    python3 scripts/build_playbook_core.py --model <playbooks/<family_id>/playbook-model.json> \\
        [--out <playbooks/<family_id>/playbook-core.json>]

אחריו: `validate_playbook_model.py <model> --core <core>` ו-`check_playbook_contract.py`
של הנושא ונותן. קוד יציאה: 0 נכתב, 2 קלט חסר.
"""
import argparse
import datetime as _dt
import hashlib
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # גם ב-python -I, שאינו מוסיף את תיקיית הסקריפט
try:
    import areo_lib  # noqa: F401  מוסיף את areolegal/lib לנתיב הייבוא
    from playbook import status as S  # noqa: E402
except ImportError:      # הסקריפט רץ גם בלי הספרייה; אז התווית נלקחת מהמודל כמו שהיא
    S = None
try:
    from playbook import validate_model as VM  # noqa: E402  מקור העמדה (הסכם וסעיף) והנקודות בלי מקור מורשה
except ImportError:
    VM = None
try:
    from common.cli import OutputRefused, guard_out  # noqa: E402
except ImportError:      # בלי הספרייה: רק הבדיקה שהפלט אינו המודל עצמו
    class OutputRefused(Exception):
        pass

    def guard_out(out, inputs=()):
        k = os.path.normcase(os.path.realpath(out))
        if any(p and os.path.normcase(os.path.realpath(p)) == k for p in inputs):
            raise OutputRefused("--out הוא קובץ קלט: %s" % out)
        return os.path.abspath(out)

TRACKS = ("green", "yellow", "red")
# הנושא "טכני": הרשימה הסגורה של `clause-catalog.md`, עם התווית שמוצגת. הגרעין נושא אותה, כדי שהנושא ונותן
# ימפה כל סעיף בנייר של הצד השני לנושא בפלייבוק או לקוד טכני, ולא ישאיר סעיף בלי שיוך
TECHNICAL_TOPICS = (("signature_block", "בלוק חתימה"), ("party_identification", "זיהוי הצדדים"),
                    ("notice_addresses", "כתובות להודעות"), ("counterparts_esignature", "עותקים וחתימה אלקטרונית"),
                    ("headings", "כותרות לנוחות"), ("interpretation_grammar", "כללי לשון"),
                    ("recitals_descriptive", "מבוא תיאורי"), ("neutral_definition", "הגדרה שאינה משנה היקף"),
                    ("bank_details", "פרטי חשבון בנק"), ("delivery_points_list", "רשימת נקודות אספקה"),
                    ("admin_form_fields", "שדות מנהליים בטופס"),
                    ("statutory_admin_restatement", "חזרה על חובה מנהלית שבחוק"))
MARKET_OR_AREO = ("market_standard", "areo_proposal")
CORE_SCHEMA = "2.0"


def text_of(v):
    """הנוסח כמחרוזת: {"he","en"} או {"text"} או מחרוזת. העברית קודמת."""
    if isinstance(v, dict):
        for k in ("he", "text", "en"):
            if isinstance(v.get(k), str) and v[k].strip():
                return v[k]
        return ""
    return v if isinstance(v, str) else ""


def fallback_source(yellow):
    """מקור נוסח הנסיגה: מזהה ציטוט או תשובה, market_standard או areo_proposal (סכמת הגרעין)."""
    fw = yellow.get("fallback_wording")
    src = fw.get("source") if isinstance(fw, dict) else None
    if src in MARKET_OR_AREO:
        return src
    refs = [r for r in yellow.get("basis_refs") or () if isinstance(r, str) and r.strip()]
    if refs:
        return refs[0]
    if yellow.get("basis") in MARKET_OR_AREO:
        return yellow["basis"]
    return src or "areo_proposal"


def block(track, cell, sources=None):
    out = {"position": cell.get("position") or "", "basis": cell.get("basis") or "",
           "label": cell.get("label") or ""}
    # כלל מייסד 12: כל עמדה מציגה את ההסכם והסעיף שעליהם נשענה. נבנה בקוד מ-basis_refs ומרשימת הראיות של הכלל
    if cell.get("basis_refs"):
        out["basis_refs"] = [str(x) for x in cell["basis_refs"] if str(x).strip()]
    if sources:
        out["sources"] = [{k: v for k, v in x.items() if k in ("agreement", "clause", "evidence_id")}
                          for x in sources]
    if cell.get("source_label"):
        out["source_label"] = cell["source_label"]
    if cell.get("market_source_ids"):
        out["source_ids"] = list(cell["market_source_ids"])
    if track == "green":
        out["preferred_wording"] = text_of(cell.get("proposed_clause"))
    elif track == "yellow":
        out["fallback_wording"] = text_of(cell.get("fallback_wording")) or text_of(cell.get("proposed_clause"))
        out["fallback_source"] = fallback_source(cell)
        # מדרגות הנסיגה בסדר, מהקרובה לירוק (playbook-schema.md, yellow.fallback_steps). הנושא ונותן צריך שתיים לפחות
        # בנושא מהותי, כדי שתהיה מדרגה לסבב 2 שאינה הנסיגה האחרונה
        out["fallback_steps"] = [text_of(x) for x in cell.get("fallback_steps") or () if text_of(x)]
        if cell.get("fallback_steps_note"):
            out["fallback_steps_note"] = cell["fallback_steps_note"]
    else:
        out["red_line"] = cell.get("position") or ""
        if text_of(cell.get("proposed_clause")):
            out["remedy_wording"] = text_of(cell.get("proposed_clause"))
    return out


def legal_review(rule):
    v = rule.get("legal_review_required")
    if isinstance(v, list):
        open_items = [x for x in v if not (isinstance(x, dict) and x.get("checked_by"))]
        # evidence-policy.md ו-playbook-schema.md: track (green | yellow | red) לכל רשומה, כמו שגיליון העמדות
        # קורא אותו. לפני כן נקרא כאן רק tracks, ו-legal_review_tracks יצא ריק;
        # tracks נקרא עדיין לתאימות
        tracks = sorted({t for x in open_items if isinstance(x, dict)
                         for t in ([x["track"]] if isinstance(x.get("track"), str) and x["track"] else [])
                         + list(x.get("tracks") or ())})
        return bool(open_items), tracks
    return bool(v), []


def track_sources(rule, model, cell):
    """[{agreement, clause, evidence_id}] של עמדה אחת, מ-playbook/validate_model.position_sources. [] בלי הספרייה."""
    if VM is None or not isinstance(model, dict) or not isinstance(cell, dict):
        return []
    try:
        return VM.position_sources(rule, model, cell)
    except Exception:  # noqa: BLE001
        return []


def open_legal_point(rule, model):
    """True כשמחקר הרשת הותר ולא נמצא מקור מורשה לנקודה (validate_model.no_source_notes): הסעיף נושא את ההערה הגלויה."""
    if VM is None or not isinstance(model, dict):
        return False
    try:
        return any(rid == rule.get("rule_id") for rid, _n, _h in VM.no_source_notes(model))
    except Exception:  # noqa: BLE001
        return False


def clause(rule, model=None):
    tl = rule.get("traffic_light") or {}
    blocks = {t: block(t, tl.get(t) or {}, track_sources(rule, model, tl.get(t) or {})) for t in TRACKS}
    lr, lr_tracks = legal_review(rule)
    out = {"id": rule.get("rule_id"), "title": rule.get("topic_name") or rule.get("topic") or "",
           # מה הנושא מכסה, כדי למפות אליו סעיף בנייר של הצד השני; topic_origin: catalog | corpus_derived
           "clause_issue": rule.get("clause_issue") or "", "topic_ids": rule.get("topic_ids") or [],
           "topic_origin": rule.get("topic_origin") or "catalog", "clause_kind": rule.get("clause_kind") or "",
           "policy_ref": rule.get("policy_ref") or rule.get("rule_id"),
           "importance": rule.get("importance") or "",
           "activation_conditions": rule.get("activation_conditions") or [],
           # בדיקת התוצאה של הכלל, שהנושא ונותן מריץ על הנוסח המתקבל
           "post_checks": rule.get("post_checks") or [],
           "green": blocks["green"], "yellow": blocks["yellow"], "red": blocks["red"],
           # השדות השטוחים: עותק של הבלוקים, לתאימות עם הנושא ונותן והמנסח
           "red_line": blocks["red"]["red_line"],
           "preferred_wording": blocks["green"]["preferred_wording"],
           "fallback_wording": blocks["yellow"]["fallback_wording"],
           "fallback_source": blocks["yellow"]["fallback_source"],
           "fallback_steps": blocks["yellow"]["fallback_steps"],
           "round1_posture": rule.get("round1_posture") or "hold_green",
           "round1_posture_source": rule.get("round1_posture_source") or "importance",
           "statutory_override": rule.get("statutory_override") or [],
           "evidence_count": rule.get("evidence_count") if rule.get("evidence_count") is not None else 0,
           "policy_status": rule.get("policy_status") or "Inferred",
           "confidence": rule.get("confidence") or "",
           "presence": rule.get("presence_rule") or {},
           "walk_away": bool(rule.get("walk_away")),
           "legal_review_required": lr, "legal_review_tracks": lr_tracks,
           "segment_overrides": [], "model_ref": "rules[id=%s]" % rule.get("rule_id")}
    # אין רצפות ותקרות של הדין בקוד. נקודה שמחקר הרשת הותר לה ולא נמצא לה מקור מורשה נושאת הערה גלויה, והסוכן שיש בידו
    # רק הגרעין מציג אותה כמו שהיא. שום דבר אינו נחסם בגללה
    if open_legal_point(rule, model):
        out["no_approved_source"] = True
        out["no_source_note"] = (VM.no_source_text(model.get("output_language") or "he") if VM else "")
    for t in TRACKS:
        if isinstance(tl.get(t), dict) and isinstance(tl[t].get("values"), dict):
            out[t]["values"] = tl[t]["values"]
    if rule.get("walk_away") and rule.get("walk_away_source"):
        out["walk_away_source"] = rule["walk_away_source"]
    for var in rule.get("segment_variants") or ():
        if not isinstance(var, dict) or not var.get("segment_id"):
            continue
        vtl = var.get("traffic_light") or {}
        ov = {"segment_id": var["segment_id"], "negotiation_mode": var.get("negotiation_mode") or "negotiated",
              "round1_posture": var.get("round1_posture") or out["round1_posture"],
              "evidence_count": var.get("evidence_count") if var.get("evidence_count") is not None else 0}
        for t in TRACKS:
            if vtl.get(t):
                ov[t] = block(t, vtl[t], track_sources(rule, model, vtl[t]))
        ov["red_line"] = (ov.get("red") or {}).get("red_line", out["red_line"])
        ov["preferred_wording"] = (ov.get("green") or {}).get("preferred_wording", out["preferred_wording"])
        ov["fallback_wording"] = (ov.get("yellow") or {}).get("fallback_wording", out["fallback_wording"])
        ov["fallback_source"] = (ov.get("yellow") or {}).get("fallback_source", out["fallback_source"])
        ov["fallback_steps"] = (ov.get("yellow") or {}).get("fallback_steps", out["fallback_steps"])
        out["segment_overrides"].append(ov)
    return out


def market_sources(model):
    mr = model.get("market_research") or {}
    supports = {}
    for rng in mr.get("ranges") or ():
        if not isinstance(rng, dict):
            continue
        for point in ("ours", "middle", "theirs"):
            p = rng.get(point)
            for sid in ((p if isinstance(p, dict) else {}).get("source_ids") or ()):
                supports.setdefault(sid, []).append({"rule_id": rng.get("rule_id") or rng.get("topic"),
                                                     "range_point": point})
    out = []
    for r in mr.get("source_refs") or ():
        if not isinstance(r, dict) or r.get("read_status") in ("located_not_read", "excluded", "blocked"):
            continue
        out.append({k: r.get(k, "") for k in ("source_id", "issuing_body", "document", "doc_date",
                                               "drafter_role", "drafted_by", "url", "retrieved_at")}
                   | {"supports": supports.get(r.get("source_id"), [])})
    return out


def coverage_summary(model):
    """הכיסוי, בקצרה: כמה יחידות קיבלו נושא, קוד טכני או סימון ייחודי, וכמה נושאים חדשים נגזרו מהקורפוס."""
    cov = model.get("coverage") or {}
    num = lambda a, b: cov.get(a) if isinstance(cov.get(a), int) else cov.get(b)  # noqa: E731
    return {"units": num("units", "units_total"), "topic_units": num("topic_units", "units_mapped"),
            "technical_units": num("technical_units", "units_technical"),
            "unique_units": num("unique_units", "units_unique") or 0,
            "unmapped_units": num("unmapped_units", "units_unmapped"),
            # ספר הכיסוי (validate_model.coverage_ledger): סעיפים = עם מדיניות + בלי מדיניות שאפשר לחלץ + ייחודיים
            "ledger": (VM.coverage_ledger(model) if VM is not None else None),
            "topics": len([r for r in model.get("rules") or () if isinstance(r, dict)]),
            "topics_new": sum(1 for r in model.get("rules") or () if isinstance(r, dict)
                              and r.get("topic_origin") == "corpus_derived")}


def gate_label(model, model_path):
    """המעמד והתווית מהפונקציה של שער המדיניות (playbook/status.gate_status), כמו באינדקס. status_label שנשמר
    במודל יכול להיות ישן: בהרצה קודמת הגרעין אמר "מבוסס הסכמי החברה" והשער "מבוסס נוסחים שהחברה מציגה"."""
    if S is not None:
        st = S.gate_status(model, model_path)
        return st["playbook_status"], st["label"]
    return model.get("playbook_status") or "Draft", model.get("status_label") or ""


def build(model, model_path):
    sc = model.get("scope_summary") or {}
    pb_status, pb_label = gate_label(model, model_path)
    fams = [f for f in sc.get("contract_families") or () if isinstance(f, dict)]
    with open(model_path, "rb") as fh:
        sha = hashlib.sha256(fh.read()).hexdigest()
    role_code = model.get("company_role_code") or next((f.get("company_role_code") for f in fams
                                                        if f.get("company_role_code")), "")
    return {
        "schema_version": CORE_SCHEMA,
        "playbook_id": model.get("playbook_id") or "",
        "family_id": model.get("family_id") or "",
        # האיתור של הנושא ונותן מתאים פלייבוק לפי משפחה וצד (check_playbook_contract.py)
        "family_code": model.get("family_code") or model.get("family_id") or "",
        "company_role_code": role_code,
        "corpus_origin": model.get("corpus_origin") or sc.get("corpus_origin") or "own",
        "market_research_date": (model.get("market_research") or {}).get("research_date") or "",
        "market_sources": market_sources(model),
        "playbook_status": pb_status,
        "status_label": pb_label,
        "produced_with": model.get("produced_with") or {},
        "playbook_version": str(model.get("version") or ""),
        "core_version": model.get("core_version") or "",
        "generated_at": _dt.date.today().isoformat(),
        "source_model": os.path.basename(model_path),
        "source_model_updated": (model.get("last_updated") or model.get("generated_at") or "")[:10],
        "source_model_sha256": sha,
        "company_role": sc.get("company_role") or next((f.get("company_role") for f in fams
                                                        if f.get("company_role")), ""),
        "output_language": model.get("output_language") or "he",
        "applicability": model.get("applicability") or {},
        # הדין החל (או מדינת ההתאגדות) כקודי מדינה: בלעדיו אין הנחה של מדינה
        "home_countries": home_of(model),
        "contract_families": [{k: f.get(k) for k in ("contract_family_name", "family_aliases", "company_role",
                                                     "company_role_code") if f.get(k) is not None}
                              for f in fams],
        "clauses": [clause(r, model) for r in model.get("rules") or () if isinstance(r, dict)],
        # כל נושא בפלייבוק הוא סעיף בגרעין, גם נושא חדש שנגזר מהקורפוס; ולצידם הנושא "טכני" והסעיפים הייחודיים
        "technical_topics": [{"code": c, "label": lbl} for c, lbl in TECHNICAL_TOPICS],
        "unique_clauses": [{k: u.get(k) for k in ("ref", "kind", "queue_id") if u.get(k)}
                           for u in (model.get("coverage") or {}).get("unique_clauses") or () if isinstance(u, dict)],
        "coverage": coverage_summary(model),
        "segments": [{k: s.get(k) for k in ("segment_id", "label", "criteria", "negotiation_mode")}
                     for s in ((model.get("segmentation_model") or {}).get("segments") or ())
                     if isinstance(s, dict)],
        # תוצאת הבדיקות הזולות (playbook/validity.validity_summary): סוכן שיש בידו רק הגרעין מזהיר את הלקוח כשהפלייבוק
        # אינו עובר את הבדיקות של עצמו (validity.playbook_warnings), בלי לפתוח את המודל ובלי ההסכמים
        "validity": validity_of(model),
    }


def stamp_model_label(model, model_path):
    """בבנייה (אין עדיין approval_records): playbook_status ו-status_label של המודל ושל ה-handoff נכתבים מהגזירה
    האחת (status.stamp), לפני שהגרעין, האינדקס, ה-Word וסביבת העבודה נבנים, כדי שהמודל לא ישמור תווית שנכתבה ביד
    או בהרצה קודמת (ניסוי ארבעת הסוגים: המודל אמר "מבוסס הסכמי החברה", והשער אמר "לא מבוסס"). אחרי קליטה, הקליטה
    היא שכותבת (after_ingest), והמאמת מסמן סטייה. מחזיר את התווית כשהמודל עודכן, אחרת None."""
    if S is None or model.get("approval_records"):
        return None
    before = (model.get("playbook_status"), model.get("status_label"),
              (model.get("handoff") or {}).get("status_label") if isinstance(model.get("handoff"), dict) else None)
    st = S.stamp(model, None, None)
    after = (model.get("playbook_status"), model.get("status_label"),
             (model.get("handoff") or {}).get("status_label") if isinstance(model.get("handoff"), dict) else None)
    if before == after:
        return None
    with io.open(model_path, "w", encoding="utf-8") as fh:
        json.dump(model, fh, ensure_ascii=False, indent=1)
    return st["label"]


def home_of(model):
    """קודי המדינות של הדין החל על הסוג (או מדינת ההתאגדות), מ-playbook/validate_model.home_countries. [] כשאינם ידועים."""
    try:
        from playbook import validate_model as VM
        return VM.home_countries(model)
    except Exception:  # noqa: BLE001
        return []


def validity_of(model):
    """{'status', 'codes', 'rules', 'no_company_position'} מ-playbook/validity, או {} כשהספרייה אינה זמינה."""
    try:
        from playbook import validity as VY
    except ImportError:
        return {}
    return VY.validity_summary(model)


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--model", required=True, help="playbook-model.json")
    ap.add_argument("--out", help="ברירת המחדל: playbook-core.json לצד המודל")
    a = ap.parse_args(argv)
    if not os.path.exists(a.model):
        print("המודל אינו קיים: %s" % a.model)
        return 2
    with io.open(a.model, encoding="utf-8") as fh:
        model = json.load(fh)
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(a.model)), "playbook-core.json")
    try:
        out = guard_out(out, inputs=[a.model])
    except OutputRefused as exc:
        print("refused: %s" % exc, file=sys.stderr)
        return 2
    stamped = stamp_model_label(model, a.model)
    if stamped:
        print("המודל: התווית נכתבה מהגזירה האחת (status.base_code): %s" % stamped)
    core = build(model, a.model)
    with io.open(out, "w", encoding="utf-8") as fh:
        json.dump(core, fh, ensure_ascii=False, indent=1)
    empty = [c["id"] for c in core["clauses"] if not c["preferred_wording"] or not c["fallback_wording"]]
    print("נכתב %s: %d סעיפים" % (out, len(core["clauses"])))
    if (core.get("validity") or {}).get("status") == "invalid":
        # אין מסירה בשקט של פלייבוק שנכשל בבדיקות שלו: הקודים לבונה, והשורות ללקוח (wf2-opinion-research-finalize.md,
        # שלב 12)
        from playbook import validity as VY
        print("הפלייבוק אינו עובר את הבדיקות של עצמו: %s" % ", ".join(
            "%s x%d" % (k, v) for k, v in core["validity"]["codes"].items()))
        for line in VY.playbook_warnings(core=core, lang=core.get("output_language") or "he"):
            print("ללקוח: %s" % line)
    if empty:
        print("לסעיפים האלה אין נוסח ירוק או נוסח נסיגה במודל, והנושא ונותן לא יוכל להחיל אותם: %s"
              % ", ".join(str(x) for x in empty))
    return 0


if __name__ == "__main__":
    sys.exit(main())
