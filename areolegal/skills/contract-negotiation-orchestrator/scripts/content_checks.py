#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""בדיקות התוכן של הסבב: מה שהשער בודק בנוסח שמתקבל אחרי כל התיקונים, ובהכרעות.

הבדיקות האלה כלליות לכל סוג הסכם: אין בהן נושא,
עמדה או חוק של סוג הסכם מסוים. כל מה שתלוי בעסקה מגיע מקובץ ההכרעות, מקובץ
המצב, מהפלייבוק או מהמניפסט של ההסכמים.

| קוד | שינוי | מה נבדק | חוסם משלוח |
|---|---|---|---|
| CON_REF_MISSING | 19, 39 | הפניה לסעיף או לנספח שאין לו יעד בנוסח המתקבל | בנוסח שהכנסנו |
| CON_TERM_* | 19, 39 | מונח מוגדר שלא מוגדר לפני השימוש, או שאינו בשימוש | לא |
| CON_TBA | 39 | "יוסכם", "יוסכמו", "to be agreed" בנוסח שהכנסנו | כן |
| CON_ANNEX_SHARED | 19 | פסקה בנספח שחולקת מונח או מספר סעיף עם פסקה שתוקנה | לא |
| CON_CLIENT_ANSWER | 19, 23 | תשובת לקוח שיושמה ואינה בנוסח, רשומה בלי status, או תשובה שיושמה בלי clause_ids | כן |
| PREC_ANNEX_PREVAILS | 23 | סעיף שקובע שנספח, נוהל או מסמך חיצוני גובר על ההסכם | כן |
| DEAL_DOCS_CONFLICT | 23 | סתירה בין מסמכי העסקה בלי הכרעה | כן |
| NEUTRALIZER | 24 | ביטוי מנטרל בנוסח שנשאר בלי שינוי | לא |
| REP_UNAPPROVED | 26 | מצג או התחייבות בנוסח שלנו בלי רשומה מאושרת, ולא בסוגריים | כן |
| CONFLICT_CHECK | 27 | "אין הסכם סותר", "החברה גילתה" בלי בדיקת התנגשות (`meta.deal_context.existing_agreements_with_counterparty`) | כן |
| EXISTING_AGREEMENT | 27 | סעיף מיצוי או עדיפות, והסכם קיים בתוקף בלי השפעה רשומה | לא |
| OTHER_PARTY_NAME | 28 | שם של צד מהסכם חתום אחר בבועה החיצונית | כן |
| PRICE_TERMS | 32 | Incoterms, מטבע או הצמדה בתיקון שלנו, בלי שינוי בנספח המחירים | לא |
| PRICE_CONFORMING | 32 | בועה "תיקון עקבי" בלבד, כשהשינוי נוגע במחיר | כן |
| COMPLIANCE | 34 | סעיף ציות (שוחד, סנקציות, יצוא, הלבנת הון) בלי הכרעה מפורשת של המשתמש | כן |
| BILINGUAL_* | 44 | הכרעה שמשנה גרסה אחת בלבד, או סתירה בין הגרסאות בלי הכרעה | כן |
| POSITION_MISMATCH | 1 | פלייבוק של משפחה אחרת או של הצד ההפוך | כן |
| PARTY_LABEL | 1 | כינוי צד בנוסח שלנו שאינו בהסכם (נוסח מהפלייבוק שלא עבר את מפת המונחים) | כן |
| RED_MARKER | 59 | סימן אדום של כלל שחל, בנוסח המתקבל, בלי הכרעה לאותו כלל | כן |
| HIDDEN_TEXT | 6 | טקסט מוסתר בטיוטה שלהם, בפסקה שאין בה הכרעה | כן |
| THEIR_INTERNAL_COMMENT | 11 | בועה שלהם שנראית פנימית, ואינה רשומה ב-`meta.exposed_comments` | כן |
| THEIR_COMMENT_UNANSWERED | 10 | בועה שלהם שאין לה מענה ואין לה הכרעה | לא |
| COMBO | 56 | שתי הכרעות באותו צירוף, בלי בדיקה רשומה ב-`meta.combo_checks` | לא |
| PARAGRAPH_REPLACED | סימון כירורגי | מחיקת פסקה והוספת פסקה במקומה, כשרוב המילים נשארו: לא כירורגי | כן |
| REPLACE_COLLAPSED | סימון כירורגי | replace שסימן את רוב הפסקה כשרוב המילים נשארו: להשתמש ב-replace_span | כן |
| STRUCT_ORPHAN_PROVISO | כלל 1 | הפניה לסייג ("הסייג שלהלן", "the foregoing proviso") בלי סייג בנוסח המתקבל | כשהסייג נמחק אצלנו |
| STRUCT_BACKREF | כלל 1 | הפסקה שאחרי פסקה שמחקנו נפתחת ב"כאמור לעיל" | כן |
| STRUCT_LIST_EMPTY | כלל 1 | כל פריטי רשימה נמחקו ונשאר משפט הפתיחה שלה | כן |
| STRUCT_DANGLING_CONJ | כלל 1 | "או", "and" לפני פריט שכבר אינו קיים | כן |
| STRUCT_PROVISO_ROLE | כלל 1 | סייג שהכנסנו ובו התחייבות או איסור | לא |
| DEPENDENT_UNDECIDED, DEPENDENT_KEEP_NO_REASON | כלל 2 | סעיף תלוי בהכרעה שמשנה משטר, בלי הכרעה או בלי נימוק להשארה | כן |
| POST_CHECK_FAILED, POST_CHECK_MANUAL | כלל 3 | בדיקת התוצאה של כלל שהוחל (post_checks בגרעין) | בכלל קריטי |
| TIME_ANCHOR | כלל 4 | מועד תחולה או התחלה שעבר, או עוגן ריק, שלא נרשם ב-time_anchors | כן |
| VAGUE_TERM | כלל 5 | מונח עמום בנוסח שלנו בלי מבחן מוגדר (common/vague_terms.py) | לא |
| FACT_WITHOUT_SOURCE | כלל 6 | בועה שנשענת על עובדה על צד, בלי fact_source | כן |
| ENTITY_PROFILE_FACT, ENTITY_RULE_UNCONFIRMED | כלל 7 | עובדה מהפרופיל או כלל של דין ורגולציה, כשהישות בנייר לא אושרה | כן |
| REF_BUBBLE, BUBBLE_SAME_TOPIC | כלל 8 | בועת הפניה, או כמה בועות לאותו כלל באותו סעיף | כן |
| WEAKNESS_IN_BUBBLE | כלל 9 | נימוק שחושף חולשה שלנו | לא |
| THEIR_GREEN_MARKED | כלל 10 | סימון של נוסח שלהם שכבר בירוק | כן |
| THEIR_YELLOW_NOT_CHIP, THEIR_TRACK_MISSING | כלל 10 | נוסח שלהם בצהוב שלא סומן כמטבע חליפין, או הכרעה בלי סיווג | לא |
| PROPORTIONALITY_UNASKED, FIGHT_LIST_MISSING | כלל 11 | יותר בקשות מרשימת המאבק, והמשתמש לא נשאל | כן |
| COUNTERPARTY_KIND_UNDECIDED | כלל 12 | כלל דין, שפה, מטבע או מס מול צד זר, בלי תנאי הפעלה לצד זר ובלי הכרעה | כן |
| BUB_UNSOURCED_FACT | בדיקה S1c, M2 | בועה שטוענת עובדה על מסמך או אירוע שלא נמסרו ("that is where the price was agreed"), בלי מקור ב-deal_documents שהתקבלו, ב-deal_context.facts או ב-fact_source | במצב משלוח (אזהרה במצב עבודה) |
| THEIR_NOTES_PARTIAL | בדיקה S1c, L6 | הערות לצוות של הצד שכנגד (בגוף ובהערות השוליים) שחלקן נמחקו וחלקן נשארו | לא |
| NOTICE_EMAIL_CONFLICT | S1d-R2, 13(ii) | נוסח שלנו שקובע הודעה בדוא"ל, כשסעיף ההודעות מוציא דוא"ל מ"בכתב" (ו"in writing" בסעיף סמוך) | לא |
| DEF_OUTDATED | S1d-R2, Data Protection Legislation | הגדרה (או נוסח שלנו) שמפנה לחוק או למועד שהוחלפו (STALE_MARKERS) | לא |
| CONSENT_REASONABLE_OURS | S1d 25.3 | "not unreasonably withheld" על הסכמה שלנו להגדלת החובות, העלויות או האחריות שלנו | לא |
| CAP_SUPER_UNCLEAR | S1e-R3, 18.4 | תקרה נוספת ("save that ... shall not exceed") בלי "in addition to" או "inclusive of" | לא |
| CAP_INSURANCE_GAP | S1e-R3, 18.3 מול 18.4 | הביטוח הנדרש והתקרה שמוצעת רחוקים זה מזה פי 2 ומעלה | לא |
| CAP_AGGREGATION_REMOVED | S1e-R3, 18.4 | נמחק מנגנון נגד צבירה של תקרות בין מסמכים ("calculated in the aggregate with") ולא הוחזר | לא |
| BUB_OFFER_UNSOURCED | S1d-R2, 11 | בועה שמייחסת לצד שכנגד הצעה ("As you offered", "כפי שהצעתם") בלי מקור בבועות או בסימונים שלו | לא |
| EXPLICIT_ANSWER_MISSING | S1d-R2 | הכרעה עם requires_explicit: true, בלי תשובה מפורשת של המשתמש (delegated, או בלי user_decision) | במצב משלוח (אזהרה במצב עבודה) |
| CONTAIN_TOPIC_NOT_EDITED | S3 | סעיף חדש (N1) מחיל עמדה בנושא שפסקה קיימת שלהם עוסקת בו או סותרת, והפסקה התקבלה כמו שהיא | במצב משלוח (אזהרה במצב עבודה) |
| CONTAIN_CONCESSION_UNDECIDED | S3 | ויתור על קו אדום (נוסח שלהם באדום, או ויתור מכוון בכלל קריטי או walk_away) בלי הכרעה מפורשת | במצב משלוח (אזהרה במצב עבודה) |
| RELATED_UNHANDLED | רף, 10 | הכרעה ששינתה סעיף, וסעיף קשור (אותו נוסח, אותו נושא, הפניה אליו, או כלל קשור בפלייבוק) נשאר בלי הכרעה ובלי רישום ב-dependents שהושאר בכוונה, עם reason | כן |
| POST_EDIT_CONTRADICTION | רף, 2 ו-10 | סעיף שלא שינינו, שנוסחו סותר משטר שהעריכה שלנו קבעה (נוסח קפוא מול "as updated", הגבלת ביקורת מול ביקורת "בכל עת", חריג בלאי מול "כל התיקונים", איסור צמצום מול זכות להפסיק) | במצב משלוח (אזהרה במצב עבודה) |
| DEF_USES_UNTRACED | רף, 10 | הכרעה שמשנה הגדרה, ושימושים במונח שלא קיבלו הכרעה או רישום ב-dependents | במצב משלוח (אזהרה במצב עבודה) |
| NO_APPROVED_SOURCE | כלל יסוד 5 | נושא רגיש (דין או פורום, חידוש או העלאת מחיר אוטומטיים, נטל מס, אחריות בלי תקרה, מידע מיוחד), או הפניה לחקיקה בשמה, שנשארו בלי הכרעה לפי כלל בפלייבוק; וכן כלל בגרעין שנושא `no_approved_source` (`no_source_note`) או `statutory_override` מסומן כך. פריט גלוי ללקוח, "AREO לא מצאה מקור מורשה לנקודה זו", עם צעד אחד הלאה. אינו חוסם ואינו ממלא מהזיכרון | לא |
| PLAYBOOK_MAP_MISSING, PLAYBOOK_RULE_NO_OUTCOME, PLAYBOOK_RULE_TWO_OUTCOMES, PLAYBOOK_OUTCOME_NO_POSITION, PLAYBOOK_OUTCOME_NO_CLAUSE, UNMATCHED_CLAUSE_NO_NOTICE | כלל יסוד 15 | מיפוי הפלייבוק להסכם (`meta.playbook_map`, `playbook_map.py`): סעיף בפלייבוק בלי תוצאה רשומה אחת בדיוק, או סעיף בהסכם בלי סעיף בפלייבוק ובלי ההודעה ללקוח | במצב משלוח (אזהרה במצב עבודה) |
| AREO_LABEL_MISSING | רף, 3 | הכרעה שמשנה נוסח בלי כלל בפלייבוק, שאינה מסומנת source_label: areo_proposal (במצב deal_only מספיקה כל תווית מקור) | במצב משלוח (אזהרה במצב עבודה) |
| DEF_CHANGED_USAGES | ארכיטקטורה 30.10, פרק 4(1) | הגדרה שתוקנה בפועל, ובבועה הפנימית של ההכרעה אין רשימת כל המופעים של המונח בנוסח המתקבל (`--definition-changes`, `--annotate-definitions`) | לא |
| INTERACTION_UNCHECKED, INTERACTION_OPEN_UNLISTED | 31.10, תנאי 2 | הכרעה שמשנה נוסח ונוגעת במשפחת מושגים (interaction_pairs.json), ופסקה בנוסח המתקבל במשפחה מזווגת שאין לה ערך ב-`interactions[]` של ההכרעה (`para`, `bypass`: no / fixed:<מזהה> / open, `answer`); או bypass פתוח שאינו ב-open_items (`decision_id`) | במצב משלוח (אזהרה במצב עבודה) |
| INTERACTION_MAP_MISSING | 31.10, תנאי 2 | interaction_pairs.json חסר או פגום | לא |
| DUPLICATE_MECHANISM | 31.10, תנאי 2 | ההכרעה מוסיפה מנגנון (ביקורת, עדכון מחיר, תקרה, חידוש) ובפסקה רחוקה יש מנגנון נוסף מאותו סוג | לא |
| BUBBLE_OVERCLAIM | 31.10, סעיף ז | בועה חיצונית עם טענה מוחלטת (הדדי, במלואו, כל, אין) כשה-`equivalence` של ההכרעה כולל narrower או `coverage: partial`; "הדדי" כשהנוסח שהוכנס אינו סימטרי חוסם | "הדדי" בלבד, במצב משלוח |
| NUMBER_UNSOURCED | 31.10, סעיף ה | אחוז, תקופה או סכום בנוסח שהכנסנו שאינם בגרעין, בתשובות הלקוח, בכרטיס העסקה או בהסכם שהתקבל (חריג: `number_source` בהכרעה) | במצב משלוח (אזהרה במצב עבודה) |

כלים נוספים כאן, לשכבת הבנייה ולמאמת: `scrub_client_text` (קודים פנימיים -> שם נושא או מחיקה, "סבב 1" -> "סבב ראשון"),
`paper_owner` (נייר שלנו / שלהם / תבנית, מסימנים בקובץ), `unit_counts` ו-`counts_line` (יחידת ספירה אחת לכל התוצרים),
ו-`validate_verify_findings` (`--validate-findings`: מבנה קובץ הממצאים של המאמת העצמאי, n9-verify.md).

הפונקציה `run_checks` מחזירה רשימת ממצאים `{code, message, where, blocking}`.
`qa_gate.py` מריץ אותה בשני המצבים: ממצא חוסם הוא כשל בשער, והעותק למשלוח
אינו מופק.

    python "AREO_RT/skills/contract-negotiation-orchestrator/scripts/content_checks.py" --work <קובץ העבודה> --received <הטיוטה> \\
        --decisions decisions_round_<N>.json [--state ...] [--core ...] [--manifest corpus-manifest.json]

קוד יציאה: **0** אין ממצא חוסם, **3** יש, **2** קלט חסר.
"""
import argparse
import io
import json
import os
import re
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # גם ב-python -I, שאינו מוסיף את תיקיית הסקריפט
import areo_lib  # noqa: F401  מוסיף את areolegal/lib לנתיב הייבוא

from lxml import etree  # noqa: E402

import common.docx_tracked as dt  # noqa: E402
import playbook_map as PM  # noqa: E402  מיפוי הפלייבוק להסכם (כלל יסוד 15)

W = dt.W
HERE = os.path.dirname(os.path.abspath(__file__))
HEB = re.compile(r"[֐-׿]")
LAT = re.compile(r"[A-Za-z]")

NEUTRALIZERS = ["יגברו", "מכריעים", "כמי שוויתר", "תתיישן", "לחלט", "לקזז", "שלטענתה", "זנח", "לא יושעו",
                "לאלתר", "ללא ספירה", "הסעד היחיד", "incorporated by reference", "conclusive",
                "sole and exclusive remedy", "deemed to have waived", "shall prevail"]
TBA = re.compile(r"יוסכ(?:ם|מו)(?![א-ת])|to be agreed|\bTBA\b|to be determined", re.I)
# מצג או התחייבות של החברה. בנוסח: פועל של מצג עם "that" או "hereby", או התחייבות לעמוד. בבועה: רק
# כשאנחנו מצהירים בה ("we confirm"). הסבר כמו "כדי שנוכל לעמוד בדין" אינו מצג
REPRESENT = re.compile(r"\b(?:represents?|warrants?|certif(?:y|ies)|confirms?)(?:\s+and\s+\w+)?\s+that\b|"
                       r"\bhereby\s+(?:represents?|warrants?|confirms?|certif(?:y|ies))\b|\bshall\s+comply\s+with\b|"
                       r"מצהיר(?:ה|ים)?\s+(?:כי|ש|בזאת)|מאשר(?:ת|ים)?\s+בזאת|מתחייב(?:ת|ים)?\s+לעמוד", re.I)
REPRESENT_BUBBLE = re.compile(r"\bwe\s+(?:represent|warrant|confirm|certify)\b|אנו\s+(?:מצהירים|מאשרים)|"
                              r"החברה\s+(?:מצהירה|מאשרת)", re.I)
CONFLICT_REP = re.compile(r"אין הסכם סותר|לא קיים הסכם (?:ה)?סותר|החברה גילתה|גילתה לצד|no conflicting agreement|"
                          r"has disclosed|is not (?:a )?party to any (?:other )?agreement", re.I)
EXHAUST = re.compile(r"מצה(?:ה|ים) את|מבטל(?:ים)? כל הסכם|כל ההסכמות|entire agreement|supersedes? (?:all|any) prior",
                     re.I)
PREVAILS = [re.compile(r"(?:הנספח|נספח|ההזמנה|הזמנת|הנוהל|נוהל|המדיניות|מדיניות|תנאי(?:ם)? (?:ה)?כללי|מסמך)[^.;]{0,70}"
                       r"(?:יגבר|יגברו|תגבר|תגברנה|יכריע|יכריעו)(?![^.;]{0,25}הסכם זה)"),
            re.compile(r"(?:annex|schedule|exhibit|appendix|order|statement of work|sow|policy|terms and conditions|"
                       r"purchase order)[^.;]{0,90}shall (?:prevail|govern|control)(?![^.;]{0,25}(?:this|the) agreement "
                       r"shall prevail)", re.I)]
INCOTERMS = re.compile(r"\b(EXW|FCA|FAS|FOB|CFR|CIF|CPT|CIP|DAP|DPU|DDP)\b")
CURRENCY = re.compile(r"ש\"ח|ש״ח|₪|\bNIS\b|\bILS\b|\bUSD\b|\$|€|\bEUR\b|דולר|יורו|הצמדה|צמוד|מדד|indexation|\bCPI\b",
                      re.I)
PRICE = re.compile(r"מחיר|מחירון|תעריף|תמורה|price|pricing|fee|tariff|rate card", re.I)
CONFORMING_ONLY = re.compile(r"^\s*(?:conforming change|תיקון עקבי|שינוי עקבי|התאמה)\s*[.]?\s*$", re.I)
COMPLIANCE = re.compile(r"bribery|corruption|FCPA|anti-?bribery|sanction|boycott|export control|money laundering|AML\b|"
                        r"שוחד|שחיתות|סנקציה|סנקציות|חרם|פיקוח על יצוא|יצוא בטחוני|הלבנת הון", re.I)
INTERNAL_HINT = re.compile(r"\b(internal|our client|client wants|between us|do not share|don'?t share|we can accept|"
                           r"fallback|walk.?away|bottom line|can live with)\b|פנימי|בינינו|הלקוח שלנו|הלקוח מוכן|"
                           r"אפשר לוותר|נוכל לוותר|מוכנים לוותר|עמדת נסיגה|לא להעביר|לא לשתף|נסתפק", re.I)
# כינויי הצדדים: אין רשימה בקוד. הכינויים הם מה שהפלייבוק רושם (company_role_code, ו-party_labels אם נרשמו),
# כטקסט חופשי בלשון המסמכים. בלי כינוי רשום, בדיקת PARTY_LABEL אינה רצה ואומרת זאת (אין עמדה)
PARTY_LABELS = ()


def party_labels(core):
    """הכינויים שהפלייבוק רושם לצדדים, עם ובלי ה' הידיעה."""
    core = core if isinstance(core, dict) else {}
    raw = [core.get("company_role_code")] + list(core.get("party_labels") or [])
    for f in core.get("contract_families") or []:
        if isinstance(f, dict):
            raw += [f.get("company_role_code")] + list(f.get("party_labels") or [])
    out = []
    for x in raw:
        x = str(x or "").strip()
        if x and x.lower() not in ("other", "mutual") and x not in out:
            out += [x] + (["ה" + x] if re.match(r"[א-ת]", x) else [])
    return out


# L5 (בדיקה עצמאית S1c): הפניה לסעיף בחוק או במסמך חיצוני ("section 123 of the Insolvency Act 1986", "סעיף 5 לחוק
# החוזים") אינה הפניה פנימית, ואינה נבדקת מול המספור של ההסכם
EXT_REF_EN = re.compile(r"^(?:\([^)]*\))*(?:\s*(?:,|and|or|to)\s*\d+(?:\.\d+)*(?:\([^)]*\))*)*\s*(?:of|under|in)\s+(?:the\s+)?"
                        r"(?:[A-Z][\w'’-]*\s+){0,8}?(?:Act|Regulations?|Law|Directive|Code|Order|Ordinance|Rules|Statute|"
                        r"Convention|Agreement|Contract)\b")
EXT_REF_HE = re.compile(r"^(?:\([^)]*\))*(?:\s*(?:,|ו|או|עד)\s*\d+(?:\.\d+)*(?:\([^)]*\))*)*\s*(?:ל|של\s+|ב)?"
                        r"(?:חוק|תקנות|פקודת|פקודה|צו|כללי|הסכם ה(?!זה))")
REF_HE = re.compile(r"(?<![א-ת])(?:ב|ל|מ|ו|ש)?סעי(?:ף|פים)\s+(\d+(?:\.\d+){0,4})")
REF_EN = re.compile(r"\b(?:Section|Clause|section|clause)s?\s+(\d+(?:\.\d+){0,4})")
ANNEX_HE = re.compile(r"(?<![א-ת])(?:ב|ל|מ|ו|ש)?נספח\s+([א-ת]['׳]?|\d+)(?![א-ת])")
ANNEX_EN = re.compile(r"\b(?:Annex|Schedule|Exhibit|Appendix)\s+([A-Z]|\d+)\b")
DEF_PATTERNS = [re.compile(r"\(\s*(?:להלן:?\s*|the\s+|hereinafter\s+)?[\"״“]([^\"״”]{2,50})[\"״”]"
                           r"(?:\s*(?:או|or)\s*[\"״“]([^\"״”]{2,50})[\"״”])?\s*\)"),
                re.compile(r"\(להלן:?\s*[\"״“]([^\"״”]{2,50})[\"״”]"),
                re.compile(r"[\"״“]([^\"״”]{2,50})[\"״”]\s*(?:-|פירושו|פירושה|משמעו|משמעה|יהיה פירושו)"),
                re.compile(r"[\"“]([A-Z][^\"”]{1,50})[\"”]\s+(?:means|shall mean|has the meaning)"),
                re.compile(r"\((?:the|hereinafter)?\s*[\"“]([A-Z][^\"”]{1,50})[\"”]\)")]


def finding(out, code, message, where="", blocking=False):
    out.append({"code": code, "message": message, "where": where, "blocking": bool(blocking)})


def load(path):
    if not path or not os.path.exists(path):
        return None
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------------------- מספור הסעיפים
def _roman(n):
    vals = ((10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i"))
    out = ""
    for v, s in vals:
        while n >= v:
            out, n = out + s, n - v
    return out


def _num_levels(path):
    """{numId: {ilvl: (lvlText, numFmt, start)}} מ-numbering.xml, כולל startOverride. בלי החלק: {}."""
    try:
        with zipfile.ZipFile(path) as z:
            root = etree.fromstring(z.read("word/numbering.xml"))
    except (KeyError, OSError, zipfile.BadZipFile, etree.XMLSyntaxError):
        return {}
    absn = {}
    for a in root.iter(W + "abstractNum"):
        lv = {}
        for l in a.iter(W + "lvl"):
            def val(tag, dflt):
                e = l.find(W + tag)
                return e.get(W + "val") if e is not None and e.get(W + "val") is not None else dflt
            lv[int(l.get(W + "ilvl") or 0)] = (val("lvlText", ""), val("numFmt", "decimal"), int(val("start", "1") or 1))
        absn[a.get(W + "abstractNumId")] = lv
    out = {}
    for n in root.iter(W + "num"):
        a = n.find(W + "abstractNumId")
        lv = dict(absn.get(a.get(W + "val") if a is not None else None) or {})
        for o in n.iter(W + "lvlOverride"):
            s = o.find(W + "startOverride")
            k = int(o.get(W + "ilvl") or 0)
            if s is not None and k in lv:
                lv[k] = (lv[k][0], lv[k][1], int(s.get(W + "val") or 1))
        out[n.get(W + "numId")] = lv
    return out


HE_LETTERS = "אבגדהוזחטיכלמנסעפצקרשת"
# מחבר הבועות הפנימיות, בעברית ובאנגלית
INTERNAL_AUTHORS = tuple(x for x in (dt.INTERNAL_AUTHOR, getattr(dt, "INTERNAL_AUTHOR_EN", None),
                                     "Internal, delete before sending") if x)


def _hebrew_numeral(n):
    """hebrew1 של Word: מספר בגימטריה. 11 = יא, 15 = טו, 16 = טז, 20 = כ, 101 = קא."""
    out = ""
    while n >= 400:
        out, n = out + "ת", n - 400
    for v, ch in ((300, "ש"), (200, "ר"), (100, "ק"), (90, "צ"), (80, "פ"), (70, "ע"), (60, "ס"), (50, "נ"),
                  (40, "מ"), (30, "ל"), (20, "כ"), (10, "י")):
        if n >= v:
            out, n = out + ch, n - v
    if n in (15, 16):
        return out + ("טו" if n == 15 else "טז")
    if out.endswith("י") and n in (5, 6):
        return out[:-1] + ("טו" if n == 5 else "טז")
    return out + ("" if not n else HE_LETTERS[n - 1])


def _fmt_num(n, fmt):
    if fmt == "hebrew1" and n > 0:
        return _hebrew_numeral(n)
    if fmt == "hebrew2" and n > 0:
        # אלפבית: א..ת, ואחרי ת האות כפולה (אא, בב)
        return HE_LETTERS[(n - 1) % 22] * ((n - 1) // 22 + 1)
    if fmt in ("lowerLetter", "upperLetter") and 0 < n <= 26:
        c = chr(96 + n)
        return c.upper() if fmt == "upperLetter" else c
    if fmt in ("lowerRoman", "upperRoman"):
        r = _roman(n)
        return r.upper() if fmt == "upperRoman" else r
    return str(n)


def numbered_labels(path):
    """המספר של כל פסקת גוף: מספר מוקלד בראש הפסקה, או מספור אוטומטי לפי numId ו-ilvl.
    numId "0" פירושו בלי מספור (OOXML), ואינו נספר כרשימה. פסקה שנפתחת בתת-סעיף מוקלד, "(a)" או "(ii)", מקבלת את
    הסעיף שמעליה ואת התת-סעיף, למשל "15.5(a)" או "15.2(b)(i)". רשימה אוטומטית מתחת לסעיף שמספרו מוקלד מקבלת את
    הסעיף ואותיות ברמה הראשונה וספרות רומיות בשנייה (S1h-RISK: 15.5(a) קיבל "20", ו-15.2(a) קיבל "1")."""
    root = dt.document_root(path)
    paras = dt.body_paragraphs(root)
    texts = [dt.para_text(p).strip() for p in paras]
    counters, bases, out = {}, {}, []
    parent, letter, roman_list, typed_parent = None, None, False, False
    last_at_level = {}   # התווית האחרונה של כל רמת מספור אוטומטי: ההורה של "(a)" מתחת ל-2.6 הוא 2.6, ולא 2
    roman = re.compile(r"^(?:i|ii|iii|iv|v|vi|vii|viii|ix|x|xi|xii)$")
    levels = _num_levels(path)
    sub_rx = re.compile(r"^\(([a-z]{1,4})\)\s")
    # תת-סעיף מוקלד בעברית: "(ד) ..." או "ד. ..." מתחת לסעיף שמספרו מוקלד, למשל 14(ד)
    sub_he = re.compile(r"^(?:\(([א-ת]{1,2})\)|([א-ת]{1,2})[.)])\s")

    def next_sub(i):
        for t in texts[i + 1:i + 4]:
            m2 = sub_rx.match(t)
            if m2:
                return m2.group(1)
        return None

    for i, p in enumerate(paras):
        text = texts[i]
        m = re.match(r"^(\d+(?:\.\d+){0,4})[.)]?\s", text)
        if m:
            out.append(m.group(1))
            parent, letter, roman_list, typed_parent = m.group(1), None, False, True
            counters = {k: v for k, v in counters.items() if not k.startswith("under:")}
            last_at_level = {}
            continue
        she = sub_he.match(text)
        if she and parent:
            out.append("%s(%s)" % (parent, she.group(1) or she.group(2)))
            continue
        sub = sub_rx.match(text)
        if sub and parent:
            s = sub.group(1)
            # "(i)" אחרי "(h)" הוא האות i, אלא אם מיד אחריו בא "(ii)"
            is_roman = bool(roman.match(s)) and not (s == "i" and letter == "h" and next_sub(i) != "ii")
            if is_roman and letter and not roman_list:
                out.append("%s(%s)(%s)" % (parent, letter, s))
            else:
                letter, roman_list = s, is_roman
                out.append("%s(%s)" % (parent, s))
            continue
        num = p.find(W + "pPr/" + W + "numPr")
        nid = num.find(W + "numId") if num is not None else None
        nid = nid.get(W + "val") if nid is not None else None
        if num is not None and nid not in (None, "0"):
            lvl = num.find(W + "ilvl")
            lvl = int(lvl.get(W + "val")) if lvl is not None else 0
            key = ("under:%s:%s" % (parent, nid)) if typed_parent and parent else nid
            c = counters.setdefault(key, [0] * 9)
            lv = levels.get(nid) or {}
            fmt = (lv.get(lvl) or ("", "decimal", 1))[0]
            # רמה עליונה שלא הופיעה עדיין ברשימה, והמספר של הרמה הזו מציג אותה ("%1.%2."), מוצגת בערך ההתחלה שלה,
            # ו-Word ממשיך ממנו: פריט ברמה 1 לפני כל פריט ברמה 0 הוא "1.1", והפריט הבא ברמה 0 הוא "2", ולא "1"
            for j in range(lvl):
                if c[j] == 0 and (not fmt or "%%%d" % (j + 1) in fmt):
                    c[j] = (lv.get(j) or ("", "decimal", 1))[2]
            c[lvl] = c[lvl] + 1 if c[lvl] else (lv.get(lvl) or ("", "decimal", 1))[2]
            for j in range(lvl + 1, 9):
                c[j] = 0
            base = bases.setdefault(key, lvl)
            if lvl < base:
                base = bases[key] = lvl
            rel = lvl - base
            if typed_parent and parent and rel <= 1:
                a0, a1 = c[base], c[base + 1] if base + 1 < 9 else 0
                bfmt = (lv.get(base) or ("", "decimal", 1))[1]
                lab = "%s(%s)" % (parent, _fmt_num(a0, bfmt) if bfmt not in ("decimal", "") else
                                  chr(96 + a0) if 0 < a0 <= 26 else a0)
                out.append(lab + ("(%s)" % _roman(a1) if rel == 1 and a1 else ""))
            else:
                if fmt and re.search(r"%\d", fmt):
                    label = re.sub(r"%(\d)", lambda m: _fmt_num(c[int(m.group(1)) - 1],
                                                                (lv.get(int(m.group(1)) - 1) or ("", "decimal"))[1]),
                                   fmt).strip().rstrip(".)").lstrip("(")
                else:
                    label = ".".join(str(x) for x in c[:lvl + 1] if x)
                # רמה פנימית שהתבנית שלה מציגה רק את עצמה ("%2." או "(%2)"): הסעיף שמעליה נכנס לתווית, 14(ד) ולא 4.
                # הסעיף שמעליה הוא התווית האחרונה ברמה שמעל (2.6 מעל "(a)"), ולא בהכרח סעיף הרמה העליונה (2)
                if lvl > 0 and parent and fmt and not any("%%%d" % (j + 1) in fmt for j in range(lvl)):
                    above = next((last_at_level[j] for j in range(lvl - 1, -1, -1) if last_at_level.get(j)), parent)
                    label = "%s(%s)" % (above, label)
                out.append(label)
                last_at_level[lvl] = label
                for j in range(lvl + 1, 9):
                    last_at_level.pop(j, None)
                if lvl == 0:
                    parent, letter, roman_list, typed_parent = label, None, False, False
        else:
            out.append(None)
    return out


PARTY_DEF = re.compile(r"\(\s*(?:להלן|ולהלן|hereinafter|the|הלן)?:?\s*(?:referred to as\s*)?(?:the\s+)?[\"״“']"
                       r"([^\"״”']{2,40})[\"״”']\s*\)", re.I)


def document_sides(path, our_names=(), their_names=(), role_side=None):
    """הצד שלנו לפי המסמך עצמו, כמו ב-CLM, ולא לפי הפלייבוק: הגדרות הצדדים בפתיח ('(להלן: "<תפקיד>")',
    '("<תפקיד>")'), והשם שמופיע לפני כל הגדרה (באותה פסקה או בשתי הפסקאות שלפניה). role_side: פונקציה שמחזירה צד
    מנורמל לתווית (resolve_playbook.role_side; בלי מיפוי לצד "נותן" או "מקבל"). מחזיר {ours, theirs, our_term, their_term, basis}, ו-ours None כשהמסמך
    אינו מכריע (אין שם מוכר, או אין תפקיד מוכר בהגדרה)."""
    texts = [t.strip() for t in dt.received_paragraphs(path)]
    # רק הפתיח: עד הסעיף הממוספר הראשון (הגדרות כמו "Recipient" בסעיף הסודיות אינן הצדדים להסכם)
    try:
        first = next((i for i, x in enumerate(numbered_labels(path)) if x), None)
    except Exception:  # noqa: BLE001
        first = None
    texts = texts[:max(first or 0, 3) if first is not None else 15][:40]
    norm = lambda s: re.sub(r"[\s\"״'”“׳.,]+", " ", str(s or "")).strip().lower()  # noqa: E731
    ours_n = [norm(n) for n in our_names if n and len(norm(n)) >= 3]
    theirs_n = [norm(n) for n in their_names if n and len(norm(n)) >= 3]
    defs = []
    for i, t in enumerate(texts):
        for m in PARTY_DEF.finditer(t):
            term = m.group(1).strip()
            side = role_side(term) if role_side else None
            if side == "mutual":
                side = None
            before = t[:m.start()]
            block = before if len(before.strip()) >= 3 else " ".join(texts[max(0, i - 2):i]) + " " + before
            defs.append({"term": term, "side": side, "block": norm(block)[-300:]})
    if not defs:
        return {"ours": None, "basis": "no_party_definitions"}

    def owner(d):
        if any(n in d["block"] for n in ours_n):
            return "ours"
        if any(n in d["block"] for n in theirs_n):
            return "theirs"
        return None
    sided = [d for d in defs if d["side"]]
    our_d = next((d for d in defs if owner(d) == "ours"), None)
    their_d = next((d for d in defs if owner(d) == "theirs"), None)
    if our_d and our_d["side"]:
        return {"ours": our_d["side"], "our_term": our_d["term"], "basis": "our_name"}
    if their_d:
        rest = [d for d in sided if d["term"] != their_d["term"]]
        if len({d["side"] for d in rest}) == 1:
            return {"ours": rest[0]["side"], "our_term": rest[0]["term"], "basis": "other_party"}
    return {"ours": None, "basis": "names_not_found"}


PLACE_WORDS = {"he": {"pre": "המבוא", "after": "אחרי סעיף %s", "in": "%s", "sign": "החתימות"},
               "en": {"pre": "Preamble", "after": "After clause %s", "in": "%s", "sign": "Signatures"}}
SIGN_RX = re.compile(r"ולראיה|על החתום|in witness whereof|signature", re.I)


def place_labels(path, lang="he", labels=None):
    """לכל פסקה בלי מספר סעיף: מקום שהלקוח מוצא ב-Word, ולא "פסקה 8". לפני הסעיף הממוספר הראשון: "המבוא". אחרי
    שורת החתימות: כותרת המסמך המצורף (פסקה קצרה בלי נקודה בסוף), ובלעדיה "החתימות". אחרת: "אחרי סעיף N". לפסקה
    ממוספרת: None."""
    L = PLACE_WORDS["en" if str(lang or "").lower()[:2] == "en" else "he"]
    root = dt.document_root(path)
    texts = [dt.para_text(p).strip() for p in dt.body_paragraphs(root)]
    labels = labels if labels is not None else numbered_labels(path)
    out, last, signed, title, head_body = [], None, False, None, False
    for t, lab in zip(texts, labels):
        if lab:
            last = lab
            out.append(None)
            # סעיף שהפסקה הממוספרת שלו היא כותרת בלבד (קצרה, בלי סוף משפט): הפסקאות הבאות בלי מספר הן גוף הסעיף,
            # ונקראות בשם הסעיף ("9"), ולא "אחרי סעיף 9"
            head_body = 0 < len((t or "").strip()) <= 80 and not re.search(r"[.;:,]\s*$", (t or "").strip()) \
                and not re.search(r"[.;:]\s", (t or "").strip())
            continue
        if head_body and last and (t or "").strip() and not SIGN_RX.search(t or ""):
            out.append(L["in"] % last)
            continue
        head_body = False
        if last and SIGN_RX.search(t or ""):
            signed, title = True, None
        elif signed and title is None and 8 <= len(t or "") <= 90 and "\t" not in t \
                and not t.endswith((".", ":", ",")) and not re.search(r"_{3,}|\.{3,}|…", t):
            # "<הליך> מס' 123 - נוסח ערבות ביצוע": השם הוא החלק האחרון
            tail = t.split(" - ")[-1].strip()
            title = tail if len(tail) >= 6 else t
        if last is None:
            out.append(L["pre"])
        elif signed:
            out.append(title or L["sign"])
        else:
            out.append(L["after"] % last)
    return out


# כותרת של תוספת או נספח (S1d-R2, 28.10.2026): פסקאות התוספת ממוספרות מחדש (1, 2, 3), ובטבלת "לאישורך" ובמפת
# הסעיפים הן נקראו "סעיף 2" ו"סעיף 4". כותרת היא פסקה קצרה שנפתחת במילה ובמזהה, ולא משפט שמפנה לתוספת
SCHEDULE_HEAD = (re.compile(r"^(Schedule|SCHEDULE|Annex|ANNEX|Appendix|APPENDIX|Exhibit|EXHIBIT|Attachment|ATTACHMENT)"
                            r"\s+([A-Z]|\d+(?:\.\d+)*|[IVX]+)\b"),
                 re.compile(r"^(תוספת|נספח)\s+([א-ת]['׳]?|\d+(?:\.\d+)*)(?![א-ת])"))


def _body_restart(paras, labels):
    """הפסקה שבה גוף ההסכם הממוספר מתחיל אחרי הנספחים, או None. בנייר שבו הסעיפים הממוספרים באים אחרי דף הפתיחה
    והנספחים (אין אף סעיף ממוספר לפני כותרת הנספח הראשונה), רצף המספור העליון הארוך ביותר שנפתח ב"1" אחרי כותרת
    נספח הוא גוף ההסכם, ולא חלק מהנספח שלפניו. רצף של שלושה סעיפים עליונים לפחות."""
    if not labels:
        return None
    first_head = next((i for i, t in enumerate(paras) if _schedule_head((t or "").strip())), None)
    if first_head is None or any(labels[i] for i in range(min(first_head, len(labels)))):
        return None
    best, best_n = None, 0
    i = first_head
    while i < len(labels):
        if labels[i] == "1":
            n, j = 0, i
            while j < len(labels) and not _schedule_head((paras[j] or "").strip()):
                if labels[j] and re.match(r"^\d+$", str(labels[j])):
                    n += 1
                j += 1
            if n > best_n:
                best, best_n = i, n
            i = j
        else:
            i += 1
    return best if best_n >= 3 else None


def _schedule_head(s):
    if len(s) <= 80 and not s.endswith(".") and not re.search(r"(\t|\.{3,}|…)\s*\d+$", s):
        return SCHEDULE_HEAD[0].match(s) or SCHEDULE_HEAD[1].match(s)
    return None


def schedule_of_paragraphs(paras, labels=None):
    """לכל פסקה (טקסט): (המילה, המזהה) של התוספת או הנספח שהיא בתוכו, לפי הכותרת האחרונה שלפניה, או None בגוף
    ההסכם. פסקת הכותרת עצמה שייכת לתוספת שלה. שורה בתוכן העניינים (טאב ומספר עמוד בסוף) אינה כותרת.
    labels (numbered_labels): כשגוף ההסכם הממוספר בא אחרי הנספחים, הוא חוזר להיות גוף (_body_restart)."""
    out, cur = [], None
    restart = _body_restart(paras, labels)
    for i, t in enumerate(paras):
        s = (t or "").strip()
        if restart is not None and i == restart:
            cur = None
        m = _schedule_head(s)
        if m:
            cur = (m.group(1)[:1].upper() + m.group(1)[1:].lower() if m.group(1)[0].isascii() else m.group(1),
                   m.group(2).replace("׳", "'"))
        out.append(cur)
    return out


def annex_names(paras):
    names = set()
    for t in paras:
        s = t.strip()
        m = re.match(r"^נספח\s+([א-ת]['׳]?|\d+)(?![א-ת])", s) or re.match(r"^(?:Annex|Schedule|Exhibit|Appendix)\s+([A-Z]|\d+)\b", s)
        if m:
            names.add(m.group(1).replace("׳", "'"))
    return names


# --------------------------------------------------------------------------- טקסט מוסתר
def hidden_scan(path):
    """כל חלקי החבילה: גוף, כותרות, הערות שוליים וסיום, בועות ותיבות טקסט, ומאפייני הקובץ.
    לכל ממצא: חלק, מספר פסקה בחלק, טקסט, ואופן ההסתרה (vanish, specVanish, צבע, גודל)."""
    out = []
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        for name in names:
            if not re.match(r"^word/(document|header\d*|footer\d*|footnotes|endnotes|comments)\.xml$", name):
                continue
            root = etree.fromstring(z.read(name))
            for pi, p in enumerate(root.iter(W + "p")):
                for r in p.iter(W + "r"):
                    rpr = r.find(W + "rPr")
                    if rpr is None:
                        continue
                    text = "".join(t.text or "" for t in r.iter(W + "t", W + "delText"))
                    if not text.strip():
                        continue
                    how = []
                    for tag in ("vanish", "specVanish", "webHidden"):
                        el = rpr.find(W + tag)
                        if el is not None and el.get(W + "val") not in ("0", "false"):
                            how.append(tag)
                    col = rpr.find(W + "color")
                    if col is not None and str(col.get(W + "val", "")).upper() in ("FFFFFF", "FEFEFE", "FDFDFD", "FCFCFC"):
                        how.append("color")
                    sz = rpr.find(W + "sz")
                    if sz is not None and str(sz.get(W + "val", "99")).isdigit() and int(sz.get(W + "val")) <= 2:
                        how.append("font_size")
                    if how:
                        out.append({"part": name, "paragraph": pi, "text": text, "how": ",".join(how)})
        for name in names:
            if name.startswith("customXml/item") and name.endswith(".xml") or name == "docProps/custom.xml":
                txt = re.sub(r"<[^>]+>", " ", z.read(name).decode("utf-8", "ignore"))
                txt = re.sub(r"\s+", " ", txt).strip()
                if len(txt) > 20:
                    out.append({"part": name, "paragraph": None, "text": txt[:300], "how": "properties"})
    return out


# --------------------------------------------------------------------------- בועות שלהם
def comment_info(path):
    """הבועות בקובץ: id, author, text, paraId של הפסקה הראשונה, והאם יש להן מענה בשרשור. מענה הוא תשובה לבועה עצמה,
    או, לבועה שהיא תשובה בשרשור, רשומה מאוחרת יותר באותו שרשור של מחבר אחר (S1e-R3: Word מצמיד כל תשובה לשורש
    השרשור, ולכן תשובה של עורכת הדין לבועות 179 עד 182, שנכתבה בסבב 2 בקובץ שנשלח, לא נספרה)."""
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        if "word/comments.xml" not in names:
            return []
        root = etree.fromstring(z.read("word/comments.xml"))
        ext = etree.fromstring(z.read("word/commentsExtended.xml")) if "word/commentsExtended.xml" in names else None
    W14 = "{http://schemas.microsoft.com/office/word/2010/wordml}"
    W15 = "{http://schemas.microsoft.com/office/word/2012/wordml}"
    parents = {}
    if ext is not None:
        for e in ext.iter(W15 + "commentEx"):
            if e.get(W15 + "paraIdParent"):
                parents[e.get(W15 + "paraId")] = e.get(W15 + "paraIdParent")
    out = []
    for c in root.iter(W + "comment"):
        ps = list(c.iter(W + "p"))
        pid = ps[-1].get(W14 + "paraId") if ps else None
        out.append({"id": c.get(W + "id"), "author": c.get(W + "author") or "", "paraId": pid,
                    "date": c.get(W + "date"),
                    "text": " ".join("".join(t.text or "" for t in p.iter(W + "t")) for p in ps).strip(),
                    "parent": parents.get(pid)})
    replied = {c["parent"] for c in out if c.get("parent")}
    for k, c in enumerate(out):
        c["has_reply"] = c["paraId"] in replied or bool(c.get("parent")) and any(
            x.get("parent") == c["parent"] and x["author"] != c["author"] and (k2 > k or (
                x.get("date") and c.get("date") and x["date"] > c["date"])) for k2, x in enumerate(out))
    return out


# --------------------------------------------------------------------------- הבדיקות
def our_texts(decisions):
    out = []
    for d in decisions or ():
        for k in ("new_text", "new", "text"):
            if d.get(k):
                out.append((d, d[k]))
    return out


def run_checks(work, received, decisions, state=None, core=None, manifest=None, profile=None, mode=None):
    """הבדיקות על קובץ העבודה מול הטיוטה שהתקבלה. decisions: רשימת ההכרעות. mode: work או send (בלעדיו כמו send):
    ממצא שחוסם רק משלוח (BUB_UNSOURCED_FACT) הוא אזהרה במצב עבודה."""
    out = []
    state = state or {}
    meta = state.get("meta") or {}
    decisions = decisions or []
    accepted = dt.accept_all(work)
    theirs = dt.received_paragraphs(received)
    whole = "\n".join(accepted)
    labels = numbered_labels(work)
    existing_refs = {x for x in labels if x}
    annexes = annex_names(accepted)
    touched = {d.get("para") for d in decisions if d.get("para") is not None} | \
              {d.get("after_para") for d in decisions if d.get("after_para") is not None}
    by_para = {}
    for d in decisions:
        if d.get("para") is not None:
            by_para.setdefault(d["para"], []).append(d)

    # 19, 39: הפניות
    for i, t in enumerate(accepted):
        for rx, kind in ((REF_HE, "sec"), (REF_EN, "sec"), (ANNEX_HE, "annex"), (ANNEX_EN, "annex")):
            for m in rx.finditer(t):
                target = m.group(1).replace("׳", "'")
                # סעיף בחוק או במסמך חיצוני (L5), גם כששם החוק עובר לפסקה הבאה ("section 123 of" / "the Insolvency Act")
                tail = t[m.end():] + " " + (accepted[i + 1] if i + 1 < len(accepted) else "")
                if kind == "sec" and (EXT_REF_EN.match(tail) or EXT_REF_HE.match(tail)):
                    continue
                ok = target in existing_refs if kind == "sec" else target in annexes
                if kind == "sec" and not existing_refs:
                    ok = True   # אין מספור שאפשר לשחזר: הבדיקה אינה רצה כאן
                if not ok:
                    ours = any(m.group(0) in txt for _, txt in our_texts(decisions))
                    finding(out, "CON_REF_MISSING", "הפניה ל%s %s, ואין לה יעד בנוסח המתקבל" %
                            ("סעיף" if kind == "sec" else "נספח", target), "פסקה %d" % i, blocking=ours)
    # מונחים מוגדרים
    defined = {}
    for i, t in enumerate(accepted):
        for rx in DEF_PATTERNS:
            for m in rx.finditer(t):
                for g in m.groups():
                    if g:
                        defined.setdefault(g.strip(), i)
    for term, at in defined.items():
        # "הקונה" נכתב בטקסט גם "לקונה" או "בקונה": ה' הידיעה נבלעת אחרי אות השימוש
        stem = term[1:] if term.startswith("ה") and len(term) > 3 else term
        if stem != term:
            trx = re.compile(r"(?<![א-ת])[ולבכמש]{0,2}ה?" + re.escape(stem) + r"(?![א-ת])")
        else:
            trx = re.compile(re.escape(term))
        uses = [i for i, t in enumerate(accepted) if trx.search(t)]
        if uses and uses[0] < at:
            finding(out, "CON_TERM_BEFORE_DEF", "המונח \"%s\" משמש לפני שהוגדר" % term, "פסקה %d" % uses[0])
        if len([i for i in uses if i != at]) == 0 and len(trx.findall(whole)) <= 1:
            finding(out, "CON_TERM_UNUSED", "המונח \"%s\" מוגדר ואינו בשימוש" % term, "פסקה %d" % at)
    # 39: "יוסכם" בנוסח שלנו
    for d, txt in our_texts(decisions):
        if TBA.search(txt):
            finding(out, "CON_TBA", "בנוסח שהכנסנו נשאר \"%s\": אין הסכמה על עניין שנשאר להסכמה" % TBA.search(txt).group(0),
                    d.get("id"), blocking=True)
    # 19: פסקאות בנספחים שחולקות מונח או מספר עם פסקה שתוקנה
    annex_start = next((i for i, t in enumerate(accepted) if re.match(r"^\s*(?:נספח|Annex|Schedule|Exhibit|Appendix)\s",
                                                                       t)), None)
    if annex_start is not None:
        for d in decisions:
            p = d.get("para")
            if p is None or p >= annex_start or p >= len(accepted):
                continue
            keys = set(re.findall(r"[\"״“]([^\"״”]{2,40})[\"״”]", accepted[p])) | set(re.findall(r"\d+(?:\.\d+)+",
                                                                                              accepted[p]))
            for j in range(annex_start, len(accepted)):
                if j not in touched and any(k in accepted[j] for k in keys):
                    finding(out, "CON_ANNEX_SHARED", "פסקה בנספח חולקת מונח או מספר עם הכרעה %s: לבדוק שהיא עקבית"
                            % d.get("id"), "פסקה %d" % j)
    # 19, 23: תשובות הלקוח
    for a in state.get("client_answers") or []:
        # תשובה שאינה על סעיף (כרטיס העסקה, הגישה, רכיבים משלימים) נרשמת בלי clause_ids (n2-questions.md): רק status
        # חובה, ותשובה שיושמה בנוסח (applied) צריכה גם clause_ids
        if not a.get("status") or (a.get("status") == "applied" and not a.get("clause_ids")):
            finding(out, "CON_CLIENT_ANSWER", "רשומה ב-client_answers בלי status, או תשובה שיושמה בנוסח בלי clause_ids",
                    a.get("question", ""), blocking=True)
        elif a.get("status") == "applied" and a.get("value") and str(a["value"]) not in whole:
            finding(out, "CON_CLIENT_ANSWER", "התשובה \"%s\" יושמה, אבל אינה בנוסח המתקבל" % a["value"],
                    ", ".join(a["clause_ids"]), blocking=True)
    # 23: נספח שגובר על ההסכם
    for i, t in enumerate(accepted):
        for rx in PREVAILS:
            m = rx.search(t)
            if m:
                finding(out, "PREC_ANNEX_PREVAILS", "נשאר סעיף שקובע שמסמך אחר גובר על ההסכם: \"%s\"" % m.group(0)[:80],
                        "פסקה %d" % i, blocking=True)
    for c in ((meta.get("deal_documents") or state.get("deal_documents") or {}).get("conflicts") or []):
        if not c.get("decision"):
            finding(out, "DEAL_DOCS_CONFLICT", "סתירה בין מסמכי העסקה בלי הכרעה: %s" % c.get("conflict", ""),
                    ", ".join(c.get("documents") or []), blocking=True)
    # 24: מנטרלים בנוסח שנשאר בלי שינוי
    for i, t in enumerate(accepted):
        if i in touched or i >= len(theirs) or t != theirs[i]:
            continue
        for w in NEUTRALIZERS:
            if w.lower() in t.lower():
                finding(out, "NEUTRALIZER", "ביטוי מנטרל בנוסח שלא שונה: \"%s\". להכריע בו" % w, "פסקה %d" % i)
    # 26: מצגים
    reps = {r.get("clause_id"): r for r in state.get("company_representations") or []}
    for d, txt, rx in [(d, t, REPRESENT) for d, t in our_texts(decisions)] + \
            [(d, d.get("external_comment") or "", REPRESENT_BUBBLE) for d in decisions]:
        m = next((x for x in rx.finditer(txt or "")
                  if not (rx is REPRESENT and _rep_by_them(txt, x.start(), state))), None)
        if not m:
            continue
        rec = reps.get(d.get("clause_id")) or reps.get(d.get("id"))
        bracketed = bool(re.search(r"\[[^\]]*" + re.escape(m.group(0)) + r"[^\]]*\]", txt))
        if not bracketed and not (rec and rec.get("status") in ("confirmed", "approved")):
            finding(out, "REP_UNAPPROVED", "מצג או התחייבות (\"%s\") בנוסח שלנו בלי רשומה מאושרת ב-company_representations,"
                    " ולא בסוגריים מרובעים" % m.group(0), d.get("id"), blocking=True)
    # 27: בדיקת התנגשות
    dc = meta.get("deal_context") or {}
    # בדיקת ההתנגשות רשומה ב-meta.deal_context.existing_agreements_with_counterparty (גם רשימה ריקה היא
    # בדיקה שנעשתה), כמו בסכמה
    conflict_done = "existing_agreements_with_counterparty" in dc or bool((dc.get("conflict_check") or {}).get("done"))
    for d, txt in our_texts(decisions):
        if CONFLICT_REP.search(txt) and not conflict_done:
            finding(out, "CONFLICT_CHECK", "מצג \"%s\" בלי בדיקת התנגשות רשומה (conflict_check)" %
                    CONFLICT_REP.search(txt).group(0), d.get("id"), blocking=True)
    if EXHAUST.search(whole):
        for e in dc.get("existing_agreements_with_counterparty") or state.get("existing_agreements_with_counterparty") or []:
            if e.get("in_force", True) and not e.get("effect_of_new_agreement"):
                finding(out, "EXISTING_AGREEMENT", "יש סעיף מיצוי או ביטול הסכמים קודמים, וההסכם הקיים \"%s\" בלי השפעה "
                        "רשומה" % (e.get("name") or e.get("file") or ""), "")
    # 28: שם של צד מהסכם אחר בבועה
    others = set()
    for doc in (manifest or {}).get("documents") or []:
        for k in ("counterparty", "parties"):
            v = doc.get(k)
            for name in (v if isinstance(v, list) else [v]):
                if name and len(str(name)) >= 3:
                    others.add(str(name))
    current = str(meta.get("counterparty_name") or "")
    for d in decisions:
        bub = d.get("external_comment") or ""
        for name in others:
            if name in bub and not (current and (name in current or current in name)):
                finding(out, "OTHER_PARTY_NAME", "בבועה החיצונית שם של צד מהסכם אחר: \"%s\"" % name, d.get("id"),
                        blocking=True)
    # 32: תנאי מסירה, מטבע והצמדה
    price_paras = {i for i, t in enumerate(accepted) if annex_start is not None and i >= annex_start and PRICE.search(t)}
    for d, txt in our_texts(decisions):
        if (INCOTERMS.search(txt) or CURRENCY.search(txt)) and price_paras and not (touched & price_paras):
            finding(out, "PRICE_TERMS", "התיקון משנה תנאי מסירה, מטבע או הצמדה, ונספח המחירים לא שונה", d.get("id"))
        if CONFORMING_ONLY.match(d.get("external_comment") or "x") and (PRICE.search(txt) or CURRENCY.search(txt)):
            finding(out, "PRICE_CONFORMING", "בועה \"תיקון עקבי\" בלבד על שינוי שנוגע במחיר", d.get("id"), blocking=True)
    # 34: ציות
    for i, t in enumerate(theirs):
        if not COMPLIANCE.search(t):
            continue
        ds = by_para.get(i) or []
        # תשובה מפורשת בהכרעה עצמה, או ב-user_decisions של קובץ המצב שחלה על הסעיף (decide --applies-to)
        ok = any(((d.get("user_decision") or {}).get("answer_kind") == "explicit") or
                 (d.get("decision_required") or {}).get("required") or _explicit_on(d, state or {}) for d in ds)
        if not ok:
            finding(out, "COMPLIANCE", "סעיף ציות (\"%s\") בלי הכרעה מפורשת של המשתמש" % COMPLIANCE.search(t).group(0),
                    "פסקה %d" % i, blocking=True)
    # 44: הסכם דו-לשוני
    bil = meta.get("bilingual") or {}
    he = sum(1 for t in theirs if len(HEB.findall(t)) > len(LAT.findall(t)) and len(t) > 30)
    en = sum(1 for t in theirs if len(LAT.findall(t)) > len(HEB.findall(t)) and len(t) > 30)
    detected = he >= 5 and en >= 5 and min(he, en) >= 0.3 * max(he, en)
    if detected and not bil.get("is_bilingual"):
        finding(out, "BILINGUAL_UNDECLARED", "ההסכם נראה דו-לשוני (%d פסקאות בעברית, %d באנגלית), ו-meta.bilingual אינו"
                " מסמן זאת" % (he, en), "", blocking=True)
    if bil.get("is_bilingual"):
        pairs = {int(k): int(v) for k, v in (bil.get("map") or {}).items()}
        pairs.update({v: k for k, v in list(pairs.items())})
        for d in decisions:
            p = d.get("para")
            if p is None or d.get("op") in ("accept", "comment_only"):
                continue
            mate = pairs.get(p)
            if mate is None or not by_para.get(mate):
                finding(out, "BILINGUAL_ONE_SIDE", "הכרעה שמשנה נוסח בגרסה אחת בלבד", d.get("id"), blocking=True)
        for mm in bil.get("mismatches") or []:
            if not mm.get("decision"):
                finding(out, "BILINGUAL_MISMATCH", "סתירה בין הגרסאות בלי הכרעה: %s" % mm.get("difference", ""),
                        mm.get("clause_ref_a", ""), blocking=True)
    # 1: התאמת הפלייבוק, ומפת המונחים
    res = state.get("playbook_resolution") or {}
    match = res.get("playbook_match") or meta.get("playbook_match")
    if match in ("side_mismatch", "family_mismatch", "mutuality_mismatch"):
        finding(out, "POSITION_MISMATCH", "הפלייבוק שהוחל אינו מתאים להסכם (%s)" % match, "", blocking=True)
    received_text = "\n".join(theirs)
    for d, txt in our_texts(decisions):
        for lab in (list(PARTY_LABELS) + party_labels(core)):
            # "Customer Data" הוא מונח מוגדר, ולא הכינוי של צד: מילה באות גדולה אחרי הכינוי מחברת אותו למונח
            rx = r"(?<![\w֐-׿'])" + re.escape(lab) + r"(?![\w֐-׿])(?!\s+[A-Z])(?!'s)"
            if re.search(rx, txt) and lab not in received_text:
                finding(out, "PARTY_LABEL", "בנוסח שלנו הכינוי \"%s\", שאינו בהסכם: הנוסח לא עבר את מפת המונחים" % lab,
                        d.get("id"), blocking=True)
    # 59: סימני האדום
    rule_decided = {}
    for d in decisions:
        for r in d.get("rule_ids") or []:
            rule_decided.setdefault(r, set()).update({d.get("para"), d.get("after_para")})
    for rule in (core or {}).get("clauses") or (core or {}).get("rules") or []:
        rid = rule.get("id") or rule.get("rule_id")
        red = ((rule.get("traffic_light") or {}).get("red") or rule.get("red") or {})
        markers = list(rule.get("red_flags") or []) + list(red.get("red_flags") or []) + \
            [x for x in red.get("match_criteria") or [] if isinstance(x, str)]
        for mk in markers:
            mk = str(mk).strip()
            if len(mk) < 4:
                continue
            for i, t in enumerate(accepted):
                if mk in t and i not in (rule_decided.get(rid) or set()):
                    finding(out, "RED_MARKER", "סימן אדום של הכלל %s (\"%s\") בנוסח המתקבל, בלי הכרעה לאותו כלל" % (rid, mk),
                            "פסקה %d" % i, blocking=True)
    # 6: טקסט מוסתר אצלם
    for h in hidden_scan(received):
        if h["part"] == "word/document.xml" and h["paragraph"] is not None:
            rroot = dt.document_root(received)        # ניתוח אחד: אותם אלמנטים בשתי הרשימות
            body = dt.body_paragraphs(rroot)
            all_p = list(rroot.iter(W + "p"))
            try:
                idx = body.index(all_p[h["paragraph"]])
            except (ValueError, IndexError):
                idx = None
            if idx is not None and not by_para.get(idx):
                finding(out, "HIDDEN_TEXT", "טקסט מוסתר (%s) בטיוטה שלהם, בלי הכרעה: \"%s\"" % (h["how"], h["text"][:80]),
                        "פסקה %d" % idx, blocking=True)
        elif h["how"] == "properties":
            finding(out, "HIDDEN_TEXT", "טקסט במאפייני הקובץ (%s): לבדוק שאינו הוראה" % h["part"], h["part"])
    # 10, 11: הבועות שלהם
    lawyer = {str(x).strip() for x in ((profile or {}).get("lawyer_names") or []) if x}
    exposed = {(e.get("quote") or "")[:40] for e in (meta.get("exposed_comments") or state.get("exposed_comments") or [])}
    replies_to = {d.get("reply_to_comment") for d in decisions if d.get("reply_to_comment")}
    for c in comment_info(received):
        if c["author"] in lawyer or c["author"] in INTERNAL_AUTHORS:
            continue
        if INTERNAL_HINT.search(c["text"]) and c["text"][:40] not in exposed:
            finding(out, "THEIR_INTERNAL_COMMENT", "בועה של %s נראית פנימית, ואינה רשומה ב-exposed_comments: \"%s\"" %
                    (c["author"], c["text"][:100]), "בועה %s" % c["id"], blocking=True)
        if not c["has_reply"] and c["id"] not in replies_to:
            finding(out, "THEIR_COMMENT_UNANSWERED", "לבועה של %s אין מענה: \"%s\"" % (c["author"], c["text"][:80]),
                    "בועה %s" % c["id"])
    # 56: צירופים
    combos = load(os.path.join(HERE, "combos.json")) or []
    checked = {tuple(sorted(x.get("decisions") or [])) for x in (meta.get("combo_checks") or state.get("combo_checks") or [])}
    texts = {d.get("id"): " ".join(str(d.get(k) or "") for k in ("new_text", "new", "text")) for d in decisions}
    for combo in combos:
        a = sorted(i for i, t in texts.items() if t.strip() and re.search(combo["a"], t, re.I))
        b = sorted(i for i, t in texts.items() if t.strip() and re.search(combo["b"], t, re.I))
        pairs = {tuple(sorted((x, y))) for x in a for y in b if x != y}
        open_pairs = sorted(pr for pr in pairs if pr not in checked)
        if open_pairs:
            finding(out, "COMBO", "צירוף \"%s\": %s מול %s. לבדוק אותם יחד, ולרשום ב-meta.combo_checks" %
                    (combo["name"], ", ".join(a), ", ".join(b)), "")
    # כירורגי, ולא פסקה במקום פסקה: שינוי של כמה מילים מסומן רק בהן
    deleted = {d.get("para"): d for d in decisions if d.get("op") == "delete_paragraph"}
    for d in decisions:
        if d.get("op") != "insert_paragraph" or not isinstance(d.get("after_para"), int):
            continue
        for p in (d["after_para"], d["after_para"] + 1):
            old = deleted.get(p)
            if old is None or p >= len(theirs):
                continue
            tok_o = re.findall(r"\w+", theirs[p])
            tok_n = set(re.findall(r"\w+", d.get("text") or ""))
            if tok_o and sum(1 for t in tok_o if t in tok_n) / len(tok_o) >= 0.4:
                finding(out, "PARAGRAPH_REPLACED", "הפסקה נמחקה ונכתבה מחדש (%s ו-%s), ורוב המילים נשארו: לסמן "
                        "ב-replace_span רק את מה שמשתנה" % (old.get("id"), d.get("id")), "פסקה %d" % p, blocking=True)
    for d in decisions:
        if d.get("op") == "replace" and isinstance(d.get("para"), int) and d["para"] < len(theirs):
            orig, new = theirs[d["para"]], d.get("new_text") or ""
            ops = dt.char_ops(orig, new)
            marked = sum((o[2] - o[1]) for o in ops if o[0] == "delete") + sum(len(o[3]) for o in ops if o[0] == "insert")
            tok_o = re.findall(r"\w+", orig)
            tok_n = set(re.findall(r"\w+", new))
            overlap = (sum(1 for t in tok_o if t in tok_n) / len(tok_o)) if tok_o else 0.0
            if marked >= 0.8 * (len(orig) + len(new)) and overlap >= 0.4:
                finding(out, "REPLACE_COLLAPSED", "ההכרעה מסמנת את רוב הפסקה אף שרוב המילים נשארו: לסמן "
                        "ב-replace_span רק את מה שמשתנה", d.get("id"), blocking=True)
    for d in decisions:
        if d.get("op") in ("replace", "replace_span", "insert_paragraph") and not (d.get("plain_effect")
                                                                                  and d.get("position_effect")):
            finding(out, "EFFECT_FIELDS", "הכרעה שמכניסה נוסח בלי plain_effect ו-position_effect", d.get("id"))
    review_2210(out, theirs, decisions, state, core, received)
    review_containment(out, theirs, decisions, state, core, mode)
    try:
        rlabels = numbered_labels(received)
    except (OSError, KeyError, zipfile.BadZipFile, etree.XMLSyntaxError):
        rlabels = None
    review_related(out, theirs, decisions, state, core, rlabels)
    review_post_edit(out, theirs, decisions, state, mode, rlabels)
    review_high_risk(out, theirs, decisions, state, core, mode, rlabels)
    review_law_coverage(out, decisions, state, core, mode)
    out.extend(PM.check_map(((state or {}).get("meta") or {}).get("playbook_map"), core, "work" if mode == "work" else "send"))
    review_definitions(out, theirs, decisions, state, mode, rlabels)
    review_definition_changes(out, theirs, accepted, decisions, rlabels)
    review_areo(out, decisions, state, mode)
    review_s1c(out, theirs, decisions, state, received, work, mode)
    review_interactions(out, accepted, theirs, decisions, state, mode)
    review_overclaim(out, decisions, mode)
    review_numbers(out, theirs, decisions, state, core, mode)
    review_consistency(out, accepted, theirs, decisions, state, received, mode, lawyer_names=(profile or {}).get(
        "lawyer_names"))
    return out


# --------------------------------------------------------------------------- בדיקה עצמאית S1c, 28.10.2026
# M2: טענה בבועה על מסמך או על עובדה חיצונית שלא נמסרו ("because that is where the price was agreed", "as agreed in
# the Services Agreement"). המקור: מסמך שהתקבל ב-deal_documents, עובדה ב-deal_context.facts, או fact_source
CLAIM = re.compile(r"\b(?:as|where|which|what)\b[^.;]{0,60}?\b(?:was|were|has been|have been|had been)\s+(?:already\s+)?"
                   r"(?:agreed|negotiated|settled|fixed|discussed|confirmed|approved)\b|\bthat is where\b|"
                   r"\bas (?:already |previously )?(?:agreed|discussed|confirmed)\b|"
                   r"\b(?:is|are) (?:already )?(?:set|fixed|agreed|priced|settled) (?:in|under|by) the\b|"
                   r"\bas you (?:have )?(?:confirmed|agreed|said|told us)\b|"
                   r"כפי ש(?:סוכם|הוסכם|נקבע|אישרתם|ציינתם|נאמר)|שם (?:סוכם|הוסכם|נקבע)|(?:סוכם|הוסכם|נקבע) (?:ב|בין)|"
                   r"(?:קבוע|קבועים|נקבעו|מוסדרים) ב(?:הסכם|חוזה)", re.I)
DOC_NAME = re.compile(r"\b((?:[A-Z][\w-]*\s+){1,4}(?:Agreement|Contract|Order Form|Order|Form|Statement of Work|Terms|Proposal|"
                      r"Quotation|Letter))\b|(?<![א-ת])(?:ב|ל|מ|ש)?(הסכם ה[א-ת]+|חוזה ה[א-ת]+|הזמנת ה[א-ת]+)")
NOT_RECEIVED = ("referenced_not_received", "not_received", "missing", "requested", "to_request")
# L6: הערות של הצד שכנגד לצוות שלו, בגוף ובהערות השוליים
THEIR_NOTE = re.compile(r"Staff Only|Note to (?:read|draft|user)|drafting note|guidance note|for internal use|"
                        r"internal use only|הערה לצוות|לשימוש פנימי|הערת ניסוח|הנחיות למילוי", re.I)
GUIDE_FOOTNOTE = re.compile(r"^\s*(?:Consider|Amend|Add|Include|Insert|Delete|Remove|Check|Please|Below is|"
                            r"This (?:should|must)|יש ל|להשלים|לשקול|למחוק|נא )|amend as necessary|consult with", re.I)


def _docs_received(state):
    meta = state.get("meta") or {}
    dd = meta.get("deal_documents") or state.get("deal_documents") or {}
    files = dd.get("files") if isinstance(dd, dict) else dd
    out = []
    for f in files or []:
        if isinstance(f, dict):
            name = " ".join(str(f.get(k) or "") for k in ("file", "name", "title"))
            out.append((name.lower(), str(f.get("status") or "received")))
    return out


def review_s1c(out, theirs, decisions, state, received, work, mode=None):
    meta = state.get("meta") or {}
    docs = _docs_received(state)
    facts = " ".join(str((f or {}).get("fact") or "") for f in ((meta.get("deal_context") or {}).get("facts") or [])
                     if isinstance(f, dict)).lower()
    for d in decisions:
        bub = d.get("external_comment") or ""
        for s in re.split(r"(?<=[.;?!])\s+", bub):
            m = CLAIM.search(s)
            if not m:
                continue
            names = [x for g in DOC_NAME.findall(s) for x in g if x and not x.lower().startswith("this ")]
            if names:
                bad = [n for n in names if n.lower() not in facts and
                       not any(n.lower() in name and st not in NOT_RECEIVED for name, st in docs)]
            else:
                bad = [] if d.get("fact_source") in ("user_answer", "agreement") else [m.group(0)]
            if bad:
                finding(out, "BUB_UNSOURCED_FACT", "הבועה טוענת עובדה על מסמך או על אירוע שלא נמסרו (\"%s\", %s): אין "
                        "לה מקור ב-deal_documents שהתקבלו, ב-deal_context.facts או ב-fact_source. לנמק בנוסח שלפנינו, "
                        "או לרשום את המקור" % (m.group(0), ", ".join(bad)), d.get("id"), blocking=(mode != "work"))
                break
    # L6: הערות לצוות שלהם מטופלות באופן עקבי: כולן נמחקות עם בועה אחת, או כולן נשארות עם בועה
    notes = [i for i, t in enumerate(theirs) if THEIR_NOTE.search(t or "")]
    deleted = {d.get("para") for d in decisions if d.get("op") == "delete_paragraph"}
    gone_notes = [i for i in notes if i in deleted]
    kept = [i for i in notes if i not in deleted]
    guide_ids = []
    try:
        with zipfile.ZipFile(received) as z:
            if "word/footnotes.xml" in z.namelist():
                fx = etree.fromstring(z.read("word/footnotes.xml"))
                for fn in fx.iter(W + "footnote"):
                    txt = "".join(t.text or "" for t in fn.iter(W + "t"))
                    if txt.strip() and GUIDE_FOOTNOTE.search(txt):
                        guide_ids.append(fn.get(W + "id"))
    except (OSError, zipfile.BadZipFile, etree.XMLSyntaxError):
        guide_ids = []
    left_fn = []
    if guide_ids:
        wroot = dt.document_root(work)
        for ref in wroot.iter(W + "footnoteReference"):
            if ref.get(W + "id") in guide_ids and not any(dt.local(a.tag) == "del" for a in ref.iterancestors()):
                left_fn.append(ref.get(W + "id"))
    removed_fn = [x for x in guide_ids if x not in left_fn]
    if (gone_notes or removed_fn) and (kept or left_fn):
        finding(out, "THEIR_NOTES_PARTIAL", "הערות לצוות של הצד שכנגד טופלו חלקית: נמחקו %s, ונשארו %s. כולן נמחקות "
                "עם בועה אחת, או כולן נשארות עם בועה (n4-redlining.md, שלב א)"
                % ("פסקאות %s" % gone_notes if gone_notes else "הערות שוליים %s" % removed_fn,
                   ", ".join(x for x in ["פסקאות %s" % kept if kept else "", "הערות שוליים %s" % left_fn if left_fn else ""]
                             if x)), "")


# --------------------------------------------------------------------------- בדיקות עקביות, S1d-R2 ו-S1e-R3 (29.10.2026)
# כל בדיקה היא ממצא לבדיקה עם המלצה, ולא חסימה (חוץ מ-EXPLICIT_ANSWER_MISSING במצב משלוח). עורך הדין שבדק ומצא שהנוסח
# תקין רושם זאת ב-checks_reviewed (code, para, reason), כמו בבדיקות המבניות.
# 1. אמצעי הודעה: S1d-R2, 13(ii) קבע "notice sent to it by email", כש-22.3 קובע "writing shall not include e-mail"
# ו-13(i) דורש "in writing"
EMAIL = re.compile(r"\be-?mail\b|\belectronic mail\b|דוא[\"״']ל|דואר אלקטרוני|אי-?מייל", re.I)
NOTICE_WORD = re.compile(r"\bnoti(?:ce|fy|fied|fication)s?\b|\bsent\b|\bserved?\b|\bdelivered\b|הודע|יישלח|תישלח|"
                         r"תימסר|יימסר|שליחה|מסירה", re.I)
EMAIL_EXCLUDED = re.compile(r"writing shall not include e-?mail|(?:e-?mail|electronic mail)[^.;]{0,40}(?:shall|does|will) "
                            r"not (?:constitute|be (?:deemed|treated as|considered|valid)|count as|be a valid)|"
                            r"\b(?:not|excluding|other than|except) (?:by |via )?(?:e-?mail|electronic mail)\b|"
                            r"(?:דוא[\"״']ל|דואר אלקטרוני)[^.;]{0,40}(?:לא ייחשב|לא תיחשב|אינו|אינה|לא יהווה|לא תהווה)|"
                            r"(?:למעט|ולא|שלא) (?:ב|באמצעות )(?:דוא[\"״']ל|דואר אלקטרוני)", re.I)
IN_WRITING = re.compile(r"\bin writing\b|\bwritten notice\b|(?<![א-ת])בכתב(?![א-ת])", re.I)
OVERRIDE = re.compile(r"\bnotwithstanding\b|\bdespite\b|\bby way of exception to\b|על אף|למרות", re.I)
# 2. הגדרה מיושנת: סימנים מבניים להפניה לחקיקה שטרם נכנסה לתוקף. אין כאן רשימה של חוקים, משטרים או מועדים בשמם:
# מה שהוחלף או בוטל נקבע במחקר העומק בזמן ריצה, מרשימת המקורות המאושרים, ולא בקוד. סימן שנוסף כאן הוא מבני בלבד
STALE_MARKERS = (
    (re.compile(r"\bsubject to (?:Royal Assent|enactment|ratification)\b|\bnot yet in force\b|טרם נכנס(?:ה)? לתוקף", re.I),
     "הפניה לחקיקה שבזמן הניסוח עוד לא נחקקה או לא נכנסה לתוקף"),
)
# 3. "not unreasonably withheld" על הסכמה להגדלת החובות שלנו (S1d, 25.3 בסבב 1)
UNREASONABLY = re.compile(r"\bnot\s+(?:to\s+)?be\s+unreasonably\s+(?:withheld|refused|delayed|conditioned)|"
                          r"\bnot\s+unreasonably\s+(?:withhold|refuse|delay|condition)|"
                          r"(?:לא|שלא)\s+(?:תסורב|יסורב|תימנע|יימנע|יעוכב|תעוכב|יסרב|תסרב)[^.;]{0,25}"
                          r"(?:בלתי\s+סביר|שלא\s+(?:מטעמים|באופן)\s+סביר|מטעמים\s+(?:בלתי\s+)?סבירים)", re.I)
INCREASE = re.compile(r"\b(?:increase|extend|expand|enlarge|add to)\w*\b[^.;]{0,60}?\b(?:obligations?|costs?|"
                      r"liabilit(?:y|ies)|responsibilit(?:y|ies)|exposure)\b|"
                      r"(?:יגדיל|יגדילו|תגדיל|להגדיל|הגדלת|ירחיב|ירחיבו|להרחיב|הרחבת)[^.;]{0,60}?"
                      r"(?:התחייבויות|חובות|עלויות|אחריות|חבות)", re.I)
# 4 ו-5. תקרות וביטוח
MONEY_CUR = {"£": "GBP", "gbp": "GBP", "ליש\"ט": "GBP", "ליש״ט": "GBP", "$": "USD", "usd": "USD", "דולר": "USD",
             "€": "EUR", "eur": "EUR", "אירו": "EUR", "יורו": "EUR", "₪": "ILS", "nis": "ILS", "ils": "ILS",
             "ש\"ח": "ILS", "ש״ח": "ILS"}
_CUR_RX = "|".join(sorted((re.escape(k) for k in MONEY_CUR), key=len, reverse=True))
_MULT = {"million": 1e6, "m": 1e6, "mm": 1e6, "מיליון": 1e6, "k": 1e3, "thousand": 1e3, "אלף": 1e3}
MONEY_BEFORE = re.compile(r"(?<![\w])(%s)\s?(\d[\d,]*(?:\.\d+)?)(?:\s*(million|mm|m|k|thousand|מיליון|אלף)(?![\w]))?"
                          % _CUR_RX, re.I)
MONEY_AFTER = re.compile(r"(?<![\d.,])(\d[\d,]*(?:\.\d+)?)\s*(million|thousand|מיליון|אלף)?\s*(%s)(?![\w])" % _CUR_RX,
                         re.I)
INSURANCE = re.compile(r"\binsurance\b|\binsured\b|\binsurer\b|ביטוח|פוליס", re.I)
CAP_WORD = re.compile(r"shall not exceed|will not exceed|limited to|capped at|\bcap\b|maximum (?:aggregate )?liability|"
                      r"לא תעלה|לא יעלה|לא יעלו|תקרת|תוגבל|מוגבלת ל", re.I)
LIAB_WORD = re.compile(r"liabilit|אחריות|חבות", re.I)
SUPER_CAP = re.compile(r"\b(?:save that|except that|provided that|save for|other than)\b(?:[^.]|\.(?=\d)){0,250}?\b(?:shall|"
                       r"will) not exceed\b|(?:ואולם|למעט|אלא ש|ובלבד ש|פרט ל)(?:[^.]|\.(?=\d)){0,250}?(?:לא תעלה|לא יעלה|"
                       r"לא יעלו)", re.I)
CAP_RELATION = re.compile(r"in addition to|inclusive of|included in|count(?:s|ed)? towards|not in addition|separate from|"
                          r"instead of|in substitution|within (?:that|the|such) (?:cap|limit|amount)|"
                          r"בנוסף ל|נוסף על|כלול|במסגרת (?:התקרה|הסכום)|מעבר לתקרה", re.I)
AGGREGATION = re.compile(r"(?:calculated|counted|aggregated|taken together|combined)\s+(?:in the aggregate\s+)?with|"
                         r"in (?:the )?aggregate with|together with (?:its|their|any|the) (?:liabilit(?:y|ies)|exposure) "
                         r"under|single (?:aggregate )?cap (?:for|across|under)|במצטבר עם|יחד עם (?:האחריות|החבות)|"
                         r"תקרה (?:אחת|משותפת)|ייכלל(?:ו)? בתקרה", re.I)
# 6. ייחוס הצעה לצד שכנגד
OFFER_ATTR = re.compile(r"\bas (?:you|the [A-Z][\w-]+) (?:have |has |had )?(?:offered|proposed|suggested)\b|"
                        r"\b(?:in line with|per|following) your (?:offer|proposal|suggestion)\b|"
                        r"\byour (?:offer|proposal|suggestion) (?:of|to|that)\b|\byou (?:have )?(?:offered|proposed|suggested)\b|"
                        r"כפי שהצעתם|כהצעתכם|בהתאם להצעתכם|לפי הצעתכם|הצעתכם ל|שהצעתם|כפי שהציעו", re.I)
OFFER_STOP = {"which", "their", "there", "these", "those", "about", "after", "before", "would", "could", "should",
              "shall", "under", "where", "while", "keep", "agree", "accept", "offered", "proposed", "suggested",
              "additional", "together"}


def _money(text):
    """[(מטבע, סכום)] בטקסט: "£2,000,000", "USD 1m", "500,000 ש\"ח"."""
    out = []
    for m in MONEY_BEFORE.finditer(text or ""):
        cur, num, mult = m.group(1), m.group(2), m.group(3)
        try:
            v = float(num.replace(",", "")) * _MULT.get((mult or "").lower(), 1)
        except ValueError:
            continue
        out.append((MONEY_CUR.get(cur.lower(), MONEY_CUR.get(cur, cur)), v))
    for m in MONEY_AFTER.finditer(text or ""):
        num, mult, cur = m.group(1), m.group(2), m.group(3)
        try:
            v = float(num.replace(",", "")) * _MULT.get((mult or "").lower(), 1)
        except ValueError:
            continue
        out.append((MONEY_CUR.get(cur.lower(), MONEY_CUR.get(cur, cur)), v))
    return out


def _norm_ws(s):
    return re.sub(r"\s+", " ", (s or "").replace("’", "'").replace("‘", "'")).strip()


def _ours_in(text, decisions):
    """האם הפסקה (בנוסח המתקבל) כוללת נוסח שהכנסנו."""
    t = _norm_ws(text)
    return any(len(_norm_ws(x)) >= 12 and _norm_ws(x) in t for _, x in our_texts(decisions))


def _sentence_span(text, pos):
    """(התחלה, סוף) של המשפט שבו נמצא המיקום pos. נקודה בתוך מספר ("18.3") אינה סוף משפט."""
    a = 0
    for m in re.finditer(r"[.;?!](?:\s+|$)", text):
        if m.end() > pos:
            break
        a = m.end()
    m = re.search(r"[.;?!](?=\s|$)", text[pos:])
    return a, (pos + m.end() if m else len(text))


def _sentence_of(text, pos):
    a, b = _sentence_span(text, pos)
    return text[a:b]


def _our_labels(state):
    """כינויי הצד שלנו בהסכם, ממפת המונחים (meta.position.defined_terms_map, means: us), בלי "the"."""
    pos = ((state or {}).get("meta") or {}).get("position") or {}
    out = []
    for x in pos.get("defined_terms_map") or []:
        if isinstance(x, dict) and x.get("means") == "us" and x.get("term"):
            out.append(re.sub(r"^(?:the|ה)\s*", "", str(x["term"]).strip(), flags=re.I))
    return [x for x in out if len(x) >= 2]


def _their_labels(state):
    """כינויי הצד שכנגד בהסכם, ממפת המונחים (means: them), בלי "the"."""
    pos = ((state or {}).get("meta") or {}).get("position") or {}
    out = []
    for x in pos.get("defined_terms_map") or []:
        if isinstance(x, dict) and x.get("means") == "them" and x.get("term"):
            out.append(re.sub(r"^(?:the|ה)\s*", "", str(x["term"]).strip(), flags=re.I))
    return [x for x in out if len(x) >= 2]


def _rep_by_them(txt, start, state):
    """מצג שהנושא שלו הוא הצד שכנגד ("המזמין מצהיר כי", "the Customer represents that") אינו מצג של החברה
    (n4b-redlining-steps.md, שלב ו2): הכינוי האחרון לפני הפועל, באותו משפט, הוא כינוי שלהם ולא שלנו."""
    a, _ = _sentence_span(txt, start)
    head = txt[max(a, start - 80):start]

    def last(labels):
        pos = -1
        for lab in labels:
            for m in re.finditer(r"(?<![א-ת\w])[ולבכמש]{0,2}ה?" + re.escape(lab) + r"(?![א-ת\w])", head, re.I):
                pos = max(pos, m.start())
        return pos

    theirs = last(_their_labels(state))
    return theirs >= 0 and theirs > last(_our_labels(state))


def _their_sources(received, ours):
    """הטקסט שהצד שכנגד כתב בעצמו: הבועות שלו (כל מחבר שאינו שלנו) וההוספות המסומנות שלו."""
    texts = [c["text"] for c in comment_info(received) if c["author"] not in ours and c["author"] not in INTERNAL_AUTHORS]
    try:
        root = dt.document_root(received)
        for e in root.iter(W + "ins"):
            if e.get(W + "author") not in ours:
                texts.append("".join(t.text or "" for t in e.iter(W + "t")))
    except (OSError, KeyError, zipfile.BadZipFile, etree.XMLSyntaxError):
        pass
    return "\n".join(texts)


def review_consistency(out, accepted, theirs, decisions, state, received, mode=None, lawyer_names=()):
    """בדיקות העקביות 1 עד 7 (29.10.2026). accepted: הנוסח המתקבל בקובץ העבודה; theirs: הטיוטה שהתקבלה."""
    state = state or {}
    ours_txt = our_texts(decisions)

    # 1. אמצעי הודעה מול סעיף ההודעות
    excluded = [(i, m.group(0)) for i, t in enumerate(accepted) for m in [EMAIL_EXCLUDED.search(t)] if m]
    if excluded:
        for d, txt in ours_txt:
            for s in re.split(r"(?<=[.;])\s+", txt):
                m = EMAIL.search(s)
                if not (m and NOTICE_WORD.search(s)) or EMAIL_EXCLUDED.search(s) or OVERRIDE.search(s):
                    continue
                p = d.get("para") if isinstance(d.get("para"), int) else d.get("after_para")
                if _reviewed(state, "NOTICE_EMAIL_CONFLICT", p):
                    break
                near = []
                if isinstance(p, int):
                    near = [j for j in range(max(0, p - 3), min(len(theirs), p + 4))
                            if j != p and IN_WRITING.search(theirs[j]) and NOTICE_WORD.search(theirs[j])]
                ex_i, ex_t = excluded[0]
                finding(out, "NOTICE_EMAIL_CONFLICT", "הנוסח שלנו קובע הודעה בדוא\"ל (\"%s\"), וסעיף ההודעות (פסקה %d: "
                        "\"%s\") מוציא דוא\"ל מ\"בכתב\"%s. המלצה: לקבוע בנוסח שלנו שההודעה לפי סעיף זה יכולה להישלח "
                        "בדוא\"ל על אף סעיף ההודעות, או לתקן את סעיף ההודעות, או לוותר על הדוא\"ל"
                        % (s.strip()[:90], ex_i, ex_t,
                           "; ובפסקה %s הסמוכה נדרשת הודעה בכתב (\"%s\"), כך שהשתיים סותרות"
                           % (near[0], theirs[near[0]].strip()[:70]) if near else ""), d.get("id"))
                break

    # 2. הגדרה מיושנת
    for i, t in enumerate(accepted):
        why = [w for rx, w in STALE_MARKERS if rx.search(t)]
        if not why or _reviewed(state, "DEF_OUTDATED", i):
            continue
        terms = sorted(_terms_in(t))
        if terms:
            relying = sorted({str(d.get("id")) for d, x in ours_txt for term in terms if _term_rx(term).search(x)})
            uses = sum(1 for j, x in enumerate(accepted) if j != i and any(_term_rx(term).search(x) for term in terms))
            finding(out, "DEF_OUTDATED", "ההגדרה \"%s\" (פסקה %d) מפנה לחוק או למועד שהוחלפו: %s. %s המלצה: להציע עדכון של "
                    "ההגדרה לדין שחל היום, או לרשום ב-checks_reviewed שהוחלט להשאיר אותה"
                    % (", ".join(terms), i, "; ".join(why),
                       "ההכרעות %s נשענות עליה, ו-%d פסקאות משתמשות בה." % (", ".join(relying), uses) if relying
                       else "%d פסקאות משתמשות בה." % uses), "פסקה %d" % i)
        elif _ours_in(t, decisions):
            finding(out, "DEF_OUTDATED", "בנוסח שלנו הפניה לחוק או למועד שהוחלפו: %s. המלצה: להפנות לדין שחל היום"
                    % "; ".join(why), "פסקה %d" % i)

    # 3. "not unreasonably withheld" על הסכמה שלנו להגדלת החובות שלנו
    labels = _our_labels(state)
    for i, t in enumerate(accepted):
        m = UNREASONABLY.search(t)
        if not m or _reviewed(state, "CONSENT_REASONABLE_OURS", i):
            continue
        s = _sentence_of(t, m.start())
        inc = INCREASE.search(s)
        if not inc:
            continue
        hit = [lab for lab in labels if re.search(r"(?<![\w֐-׿])" + re.escape(lab) + r"(?![\w֐-׿])", s, re.I)]
        if labels and not hit:
            continue
        finding(out, "CONSENT_REASONABLE_OURS", "\"%s\" חל על הסכמה להגדלת החובות, העלויות או האחריות%s (\"%s\")%s. "
                "המלצה: הסכמה כזו בשיקול דעתנו המוחלט: למחוק את הסייג, או לכתוב \"in its sole discretion\". אחרת הצד "
                "שכנגד יטען שסירוב לשאת בחובה או בעלות נוספת אינו סביר"
                % (m.group(0), " של %s" % hit[0] if hit else "", inc.group(0)[:70],
                   " בנוסח שלנו" if _ours_in(t, decisions) else "" if labels else
                   ". לא נמצאה מפת מונחים: הממצא חל רק כשזה הצד שלנו"), "פסקה %d" % i)

    # 4. תקרה נוספת בלי יחס לתקרה הכללית
    for i, t in enumerate(accepted):
        m = SUPER_CAP.search(t)
        if not m or CAP_RELATION.search(t) or len(_money(t)) < 2 or _reviewed(state, "CAP_SUPER_UNCLEAR", i):
            continue
        finding(out, "CAP_SUPER_UNCLEAR", "ניסוח: תקרה נוספת (\"%s...\")%s בלי \"in addition to\" או \"inclusive of\". לא "
                "ברור אם הסכום שלה נוסף על התקרה הכללית או כלול בה. המלצה: לכתוב במפורש \"inclusive of, and not in "
                "addition to\" (או \"in addition to\"), לפי העמדה" % (m.group(0)[:60],
                                                                    " בנוסח שלנו" if _ours_in(t, decisions) else ""),
                "פסקה %d" % i)

    # 5א. ביטוח מול תקרה: רחוקים זה מזה פי 2 ומעלה, כשאחד מהם בנוסח שלנו
    our_amounts = {a for _, x in ours_txt for a in _money(x)}
    ins, caps = {}, {}
    for i, t in enumerate(accepted):
        amounts = _money(t)
        if not amounts:
            continue
        is_cap = CAP_WORD.search(t) and LIAB_WORD.search(t)
        target = caps if is_cap else ins if INSURANCE.search(t) else None
        if target is None:
            continue
        for cur, v in amounts:
            target.setdefault(cur, []).append((v, i))
    for cur in sorted(set(ins) & set(caps)):
        iv, ii = max(ins[cur])
        cv, ci = max(caps[cur])
        if not (iv and cv) or max(iv, cv) / min(iv, cv) < 2:
            continue
        if not ({(cur, v) for v, _ in ins[cur] + caps[cur]} & our_amounts):
            continue
        if _reviewed(state, "CAP_INSURANCE_GAP", ci):
            continue
        finding(out, "CAP_INSURANCE_GAP", "הביטוח הנדרש (פסקה %d: %s %s) והתקרה (פסקה %d: %s %s) רחוקים זה מזה פי %.1f. %s "
                "המלצה: ליישר את התקרה לסכום הביטוח או את הביטוח לתקרה, או לנמק את הפער בבועה ולרשום אותו בהכרעה"
                % (ii, cur, "{:,.0f}".format(iv), ci, cur, "{:,.0f}".format(cv), max(iv, cv) / min(iv, cv),
                   "תקרה נמוכה בהרבה מהביטוח מזמינה את הטענה שהכיסוי קיים ולכן התקרה צריכה לעלות." if iv > cv else
                   "ביטוח נמוך בהרבה מהתקרה משאיר חשיפה שאינה מבוטחת."), "פסקה %d" % ci)

    # 5ב. מנגנון נגד צבירה של תקרות בין מסמכים שנמחק
    if not any(AGGREGATION.search(t) and LIAB_WORD.search(t) for t in accepted):
        try:
            base_rej, base_acc = dt.reject_all(received), dt.accept_all(received)
        except (OSError, KeyError, zipfile.BadZipFile, etree.XMLSyntaxError):
            base_rej, base_acc = [], []
        was = [(j, AGGREGATION.search(t).group(0), t) for j, t in enumerate(base_rej + base_acc)
               if AGGREGATION.search(t) and LIAB_WORD.search(t)]
        if was and not _reviewed(state, "CAP_AGGREGATION_REMOVED", None):
            j, phrase, t = was[0]
            by_them = not any(AGGREGATION.search(x) and LIAB_WORD.search(x) for x in base_acc)
            finding(out, "CAP_AGGREGATION_REMOVED", "נמחק מנגנון נגד צבירה של תקרות בין מסמכים (\"%s\")%s. בלעדיו התקרה "
                    "בהסכם הזה עלולה להיספר בנוסף לתקרה בהסכם האחר, ולא יחד איתה. המלצה: להחזיר את המנגנון (למשל "
                    "\"calculated in the aggregate with its liability under the [other agreement]\"), או לוודא שההסכם "
                    "האחר קובע תקרה משותפת" % (phrase, ": הצד שכנגד מחק אותו, וההכרעה לא החזירה אותו" if by_them
                                               else ": המחיקה בהכרעה שלנו"), "")

    # 6. בועה שמייחסת לצד שכנגד הצעה שלא כתב
    ours = {str(x).strip() for x in (lawyer_names or ()) if x}
    their_text = None
    for d in decisions:
        bub = d.get("external_comment") or ""
        m = OFFER_ATTR.search(bub)
        if not m or d.get("offer_source") or d.get("fact_source") == "user_answer":
            continue
        if their_text is None:
            their_text = _their_sources(received, ours) if received else ""
        a, b = _sentence_span(bub, m.start())
        rest = bub[a:m.start()] + " " + bub[m.end():b]
        nums = set(re.findall(r"\d+", rest))
        words = {w.lower() for w in re.findall(r"[A-Za-z]{5,}|[א-ת]{4,}", rest)} - OFFER_STOP
        src_nums = set(re.findall(r"\d+", their_text))
        src = their_text.lower()
        missing_nums = sorted(nums - src_nums)
        found = [w for w in words if w in src]
        if missing_nums or not their_text.strip() or (words and len(found) < 0.5 * len(words)):
            finding(out, "BUB_OFFER_UNSOURCED", "הבועה מייחסת לצד שכנגד הצעה (\"%s\") שאין לה מקור בבועות או בסימונים שלו%s. "
                    "המלצה: לנסח כהצעה שלנו, או לרשום את המקור ב-offer_source (מזהה הבועה שלהם, their_markup, או "
                    "user_answer כשההצעה נמסרה בשיחה)" % (m.group(0), " (%s לא מופיעים אצלם)" % ", ".join(missing_nums)
                                                          if missing_nums else ""), d.get("id"))

    # 7. הכרעה שדורשת תשובה מפורשת: delegated, או בלי user_decision, חוסם משלוח
    explicit_by_state = set()
    for q in state.get("user_decisions") or []:
        if isinstance(q, dict) and q.get("answer_kind") == "explicit" and this_round(state, q):
            explicit_by_state |= {str(x) for x in q.get("applies_to") or []}
    for d in decisions:
        req = d.get("requires_explicit") or (d.get("decision_required") or {}).get("requires_explicit")
        if req is not True:
            continue
        kind = (d.get("user_decision") or {}).get("answer_kind")
        if kind == "explicit" or str(d.get("id")) in explicit_by_state:
            continue
        # פריט שנשאר פתוח ולא הוחל (n3c-matrix-cases.md, "איך זה עובד", 3): כיסוי for_call, הנוסח שלהם נשאר בלי
        # שינוי ובלי קבלה, ובבועה הנושא פתוח לשיחה. אין כאן הכרעה שהוחלה, ולכן אין חסימה; הפריט נשאל שוב במנה הבאה
        if d.get("coverage") == "for_call" and d.get("op") in (None, "", "comment_only"):
            continue
        finding(out, "EXPLICIT_ANSWER_MISSING", "ההכרעה מסומנת requires_explicit, והתשובה של המשתמש %s. נדרשת תשובה מפורשת "
                "לפני משלוח: negotiation_state.py decide --id <השאלה> --answer-kind explicit --applies-to %s"
                % ("הואצלה (delegated)" if kind == "delegated" else "אינה מפורשת (%s)" % kind if kind else "חסרה",
                   d.get("id")), d.get("id"), blocking=(mode != "work"))


# --------------------------------------------------------------------------- שלמות מבנית, תלויים ובדיקות תוצאה
# כללים 1 עד 12 של ההערות לנושא ונותן. הבדיקות רצות על הנוסח שמתקבל אחרי ההכרעות (result_view), במספור של
# הטיוטה שהתקבלה, כך שידוע לכל פסקה אם היא שלנו. כל מה שתלוי בעסקה מגיע מקובץ ההכרעות, ממצב העסקה ומהגרעין.
PROVISO_REF = re.compile(r"הסייג (?:האמור|ה?נ[\"״]ל|שלעיל|שלהלן|הבא|דלעיל)|בכפוף לסייג|"
                         r"the (?:foregoing|above|following|said|preceding) proviso|subject to the proviso", re.I)
PROVISO_MARK = re.compile(r"ובלבד ש|בתנאי ש|ואולם|אלא אם|provided(?:,)? (?:however,? )?that|provided always that|"
                          r"except that", re.I)
BACKREF = re.compile(r"^\s*(?:\(?[א-תa-z0-9]{1,3}[.)]\s*)?(?:כאמור לעיל|האמור לעיל|על אף האמור לעיל|בנוסף לאמור לעיל|"
                     r"מבלי לגרוע מהאמור לעיל|The foregoing|Notwithstanding the foregoing|In addition to the foregoing|"
                     r"Without limiting the foregoing)", re.I)
LEAD_IN = re.compile(r"(?::|שלהלן|כדלקמן|as follows|the following)\s*:?\s*$", re.I)
LIST_ITEM = re.compile(r"^\s*(?:\(?[א-י]\)|\(?[a-z]\)|\(?\d{1,2}\)|[א-י]['׳]?[.)]|[a-z][.)]|\(?[ivx]{1,4}\))\s", re.I)
DANGLING_END = re.compile(r"(?:,|;|\s)(?:או|וכן|or|and)\s*[;:]?\s*$", re.I)
DANGLING_MID = re.compile(r"(?:,|\s)(?:או|or|and)\s*[.;](?:\s|$)", re.I)
TAIL_CONJ = re.compile(r"[;,]\s*(?:או|וכן|or|and)\s*$", re.I)
OBLIGATION = re.compile(r"\bshall\b|\bmust\b|יתחייב|מתחייב|תתחייב|מחויב|חייב(?:ת|ים)?\s|אסור|לא יהיה רשאי|לא תהיה רשאית",
                        re.I)
REF_BUBBLE = re.compile(r"רא(?:ו|ה) (?:את )?הערת(?:נו|י)|כאמור בהערת(?:נו|י)|כמפורט בהערת(?:נו|י)|ר' הערת|"
                        r"see (?:our )?(?:comment|note)|as per our (?:comment|note)|as noted above|"
                        r"part of the same change|same as (?:above|our comment)", re.I)
FACT_THEM = re.compile(r"מאחר ש(?:אתם|אתן|הנכם|החברה שלכם)|הואיל ואתם|בהיותכם|כפי שידוע(?: לנו)? ש|"
                       r"אתם (?:פועלים|נסחרים|מעסיקים|מפוקחים|רשומים|מתחרים)|לקוחותיכם|עובדיכם|מתחריכם|המתחרים שלכם|"
                       r"הרגולטור (?:שלכם|החל עליכם)|"
                       r"given that you|since you (?:are|operate|have)|as you (?:are|operate)|you operate|you employ|"
                       r"you are (?:a |an )?(?:public|listed|regulated|subject to)|"
                       r"your (?:customers|clients|employees|competitors|regulator)", re.I)
FACT_US = re.compile(r"(?:החברה|אנו|אנחנו) (?:היא )?(?:חברה ציבורית|נסחרת|נסחרים|פועלת ב(?!התאם|אופן|מסגרת|הקשר)|"
                     r"פועלים ב(?!התאם|אופן|מסגרת|הקשר)|מעסיקה|מעסיקים|"
                     r"מפוקחת|מפוקחים|כפופה לפיקוח|רשומה ב)|כחברה (?:ציבורית|נסחרת|בורסאית|זרה|מפוקחת)|"
                     r"we are (?:a )?(?:public|listed|regulated)|we operate in|we employ|as a (?:public|listed|regulated) "
                     r"(?:company|entity)|our (?:customers|employees|regulator)", re.I)
FACT_SOURCES = ("profile", "user_answer", "agreement")
WEAKNESS = re.compile(r"אין לנו ברירה|אין לנו חלופה|אין בידינו חלופה|קשה לנו לגבות|יקשה עלינו לגבות|קשה לגבות|"
                      r"אנו תלויים|אנחנו תלויים|תלויים בכם|לחץ זמנים|לוח הזמנים שלנו לחוץ|תזרים|"
                      r"we have no (?:choice|alternative)|we (?:depend|rely) (?:heavily )?on you|"
                      r"we are under (?:time )?pressure|cash ?flow|difficult (?:for us )?to collect|we cannot afford", re.I)
# כלל 12: נושאים שהעמדה בהם תלויה בזהות הצד שכנגד (דין ופורום, שפה גוברת, מטבע ומסים). מילה שלמה בלבד, עם
# אותיות השימוש (ו, ב, ל, מ, ש, כ, ה) לפניה: בהרצה S1c (28.10.2026) "ביקורות, דוחות והסמכות" (certifications) נתפס
# כ"סמכות", ו-R_AUDIT סומן כתלוי בזהות הצד שכנגד. ל"סמכות" אין ה' הידיעה לפניה, כי "הסמכות" היא גם רבים של "הסמכה"
_HE_PRE = r"(?<![א-ת])(?:[ובלמשכ]{0,2}ה?)"
CP_TOPIC = re.compile(_HE_PRE + r"(?:דין|שיפוט|פורום|בוררות|שפה|מטבע|מס|מסים|מיסים|מיסוי|ניכוי במקור)(?![א-ת])|"
                      r"(?<![א-ת])[ובלמשכ]{0,2}סמכות(?![א-ת])|"
                      r"\b(?:governing law|jurisdictions?|forums?|arbitration|languages?|currenc(?:y|ies)|tax(?:es|ation)?|"
                      r"withholding)\b", re.I)
# כלל שתלוי במקום, בדין, ברגולציה או ברישום (ENTITY_RULE_UNCONFIRMED): מילה שלמה בלבד, כמו CP_TOPIC, כדי ש"והסמכות"
# (certifications), "עדיין" או "השפעה" לא ייתפסו כ"סמכות", "דין" או "שפה"
LAW_TOPIC = re.compile(_HE_PRE + r"(?:דין|דיני|שיפוט|פורום|בוררות|שפה|מטבע|מס|מסים|מיסים|מיסוי|ניכוי במקור|פרטיות|"
                       r"מידע אישי|ניירות ערך)(?![א-ת])|(?<![א-ת])[ובלמשכ]{0,2}סמכות(?![א-ת])|רגולצ|"
                       r"\b(?:governing law|jurisdictions?|forums?|arbitration|languages?|currenc(?:y|ies)|tax(?:es|ation)?|"
                       r"withholding|privacy|data protection|securities)\b|\bregulat", re.I)
HE_MONTHS = {"ינואר": 1, "פברואר": 2, "מרץ": 3, "מרס": 3, "אפריל": 4, "מאי": 5, "יוני": 6, "יולי": 7, "אוגוסט": 8,
             "ספטמבר": 9, "אוקטובר": 10, "נובמבר": 11, "דצמבר": 12}
EN_MONTHS = {m: i + 1 for i, m in enumerate(("january", "february", "march", "april", "may", "june", "july", "august",
                                              "september", "october", "november", "december"))}
ANCHOR_CTX = re.compile(r"תחילת|תחולת|יחול|ייכנס לתוקף|ייכנסו לתוקף|נכנס לתוקף|מועד התחילה|מועד התחולה|מועד הקובע|"
                        r"תקופת ההסכם|יתחיל|תתחיל|החל מיום|החל מתאריך|effective|commenc|start date|as of|"
                        r"term (?:of this agreement )?(?:shall )?(?:begin|start)", re.I)
DATE_RX = [
    (re.compile(r"(?<!\d)(\d{1,2})[./](\d{1,2})[./](\d{4})(?!\d)"), "dmy"),
    (re.compile(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)"), "ymd"),
    (re.compile(r"(?<!\d)(\d{1,2})\s+ב?(%s),?\s+(\d{4})" % "|".join(HE_MONTHS)), "d_he_y"),
    (re.compile(r"(?<!\d)(\d{1,2})(?:st|nd|rd|th)?\s+(%s),?\s+(\d{4})" % "|".join(EN_MONTHS), re.I), "d_en_y"),
    (re.compile(r"\b(%s)\s+(\d{1,2}),?\s+(\d{4})" % "|".join(EN_MONTHS), re.I), "en_d_y"),
]
EMPTY_ANCHOR = re.compile(r"(?:מיום|מתאריך|החל מיום|ביום|effective(?: as of)?|dated|as of|commencing on)\s*"
                          r"(?:_{2,}|\[\s*[•·.\s]*\]|\.{3,}|__\s*/\s*__)", re.I)


def result_view(theirs, decisions):
    """הנוסח שמתקבל אחרי ההכרעות, במספור של הטיוטה שהתקבלה. מחזיר רשימת (מקור, טקסט, שלנו): מקור הוא אינדקס
    הפסקה שלהם, או ("ins", after_para) לפסקה שהוספנו. פסקה שנמחקה אינה ברשימה."""
    res = list(theirs)
    ours = set()
    gone = set()
    ins = {}
    for d in decisions:
        p, op = d.get("para"), d.get("op")
        if op == "insert_paragraph" and isinstance(d.get("after_para"), int):
            ins.setdefault(d["after_para"], []).append(d.get("text") or "")
        if not isinstance(p, int) or not 0 <= p < len(res):
            continue
        if op == "replace" and d.get("new_text") is not None:
            res[p] = d["new_text"]
            ours.add(p)
        elif op == "replace_span" and d.get("old") and d["old"] in res[p]:
            res[p] = res[p].replace(d["old"], d.get("new") or "", 1)
            ours.add(p)
        elif op == "delete_paragraph":
            gone.add(p)
    out = []
    for i, t in enumerate(res):
        if i not in gone:
            out.append((i, t, i in ours))
        for t2 in ins.get(i, []):
            out.append((("ins", i), t2, True))
    return out, gone


def _dates(text):
    import datetime as _dt
    for rx, kind in DATE_RX:
        for m in rx.finditer(text):
            g = m.groups()
            try:
                if kind == "dmy":
                    d = _dt.date(int(g[2]), int(g[1]), int(g[0]))
                elif kind == "ymd":
                    d = _dt.date(int(g[0]), int(g[1]), int(g[2]))
                elif kind == "d_he_y":
                    d = _dt.date(int(g[2]), HE_MONTHS[g[1]], int(g[0]))
                elif kind == "d_en_y":
                    d = _dt.date(int(g[2]), EN_MONTHS[g[1].lower()], int(g[0]))
                else:
                    d = _dt.date(int(g[2]), EN_MONTHS[g[0].lower()], int(g[1]))
            except (ValueError, KeyError):
                continue
            yield m, d


def time_anchors(theirs, today=None):
    """כלל 4: עוגני זמן בנייר שלהם שנמצאים בעבר או ריקים. לכל ממצא: para, text, issue (past / empty), date."""
    import datetime as _dt
    today = today or _dt.date.today()
    out = []
    for i, t in enumerate(theirs):
        for m in EMPTY_ANCHOR.finditer(t):
            out.append({"para": i, "text": m.group(0), "issue": "empty", "date": None})
        for m, d in _dates(t):
            before = t[max(0, m.start() - 60):m.start()]
            if d < today and ANCHOR_CTX.search(before):
                out.append({"para": i, "text": t[max(0, m.start() - 40):m.end()].strip(), "issue": "past",
                            "date": d.isoformat()})
    return out


def _terms_in(text):
    out = set()
    for rx in DEF_PATTERNS:
        for m in rx.finditer(text or ""):
            out.update(g.strip() for g in m.groups() if g)
    return out


def _term_rx(term):
    stem = term[1:] if term.startswith("ה") and len(term) > 3 else term
    if stem != term:
        return re.compile(r"(?<![א-ת])[ולבכמש]{0,2}ה?" + re.escape(stem) + r"(?![א-ת])")
    return re.compile(re.escape(term))


def dependents_of(d, theirs, labels):
    """כלל 2: הסעיפים שתלויים בהכרעה שמשנה משטר. מחזיר רשימת אינדקסים בטיוטה שהתקבלה, בלי הפסקה עצמה.
    תלוי: פסקה שמפנה לסעיף ששונה, פסקה שמשתמשת במונח שהגדרתו שונתה, ופסקאות ש-same_topic מונה."""
    p = d.get("para")
    if not isinstance(p, int) or not 0 <= p < len(theirs):
        return []
    # רק הכרעה שהסקיל הצהיר שהיא משנה משטר (regime). השלמת שם או הוספת כינוי בפסקת הגדרות אינן משנות את
    # המשמעות, ולכן אין הנחה אוטומטית; הכרעה שנוגעת בהגדרה בלי regime מקבלת אזהרה (REGIME_UNDECLARED)
    regime = d.get("regime")
    terms = _terms_in(theirs[p])
    if regime in (None, "", "none"):
        return []
    deps = set()
    lab = labels[p] if p < len(labels) else None
    if lab:
        for j, t in enumerate(theirs):
            if j == p:
                continue
            for rx in (REF_HE, REF_EN):
                if any(m.group(1) == lab for m in rx.finditer(t)):
                    deps.add(j)
    if regime == "definition":
        for term in terms:
            trx = _term_rx(term)
            deps.update(j for j, t in enumerate(theirs) if j != p and trx.search(t))
    deps.update(x for x in d.get("same_topic") or [] if isinstance(x, int) and x != p)
    return sorted(deps)


def _rule_index(core):
    return {(r.get("id") or r.get("rule_id")): r for r in (core or {}).get("clauses") or (core or {}).get("rules") or []}


def _kinds(meta):
    v = ((meta.get("deal_context") or {}).get("counterparty_kind"))
    return set(v if isinstance(v, list) else [v] if v else [])


# --------------------------------------------------------------------------- הכלת הפלייבוק בנייר שלהם
# העמדה מוחלת בתיקון כירורגי של ההוראה שלהם שעוסקת בנושא, ולא בסעיף חדש שיושב לצד נוסח סותר שהתקבל
# (n3c-matrix-cases.md, "הכלת העמדה בנייר שלהם"). הקשר בין סעיף חדש לפסקה קיימת נגזר קודם מהפלייבוק (אותו כלל, או
# כלל קשור ב-related_rule_ids), ואחר כך ממילון כללי של תפקידי סעיף שקיימים בכל סוג הסכם (אחריות, קבלני משנה והסבה,
# החזרה בסיום, הפרה וסיום, ביקורת): (עוגן: הנושא, סימן סותר: נוסח שלהם שסותר עמדה שנכנסה בסעיף חדש), בעברית ובאנגלית.
# ממצא שנבדק ונמצא תקין נרשם ב-checks_reviewed.
CONTAIN_TOPICS = {
    "אחריות ושיפוי": (
        r"הגבלת (?:ה)?אחריות|תקר[הת]|מוגבלת ל|נזק (?:עקיף|תוצאתי)|אחריות(?:ו)? (?:ו)?שיפוי|ישפה|שיפוי|"
        r"limitation of liability|liabilit[^.\n]{0,40}(?:limited|cap|exceed)|indirect|consequential|indemnif",
        r"האחראי(?:ת)? הבלעדי|אחריות (?:מלאה|בלעדית|מוחלטת|בלתי מוגבלת)|(?:ב)?יחד ולחוד|בגין כל נזק|לכל נזק|"
        r"נזקים? (?:כבדים|עקיפים|תוצאתיים)|לרבות נזק (?:עקיף|תוצאתי)|ישפה[^.\n]{0,60}כל|"
        r"sole(?:ly)? (?:responsib|liab)|jointly and severally|unlimited liability|any and all (?:loss|damage|claim)|"
        r"including (?:indirect|consequential)"),
    "קבלני משנה, הסבה וגילוי לצד שלישי": (
        r"קבלני? משנה|מעבד(?:י)? משנה|להסב|הסבה|להמחות|subcontract|sub-?processor|\bassign",
        r"(?:לא|אין)[^.\n]{0,30}(?:י?מסור|יגלה|לגלות|יעביר|להעביר|ישתף|יסב|להסב|ימחה)[^.\n]{0,60}"
        r"(?:צד (?:שלישי|ג)|לכל (?:אדם|גורם)|לאחר)|לא (?:יעסיק|ייעזר|יתקשר)[^.\n]{0,40}(?:קבלני? משנה|מעבד)|"
        r"סודיות (?:מלאה|מוחלטת)|shall not (?:disclose|transfer|subcontract|assign|share)[^.\n]{0,60}"
        r"(?:third part|any person|any other)"),
    "החזרה והשמדה בסיום": (
        r"יחזיר|השבה|ימחק|מחיק|השמד|\breturn|delet|destroy",
        r"(?:מיד|לאלתר|מיידית|immediately)[^.\n]{0,40}(?:יחזיר|ישיב|מחק|ימחק|מחיק|השמד|return|delet|destroy)|"
        r"(?:יחזיר|ישיב|מחק|ימחק|מחיק|השמד|return|delet|destroy)[^.\n]{0,40}(?:מיד|לאלתר|מיידית|immediately)"),
    "הפרה וסיום": (
        r"הפרה יסודית|תקופת תיקון|לתקן את ההפרה|שימוע|material breach|cure period",
        r"הפרה יסודית|תנאי (?:מהותי|עיקרי)|fundamental breach|material term|of the essence"),
    "ביקורת": (
        r"ביקורת|audit|inspect",
        r"במתקני|באתרי|בחצרי|בחצרות|on-?site|premises|ללא הודעה|without notice"),
}
# סוג הסעיף שבו נוסח סותר נספר: מילה של חבות בפסקה עצמה
CONTAIN_CONTEXT = {
    "אחריות ושיפוי": r"(?<![א-ת])[ובלמהש]{0,2}(?:אחריות|אחראי|אחראית|ישפה|תשפה|לשפות|שיפוי|יפצה|תפצה|לפצות|פיצוי|חבות|חב)"
                     r"(?![א-ת])|liab|indemn|compensat|reimburs",
}
KEEPS_THEIRS = ("accept",)


def _rule_titles(core):
    out = {}
    for key in ("clauses", "rules"):
        for r in (core or {}).get(key) or ():
            if isinstance(r, dict) and (r.get("id") or r.get("rule_id")):
                out[r.get("id") or r.get("rule_id")] = r
    return out


def _explicit_on(d, state):
    if (d.get("user_decision") or {}).get("answer_kind") == "explicit":
        return True
    cid = str(d.get("id"))
    for q in state.get("user_decisions") or ():
        if isinstance(q, dict) and q.get("answer_kind") == "explicit" and cid in {str(x) for x in q.get("applies_to") or ()}:
            return True
    for w in state.get("deliberate_concessions") or ():
        if isinstance(w, dict) and str(w.get("clause_ref")) == cid and \
                (w.get("user_decision") or {}).get("answer_kind") == "explicit":
            return True
    return False


def review_containment(out, theirs, decisions, state, core, mode=None):
    """CONTAIN_TOPIC_NOT_EDITED: סעיף חדש (insert_paragraph, N1) מחיל עמדה בנושא שפסקה קיימת שלהם כבר עוסקת בו,
    או שנוסח שלה סותר אותה, והפסקה הזו התקבלה כמו שהיא (accept או ויתור מכוון). העמדה צריכה לעבור לתיקון כירורגי של
    הפסקה, או שגם הפסקה מתוקנת (סריקת סתירות).
    CONTAIN_CONCESSION_UNDECIDED: ויתור על קו אדום בלי הכרעה מפורשת של המשתמש: קבלה של נוסח שלהם שסווג אדום, או
    ויתור מכוון בכלל קריטי או walk_away. ויתור מכוון בכלל שאינו כזה מותר בתגובה ממוקדת, ומתועד בקובץ הפנימי בלבד."""
    state = state or {}
    rules = _rule_titles(core)
    rel = _related_map(core)
    blocking = mode != "work"
    kept = [d for d in decisions if d.get("op") in KEEPS_THEIRS and isinstance(d.get("para"), int)
            and d.get("para") < len(theirs)]
    for n in decisions:
        if n.get("op") != "insert_paragraph":
            continue
        ntext = " ".join(str(n.get(k) or "") for k in ("text", "new_text", "new"))
        ntext += " " + " ".join(str((rules.get(r) or {}).get("title") or "") for r in n.get("rule_ids") or ())
        topics = [t for t, (anchor, _) in CONTAIN_TOPICS.items() if re.search(anchor, ntext, re.I)]
        nrules = set(n.get("rule_ids") or ())
        for d in kept:
            if _reviewed(state, "CONTAIN_TOPIC_NOT_EDITED", d.get("para")) or _explicit_on(d, state):
                continue
            t = theirs[d["para"]]
            why = None
            shared = nrules & set(d.get("rule_ids") or ())
            linked = {x for r in nrules for x in rel.get(r) or ()} & set(d.get("rule_ids") or ())
            if shared:
                why = "אותו כלל (%s)" % ", ".join(sorted(shared))
            elif linked and d.get("their_track") in ("red", "yellow"):
                why = "כלל קשור בפלייבוק (%s), והנוסח שלהם בו אינו בירוק" % ", ".join(sorted(linked))
            for topic in topics:
                # בדיקת סוג הסעיף: נוסח סותר נספר רק בפסקה שהיא באמת מאותו סוג (למשל הצהרה על "נזקים כבדים" בלי
                # אחריות, שיפוי או פיצוי אינה סעיף אחריות)
                ctx = CONTAIN_CONTEXT.get(topic)
                if ctx and not re.search(ctx, t, re.I):
                    continue
                m = re.search(CONTAIN_TOPICS[topic][1], t, re.I)
                if m:
                    why = "נוסח שסותר את הסעיף החדש בנושא %s: \"%s\"" % (topic, m.group(0))
                    break
            if why:
                finding(out, "CONTAIN_TOPIC_NOT_EDITED", "הסעיף החדש %s מחיל עמדה, והפסקה %s, שעוסקת באותו נושא (%s), התקבלה "
                        "כמו שהיא. להחיל את העמדה בתיקון כירורגי של הפסקה הקיימת, או לתקן גם אותה; ויתור על הפסקה אינו "
                        "חי לצד סעיף חדש שלנו באותו נושא, וסעיף חדש מוסיפים רק לנושא שאף הוראה בנייר שלהם אינה עוסקת בו" % (n.get("id"), d.get("id"), why), d.get("id"),
                        blocking=blocking)
    for d in kept:
        conceded = d.get("tier") == "deliberate_concession"
        rs = [rules.get(r) or {} for r in d.get("rule_ids") or ()]
        heavy = any(str(r.get("importance") or "").lower() == "critical" or r.get("walk_away") is True for r in rs)
        if not ((conceded and heavy) or d.get("their_track") == "red"):
            continue
        if _explicit_on(d, state) or _reviewed(state, "CONTAIN_CONCESSION_UNDECIDED", d.get("para")):
            continue
        finding(out, "CONTAIN_CONCESSION_UNDECIDED", "הנוסח שלהם התקבל כמו שהוא (%s) בכלל %s, %s, בלי הכרעה מפורשת של "
                "המשתמש. ויתור על קו אדום אינו נעשה בשקט, גם לא בתגובה ממוקדת: תיקון כירורגי, נקודה לשיחה, או \"נדרשת "
                "הכרעתך\" בהכרעה מפורשת" % ("ויתור מכוון" if conceded else "קבלה",
                                             ", ".join(d.get("rule_ids") or ()) or "?",
                                             "שהנוסח שלהם בו אדום" if d.get("their_track") == "red"
                                             else "שהוא קו אדום (חשיבות קריטית או walk_away)"), d.get("id"),
                blocking=blocking)


# --------------------------------------------------------------------------- סעיפים קשורים (רף, פריט 10)
# הערה על סעיף אחד חלה, באותה תכלית ובנוסח דומה, על הסעיפים הקשורים: אותו נוסח שחוזר בפסקה אחרת, הפניה לסעיף
# שתוקן, וכללים קשורים בפלייבוק (related_rule_ids במודל). סעיף קשור שהושאר בכוונה נרשם בהכרעה, ב-dependents, עם
# {"para", "keep": true, "reason"}, או מקבל הכרעה משלו (dependents: {"para", "decision"}).
RELATED_OPS = ("replace", "replace_span", "delete_paragraph", "insert_paragraph")
RELATED_STOP = set("""של את על עם או כל לא אם כי גם זה זו אשר יהיה תהיה יהיו לפי בין עד כן אלה אותו אותה הוא היא הם
לרבות ככל וכן מכל כלשהו כלשהי בכל הספק המזמין הלקוח החברה הצד הצדדים ההסכם הסכם נספח בנספח זה ידי the and of to in or
a an any all shall be by for with this that such as is are any other its their
יובהר מובהר יודגש לעיל להלן כמפורט בהתאם לצורך במסגרת אין""".split())


# הנושא של כלל, מהכותרת שלו בפלייבוק (title בגרעין, topic_name במודל): פסקה שלא נגענו בה, שיש בה שתיים ממילות
# הכותרת או יותר, עוסקת באותו נושא. כך הנושא בא מהפלייבוק של סוג ההסכם, ולא ממילון של סוג הסכם אחד
_HE_PREFIX = re.compile(r"^[והבלמשכ](?=[א-ת]{4,})")


def _norm_token(w):
    w = _HE_PREFIX.sub("", w.lower().strip("\"'׳״,.;:()"))
    return re.sub(r"[התםן]$", "", w) if re.match(r"[א-ת]", w) and len(w) > 4 else w


def _title_tokens(core, rule_ids, stop):
    rules = _rule_titles(core)
    out = set()
    for r in rule_ids or ():
        t = (rules.get(r) or {}).get("title") or (rules.get(r) or {}).get("topic_name") or ""
        out |= {_norm_token(w) for w in re.findall(r"[א-ת\w]{4,}", t) if w.lower() not in stop}
    return {w for w in out if len(w) >= 3}


RELATED_BACKREF = re.compile(r"^\s*(?:במקרה כאמור|כאמור לעיל|כאמור|בנסיבות אלה|לצורך כך|in such (?:case|event)|as aforesaid)", re.I)


def attach_related(core, core_path):
    """related_rule_ids של כל כלל, מהמודל שליד הגרעין (playbook-model.json באותה תיקייה), ל-core["_related"]."""
    if not isinstance(core, dict) or not core_path or core.get("_related"):
        return core
    mp = os.path.join(os.path.dirname(os.path.abspath(core_path)), "playbook-model.json")
    model = load(mp) if os.path.exists(mp) else None
    if isinstance(model, dict):
        core["_related"] = {r.get("rule_id") or r.get("id"): list(r.get("related_rule_ids") or [])
                            for r in model.get("rules") or () if isinstance(r, dict)}
    return core


def _related_map(core):
    """{rule_id: [rule_id]} מ-related_rule_ids: בגרעין (_related, שהשער טוען מהמודל שלצדו) או בכללי המודל."""
    out = dict((core or {}).get("_related") or {})
    for key in ("clauses", "rules"):
        for r in (core or {}).get(key) or ():
            if isinstance(r, dict) and r.get("related_rule_ids"):
                out[r.get("id") or r.get("rule_id")] = list(r["related_rule_ids"])
    return out


def _key_phrases(text, stop=RELATED_STOP):
    """רצפים של שלוש מילים משמעותיות מהנוסח שנמחק או הוחלף: הם הנוסח שחוזר בסעיפים קשורים."""
    words = re.findall(r"[^\s,.;:()‎‏]+", text or "")
    sig = lambda w: len(w) >= 3 and w.lower() not in stop and w[1:] not in stop  # noqa: E731
    out = []
    for i in range(len(words) - 2):
        tri = words[i:i + 3]
        if sum(1 for w in tri if sig(w)) >= 2 and (sig(tri[0]) or sig(tri[2])):
            out.append(" ".join(tri))
    return out


def deal_only_mode(state):
    """True כשהלקוח בחר לעבוד בלי פלייבוק: ביקורת לעסקה זו בלבד (positions_source.mode: deal_only)."""
    ps = (state or {}).get("positions_source")
    return isinstance(ps, dict) and ps.get("mode") == "deal_only"


def review_areo(out, decisions, state, mode=None):
    """AREO_LABEL_MISSING: הכרעה שמשנה נוסח או מעירה, בלי כלל בפלייבוק (rule_ids ריק), שאינה מסומנת כסעיף AREO
    (source_label: areo_proposal). בלי הסימון אין לה מירקור ותווית בקובץ העבודה (n4b-redlining-steps.md, שלב ג2)."""
    for d in decisions:
        if d.get("op") not in RELATED_OPS + ("comment_only",) or d.get("rule_ids") or d.get("structural")                 or d.get("conforming") or d.get("silent_change") or d.get("reply_to_comment"):
            continue
        if d.get("source_label") in ("areo_proposal", "הצעת Areo", "Areo proposal") or d.get("areo_clause") is True:
            continue
        # בלי פלייבוק (positions_source.mode: deal_only) כל הכרעה היא המלצה לעסקה זו, ולכן אין לה כלל: מספיקה תווית מקור
        # (שיקול מקצועי, דין, הסכם קודם, הוראת הלקוח) והיא עוברת. הכרעה בלי שום תווית מקור נשארת ממצא
        if deal_only_mode(state) and str(d.get("source_label") or "").strip():
            continue
        # רק הכרעה שהבסיס שלה הוא מסלול ב (דין, הסכם קודם, שיקול מקצועי): הכרעה בלי rule_ids ובלי בסיס אינה ראיה
        # שאין לנושא עמדה בפלייבוק
        label = str(d.get("source_label") or "")
        if d.get("decision_basis") not in ("Law", "CompanyPractice", "ExpertJudgment") and                 not label.startswith(("שיקול מקצועי", "דין", "הסכם קודם", "Professional judgment", "Law", "Prior")):
            continue
        if _reviewed(state or {}, "AREO_LABEL_MISSING", d.get("para")):
            continue
        finding(out, "AREO_LABEL_MISSING", "להכרעה %s אין כלל בפלייבוק, והיא אינה מסומנת כסעיף AREO (source_label: "
                "areo_proposal). כך עורך הדין אינו רואה שהיא הצעת Areo. / Decision %s has no playbook rule and is not "
                "marked as an Areo clause (source_label: areo_proposal)" % (d.get("id"), d.get("id")), d.get("id"),
                blocking=mode != "work")


def review_related(out, theirs, decisions, state, core, labels=None):
    """RELATED_UNHANDLED: הכרעה ששינתה סעיף, וסעיף קשור אליו נשאר בלי הכרעה משלו ובלי רישום שהושאר בכוונה (dependents
    עם reason). קשור, בכל סוג הסכם: (1) אותו נוסח (שלוש מילים רצופות מהנוסח שנמחק) בפסקה שלא נגענו בה; (2) אותו נושא
    לפי הכותרת של הכלל בפלייבוק; (3) הפניה לסעיף שתוקן, מפורשת או "במקרה כאמור"; (4) פסקה שהוכרעה על כלל קשור
    בפלייבוק (related_rule_ids), והנוסח שלהם בה אינו בירוק."""
    state = state or {}
    rel = _related_map(core)
    pos = (state.get("meta") or {}).get("position") or {}
    party = [re.sub(r"^(?:the|ה)\s*", "", str(x.get("term") or ""), flags=re.I) for x in pos.get("defined_terms_map") or ()
             if isinstance(x, dict) and x.get("term")]
    stop = RELATED_STOP | {w for t in party for w in re.findall(r"[א-ת\w]{3,}", t)}
    conceded = {d.get("para") for d in decisions if d.get("tier") == "deliberate_concession"}
    df = {}
    for t in theirs:
        for w in {_norm_token(x) for x in re.findall(r"[א-ת\w]{3,}", t or "")}:
            df[w] = df.get(w, 0) + 1
    # טיפול בסעיף קשור: הכרעה משלו, וגם קבלה מפורשת עם נימוק (internal_comment או reason) היא הכרעה
    touched = {d.get("para") for d in decisions if isinstance(d.get("para"), int) and (
        d.get("op") in RELATED_OPS + ("comment_only",)
        or (d.get("op") == "accept" and (d.get("internal_comment") or d.get("reason"))))}
    by_para = {}
    for d in decisions:
        if isinstance(d.get("para"), int):
            by_para.setdefault(d["para"], []).append(d)
    seen = set()
    for d in decisions:
        if d.get("op") not in RELATED_OPS or d.get("structural") or d.get("conforming"):
            continue
        p = d.get("para")
        handled = {x.get("para") for x in d.get("dependents") or () if isinstance(x, dict)
                   and (x.get("decision") or (x.get("keep") and x.get("reason")))}
        cands = {}
        old = d.get("old") or (theirs[p] if d.get("op") in ("replace", "delete_paragraph") and isinstance(p, int)
                               and p < len(theirs) else "")
        free = lambda i: i != p and i not in touched and i not in conceded and len((theirs[i] or "").split()) >= 8  # noqa: E731
        for ph in _key_phrases(old, stop):
            hits = [i for i, t in enumerate(theirs) if i != p and ph in t]
            if not hits or len(hits) > 4:
                continue  # נוסח שחוזר בכל ההסכם הוא נוסח כללי, ולא סעיף קשור
            for i in hits:
                if free(i):
                    cands.setdefault(i, 'אותו נוסח: "%s"' % ph)
        tokens = _title_tokens(core, d.get("rule_ids"), stop)
        # מילה שמופיעה ביותר מחמישית מהפסקאות היא מילה של ההסכם כולו (למשל שם הנושא של ההסכם עצמו), ולא סימן לנושא
        tokens = {w for w in tokens if df.get(w, 0) <= max(2, len(theirs) // 5)}
        if len(tokens) >= 2:
            for i, t in enumerate(theirs):
                if not free(i):
                    continue
                hit = tokens & {_norm_token(w) for w in re.findall(r"[א-ת\w]{3,}", t)}
                if len(hit) >= 2:
                    cands.setdefault(i, "אותו נושא בפלייבוק (%s)" % ", ".join(sorted(hit)))
        if isinstance(p, int):
            for i in range(p + 1, min(p + 4, len(theirs))):
                if free(i) and RELATED_BACKREF.search(theirs[i] or ""):
                    cands.setdefault(i, "מפנה לסעיף שתוקן (\"%s\")" % RELATED_BACKREF.search(theirs[i]).group(0).strip())
        lab = (labels or [None] * (len(theirs) + 1))[p] if isinstance(p, int) and labels and p < len(labels) else None
        if lab:
            rx = re.compile(r"(?:סעיף|סעיפים|בסעיף|לסעיף|section|clause)\s*" + re.escape(lab) + r"(?![\d.]*\d)", re.I)
            for i, t in enumerate(theirs):
                if free(i) and rx.search(t):
                    cands.setdefault(i, "הפניה לסעיף %s" % lab)
        rr = {x for r in d.get("rule_ids") or () for x in rel.get(r) or ()}
        if rr:
            for i, ds in by_para.items():
                if not free(i):
                    continue
                for o in ds:
                    if o.get("op") == "accept" and rr & set(o.get("rule_ids") or ()) and o.get("their_track") in ("red", "yellow"):
                        cands.setdefault(i, "כלל קשור בפלייבוק (%s)" % ", ".join(sorted(rr & set(o.get("rule_ids")))))
        group = d.get("cluster_id") or d.get("id")
        for i, why in sorted(cands.items()):
            if i in handled or (group, i) in seen or _reviewed(state, "RELATED_UNHANDLED", i):
                continue
            seen.add((group, i))
            ref = (labels[i] if labels and i < len(labels) and labels[i] else "פסקה %d" % i)
            finding(out, "RELATED_UNHANDLED", "ההכרעה %s שינתה סעיף, והסעיף הקשור %s (%s) נשאר בלי הכרעה. להחיל עליו את אותה "
                    "תכלית בנוסח דומה, או לרשום ב-dependents של ההכרעה שהוא הושאר בכוונה, עם reason. / Decision %s "
                    "changed a clause; the related clause %s was not handled: apply the same purpose there, or record it "
                    "in dependents as deliberately unchanged, with a reason" % (d.get("id"), ref, why, d.get("id"), ref),
                    d.get("id"), blocking=True)


# --------------------------------------------------------------------------- סתירה שנשארה אחרי העריכה (רף, פריטים 2 ו-10)
# אחרי שכל התיקונים חלים, כל סעיף שלא שינינו נסרק לנוסח שסותר את המשטר שהעריכה שלנו קבעה. הזוגות כלליים, לכל סוג
# הסכם, בעברית ובאנגלית: (סימן שהעריכה שלנו קבעה, נושא הפסקה שנבדקת או None, נוסח שסותר אותו). סתירה כזו מתוקנת
# כסעיף קשור (הכרעה משלה), או נרשמת ב-dependents של ההכרעה עם keep ו-reason, ואז היא מוסברת בבועה לצד השני.
POST_EDIT_PAIRS = (
    ("נוסח קפוא של מסמך או מדיניות",
     r"version in (?:effect|force) (?:on|at|as at)|as (?:in force|in effect) (?:on|at) the (?:date|effective)|"
     r"shall not (?:be )?(?:amend|chang|modif)\w* (?:unilaterally|without)|"
     r"בנוסח(?:ו|ה|ם)? (?:התקף|שבתוקף|שהיה בתוקף) (?:במועד|ביום)|לא (?:ישונה|ישונו|יעודכן|יעודכנו) (?:באופן חד.?צדדי|ללא|בלי)",
     None,
     r"as (?:amended|updated|modified|revised) (?:from time to time|periodically)|as updated periodically|"
     r"then[- ]current|from time to time (?:amend|updat|modif|revis)|"
     r"כפי (?:שי|שת)(?:עודכן|עודכנו|שונה|שונו) מעת לעת|כפי שיהיה בתוקף מעת לעת|בנוסח(?:ו|ה)? העדכני|כפי שיתעדכן"),
    ("הגבלת היקף או תדירות של ביקורת",
     r"(?:not|no) more (?:often )?than once (?:in|per|every|a)|once (?:per|a|in any|every) (?:year|calendar|twelve|12)|"
     r"by way of (?:written )?(?:reports?|questionnaires?)|לא יותר מפעם(?: אחת)? ב|פעם(?: אחת)? (?:בשנה|ב-?12 חודשים)|"
     r"בדרך של (?:בקשת )?(?:דוחות|דו\"חות|שאלון)",
     r"audit|inspect|ביקורת|בדיקה|לבדוק",
     r"at any time|without (?:prior )?notice|on (?:any )?suspicion|(?:if|where) (?:it|there) (?:is|has) (?:a )?"
     r"(?:suspicion|concern)|in its (?:sole|absolute) discretion|בכל עת|ללא הודעה|בלי הודעה|בעקבות חשש|בשל חשש|"
     r"לפי שיקול דעת(?:ו|ה)?(?: הבלעדי)?|(?:החלטת|קביעת)[^.;]{0,40}(?:תהיה )?(?:מכרעת|סופית)|כחלופה"),
    ("חריג של בלאי, אשם או פגם",
     r"fair wear and tear|reasonable wear|(?:caused by|due to|arising from) (?:its|their|the \w+'s) "
     r"(?:act|omission|fault|negligence)|בלאי סביר|בלאי רגיל|עקב מעשה או מחדל של(?:ו|ה|הם)|למעט[^.;]{0,40}(?:פגם|בלאי)",
     r"repair|damage|maintenance|restor|תיקון|תיקונים|נזק|נזקים|אחזקה|החזקה|לתקן",
     r"(?:all|any(?: and all)?) (?:repairs?|damages?|costs? of repair|loss)|כל (?:ה)?(?:נזקים|תיקונים|הוצאות|הקלקולים)|"
     r"את כל (?:ה)?(?:נזקים|תיקונים|הוצאות)|הנובעים מ(?:ה)?(?:שימוש|השכרת)"),
    ("איסור לצמצם שירות או תכונה",
     r"(?:will|shall) not (?:remove|reduce|degrade|materially reduce|discontinue)|לא (?:יסיר|יפחית|יצמצם|יפסיק)",
     None,
     r"discontinu|withdraw (?:the|a|any) (?:service|feature)|end[- ]of[- ]life|deprecat|"
     r"(?:רשאי|זכאי)[^.;]{0,30}(?:להפסיק|לצמצם|להסיר)"),
)


def review_post_edit(out, theirs, decisions, state, mode=None, labels=None):
    """POST_EDIT_CONTRADICTION: אחרי כל התיקונים, סעיף שלא שינינו (התקבל, נשאר לשיחה, או בלי הכרעה) שנוסחו סותר
    משטר שהעריכה שלנו קבעה (POST_EDIT_PAIRS). חוסם במצב משלוח (אזהרה במצב עבודה), עד הכרעה משלו או רישום ב-dependents
    של ההכרעה, עם keep ו-reason."""
    state = state or {}
    blocking = mode != "work"
    changed = {d.get("para") for d in decisions if d.get("op") in RELATED_OPS and isinstance(d.get("para"), int)}
    view, gone = result_view(theirs, decisions)
    new_text = {}
    for src, t, ours in view:
        if ours:
            new_text.setdefault(src, []).append(t)
    seen = set()
    for d in decisions:
        if d.get("op") not in RELATED_OPS or d.get("structural"):
            continue
        p = d.get("para") if d.get("op") != "insert_paragraph" else ("ins", d.get("after_para"))
        ours_txt = " ".join(str(d.get(k) or "") for k in ("new", "new_text", "text"))
        before = theirs[p] if isinstance(p, int) and p < len(theirs) else ""
        handled = {x.get("para") for x in d.get("dependents") or () if isinstance(x, dict)
                   and (x.get("decision") or (x.get("keep") and x.get("reason")))}
        for name, sig, topic, contra in POST_EDIT_PAIRS:
            # המשטר נקבע בעריכה שלנו: הסימן בנוסח שהכנסנו, ולא בנוסח שהיה שם קודם
            if not re.search(sig, ours_txt, re.I) or re.search(sig, before, re.I):
                continue
            for i, t in enumerate(theirs):
                if i == p or i in changed or i in gone or i in handled or (name, i) in seen:
                    continue
                if topic and not re.search(topic, t or "", re.I):
                    continue
                m = re.search(contra, t or "", re.I)
                if not m or _reviewed(state, "POST_EDIT_CONTRADICTION", i):
                    continue
                seen.add((name, i))
                ref = labels[i] if labels and i < len(labels) and labels[i] else "פסקה %d" % i
                finding(out, "POST_EDIT_CONTRADICTION",
                        "ההכרעה %s קבעה %s, והסעיף %s נשאר עם נוסח שסותר אותה: \"%s\". לתקן אותו כסעיף קשור (הכרעה "
                        "משלו), או לרשום ב-dependents של ההכרעה keep עם reason ולהסביר בבועה. / Decision %s set a rule "
                        "(%s); clause %s still contradicts it (\"%s\"): fix it as a related clause, or record it in "
                        "dependents with keep and a reason, and explain it in the comment"
                        % (d.get("id"), name, ref, m.group(0), d.get("id"), name, ref, m.group(0)),
                        d.get("id"), blocking=blocking)


# --------------------------------------------------------------------------- נושאים רגישים: פריט גלוי, לא חסימה
# בכל סוג הסכם, בכל צד ובכל דין: שינוי דין או פורום, העלאת מחיר אוטומטית או חידוש אוטומטי, העברת נטל מס, אחריות או
# שיפוי בלי תקרה, ומידע מסוג מיוחד. הם מוחלים לפי הפלייבוק כמו כל נושא. נושא כזה שנשאר בלי הכרעה לפי כלל בפלייבוק,
# והפניה לחקיקה בשמה שהפלייבוק שותק עליה, הם פריט גלוי ללקוח (NO_APPROVED_SOURCE), ולא אישור עורך דין
HIGH_RISK = (
    ("דין או פורום", r"governing law|governed by|exclusive jurisdiction|courts? of|arbitrat|venue|הדין החל|"
                     r"יחול(?:ו)? (?:ה)?דין|דיני מדינת|סמכות (?:ה)?שיפוט|בוררות"),
    ("חידוש אוטומטי או העלאת מחיר", r"auto(?:matic(?:ally)?)?[- ]?renew|renew(?:s|ed|al)? automatically|"
                                    r"(?:increase|uplift|adjust)\w*[^.;]{0,50}\d+(?:\.\d+)?\s?%|\bCPI\b|indexation|"
                                    r"יתחדש(?:ו)? (?:באופן )?אוטומטי|חידוש אוטומטי|(?:יעודכנו|יעלו|יועלו|תוספת)[^.;]{0,40}\d+\s?%|"
                                    r"הצמדה למדד"),
    ("העברת נטל מס", r"withholding|gross[- ]?up|taxes?[^.;]{0,40}(?:borne|paid|payable) by|ניכוי (?:מס )?במקור|גילום|"
                     r"המס(?:ים)? (?:יחול|יחולו|ישולם|ישולמו) על"),
    ("אחריות או שיפוי בלי תקרה", r"(?:indemnif|liab)\w*[^.;]{0,90}(?:unlimited|without (?:any )?(?:limit|cap)|"
                                 r"not (?:be )?subject to (?:the|any) (?:cap|limit))|uncapped|unlimited liability|"
                                 r"(?:אחריות|שיפוי|ישפה)[^.;]{0,60}(?:ללא הגבלה|ללא תקרה|בלתי מוגבל)|"
                                 r"לא (?:תחול|יחולו)[^.;]{0,30}(?:הגבלת|תקרת) (?:ה)?אחריות"),
    ("מידע מסוג מיוחד", r"special categor|sensitive (?:personal )?(?:data|information)|health (?:data|information)|"
                        r"protected health|biometric|genetic|criminal (?:record|offen)|מידע (?:רגיש|רפואי|בריאותי|"
                        r"ביומטרי|גנטי)|בעל רגישות מיוחדת"),
)
# הפניה לחקיקה או לתקנה בשמה (מבנה, לא רשימה): שם שנגמר ב-Act, Law, Regulation(s), Directive, Code או Rules ואחריו שנה
# או מספר; הפניה לאקט לפי מספר; "בהתאם ל-<שם>" לפני ראשי תיבות באותיות רישיות; ובעברית "חוק/תקנות/צו" עם שנה או נוסח
# עברי של תאריך. כל הפניה כזו שאין עליה עמדה בפלייבוק מסומנת "אין עמדה, לסמן לעורך דין"
SECTOR_LAW = re.compile(
    r"\b(?:[A-Z][\w'’&.\-]*\s+){1,6}(?:Act|Law|Regulations?|Directive|Code|Rules)\b(?:\s+(?:of\s+)?\(?\d{4}\)?|\s+No\.?\s*\d+)|"
    r"\bRegulation\s*\((?:EU|EC)\)\s*\d{2,4}/\d+|"
    r"\b(?:compl(?:y|iance|ies)\s+with|subject\s+to|governed\s+by|pursuant\s+to|in\s+accordance\s+with)\s+(?:the\s+)?[A-Z]{3,8}\b|"
    r"(?:חוק|תקנות|צו)\s+[^\n.;,]{2,50}?,?\s*(?:ה?ת[א-ת\"״']{1,6}[-–]\d{4}|\d{4})")
CHANGING_OPS = ("replace", "replace_span", "delete_paragraph")


HIGH_RISK_EN = {"דין או פורום": "governing law or forum", "חידוש אוטומטי או העלאת מחיר": "automatic renewal or price increase",
                "העברת נטל מס": "tax withholding or gross-up", "אחריות או שיפוי בלי תקרה": "uncapped liability or indemnity",
                "מידע מסוג מיוחד": "sensitive data", "הפניה לחקיקה": "reference to legislation"}


def review_high_risk(out, theirs, decisions, state, core, mode=None, labels=None):
    """NO_APPROVED_SOURCE: נושא רגיש, או הפניה לחקיקה בשמה, שנשארו כמו שהם בלי הכרעה לפי כלל בפלייבוק. אין כאן חסימה
    ואין אישור עורך דין (כלל יסוד 6): זה פריט גלוי ללקוח, "AREO לא מצאה מקור מורשה לנקודה זו", עם צעד אחד הלאה, ולעולם
    לא מתמלא מהזיכרון (כלל יסוד 5). פסקה שיש עליה הכרעה לפי כלל בפלייבוק (rule_ids), או שהוחלפה, אינה פריט."""
    state = state or {}
    by_para = {}
    for d in decisions:
        if isinstance(d.get("para"), int):
            by_para.setdefault(d["para"], []).append(d)
    core_txt = json.dumps(core or {}, ensure_ascii=False)
    for i, t in enumerate(theirs):
        ds = by_para.get(i, [])
        if any(d.get("op") in CHANGING_OPS or d.get("rule_ids") for d in ds):
            continue
        ref = labels[i] if labels and i < len(labels) and labels[i] else "פסקה %d" % i
        hit = None
        for name, rx in HIGH_RISK:
            m = re.search(rx, t or "", re.I)
            if m:
                hit = (name, m.group(0)[:40])
                break
        if not hit:
            for m in SECTOR_LAW.finditer(t or ""):
                if m.group(0).lower() not in core_txt.lower():
                    hit = ("הפניה לחקיקה", m.group(0)[:40])
                break
        if hit:
            finding(out, "NO_APPROVED_SOURCE",
                    "AREO לא מצאה מקור מורשה לנקודה זו: %s (%s, \"%s\"). הצעד הבא: להוסיף לתיקיית ההסכמים של החברה הסכם "
                    "שמסדיר אותה, או לאשר עמדה בפלייבוק. / AREO did not find an approved source for this point: %s (%s). "
                    "Next step: add to the company's agreements folder an agreement that covers it, or confirm a position "
                    "in the playbook" % (hit[0], ref, hit[1], HIGH_RISK_EN.get(hit[0], hit[0]), ref),
                    (ds[0].get("id") if ds else "para %d" % i), blocking=False)


def review_law_coverage(out, decisions, state, core, mode=None):
    """NO_APPROVED_SOURCE מהפלייבוק עצמו: הפריט נוצר רק כשהגרעין נושא נקודה כזו, כלל עם `no_approved_source` (ו-
    `no_source_note`, ההסבר והצעד הבא), או פריט ב-`statutory_override` שמסומן כך. אין בקוד שום הוראה כופה של דין, ואין
    יותר רצפות דין בפלייבוק: גרעין בלי השדות האלה אינו מפיק פריט (אין פריט בכל עסקה). הפריט גלוי ללקוח, אינו חוסם
    ואינו ממולא מהזיכרון (כלל יסוד 5 ו-6)."""
    core = core if isinstance(core, dict) else {}
    for r in core.get("clauses") or core.get("rules") or []:
        if not isinstance(r, dict):
            continue
        rid = r.get("id") or r.get("rule_id") or "?"
        note = r.get("no_source_note")
        hit = bool(r.get("no_approved_source")) or any(
            isinstance(x, dict) and x.get("no_approved_source") for x in r.get("statutory_override") or [])
        if not hit:
            continue
        if not isinstance(note, str) or not note.strip():
            note = next((x.get("no_source_note") for x in r.get("statutory_override") or []
                         if isinstance(x, dict) and x.get("no_source_note")), "")
        topic = r.get("title") or r.get("topic_name") or rid
        finding(out, "NO_APPROVED_SOURCE",
                "AREO לא מצאה מקור מורשה לנקודה זו: %s. %sהצעד הבא: להוסיף לפלייבוק את המקור המאושר, או לאשר עמדה "
                "בפלייבוק. / AREO did not find an approved source for this point: %s"
                % (topic, (note.strip() + " ") if note else "", topic), rid, blocking=False)


def review_definitions(out, theirs, decisions, state, mode=None, labels=None):
    """DEF_USES_UNTRACED: הכרעה שמשנה פסקה שמגדירה מונח (מצמצמת או מרחיבה אותו). כל פסקה אחרת שמשתמשת במונח
    מושפעת, גם הגנות שלנו שנשענות עליו. כל שימוש כזה צריך הכרעה משלו, או רישום ב-dependents עם keep ו-reason, וההשפעה
    מוסברת בבועה. חוסם במצב משלוח (אזהרה במצב עבודה)."""
    state = state or {}
    blocking = mode != "work"
    for d in decisions:
        p = d.get("para")
        if d.get("op") not in ("replace", "replace_span") or not isinstance(p, int) or p >= len(theirs):
            continue
        terms = _terms_in(theirs[p])
        if not terms:
            continue
        # שינוי שאינו נוגע בהגדרה עצמה (תיקון כינוי, פיסוק) אינו משנה את המשמעות; וגם שינוי שאינו בתוך משפט ההגדרה
        if d.get("regime") == "none":
            continue
        if d.get("op") == "replace_span" and d.get("old") and not any(
                _term_rx(tm).search(d["old"]) or d["old"] in theirs[p][max(0, theirs[p].find(tm) - 10):
                                                                       theirs[p].find(tm) + len(tm) + 200]
                for tm in terms if tm in theirs[p]):
            continue
        handled = {x.get("para") for x in d.get("dependents") or () if isinstance(x, dict)
                   and (x.get("decision") or (x.get("keep") and x.get("reason")))}
        decided = {x.get("para") for x in decisions if isinstance(x.get("para"), int) and x is not d
                   and x.get("op") in RELATED_OPS}
        for term in sorted(terms):
            trx = _term_rx(term)
            uses = [j for j, t in enumerate(theirs) if j != p and trx.search(t or "")]
            if len(uses) > 40:
                continue   # מונח שמופיע בכל ההסכם (שם הצד, "ההסכם"): השינוי בו נבדק ביד
            open_uses = [j for j in uses if j not in handled and j not in decided
                         and not _reviewed(state, "DEF_USES_UNTRACED", j)]
            if open_uses:
                # dependents מצפה למספר הפסקה (para); המספר בהסכם, כשיש, בא בסוגריים
                refs = ", ".join("%d%s" % (j, " (%s)" % labels[j] if labels and j < len(labels) and labels[j] else "")
                                 for j in open_uses[:12])
                finding(out, "DEF_USES_UNTRACED",
                        "ההכרעה %s משנה את ההגדרה \"%s\". השימושים במונח (פסקאות %s) לא נבדקו: לכל שימוש הכרעה, או רישום "
                        "ב-dependents עם keep ו-reason, כולל ההשפעה על הגנות שלנו שנשענות על המונח, וההשפעה מוסברת "
                        "בבועה. / Decision %s changes the definition of \"%s\"; its uses (%s) were not traced"
                        % (d.get("id"), term, refs, d.get("id"), term, refs), d.get("id"), blocking=blocking)


def this_round(state, x):
    """רשומה של הסבב הנוכחי: בלי round, או עם round של meta.round_number. רשומות של סבב קודם נשמרות בקובץ המצב תחת
    הסבב שלהן (negotiation_state.py write, S1d), ומספרי הפסקאות בהן הם של הטיוטה של אותו סבב."""
    r = x.get("round") if isinstance(x, dict) else None
    return r is None or str(r) == str((state.get("meta") or {}).get("round_number"))


def _reviewed(state, code, para):
    """בדיקה מבנית היא היוריסטיקה. עורך הדין שבדק ומצא שההפניה תקינה רושם זאת ב-checks_reviewed, עם נימוק."""
    return any(isinstance(x, dict) and x.get("code") == code and x.get("para") == para and x.get("reason")
               and this_round(state, x) for x in state.get("checks_reviewed") or [])


def review_2210(out, theirs, decisions, state, core, received):
    meta = state.get("meta") or {}
    by_para = {}
    for d in decisions:
        if isinstance(d.get("para"), int):
            by_para.setdefault(d["para"], []).append(d)
    view, gone = result_view(theirs, decisions)
    vtexts = [t for _, t, _ in view]

    # כלל 1: שלמות מבנית
    for k, (src, t, ours) in enumerate(view):
        if PROVISO_REF.search(t):
            window = " ".join(vtexts[max(0, k - 1):k + 2])
            if not PROVISO_MARK.search(window):
                i = src if isinstance(src, int) else src[1]
                before = " ".join(theirs[max(0, i - 1):i + 2])
                caused = (bool(PROVISO_MARK.search(before)) or ours) and not _reviewed(state, "STRUCT_ORPHAN_PROVISO", i)
                finding(out, "STRUCT_ORPHAN_PROVISO", "הפניה לסייג (\"%s\") בלי סייג שהיא מפנה אליו בנוסח המתקבל"
                        % PROVISO_REF.search(t).group(0), "פסקה %s" % (i,), blocking=caused)
        nxt_text = vtexts[k + 1] if k + 1 < len(vtexts) else ""
        if ours and (DANGLING_MID.search(t) or (DANGLING_END.search(t) and not LIST_ITEM.search(nxt_text))):
            finding(out, "STRUCT_DANGLING_CONJ", "בנוסח שלנו נשארה מילת חיבור (\"או\", \"and\") בלי פריט אחריה",
                    "פסקה %s" % (src if isinstance(src, int) else src[1],), blocking=True)
    alive = [i for i in range(len(theirs)) if i not in gone]
    for p in sorted(gone):
        nxt = next((i for i in alive if i > p), None)
        prv = next((i for i in reversed(alive) if i < p), None)
        if nxt is not None and BACKREF.search(theirs[nxt]) and not _reviewed(state, "STRUCT_BACKREF", nxt):
            finding(out, "STRUCT_BACKREF", "הפסקה שאחרי הפסקה שמחקנו מפנה \"לעיל\", ומה שהיא הפנתה אליו נמחק",
                    "פסקה %d" % nxt, blocking=True)
        last_item = nxt is None or not LIST_ITEM.search(theirs[nxt])
        if prv is not None and last_item and LIST_ITEM.search(theirs[p]):
            if LEAD_IN.search(theirs[prv]) and all(j in gone for j in range(prv + 1, p + 1)):
                finding(out, "STRUCT_LIST_EMPTY", "כל פריטי הרשימה נמחקו, ונשאר משפט הפתיחה שלה (\"%s\")"
                        % theirs[prv][-40:], "פסקה %d" % prv, blocking=True)
            elif TAIL_CONJ.search(theirs[prv]):
                finding(out, "STRUCT_DANGLING_CONJ", "מחקנו את הפריט האחרון ברשימה, ו\"או\" או \"and\" נשארו לפני "
                        "פריט שכבר אינו קיים", "פסקה %d" % prv, blocking=True)
    for d in decisions:
        txt = (d.get("text") if d.get("op") == "insert_paragraph" else d.get("new")) or ""
        if PROVISO_MARK.match(txt.strip()) and OBLIGATION.search(txt):
            finding(out, "STRUCT_PROVISO_ROLE", "נוסח שהכנסנו כסייג כולל התחייבות או איסור. התחייבות מקבלת פסקה "
                    "משלה, וסייג צריך לסייג", d.get("id"))

    # כלל 2: סעיפים תלויים
    labels = numbered_labels(received)
    for d in decisions:
        p = d.get("para")
        if d.get("regime") in (None, "") and d.get("op") in ("replace", "replace_span", "delete_paragraph") and \
                isinstance(p, int) and 0 <= p < len(theirs):
            spans = [m.span() for rx in DEF_PATTERNS for m in rx.finditer(theirs[p])]
            at = theirs[p].find(d.get("old") or "\x00") if d.get("op") == "replace_span" else -1
            touched_def = spans and (d.get("op") != "replace_span" or (
                at >= 0 and any(a0 < at + len(d["old"]) and at < b0 for a0, b0 in spans)))
            if touched_def:
                finding(out, "REGIME_UNDECLARED", "ההכרעה נוגעת בהגדרה: לקבוע regime (definition, או none כשהמשמעות "
                        "אינה משתנה), כדי שהסעיפים התלויים ייבדקו", d.get("id"))
        deps = dependents_of(d, theirs, labels)
        if not deps:
            continue
        handled, no_reason = set(), []
        for x in d.get("dependents") or []:
            if not isinstance(x, dict) or not isinstance(x.get("para"), int):
                continue
            if x.get("decision") or (x.get("keep") and x.get("reason")):
                handled.add(x["para"])
            elif x.get("keep"):
                no_reason.append(x["para"])
        missing = [j for j in deps if j not in handled and not any(e is not d for e in by_para.get(j, []))]
        missing = [j for j in missing if j not in no_reason]
        if no_reason:
            finding(out, "DEPENDENT_KEEP_NO_REASON", "סעיף תלוי שהוחלט להשאיר בלי נימוק: פסקאות %s"
                    % ", ".join(map(str, no_reason)), d.get("id"), blocking=True)
        if missing:
            finding(out, "DEPENDENT_UNDECIDED", "ההכרעה משנה משטר (%s), ויש סעיפים תלויים בלי הכרעה: פסקאות %s"
                    % (d.get("regime") or "definition", ", ".join(map(str, missing))), d.get("id"), blocking=True)

    # כלל 3: בדיקת התוצאה של כל כלל שהוחל
    rules = _rule_index(core)
    applied = {r for d in decisions for r in d.get("rule_ids") or []}
    done = {(x.get("rule_id"), x.get("id")): x for x in state.get("post_checks_done") or [] if isinstance(x, dict)
            and this_round(state, x)}
    annex_at = next((k for k, t in enumerate(vtexts) if re.match(r"^\s*(?:נספח|Annex|Schedule|Exhibit|Appendix)\s", t)),
                    len(vtexts))
    for rid in sorted(applied):
        rule = rules.get(rid) or {}
        for pc in rule.get("post_checks") or []:
            if not isinstance(pc, dict):
                continue
            block = pc.get("on_fail") == "block" or (pc.get("on_fail") is None and
                                                      str(rule.get("importance", "")).lower() == "critical")
            scope = pc.get("scope") or "whole_agreement"
            if scope == "definitions":
                text = "\n".join(t for t in vtexts if _terms_in(t))
            elif scope == "annexes":
                text = "\n".join(vtexts[annex_at:])
            else:
                text = "\n".join(vtexts)
            cond = pc.get("pass_when")
            where = "%s/%s" % (rid, pc.get("id", "?"))
            if isinstance(cond, dict):
                bad = [x for x in cond.get("absent") or [] if re.search(x, text, re.I)]
                lack = [x for x in cond.get("present") or [] if not re.search(x, text, re.I)]
                if bad or lack:
                    finding(out, "POST_CHECK_FAILED", "בדיקת התוצאה של הכלל נכשלה (%s)%s%s" % (
                        pc.get("intent") or "", ": נמצא %s" % ", ".join(bad) if bad else "",
                        ": חסר %s" % ", ".join(lack) if lack else ""), where, blocking=block)
            else:
                rec = done.get((rid, pc.get("id")))
                if rec is None:
                    finding(out, "POST_CHECK_MANUAL", "בדיקת תוצאה שאינה אוטומטית, ולא נרשמה ב-post_checks_done: %s"
                            % (pc.get("intent") or cond or ""), where)
                elif rec.get("result") == "fail":
                    finding(out, "POST_CHECK_FAILED", "בדיקת התוצאה נרשמה כנכשלת: %s" % (pc.get("intent") or ""),
                            where, blocking=block)

    # כלל 4: עוגני זמן
    known = {(x.get("para"), x.get("issue")) for x in state.get("time_anchors") or []
             if isinstance(x, dict) and x.get("status") in ("answered", "accepted", "fixed") and this_round(state, x)}
    for a in time_anchors(theirs):
        if (a["para"], a["issue"]) not in known:
            finding(out, "TIME_ANCHOR", "עוגן זמן %s בנייר שלהם (\"%s\"): שאלה לפני ההכרעה, ורישום ב-time_anchors"
                    % ("שכבר עבר" if a["issue"] == "past" else "ריק", a["text"][:80]), "פסקה %d" % a["para"],
                    blocking=True)

    # כלל 5: מונחים עמומים בנוסח שלנו
    from common import vague_terms
    for d, txt in our_texts(decisions):
        for f in vague_terms.undefined(txt):
            finding(out, "VAGUE_TERM", "מונח עמום בנוסח שלנו (\"%s\") בלי מבחן מוגדר: תקן, הוראות בכתב, רף מספרי או "
                    "נספח" % f["term"], d.get("id"))

    # כללים 6 ו-7: עובדה על הצדדים, והישות בנייר
    ent = meta.get("entity_check") or {}
    mismatch = ent.get("match") in ("related", "none") and not ent.get("facts_confirmed")
    for d in decisions:
        bub = d.get("external_comment") or ""
        m = FACT_THEM.search(bub) or FACT_US.search(bub)
        if m and d.get("fact_source") not in FACT_SOURCES:
            finding(out, "FACT_WITHOUT_SOURCE", "הבועה נשענת על עובדה על אחד הצדדים (\"%s\") בלי מקור ב-fact_source "
                    "(profile, user_answer או agreement)" % m.group(0), d.get("id"), blocking=True)
        if mismatch and d.get("fact_source") == "profile":
            finding(out, "ENTITY_PROFILE_FACT", "הישות בנייר אינה הישות שבפרופיל, והמשתמש לא אישר שהעובדות חלות עליה: "
                    "אין להשתמש בעובדה מהפרופיל", d.get("id"), blocking=True)
        if mismatch and not (d.get("decision_required") or {}).get("required"):
            for rid in d.get("rule_ids") or []:
                title = (rules.get(rid) or {}).get("title") or ""
                if LAW_TOPIC.search(title):
                    finding(out, "ENTITY_RULE_UNCONFIRMED", "כלל שתלוי במקום, בדין, ברגולציה או ברישום (%s), כשהישות "
                            "בנייר לא אושרה: נדרשת הכרעתך" % (title or rid), d.get("id"), blocking=True)

    # כלל 8: בועה אחת לכל נושא
    seen = {}
    for d in decisions:
        bub = d.get("external_comment") or ""
        if bub and REF_BUBBLE.search(bub):
            finding(out, "REF_BUBBLE", "בועת הפניה (\"%s\"). כל השינויים של אותו כלל באותו סעיף מקבלים בועה אחת "
                    "(cluster_id)" % REF_BUBBLE.search(bub).group(0), d.get("id"), blocking=True)
        if bub and isinstance(d.get("para"), int) and d.get("rule_ids") and not d.get("cluster_id"):
            seen.setdefault((d["para"], tuple(sorted(d["rule_ids"]))), []).append(d.get("id"))
    for (p, rids), ids in sorted(seen.items(), key=lambda kv: str(kv[0])):
        if len(ids) > 1:
            finding(out, "BUBBLE_SAME_TOPIC", "כמה בועות לאותו כלל באותו סעיף (%s): אשכול אחד עם בועה אחת"
                    % ", ".join(ids), "פסקה %d" % p, blocking=True)

    # כלל 9: חולשה שלנו בנימוק
    for d in decisions:
        m = WEAKNESS.search(d.get("external_comment") or "")
        if m:
            finding(out, "WEAKNESS_IN_BUBBLE", "הנימוק בבועה חושף חולשה שלנו (\"%s\"). לנסח כאינטרס של העסקה או "
                    "כהגינות, והחשש נשאר בשכבה הפנימית" % m.group(0), d.get("id"))

    # כלל 10: קודם מסווגים את הנוסח שלהם
    for d in decisions:
        changes = d.get("op") in ("replace", "replace_span", "delete_paragraph")
        if d.get("their_track") == "green" and changes and not d.get("mandatory"):
            finding(out, "THEIR_GREEN_MARKED", "הנוסח שלהם כבר בירוק, ובכל זאת סומן. נוסח בירוק אינו מסומן",
                    d.get("id"), blocking=True)
        elif d.get("their_track") == "yellow" and d.get("decision_code") in ("R1", "R2") and changes and not (
                d.get("tier") == "tradeable" and d.get("fallback") == "their_wording"):
            finding(out, "THEIR_YELLOW_NOT_CHIP", "הנוסח שלהם בצהוב וביקשנו יותר: ההכרעה היא מטבע חליפין "
                    "(tier: tradeable), ועמדת הנסיגה היא הנוסח שלהם (fallback: their_wording)", d.get("id"))
        elif changes and d.get("rule_ids") and not d.get("their_track"):
            finding(out, "THEIR_TRACK_MISSING", "הכרעה לפי כלל בלי סיווג של הנוסח שלהם (their_track)", d.get("id"))

    # כלל 11: רשימת המאבק, לפני הסימון
    from orchestrator import proportionality as P
    prop = (meta.get("deal_context") or {}).get("proportionality") or {}
    asks = P.count_asks(decisions)["asks"]
    size = prop.get("fight_list_size")
    if isinstance(size, int) and asks > size and prop.get("user_choice") in (None, "", "unanswered"):
        finding(out, "PROPORTIONALITY_UNASKED", "%d בקשות מול רשימת מאבק של %d, והמשתמש לא נשאל לפני הסימון (מצב 4, "
                "עם שלושה ויתורים מוצעים)" % (asks, size), "", blocking=True)
    elif not isinstance(size, int) and asks > 7:
        finding(out, "FIGHT_LIST_MISSING", "%d בקשות, ולא נרשם גודל רשימת המאבק (deal_context.proportionality."
                "fight_list_size)" % asks, "")

    # כלל 12: עמדה שתלויה בזהות הצד שכנגד
    if "foreign" in _kinds(meta):
        for d in decisions:
            if (d.get("decision_required") or {}).get("required") or \
                    (d.get("user_decision") or {}).get("answer_kind") == "explicit":
                continue
            for rid in d.get("rule_ids") or []:
                rule = rules.get(rid) or {}
                conds = [c for c in rule.get("activation_conditions") or [] if isinstance(c, dict)]
                kinds = {c.get("counterparty_kind") for c in conds if c.get("counterparty_kind")}
                dependent = bool(kinds) or bool(CP_TOPIC.search(rule.get("title") or ""))
                if dependent and not kinds & {"foreign", "any"}:
                    finding(out, "COUNTERPARTY_KIND_UNDECIDED", "הכלל %s תלוי בזהות הצד שכנגד, ואין לו תנאי הפעלה "
                            "לצד זר: נדרשת הכרעתך" % (rule.get("title") or rid), d.get("id"), blocking=True)


# --------------------------------------------------------------------------- סקירת ארכיטקטורה 30.10.2026, פרק 4
# 1. מעקב שינוי הגדרה: לכל הגדרה שתוקנה בפועל (הנוסח המתקבל שונה מהנוסח שהתקבל בפסקה שמגדירה מונח), רשימת כל
#    המופעים של המונח בנוסח המתקבל, ודגל DEF_CHANGED_USAGES בבועה הפנימית. משלים את DEF_USES_UNTRACED (שבודק
#    שלכל שימוש יש הכרעה): כאן נרשם מה השתנה ואיפה המונח חי, גם כשכל השימושים כבר הוכרעו
DEF_USAGES_MARK = "DEF_CHANGED_USAGES"


def definition_changes(theirs, accepted, decisions, labels=None):
    """[{decision, para, term, usages: [{para, label}], usage_count}] לכל הגדרה שהנוסח שלה השתנה בפועל.
    theirs: פסקאות הטיוטה שהתקבלה; accepted: הנוסח המתקבל ("קבל הכול"). ההגדרה נחשבת כמשתנה כשההכרעה על הפסקה
    משנה נוסח (replace, replace_span) והנוסח המתקבל שונה, או כשהפסקה מוגדרת ו-accepted שונה מ-theirs באותו אינדקס."""
    out = []
    by_para = {}
    for d in decisions or []:
        if d.get("op") in ("replace", "replace_span") and isinstance(d.get("para"), int):
            by_para.setdefault(d["para"], d)
    n = min(len(theirs), len(accepted))
    for p in range(n):
        before, after = theirs[p] or "", accepted[p] or ""
        if _norm_ws(before) == _norm_ws(after):
            continue
        terms = _terms_in(before) | _terms_in(after)
        if not terms:
            continue
        d = by_para.get(p)
        if d is not None and d.get("regime") == "none":
            continue
        for term in sorted(terms):
            trx = _term_rx(term)
            uses = [j for j, t in enumerate(accepted) if j != p and trx.search(t or "")]
            if not uses or len(uses) > 40:
                continue   # מונח בכל ההסכם (שם צד, "ההסכם"): לא רשימה
            out.append({"decision": d.get("id") if d else None, "para": p, "term": term,
                        "usages": [{"para": j, "label": (labels[j] if labels and j < len(labels) else None)}
                                   for j in uses],
                        "usage_count": len(uses)})
    return out


def usages_line(ch, lang="he"):
    refs = ", ".join((("סעיף %s" if lang != "en" else "clause %s") % u["label"]) if u["label"] else
                     (("פסקה %d" if lang != "en" else "paragraph %d") % u["para"]) for u in ch["usages"][:15])
    more = ch["usage_count"] - min(ch["usage_count"], 15)
    tail = (" ועוד %d" % more if lang != "en" else " and %d more" % more) if more > 0 else ""
    if lang == "en":
        return "%s: the definition of \"%s\" changed; the term also appears in %d places: %s%s. Each use was checked " \
               "against the new definition." % (DEF_USAGES_MARK, ch["term"], ch["usage_count"], refs, tail)
    return "%s: ההגדרה \"%s\" שונתה; המונח מופיע גם ב-%d מקומות: %s%s. כל שימוש נבדק מול ההגדרה החדשה." % (
        DEF_USAGES_MARK, ch["term"], ch["usage_count"], refs, tail)


def annotate_definition_changes(decisions, theirs, accepted, labels=None, lang="he"):
    """מוסיף לבועה הפנימית של ההכרעה שמשנה הגדרה את שורת DEF_CHANGED_USAGES. מחזיר כמה הכרעות עודכנו. אידמפוטנטי."""
    n = 0
    by_id = {d.get("id"): d for d in decisions or []}
    for ch in definition_changes(theirs, accepted, decisions, labels):
        d = by_id.get(ch["decision"])
        if d is None:
            continue
        line = usages_line(ch, lang)
        cur = d.get("internal_comment") or ""
        if ("%s: " % DEF_USAGES_MARK) in cur and ("\"%s\"" % ch["term"]) in cur:
            continue
        d["internal_comment"] = (cur + ("\n" if cur else "") + line).strip()
        n += 1
    return n


def review_definition_changes(out, theirs, accepted, decisions, labels=None):
    """DEF_CHANGED_USAGES: הגדרה שתוקנה ובבועה הפנימית של ההכרעה אין רשימת המופעים. אינו חוסם: הדגל נוסף ב-
    content_checks.py --annotate-definitions, או ביד."""
    for ch in definition_changes(theirs, accepted, decisions, labels):
        d = next((x for x in decisions if x.get("id") == ch["decision"]), None)
        cur = (d or {}).get("internal_comment") or ""
        if ("%s: " % DEF_USAGES_MARK) in cur and ("\"%s\"" % ch["term"]) in cur:
            continue
        finding(out, DEF_USAGES_MARK, "ההגדרה \"%s\" שונתה (פסקה %d), והמונח מופיע ב-%d מקומות נוספים. רשימת המופעים "
                "נכנסת לבועה הפנימית (content_checks.py --annotate-definitions) / The definition of \"%s\" changed; "
                "its %d uses are listed in the internal comment" % (ch["term"], ch["para"], ch["usage_count"],
                                                                     ch["term"], ch["usage_count"]),
                ch["decision"] or "פסקה %d" % ch["para"])


# 3. ניקוי קודים פנימיים בשכבת הבנייה: מזהה כלל -> שם נושא (כשיש גרעין), ואחרת נמחק; קוד הכרעה, מזהה מקור (S12),
#    מזהה מסמך (DOC-1, AGR-1) ו"סבב 1" -> "סבב ראשון". רץ על כל טקסט שנבנה בסקריפט ומוצג ללקוח (round_tools,
#    tender_outputs), ולא רק על הודעת המסירה (voice_check)
_RULE_CODE = r"(?:R|V|Q|SEG|DS|LG|PB|OS|EMP)-?\d+[a-z]?"
SCRUB_RULE = re.compile(r"(?<![\w-])(?:כלל\s+|rule\s+)?(" + _RULE_CODE + r")(?![\w-])", re.I)
SCRUB_CODES = re.compile(r"\s*\((?:\s*(?:[ARKNQ]|REG-?|APR-?|DOC-?|AGR-?|S)\d+[a-z]?\s*,?)+\)|"
                         r"(?<![\w-])(?:קוד\s+)?(?:[ARKNQ]\d{1,3}[a-z]?|REG-\d+|APR-\d+|DOC-\d+|AGR-\d+|S\d{1,3})(?![\w-])")
ROUND_WORDS = {"he": {1: "ראשון", 2: "שני", 3: "שלישי", 4: "רביעי"},
               "en": {1: "first", 2: "second", 3: "third", 4: "fourth"}}


def scrub_client_text(text, core=None, lang="he"):
    """טקסט ללקוח בלי קודים פנימיים. core: playbook-core.json (clauses[].id -> title) או מילון {rule_id: topic}."""
    t = str(text or "")
    names = {}
    if isinstance(core, dict):
        for c in core.get("clauses") or core.get("rules") or []:
            if isinstance(c, dict) and (c.get("id") or c.get("rule_id")):
                names[str(c.get("id") or c.get("rule_id")).upper()] = c.get("title") or c.get("topic_name") or ""
        for k, v in core.items():
            if isinstance(v, str) and re.fullmatch(_RULE_CODE, str(k), re.I):
                names[str(k).upper()] = v

    def rule(m):
        return names.get(m.group(1).upper().replace("-", "")) or names.get(m.group(1).upper()) or ""
    t = SCRUB_RULE.sub(rule, t)
    t = SCRUB_CODES.sub("", t)

    def rnd(m):
        n = int(m.group(2))
        w = ROUND_WORDS["en" if m.group(1).lower() == "round" else "he"].get(n)
        return (m.group(1) + " " + w) if w else m.group(0)
    t = re.sub(r"(סבב|Round|round)\s+(\d+)", rnd, t)
    t = re.sub(r"\s+([,.;:)])", r"\1", t)
    t = re.sub(r"\(\s*\)", "", t)
    return re.sub(r"\s{2,}", " ", t).strip()


# 4. "נייר של מי": הנייר שלנו שחזר, הנייר שהצד שכנגד ניסח, או תבנית של גורם שלישי (n1b-learning.md, שער הפוזיציה 5).
#    בקוד, מסימנים בקובץ עצמו, ולא בהסקה של המודל
TEMPLATE_BLANK = re.compile(r"_{3,}|\[\s*●\s*\]|\[[^\]\n]{0,40}\]|<[^>\n]{2,40}>")


def paper_owner(received, our_names=(), their_names=(), lawyer_names=(), sent_shas=()):
    """{owner: ours|theirs|template|None, confident, signals}. אותות: טביעת אצבע של קובץ שהחברה שלחה; סימונים או בועות
    בשם עורך הדין שלנו (הנייר שלנו שחזר עם הערותיהם); שם הצד הראשון בבלוק הצדדים; מאפייני הקובץ (creator,
    lastModifiedBy); ובלוק צדדים ריק (קווי מילוי, [●]) בלי שם של אף צד: תבנית."""
    sig, votes = [], {"ours": 0, "theirs": 0, "template": 0}
    norm = lambda s: re.sub(r"[\s\"״'”“׳.,]+", " ", str(s or "")).strip().lower()  # noqa: E731
    ours_n = [norm(n) for n in our_names if n and len(norm(n)) >= 3]
    theirs_n = [norm(n) for n in their_names if n and len(norm(n)) >= 3]
    lawyers = {str(x).strip() for x in lawyer_names if x} | set(INTERNAL_AUTHORS)
    try:
        import hashlib
        sha = hashlib.sha256(open(received, "rb").read()).hexdigest()
        if sha in set(sent_shas or ()):
            sig.append("sha_of_sent_document")
            return {"owner": "ours", "confident": True, "signals": sig}
    except OSError:
        pass
    parts = dt.read_package(received)
    root = etree.fromstring(parts["word/document.xml"])
    authors = {e.get(W + "author") for e in root.iter(W + "ins", W + "del")} | {c["author"] for c in dt.read_comments(parts)}
    authors.discard(None)
    if authors & lawyers:
        sig.append("our_markup_present")
        votes["ours"] += 2
    core = parts.get("docProps/core.xml")
    if core:
        meta = norm(re.sub(r"<[^>]+>", " ", core.decode("utf-8", "ignore")))
        if any(n in meta for n in ours_n):
            sig.append("properties_ours")
            votes["ours"] += 1
        elif any(n in meta for n in theirs_n):
            sig.append("properties_theirs")
            votes["theirs"] += 1
    texts = [t.strip() for t in dt.received_paragraphs(received)]
    try:
        first = next((i for i, x in enumerate(numbered_labels(received)) if x), None)
    except Exception:  # noqa: BLE001
        first = None
    # בלוק הצדדים בלבד: הפתיח עד הסעיף הממוספר הראשון (שם צד בגוף ההסכם אינו סימן של מי הנייר)
    head = (texts[:first] if first else texts[:15])[:40]
    block = norm(" ".join(head))
    pos_o = min([block.find(n) for n in ours_n if n in block] or [-1])
    pos_t = min([block.find(n) for n in theirs_n if n in block] or [-1])
    if pos_o >= 0 and (pos_t < 0 or pos_o < pos_t):
        sig.append("our_name_first_party")
        votes["ours"] += 1
    elif pos_t >= 0:
        sig.append("their_name_first_party")
        votes["theirs"] += 1
    blanks = sum(len(TEMPLATE_BLANK.findall(t)) for t in head)
    if pos_o < 0 and pos_t < 0 and blanks >= 2:
        sig.append("party_block_blank")
        votes["template"] += 2
    if not sig:
        return {"owner": None, "confident": False, "signals": sig}
    best = max(votes, key=votes.get)
    others = [v for k, v in votes.items() if k != best]
    confident = votes[best] >= 2 and max(others) == 0
    return {"owner": best if votes[best] else None, "confident": confident, "signals": sig}


# 7. יחידת ספירה אחת לכל התוצרים (user-A #17: "5 סומנו" / "12 מתוך 144" / "2 מתוך 48"): הפסקאות בטיוטה שהתקבלה,
#    וההכרעות עליהן. כל שורת ספירה בסיכום, בדוח השער ובפנקס נבנית מכאן, ולא מחושבת במודל
def unit_counts(decisions, para_count=None, playbook_map=None):
    """{unit: 'paragraph', paragraphs, decided, changed, accepted, comment_only, open, playbook_rules, applied,
    no_matching_clause}. decided <= paragraphs; changed + accepted + comment_only == decided (על פסקאות).
    open: פסקאות בלי הכרעה (כש-para_count ידוע)."""
    ds = [d for d in (decisions or []) if isinstance(d, dict)]
    paras = {d.get("para") for d in ds if isinstance(d.get("para"), int)}
    changed = {d.get("para") for d in ds if d.get("op") in ("replace", "replace_span", "delete_paragraph")
               and isinstance(d.get("para"), int)}
    comment = {d.get("para") for d in ds if d.get("op") == "comment_only" and isinstance(d.get("para"), int)} - changed
    accepted = paras - changed - comment
    added = sum(1 for d in ds if d.get("op") == "insert_paragraph")
    out = {"unit": "paragraph", "paragraphs": para_count, "decided": len(paras), "changed": len(changed),
           "accepted": len(accepted), "comment_only": len(comment), "added": added,
           "open": (max(para_count - len(paras), 0) if isinstance(para_count, int) else None)}
    pm = playbook_map or {}
    cnt = pm.get("counts") or {}
    if pm:
        out.update(playbook_rules=cnt.get("rules"), applied=cnt.get("applied"),
                   no_matching_clause=cnt.get("no_matching_clause"), rules_no_outcome=cnt.get("no_outcome"))
    return out


def counts_line(c, lang="he"):
    """השורה האחת שמוצגת ללקוח. אותם מספרים בכל מקום."""
    tot = c.get("paragraphs")
    if lang == "en":
        s = "%d paragraphs changed, %d accepted as they are" % (c["changed"], c["accepted"])
        if c.get("added"):
            s += ", %d added" % c["added"]
        if isinstance(tot, int):
            s += ", out of %d paragraphs in their draft" % tot
        if c.get("playbook_rules") is not None:
            s += "; playbook: %s of %s positions applied, %s with no matching clause" % (
                c.get("applied"), c.get("playbook_rules"), c.get("no_matching_clause"))
        return s + "."
    s = "%d פסקאות תוקנו, %d התקבלו כמו שהן" % (c["changed"], c["accepted"])
    if c.get("added"):
        s += ", %d נוספו" % c["added"]
    if isinstance(tot, int):
        s += ", מתוך %d פסקאות בטיוטה שלהם" % tot
    if c.get("playbook_rules") is not None:
        s += "; הפלייבוק: %s מתוך %s עמדות הוחלו, %s בלי סעיף מתאים" % (
            c.get("applied"), c.get("playbook_rules"), c.get("no_matching_clause"))
    return s + "."


# --------------------------------------------------------------------------- עקיפות בין סעיפים, הפרזה בבועות, מספרים בלי מקור (31.10.2026)
# מפת הקשרים נמצאת ב-interaction_pairs.json (משפחות מושגים כלליות ושפות עברית ואנגלית). אין כאן סוג הסכם או עסקה
_PAIRS_CACHE = {}
BODY_DELETE_OPS = ("delete", "delete_paragraph", "delete_span")
NUM_UNIT = r"(?P<unit>ימים|יום|שבועות|שבוע|חודשים|חודש|שנים|שנה|days?|weeks?|months?|years?)"
NUM_RX = [("pct", re.compile(r"(?P<n>\d+(?:[.,]\d+)?)\s*(?:%|אחוז|percent\b|per cent\b)", re.I)),
          ("dur", re.compile(r"(?P<n>\d+)\s*(?:\(\s*\w+\s*\)\s*)?-?\s*" + NUM_UNIT, re.I)),
          ("amt", re.compile(r"(?:[$€₪]\s*(?P<n>\d[\d,]*(?:\.\d+)?)|(?P<n2>\d[\d,]*(?:\.\d+)?)\s*(?:ש\"ח|ש״ח|₪|NIS\b|ILS\b|USD\b|EUR\b|"
                             r"דולר|אירו|יורו))", re.I))]
UNIT_CLASS = {"יום": "d", "ימים": "d", "day": "d", "days": "d", "שבוע": "w", "שבועות": "w", "week": "w", "weeks": "w",
              "חודש": "m", "חודשים": "m", "month": "m", "months": "m", "שנה": "y", "שנים": "y", "year": "y", "years": "y"}


def interaction_map(path=None):
    """טוען את interaction_pairs.json ומקמפל את מילות המפתח. None כשהקובץ חסר או פגום."""
    path = path or os.path.join(HERE, "interaction_pairs.json")
    if path in _PAIRS_CACHE:
        return _PAIRS_CACHE[path]
    res = None
    try:
        with io.open(path, encoding="utf-8") as fh:
            raw = json.load(fh)

        def comp(v):
            he = tuple(x.lower() for x in (v.get("he") or ()))
            en = v.get("en") or ()
            rx = re.compile("|".join((r"(?<![A-Za-z])" if x[:1].isalnum() else "") + re.escape(x) for x in en), re.I) if en else None
            return (he, rx)
        res = {"raw": raw, "fam": {k: comp(v) for k, v in (raw.get("families") or {}).items()},
               "dup": {k: comp(v) for k, v in (raw.get("duplicate_mechanisms") or {}).items()},
               "pairs": [tuple(p) for p in raw.get("pairs") or []]}
    except (OSError, ValueError):
        res = None
    _PAIRS_CACHE[path] = res
    return res


def _hits(text, comp):
    """מספר מילות המפתח השונות של המשפחה שמופיעות בטקסט."""
    he, en = comp
    low = (text or "").lower()
    n = sum(1 for k in he if k in low)
    if en:
        n += len({m.group(0).lower() for m in en.finditer(text or "")})
    return n


def _decision_text(d, theirs):
    """הנוסח שההכרעה נוגעת בו: החדש והמקורי."""
    old = theirs[d["para"]] if isinstance(d.get("para"), int) and 0 <= d["para"] < len(theirs) else ""
    new = ""
    for k in ("new_text", "new", "text"):
        if d.get(k):
            new = d[k]
            break
    return new, old


def _changes_body(d, theirs):
    new, _old = _decision_text(d, theirs)
    return bool(new) or d.get("op") in BODY_DELETE_OPS


def _locate(accepted, d, new):
    """אינדקס הפסקה של ההכרעה בנוסח המתקבל (לפי הנוסח החדש, ואם אין, לפי para)."""
    probe = _norm_ws(new)[:50] if new else ""
    if probe:
        for i, t in enumerate(accepted):
            if probe in _norm_ws(t):
                return i
    p = d.get("para") if isinstance(d.get("para"), int) else d.get("after_para")
    return p if isinstance(p, int) and 0 <= p < len(accepted) else None


def _entry_covers(e, idx):
    if not isinstance(e, dict):
        return False
    if e.get("para") == idx:
        return True
    ps = e.get("paras")
    return isinstance(ps, (list, tuple)) and idx in ps


def _open_item_listed(state, d):
    items = list((state or {}).get("open_items") or []) + list(((state or {}).get("meta") or {}).get("open_items") or [])
    did = d.get("id")
    for it in items:
        if isinstance(it, dict) and did and (it.get("decision_id") == did or it.get("interaction_of") == did or
                                              str(did) in str(it.get("item", ""))):
            return True
    return False


def review_interactions(out, accepted, theirs, decisions, state, mode=None, imap=None, cap=8):
    """בדיקת עקיפות: לכל הכרעה שמשנה נוסח ונוגעת במשפחה X, פסקאות בנוסח המתקבל שנוגעות במשפחה מזווגת ל-X חייבות
    להופיע ב-interactions[] של ההכרעה, עם bypass (no / fixed:<id> / open) ותשובה לשאלה: האם הצד השני עדיין יכול להגיע
    לתוצאה שהפלייבוק מבקש למנוע, באמצעות הוראה אחרת בהסכם. חוסם במצב משלוח."""
    imap = imap or interaction_map()
    blocking = mode != "work"
    if not imap:
        finding(out, "INTERACTION_MAP_MISSING", "interaction_pairs.json חסר או פגום: בדיקת העקיפות לא רצה", "")
        return
    decisions = [d for d in decisions if isinstance(d, dict)]
    ids = {d.get("id") for d in decisions if d.get("id")}
    for d in decisions:
        if not _changes_body(d, theirs):
            continue
        new, old = _decision_text(d, theirs)
        text = new + "\n" + old
        mine = {f for f, comp in imap["fam"].items() if _hits(text, comp)}
        if not mine:
            continue
        own = _locate(accepted, d, new)
        want = {}   # אינדקס פסקה -> (משפחה מזווגת, ציון)
        for a, b, _why in imap["pairs"]:
            for x, y in ((a, b), (b, a)):
                if x not in mine or y not in imap["fam"]:
                    continue
                ranked = sorted(((_hits(t, imap["fam"][y]), i) for i, t in enumerate(accepted) if i != own),
                                key=lambda r: (-r[0], r[1]))
                for score, i in [r for r in ranked if r[0] > 0][:4]:
                    if i not in want or want[i][1] < score:
                        want[i] = (y, score)
        want = dict(sorted(want.items(), key=lambda kv: (-kv[1][1], kv[0]))[:cap])
        inter = d.get("interactions")
        inter = inter if isinstance(inter, list) else []
        for idx, (fam, _s) in sorted(want.items()):
            ents = [e for e in inter if _entry_covers(e, idx)]
            where = "%s, פסקה %d" % (d.get("id"), idx)
            lab = imap["raw"]["families"][fam].get("label", fam)
            if not ents:
                finding(out, "INTERACTION_UNCHECKED", "ההכרעה משנה נוסח, ופסקה %d נוגעת ב\"%s\" ויכולה לצמצם או לעקוף אותה, "
                        "ואין ב-interactions[] ערך שמכסה אותה (para, bypass, answer)" % (idx, lab), where, blocking)
                continue
            e = ents[0]
            by = str(e.get("bypass", ""))
            if not (by in ("no", "open") or (by.startswith("fixed:") and by[6:] in ids)):
                finding(out, "INTERACTION_UNCHECKED", "bypass חייב להיות no, open או fixed:<מזהה הכרעה קיימת>; נמצא %r" % by,
                        where, blocking)
            elif not str(e.get("answer") or "").strip():
                finding(out, "INTERACTION_UNCHECKED", "חסרה התשובה לשאלה: האם הצד השני עדיין יכול להגיע לתוצאה שהפלייבוק "
                        "מבקש למנוע באמצעות הוראה אחרת (answer)", where, blocking)
            elif by == "open" and not _open_item_listed(state, d):
                finding(out, "INTERACTION_OPEN_UNLISTED", "עקיפה פתוחה שאינה ברשימת הפריטים הפתוחים (open_items עם decision_id)",
                        where, blocking)
    # מנגנון כפול: שתי זכויות או מנגנונים נפרדים מאותו סוג
    for d in decisions:
        new, _old = _decision_text(d, theirs)
        if not new:
            continue
        own = _locate(accepted, d, new)
        for fam, comp in imap["dup"].items():
            if not _hits(new, comp):
                continue
            others = [i for i, t in enumerate(accepted) if _hits(t, comp) and (own is None or abs(i - own) > 2)]
            if others:
                lab = imap["raw"]["duplicate_mechanisms"][fam].get("label", fam)
                finding(out, "DUPLICATE_MECHANISM", "ההכרעה מוסיפה מנגנון (%s) ובפסקה %d יש מנגנון נוסף מאותו סוג: לאחד, "
                        "להפנות או לוודא שהם אינם מתנגשים" % (lab, others[0]), "%s, פסקה %d" % (d.get("id"), others[0]))


def _claims(rx_list, text):
    for r in rx_list or ():
        m = re.search(r, text, re.I)
        if m:
            return m.group(0)
    return None


def _eq_values(d):
    eq = d.get("equivalence")
    if not isinstance(eq, dict):
        return None
    vals = {}
    for k, v in eq.items():
        if isinstance(v, dict):
            v = v.get("value") or v.get("result")
        vals[k] = str(v or "").lower()
    return vals


def review_overclaim(out, decisions, mode=None, imap=None):
    """BUBBLE_OVERCLAIM: בועה חיצונית שטוענת טענה מוחלטת (הדדי, במלואו, כל, אין) כשהשינוי חלקי."""
    imap = imap or interaction_map()
    oc = ((imap or {}).get("raw") or {}).get("overclaim") or {}
    if not oc:
        return
    blocking = mode != "work"
    for d in decisions:
        if not isinstance(d, dict):
            continue
        bub = d.get("external_comment") or ""
        if not bub:
            continue
        new, _old = _decision_text(d, [])
        eq = _eq_values(d)
        narrower = [k for k, v in (eq or {}).items() if v == "narrower"]
        partial = bool(narrower) or str(d.get("coverage") or "").lower() == "partial"
        mut = _claims(oc.get("mutual", {}).get("he", []) + oc.get("mutual", {}).get("en", []), bub)
        tot = _claims(oc.get("total", {}).get("he", []) + oc.get("total", {}).get("en", []) +
                      oc.get("none", {}).get("he", []) + oc.get("none", {}).get("en", []), bub)
        sym = _claims(oc.get("symmetric_markers", {}).get("he", []) + oc.get("symmetric_markers", {}).get("en", []), new)
        if mut and new and (not sym or narrower):
            finding(out, "BUBBLE_OVERCLAIM", "הבועה טוענת \"%s\" (הדדיות), והנוסח שהוכנס אינו סימטרי או שהשקילות צרה יותר "
                    "(%s): לתאר רק את מה שתוקן" % (mut, ", ".join(narrower) or "אין ניסוח הדדי"), d.get("id"), blocking)
        elif (mut or tot) and partial:
            finding(out, "BUBBLE_OVERCLAIM", "הבועה טוענת טענה מוחלטת (\"%s\") והשינוי חלקי%s: לתאר במדויק מה תוקן ומה לא"
                    % (mut or tot, " (צר יותר ב: %s)" % ", ".join(narrower) if narrower else ""), d.get("id"))


def _numbers(text):
    """קבוצת (סוג, ערך, מחלקת יחידה) של מספרים בטקסט: אחוז, תקופה, סכום."""
    res = set()
    for kind, rx in NUM_RX:
        for m in rx.finditer(text or ""):
            g = m.groupdict()
            n = (g.get("n") or g.get("n2") or "").replace(",", "")
            u = UNIT_CLASS.get((g.get("unit") or "").lower(), "") if kind == "dur" else ""
            if n:
                try:
                    n = str(float(n)).rstrip("0").rstrip(".")
                except ValueError:
                    pass
                res.add((kind, n, u))
    return res


def review_numbers(out, theirs, decisions, state, core, mode=None):
    """NUMBER_UNSOURCED: מספר (אחוז, ימים, חודשים, שנים, סכום) בנוסח שהכנסנו שאינו בגרעין, בתשובות הלקוח, בכרטיס העסקה
    או בהסכם שהתקבל. במקום להמציא: [להשלים] ופריט פתוח. מקור מפורש להכרעה: השדה number_source."""
    blocking = mode != "work"
    state = state or {}
    meta = state.get("meta") or {}
    src = [json.dumps(core or {}, ensure_ascii=False), "\n".join(theirs),
           json.dumps(state.get("client_answers") or [], ensure_ascii=False),
           json.dumps(state.get("user_decisions") or [], ensure_ascii=False),
           json.dumps(meta.get("deal_card") or state.get("deal_card") or meta.get("deal_context") or {}, ensure_ascii=False)]
    known = set()
    for s in src:
        known |= _numbers(s)
    bare = set()
    for s in src[2:]:
        bare |= set(re.findall(r"(?<![\d.,])\d+(?![\d])", s))
    for d, txt in our_texts(decisions):
        if str(d.get("number_source") or "").strip():
            continue
        for kind, n, u in sorted(_numbers(txt)):
            if (kind, n, u) not in known and n not in bare:
                finding(out, "NUMBER_UNSOURCED", "בנוסח שהכנסנו מספר (%s) שאינו בגרעין, בתשובות הלקוח, בכרטיס העסקה או בהסכם "
                        "שהתקבל: לכתוב [להשלים] ולפתוח פריט פתוח, ולא להמציא" % n, d.get("id"), blocking)
                break


# --------------------------------------------------------------------------- המאמת העצמאי (n9-verify.md)
# המאמת רץ בהקשר נקי, קורא קבצים מקומיים בלבד, וכותב קובץ ממצאים אחד. הסכמה שלו נבדקת כאן, והשער מתרגם כל ממצא
# פתוח לאזהרה VERIFY_OPEN (אינו חוסם בשלב הראשון)
VERIFY_CHECKS = ("contradiction_after_accept", "bubble_vs_change", "reasoning_vs_position", "syntax_break",
                 "bubble_exploitable", "scope_vs_paper_type", "legal_review_scope", "definition_uses",
                 "bypass_remaining", "protection_incomplete", "survival_numbering_refs", "external_documents",
                 "rule_coverage_vs_text")
VERIFY_SEVERITIES = ("open", "note")


def validate_verify_findings(data):
    """רשימת שגיאות מבנה של קובץ הממצאים; ריקה כשתקין. המבנה: {"verifier": "n9", "round", "read": [..נתיבים..],
    "findings": [{"check", "severity": "open|note", "where": "<סעיף או פסקה>", "quote": "<ציטוט מהנוסח>",
    "issue": "<מה נמצא>", "suggest": "<מה לבדוק>"}]}. אין בו הכרעה, אין נוסח יעד ואין כתיבה לקובץ המצב."""
    errs = []
    if not isinstance(data, dict):
        return ["הקובץ אינו אובייקט JSON"]
    if data.get("verifier") != "n9":
        errs.append("verifier חייב להיות n9")
    if not isinstance(data.get("findings"), list):
        errs.append("findings חייב להיות רשימה")
        return errs
    for i, f in enumerate(data["findings"]):
        w = "findings[%d]" % i
        if not isinstance(f, dict):
            errs.append("%s אינו אובייקט" % w)
            continue
        if f.get("check") not in VERIFY_CHECKS:
            errs.append("%s: check לא מוכר: %r (אחד מ: %s)" % (w, f.get("check"), ", ".join(VERIFY_CHECKS)))
        if f.get("severity") not in VERIFY_SEVERITIES:
            errs.append("%s: severity חייב להיות open או note" % w)
        for k in ("where", "quote", "issue"):
            if not isinstance(f.get(k), str) or not f.get(k).strip():
                errs.append("%s: חסר %s (ממצא בלי ציטוט ומיקום אינו ממצא)" % (w, k))
        for k in ("decision", "new_text", "replace_with", "op", "decision_code"):
            if k in f:
                errs.append("%s: המאמת אינו מכריע ואינו מנסח: השדה %s אסור" % (w, k))
    return errs


def main(argv=None):
    sys.dont_write_bytecode = True
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    from common.cli import load_docx_or_explain
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--work", help="קובץ העבודה (לא נדרש עם --hidden-only)")
    ap.add_argument("--received", required=True)
    ap.add_argument("--decisions", help="קובץ ההכרעות (לא נדרש עם --hidden-only)")
    ap.add_argument("--state")
    ap.add_argument("--core")
    ap.add_argument("--manifest", help="corpus-manifest.json: שמות הצדדים בהסכמים החתומים")
    ap.add_argument("--hidden-only", action="store_true", help="רק סריקת הטקסט המוסתר בטיוטה שהתקבלה")
    ap.add_argument("--mode", choices=("work", "send"), default="send",
                    help="work: ממצא שחוסם רק משלוח (BUB_UNSOURCED_FACT) הוא לבדיקה. ברירת מחדל: send")
    ap.add_argument("--anchors", action="store_true",
                    help="בקליטה: עוגני הזמן בנייר שלהם שכבר עברו או ריקים (כלל 4). כל ממצא הוא שאלה במנת השאלות")
    ap.add_argument("--profile", help="פרופיל-לקוח.json: השמות שלנו, כדי שבועה שלנו לא תיחשב מקור של הצד שכנגד")
    ap.add_argument("--definition-changes", action="store_true",
                    help="JSON: כל הגדרה שתוקנה בקובץ העבודה, וכל המופעים של המונח בנוסח המתקבל (DEF_CHANGED_USAGES)")
    ap.add_argument("--annotate-definitions", action="store_true",
                    help="מוסיף לקובץ ההכרעות (--decisions, נכתב במקומו) את שורת DEF_CHANGED_USAGES בבועה הפנימית של כל "
                         "הכרעה שמשנה הגדרה, לפני apply_redlines.py")
    ap.add_argument("--validate-findings", help="קובץ הממצאים של המאמת העצמאי (n9-verify.md): בדיקת מבנה בלבד")
    ap.add_argument("--lang", choices=("he", "en"), default="he", help="שפת שורת DEF_CHANGED_USAGES בבועה הפנימית")
    a = ap.parse_args(argv)
    if a.validate_findings:
        data = load(a.validate_findings)
        errs = validate_verify_findings(data) if data is not None else ["הקובץ חסר או אינו JSON"]
        for e_ in errs:
            print("  [VERIFY_SCHEMA] %s" % e_)
        if not errs:
            n_open = sum(1 for f in data["findings"] if f.get("severity") == "open")
            print("תקין: %d ממצאים, %d פתוחים" % (len(data["findings"]), n_open))
        return 3 if errs else 0
    if a.anchors:
        if not a.received or not os.path.exists(a.received):
            print("אינו קיים או חסר: %s" % a.received)
            return 2
        ok, msg, code = load_docx_or_explain(a.received, loader=False)
        if ok is None:
            print(msg)
            return code
        print(json.dumps(time_anchors(dt.received_paragraphs(a.received)), ensure_ascii=False, indent=1))
        return 0
    need = (a.received,) if a.hidden_only else (a.work, a.received, a.decisions)
    for p in need:
        if not p or not os.path.exists(p):
            print("אינו קיים או חסר: %s" % p)
            return 2
    # Word פגום, DOC, מוצפן או Strict: הודעה דו-לשונית וקוד 2, ולא traceback
    for p in ((a.received,) if a.hidden_only else (a.work, a.received)):
        ok, msg, code = load_docx_or_explain(p, loader=False)
        if ok is None:
            print(msg)
            return code
    if a.hidden_only:
        print(json.dumps(hidden_scan(a.received), ensure_ascii=False, indent=1))
        return 0
    dec = load(a.decisions)
    if a.definition_changes or a.annotate_definitions:
        items = dec.get("decisions", []) if isinstance(dec, dict) else dec
        theirs = dt.received_paragraphs(a.received)
        accepted = dt.accept_all(a.work)
        try:
            labels = numbered_labels(a.received)
        except Exception:  # noqa: BLE001
            labels = None
        if a.annotate_definitions:
            n = annotate_definition_changes(items, theirs, accepted, labels, a.lang)
            with open(a.decisions, "w", encoding="utf-8") as fh:
                json.dump(dec, fh, ensure_ascii=False, indent=1)
            print("עודכנו %d הכרעות בשורת %s" % (n, DEF_USAGES_MARK))
            return 0
        print(json.dumps(definition_changes(theirs, accepted, items, labels), ensure_ascii=False, indent=1))
        return 0
    names = [dec.get("author")] if isinstance(dec, dict) else []
    if a.profile:
        from lawyer import lawyer_view
        prof = lawyer_view(load(a.profile) or {})
        names += [prof.get("lawyer_name"), prof.get("lawyer_name_en")] + list(prof.get("lawyer_aliases") or [])
    res = run_checks(a.work, a.received, dec.get("decisions", []) if isinstance(dec, dict) else dec,
                     load(a.state), attach_related(load(a.core), a.core), load(a.manifest), mode=a.mode,
                     profile={"lawyer_names": [x for x in names if x]})
    for f in res:
        print("%s [%s] %s%s" % ("חוסם" if f["blocking"] else "לבדיקה", f["code"], f["message"],
                                "  (%s)" % f["where"] if f["where"] else ""))
    blocking = [f for f in res if f["blocking"]]
    print("ממצאים: %d, חוסמים: %d" % (len(res), len(blocking)))
    return 3 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
