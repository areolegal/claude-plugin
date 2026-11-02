# -*- coding: utf-8 -*-
"""שלושה מצבים לכל סיכון, קשורים לגרסאות מסמך: נוכחי, מוצע, מוסכם.

* נוכחי (current): מה שהנוסח שבתוקף או שהתקבל אחרון אומר. הדרגה נגזרת ממנו.
* מוצע (proposed): בקרה שהוצעה או נשלחה במרקאפ ועוד לא התקבלה. אינה מורידה את הדרגה.
* מוסכם (agreed): הצד שכנגד קיבל, עם ראיית קבלה (הגרסה או הסבב שהתקבלו). גם אז נבדקת
  האפקטיביות, והדרגה נקבעת לפי ההערכה, ולא יורדת אוטומטית.

מרשם בלי הבלוק `states` נקרא כמו שהיה ונחשב "נוכחי" בלבד (תאימות לאחור).
המודול אינו תלוי בספרייה המשותפת, ומשמש את בונה הדוח, את הבודק ואת הבדיקות.
"""
import copy

EFFECTIVENESS = ("effective", "partial", "not_effective")
PROPOSAL_STATUS = ("pending", "sent", "rejected")
STATE_LABEL = {"current": "נוכחי", "proposed": "בקרה מוצעת", "agreed": "מוסכם"}
STATE_LABEL_EN = {"current": "Current", "proposed": "Proposed control", "agreed": "Agreed"}


def lvl(score):
    """אותם ספים כמו בבודק המשותף: 16, 9 ו-4."""
    return "critical" if score >= 16 else "high" if score >= 9 else "medium" if score >= 4 else "low"


def _score(block):
    s = (block or {}).get("score")
    return s if isinstance(s, (int, float)) and not isinstance(s, bool) else None


def has_states(r):
    return isinstance(r.get("states"), dict)


def risk_state(r):
    """current | proposed | agreed. בלי בלוק states: current."""
    st = r.get("states") if has_states(r) else None
    if not st:
        return "current"
    if st.get("agreed"):
        return "agreed"
    if [p for p in st.get("proposed") or [] if p.get("status") in ("pending", "sent")]:
        return "proposed"
    return "current"


def current_score(r):
    """הציון של המצב הנוכחי: states.current.score, ובהיעדרו הגולמי (inherent)."""
    st = r.get("states") or {}
    s = _score(st.get("current"))
    return s if s is not None else _score(r.get("inherent"))


def effective_score(r):
    """הציון שמכתיב את הדרגה. מרשם ישן: שיורי, ובהיעדרו הגולמי (כמו קודם).
    מרשם עם states: מוסכם (עם ראיית קבלה) או נוכחי. מוצע אינו נספר."""
    if not has_states(r):
        s = _score(r.get("residual"))
        return s if s is not None else _score(r.get("inherent"))
    ag = (r["states"].get("agreed") or {})
    if ag and _score(ag) is not None and ag.get("acceptance_evidence") and ag.get("effectiveness") in EFFECTIVENESS:
        return _score(ag)
    return current_score(r)


def derive_levels(data):
    """כותב severity_level ו-exposure_state לכל סיכון עם states. סיכון ישן נשאר כמות שהוא."""
    for r in data.get("risks") or []:
        if not has_states(r):
            continue
        s = effective_score(r)
        if s is not None:
            r["severity_level"] = lvl(s)
        r["exposure_state"] = risk_state(r)
    return data


def state_counts(data):
    c = {"current": 0, "proposed": 0, "agreed": 0}
    for r in data.get("risks") or []:
        c[risk_state(r)] += 1
    return c


def identity(r):
    """זהות סיכון: אירוע, השפעה ובקרה. סעיף אחד יכול לשאת כמה סיכונים."""
    n = lambda k: " ".join(str(r.get(k) or "").split()).strip().lower()
    return (n("event"), n("impact"), n("control_ref"))


def check(data):
    """(errors, warnings) לכללי שלושת המצבים. מרשם ישן: אזהרה בלבד כשיש בקרה מוצעת שמורידה את הדרגה."""
    errors, warnings = [], []
    seen = {}
    for r in data.get("risks") or []:
        rid = r.get("id") or r.get("risk_no")
        if r.get("event") or r.get("impact"):
            if not (r.get("event") and r.get("impact")):
                errors.append("%s: צריך גם event וגם impact" % rid)
            key = identity(r)
            if key in seen:
                errors.append("%s: אותו אירוע, השפעה ובקרה כמו %s; אלה סיכון אחד" % (rid, seen[key]))
            seen[key] = rid
        if not has_states(r):
            if any((c or {}).get("basis") == "proposed_text" for c in r.get("controls") or []):
                warnings.append("%s: בקרה מוצעת במרשם בלי states נחשבת נוכחית; יש להעביר ל-states.proposed" % rid)
            continue
        st = r["states"]
        cur = st.get("current")
        if not isinstance(cur, dict) or _score(cur) is None or not cur.get("version"):
            errors.append("%s: states.current דורש version ו-score" % rid)
        for c in r.get("controls") or []:
            if (c or {}).get("basis") == "proposed_text":
                errors.append("%s: בקרה מוצעת נרשמת ב-states.proposed ולא ב-controls עם proposed_text" % rid)
        ids = set()
        for p in st.get("proposed") or []:
            if not p.get("id") or p["id"] in ids:
                errors.append("%s: לכל הצעה מזהה ייחודי" % rid)
            ids.add(p.get("id"))
            if p.get("status") not in PROPOSAL_STATUS:
                errors.append("%s: סטטוס הצעה חייב להיות אחד מ-%s (קבלה נרשמת ב-agreed)" % (rid, "/".join(PROPOSAL_STATUS)))
            if not p.get("control") or not p.get("markup_version"):
                errors.append("%s: הצעה דורשת control ו-markup_version" % rid)
        ag = st.get("agreed")
        cs = current_score(r)
        if ag:
            if not ag.get("accepted_version") or not ag.get("acceptance_evidence"):
                errors.append("%s: מצב מוסכם דורש accepted_version ו-acceptance_evidence" % rid)
            if ag.get("effectiveness") not in EFFECTIVENESS:
                errors.append("%s: מצב מוסכם דורש effectiveness (%s)" % (rid, "/".join(EFFECTIVENESS)))
            if _score(ag) is None:
                errors.append("%s: מצב מוסכם דורש score שהוערך" % rid)
            elif ag.get("effectiveness") == "not_effective" and cs is not None and _score(ag) < cs:
                errors.append("%s: בקרה לא אפקטיבית אינה מורידה את הציון" % rid)
            if ag.get("proposal_id") and ag["proposal_id"] not in ids:
                errors.append("%s: proposal_id אינו מפנה להצעה" % rid)
        # הציון בשיורי חייב להיות הציון שבתוקף, לא המוצע
        res = _score(r.get("residual"))
        eff = effective_score(r)
        if res is not None and eff is not None and res != eff:
            errors.append("%s: residual.score (%s) שונה מהציון שבתוקף (%s); בקרה מוצעת אינה מורידה" % (rid, res, eff))
    return errors, warnings


def apply_acceptance(data, accepted_version, evidence_by_risk):
    """מעביר למוסכם רק את הסיכונים שב-evidence_by_risk (קבלה חלקית משנה רק אותם).
    evidence_by_risk: {risk_id: {proposal_id, acceptance_evidence, effectiveness, score, effectiveness_note}}.
    מחזיר עותק; הקלט לא משתנה."""
    out = copy.deepcopy(data)
    for r in out.get("risks") or []:
        ev = evidence_by_risk.get(r.get("id"))
        if not ev or not has_states(r):
            continue
        r["states"]["agreed"] = {
            "accepted_version": accepted_version,
            "acceptance_evidence": ev.get("acceptance_evidence"),
            "proposal_id": ev.get("proposal_id"),
            "effectiveness": ev.get("effectiveness"),
            "effectiveness_note": ev.get("effectiveness_note"),
            "score": ev.get("score"),
        }
        if r.get("residual") is not None and ev.get("score") is not None:
            r["residual"]["score"] = ev["score"]
    return out
