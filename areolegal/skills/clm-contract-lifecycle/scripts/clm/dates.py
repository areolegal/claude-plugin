"""גזירת מועדים: מועד יעד לטיפול, מועד חוזר, מצב המועד, תזכורת הבאה ופעולה.

עיקרון מחייב: מועד שחלף אינו נסגר אוטומטית. הוא נשאר "באיחור" כשיש חובה פתוחה,
או "חלף, ממתין לאישור תוצאה" כשהמערכת אינה יודעת מה קרה. רק אדם סוגר.
מועד חוזר מגולגל למופע הבא, והמופע האחרון שחלף נשאר פריט פתוח נפרד (occurrence: passed).
בחידוש אוטומטי שחלף, ההסכם מוצג כמתחדש (renewed), והמופע שחלף מבקש לאמת שההסכם התחדש.
"""
import calendar
import datetime as dt

from clm.i18n import t

STATES = {"upcoming", "pending_trigger", "missing", "needs_action", "lapsed_pending"}
LADDER = (14, 7, 3, 1, 0)
GENERIC = ("לבחון את הסעיף", "לפעול לפי הנדרש", "Review the clause", "Act as required")
RENEWING = {"term_end", "nonrenewal_notice", "auto_renewal"}
NEEDS_ACTION_NOTE = {
    "term_end": ("תום התקופה חלף. לאשר אם ההסכם הסתיים, הוארך או התחדש",
                 "The term has ended. Confirm whether the agreement ended, was extended or renewed"),
    "guarantee_expiry": ("הערבות פקעה. לוודא שהומצאה ערבות חדשה בתוקף",
                         "The guarantee has expired. Make sure a new valid guarantee was provided"),
}
HINT = {"right_lapses": ("האם מומש או פקע", "was it exercised or did it lapse"),
        "opportunity": ("האם מומש או לא נוצל", "was it used or not"),
        "auto_change": ("האם השינוי נכנס לתוקף כפי שנקבע", "did the change take effect as set"),
        "we_breach": ("האם בוצע", "was it done"),
        "they_breach_monitor": ("האם הצד שכנגד קיים", "did the other side comply")}


def _hint(cons):
    return t(*HINT[cons])


def parse(s):
    return dt.date.fromisoformat(s) if s else None


def fmt(d):
    return "%d.%d.%d" % (d.day, d.month, d.year) if d else ""


def add_months(d, months):
    y, m = divmod(d.month - 1 + months, 12)
    y, m = d.year + y, m + 1
    return dt.date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def is_month_end(d):
    return d.day == calendar.monthrange(d.year, d.month)[1]


def add_months_eom(d, months):
    """כמו add_months, אך תאריך שהוא סוף חודש נשאר בסוף החודש של היעד (28.2.2023 ועוד 12 חודשים: 29.2.2024)."""
    r = add_months(d, months)
    return dt.date(r.year, r.month, calendar.monthrange(r.year, r.month)[1]) if is_month_end(d) else r


def term_end_after(start, months):
    """סיום תקופה קצובה: היום שלפני אותו יום בחודש היעד. כשאותו יום אינו קיים בחודש היעד (31.1 ועוד חודש), סוף חודש היעד.
    1.3.2025 ועוד 12: 28.2.2026. 15.5.2025 ועוד 6: 14.11.2025. 31.1.2025 ועוד 1: 28.2.2025. 29.2.2024 ועוד 12: 28.2.2025."""
    r = add_months(start, months)
    return r if r.day < start.day else r - dt.timedelta(days=1)


def _positive_int(v):
    return isinstance(v, int) and not isinstance(v, bool) and v > 0


def _next_reminder(act_by, today):
    for k in LADDER:
        d = act_by - dt.timedelta(days=k)
        if d >= today:
            return d.isoformat()
    return today.isoformat()


def _passed(ev, prefix=None):
    """מצב של מועד שחלף בלי מופע עתידי: "באיחור" כשיש חובה פתוחה, אחרת "חלף, ממתין לאישור תוצאה"."""
    code, cons = ev["event_code"], ev["consequence"]
    if code in NEEDS_ACTION_NOTE:
        return "needs_action", t(*NEEDS_ACTION_NOTE[code])
    head = prefix or t("המועד חלף", "The date has passed")
    if cons == "we_breach":
        return "needs_action", head + t(", והחובה עדיין דורשת טיפול", ", and the duty still needs handling")
    return "lapsed_pending", head + t(". לאשר מה קרה: ", ". Confirm what happened: ") + _hint(cons)


def _passed_occurrence(main, ev, when, renewal):
    """המופע האחרון שחלף של מועד שגולגל. נשאר פתוח עד שאדם מסמן מה קרה (החלטת אנוש, פריט 4)."""
    if renewal:
        state = "needs_action" if ev["consequence"] == "we_breach" else "lapsed_pending"
        note = t("המועד מיום %s חלף וההסכם התחדש לכאורה מכוח סעיף החידוש. לאמת שההסכם התחדש",
                 "The date of %s has passed, and the agreement appears to have renewed under its renewal clause. "
                 "Confirm that it renewed") % fmt(when)
    elif ev["consequence"] == "we_breach":
        state, note = "needs_action", t("המועד החוזר מיום %s חלף, והחובה עדיין דורשת טיפול. לאשר שבוצע",
                                        "The recurring date of %s has passed, and the duty still needs handling. "
                                        "Confirm it was done") % fmt(when)
    else:
        state, note = "lapsed_pending", t("המועד החוזר מיום %s חלף. לאשר מה קרה: %s",
                                          "The recurring date of %s has passed. Confirm what happened: %s") % (
            fmt(when), _hint(ev["consequence"]))
    p = dict(main)
    p.update(date=when.isoformat(), act_by=None, next_reminder=None, state=state, state_note=note, action=note,
             history=[], derived=when.isoformat() != ev.get("date"), renewed=False, occurrence="passed",
             renewal_check=renewal)
    return p


def derive_all(ev, today, events_catalog, role_confirmed=True, cp=None):
    """המועד המחושב, ואחריו, כשהמועד גולגל, המופע האחרון שחלף כפריט פתוח נפרד."""
    c = events_catalog[ev["event_code"]]
    cp = cp or t("הצד שכנגד", "the other side")
    out = dict(ev)
    date = parse(ev.get("date"))
    history, note, renewal = [], "", False
    rec = ev.get("recurrence") or {}
    step = rec.get("months") if c["rollable"] else None
    if not _positive_int(step):
        step = None
    limit = rec.get("max") if step else None
    if not step and ev["event_code"] in RENEWING and _positive_int(ev.get("renewal_months")):
        step, limit, renewal = ev["renewal_months"], ev.get("renewal_max"), True
    if ev.get("relative") or (date is None and ev.get("trigger")):
        state = "pending_trigger"
    elif date is None:
        state, note = "missing", t("המועד אינו כתוב בהסכם. להשלים", "The agreement gives no date. Fill it in")
    elif date < today and step:
        anchor, n, add = date, 0, (add_months_eom if renewal else add_months)
        while date < today and (limit is None or n < limit):
            history.append(date.isoformat())
            n += 1
            date = add(anchor, step * n)
        if date < today:
            state, note = _passed(ev, t("המועד החוזר האחרון שבהסכם חלף", "The last recurring date in the agreement has passed"))
        else:
            state, note = "upcoming", t("מועד חוזר: מחושב מהמחזור הקודם (%s)",
                                        "Recurring date: computed from the previous cycle (%s)") % fmt(parse(history[-1]))
    elif date < today:
        state, note = _passed(ev)
    else:
        state = "upcoming"
    act_by = date - dt.timedelta(days=c["lead_days"]) if state == "upcoming" else None
    rolled = bool(history) and state == "upcoming"
    out.update(date=date.isoformat() if date else None, contract_date_original=ev.get("date"),
               act_by=act_by.isoformat() if act_by else None, lead_days=c["lead_days"],
               state=state, state_note=note, history=history, derived=bool(history),
               category=c["category"], critical=c["critical"], role_pending=not role_confirmed,
               if_nothing=ev.get("if_nothing") or c["if_nothing"],
               next_reminder=_next_reminder(act_by, today) if act_by else None, status="open",
               renewed=renewal and rolled)
    if state in ("needs_action", "lapsed_pending"):
        out["action"] = note
    elif history or not ev.get("action") or any(g in ev["action"] for g in GENERIC):
        nd = ev.get("notice_days")
        when = t("המועד", "the date")
        notice = t(" (הודעה של %d יום מראש)", " (%d day's notice)" if nd == 1 else " (%d days' notice)") % nd if nd else ""
        out["action"] = c["action"].format(cp=cp, date=fmt(date) or when, act_by=fmt(act_by) or when,
                                           notice=notice, title=ev["label"])
    if rolled:
        return [out, _passed_occurrence(out, ev, parse(history[-1]), renewal)]
    return [out]


def derive(ev, today, events_catalog, role_confirmed=True, cp=None):
    return derive_all(ev, today, events_catalog, role_confirmed=role_confirmed, cp=cp)[0]
