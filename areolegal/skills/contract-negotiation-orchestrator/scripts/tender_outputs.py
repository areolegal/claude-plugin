#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""התוצרים בהליך תחרותי ובתנאים מקוונים: טבלת שאלות הבהרה ותזכיר החלטה פנימי, בקובצי Word.

בהליך תחרותי לפני הגשה ובתנאים מקוונים אין סימון בגוף החוזה ואין בועות: שינוי בגוף
עלול לפסול את ההצעה, והערוץ היחיד הוא שאלות ההבהרה (`n4c-produce.md`, שלב ד;
הערות הנושא ונותן, שינוי 7). `apply_redlines.py` מסרב לרוץ על נייר כזה.

* **`tender_pre_bid`**: שני קבצים. **טבלת שאלות הבהרה** (מספר, מסמך, סעיף,
  עמוד, השאלה), ממוינת לפי חשיבות ועד 20 שאלות, מ-`clarification_questions`
  שבקובץ המצב. כל שאלה מנוסחת כבקשה; אין בה "מוסכם", "לא מוסכם", מדיניות,
  פלייבוק או נימוק פנימי, כי התשובות מתפרסמות לכל המציעים, ו-`internal_reason`
  לעולם אינו נכנס לטבלה. ו**תזכיר החלטה פנימי (go/no-go)**, שאינו נשלח, ובראשו
  המועד האחרון לשאלות ההבהרה והמועד האחרון להגשה.
* **`tender_awarded`** ו-**`standard_form_online`**: התזכיר הפנימי בלבד, ובו ההחלטה אם לחתום ולא אם לגשת
  (כותרת, ערכי ההמלצה ותווית "עמדה מסחרית" לפי סוג הנייר; מועדי שאלות ההבהרה וההגשה רק בהליך תחרותי לפני הגשה).

    python "AREO_RT/skills/contract-negotiation-orchestrator/scripts/tender_outputs.py" --deal "<תיקיית העסקה>" --memo <תזכיר.json> \\
        --agreement-type "<סוג ההסכם>" --company "<שם החברה>"

`--memo` הוא JSON: `{"questions_deadline", "submission_deadline", "items": [{"topic",
"contract_ref", "what", "nature": "mandatory_law | commercial", "price_impact", "risk_impact",
"recommendation", "note"}]}`. `recommendation` בהליך תחרותי לפני הגשה: `go | go_priced | go_if_answered | no_go`; בהליך תחרותי
אחרי זכייה: `sign | sign_with_reservation | no_sign`; בתנאים מקוונים: `sign | sign_priced | request_signed | no_sign`.
ערכי go הישנים מתורגמים בשני האחרונים לערכי החתימה המקבילים.

**שפה** (דרישת מוצר: deliverable_language קובע את שפת התוצרים): `--lang he|en`, ובלעדיו `meta.lang` של קובץ
המצב. בעברית: RTL מלא. באנגלית: כל כותרת, עמודה וסימון "פנימי" באנגלית, ו-Word ב-LTR מלא.

קוד יציאה: **0** נבנה, **3** שאלה שאסור שתצא לכל המציעים (מסורבת, ולא נכתב
דבר), **2** קלט חסר או סוג נייר שאינו הליך תחרותי, **1** נתיב פלט שסורב (guard_out).

שאלה מסורבת רק כשהיא חושפת עמדה או מסמך פנימי: תווית עמדה בתחילת השאלה או כמשפט עצמאי ("מוסכם.", "לא מוסכם:",
"Agreed."), "מקובל עלינו", או אזכור של פלייבוק, מדיניות פנימית, קו אדום, נסיגה או עמדת החברה. מונח רגיל אינו
עמדה: "הפיצוי המוסכם", "סכום מוסכם", "insurance policy", "privacy policy", "the agreed service levels".
"""
import argparse
import datetime as _dt
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # גם ב-python -I, שאינו מוסיף את תיקיית הסקריפט
import areo_lib  # noqa: F401  מוסיף את areolegal/lib לנתיב הייבוא

from docx import Document  # noqa: E402
from docx.shared import Pt  # noqa: E402

from common import paths, rtl  # noqa: E402
from common.cli import OutputRefused, guard_out  # noqa: E402
from orchestrator import state_builder as SB  # noqa: E402

MAX_QUESTIONS = 20
PRIORITY = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
# שאלה שחושפת עמדה או מסמך פנימי. "מוסכם" ו-"agreed" הם תווית עמדה רק בתחילת השאלה או כמשפט עצמאי, ולא בתוך
# מונח ("הפיצוי המוסכם", "the agreed service levels"); "policy" ו"מדיניות" רק כמסמך פנימי שלנו, ולא פוליסת ביטוח
# או מדיניות פרטיות; "נסיגה" רק כעמדת נסיגה, ולא נסיגה מההצעה
_LABEL_START = r"(?:^|[.:;!?\n]\s*)(?:\d+[.)]\s*)?"
_LABEL_END = r"\s*(?:[.:;,!\-]|$)"
FORBIDDEN = re.compile(
    _LABEL_START + r"(?:(?:לא|אינו)\s+)?(?:מוסכם|מקובל)(?:\s+עלינו)?" + _LABEL_END + "|" +
    _LABEL_START + r"(?:not\s+)?(?:agreed|accepted|acceptable)" + _LABEL_END + "|"
    r"(?:לא\s+|אינו\s+)?מקובל\s+עלינו|\b(?:not\s+)?acceptable\s+to\s+us\b|\bwe\s+(?:do\s+not\s+|don't\s+)?agree\b|"
    # "סעיף 12 לא מוסכם על החברה": עמדה של החברה גם באמצע המשפט, כשהיא מיוחסת לנו
    r"(?:לא|אינו|אינה)\s+(?:מוסכם|מוסכמת|מקובל|מקובלת)\s+על\s+(?:ה)?(?:חברה|לקוח|לקוחה|מזמין|מזמינה)(?![א-ת])|"
    r"\b(?:not\s+)?(?:agreed|accepted|acceptable)\s+(?:to|by)\s+(?:the\s+)?(?:company|client|customer)\b|"
    r"פלייבוק|playbook|קו\s+(?:ה)?אדום|red\s+lines?\b|"
    r"מדיניות\s+(?:ה)?(?:חברה|פנימית|חוזית|שלנו)|מדיניותנו|\b(?:our|internal|company|contracting)\s+polic(?:y|ies)\b|"
    r"(?:עמדת|מדרגת)\s+(?:ה)?נסיגה|נסיגה\s+(?:ראשונה|אחרונה|שנייה)|\bfallback\s+position\b|\b(?:our|first|last)\s+fallback\b|"
    r"עמדת\s+(?:ה)?חברה|עמדתנו|\bour\s+position\b", re.I | re.M)
RECOMMEND = {"go": "לגשת", "go_priced": "לגשת ולתמחר את הסיכון", "go_if_answered": "לגשת בכפוף לתשובה לשאלה",
             "no_go": "לא לגשת"}
NATURE = {"mandatory_law": "הוראת דין כופה", "commercial": "עמדה מסחרית של המזמין"}
# תזכיר לפי סוג הנייר: בהליך תחרותי לפני הגשה השאלה היא אם לגשת; בהליך תחרותי שזכינו בו ובתנאים מקוונים, אם לחתום
SIGN_FROM_GO = {"tender_awarded": {"go": "sign", "go_priced": "sign_with_reservation",
                                   "go_if_answered": "sign_with_reservation", "no_go": "no_sign"},
                "standard_form_online": {"go": "sign", "go_priced": "sign_priced", "go_if_answered": "request_signed",
                                         "no_go": "no_sign"}}
PAPER_TXT = {
    "he": {"tender_awarded": {"memo": "תזכיר החלטה פנימי: חתימה על הסכם ההליך התחרותי",
                              "recommend": {"sign": "לחתום", "sign_with_reservation": "לחתום עם הסתייגות",
                                            "no_sign": "לא לחתום"}},
           "standard_form_online": {"memo": "תזכיר החלטה פנימי: האם לקבל את התנאים",
                                    "recommend": {"sign": "לקבל את התנאים", "sign_priced": "לקבל ולתמחר את הסיכון",
                                                  "request_signed": "לבקש הסכם ארגוני חתום", "no_sign": "לא לקבל"},
                                    "nature": {"mandatory_law": "הוראת דין כופה",
                                               "commercial": "עמדה מסחרית של הצד שכנגד"}}},
    "en": {"tender_awarded": {"memo": "Internal decision memo: signing the procedure agreement",
                              "recommend": {"sign": "Sign", "sign_with_reservation": "Sign with a reservation",
                                            "no_sign": "Do not sign"}},
           "standard_form_online": {"memo": "Internal decision memo: whether to accept the terms",
                                    "recommend": {"sign": "Accept the terms", "sign_priced": "Accept and price the risk",
                                                  "request_signed": "Ask for a signed enterprise agreement",
                                                  "no_sign": "Do not accept"},
                                    "nature": {"mandatory_law": "Mandatory law",
                                               "commercial": "Commercial position of the counterparty"}}}}
TXT = {
    "he": {"recommend": RECOMMEND, "nature": NATURE, "q_title": "טבלת שאלות הבהרה",
           "q_head": ("מספר", "מסמך", "סעיף", "עמוד", "השאלה"), "memo": "תזכיר החלטה פנימי: האם לגשת",
           "internal": "פנימי, לא למשלוח", "q_deadline": "המועד האחרון לשאלות הבהרה: %s",
           "s_deadline": "המועד האחרון להגשה: %s",
           "m_head": ("נושא", "סעיף", "מה קובע הסעיף", "דין כופה או עמדה מסחרית", "השפעה על המחיר", "השפעה על הסיכון",
                      "המלצה"), "f_questions": "שאלות הבהרה", "f_memo": "תזכיר פנימי"},
    "en": {"recommend": {"go": "Bid", "go_priced": "Bid and price the risk", "go_if_answered": "Bid subject to the answer",
                         "no_go": "Do not bid"},
           "nature": {"mandatory_law": "Mandatory law", "commercial": "Commercial position of the buyer"},
           "q_title": "Clarification questions",
           "q_head": ("No.", "Document", "Clause", "Page", "Question"), "memo": "Internal decision memo: whether to bid",
           "internal": "Internal, not for sending", "q_deadline": "Deadline for clarification questions: %s",
           "s_deadline": "Submission deadline: %s",
           "m_head": ("Topic", "Clause", "What the clause says", "Mandatory law or commercial position", "Price impact",
                      "Risk impact", "Recommendation"), "f_questions": "Clarification questions",
           "f_memo": "Internal memo"},
}


def load(path, what):
    if not path or not os.path.exists(path):
        print("%s אינו קיים: %s" % (what, path))
        raise SystemExit(2)
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh)


def table(doc, head, rows, lang="he"):
    t = doc.add_table(rows=1, cols=len(head))
    t.style = "Table Grid"
    for i, h in enumerate(head):
        t.rows[0].cells[i].text = h
        for r in t.rows[0].cells[i].paragraphs[0].runs:
            r.bold = True
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = str(v or "")
    if lang != "en":
        rtl.set_table_rtl(t)
    return t


def out_path(deal, agreement_type, company, what, date):
    name = " - ".join(x for x in (agreement_type, company, what, date) if x) + ".docx"
    name = re.sub(r'[\\/:*?"<>|]', "", name)
    p = paths.unique_path(os.path.join(deal, name))
    paths.check_write_path(p)
    guard_out(p)   # לא בתיקיית מקור של הלקוח (--deal שמצביע בטעות לתיקייה שקיבלה את הקבצים מהצד שכנגד)
    return p


def _scrub(text, lang="he"):
    """קודים פנימיים (מזהה כלל, קוד הכרעה, מזהה מקור, "סבב 1") אינם יוצאים בטבלה או בתזכיר: הניקוי של שכבת הבנייה."""
    if text is None:
        return None
    try:
        import content_checks as CC
        return CC.scrub_client_text(text, None, lang)
    except Exception:  # noqa: BLE001
        return text


def build_questions(qs, path, company, lang="he"):
    T = TXT[lang]
    doc = Document()
    rtl.add_paragraph(doc, T["q_title"], bold=True, size=16)
    rows = []
    for n, q in enumerate(qs, 1):
        # ניקוי קודים פנימיים בשכבת הבנייה (content_checks.scrub_client_text): הטבלה מתפרסמת לכל המציעים
        rows.append((n, _scrub(q.get("document"), lang), q.get("contract_ref"), q.get("page"), _scrub(q.get("question"), lang)))
    table(doc, T["q_head"], rows, lang)
    rtl.enforce(doc, lang, author=company, keep_hebrew=True)
    doc.save(path)


def build_memo(memo, path, company, paper, lang="he"):
    T = dict(TXT[lang], **PAPER_TXT[lang].get(paper, {}))
    doc = Document()
    rtl.add_paragraph(doc, T["memo"], bold=True, size=16)
    rtl.add_paragraph(doc, T["internal"], bold=True, size=11)
    if paper == "tender_pre_bid":
        if memo.get("questions_deadline"):
            rtl.add_paragraph(doc, T["q_deadline"] % memo["questions_deadline"], bold=True)
        if memo.get("submission_deadline"):
            rtl.add_paragraph(doc, T["s_deadline"] % memo["submission_deadline"], bold=True)
    if paper == "standard_form_online" and memo.get("signed_agreement_recommendation"):
        rtl.add_paragraph(doc, memo["signed_agreement_recommendation"])
    rows = []
    for it in memo.get("items") or []:
        rec = it.get("recommendation")
        rec = SIGN_FROM_GO.get(paper, {}).get(rec, rec)
        rows.append((_scrub(it.get("topic"), lang), it.get("contract_ref"), _scrub(it.get("what"), lang),
                     T["nature"].get(it.get("nature"), ""), _scrub(it.get("price_impact"), lang),
                     _scrub(it.get("risk_impact"), lang), T["recommend"].get(rec, rec or "")))
    table(doc, T["m_head"], rows, lang)
    for p in doc.sections[0].header.paragraphs or [doc.sections[0].header.add_paragraph()]:
        p.add_run(T["internal"]).font.size = Pt(9)
    rtl.enforce(doc, lang, author=company, keep_hebrew=True)
    doc.save(path)


def main(argv=None):
    sys.dont_write_bytecode = True
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--deal", required=True)
    ap.add_argument("--memo", required=True, help="JSON התזכיר")
    ap.add_argument("--agreement-type", required=True)
    ap.add_argument("--company", default="")
    ap.add_argument("--date", help="התאריך בשם הקובץ (כלל 3.6: D.M.YYYY בעברית, \"3 April 2027\" באנגלית, או ISO); בלעדיו: היום")
    ap.add_argument("--lang", choices=("he", "en"), help="שפת התוצרים; בלעדיו: meta.lang בקובץ המצב")
    a = ap.parse_args(argv)
    state = load(os.path.join(a.deal, "negotiation_state.json"), "קובץ המצב")
    paper = state.get("paper_type") or (state.get("meta") or {}).get("paper_type")
    if paper not in ("tender_pre_bid", "tender_awarded", "standard_form_online"):
        print("סוג הנייר הוא %s, ולא הליך תחרותי או תנאים מקוונים. התגובה נבנית ב-apply_redlines.py." % paper)
        return 2
    memo = load(a.memo, "התזכיר")
    lang = rtl.lang_of(a.lang, (state.get("meta") or {}).get("lang"))
    T = TXT[lang]
    date = SB.display_date(a.date, lang) if a.date and re.fullmatch(r"\d{4}-\d{2}-\d{2}", a.date) else \
        (a.date or SB.display_date(None, lang))
    written = []
    if paper == "tender_pre_bid":
        qs = sorted(state.get("clarification_questions") or [],
                    key=lambda q: (PRIORITY.get(str(q.get("priority")).upper(), 3), q.get("number") or 0))
        bad = [q for q in qs if FORBIDDEN.search(q.get("question") or "")]
        if bad:
            for q in bad:
                print("שאלה %s נוסחה כעמדה ולא כבקשה (\"%s\"): התשובות מתפרסמות לכל המציעים."
                      % (q.get("number"), FORBIDDEN.search(q["question"]).group(0)))
            return 3
        if len(qs) > MAX_QUESTIONS:
            print("יש %d שאלות; בטבלה נכנסות %d המהותיות ביותר, לפי החשיבות." % (len(qs), MAX_QUESTIONS))
            qs = qs[:MAX_QUESTIONS]
        p = out_path(a.deal, a.agreement_type, a.company, T["f_questions"], date)
        build_questions(qs, p, a.company, lang)
        written.append(p)
    p = out_path(a.deal, a.agreement_type, a.company, T["f_memo"], date)
    build_memo(memo, p, a.company, paper, lang)
    written.append(p)
    for p in written:
        problems = rtl.audit(p, lang, run_date=_dt.date.today())
        print("נבנה: %s%s" % (p, "" if not problems else "  (בדיקת כיווניות: %s)" % "; ".join(problems[:3])))
    return 0


def _main(argv=None):
    try:
        return main(argv)
    except OutputRefused as exc:
        print("סירוב: %s" % exc)
        return 1


if __name__ == "__main__":
    sys.exit(_main())
