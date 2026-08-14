#!/usr/bin/env python3
import json
import sys
from pathlib import Path

VALID_STATUS = {"Confirmed", "Inferred", "Unclear"}
VALID_CONF = {"High", "Medium", "Low"}
VALID_PB_STATUS = {"Draft", "Approved", "Superseded", "Invalid"}
VALID_REG_STATUS = {"NotResearched", "NoSpecificSourceIdentified", "ApplicableSourcesFound"}
VALID_PRESENCE = {"Required", "Optional", "Prohibited", "Conditional"}
VALID_MISSING_COLOR = {"Green", "Yellow", "Red", "NotApplicable"}
VALID_RESEARCH_STATUS = {"NotRequested", "Declined", "Completed", "Partial"}
VALID_QA_STATUS = {"NotRun", "Partial", "Completed"}
VALID_SEG_STATUS = {"NotDetected", "Candidate", "Confirmed"}
VALID_RATIONALE_STATUS = {"Draft", "Confirmed"}
VALID_OUTPUT_LANGUAGE = {"he", "en"}
VALID_MARKET_BASIS = {"ExternalResearch", "ExpertAssessment", "InternalTrendOnly", "NotAssessed"}
LEGACY_RULE_KEYS = {"fallbacks", "fallback_1", "fallback_2", "red_line", "escalation"}
COLOR_SPEC = {"green": "Approved", "yellow": "AgreeWithComments", "red": "NotApproved"}

RATIONALE_MIN = {
    "executive_policy_rationale": 240,
    "protected_interest_and_clause_purpose": 140,
    "legal_risk_and_legal_framework": 180,
    "contractual_risk_allocation_mechanism": 140,
    "company_role_and_policy_fit": 120,
    "business_operational_impact": 160,
    "internal_evidence_rationale": 100,
    "market_practice_assessment": 80,
    "green_boundary_rationale": 90,
    "yellow_boundary_rationale": 90,
    "red_boundary_rationale": 90,
    "tradeoff_statement": 80,
    "related_clause_rationale": 60,
    "uncertainties_and_limitations": 40,
}
SEG_RATIONALE_MIN = {
    "executive_segment_rationale": 140,
    "segment_characteristic_and_risk_change": 100,
    "legal_basis": 90,
    "business_basis": 90,
    "internal_evidence_basis": 70,
    "market_practice_assessment": 50,
    "green_boundary_rationale": 70,
    "yellow_boundary_rationale": 70,
    "red_boundary_rationale": 70,
    "tradeoff": 60,
    "related_clause_effect": 40,
    "uncertainties_and_limitations": 30,
}


def nonempty(value):
    return value not in (None, "", [], {})


def text_len(value):
    if not isinstance(value, str):
        return 0
    return len(" ".join(value.split()))


def add(errors, msg):
    errors.append(msg)


def require_obj(errors, obj, key, prefix):
    value = obj.get(key)
    if not isinstance(value, dict) or not value:
        add(errors, f"{prefix} missing/non-object {key}")
        return None
    return value


def validate_previous(errors, items, prefix, segment_ids):
    if items is None:
        return
    if not isinstance(items, list):
        add(errors, f"{prefix}.previous_agreements_where_language_accepted must be list")
        return
    for j, item in enumerate(items):
        pp = f"{prefix}.previous_agreements_where_language_accepted[{j}]"
        if not isinstance(item, dict):
            add(errors, f"{pp} must be object")
            continue
        for key in ["agreement_id", "agreement_label", "agreement_status", "company_role", "date", "clause_ref", "similarity", "source_ref"]:
            if not nonempty(item.get(key)):
                add(errors, f"{pp} missing {key}")
        if item.get("similarity") not in {"Exact", "SubstantiallySimilar"}:
            add(errors, f"{pp} invalid similarity")
        sid = item.get("segment_id")
        if sid and sid not in segment_ids:
            add(errors, f"{pp} references unknown segment_id {sid}")


def validate_traffic_light(errors, light, prefix, segment_ids):
    if not isinstance(light, dict) or not light:
        add(errors, f"{prefix} missing/non-object traffic_light")
        return
    for color, expected in COLOR_SPEC.items():
        block = light.get(color)
        cp = f"{prefix}.traffic_light.{color}"
        if not isinstance(block, dict) or not block:
            add(errors, f"{cp} missing/non-object")
            continue
        if block.get("meaning") != expected:
            add(errors, f"{cp} meaning must be {expected}")
        for key in ["position", "match_criteria", "proposed_clause"]:
            if not nonempty(block.get(key)):
                add(errors, f"{cp} missing {key}")
        if not isinstance(block.get("match_criteria"), list) or not block.get("match_criteria"):
            add(errors, f"{cp}.match_criteria must be a non-empty list")
        if color == "yellow" and not nonempty(block.get("comments")):
            add(errors, f"{cp} requires comments")
        validate_previous(errors, block.get("previous_agreements_where_language_accepted", []), cp, segment_ids)


def validate_rationale(errors, rationale, prefix, min_spec, applicability_min=2):
    if not isinstance(rationale, dict) or not rationale:
        add(errors, f"{prefix} missing/non-object rationale")
        return
    for key, minimum in min_spec.items():
        if not nonempty(rationale.get(key)):
            add(errors, f"{prefix} missing {key}")
        elif text_len(rationale.get(key)) < minimum:
            add(errors, f"{prefix}.{key} too thin ({text_len(rationale.get(key))} chars; minimum {minimum})")
    scenarios = rationale.get("applicability_scenarios")
    if not isinstance(scenarios, list) or len([x for x in scenarios if nonempty(x)]) < applicability_min:
        add(errors, f"{prefix}.applicability_scenarios requires at least {applicability_min} substantive scenarios")
    if rationale.get("rationale_status") not in VALID_RATIONALE_STATUS:
        add(errors, f"{prefix} invalid rationale_status")
    if rationale.get("market_practice_basis") not in VALID_MARKET_BASIS:
        add(errors, f"{prefix} invalid market_practice_basis")


def main(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        print("INVALID")
        print("- cannot parse JSON:", exc)
        return 1

    errors = []
    required_top = ["schema_version", "core_version", "playbook_id", "profile_id", "version", "playbook_status", "output_language", "scope_summary", "segmentation_model", "rules", "regulatory_research", "qa_summary"]
    for key in required_top:
        if not nonempty(data.get(key)):
            add(errors, f"missing {key}")

    if data.get("playbook_status") not in VALID_PB_STATUS:
        add(errors, "invalid playbook_status")
    if data.get("output_language") not in VALID_OUTPUT_LANGUAGE:
        add(errors, "invalid output_language")
    if data.get("playbook_status") == "Approved":
        for key in ["approved_by", "approved_at"]:
            if not nonempty(data.get(key)):
                add(errors, f"Approved playbook requires {key}")

    scope = data.get("scope_summary")
    if not isinstance(scope, dict):
        add(errors, "scope_summary must be object")
    else:
        families = scope.get("contract_families")
        if not isinstance(families, list) or not families:
            add(errors, "scope_summary requires contract_families[]")
        else:
            for i, family in enumerate(families):
                fp = f"scope_summary.contract_families[{i}]"
                if not isinstance(family, dict):
                    add(errors, f"{fp} must be object")
                    continue
                for key in ["contract_family_id", "contract_family_name", "company_role", "document_count"]:
                    if not nonempty(family.get(key)):
                        add(errors, f"{fp} missing {key}")
        if not nonempty(scope.get("total_document_count")):
            add(errors, "scope_summary missing total_document_count")

    segmentation = data.get("segmentation_model")
    segment_ids = set()
    segment_status = {}
    if not isinstance(segmentation, dict):
        add(errors, "segmentation_model must be object")
        segmentation = {}
    if segmentation.get("status") not in VALID_SEG_STATUS:
        add(errors, "segmentation_model invalid status")
    segments = segmentation.get("segments", [])
    if not isinstance(segments, list):
        add(errors, "segmentation_model.segments must be list")
        segments = []
    if segmentation.get("status") == "Confirmed" and not segments:
        add(errors, "Confirmed segmentation_model requires segments[]")
    for i, seg in enumerate(segments):
        sp = f"segmentation_model.segments[{i}]"
        if not isinstance(seg, dict):
            add(errors, f"{sp} must be object")
            continue
        for key in ["segment_id", "label", "criteria", "policy_status", "confidence", "evidence"]:
            if not nonempty(seg.get(key)):
                add(errors, f"{sp} missing {key}")
        sid = seg.get("segment_id")
        if sid in segment_ids:
            add(errors, f"duplicate segment_id {sid}")
        if sid:
            segment_ids.add(sid)
            segment_status[sid] = seg.get("policy_status")
        if seg.get("policy_status") not in VALID_STATUS:
            add(errors, f"{sp} invalid policy_status")
        if seg.get("confidence") not in VALID_CONF:
            add(errors, f"{sp} invalid confidence")

    rr = data.get("regulatory_research")
    if not isinstance(rr, dict):
        add(errors, "regulatory_research must be object")
    else:
        status = rr.get("status")
        if status not in VALID_RESEARCH_STATUS:
            add(errors, "regulatory_research invalid status")
        if status in {"Completed", "Partial"}:
            if rr.get("requested_by_user") is not True:
                add(errors, "regulatory research cannot be Completed/Partial without requested_by_user=true")
            if not nonempty(rr.get("checked_at")):
                add(errors, "completed/partial regulatory research requires checked_at")

    qa = data.get("qa_summary")
    if not isinstance(qa, dict):
        add(errors, "qa_summary must be object")
    else:
        if qa.get("status") not in VALID_QA_STATUS:
            add(errors, "qa_summary invalid status")
        if data.get("playbook_status") == "Approved":
            if qa.get("status") != "Completed":
                add(errors, "Approved playbook requires completed QA back-test")
            for key in ["tested_rule_count", "tested_source_count", "checked_at"]:
                if not nonempty(qa.get(key)):
                    add(errors, f"Approved playbook requires qa_summary.{key}")

    rules = data.get("rules")
    if not isinstance(rules, list) or not rules:
        add(errors, "rules must be a non-empty list")
        rules = []

    rule_ids = set()
    confirmed_segment_variants = 0
    for i, rule in enumerate(rules):
        prefix = f"rules[{i}]"
        if not isinstance(rule, dict):
            add(errors, f"{prefix} must be object")
            continue
        for legacy in sorted(LEGACY_RULE_KEYS):
            if legacy in rule:
                add(errors, f"{prefix} contains prohibited legacy field {legacy}")
        for key in ["rule_id", "topic_name", "clause_issue", "why_address_topic", "policy_status", "confidence", "evidence", "presence_rule", "policy_rationale", "traffic_light"]:
            if not nonempty(rule.get(key)):
                add(errors, f"{prefix} missing {key}")
        rid = rule.get("rule_id")
        if rid in rule_ids:
            add(errors, f"duplicate rule_id {rid}")
        if rid:
            rule_ids.add(rid)
        if rule.get("policy_status") not in VALID_STATUS:
            add(errors, f"{prefix} invalid policy_status")
        if rule.get("confidence") not in VALID_CONF:
            add(errors, f"{prefix} invalid confidence")

        perspective = require_obj(errors, rule, "company_perspective", prefix)
        if perspective:
            for key in ["legal_analysis", "business_analysis", "internal_corpus_findings", "internal_contracting_trend", "external_market_trend"]:
                if not nonempty(perspective.get(key)):
                    add(errors, f"{prefix}.company_perspective missing {key}")

        validate_rationale(errors, rule.get("policy_rationale"), f"{prefix}.policy_rationale", RATIONALE_MIN, 2)
        if data.get("playbook_status") == "Approved" and isinstance(rule.get("policy_rationale"), dict):
            if rule["policy_rationale"].get("rationale_status") != "Confirmed":
                add(errors, f"Approved playbook requires confirmed rationale for {prefix}")

        presence = rule.get("presence_rule")
        if not isinstance(presence, dict):
            add(errors, f"{prefix}.presence_rule must be object")
        else:
            if presence.get("requirement") not in VALID_PRESENCE:
                add(errors, f"{prefix}.presence_rule invalid requirement")
            if presence.get("missing_clause_color") not in VALID_MISSING_COLOR:
                add(errors, f"{prefix}.presence_rule invalid missing_clause_color")

        reg_status = rule.get("regulatory_status")
        if reg_status not in VALID_REG_STATUS:
            add(errors, f"{prefix} invalid/missing regulatory_status")
        if reg_status == "ApplicableSourcesFound" and not nonempty(rule.get("regulatory_sources")):
            add(errors, f"{prefix} ApplicableSourcesFound requires regulatory_sources")

        validate_traffic_light(errors, rule.get("traffic_light"), prefix, segment_ids)

        variants = rule.get("segment_variants", [])
        if not isinstance(variants, list):
            add(errors, f"{prefix}.segment_variants must be list")
            variants = []
        seen = set()
        for j, variant in enumerate(variants):
            vp = f"{prefix}.segment_variants[{j}]"
            if not isinstance(variant, dict):
                add(errors, f"{vp} must be object")
                continue
            for key in ["segment_id", "applies_when", "segmentation_rationale", "traffic_light", "policy_status", "confidence", "evidence"]:
                if not nonempty(variant.get(key)):
                    add(errors, f"{vp} missing {key}")
            sid = variant.get("segment_id")
            if sid not in segment_ids:
                add(errors, f"{vp} references unknown segment_id {sid}")
            if sid in seen:
                add(errors, f"{prefix} duplicate segment variant for {sid}")
            seen.add(sid)
            if variant.get("policy_status") not in VALID_STATUS:
                add(errors, f"{vp} invalid policy_status")
            if variant.get("confidence") not in VALID_CONF:
                add(errors, f"{vp} invalid confidence")
            validate_rationale(errors, variant.get("segmentation_rationale"), f"{vp}.segmentation_rationale", SEG_RATIONALE_MIN, 1)
            validate_traffic_light(errors, variant.get("traffic_light"), vp, segment_ids)
            if variant.get("policy_status") == "Confirmed":
                confirmed_segment_variants += 1
                if segment_status.get(sid) != "Confirmed":
                    add(errors, f"{vp} Confirmed policy cannot rely on unconfirmed segment {sid}")
                rationale = variant.get("segmentation_rationale")
                if isinstance(rationale, dict) and rationale.get("rationale_status") != "Confirmed":
                    add(errors, f"{vp} Confirmed segment policy requires confirmed segmentation rationale")

        cpr = rule.get("company_process_reference")
        if nonempty(cpr):
            if not isinstance(cpr, dict) or not nonempty(cpr.get("source_refs")):
                add(errors, f"{prefix}.company_process_reference requires source_refs")

    for i, rule in enumerate(rules):
        if not isinstance(rule, dict):
            continue
        for rel in rule.get("related_rule_ids", []):
            if rel not in rule_ids:
                add(errors, f"rules[{i}] related_rule_id {rel} does not exist")

    if data.get("playbook_status") == "Approved" and confirmed_segment_variants:
        if not isinstance(qa, dict) or not nonempty(qa.get("tested_segment_count")):
            add(errors, "Approved playbook with confirmed segment variants requires qa_summary.tested_segment_count")

    queue = data.get("validation_queue", [])
    if not isinstance(queue, list):
        add(errors, "validation_queue must be list")
        queue = []
    queue_rule_ids = {q.get("rule_id") for q in queue if isinstance(q, dict)}
    for i, rule in enumerate(rules):
        if isinstance(rule, dict) and rule.get("policy_status") == "Unclear":
            if rule.get("rule_id") not in queue_rule_ids and not nonempty(rule.get("validation_question")):
                add(errors, f"rules[{i}] Unclear rule lacks validation queue item/question")

    if errors:
        print("INVALID")
        for error in errors:
            print("-", error)
        return 1
    print("VALID")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: validate_playbook_model.py PLAYBOOK.json")
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
