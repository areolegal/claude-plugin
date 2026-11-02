#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""סימון ההכרעות על הטיוטה של הצד שכנגד, בעקוב אחר שינויים, במנוע האחד.

הקובץ נבנה **על הטיוטה שלהם**, ולא כמסמך חדש. הסימון נעשה במנוע המשותף
(`areolegal/lib/common/docx_tracked.py`):

* **סימון כירורגי.** רק ההבדל בין הנוסח שלהם לנוסח היעד מסומן, ברמת המילה,
  ומספר, סכום או סוגריים מרובעים כיחידה אחת. פסקה שלמה אינה נמחקת ונכתבת
  מחדש בגלל מילה.
* **הבועה היא `external_comment` בלבד.** אין פתיח קבוע, אין "סעיף X למדיניות
  שלנו" ואין צבע. המסלול ומזהי הכללים נרשמים בקובץ המצב בלבד.
* **השינויים וההערות של הצד שכנגד נשארים במקומם**, עם המחבר והתאריך שלהם.
  שום דבר שלהם אינו מתקבל או נמחק בשקט.
* **שתי שכבות בקובץ העבודה, תמיד.** הבועות לצד שכנגד, ולצד כל תיקון בועה פנימית
  ("פנימי, למחיקה לפני המשלוח") עם הנימוק, המסלול ובסיס ההכרעה, והכותרת "טיוטת
  עבודה פנימית". העותק למשלוח נגזר בלי השכבה הפנימית ב-`qa_gate.py --mode send`.
  `--no-internal-layer` מפיק קובץ בלי השכבה הפנימית, לבדיקות בלבד.
* **כירורגי, ולא פסקה במקום פסקה.** לכל הכרעה מודפס איזה חלק מהפסקה סומן.
  הכרעת `replace` שמסמנת את רוב הפסקה כשרוב המילים נשארו היא לא סימון כירורגי,
  ושער האיכות עוצר אותה: במקרה כזה כותבים `replace_span` למילים שמשתנות.
* **"עקוב אחר שינויים" דולק בקובץ**, והשעה בכל שינוי היא שעת ההרצה.
* **בדיקת הלוך ושוב:** "דחה הכול" חייב להחזיר את הטיוטה שהתקבלה, ו"קבל
  הכול" את נוסחי היעד. הכרעה שאינה ניתנת לסימון בבטחה אינה מוחלת חלקית:
  היא מדווחת כ"לא סומנה". בסבב 2 ואילך "הטיוטה שהתקבלה" היא הטיוטה כפי שהיא,
  כולל הסימונים הפתוחים שלנו מסבבים קודמים, ו"דחה הכול" דוחה רק את מה שסומן
  בריצה הזו (`docx_tracked.prior_revisions`, לפי מחבר ותאריך).
* **פסקה עם סימון פתוח שלנו מסבב קודם** (S1c, סבב 2, 13(ii)): ההתאמה היא מול הנוסח אחרי קבלת הסימונים
  הפתוחים. מחיקה בתוך הוספה פתוחה שלנו נכתבת כ-w:del חדש בתוכה, והכרעה למחוק מחדש טקסט שהמחיקה הפתוחה שלנו
  עדיין עליו מדווחת "קיימת מסבב קודם" ואינה מסומנת פעמיים. הסימונים שלנו מזוהים לפי השמות שבפרופיל ולפי
  הקבצים שב-`meta.sent_documents` (מ---deal, או מקובץ המצב שליד קובץ ההכרעות).

הקלט הוא קובץ ההכרעות של הסבב, `decisions_round_<n>.json`
(`n8-state-schema.md`, "קובץ ההכרעות"): לכל הכרעה `id`, `op`
(replace, replace_span, insert_paragraph, delete_paragraph, comment_only או
accept) ו-`decision_code`, והשדות של אותה פעולה. הקובץ נבדק מול החוזה לפני
כל החלה, ושגיאה בו עוצרת את ההרצה בלי לכתוב קובץ.

    python "AREO_RT/skills/contract-negotiation-orchestrator/scripts/apply_redlines.py" --draft "<הטיוטה שהתקבלה>.docx" \\
        --decisions decisions_round_2.json --profile Areo-נתונים/פרופיל-לקוח.json \\
        --deal "Areo-נתונים/transactions/<id>" --agreement-type "<סוג ההסכם>" \\
        --company "<שם החברה המקוצר>" --round 2

**שמות הקבצים נגזרים בקוד** (`n6-gate-and-send.md`, "שמירה, נתיבים ושמות קבצים"):
`<סוג ההסכם> - <שם החברה> - סבב <N> - <D.M.YYYY>.docx` לעותק למשלוח (בהסכם באנגלית "3 April 2027"), ואותו
שם עם " - פנימי" לקובץ העבודה ועם " - כפי שהופק" לעותק כפי שהופק, עד 230
תווים לנתיב, ובלי לדרוס קובץ קיים: שם תפוס מקבל " (2)". הסקריפט מדפיס את
הנתיב של העותק למשלוח, וזה הנתיב שמועבר ל-`qa_gate.py --send`. `--out` מפורש
נשאר לבדיקות ולמקרה חריג.

**דוח ההרצה בשם קנוני** (29.10.2026): עם `--deal` ובלי `--report`, הדוח נכתב ל-`<תיקיית העסקה>/runs/round-<N>/apply.json`.
הרצה חוזרת מחליפה אותו, והדוח הקודם עובר ל-`history` שבאותה תיקייה. `--report` מפורש נשאר כמו שהוא.

**הפקה מחדש באותה ריצה** (`--run-id`, הרצה S1c, 28.10.2026: הפקה חוזרת השאירה כפולים עם " (2)"): עם `--deal`
ו-`--run-id`, הקבצים שהופקו באותה ריצה נרשמים ב-`<תיקיית העסקה>/apply-report-round-<N>.json`. הפקה מחדש עם
אותו `--run-id`, לפני מסירה, כותבת על אותם שמות במקום " (2)", רק כשהקובץ זהה למה שהופק (עורך הדין לא שינה
אותו) ואינו ב-`meta.sent_documents`. קובץ שנמסר או נשלח לעולם אינו נדרס: אחרי מסירה, הפקה חדשה היא ריצה חדשה,
עם `--run-id` חדש. בלי `--run-id` ההתנהגות כמו תמיד: שם תפוס מקבל " (2)".

**שם החברה בהסכם באנגלית** (בדיקה עצמאית S1c, ממצא H1: השם העברי נכנס לבלוק הצדדים ולבלוק החתימה): השם העברי של
החברה (`organization_name`) בנוסח שהכנסנו ובבועות מוחלף בשם הרשום באנגלית (`organization_name_en`), וההחלפה נרשמת
בקובץ ההכרעות. **כשאין בפרופיל שם באנגלית, קובץ העבודה מופק בכל זאת** (S1d, 28.10.2026: העצירה בקוד 2 חסמה את כל
הסבב, גם כששום הכרעה לא הכניסה את השם): הכרעה שצריכה את השם מקבלת את מציין המקום `[Company registered English
name]`, והשם החסר חוסם את העותק למשלוח בשער (ENTITY_NAME_EN_MISSING, ו-PH_OURS על מציין המקום). השם העברי אינו
מתועתק ואינו מתורגם. כשהשם נשמר בפרופיל, הרצה חוזרת מאותו קובץ הכרעות מחליפה את מציין המקום בשם. המחבר של הבועות
אינו תלוי בזה: הוא `lawyer_name_en` (qa_gate.author_for), ובלעדיו הסקריפט שואל כמו תמיד.

לצד קובץ העבודה נכתבים שני קבצים: `<שם>.expected.json`, נוסחי היעד שהשער
בודק מולם (`qa_gate.py --expected-accept`), ו-`<שם>.as_produced.docx`, עותק
של קובץ העבודה כפי שהופק, כדי שאפשר יהיה לראות מה עורך הדין שינה בו לפני
המשלוח (שינוי 3ז).

קוד יציאה: **0** הכול סומן והבדיקה עברה, **3** קובץ העבודה נכתב אבל לא הכול
סומן או שבדיקת ההלוך ושוב נכשלה (אינו מוכן למשלוח), **2** קלט שגוי, ולא נכתב
דבר, **1** נתיב פלט שסורב.
"""
import datetime as _dt
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # גם ב-python -I, שאינו מוסיף את תיקיית הסקריפט
import areo_lib  # noqa: F401  מוסיף את areolegal/lib לנתיב הייבוא

from common.cli import OutputRefused, guard_out, load_docx_or_explain, no_bytecode, parser  # noqa: E402
import common.docx_tracked as dt  # noqa: E402
from common import gap_checks, paths  # noqa: E402
from orchestrator import pre_send, qa_gate  # noqa: E402
from orchestrator import state_builder as SB  # noqa: E402
from lawyer import lawyer_view, needs_english_name  # noqa: E402
import threads  # noqa: E402


def scrub_internal_codes(decisions):
    """שכבת הבנייה: מנקה קודים פנימיים (מזהי כללים, "סבב 1") מהבועה החיצונית של כל הכרעה לפני הכתיבה לקובץ.
    מחזיר את מספר הבועות ששונו. הבועה הפנימית נשארת כפי שהיא."""
    import content_checks as CC
    n = 0
    for d in decisions or ():
        for k in ("external_comment", "external_bubble"):
            if d.get(k):
                cleaned = CC.scrub_client_text(d[k])
                if cleaned != d[k]:
                    d[k] = cleaned
                    n += 1
    return n


def load(path, what):
    if not os.path.exists(path):
        print("%s אינו קיים: %s" % (what, path))
        raise SystemExit(2)
    with open(path, encoding="utf-8") as fh:
        try:
            return json.load(fh)
        except ValueError as exc:
            print("%s אינו JSON תקין (%s)" % (what, exc))
            raise SystemExit(2)


def side_paths(out):
    stem = out[:-5] if out.lower().endswith(".docx") else out
    return stem + ".expected.json", stem + ".as_produced.docx"


def sentences(text):
    return [x.strip() for x in re.split(r"(?<=[.!?;])\s+", text or "") if len(x.strip()) >= 20]


def marked_shares(draft, dec, ours=()):
    """לכל הכרעת replace: איזה חלק מהפסקה סומן (מחיקה והוספה יחד, מול אורך הפסקה), וכמה מהמילים
    המקוריות נשארו. סימון של רוב הפסקה כשרוב המילים נשארו אינו כירורגי. ours: השמות שלנו. כשהשינויים שלהם בפסקה
    נדחים (their_changes: reject), הבסיס הוא הנוסח שאחרי הדחייה, כמו בסימון עצמו, ולא הנוסח הגלוי (S1d-R2, 13(ii):
    "סומנו 94% מהפסקה" כשההוספה שלנו מסבב קודם חזרה בדחייה)."""
    paras = dt.received_paragraphs(draft)
    body = dt.body_paragraphs(dt.document_root(draft))
    out = []
    for d in dec.get("decisions") or []:
        if d.get("op") != "replace" or not isinstance(d.get("para"), int) or d["para"] >= len(paras):
            continue
        orig, new = paras[d["para"]], d.get("new_text") or ""
        if len(body) == len(paras) and dt.their_changes_mode(d) == "reject":
            orig = dt.received_reject_text(body[d["para"]], set(ours or ()))
        ops = dt.char_ops(orig, new)
        marked = sum((o[2] - o[1]) for o in ops if o[0] == "delete") + sum(len(o[3]) for o in ops if o[0] == "insert")
        tok_o = [t for t in re.findall(r"\w+", orig)]
        tok_n = set(re.findall(r"\w+", new))
        overlap = (sum(1 for t in tok_o if t in tok_n) / len(tok_o)) if tok_o else 0.0
        pct = int(round(100.0 * marked / max(1, len(orig) + len(new))))
        d["marked_share"], d["token_overlap"] = pct, round(overlap, 2)
        out.append((d.get("id"), pct, overlap))
    return out


def mark_survivors(draft, dec):
    """שינוי 30: בהחלפה של פסקה שלמה, כל משפט מהנוסח שלהם ששרד בנוסח החדש נרשם בבועה הפנימית,
    כדי שעורך הדין יאשר אותו במפורש, ולא יעבור כחלק מנוסח שנראה כולו שלנו."""
    paras = dt.received_paragraphs(draft)
    out = []
    for d in dec.get("decisions") or []:
        if d.get("op") != "replace" or not isinstance(d.get("para"), int) or d["para"] >= len(paras):
            continue
        new = re.sub(r"\s+", " ", d.get("new_text") or "")
        kept = [x for x in sentences(paras[d["para"]]) if re.sub(r"\s+", " ", x) in new]
        if kept:
            note = "נשאר מהנוסח שלהם, לאישור: " + " | ".join(kept)
            d["internal_comment"] = ((d.get("internal_comment") or "") + " " + note).strip()
            d["survived_sentences"] = kept
            out.append((d.get("id"), kept))
    return out


def _bare(s):
    return re.sub(r"[\s\u200e\u200f.)\-]+", "", s or "")


def _strip_once(text, num):
    """הטקסט בלי המספר שבראשו, או None כשהטקסט אינו נפתח במספר הזה (12.3 אינו 12)."""
    got, i = "", 0
    while i < len(text) and got != num:
        if _bare(text[i]):
            if not num.startswith(got + text[i]):
                return None
            got += text[i]
        i += 1
    if got != num:
        return None
    j = i
    while j < len(text) and not _bare(text[j]):
        j += 1
    rest = text[j:]
    # אחרי המספר בא מפריד ואז טקסט, או אותו מספר שוב ("5א.5א."). ספרה מיד אחריו היא תת-סעיף
    if j == i and rest:
        return None
    if rest[:1].isdigit() and _strip_once(rest, num) is None:
        return None
    return rest


def strip_repeated_number(d):
    """סעיף חדש עם number, שהטקסט שלו כבר נפתח באותו מספר, יצא "5א.5א." (הרצה חיה, 20.10.2026).
    המספר נכתב פעם אחת: מהשדה number, והטקסט מתחיל אחריו."""
    if d.get("op") != "insert_paragraph" or not d.get("number") or not d.get("text"):
        return
    num = _bare(d["number"])
    rest = _strip_once(d["text"], num) if num else None
    while rest is not None:
        d["text"] = rest
        rest = _strip_once(rest, num)


HEB = re.compile("[֐-׿]")
ENTITY_FIELDS = ("new", "new_text", "text", "external_comment")


def _name_variants(name):
    """השם כפי שנכתב, ועם גרשיים בכל צורה (בע"מ, בע״מ), כדי שכל הופעה שלו תוחלף."""
    base = name.strip()
    return sorted({base, base.replace('"', "״"), base.replace("״", '"')}, key=len, reverse=True)


def english_entity_name(dec, profile, decisions_path=None):
    """H1 (בדיקה עצמאית S1c): בהסכם באנגלית השם העברי של החברה בנוסח שהכנסנו ובבועה מוחלף בשם הרשום באנגלית
    (organization_name_en). בלי שם באנגלית בפרופיל: במציין המקום (qa_gate.ENTITY_NAME_EN_PLACEHOLDER), שהשער חוסם,
    ולעולם לא בתעתיק או בתרגום. כשהשם נמסר, גם מציין מקום שנרשם בהרצה קודמת מוחלף בו. ההחלפה נרשמת גם בקובץ ההכרעות,
    כדי ששער האיכות ישווה את ההכרעה למה שסומן בפועל. מחזיר [(מזהה ההכרעה, שדה)]."""
    he, en = profile.get("organization_name"), profile.get("organization_name_en")
    if not he:
        return []
    variants = _name_variants(he) + ([qa_gate.ENTITY_NAME_EN_PLACEHOLDER] if en else [])
    en = en or qa_gate.ENTITY_NAME_EN_PLACEHOLDER

    def fix(items):
        out = []
        for d in items:
            for k in ENTITY_FIELDS:
                v = d.get(k)
                if isinstance(v, str) and any(x in v for x in variants):
                    for x in variants:
                        v = v.replace(x, en)
                    d[k] = v
                    out.append((d.get("id"), k))
        return out

    done = fix(dec.get("decisions") or [])
    if done and decisions_path:
        with open(decisions_path, encoding="utf-8") as fh:
            raw = json.load(fh)
        fix(raw.get("decisions", []) if isinstance(raw, dict) else raw)
        with open(decisions_path, "w", encoding="utf-8") as fh:
            json.dump(raw, fh, ensure_ascii=False, indent=1)
    return done


def record_dependents(draft, decisions_path):
    """כלל 2: לכל הכרעה שמשנה משטר (regime), הסקריפט מחשב את הסעיפים שתלויים בה
    (הפניה לסעיף, מונח שהגדרתו שונתה, same_topic) ורושם אותם בקובץ ההכרעות, ב-dependents_found. שער האיכות
    (content_checks.py, DEPENDENT_UNDECIDED) אינו מאשר משלוח כל עוד יש תלוי בלי הכרעה."""
    import content_checks
    with open(decisions_path, encoding="utf-8") as fh:
        raw = json.load(fh)
    items = raw.get("decisions", []) if isinstance(raw, dict) else raw
    theirs = dt.received_paragraphs(draft)
    labels = content_checks.numbered_labels(draft)
    out, changed = [], False
    for d in items:
        deps = content_checks.dependents_of(d, theirs, labels)
        if deps:
            out.append((d.get("id"), d.get("regime"), deps))
            if d.get("dependents_found") != deps:
                d["dependents_found"], changed = deps, True
    if changed:
        with open(decisions_path, "w", encoding="utf-8") as fh:
            json.dump(raw, fh, ensure_ascii=False, indent=1)
    return out


def prior_history(profile, author, deal_dir, state):
    """הסימונים הפתוחים שלנו מסבבים קודמים, שחזרו בטיוטה (סבב 2 ואילך): (השמות שלנו, מפתחות הסימונים שלנו בקבצים
    שנשלחו). השמות: עורך הדין מהפרופיל בעברית ובאנגלית והכינויים שלו, כמו בשער האיכות. המפתחות: מהקבצים שב-
    meta.sent_documents, בלי הסימונים שכבר היו בטיוטות שהתקבלו עד אותו סבב. כך המנוע מסמן בתוך הוספה פתוחה שלנו,
    וההודעה על הכרעה שלא סומנה מבחינה בין סימון שלנו לסימון של הצד שכנגד (S1c, סבב 2, 13(ii))."""
    names = [x for x in [profile.get("lawyer_name"), profile.get("lawyer_name_en")]
             + list(profile.get("lawyer_aliases") or []) if x and x != author]
    meta = (state or {}).get("meta") or {}

    def where(rec):
        f = rec.get("file_name") or rec.get("path") or ""
        return f if os.path.isabs(f) else os.path.join(deal_dir or "", f)
    sent = [d for d in meta.get("sent_documents") or () if isinstance(d, dict)]
    if not (deal_dir and sent):
        return names, set()
    last = max(int(d.get("round") or 0) for d in sent)
    recv = [where(d) for d in meta.get("received_documents") or () if isinstance(d, dict)
            and int(d.get("round") or 0) <= last]
    return names, dt.sent_revision_keys([where(d) for d in sent], recv)


def file_prefix(a, st, profile, lang):
    """(סוג ההסכם, החברה) לשם הקובץ: התחילית שנקבעה בסבב הראשון ונשמרה בקובץ המצב (paths.stored_prefix), ולא
    --agreement-type ו---company של ההרצה (S1d-R2: "ענןפלו מערכות" בסבב 1 ו-"AnanFlow" בסבב 2). התחילית מוחלפת רק
    בתשובה לשאלה האחת (file_prefix, במנת השאלות) או ב---file-prefix switch."""
    given = (a.agreement_type, a.company or "")
    stored = paths.stored_prefix(st) if st else None
    if not stored or tuple(stored) == given:
        return given
    choice = a.file_prefix or paths.prefix_switch_answer(st)
    if choice == "switch":
        print("שם הקובץ: התחילית מוחלפת ל-\"%s\" (במקום \"%s\" מהסבב הראשון), לפי התשובה לשאלה"
              % (" - ".join(x for x in given if x), " - ".join(x for x in stored if x)))
        return given
    print("שם הקובץ: התחילית \"%s\" נקבעה בסבב הראשון ונשמרת (ולא \"%s\")"
          % (" - ".join(x for x in stored if x), " - ".join(x for x in given if x)))
    alt = given[1] if paths.name_lang(given[1]) == lang else (profile.get("organization_name_en") if lang == "en"
                                                                else "")
    if choice is None and paths.prefix_switch_item(stored, lang, alt):
        print("  התחילית בשפה שאינה שפת ההסכם. השאלה אם להחליף נשאלת פעם אחת, במנת השאלות (key: file_prefix, "
              "round_tools.py questions --profile), והתשובה נרשמת ב-negotiation_state.py decide --id file_prefix")
    return tuple(stored)


def file_date(value, lang):
    """התאריך בשם הקובץ לפי כלל 3.6: ISO (YYYY-MM-DD) שנמסר מומר; כל צורה אחרת נשארת כמו שהיא; בלעדיו היום."""
    if value and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return SB.display_date(value, lang)
    return value or SB.display_date(None, lang)


def main(argv=None):
    no_bytecode()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = parser(__doc__.split("\n")[0], out_required=False,
                out_help="קובץ העבודה (docx), במקום שם לפי הכלל. לעולם לא הטיוטה שהתקבלה")
    ap.add_argument("--draft", required=True, help="הטיוטה שהתקבלה מהצד שכנגד")
    ap.add_argument("--decisions", required=True, help="decisions_round_<n>.json")
    ap.add_argument("--profile", help="פרופיל-לקוח.json: שם עורך הדין וראשי התיבות")
    ap.add_argument("--author", help="שם עורך הדין, כשאינו בפרופיל או בקובץ ההכרעות")
    ap.add_argument("--initials", help="ראשי התיבות לבועות")
    ap.add_argument("--report", help="דוח ההרצה (JSON)")
    # השכבה הפנימית (בועות פנימיות עם הנימוק, והכותרת הפנימית) נכתבת לקובץ העבודה תמיד, כברירת מחדל. העותק
    # למשלוח נגזר בלעדיה ב-qa_gate.py --mode send. --internal-layer נשאר לתאימות
    ap.add_argument("--internal-layer", dest="internal_layer", action="store_true", default=True,
                    help="ברירת המחדל: לכתוב את השכבה הפנימית לקובץ העבודה (בועות פנימיות וכותרת פנימית)")
    ap.add_argument("--no-internal-layer", dest="internal_layer", action="store_false",
                    help="קובץ עבודה בלי השכבה הפנימית (רק לבדיקות; הנימוק נשאר בקובץ ההכרעות ובקובץ המצב)")
    ap.add_argument("--deal", help="תיקיית העסקה: שם הקובץ נגזר לפי הכלל")
    ap.add_argument("--agreement-type", help="סוג ההסכם, בשם המקוצר")
    ap.add_argument("--company", help="שם החברה המקוצר, בלי סיומת התאגדות")
    ap.add_argument("--round", type=int, help="מספר הסבב")
    ap.add_argument("--date", help="התאריך בשם הקובץ (כלל 3.6: D.M.YYYY בעברית, \"3 April 2027\" באנגלית, או ISO); בלעדיו: היום")
    ap.add_argument("--run-id", help="מזהה הריצה: הפקה מחדש באותה ריצה, לפני מסירה, מחליפה את הקבצים שלה")
    ap.add_argument("--file-prefix", choices=("keep", "switch"),
                    help="סבב המשך: keep (ברירת המחדל) שומר את תחילת שם הקובץ מהסבב הראשון; switch מחליף אותה "
                         "ל---agreement-type ו---company של ההרצה, אחרי שהמשתמש ענה לשאלה")
    a = ap.parse_args(argv)
    if bool(a.out) == bool(a.deal):
        print("יש לתת --deal עם סוג ההסכם, החברה והסבב (שם לפי הכלל), או --out מפורש, ולא את שניהם")
        return 2

    if not os.path.exists(a.draft):
        print("הטיוטה אינה קיימת: %s" % a.draft)
        return 2
    # Word פגום, DOC, מוצפן או Strict: הודעה דו-לשונית וקוד 2, ולא traceback של zipfile
    ok, msg, code = load_docx_or_explain(a.draft, loader=False)
    if ok is None:
        print(msg)
        return code
    dec = load(a.decisions, "קובץ ההכרעות")
    profile = lawyer_view(load(a.profile, "הפרופיל") if a.profile else {})

    # שם עורך הדין: מהשורה, מקובץ ההכרעות, או מהפרופיל לפי שפת ההסכם
    # (lawyer_name_en בנייר באנגלית). בלעדיו אין מי שחותם על הבועות
    lang = gap_checks.detect_lang("\n".join(dt.received_paragraphs(a.draft)))
    # השם מהפרופיל גובר על "author" שבקובץ ההכרעות: שער האיכות בודק לפי הפרופיל (qa_gate.author_for), ושם אחר
    # בקובץ ההכרעות הכשיל את כל השער בלי הסבר. --author מפורש נשאר לבדיקות ולפרופיל בלי שם
    author = a.author
    initials = a.initials
    if not author and profile.get("lawyer_name"):
        author = qa_gate.author_for(profile, lang)
        initials = initials or qa_gate.initials_for(profile, lang)
        if dec.get("author") and dec["author"] != author:
            print("  \"author\" בקובץ ההכרעות (%s) שונה מעורך הדין בפרופיל; הסימונים והבועות נחתמים בשם מהפרופיל: %s"
                  % (dec["author"], author))
    if not author:
        author = dec.get("author")
        initials = initials or dec.get("initials")
    if not a.author and needs_english_name(profile, lang):
        # בהסכם באנגלית הבועות נחתמות בשם האנגלי. השם נשאל מראש במנת השאלות (n2-questions.md); כשהוא חסר, קובץ
        # העבודה מופק בכל זאת בשם מהפרופיל, והעותק למשלוח חסום בשער (LAWYER_NAME_EN_MISSING) עד שהשם נשמר
        print("ההסכם באנגלית, ובפרופיל אין שם באנגלית לעורך הדין (lawyer_name_en). קובץ העבודה מופק, והעותק למשלוח "
              "חסום עד שהשם נמסר. שאלה אחת: \"באיזה שם באנגלית לחתום על ההערות לצד שכנגד?\" (EN: \"Which English name "
              "should sign the comments to the other side?\"); התשובה נשמרת ב-build_profile.py של רכיב ההקמה: "
              "--set branding.lawyer_name_en=\"<השם>\" --out <profile_path>, וקובץ העבודה מופק מחדש מאותן הכרעות.")
    if not author:
        print("אין שם עורך דין: לא ב---author, לא בקובץ ההכרעות ולא בפרופיל (lawyer_name). "
              "שאלו מי חותם על ההערות לצד שכנגד, ושמרו בפרופיל.")
        return 2
    # שם רשום באנגלית (organization_name_en, אופציונלי בהקמה): בהסכם באנגלית הישות שלנו נכתבת בו, ולא בשם העברי
    # (בדיקה עצמאית S1c, ממצא H1: השם העברי נכנס לבלוק הצדדים ולבלוק החתימה). בלעדיו קובץ העבודה מופק בכל זאת, הכרעה
    # שצריכה את השם מקבלת מציין מקום, והשם החסר חוסם את העותק למשלוח בשער (S1d, 28.10.2026: העצירה כאן חסמה את כל
    # הסבב, גם כששום הכרעה לא הכניסה את השם)
    name_missing = lang == "en" and profile.get("organization_name") and not profile.get("organization_name_en")
    if lang == "en":
        for did, field in english_entity_name(dec, profile, a.decisions):
            print("  %s: השם העברי של החברה ב-%s הוחלף ב%s" % (
                did, field, "מציין המקום %s" % qa_gate.ENTITY_NAME_EN_PLACEHOLDER if name_missing
                else "שם הרשום באנגלית (organization_name_en)"))
    if name_missing:
        print("ההסכם באנגלית, ובפרופיל אין שם רשום באנגלית לחברה (organization_name_en). קובץ העבודה מופק, והעותק "
              "למשלוח חסום בשער (ENTITY_NAME_EN_MISSING) עד שהשם נמסר. שאלה אחת במנת השאלות: \"מה השם הרשום של "
              "החברה באנגלית, כפי שהוא מופיע במרשם?\" (EN: \"What is the company's registered name in English?\"); "
              "התשובה נשמרת ב-organization_name_en בפרופיל ברכיב ההקמה, וקובץ העבודה מופק מחדש מאותן הכרעות. השם "
              "העברי אינו מתועתק ואינו מתורגם.")

    # הליך תחרותי לפני הגשה ותנאים מקוונים: אין סימון בגוף ואין בועות (n4c-produce.md, שלב ד; שינוי 7)
    paper, st = None, None
    if a.deal and os.path.exists(os.path.join(a.deal, "negotiation_state.json")):
        with open(os.path.join(a.deal, "negotiation_state.json"), encoding="utf-8") as fh:
            st = json.load(fh)
        paper = st.get("paper_type") or (st.get("meta") or {}).get("paper_type")
    if paper in ("tender_pre_bid", "standard_form_online"):
        print("סוג הנייר הוא %s: אין סימון בגוף ואין בועות. התוצרים נבנים ב-AREO_RT/skills/contract-negotiation-orchestrator/scripts/tender_outputs.py." % paper)
        return 2

    errors = dt.validate_decisions(dec)
    if errors:
        print("קובץ ההכרעות אינו עומד בחוזה, ולא נכתב קובץ (%d):" % len(errors))
        for e in errors:
            print("  - %s" % e)
        return 2

    send_path = None
    if a.deal:
        if not (a.agreement_type and a.round):
            print("עם --deal נדרשים --agreement-type ו---round")
            return 2
        date = file_date(a.date, lang)
        at, co = file_prefix(a, st, profile, lang)
        try:
            names = paths.safe_out_paths(a.deal, at, co, a.round, date,
                                         lang=lang)
        except paths.PathTooLong as exc:
            print("הנתיב ארוך מדי גם אחרי קיצור: %s. קצרו את שם התיקייה." % exc)
            return 2
        os.makedirs(a.deal, exist_ok=True)

        def pick(kind, name):
            # קובץ מאותה ריצה (--run-id), שלא שונה, לא נמסר ולא נשלח: מוחלף. אחרת שם חדש, " (2)"
            same = pre_send.reusable_path(a.deal, a.round, a.run_id, kind, st)
            if same:
                reused.append(kind)
            return same or paths.unique_path(name)
        reused = []
        a.out = pick("work", names.work)
        send_path = pick("send", names.send)
        produced_name = pick("as_produced", names.as_produced)
        if reused:
            print("הפקה מחדש באותה ריצה (%s), לפני מסירה: הקבצים שלה מוחלפים (%s)" % (a.run_id, ", ".join(reused)))
    expected_path, produced_path = side_paths(a.out)
    if a.deal:
        produced_path = produced_name
    try:
        out = guard_out(a.out, inputs=[a.draft, a.decisions], allow_existing_doc=bool(a.deal and "work" in reused))
        guard_out(expected_path, inputs=[a.draft, a.decisions])
        guard_out(produced_path, inputs=[a.draft, a.decisions], allow_existing_doc=True)
    except OutputRefused as exc:
        print("סירוב: %s" % exc)
        return 1

    survivors = mark_survivors(a.draft, dec)
    for d in dec["decisions"]:
        strip_repeated_number(d)
    if not a.internal_layer:
        # הנימוק הפנימי נשאר בקובץ ההכרעות (לקובץ המצב), ואינו נכנס לבועה
        for d in dec["decisions"]:
            d["internal_note"] = d.pop("internal_comment", None)
    # סעיף AREO (source_label: areo_proposal): בקובץ העבודה, גם בלי השכבה הפנימית, בועה פנימית שנפתחת בתווית הקבועה
    # ומירקור צהוב על הנוסח שלנו בסעיף (docx_tracked). העותק למשלוח נגזר בלי שניהם (strip_internal)
    areo = [d for d in dec["decisions"] if dt.is_areo_decision(d) and d.get("op") != "accept"]
    if areo:
        ui = str(profile.get("display_language") or "he")
        ui = "he" if ui not in ("he", "en") else ui
        pos = ((st or {}).get("meta") or {}).get("position") or {}
        role = (st or {}).get("meta", {}).get("our_role") or pos.get("our_side_in_agreement") or dec.get("our_role")
        company = a.company or (profile.get("organization_name_en") if ui == "en" else None) \
            or profile.get("organization_name")
        label = dt.areo_label(company, role, ui)
        for d in areo:
            note = d.get("internal_comment")
            d["internal_comment"] = label + ((" " + note) if note and not str(note).startswith(label) else "")
        print("סעיפי AREO (אין להם עמדה בפלייבוק): %d, מסומנים בקובץ העבודה במירקור צהוב ובבועה פנימית: %s"
              % (len(areo), ", ".join(str(d.get("id")) for d in areo)))
    # ההיסטוריה של העסקה: מ---deal, ואחרת מהתיקייה של קובץ ההכרעות כשיש בה קובץ מצב
    hist_dir = a.deal or os.path.dirname(os.path.abspath(a.decisions))
    st_hist = st
    if st_hist is None and os.path.exists(os.path.join(hist_dir, "negotiation_state.json")):
        try:
            with open(os.path.join(hist_dir, "negotiation_state.json"), encoding="utf-8") as fh:
                st_hist = json.load(fh)
        except ValueError:
            st_hist = None
    prior_authors, prior_keys = prior_history(profile, author, hist_dir, st_hist)
    scrubbed = scrub_internal_codes(dec["decisions"])
    if scrubbed:
        print("קודים פנימיים הוסרו מבועות לפני הכתיבה לקובץ: %d" % scrubbed)
    res = dt.apply_decisions(a.draft, dec, out_path=out, author=author, initials=initials,
                             internal_header=bool(a.internal_layer), prior_authors=prior_authors,
                             prior_keys=prior_keys)
    shares = marked_shares(a.draft, dec, {author} | set(prior_authors or ()))
    replies = [(d["reply_to_comment"], d.get("external_comment") or "") for d in dec["decisions"]
               if d.get("reply_to_comment") and d.get("external_comment")]
    thread_res = threads.apply_threads(out, replies, author) if replies and not res.get("errors") else []
    if res.get("errors"):
        print("קובץ ההכרעות נדחה: %s" % "; ".join(res["errors"]))
        return 2
    with open(expected_path, "w", encoding="utf-8") as fh:
        json.dump(res["expected_accept"], fh, ensure_ascii=False, indent=1)
    shutil.copyfile(out, produced_path)

    marked = len(dec["decisions"]) - len(res["not_marked"])
    print("קובץ העבודה: %s" % out)
    print("  הכרעות: %d, סומנו: %d%s, לא סומנו: %d" % (
        len(dec["decisions"]), marked, " (מהן קיימות מסבב קודם: %d)" % len(res["existing"]) if res.get("existing")
        else "", len(res["not_marked"])))
    for nm in res["not_marked"]:
        print("    לא סומנה %s: %s" % (nm["id"], nm["reason"]))
    for ex in res.get("existing") or ():
        print("    %s: %s" % (ex["id"], ex["note"]))
    for v in res["verify"]:
        print("  בדיקת הלוך ושוב: %s" % (v,))
    for did, pct, overlap in shares:
        print("  %s: סומנו %d%% מהפסקה%s" % (did, pct, ", ורוב המילים נשארו: לסמן ב-replace_span רק את מה שמשתנה"
                                           if pct >= 80 and overlap >= 0.4 else ""))
    for did, sents in survivors:
        print("  משפטים מהנוסח שלהם ששרדו בהחלפה %s (לאישור מפורש): %s" % (did, " | ".join(sents)))
    for cid, what in thread_res:
        print("  בועה %s שלהם: %s" % (cid, what))
    for did, regime, deps in record_dependents(a.draft, a.decisions):
        print("  סעיפים תלויים ב-%s (%s): פסקאות %s. לכל אחד הכרעה, או dependents עם keep ו-reason"
              % (did, regime, ", ".join(map(str, deps))))
    if a.deal and a.run_id:
        pre_send.update_run_record(a.deal, a.round, a.run_id, {"work": out, "as_produced": produced_path,
                                                               "expected_accept": expected_path})
    if lang == "en":
        for d in dec["decisions"]:
            heb = [k for k in ("new", "new_text", "text") if HEB.search(d.get(k) or "")]
            if heb:
                print("  אזהרה: %s מכניס אותיות עבריות לנוסח של הסכם באנגלית (%s). שער האיכות חוסם זאת "
                      "(LANG_HEBREW_IN_EN), אלא כשזה ציטוט של נוסח קיים" % (d.get("id"), ", ".join(heb)))
    print("  נוסחי היעד לשער: %s" % expected_path)
    print("  העותק כפי שהופק: %s" % produced_path)
    if send_path:
        print("  העותק למשלוח (ל-qa_gate.py --send): %s" % send_path)
    if res["not_marked"]:
        print("הכרעה שלא סומנה לא הוחלה בכלל, ולא חלקית. מסור אותה למשתמש לטיפול ידני, "
              "ואל תסמן אותה בעצמך.")

    report = {"work": out, "author": author, "lang": lang,
              "decisions": len(dec["decisions"]), "not_marked": res["not_marked"],
              "existing": res.get("existing") or [],
              "verify": res["verify"], "expected_accept": expected_path,
              "as_produced": produced_path, "send": send_path}
    if a.report:
        try:
            rp = guard_out(a.report, inputs=[a.draft, a.decisions])
        except OutputRefused as exc:
            print("הדוח לא נכתב. סירוב: %s" % exc)
        else:
            os.makedirs(os.path.dirname(os.path.abspath(rp)), exist_ok=True)
            with open(rp, "w", encoding="utf-8") as fh:
                json.dump(report, fh, ensure_ascii=False, indent=2)
    elif a.deal:
        # בלי --report: השם הקנוני runs/round-<N>/apply.json, והרצה חוזרת שומרת את הקודם ב-history (29.10.2026)
        rp = qa_gate.run_report_path(a.deal, a.round, "apply.json")
        try:
            guard_out(rp, inputs=[a.draft, a.decisions])
        except OutputRefused as exc:
            print("הדוח לא נכתב. סירוב: %s" % exc)
        else:
            print("  דוח ההרצה: %s" % qa_gate.write_run_report(rp, report))
    return 0 if res["ok"] else 3


if __name__ == "__main__":
    sys.exit(main())
