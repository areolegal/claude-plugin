"""הצעת סוג מסמך לפי שם הקובץ ואותות מתוכו.

זו הצעה בלבד. Claude מכריע בקובץ החילוץ אחרי קריאת המסמך.
הסדר חשוב: מסמך שאינו הסכם, אחריו טיוטה עם הערות, תבנית, הזמנה, תיקון, נספח, הסכם חתום,
ורק אז שדות ריקים רבים. שם קובץ "חתום" גובר על שדות ריקים, כי תוכן עניינים ושורות חתימה
נראים כשדות ריקים. "unsigned", "non-signed", "not signed" ו"לא חתום" אינם חתום.

"מעיד על חתום" (סימון kind_conflict בהרכבה) נקבע רק לפי שם הקובץ והצעת הסריקה, לא לפי טקסט המסמך:
נוסחי סיום כמו "ולראיה באו הצדדים על החתום" או "IN WITNESS WHEREOF ... signed" מופיעים גם בתבניות.
"""
import re
import zipfile

DOC_KINDS = {"signed", "draft", "negotiation_version", "template", "amendment", "schedule", "order", "non_agreement"}

NON_AGREEMENT = re.compile(r"(גילוי דעת|חוות דעת|מצגת|פרוטוקול|מכתב|memo|presentation)", re.I)
NEGOTIATION = re.compile(r"(הערות|redline|עקוב אחר שינויים|tracked|edits|טיוטה נגדית|markup)", re.I)
TEMPLATE = re.compile(r"(תבנית|template|\(דוגמה\)|sample)", re.I)
ORDER = re.compile(r"(הזמנת עבודה|statement of work|\bsow\b|order form|purchase order)", re.I)
AMENDMENT = re.compile(r"(תיקון|תוספת|amendment|addendum)", re.I)
SCHEDULE = re.compile(r"(נספח|schedule|annex|exhibit)", re.I)
SIGNED = re.compile(r"(?<!un)(?<!non )(?<!non_)(?<!non\-)(?<!not )(?<!not_)(?<!not\-)"
                    r"(?<!לא )(?<!לא_)(?<!לא\-)(חתום|signed|executed)", re.I)
BLANKS = re.compile(r"(_{4,}|\[\s*_+\s*\]|\.{6,})")
TOC_LEADER = re.compile(r"\.{6,}\s*\d+\s*$")
SIGNATURE_LINE = re.compile(r"^\s*(חתימה|חתימת|שם|signature|name)\b", re.I)


def count_blanks(paragraphs):
    """שדות ריקים בגוף המסמך, בלי שורות חתימה ושם ובלי נקודות מנחות של תוכן עניינים."""
    n = 0
    for t in paragraphs:
        if SIGNATURE_LINE.match(t):
            continue
        n += len(BLANKS.findall(TOC_LEADER.sub("", t)))
    return n


def docx_signals(path):
    try:
        with zipfile.ZipFile(path) as z:
            xml = z.read("word/document.xml").decode("utf-8", "ignore")
            has_comments = "word/comments.xml" in z.namelist()
    except (KeyError, zipfile.BadZipFile, OSError):
        return {"readable": False}
    paragraphs = [re.sub(r"<[^>]+>", "", p) for p in xml.split("</w:p>")]
    return {"readable": True, "tracked_changes": "<w:ins " in xml or "<w:del " in xml,
            "comments": has_comments, "blanks": count_blanks(paragraphs)}


DRAFT = re.compile(r"(טיוטה|\bdraft\b|unsigned|non[ _\-]signed|not[ _\-]signed|לא חתום)", re.I)


def says_draft(name):
    """שם הקובץ מעיד על טיוטה או על נוסח עם הערות, ולכן אינו ראיה לחתימה."""
    return bool(DRAFT.search(name) or NEGOTIATION.search(name))


def says_signed(name):
    base = name.replace("\\", "/").split("/")[-1]
    return bool(SIGNED.search(base))


def suggest(name, signals=None):
    s = signals or {}
    base = re.sub(r"\.(docx|pdf|doc|txt|md|eml)$", "", name.replace("\\", "/").split("/")[-1], flags=re.I)
    if NON_AGREEMENT.search(base):
        return "non_agreement", ["שם הקובץ מעיד על מסמך שאינו הסכם"]
    if s.get("tracked_changes") or s.get("comments"):
        return "negotiation_version", ["עקוב אחר שינויים או הערות בקובץ"]
    if NEGOTIATION.search(base):
        return "negotiation_version", ["שם הקובץ מעיד על טיוטה עם הערות"]
    if TEMPLATE.search(base):
        return "template", ["שם הקובץ מעיד על תבנית"]
    if ORDER.search(base):
        return "order", ["שם הקובץ מעיד על הזמנת עבודה"]
    if AMENDMENT.search(base):
        return "amendment", ["שם הקובץ מעיד על תיקון"]
    if SCHEDULE.search(base):
        return "schedule", ["שם הקובץ מעיד על נספח"]
    if SIGNED.search(base):
        return "signed", ["שם הקובץ מעיד על הסכם חתום"]
    if s.get("blanks", 0) >= 5:
        return "template", ["שדות ריקים רבים בגוף המסמך"]
    return "draft", ["אין סימן מובהק בשם או בקובץ; ההכרעה בחילוץ"]
