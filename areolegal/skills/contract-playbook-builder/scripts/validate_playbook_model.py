#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

VALID_STATUS = {"Confirmed", "Inferred", "Unclear"}
VALID_CONF = {"High", "Medium", "Low"}
VALID_PB_STATUS = {"Draft", "PartiallyApproved", "Approved", "Superseded", "Invalid"}
# מאיפה בא round1_posture: מברירת המחדל לפי החשיבות, מהצהרת התמורה, או
# מתשובת הלקוח (שינוי 69; קודם לכן הערך הראשון נקרא default)
VALID_POSTURE_SOURCE = {"importance", "tradeoff_statement", "client_answer"}
VALID_POSTURE = {"hold_green", "offer_yellow", "not_applicable"}
WALK_AWAY_MAX = 5
VALID_REG_STATUS = {"NotResearched", "NoSpecificSourceIdentified", "ApplicableSourcesFound"}
VALID_PRESENCE = {"Required", "Optional", "Prohibited", "Conditional"}
VALID_MISSING_COLOR = {"Green", "Yellow", "Red", "NotApplicable"}
# playbook-schema.md: "סטטוס המחקר, בשוק ובדין, מאותו סט: Performed | Partial | NotPerformed". הערכים
# הישנים נשארים מותרים, כדי שפלייבוק קיים לא ייפסל. לפני כן הסט של הסכמה נפסל כאן, ותבנית סביבת העבודה
# קיבלה רק אותו, ולכן בהרצה חיה צריך היה למפות ביד (20.10.2026)
VALID_RESEARCH_STATUS = {"Performed", "Partial", "NotPerformed", "NotRequested", "Declined", "Completed"}
RESEARCH_DONE = {"Performed", "Completed", "Partial"}
VALID_QA_STATUS = {"NotRun", "Partial", "Completed"}
VALID_SEG_STATUS = {"NotDetected", "Candidate", "Confirmed"}
VALID_RATIONALE_STATUS = {"Draft", "Confirmed"}
VALID_OUTPUT_LANGUAGE = {"he", "en"}
VALID_MARKET_BASIS = {"ExternalResearch", "ExpertAssessment", "InternalTrendOnly", "NotAssessed"}
# מאיפה נבנה הפלייבוק: מההסכמים של החברה, מהם יחד עם השוק, או מהשוק בלבד (שינוי 3)
VALID_CORPUS_ORIGIN = {"own", "own_plus_market", "market_built"}
# הרצועה נגזרת ממספר ההסכמים בסוג, אחרי ניקוי כפילויות, גרסאות, תיקונים
# ותבניות. השמות הם אלה של `playbook-schema.md`, והספירה נעשית ב-
# `build_corpus_manifest.py` ולא בהערכה של המודל
CORPUS_BANDS = [(20, None, "full"), (7, 19, "below20"), (1, 6, "below7"), (0, 0, "none")]
# ב-1 עד 6 הלקוח בוחר: לשלב מחקר שוק, או להישאר רק עם ההסכמים שלו
BAND_CHOICES = {"full": {"own"}, "below20": {"own"},
                "below7": {"own", "own_plus_market"}, "none": {"market_built"}}
BAND_CHOICE_FIELD = {"full": {"not_asked"}, "below20": {"not_asked"},
                     "below7": {"combine", "own_only"}, "none": {"market"}}
CHOICE_ORIGIN = {"own_only": "own", "combine": "own_plus_market", "market": "market_built"}
# הבסיס של כל מסלול: ראיה מההסכמים, נוסח שוק, או הצעה של Areo כשאין פשרה בראיות
# כל הערכים של playbook-schema.md ("basis: מקור המסלול"), ו-own_evidence מהגרסה הקודמת. לפני כן רק ארבעה
# ערכים, ומודל שנכתב לפי הסכמה ("template", "established", "single") נפסל (הרצה חיה, 20.10.2026)
VALID_TRACK_BASIS = {"own_evidence", "own_paper_repeated", "template", "company_request", "client_answer",
                     "established", "single", "offered_unexecuted", "company_source", "struck",
                     "rejected_comment", "never_accepted", "bid_condition", "market_standard", "areo_proposal"}
VALID_FALLBACK_SOURCE = {"signed_compromise", "single_compromise", "offered_not_signed",
                         "client_answer", "areo_proposal"}
VALID_ACCEPTANCE_MODE = {"negotiated", "imposed", "unnegotiated", "unknown"}
VALID_PAPER = {"ours", "theirs", "unknown"}
# קודים לסעיף שאין לו מדיניות, רשימה סגורה (שינוי 5)
# הרשימה הסגורה של הקודים הטכניים, מילה במילה מ-`clause-catalog.md`,
# "Technical clauses: closed list". אין קוד "אחר": סעיף שאינו אחד מאלה
# הוא נושא מדיניות
TECHNICAL_CODES = {"signature_block", "party_identification", "notice_addresses",
                   "counterparts_esignature", "headings", "interpretation_grammar",
                   "recitals_descriptive", "neutral_definition", "bank_details",
                   "delivery_points_list", "admin_form_fields",
                   "statutory_admin_restatement"}
# נימוקי השמטה שאינם מתקבלים (`playbook-schema.md`, `coverage`): נוסח שחוזר
# בכל ההסכמים הוא הראיה החזקה ביותר לירוק, ולא סיבה לדלג עליו
FORBIDDEN_OMISSION = ("לא רלוונטי", "נוסח אחיד", "נוסח עקבי", "אין מחלוקת", "תפעולי",
                      "הסכם יחיד", "תנאי מסחרי", "אין ראיה לעמדת החברה", "סטנדרטי",
                      "טכני בלבד", "אין צורך", "ברור מאליו",
                      "not relevant", "standard", "boilerplate")
# ביטויים שאסורים בנוסח צהוב: הם ויתור בלי תנאי
FORBIDDEN_YELLOW = ("לפי שיקול דעת הצד", "ללא הגבלה", "כפי שיידרש", "unlimited", "sole discretion")
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

        # מאיפה המסלול הגיע. בלי זה אי אפשר לדעת אם העמדה נגזרה מההסכמים
        # או שהיא הצעה שלנו, וזו ההבחנה שהלקוח חייב לראות (שינויים 6, 7).
        basis = block.get("basis")
        if basis not in VALID_TRACK_BASIS:
            add(errors, f"{cp} missing/invalid basis")
        elif basis != "areo_proposal" and not nonempty(block.get("basis_refs")):
            add(errors, f"{cp} basis {basis} requires basis_refs")
        if basis in {"market_standard", "areo_proposal"} and not nonempty(block.get("label")):
            add(errors, f"{cp} requires a label when the source is not the company")
        if basis == "market_standard":
            refs = block.get("basis_refs")
            if not isinstance(refs, list) or len(refs) < 3:
                add(errors, f"{cp} market_standard requires three counted sources")

        if color == "yellow":
            fb = block.get("fallback_wording")
            if not isinstance(fb, dict) or not nonempty(fb.get("text")):
                add(errors, f"{cp} requires fallback_wording.text")
            elif fb.get("source") not in VALID_FALLBACK_SOURCE:
                add(errors, f"{cp}.fallback_wording invalid source")
            elif fb.get("source") == "signed_compromise" and len(fb.get("negotiation_refs") or []) < 2:
                add(errors, f"{cp} established yellow requires two different negotiations")
            if block.get("offer_yellow") and (fb or {}).get("source") != "signed_compromise":
                add(errors, f"{cp} offer_yellow is allowed only when the yellow is established")
            text = " ".join(str(x) for x in [block.get("proposed_clause"), (fb or {}).get("text")] if x)
            for bad in FORBIDDEN_YELLOW:
                if bad in text:
                    add(errors, f"{cp} yellow wording contains an unconditional concession: {bad}")
        validate_previous(errors, block.get("previous_agreements_where_language_accepted", []), cp, segment_ids)


# policy-rationale.md, "שני מעברים": במעבר א (rationale_status: Draft) נכתבים רק השדות הקצרים האלה, ויתר
# השדות ריקים ורשומים ב-pass_b_pending. האורכים במפרט הם תקרות, "ולעולם לא יעד". לפני כן המאמת דרש אורך
# מינימלי גם בטיוטה, ובהרצה חיה הבונה מתח את הנימוקים כדי לעבור אותו (20.10.2026)
PASS_A_FIELDS = ("executive_policy_rationale", "green_boundary_rationale", "yellow_boundary_rationale",
                 "red_boundary_rationale", "internal_evidence_rationale")


def validate_rationale(errors, rationale, prefix, min_spec, applicability_min=2):
    if not isinstance(rationale, dict) or not rationale:
        add(errors, f"{prefix} missing/non-object rationale")
        return
    if rationale.get("rationale_status") == "Draft" and min_spec is RATIONALE_MIN:
        pending = set(rationale.get("pass_b_pending") or ())
        for key in PASS_A_FIELDS:
            if not nonempty(rationale.get(key)):
                add(errors, f"{prefix} missing {key} (pass A)")
        for key in min_spec:
            if key not in PASS_A_FIELDS and not nonempty(rationale.get(key)) and key not in pending:
                add(errors, f"{prefix}.{key} is empty and not listed in pass_b_pending")
        if rationale.get("rationale_status") not in VALID_RATIONALE_STATUS:
            add(errors, f"{prefix} invalid rationale_status")
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


def main(path, core=None, index_entry=None, word=None, workspace=None):
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

    # הבונה כותב תמיד Draft (שינוי 27). אישור מדיניות אינו מתואר, אינו
    # מתועד ואינו נכתב כאן, ולכן מודל שיוצא מהבונה בכל ערך אחר נפסל
    # בבנייה הערך תמיד Draft. PartiallyApproved ו-Approved נגזרים בקוד אחרי
    # קליטה של גיליון העמדות, ולכן מותרים רק כשיש רשומת קליטה (שינוי 68)
    status = data.get("playbook_status")
    records = data.get("approval_records")
    ingested = isinstance(records, list) and bool(records)
    if status not in VALID_PB_STATUS:
        add(errors, "invalid playbook_status")
    elif status in ("PartiallyApproved", "Approved") and not ingested:
        add(errors, f"playbook_status is {status} with no approval_records[]: the builder "
                    f"writes Draft, and the status is derived only after a positions "
                    f"sheet is ingested")
    elif status not in ("Draft", "PartiallyApproved", "Approved"):
        add(errors, f"playbook_status must be Draft on build, got {status}")
    # התווית היא שדה אחד, ושתי תוויות באותה רשומה הן תקלה (שינוי 79)
    if not nonempty(data.get("status_label")):
        add(errors, "missing status_label: it is the only field that states the "
                    "playbook's status, and every component prints it as it is")
    if "presentation_label" in json.dumps(data, ensure_ascii=False):
        add(errors, "presentation_label must not appear anywhere: status_label is the "
                    "only label field (two labels in one record is a defect)")
    if not nonempty(data.get("produced_with")):
        add(errors, "missing produced_with: the skill version, the notes version and "
                    "refs_sha256 of the run that produced this model")
    for key in ["approved_by", "approved_at", "confirmed_by", "approved_version"]:
        if nonempty(data.get(key)):
            add(errors, f"{key} must not be written: who approved is recorded in "
                        f"approval_records[], not in a field of its own")
    if data.get("output_language") not in VALID_OUTPUT_LANGUAGE:
        add(errors, "invalid output_language")

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

        # מאיפה נבנה הפלייבוק, וכמה הסכמים באמת עמדו מאחוריו. הספירה נעשית
        # בקוד מתוך המניפסט, ולא בהערכה של המודל (שינויים 2 ו-3).
        origin = scope.get("corpus_origin")
        if origin not in VALID_CORPUS_ORIGIN:
            add(errors, "scope_summary missing/invalid corpus_origin")
        basis = scope.get("corpus_basis")
        if not isinstance(basis, dict):
            add(errors, "scope_summary requires corpus_basis{}")
        else:
            units = basis.get("agreement_units")
            band = basis.get("band") if basis.get("band") in BAND_CHOICES else None
            if not isinstance(units, int):
                add(errors, "corpus_basis.agreement_units must be a number counted in code")
            else:
                band = next((name for lo, hi, name in CORPUS_BANDS
                             if units >= lo and (hi is None or units <= hi)), None)
                if basis.get("band") != band:
                    add(errors, f"corpus_basis.band must be {band} for {units} agreements")
                if origin and band and origin not in BAND_CHOICES.get(band, set()):
                    add(errors, f"corpus_origin {origin} does not match band {band}")
            # מה נוכה נרשם ברשימות, כי מהן נבנית ההודעה ללקוח בשלב 2א
            lists = ["removed_duplicates", "merged_versions",
                     "amendments_attached", "excluded_templates"]
            for key in lists:
                if not isinstance(basis.get(key), list):
                    add(errors, f"corpus_basis missing {key}[] (counted in code)")
            if not isinstance(basis.get("files"), int):
                add(errors, "corpus_basis missing files (counted in code)")
            # הספירה חייבת להסתכם: כל קובץ או נספר, או נוכה בעילה מוצהרת.
            # כך מתגלה ספירה שנכתבה ביד או שעוגלה כדי להיכנס למסלול אחר
            elif all(isinstance(basis.get(k), list) for k in lists) and isinstance(units, int):
                deducted = sum(len(basis[k]) for k in lists)
                if units + deducted != basis["files"]:
                    add(errors, f"corpus_basis does not add up: {basis['files']} files "
                                f"but {units} counted plus {deducted} deducted")
            # הבחירה של הלקוח, והמסלול שנגזר ממנה
            choice = basis.get("choice")
            if band and choice not in BAND_CHOICE_FIELD.get(band, set()):
                add(errors, f"corpus_basis.choice {choice} is not allowed in band {band}")
            elif choice in CHOICE_ORIGIN and origin and origin != CHOICE_ORIGIN[choice]:
                add(errors, f"corpus_origin {origin} does not match choice {choice}")

        # מי חתום על ההסכמים. כשזו אינה החברה שבפרופיל, חייבים לומר מי כן.
        if scope.get("contracting_entity_differs") and not nonempty(scope.get("contracting_entity")):
            add(errors, "scope_summary requires contracting_entity when the signer is not the profile company")

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
        if status in RESEARCH_DONE:
            # playbook-schema.md: המחקר הרגולטורי רץ לפי מספר ההסכמים ואינו נשאל, ו-requested_by_user יוצא.
            # הדרישה הישנה פסלה כל מחקר רגולטורי שהמפרט עצמו מחייב (1 עד 6 הסכמים, או אין)
            if rr.get("trigger") not in ("band_below7", "band_none") and rr.get("requested_by_user") is not True:
                add(errors, "regulatory research Performed/Partial requires trigger band_below7 or band_none")
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

    # מלאי הסעיפים: כל סעיף בהסכם קיבל מדיניות, או קוד טכני מרשימה סגורה.
    # בלי זה סעיף נשמט בשקט ואיש אינו יודע (שינוי 5).
    # מלאי הסעיפים: ההוכחה שאף סעיף לא נשר בשקט. המבנה הוא זה של
    # `playbook-schema.md`, `coverage`: מספרים, ורשימה לסעיפים הטכניים
    coverage = data.get("coverage")
    if not isinstance(coverage, dict):
        add(errors, "missing coverage{} (clause inventory written by the extractor)")
    else:
        nums = ["units", "topic_units", "technical_units", "unmapped_units",
                "topics", "topics_with_rule"]
        for key in nums:
            if not isinstance(coverage.get(key), int):
                add(errors, f"coverage.{key} must be a number counted in code")
        if not nonempty(coverage.get("inventory_ref")):
            add(errors, "coverage missing inventory_ref (where the clause inventory is kept)")
        if all(isinstance(coverage.get(k), int) for k in nums):
            if coverage["unmapped_units"] != 0:
                add(errors, f"coverage.unmapped_units must be 0, got {coverage['unmapped_units']}")
            total = coverage["topic_units"] + coverage["technical_units"] + coverage["unmapped_units"]
            if total != coverage["units"]:
                add(errors, f"coverage does not add up: {coverage['units']} units "
                            f"but {total} mapped")
            # לכל נושא יש כלל: נושא בלי כלל הוא סעיף שנמצא ולא קיבל מדיניות
            if coverage["topics_with_rule"] != coverage["topics"]:
                add(errors, f"coverage: {coverage['topics'] - coverage['topics_with_rule']} "
                            f"topics have no rule in rules[]")
        items = coverage.get("technical_items")
        if not isinstance(items, list):
            add(errors, "coverage.technical_items[] missing (the source of the Word chapter "
                        "and of the coverage panel)")
        else:
            refs_total = 0
            for k, item in enumerate(items):
                ip = f"coverage.technical_items[{k}]"
                if not isinstance(item, dict):
                    add(errors, f"{ip} must be object")
                    continue
                if item.get("code") not in TECHNICAL_CODES:
                    add(errors, f"{ip} code {item.get('code')} is not in the closed list")
                reason = str(item.get("reason") or "")
                if not reason:
                    add(errors, f"{ip} missing reason")
                elif any(bad in reason for bad in FORBIDDEN_OMISSION):
                    add(errors, f"{ip} reason is not a reason: {reason[:40]}")
                refs = item.get("refs")
                if not isinstance(refs, list) or not refs:
                    add(errors, f"{ip} missing refs[] (which clause this is)")
                else:
                    refs_total += len(refs)
            if isinstance(coverage.get("technical_units"), int) and items \
                    and refs_total != coverage["technical_units"]:
                add(errors, f"coverage.technical_items cover {refs_total} clauses "
                            f"but technical_units is {coverage['technical_units']}")

    rules = data.get("rules")
    if not isinstance(rules, list) or not rules:
        add(errors, "rules must be a non-empty list")
        rules = []

    # רישום המקורות: על נייר של מי כל הסכם, ואיך התקבל. בלי זה ראיה
    # ממסמך שהצד שכנגד ניסח נראית כמו ראיה למדיניות שלנו (שינוי 6).
    source_ids = set()
    for i, src in enumerate(data.get("source_log") or []):
        sp = f"source_log[{i}]"
        if not isinstance(src, dict):
            add(errors, f"{sp} must be object")
            continue
        sid = src.get("source_id")
        if not nonempty(sid):
            add(errors, f"{sp} missing source_id")
        elif sid in source_ids:
            add(errors, f"duplicate source_id {sid}")
        else:
            source_ids.add(sid)
        if src.get("doc_role") == "template":
            continue          # תבנית אינה הסכם, ואינה נספרת ככזה
        if src.get("paper") not in VALID_PAPER:
            add(errors, f"{sp} missing/invalid paper (ours, theirs, unknown)")
        if not nonempty(src.get("channel")):
            add(errors, f"{sp} missing channel")
        if src.get("acceptance_mode") not in VALID_ACCEPTANCE_MODE:
            add(errors, f"{sp} missing/invalid acceptance_mode")

    citation_ids = {c.get("citation_id") for c in (data.get("citations") or [])
                    if isinstance(c, dict)}

    rule_ids = set()
    confirmed_segment_variants = 0
    walk_away_rules = []
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

        # מה מציעים בסבב הראשון, ומאיפה הערך בא (שינוי 69). ברירת המחדל
        # נקבעת לפי החשיבות, ולכן המקור נקרא importance ולא default
        posture = rule.get("round1_posture")
        if posture is None:
            add(errors, f"{prefix} missing round1_posture")
        elif posture not in VALID_POSTURE:
            add(errors, f"{prefix} invalid round1_posture: {posture}")
        src = rule.get("round1_posture_source")
        if src is None:
            add(errors, f"{prefix} missing round1_posture_source")
        elif src == "default":
            add(errors, f"{prefix} round1_posture_source is 'default': the value was "
                        f"renamed to 'importance', because the default follows importance")
        elif src not in VALID_POSTURE_SOURCE:
            add(errors, f"{prefix} invalid round1_posture_source: {src}")

        # שובר עסקה: חובה בכל כלל, ומקור רשום כשהערך true (שינוי 84)
        wa = rule.get("walk_away")
        if not isinstance(wa, bool):
            add(errors, f"{prefix} walk_away must be true or false on every rule")
        elif wa:
            walk_away_rules.append(rid)
            if not nonempty(rule.get("walk_away_source")):
                add(errors, f"{prefix} walk_away is true without walk_away_source: a "
                            f"deal breaker needs a recorded source (statute, a company "
                            f"document, or the client's answer)")
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

        # הראיות של הכלל: לאיזה מסלול הן שייכות, מאיזה הסכם, ובאיזו פוזיציה.
        # ראיה ממשפחת הסכמים אחרת אינה בסיס למסלול, רק הקשר (שינוי 6).
        excluded = set()
        for key in ("agreement_exceptions", "observed_alternatives", "statutory_override"):
            for item in (rule.get(key) or []):
                ref = item.get("source_ref") if isinstance(item, dict) else item
                if ref:
                    excluded.add(ref)
        ev_count = 0
        for k, ev in enumerate(rule.get("evidence") or []):
            ep = f"{prefix}.evidence[{k}]"
            if not isinstance(ev, dict):
                add(errors, f"{ep} must be object")
                continue
            ev_count += 1
            if ev.get("same_family") is None:
                add(errors, f"{ep} missing same_family")
            if not nonempty(ev.get("company_role_in_source")):
                add(errors, f"{ep} missing company_role_in_source")
            track = ev.get("track")
            if ev.get("same_family") is False and track != "context":
                add(errors, f"{ep} evidence from another contract family may only be context")
            ref = ev.get("source_ref")
            if ref and source_ids and ref.split("#")[0] not in source_ids:
                add(errors, f"{ep} source_ref {ref} is not in source_log")
            cid = ev.get("citation_id")
            if cid and citation_ids and cid not in citation_ids:
                add(errors, f"{ep} citation_id {cid} is not in citations[]")
            if track in {"green", "yellow"} and ref in excluded:
                add(errors, f"{ep} a green/yellow track cannot rest on an exception, a replaced wording or a statutory override")
        # playbook-schema.md: evidence_count הוא {independent_negotiations, on_company_paper}, ספירה של משאים
        # ומתנים ולא של שורות ראיה. רק מספר שלם (צורה ישנה) מושווה למספר השורות; אובייקט נבדק לצורתו
        ec = rule.get("evidence_count")
        if isinstance(ec, bool) or (ec is not None and not isinstance(ec, (int, dict))):
            add(errors, f"{prefix}.evidence_count must be {{independent_negotiations, on_company_paper}}")
        elif isinstance(ec, int) and ec != ev_count:
            add(errors, f"{prefix}.evidence_count says {ec} but {ev_count} entries were found")
        elif isinstance(ec, dict):
            ind, own = ec.get("independent_negotiations"), ec.get("on_company_paper")
            if not isinstance(ind, int) or not isinstance(own, int) or own > ind:
                add(errors, f"{prefix}.evidence_count needs integers independent_negotiations >= on_company_paper")

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

    # לכל היותר חמישה שוברי עסקה בפלייבוק (שינוי 84). פלייבוק שבו כל כלל
    # שובר עסקה אינו מדיניות, אלא רשימת תנאים שאין איתה משא ומתן
    if len(walk_away_rules) > WALK_AWAY_MAX:
        add(errors, "%d rules have walk_away: true, the limit is %d (%s)"
                    % (len(walk_away_rules), WALK_AWAY_MAX,
                       ", ".join(str(r) for r in walk_away_rules[:8])))

    warnings = []
    content = content_findings(data, errors, warnings, core=core,
                              index_entry=index_entry, word=word, workspace=workspace)
    handoff_findings(data, errors)

    if errors:
        print("INVALID")
        for error in errors:
            print("-", error)
        for w in warnings:
            print("! warning:", w)
        return 1
    print("VALID")
    for w in warnings:
        print("! warning:", w)
    if content:
        print("(content checks from the shared library ran: %d findings, none blocking)"
              % len(warnings))
    return 0


def handoff_findings(data, errors):
    """בנייה לבקשת הנושא ונותן (הערות הפלייבוק 5.5, שינוי 73): התשובה לשאלת המסלול
    חוזרת ב-handoff.route_answer כשנשאלה בבונה, ועד שלוש החלטות ב-decisions_now[],
    כל אחת עם המלצה. ואין בתור השאלות פריט שמבקש לאשר בחירה שנעשתה באותה הפעלה."""
    req = (data.get("meta") or {}).get("build_request") or {}
    if req.get("requested_by") != "negotiation_orchestrator":
        return
    h = data.get("handoff")
    if not isinstance(h, dict):
        add(errors, "handoff: a build for the negotiator returns a handoff record")
        return
    asked = req.get("route_answer")
    if asked and h.get("route_answer") != asked:
        add(errors, "handoff.route_answer: the route question was answered in the builder "
                    "(meta.build_request.route_answer) and must be returned as is")
    for k in ("asked_in", "answer_verbatim", "choice"):
        if asked and k not in asked:
            add(errors, "meta.build_request.route_answer.%s is required" % k)
    dn = h.get("decisions_now")
    if dn is None:
        add(errors, "handoff.decisions_now[] is required (up to three decisions, each with a recommendation)")
    elif len(dn) > 3:
        add(errors, "handoff.decisions_now has %d items; at most three" % len(dn))
    else:
        for i, d in enumerate(dn):
            if not (isinstance(d, dict) and d.get("recommendation")):
                add(errors, "handoff.decisions_now[%d]: every decision carries a recommendation" % i)
    if asked:
        for q in data.get("validation_queue") or []:
            text = "%s %s" % (q.get("question") or "", q.get("why") or "")
            if "לאשר את הבחירה" in text or "לאשר?" in text and "בחירה" in text:
                add(errors, "validation_queue %s: asks to confirm a choice the client already made in this "
                            "session (route_answer)" % q.get("id"))


def content_findings(data, errors, warnings, core=None, index_entry=None,
                     word=None, workspace=None):
    """בדיקות התוכן של ספריית הייחוס, לצד בדיקות הסכמה שלמעלה.

    חוסר של הספרייה אינו עובר בשקט: מודל שלא נבדקו בו המנגנונים אינו
    מודל שנבדק, ולכן הוא נפסל עם הסיבה.
    """
    try:
        import areo_lib  # noqa: F401
        from playbook.status import check_consistency
        from playbook.validate_model import validate
    except ImportError as exc:
        add(errors, "the shared library (areolegal/lib) is not importable, so the "
                    "content checks did not run: %s" % exc)
        return False
    try:
        findings = validate(data, core=core, index_entry=index_entry)
    except Exception as exc:                      # מודל פגום מכדי להיבדק
        add(errors, "content checks raised %s: %s" % (type(exc).__name__, exc))
        return False
    for fnd in findings:
        where = " ".join(str(fnd.get(k)) for k in ("rule_id", "track") if fnd.get(k))
        line = "%s%s: %s" % (fnd.get("code", "?"), " (%s)" % where if where else "",
                             fnd.get("message", ""))
        if fnd.get("severity") == "error":
            add(errors, line)
        else:
            warnings.append(line)

    # המעמד והתווית חייבים להיות אותו דבר בכל שכבה, ו-check_consistency הוא
    # מה שמודד את זה: המודל, הגרעין, הרשומה באינדקס, ה-handoff, התאים, וגם
    # ה-Word וסביבת העבודה כשנתיביהם נמסרו. מודל שאומר "מדיניות מאושרת"
    # בעוד הגרעין אומר "טעון אישור" אינו מודל תקף, ולכן אלה שגיאות
    try:
        drift = check_consistency(data, core, index_entry,
                                  cells=None, word_path=word, workspace_path=workspace)
    except Exception as exc:
        add(errors, "the cross-layer status check raised %s: %s" % (type(exc).__name__, exc))
        return True
    for d in drift:
        add(errors, "status drift: %s" % d)
    return True


def _load(path, label):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        print("INVALID")
        print("- cannot read %s (%s): %s" % (label, path, exc))
        raise SystemExit(1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Validates playbook-model.json: the schema here, and the "
                    "mechanisms in the shared library (areolegal/lib).")
    ap.add_argument("model")
    ap.add_argument("--core", help="playbook-core.json, compared against the model")
    ap.add_argument("--index", help="the playbook's entry in playbooks/index.json")
    ap.add_argument("--word", help="the playbook .docx, checked for a stale status")
    ap.add_argument("--workspace", help="the workspace file, checked for a stale status")
    a = ap.parse_args()
    raise SystemExit(main(a.model,
                          core=_load(a.core, "the core") if a.core else None,
                          index_entry=_load(a.index, "the index entry") if a.index else None,
                          word=a.word, workspace=a.workspace))
