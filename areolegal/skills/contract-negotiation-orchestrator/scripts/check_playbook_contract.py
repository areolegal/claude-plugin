#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""חוזה הנתונים: האם הנושא ונותן יכול לעבוד עם הפלייבוק הזה.

`playbook-qa.md`, בדיקה 2: `check_playbook_contract.py <model> --core
<core>` של רכיב המשא ומתן, **אפס שגיאות. זהו חוזה הנתונים עם הרכיבים
שקוראים את הפלייבוק.**

הבדיקה הזאת אינה אימות הסכמה מחדש. את הסכמה מאמת
`contract-playbook-builder/scripts/validate_playbook_model.py`, וזה הצד
של הכותב. כאן נבדק **הצד של הקורא**: בכל שדה שהנושא ונותן באמת שולף
מהפלייבוק בזמן ההכרעה, ובאוצר המילים שהוא מצפה לו. פלייבוק שעובר את
הסכמה ואינו עובר כאן הוא פלייבוק שהבונה כתב והנושא ונותן אינו יכול
להחיל, וזה מתגלה בעסקה אמיתית, באמצע סבב.

מה נבדק, ולפי מה:

| מה | מאיפה בתוכן |
|---|---|
| `round1_posture` הוא `hold_green` או `offer_yellow` | `decision_matrix.md`, "round1_posture: מה מציעים בסבב הראשון" |
| שלושת המסלולים קיימים, ולירוק ולצהוב יש נוסח | `phase2_redlining.md`, שלב ג: "שלוף מהפלייבוק" |
| `fallback_wording` ו-`fallback_source` אינם ריקים | `playbook-core-schema.md` |
| `policy_ref` קיים בכל כלל | `external_comments_guide.md`: מספר הכלל נכנס לבועה |
| `company_role_code` ו-`family_code` קיימים | `overview.md`, שלב א.3: ההתאמה לפי משפחה וצד |
| `status_label` ו-`playbook_status` קיימים וזהים בגרעין | `overview.md`: המעמד מוצג כפי שהשער מחזיר |
| `schema_version`, `core_version`, `produced_with` | `overview.md`: אזהרה על פלייבוק מגרסה קודמת |
| הגרעין והמודל אומרים אותו דבר בכל כלל | `playbook-core-schema.md`, "אימות" |

`round1_posture` **חסר אינו שגיאה**: `decision_matrix.md` אומר שאז
מחזיקים בירוק ומציינים זאת בסיכום הפנימי. ערך שאינו אחד מהשניים הוא
שגיאה, כי אין לו התנהגות מוגדרת.

    python3 scripts/check_playbook_contract.py <playbook-model.json> \\
        --core <playbook-core.json> [--min-skill-version 3.2]

קוד יציאה: **0** החוזה מתקיים, **3** אינו מתקיים, **2** קלט חסר.
"""
import argparse
import json
import sys
from pathlib import Path

POSTURES = ("hold_green", "offer_yellow")
TRACKS = ("green", "yellow", "red")
WORDED = ("green", "yellow")          # לאדום יש נוסח ריפוי, ולא נוסח להחלה
TOP = ("schema_version", "core_version", "family_id", "produced_with")
MATCH = ("company_role_code", "family_code")
STATUS = ("status_label", "playbook_status")


def nonempty(v):
    return bool(v) and (not isinstance(v, str) or bool(v.strip()))


def wording_of(cell):
    """הנוסח שיוחל, בכל אחת מהצורות שהבונה כותב בהן."""
    # proposed_clause ו-fallback_wording הם השדות של playbook-schema.md; בלעדיהם כל מודל לפי הסכמה נכשל כאן
    for key in ("wording", "preferred_wording", "proposed_clause", "fallback_wording", "text", "clause_text",
                "wording_he"):
        v = cell.get(key)
        if isinstance(v, dict):
            v = v.get("he") or v.get("en")
        if nonempty(v):
            return v
    return None


def rule_findings(rule, core_rule):
    out = []
    rid = rule.get("rule_id") or "(כלל בלי מזהה)"

    def say(msg):
        out.append("%s: %s" % (rid, msg))

    if not nonempty(rule.get("rule_id")):
        out.append("כלל בלי rule_id: אין לו שם בשום הכרעה ובשום קובץ מצב")
    # playbook-schema.md מגדיר topic_name ואת rule_id, ולא topic ו-policy_ref. בלי הקריאה הזו כל מודל
    # שנבנה לפי הסכמה נכשל בחוזה (הרצה חיה, 20.10.2026). מספר הכלל בבועה הוא rule_id כשאין policy_ref
    if not (nonempty(rule.get("topic")) or nonempty(rule.get("topic_name"))):
        say("אין topic_name. הנושא הוא מה שמוצג ללקוחה ומה שנרשם בקובץ המצב")
    if not nonempty(rule.get("importance")):
        say("אין importance. הדרגה בפקטור 1 נשענת עליה")
    if not (nonempty(rule.get("policy_ref")) or nonempty(rule.get("rule_id"))):
        say("אין policy_ref. מספר הכלל נכנס לבועה החיצונית")

    posture = _val(rule, core_rule, "round1_posture")
    if posture is not None and posture not in POSTURES:
        say('round1_posture="%s", ומותר %s. חסר מותר, ואז מחזיקים בירוק'
            % (posture, " או ".join(POSTURES)))

    tl = rule.get("traffic_light") or {}
    if not isinstance(tl, dict):
        say("traffic_light אינו אובייקט")
        return out
    for track in TRACKS:
        cell = tl.get(track)
        if not isinstance(cell, dict):
            say("אין מסלול %s. שלושת המסלולים נשלפים בכל הכרעה" % track)
            continue
        if not nonempty(cell.get("position")):
            say("%s: אין position. זו העמדה שמוצגת" % track)
        if track in WORDED and not wording_of(cell):
            say("%s: אין נוסח להחלה. הנושא ונותן מכניס נוסח לגוף ההסכם, "
                "ולא תקציר" % track)
    for field in ("fallback_wording", "fallback_source"):
        if not nonempty(_val(rule, core_rule, field)):
            say("אין %s. הנסיגה היא מה שמוצע כשהירוק נדחה" % field)
    for seg in (rule.get("segment_overrides") or ()):
        if isinstance(seg, dict):
            for field in ("fallback_wording", "fallback_source"):
                if field in seg and not nonempty(seg.get(field)):
                    say("segment_overrides: %s ריק" % field)
    return out


def _val(rule, core_rule, field):
    """הערך כפי שהקורא רואה אותו: מהמודל, ואחרת מהגרעין."""
    if field in rule:
        return rule.get(field)
    return (core_rule or {}).get(field)


def core_rules_by_id(core):
    out = {}
    for key in ("clauses", "rules"):
        for c in (core or {}).get(key) or ():
            if isinstance(c, dict):
                rid = c.get("rule_id") or c.get("id")
                if rid:
                    out[rid] = c
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("model", help="playbook-model.json")
    ap.add_argument("--core", help="playbook-core.json")
    ap.add_argument("--min-skill-version",
                    help="גרסת בונה מינימלית. פלייבוק שנבנה לפניה מדווח כישן")
    a = ap.parse_args(argv)

    try:
        model = json.loads(Path(a.model).read_text(encoding="utf-8"))
    except Exception as exc:
        print("cannot read the model (%s): %s" % (a.model, exc))
        return 2
    core = None
    if a.core:
        try:
            core = json.loads(Path(a.core).read_text(encoding="utf-8"))
        except Exception as exc:
            print("cannot read the core (%s): %s" % (a.core, exc))
            return 2

    errors, notes = [], []
    for field in TOP:
        if not nonempty(model.get(field)):
            errors.append("אין %s במודל" % field)
    fams = [f for f in ((model.get("scope_summary") or {}).get("contract_families") or ()) if isinstance(f, dict)]
    derived = {"company_role_code": next((f.get("company_role_code") for f in fams if f.get("company_role_code")), None),
               "family_code": model.get("family_id")}
    for field in MATCH:
        if not nonempty(model.get(field)) and not nonempty((core or {}).get(field)) \
                and not nonempty(derived.get(field)):
            errors.append("אין %s במודל ולא בגרעין. בלעדיו האיתור אינו מתאים "
                          "את הפלייבוק למשפחה ולצד" % field)
    for field in STATUS:
        if not nonempty(model.get(field)):
            errors.append("אין %s במודל. המעמד מוצג כפי שהוא, ואינו מנוסח מחדש" % field)
        elif core is not None and field in core and core.get(field) != model.get(field):
            errors.append('%s בגרעין "%s" ובמודל "%s". הקורא אינו יודע במי להאמין'
                          % (field, core.get(field), model.get(field)))
    if "presentation_label" in json.dumps(model, ensure_ascii=False):
        errors.append("presentation_label במודל. התווית היחידה היא status_label")

    rules = model.get("rules")
    if not isinstance(rules, list) or not rules:
        errors.append("אין rules[] במודל: אין ממה להכריע")
        rules = []
    cby = core_rules_by_id(core)
    for rule in rules:
        if isinstance(rule, dict):
            errors += rule_findings(rule, cby.get(rule.get("rule_id")))
        else:
            errors.append("כלל שאינו אובייקט ב-rules[]")

    if core is not None and cby:
        model_ids = {r.get("rule_id") for r in rules if isinstance(r, dict)}
        for rid in sorted(set(cby) - model_ids):
            errors.append("%s: בגרעין ואינו במודל" % rid)
        for rid in sorted(model_ids - set(cby)):
            if rid:
                notes.append("%s: במודל ואינו בגרעין" % rid)

    if a.min_skill_version:
        built = str((model.get("produced_with") or {}).get("skill_version") or "")
        if built and _older(built, a.min_skill_version):
            notes.append("הפלייבוק נבנה בגרסת בונה %s, והמינימום הוא %s. "
                         "אמור זאת ללקוחה ואל תוריד בשקט"
                         % (built, a.min_skill_version))

    missing_posture = [r.get("rule_id") for r in rules
                       if isinstance(r, dict)
                       and _val(r, cby.get(r.get("rule_id")), "round1_posture") is None]
    if missing_posture:
        notes.append("אין round1_posture ל-%d כללים (%s). מחזיקים בירוק, ונאמר "
                     "בסיכום הפנימי" % (len(missing_posture),
                                        ", ".join(str(x) for x in missing_posture[:6])))

    if errors:
        print("CONTRACT NOT MET")
        for e in errors:
            print("-", e)
        for n in notes:
            print("! note:", n)
        print("%d errors" % len(errors))
        return 3
    print("CONTRACT MET")
    for n in notes:
        print("! note:", n)
    return 0


def _older(a, b):
    def parts(v):
        return [int(x) if x.isdigit() else 0 for x in str(v).split(".")]
    pa, pb = parts(a), parts(b)
    pa += [0] * (len(pb) - len(pa))
    pb += [0] * (len(pa) - len(pb))
    return pa < pb


if __name__ == "__main__":
    sys.exit(main())
