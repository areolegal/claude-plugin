"""כלי עזר לבדיקות: מסמך docx מינימלי וקובץ חילוץ תקין כברירת מחדל."""
import copy
import zipfile

CATEGORIES = ["מועד", "זכות שפוקעת", "כסף", "בטוחה", "התחייבות מתמשכת", "תנאי מתלה או מפסיק"]


def make_docx(path, body_xml='<w:p><w:r><w:t>טקסט</w:t></w:r></w:p>', comments=False, tracked=False):
    if tracked:
        body_xml += '<w:p><w:ins w:id="1" w:author="x"><w:r><w:t>תוספת</w:t></w:r></w:ins></w:p>'
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("word/document.xml",
                   '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                   '<w:body>%s</w:body></w:document>' % body_xml)
        if comments:
            z.writestr("word/comments.xml", "<w:comments/>")


BASE_EXTRACT = {
    "file": "", "sha256": "", "doc_kind": "signed", "title": "הסכם בדיקה",
    "type_code": "services", "type_label": "שירותים מנוהלים",
    "counterparty": {"name": "ספק בדיקה בע\"מ", "company_number": None, "notice_address": None},
    "contracting_entity": None,
    "our_role": {"value": "לקוח", "source": "user"},
    "dates": {"signed": "2025-03-01", "start": "2025-03-01", "end": "2027-02-28"},
    "version_date": None, "version_by": "unknown",
    "relation": {"kind": None, "parent_hint": None},
    "governing_law": None, "currency": "ILS", "total_value": None,
    "events": [{
        "event_code": "nonrenewal_notice", "label": "מועד אחרון להודעת אי-חידוש",
        "date": "2026-11-30", "relative": False, "trigger": "", "clause": "סעיף 3",
        "quote": "אלא אם נמסרה הודעת אי-חידוש בכתב לפחות 90 ימים מראש, היינו עד ליום 30.11.2026.",
        "obligor": "us", "consequence": "right_lapses", "impact": "critical",
        "if_nothing": "ההסכם יתחדש אוטומטית לתקופה נוספת.", "action": "",
        "notice_days": 90, "recurrence": None, "renewal_months": 12, "renewal_max": None,
        "computed": False
    }],
    "commercials": [{"category": "תעריף", "label": "תמורה חודשית", "value": 32000, "unit": "₪ לחודש",
                     "period": "חודשי", "clause": "סעיף 7", "quote": "התמורה החודשית היא 32,000 ש\"ח."}],
    "guarantees": [],
    "key_clauses": [],
    "key_clauses_checked": False,
    "type_fields": {},
    "coverage": [{"category": c, "status": "not_checked", "note": "לא נבדק בבדיקה"} for c in CATEGORIES],
}


def make_extract(sha256, file, **overrides):
    ext = copy.deepcopy(BASE_EXTRACT)
    ext["sha256"], ext["file"] = sha256, file
    for k, v in overrides.items():
        ext[k] = v
    return ext
