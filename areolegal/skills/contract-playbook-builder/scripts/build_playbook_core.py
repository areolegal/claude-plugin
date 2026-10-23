#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""בונה את גרעין ההפעלה (playbook-core.json) מהמודל, בקוד.

`playbook-core-schema.md`: הגרעין "נגזר במלואו מהמודל", "לעולם אינו נערך ידנית ואינו
מקור אמת", ונבנה מחדש בכל שמירה של המודל. עד עכשיו לא היה לו סקריפט: בכל הרצה הבונה כתב
את הגרעין בעצמו, וכל הרצה יצאה אחרת. בהרצה חיה (20.10.2026) הגרעין הראשון נכשל בחוזה מול
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

TRACKS = ("green", "yellow", "red")
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


def block(track, cell):
    out = {"position": cell.get("position") or "", "basis": cell.get("basis") or "",
           "label": cell.get("label") or ""}
    if cell.get("source_label"):
        out["source_label"] = cell["source_label"]
    if cell.get("market_source_ids"):
        out["source_ids"] = list(cell["market_source_ids"])
    if track == "green":
        out["preferred_wording"] = text_of(cell.get("proposed_clause"))
    elif track == "yellow":
        out["fallback_wording"] = text_of(cell.get("fallback_wording")) or text_of(cell.get("proposed_clause"))
        out["fallback_source"] = fallback_source(cell)
    else:
        out["red_line"] = cell.get("position") or ""
        if text_of(cell.get("proposed_clause")):
            out["remedy_wording"] = text_of(cell.get("proposed_clause"))
    return out


def legal_review(rule):
    v = rule.get("legal_review_required")
    if isinstance(v, list):
        open_items = [x for x in v if not (isinstance(x, dict) and x.get("checked_by"))]
        tracks = sorted({t for x in open_items if isinstance(x, dict) for t in x.get("tracks") or ()})
        return bool(open_items), tracks
    return bool(v), []


def clause(rule):
    tl = rule.get("traffic_light") or {}
    blocks = {t: block(t, tl.get(t) or {}) for t in TRACKS}
    lr, lr_tracks = legal_review(rule)
    out = {"id": rule.get("rule_id"), "title": rule.get("topic_name") or rule.get("topic") or "",
           "policy_ref": rule.get("policy_ref") or rule.get("rule_id"),
           "importance": rule.get("importance") or "",
           "activation_conditions": rule.get("activation_conditions") or [],
           # בדיקת התוצאה של הכלל, שהנושא ונותן מריץ על הנוסח המתקבל (הערות ענבל 22.10.2026, כלל 3)
           "post_checks": rule.get("post_checks") or [],
           "green": blocks["green"], "yellow": blocks["yellow"], "red": blocks["red"],
           # השדות השטוחים: עותק של הבלוקים, לתאימות עם הנושא ונותן והמנסח
           "red_line": blocks["red"]["red_line"],
           "preferred_wording": blocks["green"]["preferred_wording"],
           "fallback_wording": blocks["yellow"]["fallback_wording"],
           "fallback_source": blocks["yellow"]["fallback_source"],
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
                ov[t] = block(t, vtl[t])
        ov["red_line"] = (ov.get("red") or {}).get("red_line", out["red_line"])
        ov["preferred_wording"] = (ov.get("green") or {}).get("preferred_wording", out["preferred_wording"])
        ov["fallback_wording"] = (ov.get("yellow") or {}).get("fallback_wording", out["fallback_wording"])
        ov["fallback_source"] = (ov.get("yellow") or {}).get("fallback_source", out["fallback_source"])
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


def build(model, model_path):
    sc = model.get("scope_summary") or {}
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
        "playbook_status": model.get("playbook_status") or "Draft",
        "status_label": model.get("status_label") or "",
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
        "contract_families": [{k: f.get(k) for k in ("contract_family_name", "family_aliases", "company_role",
                                                     "company_role_code") if f.get(k) is not None}
                              for f in fams],
        "clauses": [clause(r) for r in model.get("rules") or () if isinstance(r, dict)],
        "segments": [{k: s.get(k) for k in ("segment_id", "label", "criteria", "negotiation_mode")}
                     for s in ((model.get("segmentation_model") or {}).get("segments") or ())
                     if isinstance(s, dict)],
    }


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
    core = build(model, a.model)
    with io.open(out, "w", encoding="utf-8") as fh:
        json.dump(core, fh, ensure_ascii=False, indent=1)
    empty = [c["id"] for c in core["clauses"] if not c["preferred_wording"] or not c["fallback_wording"]]
    print("נכתב %s: %d סעיפים" % (out, len(core["clauses"])))
    if empty:
        print("לסעיפים האלה אין נוסח ירוק או נוסח נסיגה במודל, והנושא ונותן לא יוכל להחיל אותם: %s"
              % ", ".join(str(x) for x in empty))
    return 0


if __name__ == "__main__":
    sys.exit(main())
