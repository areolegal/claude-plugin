"""הרכבת clm-data.json בגרסה 2 מתוצאות הסריקה ומקובצי החילוץ.

זה המקום היחיד שבו נוצר clm-data.json. ההרכבה דטרמיניסטית: אותו קלט, אותו פלט.
מספרי ההסכמים ומזהי המועדים יציבים בין הרצות, כדי שאימות ושיוך (שלב 2) יישמרו.

החוזה (מה שהתבנית קוראת):
  meta{company, generated_at, last_updated, as_of, source_run, schema_version, files_scanned, number_seq, lang}
  lang: he או en. כל מחרוזת שההרכבה כותבת ללקוח (פריטי אימות, הערות בסיס, פעולות, תוויות הקטלוג, סיבות שווי)
  נכתבת בשפה הזו (ראו i18n.py ו-catalog/en.json). המפתחות והקודים זהים בשתי השפות, וציטוט מההסכם אינו מתורגם.
  documents[{id, file, sha256, doc_kind, date, counterparty, title, relation, version_by, base_version?}]
  agreements[{id, number, title, type_code, family, type_label, counterparty, counterparty_id,
              contracting_entity, our_role{value, source, confirmed}, doc_ids, versions, file,
              original_location, signature (signed_unverified | not_signed | unknown),
              dates{signed, start, end, actual_end, original_end?, end_source?, end_basis{kind, note}, current_end,
              current_end_basis{kind, note}}, governing_law, law_class, counterparty_notice_address, notes[{text, file}],
              key_clauses_not_found[קוד], legal_owner, business_owner, coverage,
              type_fields[{label, value}],
              value{annual_by_currency{cur: n}, annual (מספר רק כשיש מטבע אחד, אחרת None), currency, total,
              total_currency, basis, components[{component, category, period, currency, value, annual_value, source, since, effective_date}] (שורה לכל רכיב; השווי הוא סכומם), not_counted[{label, reason}], unknown_currency[label], in_portfolio}, handling_stage,
              agreement_state, waiting_on?, idle_days?, field_status,
              source_removed? (כל קובצי המקור הוסרו; ההסכם ותוכנו נשמרים מההרצה הקודמת),
              extraction_pending? (קובץ המקור קיים אך לא חולץ בהרצה הזו; התוכן מההרצה הקודמת)}]
              end_basis.kind: contract (מהחוזה) | amendment (מתיקון חתום) | deadline (נגזר ממועד תום תקופה כתוב, כשאין סיום) | None.
              current_end: סיום התקופה הנוכחית. בחידוש אוטומטי שגולגל, התאריך העתידי של הגלגול (current_end_basis.kind =
              auto_renewal, והערה עם הנוסחה); אחרת שווה ל-end (same_as_end); None כשאין סיום (kind None).
              field_status.end_date: extracted | derived (end_basis deadline) | not_expected (הקטלוג: end_date_expected false,
              ואין סיום) | missing. הסכם חתום שחסר בו תאריך חתימה או תאריך סיום פותח פריט אימות missing_core.
              law_class: home (home_law מופיע בדין החל) | foreign | unset (ריק, או "לא נקבע" או "לא סוכם").
              contracting_entity: שם החברה כפי שהוזן כשהחילוץ זהה לו עד כדי גרשיים ורווחים.
              תיקון חתום שמאריך את התקופה מחליף גם מועדי אופציה מותנים (pending_trigger) שתאריכם קדם לסיום החדש.
              dates.end מתוקן לפי התיקון להסכם החתום האחרון שיש בו תאריך סיום (end_source = מזהה מסמך התיקון,
              original_end = הסיום שבהסכם המקורי). תיקון שאינו חתום, או ששמו מעיד על טיוטה, אינו משנה תאריכים
              (בטיוטה עם תאריך חתימה נפתח פריט אימות amendment_unconfirmed). מועד של הנוסח הקודם שהתיקון
              הרחיק או קירב את התקופה ביחס אליו נשאר פתוח ואינו נסגר: superseded_by (מזהה מסמך התיקון) ו-
              superseded_note (state_note זהה) מסבירים מדוע. פעולה שנגזרה (action) אינה משתנה. מועד כזה שעדיין
              עתידי לא מניע התראות ומצב: act_by ו-next_reminder מתרוקנים, והמצב נגזר רק ממועדי התיקון.
  ליבה מורחבת (שלב ב, ראו core.py): agreements[].term, renewal, exit, signatories, jurisdiction, payment_terms, facts,
  dates.max_end, max_end_basis, survival_end, survival_end_label; end_basis.kind computed (נגזר מתחילה ועוד חודשים);
  current_end_basis.kind indefinite | option_pending; field_status.end_date not_relevant; field_status.term_kind
  ו-signatories. סדר הסיום: תיקון, חוזה, מועד תום תקופה (initial_end או בלי תפקיד), נגזר מתקופה קצובה.
  events[{id, agreementId, event_code, label, clause, refs, verify, obligor, consequence, impact,
          ...שדות dates.derive, overdue_bucket}]
  overdue_bucket: למועד במצב needs_action או lapsed_pending בלבד, אחרת None: superseded | old (לפני 1 בינואר של השנה) |
  role (צד החברה לא אושר) | theirs | ours (needs_action) | outcome.
  commercials[], guarantees[{..., direction, refs}],
  key_clauses[{..., bound_party (counterparty | contracting | both | unknown, אחרי התאמת שם), bound_party_certain,
  bound_party_name, stance (ברירת מחדל set), norm, active_until, active}], footnotes[{n, agreementId, clause, file, quote}]
  timeline[{agreementId, date, stage, source{type, name}, evidence_rank}]
  counterparties[{name, agreements, annual_by_currency}] (רק הסכמים עם value.in_portfolio, ממוין לפי שם), registers{term_passed, not_signed, change_of_control,
  change_of_control_review, restrictions, restrictions_review, restriction_details, poa, regulatory,
  key_clauses_unchecked}, review_queue[{id, kind, group, text, agreementId?,
  eventId?}], catalog, key_clause_labels

מזהים: מספר הסכם נשמר לפי מזהה מסמך או נתיב קובץ. מזהה מועד נגזר מהמספר, מהקוד, מהתווית ומהסעיף,
ובהתנגשות בתוך הסכם מתווסף מספר סידורי לפי תאריך ואז סדר הקלט. מזהה פריט אימות נגזר מסוגו,
מההסכם, מהמועד ומנושאו, ולא ממיקומו ברשימה.
"""
import copy
import datetime as dt
import hashlib
import json
import os
import re

from clm import catalog, core, dates, doc_kind, grouping, i18n, money
from clm.i18n import t
from clm.validate import check_extraction

RENEWAL_CODES = ("term_end", "nonrenewal_notice", "option_extend")
NOT_TERM_END_ROLES = ("min_commitment_end", "max_end")
CARRIED = ("events", "commercials", "guarantees", "key_clauses")
# כל ערך: (עברית, אנגלית). השפה נבחרת בהרכבה לפי meta.lang
REVIEW_GROUP = {"role": ("צד החברה בהסכם", "Company's side in the agreement"), "counterparty": ("צד שכנגד", "Other side"),
                "family": ("סוג הסכם", "Agreement type"),
                "non_agreement": ("מסמך שאינו הסכם", "Document that is not an agreement"),
                "outcome": ("תוצאת מועד שחלף", "Outcome of a passed date"),
                "verify_critical": ("מועד קריטי לאימות מול המקור", "Critical date to check against the source"),
                "duplicate": ("כפילות", "Duplicate"), "not_extracted": ("קובץ שלא חולץ", "File not read yet"),
                "bad_extract": ("חילוץ פגום", "Reading to redo"), "source_removed": ("מקור שהוסר", "Removed source"),
                "split": ("קיבוץ לבדיקה", "Grouping to check"), "merged": ("קיבוץ לבדיקה", "Grouping to check"),
                "renewal_verify": ("תוצאת מועד שחלף", "Outcome of a passed date"),
                "unreadable": ("קובץ שלא נקרא", "File we could not open"),
                "amendment_unconfirmed": ("סוג מסמך לבדיקה", "Document type to check"),
                "kind_conflict": ("סוג מסמך לבדיקה", "Document type to check"),
                "role_conflict": ("סתירה לבדיקה", "Conflict to review"),
                "removed_from_register": ("הוצא מהמאגר", "Removed from the register"),
                "missing_core": ("שדה ליבה חסר", "Missing core field"), "abandoned_evidence": ("משא ומתן", "Negotiation"),
                "unsupported": ("קובץ שלא קראנו", "File we did not read"),
                "signing_unverified": ("חתימה ותחילה לבדיקה", "Signing and start to check"),
                "home_law_unknown": ("הדין המקומי", "Home law"),
                "scanned": ("מסמך סרוק", "Scanned document")}
ROLE_SOURCE = {"playbook": ("מהפלייבוק", "from the playbook"), "suggested": ("השערה מהחילוץ", "our reading of the agreement"),
               "none": ("בלי מקור", "no source"), "user": ("אישור משתמש", "confirmed by a user")}
OUT_OF_REGISTER = {"template": ("תבנית", "a template"), "non_agreement": ("מסמך שאינו הסכם", "a document that is not an agreement")}
# מציין המקום האחיד לנתון חסר (כלל 3.5): "[להשלים]", ובאנגלית "[to complete]"
PLACEHOLDERS = ("[להשלים]", "[to complete]")
OVERDUE_BUCKETS = ("ours", "theirs", "role", "outcome", "old", "superseded")


def _sid(*parts):
    return hashlib.sha1("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()[:10]


def _int(v):
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0


DASHES = {"\u2013": "-", "\u2014": "-"}


def undash(x, key=None):
    """מקף ארוך במחרוזת שאינה ציטוט מוחלף במקף רגיל (שם מסמך, כותרת). ציטוט (quote) נשאר מילה במילה."""
    if isinstance(x, str):
        if key == "quote":
            return x
        for a, b in DASHES.items():
            x = x.replace(a, b)
        return x
    if isinstance(x, dict):
        return {k: undash(v, k) for k, v in x.items()}
    if isinstance(x, list):
        return [undash(v, key) for v in x]
    return x


def load_extracts(extract_dir):
    """(תקינים לפי sha256, פסולים). מקף ארוך מחוץ לציטוט מנורמל לפני הבדיקה, ולכן אינו פוסל הסכם."""
    good, bad = {}, []
    if not os.path.isdir(extract_dir):
        return good, bad
    for name in sorted(os.listdir(extract_dir)):
        if not name.endswith(".json"):
            continue
        try:
            with open(os.path.join(extract_dir, name), encoding="utf-8-sig") as f:
                ext = json.load(f)
        except (ValueError, UnicodeDecodeError, OSError) as e:
            bad.append({"file": name, "problems": ["הקובץ פגום ולא נקרא (%s)" % type(e).__name__]})
            continue
        ext = undash(ext)
        problems = check_extraction(ext)
        if not problems and str(ext["sha256"]) != name[:-len(".json")]:
            problems = ["sha256 שבתוך הקובץ אינו תואם את שם הקובץ %s. שם הקובץ חייב להיות <sha256>.json לפי scan.json" % name]
        if problems:
            bad.append({"file": ext.get("file", name) if isinstance(ext, dict) else name, "problems": problems})
        else:
            good[ext["sha256"]] = ext
    return good, bad


def _role_label(row):
    """תווית צד החברה של רשומה: company_role (מקובץ הגרעין או מרשומה ישנה), אחרת company_role_code."""
    for k in ("company_role", "company_role_code"):
        v = row.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def load_playbooks(path):
    """רשומות אינדקס הפלייבוקים (Areo-נתונים/playbooks/index.json), אם קיים. מחזיר (רשומות, שגיאה).

    הצורה שכותב register_playbook בסוכן הפלייבוק: family_id, family_code, family_name, family_aliases,
    company_role_code ו-core_path (יחסי ל-Areo-נתונים). תווית צד החברה נקראת מ-company_role שבקובץ
    playbook-core.json; בלעדיו, הקוד עצמו. רשומה ישנה עם company_role ישיר נקראת כפי שהיא.
    """
    if not path or not os.path.exists(path):
        return [], None
    try:
        with open(path, encoding="utf-8-sig") as f:
            idx = json.load(f)
    except (ValueError, UnicodeDecodeError, OSError) as e:
        return [], "אינדקס הפלייבוקים אינו קריא (%s). צד החברה לא נלקח ממנו" % type(e).__name__
    rows = idx.get("playbooks") if isinstance(idx, dict) else None
    if not isinstance(rows, list):
        return [], "באינדקס הפלייבוקים אין רשימת playbooks. צד החברה לא נלקח ממנו"
    playbooks_dir = os.path.dirname(os.path.abspath(path))
    out = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        row = dict(r)
        core_rel = row.get("core_path")
        if not (isinstance(row.get("company_role"), str) and row["company_role"].strip()) and isinstance(core_rel, str):
            for base in (os.path.dirname(playbooks_dir), playbooks_dir):
                core_path = os.path.join(base, *core_rel.replace("\\", "/").split("/"))
                if os.path.exists(core_path):
                    try:
                        with open(core_path, encoding="utf-8-sig") as f:
                            core = json.load(f)
                    except (ValueError, UnicodeDecodeError, OSError):
                        break
                    if isinstance(core, dict) and isinstance(core.get("company_role"), str) and core["company_role"].strip():
                        row["company_role"] = core["company_role"].strip()
                    break
        if _role_label(row):
            out.append(row)
    return out, None


def _norm(s):
    return " ".join(str(s or "").split()).casefold()


def playbook_role(ext, tinfo, playbooks):
    """צד החברה מהפלייבוק: (ערך או None, הערה לאימות).

    קובץ החילוץ יכול לציין playbook_family_id (Claude בחר את הפלייבוק לפי סוג ההסכם והפוזיציה), שמותאם
    ל-family_id או ל-family_code של הרשומה. בלעדיו, רשומה מתאימה כשה-family_code או ה-type_code שלה זהה
    ל-type_code של ההסכם, או כששם המשפחה או שם חלופי זהה לתווית הסוג. כמה פוזיציות שונות, או השערה
    מהחילוץ שסותרת את הפלייבוק, אינן מאושרות אוטומטית.
    """
    if not playbooks:
        return None, ""
    fid = ext.get("playbook_family_id")
    if fid:
        rows = [r for r in playbooks if fid in (r.get("family_id"), r.get("family_code"))]
        if not rows:
            return None, t("הפלייבוק %s לא נמצא ברשימת הפלייבוקים", "The playbook %s is not in your playbook list") % fid
    else:
        labels = {_norm(ext.get("type_label")), _norm((tinfo or {}).get("label"))} - {""}
        tc = ext.get("type_code")
        rows = []
        for r in playbooks:
            names = [r.get("family_name")] + (r.get("family_aliases") if isinstance(r.get("family_aliases"), list) else [])
            if (tc and tc in (r.get("type_code"), r.get("family_code"))) or \
                    labels & {_norm(x) for x in names if isinstance(x, str)}:
                rows.append(r)
    roles = sorted({_role_label(r) for r in rows} - {""})
    if len(roles) > 1:
        return None, t("כמה פלייבוקים מתאימים, וכל אחד מגדיר צד אחר שלכם בהסכם: %s",
                       "Several playbooks match, each with a different side for you: %s") % ", ".join(roles)
    if not roles:
        return None, ""
    role, guess = roles[0], _norm((ext.get("our_role") or {}).get("value"))
    if not fid and guess and guess not in _norm(role) and _norm(role) not in guess:
        return None, t("ההשערה מהחילוץ (%s) שונה מצד החברה בפלייבוק (%s)",
                       "Our reading of the agreement (%s) differs from the company's side in the playbook (%s)") % (
            ext["our_role"]["value"], role)
    return role, ""


POLICY_MATCH = ("match", "differs", "not_compared")


def policy_match(kc, pb):
    """התאמת סעיף מפתח למדיניות: match (הסעיף בתוך העמדה שהפלייבוק מקבל), differs (שונה ממנה) או not_compared.
    ההשוואה עצמה נעשית בחילוץ (Claude משווה את נוסח הסעיף לעמדה של אותו נושא בפלייבוק המתאים, ורושם policy_match
    ו-policy_rule). כאן היא רק נבדקת: בלי פלייבוק מתאים להסכם, או בלי ערך תקין, הסעיף לא הושווה."""
    v = (kc.get("policy_match") or "").strip() if isinstance(kc.get("policy_match"), str) else ""
    if not pb or v not in POLICY_MATCH:
        return "not_compared"
    return v


def _value_rank(src, si):
    """דרגת שורת תמורה לחישוב השווי: "" להסכם, לנספח ולהזמנה; תאריך החתימה לתיקון חתום; None לתיקון שאינו
    חתום או ששמו מעיד על טיוטה (שורותיו אינן נספרות בשווי)."""
    if si == 0 or src["doc_kind"] != "amendment":
        return ""
    signed = src["_ext"]["dates"].get("signed")
    if not signed or doc_kind.says_draft(grouping.basename(src["file"])):
        return None
    return signed


def _clause_code(x):
    """קוד סעיף מפתח מרשומת "נבדק ולא נמצא": מחרוזת, או אובייקט עם clause_code."""
    if isinstance(x, dict):
        x = x.get("clause_code")
    return x if isinstance(x, str) else None


def _rv(kind, text, subject=None, **kw):
    item = {"kind": kind, "group": t(*REVIEW_GROUP[kind]) if kind in REVIEW_GROUP else kind, "text": text}
    item.update(kw)
    if subject is not None:
        item["_s"] = subject
    return item


def _event_ids(items):
    """items: [(parts, date)]. מזהה כפול בתוך הסכם מקבל מספר סידורי לפי תאריך ואז סדר הקלט."""
    keys = [_sid(*parts) for parts, _ in items]
    out, by = [None] * len(items), {}
    for i, k in enumerate(keys):
        by.setdefault(k, []).append(i)
    for k, idxs in by.items():
        for n, i in enumerate(sorted(idxs, key=lambda j: (str(items[j][1] or ""), j))):
            out[i] = "ev-" + (k if n == 0 else _sid(*(items[i][0] + ["#%d" % n])))
    return out


def _review_ids(review):
    used = {}
    for r in review:
        subject = r.pop("_s", None)
        if subject is None:
            subject = "" if (r.get("agreementId") or r.get("eventId")) else r["text"]
        basis = [r["kind"], r.get("agreementId") or "", r.get("eventId") or "", subject]
        rid = "rv-" + _sid(*basis)
        n = used.get(rid, 0)
        used[rid] = n + 1
        r["id"] = rid if n == 0 else "rv-" + _sid(*(basis + ["#%d" % n]))


def _signed_state(mine, start, today):
    """מצב הסכם חתום. חלון חידוש פתוח גובר על "בהארכה", כדי שחלון החידוש הבא יופיע גם אחרי חידוש.
    מועד של הנוסח הקודם שתיקון חתום החליף (superseded_by) אינו קובע את המצב. "בהארכה מכוח ההסכם" רק כשההסכם
    עצמו התחדש (renewed): תיקון שהאריך את התקופה משאיר את ההסכם בתוקף."""
    mine = [e for e in mine if not e.get("superseded_by")]
    # סיום התחייבות מזערית וסיום התקופה המרבית אינם סיום התקופה: הם נשארים מועדים, ואינם קובעים מצב
    mine = [e for e in mine if not (e["event_code"] == "term_end" and e.get("term_role") in NOT_TERM_END_ROLES)]
    soon = [e for e in mine if e["event_code"] in RENEWAL_CODES and e["state"] == "upcoming" and e["date"]
            and (dt.date.fromisoformat(e["date"]) - today).days <= 120]
    if any(e["event_code"] == "term_end" and e["state"] == "needs_action" for e in mine):
        return "term_passed_unverified"
    if soon:
        return "renewal_window"
    if any(e.get("renewed") for e in mine):
        return "extended"
    if start and dt.date.fromisoformat(start) > today:
        return "signed_not_effective"
    return "in_force"


def _amendment_note(signed, end, original_end):
    if not original_end:
        # בהסכם המקורי אין תאריך סיום (למשל תנאים מקוונים שהתקופה בהם בהזמנה): התיקון קובע את הסיום
        return t("תיקון להסכם מיום %s קובע את סיום התקופה: %s; לאשר את התוצאה",
                 "An amendment dated %s sets the end of the term: %s; confirm the outcome") % (
            dates.fmt(dates.parse(signed)), dates.fmt(dates.parse(end)))
    shorter = dates.parse(end) < dates.parse(original_end)
    verb = t("מקצר", "shortens") if shorter else t("מאריך", "extends")
    return t("תיקון להסכם מיום %s %s את התקופה עד %s; לאשר את התוצאה",
             "An amendment dated %s %s the term to %s; confirm the outcome") % (
        dates.fmt(dates.parse(signed)), verb, dates.fmt(dates.parse(end)))


def _mark_superseded(e, kid_id, note):
    """מועד שהתיקון החליף: נשאר פתוח עם הערה. עתידי: בלי act_by ובלי תזכורת, כדי שלא יניע התראות."""
    e.update(superseded_by=kid_id, superseded_note=note, state_note=note)
    if e["state"] == "upcoming":
        e.update(act_by=None, next_reminder=None)


def _amendment_end(head, kids, order):
    """(תיקון חתום אחרון שיש בו סיום שונה מהמקורי, תיקונים שיש בהם תאריך חתימה ושמם מעיד על טיוטה)."""
    cands, doubtful = [], []
    for k in kids:
        d = k["_ext"]["dates"]
        if k["doc_kind"] != "amendment" or not d.get("end"):
            continue
        if d["end"] == head["_ext"]["dates"].get("end"):
            continue
        # בלי תאריך חתימה, או ששם הקובץ מעיד על טיוטה: התיקון אינו משנה תאריכים עד שאדם מאשר שנחתם
        (doubtful if not d.get("signed") or doc_kind.says_draft(grouping.basename(k["file"])) else cands).append(k)
    late = max(cands, key=lambda z: (z["_ext"]["dates"]["signed"], order[z["id"]])) if cands else None
    return late, doubtful


def _supersede(head_events, kid, original_end):
    """מועדי תקופה של הנוסח הקודם שהתיקון עקף: בהארכה, מועדים שקדמו לסיום החדש; בקיצור, מועדים שאחריו."""
    d = kid["_ext"]["dates"]
    end = dates.parse(d["end"])
    # בלי סיום מקורי, התיקון נחשב הארכה: מועדי תקופה שקדמו לסיום החדש הוחלפו
    orig = dates.parse(original_end) if original_end else end - dt.timedelta(days=1)
    note = _amendment_note(d["signed"], d["end"], original_end)
    states = ("needs_action", "lapsed_pending", "upcoming") + (("pending_trigger",) if end > orig else ())
    for e in head_events:
        if e["event_code"] not in RENEWAL_CODES or e["state"] not in states:
            continue
        when = dates.parse(e["date"]) if e.get("date") else None
        if when and ((end > orig and when < end) or (end < orig and when > end)):
            _mark_superseded(e, kid["id"], note)


_norm_entity = core.norm_entity


def _signing_shown(a):
    """יש במסמך ראיה לחתימה ולתחילה: תאריך חתימה (שמעיד גם על תחילה), או תאריך תחילה וחותם שחתם או תאריך חתימה של חותם.
    כשבלוק החתימות נקרא וכל שורותיו ריקות, אין ראיה לחתימה, גם אם בראש המסמך כתוב תאריך."""
    d, sigs = a["dates"], a.get("signatories") or []
    signed_by = any(s.get("status") == "signed" or s.get("date") for s in sigs)
    if sigs and not signed_by and all(s.get("status") == "blank" for s in sigs):
        return False
    return bool(d.get("signed")) or bool(d.get("start") and (signed_by or not sigs)) or any(s.get("date") for s in sigs)


def _entity(extracted, company):
    """הישות המתקשרת: שם החברה כפי שהוזן כשהחילוץ זהה לו עד כדי גרשיים ורווחים, אחרת הטקסט שחולץ."""
    if _norm_entity(extracted) == _norm_entity(company):
        return company
    return extracted or company


# שם הדין המקומי בעברית ובאנגלית, כדי שחילוץ באנגלית ("Israeli law") יסווג כמו חילוץ בעברית
HOME_ALIASES = ({"ישראל", "israel", "israeli", "הישראלי"},
                {"בריטניה", "אנגליה", "united kingdom", "uk", "england", "english", "england and wales", "האנגלי"},
                {"ארצות הברית", "united states", "usa", "u.s.", "american", "האמריקני"},
                {"גרמניה", "germany", "german", "הגרמני"}, {"צרפת", "france", "french", "הצרפתי"},
                {"הולנד", "netherlands", "dutch", "ההולנדי"}, {"אירלנד", "ireland", "irish", "האירי"},
                {"קפריסין", "cyprus", "cypriot", "הקפריסאי"})


def _home_law(home_law, previous, source=None):
    """(הדין המקומי, מקורו). מה שנמסר (מהפרופיל, מדינת ההתאגדות, או --home-law), ואחריו מה שנרשם בהרצה הקודמת
    רק כשנרשם לו מקור (home_law_source). ערך ישן בלי מקור הוא ברירת המחדל הישנה, ואינו נלקח. בלי שניהם:
    (None, None): הדין המקומי לא ידוע, ואין "דין בית" מונח מראש."""
    if home_law:
        return home_law, source or "given"
    meta = (previous or {}).get("meta") or {}
    if meta.get("home_law") and meta.get("home_law_source"):
        return meta["home_law"], meta["home_law_source"]
    return None, None


def _law_class(law, home_law):
    """home | foreign | unset | unknown (יש דין חל, אבל הדין המקומי של החברה לא ידוע, ולכן אין סיווג)."""
    law = (law or "").strip()
    if not law or law.startswith(("לא נקבע", "לא סוכם")) or law.lower().startswith(("not set", "not agreed")):
        return "unset"
    if not home_law:
        return "unknown"
    names = {home_law.lower()} if home_law else set()
    for group in HOME_ALIASES:
        if names & group:
            names |= group
    return "home" if any(n in law.lower() for n in names) else "foreign"


def _as_texts(v):
    if isinstance(v, str):
        v = [v]
    return [t.strip() for t in v if isinstance(t, str) and t.strip()] if isinstance(v, list) else []


def _deadline_end(head_evs):
    """סיום ממועד: מועד תום תקופה כתוב בתאריך (לא יחסי, לא מופע שחלף, תפקיד initial_end או בלי תפקיד) המוקדם ביותר."""
    cands = [e for e in head_evs if e["event_code"] == "term_end" and not e.get("relative")
             and e.get("term_role") in (None, "initial_end")
             and e.get("contract_date_original") and e.get("occurrence") != "passed"]
    return min(cands, key=lambda e: e["contract_date_original"]) if cands else None


def _current_end(mine, end):
    """סיום התקופה הנוכחית: המועד העתידי של חידוש אוטומטי שגולגל, אם יש. (תאריך, בסיס) או (None, None)."""
    cands = [e for e in mine if e["event_code"] in ("term_end", "auto_renewal") and e.get("renewed")
             and e.get("term_role") not in NOT_TERM_END_ROLES
             and e["state"] == "upcoming" and not e.get("superseded_by") and e.get("occurrence") != "passed"
             and e.get("date") and (not end or e["date"] > end)]
    if not cands:
        return None, None
    e = min(cands, key=lambda x: x["date"])
    months = e.get("renewal_months") or (e.get("recurrence") or {}).get("months")
    return e["date"], {"kind": "auto_renewal",
                       "note": t("מחושב: %s ועוד %s של %s לפי %s; לאמת שההסכם התחדש",
                                 "Computed: %s plus %s of %s under %s; confirm that the agreement renewed") % (
                           dates.fmt(dates.parse(e["contract_date_original"])),
                           core.count(len(e["history"]), "חידוש אחד", "חידושים", "renewal", "renewals"),
                           core.count(months, "חודש אחד", "חודשים", "month", "months"), e["clause"])}


def _abandoned_items(a):
    return [_rv("abandoned_evidence", t("סימן לכך שהמשא ומתן הופסק ב\"%s\": %s. רק אדם מסמן משא ומתן כ\"נזנח\"",
                                        "A sign that negotiations stopped on \"%s\": %s. Only a person can mark it \"Abandoned\"")
                % (a["title"], f["value"] or f["label"]), agreementId=a["id"], subject="%s|%s" % (f["file"], f["value"] or f["label"]))
            for f in a.get("facts") or [] if f.get("code") == "negotiation_stopped"]


def _overdue_bucket(e, today):
    if e["state"] == "upcoming" and e.get("act_by_passed"):
        # מועד היעד לטיפול חלף והמועד עצמו עוד לא: באיחור לפעולה, לפי מי שצריך לפעול
        return "role" if e.get("role_pending") else "theirs" if e.get("obligor") == "them" else "ours"
    if e["state"] not in ("needs_action", "lapsed_pending"):
        return None
    if e.get("superseded_by"):
        return "superseded"
    if e.get("date") and dates.parse(e["date"]) < dt.date(today.year, 1, 1):
        return "old"
    if e.get("role_pending"):
        return "role"
    if e.get("obligor") == "them":
        return "theirs"
    return "ours" if e["state"] == "needs_action" else "outcome"


def tidy_text(s):
    """נקודה כפולה שנוצרה מחיבור שם שמסתיים בנקודה (Inc.) עם סוף משפט: נקודה אחת. שלוש נקודות נשארות."""
    return re.sub(r"(?<!\.)\.\.(?!\.)", ".", s) if isinstance(s, str) else s


NOTICE_CODES = ("nonrenewal_notice", "option_extend")
ACT_BY_PREFIX = re.compile(r"^(?:מועד היעד לטיפול \([\d.]+\) חלף\. |The act-by date \([\d.]+\) has passed\. )+")


def _act_by_passed(events, today):
    """מועד עתידי שמועד היעד לטיפול בו חלף. בתום תקופה או חידוש אוטומטי, כשמועד ההודעה לאותה תקופה כבר חלף,
    ההחלטה נסגרה: decision_closed, והפעולה אומרת שההסכם יתחדש ומתי ההחלטה הבאה. אחרת act_by_passed, והמועד נספר
    כבאיחור. המצב (state) אינו משתנה: המועד עצמו עדיין עתידי, ואין סגירה אוטומטית."""
    by_ag = {}
    for e in events:
        by_ag.setdefault(e["agreementId"], []).append(e)
    iso = today.isoformat()
    for e in events:
        if (e["state"] != "upcoming" or not e.get("act_by") or e["act_by"] >= iso or e.get("superseded_by")
                or e.get("occurrence") == "passed"):
            continue
        mine = [x for x in by_ag[e["agreementId"]] if not x.get("superseded_by")]
        closed = e["event_code"] in ("term_end", "auto_renewal") and any(
            x["event_code"] in NOTICE_CODES and x.get("date") and x["date"] < iso and x["date"] <= e["date"]
            and (x["state"] in ("lapsed_pending", "needs_action") or x.get("occurrence") == "passed")
            and (dates.parse(e["date"]) - dates.parse(x["date"])).days <= 366 for x in mine)
        if closed:
            nxt = sorted(x for x in mine if x["event_code"] in NOTICE_CODES and x["state"] == "upcoming"
                         and x.get("act_by") and x["act_by"] >= iso and x is not e and x.get("occurrence") != "passed"
                         and x.get("date"))
            e["decision_closed"] = True
            note = t("המועד להודעה חלף, ולכן ההסכם יתחדש ב-%s לפי ההסכם.", "The notice deadline has passed, so the agreement "
                     "renews on %s under its terms.") % dates.fmt(dates.parse(e["date"]))
            if nxt:
                n0 = min(nxt, key=lambda x: x["act_by"])
                note += t(" ההחלטה הבאה: עד %s (%s).", " Next decision: by %s (%s).") % (
                    dates.fmt(dates.parse(n0["act_by"])), n0["label"])
            e["action"] = note
        else:
            e["act_by_passed"] = True
            base = ACT_BY_PREFIX.sub("", e.get("action") or "")  # בהרצה חוזרת על מועד שנגרר: בלי כפילות של הפתיח
            e["action"] = t("מועד היעד לטיפול (%s) חלף. ", "The act-by date (%s) has passed. ") % dates.fmt(
                dates.parse(e["act_by"])) + base


def _rederive(row, today, ev_cat, confirmed, cp):
    """מועד שנגרר מההרצה הקודמת נגזר מחדש מהמועד שבהסכם, כדי שמועד שחלף לא יוצג כעתידי."""
    base = {k: v for k, v in row.items() if k not in ("renewed", "occurrence", "renewal_check")}
    base["date"] = row.get("contract_date_original")
    if base.get("action") and base.get("action") == row.get("state_note"):
        base["action"] = ""
    derived = dates.derive_all(base, today, ev_cat, role_confirmed=confirmed, cp=cp)
    for occ in derived[1:]:
        occ["id"] = "ev-" + _sid(row["id"], "occurrence", occ["date"])
    if row.get("superseded_by"):
        _mark_superseded(derived[0], row["superseded_by"], row["superseded_note"])
    return derived


def resolve_lang(lang=None, previous=None):
    """שפת הנתונים: lang שהועבר, אחרת meta.lang של ההרצה הקודמת, אחרת עברית."""
    if lang:
        return i18n.norm(lang)
    return i18n.norm(((previous or {}).get("meta") or {}).get("lang"))


def assemble(scan, extracts, company, today, previous=None, default_owner="me", bad_extracts=(), as_of=None,
             playbooks=(), home_law=None, company_aliases=(), lang=None, home_law_source=None):
    """clm-data.json. lang (he או en) קובע את שפת כל מחרוזת שנכתבת ללקוח, ונשמר ב-meta.lang."""
    with i18n.using(resolve_lang(lang, previous)) as code:
        law, law_source = _home_law(home_law, previous, home_law_source)
        data = _assemble(scan, extracts, company, today, previous, default_owner, bad_extracts, as_of, playbooks,
                         law, company_aliases)
        data["meta"]["lang"], data["meta"]["home_law_source"] = code, law_source
        if not law and any(a.get("law_class") == "unknown" for a in data["agreements"]):
            item = _rv("home_law_unknown", t("לא ידוע מהו הדין המקומי של החברה, ולכן הדין החל בהסכמים לא סווג כמקומי או זר. "
                                             "להשלים את מדינת ההתאגדות בהקמה",
                                             "We do not know the company's home law, so governing law is not classed as "
                                             "home or foreign. Add the country of incorporation in the setup"),
                       subject="home_law")
            _review_ids([item])
            data["review_queue"].append(item)
        return data


def _assemble(scan, extracts, company, today, previous, default_owner, bad_extracts, as_of, playbooks, home_law,
              company_aliases):
    ev_cat, types = catalog.load_events(), catalog.load_types()
    placeholder = t(*PLACEHOLDERS)
    names = [company] + [n for n in company_aliases if n]
    review, docs, pending, dup_items = [], [], [], {}
    for f in scan["files"]:
        if f["status"] == "removed":
            continue
        if f["status"] == "duplicate":
            dup_items[f["path"]] = _rv("duplicate", t("%s זהה ל-%s", "%s is identical to %s") % (f["path"], f.get("duplicate_of")),
                                       subject=f["path"])
            review.append(dup_items[f["path"]])
            continue
        if f["status"] == "unsupported":
            review.append(_rv("unsupported", t("לא קראנו את %s, כי אין לנו דרך לקרוא קובץ מהסוג הזה. אם יש בו הסכם, "
                                               "שמרו אותו בפורמט אחר והוסיפו אותו לתיקייה",
                                               "We did not read %s, because we cannot open this kind of file. If it holds "
                                               "an agreement, save it in another format and add it to the folder") % f["path"],
                              subject=f["path"]))
            continue
        if f.get("scanned"):
            review.append(_rv("scanned", (t("%s הוא מסמך סרוק. זיהינו בו טקסט מהתמונה, וכדאי לבדוק את התאריכים והסכומים "
                                            "מול המקור", "%s is a scanned document. We recognised its text from the image, "
                                            "so check the dates and amounts against the source")
                                          if f.get("ocr") == "done" else
                                          t("%s הוא מסמך סרוק, ואין במחשב כלי לזיהוי טקסט. הנתונים נקראים מתמונות העמודים, "
                                            "וכדאי לבדוק את התאריכים והסכומים מול המקור", "%s is a scanned document, and "
                                            "this computer has no text recognition. The data is read from the page images, "
                                            "so check the dates and amounts against the source")) % f["path"],
                              subject=f["path"]))
        if f["status"] == "unreadable":
            review.append(_rv("unreadable", t("לא ניתן היה לקרוא את הקובץ (נעול או לא זמין): %s. הנתונים מהחילוץ הקודם "
                                              "נשמרים. לסגור את הקובץ ולהריץ סריקה שוב",
                                              "We could not open the file (locked or unavailable): %s. The data from the last "
                                              "reading is kept. Close the file and scan again") % f["path"], subject=f["path"]))
        ext = extracts.get(f["sha256"]) if f.get("sha256") else None
        if not ext:
            pending.append(f["path"])
            continue
        docs.append({"id": "doc-" + f["sha256"][:10], "file": f["path"], "sha256": f["sha256"],
                     "doc_kind": ext["doc_kind"], "date": ext.get("version_date") or ext["dates"].get("signed"),
                     "signed_date": ext["dates"].get("signed"), "start_date": ext["dates"].get("start"),
                     "counterparty": ext["counterparty"].get("name") or "", "title": ext["title"],
                     "relation": ext.get("relation") or {"kind": None, "parent_hint": None},
                     "version_by": ext.get("version_by", "unknown"), "_ext": ext})
        # מייל שהקבצים המצורפים אליו נסרקו כרשומות נפרדות אינו "הסכם חתום שסווג אחרת", גם כששמו אומר "חתום"
        if ext["doc_kind"] in OUT_OF_REGISTER and not f.get("attachments") and (
                doc_kind.says_signed(f["path"]) or f.get("suggested_kind") == "signed"):
            review.append(_rv("kind_conflict", t("%s: שם הקובץ מעיד על הסכם חתום, והחילוץ סיווג אותו כ%s. לאשר את הסיווג",
                                                 "%s: the file name suggests a signed agreement, but our reading classed it "
                                                 "as %s. Confirm the classification")
                              % (grouping.basename(f["path"]), t(*OUT_OF_REGISTER[ext["doc_kind"]])), subject=f["path"]))
    by_sha = {f.get("sha256"): f["path"] for f in scan["files"] if f.get("sha256")}
    for b in bad_extracts:
        name = by_sha.get(str(b["file"])[:-len(".json")], b["file"]) if str(b["file"]).endswith(".json") else b["file"]
        if i18n.en():
            # הבעיות עצמן הן הודעות טכניות בעברית (validate.py), ולכן בממשק באנגלית מוצג רק מה קרה ומה יקרה
            what = "one of the files" if str(name).endswith(".json") else name
            review.append(_rv("bad_extract", "We could not use what we read from %s. It will be read again on the next "
                                             "update" % what, subject=b["file"], detail=list(b["problems"][:5]), source=name))
        else:
            review.append(_rv("bad_extract", "%s: %s" % (name, "; ".join(b["problems"][:3])),
                              detail=list(b["problems"][:5]), source=name))

    g = grouping.group(docs, company)
    review.extend(g["review"])
    by_id = {d["id"]: d for d in docs}
    prev = previous or {}
    prev_ags = prev.get("agreements", [])
    prev_by_number = {p["number"]: p for p in prev_ags}
    prev_doc = {d["id"]: d for d in prev.get("documents", [])}

    def prev_files(p):
        fs = {prev_doc[x]["file"] for x in p.get("doc_ids", []) if x in prev_doc}
        if p.get("file"):
            fs.add(p["file"])
        return fs

    def num_of(n):
        tail = str(n).rsplit("-", 1)[-1]
        return int(tail) if tail.isdigit() else 0

    seq = max([_int((prev.get("meta") or {}).get("number_seq"))] + [num_of(p["number"]) for p in prev_ags])
    order = {d["id"]: i for i, d in enumerate(docs)}
    kids_of = {gi: [by_id[c] for c, pg in sorted(g["children"].items()) if pg == gi] for gi in range(len(g["groups"]))}
    gids = [set(grp["doc_ids"]) | {k["id"] for k in kids_of[gi]} for gi, grp in enumerate(g["groups"])]
    gfiles = [{by_id[x]["file"] for x in ids} for ids in gids]
    numbers, split_from, merged = {}, {}, []
    for p in prev_ags:
        pids, pfiles = set(p.get("doc_ids", [])), prev_files(p)
        cand = [gi for gi in range(len(gids)) if gids[gi] & pids or gfiles[gi] & pfiles]
        match = [gi for gi in cand if gi not in numbers]
        if not match:
            if cand:
                merged.append((cand[0], p["number"]))
            continue
        win = next((gi for gi in match if p.get("file") in gfiles[gi]), match[0])
        numbers[win] = p["number"]
        for gi in match:
            if gi != win:
                split_from.setdefault(gi, p["number"])
    inherited = set(numbers)

    agreements, events, commercials, guarantees, key_clauses, timeline, notes = [], [], [], [], [], [], []
    checked_ids = set()

    def ref(aid, clause, file, quote):
        if not quote:
            return []
        notes.append({"n": len(notes) + 1, "agreementId": aid, "clause": clause, "file": file, "quote": quote})
        return [len(notes)]

    for gi, grp in enumerate(g["groups"]):
        members = [by_id[x] for x in grp["doc_ids"]]
        head = by_id[grp["head_id"]]
        ext = head["_ext"]
        kids = kids_of[gi]
        number = numbers.get(gi)
        if not number:
            seq += 1
            number = "CLM-%d-%04d" % (today.year, seq)
        aid = "ag-" + _sid(number)
        tinfo = types.get(ext.get("type_code"))
        role, role_note, conflict = ext["our_role"], "", None
        before = (prev_by_number.get(number) or {}).get("our_role") or {}
        if before.get("source") == "user" and before.get("value") and role.get("source") != "user":
            if role.get("value") and _norm(role["value"]) != _norm(before["value"]):
                conflict = role
            role = {"value": before["value"], "source": "user"}
        elif role.get("source") != "user":
            if role.get("source") == "playbook" and role.get("value"):
                pb = role["value"]
            else:
                pb, role_note = playbook_role(ext, tinfo, playbooks)
            if pb:
                # צד החברה מהפלייבוק מאושר רק כשהמסמך אינו סותר אותו: אם הצד שכנגד מוגדר בהסכם בתפקיד הזה,
                # או שהחברה מוגדרת בתפקיד אחר, הצד ממתין לאישור
                clash = core.side_conflict(pb, ext)
                role = {"value": pb, "source": "suggested"} if clash else {"value": pb, "source": "playbook"}
                role_note = clash or role_note
        confirmed = role.get("source") in ("playbook", "user")
        # פלייבוק שמתאים להסכם, להשוואת סעיפי המפתח למדיניות (policy_match); בלעדיו אין השוואה
        pb_for_policy = playbook_role(ext, tinfo, playbooks)[0] if playbooks else None
        orphan_child = head["doc_kind"] in grouping.CHILD
        if orphan_child:
            signed = bool(ext["dates"].get("signed"))
        else:
            signed = any(m["doc_kind"] == "signed" for m in members)
        cp = ext["counterparty"].get("name") or placeholder
        a = {"id": aid, "number": number, "title": ext["title"],
             "type_code": ext.get("type_code") if tinfo else None,
             "family": tinfo["label"] if tinfo else (ext.get("type_label") or t("לא סווג", "Not classified")),
             "type_label": ext.get("type_label") or "", "counterparty": cp,
             "counterparty_id": ext["counterparty"].get("company_number"),
             "contracting_entity": _entity(ext.get("contracting_entity"), company),
             "our_role": {"value": role.get("value") or "", "source": role.get("source") or "none", "confirmed": confirmed},
             "doc_ids": [m["id"] for m in members] + [k["id"] for k in kids], "versions": len(members),
             "file": head["file"], "original_location": head["file"],
             "signature": "signed_unverified" if signed else ("unknown" if orphan_child else "not_signed"),
             "dates": {"signed": ext["dates"].get("signed"), "start": ext["dates"].get("start"),
                       "end": ext["dates"].get("end"), "actual_end": None},
             "governing_law": ext.get("governing_law"), "law_class": _law_class(ext.get("governing_law"), home_law),
             "counterparty_notice_address": ext["counterparty"].get("notice_address") or None,
             "legal_owner": default_owner if confirmed else None, "business_owner": None,
             "coverage": ext["coverage"],
             "type_fields": [{"label": f["label"], "value": (ext.get("type_fields") or {}).get(f["key"])}
                             for f in (tinfo or {}).get("type_fields", [])]}
        srcs = [head] + kids
        slots = [(si, ei) for si, src in enumerate(srcs) for ei in range(len(src["_ext"]["events"]))]
        ev_ids = dict(zip(slots, _event_ids([
            ([number, e["event_code"], e["label"], e["clause"]] + ([] if si == 0 else [srcs[si]["id"]]), e.get("date"))
            for si, ei in slots for e in [srcs[si]["_ext"]["events"][ei]]])))
        a_com, value_rows, head_evs, a_notes, found_codes = [], [], [], [], set()
        kc_codes = catalog.load_key_clauses()
        for si, src in enumerate(srcs):
            sx = src["_ext"]
            a_notes.extend({"text": t, "file": src["file"]} for t in _as_texts(sx.get("notes")))
            found_codes.update(k.get("clause_code") for k in sx.get("key_clauses") or [] if isinstance(k, dict))
            for ei, e in enumerate(sx["events"]):
                base = {k: v for k, v in e.items() if k != "quote"}
                base.update(agreementId=aid, refs=ref(aid, e["clause"], src["file"], e.get("quote")),
                            verify=not e.get("quote"), id=ev_ids[(si, ei)])
                derived = dates.derive_all(base, today, ev_cat, role_confirmed=confirmed, cp=cp)
                for occ in derived[1:]:
                    occ["id"] = "ev-" + _sid(base["id"], "occurrence", occ["date"])
                events.extend(derived)
                if si == 0:
                    head_evs.extend(derived)
            for c in sx.get("commercials", []):
                row = {k: v for k, v in c.items() if k != "quote"}
                row.update(agreementId=aid, refs=ref(aid, c["clause"], src["file"], c.get("quote")))
                commercials.append(row)
                a_com.append(row)
                rank = _value_rank(src, si)
                if rank is not None:
                    value_rows.append(dict(row, _rank=rank))
            for gu in sx.get("guarantees", []):
                row = {k: v for k, v in gu.items() if k != "quote"}
                row.update(agreementId=aid, refs=ref(aid, gu["clause"], src["file"], gu.get("quote")))
                guarantees.append(row)
            for kc in sx.get("key_clauses", []):
                row = {k: v for k, v in kc.items() if k != "quote"}
                row.update(agreementId=aid, refs=ref(aid, kc["clause"], src["file"], kc.get("quote")))
                row.update(core.key_clause_fields(kc, names, ext["counterparty"].get("name"), confirmed, today))
                row["policy_match"] = policy_match(kc, pb_for_policy)
                key_clauses.append(row)
        # "נבדק ולא נמצא": רק ממקורות שנבדקו (אם אין, מהמסמך הראשי), בניכוי כל סעיף שנמצא באחד המקורות
        nf_srcs = [s_ for s_ in srcs if s_["_ext"].get("key_clauses_checked")] or [head]
        not_found = {c for s_ in nf_srcs for c in map(_clause_code, s_["_ext"].get("key_clauses_not_found") or [])
                     if c in kc_codes} - found_codes
        val = money.annual(value_rows, ext.get("currency"), as_of=today.isoformat())
        by = val["by_currency"]
        basis = None
        if by:
            basis = t("מחושב מהתמורה שבהסכם", "Computed from the payments in the agreement")
            if val["amended_on"]:
                basis += t("; לפי התיקון להסכם מיום %s", "; per the amendment dated %s") % dates.fmt(dates.parse(val["amended_on"]))
            if val["estimated"]:
                basis += t("; כולל אומדן", "; includes an estimate")
        doc_cur = money.currency_of({}, ext.get("currency"))
        a["value"] = {"annual_by_currency": by, "annual": next(iter(by.values())) if len(by) == 1 else None,
                      "currency": next(iter(by)) if len(by) == 1 else doc_cur,
                      "total": ext.get("total_value"), "total_currency": doc_cur, "basis": basis,
                      "components": val["components"], "not_counted": val["not_counted"], "unknown_currency": val["unknown_currency"],
                      "in_portfolio": False}
        late, doubtful = _amendment_end(head, kids, order) if signed else (None, [])
        if late:
            a["dates"].update(original_end=a["dates"]["end"], end=late["_ext"]["dates"]["end"], end_source=late["id"])
            _supersede(head_evs, late, a["dates"]["original_end"])
        a["notes"], a["key_clauses_not_found"] = a_notes, sorted(not_found)
        a.update(core.agreement_fields(ext, lambda cl, q: ref(aid, cl, head["file"], q), names,
                                       ext["counterparty"].get("name"), confirmed))
        a["facts"] = core.facts([(s_["file"], s_["_ext"]) for s_ in srcs], lambda cl, q, f: ref(aid, cl, f, q))
        dl = _deadline_end(head_evs) if not a["dates"]["end"] else None
        comp, comp_note = (None, None) if a["dates"]["end"] or dl else core.computed_end(
            ext.get("term"), core.start_for(ext.get("term"), ext["dates"]))
        if late:
            a["dates"]["end_basis"] = {"kind": "amendment", "note": t("לפי התיקון להסכם מיום %s", "Per the amendment dated %s") % (
                dates.fmt(dates.parse(late["_ext"]["dates"]["signed"])))}
        elif dl:
            a["dates"]["end"] = dl["contract_date_original"]
            a["dates"]["end_basis"] = {"kind": "deadline", "note": t("לפי המועד: ", "From the date: ") + dl["label"]}
        elif comp:
            a["dates"]["end"] = comp
            a["dates"]["end_basis"] = {"kind": "computed", "note": comp_note}
        else:
            a["dates"]["end_basis"] = {"kind": "contract" if a["dates"]["end"] else None, "note": ""}
        for k in doubtful:
            review.append(_rv("amendment_unconfirmed", t("%s: תיקון להסכם משנה את תאריך הסיום; לאשר שנחתם",
                                                         "%s: an amendment changes the end date; confirm it was signed")
                              % grouping.basename(k["file"]), agreementId=aid, subject=k["file"]))
        mine = [e for e in events if e["agreementId"] == aid]
        cur, cur_basis = _current_end(mine, a["dates"]["end"])
        if cur:
            a["dates"]["current_end"], a["dates"]["current_end_basis"] = cur, cur_basis
        else:
            cur, cur_basis, verify = core.current_end(a["dates"]["end"], a["term"], a["renewal"], today, signed)
            if verify:
                review.append(_rv("renewal_verify", "%s: %s" % (a["title"], verify), agreementId=aid))
            if cur_basis:
                a["dates"]["current_end"], a["dates"]["current_end_basis"] = cur, cur_basis
            else:
                a["dates"]["current_end"] = a["dates"]["end"] or None
                a["dates"]["current_end_basis"] = {"kind": "same_as_end" if a["dates"]["end"] else None, "note": ""}
        mx, mx_kind, mx_note = core.max_end(ext.get("term"), ext.get("renewal"), a["dates"]["end"], head_evs)
        a["dates"].update(max_end=mx, max_end_basis={"kind": mx_kind, "note": mx_note} if mx_kind else None)
        a["dates"]["survival_end"], a["dates"]["survival_end_label"] = core.survival_end(head_evs)
        if signed:
            a["handling_stage"] = None
            a["agreement_state"] = core.term_passed(_signed_state(mine, a["dates"]["start"], today), a["dates"],
                                                    a["dates"]["current_end"], today)
            a["value"]["in_portfolio"] = a["agreement_state"] in money.PORTFOLIO_STATES
        else:
            last = None
            for m in sorted(members, key=lambda z: z["date"] or "0000"):
                theirs = m["doc_kind"] == "negotiation_version" and m["version_by"] == "them"
                last = {"agreementId": aid, "date": m["date"], "stage": "comments_received" if theirs else "drafting",
                        "source": {"type": "file", "name": m["file"]}, "evidence_rank": 3}
                timeline.append(last)
            a["agreement_state"] = None
            a["handling_stage"] = "comments" if last["stage"] == "comments_received" and not orphan_child else "drafting"
            a["waiting_on"] = "us"
            a["idle_days"] = (today - dt.date.fromisoformat(last["date"])).days if last["date"] else None
        a["field_status"] = {k: ("extracted" if v else "missing") for k, v in {
            "our_role": a["our_role"]["value"], "counterparty": cp != placeholder, "type": bool(tinfo),
            "end_date": a["dates"]["end"], "start_date": a["dates"]["start"], "value": by,
            "governing_law": a["governing_law"], "business_owner": None, "term_kind": a["term"],
            "signatories": a["signatories"]}.items()}
        basis_kind = a["dates"]["end_basis"]["kind"]
        if basis_kind in ("contract", "amendment"):
            a["field_status"]["end_date"] = "extracted"
        elif basis_kind in ("deadline", "computed"):
            a["field_status"]["end_date"] = "derived"
        elif (a["term"] or {}).get("kind") in core.NOT_RELEVANT_TERMS:
            a["field_status"]["end_date"] = "not_relevant"
        elif not a["term"] and not a["dates"]["current_end"] and (tinfo or {}).get("end_date_expected") is False:
            a["field_status"]["end_date"] = "not_expected"
        else:
            a["field_status"]["end_date"] = "missing"
        if a["signature"] == "signed_unverified":
            absent = [label for label, miss in ((t("תאריך חתימה", "Signing date"), not a["dates"]["signed"]),
                                                (t("תאריך סיום", "End date"), a["field_status"]["end_date"] == "missing"),
                                                (t("סוג תקופה", "Term type"), not a["term"]),
                                                (t("חותמים", "Signatories"), not a["signatories"])) if miss]
            absent += core.missing_party_sides(a["signatories"])
            if absent:
                review.append(_rv("missing_core", t("שדה ליבה חסר ב\"%s\": %s. להשלים מהמקור, או לאשר \"נבדק ולא נמצא\"",
                                                    "Missing core field in \"%s\": %s. Fill it in from the source, or confirm "
                                                    "\"Checked, not found\"")
                                  % (a["title"], ", ".join(absent)), agreementId=aid))
        if not signed:
            review.extend(_abandoned_items(a))
        if signed and not _signing_shown(a):
            # אין במסמך תאריך חתימה, תאריך תחילה או חותם שחתם: ההסכם אינו מוצג "בתוקף" עד שאדם מאשר
            a.update(signature="unknown", agreement_state="status_unverified")
            a["value"]["in_portfolio"] = False
            review.append(_rv("signing_unverified", t("לא מצאנו ב\"%s\" תאריך חתימה, תאריך תחילה או חותם שחתם, ולכן הוא לא "
                                                      "מוצג כבתוקף. לאשר שנחתם ומתי נכנס לתוקף",
                                                      "We found no signing date, start date or signed signatory in \"%s\", "
                                                      "so it is not shown as in force. Confirm it was signed and when it "
                                                      "took effect") % a["title"], agreementId=aid))
        agreements.append(a)
        if ext.get("key_clauses_checked"):
            checked_ids.add(aid)
        if gi in split_from and gi not in inherited:
            review.append(_rv("split", t("ההסכם %s פוצל. מספר חדש: %s", "Agreement %s was split. New number: %s") % (
                split_from[gi], number), agreementId=aid))
        for mgi, other in merged:
            if mgi == gi:
                review.append(_rv("merged", t("ההסכמים %s ו-%s זוהו כעסקה אחת ואוחדו. נשמר המספר %s, והמספר %s אינו "
                                              "בשימוש עוד. לאשר את האיחוד",
                                              "Agreements %s and %s were found to be one deal and merged. Number %s is "
                                              "kept, and %s is no longer used. Confirm the merge") % (number, other, number, other),
                                  agreementId=aid, subject=other))
        if conflict:
            review.append(_rv("role_conflict", t("סתירה לבדיקה: צד החברה ב\"%s\" אושר כ\"%s\", והגרסה החדשה מציינת \"%s\" (%s). "
                                                 "הערך שאושר נשמר עד להכרעה",
                                                 "Conflict to review: the company's side in \"%s\" was confirmed as \"%s\", and "
                                                 "the new version says \"%s\" (%s). The confirmed value stays until you decide")
                              % (a["title"], role["value"], conflict["value"],
                                 t(*ROLE_SOURCE[conflict.get("source")]) if conflict.get("source") in ROLE_SOURCE else ""),
                              agreementId=aid))
        if not confirmed:
            review.append(_rv("role", t("לאשר את צד החברה ב\"%s\"%s", "Confirm the company's side in \"%s\"%s") % (
                a["title"], " (%s)" % role_note if role_note else ""), agreementId=aid))
        if cp == placeholder:
            review.append(_rv("counterparty", t("להשלים את הצד שכנגד ב\"%s\"", "Fill in the other side in \"%s\"") % a["title"],
                              agreementId=aid))
        if not tinfo:
            review.append(_rv("family", t("סוג הסכם שאינו בקטלוג (\"%s\"): לאשר או להציע הגדרה מקומית",
                                          "Agreement type not in the catalogue (\"%s\"): confirm it or suggest a local definition")
                              % a["family"], agreementId=aid))

    # הסכם מההרצה הקודמת שלא נבנה מחדש: נשמר כמות שהוא, עם מועדיו, סעיפיו וציטוטיו (בהפניות ממוספרות מחדש)
    present_paths = {f["path"] for f in scan["files"] if f["status"] != "removed"}
    removed_paths = {f["path"] for f in scan["files"] if f["status"] == "removed"}
    inherited_numbers, merged_numbers = set(numbers.values()), {n for _, n in merged}
    now_doc_ids = {d["id"] for d in docs}
    prev_unchecked = set((prev.get("registers") or {}).get("key_clauses_unchecked") or [])
    carried_files, carried_docs, carried_pending = set(), [], {}
    grouped_files = set().union(*gfiles) if gfiles else set()
    out_kind = {d["file"]: d["doc_kind"] for d in docs if d["doc_kind"] in OUT_OF_REGISTER and d["file"] not in grouped_files}

    def carry(p, flag):
        c = copy.deepcopy(p)
        c.pop("source_removed", None)
        c.pop("extraction_pending", None)
        c[flag] = True
        agreements.append(c)
        nmap = {}
        for f in sorted((x for x in prev.get("footnotes", []) if x.get("agreementId") == p["id"]), key=lambda x: x["n"]):
            notes.append(dict(copy.deepcopy(f), n=len(notes) + 1))
            nmap[f["n"]] = len(notes)
        for coll, target in zip(CARRIED, (events, commercials, guarantees, key_clauses)):
            for row in prev.get(coll, []):
                if row.get("agreementId") != p["id"] or row.get("occurrence") == "passed":
                    continue
                r = copy.deepcopy(row)
                r["refs"] = [nmap[n] for n in row.get("refs") or [] if n in nmap]
                if coll == "events":
                    target.extend(_rederive(r, today, ev_cat, bool((c.get("our_role") or {}).get("confirmed")),
                                            c.get("counterparty") or None))
                else:
                    if coll == "key_clauses":
                        r["active"] = core._active(r, today)
                    target.append(r)

        def remap(x):
            if isinstance(x, dict) and "refs" in x:
                x["refs"] = [nmap[n] for n in x.get("refs") or [] if n in nmap]
        for k in ("term", "renewal", "exit", "jurisdiction", "payment_terms"):
            remap(c.get(k))
        for k in ("signatories", "facts"):
            for x in c.get(k) or []:
                remap(x)
        if c.get("agreement_state") and c["agreement_state"] != "status_unverified":
            c["agreement_state"] = _signed_state([e for e in events if e["agreementId"] == c["id"]],
                                                 (c.get("dates") or {}).get("start"), today)
        d = c.setdefault("dates", {})
        d.setdefault("end_basis", {"kind": "amendment" if d.get("end_source") else ("contract" if d.get("end") else None),
                                   "note": ""})
        # סיום התקופה הנוכחית נגזר מחדש מהמועדים שנגזרו מחדש, כדי שחידוש שגולגל לא יישאר ישן
        cur, cur_basis = _current_end([e for e in events if e["agreementId"] == c["id"]], d.get("end"))
        verify = None
        if not cur:
            cur, cur_basis, verify = core.current_end(d.get("end"), c.get("term"), c.get("renewal"), today,
                                                      c.get("signature") == "signed_unverified")
        if verify:
            review.append(_rv("renewal_verify", "%s: %s" % (c["title"], verify), agreementId=c["id"]))
        if cur_basis:
            d["current_end"], d["current_end_basis"] = cur, cur_basis
        else:
            d["current_end"] = d.get("end") or None
            d["current_end_basis"] = {"kind": "same_as_end" if d.get("end") else None, "note": ""}
        for k in ("term", "renewal", "exit", "jurisdiction", "payment_terms"):
            c.setdefault(k, None)
        for k in ("signatories", "facts"):
            c.setdefault(k, [])
        for k in ("max_end", "max_end_basis", "survival_end", "survival_end_label"):
            d.setdefault(k, None)
        # תאריכים נגזרים מהמועדים שנגזרו מחדש. תקרה שנכתבה בהסכם נשמרת כפי שחולצה
        mine = [e for e in events if e["agreementId"] == c["id"]]
        d["survival_end"], d["survival_end_label"] = core.survival_end(mine)
        if (d.get("max_end_basis") or {}).get("kind") != "extracted":
            mx, mx_kind, mx_note = core.max_end(None, c.get("renewal"), d.get("end"), mine)
            d["max_end"], d["max_end_basis"] = mx, {"kind": mx_kind, "note": mx_note} if mx_kind else None
        fs = c.setdefault("field_status", {})
        fs.setdefault("term_kind", "missing")
        fs.setdefault("signatories", "missing")
        if c.get("agreement_state"):
            c["agreement_state"] = core.term_passed(c["agreement_state"], d, d["current_end"], today)
        if c.get("signature") != "signed_unverified":
            review.extend(_abandoned_items(c))
        c["law_class"] = _law_class(c.get("governing_law"), home_law)
        c["value"] = money.normalize(c.get("value"), (c.get("signature") == "signed_unverified")
                                     and c.get("agreement_state") in money.PORTFOLIO_STATES)
        timeline.extend(copy.deepcopy(t) for t in prev.get("timeline", []) if t.get("agreementId") == p["id"])
        carried_docs.extend(copy.deepcopy(prev_doc[x]) for x in p.get("doc_ids", [])
                            if x in prev_doc and x not in now_doc_ids)
        if prev.get("registers") is not None and p["id"] not in prev_unchecked:
            checked_ids.add(p["id"])
        return c

    for p in prev_ags:
        if p["number"] in inherited_numbers or p["number"] in merged_numbers:
            continue
        pf = prev_files(p)
        if not pf:
            continue
        here = pf & present_paths
        if here and all(x in out_kind for x in here):
            kinds = t(" ו", " and ").join(sorted({t(*OUT_OF_REGISTER[out_kind[x]]) for x in here}))
            review.append(_rv("removed_from_register", t("הוצא מהמאגר: ההסכם %s (\"%s\") סווג כ%s. המספר אינו בשימוש עוד. "
                                                         "לאשר את הסיווג",
                                                         "Removed from the register: agreement %s (\"%s\") was classed as %s. "
                                                         "The number is no longer used. Confirm the classification")
                              % (p["number"], p["title"], kinds), subject=p["number"]))
            continue
        if here:
            c = carry(p, "extraction_pending")
            for path in here:
                carried_pending[path] = c
        elif pf <= removed_paths or p.get("source_removed"):
            c = carry(p, "source_removed")
            carried_files |= pf
            review.append(_rv("source_removed", t("המקור של \"%s\" הוסר מהתיקייה. ההסכם נשמר ומסומן",
                                                  "The source of \"%s\" was removed from the folder. The agreement is kept "
                                                  "and marked") % c["title"], agreementId=c["id"]))
    for path, item in dup_items.items():
        c = carried_pending.get(path)
        if c:
            item["text"] += t(". ההסכם %s מוצג לפי החילוץ הקודם", ". Agreement %s is shown as last read") % c["number"]
            item["agreementId"] = c["id"]
    for path in pending:
        c = carried_pending.get(path)
        if c:
            review.append(_rv("not_extracted", t("הקובץ טרם חולץ מחדש: %s. ההסכם %s מוצג לפי החילוץ הקודם",
                                                 "The file has not been read again yet: %s. Agreement %s is shown as last read")
                              % (path, c["number"]), agreementId=c["id"], subject=path))
        else:
            review.append(_rv("not_extracted", t("הקובץ טרם חולץ: %s", "The file has not been read yet: %s") % path, subject=path))
    for f in scan["files"]:
        if f["status"] == "removed" and f["path"] not in carried_files:
            review.append(_rv("source_removed", t("הקובץ הוסר מהתיקייה: %s", "The file was removed from the folder: %s") % f["path"],
                              subject=f["path"]))
    containers = {f["path"] for f in scan["files"] if f.get("attachments")}
    for d in docs:
        if d["doc_kind"] == "non_agreement" and d["file"] not in containers:
            review.append(_rv("non_agreement", t("זוהה כמסמך שאינו הסכם: %s. לאשר הוצאה מהמאגר",
                                                 "Identified as a document that is not an agreement: %s. Confirm removing it "
                                                 "from the register") % grouping.basename(d["file"]), subject=d["file"]))
    titles = {a["id"]: a["title"] for a in agreements}
    _act_by_passed(events, today)
    for e in events:
        e["overdue_bucket"] = _overdue_bucket(e, today)
        for k in ("action", "state_note", "superseded_note"):
            if e.get(k):
                e[k] = tidy_text(e[k])
    for e in events:
        if e.get("renewal_check"):
            review.append(_rv("renewal_verify", t("לאמת שההסכם התחדש: %s, %s (המועד %s חלף)",
                                                  "Confirm that the agreement renewed: %s, %s (the date %s has passed)")
                              % (titles[e["agreementId"]], e["label"], dates.fmt(dates.parse(e["date"]))),
                              agreementId=e["agreementId"], eventId=e["id"]))
        elif e["state"] == "lapsed_pending":
            review.append(_rv("outcome", "%s: %s%s" % (e["label"], titles[e["agreementId"]],
                                                       ". " + e["superseded_note"] if e.get("superseded_note") else ""),
                              agreementId=e["agreementId"], eventId=e["id"]))
    for e in events:
        if (e["critical"] and e["state"] in ("upcoming", "needs_action") and e.get("occurrence") != "passed"
                and not (e.get("superseded_by") and e["state"] == "upcoming")):
            review.append(_rv("verify_critical", "%s: %s" % (e["label"], titles[e["agreementId"]]),
                              agreementId=e["agreementId"], eventId=e["id"]))
    _review_ids(review)

    cps = {}
    for a in agreements:
        if a["counterparty"] in PLACEHOLDERS:
            continue
        c = cps.setdefault(a["counterparty"], {"name": a["counterparty"], "agreements": [], "annual_by_currency": {}})
        c["agreements"].append(a["id"])
        if a["value"]["in_portfolio"]:
            for cur, n in a["value"]["annual_by_currency"].items():
                c["annual_by_currency"][cur] = c["annual_by_currency"].get(cur, 0) + n

    for c in cps.values():
        c["annual_by_currency"] = money.tidy(c["annual_by_currency"])

    registers = {"term_passed": [a["id"] for a in agreements if a["agreement_state"] == "term_passed_unverified"],
                 "not_signed": [a["id"] for a in agreements if a["signature"] == "not_signed"],
                 "poa": None, "regulatory": None,
                 "key_clauses_unchecked": sorted(a["id"] for a in agreements if a["id"] not in checked_ids)}
    registers.update(core.registers(agreements, key_clauses, checked_ids, today))
    stamp = today.isoformat()
    return {"meta": {"company": company, "generated_at": stamp, "last_updated": stamp, "as_of": as_of or stamp + "T07:00",
                     "source_run": stamp, "home_law": home_law, "schema_version": "2.0", "files_scanned": sum(1 for f in scan["files"] if f["status"] not in ("removed", "duplicate")),
                     "number_seq": seq},
            "documents": [{k: v for k, v in d.items() if not k.startswith("_")} for d in docs] + carried_docs,
            "agreements": agreements, "events": events, "commercials": commercials, "guarantees": guarantees,
            "key_clauses": key_clauses, "footnotes": notes, "timeline": timeline,
            "counterparties": sorted(cps.values(), key=lambda c: c["name"]), "registers": registers,
            "review_queue": review, "catalog": ev_cat, "key_clause_labels": catalog.load_key_clauses()}
