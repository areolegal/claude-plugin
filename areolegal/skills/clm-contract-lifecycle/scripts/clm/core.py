"""ליבה מורחבת (שלב ב): תקופה, חידוש, יציאה, חותמים, שיפוט, תנאי תשלום ועובדות.

הכללים: ערך שלא נכתב נשאר None; ערך מחושב מסומן "מחושב" (Computed), עם נוסחה בטקסט. אין סגירה אוטומטית של מועד ואין שינוי
אוטומטי של מצב. צד החברה אינו מוסק: צד נקבע רק לפי התאמת שם לשמות החברה או לצד שכנגד, או לפי ערך המחלץ כשצד
החברה אושר. הקובץ אינו מייבא את assemble, כדי שלא ייווצר ייבוא מעגלי.
"""
import datetime as dt
import re

from clm import catalog, dates
from clm.i18n import t

RESTRICTION_CODES = ("exclusivity", "non_compete", "mfn")
COC_CODES = ("change_of_control", "assignment")
BOUND = ("contracting", "both")
NOT_RELEVANT_TERMS = ("indefinite", "until_event", "project", "none")
LEGAL_FORMS = {"בעמ", "ltd", "inc", "llc", "gmbh", "bv", "sa", "limited"}
OPTION_NOTE = "הסיום נשאר עד אישור מימוש או תיקון חתום"
OPTION_NOTE_EN = "The end stands until an exercise is confirmed or an amendment is signed"
add_months = dates.add_months


def norm_entity(s):
    return " ".join(str(s or "").replace("״", '"').replace("׳", "'").split()).casefold()


def count(n, he_one, he_many, en_one, en_many):
    """מספר ושם עצם, ביחיד כשהמספר 1: "חידוש אחד" / "3 חידושים", "1 renewal" / "3 renewals"."""
    if n == 1:
        return t(he_one, "1 " + en_one)
    return t("%d %s" % (n, he_many), "%d %s" % (n, en_many))


def _by(clause):
    return t(" לפי %s", " under %s") % clause if clause else ""


def _posint(v):
    return isinstance(v, int) and not isinstance(v, bool) and v > 0


def _names(x):
    return [x] if isinstance(x, str) else [n for n in (x or []) if isinstance(n, str)]


def _tokens(s):
    """מילות שם הישות: בלי תוכן בסוגריים (\"(הספק)\"), בלי פיסוק ובלי צורת התאגדות (בע"מ, Ltd, Inc ...)."""
    s = re.sub(r"\([^)]*\)", " ", norm_entity(s))
    s = re.sub(r"[.\"'`]", "", s)
    return [t for t in re.sub(r"[^\w]+", " ", s).split() if t not in LEGAL_FORMS]


def _run_in(short, long):
    return any(long[i:i + len(short)] == short for i in range(len(long) - len(short) + 1))


def _same(a, b):
    """התאמת שם לפי מילים שלמות: זהות, או רצף רציף של אחד בתוך השני. לפחות שתי מילים, או מילה אחת של 4 תווים ויותר.
    זהות מלאה של הרצף (אחרי ניקוי) מספיקה."""
    a, b = _tokens(a), _tokens(b)
    if a and a == b:
        return len(" ".join(a)) >= 3
    short, long = (a, b) if len(a) <= len(b) else (b, a)
    if not short or (len(short) == 1 and len(short[0]) < 4):
        return False
    return _run_in(short, long)


def resolve_party(raw, name, company, counterparty, role_confirmed):
    """(צד, ודאי). הצד: counterparty | contracting | both | unknown. both (הדדי) גובר על הכול: סעיף הדדי מחייב כל צד
    ויהיו השמות אשר יהיו, וזה אינו תלוי בצד החברה. אחרת שם גובר; אחריו הערך המחולץ."""
    if raw == "both":
        return "both", True
    ours = any(_same(name, c) for c in _names(company))
    theirs = _same(name, counterparty)
    if ours != theirs:
        return ("contracting", True) if ours else ("counterparty", True)
    if ours and theirs:
        return "unknown", False
    if raw in ("contracting", "counterparty"):
        return raw, bool(role_confirmed)
    return "unknown", False


def computed_end(term, start):
    """(סיום, הערה) לתקופה קצובה: תחילה ועוד חודשים, פחות יום. אחרת (None, None)."""
    if not term or term.get("kind") != "fixed" or not _posint(term.get("initial_months")) or not start:
        return None, None
    s = dates.parse(start)
    end = dates.term_end_after(s, term["initial_months"])
    return end.isoformat(), t("מחושב: תחילה %s ועוד %d חודשים, פחות יום%s",
                              "Computed: start %s plus %d months, less one day%s") % (
        dates.fmt(s), term["initial_months"], _by(term.get("clause")))


def start_for(term, dts):
    """תאריך התחילה של התקופה לפי starts_on (ברירת מחדל: תחילת ההסכם). other: לא ידוע."""
    which = (term or {}).get("starts_on") or "start"
    return dts.get(which) if which in ("start", "signed") else None


def roll(end_iso, renewal, today):
    """(סיום מגולגל, מספר חידושים, הערה) לחידוש אוטומטי שחלף; אחרת (None, 0, None). אינו סוגר דבר."""
    if not end_iso or not renewal or renewal.get("kind") != "auto" or not _posint(renewal.get("period_months")):
        return None, 0, None
    end0, per, cap = dates.parse(end_iso), renewal["period_months"], renewal.get("max_count")
    cur, n = end0, 0
    while cur < today and (cap is None or n < cap):
        n += 1
        cur = dates.add_months_eom(end0, per * n)
    if not n:
        return None, 0, None
    head = t("מחושב: %s ועוד %s של %s%s", "Computed: %s plus %s of %s%s") % (
        dates.fmt(end0), count(n, "חידוש אחד", "חידושים", "renewal", "renewals"),
        count(per, "חודש אחד", "חודשים", "month", "months"), _by(renewal.get("clause")))
    if cur < today:
        return cur.isoformat(), n, head + t("; הגיע למספר החידושים המרבי (%d); לאמת את מצב ההסכם",
                                            "; reached the maximum number of renewals (%d); confirm the agreement's status") % n
    return cur.isoformat(), n, head + t("; לאמת שההסכם התחדש", "; confirm that the agreement renewed")


def current_end(end_iso, term, renewal, today, signed=True):
    """סיום התקופה הנוכחית כשאין גלגול ממועדים: (תאריך, בסיס, הערת אימות) או (None, None, None) לשלב א."""
    if signed:
        iso, _n, note = roll(end_iso, renewal, today)
        if iso:
            return iso, {"kind": "auto_renewal", "note": note}, note
    if (term or {}).get("kind") == "indefinite" and not end_iso:
        return None, {"kind": "indefinite", "note": t("ללא הגבלת זמן", "No end date")}, None
    if (renewal or {}).get("kind") in ("option", "mutual") and end_iso:
        return end_iso, {"kind": "option_pending", "note": t(OPTION_NOTE, OPTION_NOTE_EN)}, None
    return None, None, None


def max_end(term, renewal, end_iso, head_events):
    """(תאריך, סוג בסיס, הערה): extracted | derived | deadline. אחרת (None, None, None)."""
    if (term or {}).get("max_end"):
        return term["max_end"], "extracted", (t("לפי %s", "Under %s") % term["clause"]) if term.get("clause") else ""
    r = renewal or {}
    if end_iso and r.get("kind") in ("auto", "option") and _posint(r.get("period_months")) and _posint(r.get("max_count")):
        d = dates.add_months_eom(dates.parse(end_iso), r["period_months"] * r["max_count"])
        return d.isoformat(), "derived", t("מחושב: %s ועוד %s של %s", "Computed: %s plus %s of %s") % (
            dates.fmt(dates.parse(end_iso)), count(r["max_count"], "תקופה אחת", "תקופות", "period", "periods"),
            count(r["period_months"], "חודש אחד", "חודשים", "month", "months"))
    cands = [e for e in head_events if e["event_code"] == "term_end" and e.get("term_role") == "max_end"
             and not e.get("relative") and e.get("contract_date_original") and e.get("occurrence") != "passed"]
    if cands:
        e = max(cands, key=lambda x: x["contract_date_original"])
        return e["contract_date_original"], "deadline", t("לפי המועד: ", "From the date: ") + e["label"]
    return None, None, None


def survival_end(events):
    """(תאריך, תווית) של פקיעת ההתחייבות השורדת האחרונה. אחרת (None, None)."""
    cands = [e for e in events if e["event_code"] == "post_term" and not e.get("relative")
             and e.get("contract_date_original") and e.get("occurrence") != "passed"]
    if not cands:
        return None, None
    e = max(cands, key=lambda x: x["contract_date_original"])
    return e["contract_date_original"], e["label"]


def signatories(rows, company, counterparty, role_confirmed):
    """חותמים, שורה לשורה לפי סדר החילוץ, עם הצד שנקבע. הפניות מתווספות בהרכבה."""
    out = []
    for r in rows or []:
        party, certain = resolve_party(r.get("party"), r.get("party_name"), company, counterparty, role_confirmed)
        out.append({"party": party, "party_certain": certain, "party_name": r.get("party_name"),
                    "name": r.get("name"), "role": r.get("role"), "date": r.get("date"), "status": r.get("status")})
    return out


def _party_of(x, field, name_field, company, counterparty, confirmed):
    raw = x.get(field)
    if raw == "none":
        return "none", True
    party, certain = resolve_party(raw, x.get(name_field), company, counterparty, confirmed)
    return (None if raw is None and party == "unknown" else party), certain


def agreement_fields(ext, rf, company, counterparty, confirmed):
    """term, renewal, exit, signatories, jurisdiction, payment_terms של ההסכם מהמסמך הראשי.

    rf(clause, quote): הפניה לציטוט. שדה שאינו בחילוץ נשאר None, וחותמים: רשימה ריקה."""
    def refs(x):
        return rf(x.get("clause"), x.get("quote"))
    out = {"term": None, "renewal": None, "exit": None, "jurisdiction": None, "payment_terms": None}
    t, r, x, j, p = (ext.get(k) for k in ("term", "renewal", "exit", "jurisdiction", "payment_terms"))
    if t:
        out["term"] = {"kind": t.get("kind"), "initial_months": t.get("initial_months"), "starts_on": t.get("starts_on"),
                       "trigger": t.get("trigger"), "refs": refs(t)}
    if r:
        holder, certain = _party_of(r, "holder", "holder_name", company, counterparty, confirmed)
        out["renewal"] = {"kind": r.get("kind"), "period_months": r.get("period_months"), "max_count": r.get("max_count"),
                          "holder": holder, "holder_certain": certain, "holder_name": r.get("holder_name"),
                          "notice_days": r.get("notice_days"), "clause": r.get("clause"), "refs": refs(r)}
    if x:
        who, certain = _party_of(x, "who", "who_name", company, counterparty, confirmed)
        out["exit"] = {"who": who, "who_certain": certain, "who_name": x.get("who_name"),
                       "notice_days": x.get("notice_days"), "min_commitment_months": x.get("min_commitment_months"),
                       "refs": refs(x)}
    if j:
        out["jurisdiction"] = {"court": j.get("court"), "exclusive": j.get("exclusive"), "refs": refs(j)}
    if p:
        out["payment_terms"] = {"days": p.get("days"), "basis": p.get("basis"), "text": p.get("text"), "refs": refs(p)}
    rows = ext.get("signatories") or []
    out["signatories"] = signatories(rows, company, counterparty, confirmed)
    for s, row in zip(out["signatories"], rows):
        s["refs"] = refs(row)
    return out


def facts(sources, rf):
    """עובדות מהמסמך הראשי ומהמסמכים הקשורים. sources: [(קובץ, חילוץ)]; rf(clause, quote, file)."""
    return [{"code": f.get("code"), "label": f.get("label"), "value": f.get("value"), "file": file,
             "refs": rf(f.get("clause"), f.get("quote"), file)}
            for file, sx in sources for f in sx.get("facts") or []]


def term_passed(state, dts, current, today):
    """הסכם חתום במצב in_force שסיומו (או סיום התקופה הנוכחית) קדם להיום: term_passed_unverified. אחרת אותו מצב."""
    end = current if current is not None else dts.get("end")
    if state == "in_force" and end and dates.parse(end) < today:
        return "term_passed_unverified"
    return state


def missing_party_sides(sigs):
    """תוויות חסר: חותמים לצד שכנגד / לחברה. ברשימה ריקה כבר נאמר "חותמים". צד לא ידוע אינו נספר לאף צד."""
    if not sigs:
        return []
    parties = {s.get("party") for s in sigs if s.get("party_certain")}
    return [label for label, side in ((t("חותמים לצד שכנגד", "Signatories for the other side"), "counterparty"),
                                      (t("חותמים לחברה", "Signatories for the company"), "contracting"))
            if side not in parties]


def key_clause_fields(row, company, counterparty, confirmed, today):
    """שדות הצד, העמדה והתוקף של שורת סעיף מפתח. צד שלא נקבע: unknown, לא ודאי. סעיף בלי until פעיל."""
    party, certain = resolve_party(row.get("bound_party"), row.get("bound_party_name"), company, counterparty, confirmed)
    norm = row.get("norm") if isinstance(row.get("norm"), dict) else None
    until = norm.get("until") if norm and isinstance(norm.get("until"), str) and norm.get("until") else None
    return {"bound_party": party, "bound_party_certain": certain, "bound_party_raw": row.get("bound_party"),
            "bound_party_name": row.get("bound_party_name"),
            "stance": row.get("stance") or "set", "norm": norm, "active_until": until,
            "active": until is None or until >= today.isoformat()}


def _requires(norm):
    """True: נדרשת הסכמה או הודעה. False: כתוב במפורש שלא. None: לא כתוב או לא מזוהה (אין norm, ערך זר, מחרוזת
    במקום בוליאני), ואז הסעיף הולך לבדיקה כשהחברה מחויבת או עשויה להיות מחויבת."""
    if not isinstance(norm, dict):
        return None
    req, consent = norm.get("requires"), norm.get("consent_required")
    if req in ("consent", "notice") or consent is True:
        return True
    if req in ("none", "termination_right") or consent is False:
        return False
    return None


def _until(row):
    """תאריך הסיום כמחרוזת ISO בלבד; אחרת None (הסעיף פעיל)."""
    until = row.get("active_until")
    if until is None and isinstance(row.get("norm"), dict):
        until = row["norm"].get("until")
    return until if isinstance(until, str) and until else None


def _active(row, today):
    until = _until(row)
    return until is None or until >= today.isoformat()


def _order(row, party, today):
    """מפתח מיון: מחויב רק החברה לפני שני הצדדים; בכל אחד, פעיל עם active_until קודם, לפי התאריך. הפעילות נמדדת מול היום."""
    until = _until(row)
    return (0 if party == "contracting" else 1 if party == "both" else 2,
            not _active(row, today), until is None, until or "")


def registers(agreements, key_clauses, checked_ids, today):
    """מרשמי מגבלות ושינוי שליטה, כל אחד עם רשימת "לבדיקה". נספרים רק הסכמים חתומים (signed_unverified): טיוטה עדיין
    אינה מגבילה איש. הצד קובע: רק צד החברה הוודאי נספר, צד לא ידוע או לא
    ודאי הולך לבדיקה, וצד שכנגד ודאי אינו נספר. סעיף שנקבע במפורש שאינו קיים (expressly_none) אינו נספר ואינו לבדיקה.
    כל הרשימות None כשלא נבדק אף הסכם."""
    keys = ("restrictions", "restrictions_review", "change_of_control", "change_of_control_review")
    if not checked_ids:
        return dict({k: None for k in keys}, restriction_details=None)
    labels = catalog.load_key_clauses()
    unsigned = {a["id"] for a in agreements if a.get("signature") != "signed_unverified"}
    by_ag = {}
    for r in key_clauses:
        if r.get("agreementId") in checked_ids and r.get("agreementId") not in unsigned                 and (r.get("stance") or "set") == "set":
            by_ag.setdefault(r["agreementId"], []).append(r)
    counted = {"restrictions": {}, "change_of_control": {}}
    review = {"restrictions": set(), "change_of_control": set()}
    for aid, rows in by_ag.items():
        for r in rows:
            party, certain = r.get("bound_party") or "unknown", bool(r.get("bound_party_certain"))
            bound = party in BOUND and certain
            if r.get("clause_code") in RESTRICTION_CODES:
                if not _active(r, today):
                    continue
                grp = "restrictions"
                state = "count" if bound else ("skip" if party == "counterparty" and certain else "review")
            elif r.get("clause_code") in COC_CODES:
                grp = "change_of_control"
                req = _requires(r.get("norm"))
                if req is False or (party == "counterparty" and certain):
                    state = "skip"
                elif req is True and bound:
                    state = "count"
                else:
                    state = "review"
            else:
                continue
            if state == "count":
                k = _order(r, party, today)
                counted[grp][aid] = min(counted[grp].get(aid, k), k)
            elif state == "review":
                review[grp].add(aid)
    for grp in counted:
        review[grp] -= set(counted[grp])
    details = {}
    for aid in sorted(set(counted["restrictions"]) | review["restrictions"]):
        rows = [r for r in by_ag.get(aid, []) if r.get("clause_code") in RESTRICTION_CODES]
        items = [{"code": r["clause_code"], "label": labels.get(r["clause_code"], r["clause_code"]),
                  "bound_party": r.get("bound_party") or "unknown",
                  "bound_party_certain": bool(r.get("bound_party_certain")), "active_until": r.get("active_until"),
                  "active": _active(r, today), "summary": r.get("summary"), "refs": list(r.get("refs") or [])}
                 for r in rows]
        items.sort(key=lambda d: (_order(d, d["bound_party"], today), d["code"], str(d["summary"] or "")))
        details[aid] = items
    def ranked(grp):
        return sorted(counted[grp], key=lambda aid: (counted[grp][aid], aid))

    return {"restrictions": ranked("restrictions"), "restrictions_review": sorted(review["restrictions"]),
            "change_of_control": ranked("change_of_control"),
            "change_of_control_review": sorted(review["change_of_control"]), "restriction_details": details}


# ---------- צד החברה מול הצדדים במסמך ----------
# שני צדדים כלליים, לכל סוג הסכם ודין: provider (נותן: ספק, מעבד, משכיר, מעניק רישיון, מוכר, מלווה, מבטח, קבלן)
# ו-customer (מקבל: לקוח, מזמין, שוכר, בעל רישיון, קונה, לווה, מבוטח, בעל המאגר / controller). מילה שאינה ברשימה
# אינה מכריעה, ולכן אינה יוצרת סתירה.
SIDE_WORDS = {
    "provider": {"ספק", "ספקית", "נותן", "נותנת", "מעבד", "מעבדת", "מחזיק", "מחזיקה", "קבלן", "קבלנית", "יועץ", "יועצת",
                 "משכיר", "משכירה", "מחכיר", "מחכירה", "מוכר", "מוכרת", "מעניק", "מעניקה", "מלווה", "מבטח", "מבטחת",
                 "עובד", "עובדת", "provider", "supplier", "vendor", "processor", "subprocessor", "sub-processor",
                 "contractor", "consultant", "licensor", "lessor", "landlord", "seller", "lender", "insurer",
                 "franchisor", "employee", "manufacturer"},
    "customer": {"לקוח", "לקוחה", "מזמין", "מזמינה", "שוכר", "שוכרת", "חוכר", "חוכרת", "קונה", "רוכש", "רוכשת",
                 "לווה", "מבוטח", "מבוטחת", "זכיין", "זכיינית", "מעסיק", "מעסיקה", "customer", "client", "buyer",
                 "purchaser", "licensee", "lessee", "tenant", "borrower", "insured", "franchisee", "employer",
                 "controller", "subscriber"},
}
SIDE_PHRASES = {"customer": ("בעל המאגר", "בעל השליטה", "מקבל השירות", "מקבלת השירות"),
                "provider": ("נותן השירות", "נותנת השירות", "service provider")}


def role_side(text):
    """provider / customer לתווית תפקיד (בעברית או באנגלית), או None כשאין הכרעה (אין מילה מוכרת, או מילים משני הצדדים)."""
    if not isinstance(text, str) or not text.strip():
        return None
    low = text.replace("״", '"').lower()
    found = {side for side, phrases in SIDE_PHRASES.items() if any(ph in low for ph in phrases)}
    for tok in re.findall(r"[\w\-]+", low):
        for cand in (tok, tok[1:] if tok[:1] in "הו" and len(tok) > 3 else tok, tok[2:] if tok[:2] == "וה" else tok):
            for side, words in SIDE_WORDS.items():
                if cand in words:
                    found.add(side)
    return found.pop() if len(found) == 1 else None


def side_conflict(pb_role, ext):
    """הערת סתירה כשהמסמך סותר את צד החברה שבפלייבוק; אחרת "". נבדקים: תפקיד הצד שכנגד בהסכם (counterparty.role),
    תפקיד החברה בהסכם (contracting_role), וההשערה מהקריאה (our_role.value כשאינו מאושר)."""
    ours = role_side(pb_role)
    if not ours:
        return ""
    cp = ext.get("counterparty") or {}
    cp_role, us_role = cp.get("role"), ext.get("contracting_role")
    if role_side(cp_role) == ours:
        return t("בהסכם, %s מוגדר כ\"%s\", וזה הצד שהפלייבוק מייחס לחברה: %s",
                 "In the agreement, %s is named \"%s\", which is the side the playbook gives the company: %s") % (
            cp.get("name") or t("הצד שכנגד", "the other side"), cp_role, pb_role)
    if role_side(us_role) and role_side(us_role) != ours:
        return t("בהסכם, החברה מוגדרת כ\"%s\", והפלייבוק מייחס לה צד אחר: %s",
                 "In the agreement, the company is named \"%s\", and the playbook gives it another side: %s") % (
            us_role, pb_role)
    guess = ext.get("our_role") or {}
    if guess.get("source") in ("suggested", "none") and role_side(guess.get("value")) not in (None, ours):
        return t("ההשערה מהחילוץ (%s) שונה מצד החברה בפלייבוק (%s)",
                 "Our reading of the agreement (%s) differs from the company's side in the playbook (%s)") % (
            guess["value"], pb_role)
    return ""
