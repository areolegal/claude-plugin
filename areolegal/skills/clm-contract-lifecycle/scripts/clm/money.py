"""שווי ההסכם: מטבע לכל שורת תמורה, שווי שנתי לכל מטבע, ושווי אפקטיבי אחרי תיקון.

כללים:
- אין מטבע ברירת מחדל. המטבע של שורה נלקח מהשדה currency שבה, אחר כך מהיחידה, אחר כך מהתווית, ואחר
  כך מהמטבע שבמסמך. בלי אף אחד מהם השורה "במטבע לא ידוע", אינה נספרת ונרשמת ב-unknown_currency.
- מטבעות שונים אינם מחוברים: השווי השנתי הוא מילון {מטבע: סכום}.
- נספרות רק שורות שהקטגוריה שלהן תמורה (VALUE_CATS), שהערך שלהן מספר ושהתקופה שלהן חודשית או שנתית.
- תעריף ליחידה (היחידה או התקופה כוללות "לעמדה", "לשעה", "למהנדס", "per seat" וכדומה) אינו נספר, כי הוא
  תלוי בהיקף שאינו כתוב. הוא נרשם ב-not_counted עם הסיבה.
- שדות מובנים (שלב ב), כשהם כתובים בשורה, גוברים על הטקסט: value_kind "unit" או basis "usage" אינם נספרים (ליחידה),
  "total" (סכום כולל) ו-"max" (תקרה) אינם נספרים, "monthly" ו-"annual" קובעים את התקופה, basis "estimate" מסמן אומדן.
  בלי השדות ההתנהגות כבשלב א.
- מטבע שנכתב במפורש (קוד של שלוש אותיות, למשל CHF) נשמר כפי שהוא, גם כשאינו ברשימת הסימנים המוכרים.
  שום ברירת מחדל אינה משנה אותו; מטבע המסמך משמש רק כשבשורה אין מטבע כלל.
- שורת תמורה מתיקון חתום (_rank = תאריך החתימה שלו) חייבת להצביע על רכיב מסוים (component), על פעולה
  (operation: replace | add | delete) ועל תאריך תוקף (effective_date). הפעולה חלה על אותו רכיב בלבד; שאר
  הרכיבים נשארים. השווי הוא סכום הרכיבים, ו-components מפרט שורה לכל רכיב. תיקון כספי שחסר בו אחד משלושת
  הפרטים אינו נספר ונרשם ב-not_counted. תיקונים באותו רכיב חלים לפי תאריך התוקף, ואחריו תאריך החתימה.
"""
import re

from clm.i18n import t

VALUE_CATS = ("תעריף", "דמי מנוי")
# לכל מטבע: סימנים ותיבות (נמצאים גם בתוך מילה), מילים בעברית (מילה שלמה, עם אות שימוש אחת בראשה
# ועם סיומת רבים "ים"), וקודים באותיות לטיניות (רק כשאין אות לטינית צמודה).
CURRENCIES = (
    ("ILS", ("₪", 'ש"ח', "ש״ח"), ("שקל",), ("ILS", "NIS")),
    ("USD", ("$",), ("דולר",), ("USD",)),
    ("EUR", ("€",), ("אירו", "יורו"), ("EUR",)),
    ("GBP", ("£", 'ליש"ט', "ליש״ט"), ("פאונד", "לירה", "לירות", "שטרלינג"), ("GBP",)),
)
KNOWN = {c[0] for c in CURRENCIES}
PORTFOLIO_STATES = ("signed_not_effective", "in_force", "renewal_window", "extended")
NOT_PER_UNIT = {"לחודש", "לשנה", "לרבעון", "לפני", "לרבות", "ללא", "לאחר", "לפי", "לתקופה", "לשנים", "לחודשים"}
HEB_WORD = re.compile("[\u05d0-\u05ea\"\u05f4']+")
ENG_PER = re.compile(r"\bper\s+(?!month|year|annum|quarter)[a-z]", re.I)


def _compile(symbols, words, codes):
    parts = [re.escape(m) for m in symbols]
    parts += ["(?<![א-ת])[בהולמש]?%s(?:ים)?(?![א-ת])" % re.escape(w) for w in words]
    parts += ["(?<![A-Za-z])%s(?![A-Za-z])" % c for c in codes]
    return re.compile("|".join(parts), re.I)


_PATTERNS = [(code, _compile(sym, words, codes)) for code, sym, words, codes in CURRENCIES]


def _marks(text):
    if not isinstance(text, str) or not text.strip():
        return set()
    return {code for code, pat in _PATTERNS if pat.search(text)}


ISO_CODE = re.compile(r"^[A-Za-z]{3}$")
OPERATIONS = ("replace", "add", "delete")
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def explicit_code(v):
    """קוד מטבע של שלוש אותיות כפי שנכתב (באותיות גדולות), או None. אינו מצריך שהמטבע יהיה ברשימת הסימנים."""
    if isinstance(v, str) and ISO_CODE.match(v.strip()):
        return v.strip().upper()
    return None


def currency_of(row, fallback=None):
    cur = row.get("currency")
    if explicit_code(cur):
        return explicit_code(cur)
    for text in (row.get("unit"), row.get("label")):
        found = _marks(text)
        if len(found) == 1:
            return found.pop()
        if found:
            return None
    if explicit_code(fallback):
        return explicit_code(fallback)
    found = _marks(fallback)
    return found.pop() if len(found) == 1 else None


PER_PERIOD = re.compile(r"לכל\s+(?:חודש|שנה|רבעון)")


def per_unit(row):
    text = " ".join(str(row.get(k) or "") for k in ("unit", "period"))
    # סימני מטבע ומילות מטבע (ובהן "ליש"ט", "לירות") אינם יחידה; וכך גם "לכל חודש", "לכל שנה"
    for _, pat in _PATTERNS:
        text = pat.sub(" ", text)
    text = PER_PERIOD.sub(" ", text)
    for tok in HEB_WORD.findall(text):
        if tok.startswith("ל") and len(tok) >= 3 and tok not in NOT_PER_UNIT:
            return True
    return bool(ENG_PER.search(text))


def _kind(row):
    p = str(row.get("period") or "")
    if p == "חודשי":
        return "monthly"
    if p.startswith("שנתי"):
        return "annual"
    return None


def _number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def tidy(by):
    """מילון {מטבע: סכום} ממוין לפי מטבע; מספר שלם כ-int, אחרת עיגול לשתי ספרות."""
    return {k: (int(v) if float(v).is_integer() else round(v, 2)) for k, v in sorted(by.items())}


PER_UNIT_REASON = ("תעריף ליחידה, תלוי בהיקף", "Rate per unit, depends on volume")


AMEND_INCOMPLETE = ("תיקון כספי בלי רכיב, פעולה או תאריך תוקף, לא נספר",
                    "Money amendment without a component, an operation or an effective date, not counted")


def _ckey(category, name, idx):
    text = " ".join(str(name or "").split()).casefold()
    return (category, text or "#%d" % idx)


def _entry(r, fallback_currency, not_counted, unknown):
    """רכיב לספירה משורה, או None (ואז הסיבה כבר נרשמה). שורה ללא ערך מספרי אינה רכיב."""
    vk, basis = r.get("value_kind"), r.get("basis")
    reason = (t(*PER_UNIT_REASON) if vk == "unit" or basis == "usage" else
              t("סכום כולל, לא שנתי", "Total amount, not annual") if vk == "total" else
              t("תקרה, לא שווי", "A cap, not a value") if vk == "max" else None)
    if reason:
        not_counted.append({"label": r.get("label") or "", "reason": reason})
        return None
    kind = vk if vk in ("monthly", "annual") else _kind(r)
    if not kind:
        return None
    if per_unit(r):
        not_counted.append({"label": r.get("label") or "", "reason": t(*PER_UNIT_REASON)})
        return None
    cur = currency_of(r, fallback_currency)
    if not cur:
        unknown.append(r.get("label") or "")
        return None
    est = "אומדן" in str(r.get("period") or "") or r.get("basis") == "estimate"
    return {"label": r.get("label") or "", "category": r.get("category"), "kind": kind, "cur": cur,
            "value": r["value"], "estimated": est}


def annual(rows, fallback_currency=None, as_of=None):
    """שווי שנתי לכל מטבע, מחושב לפי רכיבים. as_of (YYYY-MM-DD): תיקון שתאריך התוקף שלו מאוחר ממנו עוד לא חל."""
    not_counted, unknown = [], []
    comps = {}  # מפתח רכיב -> רשימת רכיבים (אפשר כמה שורות באותו שם בהסכם עצמו)
    ops = []
    for idx, r in enumerate(rows):
        if r.get("category") not in VALUE_CATS:
            continue
        rank = r.get("_rank") or ""
        label = r.get("label") or ""
        if not rank:
            if not _number(r.get("value")):
                continue
            e = _entry(r, fallback_currency, not_counted, unknown)
            if e:
                e.update(source="agreement", since="", effective="")
                comps.setdefault(_ckey(e["category"], label, idx), []).append(e)
            continue
        comp, op, eff = str(r.get("component") or "").strip(), r.get("operation"), r.get("effective_date")
        if not comp or op not in OPERATIONS or not isinstance(eff, str) or not ISO_DATE.match(eff):
            not_counted.append({"label": comp or label, "reason": t(*AMEND_INCOMPLETE)})
            continue
        if as_of and eff > as_of:
            not_counted.append({"label": comp, "reason": t("תיקון שטרם נכנס לתוקף", "An amendment not yet in effect")})
            continue
        ops.append((eff, rank, idx, comp, op, r))
    amended = ""
    for eff, rank, idx, comp, op, r in sorted(ops, key=lambda x: x[:3]):
        key = _ckey(r.get("category"), comp, idx)
        old = comps.get(key)
        if op == "add" and old:
            not_counted.append({"label": comp, "reason": t("הרכיב כבר קיים, להשתמש בהחלפה", "The component already exists, use replace")})
            continue
        if op in ("replace", "delete") and not old:
            not_counted.append({"label": comp, "reason": t("הרכיב לא נמצא בהסכם", "The component was not found in the agreement")})
            continue
        e = None
        if op != "delete":
            if not _number(r.get("value")):
                not_counted.append({"label": comp, "reason": t(*AMEND_INCOMPLETE)})
                continue
            e = _entry(r, fallback_currency, not_counted, unknown)
            if not e:
                continue
            e.update(label=comp, source="amendment", since=rank, effective=eff)
        for o in old or []:
            not_counted.append({"label": o["label"], "reason": t("הוחלף בתיקון להסכם", "Replaced by an amendment")
                                if op == "replace" else t("בוטל בתיקון להסכם", "Removed by an amendment")})
        comps.pop(key, None)
        if e:
            comps[key] = [e]
        amended = max(amended, rank)
    by, components, estimated = {}, [], False
    for lst in comps.values():
        for e in lst:
            annual_v = e["value"] * (12 if e["kind"] == "monthly" else 1)
            by[e["cur"]] = by.get(e["cur"], 0) + annual_v
            estimated = estimated or e["estimated"]
            components.append({"component": e["label"], "category": e["category"], "period": e["kind"], "currency": e["cur"],
                               "value": e["value"], "annual_value": annual_v, "source": e["source"],
                               "since": e["since"] or None, "effective_date": e["effective"] or None})
    components.sort(key=lambda c: (c["currency"], c["component"]))
    return {"by_currency": tidy(by), "components": components, "unknown_currency": unknown, "not_counted": not_counted,
            "amended_on": amended or None, "estimated": estimated}


def normalize(value, in_portfolio):
    """ערך של הסכם שנגרר מהרצה קודמת (ייתכן במבנה הישן) במבנה הנוכחי."""
    v = dict(value or {})
    if not isinstance(v.get("annual_by_currency"), dict):
        # המבנה הישן נתן מטבע ברירת מחדל ועירבב שורות: לא סומכים עליו, והשווי ממתין לחילוץ מחדש
        v["annual_by_currency"] = {}
        v["annual"] = None
        v["unknown_currency"] = list(v.get("unknown_currency") or []) + [
            t("שווי מהרצה קודמת, ממתין לחילוץ מחדש", "Value from an earlier run, waiting to be read again")]
    for k in ("not_counted", "unknown_currency"):
        v.setdefault(k, [])
    v.setdefault("total_currency", None)
    v.setdefault("components", [])
    v["in_portfolio"] = bool(in_portfolio)
    return v
