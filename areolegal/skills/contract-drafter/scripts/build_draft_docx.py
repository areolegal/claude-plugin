#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""בונה את מסמך הטיוטה ב-Word ישירות מ-draft.json.

**זה המסלול היחיד להפקת טיוטה ב-Word.** אין לכתוב את המסמך ב-python-docx בכל
הרצה, ואין "לשפר" את העיצוב ביד. בנייה ידנית היא מה שגרם לטיוטה לצאת בברירות
המחדל של Word, בלי היררכיה ובלי כיווניות, והיא גם מה שגרם לשלב ההפקה להימשך
עשרות דקות: המודל נאלץ לפלוט סדרתית גם את נוסח ההסכם וגם את קוד הבנייה שלו.
כאן המודל פולט **נתונים בלבד**, והסקריפט עושה את המספור, ההיררכיה, הכיווניות
וסימון החוסרים.

**שפה:** `--lang he|en`, ובלעדיו `meta.language`, ובלעדיו `deliverable_language` מהפרופיל. בעברית: RTL מלא
(bidi, rtl, bidiVisual, rtlGutter). באנגלית: LTR מלא, בלי bidi ובלי rtl, וכל טקסט קבוע (חותמת "Produced on",
"Draft", "[to complete]", "IN WITNESS WHEREOF", כותרות הנספחים ודף הליווי) באנגלית. נוסח מהנתונים נשאר כמו שהוא.

הסקריפט אוכף כיווניות בעצמו. **אין להעביר את התוצר שלו ב-rtl-docx-enforcer:**
מעבר נוסף מייצר שכתוב מלא של המסמך בלי להוסיף דבר.

    python3 build_draft_docx.py --draft Areo-נתונים/draft-<slug>.json \\
        --profile "<profile_path של הישות>" --out "<שם המסמך>.docx" [--cover "<שם המסמך> - דף ליווי.docx"]

**דף ליווי בכל מצב:** `--cover` מפיק דף ליווי גם בלי `--research`: מטריצת המקורות (פלייבוק, נוסחים, עובדות
העסקה), מה נותר [להשלים], טעון בדיקה משפטית, סעיפים מותנים ונושאים בלי עמדה מבוססת בפלייבוק.

מבנה draft.json, במלואו. שדה חסר מדולג בשקט; אין שדה חובה מלבד clauses:
    meta{doc_type,title,language,classification,transaction_id,template{},source_mode,notice,
         parties[{defined_as,name,reg,address,role}],place_date,generated_at,counterparty_public_body,
         company_role_code}
    recitals[str]  definitions[{term,text}]
    clauses[{number,heading,text,source,needs_legal_review,condition,opening_position,public_form,
             user_requested,children[...]}]
    annexes[{label,title,text|clauses[]}]
    signatures{note,blocks[{name,by,title}]}
    cover{title,source,playbook{name,status},documents[{no,title,publisher,year}],facts[],
          playbook_gaps[{topic,reason}],playbook_gaps_answer,main_concern{answer,clauses[]},
          key_dates[{what,when,clause}],options[{title,reason}],decisions[],notes[]}

**מספר מצייני החוסר** נספר בבקרת השלמות (check_draft_integrity.count_placeholders) על הקובץ שנכתב, והוא המספר
שמודפס ונכתב בדף הליווי. **סעיף מטופס ציבורי** (public_form) נכנס רק כשאחד הצדדים גוף ציבורי, ואחרת הסקריפט מסרב
ומפנה ל-cover.options. **החשש העיקרי** (cover.main_concern) חייב להפנות לפחות לסעיף קיים אחד.
"""
import argparse
import datetime
import io
import json
import os
import re
import sys

# python -I אינו מוסיף את תיקיית הסקריפט: הסקריפטים השכנים (check_draft_integrity, research_sources) נטענים ממנה
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


from areo_rt import ensure_lib  # noqa: E402
from client_text_gate import HEB_CH, client_text_problems, english_parties  # noqa: E402  AREO_RT/lib: הספרייה המשותפת מחבילת זמן הריצה

ensure_lib()
try:
    from common.voice_check import check_text as _voice_check   # noqa: E402
except Exception:  # noqa: BLE001  בלי החבילה: הבדיקה המקומית שלהלן בלבד
    _voice_check = None

try:                                   # פלט עברי במסוף של Windows
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):   # pragma: no cover
    pass

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

# ---------- פלטה: מסמך משפטי, לא דוח. מאופקת בכוונה ----------
INK = "16191F"
INK_SOFT = "5B6472"
LINE = "C9CFD6"
NAVY = "12314F"
GAP_BG = "FFF2A8"      # רקע לציון חוסר, כדי שלא ייחתם מסמך עם [להשלים]
# גופן: בתוצר עברי David בכל ריצה (ascii, hAnsi ו-cs), כמו כל מסמך Word עברי של Areo. בתוצר אנגלי Calibri
# לטקסט הלטיני, כמו LATIN_FONT בספרייה המשותפת, ו-David נשאר בגופן ה-cs, כך ששם צד או ציטוט בעברית בתוך
# מסמך אנגלי יוצא באותו גופן עברי. FONT נשאר לתאימות: הגופן הלטיני של התוצר הנוכחי, לפי RTL
FONT_HE = "David"
FONT_LATIN = "Calibri"
FONT = FONT_HE

RTL = True             # נקבע מ-meta.language בזמן הבנייה

# ---------- טקסט קבוע בשתי השפות ----------
# דרישת מוצר: שפת התוצר קובעת כל טקסט קבוע בטיוטה ובדפי הליווי. RTL=False הוא תוצר באנגלית: כל
# כותרת, תווית, עמודה, חותמת "Produced on" וציין חוסר באנגלית, והמסמך LTR מלא. נוסח שמגיע מהנתונים נשאר כמו שהוא.
TXT = {
    "he": {"draft": "טיוטה", "stamp": "טיוטה · הופק בתאריך %s", "fill": "[להשלים]", "defined": ' (להלן: "%s")',
           "part1": "מצד אחד;", "part2": "מצד שני;", "whereas": "הואיל ו", "now": "לפיכך הוסכם, הותנה והוצהר בין הצדדים כדלקמן:",
           "definitions": "הגדרות", "case_law": " [להשלמה]", "annex": "נספח",
           "defs_lead": "בהסכם זה יהיו למונחים הבאים הפירושים שלצידם:",
           "defs_lead_recitals": "בהסכם זה, לרבות במבוא לו, יהיו למונחים הבאים הפירושים שלצידם:",
           "witness": "ולראיה באו הצדדים על החתום:", "by": "על ידי: ", "not_found": "[לא אותר]",
           "mand": "סעיף שהחוק מחייב: %s", "sources": "המקורות שהטיוטה נשענת עליהם", "internal": "פנימי. לא נשלח לצד השני.",
           "law": "הדין החל", "law_head": ["דרג", "מקור", "סעיפים", "סטטוס"], "verified": "אומת",
           "unverified": "טעון אימות", "ags": "הסכמים מייצגים שאושרו", "ags_head": ["הסכם", "מפרסם", "כיוון"],
           "page": " · עמוד ", "cover": "דף ליווי: ", "cover_stamp": "טיוטה · הופק בתאריך %s",
           "trace": "מטריצת עקיבות", "trace_head": ["סעיף", "נושא", "מקור", "סעיף חובה", "עמדת פתיחה"],
           "own": "ניסוח עצמאי", "yes": "כן", "no": "לא", "removed": "סעיפי חובה שהוסרו לבקשתכם",
           "removed_line": "%s: %s. החשיפה: %s", "gaps": "פערים ומגבלות",
           "no_research": "לא בוצע מחקר רגולטורי: נבחר איסוף הסכמים בלבד. הטיוטה אינה נשענת על מיפוי של הדין החל.",
           "research_limits": "המחקר מוגבל למאגר המקורות המאושרים של Areo (רק האתרים והנתיבים שרשומים בו לכל מדינה). "
                              "הנחיות שלא פורסמו במקורות האלה, או שלא ניתן היה לשלוף אותן, אינן בו.",
           "unverified_line": "טעון אימות: ", "case_law_list": "AREO לא מצאה מקור מורשה לנקודה זו. הצעד הבא: להעלות הסכם דומה כמקור, או להשאיר את הנקודה כפי שהיא. סעיפים ",
           "run_risk": "להריץ על הטיוטה הערכת סיכונים לפני שהיא יוצאת?",
           # דף הליווי בכל מצב, גם בלי --research
           "cover_stamp_plain": "טיוטה · הופק בתאריך %s", "src_playbook": "פלייבוק",
           "src_third_party": "פלייבוק ונוסחים של צד שלישי",
           "tp_notice": "הנייר אינו של החברה. המבנה וסדר הסעיפים נלקחו מנוסחים של צד שלישי שעומד באותו צד בהסכם, "
                        "והעמדה בכל סעיף נלקחה מהפלייבוק. הנוסח נכתב מחדש ואינו מועתק מהנוסחים.",
           "matrix": "מטריצת המקורות", "matrix_head": ["סעיף", "נושא", "פלייבוק", "נוסחים", "עובדות העסקה"],
           "no_pb": "אין עמדה בפלייבוק", "sources_used": "המקורות", "pb_line": "פלייבוק: %s",
           "doc_line": "%s. %s", "facts": "עובדות העסקה", "to_fill": "מה נותר להשלים",
           "loc_meta": "פרטי המסמך והצדדים", "loc_recitals": "מבוא", "loc_def": "הגדרת \"%s\"",
           "loc_clause": "סעיף %s", "loc_sign": "בלוק החתימות", "legal_review": "נקודות בלי מקור מורשה",
           "conditional": "סעיפים מותנים",
           "conditional_line": "סעיף %s: הסעיף נכלל כי %s לא נשלל; אשרו או מחקו.",
           "pb_gaps": "נושאים שאין עליהם עדיין עמדה בפלייבוק", "pb_gap_line": "%s (%s)", "pb_gaps_answer": "התשובה לשאלת ההשלמה: %s",
           "decisions": "הכרעות", "notes": "הערות", "choices": "מה נבחר ולמה",
           "pb_pending": "טיוטת מדיניות", "from_pb": "כן",
           "choice_default": "ברירת המחדל, הנוסח השכיח בהסכמים שלכם",
           "to_fill_count": "%s: %d פרטים פתוחים", "concern": "החשש העיקרי שלכם בעסקה",
           "concern_answer": "כלשונכם: %s", "concern_clauses": "המענה בטיוטה: סעיפים %s",
           "options": "מוצע כאפשרות, לא נכלל", "option_line": "%s: %s",
           "key_dates": "המועדים שיהיו חשובים בהמשך", "key_date_clause": " (סעיף %s)",
           "ld_review": "פיצוי מוסכם (סעיף %s): AREO לא מצאה מקור מורשה לנקודה זו (אכיפות הפיצוי המוסכם לפי %s). הצעד הבא: לחבר מקור מהרשימה המאושרת, או להשאיר את הסעיף כפי שהוא.",
           "law_unset": "הדין החל, שטרם נקבע",
           "lead": "הטיוטה מוכנה.", "lead_clear": "אין בה פרטים פתוחים.",
           "lead_open": "נשארו %d פרטים להשלים, כ-%d דקות.",
           "next_fill": "הצעד הבא: להשלים את הפרטים המסומנים ברקע צהוב.",
           "next_review": "הצעד הבא: להחליט על סעיפים %s: להעלות מקור, או להשאיר אותם כפי שהם.",
           "next_send": "הצעד הבא: לשלוח לצד השני, או להריץ קודם בדיקת סיכונים.",
           "notice_title": "מאיפה באה הטיוטה", "internal_note": "פנימי. לא נשלח לצד השני."},
    "en": {"draft": "Draft", "stamp": "Draft · Produced on %s", "fill": "[to complete]", "defined": ' (the "%s")',
           "part1": "of the first part;", "part2": "of the second part;", "whereas": "WHEREAS ",
           "now": "NOW, THEREFORE, the parties agree as follows:",
           "definitions": "Definitions", "case_law": " [to be completed]", "annex": "Annex",
           "defs_lead": "In this Agreement, the following terms have the meanings set out below:",
           "defs_lead_recitals": "In this Agreement, including the recitals, the following terms have the meanings "
                                 "set out below:",
           "witness": "IN WITNESS WHEREOF, the parties have signed:", "by": "By: ", "not_found": "[not found]",
           "mand": "Clause required by law: %s", "sources": "Sources the draft relies on",
           "internal": "Internal. Not sent to the other side.",
           "law": "Applicable law", "law_head": ["Rank", "Source", "Sections", "Status"], "verified": "Verified",
           "unverified": "Needs verification", "ags": "Approved representative agreements",
           "ags_head": ["Agreement", "Publisher", "Orientation"],
           "page": " · Page ", "cover": "Cover note: ", "cover_stamp": "Draft · Produced on %s",
           "trace": "Traceability matrix", "trace_head": ["Clause", "Topic", "Source", "Mandatory", "Opening position"],
           "own": "Independent drafting", "yes": "Yes", "no": "No",
           "removed": "Mandatory clauses removed at your request",
           "removed_line": "%s: %s. Exposure: %s", "gaps": "Gaps and limits",
           "no_research": "No regulatory research was done: only collecting agreements was chosen. The draft does not "
                          "rest on a mapping of the applicable law.",
           "research_limits": "The research is limited to the approved-sources repository (only the sites "
                              "and paths listed for each country). Guidance not published in these sources, or not retrievable, "
                              "is not in it.",
           "unverified_line": "Needs verification: ", "case_law_list": "AREO did not find an approved source for this point. Next step: upload a similar agreement as a source, or keep the point as it is. Clauses ",
           "run_risk": "Run a risk assessment on the draft before it goes out?",
           "cover_stamp_plain": "Draft · Produced on %s", "src_playbook": "playbook",
           "src_third_party": "playbook and third-party forms",
           "tp_notice": "This is not the company's paper. The structure and the order of the clauses come from "
                        "third-party forms in the same position, and the position in each clause comes from the "
                        "playbook. The wording was written anew and is not copied from the forms.",
           "matrix": "Source matrix", "matrix_head": ["Clause", "Topic", "Playbook", "Forms", "Deal facts"],
           "no_pb": "No playbook position", "sources_used": "Sources", "pb_line": "Playbook: %s",
           "doc_line": "%s. %s", "facts": "Deal facts", "to_fill": "What is still open",
           "loc_meta": "Document details and parties", "loc_recitals": "Recitals", "loc_def": "Definition of \"%s\"",
           "loc_clause": "Clause %s", "loc_sign": "Signature block", "legal_review": "Points without an approved source",
           "conditional": "Conditional clauses: for your confirmation",
           "conditional_line": "Clause %s: included because %s was not ruled out; confirm or delete.",
           "pb_gaps": "Topics with no settled playbook position yet", "pb_gap_line": "%s (%s)",
           "pb_gaps_answer": "Answer to the completion question: %s",
           "decisions": "Decisions", "notes": "Notes", "choices": "What was chosen and why",
           "pb_pending": "Draft policy", "from_pb": "Yes",
           "choice_default": "the default, the most common wording in your agreements",
           "to_fill_count": "%s: %d open details", "concern": "Your main concern in this deal",
           "concern_answer": "In your words: %s", "concern_clauses": "Where the draft answers it: clauses %s",
           "options": "Offered as an option, not included", "option_line": "%s: %s",
           "key_dates": "Dates that will matter later", "key_date_clause": " (clause %s)",
           "ld_review": "Liquidated damages (clause %s): AREO did not find an approved source for this point (enforceability under %s). Next step: connect a source from the approved list, or keep the clause as it is.",
           "law_unset": "the governing law, not yet set",
           "lead": "Your draft is ready.", "lead_clear": "Nothing is left open.",
           "lead_open": "%d details are left to complete, about %d minutes.",
           "next_fill": "Next step: complete the details marked in yellow.",
           "next_review": "Next step: decide on clauses %s: upload a source, or keep them as they are.",
           "next_send": "Next step: send it to the other side, or run a risk check first.",
           "notice_title": "Where this draft came from", "internal_note": "Internal. Not sent to the other side."},
}
# ערכים בעברית שמגיעים מ-research_sources (מדרג, היקף, כיוון), לתוצר באנגלית
NORM_RANKS_EN = {1: "Primary legislation", 2: "Secondary legislation", 3: "Binding regulator instruction",
                 4: "Regulator guidance", 5: "Staff position or FAQ", 6: "Source in process"}
SCOPES_EN = {"agreements": "collecting representative agreements", "research": "layered regulatory research",
             "both": "collecting agreements and regulatory research"}
ORIENT_EN = {"לטובת הפוזיציה": "Favours our position", "מאוזן": "Balanced", "נגד הפוזיציה": "Against our position"}
# התצוגה בעברית: ערך השדה נשאר כמו שהוא, והלקוח רואה "הצד שלכם" (areo-voice.md)
ORIENT_HE = {"לטובת הפוזיציה": "לטובת הצד שלכם", "מאוזן": "מאוזן", "נגד הפוזיציה": "נגד הצד שלכם"}


def tr(key):
    """הטקסט הקבוע בשפת התוצר (לפי RTL, שנקבע מהשפה)."""
    return TXT["he" if RTL else "en"][key]


def is_en(lang):
    v = str(lang or "").strip().lower()
    return v[:2] == "en" or v in ("english", "אנגלית")


def profile_lang(prof):
    """שפת התוצר מהפרופיל: deliverable_language, וכשהוא both, display_language (language-policy.md)."""
    prof = prof or {}
    v = str(prof.get("deliverable_language") or "").strip().lower()
    if v == "both":
        v = str(prof.get("display_language") or "").strip().lower()
    return v or None

PPR_ORDER = ["pStyle", "keepNext", "keepLines", "pageBreakBefore", "numPr", "pBdr",
             "shd", "tabs", "bidi", "spacing", "ind", "contextualSpacing", "jc",
             "outlineLvl", "rPr"]

# "[להשלים: ...]" בכל אורך, כמו count_placeholders בבקרת השלמות; סוגריים אחרים עד 80 תווים
GAP_RX = re.compile(r"(\[(?:להשלים|to complete)[^\[\]]*\]|\[[^\[\]]{0,80}\])", re.I)


# ---------- כלי XML ----------
def _el(tag, **attrs):
    e = OxmlElement(tag)
    for k, v in attrs.items():
        e.set(qn("w:" + k), v)
    return e


def _local(tag):
    return tag.split("}")[-1]


# אותו כלל סדר חל על w:tblPr ועל w:sectPr, ושם הוא לא נאכף עד כה: bidiVisual
# שצורף בסוף tblPr נחת אחרי tblBorders ו-tblLook, ו-bidi בסוף sectPr נחת אחרי
# docGrid. Word פותח בכל זאת, אבל הקובץ אינו תקף מול הסכמה.
TBLPR_ORDER = ["tblStyle", "tblpPr", "tblOverlap", "bidiVisual", "tblStyleRowBandSize",
               "tblStyleColBandSize", "tblW", "jc", "tblCellSpacing", "tblInd",
               "tblBorders", "shd", "tblLayout", "tblCellMar", "tblLook", "tblCaption",
               "tblDescription", "tblPrChange"]
SECTPR_ORDER = ["footnotePr", "endnotePr", "type", "pgSz", "pgMar", "paperSrc",
                "pgBorders", "lnNumType", "pgNumType", "cols", "formProt", "vAlign",
                "noEndnote", "titlePg", "textDirection", "bidi", "rtlGutter", "docGrid",
                "printerSettings", "sectPrChange"]


def put_ordered(parent, el, order):
    """מכניס אלמנט למקומו לפי הסכמה, ומחליף אלמנט קיים מאותו סוג."""
    name = _local(el.tag)
    old = parent.find(qn("w:" + name))
    if old is not None:
        parent.remove(old)
    idx = order.index(name) if name in order else 99
    for child in parent:
        c = _local(child.tag)
        if (order.index(c) if c in order else 99) > idx:
            child.addprevious(el)
            return el
    parent.append(el)
    return el


def ppr_put(p, el):
    """סדר הילדים ב-w:pPr קבוע בסכמת OOXML. אלמנט שמצורף בסוף מתעלמים ממנו בשקט."""
    ppr = p._p.get_or_add_pPr()
    name = _local(el.tag)
    old = ppr.find(qn("w:" + name))
    if old is not None:
        ppr.remove(old)
    idx = PPR_ORDER.index(name) if name in PPR_ORDER else 99
    for child in ppr:
        c = _local(child.tag)
        if (PPR_ORDER.index(c) if c in PPR_ORDER else 99) > idx:
            child.addprevious(el)
            return el
    ppr.append(el)
    return el


def dir_p(p):
    if RTL:
        ppr_put(p, _el("w:bidi"))


def mixed_direction(doc):
    """מסמך באנגלית (LTR) שיש בו עברית: שם צד, ציטוט או הערה שנכתבו בעברית. פסקה שהעברית בה היא רוב האותיות
    מקבלת w:bidi, וכל ריצה עם אות עברית מקבלת w:rtl, כדי שהפיסוק והספרות יישארו במקומם בקריאה מימין לשמאל.
    פסקה לטינית עם מילה עברית אחת נשארת LTR, והמילה העברית היא ריצת rtl. פסקה בלי עברית לא משתנה: LTR, ובלי
    הספרה ".1.7". בגוף, בטבלאות ובכותרות העליונות והתחתונות. מחזיר את מספר הפסקאות שהפכו ל-RTL."""
    roots = [doc.element.body]
    for sec in doc.sections:
        for part in (sec.header, sec.footer):
            if not part.is_linked_to_previous:     # בלי זה python-docx מוסיף כותרת ריקה לקובץ
                roots.append(part._element)
    n = 0
    for root in roots:
        for p in root.iter(qn("w:p")):
            full = "".join(t.text or "" for t in p.iter(qn("w:t")))
            heb = len(HEB_RX.findall(full))
            if not heb:
                continue
            if heb >= len(re.findall("[A-Za-z]", full)):
                pp = p.find(qn("w:pPr"))
                if pp is None:
                    pp = p.makeelement(qn("w:pPr"), {})
                    p.insert(0, pp)
                old = pp.find(qn("w:bidi"))
                if old is not None:
                    pp.remove(old)
                idx = PPR_ORDER.index("bidi")
                for child in pp:
                    c = _local(child.tag)
                    if (PPR_ORDER.index(c) if c in PPR_ORDER else 99) > idx:
                        child.addprevious(_el("w:bidi"))
                        break
                else:
                    pp.append(_el("w:bidi"))
                for jc in pp.findall(qn("w:jc")):
                    if jc.get(qn("w:val")) in ("left", "right"):
                        pp.remove(jc)
                n += 1
            for r in p.iter(qn("w:r")):
                rt = "".join(t.text or "" for t in r.iter(qn("w:t")))
                if HEB_RX.search(rt):
                    rpr = r.find(qn("w:rPr"))
                    if rpr is None:
                        rpr = r.makeelement(qn("w:rPr"), {})
                        r.insert(0, rpr)
                    put_ordered(rpr, _el("w:rtl"), RPR_ORDER)
    return n


RPR_ORDER = ["rStyle", "rFonts", "b", "bCs", "i", "iCs", "caps", "smallCaps", "strike", "dstrike",
             "outline", "shadow", "emboss", "imprint", "noProof", "snapToGrid", "vanish", "webHidden",
             "color", "spacing", "w", "kern", "position", "sz", "szCs", "highlight", "u", "effect",
             "bdr", "shd", "fitText", "vertAlign", "rtl", "cs", "em", "lang", "eastAsianLayout"]
HEB_RX = re.compile("[֐-׿]")


def latin_font():
    return FONT_HE if RTL else FONT_LATIN


def set_fonts(rpr, text="", size=None, bold=False, italic=False):
    """גופן וגודל לריצה. ריצה עם w:rtl, וכל ריצה שיש בה עברית, נקראת ב-Word מתכונות ה-cs: בלי bCs,
    iCs ו-szCs כותרת עברית יוצאת לא מודגשת ובגודל ברירת המחדל. לכן הן נכתבות תמיד, לצד b, i ו-sz."""
    rf = _el("w:rFonts")
    rf.set(qn("w:ascii"), latin_font())
    rf.set(qn("w:hAnsi"), latin_font())
    rf.set(qn("w:cs"), FONT_HE)
    if RTL or HEB_RX.search(text or ""):
        rf.set(qn("w:hint"), "cs")
    put_ordered(rpr, rf, RPR_ORDER)
    if bold:
        put_ordered(rpr, _el("w:bCs"), RPR_ORDER)
    if italic:
        put_ordered(rpr, _el("w:iCs"), RPR_ORDER)
    if size:
        put_ordered(rpr, _el("w:szCs", val=str(int(round(size * 2)))), RPR_ORDER)


def run(p, text, size=11, bold=False, color=INK, italic=False, fill=None, underline=False):
    r = p.add_run(text)
    r.font.size = Pt(size)
    r.bold = bold
    r.italic = italic
    r.underline = underline
    r.font.color.rgb = RGBColor.from_string(color)
    rpr = r._r.get_or_add_rPr()
    set_fonts(rpr, text, size, bold, italic)
    if fill:
        put_ordered(rpr, _el("w:shd", val="clear", color="auto", fill=fill), RPR_ORDER)
    if RTL:
        put_ordered(rpr, _el("w:rtl"), RPR_ORDER)
    return r


GAPS = []


LINK = "0B5CAD"


def link(p, url, text=None, size=10, bold=False):
    """היפר-קישור לחיץ: w:hyperlink עם r:id שנרשם כקשר חיצוני של המסמך.
    כתובת שנכתבת כטקסט רגיל אינה לחיצה ב-Word, ולכן אינה נחשבת קישור."""
    from docx.opc.constants import RELATIONSHIP_TYPE as RT
    url = (url or "").strip()
    if not url:
        return None
    rid = p.part.relate_to(url, RT.HYPERLINK, is_external=True)
    h = _el("w:hyperlink")
    h.set(qn("r:id"), rid)
    r = _el("w:r")
    rpr = _el("w:rPr")
    if bold:
        rpr.append(_el("w:b"))
    rpr.append(_el("w:color", val=LINK))
    rpr.append(_el("w:sz", val=str(int(size * 2))))
    rpr.append(_el("w:u", val="single"))
    set_fonts(rpr, text or url, size, bold)
    if RTL:
        put_ordered(rpr, _el("w:rtl"), RPR_ORDER)
    r.append(rpr)
    t = _el("w:t")
    t.text = text or url
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    r.append(t)
    h.append(r)
    p._p.append(h)
    return h


def cell_link(cell, url, text=None, size=9.5):
    p = cell.paragraphs[0]
    for r in list(p._p.findall(qn("w:r"))):
        p._p.remove(r)
    dir_p(p)
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(3)
    if url:
        link(p, url, text or url, size)
    else:
        run(p, text or tr("not_found"), size, False, INK_SOFT)


def rich(p, text, size=11, bold=False, color=INK):
    """כותב טקסט ומסמן כל ציין חוסר ברקע, כדי שלא ייעלם בקריאה."""
    for part in GAP_RX.split(s(text)):
        if not part:
            continue
        if GAP_RX.fullmatch(part):
            GAPS.append(part)
            run(p, part, size, True, INK, fill=GAP_BG)
        else:
            run(p, part, size, bold, color)
    return p


def para(doc, text="", size=11, bold=False, color=INK, before=0, after=5, line=1.2,
         container=None, align=None, indent=0.0, italic=False):
    p = (container or doc).add_paragraph()
    dir_p(p)
    pf = p.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = line
    pf.alignment = align if align is not None else WD_ALIGN_PARAGRAPH.JUSTIFY
    if indent:
        pf.left_indent = Cm(indent) if not RTL else None
        pf.right_indent = Cm(indent) if RTL else None
    if text:
        run(p, text, size, bold, color, italic)
    return p


def table_borders(tbl, color=LINE, visible=True):
    tpr = tbl._tbl.tblPr
    b = _el("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        b.append(_el("w:" + edge, val="single" if visible else "none",
                     sz="4", space="0", color=color))
    put_ordered(tpr, b, TBLPR_ORDER)
    if RTL:
        put_ordered(tpr, _el("w:bidiVisual"), TBLPR_ORDER)


def cell_text(cell, text, bold=False, size=10.5, color=INK, align=None):
    p = cell.paragraphs[0]
    for r in list(p._p.findall(qn("w:r"))):
        p._p.remove(r)           # cell.text = "" leaves a run with no rPr, hence no w:rtl
    dir_p(p)
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(3)
    if align is not None:
        p.alignment = align
    # split BEFORE s(): it normalises whitespace and would swallow the newlines
    lines = str(text).split("\n") if text else [""]
    for i, line in enumerate(lines):
        if i:
            run(p, "", size, bold, color)._r.append(_el("w:br"))
        rich(p, line, size, bold, color)


# ---------- ניקוי ----------
MONTHS_EN = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
             "November", "December")
DMY_RX = re.compile(r"(?<![\d.])(\d{1,2})[./](\d{1,2})[./](\d{4})(?![\d.]?\d)")
ISO_RX = re.compile(r"(?<![\d-])(\d{4})-(\d{2})-(\d{2})(?![\d-])")


def local_dates(t, en=None):
    """כל תאריך בתוצר בצורת השפה (כלל 3.6): באנגלית "30 October 2026", בעברית 30.10.2026. בקוד ולא בהוראה:
    יום.חודש.שנה ו-ISO מומרים. en: None, לפי שפת התוצר הנוכחית."""
    en = (not RTL) if en is None else en

    def dmy(d, m, y):
        d, m = int(d), int(m)
        if not (1 <= d <= 31 and 1 <= m <= 12):
            return None
        return "%d %s %s" % (d, MONTHS_EN[m - 1], y) if en else "%d.%d.%s" % (d, m, y)

    t = ISO_RX.sub(lambda x: dmy(x.group(3), x.group(2), x.group(1)) or x.group(0), t)
    if en:
        t = DMY_RX.sub(lambda x: dmy(x.group(1), x.group(2), x.group(3)) or x.group(0), t)
    return t


def s(v, limit=None):
    """מקף ארוך אסור בכל תוצר, וגם רווחים כפולים שנוצרים בהרכבת נוסח. תאריכים בצורת שפת התוצר."""
    t = " ".join(str(v).split()) if v not in (None, "") else ""
    t = t.replace("—", ", ").replace("–", "-").replace(" ,", ",")
    t = local_dates(t)
    return t[:limit] if limit else t


def produced_on(meta):
    """תאריך ההפקה בשפת התוצר (כלל 3.6): יום.חודש.שנה בעברית, "3 April 2027" באנגלית."""
    from research_sources import display_date
    raw = s(meta.get("generated_at"))[:10]
    if not (len(raw) == 10 and raw[4] == "-"):
        raw = datetime.date.today().isoformat()
    return display_date(raw, "he" if RTL else "en")


def txt(node, *keys):
    for k in keys:
        if node.get(k):
            return s(node[k])
    return ""


# ---------- בלוקי המסמך ----------
def base(doc):
    global FONT
    FONT = latin_font()
    st = doc.styles["Normal"]
    st.font.size = Pt(11)
    srpr = st.element.get_or_add_rPr()
    set_fonts(srpr, "", 11)
    # שפת ההגהה: עברית כשפת ה-cs, כדי ש-Word לא יסמן כל מילה עברית כשגיאת כתיב
    put_ordered(srpr, _el("w:lang", val="en-US", bidi="he-IL"), RPR_ORDER)
    if RTL:
        put_ordered(srpr, _el("w:rtl"), RPR_ORDER)
    for sec in doc.sections:
        sec.left_margin = sec.right_margin = Cm(2.4)
        sec.top_margin = Cm(2.2)
        sec.bottom_margin = Cm(2.0)
        if RTL:
            put_ordered(sec._sectPr, _el("w:bidi"), SECTPR_ORDER)
            put_ordered(sec._sectPr, _el("w:rtlGutter"), SECTPR_ORDER)


def title_block(doc, m):
    t = txt(m, "title", "doc_type") or tr("draft")
    p = para(doc, before=0, after=4, align=WD_ALIGN_PARAGRAPH.CENTER)
    run(p, t, 19, True, NAVY)
    sub = " · ".join([x for x in (txt(m, "doc_type") if txt(m, "title") else "",
                                  txt(m, "place_date")) if x])
    if sub:
        p = para(doc, before=0, after=2, align=WD_ALIGN_PARAGRAPH.CENTER)
        run(p, sub, 10.5, False, INK_SOFT)
    stamp = tr("stamp") % produced_on(m)
    cls = txt(m, "classification")
    if cls:
        stamp += " · " + cls
    p = para(doc, before=0, after=14, align=WD_ALIGN_PARAGRAPH.CENTER)
    run(p, stamp, 9.5, False, INK_SOFT)
    # meta.notice (מאיפה באה הטיוטה) הוא הערה ללקוח, ולא חלק מההסכם: הוא נכתב בדף הליווי בלבד, כי הטיוטה עצמה
    # נשלחת לצד השני כמו שהיא
    rule = para(doc, before=0, after=14)
    ppr = rule._p.get_or_add_pPr()
    b = ppr_put(rule, _el("w:pBdr"))
    b.append(_el("w:top", val="single", sz="8", space="6", color=LINE))


def parties(doc, m):
    ps = m.get("parties") or []
    if not ps:
        return
    for i, party in enumerate(ps):
        p = para(doc, before=2, after=2)
        name = txt(party, "name") or tr("fill")
        head = name
        for extra in (txt(party, "reg"), txt(party, "address")):
            if extra:
                head += ", " + extra
        rich(p, head, 11, False)
        defined = txt(party, "defined_as") or txt(party, "role")
        if defined:
            run(p, tr("defined") % defined, 11, True)
        # בעברית בצד הסוף של השורה (שמאל); באנגלית יישור לשמאל, כמו כל המסמך
        if i < len(ps) - 1:
            para(doc, tr("part1"), 10, False, INK_SOFT, after=6, align=WD_ALIGN_PARAGRAPH.LEFT)
    para(doc, tr("part2"), 10, False, INK_SOFT, after=12, align=WD_ALIGN_PARAGRAPH.LEFT)


def recitals(doc, rs):
    if not rs:
        return
    for r in rs:
        body = s(r)
        p = para(doc, before=0, after=5, indent=0.6)
        if RTL and not body.startswith("הואיל"):
            run(p, tr("whereas"), 11, True)
        elif not RTL and not body.upper().startswith("WHEREAS"):
            run(p, tr("whereas"), 11, True)
        rich(p, body, 11)
    para(doc, tr("now"), 11, True, INK, before=8, after=12)


def definitions(doc, defs, has_recitals=False):
    """פרק ההגדרות בא אחרי המבוא, ולכן מונח מוגדר שהמבוא משתמש בו ("למתן השירותים") מופיע לפני הגדרתו.
    משפט הפתיחה קובע שההגדרות חלות גם על המבוא, כך שהמונח מוגדר גם שם, ובקרת השלמות מזהה את המשפט
    ומורידה את הממצא לרמת מידע. בלי מבוא, משפט הפתיחה בלי "לרבות במבוא"."""
    if not defs:
        return
    h1(doc, tr("definitions"))
    para(doc, tr("defs_lead_recitals") if has_recitals else tr("defs_lead"), 11, False, INK, before=0, after=4)
    for d in defs:
        p = para(doc, before=2, after=4, indent=0.6)
        run(p, '"%s" ' % txt(d, "term"), 11, True)
        run(p, "- ", 11, False, INK_SOFT)
        rich(p, txt(d, "text", "definition"), 11)


def h1(doc, text, num=""):
    p = para(doc, before=16, after=6, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    if num:
        run(p, "%s. " % num, 13, True, NAVY)
    run(p, s(text), 13, True, NAVY)
    return p


def num_label(num):
    """מספר סעיף כפי שהוא נכתב בטקסט: נקודה אחת אחרי המספר בכל רמה, "9." וגם "9.1.", כמו שבקרת השלמות
    מחפשת. מספר שכבר נכתב עם נקודה ("9.1.") אינו מקבל נקודה שנייה, ומספר שנסגר בסוגר ("(א)") נשאר כמו שהוא."""
    n = s(num).rstrip(".")
    return n + "." if n and n[-1].isalnum() else n


def needs_review(c):
    # needs_legal_review הוא השם החדש; needs_case_law נשאר לתאימות עם טיוטות קיימות
    return bool(c.get("needs_legal_review") or c.get("needs_case_law"))


def clause(doc, c, depth=0):
    """סעיף ותתי-סעיפיו. המספר נכתב לתוך הטקסט ולא כמספור אוטומטי של Word,
    כדי שבקרת השלמות תמצא אותו ושהכיווניות לא תהפוך את הספרה והנקודה."""
    num = num_label(c.get("number"))
    head = txt(c, "heading", "title")
    body = txt(c, "text", "body")
    if needs_review(c) and body:
        # בלי מחבר פסיקה סגור אין פסיקה בשום תוצר (areo-hard-rules 1.1, 3.5), ולכן סעיף רגיש
        # (הגבלת אחריות, אי תחרות, פיצוי מוסכם) מסומן לעורך הדין בתווית האחידה, בלי המילה "פסיקה"
        body += tr("case_law")
    if depth == 0:
        if head:
            h1(doc, head, num.rstrip("."))
            if body:
                rich(para(doc, before=0, after=5, indent=0.6), body, 11)
        else:
            p = para(doc, before=8, after=5)
            if num:
                run(p, "%s " % num, 11, True)
            rich(p, body, 11)
    else:
        p = para(doc, before=0, after=4, indent=0.6 + 0.6 * depth)
        if num:
            run(p, "%s " % num, 11, True)
        if head:
            run(p, s(head) + ". ", 11, True)
        rich(p, body, 11)
    for ch in (c.get("children") or c.get("subclauses") or []):
        clause(doc, ch, depth + 1)


def page_break(doc):
    p = para(doc, before=0, after=0)
    run(p, "")._r.append(_el("w:br", type="page"))
    return p


def annexes(doc, ans):
    if not ans:
        return
    for a in ans:
        page_break(doc)
        label = txt(a, "label") or tr("annex")
        title = txt(a, "title")
        p = para(doc, before=0, after=10, align=WD_ALIGN_PARAGRAPH.CENTER)
        run(p, label + (" - " + title if title else ""), 15, True, NAVY)
        if a.get("text"):
            rich(para(doc, before=0, after=5), txt(a, "text"), 11)
        for c in (a.get("clauses") or []):
            clause(doc, c)


def signatures(doc, sig, m):
    blocks = (sig or {}).get("blocks") or []
    if not blocks:
        blocks = [{"name": txt(p, "defined_as", "name")} for p in (m.get("parties") or [])]
    if not blocks:
        return
    para(doc, s((sig or {}).get("note")) or tr("witness"),
         11, True, INK, before=22, after=14)
    tbl = doc.add_table(rows=2, cols=len(blocks))
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_borders(tbl, LINE, visible=False)
    for i, b in enumerate(blocks):
        cell_text(tbl.rows[0].cells[i], "_______________________", False, 11,
                  INK_SOFT, WD_ALIGN_PARAGRAPH.CENTER)
        lines = [txt(b, "name")]
        if txt(b, "by"):
            lines.append(tr("by") + txt(b, "by"))
        if txt(b, "title"):
            lines.append(txt(b, "title"))
        cell_text(tbl.rows[1].cells[i], "\n".join([x for x in lines if x]),
                  False, 10, INK, WD_ALIGN_PARAGRAPH.CENTER)


def clause_sources(c):
    """"MAND-M1, REG-2" או רשימה: מזהי המקור של סעיף."""
    v = c.get("source")
    if isinstance(v, (list, tuple)):
        items = v
    else:
        items = [x for x in re.split(r"[,;]", str(v or ""))]
    return [x.strip() for x in items if str(x).strip()]


def walk_clauses(cs, out=None):
    out = [] if out is None else out
    for c in cs or []:
        out.append(c)
        walk_clauses(c.get("children") or c.get("subclauses"), out)
    return out


def all_clauses(d):
    out = walk_clauses(d.get("clauses"))
    for a in d.get("annexes") or []:
        walk_clauses(a.get("clauses"), out)
    return out


def source_link(sid, research):
    """טקסט וקישור למזהה מקור: REG-<שורה>, MAND-<מזהה>, AGR-<מספר>."""
    from research_sources import approved_agreements, normalise
    r = normalise(research or {})
    kind, _, key = sid.partition("-")
    if kind == "REG":
        for i, x in enumerate(r.get("law") or []):
            if str(x.get("row", i + 1)) == key:
                return "%s (%s)" % (s(x.get("instrument")), s(x.get("sections"))), x.get("url")
    elif kind == "AGR":
        for x in approved_agreements(r):
            if str(x.get("no")) == key:
                return s(x.get("title")), x.get("url")
    elif kind == "MAND":
        rows = {str(x.get("row", i + 1)): x for i, x in enumerate(r.get("law") or [])}
        for m in r.get("mandatory_clauses") or []:
            if m.get("clause_id") == key:
                src = rows.get(str(m.get("source_row")), {})
                return tr("mand") % (s(m.get("title")) or key), src.get("url")
    return sid, None


def sources_section(doc, d, research):
    """המקורות שהטיוטה נשענת עליהם (מצב מחקר), בדף הליווי. לא חלק מהטיוטה: היא נשלחת לצד השני כמו שהיא. כל מקור
    לחיץ, ובלי מזהים פנימיים."""
    if not research:
        return
    from research_sources import NORM_RANKS, approved_agreements, normalise, scope_has
    r = normalise(research)
    law = (r.get("law") or []) if scope_has(r, "research") else []
    ags = approved_agreements(r) if scope_has(r, "agreements") else []
    if not (law or ags):
        return
    h1(doc, tr("sources"))

    def grid(header, rows, link_col):
        tbl = doc.add_table(rows=1 + len(rows), cols=len(header))
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        table_borders(tbl)
        for jj, h in enumerate(header):
            cell_text(tbl.rows[0].cells[jj], h, True, 9.5, NAVY)
        for ii, row in enumerate(rows):
            for jj, v in enumerate(row):
                if jj == link_col:
                    cell_link(tbl.rows[ii + 1].cells[jj], v[1], v[0])
                else:
                    cell_text(tbl.rows[ii + 1].cells[jj], v, False, 9.5)
        para(doc, after=6)

    if law:
        h1(doc, tr("law"))
        ranks = NORM_RANKS if RTL else NORM_RANKS_EN
        grid(tr("law_head"),
             [[ranks.get(x.get("rank"), ""), (s(x.get("instrument")), x.get("url")), s(x.get("sections")),
               tr("verified") if x.get("verified") else tr("unverified")] for x in law], 1)
    if ags:
        h1(doc, tr("ags"))
        grid(tr("ags_head"),
             [[(s(x.get("title")), x.get("url")), s(x.get("publisher")),
               ORIENT_HE.get(x.get("orientation"), s(x.get("orientation"))) if RTL else ORIENT_EN.get(x.get("orientation"), s(x.get("orientation")))]
              for x in ags], 0)


def footer(doc, m):
    bits = [txt(m, "doc_type") or tr("draft")]
    if txt(m, "classification"):
        bits.append(txt(m, "classification"))
    bits.append(produced_on(m))
    for sec in doc.sections:
        p = sec.footer.paragraphs[0]
        dir_p(p)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run(p, " · ".join(bits) + tr("page"), 8.5, False, INK_SOFT)
        p._p.append(_el("w:fldSimple", instr="PAGE"))


# ---------- הרכבה ----------
class DraftRefused(Exception):
    """הטיוטה אינה נבנית. args[0]: רשימת הסיבות."""


class State4Refused(DraftRefused):
    pass


class PublicFormRefused(DraftRefused):
    pass


def public_form_gate(d, prof):
    """סעיף שמקורו בטופס של גוף ציבורי, או בדרישה שחלה רק על גוף ציבורי (public_form: true: ערבות לפי טופס
    ההליך התחרותי, הצהרה לפי כללי העסקאות של גופים ציבוריים, נוהלי רכש ציבוריים), נכנס רק כשאחד הצדדים גוף ציבורי: החברה לפי
    הפרופיל או לפי meta.company_role_code (contracting_authority), או הצד שכנגד (meta.counterparty_public_body, או
    bidder: החברה מציעה בהליך תחרותי), או כשהמשתמש ביקש אותו (user_requested: true). אחרת הוא מוצע כאפשרות
    ב-cover.options ואינו נכנס."""
    from check_draft_integrity import public_party
    meta = d.get("meta") or {}
    if public_party(prof, meta.get("counterparty_public_body"), meta.get("company_role_code")):
        return
    bad = [c for c in all_clauses(d) if c.get("public_form") and not c.get("user_requested")]
    if bad:
        raise PublicFormRefused(
            ["סעיף %s (%s) מקורו בטופס של גוף ציבורי, ואף אחד מהצדדים אינו גוף ציבורי (הפרופיל, "
             "meta.counterparty_public_body). הוציאו אותו מ-clauses "
             "והעבירו ל-cover.options, או סמנו user_requested אם המשתמש ביקש אותו."
             % (num_label(c.get("number")).rstrip(".") or "?", txt(c, "heading") or txt(c, "text")[:40])
             for c in bad])


def concern_refs(d):
    """(התשובה, [סעיפים]) מ-cover.main_concern: התשובה לשאלה "מה הכי מדאיג אתכם בעסקה הזו?"."""
    mc = (d.get("cover") or {}).get("main_concern")
    if not mc:
        return "", []
    if not isinstance(mc, dict):
        return s(mc), []
    refs = mc.get("clauses") or []
    refs = refs if isinstance(refs, (list, tuple)) else re.split(r"[,;]\s*", str(refs))
    return s(mc.get("answer")), [num_label(x).rstrip(".") for x in refs if str(x).strip()]


def concern_gate(d):
    """החשש העיקרי שהלקוח מסר מתורגם לפחות לסעיף מותאם אחד, והסעיף קיים בטיוטה."""
    answer, refs = concern_refs(d)
    if not answer:
        return
    if not refs:
        raise DraftRefused(["החשש העיקרי שמסר הלקוח (cover.main_concern) לא תורגם לאף סעיף. נסחו לפחות סעיף מותאם "
                            "אחד, ורשמו את מספרו ב-cover.main_concern.clauses."])
    nums = {num_label(c.get("number")).rstrip(".") for c in all_clauses(d) if c.get("number")}
    missing = [x for x in refs if x not in nums]
    if missing:
        raise DraftRefused(["cover.main_concern מפנה לסעיפים שאינם בטיוטה: %s." % ", ".join(missing)])


THIRD_PARTY = "third_party_paper"   # meta.source_mode של מצב 2ב: פלייבוק ונוסחים של צד שלישי, בלי מחקר
RESEARCH_IDS = re.compile(r"^(?:REG|MAND|AGR)-")


def state4_gate(d, research, approved_sources=None, inc_country=None):
    """ניסוח מבחוץ (הסכמים ברשת ופרקטיקת שוק) מזוהה לפי notice, sources, קובץ מחקר או מקור REG-, MAND-, AGR-.
    מותר רק כשללקוח אין פלייבוק ואין הסכמי טיוטה והוא ביקש זאת במפורש: meta.outside_basis חייב לכלול
    no_playbook, no_client_agreements ו-client_asked כאמת (core-contract.md, פרק 10). אין שער אישור על המחקר:
    הבדיקה כאן היא של מבנה ומקורות מורשים בלבד. מצב 2ב (meta.source_mode: third_party_paper) נושא notice
    משלו ואינו מחקר, אבל סעיף שמקורו במחקר מחזיר אותו לכאן. approved_sources: מקורות-מאושרים.json."""
    from research_sources import approved_mandatory, check, normalise, scope_has
    m = d.get("meta") or {}
    tp = s(m.get("source_mode")) == THIRD_PARTY
    from_research = any(RESEARCH_IDS.match(x) for c in all_clauses(d) for x in clause_sources(c))
    if not ((m.get("notice") and not tp) or d.get("sources") or research or from_research):
        return None
    ob = m.get("outside_basis") or {}
    miss = [k for k in ("no_playbook", "no_client_agreements", "client_asked") if ob.get(k) is not True]
    if miss:
        raise State4Refused(["ניסוח מבחוץ מותר רק כשללקוח אין פלייבוק ואין הסכמי טיוטה והוא ביקש זאת במפורש. "
                             "חסר ב-meta.outside_basis: %s." % ", ".join(miss)])
    if not research:
        raise State4Refused(["מקור REG-, MAND-, AGR- או sources דורש את קובץ המחקר (--research), "
                             "שנאסף מהרשימה המאושרת בלבד."])
    blocking, _, _ = check(research, stage="draft", approved_sources=approved_sources, inc_country=inc_country)
    r = normalise(research)
    if scope_has(r, "research"):
        placed = set()
        for c in all_clauses(d):
            placed.update(clause_sources(c))
        for mc in approved_mandatory(r):
            if "MAND-%s" % mc.get("clause_id") not in placed:
                blocking.append("סעיף חובה %s (%s) לא שובץ באף סעיף בטיוטה. משבצים אותו, או מסירים אותו עם סיבה."
                                % (mc.get("clause_id"), mc.get("title") or ""))
    if blocking:
        raise State4Refused(blocking)
    return r


def build(d, prof, out, research=None, cover=None, lang=None, approved_sources=None):
    global RTL
    m = d.get("meta") or {}
    r4 = state4_gate(d, research, approved_sources, (prof or {}).get("incorporation_country"))
    public_form_gate(d, prof)
    concern_gate(d)
    # שפת התוצר: --lang, אחריו meta.language של הטיוטה, אחריו deliverable_language בפרופיל (both: display_language)
    lang = s(lang) or s(m.get("language")) or s(profile_lang(prof)) or "he"
    RTL = not is_en(lang)
    d, why = english_parties(d, prof, RTL, s)
    if why:
        raise DraftRefused(why)

    del GAPS[:]
    doc = Document()
    base(doc)
    title_block(doc, m)
    parties(doc, m)
    recitals(doc, d.get("recitals"))
    definitions(doc, d.get("definitions"), bool(d.get("recitals")))
    for c in (d.get("clauses") or []):
        clause(doc, c)
    annexes(doc, d.get("annexes"))
    signatures(doc, d.get("signatures"), m)
    footer(doc, m)
    if not RTL:
        mixed_direction(doc)
    doc.save(out)
    # counted from what was actually written, not from the input: a placeholder
    # that never reached the page must not be reported as marked. Counted before
    # the cover, whose list of open items would otherwise be counted again.
    # **One counter for every report**: the integrity check's
    # count_placeholders, run on the saved file, is the number printed and written to the cover.
    from build_template_registry import docx_text
    from check_draft_integrity import count_placeholders
    gaps = count_placeholders(docx_text(out, limit=400000)[0])
    if cover:
        write_cover(cover, d, r4, gaps)
    problems = client_text_problems((out, cover), RTL, docx_text, _voice_check)
    if problems:
        for f in (out, cover):
            if f and os.path.exists(f):
                os.remove(f)
        raise DraftRefused(problems)
    return {"out": out, "rtl": RTL, "clauses": len(d.get("clauses") or []),
            "definitions": len(d.get("definitions") or []),
            "annexes": len(d.get("annexes") or []), "placeholders": gaps,
            "cover": cover or ""}


def open_items(d):
    """[(מיקום, [מצייני חוסר])] מתוך ה-JSON, לפי סדר המסמך. התווית "טעון בדיקה משפטית" אינה חוסר."""
    out = []

    def add(where, *texts):
        hits = [x for t in texts for x in GAP_RX.findall(s(t)) if x.strip() not in
                (TXT["he"]["case_law"].strip(), TXT["en"]["case_law"].strip())]
        if hits:
            out.append((where, hits))

    m = d.get("meta") or {}
    add(tr("loc_meta"), m.get("title"), m.get("place_date"),
        *[txt(p, k) for p in (m.get("parties") or []) for k in ("name", "reg", "address")])
    add(tr("loc_recitals"), *(d.get("recitals") or []))
    for x in d.get("definitions") or []:
        add(tr("loc_def") % txt(x, "term"), txt(x, "text", "definition"))
    for a in d.get("annexes") or []:
        if a.get("text"):
            add(txt(a, "label") or tr("annex"), txt(a, "text"))
    for c in all_clauses(d):
        add(tr("loc_clause") % num_label(c.get("number")).rstrip("."), txt(c, "heading", "title"), txt(c, "text", "body"))
    blocks = (d.get("signatures") or {}).get("blocks") or []
    add(tr("loc_sign"), *[txt(b, k) for b in blocks for k in ("name", "by", "title")])
    return out


def key_date_lines(cv, lang=None):
    """שורות הפרק "המועדים שיהיו חשובים בהמשך" מ-cover.key_dates: מחרוזת, או {what, when, clause}. המנסח אינו
    מחשב תאריך: when הוא המועד כפי שההסכם מגדיר אותו ("90 יום לפני תום התקופה"). רשימה ריקה: הפרק אינו מוצג."""
    t = TXT[("en" if is_en(lang) else "he") if lang else ("he" if RTL else "en")]
    out = []
    for k in (cv or {}).get("key_dates") or []:
        if isinstance(k, dict):
            what, when, cl = s(k.get("what")), s(k.get("when")), s(k.get("clause"))
            line = ": ".join(x for x in (what, when) if x)
            if line and cl:
                line += t["key_date_clause"] % cl
        else:
            line = s(k)
        if line:
            out.append(line)
    return out


def write_cover(path, d, r=None, gaps=None):
    """דף הליווי, בכל מצב. במצב 4 (r הוא קובץ המחקר) מטריצת עקיבות מול המחקר, סעיפי חובה שהוסרו
    ומגבלות המחקר. בלי מחקר (מצב 2ב, או טיוטה מ-JSON בלי נייר של החברה) מטריצת המקורות מול הפלייבוק,
    הנוסחים ועובדות העסקה, לפי clauses[].source: PB-<נושא או כלל>, DOC-<מספר בנוסחים>, DEAL-<עובדה>.
    בשני המצבים: מה נותר [להשלים], טעון בדיקה משפטית, סעיפים מותנים, נושאים בלי עמדה מבוססת בפלייבוק,
    הכרעות והערות, ובשורה האחרונה הצעה להערכת סיכונים. הנתונים מ-cover שב-JSON (draft-json-schema.md)."""
    m = d.get("meta") or {}
    cv = d.get("cover") or {}
    tp = s(m.get("source_mode")) == THIRD_PARTY
    doc = Document()
    base(doc)
    run(para(doc, after=2), tr("cover") + s(cv.get("title") or txt(m, "title", "doc_type") or tr("draft")),
        16, True, NAVY)
    if r is not None:
        from research_sources import normalise
        r = normalise(r)
        stamp = tr("cover_stamp") % produced_on(m)
    else:
        stamp = tr("cover_stamp_plain") % produced_on(m)
    run(para(doc, after=6), stamp, 9.5, False, INK_SOFT)

    # התוצאה קודם, ואחריה פעולה אחת (areo-voice.md): מה מוכן, כמה נשאר, מה עושים עכשיו. הכול נספר בקוד
    marked = [c for c in all_clauses(d) if needs_review(c)]
    cond = [c for c in all_clauses(d) if c.get("condition")]
    lead = tr("lead")
    todo = (gaps or 0) + len(marked) + len(cond)
    if todo:
        lead += " " + tr("lead_open") % (todo, 5 * max(1, -(-todo // 5)))
        if gaps:
            nxt = tr("next_fill")
        else:
            nxt = tr("next_review") % ", ".join(num_label(c.get("number")).rstrip(".") for c in marked + cond)
    else:
        lead += " " + tr("lead_clear")
        nxt = tr("next_send")
    run(para(doc, after=2), lead, 12, True, INK)
    run(para(doc, after=10), nxt, 11, False, NAVY)

    notice = txt(m, "notice")
    if tp and not notice:
        notice = tr("tp_notice")
    if notice:
        h1(doc, tr("notice_title"))
        box = para(doc, before=0, after=10)
        ppr_put(box, _el("w:shd", val="clear", color="auto", fill="F5F7F9"))
        run(box, notice, 10, False, NAVY)

    def matrices():
        if r is not None:
            trace_matrix(doc, d, r)
            sources_section(doc, d, r)
        else:
            source_matrix(doc, d, cv)

    def section(title, lines, size=10.5):
        if not lines:
            return
        h1(doc, title)
        for ln in lines:
            rich(para(doc, after=2, indent=0.5), ln, size)

    # החשש העיקרי של הלקוח והסעיפים שעונים לו, בראש הרשימה: זה מה שהלקוח יבדוק ראשון
    answer, refs = concern_refs(d)
    if answer:
        section(tr("concern"), [tr("concern_answer") % answer, tr("concern_clauses") % ", ".join(refs)])
    # מה נבחר בטופס השאלות שנבנה ממפת השונות, ולמה (cover.choices)
    section(tr("choices"), choice_lines(cv))
    # מועדי הודעה, חידוש ואבני דרך, כפי שההסכם מגדיר אותם; מרשם ההתחייבויות מחשב אותם אחרי החתימה
    section(tr("key_dates"), key_date_lines(cv))
    # המספר מ-count_placeholders על הטיוטה שנשמרה, כמו בבקרת השלמות; בלעדיו (קריאה ישנה) הכותרת כמו קודם
    section(tr("to_fill_count") % (tr("to_fill"), gaps) if gaps else tr("to_fill"),
            ["%s: %s" % (where, ", ".join(hits)) for where, hits in open_items(d)])
    if marked:
        section(tr("legal_review"), [tr("case_law_list") + ", ".join(num_label(c.get("number")).rstrip(".")
                                                                   for c in marked)])
    section(tr("conditional"), [tr("conditional_line") % (num_label(c.get("number")).rstrip("."), s(c.get("condition")))
                                for c in all_clauses(d) if c.get("condition")])
    gaps_ = [tr("pb_gap_line") % (s(g.get("topic")), s(g.get("reason"))) if isinstance(g, dict) else s(g)
             for g in (cv.get("playbook_gaps") or [])]
    if gaps_ and cv.get("playbook_gaps_answer"):
        gaps_.append(tr("pb_gaps_answer") % s(cv.get("playbook_gaps_answer")))
    section(tr("pb_gaps"), gaps_)
    section(tr("options"), [tr("option_line") % (s(o.get("title")), s(o.get("reason"))) if isinstance(o, dict)
                            else s(o) for o in (cv.get("options") or [])])
    section(tr("decisions"), [s(x) for x in (cv.get("decisions") or [])])
    section(tr("notes"), [s(x) for x in (cv.get("notes") or [])] + ld_notes(d))
    matrices()
    if r is not None:
        research_gaps(doc, d, r)
    para(doc, tr("run_risk"), 10.5, True, INK, before=14)
    if not RTL:
        mixed_direction(doc)
    doc.save(path)


def choice_lines(cv, lang=None):
    """שורות הפרק "מה נבחר ולמה" מ-cover.choices: מחרוזת, או {question, answer, why, default}. בלשון הלקוח:
    השאלה, מה נבחר, והסיבה (תשובת הלקוח, או ברירת המחדל כשלא נשאל)."""
    t = TXT[("en" if is_en(lang) else "he") if lang else ("he" if RTL else "en")]
    out = []
    for c in (cv or {}).get("choices") or []:
        if isinstance(c, dict):
            why = s(c.get("why")) or (t["choice_default"] if c.get("default") else "")
            line = ": ".join(x for x in (s(c.get("question")), s(c.get("answer"))) if x)
            out.append(line + ((". " if line and not line.endswith(".") else " ") + why if why else ""))
        elif s(c):
            out.append(s(c))
    return [x for x in out if x]


def ld_notes(d):
    """ההערה על פיצוי מוסכם בדף הליווי, בכל דין: "טעון בדיקה משפטית" עם שם הדין החל (meta.governing_law), או "הדין
    החל, שטרם נקבע". הקוד אינו מצטט הוראת חוק: מה שהדין קובע נשלף במחקר העומק, מרשימת המקורות המאושרים."""
    from check_draft_integrity import LD_RX
    import governing_law as GL
    ld = [num_label(c.get("number")).rstrip(".") for c in all_clauses(d)
          if c.get("number") and LD_RX.search(txt(c, "text", "body"))]
    if not ld:
        return []
    law = (d.get("meta") or {}).get("governing_law")
    return [tr("ld_review") % (", ".join(ld), GL.name(law, "he" if RTL else "en") if law else tr("law_unset"))]


def source_matrix(doc, d, cv):
    """מטריצת המקורות של טיוטה בלי מחקר: לכל סעיף, העמדה מהפלייבוק, המבנה מהנוסחים, ועובדות העסקה."""
    h1(doc, tr("matrix"))
    # תת-סעיף בלי source יורש את המקור של הסעיף שמעליו, כדי שלא יוצג "אין עמדה" בכל שורה
    rows = []

    def walk(cs, inherited):
        for c in cs or []:
            own = clause_sources(c) or inherited
            if c.get("number"):
                rows.append((c, own))
            walk(c.get("children") or c.get("subclauses"), own)

    walk(d.get("clauses"), [])
    for a in d.get("annexes") or []:
        walk(a.get("clauses"), [])
    tbl = doc.add_table(rows=1 + len(rows), cols=5)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_borders(tbl)
    for jj, h in enumerate(tr("matrix_head")):
        cell_text(tbl.rows[0].cells[jj], h, True, 9.5, NAVY)
    for ii, (c, sids) in enumerate(rows):
        by = lambda pre: ", ".join(x[len(pre):] for x in sids if x.upper().startswith(pre))
        cells = tbl.rows[ii + 1].cells
        cell_text(cells[0], num_label(c.get("number")).rstrip("."), False, 9.5)
        cell_text(cells[1], txt(c, "heading") or txt(c, "text")[:40], False, 9.5)
        # במקום קודים (R33, DOC-1): נושא הכלל כשהוא ידוע (cover.playbook_topics), ושם הנוסח (cover.documents)
        pb = [x for x in by("PB-").split(", ") if x]
        topics = cv.get("playbook_topics") or {}
        pb_txt = ", ".join(dict.fromkeys(lang_safe(s(topics.get(x)), "") or tr("from_pb") for x in pb))
        cell_text(cells[2], pb_txt or tr("no_pb"), False, 9.5, INK if pb else INK_SOFT)
        # שם ההסכם והסעיף שעליו נשענו (clauses[].source_clause, בלשון הלקוח, למשל "סעיף 9.2")
        src_c = s(c.get("source_clause")) if c.get("source_clause") else ""
        titles = ", ".join(doc_title(cv, x) for x in by("DOC-").split(", ") if x)
        cell_text(cells[3], (titles + (" (%s)" % src_c if titles and src_c else src_c)) if (titles or src_c) else "", False, 9.5)
        deal = by("DEAL-") or (tr("yes") if any(x.upper() == "DEAL" for x in sids) else "")
        cell_text(cells[4], deal, False, 9.5)
    para(doc, after=6)
    lines = []
    pb_ = cv.get("playbook") or {}
    if pb_:
        lines.append(tr("pb_line") % ", ".join(x for x in (lang_safe(s(pb_.get("name")), ""), pb_status(pb_.get("status"))) if x)
                     if isinstance(pb_, dict) else tr("pb_line") % s(pb_))
    for i, x in enumerate(cv.get("documents") or []):
        if isinstance(x, dict):
            lines.append(tr("doc_line") % (s(x.get("no") or i + 1),
                                           ", ".join(lang_safe(s(x.get(k)), "") for k in ("title", "publisher", "year")
                                                     if lang_safe(s(x.get(k)), ""))
                                           or "Form %s" % (x.get("no") or i + 1)))
        else:
            lines.append(tr("doc_line") % (i + 1, lang_safe(s(x), "Form %s" % (i + 1))))
    if lines:
        h1(doc, tr("sources_used"))
        for ln in lines:
            rich(para(doc, after=2, indent=0.5), ln, 10.5)
    facts = [s(x) for x in (cv.get("facts") or [])]
    if facts:
        h1(doc, tr("facts"))
        for ln in facts:
            rich(para(doc, after=2, indent=0.5), ln, 10.5)


def lang_safe(text, fallback):
    """בעסקה באנגלית שם עברי (נושא בפלייבוק, שם נוסח) אינו מוצג: במקומו הכינוי הניטרלי."""
    return fallback if (not RTL and HEB_CH.search(text or "")) else text


def doc_title(cv, no):
    """שם הנוסח מספר no מ-cover.documents, קצר, במקום "DOC-<n>"."""
    for i, x in enumerate(cv.get("documents") or []):
        n = str(x.get("no") or i + 1) if isinstance(x, dict) else str(i + 1)
        if n == str(no):
            t = lang_safe(s(x.get("title") if isinstance(x, dict) else x), "Form %s" % no)
            return t if len(t) <= 40 else t[:40].rsplit(" ", 1)[0] + "..."
    return s(no)


def pb_status(v):
    """מעמד הפלייבוק במילים של הלקוח: "פלייבוק מוצע" או "טעון אישור" הם טיוטת מדיניות (בלי שער אישור)."""
    t = s(v)
    return tr("pb_pending") if re.search(r"מוצע|טעון אישור|טיוטת מדיניות|מחכה לאישור|proposed|pending|draft|awaiting", t, re.I) else t


def write_cover4(path, d, r):
    """שם קודם, לתאימות: דף הליווי של מצב 4."""
    write_cover(path, d, r)


def trace_matrix(doc, d, r):
    """מטריצת העקיבות של מצב 4: מקור במחקר, סעיף חובה ועמדת פתיחה, לכל סעיף."""
    h1(doc, tr("trace"))
    rows = [c for c in all_clauses(d) if c.get("number")]
    tbl = doc.add_table(rows=1 + len(rows), cols=5)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_borders(tbl)
    for jj, h in enumerate(tr("trace_head")):
        cell_text(tbl.rows[0].cells[jj], h, True, 9.5, NAVY)
    for ii, c in enumerate(rows):
        sids = clause_sources(c)
        cells = tbl.rows[ii + 1].cells
        cell_text(cells[0], s(c.get("number")), False, 9.5)
        cell_text(cells[1], txt(c, "heading") or txt(c, "text")[:40], False, 9.5)
        if sids:
            label, url = source_link(sids[0], r)
            label = label if label != sids[0] else tr("own")
            cell_link(cells[2], url, label) if url else cell_text(cells[2], label, False, 9.5)
        else:
            cell_text(cells[2], tr("own"), False, 9.5, INK_SOFT)
        cell_text(cells[3], tr("yes") if any(x.startswith("MAND-") for x in sids) else tr("no"), False, 9.5)
        cell_text(cells[4], tr("yes") if c.get("opening_position") else "", False, 9.5)
    para(doc, after=6)


def research_gaps(doc, d, r):
    """סעיפי החובה שהוסרו והחשיפה, ומגבלות המחקר: רק במצב 4."""
    from research_sources import scope_has
    ap_ = r.get("approvals") or {}
    removed = ap_.get("removed_clauses") or []
    if removed:
        h1(doc, tr("removed"))
        for x in removed:
            if isinstance(x, dict):
                line = tr("removed_line") % (x.get("clause_id", ""), x.get("reason", ""), x.get("exposure", tr("fill")))
            else:
                line = str(x)
            rich(para(doc, after=3, indent=0.5), line, 10.5)

    h1(doc, tr("gaps"))
    if not scope_has(r, "research"):
        para(doc, tr("no_research"), 10.5, True, INK, after=3)
    else:
        para(doc, tr("research_limits"), 10.5, False, INK, after=3)
        for x in [x for x in (r.get("law") or []) if not x.get("verified")]:
            p = para(doc, after=3, indent=0.5)
            run(p, tr("unverified_line"), 10.5, True)
            link(p, x.get("url"), s(x.get("instrument")), 10.5)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--draft", required=True)
    ap.add_argument("--profile")
    ap.add_argument("--out", required=True)
    ap.add_argument("--research", help="מצב 4: קובץ המחקר שאושר. בלעדיו טיוטת מצב 4 אינה נבנית")
    ap.add_argument("--cover", help="דף ליווי, בכל מצב: במצב 4 עם מטריצת עקיבות מול המחקר, ובלי מחקר עם "
                                    "מטריצת המקורות (פלייבוק, נוסחים, עובדות העסקה)")
    ap.add_argument("--lang", choices=("he", "en"), help="שפת הטיוטה; בלעדיו: meta.language, ואחריו "
                                                         "deliverable_language בפרופיל")
    ap.add_argument("--approved-sources", help="מצב 4: מקורות-מאושרים.json (ברירת מחדל: משתנה הסביבה "
                                               "AREO_APPROVED_SOURCES, ואחריו העותק שבתוסף, lib/מקורות-מאושרים.json). "
                                               "בלי רשימה תקפה, טיוטה ממחקר רגולטורי נעצרת בקוד 2")
    ap.add_argument("--force", action="store_true", help="לדרוס טיוטה או דף ליווי קיימים (הרצה חוזרת אחרי תיקון)")
    a = ap.parse_args()
    from build_template_registry import guard_out
    inputs = [a.draft, a.profile, a.research, a.approved_sources]
    guard_out(a.out, inputs, a.force)
    if a.cover:
        guard_out(a.cover, inputs + [a.out], a.force)
    d = json.load(io.open(a.draft, encoding="utf-8"))
    prof = {}
    if a.profile:
        try:
            prof = json.load(io.open(a.profile, encoding="utf-8"))
        except (OSError, ValueError):
            prof = {}
    research = json.load(io.open(a.research, encoding="utf-8")) if a.research else None
    from research_sources import ApprovedSourcesMissing
    try:
        r = build(d, prof, a.out, research, a.cover, a.lang, a.approved_sources)
    except ApprovedSourcesMissing as e:
        print("הטיוטה לא נבנתה. סירוב: %s" % e)
        sys.exit(2)
    except DraftRefused as e:
        print("הטיוטה לא נבנתה:")
        for b in e.args[0]:
            print("  חוסם: " + b)
        sys.exit(1)
    print("הטיוטה נבנתה: %s" % r["out"])
    print("סעיפים ראשיים: %d · הגדרות: %d · נספחים: %d · כיווניות: %s"
          % (r["clauses"], r["definitions"], r["annexes"], "RTL" if r["rtl"] else "LTR"))
    if r["placeholders"]:
        print("פרטים להשלים שסומנו בצהוב: %d. הם של הלקוח, רשומים בדף הליווי ובהודעת המסירה, ואינם עוצרים "
              "את המסירה." % r["placeholders"])
    if r["cover"]:
        print("דף הליווי נבנה: %s" % r["cover"])
    import governing_law as GL
    if not GL.code((d.get("meta") or {}).get("governing_law")):
        print("אזהרה: meta.governing_law חסר או לא מוכר. הדין החל נשאל לפני הניסוח (SKILL.md), ואינו מונח. "
              "Warning: meta.governing_law is missing or unknown. Ask for the governing law; never assume it.")


if __name__ == "__main__":
    main()
