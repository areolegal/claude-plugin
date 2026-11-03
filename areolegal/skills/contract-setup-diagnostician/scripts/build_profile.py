# -*- coding: utf-8 -*-
"""
בונה את פרופיל-לקוח.json מתשובות השאלון, וגוזר את הרגולטורים לפי טבלאות
המיפוי שב-references/full_spec.md.

מדוע סקריפט ולא גזירה בכל הרצה: מיפוי הרגולטורים הוא כלל דטרמיניסטי, ולא
שיקול דעת. גזירה ידנית חוזרת בכל התקנה מייצרת שונות בין לקוחות באותו מצב
עובדתי, וזה בדיוק מה שפרופיל אמור למנוע. הסקריפט אינו שואל דבר ואינו ממציא
דבר: הוא מקבל את התשובות שכבר נמסרו ומחיל עליהן את הטבלאות.

הרצה, בשני שלבים (הפרופיל נשמר רק אחרי אישור המשתמש):
  1. תצוגה מקדימה, בלי כתיבה לדיסק. מדפיסה את שתי טבלאות התקציר לאישור:
     python3 -B build_profile.py --answers answers.json --preview
  2. אחרי האישור, עם התשובות המתוקנות אם תוקן שדה:
     python3 -B build_profile.py --answers answers.json --out Areo-נתונים/פרופיל-לקוח.json

עדכון שדה בודד בפרופיל קיים, בלי לבנות אותו מחדש (profile_id, התאריכים וכל השאר נשמרים; last_updated מתעדכן):
     python3 -B build_profile.py --set organization_name_en="<השם הרשום באנגלית>" --out Areo-נתונים/פרופיל-לקוח.json
  עם --preview: מדפיס את השינוי ואינו כותב. רק השדות שהכללים המשותפים (1.7) מתירים (SET_ALLOWED); כל שדה אחר: סירוב.

העותק ל-Areo: מידע ציבורי בלבד, מרשימת שדות חיובית (PUBLIC_FIELDS); הפרופיל עצמו אינו משתנה:
     python3 -B build_profile.py --areo-copy --out Areo-נתונים/פרופיל-לקוח.json [--to <קובץ זמני>]

מבנה answers.json:
{
  "organization_name": "שם החברה",
  "organization_name_en": "השם הרשום באנגלית (רשות; בהסכם באנגלית הישות נכתבת בו)",
  "registration_number": "515555551",
  "incorporation_country": "ישראל",
  "organization_type": "חברה פרטית",
  "listed_in": ["ישראל", "רישום דואלי"],
  "dual_listed_in": ["נאסד״ק", "ניו יורק (NYSE)"],
  "sectors": ["הייטק", "סייבר"],
  "activity_description": "תיאור חופשי קצר, כלשונו",
  "financial_activity": ["מנהל תיקים"],
  "markets": ["ישראל", "האיחוד האירופי"],
  "signer": "שם ותפקיד החותם על המסמכים היוצאים",
  "logo": "אעלה עכשיו | אוסיף מאוחר יותר | בלי לוגו",
  "logo_path": "Areo-נתונים/<שם-הקובץ>",
  "website": "כתובת אתר החברה (רשות), למשל example.co.il",
  "brand_theme": "כן | לא (נשאל רק כשצורף לוגו או נמסרה כתובת אתר)",
  "display_language": "he",
  "shared_output_folder": "<התיקייה שחוברה לשיחה, או null>",
  "user_declared_regulators": ["רגולטור שהמשתמש הוסיף בתקציר"],
  "removed_regulators": ["רגולטור שהמשתמש ביקש להסיר"]
}

שפה: הטופס נשלח בעברית או באנגלית, והערכים מגיעים בתוויות הקבועות של אחת משתי השפות
(EN_LABELS). שתיהן מתקבלות, ומלל חופשי נשמר כלשונו. התקציר (--preview), שמות הרגולטורים,
הבסיס והשדות הטקסטואליים בפרופיל נכתבים בשפת display_language: בעברית כמו קודם, ובאנגלית
בלי אף מילה עברית (חוץ ממלל חופשי שהמשתמש הקליד בעברית).

ריבוי ישויות: "entities": [{...}, {...}]. כל רשומה יורשת מהקודמת את מה שלא
נמסר בה (הרשומה הראשונה יורשת מהשדות שבראש הקובץ). כשיש שתי ישויות או יותר,
--out מצביע על Areo-נתונים/פרופיל-לקוח.json כרגיל, אבל נכתבים במקומו
Areo-נתונים/ישויות/<שם-הישות>/פרופיל-לקוח.json לכל ישות, והמרשם
Areo-נתונים/ישויות.json.

מיתוג סביבות העבודה בצבעי הלקוח (branding.theme): בהסכמת הלקוח בלבד. הצבעים נגזרים פעם אחת, מהלוגו, מאתר
החברה שבפרופיל או מצבעים שהמשתמש מסר, ונשמרים בפרופיל; כל רכיב שמפיק סביבת עבודה HTML מחיל אותם:
  python3 -B build_profile.py --derive-theme [--fetch-site] [--site-file page.html] [--colors "#1B4F9C,#F2A900"] --out <פרופיל>
  --fetch-site קורא רק את דף הבית של branding.website ואת גיליונות הסגנון שלו מאותו אתר (GET, בלי שום מידע של הלקוח).
  עם --preview: מדפיס את הצבעים ואינו כותב.

הוספת ישות להתקנה קיימת (בלי לגעת בפרופיל הקיים): --add-entity, עם --out של פרופיל-לקוח.json שבשורש.
  python3 -B build_profile.py --answers answers.json --add-entity [--inherit] --out Areo-נתונים/פרופיל-לקוח.json
  הפרופיל החדש נכתב ב-ישויות/<שם-הישות>/, ונרשם ב-ישויות.json; בלי מרשם, הוא נוצר והישות הקיימת נרשמת בו
  ראשונה, בנתיב שבו היא יושבת. --inherit: שדה שחסר בתשובות נורש מישות ברירת המחדל. ישות שכבר רשומה (שם או
  מספר רישום) או תיקייה קיימת: סירוב, קוד 2.

מורשי חתימה: "signer" מהטופס, ובו חותם אחד או כמה מופרדים ב-";", או "signatories" (רשימה), או "signatory"
(יחיד, תאימות לאחור). בפרופיל: branding.signatories[], והראשון הוא גם branding.lawyer_name ו-lawyer_role.
"""
import argparse
import io
import json
import os
import re
import sys
import uuid
import zlib
from datetime import date

SCHEMA_VERSION = "1.0"
CORE_VERSION = "2.1.0"

# הרשימה הסגורה שמוצגת למשתמש. כל היתר נשמרים ואינם מוצגים.
PRIMARY_DISPLAY = [
    "הרשות להגנת הפרטיות",
    "רשות התחרות",
    "רשות ניירות ערך",
    "רשות שוק ההון, ביטוח וחיסכון",
    "בנק ישראל, הפיקוח על הבנקים",
    "SEC",
    "FCA",
    "EDPB and the national data protection authorities · מפקחות על הגנת המידע האישי והעברתו באיחוד האירופי",
    "ICO · מפקח על הגנת המידע האישי בבריטניה",
    "FTC and the state privacy regulators · מפקחים על הגנת הצרכן והפרטיות בארצות הברית, פדרלית ובמדינות",
    # גופים ציבוריים ומגזר שלישי: הרגולטור של צורת ההתאגדות, ואילוץ ההתקשרות של גוף ציבורי
    "רשם העמותות",
    "רשם ההקדשות",
    "המועצה להשכלה גבוהה ות״ת",
    "רשות החברות הממשלתיות",
    "משרד הפנים, הממונה על המחוז",
    "Charity Commission",
    "IRS, 501(c)(3)",
    "Office for Students",
]

# "מימון המונים" הוא הנוסח שבטופס; "רכז הצעה, מימון המונים" הוא הנוסח הקודם במפרט. שניהם מתקבלים.
SEC_ISA = {"מנהל תיקים", "יועץ השקעות", "משווק השקעות", "מנהל קרנות נאמנות",
           "חתם", "נאמן לאיגרות חוב", "זירת סוחר", "מימון המונים", "רכז הצעה, מימון המונים",
           "חברת דירוג אשראי"}
CMISA = {"מבטח", "קרן פנסיה או גמל", "נותן שירותים פיננסיים מוסדר"}
BOI = {"תאגיד בנקאי", "חברת כרטיסי אשראי"}

SECTOR_REGULATORS = {
    "אנרגיה": ["רשות החשמל", "משרד האנרגיה", "המשרד להגנת הסביבה"],
    "ביומד": ["משרד הבריאות", "רשות החדשנות"],
    "בריאות": ["משרד הבריאות"],
    "מזון ומשקאות": ["משרד הבריאות", "הרשות להגנת הצרכן ולסחר הוגן"],
    "תקשורת ומדיה": ["משרד התקשורת"],
    "נדל״ן": ["רשם הקבלנים", "רשות מקרקעי ישראל"],
    "בנייה ותשתיות": ["רשם הקבלנים", "רשות מקרקעי ישראל", "המשרד להגנת הסביבה"],
    "ביטחון ותעופה": ["אפ״י", "BIS and DDTC · מפקחים על בקרת היצוא הביטחוני והדו-שימושי של ארצות הברית"],
    "תחבורה ולוגיסטיקה": ["משרד התחבורה"],
    "חינוך": ["משרד החינוך", "הרשות להגנת הצרכן ולסחר הוגן"],
    "קמעונאות": ["הרשות להגנת הצרכן ולסחר הוגן"],
    "תיירות ומלונאות": ["הרשות להגנת הצרכן ולסחר הוגן"],
    "תעשייה": ["המשרד להגנת הסביבה", "רשות החדשנות"],
    "הייטק": ["רשות החדשנות"],
    "סייבר": ["רשות החדשנות"],
}
# רגולטורים ענפיים שאינם ישראליים: חלים בלי קשר לזיקה לישראל.
SECTOR_NOT_IL = {"BIS and DDTC · מפקחים על בקרת היצוא הביטחוני והדו-שימושי של ארצות הברית"}
# קרקע וקבלנות: חלים רק כשהחברה פועלת בשוק הישראלי, לא מעצם ההתאגדות.
SECTOR_IL_MARKET_ONLY = {"רשם הקבלנים", "רשות מקרקעי ישראל"}

MARKET_REGULATORS = {
    "האיחוד האירופי": [("EDPB and the national data protection authorities · מפקחות על הגנת המידע האישי והעברתו באיחוד האירופי", "Likely"),
                       ("European AI Office · מפקח על פיתוח ושימוש במערכות בינה מלאכותית באיחוד האירופי", "Likely")],
    "בריטניה": [("ICO · מפקח על הגנת המידע האישי בבריטניה", "Potential"), ("SFO · חוקר ותובע שוחד ומרמה חמורה בבריטניה", "Likely")],
    "ארצות הברית": [("FTC and the state privacy regulators · מפקחים על הגנת הצרכן והפרטיות בארצות הברית, פדרלית ובמדינות", "Potential"),
                    ("DOJ · אוכף את איסור השוחד של גורמים זרים", "Likely"), ("OFAC", "Likely"), ("BIS", "Likely")],
}

# צורות התאגדות ישראליות. חלות רק כשמדינת ההתאגדות היא ישראל. בגופים ציבוריים ובמגזר השלישי המעמד
# Likely או Potential: הצורה הוצהרה, ולא נבדק אם הגוף רשום, מתוקצב או פטור (הקדש מול מלכ"ר, מוסד מתוקצב).
# גוף ציבורי: אין בקוד חקיקה בשמה. כללי הרכש של הגוף נשלפים במחקר העומק, מרשימת המקורות המאושרים.
CORPORATE_REGULATORS = {
    "חברה ממשלתית": [("רשות החברות הממשלתיות", "Likely")],
    "עמותה": [("רשם העמותות", "Likely")],
    "חל״צ (חברה לתועלת הציבור)": [("רשם ההקדשות", "Likely")],
    "הקדש או מלכ״ר": [("רשם ההקדשות", "Potential")],
    "מוסד להשכלה גבוהה או אוניברסיטה": [("המועצה להשכלה גבוהה ות״ת", "Likely")],
    "גוף ציבורי או משרד ממשלתי": [],
    "רשות מקומית": [("משרד הפנים, הממונה על המחוז", "Likely", "corp_local")],
    "תאגיד סטטוטורי": [],
    "שותפות": [("רשם השותפויות, רשות התאגידים", "Confirmed")],
    "אגודה שיתופית": [("רשם האגודות השיתופיות", "Confirmed")],
    # הנוסחים הקודמים של הטופס, לתשובות ולפרופילים שנבנו בהם
    "עמותה או חל״צ": [("רשם העמותות", "Likely"), ("רשם ההקדשות", "Potential")],
    "גוף ציבורי (משרד ממשלתי, רשות מקומית, תאגיד סטטוטורי)": [],
}
# מגזר שלישי ומוסד להשכלה גבוהה מחוץ לישראל: חלים לפי מדינת ההתאגדות (Likely) או לפי השוק (Potential),
# בלי קשר לזיקה לישראל. אוניברסיטה באנגליה מפוקחת בידי ה-OfS, ולא בידי ה-Charity Commission.
NONPROFIT_FORMS = {"עמותה", "חל״צ (חברה לתועלת הציבור)", "הקדש או מלכ״ר", "עמותה או חל״צ"}
HIGHER_ED_FORMS = {"מוסד להשכלה גבוהה או אוניברסיטה"}
FOREIGN_FORM_REGULATORS = [
    # (צורות, קוד מדינה, השוק בטופס, רגולטור)
    (NONPROFIT_FORMS, "GB", "בריטניה", "Charity Commission"),
    (NONPROFIT_FORMS | HIGHER_ED_FORMS, "US", "ארצות הברית", "IRS, 501(c)(3)"),
    (HIGHER_ED_FORMS, "GB", "בריטניה", "Office for Students"),
]
# צורות שאינן חברה: רשם החברות אינו חל עליהן מכוח הציר הרוחבי
NON_COMPANY_FORMS = {"עמותה", "הקדש או מלכ״ר", "גוף ציבורי או משרד ממשלתי", "רשות מקומית", "תאגיד סטטוטורי",
                     "גוף ציבורי (משרד ממשלתי, רשות מקומית, תאגיד סטטוטורי)", "שותפות", "אגודה שיתופית"}
PUBLIC_FORMS = {"חברה ממשלתית", "גוף ציבורי או משרד ממשלתי", "רשות מקומית", "תאגיד סטטוטורי",
                "מוסד להשכלה גבוהה או אוניברסיטה", "גוף ציבורי (משרד ממשלתי, רשות מקומית, תאגיד סטטוטורי)"}

# בורסות, לפי קוד. הקוד נגזר מהנוסח שבטופס (venue_code).
VENUE_REGULATORS = {
    "TASE": [("רשות ניירות ערך", "Confirmed"), ("הבורסה לניירות ערך בתל אביב", "Confirmed")],
    "NASDAQ": [("SEC", "Confirmed")],
    "NYSE": [("SEC", "Confirmed")],
    "LSE": [("FCA", "Confirmed")],
    "FSE": [("BaFin", "Confirmed")],
}

COUNTRY_CODES = {
    "ישראל": "IL", "israel": "IL", "isr": "IL", "מדינת ישראל": "IL", "state of israel": "IL",
    "ארצות הברית": "US", "ארה״ב": "US", "ארה\"ב": "US", "united states": "US", "usa": "US", "us": "US",
    "united states of america": "US", "america": "US",
    "בריטניה": "GB", "אנגליה": "GB", "הממלכה המאוחדת": "GB", "united kingdom": "GB", "uk": "GB", "gbr": "GB",
    "great britain": "GB", "britain": "GB", "england": "GB", "england and wales": "GB", "wales": "GB",
    "scotland": "GB", "northern ireland": "GB", "סקוטלנד": "GB", "ויילס": "GB", "צפון אירלנד": "GB",
    "גרמניה": "DE", "germany": "DE", "deu": "DE", "צרפת": "FR", "france": "FR", "fra": "FR",
    "הולנד": "NL", "netherlands": "NL", "the netherlands": "NL", "holland": "NL", "nld": "NL",
    "אירלנד": "IE", "ireland": "IE", "irl": "IE", "republic of ireland": "IE",
    "קפריסין": "CY", "cyprus": "CY", "cyp": "CY",
    "איטליה": "IT", "italy": "IT", "ita": "IT", "ספרד": "ES", "spain": "ES", "esp": "ES",
    "פורטוגל": "PT", "portugal": "PT", "prt": "PT", "בלגיה": "BE", "belgium": "BE", "bel": "BE",
    "לוקסמבורג": "LU", "luxembourg": "LU", "lux": "LU", "אוסטריה": "AT", "austria": "AT", "aut": "AT",
    "שוודיה": "SE", "sweden": "SE", "swe": "SE", "דנמרק": "DK", "denmark": "DK", "dnk": "DK",
    "פינלנד": "FI", "finland": "FI", "fin": "FI", "פולין": "PL", "poland": "PL", "pol": "PL",
    "צ'כיה": "CZ", "צכיה": "CZ", "czechia": "CZ", "czech republic": "CZ", "cze": "CZ",
    "יוון": "GR", "greece": "GR", "grc": "GR", "הונגריה": "HU", "hungary": "HU", "hun": "HU",
    "רומניה": "RO", "romania": "RO", "rou": "RO", "בולגריה": "BG", "bulgaria": "BG", "bgr": "BG",
    "קרואטיה": "HR", "croatia": "HR", "hrv": "HR", "סלובקיה": "SK", "slovakia": "SK", "svk": "SK",
    "סלובניה": "SI", "slovenia": "SI", "svn": "SI", "אסטוניה": "EE", "estonia": "EE", "est": "EE",
    "לטביה": "LV", "latvia": "LV", "lva": "LV", "ליטא": "LT", "lithuania": "LT", "ltu": "LT",
    "מלטה": "MT", "malta": "MT", "mlt": "MT",
    "שווייץ": "CH", "שוויץ": "CH", "switzerland": "CH", "che": "CH", "נורווגיה": "NO", "norway": "NO", "nor": "NO",
    "קנדה": "CA", "canada": "CA", "can": "CA", "אוסטרליה": "AU", "australia": "AU", "aus": "AU",
    "ניו זילנד": "NZ", "new zealand": "NZ", "סינגפור": "SG", "singapore": "SG", "sgp": "SG",
    "הונג קונג": "HK", "hong kong": "HK", "hkg": "HK", "הודו": "IN", "india": "IN", "ind": "IN",
    "סין": "CN", "china": "CN", "chn": "CN", "יפן": "JP", "japan": "JP", "jpn": "JP",
    "דרום קוריאה": "KR", "south korea": "KR", "korea": "KR", "kor": "KR",
    "איחוד האמירויות": "AE", "איחוד האמירויות הערביות": "AE", "united arab emirates": "AE", "uae": "AE", "are": "AE",
    "איי קיימן": "KY", "cayman islands": "KY", "cym": "KY",
    "איי הבתולה הבריטיים": "VG", "british virgin islands": "VG", "bvi": "VG", "vgb": "VG",
    "ג'רזי": "JE", "jersey": "JE", "גרנזי": "GG", "guernsey": "GG", "האי מאן": "IM", "isle of man": "IM",
    "גיברלטר": "GI", "gibraltar": "GI", "ברמודה": "BM", "bermuda": "BM",
    "דרום אפריקה": "ZA", "south africa": "ZA", "ברזיל": "BR", "brazil": "BR", "מקסיקו": "MX", "mexico": "MX",
    "טורקיה": "TR", "turkey": "TR", "türkiye": "TR", "turkiye": "TR", "אוקראינה": "UA", "ukraine": "UA",
}
# קוד דו-אותי שאינו ISO אבל נפוץ בהקלדה
ALPHA2_ALIASES = {"UK": "GB", "EL": "GR"}
# מדינות האיחוד האירופי: התאגדות באחת מהן מפעילה את ציר האיחוד האירופי, כמו שוק פעילות
EU_MEMBERS = {"AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE", "IT", "LV",
              "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE"}
# מדינות ארה"ב: התאגדות בהן היא התאגדות בארה"ב, והמדינה נשמרת ב-incorporation_state (US-DE, US-NY)
US_STATES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA", "colorado": "CO",
    "connecticut": "CT", "delaware": "DE", "florida": "FL", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS", "kentucky": "KY", "louisiana": "LA",
    "maine": "ME", "maryland": "MD", "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
    "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY", "north carolina": "NC",
    "north dakota": "ND", "ohio": "OH", "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA",
    "rhode island": "RI", "south carolina": "SC", "south dakota": "SD", "tennessee": "TN", "texas": "TX",
    "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY", "district of columbia": "DC", "washington dc": "DC", "washington d.c": "DC", "washington, d.c": "DC",
    "washington, dc": "DC",
    "דלאוור": "DE", "דלוור": "DE", "דלאוואר": "DE", "ניו יורק": "NY", "קליפורניה": "CA", "טקסס": "TX",
    "פלורידה": "FL", "מסצ'וסטס": "MA", "מסצ׳וסטס": "MA", "ניו ג'רזי": "NJ", "ניו ג׳רזי": "NJ", "נבדה": "NV",
    "אילינוי": "IL", "וושינגטון": "WA", "ויומינג": "WY", "קולורדו": "CO", "פנסילבניה": "PA",
    "וירג'יניה": "VA", "מרילנד": "MD", "קונטיקט": "CT", "מישיגן": "MI", "אוהיו": "OH", "יוטה": "UT",
}
# בריטניה: שלוש מערכות דין. קוד המדינה GB, והתחום נשמר ב-incorporation_state, באותם קודים כמו הדין החל
GB_JURISDICTIONS = {"england": "GB-EAW", "wales": "GB-EAW", "england and wales": "GB-EAW", "אנגליה": "GB-EAW",
                    "ויילס": "GB-EAW", "אנגליה ווילס": "GB-EAW", "אנגליה ויילס": "GB-EAW",
                    "scotland": "GB-SCT", "סקוטלנד": "GB-SCT", "northern ireland": "GB-NIR",
                    "צפון אירלנד": "GB-NIR"}

# שם מדינה בשתי השפות, לפי הקוד: השם העברי והאנגלי הראשונים ב-COUNTRY_CODES. לתצוגה של מדינה או שוק שאינם
# ברשימת הטופס ("קנדה" מוצג Canada בפרופיל אנגלי)
COUNTRY_NAMES = {}
for _k, _c in COUNTRY_CODES.items():
    _n = COUNTRY_NAMES.setdefault(_c, {})
    if re.search(r"[\u0590-\u05ff]", _k):
        _n.setdefault("he", _k)
    elif len(_k) > 3 and re.fullmatch(r"[a-z .'-]+", _k):
        _n.setdefault("en", " ".join(w if w in ("and", "of") else w.capitalize() for w in _k.split()))
# השווקים שבטופס, לפי קוד. כל שוק אחר מתקבל כלשונו: מדינה (קוד ISO) או אזור; מדינה באיחוד נגזרת כשוק האיחוד,
# ושוק שאין לו שורה בטבלה נרשם בלי רגולטור נגזר, עם שאלה פתוחה
MARKET_CODES = {"ישראל": "IL", "האיחוד האירופי": "EU", "בריטניה": "GB", "ארצות הברית": "US"}
MARKET_ROW = {"EU": "האיחוד האירופי", "GB": "בריטניה", "US": "ארצות הברית"}
EU_NAMES = {"eu", "european union", "האיחוד האירופי", "איחוד אירופי", "אירופה", "europe", "eea"}
# "לא נסחרת" שהגיע כערך ברשימת מקומות המסחר אינו מקום מסחר
NOT_LISTED = {"לא נסחרת", "לא", "not traded", "not listed", "none", "no", "-"}

STATUS_LABELS = {"he": {"Confirmed": "מאומת", "Likely": "סביר", "Potential": "אפשרי",
                        "UserDeclared": "הוצהר על ידכם"},
                 "en": {"Confirmed": "Verified", "Likely": "Likely", "Potential": "Possible",
                        "UserDeclared": "Declared by you"}}
LOGO_LABELS = {"he": {"attached": "צורף", "later": "יתווסף מאוחר יותר", "none": "בלי לוגו"},
               "en": {"attached": "Attached", "later": "To be added later", "none": "No logo"}}

# התוויות הקבועות של הטופס האנגלי. המפתח הוא התווית העברית, שהיא הערך הקנוני שהטבלאות
# שלמעלה כתובות בו. תווית אנגלית מומרת לקנונית לגזירה, ומוצגת ונשמרת בשפת display_language.
EN_LABELS = {
    "country": {"ישראל": "Israel", "ארצות הברית": "United States", "בריטניה": "United Kingdom",
                "גרמניה": "Germany", "צרפת": "France", "הולנד": "Netherlands", "אירלנד": "Ireland",
                "קפריסין": "Cyprus"},
    "form": {"חברה פרטית": "Private company",
             "חברה ציבורית (נסחרת בבורסה)": "Public company (listed on a stock exchange)",
             "חברת אג״ח (גייסה אג״ח לציבור)": "Bond issuer (raised bonds from the public)",
             "חברה ממשלתית": "Government company",
             "גוף ציבורי או משרד ממשלתי": "Public body or government ministry",
             "רשות מקומית": "Local authority (municipality or local council)",
             "תאגיד סטטוטורי": "Statutory corporation",
             "מוסד להשכלה גבוהה או אוניברסיטה": "University or higher education institution",
             "עמותה": "Non-profit association (amuta)",
             "חל״צ (חברה לתועלת הציבור)": "Public benefit company (PBC)",
             "הקדש או מלכ״ר": "Charity, trust, foundation or other non-profit",
             "חברת חוץ (חברה זרה הרשומה בישראל)": "Foreign company registered in Israel",
             "חברה זרה (לא רשומה בישראל)": "Foreign company (not registered in Israel)",
             "שותפות": "Partnership", "אגודה שיתופית": "Cooperative society",
             # הנוסחים הקודמים של הטופס: עדיין מתקבלים
             "גוף ציבורי (משרד ממשלתי, רשות מקומית, תאגיד סטטוטורי)":
                 "Public body (government ministry, local authority, statutory corporation)",
             "עמותה או חל״צ": "Non-profit association or public benefit company"},
    "listed": {"ישראל": "Israel (TASE)", "נאסד״ק": "Nasdaq", "ניו יורק (NYSE)": "New York (NYSE)",
               "לונדון": "London", "רישום דואלי": "Dual listing"},
    "dual": {"נאסד״ק": "Nasdaq", "ניו יורק (NYSE)": "New York (NYSE)", "לונדון (LSE)": "London (LSE)",
             "פרנקפורט": "Frankfurt"},
    "sector": {"הייטק": "High-tech", "פינטק": "Fintech", "פיננסים": "Finance", "ביטוח": "Insurance",
               "אנרגיה": "Energy", "שירותים": "Services", "נדל״ן": "Real estate", "ביומד": "Biomed",
               "בריאות": "Healthcare", "תעשייה": "Industry", "קמעונאות": "Retail",
               "תקשורת ומדיה": "Telecom and media", "תחבורה ולוגיסטיקה": "Transport and logistics",
               "מזון ומשקאות": "Food and beverages", "בנייה ותשתיות": "Construction and infrastructure",
               "ביטחון ותעופה": "Defense and aerospace", "סייבר": "Cyber", "חקלאות": "Agriculture",
               "חינוך": "Education", "תיירות ומלונאות": "Tourism and hospitality",
               "השכלה גבוהה ומחקר": "Higher education and research", "רווחה וקהילה": "Welfare and community",
               "שירותים ציבוריים ושלטון מקומי": "Public services and local government"},
    "fin": {"מנהל תיקים": "Portfolio manager", "יועץ השקעות": "Investment adviser",
            "משווק השקעות": "Investment marketer", "מנהל קרנות נאמנות": "Mutual fund manager",
            "חתם": "Underwriter", "נאמן לאיגרות חוב": "Bond trustee",
            "זירת סוחר": "Trading platform (forex and CFD)", "מימון המונים": "Crowdfunding (offering coordinator)",
            "רכז הצעה, מימון המונים": "Crowdfunding (offering coordinator)",
            "חברת דירוג אשראי": "Credit rating agency", "מבטח": "Insurer",
            "קרן פנסיה או גמל": "Pension or provident fund",
            "נותן שירותים פיננסיים מוסדר": "Regulated financial services provider",
            "תאגיד בנקאי": "Banking corporation", "חברת כרטיסי אשראי": "Credit card company"},
    "market": {"ישראל": "Israel", "האיחוד האירופי": "European Union", "בריטניה": "United Kingdom",
               "ארצות הברית": "United States"},
    "logo": {"אעלה עכשיו": "Upload now", "אוסיף מאוחר יותר": "Add later", "בלי לוגו": "No logo"},
    "brand": {"כן": "Yes", "לא": "No"},
}

# שמות הרגולטורים באנגלית, לפרופיל ולתקציר כש-display_language הוא en. הגזירה כולה בשמות העבריים.
REG_EN = {
    "הרשות להגנת הפרטיות": "Privacy Protection Authority (Israel)",
    "רשות התחרות": "Israel Competition Authority",
    "רשות ניירות ערך": "Israel Securities Authority",
    "רשות שוק ההון, ביטוח וחיסכון": "Capital Market, Insurance and Savings Authority (Israel)",
    "בנק ישראל, הפיקוח על הבנקים": "Bank of Israel, Banking Supervision Department",
    "EDPB and the national data protection authorities · מפקחות על הגנת המידע האישי והעברתו באיחוד האירופי": "EDPB and the national data protection authorities",
    "FTC and the state privacy regulators · מפקחים על הגנת הצרכן והפרטיות בארצות הברית, פדרלית ובמדינות": "FTC and the state privacy regulators",
    "רשות המסים": "Israel Tax Authority",
    "רשם החברות, רשות התאגידים": "Registrar of Companies, Israel Corporations Authority",
    "משרד העבודה, מינהל הסדרה ואכיפה": "Ministry of Labor, Regulation and Enforcement Administration",
    "המוסד לביטוח לאומי": "National Insurance Institute",
    "נציבות שוויון זכויות לאנשים עם מוגבלות": "Commission for Equal Rights of Persons with Disabilities",
    "הבורסה לניירות ערך בתל אביב": "Tel Aviv Stock Exchange",
    "רשות החברות הממשלתיות": "Government Companies Authority",
    "רשם העמותות": "Registrar of Non-profit Associations",
    "רשם השותפויות, רשות התאגידים": "Registrar of Partnerships, Israel Corporations Authority",
    "רשם האגודות השיתופיות": "Registrar of Cooperative Societies",
    "רשות החשמל": "Electricity Authority", "משרד האנרגיה": "Ministry of Energy",
    "המשרד להגנת הסביבה": "Ministry of Environmental Protection", "משרד הבריאות": "Ministry of Health",
    "רשות החדשנות": "Israel Innovation Authority",
    "הרשות להגנת הצרכן ולסחר הוגן": "Consumer Protection and Fair Trade Authority",
    "משרד התקשורת": "Ministry of Communications", "רשם הקבלנים": "Registrar of Contractors",
    "רשות מקרקעי ישראל": "Israel Land Authority", "אפ״י": "Defense Export Controls Agency (DECA)",
    "BIS and DDTC · מפקחים על בקרת היצוא הביטחוני והדו-שימושי של ארצות הברית": "BIS and DDTC", "משרד התחבורה": "Ministry of Transport", "משרד החינוך": "Ministry of Education",
    "European AI Office · מפקח על פיתוח ושימוש במערכות בינה מלאכותית באיחוד האירופי": "European AI Office", "SFO · חוקר ותובע שוחד ומרמה חמורה בבריטניה": "SFO",
    "DOJ · אוכף את איסור השוחד של גורמים זרים": "DOJ",
    "ICO · מפקח על הגנת המידע האישי בבריטניה": "ICO",
    "רשם ההקדשות": "Registrar of Endowments (Israel)",
    "המועצה להשכלה גבוהה ות״ת": "Council for Higher Education and its Planning and Budgeting Committee (Israel)",
    "משרד הפנים, הממונה על המחוז": "Ministry of Interior, District Commissioner (Israel)",
    "Charity Commission": "Charity Commission (UK)",
    "IRS, 501(c)(3)": "IRS, section 501(c)(3) (US)",
    "Office for Students": "Office for Students (UK)",
}
REG_HE = {v.casefold(): k for k, v in REG_EN.items()}

CATALOG_EN = {"הגנת הפרטיות ואבטחת מידע": "Privacy and data security", "שימוש במערכת AI": "AI system use",
              "איסור שוחד": "Anti-bribery", "סנקציות": "Sanctions", "בקרת יצוא": "Export controls",
              "פרטיות לפי דין מקומי": "Local-law privacy",
              "עיבוד מידע אישי על ידי צד שלישי": "Personal-data processing by a third party",
              "העברת מידע אישי בין מדינות": "Cross-border personal-data transfer",
              "התחייבויות כלפי מחזיקי ניירות ערך ואמות מידה פיננסיות": "Obligations to securities holders and financial covenants",
              "ציות רגולטורי פיננסי": "Financial regulatory compliance",
              "גילוי מכוח כללי שקיפות לציבור": "Disclosure under public-access rules",
              "כללי רכש והליך תחרותי": "Public procurement and competitive-procedure rules",
              "תקציב והתחייבות לתקופה": "Budget appropriation and multi-year commitment",
              "כספי תרומות ודיווח לרשם": "Restricted donor funds and reporting to the registrar"}

# כל מחרוזת שהסקריפט כותב לפרופיל או לתקציר, בשתי השפות
T = {
    "he": {"privacy": "הגנת הפרטיות; %s", "il_axis": "%s",
           "nx_inc": "התאגדות בישראל", "nx_foreign": "רישום כחברת חוץ בישראל", "nx_market": "שוק פעילות: ישראל",
           "corp": "צורת ההתאגדות: %s", "corp_inc": "צורת ההתאגדות: %s, התאגדות ב%s",
           "corp_mkt": "צורת ההתאגדות: %s; שוק פעילות: %s",
           "corp_local": "צורת ההתאגדות: %s; רשות מקומית", "bond": "חברת אג״ח, כתאגיד מדווח",
           "dual": "רישום כפול", "dual_on": "רישום דואלי ב%s", "listed_on": "נסחרת ב%s",
           "fin": "עיסוק מפוקח: %s", "sector": "ענף פעילות: %s", "market": "שוק פעילות: %s",
           "fin_mkt": "עיסוק מפוקח: %s; שוק פעילות: ישראל, בלי התאגדות או רישום בישראל",
           "geo_inc": "מדינת ההתאגדות: %s",
           "declared": "הוצהר על ידכם בהקמה",
           "q_country": "מדינת ההתאגדות לא נמסרה או אינה מוכרת, ולכן חסרים הרגולטורים שתלויים בה ובצורת "
                        "ההתאגדות. מסרו את מדינת ההתאגדות כדי להשלים אותם.",
           "q_dual": "נבחר רישום דואלי בלי הבורסות הזרות, ולכן הרגולטור שלהן לא זוהה. מסרו באילו בורסות.",
           "q_fin": "עיסוק פיננסי (%s) מחוץ לישראל: הרגולטור שלו אינו ברשימה. אפשר להוסיף אותו ידנית.",
           "q_signer": "שם החותם על המסמכים היוצאים לא נמסר.",
           "q_market": "שוק פעילות %s: אין לו רגולטור ברשימה, ולכן לא נוסף רגולטור. אפשר להוסיף אחד ידנית.",
           "q_regno": "מספר הרישום %s אינו עובר את בדיקת ספרת הביקורת. בדקו אותו.",
           "q_name_en": "השם הרשום באנגלית לא נמסר. בהסכם באנגלית הוא יידרש.",
           "q_title": "**שאלות פתוחות** (אפשר לענות עליהן עכשיו, או לאשר ולהשלים אחר כך)",
           "kept": "כמו בפרופיל הקודם: העובדות שעליהן הוא נשען לא השתנו",
           "chg_title": "**מה משתנה ברגולטורים**",
           "chg": "%s: היה %s, עכשיו %s", "chg_add": "%s: נוסף, %s", "chg_del": "%s: יורד מהרשימה",
           "pv": "תצוגה מקדימה: הפרופיל עוד לא נשמר.", "upd": "הפרופיל עודכן.", "saved": "הפרופיל נשמר.",
           "openq": "שאלה פתוחה: %s",
           "set_line": "%s: %s, במקום %s", "set_new": "%s: %s",
           "fields": {"display_language": "שפת הממשק", "deliverable_language": "שפת התוצרים",
                      "deliverable_language_basis": "הבסיס לשפת התוצרים", "organization_name_en": "השם הרשום באנגלית",
                      "registration_number": "מספר הרישום", "branding.signatories": "מורשי החתימה",
                      "branding.policy_approver": "מאשר המדיניות",
                      "branding.lawyer_name": "החותם", "branding.website": "אתר החברה", "branding.theme": "המיתוג",
                      "branding.logo_path": "הלוגו", "branding.logo_status": "הלוגו", "branding.logo_added_at": "הלוגו",
                      "departments_involved": "המחלקות המעורבות", "connections": "החיבורים"},
           "langs": {"he": "עברית", "en": "אנגלית", "both": "עברית ואנגלית"}, "none": "לא נמסר",
           "confidential": "חסוי: הוכן לצורך קבלת ייעוץ משפטי", "type_basis": "הצהרת המשתמש בהקמה",
           "method": "הצהרת המשתמש בלבד, בלי מחקר רשת",
           "note": "הפרופיל שומר זהות רגולטורים בלבד, ולא תוכן חובות.",
           "title": "**תקציר הפרופיל לאישור**", "head": "| שדה | ערך |",
           "r_name": "שם ומספר רישום", "v_name": "%s, מספר רישום %s", "r_country": "מדינת התאגדות",
           "r_name_en": "שם רשום באנגלית", "v_name_en_none": "לא נמסר (לא חובה)",
           "r_form": "צורת התאגדות", "r_listed": "היכן נסחרת", "r_sectors": "תחומי פעילות",
           "r_desc": "תיאור הפעילות", "r_markets": "שווקים", "r_signer": "חותם על המסמכים היוצאים",
           "r_lang": "שפת ממשק", "v_lang": {"he": "עברית", "en": "אנגלית"}, "r_logo": "לוגו",
           "r_site": "אתר החברה", "r_brand": "מיתוג סביבות העבודה בצבעי המותג", "v_yesno": {"yes": "כן", "no": "לא"},
           "missing": "לא נמסר", "not_listed": "לא נסחרת",
           "regs": "**רגולטורים עיקריים** (לפי התשובות שלכם)", "regs_head": "| רגולטור | מעמד | על סמך |",
           "no_regs": "| לפי התשובות, אף רגולטור מהרשימה אינו חל | | |"},
    "en": {"privacy": "Privacy protection; %s", "il_axis": "%s",
           "nx_inc": "Incorporated in Israel", "nx_foreign": "Registered in Israel as a foreign company",
           "nx_market": "Market: Israel",
           "corp": "Legal form: %s", "corp_inc": "Legal form: %s, incorporated in %s",
           "corp_mkt": "Legal form: %s; market: %s",
           "corp_local": "Legal form: %s; local authority",
           "bond": "Bond issuer, as a reporting corporation",
           "dual": "Dual listing", "dual_on": "Dual listing on: %s",
           "listed_on": "Listed on: %s",
           "fin": "Regulated activity: %s", "sector": "Sector: %s", "market": "Market: %s",
           "fin_mkt": "Regulated activity: %s; market: Israel, without incorporation or registration in Israel",
           "geo_inc": "Country of incorporation: %s",
           "declared": "Declared by you at setup",
           "q_country": "The country of incorporation was not given or is not recognized, so the regulators that "
                        "depend on it and on the legal form are missing. Give the country of incorporation to "
                        "complete them.",
           "q_dual": "Dual listing was selected without the foreign exchanges, so their regulator was not identified. Give the exchanges.",
           "q_fin": "Financial activity (%s) outside Israel: its regulator is not on the list. You can add it yourself.",
           "q_signer": "The signer of outgoing documents was not given.",
           "q_market": "Market %s: no regulator on the list, so none was added. You can add one yourself.",
           "q_regno": "The registration number %s fails the check digit. Check it.",
           "q_name_en": "The registered English name was not given. An English agreement will need it.",
           "q_title": "**Open questions** (answer them now, or approve and complete them later)",
           "kept": "As in the previous profile: the facts it rests on did not change",
           "chg_title": "**What changes in the regulators**",
           "chg": "%s: was %s, now %s", "chg_add": "%s: added, %s", "chg_del": "%s: leaves the list",
           "pv": "Preview only: the profile is not saved yet.", "upd": "The profile is updated.",
           "saved": "The profile is saved.", "openq": "Open question: %s",
           "set_line": "%s: %s (was %s)", "set_new": "%s: %s",
           "fields": {"display_language": "Interface language", "deliverable_language": "Output language",
                      "deliverable_language_basis": "Basis for the output language",
                      "organization_name_en": "Registered English name", "registration_number": "Registration number",
                      "branding.signatories": "Signatories", "branding.lawyer_name": "Signer",
                      "branding.policy_approver": "Policy approver",
                      "branding.website": "Company website", "branding.theme": "Branding",
                      "branding.logo_path": "Logo", "branding.logo_status": "Logo", "branding.logo_added_at": "Logo",
                      "departments_involved": "Departments involved", "connections": "Connections"},
           "langs": {"he": "Hebrew", "en": "English", "both": "Hebrew and English"}, "none": "not given",
           "confidential": "Privileged and confidential: prepared for the purpose of obtaining legal advice",
           "type_basis": "Declared by the user at setup", "method": "User declaration only, no web research",
           "note": "The profile records the identity of regulators only, not the content of obligations.",
           "title": "**Profile summary for approval**", "head": "| Field | Value |",
           "r_name": "Name and registration number", "v_name": "%s, registration number %s",
           "r_name_en": "Registered name in English", "v_name_en_none": "Not given (optional)",
           "r_country": "Country of incorporation", "r_form": "Legal form", "r_listed": "Where traded",
           "r_sectors": "Sectors", "r_desc": "Activity description", "r_markets": "Markets",
           "r_signer": "Signer of outgoing documents", "r_lang": "Interface language",
           "v_lang": {"he": "Hebrew", "en": "English"}, "r_logo": "Logo",
           "r_site": "Company website", "r_brand": "Brand the workspaces in your brand colours",
           "v_yesno": {"yes": "Yes", "no": "No"},
           "missing": "Not given", "not_listed": "Not traded",
           "regs": "**Primary regulators** (based on your answers)",
           "regs_head": "| Regulator | Status | Basis |",
           "no_regs": "| Based on your answers, no regulator on the list applies | | |"},
}

# שדה בתשובות -> רשימת התוויות שלו
FIELD_LABELS = {"incorporation_country": "country", "organization_type": "form", "listed_in": "listed",
                "dual_listed_in": "dual", "sectors": "sector", "financial_activity": "fin", "markets": "market",
                "logo": "logo", "brand_theme": "brand"}


def canon(kind, v):
    """התווית הקנונית (העברית) של ערך מהטופס, בכל אחת משתי השפות. ערך שאינו ברשימה: כלשונו."""
    s = str(v or "").strip()
    m = EN_LABELS.get(kind, {})
    if s in m:
        return s
    low = s.casefold()
    return next((he for he, en in m.items() if en.casefold() == low), s)


def label(kind, v, lang):
    """הערך הקנוני בשפת התצוגה. מלל חופשי: כלשונו; מדינה או שוק שאינם ברשימה ומזוהים כמדינה: שמם בשפת התצוגה."""
    if v in EN_LABELS.get(kind, {}):
        return EN_LABELS[kind][v] if lang == "en" else v
    if kind in ("country", "market") and v:
        code = market_code(v) if kind == "market" else country_code(v)
        if code == "EU":
            return EN_LABELS["market"]["האיחוד האירופי"] if lang == "en" else "האיחוד האירופי"
        if kind == "country" and parse_country(v)[1]:
            return v          # מדינה בארה"ב או תחום בבריטניה: כלשונו (Delaware)
        name = (COUNTRY_NAMES.get(code) or {}).get(lang)
        if name:
            return name
    return v


def market_code(m):
    """קוד השוק: IL, EU, GB, US, קוד ISO של מדינה אחרת, או None לשוק שאינו מזוהה (נשמר כלשונו)."""
    s_ = str(m or "").strip()
    if s_ in MARKET_CODES:
        return MARKET_CODES[s_]
    if s_.casefold() in EU_NAMES or canon("market", s_) == "האיחוד האירופי":
        return "EU"
    c = canon("market", s_)
    if c in MARKET_CODES:
        return MARKET_CODES[c]
    return country_code(s_)


def market_row(code):
    """שורת הטבלה בציר הגיאוגרפי לקוד שוק, או None. מדינה באיחוד היא שוק האיחוד."""
    if code in EU_MEMBERS:
        return MARKET_ROW["EU"]
    return MARKET_ROW.get(code)


def reg_label(name, lang):
    return REG_EN.get(name, name) if lang == "en" else name

# סעיפי קטלוג שהפרופיל מפעיל. רכיב הפלייבוק קורא את השדה הזה ראשון.
CATALOG_TRIGGERS = [
    (lambda a: True, ["הגנת הפרטיות ואבטחת מידע"]),
    # השוק כולל את מדינת ההתאגדות (geo_markets)
    (lambda a: "האיחוד האירופי" in geo_markets(a), ["עיבוד מידע אישי על ידי צד שלישי", "העברת מידע אישי בין מדינות", "שימוש במערכת AI"]),
    (lambda a: "בריטניה" in geo_markets(a), ["עיבוד מידע אישי על ידי צד שלישי", "העברת מידע אישי בין מדינות", "איסור שוחד"]),
    (lambda a: "ארצות הברית" in geo_markets(a), ["סנקציות", "בקרת יצוא", "פרטיות לפי דין מקומי"]),
    (lambda a: a["organization_type"].startswith("חברת אג״ח"),
     ["התחייבויות כלפי מחזיקי ניירות ערך ואמות מידה פיננסיות"]),
    (lambda a: bool(a["financial_activity"]), ["ציות רגולטורי פיננסי"]),
    # החברה עצמה גוף ציבורי או מגזר שלישי: הנושאים שהמעמד הזה מכניס לכל הסכם שלה (clause-catalog.md)
    (lambda a: a["organization_type"] in PUBLIC_FORMS,
     ["גילוי מכוח כללי שקיפות לציבור", "כללי רכש והליך תחרותי", "תקציב והתחייבות לתקופה"]),
    (lambda a: a["organization_type"] in NONPROFIT_FORMS, ["כספי תרומות ודיווח לרשם"]),
]
# נושא שחל רק על הסכם שיש בו הנושא עצמו, ולא על כל משפחה: הפרופיל אינו יודע
# אילו הסכמים יהיו, ולכן התנאי נשמר ב-clause_catalog_conditions, והרכיב שקורא את הקטלוג מחיל את הנושא רק על
# הסכם או משפחה שעומדים בו, לפי הפלייבוק או ההסכם עצמו
CATALOG_CONDITIONS = {
    "personal_data": {"he": "חל רק על הסכם שבו צד מעבד, מקבל, מעביר או ניגש למידע אישי, לפי הפלייבוק או ההסכם עצמו",
                      "en": "Applies only to an agreement under which a party processes, receives, transfers or "
                            "accesses personal data, according to the playbook or the agreement itself"},
    "ai": {"he": "חל רק על הסכם שיש בו פיתוח, אספקה או שימוש במערכת AI, לפי הפלייבוק או ההסכם עצמו",
           "en": "Applies only to an agreement that involves developing, supplying or using an AI system, "
                 "according to the playbook or the agreement itself"},
}
CATALOG_CONDITION_OF = {"הגנת הפרטיות ואבטחת מידע": "personal_data", "עיבוד מידע אישי על ידי צד שלישי": "personal_data",
                        "העברת מידע אישי בין מדינות": "personal_data", "פרטיות לפי דין מקומי": "personal_data",
                        "שימוש במערכת AI": "ai"}


def _country_key(s):
    s = re.sub(r"\s+", " ", str(s or "").replace("״", '"').replace("׳", "'").strip().strip(".")).casefold()
    return re.sub(r"^(the|state of|commonwealth of) ", "", s)


def _lookup_country(part):
    """(קוד, תחום) לחלק אחד של הנוסח, או (None, None)."""
    k = _country_key(part)
    if not k:
        return None, None
    if re.fullmatch(r"[a-z]{2}", k):
        up = k.upper()
        return ALPHA2_ALIASES.get(up, up), None
    m = re.fullmatch(r"([a-z]{2})-([a-z]{2,3})", k)
    if m:
        c = ALPHA2_ALIASES.get(m.group(1).upper(), m.group(1).upper())
        return c, "%s-%s" % (c, m.group(2).upper())
    keys = (k, k.replace('"', "״"), k.replace("'", "׳"))
    for kk in keys:
        if kk in GB_JURISDICTIONS:
            return "GB", GB_JURISDICTIONS[kk]
    for kk in keys:
        if kk in COUNTRY_CODES:
            return COUNTRY_CODES[kk], None
    for kk in keys:
        if kk in US_STATES:
            return "US", "US-" + US_STATES[kk]
    return None, None


def parse_country(raw):
    """(ISO-3166 alpha-2, תחום) מהנוסח שהמשתמש מסר, בעברית או באנגלית: שם מדינה, קוד דו-אותי או תלת-אותי, מדינה
    בארה"ב ("Delaware", "דלאוור", "Delaware, USA") או תחום בבריטניה ("England and Wales"). התחום נשמר ב-ISO-3166-2
    (US-DE, GB-EAW), באותם קודים כמו הדין החל. ערך לא מוכר: (None, None), והנוסח נשמר כלשונו בשדה נפרד."""
    s = (raw or "").strip()
    if not s:
        return None, None
    code, sub = _lookup_country(s)
    if code:
        return code, sub
    for part in re.split(r"\s*[,()/;]\s*|\s+-\s+", s):
        c, sb = _lookup_country(part)
        if c and code in (None, c):
            code, sub = c, sub or sb
    return code, sub


def country_code(raw):
    """ISO-3166 alpha-2 מהנוסח שהמשתמש מסר. ערך לא מוכר: None, והנוסח נשמר כלשונו בשדה נפרד."""
    return parse_country(raw)[0]


def venue_code(raw):
    s = (raw or "").lower()
    if "דואלי" in s or "dual" in s:
        return "DUAL"
    if "nyse" in s or "ניו יורק" in s:
        return "NYSE"
    if "נאסד" in s or "nasdaq" in s:
        return "NASDAQ"
    if "לונדון" in s or "london" in s or "lse" in s:
        return "LSE"
    if "פרנקפורט" in s or "frankfurt" in s:
        return "FSE"
    if "ישראל" in s or "תל אביב" in s or "tase" in s or "israel" in s or "tel aviv" in s:
        return "TASE"
    return None


def add(reg_list, name, status, basis):
    for r in reg_list:
        if r["regulator_name"] == name:
            order = {"Confirmed": 0, "Likely": 1, "Potential": 2, "UserDeclared": 3}
            if order[status] < order[r["applicability_status"]]:
                r["applicability_status"] = status
                r["basis"] = basis
            return
    reg_list.append({"regulator_name": name, "applicability_status": status, "basis": basis})


# צורות שמעידות על רישום בישראל, לבדיקת ספרת הביקורת גם כשמדינת ההתאגדות לא נמסרה
IL_REGISTERED_FORMS = {"חברת חוץ (חברה זרה הרשומה בישראל)", "עמותה", "חל״צ (חברה לתועלת הציבור)", "חברה ממשלתית",
                       "אגודה שיתופית", "עמותה או חל״צ"}


def il_check_digit(num):
    """ספרת הביקורת של מספר תאגיד ישראלי בן 9 ספרות (כמו common/ids.py; ההקמה אינה טוענת את הספרייה, ולכן עותק
    מינימלי כאן). מספר שאינו 9 ספרות: לא נבדק כאן (True)."""
    if not re.fullmatch(r"\d{9}", num):
        return True
    tot = 0
    for i, ch in enumerate(num):
        d = int(ch) * (1 if i % 2 == 0 else 2)
        tot += d - 9 if d > 9 else d
    return tot % 10 == 0


def nexus(a):
    """הזיקה לישראל. (inc, il_entity, il_market, key): il_entity הוא התאגדות בישראל או רישום כחברת חוץ בישראל, והוא
    לבדו מחיל את הציר הישראלי כולו. שוק פעילות ישראלי בלבד הוא זיקה חלשה: הוא מחיל רק את הפרטיות והתחרות, במעמד
    אפשרי, ואת הענפים והעיסוק הפיננסי במעמד אפשרי, ולעולם לא רשם החברות, העבודה, ביטוח לאומי, המסים או צורה
    ישראלית."""
    inc = country_code(a.get("incorporation_country"))
    il_market = any(market_code(m) == "IL" for m in a["markets"])
    foreign_reg = a["organization_type"].startswith("חברת חוץ")
    if inc == "IL":
        return inc, True, il_market, "nx_inc"
    if foreign_reg:
        return inc, True, il_market, "nx_foreign"
    if il_market:
        return inc, False, True, "nx_market"
    return inc, False, False, None


# מדינת ההתאגדות כשוק לציר הגיאוגרפי: חברה שהתאגדה בבריטניה, בארה"ב או במדינה באיחוד כפופה לרגולטורים שלהן גם
# כשלא סימנה אותן כשוק
def inc_market(inc):
    if inc == "GB":
        return "בריטניה"
    if inc == "US":
        return "ארצות הברית"
    if inc in EU_MEMBERS:
        return "האיחוד האירופי"
    return None


def market_rows(a):
    """שורות הטבלה של השווקים שבתשובות בלבד (מדינה באיחוד היא שורת האיחוד)."""
    out = []
    for m in a["markets"]:
        r = market_row(market_code(m))
        if r and r not in out:
            out.append(r)
    return out


def geo_markets(a):
    """שורות הטבלה של השווקים, ולצידן השוק של מדינת ההתאגדות. משמש לציר הגיאוגרפי ולקטלוג."""
    out = market_rows(a)
    im = inc_market(country_code(a.get("incorporation_country")))
    if im and im not in out:
        out.append(im)
    return out


def derive(a):
    """הגזירה על הערכים הקנוניים; הבסיס, השאלות הפתוחות ושמות הרגולטורים בשפת display_language."""
    lang = a["display_language"]
    t = T[lang]
    regs, unresolved = [], []
    inc, il, il_market, il_key = nexus(a)
    il_basis = t[il_key] if il_key else None
    # זיקה חלשה (שוק בלבד): מה שחל, חל במעמד אפשרי
    weak = il_market and not il
    if inc is None:
        unresolved.append(t["q_country"])
    reg_no = re.sub(r"[\s\-.]", "", str(a.get("registration_number") or ""))
    if reg_no and (inc == "IL" or a["organization_type"] in IL_REGISTERED_FORMS) and not il_check_digit(reg_no):
        unresolved.append(t["q_regno"] % reg_no)
    foreign = (inc not in (None, "IL")) or any(market_code(m) not in ("IL",) for m in a["markets"])
    if foreign and not (a.get("organization_name_en") or "").strip() and \
            re.search(r"[\u0590-\u05ff]", a.get("organization_name") or ""):
        unresolved.append(t["q_name_en"])

    # ציר 1, רוחבי ישראלי. כולו רק בהתאגדות בישראל או ברישום כחברת חוץ; בשוק בלבד, פרטיות ותחרות, אפשרי
    if il:
        add(regs, "הרשות להגנת הפרטיות", "Confirmed", t["privacy"] % il_basis)
        add(regs, "רשות התחרות", "Potential", t["il_axis"] % il_basis)
        for n in ["רשות המסים", "רשם החברות, רשות התאגידים",
                  "משרד העבודה, מינהל הסדרה ואכיפה", "המוסד לביטוח לאומי",
                  "נציבות שוויון זכויות לאנשים עם מוגבלות"]:
            if n == "רשם החברות, רשות התאגידים" and a["organization_type"] in NON_COMPANY_FORMS:
                continue
            add(regs, n, "Confirmed", t["il_axis"] % il_basis)
    elif weak:
        add(regs, "הרשות להגנת הפרטיות", "Potential", t["privacy"] % il_basis)
        add(regs, "רשות התחרות", "Potential", t["il_axis"] % il_basis)

    # ציר 2, מעמד תאגידי. צורות ישראליות רק בהתאגדות ישראלית: לא כשהמדינה זרה ולא כשאינה ידועה.
    form_l = label("form", a["organization_type"], lang)
    if inc == "IL":
        for name, status, *key in CORPORATE_REGULATORS.get(a["organization_type"], []):
            add(regs, name, status, t[key[0] if key else "corp"] % form_l)
    # מגזר שלישי ומוסד להשכלה גבוהה בבריטניה ובארה"ב: לפי ההתאגדות, או לפי השוק (אפשרי)
    for forms, code, market, name in FOREIGN_FORM_REGULATORS:
        if a["organization_type"] not in forms:
            continue
        if inc == code:
            add(regs, name, "Likely", t["corp_inc"] % (form_l, label("market", market, lang)))
        elif market in market_rows(a):
            add(regs, name, "Potential", t["corp_mkt"] % (form_l, label("market", market, lang)))
    # רישום דואלי ראשון, כדי שבסיס רשות ניירות ערך יהיה מתכונת הרישום הכפול (פרק ה׳3) ולא "נסחרת בישראל"
    venues = sorted(((v, venue_code(v)) for v in a["listed_in"]), key=lambda x: x[1] != "DUAL")
    if a["organization_type"].startswith("חברת אג״ח") and (
            any(c == "TASE" for _, c in venues) or (not venues and (il or weak))):
        add(regs, "רשות ניירות ערך", "Confirmed" if il or venues else "Potential", t["bond"])
    for where, code in venues:
        if code == "DUAL":
            add(regs, "רשות ניירות ערך", "Confirmed", t["dual"])
            if not a["dual_listed_in"]:
                unresolved.append(t["q_dual"])
            for dv in a["dual_listed_in"]:
                for name, status in VENUE_REGULATORS.get(venue_code(dv), []):
                    add(regs, name, status, t["dual_on"] % label("dual", dv, lang))
            continue
        for name, status in VENUE_REGULATORS.get(code, []):
            add(regs, name, status, t["listed_on"] % label("listed", where, lang))

    # ציר 3, עיסוק פיננסי. הרגולטורים כאן ישראליים, ולכן רק בזיקה לישראל; בשוק בלבד, אפשרי (הרישיון תלוי
    # בפעילות בישראל, שלא נשאלה).
    for act in a["financial_activity"]:
        act_l = label("fin", act, lang)
        if not il and not weak:
            unresolved.append(t["q_fin"] % act_l)
            continue
        fin_status = "Confirmed" if il else "Potential"
        fin_basis = t["fin"] % act_l if il else t["fin_mkt"] % act_l
        if act in SEC_ISA:
            add(regs, "רשות ניירות ערך", fin_status, fin_basis)
        elif act in CMISA:
            add(regs, "רשות שוק ההון, ביטוח וחיסכון", fin_status, fin_basis)
        elif act in BOI:
            add(regs, "בנק ישראל, הפיקוח על הבנקים", fin_status, fin_basis)

    # ציר 3ב, ענף. בשוק בלבד, אפשרי
    for sec in a["sectors"]:
        for name in SECTOR_REGULATORS.get(sec, []):
            if name in SECTOR_IL_MARKET_ONLY and not il_market:
                continue
            if name not in SECTOR_NOT_IL and not il and not weak:
                continue
            status = "Potential" if weak and name not in SECTOR_NOT_IL else "Likely"
            add(regs, name, status, t["sector"] % label("sector", sec, lang))

    # ציר 4, גיאוגרפי: השווקים שבטופס, ומדינת ההתאגדות (בריטניה, ארה"ב, מדינה באיחוד). בהתאגדות, מה שבשוק
    # אפשרי עולה לסביר: החברה עצמה כפופה לדין שם.
    for mk in a["markets"]:
        code = market_code(mk)
        row = market_row(code)
        if row:
            for name, status in MARKET_REGULATORS.get(row, []):
                add(regs, name, status, t["market"] % label("market", mk, lang))
        elif code != "IL":
            # שוק שאינו בטבלה: נרשם בלי רגולטור נגזר, ולא נדחה
            unresolved.append(t["q_market"] % label("market", mk, lang))
    im = inc_market(inc)
    if im:
        inc_l = label("country", (a.get("incorporation_country") or "").strip(), lang)
        for name, status in MARKET_REGULATORS.get(im, []):
            add(regs, name, "Likely" if status == "Potential" else status, t["geo_inc"] % inc_l)

    # תיקוני המשתמש בתקציר לאישור: הסרה יורדת מהטבלה, הוספה נשמרת UserDeclared ומוצגת תמיד.
    # שם שנכתב באנגלית מוחזר לשם הקנוני, כדי שהסרה תעבוד בשתי השפות.
    def to_canon(n):
        n = str(n).strip()
        return REG_HE.get(n.casefold(), n)
    removed = set(to_canon(n) for n in (a.get("removed_regulators") or []))
    regs = [r for r in regs if r["regulator_name"] not in removed]
    declared = [n for n in (a.get("user_declared_regulators") or []) if to_canon(n) not in removed]
    declared_c = set(to_canon(n) for n in declared)
    primary = [r for r in regs if r["regulator_name"] in PRIMARY_DISPLAY and r["regulator_name"] not in declared_c]
    secondary = [r for r in regs if r["regulator_name"] not in PRIMARY_DISPLAY and r["regulator_name"] not in declared_c]
    primary.sort(key=lambda r: PRIMARY_DISPLAY.index(r["regulator_name"]))
    for n in declared:
        primary.append({"regulator_name": n, "applicability_status": "UserDeclared",
                        "basis": t["declared"]})
    # שמות הרגולטורים בשפת display_language; הגזירה כולה נעשתה בשמות הקנוניים
    for r in primary + secondary:
        r["regulator_name"] = reg_label(r["regulator_name"], lang)
    return primary, secondary, unresolved


def normalize_answers(a):
    a = dict(a)
    for k, default in (("listed_in", []), ("dual_listed_in", []), ("sectors", []),
                       ("financial_activity", []), ("markets", []), ("display_language", "he")):
        if a.get(k) in (None, "", "-"):
            a[k] = default
    for k in ("listed_in", "dual_listed_in", "sectors", "financial_activity", "markets"):
        if isinstance(a[k], str):
            a[k] = [x.strip() for x in a[k].split(",") if x.strip() and x.strip() != "-"]
    a["listed_in"] = [x for x in a["listed_in"] if str(x).strip().casefold() not in NOT_LISTED]
    lang = str(a.get("display_language") or "he").strip().lower()
    a["display_language"] = "en" if lang in ("en", "english", "אנגלית") else "he"
    a["organization_type"] = (a.get("organization_type") or "").strip()
    if not a.get("registration_number") and a.get("company_number"):
        a["registration_number"] = a["company_number"]
    # תוויות הטופס האנגלי מומרות לקנוניות; מלל חופשי נשאר כלשונו
    for k, kind in FIELD_LABELS.items():
        if isinstance(a.get(k), list):
            a[k] = [canon(kind, x) for x in a[k]]
        elif a.get(k):
            a[k] = canon(kind, a[k])
    return a


# תואר בראש שם החותם, כמו risk/render_check.COUNSEL_TITLE_RE: השם נשמר בלי תואר
COUNSEL_TITLE_RE = re.compile(r'^\s*(?:עו(?:"|״|\x27\x27|”)ד|עוה(?:"|״)ד|עורך הדין|עורכת הדין|Adv\.?|Advocate)\s+', re.I)


def split_signer(raw, role=None):
    """"עו\"ד <שם>, יועצת משפטית (<Name>, General Counsel)" לשם, לתפקיד, לשם באנגלית ולתפקיד באנגלית.
    השם הוא מה שלפני הפסיק הראשון, בלי תואר; התפקיד הוא מה שאחריו, ותשובה מפורשת לתפקיד (role) גוברת עליו. שם
    בסוגריים בסוף הוא השם באנגלית, ומה שאחרי הפסיק שבתוכם הוא התפקיד באנגלית. בהסכם באנגלית הבועות נחתמות בשם
    האנגלי (lawyer_name_en)."""
    raw = (raw or "").strip()
    name_en = role_en = None
    m = re.search(r"\(([^()]*)\)\s*$", raw)
    if m and re.search(r"[A-Za-z]", m.group(1)):
        en = [x.strip() for x in m.group(1).split(",", 1)]
        name_en = COUNSEL_TITLE_RE.sub("", en[0]).strip() or None
        role_en = en[1] if len(en) > 1 and en[1] else None
        raw = raw[:m.start()].strip()
    parts = [x.strip() for x in raw.split(",", 1)]
    name = COUNSEL_TITLE_RE.sub("", parts[0]).strip() or None
    found_role = parts[1] if len(parts) > 1 and parts[1] else None
    return name, ((role or "").strip() or found_role), name_en, role_en


def signatories_of(a):
    """מורשי החתימה, [{name, role, name_en, role_en}]. עמותות ומוסדות חותמים לרוב בשניים.

    המקורות, לפי הסדר: signatories (רשימה של מחרוזות "שם, תפקיד" או של מילונים); signatory יחיד (מחרוזת או
    מילון, תאימות לאחור); ו-signer מהטופס, שבו כמה חותמים מופרדים ב-";" או בשורה חדשה. הראשון הוא גם
    branding.lawyer_name, השם שעל הבועות, כמו קודם."""
    raw = a.get("signatories")
    if raw in (None, "", "-", []):
        raw = a.get("signatory")
    if raw in (None, "", "-", []):
        raw = a.get("signer") or a.get("lawyer_name")
        raw = [x for x in re.split(r"\s*[;\n]\s*", raw or "") if x.strip() and x.strip() != "-"]
        if len(raw) == 1 and (a.get("signer_role") or a.get("lawyer_role")):
            raw = [{"name": raw[0], "role": a.get("signer_role") or a.get("lawyer_role")}]
    if isinstance(raw, (str, dict)):
        raw = [raw]
    out = []
    for item in raw or []:
        if isinstance(item, dict):
            n, r, ne, re_ = split_signer(item.get("name"), item.get("role"))
            ne, re_ = item.get("name_en") or ne, item.get("role_en") or re_
        else:
            n, r, ne, re_ = split_signer(str(item))
        if n:
            out.append({"name": n, "role": r, "name_en": ne, "role_en": re_})
    return out


def logo_state(a):
    path = a.get("logo_path") or None
    choice = (a.get("logo") or "").strip()
    if path:
        return "attached", path
    if choice in ("בלי לוגו", "none", "no logo", "No logo"):
        return "none", None
    if choice:
        return "later", None
    return "none", None


def build(a):
    for k in ("organization_name", "organization_type"):
        if not a.get(k):
            print("חסר שדה חובה בתשובות: %s" % k)
            sys.exit(2)

    lang = a["display_language"]
    t = T[lang]
    primary, secondary, unresolved = derive(a)
    catalog, catalog_cond = [], {}
    for cond, items in CATALOG_TRIGGERS:
        if cond(a):
            for canon_it in items:
                it = CATALOG_EN.get(canon_it, canon_it) if lang == "en" else canon_it
                if it not in catalog:
                    catalog.append(it)
                if canon_it in CATALOG_CONDITION_OF:
                    catalog_cond[it] = CATALOG_CONDITIONS[CATALOG_CONDITION_OF[canon_it]][lang]

    # הערכים נשמרים בשפת display_language: תווית מהרשימה מתורגמת, מלל חופשי כלשונו
    lab = lambda kind, vs: [label(kind, v, lang) for v in vs]  # noqa: E731
    sectors = lab("sector", a["sectors"])
    today = date.today().isoformat()
    reg_raw = (a.get("registration_number") or "").strip()
    reg_norm = re.sub(r"[\s\-.]", "", reg_raw) or None
    logo_status, logo_path = logo_state(a)
    website = normalize_website(a.get("website"))
    brand_choice = THEME_CHOICES.get(str(a.get("brand_theme") or "").strip())
    # השאלה מוצגת בטופס רק כשיש לוגו או אתר; בלעדיהם אין ממה למתג, ותשובה שהגיעה אינה נשמרת
    theme = {"choice": brand_choice, "asked_at": today} if brand_choice and (logo_path or website) else None
    signatories = signatories_of(a)
    first = signatories[0] if signatories else {}
    signer, signer_role, signer_en, signer_role_en = (first.get("name"), first.get("role"),
                                                      first.get("name_en"), first.get("role_en"))
    if not signer:
        unresolved.append(t["q_signer"])
    profile = {
        "schema_version": SCHEMA_VERSION,
        "core_version": CORE_VERSION,
        "profile_id": "orgprof_" + uuid.uuid4().hex[:12],
        "version": 1,
        "status": "Provisional",
        "checked_at": today,
        "confidential": t["confidential"],
        "organization_name": a["organization_name"],
        # שם רשום באנגלית, אופציונלי: בהסכם באנגלית הישות נכתבת בו. כלשונו, בלי תרגום
        "organization_name_en": (a.get("organization_name_en") or "").strip() or None,
        # registration_number כפי שנמסר; organization_id מנורמל (בלי רווחים, מקפים ונקודות), לבדיקות הזיהוי.
        "registration_number": reg_raw or None,
        "organization_id": reg_norm,
        "incorporation_country": country_code(a.get("incorporation_country")),
        # מדינה בארה"ב או תחום בבריטניה, ב-ISO-3166-2 (US-DE, GB-EAW), או null
        "incorporation_state": parse_country(a.get("incorporation_country"))[1],
        "incorporation_country_name": label("country", (a.get("incorporation_country") or "").strip(), lang) or None,
        "organization_type": label("form", a["organization_type"], lang),
        "organization_type_basis": t["type_basis"],
        "public_market": {"listed": bool(a["listed_in"]), "venues": lab("listed", a["listed_in"]),
                          "dual_listed_in": lab("dual", a["dual_listed_in"])},
        "sector": {"primary": sectors[0] if sectors else None,
                   "all": sectors,
                   "financial_activity": lab("fin", a["financial_activity"]),
                   "description": (a.get("activity_description") or "").strip() or None},
        "material_operating_jurisdictions": lab("market", a["markets"]),
        "regulatory_footprint_primary": primary,
        "regulatory_footprint_secondary": secondary,
        "clause_catalog_activated": catalog,
        # פריט שמופיע כאן חל רק על הסכם שעומד בתנאי; פריט שאינו כאן חל על כל הסכם של החברה
        "clause_catalog_conditions": catalog_cond,
        "unresolved_questions": unresolved,
        # תיקוני המשתמש בתקציר: נשמרים, כדי שעדכון פרופיל לא יחזיר רגולטור שהוסר
        "removed_regulators": [str(n).strip() for n in (a.get("removed_regulators") or []) if str(n).strip()],
        "onboarding": {"research_performed": False,
                       "method": t["method"]},
        "notes": [t["note"]],
        "branding": {"lawyer_name": signer,
                     "lawyer_role": signer_role,
                     "lawyer_name_en": signer_en,
                     "lawyer_role_en": signer_role_en,
                     # כל מורשי החתימה; lawyer_name ו-lawyer_role הם הראשון שבהם (תאימות לאחור)
                     "signatories": signatories,
                     "logo_path": logo_path,
                     "logo_added_at": today if logo_path else None,
                     "logo_status": logo_status,
                     "website": website,
                     "theme": theme},
        "display_language": a["display_language"],
        "deliverable_language": a.get("deliverable_language", a["display_language"]),
        # shared_output_folder is the root of Areo-נתונים, not just an output
        # target: null means this install serves one lawyer, a path means it
        # serves the department. Eight components read it, so it is always
        # present in the file, even when unanswered. The folder connected at
        # setup goes here only; agreement folders are recorded in
        # connections.folders by the components that scan them.
        "connections": a.get("connections", {
            "folders": [], "shared_output_folder": a.get("shared_output_folder"),
            "email": None, "calendar": None, "email_tracking": None,
            "doc_access": {"mode": "local", "baseUrl": ""}, "asked_at": ""}),
        "areo_notice_shown": True,
        "generated_at": today,
        "last_updated": today,
    }
    profile["connections"].setdefault("shared_output_folder", None)
    return profile


def cell(v):
    return str(v).replace("|", "/").replace("\n", " ")


def print_summary(p):
    """שתי טבלאות התקציר לאישור, בפורמט המחייב שבמפרט, בשפת display_language. בלי קודי מעמד פנימיים."""
    lang = p.get("display_language") if p.get("display_language") in T else "he"
    t = T[lang]
    miss = t["missing"]
    # פרופיל שנבנה בגרסה קודמת עלול להיות חסר שדות: התקציר מציג אותם כ"לא נמסר", ואינו נופל
    p = dict(p)
    p.setdefault("public_market", {"venues": [], "dual_listed_in": []})
    p["public_market"] = dict({"venues": [], "dual_listed_in": []}, **(p["public_market"] or {}))
    p["sector"] = dict({"all": [], "financial_activity": [], "description": None}, **(p.get("sector") or {}))
    p["branding"] = dict({"lawyer_name": None, "logo_status": "none"}, **(p.get("branding") or {}))
    if p["branding"].get("logo_status") not in LOGO_LABELS[lang]:
        p["branding"]["logo_status"] = "attached" if p["branding"].get("logo_path") else "none"
    for k in ("incorporation_country_name", "organization_name_en", "organization_type"):
        p.setdefault(k, None)
    p.setdefault("material_operating_jurisdictions", [])
    p.setdefault("regulatory_footprint_primary", [])
    p["display_language"] = lang
    reg = p.get("registration_number") or p.get("organization_id") or miss
    venues = ", ".join(v for v in p["public_market"]["venues"] if venue_code(v) != "DUAL")
    dual = p["public_market"]["dual_listed_in"]
    if any(venue_code(v) == "DUAL" for v in p["public_market"]["venues"]):
        venues = ((venues + ", " if venues else "") + label("listed", "רישום דואלי", lang)
                  + (" (%s)" % ", ".join(dual) if dual else ""))
    sectors = ", ".join(p["sector"]["all"]) or miss
    if p["sector"]["financial_activity"]:
        sectors += " (%s)" % ", ".join(p["sector"]["financial_activity"])
    rows = [(t["r_name"], t["v_name"] % (p["organization_name"], reg)),
            (t["r_name_en"], p.get("organization_name_en") or t["v_name_en_none"]),
            (t["r_country"], p["incorporation_country_name"] or miss),
            (t["r_form"], p["organization_type"] or miss),
            (t["r_listed"], venues or t["not_listed"]),
            (t["r_sectors"], sectors)]
    if p["sector"]["description"]:
        rows.append((t["r_desc"], p["sector"]["description"]))
    sigs = p["branding"].get("signatories") or ([{"name": p["branding"]["lawyer_name"],
                                                  "role": p["branding"].get("lawyer_role")}]
                                                if p["branding"]["lawyer_name"] else [])
    if lang == "en":   # בפרופיל אנגלי, השם והתפקיד באנגלית כשנמסרו
        sigs = [dict(x, name=x.get("name_en") or x.get("name"), role=x.get("role_en") or x.get("role")) for x in sigs]
    rows += [(t["r_markets"], ", ".join(p["material_operating_jurisdictions"]) or miss),
             (t["r_signer"], "; ".join(s["name"] + (", " + s["role"] if s.get("role") else "") for s in sigs)
              or miss),
             (t["r_lang"], t["v_lang"][p["display_language"]]),
             (t["r_logo"], LOGO_LABELS[lang][p["branding"]["logo_status"]])]
    if p["branding"].get("website"):
        rows.append((t["r_site"], p["branding"]["website"]))
    if (p["branding"].get("theme") or {}).get("choice"):
        rows.append((t["r_brand"], t["v_yesno"][p["branding"]["theme"]["choice"]]))
    print(t["title"])
    print("")
    print(t["head"])
    print("|---|---|")
    for k, v in rows:
        print("| %s | %s |" % (k, cell(v)))
    print("")
    print(t["regs"])
    print("")
    print(t["regs_head"])
    print("|---|---|---|")
    for r in p["regulatory_footprint_primary"]:
        print("| %s | %s | %s |" % (cell(r["regulator_name"]), STATUS_LABELS[lang][r["applicability_status"]],
                                   cell(r["basis"])))
    if not p["regulatory_footprint_primary"]:
        print(t["no_regs"])
    if p.get("unresolved_questions"):
        print("")
        print(t["q_title"])
        print("")
        for q in p["unresolved_questions"]:
            print("- " + q)


def entity_dirname(name):
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", name).strip().rstrip(".") or "ישות"


def write_json(path, obj):
    d = os.path.dirname(os.path.abspath(path))
    if d and not os.path.isdir(d):
        os.makedirs(d)
    io.open(path, "w", encoding="utf-8").write(json.dumps(obj, ensure_ascii=False, indent=2))
    json.load(io.open(path, encoding="utf-8"))  # נטען חזרה: JSON תקין, או חריגה


def report(p, path):
    t = T[p.get("display_language") if p.get("display_language") in T else "he"]
    print(t["saved"] + " " + path)
    en = p.get("display_language") == "en"   # האבחון בשפת הלקוח, כדי שגם אם נמסר כלשונו לא תהיה שפה שנייה
    print(("Primary regulators shown: %d. Other regulators, stored and not shown: %d" if en else
           "רגולטורים עיקריים, לתצוגה: %d. רגולטורים נוספים, נשמרים ואינם מוצגים: %d")
          % (len(p["regulatory_footprint_primary"]), len(p["regulatory_footprint_secondary"])))
    if p["clause_catalog_activated"]:
        print(("Clause topics activated: " if en else "סעיפי קטלוג שהופעלו: ") + ", ".join(p["clause_catalog_activated"]))
    for it, why in (p.get("clause_catalog_conditions") or {}).items():
        print(("Conditional clause topic: %s. %s" if en else "סעיף קטלוג מותנה: %s. %s") % (it, why))
    for q in p["unresolved_questions"]:
        print(t["openq"] % q)


# עדכון שדה בודד בפרופיל קיים (בנייה מחדש יוצרת profile_id חדש ומאבדת שדות). השדות שאינם משתנים כך: הזהות
# והגרסאות של הפרופיל, ותאריך היצירה
SET_PROTECTED = ("profile_id", "schema_version", "core_version", "generated_at", "checked_at", "version")
# שדה שאפשר להוסיף גם כשאינו בקובץ: פרופיל שנבנה לפני שהשדה נוסף, ותשובות המשתמש על הארגון שרכיב אחר רושם
# אחרי ההקמה (שפת התוצר ובסיסה, המחלקות המעורבות לכל משפחת הסכמים). שום דבר שנגזר ממסמך, מפלייבוק או מעסקה.
SET_NEW_OK = ("organization_name_en", "branding.signatories", "branding.policy_approver", "deliverable_language",
              "deliverable_language_basis",
              "departments_involved", "departments_involved.asked_at", "branding.website", "branding.theme",
              "branding.lawyer_name_en", "branding.lawyer_role_en")
# departments_involved.<משפחת ההסכמים>: כל משפחה, ערך רשימת JSON של שמות מחלקות
SET_FAMILY_FIELD = "departments_involved"
DELIVERABLE_LANGS = ("he", "en", "both")
# השדות היחידים ש---set משנה (הכללים המשותפים 1.7): תשובות המשתמש על הארגון שרכיבים רושמים אחרי ההקמה, הגדרות
# החיבורים, לוגו שנוסף מאוחר יותר, ושדות שההקמה מתקנת בעצמה לבקשת המשתמש בלי לשנות את גזירת הרגולטורים (מספר
# הרישום, החותם). כל שדה אחר: סירוב. שינוי שמשפיע על הגזירה או על זהות הארגון עובר בעדכון פרופיל, מקובץ תשובות.
SET_ALLOWED = ("organization_name_en", "registration_number",
               "branding.signatories", "branding.policy_approver", "branding.lawyer_name", "branding.lawyer_role",
               "branding.lawyer_name_en", "branding.lawyer_role_en", "branding.logo_path", "branding.logo_status", "branding.logo_added_at",
               "branding.website", "branding.theme", "deliverable_language", "deliverable_language_basis")
SET_ALLOWED_PREFIXES = (SET_FAMILY_FIELD, "connections")
# שפת הממשק: הערכים בפרופיל (רשימות, רגולטורים, בסיס) נשמרים בה, ולכן שינוי שלה הוא עדכון פרופיל (update_profile),
# ולא החלפת שדה
SET_REBUILD = ("display_language",)
# connections אינו מחזיק מחבר פסיקה: פסיקה לפי כלל 1.1, מחבר סגור שפעיל בשיחה
SET_REFUSED = ("connections.case_law_connector",)
LOGO_STATUSES = ("attached", "later", "none")
# נתיבי תיקיות מקומיים בפרופיל: נשארים בקובץ שבתיקייה, ואינם חלק מהעותק שב-Areo (הכללים המשותפים 1.7)
LOCAL_PATH_FIELDS = ("connections.shared_output_folder", "connections.folders", "connections.doc_access.baseUrl",
                     "branding.logo_path")


def set_allowed(key):
    if key in SET_REBUILD:
        return True
    if key in SET_REFUSED:
        return False
    return key in SET_ALLOWED or any(key == p or key.startswith(p + ".") for p in SET_ALLOWED_PREFIXES)


# רשימת השדות המותרת בעותק שנשלח ל-Areo: מידע ציבורי על הארגון בלבד. כל שדה שאינו כאן נשאר מקומי, כולל שדה חדש שיתווסף
# לפרופיל המקומי: שדה נכנס לעותק רק בהוספה מפורשת לרשימה הזו, ולכן אי אפשר ש"סתם" יעבור לשרת.
PUBLIC_FIELDS = ("schema_version", "core_version", "profile_id", "version", "status", "checked_at",
                 "organization_name", "organization_name_en", "registration_number", "organization_id",
                 "incorporation_country", "incorporation_state", "incorporation_country_name",
                 "organization_type", "organization_type_basis", "public_market", "sector",
                 "material_operating_jurisdictions", "regulatory_footprint_primary", "regulatory_footprint_secondary",
                 "branding.website", "branding.theme", "display_language", "deliverable_language",
                 "generated_at", "last_updated")


def public_profile(prof):
    """הפרופיל הציבורי: רק השדות שב-PUBLIC_FIELDS, בעותק עמוק. שדה לא מוכר, תשובה פנימית, שם חותם, נתיב, מחלקה
    וערך שנגזר מהסכם אינם נכללים לעולם."""
    import copy
    out = {}
    for dotted in PUBLIC_FIELDS:
        parts = dotted.split(".")
        src, dst = prof, out
        for p in parts[:-1]:
            src = src.get(p) if isinstance(src, dict) else None
            if not isinstance(src, dict):
                break
            dst = dst.setdefault(p, {})
        else:
            if isinstance(src, dict) and parts[-1] in src:
                dst[parts[-1]] = copy.deepcopy(src[parts[-1]])
    return out


def areo_copy(path, to=None):
    """העותק של הפרופיל שנשלח ל-Areo: הפרופיל הציבורי בלבד (PUBLIC_FIELDS, רשימה חיובית). המסלול המקומי של הלקוח
    מכיל גם תצורה, מחלקות, חותמים ונתיבים, והם לעולם אינם בעותק. מודפס כ-JSON, או נכתב ל---to. הקובץ שבתיקייה אינו משתנה."""
    if not os.path.isfile(path):
        print("אין פרופיל בנתיב %s" % path)
        return 2
    prof = public_profile(json.load(io.open(path, encoding="utf-8")))
    if to:
        write_json(to, prof)
        print(("The copy for Areo was written: %s" if prof.get("display_language") == "en" else "העותק ל-Areo נכתב: %s") % to)
    else:
        print(json.dumps(prof, ensure_ascii=False, indent=2))
    return 0


# מילים שמעידות שנכתב תפקיד ולא אדם (כמו ב-lib/playbook/ingest_approval.py): כל אישור נרשם בשם אדם מלא
ROLE_WORDS = ('היועץ', 'היועצת', 'המשפטי', 'המשפטית', 'מנכ"ל', 'מנכ״ל', 'סמנכ"ל', 'הלשכה', 'המחלקה',
              'general counsel', 'legal counsel', 'ceo')


def is_person_name(name):
    n = " ".join(str(name or "").split())
    return len(n.split()) >= 2 and not any(w.lower() in n.lower() for w in ROLE_WORDS)


def check_set_value(key, val):
    """(ערך, None) או (None, הודעת שגיאה) לשדות שרכיבים אחרים רושמים. שדה אחר עובר כמו שהוא."""
    if key == "branding.policy_approver":
        # מי שמאשר את המדיניות (הפלייבוקים): נשאל בשלב הפלייבוק, ונשמר רק בפרופיל שבתיקייה, לא ב-Areo
        if val is None:
            return None, None
        if not isinstance(val, dict) or not is_person_name(val.get("name")):
            return None, 'branding.policy_approver: {"name": "<שם פרטי ומשפחה>", "role": "<תפקיד>"}, שם אדם מלא'
        return {"name": " ".join(val["name"].split()), "role": " ".join(str(val.get("role") or "").split()) or None}, None
    if key == "branding.website":
        site = normalize_website(val)
        if val not in (None, "") and not site:
            return None, "branding.website: כתובת אתר, למשל example.co.il או https://www.example.com"
        return site, None
    if key == "branding.theme":
        # רכיב אחר רושם רק את תשובת המשתמש: {"choice": "yes|no", "asked_at": "YYYY-MM-DD"}. הצבעים נגזרים
        # ב---derive-theme בלבד, כדי שיהיו בדוקי ניגודיות
        if not isinstance(val, dict) or THEME_CHOICES.get(str(val.get("choice") or "")) is None:
            return None, 'branding.theme: {"choice": "yes|no", "asked_at": "YYYY-MM-DD"}'
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(val.get("asked_at") or "")):
            return None, "branding.theme.asked_at בפורמט YYYY-MM-DD"
        return {"choice": THEME_CHOICES[str(val["choice"])], "asked_at": val["asked_at"]}, None
    if key == "branding.logo_status":
        if val not in LOGO_STATUSES:
            return None, "branding.logo_status מקבל רק attached, later או none"
        return val, None
    if key == "branding.logo_added_at":
        if val is not None and not re.match(r"^\d{4}-\d{2}-\d{2}$", str(val)):
            return None, "branding.logo_added_at בפורמט YYYY-MM-DD"
        return val, None
    if key == "display_language":
        if val not in ("he", "en"):
            return None, "display_language מקבל רק he או en (display_language accepts only he or en)"
        return val, None
    if key == "deliverable_language":
        if val not in DELIVERABLE_LANGS:
            return None, "deliverable_language מקבל רק he, en או both"
        return val, None
    if key == "deliverable_language_basis":
        if not isinstance(val, str) or not val:
            return None, "deliverable_language_basis הוא מחרוזת לא ריקה (למשל user_answer YYYY-MM-DD corpus=he)"
        return val, None
    if key == SET_FAMILY_FIELD:
        if not isinstance(val, dict) or not val:
            return None, "departments_involved כולו הוא אובייקט JSON: {\"<משפחה>\": [\"<מחלקה>\"], \"asked_at\": \"YYYY-MM-DD\"}"
        out = {}
        for k, v in val.items():
            v = v.strip() or None if isinstance(v, str) else v
            ok, err = check_set_value("%s.%s" % (SET_FAMILY_FIELD, str(k).strip()), v)
            if err:
                return None, err
            out[str(k).strip()] = ok
        return out, None
    if key.startswith(SET_FAMILY_FIELD + "."):
        sub = key[len(SET_FAMILY_FIELD) + 1:]
        if not sub or "." in sub:
            return None, "departments_involved.<משפחת ההסכמים>: שם משפחה אחד, בלי נקודה"
        if sub == "asked_at":
            if not isinstance(val, str) or not re.match(r"^\d{4}-\d{2}-\d{2}$", val):
                return None, "departments_involved.asked_at בפורמט YYYY-MM-DD"
            return val, None
        if not isinstance(val, list) or not val or \
                not all(isinstance(x, str) and x.strip() for x in val):
            return None, ("departments_involved.%s הוא רשימת JSON של שמות מחלקות, למשל "
                          "'[\"משפטית\", \"כספים\"]'" % sub)
        names = []
        for x in val:
            if x.strip() not in names:
                names.append(x.strip())   # כלשונו, בלי תרגום ובלי נרמול
        return names, None
    return val, None


def set_fields(path, assignments, preview=False):
    """--set שדה=ערך, אחד או יותר, על פרופיל-לקוח.json קיים: משנה רק את השדה (נתיב בנקודות, למשל
    branding.lawyer_name_en), ושומר את profile_id, התאריכים וכל השאר. last_updated מתעדכן. ערך JSON (null, רשימה)
    נקרא כ-JSON, וכל ערך אחר כמחרוזת, כלשונו. registration_number מעדכן גם את organization_id המנורמל."""
    if not os.path.exists(path):
        print("אין פרופיל בנתיב %s. --set מעדכן פרופיל קיים; פרופיל חדש נבנה מ---answers" % path)
        return 2
    prof = json.load(io.open(path, encoding="utf-8"))
    changes = []
    new_lang = None
    for item in assignments:
        key, sep, raw = item.partition("=")
        key = key.strip()
        if not sep or not key:
            print("--set %r: נדרש שדה=ערך" % item)
            return 2
        try:
            val = json.loads(raw)
        except ValueError:
            val = raw
        if isinstance(val, str):
            val = val.strip() or None
        parts = key.split(".")
        if parts[0] in SET_PROTECTED:
            print("השדה %s אינו משתנה ב---set (זהות הפרופיל ותאריך היצירה)" % parts[0])
            return 2
        if not set_allowed(key):
            print("השדה %s אינו מתעדכן ב---set. --set משנה רק את תשובות המשתמש על הארגון שהכללים המשותפים (1.7) "
                  "מתירים: %s, departments_involved.<משפחה>, connections.<הגדרה>. שינוי שמשפיע על גזירת "
                  "הרגולטורים או על זהות הארגון עובר בעדכון פרופיל, מקובץ תשובות"
                  % (key, ", ".join(SET_ALLOWED)))
            return 2
        family = parts[0] == SET_FAMILY_FIELD and len(parts) == 2
        val, err = check_set_value(key, val)
        if err:
            print(err)
            return 2
        if key in SET_REBUILD:
            new_lang = val
            continue
        if family and prof.get(SET_FAMILY_FIELD) is None:
            prof[SET_FAMILY_FIELD] = {}   # המשפחה הראשונה שנשאלה
        node = prof
        for p in parts[:-1]:
            if not isinstance(node.get(p), dict):
                print("אין בפרופיל שדה %s" % key)
                return 2
            node = node[p]
        if parts[-1] not in node and key not in SET_NEW_OK and not family:
            print("אין בפרופיל שדה %s. --set משנה שדה קיים; שדה חדש נכנס בבנייה מ---answers" % key)
            return 2
        if key == SET_FAMILY_FIELD and isinstance(node.get(key), dict):
            val = dict(node[key], **val)   # משפחה חדשה אינה מוחקת את הקודמות
        if key == "branding.theme" and isinstance(node.get("theme"), dict) and val["choice"] == "yes":
            val = dict(node["theme"], **val)   # תשובה חוזרת "כן" אינה מוחקת צבעים שכבר נגזרו
        if key == "branding.signatories":
            # אותה צורה כמו בבנייה: [{name, role, name_en, role_en}], בלי תואר
            val = signatories_of({"signatories": val} if isinstance(val, (list, dict)) else {"signer": val or ""})
        changes.append((key, node.get(parts[-1]), val))
        node[parts[-1]] = val
        if key == "registration_number":
            prof["organization_id"] = re.sub(r"[\s\-.]", "", val or "") or None
    t = T[new_lang or (prof.get("display_language") if prof.get("display_language") in T else "he")]
    for key, old, new in changes:
        print(set_line(t, key, old, new))
    if new_lang and new_lang != prof.get("display_language"):
        print(set_line(t, "display_language", prof.get("display_language"), new_lang))
        if not preview and changes:
            prof["last_updated"] = date.today().isoformat()
            write_json(path, prof)
        if preview and changes:
            print(t["pv"])
            return 0
        return update_profile(path, {"display_language": new_lang}, preview=preview)[0]
    if preview:
        print(t["pv"])
        return 0
    prof["last_updated"] = date.today().isoformat()
    write_json(path, prof)
    print(t["upd"])
    return 0


def set_line(t, key, old, new):
    """שורה קריאה לשינוי בשדה, בשפת הפרופיל: שם השדה במילים, והערכים בלי קודים."""
    def show(v):
        if v in (None, "", [], {}):
            return t["none"]
        if isinstance(v, str) and v in t["langs"]:
            return t["langs"][v]
        if isinstance(v, list):
            return ", ".join(x.get("name") or "" if isinstance(x, dict) else str(x) for x in v)
        if isinstance(v, dict):
            return ", ".join("%s" % (", ".join(x) if isinstance(x, list) else x) for k, x in v.items()
                             if k not in ("asked_at",) and not isinstance(x, dict)) or t["none"]
        return str(v)
    name = t["fields"].get(key) or t["fields"].get(key.split(".")[0]) or key
    if old in (None, "", [], {}):
        return t["set_new"] % (name, show(new))
    return t["set_line"] % (name, show(new), show(old))


# ---- מיתוג סביבות העבודה בצבעי הלקוח (branding.theme) ----
# הלקוח מאשר בטופס ההקמה (או בשאלה אחת ברכיב הראשון שמפיק סביבת עבודה), והצבעים נגזרים כאן בלבד: מצבעים שמסר,
# מהלוגו שבפרופיל או מאתר החברה. התוצאה היא אסימוני עיצוב לתצוגת יום ולתצוגת לילה, בניגודיות של 4.5:1 לפחות
# לטקסט, וכל תבנית HTML מחילה אותם על צבעי המותג בלבד (meta.branding.theme). סימן Areo נשאר.
THEME_CHOICES = {"כן": "yes", "yes": "yes", "Yes": "yes", "לא": "no", "no": "no", "No": "no"}
LIGHT_BG = (255, 255, 255)
DARK_BG = (0x15, 0x19, 0x23)
SITE_MAX_BYTES = 2 * 1024 * 1024
SITE_MAX_SHEETS = 4
HEX_RE = re.compile(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")
RGB_RE = re.compile(r"rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*(?:,\s*([\d.]+)\s*)?\)")
THEME_TEXT = {
    "he": {"line": "צבעי המותג: ראשי %s, משני %s (מקור: %s)",
           "src": {"user": "הצבעים שמסרתם", "logo": "הלוגו", "website": "אתר החברה"},
           "none": "לא נמצאו צבעי מותג בלוגו או באתר. אפשר למסור אותם (למשל #1B4F9C, #F2A900), או להמשיך בעיצוב "
                   "הרגיל של Areo.",
           "consent": "הלקוח לא אישר מיתוג (branding.theme.choice אינו yes). שאלו אותו קודם, ורשמו את התשובה ב---set."},
    "en": {"line": "Brand colours: primary %s, secondary %s (source: %s)",
           "src": {"user": "the colours you gave", "logo": "the logo", "website": "the company website"},
           "none": "No brand colours were found in the logo or on the website. You can give them (for example "
                   "#1B4F9C, #F2A900), or continue with the standard Areo design.",
           "consent": "The client has not approved branding (branding.theme.choice is not yes). Ask first, and "
                      "record the answer with --set."},
}


def normalize_website(v):
    """כתובת אתר כפי שהוקלדה ("example.co.il", "www.x.com/he") לכתובת https מלאה, או None."""
    v = v.strip() if isinstance(v, str) else ""
    if not v or v == "-":
        return None
    if not re.match(r"^https?://", v, re.I):
        v = "https://" + v
    host = re.sub(r"^https?://", "", v, flags=re.I).split("/")[0].split(":")[0].lower()
    if not re.match(r"^[a-z0-9\-]+(\.[a-z0-9\-]+)+$", host):
        return None
    return v


def _hex(c):
    return "#%02X%02X%02X" % tuple(max(0, min(255, int(round(x)))) for x in c)


def _rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _lum(c):
    def ch(x):
        x = x / 255.0
        return x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(x) for x in c)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _hls(c):
    import colorsys
    return colorsys.rgb_to_hls(*(x / 255.0 for x in c))


def _from_hls(h, l, s):
    import colorsys
    return tuple(x * 255 for x in colorsys.hls_to_rgb(h, max(0.0, min(1.0, l)), s))


def _fit(c, bg, ratio, darker):
    """אותו גוון ורוויה, בהירות שמשתנה בצעדים עד ניגודיות ratio מול הרקע."""
    h, l, s = _hls(c)
    step = -0.02 if darker else 0.02
    for _ in range(60):
        cand = _from_hls(h, l, s)
        if _contrast(cand, bg) >= ratio:
            return cand
        l += step
        if l <= 0 or l >= 1:
            break
    return (0, 0, 0) if darker else (255, 255, 255)


def _mix(a, b, t):
    """t מתוך b: 0.9 הוא 90% רקע ו-10% צבע."""
    return tuple(x * (1 - t) + y * t for x, y in zip(a, b))


def _best_ink(c, inks):
    return max(inks, key=lambda k: _contrast(c, k))


def _count(counter, rgb, w=1):
    key = tuple(int(x) // 16 for x in rgb)          # דלי של 16 גוונים לערוץ: אותו צבע בהבדלי עיבוד קטנים
    tot, sums = counter.get(key, (0, (0, 0, 0)))
    counter[key] = (tot + w, tuple(s + x * w for s, x in zip(sums, rgb)))


def colors_from_css(text, counter, weight=1):
    """צבעים מטקסט HTML, CSS או SVG: theme-color, משתני מותג (brand, primary, accent), ושאר הצבעים לפי שכיחות."""
    for m in re.finditer(r"<meta[^>]+name=[\"']theme-color[\"'][^>]*>", text, re.I):
        mm = HEX_RE.search(m.group(0))
        if mm:
            _count(counter, _rgb(mm.group(0)), 40 * weight)
    for m in re.finditer(r"--[\w-]*(?:brand|primary|accent|main|theme)[\w-]*\s*:\s*([^;}]+)", text, re.I):
        mm = HEX_RE.search(m.group(1))
        if mm:
            _count(counter, _rgb(mm.group(0)), 15 * weight)
    for m in HEX_RE.finditer(text):
        _count(counter, _rgb(m.group(0)), weight)
    for m in RGB_RE.finditer(text):
        if m.group(4) is None or float(m.group(4)) >= 0.5:
            _count(counter, tuple(min(255, int(m.group(i))) for i in (1, 2, 3)), weight)


def _png_pixels(raw, limit=40000):
    """פענוח PNG בספרייה הסטנדרטית: 8 ביט, RGB, RGBA או פלטה, בלי שזירה. אחרת None."""
    if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
        return None
    pos, idat, plte, trns, ihdr = 8, [], None, None, None
    while pos + 8 <= len(raw):
        n = int.from_bytes(raw[pos:pos + 4], "big")
        typ, data = raw[pos + 4:pos + 8], raw[pos + 8:pos + 8 + n]
        pos += 12 + n
        if typ == b"IHDR":
            ihdr = data
        elif typ == b"PLTE":
            plte = data
        elif typ == b"tRNS":
            trns = data
        elif typ == b"IDAT":
            idat.append(data)
        elif typ == b"IEND":
            break
    if not ihdr:
        return None
    w, h = int.from_bytes(ihdr[0:4], "big"), int.from_bytes(ihdr[4:8], "big")
    depth, ctype, interlace = ihdr[8], ihdr[9], ihdr[12]
    bpp = {2: 3, 6: 4, 3: 1}.get(ctype)
    if depth != 8 or interlace or not bpp or (ctype == 3 and not plte):
        return None
    try:
        data = zlib.decompress(b"".join(idat))
    except zlib.error:
        return None
    stride, prev, out, i = w * bpp, bytearray(w * bpp), [], 0
    every = max(1, (w * h) // limit)
    for y in range(h):
        if i >= len(data):
            break
        f, line = data[i], bytearray(data[i + 1:i + 1 + stride])
        i += 1 + stride
        for x in range(len(line)):
            a = line[x - bpp] if x >= bpp else 0
            b = prev[x]
            c = prev[x - bpp] if x >= bpp else 0
            if f == 1:
                line[x] = (line[x] + a) & 255
            elif f == 2:
                line[x] = (line[x] + b) & 255
            elif f == 3:
                line[x] = (line[x] + ((a + b) >> 1)) & 255
            elif f == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        prev = line
        for px in range(w):
            if (y * w + px) % every:
                continue
            o = px * bpp
            if o + bpp > len(line):
                break
            if ctype == 3:
                k = line[o]
                if k * 3 + 3 > len(plte) or (trns and k < len(trns) and trns[k] < 128):
                    continue
                out.append(tuple(plte[k * 3:k * 3 + 3]))
            elif ctype == 6:
                if line[o + 3] >= 128:
                    out.append(tuple(line[o:o + 3]))
            else:
                out.append(tuple(line[o:o + 3]))
    return out


def colors_from_logo(path, counter):
    """צבעי הלוגו: SVG מהטקסט, PNG בספרייה הסטנדרטית, ושאר הפורמטים ב-Pillow כשהיא מותקנת."""
    try:
        raw = io.open(path, "rb").read()
    except OSError:
        return False
    if path.lower().endswith(".svg") or b"<svg" in raw[:2048].lower():
        colors_from_css(raw.decode("utf-8", "replace"), counter)
        return True
    pixels = _png_pixels(raw)
    if pixels is None:
        try:
            from PIL import Image
            im = Image.open(io.BytesIO(raw)).convert("RGBA")
            im.thumbnail((160, 160))
            pixels = [px[:3] for px in im.getdata() if px[3] >= 128]
        except Exception:  # noqa: BLE001  אין Pillow, או קובץ שאינו תמונה
            return False
    for px in pixels:
        _count(counter, px)
    return True


def fetch_site(url):
    """דף הבית של אתר החברה, ועד ארבעה גיליונות סגנון מאותו אתר. GET בלבד, בלי עוגיות ובלי פרמטרים."""
    import urllib.request
    from urllib.parse import urljoin, urlsplit
    site = (urlsplit(url).hostname or "").lower()
    base = site[4:] if site.startswith("www.") else site

    def same_site(u):
        h = (urlsplit(u).hostname or "").lower()
        return urlsplit(u).scheme in ("http", "https") and (h == base or h.endswith("." + base))

    def get(u):
        u = u.split("#")[0].split("?")[0]
        if not same_site(u):
            return ""
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 (compatible; AreoBrand/1.0)"})
        with urllib.request.urlopen(req, timeout=12) as r:
            if not same_site(r.geturl()):
                return ""      # הפניה לאתר אחר: לא נקרא
            return r.read(SITE_MAX_BYTES).decode("utf-8", "replace")
    page = get(url)
    texts = [page]
    for tag in re.findall(r"<link[^>]+rel=[\"']?stylesheet[\"']?[^>]*>", page, re.I)[:SITE_MAX_SHEETS]:
        m = re.search(r"href=[\"']([^\"']+)[\"']", tag)
        if m:
            try:
                texts.append(get(urljoin(url, m.group(1))))
            except Exception:  # noqa: BLE001  גיליון שלא נטען אינו עוצר את הגזירה
                pass
    return texts


def pick_palette(counter):
    """הצבע הראשי: הצבע הרווי השכיח. המשני: הבא אחריו בגוון שונה ב-25 מעלות לפחות. מותג חד-גוני (שחור או
    אפור כהה בלבד): הצבע הכהה השכיח. בלי צבע כזה: (None, None)."""
    items = []
    for tot, sums in counter.values():
        c = tuple(x / tot for x in sums)
        h, l, s = _hls(c)
        items.append((tot, c, h, l, s))
    items.sort(key=lambda x: -x[0])
    chroma = [x for x in items if x[4] >= 0.22 and 0.12 <= x[3] <= 0.9]
    if chroma:
        primary = chroma[0]
        accent = next((x for x in chroma[1:]
                       if min(abs(x[2] - primary[2]), 1 - abs(x[2] - primary[2])) >= 25 / 360.0
                       and x[0] >= primary[0] * 0.04), None)
        return primary[1], (accent[1] if accent else None)
    dark = [x for x in items if x[3] < 0.45]
    return (dark[0][1], None) if dark else (None, None)


def theme_tokens(primary, accent=None):
    """אסימוני העיצוב לשתי התצוגות. הצבע הראשי משמש לטקסט, לקישורים ולכפתורים, ולכן 4.5:1 מול הרקע; המשני
    משמש לגרפים ולהדגשות, 3:1."""
    sec = accent or primary
    pl = _fit(primary, LIGHT_BG, 4.5, darker=True)
    sl = _fit(sec, LIGHT_BG, 3.0, darker=True)
    pd = _fit(primary, DARK_BG, 4.5, darker=False)
    sd = _fit(sec, DARK_BG, 3.0, darker=False)
    return {"primary_light": _hex(pl), "secondary_light": _hex(sl), "soft_light": _hex(_mix(pl, LIGHT_BG, 0.9)),
            "on_light": _hex(_best_ink(pl, ((255, 255, 255), (0x10, 0x22, 0x1C)))),
            "primary_dark": _hex(pd), "secondary_dark": _hex(sd), "soft_dark": _hex(_mix(pd, DARK_BG, 0.86)),
            "on_dark": _hex(_best_ink(pd, ((0x0E, 0x10, 0x16), (255, 255, 255))))}


def derive_theme(path, colors=None, site_files=(), fetch=False, preview=False):
    """branding.theme.tokens מהצבעים שנמסרו, מהלוגו שבפרופיל או מאתר החברה, בסדר הזה. רק בהסכמה (choice=yes)."""
    if not os.path.isfile(path):
        print("אין פרופיל בנתיב %s" % path)
        return 2
    prof = json.load(io.open(path, encoding="utf-8"))
    tt = THEME_TEXT["en" if prof.get("display_language") == "en" else "he"]
    b = prof.setdefault("branding", {})
    theme = b.get("theme") or {}
    if theme.get("choice") != "yes":
        print(tt["consent"])
        return 2
    primary = accent = source = None
    if colors:
        found = [_rgb(m.group(0)) for m in HEX_RE.finditer(colors)]
        if not found:
            print("--colors: צבע אחד או שניים בפורמט #RRGGBB")
            return 2
        primary, accent, source = found[0], (found[1] if len(found) > 1 else None), "user"
    if primary is None and b.get("logo_path"):
        logo = b["logo_path"]
        if not os.path.isabs(logo):
            # הנתיב בפרופיל יחסי לתיקייה שמחזיקה את Areo-נתונים, או לתיקיית הפרופיל עצמה
            here = os.path.dirname(os.path.abspath(path))
            cands = [os.path.join(os.path.dirname(here), logo), os.path.join(here, logo),
                     os.path.join(here, os.path.basename(logo))]
            logo = next((c for c in cands if os.path.isfile(c)), cands[0])
        counter = {}
        if colors_from_logo(logo, counter):
            primary, accent = pick_palette(counter)
            source = "logo" if primary is not None else None
    if primary is None and (site_files or (fetch and b.get("website"))):
        counter, texts = {}, []
        for f in site_files:
            texts.append(io.open(f, encoding="utf-8", errors="replace").read())
        if fetch and b.get("website") and not site_files:
            try:
                texts = fetch_site(b["website"])
            except Exception as exc:  # noqa: BLE001  אתר שאינו נגיש: אין גזירה מהאתר
                print("אתר החברה לא נקרא (%s)" % exc)
        for tx in texts:
            colors_from_css(tx, counter)
        primary, accent = pick_palette(counter)
        source = "website" if primary is not None else None
    if primary is None:
        print(tt["none"])
        return 3
    tokens = theme_tokens(primary, accent)
    new = dict(theme, source=source, primary=_hex(primary), accent=_hex(accent) if accent else None,
               tokens=tokens, derived_at=date.today().isoformat())
    print(tt["line"] % (new["primary"], new["accent"] or tokens["secondary_light"], tt["src"][source]))
    print(json.dumps(tokens, ensure_ascii=False))
    if preview:
        print("תצוגה מקדימה: הפרופיל לא נכתב")
        return 0
    b["theme"] = new
    prof["last_updated"] = date.today().isoformat()
    write_json(path, prof)
    print(("The profile was updated: %s" if prof.get("display_language") == "en" else "הפרופיל עודכן: %s") % path)
    return 0


REGISTRY = "ישויות.json"


def registry_entry(p, rel):
    return {"name": p["organization_name"],
            "registration_number": p.get("registration_number") or p.get("organization_id"),
            "incorporation_country": p.get("incorporation_country"), "profile_id": p.get("profile_id"),
            "profile_path": rel}


def load_setup(root, flat_path):
    """(registry, default_profile) של התקנה קיימת, להוספת ישות. בלי מרשם: מרשם חדש שבו הישות הקיימת ראשונה,
    כישות ברירת המחדל, בנתיב שבו היא יושבת. בלי הקמה קיימת: (None, None)."""
    reg_path = os.path.join(root, REGISTRY)
    if os.path.exists(reg_path):
        registry = json.load(io.open(reg_path, encoding="utf-8"))
        entries = registry.get("entities") or []
        default = next((e for e in entries if e.get("name") == registry.get("default_entity")), None) or \
            (entries[0] if entries else None)
        prof = None
        if default and default.get("profile_path"):
            dp = os.path.join(root, *default["profile_path"].split("/"))
            if os.path.exists(dp):
                prof = json.load(io.open(dp, encoding="utf-8"))
        return registry, prof
    if not os.path.exists(flat_path):
        return None, None
    prof = json.load(io.open(flat_path, encoding="utf-8"))
    today = date.today().isoformat()
    rel = os.path.relpath(os.path.abspath(flat_path), root).replace(os.sep, "/")
    return ({"schema_version": SCHEMA_VERSION, "default_entity": prof["organization_name"],
             "entities": [registry_entry(prof, rel)], "generated_at": today, "last_updated": today}, prof)


def profile_to_answers(p, for_update=False):
    """הפרופיל הקיים כקובץ תשובות. בירושה לישות אחרת (--inherit): השם, מספר הרישום, השם באנגלית, תיאור הפעילות,
    הלוגו והאתר אינם עוברים. בעדכון אותו פרופיל (for_update): עוברים כולם, כולל רגולטורים שהמשתמש הוסיף או הסיר."""
    b = p.get("branding") or {}
    pm = p.get("public_market") or {}
    sec = p.get("sector") or {}
    sigs = b.get("signatories") or ([{"name": b["lawyer_name"], "role": b.get("lawyer_role"),
                                      "name_en": b.get("lawyer_name_en"), "role_en": b.get("lawyer_role_en")}]
                                    if b.get("lawyer_name") else [])
    out = {"incorporation_country": p.get("incorporation_country_name") or p.get("incorporation_country") or "",
            "organization_type": p.get("organization_type") or "",
            "listed_in": list(pm.get("venues") or []), "dual_listed_in": list(pm.get("dual_listed_in") or []),
            "sectors": list(sec.get("all") or []), "financial_activity": list(sec.get("financial_activity") or []),
            "markets": list(p.get("material_operating_jurisdictions") or []),
            "display_language": p.get("display_language") or "he",
            "deliverable_language": p.get("deliverable_language") or p.get("display_language") or "he",
            "signatories": sigs,
            "shared_output_folder": (p.get("connections") or {}).get("shared_output_folder")}
    if for_update:
        out.update({
            "organization_name": p.get("organization_name") or "",
            "organization_name_en": p.get("organization_name_en") or "",
            "registration_number": p.get("registration_number") or p.get("organization_id") or "",
            "activity_description": sec.get("description") or "",
            "logo_path": b.get("logo_path") or "",
            "logo": {"attached": "אעלה עכשיו", "later": "אוסיף מאוחר יותר"}.get(b.get("logo_status"), "בלי לוגו"),
            "website": b.get("website") or "",
            "brand_theme": (b.get("theme") or {}).get("choice") or "",
            "user_declared_regulators": [r.get("regulator_name") for r in p.get("regulatory_footprint_primary") or []
                                         if r.get("applicability_status") == "UserDeclared"],
            "removed_regulators": list(p.get("removed_regulators") or []),
            "connections": p.get("connections"),
        })
    return out


# שדות שהבנייה אינה מייצרת ושנשמרים בעדכון כמו שהם: תשובות המשתמש שנרשמו אחרי ההקמה, וכל שדה עתידי
KEEP_ON_UPDATE = ("departments_involved", "deliverable_language", "deliverable_language_basis")


# העובדות שהגזירה נשענת עליהן. עדכון שאינו משנה אף אחת מהן (שפה, חותם, שם באנגלית) אינו משנה מעמד של רגולטור
FACT_KEYS = ("incorporation_country", "organization_type", "listed_in", "dual_listed_in", "sectors",
             "financial_activity", "markets")
STATUS_ORDER = {"Confirmed": 0, "Likely": 1, "Potential": 2, "UserDeclared": 3}


def facts_of(a):
    n = normalize_answers(a)
    out = {}
    for k in FACT_KEYS:
        v = n.get(k)
        if k == "incorporation_country":
            out[k] = parse_country(v) if v else (None, None)
        elif k == "markets":
            out[k] = sorted(str(market_code(x) or x).casefold() for x in v or [])
        elif isinstance(v, list):
            out[k] = sorted(str(x) for x in v)
        else:
            out[k] = str(v or "").strip()
    return out


def facts_only_added(of, nf):
    """True כשהעדכון רק הוסיף עובדות (שוק, ענף, עיסוק או מקום מסחר נוספים) או לא שינה אותן: מדינת ההתאגדות וצורתה
    זהות, וכל רשימה חדשה מכילה את הקודמת. עובדה שנוספה אינה יכולה להוריד מעמד של רגולטור קיים."""
    for k in FACT_KEYS:
        if isinstance(of[k], list):
            if not set(of[k]) <= set(nf[k]):
                return False
        elif of[k] != nf[k]:
            return False
    return True


def _canon_reg(name):
    n = str(name or "").strip()
    return REG_HE.get(n.casefold(), n)


def keep_statuses(old, out):
    """כשהעובדות לא השתנו: רגולטור שהיה בפרופיל אינו יורד במעמד ואינו נעלם. המעמד והבסיס הקודמים נשמרים (בשפה אחרת,
    הבסיס הוא "כמו בפרופיל הקודם"). רגולטור שהמשתמש הסיר נשאר מחוץ לרשימה, ורגולטור שהוסיף נשאר UserDeclared."""
    lang = out.get("display_language") if out.get("display_language") in T else "he"
    same_lang = old.get("display_language") == out.get("display_language")
    removed = {_canon_reg(n) for n in out.get("removed_regulators") or []}
    prim, sec = list(out.get("regulatory_footprint_primary") or []), list(out.get("regulatory_footprint_secondary") or [])
    idx = {_canon_reg(r["regulator_name"]): r for r in prim + sec}
    for r in (old.get("regulatory_footprint_primary") or []) + (old.get("regulatory_footprint_secondary") or []):
        st = r.get("applicability_status")
        c = _canon_reg(r.get("regulator_name"))
        if st not in STATUS_ORDER or st == "UserDeclared" or c in removed:
            continue
        basis = r.get("basis") if same_lang else T[lang]["kept"]
        n = idx.get(c)
        if n is None:
            entry = {"regulator_name": reg_label(c, lang), "applicability_status": st, "basis": basis}
            (prim if c in PRIMARY_DISPLAY else sec).append(entry)
            idx[c] = entry
        elif STATUS_ORDER[st] < STATUS_ORDER.get(n.get("applicability_status"), 9):
            n["applicability_status"], n["basis"] = st, basis
    rank = lambda r: (r["applicability_status"] == "UserDeclared",  # noqa: E731
                      PRIMARY_DISPLAY.index(_canon_reg(r["regulator_name"]))
                      if _canon_reg(r["regulator_name"]) in PRIMARY_DISPLAY else 99)
    out["regulatory_footprint_primary"] = sorted(prim, key=rank)
    out["regulatory_footprint_secondary"] = sec
    return out


def reg_changes(old, new):
    """שורות קריאות, בשפת הפרופיל החדש: רגולטור שמעמדו השתנה, שנוסף או שיורד מהרשימה."""
    lang = new.get("display_language") if new.get("display_language") in T else "he"
    t, lab = T[lang], STATUS_LABELS[lang]
    o = {_canon_reg(r["regulator_name"]): r["applicability_status"] for r in old.get("regulatory_footprint_primary") or []}
    n = {_canon_reg(r["regulator_name"]): r["applicability_status"] for r in new.get("regulatory_footprint_primary") or []}
    lines = []
    for c in list(o) + [c for c in n if c not in o]:
        name = reg_label(c, lang)
        if c in o and c in n and o[c] != n[c]:
            lines.append(t["chg"] % (name, lab.get(o[c], o[c]), lab.get(n[c], n[c])))
        elif c in n and c not in o:
            lines.append(t["chg_add"] % (name, lab.get(n[c], n[c])))
        elif c in o and c not in n:
            lines.append(t["chg_del"] % name)
    return lines


def merge_update(old, new, given, old_answers=None, new_answers=None):
    """פרופיל שנבנה מחדש מתשובות מעודכנות, על בסיס הפרופיל הקיים: אותו profile_id ותאריך יצירה, version עולה באחד,
    וכל שדה שנוסף אחרי ההקמה נשמר. given: מפתחות התשובות שהמשתמש שינה בעדכון הזה (שפת התוצר משתנה רק כשנמסרה)."""
    out = dict(new)
    for k in ("profile_id", "generated_at", "checked_at", "schema_version"):
        if old.get(k):
            out[k] = old[k]
    out["version"] = int(old.get("version") or 1) + 1
    out["last_updated"] = date.today().isoformat()
    for k in KEEP_ON_UPDATE:
        if k in old and not (k == "deliverable_language" and "deliverable_language" in given):
            out[k] = old[k]
    for k, v in old.items():           # שדה שהבנייה אינה מכירה: נשמר
        if k not in out:
            out[k] = v
    ob, nb = old.get("branding") or {}, dict(out.get("branding") or {})
    for k, v in ob.items():
        if k not in nb or (nb.get(k) in (None, [], "") and v not in (None, [], "")):
            nb[k] = v
    if isinstance(ob.get("theme"), dict) and (nb.get("theme") or {}).get("choice") == ob["theme"].get("choice"):
        nb["theme"] = ob["theme"]       # צבעים שכבר נגזרו נשמרים כשהתשובה לא השתנתה
    out["branding"] = nb
    if isinstance(old.get("connections"), dict):
        out["connections"] = dict(old["connections"], **{k: v for k, v in (out.get("connections") or {}).items()
                                                           if k not in old["connections"]})
    if old_answers is not None and new_answers is not None and facts_only_added(facts_of(old_answers),
                                                                                facts_of(new_answers)):
        keep_statuses(old, out)
    return out


def update_registry_entry(path, prof):
    """כשהפרופיל רשום ב-ישויות.json (בתיקייה שלו או מעליה), הרשומה שלו מתעדכנת: שם, מספר רישום ומדינה."""
    d = os.path.dirname(os.path.abspath(path))
    for _ in range(3):
        rp = os.path.join(d, REGISTRY)
        if os.path.exists(rp):
            reg = json.load(io.open(rp, encoding="utf-8"))
            hit = False
            for e in reg.get("entities") or []:
                if e.get("profile_id") == prof.get("profile_id"):
                    if reg.get("default_entity") == e.get("name"):
                        reg["default_entity"] = prof["organization_name"]
                    e.update({k: v for k, v in registry_entry(prof, e.get("profile_path")).items()
                              if k != "profile_path"})
                    hit = True
            if hit:
                reg["last_updated"] = date.today().isoformat()
                write_json(rp, reg)
            return
        d = os.path.dirname(d)


def update_profile(path, changes, preview=False):
    """עדכון פרופיל קיים מתשובות (חלקיות או מלאות), בלי לאבד דבר: התשובות הקיימות (profile_to_answers) והשינויים
    מתמזגים, הגזירה רצה מחדש, ו-merge_update שומר את הזהות ואת השדות שנוספו. מחזיר (קוד, פרופיל)."""
    if not os.path.isfile(path):
        print("אין פרופיל בנתיב %s. עדכון חל על פרופיל קיים; פרופיל חדש נבנה מ---answers" % path)
        return 2, None
    old = json.load(io.open(path, encoding="utf-8"))
    given = {k: v for k, v in (changes or {}).items() if k != "entities" and v not in (None, "", "-")}
    base = profile_to_answers(old, for_update=True)
    merged = dict(base, **given)
    a = normalize_answers(merged)
    new = merge_update(old, build(a), given, base, merged)
    t = T[new["display_language"]]
    changed = reg_changes(old, new)
    if preview:
        print_summary(new)
        if changed:
            print("")
            print(t["chg_title"])
            print("")
            for line in changed:
                print("- " + line)
        print("")
        print(t["pv"])
        return 0, new
    write_json(path, new)
    update_registry_entry(path, new)
    print(t["upd"])
    for line in changed:
        print("- " + line)
    for q in new["unresolved_questions"]:
        print(t["openq"] % q)
    return 0, new


def add_entities(root, registry, profiles, dry=False):
    """כותב פרופיל לכל ישות חדשה בתיקייה משלה, ומוסיף אותה למרשם. אינו נוגע בפרופיל קיים. מחזיר קוד יציאה.
    dry: רק בדיקת הכפילות (בתצוגה מקדימה), בלי כתיבה."""
    names = {(e.get("name") or "").strip().casefold() for e in registry.get("entities") or []}
    regs = {re.sub(r"[\s\-.]", "", e.get("registration_number") or "") for e in registry.get("entities") or []}
    regs.discard("")
    plan = []
    for p in profiles:
        rel = "ישויות/%s/פרופיל-לקוח.json" % entity_dirname(p["organization_name"])
        path = os.path.join(root, *rel.split("/"))
        if p["organization_name"].strip().casefold() in names or (p.get("organization_id") or "") in regs:
            print("הישות %s כבר רשומה ב-%s. הוספת ישות אינה מעדכנת ישות קיימת" % (p["organization_name"], REGISTRY))
            return 2
        if os.path.exists(path):
            print("כבר קיים פרופיל בנתיב %s. הוספת ישות אינה דורסת פרופיל" % path)
            return 2
        names.add(p["organization_name"].strip().casefold())
        if p.get("organization_id"):
            regs.add(p["organization_id"])
        plan.append((p, rel, path))
    if dry:
        return 0
    for p, rel, path in plan:
        write_json(path, p)
        report(p, path)
        registry.setdefault("entities", []).append(registry_entry(p, rel))
    registry["last_updated"] = date.today().isoformat()
    reg_path = os.path.join(root, REGISTRY)
    write_json(reg_path, registry)
    print("מרשם הישויות עודכן: %s (%d ישויות, ברירת מחדל: %s)"
          % (reg_path, len(registry["entities"]), registry.get("default_entity")))
    return 0


def main():
    # התקציר מודפס בעברית; בקונסול Windows שאינו UTF-8 הוא יוצא משובש בלי זה
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--answers", help="תשובות השאלון. נדרש בבנייה; לא עם --set")
    ap.add_argument("--out", help="נתיב פרופיל-לקוח.json. נדרש בשמירה, אחרי האישור, ובעדכון שדה (--set)")
    ap.add_argument("--preview", action="store_true",
                    help="תצוגה מקדימה לאישור: מדפיס את טבלאות התקציר ואינו כותב דבר")
    ap.add_argument("--set", action="append", metavar="FIELD=VALUE",
                    help="עדכון שדה בודד בפרופיל קיים (--out), בלי לבנות אותו מחדש: profile_id, התאריכים וכל "
                         "השאר נשמרים. אפשר כמה פעמים; נתיב בנקודות לשדה פנימי. רק השדות שהכללים המשותפים (1.7) "
                         "מתירים: organization_name_en, registration_number, branding.signatories, branding.lawyer_*, "
                         "branding.logo_path/logo_status/logo_added_at, branding.website, branding.theme, "
                         "deliverable_language (he|en|both), deliverable_language_basis, "
                         "departments_involved.<משפחה> (רשימת JSON), departments_involved.asked_at (YYYY-MM-DD), "
                         "connections.<הגדרה>. כל שדה אחר: סירוב, קוד 2")
    ap.add_argument("--update", action="store_true",
                    help="עדכון פרופיל קיים (--out) מקובץ תשובות חלקי או מלא (--answers): השינויים מתמזגים עם "
                         "התשובות הקיימות, הרגולטורים נגזרים מחדש, profile_id ותאריך היצירה נשמרים, version עולה "
                         "באחד, וכל שדה שנוסף אחרי ההקמה נשמר. עם --preview: מדפיס את התקציר ואינו כותב")
    ap.add_argument("--summary", action="store_true",
                    help="צפייה בפרופיל שב---out: מדפיס את התקציר (פרטים, רגולטורים ושאלות פתוחות) ואינו כותב דבר")
    ap.add_argument("--areo-copy", action="store_true",
                    help="העותק של הפרופיל שב---out שנשלח ל-Areo: בלי נתיבי התיקיות המקומיים "
                         "(connections.shared_output_folder, connections.folders, connections.doc_access.baseUrl, "
                         "branding.logo_path). מודפס כ-JSON, או נכתב ל---to. הפרופיל עצמו אינו משתנה")
    ap.add_argument("--to", help="עם --areo-copy: קובץ שאליו נכתב העותק, בתיקייה זמנית ולא ב-Areo-נתונים")
    ap.add_argument("--derive-theme", action="store_true",
                    help="גזירת צבעי המותג לפרופיל שב---out (branding.theme.tokens), רק כש-branding.theme.choice הוא "
                         "yes: מ---colors, מהלוגו שבפרופיל, או מאתר החברה (--fetch-site / --site-file)")
    ap.add_argument("--colors", help="עם --derive-theme: צבעי המותג שהמשתמש מסר, ראשי ומשני, למשל \"#1B4F9C,#F2A900\"")
    ap.add_argument("--fetch-site", action="store_true",
                    help="עם --derive-theme: קריאת דף הבית של branding.website וגיליונות הסגנון שלו מאותו אתר")
    ap.add_argument("--site-file", action="append", default=[],
                    help="עם --derive-theme: עותק של דף הבית או של גיליון סגנון מאתר החברה, כשאין גישה ישירה")
    ap.add_argument("--add-entity", action="store_true",
                    help="הוספת ישות להתקנה קיימת: פרופיל חדש ב-ישויות/<שם>/ ורישום ב-ישויות.json, בלי לגעת בפרופיל "
                         "הקיים. --out הוא פרופיל-לקוח.json שבשורש Areo-נתונים")
    ap.add_argument("--inherit", action="store_true",
                    help="עם --add-entity: שדה שחסר בתשובות נורש מהישות הקיימת (כמו הקיימת)")
    args = ap.parse_args()
    if args.inherit and not args.add_entity:
        ap.error("--inherit רק עם --add-entity")
    if args.summary:
        if not args.out or args.answers or args.set or args.update:
            ap.error("--summary מציג את הפרופיל שב---out בלבד")
        if not os.path.isfile(args.out):
            print("אין פרופיל בנתיב %s" % args.out)
            sys.exit(2)
        print_summary(json.load(io.open(args.out, encoding="utf-8")))
        sys.exit(0)
    if args.to and not args.areo_copy:
        ap.error("--to רק עם --areo-copy")
    if args.areo_copy:
        if args.answers or args.set or args.derive_theme or args.add_entity or not args.out:
            ap.error("--areo-copy פועל על הפרופיל שב---out בלבד")
        sys.exit(areo_copy(args.out, args.to))
    if args.derive_theme:
        if args.answers or args.set or not args.out:
            ap.error("--derive-theme פועל על הפרופיל שב---out, בלי --answers ובלי --set")
        sys.exit(derive_theme(args.out, colors=args.colors, site_files=args.site_file, fetch=args.fetch_site,
                              preview=args.preview))
    if args.colors or args.fetch_site or args.site_file:
        ap.error("--colors, --fetch-site ו---site-file רק עם --derive-theme")
    if args.set:
        if args.answers or not args.out or args.update:
            ap.error("--set מעדכן את הפרופיל שב---out, בלי --answers ובלי --update")
        sys.exit(set_fields(args.out, args.set, preview=args.preview))
    if args.update:
        if not args.answers or not args.out or args.add_entity:
            ap.error("--update דורש --answers (השינויים) ו---out (הפרופיל הקיים), בלי --add-entity")
        sys.exit(update_profile(args.out, json.load(io.open(args.answers, encoding="utf-8")),
                                preview=args.preview)[0])
    if not args.answers:
        ap.error("נדרש --answers")
    if not args.preview and not args.out:
        ap.error("נדרש --out לשמירה, או --preview לתצוגה מקדימה")
    if args.add_entity and not args.out:
        ap.error("--add-entity דורש --out: פרופיל-לקוח.json שבשורש Areo-נתונים, גם בתצוגה מקדימה")

    raw = json.load(io.open(args.answers, encoding="utf-8"))
    base = {k: v for k, v in raw.items() if k != "entities"}
    registry = None
    if args.add_entity:
        root = os.path.dirname(os.path.abspath(args.out))
        registry, existing = load_setup(root, args.out)
        if registry is None:
            print("אין הקמה קיימת ב-%s. ישות ראשונה נבנית בהקמה רגילה, בלי --add-entity" % root)
            sys.exit(2)
        if args.inherit:
            if existing is None:
                print("לא נמצא הפרופיל של ישות ברירת המחדל, ולכן אין ממה לרשת. הריצו בלי --inherit, עם התשובות המלאות")
                sys.exit(2)
            inherited = profile_to_answers(existing)
            if not inherited.get("incorporation_country") and not base.get("incorporation_country"):
                print("לישות הקיימת אין מדינת התאגדות בפרופיל, ולכן היא אינה עוברת בירושה. שאלו את מדינת ההתאגדות "
                      "של הישות החדשה והוסיפו אותה לתשובות (incorporation_country)")
            if any(base.get(k) not in (None, "", "-", []) for k in ("signer", "signatory", "lawyer_name")):
                inherited.pop("signatories")   # חותם שנמסר לישות החדשה גובר על מורשי החתימה של הקיימת
            base = dict(inherited, **{k: v for k, v in base.items() if v not in (None, "", "-", [])})
    entities = raw.get("entities") or []
    if len(entities) < 2:
        if entities:
            base.update(entities[0])
        answers = [normalize_answers(base)]
    else:
        answers, prev = [], base
        for e in entities:
            if e.get("organization_name") and "organization_name_en" not in e:
                prev = {k: v for k, v in prev.items() if k != "organization_name_en"}   # שם אנגלי אינו עובר לישות אחרת
            prev = dict(prev, **e)
            answers.append(normalize_answers(prev))

    profiles = [build(a) for a in answers]

    if args.add_entity and add_entities(root, registry, profiles, dry=True):
        sys.exit(2)
    if args.preview and not args.add_entity and len(profiles) == 1 and args.out and os.path.isfile(args.out):
        sys.exit(update_profile(args.out, base if not entities else dict(base, **entities[0]), preview=True)[0])
    if args.preview:
        for p in profiles:
            if len(profiles) > 1:
                print("### %s" % p["organization_name"])
                print("")
            print_summary(p)
            print("")
        return

    if args.add_entity:
        sys.exit(add_entities(root, registry, profiles))

    if len(profiles) == 1:
        if os.path.isfile(args.out):
            # הרצה חוזרת של ההקמה על פרופיל קיים: עדכון במקום, לא פרופיל חדש
            print("קיים פרופיל ב-%s: הוא מתעדכן במקום, עם אותו profile_id" % args.out)
            sys.exit(update_profile(args.out, base if not entities else dict(base, **entities[0]))[0])
        write_json(args.out, profiles[0])
        report(profiles[0], args.out)
        return

    root = os.path.dirname(os.path.abspath(args.out))
    registry = {"schema_version": SCHEMA_VERSION, "default_entity": profiles[0]["organization_name"],
                "entities": [], "generated_at": profiles[0]["generated_at"],
                "last_updated": profiles[0]["generated_at"]}
    for i, p in enumerate(profiles):
        rel = "ישויות/%s/פרופיל-לקוח.json" % entity_dirname(p["organization_name"])
        path = os.path.join(root, *rel.split("/"))
        if os.path.isfile(path):
            # הרצה חוזרת: הפרופיל הקיים של הישות מתעדכן במקום
            old = json.load(io.open(path, encoding="utf-8"))
            p = merge_update(old, p, answers[i], profile_to_answers(old, for_update=True), answers[i])
        write_json(path, p)
        report(p, path)
        registry["entities"].append({"name": p["organization_name"],
                                     "registration_number": p.get("registration_number") or p.get("organization_id"),
                                     "incorporation_country": p["incorporation_country"],
                                     "profile_id": p["profile_id"], "profile_path": rel})
    reg_path = os.path.join(root, "ישויות.json")
    write_json(reg_path, registry)
    print("מרשם הישויות נשמר: %s (%d ישויות, ברירת מחדל: %s)"
          % (reg_path, len(profiles), registry["default_entity"]))


if __name__ == "__main__":
    main()
