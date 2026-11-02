# -*- coding: utf-8 -*-
"""קולט את קובץ ההחלטות שיוצא מאשף ההערות, וכותב אותו למודל הפלייבוק.

**זה המסלול היחיד שבו הכרעה של הלקוח נכנסת למודל ולגרעין.** האשף
(`wizard_spec.md`) הוא המקום שבו הלקוח מאשר סעיף, מציע נוסח או מעיר, ובסופו
הוא מוריד קובץ החלטות ומעלה אותו לשיחה.

**סביבת העבודה אינה מכריעה ואינה כותבת הערות.** אין בה כפתורי אישור ואין בה
תיבת הערה: הערות, אישורים והצעות נוסח נכתבים רק באשף (`dashboard_spec.md`, "הערות
והצעות: איפה הן חיות"). קובץ "comments_and_proposals" ישן מסביבת העבודה, שיגיע
לכאן, נדחה עם הסבר, כדי שהצעה לא תיכנס למדיניות בטעות.

קובץ האשף נקרא `<slug>-<שם הממלא>-<תאריך>-notes.json` (או `<slug>-notes.json`
מגרסה קודמת). שם הקובץ אינו נבדק: הסוג נקבע לפי `kind`.

ההכרעה היא מסר בדרך, ולא מקור אמת: מקור האמת הוא `playbook-model.json`
ו-`playbook-core.json` שבתיקייה המשותפת. הסקריפט הזה סוגר את הלולאה, ואחריו
סביבת העבודה נבנית מחדש מהמודל ומתפרסמת לאותו קישור.

שימוש:
  python3 apply_decisions.py --decisions playbook-decisions.json \\
      --model playbook-model.json [--core playbook-core.json] \\
      [--records "Areo-נתונים/אישורים"] [--index Areo-נתונים/playbooks/index.json] \\
      [--lang he|en] [--by "שם המכריע"] [--dry-run] [--force]

מה הוא עושה:
  1. מאמת שהקובץ שייך לפלייבוק הזה, ושלא נקלט כבר.
  2. כותב לכל סעיף את ההכרעה: אושר, אושר עם שינוי, לא אושר. אישור שניתן על נוסח
     שהשתנה מאז אינו נרשם. הערה בלי הכרעה נרשמת לסעיף (client_notes) עם הכותב
     והזמן, ואינה משנה מעמד.
  3. מחיל עריכות נוסח על מסלול הרמזור, ושומר את הנוסח הקודם ביומן.
  4. מוסיף רשומה ליומן ההחלטות שבמודל, עם מי, מתי, ומה השתנה.
  5. מסנכרן את ההכרעה והנוסח לגרעין ההפעלה.
  6. **אישור באשף נספר כמו אישור בצ'אט.** כל מסלול שאושר על הנוסח שבמודל נרשם כתא מאושר ברשומת אישור
     (APR-NNNN, kind: wizard) בתיקיית האישורים, באותה פונקציה של תור האישור (ingest_approval.wizard_approvals),
     והמעמד נכתב לכל השכבות (after_ingest.apply_ingest): המודל, הגרעין, האינדקס ו-policy_status. כך סביבת
     העבודה, תור האישור ו"שאלו את המדיניות" אומרים אותו מספר. עמדה שנשארו בה סוגריים של ערך שלא נקבע, ועמדה
     שעורך דין צריך לעבור עליה, נרשמות אבל אינן נספרות עד שהערך נקבע או שהבדיקה נרשמה.

טביעת האצבע של הנוסח: כלל אחד בשני הצדדים. האשף מציג את proposed_clause בשפת הדף, ובלעדיה בשפה האחרת
(approval_sheet.clause_text), ומחשב עליו את wiz_hash; הקליטה מחשבת את אותו חישוב על אותו טקסט, לפי
clause_lang שהאשף רשם (או lang של הקובץ). בקובץ מאשף קודם, שאין בו clause_lang, נבדקות שתי השפות.

מה הוא אינו עושה: אינו ממציא הכרעה, אינו מכריע סעיף שלא הוכרע, ואינו מוחק
ראיות. סעיף שנוסחו במודל השתנה מאז ההכרעה מסומן כטעון אימות ואינו מוחל בשקט.
"""
import argparse, hashlib, io, json, os, shutil, sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # גם ב-python -I, שאינו מוסיף את תיקיית הסקריפט
import areo_lib  # noqa: F401,E402  מוסיף את areolegal/lib לנתיב הייבוא
from playbook import after_ingest  # noqa: E402
from playbook import approval_sheet as A  # noqa: E402
from playbook import ingest_approval as IA  # noqa: E402
from playbook import status as S  # noqa: E402

for _s in (sys.stdout, sys.stderr):  # עברית בקונסולה שאינה UTF-8 (cp1252): בלי UnicodeEncodeError
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):   # לא TextIOWrapper (לכידה בבדיקות, pythonw)
        pass

STATUS = {"accept": "approved", "edit": "approved_with_change", "reject": "rejected", "na": "not_relevant"}
HE = {"approved": "אושר", "approved_with_change": "אושר עם שינוי", "rejected": "לא אושר", "not_relevant": "לא רלוונטי"}
EN_STATUS = {"approved": "approved", "approved_with_change": "approved with a change", "rejected": "not approved",
             "not_relevant": "not relevant", "held": "not recorded"}
HE.setdefault("held", "האישור לא נרשם")
# אשף schema 3: הכרעה לכל עמדה (type: decision, outcome). התוצאה ממופה למעמדי ההחלטה הקיימים של המודל; רק
# "approve" על הנוסח שבמודל נרשם כתא מאושר (ingest_approval.wizard_approvals). אישור של עמדה אחת אינו מאשר אחרת.
OUTCOME_PICK = {"approve": "accept", "approve_change": "edit", "reject": "reject", "not_relevant": "na"}
# מעמד הסעיף כשיש כמה הכרעות על עמדותיו: הדחייה קובעת, אחריה שינוי, אחריו אישור, ורק "לא רלוונטי" בכולן: לא רלוונטי
PICK_ORDER = ("reject", "edit", "accept", "na")
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
    למבנה שהקליטה מכירה, כדי שהמסלול יישאר אחד. הערה נכתבת כ-comment, ואשף
    מגרסה קודמת כתב note; שני הערכים נקלטים. שם הכותב נלקח מהרשומה, ובלעדיו
    מ-by שבראש הקובץ. ב-approve נשמרת טביעת האצבע של הנוסח הירוק שאושר.
    """
    picks, notes, edits, whos, ats, seen, at_rule, langs, tracks = {}, {}, {}, {}, [], {}, {}, {}, {}
    positions = {}      # rid -> {track: {"outcome", "wording"}}: ההכרעות על העמדות (schema 3, ואישור סעיף ישן)
    top_by = raw.get("by") or ""
    file_lang = raw.get("lang") or ""
    # schema 2: הערה נושאת רק note, והצעת נוסח רק wording. אין שדה text משותף, ולכן הערה לעולם אינה נקראת כנוסח.
    # קובץ מגרסה קודמת (בלי schema) נושא text משותף: הצעה ממנו נקלטת רק עם הנוסח שכתוב בה, והערה נשארת הערה.
    # schema 3: רשומת decision לכל עמדה (track, outcome); קובץ schema 2 ומטה (approve של סעיף) נקלט כמו קודם.
    v2 = (raw.get("schema") or 0) >= 2
    for e in raw.get("entries") or []:
        rid, kind = e.get("rule_id"), e.get("type")
        if not rid or not kind:
            continue
        if e.get("by") or top_by:
            whos[rid] = e.get("by") or top_by
        if e.get("at"):
            ats.append(e["at"])
            at_rule[rid] = e["at"]
        # השפה של הנוסח שהאשף הציג וחישב עליו את טביעת האצבע; בקובץ מאשף קודם: None, ושתי השפות נבדקות
        langs[rid] = e.get("clause_lang") or None
        if kind == "decision":
            track, outcome = e.get("track"), e.get("outcome")
            if track not in COLORS or outcome not in OUTCOME_PICK:
                continue
            wording = str(e.get("wording") or "")
            positions.setdefault(rid, {})[track] = {"outcome": outcome, "wording": wording}
            if e.get("clause_hash"):
                seen.setdefault(rid, {})[track] = e["clause_hash"]
            # "אישור בשינוי" עם נוסח מתוקן: הנוסח נכתב לעמדה כהצעה (apply_edits), והעמדה ממתינה לאישור על הנוסח החדש
            if outcome == "approve_change" and wording.strip():
                edits.setdefault(rid, {})[track] = {"clause": wording}
        elif kind == "approve":
            picks[rid] = "accept"
            # אשף מגרסה זו רושם טביעת אצבע לכל מסלול שהוצג (track_hashes), והאישור חל על כולם; אשף קודם רשם
            # רק את הירוק (clause_hash), והאישור חל עליו בלבד
            th = {k: v for k, v in (e.get("track_hashes") or {}).items() if k in COLORS and v}
            if th:
                seen.setdefault(rid, {}).update(th)
                tracks[rid] = [c for c in COLORS if c in th]
            else:
                if e.get("clause_hash"):
                    seen.setdefault(rid, {})["green"] = e["clause_hash"]
                tracks[rid] = ["green"]
            for c in tracks[rid]:
                positions.setdefault(rid, {}).setdefault(c, {"outcome": "approve", "wording": ""})
        elif kind == "suggestion":
            picks[rid] = "edit"
            track = e.get("track") or "green"
            wording = (e.get("wording") if v2 else (e.get("wording") or e.get("text"))) or ""
            if not str(wording).strip():
                picks.pop(rid, None)        # הצעה בלי נוסח אינה הצעה
                continue
            edits.setdefault(rid, {})[track] = {"clause": wording}
            if e.get("clause_hash"):
                seen.setdefault(rid, {})[track] = e["clause_hash"]
        elif kind in ("comment", "note"):
            notes[rid] = (e.get("note") if v2 else (e.get("note") or e.get("text"))) or ""
        if kind == "approve" and not v2 and e.get("text"):
            notes[rid] = e["text"]
    # מעמד הסעיף נגזר מההכרעות על עמדותיו (PICK_ORDER); ההכרעה על כל עמדה נשמרת בנפרד ב-positions
    for rid, pos in positions.items():
        pks = {OUTCOME_PICK[p["outcome"]] for p in pos.values()}
        picks[rid] = next(k for k in PICK_ORDER if k in pks)
        tracks[rid] = [c for c in COLORS if c in pos and pos[c]["outcome"] == "approve"]
    return {"playbook": raw.get("playbook") or {}, "decisions": picks, "notes": notes,
            "ruleEdits": edits, "by_rule": whos, "seen_hash": seen, "at_rule": at_rule,
            "clause_lang": langs, "approve_tracks": tracks, "positions": positions, "lang": file_lang,
            "exported": raw.get("created") or (max(ats) if ats else "")}


def wiz_hash(text):
    """אותו גיבוב שהאשף מחשב על הנוסח שהוצג (hash() שבתבנית האשף). המימוש האחד: approval_sheet.wiz_hash."""
    return A.wiz_hash(text)


def seen_matches(light, want, clause_lang, file_lang):
    """האם טביעת האצבע מהאשף תואמת לנוסח שבמודל עכשיו. הטקסט נבחר באותו כלל שבו האשף בחר אותו
    (approval_sheet.clause_text): clause_lang שהאשף רשם, ובלעדיו lang של הקובץ. קובץ מאשף קודם, בלי clause_lang:
    גם הנוסח בשפה האחרת נבדק, כי האשף הציג את מה שהיה בנתונים (גם נוסח אנגלי בלבד, כש-he ריק)."""
    pc = light.get("proposed_clause")
    if not isinstance(pc, dict):
        return wiz_hash(pc or "") == want
    if clause_lang:
        return wiz_hash(pc.get(clause_lang) or "") == want
    first, _ = A.clause_text(pc, file_lang or "he")
    return want in {wiz_hash(first), wiz_hash(pc.get("he") or ""), wiz_hash(pc.get("en") or "")}


def records_dir_for(model_path, model):
    """תיקיית רשומות האישור: התיקייה של הרשומה האחרונה שהמודל מפנה אליה, ובלעדיה Areo-נתונים/אישורים (המודל
    יושב ב-Areo-נתונים/playbooks/<סוג>/), ובלי מבנה כזה, אישורים לצד המודל."""
    base = os.path.dirname(os.path.abspath(model_path))
    last = S._latest_record(model) or {}
    if last.get("record"):
        rec = last["record"] if os.path.isabs(last["record"]) else os.path.join(base, last["record"])
        return os.path.dirname(os.path.normpath(rec))
    parent = os.path.dirname(base)
    if os.path.basename(parent) == "playbooks":
        return os.path.join(os.path.dirname(parent), "אישורים")
    return os.path.join(base, "אישורים")


def index_for(records, index_arg):
    """playbooks/index.json: --index, ובלעדיו playbooks/index.json לצד תיקיית האישורים, כשהוא קיים."""
    if index_arg:
        return index_arg
    guess = os.path.join(os.path.dirname(os.path.abspath(records)), "playbooks", "index.json")
    return guess if os.path.exists(guess) else None


# ההודעות שהלקוח קורא, בשפת קובץ ההערות (areo-voice.md: בלי קודים ובלי מונחים פנימיים)
MSG = {
    "he": {"counted": "נספרו כמאושרות: {a}. עכשיו מאושרות {n} מתוך {m} עמדות במדיניות.",
           "already": "מתוך מה שאישרתם, {n} כבר היו מאושרות קודם ולא נספרו שוב.",
           "value": "לא נספרו עד שייקבע הערך שבסוגריים: {n}, {r}.",
           "legal": "לא נספרו עד שעורך דין יעבור עליהן ויאשר בצ'אט (\"נבדק ולאשר\"): {n}, {r}.",
           "person": "לא נספרו, כי השם באשף אינו שם מלא של אדם: {r}. אשרו אותם בצ'אט בשם המאשר.",
           "held": "לא נספרו, כי הנוסח השתנה מאז שאושר באשף: {r}. כדאי לשאול אם לאשר את הנוסח הנוכחי.",
           "read": "בקובץ {m} הכרעות, ונקלטו {n}: {s}.",
           "commented": "הערות שנרשמו לסעיפים, בלי לשנות את המעמד שלהם: {r}.",
           "edited": "שינויי נוסח שהוחלו: {n}. הנוסח הקודם נשמר ביומן ההחלטות.",
           "stale_edit": "{r}: הנוסח השתנה מאז שההצעה נכתבה, ולכן היא לא הוחלה. כדאי להשוות ולהחליט.",
           "no_change": "{r}: סומן \"אושר עם שינוי\", אבל אין נוסח חדש או הערה. הנוסח נשאר כפי שהיה.",
           "dry": "ריצת יובש. לא נכתב דבר."},
    "en": {"counted": "Counted as approved: {a}. {n} of {m} positions in the policy are now approved.",
           "already": "Of what you approved, {n} were already approved before and were not counted again.",
           "value": "Not counted until the value in brackets is set: {n}, in {r}.",
           "legal": "Not counted until a lawyer reviews them and approves in the chat (\"reviewed and approve\"): "
                    "{n}, in {r}.",
           "person": "Not counted, because the name in the wizard is not a person's full name: {r}. "
                     "Approve them in the chat in the approver's name.",
           "held": "Not counted, because the wording changed after it was approved in the wizard: {r}. "
                   "Ask whether to approve the current wording.",
           "read": "The file has {m} decisions, and {n} were applied: {s}.",
           "commented": "Comments added to clauses, without changing their status: {r}.",
           "edited": "Wording changes applied: {n}. The previous wording is kept in the decision log.",
           "stale_edit": "{r}: the wording changed after the suggestion was written, so it was not applied. "
                         "Compare and decide.",
           "no_change": "{r}: marked \"approved with a change\", but there is no new wording or comment. The "
                        "wording stays as it was.",
           "dry": "Dry run. Nothing was written."},
}


def nums(model, rids, lang="he"):
    """"סעיף 3" או "סעיפים 3, 7": מספרי הסעיפים כפי שהלקוח רואה אותם (approval_sheet.display_num), ולא המזהים
    הפנימיים (areo-voice.md)."""
    ns = ", ".join(A.display_num(model, r) or r for r in rids)
    if lang == "en":
        return ("clause %s" if len(rids) == 1 else "clauses %s") % ns
    return ("סעיף %s" if len(rids) == 1 else "סעיפים %s") % ns


def npos(n, lang="he"):
    """"עמדה אחת" או "4 עמדות", ולא "1 עמדות"."""
    if lang == "en":
        return "1 position" if n == 1 else "%d positions" % n
    return "עמדה אחת" if n == 1 else "%d עמדות" % n


def _clip(text, n=400):
    text = " ".join(str(text or "").split())
    return text if len(text) <= n else text[:n - 1] + "…"


def lang_for_preview(dec, model):
    return S.norm_lang(dec.get("lang")) or S.model_lang(model)


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
        sys.exit("שגיאה: זה קובץ הערות והצעות מגרסה קודמת של סביבת העבודה, ולא קובץ "
                 "ההערות של האשף. הוא אינו נקלט. כתבו את ההערות באשף ההערות (בסביבת "
                 "העבודה: \"להעיר על הסעיף באשף\"), והעלו את הקובץ שהוא מפיק.\n"
                 "Error: this is a comments file from an earlier version of the workspace, "
                 "not the wizard's comments file, and it is not ingested. Write the comments "
                 "in the comments wizard and upload the file it creates.")
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
                    "השתנה מאז מסומן כטעון אימות ואינו מוחל." % (seen, cur))
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
            if short == "clause":
                # נוסח דו-לשוני נשאר מבנה דו-לשוני: הנוסח החדש נכתב בשפתו, והתרגום הישן של הנוסח הקודם יורד
                prev = A.clause_text(old, "he")[0] if isinstance(old, dict) else old
                if prev == new:
                    continue
                if isinstance(old, dict):
                    tlang = "he" if any(0x590 <= ord(ch) <= 0x5ff for ch in new) else "en"
                    light[name] = {"he": new if tlang == "he" else "", "en": new if tlang == "en" else "",
                                   "source_language": tlang}
                    for k in old:
                        if k not in ("he", "en", "source_language"):
                            light[name][k] = old[k]
                else:
                    light[name] = new
                fb = light.get("fallback_wording")
                if color == "yellow" and isinstance(fb, dict) and fb.get("text"):
                    fb["text"] = new
                elif color == "yellow" and isinstance(fb, str) and fb.strip():
                    light["fallback_wording"] = new
                light["edited_by_user"] = True
                log_entry.setdefault("wording_changes", []).append(
                    {"track": color, "field": name, "from": prev, "to": new, "source": "wizard_suggestion"})
                changed += 1
                continue
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
    ap.add_argument("--records", help="תיקיית רשומות האישור (Areo-נתונים/אישורים). בלעדיה נגזרת מהמודל")
    ap.add_argument("--index", help="playbooks/index.json, להטבעת המעמד. בלעדיו: לצד תיקיית האישורים, כשקיים")
    ap.add_argument("--lang", help="שפת ההודעות: he או en. בלעדיו lang של קובץ ההערות")
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
    if not picks and not any(str(v).strip() for v in notes.values()):
        sys.exit("בקובץ אין אף הכרעה. אין מה לקלוט.")

    log, applied, unknown, counts, held, commented = [], {}, [], {}, [], []
    live_tracks = {}    # rid -> העמדות שאושרו על הנוסח שבמודל עכשיו: רק הן נרשמות כתאים מאושרים
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
            if want and not seen_matches(light, want, (dec.get("clause_lang") or {}).get(rid),
                                         dec.get("lang")):
                stale.append(color)
        he = {"green": "בירוק", "yellow": "בצהוב", "red": "באדום"}
        pos = (dec.get("positions") or {}).get(rid) or {}
        appr_tracks = (dec.get("approve_tracks") or {}).get(rid) or (["green"] if status == "approved" and not pos else [])
        stale_appr = [c for c in appr_tracks if c in stale]
        live_appr = [c for c in appr_tracks if c not in stale]
        if stale_appr and not live_appr and status == "approved":
            # האישור ניתן על נוסח אחר מזה שבמודל עכשיו, ולכן אינו נרשם (wizard_spec.md,
            # "מה המערכת עושה עם הקובץ", סעיף 5). שואלים את המשתמש אם לאשר את הנוסח הנוכחי.
            entry["status"], entry["status_he"] = "held", "האישור לא נרשם"
            entry["review_code"] = "held"
            entry["review_required"] = ("הנוסח %s השתנה במודל מאז שהלקוח אישר אותו, "
                                        "ולכן האישור לא נרשם. יש לשאול אם לאשר את הנוסח הנוכחי."
                                        % " ו".join(he.get(c, c) for c in stale_appr))
            log.append(entry)
            held.append(rid)
            continue
        if stale_appr:
            # חלק מהעמדות שאושרו השתנו: הן אינן נרשמות, והאחרות כן. האישור לעולם אינו עובר בשקט לנוסח אחר
            entry["review_code"] = "held_partial"
            entry["review_required"] = ("הנוסח %s השתנה במודל מאז שהלקוח אישר אותו, ולכן האישור על העמדה הזאת "
                                        "לא נרשם. יש לשאול אם לאשר את הנוסח הנוכחי."
                                        % " ו".join(he.get(c, c) for c in stale_appr))
            held.append(rid)
        stale_edit = [c for c in stale if c not in appr_tracks]
        if stale_edit:
            entry["review_code"] = "stale_edit"
            entry["review_required"] = ("הנוסח %s השתנה במודל מאז שהלקוח ראה אותו, "
                                        "ולכן ההצעה לא הוחלה. יש להשוות ולהכריע."
                                        % " ו".join(he.get(c, c) for c in stale_edit))
            for color in stale_edit:
                (edits.get(rid) or {}).pop(color, None)
        if pos:
            # ההכרעה על כל עמדה בנפרד, במעמדי ההחלטה הקיימים (אישור של עמדה אינו מאשר אחרת)
            entry["positions"] = {c: dict(status=STATUS[OUTCOME_PICK[p["outcome"]]],
                                          status_he=HE[STATUS[OUTCOME_PICK[p["outcome"]]]],
                                          **({"held": True} if c in stale_appr else {}))
                                  for c, p in pos.items()}
        live_tracks[rid] = live_appr
        changed = apply_edits(rule, edits.get(rid), entry)
        if (status == "approved_with_change" and not changed and not notes.get(rid)
                and not entry.get("review_required")):
            entry["review_code"] = "no_change"
            entry["review_required"] = ("סומן אושר עם שינוי, אך לא נמצא נוסח חדש "
                                        "ולא הערה. הנוסח נשאר כפי שהיה.")
        rule["decision"] = {k: entry[k] for k in
                            ("status", "status_he", "note", "decided_at", "applied_at", "by", "positions")
                            if k in entry}
        log.append(entry)
        applied[rid] = rule["decision"]
        counts[status] = counts.get(status, 0) + 1

    # הערה בלי הכרעה נרשמת לסעיף כהערה של הלקוח, עם הכותב והזמן, ואינה משנה מעמד
    for rid in sorted(notes):
        text = str(notes[rid] or "").strip()
        if rid in picks or not text:
            continue
        rule = by_id.get(rid)
        if rule is None:
            unknown.append("%s: אין סעיף כזה במודל" % rid)
            continue
        who = (dec.get("by_rule") or {}).get(rid) or a.by
        at = (dec.get("at_rule") or {}).get(rid) or stamp
        rule.setdefault("client_notes", []).append(
            {"text": text, "by": who, "at": at, "source": os.path.basename(a.decisions)})
        log.append({"rule_id": rid, "topic": rule.get("topic_name", ""), "status": "comment",
                    "status_he": "הערה", "note": text, "decided_at": at,
                    "applied_at": now(), "by": who, "source": os.path.basename(a.decisions)})
        commented.append(rid)

    # הצעות נוסח מוצגות לפני כתיבה (ובריצת יובש): הנוסח הקיים מול החדש, לכל עמדה. הערה אינה מופיעה כאן
    # לעולם: היא נרשמת כהערה בלבד. הצעת נוסח היא שינוי מדיניות (wizard_spec.md, "מה המערכת עושה עם הקובץ")
    names_c = {"green": ("ירוקה", "green"), "yellow": ("צהובה", "yellow"), "red": ("אדומה", "red")}
    for e in log:
        for ch in e.get("wording_changes", []):
            hl = lang_for_preview(dec, model)
            print(("Wording suggestion, %s, %s position:\n  now:  %s\n  new:  %s" if hl == "en" else
                   "הצעת נוסח, %s, העמדה ה%s:\n  עכשיו: %s\n  חדש:  %s")
                  % (nums(model, [e["rule_id"]], hl), names_c.get(ch["track"], (ch["track"],) * 2)[hl == "en"],
                     _clip(ch["from"]), _clip(ch["to"])))
    for line in warnings:
        print("אזהרה: " + line)
    for line in unknown:
        print("לא נקלט, " + line)

    # אישור באשף נרשם כתא מאושר, כמו אישור בצ'אט, כדי שייספר בכל השכבות (ingest_approval.wizard_approvals)
    lang = S.norm_lang(a.lang) or S.norm_lang(dec.get("lang")) or S.model_lang(model)
    T = MSG[lang]
    # רק עמדות שהוכרעו "אישור" על הנוסח שבמודל עכשיו; עמדה שנדחתה, שאושרה בשינוי או שסומנה לא רלוונטית
    # אינה תא מאושר, גם כשעמדה אחרת באותו סעיף אושרה
    approvals = {rid: live_tracks[rid] for rid in applied if live_tracks.get(rid)}
    wiz = None
    if approvals:
        prior_cells = S.record_cells_for(model, a.model)
        src_sha = hashlib.sha256(io.open(a.decisions, "rb").read()).hexdigest()
        wiz = IA.wizard_approvals(model, approvals, dec.get("by_rule") or {}, os.path.basename(a.decisions),
                                  src_sha, dec.get("at_rule"), None, prior_cells, lang)
        sm, rr = wiz["summary"], wiz["rules"]
        st_now = S.derive_status(model, wiz["cells"], lang=lang)
        print(T["counted"].format(a=npos(sm["approved"], lang), n=st_now["approved_count"], m=st_now["positions_count"]))
        if sm["already"]:
            print(T["already"].format(n=npos(sm["already"], lang)))
        if rr["pending_value"]:
            print(T["value"].format(n=npos(sm["pending_value"], lang), r=nums(model, rr["pending_value"], lang)))
        if rr["pending_legal"]:
            print(T["legal"].format(n=npos(sm["pending_legal"], lang), r=nums(model, rr["pending_legal"], lang)))
        if rr["not_person"]:
            print(T["person"].format(r=nums(model, rr["not_person"], lang)))
    if held:
        print(T["held"].format(r=nums(model, held, lang)))

    names = HE if lang == "he" else EN_STATUS
    summary = ", ".join("%s: %d" % (names[k], counts[k]) for k in sorted(counts))
    print(T["read"].format(n=len(applied), m=len(picks), s=summary or "-"))
    if commented:
        print(T["commented"].format(r=nums(model, commented, lang)))
    edited = sum(len(e.get("wording_changes", [])) for e in log)
    if edited:
        print(T["edited"].format(n=edited))
    for e in log:
        if e.get("review_code") in ("stale_edit", "no_change"):
            print(T[e["review_code"]].format(r=nums(model, [e["rule_id"]], lang)))

    if a.dry_run:
        print(T["dry"])
        return

    model.setdefault("decision_log", []).extend(log)
    batches.append({"exported": stamp, "applied_at": now(), "count": len(log),
                    "source": os.path.basename(a.decisions), "by": a.by})
    model["last_updated"] = now()[:10]
    core = load(a.core, "גרעין ההפעלה") if a.core else None
    if wiz is not None and any(c.get("via") == "wizard" for c in wiz["cells"].values()):
        # הרשומה נשמרת, ואז המעמד נכתב לכל השכבות באותה פונקציה של קליטת הגיליון והתור (after_ingest)
        records = a.records or records_dir_for(a.model, model)
        idx_path = index_for(records, a.index)
        index = load(idx_path, "האינדקס") if idx_path and os.path.exists(idx_path) else None
        try:
            import ingest_approval as IAS   # הסקריפט הסמוך: אותו איתור של הרשומה באינדקס
            entry, entries = IAS.index_entry_of(index, model, core)
        except Exception:   # pragma: no cover  בלי הסקריפט הסמוך: בלי אינדקס
            entry, entries = None, None
        prior = (S._latest_record(model) or {}).get("record_id")
        path = IA.save_chat_record(records, wiz, supersedes=prior)
        try:
            rel = os.path.relpath(os.path.abspath(path), os.path.dirname(os.path.abspath(a.model)))
        except ValueError:   # כונן אחר ב-Windows
            rel = os.path.abspath(path)
        out = after_ingest.apply_ingest(model, core, entry, wiz, rel)
        if index is not None and entry is not None:
            with io.open(idx_path, "w", encoding="utf-8") as fh:
                json.dump(index if isinstance(index, dict) else entries, fh, ensure_ascii=False, indent=1)
        print("רשומת האישור: %s" % path)
        print(S.label_for(out["status"], lang))
        for prob in out.get("problems") or ():
            print("  סתירה בין השכבות: %s" % prob)
    write(a.model, model)
    print("נכתב %s (גיבוי ב-%s.bak)" % (a.model, a.model))

    if core is not None:
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
