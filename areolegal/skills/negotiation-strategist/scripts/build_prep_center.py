# -*- coding: utf-8 -*-
"""בונה את מרכז ההיערכות למשא ומתן מתוך התבנית וקובץ הנתונים, בלי לקרוא את התבנית להקשר.

שימוש:
  python3 -B build_prep_center.py --data strategy-data.json --out "מרכז היערכות.html" [--artifact artifact.html]

התבנית נארזת בתוסף: בלי --template נקרא העותק שבתוסף, skills/negotiation-strategist/assets/prep-center-template.html.
אין הורדה מהשרת בזמן ריצה, ותבנית אינה נשמרת לעולם בתיקיית הלקוח (strategist-main.md, "תבנית התוצר").

--out       קובץ מקומי, publishTarget=local.
--lang      he | en | both: שפת מרכז ההיערכות. בלעדיו: deliverable_language מ---profile, ואחריו
            meta.deliverable_language או meta.display_language שבנתונים, ואחרת עברית. both: המרכז וכרטיס הכיס
            בשפת הממשק (display_language מהפרופיל, ואחריו מהנתונים), ומה שיוצא לצד השני בשפת ההסכם
            (meta.agreement_language). השפה שנקבעה נרשמת ב-meta.deliverable_language (he או en);
            התבנית מציגה עברית RTL או אנגלית LTR (title, lang, dir וכל טקסט קבוע). נוסח מצוטט נשאר בשפת המקור.
            מייל הסיכום נכתב תמיד בשפת ההסכם, meta.agreement_language, ובלעדיו בשפת המרכז.
--profile   פרופיל-לקוח.json: שפת התוצר (deliverable_language) ושפת הממשק (display_language), וצבעי המותג
            (branding.theme), כשהלקוח אישר מיתוג והצבעים נגזרו: נכנסים ל-meta.branding.theme.
--artifact  תוכן לפרסום כ-Artifact פרטי בחשבון הלקוח עצמו בלבד (כלל 2.1 ב-areo-hard-rules.md): ללא תגיות
            doctype/html/head/body, publishTarget=artifact, וללא מסלולי הורדת קבצים, שכן בדף שמתפרסם שמירת קובץ
            חסומה בדפדפן. הפרסום פרטי בלבד: אין קישור ציבורי, אין גלריה ואין שיתוף מחוץ לארגון הלקוח; הפרטיות
            מאומתת מתוצאת הפרסום עצמה והדף אינו נקרא בחזרה. העותק המקומי הוא קובץ --out, שנשמר תמיד בתיקיית העסקה
            ב-Areo-נתונים.

הסקריפט אינו ממציא נתונים ואינו ממציא כתובות. הוא משתמש רק במה שקיים במרשם:
meta.docAccess.mode = local | connector | base | none, meta.docAccess.baseUrl, ולכל מסמך webUrl ו-urlSource.

--template  רשות. בלעדיו: העותק שבתוסף (assets/prep-center-template.html). תבנית בתוך תיקיית הלקוח (תיקייה שיש בה Areo-נתונים)
            או בתוך Areo-נתונים נדחית בקוד 2, ולא משמשת לבנייה. אחרי בנייה מוצלחת העותק הזמני של התבנית
            (prep-center-template*.html) נמחק, אלא עם --keep-template, ורק כשהוא בתיקייה הזמנית של מערכת ההפעלה
            ואינו בתוך תיקיית רכיב (מהתוסף, תוכן מהשרת): תבנית מקור אינה נמחקת לעולם.
--external-out  עותק לצד השני (נוסח מאושר בלבד). נבנה רק מ-external_view(data) שב-validate_data.py: רשימת היתר
            שאינה כוללת שום רשומה פנימית, אפילו לא שדה ניסוח מחדש. ההכנה הפנימית, כרטיס השיחה וחומר התרגול אינם
            מגיעים למרכיב שמפיק את הטקסט. אחרי הבנייה נבדק התוכן המדויק של הבייטים (leak_check): מחרוזת פנימית שנמצאה
            חוסמת את הכתיבה (קוד 4). הבדיקה תופסת הדלפה מילולית בלבד; הדלפה בניסוח מחדש אי אפשר להוכיח בקוד שאינה
            קיימת, ולכן נדרשת גם סקירת עורך דין.
--state     negotiation_state.json לקריאה בלבד. אם הסבב או last_updated שבו שונים ממה שהנתונים נשענים עליו
            (meta.round_number, proposal.base), הסבב השתנה בזמן ההכנה: לא נכתב דבר, קוד 3, ויש לרענן.
--out ו---artifact נבדקים ב-guard_out: לא על קובץ קלט, לא על מסמך קיים ולא בתיקיית מקור של הלקוח (קוד 1).
"""
import argparse, io, json, os, re, sys, tempfile, urllib.parse
from pathlib import Path

for _s in (sys.stdout, sys.stderr):  # עברית בקונסולה שאינה UTF-8 (cp1252): בלי UnicodeEncodeError באמצע הפלט
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):   # לא TextIOWrapper (לכידה בבדיקות, pythonw)
        pass

# הספרייה המשותפת (AREO_RT/lib) נותנת guard_out. בלעדיה: בדיקה מינימלית, שהפלט אינו קובץ קלט ואינו מסמך קיים
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from areo_rt import ensure_lib  # noqa: E402
import validate_data as vd  # noqa: E402  external_view, leak_check, WORDLIST: ההפרדה הפנימי/חיצוני
ensure_lib()
try:
    from common.cli import OutputRefused, guard_out
except ImportError:
    class OutputRefused(Exception):
        pass

    def guard_out(out, inputs=()):
        k = os.path.normcase(os.path.realpath(out))
        if any(p and os.path.normcase(os.path.realpath(p)) == k for p in inputs):
            raise OutputRefused("--out הוא קובץ קלט: %s" % out)
        if os.path.isfile(k) and k.lower().endswith((".docx", ".doc", ".pdf", ".xlsx", ".pptx")):
            raise OutputRefused("--out הוא מסמך קיים: %s" % out)
        return os.path.abspath(out)

DATA_DIR = "Areo-נתונים"
TEMPLATE_NAME = "prep-center-template"
# תיקיות של רכיב: תבנית בתוכן אינה עותק זמני, גם כשהיא יושבת בתוך התיקייה הזמנית (עותק של תיקיית הסקילים)
SKILL_DIRS = ("מהתוסף", "תוכן מהשרת", "skills", "runtime")
# התבנית שנארזת בתוסף: ברירת המחדל של --template (אין הורדה מהשרת בזמן ריצה)
DEFAULT_TEMPLATE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets",
                                TEMPLATE_NAME + ".html")


def is_temp_copy(path):
    """True רק לעותק זמני של התבנית: בתוך התיקייה הזמנית של מערכת ההפעלה, ולא בתוך תיקיית רכיב."""
    t = os.path.normcase(os.path.realpath(path))
    tmp = os.path.normcase(os.path.realpath(tempfile.gettempdir())).rstrip("\\/") + os.sep
    if not t.startswith(tmp):
        return False
    parts = [x.lower() for x in t[len(tmp):].split(os.sep)[:-1]]
    return not any(x in SKILL_DIRS for x in parts)

PLACEHOLDER = "__STRATEGY_DATA__"

def load(p):
    return io.open(p, encoding="utf-8").read()

def derive_urls(data):
    """גזירת כתובות במצב base בלבד, ורק למסמך שאין לו כתובת ולא סומן none."""
    meta = data.setdefault("meta", {})
    acc = meta.get("docAccess") or {"mode": "local"}
    meta["docAccess"] = acc
    if acc.get("mode") != "base" or not acc.get("baseUrl"):
        return 0
    base = acc["baseUrl"].rstrip("/")
    n = 0
    for d in data.get("footnotes", []) or []:
        f = d.get("file")
        if not f or d.get("webUrl") or d.get("urlSource") == "none":
            continue
        d["webUrl"] = base + "/" + urllib.parse.quote(f)
        d["urlSource"] = "derived"
        n += 1
    return n

def inject(tpl, data):
    blob = json.dumps(data, ensure_ascii=False).replace("—", ", ").replace("–", "-").replace("</", "<\\/")
    if tpl.count(PLACEHOLDER) != 1:
        sys.exit("שגיאה: מציין המיקום %s חייב להופיע פעם אחת בתבנית, נמצא %d"
                 % (PLACEHOLDER, tpl.count(PLACEHOLDER)))
    h = tpl.replace(PLACEHOLDER, blob)
    if "—" in h or "–" in h:
        sys.exit("שגיאה: מקף ארוך זלג לתוצר")
    return h

TITLES = {"he": "Areo | מרכז היערכות למשא ומתן", "en": "Areo | Negotiation prep centre"}


def _he_en(v):
    v = str(v or "").strip().lower()
    return "en" if v[:2] == "en" or v in ("english", "אנגלית") else "he"


# צבעי המותג של הלקוח מהפרופיל, כמו common/branding.py בספרייה המשותפת (הרכיב רץ גם בלעדיה). הצבעים נגזרים
# ונבדקים לניגודיות רק ברכיב ההקמה (build_profile.py --derive-theme), ורק בהסכמת הלקוח
THEME_KEYS = ("primary_light", "secondary_light", "soft_light", "on_light",
              "primary_dark", "secondary_dark", "soft_dark", "on_dark")


def apply_theme(data, profile):
    th = ((profile or {}).get("branding") or {}).get("theme") or {}
    tok = {k: (th.get("tokens") or {}).get(k) for k in THEME_KEYS}
    if th.get("choice") != "yes":
        return None
    if not all(re.match(r"^#[0-9A-Fa-f]{6}$", str(v or "")) for v in tok.values()):
        return "מיתוג: אושר, אך הצבעים עוד לא נגזרו (build_profile.py --derive-theme). התוצר נבנה בעיצוב הרגיל"
    data.setdefault("meta", {}).setdefault("branding", {})["theme"] = tok
    return "מיתוג: צבעי המותג של הלקוח הוחלו (%s)" % tok["primary_light"]


def resolve_lang(data, lang_arg=None, profile=None):
    """--lang, אחריו deliverable_language בפרופיל, אחריו השדות שבנתונים; he או en.

    both אינו מומר עוד לעברית בשקט: המרכז הפנימי בשפת הממשק (display_language), ומה שיוצא לצד השני
    בשפת ההסכם, שהתבנית קוראת מ-meta.agreement_language."""
    meta = data.setdefault("meta", {})
    prof = profile or {}
    v = (lang_arg or prof.get("deliverable_language") or meta.get("deliverable_language")
         or meta.get("display_language") or meta.get("lang") or "he")
    v = str(v).strip().lower()
    if v == "both":
        lang = _he_en(prof.get("display_language") or meta.get("display_language") or "he")
        meta["display_language"] = lang
        if not meta.get("agreement_language"):
            print("אזהרה: deliverable_language הוא both בלי meta.agreement_language. "
                  "מייל הסיכום ייכתב בשפת המרכז (%s)" % lang)
    else:
        lang = _he_en(v)
    meta["deliverable_language"] = lang
    return lang


def localize_shell(html, lang):
    """בתוצר באנגלית גם השלד הסטטי באנגלית ו-LTR, עוד לפני שהסקריפט רץ."""
    if lang != "en":
        return html
    html = html.replace('<html lang="he" dir="rtl">', '<html lang="en" dir="ltr">', 1)
    return html.replace("<title>%s</title>" % TITLES["he"], "<title>%s</title>" % TITLES["en"], 1)


def to_artifact(html, lang="he"):
    """הפשטה לתוכן בלבד, כנדרש בדף שמתפרסם כ-Artifact פרטי. הכיוון והשפה לפי שפת התוצר."""
    title = re.search(r"<title>.*?</title>", html, re.S)
    body = re.search(r"<body[^>]*>(.*)</body>", html, re.S)
    if not (title and body):
        sys.exit("שגיאה: מבנה התבנית אינו כצפוי, לא ניתן להפיק תוכן לפרסום")
    head_bits = re.findall(r"<style>.*?</style>|<script>.*?</script>", html[:html.index("<body")], re.S)
    d, l = ("ltr", "en") if lang == "en" else ("rtl", "he")
    return (title.group(0) + "\n" + "\n".join(head_bits) +
            '\n<script>document.documentElement.setAttribute("dir","%s");'
            'document.documentElement.setAttribute("lang","%s");</script>\n' % (d, l) +
            body.group(1).strip() + "\n")

EXT_TXT = {
    "he": {"dir": "rtl", "hello": "שלום,", "intro": "בהמשך לשיחתנו, להלן עיקרי הדברים:", "close": "נשמח לתגובתכם.",
           "regards": "בברכה,", "fill": "[להשלמה]", "subj": "הנדון: "},
    "en": {"dir": "ltr", "hello": "Hello,", "intro": "Following our conversation, the main points are:",
           "close": "We look forward to your response.", "regards": "Kind regards,", "fill": "[to be completed]",
           "subj": "Subject: "},
}


def render_external(view, lang):
    """עותק לצד השני מתוך תצוגה חיצונית בלבד (external_view). אין כאן גישה לנתונים המלאים."""
    import html as _h
    L = EXT_TXT["en" if lang == "en" else "he"]
    meta, ob = view["meta"], view["outbound"]
    subj = ob.get("subject") or meta.get("agreement") or L["fill"]
    items = [i["text"] for i in ob.get("items", [])]
    li = "\n".join("<li>%s</li>" % _h.escape(x) for x in items) or "<li>%s</li>" % _h.escape(L["fill"])
    blob = json.dumps(view, ensure_ascii=False).replace("</", "<\\/")
    return ('<!DOCTYPE html>\n<html lang="%s" dir="%s"><head><meta charset="utf-8"><title>%s</title></head><body>\n'
            '<p>%s%s</p><p>%s</p><p>%s</p><ul>\n%s\n</ul><p>%s</p><p>%s</p>\n'
            '<script type="application/json" id="outbound-data">%s</script>\n</body></html>\n'
            % ("en" if lang == "en" else "he", L["dir"], _h.escape(subj), _h.escape(L["subj"]), _h.escape(subj),
               _h.escape(L["hello"]), _h.escape(L["intro"]), li, _h.escape(L["close"]), _h.escape(L["regards"]), blob))


def check_state(data, state):
    """השוואת הנתונים למצב החי: רשימת סיבות לרענון. ריקה: הנתונים נשענים על הסבב והגרסה הנוכחיים."""
    out = []
    meta = data.get("meta") or {}
    srn = None
    for k in ("round_number", "current_round", "round"):
        v = state.get(k, (state.get("meta") or {}).get(k) if isinstance(state.get("meta"), dict) else None)
        if isinstance(v, int) and not isinstance(v, bool):
            srn = v
            break
    if srn is not None and isinstance(meta.get("round_number"), int) and meta["round_number"] != srn:
        out.append("מצב העסקה בסבב %s והנתונים בסבב %s" % (srn, meta["round_number"]))
    base = (data.get("proposal") or {}).get("base") or {}
    if srn is not None and isinstance(base.get("round_number"), int) and base["round_number"] != srn:
        out.append("הצעת השינוי נשענת על סבב %s ומצב העסקה בסבב %s" % (base["round_number"], srn))
    sup = state.get("last_updated")
    if sup and base.get("state_updated") and str(base["state_updated"]) != str(sup):
        out.append("הצעת השינוי נשענת על גרסה %s של קובץ המצב, והחי הוא %s" % (base["state_updated"], sup))
    pr = ((data.get("practice") or {}).get("base_round"))
    if srn is not None and isinstance(pr, int) and pr != srn:
        out.append("התרגול נעשה בסבב %s ומצב העסקה בסבב %s" % (pr, srn))
    return out


def client_roots(*paths):
    """תיקיות הלקוח שעולות מהנתיבים: ההורה של כל Areo-נתונים שבנתיב, וכל תיקייה מעל הנתיב שיש בה Areo-נתונים."""
    roots = set()
    for p in paths:
        if not p:
            continue
        cur = Path(os.path.abspath(p))
        for anc in [cur] + list(cur.parents):
            if anc.name == DATA_DIR:
                roots.add(str(anc.parent))
            elif anc.is_dir() and (anc / DATA_DIR).is_dir():
                roots.add(str(anc))
    return roots


def template_in_client_folder(template, *others):
    """התיקייה של הלקוח שהתבנית בתוכה, או None. התבנית היא תוכן של Areo, ולעולם אינה נקראת מתיקיית הלקוח."""
    t = os.path.normcase(os.path.abspath(template))
    for r in sorted(client_roots(template, *others)):
        if t.startswith(os.path.normcase(r).rstrip("\\/") + os.sep):
            return r
    return None


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--data", required=True)
    p.add_argument("--template", help="רשות. בלעדיו: העותק שבתוסף, %s" % DEFAULT_TEMPLATE)
    p.add_argument("--out")
    p.add_argument("--external-out", dest="external_out")
    p.add_argument("--state")
    p.add_argument("--artifact")
    p.add_argument("--lang", choices=("he", "en", "both"))
    p.add_argument("--profile")
    p.add_argument("--keep-template", action="store_true",
                   help="לא למחוק את העותק הזמני של התבנית אחרי הבנייה")
    a = p.parse_args(argv)
    if not a.out and not a.artifact and not a.external_out:
        sys.exit("שגיאה: יש לציין --out, --artifact או --external-out")
    explicit_template = bool(a.template)
    if (a.out or a.artifact) and not a.template:
        a.template = DEFAULT_TEMPLATE
    if a.template and not os.path.isfile(a.template):
        sys.exit("שגיאה: התבנית אינה קיימת: %s" % a.template)
    # התבנית היא תוכן של Areo: עותק בתיקיית הלקוח (מהרצה קודמת) אינו משמש לבנייה (strategist-main.md, "תבנית התוצר")
    root = template_in_client_folder(a.template, a.data, a.out, a.artifact, a.profile) if a.template else None
    if root:
        print("סירוב: --template בתוך תיקיית הלקוח או Areo-נתונים (%s). התבנית היא תוכן של Areo ונארזת בתוסף: "
              "מריצים בלי --template, והעותק שבתוסף נקרא (%s).\nRefused: --template is inside the client folder. "
              "Run without --template to use the copy bundled with the plugin." % (root, DEFAULT_TEMPLATE))
        return 2
    try:
        for o in (a.out, a.artifact, a.external_out):
            if o:
                guard_out(o, inputs=[a.data, a.template, a.profile, a.state])
    except OutputRefused as exc:
        print("סירוב: %s" % exc)
        return 1
    data = json.load(io.open(a.data, encoding="utf-8"))
    prof = json.load(io.open(a.profile, encoding="utf-8")) if a.profile else {}
    if a.state:   # קריאה בלבד: הבנייה אינה כותבת לקובץ המצב לעולם
        stale = check_state(data, json.load(io.open(a.state, encoding="utf-8")))
        if stale:
            print("נדרש רענון, לא נכתב דבר (קוד 3):\n  " + "\n  ".join(stale))
            return 3
    lang = resolve_lang(data, a.lang, prof)
    brand = apply_theme(data, prof)
    tpl = localize_shell(load(a.template), lang) if a.template and (a.out or a.artifact) else ""
    n = derive_urls(data)
    mode = (data.get("meta", {}).get("docAccess") or {}).get("mode", "local")
    if a.external_out:
        # הרכיב שמפיק את הטקסט החיצוני מקבל רק את התצוגה המותרת; הנתונים המלאים אינם נכנסים לפונקציית הרינדור
        view = vd.external_view(data)
        ext_lang = _he_en((data.get("meta") or {}).get("agreement_language") or lang)
        built = render_external(view, ext_lang)
        hits = vd.leak_check(built.encode("utf-8"), data)
        if hits:
            print("הדלפה מילולית בעותק לצד השני, לא נכתב (קוד 4). שדות פנימיים שתוכנם נמצא:\n  " + "\n  ".join(hits))
            return 4
        for it in view["outbound"]["items"]:
            if vd.WORDLIST.search(it["text"]):
                print("אזהרה: בנוסח לצד השני מונח של משא ומתן פנימי: בדיקת רשימת מילים משלימה, נדרשת סקירה")
        io.open(a.external_out, "w", encoding="utf-8", newline="\n").write(built)
        print("עותק לצד השני נכתב: %d פריטים מאושרים. בדיקת תוכן מדויק עברה (הדלפה בניסוח מחדש אינה ניתנת להוכחה "
              "בקוד: נדרשת סקירת עורך דין)" % len(view["outbound"]["items"]))
    if a.out:
        d = json.loads(json.dumps(data)); d["meta"]["publishTarget"] = "local"
        io.open(a.out, "w", encoding="utf-8").write(inject(tpl, d))
    if a.artifact:
        d = json.loads(json.dumps(data)); d["meta"]["publishTarget"] = "artifact"
        io.open(a.artifact, "w", encoding="utf-8").write(to_artifact(inject(tpl, d), lang))
    docs = data.get("footnotes", []) or []
    linked = sum(1 for x in docs if x.get("webUrl"))
    print("מצב גישה: %s. ציטוטים עם קישור למסמך: %d מתוך %d. נגזרו כעת: %d"
          % (mode, linked, len(docs), n))
    if brand:
        print(brand)
    # העותק הזמני של התבנית אינו נשאר אחרי הבנייה (רק העותק הקנוני, בשמו, ורק כשלא ביקשו לשמור אותו)
    if explicit_template and not a.keep_template and os.path.basename(a.template).lower().startswith(TEMPLATE_NAME)             and is_temp_copy(a.template):
        try:
            os.remove(a.template)
            print("העותק הזמני של התבנית נמחק: %s" % a.template)
        except OSError as exc:
            print("אזהרה: העותק הזמני של התבנית לא נמחק (%s): %s" % (type(exc).__name__, a.template))
    return 0

if __name__ == "__main__":
    sys.exit(main())
