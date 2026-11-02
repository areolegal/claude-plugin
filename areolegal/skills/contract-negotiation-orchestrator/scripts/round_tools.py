#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""הכלים של הסבב: מנת השאלות, "לאישורך", נקודות לשיחה, הרשימה לפני חתימה ומידתיות.

חמשת הכלים האלה הם קוד הייחוס (`areolegal/lib/orchestrator`, הערות
הנושא ונותן 4.8 ו-4.9, שינויים 70, 71, 82, 83, 85 ו-89). עד עכשיו המודל עשה
את כולם בעצמו, וכל הרצה יצאה קצת אחרת: "נדרשת הכרעתך" בלי מספר מצב, שאלה
שנשאלה פעמיים, "טעון אישור מנכ"ל" בטבלה שאין בה שרשרת אישורים, ספירת בקשות
שכללה כותרות. כאן הם רצים בקוד, בכל סבב, באותו אופן.

* `questions` - מנת השאלות האחת שלפני ההכרעות. "נדרשת הכרעתך" רק בתשעת
  המצבים, חוסם משלוח ראשון, ושאלה שכבר נשאלה אינה נשאלת שוב. שאלת הגישה להחלת
  הפלייבוק (לפי הפלייבוק, מחמירה, מקלה) נכנסת למנה כשבקובץ המצב אין עדיין גישה,
  ושוב רק עם `--ask-stance` (המשתמש ביקש לשנות, או סבב חדש שבו המצב השתנה).
* `review` - טבלת "לאישורך" בסיכום הפנימי: סעיף, מה הוכרע, תווית מקור. אין בה
  עמודת מאשר, ונושא ציות אינו בה. בתצוגה רק הכרעות שאינן "קבל", וקבלות מהותיות
  או ויתורים מכוונים; הטבלה המלאה נכתבת לקובץ המצב.
* `talking-points` - נקודות לשיחה, עד שבע: חיכוך צפוי, נסיגה אחרונה, ויתורים
  מכוונים ומה שנשאר לשיחה. פנימי בלבד. נקודות שנכתבו ביד בקובץ המצב נשמרות:
  המיזוג הוא לפי מזהה (talking_points.merge_points).
* `signing` - הרשימה לפני חתימה, מתוצאת השער ומקובץ המצב. passed רק כשאין אף
  פריט פתוח.
* `proportionality` - ספירת הבקשות (R1 עד R3 ו-N1, בלי כותרות) מול רשימת
  המאבק. מעליה: "נדרשת הכרעתך" (מצב 4), עם שלושה ויתורים מוצעים.
* `clean-copy` - העותק הנקי לחתימה (שינוי 43): כל השינויים מתקבלים, ההערות
  והסימונים יוצאים, ו"עקוב אחר שינויים" כבוי. רק אחרי שהרשימה לפני חתימה
  עברה, ורק כשהטקסט שלו זהה לנוסח המוסכם מילה במילה.
* `round-rules` - מטריצת הסבבים (בדיקה עצמאית S1c, 28.10.2026): השורה של הסבב (מטרה, נסיגה מותרת, אורך בועה,
  טון, מה עונים על קבלה), ועם `--decisions` הבדיקה של קובץ ההכרעות מולה (question_batch.round_violations).
* `resolve-threads` - מסמן "בוצע" (w15:done) את השרשורים שלנו בנושאים שנסגרו, לפי השוואת הסבב, כדי שהקובץ שיוצא
  בסבב סגירה לא יהיה עמוס בבועות ישנות (פער 3). הבועות אינן נמחקות. כשהוא כותב על קובץ העבודה, רשומת ההפקה של
  הריצה מתעדכנת, והפקה חוזרת באותה ריצה מחליפה את הקובץ ולא יוצרת " (2)" (S1d-R2).
* `carry` - שלד ההכרעות של סבב המשך (S1d-R2): כל הכרעה מהסבב הקודם, ממופה לפי יישור טקסט לפסקה שלא השתנתה בטיוטה
  שחזרה, עם כל השדות (כולל decision_required), כקבלה ובלי בועה, ו-carried_from. פסקה שהשתנתה, הצעה שלנו שעוד פתוחה
  ובקשה חדשה שלהם נשארות להכרעה (קוד 3 כל עוד נשארו). ההכרעות שכבר נכתבו לסבב נשמרות. הכרעה שהועברה אינה בטבלת
  "לאישורך" שבתצוגה. כשהטיוטה של הסבב הקודם אינה בתיקייה, היישור הוא מול הקובץ שנשלח בסבב הקודם, בתצוגה שהצד השני
  ראה: השינויים שלנו מאותו סבב דחויים, והסימונים הפתוחים שלנו מסבבים קודמים נשארים (compare_rounds.base_paragraphs,
  S1e-R3). זו אותה תצוגה שממנה compare_rounds מחשב base_para, ולכן הוספה פתוחה שלנו מסבב קודם אינה מזיזה את היישור.

פאנל S1d-R2 ו-S1e-R3 (29.10.2026):
* `questions` קורא את `strategy-data.json` של האסטרטג (בתיקיית העסקה, או `--strategy`) ומצטט בפריט שיש לו
  `clause_ids` את גבול הקו האדום ואת החבילות. פריט שדורש תשובה מפורשת (מצב 2, counter_tighter, סכום, גבול הקו האדום,
  התחייבות תפעולית) נרשם ב-`question_batches[].requires_explicit`, ואם נענה בתשובה כללית הוא נשאל שוב. סעיף כמותי
  מורכב (`kind: composite`, או יעד שנמסר לפני ההצעה שלהם) נשאל רכיב אחר רכיב, ובסבב סגירה מעבר לנסיגה האחרונה מודפס
  לפני המנה תזכיר החלטה. כשהצד השני מאותת שהוא מוכן לסיים, מודפסת הרשימה לפני חתימה בתצוגה מקדימה.
* `signing --preview`: הרשימה לפני חתימה בלי דוח שער, ובלי רישום כ"עברה".
* `resolve-threads --decisions`: עמדה חדשה שלנו בבועה חדשה מסמנת את הבועה הקודמת שלנו בשרשור "בוצע"; תשובה באותו
  שרשור צריכה לומר "This replaces our earlier proposal." (קוד 3 כשאינה אומרת).
* `summary-head`: השורות הראשונות של הסיכום: פריט קריטי פתוח עם ההמלצה (סבב סגירה), open_items שנסגרו או שצריך
  לבדוק, ושורת עדכון הפלייבוק מהעסקה.

ב-`questions`, `--compare <round-compare.json>` מוסיף את פריטי הסבב: שינוי שקט (מצב 9, חוסם משלוח), סעיף מוסכם
שנפתח, מונח שהגדרתו נמחקה, STUCK עם הצעה לשיחה, וקבלה שעומדת לשיחה. הפריטים מחושבים ישירות מהשוואת הסבב ומההיסטוריה
שבקובץ המצב (apply_compare על עותק), ולא מקובץ המצב אחרי `write`, שרץ רק אחרי ההפקה (S1d, 28.10.2026). STUCK רק לפי
`state_builder.stuck_reason`: הצעה שלנו, או המדרגה שאחריה, שנדחתה בשני סבבים בלי תזוזה שלהם, או עמדה סופית שלהם.

* `basis` - בסיס ההשוואה, לפני `compare_rounds.py` (S1d): כשהקובץ שנשלח בסבב הקודם רשום ב-`sent_documents`,
  הבסיס ידוע (קוד 0). אחרת הכלי מדפיס שאלה אחת, שנשאלת לבד ולפני ההשוואה: זה החריג המותר למנה האחת (קוד 3). בלי
  תשובה, ההשוואה רצה מול בסיס משוער (`compare_rounds.py --deal` בלי `--sent`) ומסומנת כך, והמנה אינה שואלת שוב.
  **עותק "ממתין לשליחה" אינו הופך ל"נשלח" בלי אישור המשתמש** (S1e-R3, 28.10.2026: העותק שהופק בסבב 2 נרשם כנשלח
  אוטומטית, אף שעורכת הדין שלחה קובץ אחר שערכה). כשיש עותק למשלוח במעמד "הופק, ממתין לשליחה", השאלה קצרה: "נשלח
  העותק שהופק, X?", עם [כן] [קובץ אחר] [לא ידוע]. קובץ docx בתיקיית העסקה שנוצר אחרי ההפקה ולא הופק בידי הכלים מוצג
  כאפשרות. התשובה נרשמת ב-`negotiation_state.py sent`, שגם רושם את ההבדלים מהעותק שהופק ב-`lawyer_overrides`.

**שפה** (דרישת מוצר: display_language לשיחה, deliverable_language לתוצרים): `--lang he|en`. ב-`questions` זו שפת
הממשק (ברירת מחדל: עברית); ב-`review`, `talking-points`, `signing` ו-`proportionality` זו שפת התוצר, ובלעדיו
`meta.lang` של קובץ המצב. באנגלית: עמודות "לאישורך", התוויות, נקודות השיחה והרשימה לפני חתימה באנגלית.

עם `--deal`, התוצאה נכתבת גם לקובץ המצב של העסקה, דרך אותה בדיקה של
`negotiation_state.py`: קובץ שאינו תקין אינו נכתב במקום הקובץ החי.

קוד יציאה: **0** תקין, **3** יש ממצא (פריט פתוח לפני חתימה, הפרה בטבלה,
ספירה מעל רשימת המאבק שדורשת שאלה, או עותק נקי שאינו זהה לנוסח המוסכם),
**2** קלט חסר, **1** נתיב פלט שסורב.
"""
import argparse
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # גם ב-python -I, שאינו מוסיף את תיקיית הסקריפט
import areo_lib  # noqa: F401  מוסיף את areolegal/lib לנתיב הייבוא

from orchestrator import proportionality as P  # noqa: E402
from orchestrator import question_batch as QB  # noqa: E402
from orchestrator import review_table as RT  # noqa: E402
from orchestrator.resolve_playbook import is_proposed_status  # noqa: E402
from orchestrator import signing_checklist as SC  # noqa: E402
from orchestrator import state_builder as SB  # noqa: E402
from orchestrator import talking_points as TP  # noqa: E402
import copy  # noqa: E402
import threads as TH  # noqa: E402
from lawyer import lawyer_view  # noqa: E402
import common.docx_tracked as dt  # noqa: E402
from common import gap_checks, paths  # noqa: E402
from common.cli import OutputRefused, guard_out  # noqa: E402
from lxml import etree  # noqa: E402

LIVE = "negotiation_state.json"
MAX_TALKING_POINTS = 7


def load(path, what, required=True):
    if not path:
        if required:
            print("חסר %s" % what)
            raise SystemExit(2)
        return None
    if not os.path.exists(path):
        print("%s אינו קיים: %s" % (what, path))
        raise SystemExit(2)
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def decisions_of(path):
    dec = load(path, "קובץ ההכרעות")
    return dec.get("decisions", []) if isinstance(dec, dict) else dec


def state_of(deal):
    if not deal:
        return None
    p = os.path.join(deal, LIVE)
    return load(p, "קובץ המצב") if os.path.exists(p) else None


def save_state(deal, state):
    """אותו כלל כמו negotiation_state.py: קובץ לא תקין אינו מחליף את החי. meta.updated_by: orchestrator."""
    state.setdefault("meta", {})["updated_by"] = "orchestrator"
    errors = SB.validate_state(state)
    if errors:
        rej = os.path.join(deal, "negotiation_state.rejected.json")
        with open(rej, "w", encoding="utf-8") as fh:
            json.dump(state, fh, ensure_ascii=False, indent=1)
        print("קובץ המצב לא עודכן (%d שגיאות), והגרסה שנדחתה ב-%s:" % (len(errors), rej))
        for e in errors[:10]:
            print("  [%s] %s" % (e.get("code"), e.get("message")))
        return False
    state["meta"]["last_updated"] = SB.now_iso()
    with open(os.path.join(deal, LIVE), "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=1)
    print("קובץ המצב עודכן: %s" % os.path.join(deal, LIVE))
    return True


def profile_deliverable_lang(profile):
    """שפת התוצר הפנימי מהפרופיל (language-policy.md, שלב 4): he או en כמו שהם, ו-both הוא שפת הממשק
    (display_language), כי התוצר הראשי בשפת הממשק. התוצר לצד שכנגד (בועות, עותק למשלוח) תמיד בשפת ההסכם, ואינו
    נקבע כאן (באג 8, הרצה S1b, 28.10.2026)."""
    p = profile or {}
    v = str(p.get("deliverable_language") or "").lower()
    if v == "both" or not v:
        v = str(p.get("display_language") or "").lower()
    return v[:2] if v[:2] in ("he", "en") else None


def out_lang(a, st):
    """שפת התוצר: --lang, אחריו הפרופיל (--profile, deliverable_language, ו-both לפי display_language), ואחריו
    meta.lang של קובץ המצב."""
    prof = load(a.profile, "הפרופיל", required=False) if getattr(a, "profile", None) else None
    v = str(getattr(a, "lang", None) or profile_deliverable_lang(prof)
            or ((st or {}).get("meta") or {}).get("lang") or "he").lower()
    return "en" if v[:2] == "en" else "he"


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def compare_round(st, compare):
    """הסבב שהשוואת הסבב שייכת לו: הסבב שבו הטיוטה שחזרה כבר רשומה ב-received_documents (write של הסבב כבר רץ),
    ואחרת הסבב שבקובץ המצב ועוד אחד. כך הפעלה אחרי write אינה מחשבת סבב נוסף (S1d)."""
    meta = (st or {}).get("meta") or {}
    rec = (compare or {}).get("received")
    if rec and os.path.exists(rec):
        sha = _sha(rec)
        for d in meta.get("received_documents") or ():
            if isinstance(d, dict) and d.get("sha256") == sha and str(d.get("round") or "").isdigit():
                return int(d["round"])
    return int(meta.get("round_number") or 0) + 1


def compare_applied(st, rnd):
    """write --compare של הסבב כבר החיל את ההשוואה על קובץ המצב: אין מחילים אותה שוב (מפת הסעיפים כבר לפי הטיוטה של
    הסבב, והחלה שנייה הייתה מצמידה סעיפים לפסקאות הלא נכונות)."""
    meta = (st or {}).get("meta") or {}
    if int(meta.get("round_number") or 0) != int(rnd):
        return False
    return any(int(c.get("their_change_round") or 0) == rnd or c.get("closed_in_round") == rnd
               or int((c.get("escalation") or {}).get("round") or 0) == rnd for c in st.get("clauses") or ()) \
        or any(int(x.get("round") or 0) == rnd for x in st.get("silent_changes") or ())


def sent_basis(st, rnd=None):
    """(הרשומה ב-sent_documents של הסבב, או None; הסבב; הקובץ המומלץ כשאין רשומה: העותק למשלוח, ובלעדיו קובץ העבודה
    האחרון שהופק, לפי produced_documents)."""
    meta = (st or {}).get("meta") or {}
    rnd = int(rnd or meta.get("round_number") or 1)
    rec = next((d for d in reversed(meta.get("sent_documents") or []) if isinstance(d, dict)
                and str(d.get("round")) == str(rnd)), None)
    prod = [d for d in (st or {}).get("produced_documents") or () if isinstance(d, dict)]
    best = next((d.get("path") for d in reversed(prod) if d.get("kind") == "send"), None) or \
        next((d.get("path") for d in reversed(prod) if d.get("kind") == "work"), None)
    return rec, rnd, best


def cmd_basis(a):
    """בסיס ההשוואה, לפני compare_rounds.py: ידוע (קוד 0), או שאלה אחת שנשאלת לבד, לפני ההשוואה (קוד 3)."""
    st = state_of(a.deal)
    if st is None:
        print("אין קובץ מצב בתיקיית העסקה: אין סבב קודם, ואין בסיס להשוואה")
        return 2
    rec, rnd, best = sent_basis(st, a.round)
    en = a.lang == "en"
    sc = (st.get("quality_gate") or {}).get("send_copy") or {}
    if not rec and sc.get("status") == "produced_pending_send" and sc.get("path"):
        # העותק למשלוח של הסבב הקודם, "הופק, ממתין לשליחה": אינו נרשם כנשלח בלי אישור המשתמש (S1e-R3, 28.10.2026).
        # שאלה אחת וקצרה, וקבצים שנוצרו בתיקייה אחרי ההפקה ולא הופקו בידי הכלים מוצגים כאפשרות
        name = os.path.basename(sc["path"])
        others = candidate_sent_files(st, a.deal, sc.get("recorded_at"))
        opts = (["Yes"] + ["Another file: %s" % f for f in others] + ["Another file: attach it", "Unknown"] if en else
                ["כן"] + ["קובץ אחר: %s" % f for f in others] + ["קובץ אחר: צרפו אותו", "לא ידוע"])
        print(("Was the produced copy sent, %s? %s" if en else "נשלח העותק שהופק, %s? %s")
              % (name, " ".join("[%s]" % o for o in opts)))
        print(("Yes: negotiation_state.py sent --deal <deal> --file \"%s\" --round %d. Another file: "
               "negotiation_state.py sent --deal <deal> --file <the file> --round %d (the differences from the produced "
               "copy are recorded "
               "in lawyer_overrides, and the comparison is against the file that was sent). Unknown: compare_rounds.py "
               "--deal without --sent compares against the produced copy, marked \"assumed base\"." if en else
               "כן: negotiation_state.py sent --deal <תיקיית העסקה> --file \"%s\" --round %d. קובץ אחר: "
               "negotiation_state.py sent --deal <תיקיית העסקה> --file <הקובץ> --round %d (ההבדלים מהעותק שהופק נרשמים "
               "ב-lawyer_overrides, וההשוואה היא מול הקובץ שנשלח). לא ידוע: compare_rounds.py --deal בלי --sent משווה "
               "לעותק שהופק, מסומן \"בסיס משוער\".") % (name, rnd, rnd))
        return 3
    if rec:
        f = rec.get("file_name") or ""
        p = f if os.path.isabs(f) else os.path.join(a.deal, f)
        if os.path.exists(p) and (not rec.get("sha256") or _sha(p) == rec.get("sha256")):
            print(("Comparison base for round %d is known: %s (%s). Run compare_rounds.py --deal without --sent."
                   if en else "בסיס ההשוואה של סבב %d ידוע: %s (%s). compare_rounds.py --deal רץ בלי --sent.")
                  % (rnd, f, rec.get("basis") or "user_confirmed"))
            return 0
        # הקובץ שנרשם אינו בנתיב, או שטביעת האצבע שלו אינה תואמת: הבסיס אינו ידוע, והשאלה נשאלת לבד
        print(("The file recorded as sent in round %d (%s) is missing or was changed after it was recorded."
               if en else "הקובץ שנרשם כנשלח בסבב %d (%s) אינו בנתיב, או שהשתנה אחרי שנרשם.") % (rnd, f))
        best = f or best
        lead = ("Which file was actually sent to the other side in round %d? %s" if en else
                "איזה קובץ נשלח בפועל לצד שכנגד בסבב %d? %s")
    else:
        lead = ("The send copy of round %d is not recorded as sent. Put this question in the single opening batch, and "
                "meanwhile compare against the last work file (assumed basis): which file was sent to the other side in "
                "round %d? %s"
                if en else "העותק למשלוח של סבב %d אינו רשום כנשלח. השאלה נכנסת למנה האחת שבפתיחה, וההשוואה רצה "
                "בינתיים מול קובץ העבודה האחרון (בסיס משוער): איזה קובץ נשלח לצד שכנגד בסבב %d? %s")
    opts = (["%s (recommended)" % best] if en else ["%s (ההמלצה)" % best]) if best else []
    since = next((d.get("produced_at") for d in reversed((st or {}).get("produced_documents") or ())
                  if isinstance(d, dict) and d.get("path") == best), None)
    opts += [f for f in candidate_sent_files(st, a.deal, since) if f != best]
    opts += (["Another file: attach it", "Unknown"] if en else ["קובץ אחר: צרפו אותו", "לא ידוע"])
    opts_s = " ".join("[%s]" % o for o in opts)
    print(lead % ((rnd, opts_s) if lead.count("%") == 2 else (rnd, rnd, opts_s)))
    print(("Answer: negotiation_state.py sent --deal <deal> --file <file> --round %d, then compare_rounds.py --deal "
           "without --sent. No answer, or \"Unknown\": compare_rounds.py --deal without --sent compares against the "
           "last work file, marked \"assumed base\", and the batch does not ask again."
           if en else "תשובה: negotiation_state.py sent --deal <תיקיית העסקה> --file <הקובץ> --round %d, ואחריה "
           "compare_rounds.py --deal בלי --sent. בלי תשובה, או \"לא ידוע\": compare_rounds.py --deal בלי --sent משווה "
           "לקובץ העבודה האחרון, מסומן \"בסיס משוער\", והמנה אינה שואלת שוב.") % rnd)
    return 3


def candidate_sent_files(st, deal, since=None):
    """קבצי docx בתיקיית העסקה שנוצרו או נשמרו אחרי ההפקה (since, ISO) ולא הופקו בידי הכלים: אינם ב-produced_documents
    (לפי נתיב או טביעת אצבע), אינם טיוטה שהתקבלה, ואינם קובץ עבודה או "כפי שהופק" (גם עם " (2)"). לאפשרות "קובץ אחר"
    בשאלה מה נשלח (S1e-R3: עורכת הדין ערכה ושלחה קובץ משלה). החדש ראשון."""
    import datetime as _dtm
    prod = [d for d in (st or {}).get("produced_documents") or () if isinstance(d, dict)]
    names = {os.path.normcase(os.path.basename(d.get("path") or "")) for d in prod}
    stems = {re.sub(r" \(\d+\)$", "", os.path.splitext(n)[0]) for n in names}
    shas = {d.get("sha256") for d in prod} | {d.get("sha256") for d in ((st or {}).get("meta") or {}).get(
        "received_documents") or () if isinstance(d, dict)}
    try:
        t0 = _dtm.datetime.fromisoformat(since).timestamp() if since else None
    except ValueError:
        t0 = None
    out = []
    for f in os.listdir(deal):
        n = os.path.normcase(f)
        if not n.endswith(".docx") or f.startswith("~$") or n in names:
            continue
        if re.sub(r" \(\d+\)$", "", os.path.splitext(n)[0]) in stems or re.search(
                r" - (?:internal|as produced)(?: \(\d+\))?$|לא למשלוח", os.path.splitext(n)[0]):
            continue
        p = os.path.join(deal, f)
        t = max(os.path.getmtime(p), os.path.getctime(p))
        if (t0 is not None and t < t0) or _sha(p) in shas:
            continue
        out.append((t, f))
    return [f for _t, f in sorted(out, reverse=True)]


def prefix_item(st, compare, a):
    """שאלת ההחלפה של תחילת שם הקובץ (paths.prefix_switch_item), או None: אין קובץ מצב, אין השוואת סבב שממנה ידועה
    שפת ההסכם, השאלה כבר נענתה, או שאין מה לשאול."""
    if not st or compare is None or paths.prefix_switch_answer(st):
        return None
    rec = compare.get("received")
    if not rec or not os.path.exists(rec):
        return None
    try:
        lang = gap_checks.detect_lang("\n".join(dt.received_paragraphs(rec)))
    except Exception:  # noqa: BLE001  טיוטה שאינה נקראת: אין שאלה
        return None
    prof = load(a.profile, "הפרופיל", required=False) if getattr(a, "profile", None) else None
    ent = ((st.get("entity_details") or {}).get("name_en") or {})
    alt = (prof or {}).get("organization_name_en") or (ent.get("value") if isinstance(ent, dict) else "")
    return paths.prefix_switch_item(paths.stored_prefix(st), lang, alt, a.lang or "he")


def sensitive_item(st, a):
    """אין שאלה על נושאים רגישים. עורך דין מאשר את הפלייבוק בלבד (כלל יסוד 6); הנושא ונותן שואל את רשימת
    השאלות שלו ומוסר. סעיף בנושא רגיש שאין עליו עמדה בפלייבוק מופיע ללקוח כפריט גלוי, "AREO לא מצאה מקור מורשה
    לנקודה זו" (NO_APPROVED_SOURCE, content_checks.py), ואינו מעכב את המשלוח. נשאר כפונקציה שמחזירה None, כדי
    שהקריאה לה במנת השאלות תמשיך לעבוד."""
    return None


CODE_RX = re.compile(r"\s*\((?:\s*(?:[ARKNQ]|REG-?|APR-?)\d+[a-z]?\s*,?)+\)|\b(?:[ARKNQ]\d{1,3}[a-z]?|REG-\d+|APR-\d+)\b")


def client_text(t, core=None, lang="he"):
    """טקסט שמוצג ללקוח: בלי מזהים פנימיים בסוגריים או לבד ("subprocessors (R43)", "A10"), מזהה כלל -> שם הנושא
    כשיש גרעין, ו"סבב 1" -> "סבב ראשון" (content_checks.scrub_client_text: הניקוי האחד של שכבת הבנייה)."""
    import content_checks as CC
    t = CODE_RX.sub("", str(t or ""))
    return CC.scrub_client_text(t, core, lang)


def is_deal_only(st):
    """הלקוחה בחרה לעבוד בלי פלייבוק: ביקורת לעסקה זו בלבד (positions_source.mode: deal_only)."""
    ps = (st or {}).get("positions_source")
    return isinstance(ps, dict) and ps.get("mode") == "deal_only"


def cmd_questions(a):
    items = load(a.items, "רשימת הפריטים")
    st = state_of(a.deal)
    asked = set(a.asked_before or ())
    if st:
        for b in st.get("question_batches") or ():
            asked |= set(b.get("keys") or ())
        # פריט שדורש תשובה מפורשת ונענה בתשובה כללית נשאר פתוח, ונשאל שוב במפורש (פאנל S1d-R2)
        asked -= SB.held_for_explicit(st)
    # הסימונים של האסטרטג (strategy-data.json בתיקיית העסקה): גבול הקו האדום וחבילות, מצוטטים בפריטים (פאנל S1d-R2)
    strategy = load(a.strategy, "נתוני האסטרטג", required=False) if a.strategy else (
        load(os.path.join(a.deal, "strategy-data.json"), "נתוני האסטרטג", required=False)
        if a.deal and os.path.exists(os.path.join(a.deal, "strategy-data.json")) else None)
    # שאלת הגישה (דרישת מוצר 28.10.2026): בסבב הראשון, או כשאין עדיין גישה בקובץ המצב; שוב רק עם --ask-stance
    if a.ask_stance:
        asked.discard("stance")
    # בהליך תחרותי ובתנאים מקוונים אין "איך להחיל את הפלייבוק": הנוסח אינו פתוח למשא ומתן
    tender = ((st or {}).get("meta") or {}).get("paper_type") in ("tender_pre_bid", "tender_awarded", "standard_form_online")
    # בלי פלייבוק מתאים אין "איך להחיל את הפלייבוק"
    res0 = (st or {}).get("playbook_resolution") or {}
    tender = tender or bool(res0 and res0.get("result") not in (None, "match"))
    # בלי פלייבוק (positions_source.mode: deal_only) אין "איך להחיל את הפלייבוק": הגישה היא של הפלייבוק, ואין פלייבוק
    tender = tender or is_deal_only(st)
    if not tender and (a.ask_stance or not SB.stance_of(st)) and not any(isinstance(i, dict) and i.get("key") == "stance"
                                                          for i in items):
        items = [QB.stance_item(a.lang or "he")] + list(items)
    # תנאי ההפעלה של הפלייבוק (activation_ok: false): שאלה אחת, מצב 4, עד שנרשמה תשובה (decide --id playbook_activation)
    resolution = load(a.resolution, "תוצאת האיתור", required=False) or (st or {}).get("playbook_resolution")
    answered = any(q.get("id") == "playbook_activation" for q in (st or {}).get("user_decisions") or ())
    # הצד שלנו לפי ההסכם סותר את הפוזיציה שנמסרה (resolve_playbook.py --draft): שאלה אחת, ראשונה
    sc = (resolution or {}).get("side_check") or {}
    if sc.get("conflict") and sc.get("question") and not any(q.get("id") == "side_conflict" for q in
                                                             (st or {}).get("user_decisions") or ()):
        if not any(isinstance(i, dict) and i.get("key") == "side_conflict" for i in items):
            items = [sc["question"]] + list(items)
    act = QB.activation_item(resolution, a.lang or "he", kind_segment=a.kind_segment)
    if act and not answered and not any(isinstance(i, dict) and i.get("key") == act["key"] for i in items):
        items = list(items) + [act]
    # פריטי הסבב מהשוואת הסבב: על עותק של קובץ המצב שהשוואת הסבב כבר הוחלה עליו (write יחיל אותה שוב, בסוף הסבב)
    # STUCK, הסלמה ושאר פריטי הסבב מחושבים כאן מהשוואת הסבב ומההיסטוריה שבקובץ המצב, ולא מקובץ המצב אחרי write
    compare = load(a.compare, "השוואת הסבב", required=False)
    status_line = a.status_line
    if ((st or {}).get("meta") or {}).get("paper_type") == "tender_awarded":
        # הליך תחרותי אחרי זכייה: משפט פשוט בראש המנה, שהתנאים אינם משתנים ושמתקנים רק טעויות
        only = PAPER_Q["en" if a.lang == "en" else "he"]["only_errors"]
        status_line = "%s\n%s" % (only, status_line) if status_line else only
    rnd = SB.current_round(st) if st is not None else None
    preview = None
    if compare is not None:
        rnd = compare_round(st, compare)
        preview = copy.deepcopy(st) if st else SB.skeleton()
        if not compare_applied(preview, rnd):
            SB.apply_compare(preview, compare, rnd)
        have = {i.get("key") for i in items if isinstance(i, dict)}
        items = list(items) + [i for i in QB.round_items(compare, preview, rnd, a.lang or "he", strategy=strategy)
                               if i["key"] not in have]
        if compare.get("base") == "assumed":
            note = ("Assumed base: the comparison is against %s, the last work file; an unmarked change may be our own "
                    "edit before sending." if a.lang == "en" else "בסיס משוער: ההשוואה היא מול %s, קובץ העבודה האחרון; "
                    "שינוי שלא סומן עשוי להיות עריכה שלנו לפני המשלוח.") % os.path.basename(compare.get("sent") or "?")
            status_line = "%s\n%s" % (status_line, note) if status_line else note
    # תחילת שם הקובץ נקבעה בסבב הראשון. כשהיא בשפה שאינה שפת ההסכם, ועכשיו ידוע שם החברה בשפת ההסכם (בפרופיל, או
    # בפרטי הישות שבקובץ המצב), נשאלת פעם אחת אם להחליף (S1d-R2). apply_redlines.py קורא את התשובה
    fp = prefix_item(st, compare, a)
    if fp and fp["key"] not in {i.get("key") for i in items if isinstance(i, dict)}:
        items = list(items) + [fp]
    # הסכם באנגלית: שם החותם על הבועות ושם החברה באנגלית נשאלים מראש, כשהם חסרים בפרופיל
    if getattr(a, "agreement_lang", None) == "en" and a.profile:
        prof = lawyer_view(load(a.profile, "הפרופיל", required=False) or {})
        have = {i.get("key") for i in items if isinstance(i, dict)}
        items = list(items) + [i for i in QB.english_name_items(prof, a.lang or "he") if i["key"] not in have]
    # אין שאלת אישור משפטי על נושאים רגישים (כלל יסוד 6): נושא בלי עמדה בפלייבוק מוצג כפריט גלוי, ואינו מעכב
    # השאלה "איזה קובץ נשלח" אינה במנה: היא נשאלת לבד, לפני ההשוואה (round_tools.py basis)
    dropped = [i for i in items if isinstance(i, dict) and i.get("kind") == "sent_basis"]
    items = [i for i in items if i not in dropped]
    for i in dropped:
        print(("  (not asked: %s, the sent file is asked alone before the comparison: round_tools.py basis)"
               if a.lang == "en" else "  (לא נשאלה: %s, הקובץ שנשלח נשאל לבד לפני ההשוואה: round_tools.py basis)")
              % (i.get("key") or i.get("text")))
    try:
        b = QB.build_batch(items, no_consideration=a.no_consideration, asked_before=asked,
                           max_questions=a.max, status_line=status_line, lang=a.lang or "he", strategy=strategy,
                           round_number=rnd)
    except ValueError as exc:
        print("המנה לא נבנתה: %s" % exc)
        return 2
    # תזכיר החלטה להנהלה (סבב סגירה, ההצעה שלהם מעבר לנסיגה האחרונה): לפני המנה, במקום בועה (פאנל S1e-R3)
    for m in b.get("memos") or ():
        print(m)
        print("")
    print(b["text"])
    for s in b["skipped"]:
        print(("  (not asked: %s, %s)" if a.lang == "en" else "  (לא נשאלה: %s, %s)") % (s["key"], s["why"]))
    # הצד השני מאותת שהוא מוכן לסיים: הרשימה לפני חתימה בתצוגה מקדימה, עם מה שחסר (פאנל S1e-R3)
    ready = QB.ready_signal(compare) if compare is not None else None
    if ready:
        print_signing_preview(preview if preview is not None else st, a, ready)
    fresh = False
    if st is None and a.deal and os.path.isdir(a.deal):
        # סבב ראשון, לפני write: המנה נרשמת בשלד של קובץ המצב, כדי ששאלה שנשאלה לא תישאל שוב ו-decide ימצא את
        # requires_explicit. write בסוף הסבב ממזג את השלד ואינו דורס את question_batches
        st, fresh = SB.skeleton(), True
        st["meta"].update(transaction_id=os.path.basename(os.path.abspath(a.deal)), round_number=1,
                          round_stage=SB.stage_for_round(1), generated_at=SB.now_iso(), last_updated=SB.now_iso())
        if SB.validate_state(st):
            st = None
    if st is not None:
        # הסבב של המנה: לפי השוואת הסבב כשנמסרה, ואחרת הסבב הנוכחי לפי קובץ המצב. meta.round_number מתעדכן רק ב-write
        # שבסוף הסבב, ולכן המנה של סבב 2 נרשמה כסבב 1 (S1d-R2)
        rec = {"round": compare_round(st, compare) if compare is not None else SB.current_round(st),
               "asked_at": SB.now_iso(),
               "keys": [k for q in b["questions"] for k in (q.get("group_keys") or [q.get("key") or q.get("text")])]}
        if b.get("deferred") or b.get("applied_by_recommendation"):
            # מעבר לתקרה: נשאלים במנה הבאה, או הוכרעו לפי ההמלצה ומוצגים בטבלת "לאישורך"
            rec["deferred"] = b.get("deferred") or []
            rec["applied_by_recommendation"] = b.get("applied_by_recommendation") or []
        if b.get("requires_explicit"):
            # negotiation_state.py decide קורא את הרשימה: תשובה כללית לפריט כזה אינה מחילה את ההמלצה
            rec["requires_explicit"] = b["requires_explicit"]
        st.setdefault("question_batches", []).append(rec)
        if not save_state(a.deal, st):
            return 0 if fresh else 3
    return 0


def print_signing_preview(st, a, ready):
    """הרשימה לפני חתימה בתצוגה מקדימה, בלי דוח שער: מה שחסר עכשיו. אינה נרשמת כ"עברה" ואינה מפיקה עותק."""
    en = (a.lang or "he") == "en"
    print(("\nThe other side signals it is ready to finalise (comment %s): \"%s\". Pre-signing checklist, preview:"
           if en else "\nהצד השני מאותת שהוא מוכן לסיים (בועה %s): \"%s\". הרשימה לפני חתימה, בתצוגה מקדימה:")
          % (ready.get("root_id"), ready.get("text")))
    prof = load(a.profile, "הפרופיל", required=False) if getattr(a, "profile", None) else None
    res = SC.build_signing_checklist({}, state=st or {}, profile=prof, lang="en" if en else "he")
    opened = [c for c in res["checks"] if c.get("status") == "open"]
    for line in SC.render_lines({"checks": opened, "passed": not opened}, "en" if en else "he")[:-1][:12]:
        print(line)
    print(("  %d items missing before signature (preview; not recorded as passed)" if en else
           "  חסרים %d פריטים לפני חתימה (תצוגה מקדימה; אינה נרשמת כ\"עברה\")") % len(opened))


def cmd_review(a):
    decisions = decisions_of(a.decisions)
    st = state_of(a.deal)
    nm = (st or {}).get("numbering_map") or {}
    conc = load(a.concessions, "הוויתורים", required=False) or (st or {}).get("deliberate_concessions") or []
    lang = out_lang(a, st)
    s = st or {}
    # פלייבוק במעמד Draft או "מוצע": "מפלייבוק מוצע", ולא "מהפלייבוק" (באג 7, הרצה S1b)
    proposed = (((s.get("positions_source") or {}).get("way") == "proposed_playbook")
                or is_proposed_status(s.get("playbook_status"))
                or is_proposed_status((s.get("playbook_resolution") or {}).get("playbook_status")))
    rows = RT.build_review_table(decisions, numbering_map=nm, concessions=conc, lang=lang, proposed=proposed)
    # בתצוגה: רק הכרעות שאינן "קבל", וקבלות מהותיות או ויתורים מכוונים (הרצה S1c). הטבלה המלאה נשמרת בקובץ המצב
    shown, hidden = (rows, 0) if a.full else RT.display_rows(decisions, rows, conc)
    print(RT.render_markdown(shown, lang))
    if hidden:
        print(RT.hidden_line(hidden, lang))
    # התווית מצטטת את תשובת המשתמש מילה במילה ('הכרעתך ("מאשרים...")'), והבדיקה
    # אוסרת את המילה "מאשר" כסימן לשרשרת אישורים. ציטוט של המשתמש אינו שרשרת
    # אישורים, ולכן הוא מוסר מהטקסט הנבדק בלבד; כל שאר הטבלה נבדקת כרגיל
    col = RT.columns(lang)[2]
    masked = [dict(r, **{col: re.sub(r'\("[^"]*"\)', '("…")', str(r.get(col, "")))}) for r in rows]
    bad = RT.check_review_table(masked, decisions, lang)
    for v in bad:
        print("  הפרה בטבלה: %s" % v)
    if st is not None:
        # שורות של סבב קודם נשמרות תחת הסבב שלהן (round), ורק שורות הסבב הנוכחי מוחלפות (S1d)
        cur = str((st.get("meta") or {}).get("round_number"))
        st["review_table"] = [r for r in st.get("review_table") or [] if isinstance(r, dict) and r.get("round")
                              and str(r["round"]) != cur] + rows
        if not save_state(a.deal, st):
            return 3
    return 3 if bad else 0


def cmd_talking_points(a):
    decisions = decisions_of(a.decisions)
    st = state_of(a.deal)
    conc = load(a.concessions, "הוויתורים", required=False) or (st or {}).get("deliberate_concessions") or []
    # אין סימון "נבדק" של עורך דין בנקודות לשיחה (כלל יסוד 6): הנסיגה שבפלייבוק מוצגת כמו שהיא
    reviewed = set()
    # STUCK מקובץ המצב (escalation, לפי state_builder.stuck_reason): נקודה לשיחה עם הצעה להסלמה
    stuck = [{"id": c.get("clause_id"), "topic": c.get("contract_ref") or c.get("clause_id"),
              "escalation": c.get("escalation")} for c in (st or {}).get("clauses") or ()
             if c.get("status") == "STUCK" and c.get("escalation")
             and c.get("clause_id") not in {d.get("id") for d in decisions}]
    pts = TP.build_talking_points(list(decisions) + stuck, conc, lang=out_lang(a, st), reviewed=reviewed)
    # מיזוג לפי מזהה: נקודה שנכתבה ביד, ונקודה שנסגרה בשיחה, נשארות כמו שהן (הרצה S1c: הכלי דרס נקודות ידניות).
    # נקודה מסבב קודם מתעדכנת לפי מצב הסעיף: סעיף שהוסכם, או שהצד השני שינה בסבב הזה, מסמן אותה superseded (S1e-R3)
    rnd = SB.current_round(st) if st is not None else None
    merged = TP.merge_points((st or {}).get("talking_points") or [], pts, clauses=(st or {}).get("clauses"),
                             round_number=rnd, lang=out_lang(a, st))
    shown = [p for p in merged if not (isinstance(p, dict) and p.get("status") == "superseded")]
    for p in merged:
        if isinstance(p, dict) and (p.get("superseded") or {}).get("round") == rnd and rnd:
            print("  עודכנה לפי מצב הסעיף: %s (%s)" % (p.get("topic") or p.get("id"), p["superseded"].get("why")))
    if len(shown) > MAX_TALKING_POINTS:
        print("  %d נקודות; בסיכום מוצגות שבע הראשונות" % len(shown))
    for n, p in enumerate(shown[:MAX_TALKING_POINTS], 1):
        print("%d. %s" % (n, p.get("text") or "%s: %s" % (p.get("topic", ""), p.get("our_goal", ""))))
    if st is not None:
        st["talking_points"] = merged
        if not save_state(a.deal, st):
            return 3
    return 0


def cmd_signing(a):
    if a.preview:
        # תצוגה מקדימה (הצד השני מאותת שהוא מוכן לסיים): מה שחסר עכשיו, בלי דוח שער ובלי רישום כ"עברה"
        st = state_of(a.deal)
        print_signing_preview(st, a, {"root_id": "-", "text": a.preview if isinstance(a.preview, str) else ""})
        return 0
    gate = load(a.gate, "דוח השער")
    st = state_of(a.deal)
    # בדיקה בקריאה שנכשלה (--fail) נשארת פתוחה בהרצות הבאות עד --pass של אותה בדיקה, ואינה נמחקת בשקט
    try:
        manual = SC.parse_manual(a.fail)
        passed_now = {m["check"] for m in SC.parse_manual("%s=" % x for x in a.pass_ or ())}
    except ValueError as exc:
        print(exc)
        return 2
    for c in ((st or {}).get("signing_checklist") or {}).get("checks") or ():
        if isinstance(c, dict) and c.get("item") == "manual_check" and c.get("status") == "open"                 and c.get("check") not in passed_now and c.get("check") not in {m["check"] for m in manual}:
            manual.append({"check": c.get("check"), "detail": c.get("detail") or ""})
            print("נשארת פתוחה מהרצה קודמת: %s (משחרר: --pass %s)" % (c.get("check"), c.get("check")))
    res = SC.build_signing_checklist(gate.get("info") or {}, state=st,
                                     profile=load(a.profile, "הפרופיל", required=False),
                                     decisions=decisions_of(a.decisions) if a.decisions else None,
                                     lang=out_lang(a, st), manual=manual)
    for line in SC.render_lines(res, out_lang(a, st)):
        print(line)
    if st is not None:
        sc = st.get("signing_checklist") or {}
        sc.update(res)
        st["signing_checklist"] = sc
        if not save_state(a.deal, st):
            return 3
    return 0 if res["passed"] else 3


def cmd_proportionality(a):
    decisions = decisions_of(a.decisions)
    lang = out_lang(a, None)
    res = P.assess(decisions, a.fight_list, value_band=a.value_band, value_text=a.value_text,
                   user_choice=a.user_choice, answer_kind=a.answer_kind, lang=lang)
    print(res["summary_line"])
    if res["question_required"]:
        en = lang == "en"
        print(("%s: more requests (%d) than the fight list (%d)." if en else "%s: יותר בקשות (%d) מרשימת המאבק (%d).")
              % (QB.label_for(4, lang=lang), res["counts"]["asks"], a.fight_list))
        print(("  Proposed concessions: %s" if en else "  ויתורים מוצעים: %s")
              % ", ".join(res["proposed_concessions"] or ["none" if en else "אין"]))
        print(("  Options: %s" if en else "  אפשרויות: %s") % " | ".join(res.get("options") or ()))
    for v in res["violations"]:
        print("  הפרה: %s" % v)
    return 3 if res["question_required"] or res["violations"] else 0


CLEAN_PARTS = re.compile(r"^word/(document|header\d*|footer\d*|footnotes|endnotes)\.xml$")
COMMENT_PARTS = re.compile(r"^word/comments(Extended|Ids|Extensible)?\.xml$")


def _merge_deleted_marks(root):
    """פסקה שסימן הפסקה שלה נמחק מתמזגת עם הפסקה הבאה, כמו "קבל הכול" ב-Word."""
    paras = dt.body_paragraphs(root)
    for i, p in enumerate(paras):
        rpr = p.find(dt.W + "pPr/" + dt.W + "rPr")
        if rpr is None or rpr.find(dt.W + "del") is None:
            continue
        if i + 1 >= len(paras):
            continue
        nxt = paras[i + 1]
        at = 1 if nxt.find(dt.W + "pPr") is not None else 0
        for child in [c for c in p if c.tag != dt.W + "pPr"]:
            nxt.insert(at, child)
            at += 1
        p.getparent().remove(p)


def _clean_part(root):
    """קבלת כל השינויים בחלק אחד: מחיקות יוצאות, הוספות נשארות בלי העטיפה."""
    if root.find(dt.W + "body") is not None:
        _merge_deleted_marks(root)
    for el in list(root.iter()):
        if not isinstance(el.tag, str):
            continue
        name = dt.local(el.tag)
        parent = el.getparent()
        if parent is None:
            continue
        if name in ("del", "moveFrom") and dt.local(parent.tag) != "rPr":
            parent.remove(el)
        elif name.endswith("PrChange") or name in ("commentRangeStart", "commentRangeEnd",
                                                     "moveFromRangeStart", "moveFromRangeEnd",
                                                     "moveToRangeStart", "moveToRangeEnd"):
            parent.remove(el)
        elif name in ("del", "ins", "moveTo") and dt.local(parent.tag) == "rPr":
            parent.remove(el)  # סימון שינוי על סימן הפסקה
    for el in list(root.iter(dt.W + "ins", dt.W + "moveTo")):
        parent = el.getparent()
        if parent is None:
            continue
        i = parent.index(el)
        for child in list(el):
            parent.insert(i, child)
            i += 1
        parent.remove(el)
    for ref in list(root.iter(dt.W + "commentReference")):
        run = ref.getparent()
        if run is not None and run.getparent() is not None:
            run.getparent().remove(run)
    return root


def cmd_clean_copy(a):
    st = state_of(a.deal)
    if st is None:
        print("אין קובץ מצב בתיקיית העסקה, ולכן אין רשימה לפני חתימה שעברה")
        return 2
    if not (st.get("signing_checklist") or {}).get("passed"):
        print("הרשימה לפני חתימה לא עברה (round_tools.py signing). העותק לחתימה אינו מופק.")
        return 3
    if not os.path.exists(a.agreed):
        print("הנוסח המוסכם אינו קיים: %s" % a.agreed)
        return 2
    try:
        out = guard_out(a.out, inputs=[a.agreed])
    except OutputRefused as exc:
        print("סירוב: %s" % exc)
        return 1
    # השכבה הפנימית (הכותרת והבועות של "פנימי") יוצאת קודם, גם אם נמסר קובץ העבודה
    parts = dt.read_package(dt.strip_internal(a.agreed))
    drop = {n for n in parts if COMMENT_PARTS.match(n)}
    for name in list(parts):
        if name in drop:
            del parts[name]
        elif CLEAN_PARTS.match(name):
            root = etree.fromstring(parts[name])
            parts[name] = etree.tostring(_clean_part(root), xml_declaration=True,
                                         encoding="UTF-8", standalone=True)
        elif name == "word/settings.xml":
            root = etree.fromstring(parts[name])
            for el in list(root.iter(dt.W + "trackRevisions")):
                el.getparent().remove(el)
            parts[name] = etree.tostring(root, xml_declaration=True, encoding="UTF-8",
                                         standalone=True)
        elif name == "word/_rels/document.xml.rels":
            txt = parts[name].decode("utf-8")
            txt = re.sub(r'<Relationship [^>]*Target="comments[^"]*"[^>]*/>', "", txt)
            parts[name] = txt.encode("utf-8")
        elif name == "[Content_Types].xml":
            txt = parts[name].decode("utf-8")
            txt = re.sub(r'<Override [^>]*PartName="/word/comments[^"]*"[^>]*/>', "", txt)
            parts[name] = txt.encode("utf-8")
    with open(out, "wb") as fh:
        fh.write(dt.write_package(parts))

    # הבדיקה: הטקסט של העותק הנקי זהה ל"קבל הכול" של הנוסח המוסכם, ואין בו סימון
    left = dt.read_package(out)
    marks = any(re.search(r"<w:(ins|del|moveFrom|moveTo)\b", left[n].decode("utf-8", "ignore"))
                for n in left if CLEAN_PARTS.match(n))
    if dt.accept_all(a.agreed) != dt.received_paragraphs(out) or marks:
        os.remove(out)
        print("העותק הנקי אינו זהה לנוסח המוסכם%s, ולא נשמר." % (" (נשאר בו סימון)" if marks else ""))
        return 3
    with open(a.agreed, "rb") as fh:
        sha = hashlib.sha256(fh.read()).hexdigest()
    print("העותק לחתימה: %s" % out)
    sc = st.setdefault("signing_checklist", {})
    sc["agreed_version_sha256"] = sha
    sc["clean_copy_path"] = out
    if not save_state(a.deal, st):
        return 3
    return 0


def cmd_round_rules(a):
    st = state_of(a.deal)
    rnd = a.round or int(((st or {}).get("meta") or {}).get("round_number") or 1)
    lang = a.lang or "he"
    row = QB.round_row(rnd, lang)
    en = lang == "en"
    print(("Round %d (%s)" if en else "סבב %d (%s)") % (rnd, row["stage"]))
    for k, he_label, en_label in (("goal", "מטרה", "Goal"), ("retreat", "נסיגה מותרת", "Allowed retreat"),
                                  ("tone", "טון", "Tone"), ("on_acceptance", "מה עונים על קבלה", "On acceptance")):
        print("  %s: %s" % (en_label if en else he_label, row[k]))
    print(("  Comment length: up to %d sentences, %d words" if en else "  אורך בועה: עד %d משפטים, %d מילים")
          % (row["max_sentences"], row["max_words"]))
    if not a.decisions:
        return 0
    # השרשורים מהשוואת הסבב: הבועה מול הנימוק שלנו מהסבב הקודם, ותשובה שלהם שיחזרו עם הצעה (S1d-R2)
    cmp_path = a.compare or (os.path.join(a.deal, "round-compare-%d.json" % rnd) if a.deal else None)
    threads = (load(cmp_path, "השוואת הסבב", required=False) or {}).get("threads") \
        if cmp_path and os.path.exists(cmp_path) else None
    bad = QB.round_violations(load(a.decisions, "קובץ ההכרעות"), rnd, state=st, lang=lang, threads=threads)
    for v in bad:
        print("  [%s] %s: %s" % (v["code"], v["id"], v["message"]))
    if not bad:
        print("  קובץ ההכרעות עומד במטריצת הסבב." if not en else "  The decisions file meets the round matrix.")
    return 3 if bad else 0


# --------------------------------------------------------------------------------------------- carry (S1d-R2)
# "רכיב שלא השתנה שומר על ההכרעה שלו", אבל קובץ ההכרעות של הסבב צריך הכרעה מפורשת לכל פסקה בטיוטה שחזרה (מפתח
# הכיסוי), ומספרי הפסקאות זזו. carry מעביר כל הכרעה מהסבב הקודם לפסקה שלא השתנתה, לפי יישור טקסט, עם כל השדות
# (decision_required, user_decision, policy_gate, tier וכו'), כקבלה (accept, A1) ובלי בועה. פסקה שהשתנתה, שיש בה
# הצעה שלנו שעוד פתוחה, או שיש עליה בקשה חדשה שלהם, נשארת להכרעה של הסבב.
# שדות שאינם עוברים: מה שמסמן או מוסיף בועה בקובץ (old, new, text, external_comment, internal_comment, תשובה
# בשרשור), ומה ששייך לפסקה שבה הוחלה ההכרעה (dependents, same_topic, silent_change)
CARRY_DROP = ("old", "new", "new_text", "text", "external_comment", "internal_comment", "reply_to_comment",
              "their_changes", "after_para", "template_para", "number", "mandatory", "kind", "cluster_id",
              "silent_change", "dependents", "dependents_found", "same_topic", "structural", "conforming",
              "conforms_to", "their_rejected", "status", "escalation_basis", "coverage")
# סיווגים בהשוואה שמשאירים את הפסקה להכרעה של הסבב (כל מה שאינו קבלה מלאה של הצעה שלנו)
OPEN_KINDS = ("their_silent", "their_tracked", "their_rejected_our_insert", "our_rejected", "our_accepted_partial",
              "our_open")


def _n(s):
    return re.sub(r"\s+", " ", re.sub(r"[‎‏‪-‮]", "", s or "")).strip()


def align_paragraphs(base, recv, compare=None):
    """{פסקה בטיוטה שחזרה: פסקה בטיוטה של הסבב הקודם}. קודם מה שהשוואת הסבב הצמידה (פריטים, ו-para_map לפסקאות עם
    טקסט), אחר כך יישור רצפים (difflib) על הטקסט, ובתוך בלוק שהוחלף, ההתאמה הקרובה ביותר. פסקה ריקה עוקבת אחרי הפסקה
    שלפניה, ולא אחרי קרבת נוסח. פסקה שהוספנו בסבב הקודם (base_para ריק) נרשמת ב-inserted: {פסקה: after_base_para}."""
    import difflib
    b = [_n(x) for x in base]
    r = [_n(x) for x in recv]
    out, inserted = {}, {}
    for c in (compare or {}).get("clauses") or ():
        j = c.get("received_para")
        if not isinstance(j, int):
            continue
        if isinstance(c.get("base_para"), int):
            out.setdefault(j, c["base_para"])
        elif isinstance(c.get("after_base_para"), int):
            inserted.setdefault(j, c["after_base_para"])
    for pm in (compare or {}).get("para_map") or ():
        j, i = pm.get("received_para"), pm.get("base_para")
        if isinstance(j, int) and isinstance(i, int) and j < len(r) and i < len(b) and r[j] and j not in inserted:
            out.setdefault(j, i)
    sm = difflib.SequenceMatcher(a=b, b=r, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                if j1 + k not in inserted:
                    out.setdefault(j1 + k, i1 + k)
        elif tag == "replace":
            used = set(out.values())
            for jj in range(j1, j2):
                if jj in out or jj in inserted or not r[jj]:
                    continue
                cand = [ii for ii in range(i1, i2) if ii not in used and b[ii]]
                if not cand:
                    continue
                best = max(cand, key=lambda ii: difflib.SequenceMatcher(a=b[ii], b=r[jj]).ratio())
                if difflib.SequenceMatcher(a=b[best], b=r[jj]).ratio() > 0.6:
                    out[jj] = best
                    used.add(best)
    for j in range(len(r)):
        if not r[j] and j not in inserted:
            k = j - 1
            while k >= 0 and k not in out:
                k -= 1
            nxt = (out[k] + (j - k)) if k >= 0 else j
            if 0 <= nxt < len(b) and not b[nxt] and nxt not in out.values():
                out[j] = nxt
    return out, inserted


def carry_decisions(prev_decs, base, recv, compare=None, existing=(), prev_round=1):
    """שלד ההכרעות של הסבב: (הכרעות שהועברו, פסקאות שנשארו להכרעה). existing: ההכרעות שכבר נכתבו לסבב הזה (הפסקאות
    שלהן אינן מועברות). פסקה פתוחה (OPEN_KINDS, או בקשה חדשה שלהם בשרשור) אינה מועברת."""
    from orchestrator.state_builder import their_requests
    m, inserted = align_paragraphs(base, recv, compare)
    by_para = {}
    for d in prev_decs:
        if isinstance(d.get("para"), int):
            by_para.setdefault(d["para"], []).append(d)
    ins_by_after = {}
    for d in prev_decs:
        if d.get("op") == "insert_paragraph" and isinstance(d.get("after_para"), int):
            ins_by_after.setdefault(d["after_para"], []).append(d)
    decided = {d.get("para") for d in existing if isinstance(d.get("para"), int)}
    used = {d.get("id") for d in existing}
    open_paras = {c.get("received_para") for c in (compare or {}).get("clauses") or ()
                  if c.get("classification") in OPEN_KINDS}
    open_paras |= set(their_requests((compare or {}).get("threads")))
    added, left = [], []
    for j in range(len(recv)):
        if j in decided:
            continue
        if j in open_paras:
            left.append((j, "השתנתה בסבב, או שיש עליה בקשה חדשה של הצד השני"))
            continue
        src = None
        if j in inserted:
            cands = ins_by_after.get(inserted[j]) or []
            src = max(cands, key=lambda d: _ratio(d.get("text"), recv[j]), default=None)
        elif j in m:
            ds = by_para.get(m[j]) or []
            src = next((d for d in ds if d.get("op") != "accept"), None) or (ds[0] if ds else None)
        if src is None or src.get("id") in used:
            if not _n(recv[j]):
                src = {"id": "K%d-%d" % (prev_round + 1, j), "op": "accept", "decision_code": "A1",
                       "reason": "פסקה ריקה", "rule_ids": []}
            else:
                left.append((j, "אין לה הכרעה מקבילה בסבב הקודם" if src is None else
                             "ההכרעה %s כבר הוחלה על פסקה אחרת בסבב" % src.get("id")))
                continue
        used.add(src["id"])
        d = {k: copy.deepcopy(v) for k, v in src.items() if k not in CARRY_DROP}
        changed = src.get("op") not in (None, "accept")
        if changed:
            # ההצעה שלנו התקבלה: הפסקה נושאת עכשיו את הנוסח שלנו, וסיווג הנוסח המקורי שלהם (their_track red/yellow)
            # אינו חל עליה. העברתו הכשילה את שער המשלוח ב"ויתור על קו אדום" על סעיף שהצד השני קיבל
            d["their_track"] = "green"
        prev_sum = src.get("summary") or src.get("reason") or ""
        d.update(op="accept", para=j, decision_code="A1",
                 carried_from={"round": prev_round, "id": src["id"], "para": src.get("para", src.get("after_para")),
                               "op": src.get("op")},
                 reason=("ההצעה שלנו מסבב %d התקבלה, ולא השתנתה בסבב הזה" if changed else
                         "לא השתנה בסבב הזה; נשאר כפי שהוכרע בסבב %d") % prev_round,
                 summary=(("ללא שינוי מסבב %d: " % prev_round) + prev_sum) if prev_sum else
                 ("ללא שינוי מסבב %d" % prev_round))
        added.append(d)
    return added, left


def _ratio(a, b):
    import difflib
    return difflib.SequenceMatcher(a=_n(a), b=_n(b)).ratio()


def cmd_carry(a):
    """שלד ההכרעות של סבב המשך: כל הכרעה מהסבב הקודם, ממופה לפסקה שלא השתנתה."""
    st = state_of(a.deal)
    if not (a.compare or a.round):
        print("חסר --compare (round-compare-<N>.json), או --round")
        return 2
    compare = load(a.compare or os.path.join(a.deal, "round-compare-%d.json" % a.round), "השוואת הסבב")
    rnd = a.round or compare_round(st, compare)
    prev =a.prev_decisions or os.path.join(a.deal, "decisions_round_%d.json" % (rnd - 1))
    prev_doc = load(prev, "קובץ ההכרעות של הסבב הקודם")
    prev_decs = prev_doc.get("decisions", []) if isinstance(prev_doc, dict) else prev_doc
    received = a.received or (compare or {}).get("received")
    base = a.prev_received
    if not base:
        rec = next((d for d in ((st or {}).get("meta") or {}).get("received_documents") or ()
                    if isinstance(d, dict) and str(d.get("round")) == str(rnd - 1)), None)
        base = rec and (rec["file_name"] if os.path.isabs(rec["file_name"]) else os.path.join(a.deal, rec["file_name"]))
    base_texts = None
    if not a.prev_received and (not base or not os.path.exists(base)):
        # הטיוטה של הסבב הקודם אינה בתיקייה (S1e-R3): הקובץ שנשלח בסבב הקודם, בתצוגה שהצד השני ראה. השינויים שלנו
        # מאותו סבב דחויים, והסימונים הפתוחים שלנו מסבבים קודמים נשארים, כמו base_para בהשוואת הסבב
        sent = (compare or {}).get("sent")
        if sent and os.path.exists(sent):
            import compare_rounds as CR
            ours = (compare or {}).get("authors") or [(compare or {}).get("author")]
            base_texts = CR.base_paragraphs(dt.body_paragraphs(dt.document_root(sent)), ours,
                                            CR.prior_keys(sent, ours, a.deal, rnd - 1))[1]
            print(("The round %d draft is not in the folder (%s): aligning against the file sent in round %d, %s, as "
                   "the other side saw it" if a.lang == "en" else "הטיוטה של סבב %d אינה בתיקייה (%s): היישור מול "
                   "הקובץ שנשלח בסבב %d, %s, כפי שהצד השני ראה אותו")
                  % (rnd - 1, base, rnd - 1, os.path.basename(sent)))
            base = sent
    for p, what in ((received, "הטיוטה שחזרה (--received)"), (base, "הטיוטה של הסבב הקודם (--prev-received)")):
        if not p or not os.path.exists(p):
            print("חסר %s: %s" % (what, p))
            return 2
    target = a.decisions or os.path.join(a.deal, "decisions_round_%d.json" % rnd)
    cur = load(target, "קובץ ההכרעות של הסבב") if os.path.exists(target) else None
    existing = (cur.get("decisions", []) if isinstance(cur, dict) else cur) or []
    added, left = carry_decisions(prev_decs, base_texts if base_texts is not None else dt.received_paragraphs(base),
                                  dt.received_paragraphs(received), compare, existing, prev_round=rnd - 1)
    out_doc = dict(cur) if isinstance(cur, dict) else {k: prev_doc.get(k) for k in ("transaction_id", "lang", "author",
                                                                                     "initials") if isinstance(prev_doc, dict)}
    out_doc["round"] = rnd
    out_doc.setdefault("received_sha256", _sha(received))
    out_doc["decisions"] = sorted(list(existing) + added, key=lambda d: (d.get("para") if isinstance(
        d.get("para"), int) else d.get("after_para", 10 ** 6) + 0.5))
    errs = dt.validate_decisions(dict(out_doc, decisions=added)) if added else []
    if errs:
        print("ההכרעות שהועברו אינן עומדות בחוזה (%d):" % len(errs))
        for e in errs[:10]:
            print("  - %s" % e)
        return 2
    print(("Carried from round %d: %d decisions. Left to decide in this round: %d paragraphs" if a.lang == "en" else
           "הועברו מסבב %d: %d הכרעות. נשארו להכרעה בסבב הזה: %d פסקאות") % (rnd - 1, len(added), len(left)))
    for j, why in left:
        print("  פסקה %d: %s" % (j, why))
    if a.dry_run:
        return 3 if left else 0
    try:
        out = guard_out(a.out or target, inputs=[received, base, prev, a.compare or ""])
    except OutputRefused as exc:
        print("סירוב: %s" % exc)
        return 1
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(out_doc, fh, ensure_ascii=False, indent=1)
    print("נכתב %s" % out)
    return 3 if left else 0


PAPER_TYPES = ("negotiable", "tender_pre_bid", "tender_awarded", "standard_form_online")
PAPER_Q = {"he": {"text": "לפי הנוסח, זה נראה כמו %s. נכון? (%s)",
                  "names": {"negotiable": "הסכם רגיל למשא ומתן", "tender_pre_bid": "הליך תחרותי לפני הגשת הצעות",
                            "tender_awarded": "חוזה של הליך תחרותי שכבר זכיתם בו", "standard_form_online": "תנאים מקוונים אחידים"},
                  "opts": ["כן, %s", "לא, הסכם רגיל למשא ומתן"], "opts_other": "לא, זה הליך תחרותי או תנאים מקוונים",
                  "unsure": "הזיהוי אינו ודאי, ולכן אין המלצה: אתם קובעים.",
                  "owner_q": "לפי הקובץ, זה נראה כמו %s. של מי הנייר?",
                  "owners": {"ours": "הנוסח שלנו, שחזר עם הערות", "theirs": "נוסח שהצד השני ניסח",
                             "template": "תבנית של גורם שלישי"},
                  "award": "האם מסמכי ההליך התחרותי מתירים הערות או סטיות אחרי הזכייה, ובאיזה היקף?",
                  "rec": "אין שינויים מהותיים, רק הבהרות ותיקון טעויות",
                  "dev_yes": "מותרות גם סטיות, ואפרט איזה",
                  "only_errors": "זה חוזה של הליך תחרותי שזכיתם בו, ולכן רק תיקון טעויות. אחרי הזכייה אסור לשנות את התנאים "
                                 "שעליהם התחרו כל המציעים: המחיר, השטח, התקופה והאופציות נשארים כמו בהליך תחרותי, ושינוי בהם "
                                 "עלול לבטל את הזכייה. מה שכן מתקנים: טעות ברורה בשם, במספר, בתאריך או בהפניה. "
                                 "את הסיכונים שנשארים מנהלים, ולא מתקנים בנוסח."},
           "en": {"text": "From the wording, this looks like %s. Correct? (%s)",
                  "names": {"negotiable": "an ordinary negotiable agreement", "tender_pre_bid": "a competitive procedure before bids are "
                            "submitted", "tender_awarded": "the contract of a competitive procedure you have won",
                            "standard_form_online": "standard online terms"},
                  "opts": ["Yes, %s", "No, an ordinary negotiable agreement"],
                  "opts_other": "No, it is a competitive procedure or online terms",
                  "unsure": "The identification is not certain, so there is no recommendation: you decide.",
                  "owner_q": "From the file, this looks like %s. Whose paper is it?",
                  "owners": {"ours": "Our wording, returned with comments", "theirs": "Wording drafted by the other side",
                             "template": "A third party's template"},
                  "award": "Do the procedure documents allow comments or deviations after award, and to what extent?",
                  "rec": "No material changes, only clarifications and corrections of errors",
                  "dev_yes": "Deviations are also allowed, and I will say which",
                  "only_errors": "This is the contract of a competitive procedure you won, so we only correct errors. After the "
                                 "award, the terms all bidders competed on cannot change: the price, area, term and "
                                 "options stay as in the procedure, and changing them could cancel the award. What we do "
                                 "correct: a clear error in a name, number, date or cross-reference. The risks that "
                                 "remain are managed, not changed in the wording."}}


def cmd_paper_type(a):
    """סוג הנייר: הצעה מהטקסט (resolve_playbook.detect_paper_type), בדיקת העובדות שהמשתמש מסר מול הנוסח
    (facts_mismatch), פריט שאלה למנה (kind: paper_type, דורש תשובה מפורשת), ועם --set רישום ב-meta.paper_type של
    קובץ המצב, שממנו קוראים גם מעריך הסיכונים והאסטרטג."""
    from orchestrator import resolve_playbook as RPL
    st = state_of(a.deal) if a.deal else None
    L = "en" if a.lang == "en" else "he"
    if a.set:
        if a.set not in PAPER_TYPES:
            print("סוג נייר לא מוכר: %s (%s)" % (a.set, ", ".join(PAPER_TYPES)))
            return 2
        if st is None:
            if not a.deal or not os.path.isdir(a.deal):
                print("חסרה תיקיית העסקה (--deal)")
                return 2
            st = SB.skeleton()
            st["meta"].update(transaction_id=os.path.basename(os.path.abspath(a.deal)), round_number=1,
                              round_stage=SB.stage_for_round(1), generated_at=SB.now_iso(), last_updated=SB.now_iso())
        meta = st.setdefault("meta", {})
        meta["paper_type"] = a.set
        meta["paper_type_basis"] = {"answer_kind": a.answer_kind or "explicit", "recorded_at": SB.now_iso(),
                                    "suggested": a.suggested or None}
        print("סוג הנייר נרשם: %s" % a.set)
        return 0 if save_state(a.deal, st) else 3
    if not a.draft or not os.path.exists(a.draft):
        print("חסרה הטיוטה (--draft)")
        return 2
    paras = dt.received_paragraphs(a.draft)
    res = RPL.detect_paper_type(paras)
    facts = list(((st or {}).get("meta") or {}).get("deal_context", {}).get("facts") or [])
    if a.facts:
        extra = load(a.facts, "העובדות")
        facts += extra if isinstance(extra, list) else (extra.get("facts") or [])
    res["facts_mismatch"] = RPL.facts_mismatch(facts, paras)
    t = PAPER_Q[L]
    name = t["names"][res["suggested"]]
    sig = ", ".join(x for k in ("award", "tender", "online") for x in res["signals"][k][:2])
    text = t["text"] % (name, sig)
    if not sig:
        text = text.replace(" ()", "")
    confident = bool(res.get("confident"))
    if not confident:
        # אין המלצה בלי ביטחון (סקירת ארכיטקטורה 30.10.2026, כשל 1; user-B #9): המשפט המסביר פותח את השאלה, והמשתמש
        # בוחר. המשפט הזה חוזר גם בהודעת המסירה (n6-gate-and-send.md, סעיף 8)
        text = t["unsure"] + " " + text
    item = {"key": "paper_type", "kind": "paper_type", "situation": 4, "blocks_sending": True,
            "text": text, "confident": confident,
            "recommendation": (t["opts"][0] % name) if confident and res.get("recommended") == res["suggested"] else None,
            "options": [t["opts"][0] % name, t["opts"][1]]}
    if res["suggested"] == "negotiable":
        item.update(options=[t["opts"][0] % name, t["opts_other"]],
                    recommendation=(t["opts"][0] % name) if confident else None)
    # הסכם רגיל למשא ומתן, בלי שום סימן להליך תחרותי או לתנאים מקוונים: אין מה לשאול
    items = [] if res["suggested"] == "negotiable" and confident else [item]
    # "נייר של מי" בקוד (n1b-learning.md, שער הפוזיציה 5): שלנו שחזר, שלהם, או תבנית; מסימנים בקובץ עצמו
    try:
        import content_checks as CC
        from lawyer import lawyer_view as _lv
        prof = _lv(load(a.profile, "הפרופיל")) if getattr(a, "profile", None) else {}
        ours = [prof.get("organization_name"), prof.get("organization_name_en")]
        lawyers = [prof.get("lawyer_name"), prof.get("lawyer_name_en")] + list(prof.get("lawyer_aliases") or [])
        meta = (st or {}).get("meta") or {}
        theirs = [meta.get("counterparty"), (meta.get("deal_context") or {}).get("counterparty")]
        shas = [d.get("sha256") for d in meta.get("sent_documents") or () if isinstance(d, dict)]
        res["paper_owner"] = CC.paper_owner(a.draft, [x for x in ours if x], [x for x in theirs if x],
                                            [x for x in lawyers if x], [s for s in shas if s])
    except Exception as exc:  # noqa: BLE001  סיווג הנייר אינו מפיל את שאלת סוג הנייר
        res["paper_owner"] = {"owner": None, "confident": False, "signals": [], "error": str(exc)}
    po = res["paper_owner"]
    if po.get("owner") and not po.get("confident"):
        items.append({"key": "paper_owner", "kind": "paper_owner", "situation": 4, "blocks_sending": False,
                      "text": t["owner_q"] % t["owners"][po["owner"]], "recommendation": None,
                      "options": [t["owners"]["ours"], t["owners"]["theirs"], t["owners"]["template"]]})
    if res["suggested"] == "tender_awarded":
        items.append({"key": "tender_deviation", "kind": "paper_type", "situation": 4, "blocks_sending": True,
                      "text": t["award"], "recommendation": t["rec"], "options": [t["rec"], t["dev_yes"]]})
    for mm in res["facts_mismatch"]:
        items.append({"key": "fact_mismatch:%s:%s" % (mm["unit"], mm["fact_value"]), "kind": "fact_mismatch",
                      "situation": 4, "blocks_sending": True,
                      "text": ("מה שמסרתם (%s) שונה מהנוסח (%s). איזה נכון לעסקה הזו?" if L == "he" else
                               "What you told us (%s) differs from the wording (%s). Which is right for this deal?")
                      % (mm["fact"], ", ".join("%g" % v for v in mm["draft_values"])),
                      "options": ["הנוסח" if L == "he" else "The wording", "מה שמסרתי" if L == "he" else "What I said"]})
    res["question_items"] = items
    print(json.dumps(res, ensure_ascii=False, indent=1))
    if a.items_out:
        try:
            out = guard_out(a.items_out, inputs=[a.draft])
        except OutputRefused as exc:
            print("סירוב: %s" % exc)
            return 1
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(items, fh, ensure_ascii=False, indent=1)
    return 0


def cmd_accept_rest(a):
    """סבב ראשון (או כל סבב): כל פסקה בטיוטה שהתקבלה שאין לה הכרעה בקובץ ההכרעות מקבלת הכרעת accept אחת, בצעד
    אחד, כדי שמפתח הכיסוי יהיה מלא בלי מאות הכרעות ידניות. פסקה ריקה נרשמת כפסקה ריקה. הכרעה קיימת אינה משתנה."""
    if not os.path.exists(a.received):
        print("הטיוטה אינה קיימת: %s" % a.received)
        return 2
    doc = load(a.decisions, "קובץ ההכרעות") if os.path.exists(a.decisions) else {}
    doc = doc if isinstance(doc, dict) else {"decisions": doc}
    existing = doc.get("decisions") or []
    taken = {d.get("para") for d in existing if isinstance(d.get("para"), int)}
    ids = {d.get("id") for d in existing}
    paras = dt.received_paragraphs(a.received)
    added = []
    for i, t in enumerate(paras):
        if i in taken:
            continue
        did = "K%d" % i
        while did in ids:
            did += "k"
        empty = not (t or "").strip()
        added.append({"id": did, "op": "accept", "para": i, "decision_code": "A1", "structural": empty,
                      "reason": ("פסקה ריקה" if empty else "לא שונתה: הנוסח שלהם מקובל כמו שהוא") if a.lang != "en"
                      else ("Empty paragraph" if empty else "Unchanged: their wording is accepted as is")})
    doc.setdefault("round", a.round or doc.get("round") or 1)
    doc.setdefault("received_sha256", _sha(a.received))
    doc["decisions"] = sorted(list(existing) + added, key=lambda d: (d.get("para") if isinstance(
        d.get("para"), int) else d.get("after_para", 10 ** 6) + 0.5))
    errs = dt.validate_decisions(dict(doc, decisions=added)) if added else []
    if errs:
        print("ההכרעות שנוספו אינן עומדות בחוזה (%d):" % len(errs))
        for e in errs[:10]:
            print("  - %s" % e)
        return 2
    print(("Accepted as is: %d paragraphs with no decision (%d of them empty). Existing decisions: %d"
           if a.lang == "en" else "התקבלו כמו שהן: %d פסקאות בלי הכרעה (מהן %d ריקות). הכרעות קיימות: %d")
          % (len(added), sum(1 for d in added if d["structural"]), len(existing)))
    if a.dry_run:
        return 0
    try:
        out = guard_out(a.out or a.decisions, inputs=[a.received])
    except OutputRefused as exc:
        print("סירוב: %s" % exc)
        return 1
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
    print("נכתב %s" % out)
    return 0


def cmd_resolve_threads(a):
    """שרשור שלנו נסגר כשכל הסיווגים בפסקה שלו הם our_accepted, או כשאין בפסקה שינוי ואין בשרשור תשובה חדשה שלהם
    שאינה סגירה. בועה של הצד שכנגד (שורש שלהם) אינה מסומנת בידינו."""
    compare = load(a.compare, "השוואת הסבב")
    by_para = {}
    for c in compare.get("clauses") or ():
        if c.get("received_para") is not None:
            by_para.setdefault(c["received_para"], set()).add(c["classification"])
    closing = re.compile(r"^\s*(?:agreed|accepted|noted|thank you|thanks|מוסכם|מקובל|תודה)[.!]?\s*$", re.I)
    roots = []
    for t in compare.get("threads") or ():
        if not t.get("root_ours") or t.get("done"):
            continue
        kinds = by_para.get(t.get("para"), set())
        new_theirs = [e for e in t.get("entries") or () if e.get("new") and not e.get("ours")]
        if kinds and kinds <= {"our_accepted"}:
            roots.append(t["root_id"])
        elif not kinds and all(closing.match(e.get("text") or "") for e in new_theirs) and not (
                t.get("last_is_theirs") and not closing.match((t.get("entries") or [{}])[-1].get("text") or "")):
            # בלי שינוי בפסקה: נסגר רק כשהמילה האחרונה שלנו, או סגירה שלהם; בקשה פתוחה שלהם נשארת פתוחה
            roots.append(t["root_id"])
    stale = stale_proposals(compare, decisions_of(a.decisions) if a.decisions else [], roots)
    for root, did in stale["missing"]:
        print(("  Comment %s: decision %s changes our position in this thread, and its reply does not say \"%s\"" if
               a.lang == "en" else "  בועה %s: ההכרעה %s משנה את העמדה שלנו בשרשור, והתשובה אינה אומרת \"%s\"")
              % (root, did, QB.REPLACES["en"]))
    print(("%d threads to mark done: %s" if a.lang == "en" else "שרשורים לסימון \"בוצע\": %d: %s")
          % (len(roots), ", ".join(roots) or "-"))
    code = 3 if stale["missing"] else 0
    if a.dry_run or not roots:
        return code
    try:
        out = guard_out(a.out, inputs=[compare.get("received") or "", compare.get("sent") or ""],
                        allow_existing_doc=os.path.abspath(a.out) == os.path.abspath(a.docx))
    except OutputRefused as exc:
        print("סירוב: %s" % exc)
        return 1
    marked = TH.mark_done(a.docx, roots, out_path=out)
    print("סומנו %d בועות ב-%s" % (len(marked), out))
    # קובץ העבודה השתנה: רשומת ההפקה של הריצה מתעדכנת, כדי שהפקה חוזרת באותה ריצה תחליף אותו ולא תיצור " (2)"
    # (S1d-R2, 28.10.2026)
    from orchestrator import pre_send
    kinds = pre_send.refresh_run_record(out)
    if kinds:
        print("רשומת ההפקה של הריצה עודכנה (%s)" % ", ".join(kinds))
    return code


def stale_proposals(compare, decisions, roots):
    """בועה ישנה בשרשור פתוח (פאנל S1e-R3): הכרעה שמשנה את הנוסח בפסקה שיש בה שרשור פתוח שלנו, עם הצעה קודמת שלנו.
    הכרעה שעונה באותו שרשור: התשובה אומרת "This replaces our earlier proposal." (אחרת missing). הכרעה עם בועה חדשה:
    הבועה הישנה מסומנת "בוצע" (נוספת ל-roots), כשאין בשרשור בקשה פתוחה שלהם. מחזיר {missing: [(root, id)]}."""
    out = {"missing": []}
    changers = [d for d in decisions or () if isinstance(d, dict) and d.get("op") in QB.CHANGE_OPS]
    if not changers:
        return out
    for t in (compare or {}).get("threads") or ():
        if not t.get("root_ours") or t.get("done") or t.get("root_id") in roots:
            continue
        if not any(e.get("ours") and not e.get("new") for e in t.get("entries") or ()):
            continue
        ds = [d for d in changers if d.get("para") == t.get("para")]
        if not ds:
            continue
        in_thread = [d for d in ds if d.get("reply_to_comment") and QB.thread_of([t], d["reply_to_comment"])]
        if in_thread:
            out["missing"] += [(t["root_id"], d.get("id")) for d in in_thread
                               if not re.search(QB.REPLACES_RE, d.get("external_comment") or "", re.I)]
            continue
        open_request = SB.their_requests([dict(t, para=t.get("para") if isinstance(t.get("para"), int) else -1)])
        if not open_request:
            roots.append(t["root_id"])
    return out


def cmd_summary_head(a):
    """השורות הראשונות של הסיכום לעורך הדין, אחרי write של סוף הסבב (פאנל S1e-R3): בסבב סגירה כל פריט קריטי פתוח, עם
    ההמלצה; פריט ב-open_items שחוסם משלוח; פריט שנסגר בסבב, עם הסיבה; פריט שהסעיף שלו השתנה, לבדיקה; ושורת עדכון
    הפלייבוק מהעסקה, כשבסבב נרשמו עמדות שונות מהפלייבוק."""
    st = state_of(a.deal)
    if st is None:
        print("אין קובץ מצב בתיקיית העסקה")
        return 2
    lang = out_lang(a, st)
    en = lang == "en"
    rnd = a.round or int((st.get("meta") or {}).get("round_number") or 1)
    lines = []
    # יחידת ספירה אחת (content_checks.unit_counts): אותם מספרים בסיכום, בדוח השער ובפנקס; לא מחושבים במודל
    try:
        import content_checks as CC
        dfile = st.get("decisions_file") or ("decisions_round_%d.json" % rnd)
        dpath = os.path.join(a.deal, dfile)
        dec = load(dpath, "קובץ ההכרעות", required=False) if os.path.exists(dpath) else None
        items_d = dec.get("decisions", []) if isinstance(dec, dict) else (dec or [])
        pc = (st.get("meta") or {}).get("para_count")
        if not isinstance(pc, int) and st.get("coverage_index"):
            pc = len([x for x in st["coverage_index"] if isinstance(x, dict) and x.get("element_type") != "missing_topic"])
        if items_d:
            lines.append(CC.counts_line(CC.unit_counts(items_d, pc, (st.get("meta") or {}).get("playbook_map")), lang))
    except Exception:  # noqa: BLE001  שורת הספירה אינה מפילה את ראש הסיכום
        pass
    if SB.stage_for_round(rnd) == "closing":
        for c in SB.critical_open_clauses(st):
            lines.append(("Critical and still open: %s (%s). Recommendation: %s" if en else
                          "פריט קריטי פתוח: %s (%s). ההמלצה: %s")
                         % (c["ref"], c["status"], c["recommendation"] or ("decide before signature" if en else
                                                                            "להכריע לפני החתימה")))
    items = [o for o in st.get("open_items") or () if isinstance(o, dict)]
    # השורות האלה מוצגות ללקוח: בלי מזהים פנימיים (R43, A10) ובלי שמות שדות. פריט שכבר לא רלוונטי נסגר
    # ב-resolves_open_items בקובץ ההכרעות (n6-gate-and-send.md), וזה לא נאמר ללקוח
    for o in items:
        if o.get("blocks_sending") and o.get("status") not in SB.OPEN_ITEM_DONE:
            lines.append(("Needed before sending: %s" if en else "נדרש לפני שליחה: %s") % client_text(o.get("item")))
    for o in items:
        if int((o.get("closed") or {}).get("round") or 0) == rnd:
            lines.append(("Closed: %s (%s)" if en else "נסגר: %s (%s)")
                         % (client_text(o.get("item")), client_text(o["closed"].get("why"))))
        elif int((o.get("updated") or {}).get("round") or 0) == rnd:
            lines.append(("Updated: %s (%s)" if en else "עודכן: %s (%s)")
                         % (client_text(o.get("item")), client_text(o["updated"].get("why"))))
    for o in SB.open_items_to_recheck(st, rnd):
        lines.append(("Still open? %s. The clause changed in this response." if en else
                      "עדיין פתוח? %s. הסעיף השתנה בתגובה הזו.") % client_text(o.get("item")))
    if is_deal_only(st):
        # בלי פלייבוק אין "עמדות שונות מהפלייבוק" ואין עדכון פלייבוק מהעסקה: במקומם שורה אחת, פעם אחת, שמציעה לבנות
        # פלייבוק לשימוש חוזר מהביקורת הזו (positions_source.deal_only.build_offer_said נרשם אחרי שנאמרה)
        said = ((st.get("positions_source") or {}).get("deal_only") or {}).get("build_offer_said")
        if not said:
            lines.append("A reusable playbook can be built from this review. Build one?" if en else
                         "אפשר לבנות מהביקורת הזו פלייבוק לשימוש חוזר בעסקאות מהסוג הזה. לבנות?")
    else:
        line = SB.playbook_update_line(st, rnd, lang)
        if line:
            lines.append(line)
        # סעיפי AREO בשורה אחת; ההצעה לעדכן את הפלייבוק נאמרת פעם אחת בלבד, ואינה שאלה
        areo = SB.areo_clauses_line(st, rnd, lang, with_trigger=not line)
        if areo:
            lines.append(areo)
    for x in lines:
        print(x)
    if not lines:
        print("No lines for the head of the summary." if en else "אין שורות לראש הסיכום.")
    return 0


def main(argv=None):
    sys.dont_write_bytecode = True
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    q = sub.add_parser("questions", help="מנת השאלות")
    q.add_argument("--items", required=True,
                   help="JSON: [{key, text, situation (1-9 או null), recommendation, options, "
                        "blocks_sending, kind}]")
    q.add_argument("--deal", help="תיקיית העסקה: שאלות שכבר נשאלו אינן נשאלות שוב")
    q.add_argument("--asked-before", action="append")
    q.add_argument("--no-consideration", action="store_true", help="הסכם בלי תמורה: בלי שאלת שווי")
    q.add_argument("--max", type=int, default=8)
    q.add_argument("--status-line", help="שורת המעמד שבראש המנה")
    q.add_argument("--lang", choices=("he", "en"), help="שפת הממשק (display_language); ברירת מחדל: עברית")
    q.add_argument("--resolution", help="הפלט של resolve_playbook.py; בלעדיו playbook_resolution שבקובץ המצב")
    q.add_argument("--compare", help="הפלט של compare_rounds.py: שינויים שקטים, סעיף מוסכם שנפתח, מונח בלי הגדרה, "
                                     "STUCK (לפי stuck_reason)")
    q.add_argument("--kind-segment", help="הסגמנט בפלייבוק לסוג הצד שכנגד: מחילים את הווריאנט שלו, ואין שאלת החלה")
    q.add_argument("--profile", help="פרופיל-לקוח.json: organization_name_en, לשאלה אם להחליף את תחילת שם הקובץ")
    q.add_argument("--agreement-lang", choices=("he", "en"),
                   help="שפת ההסכם. en עם --profile: כשבפרופיל אין שם באנגלית לעורך הדין (lawyer_name_en) או לחברה "
                        "(organization_name_en), השאלה נכנסת למנה מראש, ולא באמצע ההפקה")
    q.add_argument("--ask-stance", action="store_true",
                   help="לשאול שוב את שאלת הגישה: המשתמש ביקש לשנות, או סבב חדש שבו המצב השתנה")
    q.add_argument("--strategy", help="strategy-data.json של האסטרטג; בלעדיו: strategy-data.json בתיקיית העסקה, כשקיים")
    q.add_argument("--received", help="הטיוטה שהתקבלה (docx): נושאים רגישים (דין ופורום, חידוש אוטומטי, מס, אחריות בלי "
                                      "תקרה, מידע רגיש, דין מגזרי זר) נשאלים כבר במנה, בשאלה אחת לכולם. בלעדיו: הקובץ "
                                      "האחרון ב-received_documents שבקובץ המצב")

    pt = sub.add_parser("paper-type", help="סוג הנייר (הליך תחרותי, תנאים מקוונים, משא ומתן): הצעה מהנוסח, בדיקת העובדות "
                                           "מול הנוסח, שאלה למנה, ורישום ב-meta.paper_type עם --set")
    pt.add_argument("--draft", help="הטיוטה שהתקבלה (docx)")
    pt.add_argument("--deal", help="תיקיית העסקה: העובדות מ-meta.deal_context.facts, והרישום ב---set")
    pt.add_argument("--facts", help="JSON: עובדות שהמשתמש מסר, כשאינן עדיין בקובץ המצב")
    pt.add_argument("--items-out", help="פריטי השאלה למנה (JSON), להוספה ל---items של questions")
    pt.add_argument("--set", help="לרשום את סוג הנייר אחרי תשובת המשתמש: " + " / ".join(PAPER_TYPES))
    pt.add_argument("--answer-kind", choices=("explicit", "delegated"))
    pt.add_argument("--suggested", help="ההצעה של הכלי, לרישום לצד התשובה")
    pt.add_argument("--profile", help="פרופיל-לקוח.json: השמות שלנו, לסיווג \"נייר של מי\" (paper_owner) מסימני הקובץ")
    pt.add_argument("--lang", choices=("he", "en"))

    ar = sub.add_parser("accept-rest", help="כל פסקה בלי הכרעה מקבלת accept בצעד אחד (מפתח כיסוי מלא, גם בסבב 1)")
    ar.add_argument("--decisions", required=True, help="decisions_round_<N>.json: קובץ ההכרעות שנכתב עד עכשיו")
    ar.add_argument("--received", required=True, help="הטיוטה שהתקבלה (docx)")
    ar.add_argument("--round", type=int)
    ar.add_argument("--out", help="ברירת מחדל: אותו קובץ הכרעות")
    ar.add_argument("--lang", choices=("he", "en"))
    ar.add_argument("--dry-run", action="store_true")

    r = sub.add_parser("review", help='טבלת "לאישורך"')
    r.add_argument("--decisions", required=True)
    r.add_argument("--deal")
    r.add_argument("--concessions")
    r.add_argument("--lang", choices=("he", "en"), help="שפת התוצר; בלעדיו: הפרופיל, ואחריו meta.lang בקובץ המצב")
    r.add_argument("--profile", help="פרופיל-לקוח.json: deliverable_language (both: שפת הממשק)")
    r.add_argument("--full", action="store_true", help="להציג את כל ההכרעות, גם קבלות שאינן מהותיות")

    t = sub.add_parser("talking-points", help="נקודות לשיחה")
    t.add_argument("--decisions", required=True)
    t.add_argument("--deal")
    t.add_argument("--concessions")
    t.add_argument("--lang", choices=("he", "en"), help="שפת התוצר; בלעדיו: הפרופיל, ואחריו meta.lang בקובץ המצב")
    t.add_argument("--profile", help="פרופיל-לקוח.json: deliverable_language (both: שפת הממשק)")

    s = sub.add_parser("signing", help="הרשימה לפני חתימה")
    s.add_argument("--gate", help="הדוח של qa_gate.py (חובה, חוץ מ---preview)")
    s.add_argument("--preview", nargs="?", const=True, default=False,
                   help="תצוגה מקדימה כשהצד השני מאותת שהוא מוכן לסיים: מה שחסר, בלי דוח שער ובלי רישום כ\"עברה\"; "
                        "ערך אופציונלי: הציטוט שלהם")
    s.add_argument("--deal")
    s.add_argument("--profile")
    s.add_argument("--register", help="נשאר לתאימות, ואינו בשימוש: המרשם של מעריך הסיכונים אינו חוסם חתימה")
    s.add_argument("--fail", action="append", help="בדיקה בקריאה שנכשלה: <check>=<הפרט והמקום>. check אחד מ: "
                                                   "%s" % ", ".join(SC.MANUAL_CHECKS))
    s.add_argument("--pass", dest="pass_", action="append", help="בדיקה בקריאה שנכשלה בהרצה קודמת ועברה עכשיו: <check>")
    s.add_argument("--decisions")
    s.add_argument("--lang", choices=("he", "en"), help="שפת התוצר; בלעדיו: meta.lang בקובץ המצב")

    p = sub.add_parser("proportionality", help="מידתיות")
    p.add_argument("--decisions", required=True)
    p.add_argument("--fight-list", type=int, required=True, help="מספר הפריטים ברשימת המאבק")
    p.add_argument("--value-band", default="לא ידוע", help="קטנה / בינונית / גדולה / לא ידוע")
    p.add_argument("--value-text", help="השווי במילים, לשורת הסיכום. בלעדיו: \"שווי ההתקשרות לא נמסר\"")
    p.add_argument("--user-choice", choices=P.USER_CHOICES)
    p.add_argument("--answer-kind", choices=("explicit", "delegated"))
    p.add_argument("--lang", choices=("he", "en"), help="שפת שורת הסיכום והאפשרויות")

    c = sub.add_parser("clean-copy", help="העותק הנקי לחתימה")
    c.add_argument("--agreed", required=True, help="הנוסח המוסכם, עם השינויים שעוד לא התקבלו")
    c.add_argument("--out", required=True, help="העותק לחתימה (docx)")
    c.add_argument("--deal", required=True, help="תיקיית העסקה: הרשימה לפני חתימה צריכה לעבור")

    rr = sub.add_parser("round-rules", help="מטריצת הסבבים, ובדיקת קובץ ההכרעות מולה")
    rr.add_argument("--round", type=int, help="בלעדיו: הסבב שבקובץ המצב")
    rr.add_argument("--decisions", help="קובץ ההכרעות של הסבב: בדיקה מול המטריצה (קוד יציאה 3 על הפרה)")
    rr.add_argument("--deal")
    rr.add_argument("--lang", choices=("he", "en"))
    rr.add_argument("--compare", help="הפלט של compare_rounds.py; בלעדיו: round-compare-<N>.json בתיקיית העסקה, כשקיים")

    cr = sub.add_parser("carry", help="שלד ההכרעות של סבב המשך: הכרעה מהסבב הקודם לכל פסקה שלא השתנתה")
    cr.add_argument("--deal", required=True, help="תיקיית העסקה")
    cr.add_argument("--compare", help="round-compare-<N>.json; בלעדיו: לפי --round בתיקיית העסקה")
    cr.add_argument("--round", type=int, help="הסבב; בלעדיו: לפי השוואת הסבב וקובץ המצב")
    cr.add_argument("--received", help="הטיוטה שחזרה; בלעדיו: received שבהשוואה")
    cr.add_argument("--prev-received", help="הטיוטה של הסבב הקודם; בלעדיו: received_documents בקובץ המצב")
    cr.add_argument("--prev-decisions", help="קובץ ההכרעות של הסבב הקודם; בלעדיו: decisions_round_<N-1>.json")
    cr.add_argument("--decisions", help="קובץ ההכרעות של הסבב (ההכרעות שכבר נכתבו נשמרות); בלעדיו: "
                                        "decisions_round_<N>.json בתיקיית העסקה, כשקיים")
    cr.add_argument("--out", help="בלעדיו: --decisions, או decisions_round_<N>.json")
    cr.add_argument("--dry-run", action="store_true")
    cr.add_argument("--lang", choices=("he", "en"))

    rt = sub.add_parser("resolve-threads", help="סימון \"בוצע\" לשרשורים שלנו בנושאים שנסגרו")
    rt.add_argument("--docx", required=True, help="קובץ העבודה של הסבב, אחרי apply_redlines.py ולפני השער")
    rt.add_argument("--compare", required=True, help="הפלט של compare_rounds.py לסבב הזה")
    rt.add_argument("--out", required=True, help="הקובץ שנכתב; אותו נתיב כמו --docx מעדכן את קובץ העבודה במקומו")
    rt.add_argument("--dry-run", action="store_true")
    rt.add_argument("--lang", choices=("he", "en"))
    rt.add_argument("--decisions", help="קובץ ההכרעות של הסבב: עמדה חדשה בבועה חדשה מסמנת את הבועה הקודמת שלנו "
                                        "\"בוצע\"; תשובה בשרשור צריכה לומר שהיא מחליפה את ההצעה הקודמת (קוד 3)")

    sh = sub.add_parser("summary-head", help="השורות הראשונות של הסיכום: פריט קריטי פתוח, open_items, עדכון הפלייבוק")
    sh.add_argument("--deal", required=True)
    sh.add_argument("--round", type=int, help="בלעדיו: הסבב שבקובץ המצב")
    sh.add_argument("--lang", choices=("he", "en"), help="שפת התוצר; בלעדיו: הפרופיל, ואחריו meta.lang בקובץ המצב")
    sh.add_argument("--profile", help="פרופיל-לקוח.json: deliverable_language (both: שפת הממשק)")

    bs = sub.add_parser("basis", help="בסיס ההשוואה לפני compare_rounds.py: ידוע, או שאלה אחת לבד לפני ההשוואה")
    bs.add_argument("--deal", required=True, help="תיקיית העסקה")
    bs.add_argument("--round", type=int, help="הסבב שנשלח; בלעדיו: הסבב שבקובץ המצב")
    bs.add_argument("--lang", choices=("he", "en"))

    a = ap.parse_args(argv)
    return {"questions": cmd_questions, "basis": cmd_basis, "review": cmd_review, "talking-points": cmd_talking_points,
            "signing": cmd_signing, "proportionality": cmd_proportionality,
            "clean-copy": cmd_clean_copy, "round-rules": cmd_round_rules,
            "resolve-threads": cmd_resolve_threads, "accept-rest": cmd_accept_rest, "paper-type": cmd_paper_type, "carry": cmd_carry, "summary-head": cmd_summary_head}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
