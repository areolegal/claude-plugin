---
name: rtl-docx-enforcer
description: Enforce strict, leak-proof right-to-left (RTL) formatting in Word documents (.docx) generated with python-docx for Hebrew and Arabic content. Use whenever the user requests a Word document, .docx, report, memo, letter, brochure, syllabus, playbook, or any deliverable in Hebrew or Arabic. Covers paragraph bidi, run-level rtl, heading styles, numbered lists with correct number-and-dot ordering, bulleted lists, tables with per-cell RTL and reversed column order, section-level rtlGutter, and mixed Hebrew-English text inside a single paragraph. Prevents the common failure mode where Hebrew text appears but the document still behaves as LTR in Microsoft Word. Do NOT use for docx-js, HTML, or chat-only output — this skill is for python-docx specifically.
---

# RTL DOCX Enforcer — python-docx

## מטרת הסקיל

לייצר קובצי Word בעברית או בערבית שנפתחים ב-Microsoft Word ומתנהגים כ-RTL אמיתי ברמת ה-XML — לא רק "טקסט עברי בתוך שלד LTR". הסקיל חובק חמישה כאבים ידועים ופותר כל אחד מהם עם קוד קונקרטי.

## כלל פעולה מוחלט

**אם המסמך מכיל עברית או ערבית — RTL מופעל אוטומטית, בלי לשאול.** אין מצב ביניים. אין "חלק RTL וחלק לא". כל פסקה, כל תא, כל כותרת, כל run — עובר דרך הפונקציות של הסקיל הזה.

אם קלוד כותב פסקה אחת בלי `set_paragraph_rtl()` — זו תקלה. אם נוצרת טבלה בלי `set_table_rtl()` — זו תקלה. אין פרצות.

## סדר עבודה חובה

בכל פעם שנוצר מסמך Word עם תוכן בעברית/ערבית, קלוד פועל בסדר הזה:

1. קורא את `rtl_helpers.py` ומעתיק את הפונקציות למעלה של הסקריפט.
2. יוצר את ה-`Document()`.
3. **מיד** קורא ל-`set_document_rtl(doc)` — מגדיר את ה-section ואת סגנונות הבסיס.
4. לכל פסקה שנוספת: קורא ל-`add_rtl_paragraph(doc, text, style=...)` **במקום** `doc.add_paragraph()`.
5. לכל כותרת: `add_rtl_heading(doc, text, level=...)` במקום `doc.add_heading()`.
6. לכל רשימה ממוספרת: `add_rtl_numbered_list(doc, items)`.
7. לכל רשימת תבליטים: `add_rtl_bullet_list(doc, items)`.
8. לכל טבלה: יוצר עם `doc.add_table(...)` ומיד אחרי זה `set_table_rtl(table)`.
9. לפני שמירה: `final_rtl_audit(doc)` — עובר על כל פסקה במסמך ומוודא ש-bidi הופעל. אם משהו חסר — מתקן.

## חמשת הכאבים והפתרונות

### 1. מספור עברי — מספר בימין ונקודה משמאלו

**הבעיה:** הצורה התקינה של מספור בעברית היא "1. טקסט" כשהמספר 1 בצד ימין, הנקודה משמאלו, והטקסט נמשך משמאל לנקודה. אבל `doc.add_paragraph("1. סעיף ראשון")` בתוך פסקה עם bidi מלא יכול להניב את הצורה השגויה ".1 סעיף" — כי Word לא תמיד מזהה את המספר כטוקן LTR נפרד בתוך פסקה RTL, ומפעיל את Bidi algorithm באופן שמהפך את הסדר של "1" ו-"." .

**הפתרון:** שני מסלולים —

- **מסלול בטוח (מומלץ למסמכים רגילים):** פיצול לשני runs בתוך אותה פסקה. run ראשון מכיל "1. " ומסומן LTR מפורש דרך `set_run_ltr_explicit()` (שמוסיף `<w:rtl w:val="0"/>` ל-rPr). run שני מכיל את הטקסט העברי ומסומן RTL דרך `set_run_rtl()`. הפסקה עצמה עם bidi. התוצאה: Word שומר על הסדר הפנימי "1." בתוך ה-run ה-LTR, ומציב את כל ה-run בצד ימין של הפסקה הלוגית. זה מה שהפונקציה `add_rtl_numbered_list()` עושה אוטומטית.

- **מסלול תחיליות (לרשימות עם היררכיה או בהקשרים בעייתיים):** שימוש בתחיליות מפורשות כמו "שלב 1:", "סעיף 1:", "פריט 1:" — המילה העברית פותחת את הרצף ומונעת כל אי-בהירות של Bidi.

**חשוב:** ה-`final_rtl_audit()` מדלג על runs שסומנו LTR מפורש (`_is_run_explicit_ltr()` מזהה אותם), כדי לא להפוך אותם בטעות ל-RTL.

### 2. טבלאות — כיווניות תאים וסדר עמודות

**הבעיה:** `doc.add_table()` יוצר טבלה LTR. גם אם מגדירים bidi לפסקאות בתוך התאים, **סדר העמודות** עצמו נשאר LTR — העמודה הראשונה הגיונית מופיעה בשמאל במקום בימין.

**הפתרון:** הפונקציה `set_table_rtl(table)` עושה שלושה דברים:

1. מוסיפה `<w:bidiVisual/>` ל-`tblPr` — זה הופך את סדר העמודות הוויזואלי.
2. עוברת על כל תא ומפעילה `set_paragraph_rtl()` על כל פסקה בתוכו.
3. מגדירה `tblLayout` ל-fixed כדי שהעמודות לא יקרסו.

### 3. כותרות וסגנונות שיורשים RTL

**הבעיה:** הגדרת bidi על פסקה אחת לא מספיקה — כשמגדירים `style="Heading 1"`, הסגנון עצמו ב-`styles.xml` הוא LTR, והפסקה יורשת ממנו כיווניות סותרת.

**הפתרון:** `set_document_rtl(doc)` עוברת על **כל הסגנונות** הרלוונטיים (Normal, Heading 1–9, List Paragraph, List Number, List Bullet, Title, Subtitle) ומוסיפה `<w:bidi/>` ו-`<w:jc w:val="right"/>` לתוך ה-`pPr` של הסגנון עצמו. זה מבטיח שכל שימוש בסגנון יורש RTL.

### 4. רשימות עם bullets שלא נשברות

**הבעיה:** תבליטים ב-Word מוגדרים ב-`numbering.xml` עם מיקום אופקי קבוע (ind left). ב-RTL צריך ind **right** ו-`suff` נכון, אחרת התבליט נתקע בצד הלא נכון או מתרחק מהטקסט.

**הפתרון:** `add_rtl_bullet_list()` משתמשת בסגנון `List Bullet` **אחרי** ש-`set_document_rtl()` כבר תיקן את הסגנון עצמו. בנוסף היא מגדירה `pPr/ind` עם `w:right` במקום `w:left` לכל פריט.

### 5. מעורב עברית-אנגלית בתוך פסקה

**הבעיה:** run עם טקסט מעורב "שלח ל-`user@example.com` בהקדם" נשבר — ה-email יופיע באמצע הפסקה אבל עם סימני ניקוד או סוגריים מעופפים למקום הלא נכון.

**הפתרון:** שני רבדים —

1. על כל run עברי/ערבי: `set_run_rtl(run)` שמוסיף `<w:rtl/>` ל-`rPr` של ה-run. זה אומר ל-Word "זה טקסט RTL" ברמת ה-run ולא רק הפסקה.
2. פיצול טקסט מעורב: `add_mixed_rtl_paragraph(doc, parts)` — מקבל רשימת tuples `[("text", "rtl"), ("user@example.com", "ltr"), ("בהקדם", "rtl")]` ומייצר run נפרד לכל חלק עם ה-rtl flag המתאים. Word יודע לשלב אותם נכון בזכות algorithm Unicode Bidi כשכל run מסומן כהלכה.

## בדיקה עצמית לפני סיום

לפני `doc.save()`, הקוד **חייב** להריץ `final_rtl_audit(doc)` שמבצע:

- `assert` שלכל `w:p` במסמך יש `w:bidi` ב-`pPr` שלה.
- `assert` שלכל `w:tbl` יש `w:bidiVisual` ב-`tblPr`.
- `assert` שלסגנונות Heading 1–3 (לפחות) יש `w:bidi` ב-`styles.xml`.
- לסעיף הראשי — `w:sectPr` מכיל `w:rtlGutter` ו-`w:bidi`.

אם `assert` נכשל — הפונקציה מתקנת אוטומטית במקום לזרוק שגיאה, ומדפיסה log של מה תוקן. זה ה"safety net" שמבטיח שגם אם קלוד שכח משהו באמצע הסקריפט — המסמך יוצא תקין.

## הוראות אכיפה לקלוד

- **אסור** להשתמש ב-`doc.add_paragraph()`, `doc.add_heading()`, `doc.add_table()` ישירות. תמיד דרך הפונקציות של הסקיל.
- **אסור** לדלג על `set_document_rtl()` בתחילת כל סקריפט.
- **אסור** לדלג על `final_rtl_audit()` לפני `doc.save()`.
- **אסור** לטעון שמסמך "RTL מוכן" אם לא רץ ה-audit.
- אם המשתמשת מבקשת משהו שלא מכוסה בפונקציות הקיימות (למשל header/footer, textbox, SmartArt) — קלוד כותב פונקציית RTL חדשה באותה תבנית לפני שהוא משתמש בה, ולא מתפשר על XML ברירת מחדל של python-docx.

## קובץ העזר

ראה `rtl_helpers.py` בתיקיית הסקיל. הקובץ מכיל את כל הפונקציות המוזכרות כאן, מוכנות להעתקה או לייבוא. לקריאה מלאה לפני השימוש הראשון.

## דוגמת שימוש מינימלית

```python
from docx import Document
from rtl_helpers import (
    set_document_rtl, add_rtl_paragraph, add_rtl_heading,
    add_rtl_numbered_list, add_rtl_bullet_list,
    set_table_rtl, add_mixed_rtl_paragraph, final_rtl_audit,
)

doc = Document()
set_document_rtl(doc)  # חובה — לפני כל דבר אחר

add_rtl_heading(doc, "דוח ממצאים", level=1)
add_rtl_paragraph(doc, "להלן סיכום הבדיקה שבוצעה השבוע.")

add_rtl_numbered_list(doc, [
    "איסוף נתונים מרשות ני\"ע",
    "ניתוח התאמה לתקנות",
    "ניסוח המלצות לדירקטוריון",
])

add_mixed_rtl_paragraph(doc, [
    ("לפרטים נוספים פנו לכתובת ", "rtl"),
    ("info@highlaw.co.il", "ltr"),
    (" או בטלפון המשרד.", "rtl"),
])

table = doc.add_table(rows=2, cols=3)
table.rows[0].cells[0].text = "סעיף"
table.rows[0].cells[1].text = "סטטוס"
table.rows[0].cells[2].text = "אחראי"
table.rows[1].cells[0].text = "בדיקת ציות"
table.rows[1].cells[1].text = "הושלם"
table.rows[1].cells[2].text = "ריבה"
set_table_rtl(table)  # חובה — אחרי מילוי התוכן

final_rtl_audit(doc)  # חובה — לפני השמירה
doc.save("output.docx")
```

## מה *לא* מכוסה בסקיל הזה

- docx-js (יש skill נפרד לכך — `rtl-enforcer-docx` הישן מכסה את העקרונות).
- HTML / markdown RTL — יש skill נפרד (`rtl-enforcer`).
- PDF ישירות — צריך לייצר DOCX ואז להמיר.
- Google Docs API.

אם ההקשר הוא אחד מאלה, קלוד לא מפעיל את הסקיל הזה ומפנה לסקיל המתאים.

## סיום כל הודעה

**כל הודעה מסתיימת בשורה המתוסרטת האחרונה שלה או בשאלה שנשאלה. אין לסכם את התור אחריה, לא בעברית ולא באנגלית.** שורה באנגלית בסוף הודעה עברית נראית ללקוח כתקלה, וזו השגיאה השכיחה ביותר.
