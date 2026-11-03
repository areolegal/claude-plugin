#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
from pathlib import Path

# areo_lib נטען בתוך הפונקציות; תיקיית הסקריפט בנתיב גם ב-python -I
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # גם ב-python -I, שאינו מוסיף את תיקיית הסקריפט

for _s in (sys.stdout, sys.stderr):  # עברית בקונסולה שאינה UTF-8 (cp1252): בלי UnicodeEncodeError
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):   # לא TextIOWrapper (לכידה בבדיקות, pythonw)
        pass

VALID_STATUS = {"Confirmed", "Inferred", "Unclear"}
VALID_CONF = {"High", "Medium", "Low"}
VALID_PB_STATUS = {"Draft", "PartiallyApproved", "Approved", "Superseded", "Invalid"}
# מאיפה בא round1_posture: מברירת המחדל לפי החשיבות, מהצהרת התמורה, או
# מתשובת הלקוח
VALID_POSTURE_SOURCE = {"importance", "tradeoff_statement", "client_answer"}
VALID_POSTURE = {"hold_green", "offer_yellow", "not_applicable"}
WALK_AWAY_MAX = 5
VALID_REG_STATUS = {"NotResearched", "NoSpecificSourceIdentified", "ApplicableSourcesFound"}
# playbook-schema.md, presence_rule: אותה רשימה כאן, ב-validate_data.py ובתבנית סביבת העבודה. Recommended הוא ערך
# ישן שרק validate_data קיבל, והתבנית אינה מסננת לפיו: מתקבל באזהרה
VALID_PRESENCE = {"Required", "Optional", "Conditional", "Prohibited"}
LEGACY_PRESENCE = {"Recommended"}
VALID_MISSING_COLOR = {"Green", "Yellow", "Red", "NotApplicable"}
# track של ראיה: לאיזו עמדה היא תומכת; context אינו נספר לאף עמדה (playbook-schema.md, "ראיה")
VALID_EVIDENCE_TRACK = {"green", "yellow", "red", "context"}
# validation_queue[].scope, ו-rule_id "GLOBAL" כש-scope הוא playbook
VALID_QUEUE_SCOPE = {"rule", "segment", "rules", "playbook"}
# מעמד המאגר ומקור הנושא (playbook-schema.md, scope_summary.corpus_status, rules[].topic_origin)
VALID_CORPUS_STATUS = {"signed", "mostly_drafts", "company_forms", "third_party_forms", "unknown"}
VALID_TEMPLATE_STATUS = {"found", "attached", "none", "unknown", "not_asked"}
VALID_TOPIC_ORIGIN = {"catalog", "corpus_derived"}
# playbook-schema.md: "סטטוס המחקר, בשוק ובדין, מאותו סט: Performed | Partial | NotPerformed". הערכים
# הישנים נשארים מותרים, כדי שפלייבוק קיים לא ייפסל. לפני כן הסט של הסכמה נפסל כאן, ותבנית סביבת העבודה
# קיבלה רק אותו, ולכן בהרצה חיה צריך היה למפות ביד
VALID_RESEARCH_STATUS = {"Performed", "Partial", "NotPerformed", "NotRequested", "Declined", "Completed"}
RESEARCH_DONE = {"Performed", "Completed", "Partial"}
# market_research.status: אותו סט. not_run ו-skipped הם שמות ישנים ל-NotPerformed, שמתקבלים באזהרה; בהרצה חיה
# הבונה כתב not_run לצד schema_status, כי הסכמה והמאמתים לא הסכימו
LEGACY_NOT_PERFORMED = {"not_run", "skipped", "NotRequested", "Declined"}
VALID_NOT_PERFORMED_REASON = {"route", "no_web_access", "not_answered", "client_declined"}
VALID_QA_STATUS = {"NotRun", "Partial", "Completed"}
VALID_SEG_STATUS = {"NotDetected", "Candidate", "Confirmed"}
VALID_RATIONALE_STATUS = {"Draft", "Confirmed"}
VALID_OUTPUT_LANGUAGE = {"he", "en"}
VALID_MARKET_BASIS = {"ExternalResearch", "ExpertAssessment", "InternalTrendOnly", "NotAssessed"}
# מאיפה נבנה הפלייבוק: מההסכמים של החברה, מהם יחד עם השוק, או מהשוק בלבד
VALID_CORPUS_ORIGIN = {"own", "own_plus_market", "market_built"}
# הרצועה נגזרת ממספר ההסכמים בסוג, אחרי ניקוי כפילויות, גרסאות, תיקונים
# ותבניות. השמות הם אלה של `playbook-schema.md`, והספירה נעשית ב-
# `build_corpus_manifest.py` ולא בהערכה של המודל
CORPUS_BANDS = [(20, None, "full"), (7, 19, "below20"), (1, 6, "below7"), (0, 0, "none")]
# הרצועה מתארת את המדגם בלבד. היציאה לרשת אינה תלויה במספר ההסכמים: בכל רצועה שיש בה הסכמים
# הלקוח בוחר במפורש לשלב מחקר שוק (combine), או נשאר רק עם ההסכמים שלו (own_only / not_asked)
BAND_CHOICES = {"full": {"own", "own_plus_market", "market_built"}, "below20": {"own", "own_plus_market", "market_built"},
                "below7": {"own", "own_plus_market", "market_built"}, "none": {"market_built"}}
BAND_CHOICE_FIELD = {"full": {"not_asked", "combine", "own_only", "market"}, "below20": {"not_asked", "combine", "own_only", "market"},
                     "below7": {"combine", "own_only", "not_asked", "market"}, "none": {"market"}}
CHOICE_ORIGIN = {"own_only": "own", "combine": "own_plus_market", "market": "market_built"}
# הבסיס של כל מסלול: ראיה מההסכמים, נוסח שוק, או הצעה של Areo כשאין פשרה בראיות
# כל הערכים של playbook-schema.md ("basis: מקור המסלול"), ו-own_evidence מהגרסה הקודמת. לפני כן רק ארבעה
# ערכים, ומודל שנכתב לפי הסכמה ("template", "established", "single") נפסל
# documents_majority: ירוק במעמד unknown, כשלא ידוע מי ניסח (workflow.md, שלב 2ח). לפני כן לא היה לו ערך, ונרשם
# own_paper_repeated עם paper ריק
VALID_TRACK_BASIS = {"own_evidence", "own_paper_repeated", "documents_majority", "template", "company_request",
                     "client_answer", "established", "single", "offered_unexecuted", "company_source", "struck",
                     "rejected_comment", "never_accepted", "bid_condition", "market_standard", "areo_proposal"}
# playbook-schema.md, yellow.fallback_wording.source: מזהה ציטוט, answer:<מזהה>, market_standard או areo_proposal.
# הערכים שלמטה הם השמות הקודמים, ומתקבלים לתאימות. לפני כן רק הם התקבלו, ומודל שנכתב לפי הסכמה נפסל
FALLBACK_SOURCE_WORDS = {"market_standard", "areo_proposal"}
LEGACY_FALLBACK_SOURCE = {"signed_compromise", "single_compromise", "offered_not_signed", "client_answer"}
VALID_ACCEPTANCE_MODE = {"negotiated", "imposed", "unnegotiated", "unknown"}
# playbook-schema.md, "ראיה": ours או theirs, ו"כשלא ניתן לקבוע: השאר ריק". unknown נשאר מותר כשם ישן, באזהרה.
# לפני כן המאמת חייב ערך, validate_data קיבל רק ours או theirs, והסכמה אמרה להשאיר ריק
VALID_PAPER = {"ours", "theirs"}
LEGACY_PAPER = {"unknown"}
# source_log[].doc_role (playbook-schema.md). form: נוסח שאינו חתום ואינו טיוטה של משא ומתן: נוסח שהחברה מציגה,
# טופס הליך תחרותי או נוסח שפורסם (workflow.md, שלב 2ח). agreement הוא מה שהמניפסט כותב להסכם
# correspondence: התכתבות עם הצד שכנגד שהלקוח צירף כדי לחדד את קווי הנסיגה (playbook/sufficiency.py); אינה הסכם ואינה משא ומתן
# guidance / policy / table: מסמך הנחיה או מדיניות של החברה. אינו הסכם ואינו נספר כהסכם (ביקורת 31.10, כלל 3)
VALID_DOC_ROLE = {"signed", "agreement", "draft", "amendment", "template", "form", "correspondence",
                  "guidance", "policy", "table"}
# מקורות שאינם משא ומתן, ולכן אינם נספרים ב-evidence_count.independent_negotiations (evidence-policy.md, "Confidence")
NOT_NEGOTIATION_ROLES = {"form", "template", "correspondence", "guidance", "policy", "table"}
# fallback_origin.baseline (playbook-schema.md); documents_majority: הנוסח שחוזר ברוב המסמכים כשהם אינם הסכמים
# חתומים (company_forms, unknown). לפני כן לא היה ערך למעמד unknown
VALID_BASELINE = {"template", "own_paper_majority", "documents_majority", "none", "market"}
# מאגר שאינו הסכמים חתומים של החברה: נוסח אינו משא ומתן, ורמת הביטחון מוגבלת לפי ההסכמים החתומים שבו בלבד
NON_SIGNED_STATUSES = {"company_forms", "third_party_forms", "unknown"}
CONF_CAP_ORDER = {"Low": 0, "Medium": 1, "High": 2}
# הקודים הטכניים ונימוקי ההשמטה האסורים עברו ל-playbook/validate_model.py (coverage_findings), שהוא המימוש
# היחיד של בדיקת הכיסוי
# ביטויים שאסורים בנוסח צהוב: הם ויתור בלי תנאי
FORBIDDEN_YELLOW = ("לפי שיקול דעת הצד", "ללא הגבלה", "כפי שיידרש", "unlimited", "sole discretion")
LEGACY_RULE_KEYS = {"fallbacks", "fallback_1", "fallback_2", "red_line", "escalation"}
COLOR_SPEC = {"green": "Approved", "yellow": "AgreeWithComments", "red": "NotApproved"}

# רצפה לכל שדה במעבר ב, בתווים, כדי לתפוס שדה ריק מתוכן, ולא יעד אורך. policy-rationale.md הוא מקור התקרות
# (500 מילים לנושא שאינו נושא ליבה, 200 לווריאנט), והרצפות כאן מסתכמות מתחתיהן: כ-780 תווים (כ-135 מילים)
# בנושא, וכ-440 (כ-75 מילים) בווריאנט. לפני כן הן הסתכמו בכ-1,600 תווים, כ-330 מילים, מעל התקרה
RATIONALE_MIN = {
    "executive_policy_rationale": 120,
    "protected_interest_and_clause_purpose": 60,
    "legal_risk_and_legal_framework": 80,
    "contractual_risk_allocation_mechanism": 60,
    "company_role_and_policy_fit": 60,
    "business_operational_impact": 60,
    "internal_evidence_rationale": 60,
    "market_practice_assessment": 40,
    "green_boundary_rationale": 50,
    "yellow_boundary_rationale": 50,
    "red_boundary_rationale": 50,
    "tradeoff_statement": 40,
    "related_clause_rationale": 30,
    "uncertainties_and_limitations": 20,
}
SEG_RATIONALE_MIN = {
    "executive_segment_rationale": 70,
    "segment_characteristic_and_risk_change": 50,
    "legal_basis": 40,
    "business_basis": 40,
    "internal_evidence_basis": 40,
    "market_practice_assessment": 25,
    "green_boundary_rationale": 35,
    "yellow_boundary_rationale": 35,
    "red_boundary_rationale": 35,
    "tradeoff": 30,
    "related_clause_effect": 20,
    "uncertainties_and_limitations": 15,
}


def corpus_status_of(data):
    """מעמד המאגר מהגזירה האחת (playbook/status.py). כשהספרייה אינה זמינה, הערך שבמודל; בדיקות התוכן מדווחות
    על הספרייה החסרה בנפרד."""
    try:
        import areo_lib  # noqa: F401
        from playbook import status as S
        return S.corpus_status(data)
    except ImportError:
        return (data.get("scope_summary") or {}).get("corpus_status") or "signed"


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


def fallback_source_ok(src, citation_ids=None):
    """playbook-schema.md: מזהה ציטוט, answer:<מזהה>, market_standard או areo_proposal; והשמות הקודמים."""
    if not isinstance(src, str) or not src.strip():
        return False
    if src in FALLBACK_SOURCE_WORDS or src in LEGACY_FALLBACK_SOURCE or src.startswith("answer:"):
        return True
    # מזהה ציטוט: נבדק מול citations[] כשיש כאלה; בלעדיהם, כל מזהה שאינו ריק
    return src in citation_ids if citation_ids else True


def validate_traffic_light(errors, light, prefix, segment_ids, citation_ids=None):
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
        # או שהיא הצעה שלנו, וזו ההבחנה שהלקוח חייב לראות.
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
            elif not fallback_source_ok(fb.get("source"), citation_ids):
                add(errors, f"{cp}.fallback_wording invalid source {fb.get('source')!r}: a citation id, "
                            f"answer:<id>, market_standard or areo_proposal")
            elif fb.get("source") == "signed_compromise" and len(fb.get("negotiation_refs") or []) < 2:
                add(errors, f"{cp} established yellow requires two different negotiations")
            if block.get("offer_yellow") and (fb or {}).get("source") != "signed_compromise" \
                    and basis != "established":
                add(errors, f"{cp} offer_yellow is allowed only when the yellow is established")
            text = " ".join(str(x) for x in [block.get("proposed_clause"), (fb or {}).get("text")] if x)
            for bad in FORBIDDEN_YELLOW:
                if bad in text:
                    add(errors, f"{cp} yellow wording contains an unconditional concession: {bad}")
        validate_previous(errors, block.get("previous_agreements_where_language_accepted", []), cp, segment_ids)


# policy-rationale.md, "שני מעברים": במעבר א (rationale_status: Draft) נכתבים רק השדות הקצרים האלה, ויתר
# השדות ריקים ורשומים ב-pass_b_pending. האורכים במפרט הם תקרות, "ולעולם לא יעד". לפני כן המאמת דרש אורך
# מינימלי גם בטיוטה, ובהרצה חיה הבונה מתח את הנימוקים כדי לעבור אותו
PASS_A_FIELDS = ("executive_policy_rationale", "green_boundary_rationale", "yellow_boundary_rationale",
                 "red_boundary_rationale", "internal_evidence_rationale")


# כלל 12 (תנאי הפעלה לפי סוג הצד שכנגד) וכלל 3 (בדיקת תוצאה לכל כלל)
# סוג הצד שכנגד: אוצר המילים האחד של playbook-schema.md (applicability), כלומר המפתחות של
# orchestrator/resolve_playbook.ENTITY_KINDS, כולל הכינויים שהנושא ונותן ממפה (municipality ו-government לגוף ציבורי,
# charity ו-npo לעמותה, חל"צ ומלכ"ר). local, large, small ו-any הם הערכים הקודמים של תנאי ההפעלה, ומתקבלים לתאימות.
# לפני כן רק הם התקבלו, וסוג ישות כמו university נפסל
ENTITY_KIND_CODES = {"company", "corporate", "individual", "person", "public_body", "public", "government",
                     "municipality", "university", "academic", "non_profit", "npo", "nonprofit", "non-profit",
                     "charity", "government_company", "foreign", "large_enterprise", "large", "enterprise", "sme",
                     "small", "consumer", "group", "partnership"}
LEGACY_COUNTERPARTY_KIND = {"local", "foreign", "large", "small", "any"}
VALID_COUNTERPARTY_KIND = ENTITY_KIND_CODES | LEGACY_COUNTERPARTY_KIND
# applicability.not_observed[].label: סוג שלא נצפה אינו מוחרג (segmentation.md, §16)
NOT_OBSERVED_LABELS = {"לא נצפה בקורפוס", "not observed in the corpus"}
EXCLUSION_WORDS = re.compile(r"מוחרג|לא חל|לא מכוסה|מחוץ לתחולה|exclud|not applicable|not covered|out of scope", re.I)
VALID_POST_SCOPE = {"whole_agreement", "definitions", "annexes"}
VALID_POST_ON_FAIL = {"block", "warn"}


def bad_kinds(value):
    """הערכים שאינם באוצר המילים. resolve_playbook מקבל רשימה או כמה ערכים בפסיק ("university,foreign")."""
    parts = value if isinstance(value, (list, tuple)) else str(value).split(",")
    return [p for p in parts if str(p).strip().lower() not in VALID_COUNTERPARTY_KIND]


def validate_applicability(errors, warnings, app):
    """applicability (playbook-schema.md): counterparty_kinds[] מאוצר המילים, ו-not_observed[] לסוג שלא נצפה בקורפוס,
    בתווית "לא נצפה בקורפוס" ולעולם לא "מוחרג". חסר אינו נפסל כאן, כדי שפלייבוק קיים לא ייפסל."""
    if app is None:
        return
    if not isinstance(app, dict):
        add(errors, "applicability must be an object {counterparty_kinds[], deal_kinds[], value_range, "
                    "not_observed[], not_covered[]}")
        return
    kinds = app.get("counterparty_kinds")
    if kinds is not None and not isinstance(kinds, list):
        add(errors, "applicability.counterparty_kinds must be a list")
    elif kinds:
        bad = bad_kinds(kinds)
        if bad:
            warnings.append(f"applicability.counterparty_kinds has values outside the vocabulary {bad}: "
                            f"{', '.join(sorted(ENTITY_KIND_CODES))}")
    no = app.get("not_observed")
    if no is None:
        return
    if not isinstance(no, list):
        add(errors, "applicability.not_observed must be a list of {kind, label, recommendation}")
        return
    for j, x in enumerate(no):
        pp = f"applicability.not_observed[{j}]"
        kind = x.get("kind") if isinstance(x, dict) else x
        if not isinstance(x, (dict, str)) or not nonempty(kind):
            add(errors, f"{pp} needs kind (a counterparty type)")
            continue
        if bad_kinds(kind):
            add(errors, f"{pp}.kind {kind!r} is not a counterparty type ({', '.join(sorted(ENTITY_KIND_CODES))}); "
                        f"a deal type goes in not_covered[]")
        if not isinstance(x, dict):
            continue
        label = x.get("label")
        if nonempty(label) and EXCLUSION_WORDS.search(str(label)):
            add(errors, f"{pp}.label {label!r}: a type not observed is never excluded; the label is "
                        f"\"לא נצפה בקורפוס\" (EN: \"not observed in the corpus\")")
        elif nonempty(label) and str(label).strip() not in NOT_OBSERVED_LABELS:
            add(errors, f"{pp}.label {label!r} must be \"לא נצפה בקורפוס\" (EN: \"not observed in the corpus\")")
        if not nonempty(x.get("recommendation")):
            warnings.append(f"{pp} has no recommendation: what to check when the playbook is applied to this "
                            f"type (clause-catalog.md, \"Considerations by counterparty type\")")


def validate_activation_and_post_checks(errors, rule, prefix):
    for j, c in enumerate(rule.get("activation_conditions") or []):
        if not isinstance(c, dict):
            continue
        # counterparty_entity: סוג הישות בתנאי ההפעלה (playbook-schema.md, applicability), מאותו אוצר מילים
        for key in ("counterparty_kind", "counterparty_entity"):
            if c.get(key) not in (None, "", []) and bad_kinds(c[key]):
                add(errors, f"{prefix}.activation_conditions[{j}].{key} invalid "
                            f"({', '.join(sorted(VALID_COUNTERPARTY_KIND))})")
    pcs = rule.get("post_checks")
    if pcs is None:
        return
    if not isinstance(pcs, list):
        add(errors, f"{prefix}.post_checks must be a list")
        return
    for j, pc in enumerate(pcs):
        pp = f"{prefix}.post_checks[{j}]"
        if not isinstance(pc, dict):
            add(errors, f"{pp} must be an object")
            continue
        if not nonempty(pc.get("id")) or not nonempty(pc.get("intent")):
            add(errors, f"{pp} missing id or intent")
        cond = pc.get("pass_when")
        if isinstance(cond, dict):
            pats = list(cond.get("absent") or []) + list(cond.get("present") or [])
            if not pats:
                add(errors, f"{pp}.pass_when needs absent[] or present[]")
            for x in pats:
                try:
                    re.compile(x)
                except (re.error, TypeError):
                    add(errors, f"{pp}.pass_when has an invalid pattern: {x!r}")
        elif not nonempty(cond):
            add(errors, f"{pp}.pass_when missing (text for a manual check, or {{absent, present}})")
        if pc.get("scope") not in (None, "") and pc["scope"] not in VALID_POST_SCOPE:
            add(errors, f"{pp}.scope invalid ({', '.join(sorted(VALID_POST_SCOPE))})")
        if pc.get("on_fail") not in (None, "") and pc["on_fail"] not in VALID_POST_ON_FAIL:
            add(errors, f"{pp}.on_fail invalid (block, warn)")


PERSPECTIVE_FIELDS = ("legal_analysis", "business_analysis", "internal_corpus_findings",
                      "internal_contracting_trend", "external_market_trend")


def validate_perspective(errors, rule, prefix):
    """company_perspective: במעבר א מותר שדה ריק כשהוא רשום ב-pass_b_pending בשם company_perspective.<שדה>
    (playbook-schema.md, pass_b_pending). לפני כן המאמת חייב את חמשת השדות כבר במעבר א, וההוראות לא."""
    rat = rule.get("policy_rationale") if isinstance(rule.get("policy_rationale"), dict) else {}
    draft = rat.get("rationale_status") == "Draft"
    pending = set(rat.get("pass_b_pending") or ())
    persp = rule.get("company_perspective")
    if not isinstance(persp, dict):
        if draft and all("company_perspective.%s" % k in pending for k in PERSPECTIVE_FIELDS):
            return
        add(errors, f"{prefix} missing/non-object company_perspective")
        return
    for key in PERSPECTIVE_FIELDS:
        if not nonempty(persp.get(key)) and not (draft and "company_perspective.%s" % key in pending):
            add(errors, f"{prefix}.company_perspective missing {key}"
                        + (" (in pass A, list it in pass_b_pending as company_perspective.%s)" % key
                           if draft else ""))


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
            # שדות מעבר א נכתבים במעבר ב במלואם (policy-rationale.md, "שני מעברים"), ולכן הרצפה חלה גם עליהם
            add(errors, f"{prefix}.{key} too thin ({text_len(rationale.get(key))} chars; minimum {minimum})"
                        + (": pass B writes this pass A field in full (policy-rationale.md, sections 1, 8 and 10)"
                           if min_spec is RATIONALE_MIN and key in PASS_A_FIELDS else ""))
    scenarios = rationale.get("applicability_scenarios")
    if not isinstance(scenarios, list) or len([x for x in scenarios if nonempty(x)]) < applicability_min:
        add(errors, f"{prefix}.applicability_scenarios requires at least {applicability_min} substantive scenarios")
    if rationale.get("rationale_status") not in VALID_RATIONALE_STATUS:
        add(errors, f"{prefix} invalid rationale_status")
    if rationale.get("market_practice_basis") not in VALID_MARKET_BASIS:
        add(errors, f"{prefix} invalid market_practice_basis")


def _guard(out, inputs):
    """הפלט (--coverage-out, --inventory-skeleton) לעולם אינו נכתב על קובץ קלט או על מסמך קיים. None: סירוב."""
    from common.cli import OutputRefused, guard_out
    try:
        return guard_out(out, inputs=inputs)
    except OutputRefused as exc:
        print("refused: %s" % exc)
        return None


def validate_qa_summary(errors, data):
    """playbook-qa.md, "qa_summary": status Completed מחייב את המספרים ואת track_coherence כבר בבנייה,
    ולא רק באישור. אחרת טיוטה עוברת את הבדיקה ונפסלת ברגע שעורך הדין מאשר אותה (הרצה מקצה לקצה, 02.11)."""
    qa = data.get("qa_summary")
    if not isinstance(qa, dict):
        add(errors, "qa_summary must be object")
        return
    status = qa.get("status")
    if status not in VALID_QA_STATUS:
        add(errors, "qa_summary invalid status")
    if data.get("playbook_status") == "Approved" and status != "Completed":
        add(errors, "Approved playbook requires completed QA back-test")
    if status != "Completed":
        return

    hint = "or record qa_summary.status Partial with untested_rule_ids (playbook-qa.md, \"qa_summary\")"
    rules = [r for r in (data.get("rules") or []) if isinstance(r, dict)]
    count = qa.get("tested_rule_count")
    if not isinstance(count, int) or isinstance(count, bool):
        add(errors, f"qa_summary status Completed requires tested_rule_count, {hint}")
    elif count != len(rules):
        add(errors, f"qa_summary status Completed requires tested_rule_count equal to the number of rules "
                    f"({count} != {len(rules)}), {hint}")
    src = qa.get("tested_source_count")
    if not isinstance(src, int) or isinstance(src, bool) or src < 0:
        add(errors, f"qa_summary status Completed requires tested_source_count, {hint}")
    if not nonempty(qa.get("checked_at")):
        add(errors, "qa_summary status Completed requires checked_at")

    tc = qa.get("track_coherence")
    if not isinstance(tc, list) or not tc:
        add(errors, f"qa_summary status Completed requires track_coherence[], one entry per rule and per "
                    f"segment variant {{rule_id, segment_id}}, {hint}")
        return
    covered = set()
    for entry in tc:
        if isinstance(entry, dict) and nonempty(entry.get("rule_id")):
            covered.add((entry["rule_id"], entry.get("segment_id") or None))
    missing = []
    for rule in rules:
        rid = rule.get("rule_id")
        if (rid, None) not in covered:
            missing.append(str(rid))
        for var in rule.get("segment_variants") or []:
            if isinstance(var, dict) and nonempty(var.get("segment_id")) \
                    and (rid, var["segment_id"]) not in covered:
                missing.append(f"{rid}/{var['segment_id']}")
    if missing:
        add(errors, "qa_summary status Completed requires a track_coherence entry for every rule and segment "
                    f"variant; missing: {', '.join(missing)}, {hint}")


def main(path, core=None, index_entry=None, word=None, workspace=None, inventory=None, extract=None,
         coverage_out=None, skeleton_out=None, inputs=()):
    if skeleton_out and not Path(path).exists():
        # שלד המלאי נבנה לפני המודל (wf1-scope-corpus-extraction.md, שלב 4א): בלי מודל, מכל מסמכי החילוץ
        data = {}
    else:
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception as exc:
            print("INVALID")
            print("- cannot parse JSON:", exc)
            return 1
    # מלאי הסעיפים וקובץ החילוץ: כשלא נמסרו, נטענים מהמקום הקבוע שלהם, כדי שבדיקת הכיסוי תרוץ בכל הרצה
    if inventory is None:
        inventory = _find_beside(path, ((data.get("coverage") or {}).get("inventory_ref"),
                                        "clause-inventory.json"))
    if extract is None:
        extract = _find_beside(path, ((data.get("coverage") or {}).get("extract_ref"),
                                      "../../corpus-extract.json"))
    if skeleton_out:
        try:
            import areo_lib  # noqa: F401
            from playbook.validate_model import inventory_skeleton
        except ImportError as exc:
            print("the shared library is not importable: %s" % exc)
            return 1
        if not extract:
            print("no corpus extract: pass --extract")
            return 2
        target = _guard(skeleton_out, [path] + list(inputs))
        if not target:
            return 2
        sk = inventory_skeleton(data, extract)
        Path(target).write_text(json.dumps(sk, ensure_ascii=False, indent=1), encoding="utf-8")
        print("inventory skeleton written to %s: %d units to map (rule_id, technical, unique or "
              "unmapped_reason in each)" % (skeleton_out, len(sk["units"])))
        return 0
    if coverage_out:
        try:
            import areo_lib  # noqa: F401
            from playbook.validate_model import coverage_from_inventory
        except ImportError as exc:
            print("the shared library is not importable: %s" % exc)
            return 1
        if not inventory:
            print("no clause inventory: pass --inventory")
            return 2
        target = _guard(coverage_out, [path] + list(inputs))
        if not target:
            return 2
        block = coverage_from_inventory(data, inventory, extract)
        block["inventory_ref"] = inventory.get("ref") or (data.get("coverage") or {}).get("inventory_ref") or ""
        Path(target).write_text(json.dumps(
            {k: v for k, v in block.items() if not k.startswith("_")}, ensure_ascii=False, indent=1),
            encoding="utf-8")
        print("coverage block written to %s (units %d: mapped %d, technical %d, unique %d, unmapped %d, "
              "unassigned %d)" % (coverage_out, block["units"], block["topic_units"],
                                  block["technical_units"], block["unique_units"], block["unmapped_units"],
                                  block["unassigned_units"]))

    errors = []
    warnings = []
    required_top = ["schema_version", "core_version", "playbook_id", "profile_id", "version", "playbook_status", "output_language", "scope_summary", "segmentation_model", "rules", "regulatory_research", "qa_summary"]
    for key in required_top:
        if not nonempty(data.get(key)):
            add(errors, f"missing {key}")

    # הבונה כותב תמיד Draft. אישור מדיניות אינו מתואר, אינו
    # מתועד ואינו נכתב כאן, ולכן מודל שיוצא מהבונה בכל ערך אחר נפסל
    # בבנייה הערך תמיד Draft. PartiallyApproved ו-Approved נגזרים בקוד אחרי
    # קליטה של גיליון העמדות, ולכן מותרים רק כשיש רשומת קליטה
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
    # התווית היא שדה אחד, ושתי תוויות באותה רשומה הן תקלה
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
        # בקוד מתוך המניפסט, ולא בהערכה של המודל.
        origin = scope.get("corpus_origin")
        if origin not in VALID_CORPUS_ORIGIN:
            add(errors, "scope_summary missing/invalid corpus_origin")
        elif data.get("corpus_origin") not in (None, origin):
            add(errors, f"corpus_origin at the root ({data.get('corpus_origin')}) differs from "
                        f"scope_summary.corpus_origin ({origin})")
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

        cs = scope.get("corpus_status")
        if cs is None:
            warnings.append("scope_summary.corpus_status is missing (signed, mostly_drafts, company_forms, "
                            "third_party_forms, unknown): the basis line falls back to source_log")
        elif cs not in VALID_CORPUS_STATUS:
            add(errors, f"scope_summary.corpus_status invalid {cs!r} ({', '.join(sorted(VALID_CORPUS_STATUS))})")
        ts = scope.get("template_status")
        if ts is not None and ts not in VALID_TEMPLATE_STATUS:
            add(errors, f"scope_summary.template_status invalid {ts!r} ({', '.join(sorted(VALID_TEMPLATE_STATUS))})")

        # מי חתום על ההסכמים. כשזו אינה החברה שבפרופיל, חייבים לומר מי כן.
        if scope.get("contracting_entity_differs") and not nonempty(scope.get("contracting_entity")):
            add(errors, "scope_summary requires contracting_entity when the signer is not the profile company")

    validate_applicability(errors, warnings, data.get("applicability"))

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
            # כלל מייסד 3: מחקר רשת רק כשהלקוח בחר בו. band_below7 ו-band_none הם הערכים הישנים (נקראים, לא נכתבים)
            if rr.get("trigger") not in ("client_chose", "band_below7", "band_none")                     and rr.get("requested_by_user") is not True:
                add(errors, "regulatory research Performed/Partial requires trigger client_chose (the client chose "
                            "deep research: corpus_basis.choice combine or market)")
            _choice = (((data.get("scope_summary") or {}).get("corpus_basis")) or {}).get("choice")
            if _choice in ("own_only", "not_asked"):
                add(errors, "regulatory research was recorded Performed/Partial, but corpus_basis.choice is %s: "
                            "outside research only when the client chose it (rr1-gate-sources-verification.md)" % _choice)
            if not nonempty(rr.get("checked_at")):
                add(errors, "completed/partial regulatory research requires checked_at")

    # סטטוס המחקר, בשוק ובדין, מאותו סט, ו-not_performed_reason חובה כשהמחקר לא בוצע (playbook-schema.md)
    if isinstance(rr, dict) and rr.get("status") == "NotPerformed" and \
            rr.get("not_performed_reason") not in VALID_NOT_PERFORMED_REASON:
        add(errors, "regulatory_research NotPerformed requires not_performed_reason "
                    "(%s)" % ", ".join(sorted(VALID_NOT_PERFORMED_REASON)))
    mr = data.get("market_research")
    if not isinstance(mr, dict):
        add(errors, "missing market_research{} (status Performed, Partial or NotPerformed)")
    else:
        ms = mr.get("status")
        if ms in LEGACY_NOT_PERFORMED:
            warnings.append(f"market_research.status {ms} is a legacy name for NotPerformed")
        elif ms not in ("Performed", "Partial", "NotPerformed", "Completed"):
            add(errors, f"market_research invalid status {ms!r} (Performed, Partial, NotPerformed)")
        elif ms == "NotPerformed" and mr.get("not_performed_reason") not in VALID_NOT_PERFORMED_REASON:
            add(errors, "market_research NotPerformed requires not_performed_reason "
                        "(%s)" % ", ".join(sorted(VALID_NOT_PERFORMED_REASON)))

    validate_qa_summary(errors, data)

    # מלאי הסעיפים: ההוכחה שאף סעיף לא נשר בשקט. הבדיקה כולה ב-playbook/validate_model.py (coverage_findings),
    # שרצה מתוך content_findings, גם מול clause-inventory.json וקובץ החילוץ כשהם נמצאים

    rules = data.get("rules")
    if not isinstance(rules, list) or not rules:
        add(errors, "rules must be a non-empty list")
        rules = []

    # רישום המקורות: על נייר של מי כל הסכם, ואיך התקבל. בלי זה ראיה
    # ממסמך שהצד שכנגד ניסח נראית כמו ראיה למדיניות שלנו.
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
        if src.get("doc_role") not in (None, "") and src["doc_role"] not in VALID_DOC_ROLE:
            add(errors, f"{sp} invalid doc_role {src['doc_role']!r} ({', '.join(sorted(VALID_DOC_ROLE))})")
        if src.get("doc_role") in ("template", "correspondence"):
            continue          # תבנית והתכתבות אינן הסכם, ואינן נספרות ככזה
        if src.get("paper") in LEGACY_PAPER:
            warnings.append(f"{sp} paper {src['paper']!r} is a legacy value: leave it empty when it cannot be "
                            f"determined (playbook-schema.md)")
        elif src.get("paper") not in VALID_PAPER and src.get("paper") not in (None, ""):
            add(errors, f"{sp} invalid paper {src.get('paper')!r} (ours, theirs, or empty when it cannot be determined)")
        if not nonempty(src.get("channel")):
            add(errors, f"{sp} missing channel")
        if src.get("acceptance_mode") not in VALID_ACCEPTANCE_MODE:
            add(errors, f"{sp} missing/invalid acceptance_mode")

    # מעמד המאגר, וכמה משאים ומתנים יש בו בכלל (workflow.md, שלב 2ח; evidence-policy.md, "Confidence")
    corpus_status = corpus_status_of(data)
    included_src = [x for x in (data.get("source_log") or []) if isinstance(x, dict) and x.get("included") is not False]
    if corpus_status == "unknown":
        max_negotiations = 0
    else:
        max_negotiations = len({x.get("negotiation_id") or x.get("source_id") for x in included_src
                                if x.get("doc_role") not in NOT_NEGOTIATION_ROLES and x.get("status") != "company_form"})
    if corpus_status == "company_forms" and included_src and             not any(x.get("doc_role") == "form" or x.get("status") == "company_form" for x in included_src):
        warnings.append("scope_summary.corpus_status is company_forms, and no source_log row is doc_role form: "
                        "record each form as doc_role form (workflow.md, step 2ח)")

    citation_ids = {c.get("citation_id") for c in (data.get("citations") or [])
                    if isinstance(c, dict)}

    rule_ids = set()
    confirmed_segment_variants = 0
    walk_away_rules = []
    legacy_ec_seen = set()
    for i, rule in enumerate(rules):
        prefix = f"rules[{i}]"
        if not isinstance(rule, dict):
            add(errors, f"{prefix} must be object")
            continue
        validate_activation_and_post_checks(errors, rule, prefix)
        for legacy in sorted(LEGACY_RULE_KEYS):
            if legacy in rule:
                add(errors, f"{prefix} contains prohibited legacy field {legacy}")
        # נושא שאין לו ראיה בקורפוס (נושא מהפרופיל או מתשובת הלקוח) נרשם עם evidence: [], כשכל המסלולים שלו
        # client_answer, areo_proposal או market_standard (ps3-rule-and-evidence.md, evidence[]); לא "ראיה" שהיא הסבר
        no_ev_ok = isinstance(rule.get("evidence"), list) and all(
            ((rule.get("traffic_light") or {}).get(t) or {}).get("basis") in ("client_answer", "areo_proposal",
                                                                                "market_standard")
            for t in ("green", "yellow", "red"))
        for key in ["rule_id", "topic_name", "clause_issue", "why_address_topic", "policy_status", "confidence", "evidence", "presence_rule", "policy_rationale", "traffic_light"]:
            if key == "evidence" and no_ev_ok:
                continue
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

        validate_perspective(errors, rule, prefix)
        if rule.get("topic_origin") not in (None, "") and rule["topic_origin"] not in VALID_TOPIC_ORIGIN:
            add(errors, f"{prefix} invalid topic_origin {rule['topic_origin']!r} (catalog, corpus_derived)")

        validate_rationale(errors, rule.get("policy_rationale"), f"{prefix}.policy_rationale", RATIONALE_MIN, 2)

        # מה מציעים בסבב הראשון, ומאיפה הערך בא. ברירת המחדל
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

        # שובר עסקה: חובה בכל כלל, ומקור רשום כשהערך true
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
            req = presence.get("requirement")
            if req in LEGACY_PRESENCE:
                warnings.append(f"{prefix}.presence_rule.requirement {req} is a legacy value; use one of "
                                f"{', '.join(sorted(VALID_PRESENCE))}")
            elif req not in VALID_PRESENCE:
                add(errors, f"{prefix}.presence_rule invalid requirement {req!r} "
                            f"({', '.join(sorted(VALID_PRESENCE))})")
            elif req == "Conditional" and not nonempty(presence.get("condition")) \
                    and not nonempty(rule.get("activation_conditions")):
                add(errors, f"{prefix}.presence_rule Conditional requires condition (or activation_conditions[])")
            if presence.get("missing_clause_color") not in VALID_MISSING_COLOR:
                add(errors, f"{prefix}.presence_rule invalid missing_clause_color")

        reg_status = rule.get("regulatory_status")
        if reg_status not in VALID_REG_STATUS:
            add(errors, f"{prefix} invalid/missing regulatory_status")
        if reg_status == "ApplicableSourcesFound" and not nonempty(rule.get("regulatory_sources")):
            add(errors, f"{prefix} ApplicableSourcesFound requires regulatory_sources")

        # הראיות של הכלל: לאיזה מסלול הן שייכות, מאיזה הסכם, ובאיזו פוזיציה.
        # ראיה ממשפחת הסכמים אחרת אינה בסיס למסלול, רק הקשר.
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
            if track not in (None, "") and track not in VALID_EVIDENCE_TRACK:
                add(errors, f"{ep} invalid track {track!r} (green, yellow, red, context)")
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
            docs = ec.get("documents_addressing")
            if docs is not None and (isinstance(docs, bool) or not isinstance(docs, int) or docs < 0):
                add(errors, f"{prefix}.evidence_count.documents_addressing must be a count of documents")
            for old in ("forms_addressing_topic", "forms_addressing", "documents_addressing_topic"):
                if old in ec and old not in legacy_ec_seen:
                    legacy_ec_seen.add(old)
                    warnings.append(f"{prefix}.evidence_count.{old} (and in other rules) is a legacy name: "
                                    f"documents_addressing")
            # נוסח שאינו חתום אינו משא ומתן (workflow.md, שלב 2ח): במאגר שאינו הסכמים חתומים הספירה היא רק של
            # ההסכמים החתומים שבו, ובמעמד unknown כל המסמכים מטופלים כלא חתומים
            if isinstance(ind, int) and corpus_status in NON_SIGNED_STATUSES and ind > max_negotiations:
                add(errors, f"{prefix}.evidence_count.independent_negotiations is {ind}, but the corpus "
                            f"({corpus_status}) has {max_negotiations} negotiations: a form is not a negotiation. "
                            f"Count the documents in documents_addressing")
            if isinstance(ind, int) and rule.get("confidence") in CONF_CAP_ORDER:
                cap = "Low" if ind <= 1 else "Medium" if ind == 2 else "High"
                if corpus_status in NON_SIGNED_STATUSES and                         CONF_CAP_ORDER[rule["confidence"]] > CONF_CAP_ORDER[cap]:
                    add(errors, f"{prefix}.confidence {rule['confidence']} is above the cap for {ind} "
                                f"negotiations ({cap})")
        fo = rule.get("fallback_origin")
        if isinstance(fo, dict) and fo.get("baseline") not in (None, "") and fo["baseline"] not in VALID_BASELINE:
            warnings.append(f"{prefix}.fallback_origin.baseline {fo['baseline']!r} is not in the schema "
                            f"({', '.join(sorted(VALID_BASELINE))})")

        validate_traffic_light(errors, rule.get("traffic_light"), prefix, segment_ids, citation_ids)

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
            validate_traffic_light(errors, variant.get("traffic_light"), vp, segment_ids, citation_ids)
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
    # כלל Unclear מכוסה גם בפריט אחד ברמת הכללים (scope: rules, עם rule_ids[]), כשכמה כללים לא ברורים מאותה
    # סיבה (למשל אין ראיה מאוכלוסיית הבסיס, segmentation.md §9): לא פריט נפרד לכל כלל
    queue_rule_ids = {q.get("rule_id") for q in queue if isinstance(q, dict)}
    queue_rule_ids |= {x for q in queue if isinstance(q, dict) and q.get("scope") == "rules"
                       for x in q.get("rule_ids") or []}
    # playbook-schema.md, validation_queue[]: rule_id חובה ב-rule וב-segment וקיים ב-rules[]; "GLOBAL" ב-playbook;
    # rule_ids[] (שניים לפחות) ב-rules. לפני כן GLOBAL נדחה ב-validate_data, והבונה כתב rule_id ריק כדי לעבור
    for i, q in enumerate(queue):
        if not isinstance(q, dict):
            add(errors, f"validation_queue[{i}] must be object")
            continue
        qp = "validation_queue[%d] (%s)" % (i, q.get("id"))
        scope_q, rid_q = q.get("scope"), q.get("rule_id")
        for key in ("id", "topic", "question", "why", "severity", "recommendation"):
            if not nonempty(q.get(key)):
                add(errors, f"{qp} missing {key}")
        if scope_q is None:
            warnings.append(f"{qp} has no scope (rule, segment, rules, playbook)")
        elif scope_q not in VALID_QUEUE_SCOPE:
            add(errors, f"{qp} invalid scope {scope_q!r}")
        if scope_q in ("rule", "segment") and rid_q not in rule_ids:
            add(errors, f"{qp} scope {scope_q} requires a rule_id that exists in rules[] (got {rid_q!r})")
        if scope_q == "playbook" and rid_q != "GLOBAL":
            if rid_q in (None, ""):
                warnings.append(f"{qp} scope playbook: rule_id should be GLOBAL")
            else:
                add(errors, f"{qp} scope playbook takes rule_id GLOBAL (got {rid_q!r})")
        if scope_q == "segment" and q.get("segment_id") not in segment_ids:
            add(errors, f"{qp} scope segment requires a known segment_id")
        if scope_q == "rules":
            ids = q.get("rule_ids") or []
            if len(ids) < 2 or any(x not in rule_ids for x in ids):
                add(errors, f"{qp} scope rules requires rule_ids[] of two or more existing rules")
        if scope_q is None and rid_q not in (None, "", "GLOBAL") and rid_q not in rule_ids:
            add(errors, f"{qp} rule_id {rid_q} does not exist")
    for i, rule in enumerate(rules):
        if isinstance(rule, dict) and rule.get("policy_status") == "Unclear":
            if rule.get("rule_id") not in queue_rule_ids and not nonempty(rule.get("validation_question")):
                add(errors, f"rules[{i}] Unclear rule lacks validation queue item/question")

    # לכל היותר חמישה שוברי עסקה בפלייבוק. פלייבוק שבו כל כלל
    # שובר עסקה אינו מדיניות, אלא רשימת תנאים שאין איתה משא ומתן
    if len(walk_away_rules) > WALK_AWAY_MAX:
        add(errors, "%d rules have walk_away: true, the limit is %d (%s)"
                    % (len(walk_away_rules), WALK_AWAY_MAX,
                       ", ".join(str(r) for r in walk_away_rules[:8])))

    content = content_findings(data, errors, warnings, core=core, index_entry=index_entry, word=word,
                              workspace=workspace, inventory=inventory, extract=extract, model_path=path)
    handoff_findings(data, errors)
    enforce_findings(data, errors, warnings, extract, path)

    if errors:
        print("INVALID")
        for error in errors:
            print("-", error)
        for w in warnings:
            print("! warning:", w)
        client_lines(data, core)
        return 1
    print("VALID")
    for w in warnings:
        print("! warning:", w)
    if content:
        print("(content checks from the shared library ran: %d findings, none blocking)"
              % len(warnings))
    return 0


def enforce_findings(data, errors, warnings, extract=None, model_path=None):
    """שכבת האכיפה (enforce_playbook_checks.run_checks) רצה גם כאן, כך שכלל שנאכף שם חוסם גם בקריאה לאימות:
    שתיקה אינה ירוק, אדום בלי נוסח הוא פער, נימוק שחוזר על העמדה ריק, שמות צדדים, סף הקורפוס."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import enforce_playbook_checks as EN
        import evidence_kind as E
    except ImportError as exc:
        add(errors, "enforce_playbook_checks is not importable, so the enforcement checks did not run: %s" % exc)
        return
    try:
        ex = extract if extract is not None else E.find_extract(data, model_path)
        errs, warns = EN.run_checks(data, ex)
    except Exception as exc:
        add(errors, "enforcement checks raised %s: %s" % (type(exc).__name__, exc))
        return
    for e in errs:
        add(errors, "enforce: " + e)
    for w in warns:
        warnings.append("enforce: " + w)


def handoff_findings(data, errors):
    """בנייה לבקשת הנושא ונותן: התשובה לשאלת המסלול
    חוזרת ב-handoff.route_answer כשנשאלה בבונה, ועד שלוש החלטות ב-decisions_now[],
    כל אחת עם המלצה. ואין בתור השאלות פריט שמבקש לאשר בחירה שנעשתה באותה הפעלה."""
    req = (data.get("meta") or {}).get("build_request") or {}
    # כל רכיב שהפלייבוק חובה בו (הנושא ונותן, מעריך הסיכונים, האסטרטג, המנסח) מקבל handoff
    if req.get("requested_by") in (None, "", "user"):
        return
    h = data.get("handoff")
    if not isinstance(h, dict):
        add(errors, "handoff: a build for another component returns a handoff record")
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


def client_lines(data, core=None):
    """אחרי INVALID: השורות ללקוח, בשפת הפלייבוק (playbook/validity.playbook_warnings). קוד 1 אינו סוף הדרך
    בשקט: הבונה מתקן ומריץ שוב, וכשהפלייבוק נמסר בכל זאת, השורות האלה נכנסות להודעה המסכמת כלשונן
    (wf2-opinion-research-finalize.md, שלב 12). סוכן אחר שמחיל את הפלייבוק קורא לאותה פונקציה."""
    try:
        import areo_lib  # noqa: F401
        from playbook import validity as VY
    except ImportError:
        return
    lang = "en" if str(data.get("output_language") or "").startswith("en") else "he"
    lines = VY.playbook_warnings(data, core, lang=lang)
    if VY.validity_summary(data, core)["status"] == "valid":
        # הבדיקות הזולות עברו, והמאמת המלא לא: השורה הכללית, לפני שאר השורות
        lines.insert(0, VY.TEXT[lang]["other"]["some"])
    print("client (%s): %s" % (lang, VY.TEXT[lang]["head"]))
    for line in lines:
        print("client (%s): %s" % (lang, line))


def _find_beside(model_path, candidates):
    """קובץ JSON לצד המודל: נתיב מוחלט, נתיב יחסי למודל, או שם הקובץ בתיקיית המודל. None כשלא נמצא."""
    base = Path(model_path).resolve().parent
    for c in candidates:
        if not c:
            continue
        for q in (Path(c), base / c, base / Path(str(c).replace("\\", "/")).name):
            try:
                if q.is_file():
                    return json.loads(q.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
    return None


def workspace_file_problems(workspace):
    """הקובץ של סביבת העבודה קיים, שלם ופתיח: מסמך HTML מלא, בלי נקודת הזרקה שנשארה ריקה."""
    import os
    if not os.path.isfile(workspace):
        return ["Workspace: הקובץ %s לא קיים" % workspace]
    s = open(workspace, encoding="utf-8", errors="replace").read()
    out = []
    if not s.lstrip().lower().startswith("<!doctype html"):
        out.append("Workspace: הקובץ אינו מסמך HTML שלם (חסר doctype)")
    if "</html>" not in s or s.count("<script") != s.count("</script>"):
        out.append("Workspace: הקובץ נחתך או לא נסגר (חסר </html> או תג script לא סגור)")
    if "/*__DATA__*/null" in s:
        out.append("Workspace: הנתונים לא הוזרקו לדף (נקודת ההזרקה נשארה ריקה)")
    return out


def workspace_findings(st, workspace, model, S, MC):
    """סטיות בין המעמד המחושב לבין סביבת העבודה. כמו surfaces_render.check_surfaces, אבל label_now ו-approved_count
    שחסרים נגזרים כאן ממה שכן נכתב: status_label במקום label_now, ו-0 במקום approved_count כשהמחושב 0. בבנייה
    ראשונה אף סקריפט אינו כותב אותם (build_workspace_payload לוקח אותם רק מ-policy_gate במודל), ולכן הבדיקה
    הקודמת נכשלה בכל בנייה ראשונה. ערך שנכתב ושונה מהמחושב נשאר שגיאה."""
    from playbook.surfaces_render import read_workspace_status
    out = []
    meta = (read_workspace_status(workspace) or {}).get("meta") or {}
    st = S.in_lang(st, meta.get("lang"))
    for f in S.DUAL_FIELDS:
        if f in meta:
            out.append("Workspace: meta.%s: שדה תווית כפול" % f)
    label = meta.get("label_now") if meta.get("label_now") is not None else meta.get("status_label")
    if label != st["label"]:
        out.append('Workspace: label_now="%s", המחושב: "%s"' % (label, st["label"]))
    count = meta.get("approved_count")
    if count is None and st["approved_count"] == 0:
        count = 0
    if count != st["approved_count"]:
        out.append("Workspace: approved_count=%s, המחושב: %d" % (count, st["approved_count"]))
    out += ["Workspace: " + p for p in MC.count_claims(meta.get("evidence_disclaimer") or "", model)]
    return out


def content_findings(data, errors, warnings, core=None, index_entry=None,
                     word=None, workspace=None, inventory=None, extract=None, model_path=None):
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
        findings = validate(data, core=core, index_entry=index_entry, inventory=inventory, extract=extract)
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
    # בעוד הגרעין אומר "מחכה לאישור שלכם" אינו מודל תקף, ולכן אלה שגיאות
    # המעמד נגזר מהתאים של רשומת האישור האחרונה (approval_records), כמו בשער המדיניות. בלעדיהם כל פלייבוק
    # שעמדה אחת בו אושרה, בגיליון או בצ'אט, נמדד כ-Draft, והמאמת דיווח סתירה על מודל עקבי
    try:
        from playbook import status as S
        cells = S.record_cells_for(data, model_path) if data.get("approval_records") else None
        drift = check_consistency(data, core, index_entry,
                                  cells=cells, word_path=word, workspace_path=None)
        if word and not workspace:
            drift.append("Workspace: לא נמסרה סביבת עבודה לצד ה-Word. פלייבוק נמסר תמיד בשני התוצרים, יחד")
        if workspace:
            drift += workspace_file_problems(workspace)
            from playbook import market_counts as MC
            drift += workspace_findings(S.derive_status(data, cells), workspace, data, S, MC)
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
    ap.add_argument("--inventory", help="clause-inventory.json; default: coverage.inventory_ref, or the file "
                                        "beside the model")
    ap.add_argument("--extract", help="corpus-extract.json; default: coverage.extract_ref, or "
                                      "Areo-נתונים/corpus-extract.json")
    ap.add_argument("--coverage-out", help="writes the coverage block computed from the inventory (and the "
                                           "extract) to this path, for the builder to copy into the model")
    ap.add_argument("--inventory-skeleton", help="writes the clause-unit skeleton built from the extract (one "
                                                 "unit per clause, no mapping) to this path, and exits")
    ap.add_argument("--approved-sources", help="מקורות-מאושרים.json saved to disk: legal and regulatory source URLs "
                                               "are checked against it (default: AREO_APPROVED_SOURCES, else the "
                                               "copy bundled in the plugin, lib/מקורות-מאושרים.json)")
    a = ap.parse_args()
    if a.approved_sources:
        if not os.path.isfile(a.approved_sources):
            print("INVALID")
            print("- the approved-sources file does not exist: %s" % a.approved_sources)
            raise SystemExit(2)
        # risk.validate_register.approved_domains קורא את משתנה הסביבה (playbook/validate_model.source_findings)
        os.environ["AREO_APPROVED_SOURCES"] = a.approved_sources
    if a.word:
        # Word פגום, DOC או Strict: הודעה דו-לשונית וקוד 2, ולא "the cross-layer status check raised BadZipFile"
        try:
            import areo_lib  # noqa: F401
            from common.cli import load_docx_or_explain
        except ImportError:
            load_docx_or_explain = None
        if load_docx_or_explain:
            ok, msg, code = load_docx_or_explain(a.word, loader=False)
            if ok is None:
                print("INVALID")
                print(msg)
                raise SystemExit(code)
    raise SystemExit(main(a.model,
                          core=_load(a.core, "the core") if a.core else None,
                          index_entry=_load(a.index, "the index entry") if a.index else None,
                          word=a.word, workspace=a.workspace,
                          inventory=_load(a.inventory, "the clause inventory") if a.inventory else None,
                          extract=_load(a.extract, "the corpus extract") if a.extract else None,
                          coverage_out=a.coverage_out, skeleton_out=a.inventory_skeleton,
                          inputs=[a.core, a.index, a.word, a.workspace, a.inventory, a.extract]))
