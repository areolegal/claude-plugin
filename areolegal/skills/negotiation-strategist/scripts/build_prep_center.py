# -*- coding: utf-8 -*-
"""בונה את מרכז ההיערכות למשא ומתן מתוך התבנית וקובץ הנתונים, בלי לקרוא את התבנית להקשר.

שימוש:
  python3 build_prep_center.py --data strategy-data.json --template assets/prep-center-template.html \
      --out "מרכז היערכות.html" [--artifact artifact.html]

--out       קובץ מקומי, publishTarget=local.
--artifact  תוכן לפרסום כעמוד משותף: ללא תגיות doctype/html/head/body, publishTarget=artifact,
            וללא מסלולי הורדת קבצים, שכן בעמוד משותף שמירת קובץ חסומה בדפדפן.

הסקריפט אינו ממציא נתונים ואינו ממציא כתובות. הוא משתמש רק במה שקיים במרשם:
meta.docAccess.mode = local | connector | base | none, meta.docAccess.baseUrl, ולכל מסמך webUrl ו-urlSource.
"""
import argparse, io, json, re, sys, urllib.parse

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

def to_artifact(html):
    """הפשטה לתוכן בלבד, כנדרש בעמוד משותף."""
    title = re.search(r"<title>.*?</title>", html, re.S)
    body = re.search(r"<body[^>]*>(.*)</body>", html, re.S)
    if not (title and body):
        sys.exit("שגיאה: מבנה התבנית אינו כצפוי, לא ניתן להפיק עמוד משותף")
    head_bits = re.findall(r"<style>.*?</style>|<script>.*?</script>", html[:html.index("<body")], re.S)
    return (title.group(0) + "\n" + "\n".join(head_bits) +
            '\n<script>document.documentElement.setAttribute("dir","rtl");'
            'document.documentElement.setAttribute("lang","he");</script>\n' +
            body.group(1).strip() + "\n")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data", required=True)
    p.add_argument("--template", required=True)
    p.add_argument("--out")
    p.add_argument("--artifact")
    a = p.parse_args()
    if not a.out and not a.artifact:
        sys.exit("שגיאה: יש לציין --out או --artifact או שניהם")
    data = json.load(io.open(a.data, encoding="utf-8"))
    tpl = load(a.template)
    n = derive_urls(data)
    mode = (data.get("meta", {}).get("docAccess") or {}).get("mode", "local")
    if a.out:
        d = json.loads(json.dumps(data)); d["meta"]["publishTarget"] = "local"
        io.open(a.out, "w", encoding="utf-8").write(inject(tpl, d))
    if a.artifact:
        d = json.loads(json.dumps(data)); d["meta"]["publishTarget"] = "artifact"
        io.open(a.artifact, "w", encoding="utf-8").write(to_artifact(inject(tpl, d)))
    docs = data.get("footnotes", []) or []
    linked = sum(1 for x in docs if x.get("webUrl"))
    print("מצב גישה: %s. ציטוטים עם קישור למסמך: %d מתוך %d. נגזרו כעת: %d"
          % (mode, linked, len(docs), n))

if __name__ == "__main__":
    main()
