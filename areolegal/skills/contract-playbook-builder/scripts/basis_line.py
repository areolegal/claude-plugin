# -*- coding: utf-8 -*-
"""שורת הבסיס: על כמה הסכמים הפלייבוק נשען, ובאיזה מסלול נבנה.

אותו נוסח בדיוק מופיע בשער ה-Word (`word-export-spec.md`, "השער") ובפס
הבסיס בארטיפקט (`dashboard_spec.md`, "פס הבסיס"). הוא נגזר כאן ממקום אחד,
כדי ששני התוצרים לא יספרו אחרת, והוא נשען על `corpus_basis.agreement_units`
ועל `corpus_origin` ולא על מספר הקבצים בתיקייה.

בארטיפקט אותו נוסח ממומש ב-JavaScript בתוך התבנית, ו-`qa_basis_line.js`
משווה בין השניים בכל חמשת המצבים, כדי שלא ייווצר הפרש.

מעמד המאגר (`scope_summary.corpus_status`, `playbook-schema.md`) קובע איך
המסמכים נקראים בשורה. "הסכמים של החברה" נכתב רק כשהם הסכמים של החברה, ולא על
נוסחים שספקים אחרים פרסמו ברשת או על נייר של הצד שכנגד. במודל שלא כתב `corpus_status`, המעמד נגזר מ-`source_log`
(רוב טיוטות, או הסכמים חתומים). `basis_line(units, origin)` בלי מעמד מחזיר
את הנוסח הקודם, ולכן חמשת המצבים של `qa_basis_line.js` אינם משתנים.

המעמד עצמו נגזר במקום אחד, `playbook/status.py` (`corpus_status`), שממנו נגזרת
גם התווית הבסיסית. כאן נשאר הנוסח: שם המסמכים בעברית ובאנגלית (`DOCS`,
`DOCS_EN`), ושורת "פלייבוק ראשוני" (`PRELIMINARY`, `PRELIMINARY_EN`), שה-Word
ונתוני סביבת העבודה (`evidence_short`) קוראים מכאן.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # גם ב-python -I, שאינו מוסיף את תיקיית הסקריפט
import areo_lib  # noqa: F401  מוסיף את areolegal/lib לנתיב הייבוא
from playbook import status as S

AREO_TAG = 'הצעת Areo (לא מבוסס על מסמכי הלקוח)'

# איך המסמכים נקראים בשורה, לפי מעמד המאגר
DOCS = {
    "signed": "הסכמים של החברה",
    "mostly_drafts": "מסמכים של החברה, רובם טיוטות ולא הסכמים חתומים",
    "company_forms": "נוסחים שהחברה מציגה לצד שכנגד, ולא הסכמים חתומים",
    "third_party_forms": "נוסחים שאינם הסכמים חתומים של החברה",
    "unknown": "נוסחים שאינם הסכמים חתומים של החברה",
    # מאגר חתום שרובו נייר של הצד שכנגד (status.theirs_paper): התווית ושורת הבסיס אומרות זאת
    "theirs_paper": "נוסחים של הצד שכנגד שהחברה חתמה עליהם",
}

# שורת השער של פלייבוק ראשוני, מילה במילה (SKILL.md, "מאגר שרובו טיוטות"; "נוסחים שאינם של החברה")
PRELIMINARY = {
    "mostly_drafts": "פלייבוק ראשוני. נבנה ברובו מטיוטות ולא מהסכמים חתומים.",
    "company_forms": "פלייבוק ראשוני. נבנה מנוסחים שהחברה מציגה לצד שכנגד, ולא מהסכמים חתומים.",
    "third_party_forms": "פלייבוק ראשוני. נבנה מנוסחים שאינם הסכמים חתומים של החברה.",
    "unknown": "פלייבוק ראשוני. נבנה מנוסחים שאינם הסכמים חתומים של החברה.",
}
DRAFTS_LINE = PRELIMINARY["mostly_drafts"]

# המקבילות באנגלית, באותם מצבים, כמו basisText() בתבנית (qa_basis_line.js משווה ביניהם)
DOCS_EN = {
    "signed": "company agreements",
    "mostly_drafts": "company documents, most of them drafts and not signed agreements",
    "company_forms": "forms the company presents to its counterparties, not signed agreements",
    "third_party_forms": "forms that are not signed agreements of the company",
    "unknown": "forms that are not signed agreements of the company",
    "theirs_paper": "counterparty forms the company signed",
}
# כשנקראו מסמכים של החברה ואף מסלול אינו נשען עליהם (status.no_company_position), השורה אומרת זאת. התווית אומרת
# ממה המדיניות נבנתה, ואינה משתנה בגלל זה (status.base_code)
NO_COMPANY_POSITION = {"he": " אף עמדה בו אינה נשענת על מסמך של החברה: כל העמדות הן הצעת Areo.",
                       "en": " No position in it rests on a company document: every position is an Areo proposal."}
PRELIMINARY_EN = {
    "mostly_drafts": "Preliminary playbook. Built mostly from drafts, not from signed agreements.",
    "company_forms": "Preliminary playbook. Built from forms the company presents to its counterparties, "
                     "not from signed agreements.",
    "third_party_forms": "Preliminary playbook. Built from forms that are not signed agreements of the company.",
    "unknown": "Preliminary playbook. Built from forms that are not signed agreements of the company.",
}


def docs(status, lang="he"):
    """שם המסמכים לפי מעמד המאגר, בעברית או באנגלית: בשורת הבסיס, ב-evidence_short ובתמונת המצב ב-Word."""
    table = DOCS_EN if lang == "en" else DOCS
    return table.get(status) or table["signed"]


def agreement_units(model):
    """מספר המסמכים של החברה שעליהם נשען הפלייבוק, או None כשאין ספירה. טפסים של הצד שכנגד ושל גופים ציבוריים אינם
    נספרים כהסכמי החברה (status.company_agreements_counted)."""
    basis = ((model.get("scope_summary") or {}).get("corpus_basis") or {})
    n = basis.get("agreement_units")
    return S.company_agreements_counted(model) if isinstance(n, int) else None


def basis_line(units, origin, status=None):
    """הנוסח לפי מספר ההסכמים, לפי המסלול ולפי מעמד המאגר. None כשאין ספירה."""
    if not isinstance(units, int):
        return None
    if units == 0 or origin == "market_built":
        return ('נבנה לפי השוק, מותאם לפוזיציה של החברה, עם בדיקה רגולטורית מעמיקה. '
                'אין בו עמדה שנגזרה מהסכמי החברה, וכל עמדה בו מסומנת "%s".' % AREO_TAG)
    name = docs(status)
    if units >= 7 and origin == "own_plus_market":
        return ('נבנה מ-%d %s, בשילוב מחקר שוק. עמדה שמקורה בשוק '
                'מסומנת "%s".' % (units, name, AREO_TAG))
    if units >= 20:
        return 'נבנה מ-%d %s.' % (units, name)
    if units >= 7:
        return ('נבנה מ-%d %s. זה פחות מהמומלץ (כ-20), ולכן חלק מהעמדות '
                'נשענות על מעט משאים ומתנים.' % (units, name))
    if origin == "own_plus_market":
        return ('נבנה מ-%d %s, בשילוב מחקר שוק. עמדה שמקורה בשוק '
                'מסומנת "%s".' % (units, name, AREO_TAG))
    return ('נבנה מ-%d %s בלבד. לא מומלץ לבנות פלייבוק מפחות מ-20 הסכמים, '
            'והחברה בחרה שלא לשלב מחקר שוק.' % (units, name))


def corpus_status(model):
    """מעמד המאגר: מהמודל (`scope_summary.corpus_status`), ובמודל שלא כתב אותו, mostly_drafts כשרוב
    ההסכמים טיוטות, ואחרת signed. הגזירה ב-`playbook/status.py`, כדי שהתווית ושורת הבסיס יקראו אותו מעמד."""
    return S.corpus_status(model)


def line_for(model):
    """שורת הבסיס של מודל פלייבוק, או None כשאין במודל ספירה."""
    line = basis_line(agreement_units(model),
                      (model.get("scope_summary") or {}).get("corpus_origin"),
                      docs_status(model))
    return line + honesty_tail(model) if line else line


def docs_status(model):
    """המפתח של שם המסמכים בשורה: מעמד המאגר, ו-theirs_paper כשהמאגר חתום ורובו נייר של הצד שכנגד."""
    status = corpus_status(model)
    return "theirs_paper" if status == "signed" and S.theirs_paper(model) else status


def honesty_tail(model, lang="he"):
    """המשפט שנוסף לשורת הבסיס כשנקראו מסמכים של החברה ואף מסלול אינו נשען עליהם, או ''. כשלא נקרא מסמך של
    החברה, שורת השוק כבר אומרת זאת, ולא חוזרים על כך."""
    return NO_COMPANY_POSITION["en" if lang == "en" else "he"] if S.no_company_position(model) else ""


def mostly_drafts(model):
    """האם רוב ההסכמים טיוטות. אז נוספת לשער השורה "פלייבוק ראשוני"."""
    return S.mostly_drafts(model)


def preliminary_line(model):
    """שורת "פלייבוק ראשוני" לשער, במלואה, או None כשהמאגר הוא הסכמים חתומים של החברה. ה-Word מדפיס אותה
    כמו שהיא, ולא נוסח מקוצר שלה."""
    return PRELIMINARY.get(corpus_status(model))


# ---- שורת "מאיפה נלמד קו הנסיגה" (playbook-schema.md, fallback_origin; evidence-policy.md, "Shown on every
# topic card"). הסכמה אומרת שהשורה נבנית בקוד מ-baseline ומהשדות שלצדו, אבל עד עכשיו לא היה קוד כזה, והבונה
# כתב אותה חופשית; למעמד unknown לא היה ערך baseline. ה-Word ונתוני סביבת העבודה
# קוראים אותה מכאן, ולכן היא זהה בשניהם.
AREO_TAG_EN = "Areo proposal (not based on the client's documents)"
# איך המסמכים נקראים בשורה כש-baseline הוא documents_majority
FALLBACK_DOCS = {
    "he": {"company_forms": "הנוסחים שהחברה מציגה לצד שכנגד", "mostly_drafts": "המסמכים, שרובם טיוטות",
           "third_party_forms": "המסמכים, שאינם הסכמים חתומים של החברה", "unknown": "המסמכים, שמעמדם אינו ידוע",
           "signed": "המסמכים"},
    "en": {"company_forms": "forms the company presents to its counterparties",
           "mostly_drafts": "documents, most of them drafts",
           "third_party_forms": "documents, which are not signed agreements of the company",
           "unknown": "documents, whose status is unknown", "signed": "documents"},
}
FALLBACK_TEXT = {
    "he": {"template_dep": "קו הנסיגה נלמד מהתבנית שלכם: הסטייה הזו נחתמה ב-%d משאים ומתנים.",
           "template": "קו הנסיגה נלמד מהתבנית שלכם, ולא נמצאה ממנה סטייה שנחתמה בשני משאים ומתנים או יותר.",
           "own_paper_majority": "קו הנסיגה נלמד מהנוסח שחוזר ב-%d מתוך %d ההסכמים על הנייר שלכם.",
           "identical": "כל ההסכמים זהים בנושא הזה, ולכן אין ראיה לקו נסיגה. הצהוב הוא הצעת Areo.",
           "documents_majority": "הירוק נלקח מהנוסח שחוזר ב-%d מתוך %d %s. אין בהם משא ומתן, ולכן אין ראיה לקו "
                                 "נסיגה, והצהוב הוא הצעת Areo.",
           "none": "אין בנושא הזה נוסח בסיס, ולכן אין ראיה לקו נסיגה. הצהוב הוא הצעת Areo.",
           "market": 'קו הנסיגה נלקח ממחקר השוק, ומסומן "%s".' % AREO_TAG},
    "en": {"template_dep": "The fallback line is learned from your template: this departure was signed in %d "
                           "negotiations.",
           "template": "The fallback line is learned from your template, and no departure from it was signed in "
                       "two negotiations or more.",
           "own_paper_majority": "The fallback line is learned from the wording that repeats in %d of the %d "
                                 "agreements on your paper.",
           "identical": "All the agreements are identical on this topic, so there is no evidence for a fallback "
                        "line. The yellow is an Areo proposal.",
           "documents_majority": "The green is taken from the wording that repeats in %d of the %d %s. They show "
                                 "no negotiation, so there is no evidence for a fallback line, and the yellow is "
                                 "an Areo proposal.",
           "none": "There is no baseline wording on this topic, so there is no evidence for a fallback line. The "
                   "yellow is an Areo proposal.",
           "market": 'The fallback line is taken from the market research, and is marked "%s".' % AREO_TAG_EN},
}


def fallback_label(origin, model, lang="he"):
    """השורה שמוצגת בכרטיס, מ-fallback_origin של הכלל או של הווריאנט. baseline שאינו בסכמה: השורה שהמודל כתב
    (label_en או label_he), כמו קודם."""
    o = origin if isinstance(origin, dict) else {}
    lang = "en" if lang == "en" else "he"
    T = FALLBACK_TEXT[lang]
    base = o.get("baseline")
    refs = [x for x in o.get("baseline_refs") or [] if x]
    rows = [r for r in (model or {}).get("source_log") or []
            if isinstance(r, dict) and r.get("included") is not False]
    if o.get("identical_in_all") and base in ("own_paper_majority", "template"):
        return T["identical"]
    if base == "template":
        dep = [d.get("negotiations") for d in o.get("departures") or []
               if isinstance(d, dict) and d.get("status") == "established" and isinstance(d.get("negotiations"), int)]
        return T["template_dep"] % max(dep) if dep else T["template"]
    if base == "own_paper_majority":
        ours = sum(1 for r in rows if r.get("paper") == "ours" and r.get("doc_role") not in ("template", "form"))
        return T["own_paper_majority"] % (len(refs), max(ours, len(refs)))
    if base == "documents_majority":
        total = sum(1 for r in rows if r.get("doc_role") != "template")
        st = corpus_status(model or {})
        name = FALLBACK_DOCS[lang].get(st, FALLBACK_DOCS[lang]["signed"])
        return T["documents_majority"] % (len(refs), max(total, len(refs)), name)
    if base in ("none", "market"):
        return T[base]
    return (o.get("label_en") if lang == "en" else None) or o.get("label_he") or ""
