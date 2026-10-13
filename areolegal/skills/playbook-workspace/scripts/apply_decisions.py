# -*- coding: utf-8 -*-
"""קולט את קובץ ההחלטות שיוצא מאשף ההערות, וכותב אותו למודל הפלייבוק.

**זה המסלול היחיד שבו הכרעה של הלקוח נכנסת למודל ולגרעין.** האשף
(`wizard_spec.md`) הוא המקום שבו הלקוח מאשר סעיף, מציע נוסח או מעיר, ובסופו
הוא מוריד קובץ החלטות ומעלה אותו לשיחה.

**סביבת העבודה אינה מכריעה.** אין בה כפתורי אישור, והערה או הצעת נוסח שנכתבו
בה נשמרות בקובץ הערות נפרד ואינן נכנסות לכאן (`dashboard_spec.md`, "הערות
והצעות: איפה הן חיות"). קובץ הערות שיגיע לכאן נדחה, כדי שהצעה לא תיכנס
למדיניות בטעות.

ההכרעה היא מסר בדרך, ולא מקור אמת: מקור האמת הוא `playbook-model.json`
ו-`playbook-core.json` שבתיקייה המשותפת. הסקריפט הזה סוגר את הלולאה, ואחריו
סביבת העבודה נבנית מחדש מהמודל ומתפרסמת לאותו קישור.

שימוש:
  python3 apply_decisions.py --decisions playbook-decisions.json \\
      --model playbook-model.json [--core playbook-core.json] \\
      [--by "שם המכריע"] [--dry-run] [--force]

מה הוא עושה:
  1. מאמת שהקובץ שייך לפלייבוק הזה, ושלא נקלט כבר.
  2. כותב לכל סעיף את ההכרעה: אושר, אושר עם שינוי, לא אושר.
  3. מחיל עריכות נוסח על מסלול הרמזור, ושומר את הנוסח הקודם ביומן.
  4. מוסיף רשומה ליומן ההחלטות שבמודל, עם מי, מתי, ומה השתנה.
  5. מסנכרן את ההכרעה והנוסח לגרעין ההפעלה.

מה הוא אינו עושה: אינו ממציא הכרעה, אינו מכריע סעיף שלא הוכרע, ואינו מוחק
ראיות. סעיף שנוסחו במודל השתנה מאז ההכרעה מסומן כטעון בדיקה ואינו מוחל בשקט.
"""
import argparse, io, json, os, shutil, sys
from datetime import datetime, timezone

STATUS = {"accept": "approved", "edit": "approved_with_change", "reject": "rejected"}
HE = {"approved": "אושר", "approved_with_change": "אושר עם שינוי", "rejected": "לא אושר"}
REVERSE = {v: k for k, v in STATUS.items()}
FIELDS = {"pos": "position", "crit": "match_criteria", "clause": "proposed_clause",
          "comments": "comments"}
COLORS = ("green", "yellow", "red")


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load(path, what):
    if not os.path.exists(path):
        sys.exit("שגיאה: %s לא נמצא בנתיב %s" % (what, path))
    try:
        return json.load(io.open(path, encoding="utf-8"))
    except ValueError as exc:
        sys.exit("שגיאה: %s אינו JSON תקין (%s)" % (what, exc))


def write(path, data):
    if os.path.exists(path):
        shutil.copyfile(path, path + ".bak")
    with io.open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def from_db(raw):
    """קלט מהמאגר של ה-Artifact: מסמך לכל סעיף, כפי שהדף כתב אותו.

    [{"id": "R-02", "data": {"status": "approved_with_change", "note": "",
      "wording": {"green": {"clause": "..."}}, "by": "", "at": "", "applied": false}}]

    מומר לאותו מבנה שמגיע מייצוא הדפדפן, כדי שהקליטה תהיה זהה בשני המסלולים.
    """
    docs = raw.get("documents") or raw.get("docs") or raw
    if isinstance(docs, dict):
        docs = [{"id": k, "data": v} for k, v in docs.items()]
    picks, notes, edits, whos, ats = {}, {}, {}, {}, []
    for doc in docs:
        rid = doc.get("id") or (doc.get("data") or {}).get("rule_id")
        d = doc.get("data") or {}
        if not rid or d.get("applied"):          # כבר בתוך המדיניות
            continue
        status = d.get("status")
        if status in STATUS:                      # הדף עשוי לכתוב accept/edit/reject
            status = STATUS[status]
        if status not in HE:
            continue
        picks[rid] = REVERSE[status]
        if d.get("note"):
            notes[rid] = d["note"]
        if d.get("wording"):
            edits[rid] = d["wording"]
        if d.get("by"):
            whos[rid] = d["by"]
        if d.get("at"):
            ats.append(d["at"])
    return {"playbook": raw.get("playbook") or {}, "decisions": picks, "notes": notes,
            "ruleEdits": edits, "by_rule": whos,
            "exported": raw.get("read_at") or (max(ats) if ats else "")}


def from_wizard(raw):
    """קלט מאשף ההערות: רשומה לכל סעיף שהלקוח נגע בו.

    {"kind": "areo-playbook-notes", "entries": [
      {"rule_id": "R-02", "type": "approve|suggestion|comment", "track": "yellow",
       "text": "...", "current_text": "...", "clause_hash": "h1f2", "by": "...", "at": "..."}]}

    שלוש הפעולות של האשף: אישור הסעיף, הצעת נוסח חדש, והערה. הן מומרות
    למבנה שהקליטה מכירה, כדי שהמסלול יישאר אחד.
    """
    picks, notes, edits, whos, ats, seen = {}, {}, {}, {}, [], {}
    for e in raw.get("entries") or []:
        rid, kind = e.get("rule_id"), e.get("type")
        if not rid or not kind:
            continue
        if e.get("by"):
            whos[rid] = e["by"]
        if e.get("at"):
            ats.append(e["at"])
        if kind == "approve":
            picks[rid] = "accept"
        elif kind == "suggestion":
            picks[rid] = "edit"
            track = e.get("track") or "green"
            edits.setdefault(rid, {})[track] = {"clause": e.get("text") or ""}
            if e.get("clause_hash"):
                seen.setdefault(rid, {})[track] = e["clause_hash"]
        elif kind == "comment":
            notes[rid] = e.get("text") or ""
        if e.get("text") and kind == "approve":
            notes[rid] = e["text"]
    return {"playbook": raw.get("playbook") or {}, "decisions": picks, "notes": notes,
            "ruleEdits": edits, "by_rule": whos, "seen_hash": seen,
            "exported": raw.get("created") or (max(ats) if ats else "")}


def wiz_hash(text):
    """אותו גיבוב שהאשף מחשב על הנוסח שהוצג (hash() שבתבנית האשף)."""
    h = 0
    for ch in str(text or ""):
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
        if h >= 0x80000000:
            h -= 0x100000000
    return "h%x" % (h & 0xFFFFFFFF)


def rules_of(model):
    return model.get("rules") or []


def rule_id(rule):
    return rule.get("rule_id") or rule.get("id") or ""


def tl_of(rule):
    return rule.get("traffic_light") or rule.get("tl") or {}


def as_list(value):
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    return [x.strip() for x in str(value).split("\n") if x.strip()]


def check_batch(model, dec, force):
    """קובץ החלטות נקלט פעם אחת. חוזר על עצמו: עצירה, אלא אם ביקשו במפורש."""
    stamp = dec.get("exported") or ""
    done = model.setdefault("applied_decision_batches", [])
    if stamp and any(b.get("exported") == stamp for b in done):
        if not force:
            sys.exit("הקובץ הזה כבר נקלט ב-%s. אין מה לקלוט שוב. "
                     "לקליטה חוזרת מכוונת הוסף --force."
                     % next(b.get("applied_at", "") for b in done
                            if b.get("exported") == stamp))
        print("אזהרה: הקובץ כבר נקלט בעבר, נקלט שוב לבקשתך.")
    return stamp, done


def check_kind(dec):
    """קובץ הערות של סביבת העבודה אינו קובץ החלטות, ואינו נקלט."""
    kind = dec.get("kind")
    if kind == "comments_and_proposals":
        sys.exit("שגיאה: זה קובץ הערות והצעות מסביבת העבודה, ולא קובץ החלטות של "
                 "האשף. הערה והצעת נוסח אינן מדיניות, ולכן אינן נכתבות לפלייבוק. "
                 "כדי לאמץ הצעה, העבירו אותה באשף או בשיחה.")
    if kind and kind not in ("areo-playbook-notes", "decisions"):
        sys.exit("שגיאה: סוג הקובץ %r אינו מוכר. נדרש קובץ ההחלטות של האשף "
                 "(kind: areo-playbook-notes)." % kind)


def check_playbook(model, dec):
    """הקובץ נושא את מזהה הפלייבוק מאז גרסת התבנית שמוסיפה אותו. בלעדיו, אזהרה."""
    check_kind(dec)
    src = dec.get("playbook") or {}
    pid, mid = src.get("id"), model.get("playbook_id")
    if not pid:
        return ["קובץ ההחלטות אינו נושא מזהה פלייבוק. ודא שהוא הופק מסביבת העבודה "
                "של הפלייבוק הזה ולא מאחר."]
    if mid and pid != mid:
        sys.exit("שגיאה: הקובץ שייך לפלייבוק %s, והמודל הוא %s. אין לקלוט בין פלייבוקים."
                 % (pid, mid))
    warn = []
    seen, cur = src.get("model_updated"), model.get("last_updated")
    if seen and cur and seen != cur:
        warn.append("המודל עודכן מאז שההחלטות התקבלו (%s מול %s). כל סעיף שנוסחו "
                    "השתנה מאז מסומן כטעון בדיקה ואינו מוחל." % (seen, cur))
    return warn


def apply_edits(rule, edits, log_entry):
    """מחיל עריכת נוסח, ושומר את הקודם. מחזיר את מספר השדות ששונו."""
    tl, changed = tl_of(rule), 0
    for color in COLORS:
        fields = (edits or {}).get(color) or {}
        light = tl.get(color)
        if not isinstance(light, dict):
            continue
        for short, name in FIELDS.items():
            if short not in fields:
                continue
            new = as_list(fields[short]) if short == "crit" else str(fields[short])
            old = light.get(name)
            if old == new:
                continue
            light[name] = new
            light["edited_by_user"] = True
            log_entry.setdefault("wording_changes", []).append(
                {"track": color, "field": name, "from": old, "to": new})
            changed += 1
    return changed


def sync_core(core, decisions_by_id, model_by_id):
    """הגרעין נגזר מהמודל, ולכן מקבל את אותה הכרעה ואת הנוסח המעודכן."""
    touched = 0
    for clause in core.get("clauses") or []:
        cid = clause.get("id")
        dec = decisions_by_id.get(cid)
        if not dec:
            continue
        clause["decision"] = dec
        rule = model_by_id.get(cid)
        if rule:
            tl = tl_of(rule)
            for key, color in (("preferred_wording", "green"),
                               ("fallback_wording", "yellow"),
                               ("red_line", "red")):
                light = tl.get(color) or {}
                if light.get("edited_by_user") and light.get("proposed_clause"):
                    clause[key] = light["proposed_clause"]
        touched += 1
    return touched


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--decisions", required=True)
    ap.add_argument("--from-db", action="store_true",
                    help="הקובץ הוא קריאה ממאגר ה-Artifact ולא ייצוא מהדפדפן")
    ap.add_argument("--model", required=True)
    ap.add_argument("--core")
    ap.add_argument("--by", default="")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    dec = load(a.decisions, "קובץ ההחלטות")
    check_kind(dec)
    if a.from_db:
        dec = from_db(dec)
        if not dec["decisions"]:
            sys.exit("במאגר אין הכרעה שטרם נקלטה. אין מה לקלוט.")
    elif dec.get("kind") == "areo-playbook-notes" or "entries" in dec:
        # הקובץ של האשף, שזה המסלול הרגיל
        dec = from_wizard(dec)
        if not dec["decisions"] and not dec["notes"]:
            sys.exit("בקובץ האשף אין אישור, הצעה או הערה. אין מה לקלוט.")
    model = load(a.model, "מודל הפלייבוק")
    warnings = check_playbook(model, dec)
    stamp, batches = check_batch(model, dec, a.force)

    by_id = {rule_id(r): r for r in rules_of(model) if rule_id(r)}
    picks = dec.get("decisions") or {}
    notes = dec.get("notes") or {}
    edits = dec.get("ruleEdits") or {}
    if not picks:
        sys.exit("בקובץ אין אף הכרעה. אין מה לקלוט.")

    log, applied, unknown, counts = [], {}, [], {}
    for rid, pick in sorted(picks.items()):
        status = STATUS.get(pick)
        if not status:
            unknown.append("%s: ערך הכרעה לא מוכר (%s)" % (rid, pick))
            continue
        rule = by_id.get(rid)
        if rule is None:
            unknown.append("%s: אין סעיף כזה במודל" % rid)
            continue
        entry = {"rule_id": rid, "topic": rule.get("topic_name", ""), "status": status,
                 "status_he": HE[status], "note": notes.get(rid, ""),
                 "decided_at": stamp, "applied_at": now(),
                 "by": (dec.get("by_rule") or {}).get(rid) or a.by,
                 "source": os.path.basename(a.decisions)}
        stale = []
        for color, want in ((dec.get("seen_hash") or {}).get(rid) or {}).items():
            light = (tl_of(rule) or {}).get(color) or {}
            cur = light.get("proposed_clause")
            cur = cur.get("he") if isinstance(cur, dict) else cur
            if want and wiz_hash(cur) != want:
                stale.append(color)
        if stale:
            he = {"green": "בירוק", "yellow": "בצהוב", "red": "באדום"}
            entry["review_required"] = ("הנוסח %s השתנה במודל מאז שהלקוח ראה אותו, "
                                        "ולכן ההצעה לא הוחלה. יש להשוות ולהכריע."
                                        % " ו".join(he.get(c, c) for c in stale))
            for color in stale:
                (edits.get(rid) or {}).pop(color, None)
        changed = apply_edits(rule, edits.get(rid), entry)
        if (status == "approved_with_change" and not changed and not notes.get(rid)
                and not entry.get("review_required")):
            entry["review_required"] = ("סומן אושר עם שינוי, אך לא נמצא נוסח חדש "
                                        "ולא הערה. הנוסח נשאר כפי שהיה.")
        rule["decision"] = {k: entry[k] for k in
                            ("status", "status_he", "note", "decided_at", "applied_at", "by")}
        log.append(entry)
        applied[rid] = rule["decision"]
        counts[status] = counts.get(status, 0) + 1

    for line in warnings:
        print("אזהרה: " + line)
    for line in unknown:
        print("לא נקלט, " + line)

    summary = "  ".join("%s: %d" % (HE[k], counts[k]) for k in sorted(counts))
    print("נקלטו %d הכרעות מתוך %d בקובץ.  %s" % (len(log), len(picks), summary))
    edited = sum(len(e.get("wording_changes", [])) for e in log)
    if edited:
        print("שינויי נוסח שהוחלו: %d. הנוסח הקודם נשמר ביומן ההחלטות." % edited)
    for e in log:
        if e.get("review_required"):
            print("טעון בדיקה, %s: %s" % (e["rule_id"], e["review_required"]))

    if a.dry_run:
        print("ריצת יובש. לא נכתב דבר.")
        return

    model.setdefault("decision_log", []).extend(log)
    batches.append({"exported": stamp, "applied_at": now(), "count": len(log),
                    "source": os.path.basename(a.decisions), "by": a.by})
    model["last_updated"] = now()[:10]
    write(a.model, model)
    print("נכתב %s (גיבוי ב-%s.bak)" % (a.model, a.model))

    if a.core:
        core = load(a.core, "גרעין ההפעלה")
        touched = sync_core(core, applied, by_id)
        core["source_model_updated"] = model["last_updated"]
        core["generated_at"] = now()[:10]
        write(a.core, core)
        print("סונכרנו %d סעיפים בגרעין ההפעלה." % touched)
    else:
        print("הגרעין לא סונכרן. הרץ שוב עם --core, או בנה אותו מחדש מהמודל.")

    ack = os.path.join(os.path.dirname(os.path.abspath(a.decisions)) or ".",
                       "decisions-applied.json")
    write(ack, {"applied_at": now(), "by": a.by, "playbook_id": model.get("playbook_id", ""),
                "rules": sorted(applied),
                "note": "סמן את המסמכים האלה במאגר כ-applied:true, כדי שלא ייקלטו שוב "
                        "וכדי שהדף יציג אותם כמי שנכנסו למדיניות."})
    print("רשימת הסעיפים לסימון במאגר נכתבה ל-%s" % ack)
    print("הצעד הבא: בנה מחדש את סביבת העבודה מהמודל ופרסם לאותו קישור, "
          "כדי שכל המשתמשים המשותפים יראו את הפלייבוק המעודכן.")


if __name__ == "__main__":
    main()
