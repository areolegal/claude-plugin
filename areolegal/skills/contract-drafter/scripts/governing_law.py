# -*- coding: utf-8 -*-
"""הדין החל של ההסכם כקוד אחיד, ושמו בעברית ובאנגלית.

הקודים הם הקודים המשותפים לכל הרכיבים (scope_summary.governing_laws בפלייבוק, meta.governing_law בטיוטה):
ISO 3166, ובמדינה עם כמה שיטות משפט, קוד המדינה וקוד התחום: IL, GB-EAW, GB-SCT, US-NY, US-DE, DE, FR.
אין דין ברירת מחדל: ערך חסר או לא מוכר מחזיר None, והרכיב שואל או מסמן "טעון בדיקה משפטית".
"""
import re

# קוד: (שם המקום בעברית, שם המקום באנגלית, שמות נוספים לזיהוי)
LAWS = {
    "IL": ("ישראל", "Israel", ("israel", "israeli", "מדינת ישראל", "ישראלי", "הישראלי")),
    "GB-EAW": ("אנגליה ווילס", "England and Wales", ("england", "england and wales", "english", "english law",
                                                    "welsh", "wales", "אנגליה", "אנגלי", "האנגלי", "ווילס")),
    "GB-SCT": ("סקוטלנד", "Scotland", ("scotland", "scottish", "scots", "סקוטלנד", "סקוטי", "הסקוטי")),
    "GB-NIR": ("צפון אירלנד", "Northern Ireland", ("northern ireland", "צפון אירלנד")),
    "GB": ("הממלכה המאוחדת", "the United Kingdom", ("united kingdom", "the united kingdom", "uk", "u.k.", "british",
                                                  "הממלכה המאוחדת", "בריטניה", "בריטי", "הבריטי")),
    "IE": ("אירלנד", "Ireland", ("ireland", "irish", "republic of ireland", "אירלנד", "אירי", "האירי")),
    "US": ("ארצות הברית", "the United States", ("united states", "the united states", "usa", "u.s.", "us",
                                              "american", "ארצות הברית", "ארה\"ב", "ארה״ב", "אמריקאי", "אמריקני",
                                              "האמריקאי", "האמריקני")),
    "US-NY": ("מדינת ניו יורק", "the State of New York", ("new york", "state of new york", "ניו יורק")),
    "US-DE": ("מדינת דלאוור", "the State of Delaware", ("delaware", "state of delaware", "דלאוור", "דלאוואר")),
    "US-CA": ("מדינת קליפורניה", "the State of California", ("california", "californian", "state of california",
                                                            "קליפורניה")),
    "US-TX": ("מדינת טקסס", "the State of Texas", ("texas", "texan", "state of texas", "טקסס")),
    "US-NJ": ("מדינת ניו ג'רזי", "the State of New Jersey", ("new jersey", "state of new jersey", "ניו ג'רזי",
                                                            "ניו ג׳רזי")),
    "US-MA": ("מדינת מסצ'וסטס", "the Commonwealth of Massachusetts", ("massachusetts", "commonwealth of massachusetts",
                                                                     "מסצ'וסטס")),
    "US-FL": ("מדינת פלורידה", "the State of Florida", ("florida", "state of florida", "פלורידה")),
    "US-WA": ("מדינת וושינגטון", "the State of Washington", ("washington", "state of washington")),
    "US-IL": ("מדינת אילינוי", "the State of Illinois", ("illinois", "state of illinois", "אילינוי")),
    "CA": ("קנדה", "Canada", ("canada", "canadian", "קנדה", "קנדי", "הקנדי")),
    "CA-ON": ("אונטריו", "the Province of Ontario", ("ontario", "province of ontario", "אונטריו")),
    "DE": ("גרמניה", "Germany", ("germany", "german", "federal republic of germany", "גרמניה", "גרמני", "הגרמני")),
    "FR": ("צרפת", "France", ("france", "french", "צרפת", "צרפתי", "הצרפתי")),
    "CH": ("שווייץ", "Switzerland", ("switzerland", "swiss", "שווייץ", "שוויץ", "שווייצרי", "השווייצרי", "שוויצרי")),
    "NL": ("הולנד", "the Netherlands", ("netherlands", "the netherlands", "dutch", "holland", "הולנד", "הולנדי",
                                       "ההולנדי")),
    "BE": ("בלגיה", "Belgium", ("belgium", "belgian", "בלגיה", "בלגי", "הבלגי")),
    "LU": ("לוקסמבורג", "Luxembourg", ("luxembourg", "grand duchy of luxembourg", "לוקסמבורג")),
    "AT": ("אוסטריה", "Austria", ("austria", "austrian", "אוסטריה", "אוסטרי", "האוסטרי")),
    "IT": ("איטליה", "Italy", ("italy", "italian", "איטליה", "איטלקי", "האיטלקי")),
    "ES": ("ספרד", "Spain", ("spain", "spanish", "ספרד", "ספרדי", "הספרדי")),
    "PT": ("פורטוגל", "Portugal", ("portugal", "portuguese", "פורטוגל", "פורטוגלי", "הפורטוגלי")),
    "SE": ("שוודיה", "Sweden", ("sweden", "swedish", "שוודיה", "שוודי", "השוודי")),
    "DK": ("דנמרק", "Denmark", ("denmark", "danish", "דנמרק", "דני", "הדני")),
    "NO": ("נורווגיה", "Norway", ("norway", "norwegian", "נורווגיה", "נורווגי", "הנורווגי")),
    "FI": ("פינלנד", "Finland", ("finland", "finnish", "פינלנד", "פיני", "הפיני")),
    "PL": ("פולין", "Poland", ("poland", "polish", "פולין", "פולני", "הפולני")),
    "CZ": ("צ'כיה", "the Czech Republic", ("czech republic", "czechia", "czech", "צ'כיה")),
    "GR": ("יוון", "Greece", ("greece", "greek", "יוון", "יווני", "היווני")),
    "CY": ("קפריסין", "Cyprus", ("cyprus", "cypriot", "republic of cyprus", "קפריסין", "קפריסאי", "הקפריסאי")),
    "MT": ("מלטה", "Malta", ("malta", "maltese", "מלטה")),
    "SG": ("סינגפור", "Singapore", ("singapore", "singaporean", "republic of singapore", "סינגפור", "סינגפורי",
                                   "הסינגפורי")),
    "HK": ("הונג קונג", "Hong Kong", ("hong kong", "hong kong sar", "הונג קונג")),
    "JP": ("יפן", "Japan", ("japan", "japanese", "יפן", "יפני", "היפני")),
    "CN": ("סין", "the People's Republic of China", ("china", "chinese", "people's republic of china", "prc", "סין")),
    "IN": ("הודו", "India", ("india", "indian", "republic of india", "הודו", "הודי", "ההודי")),
    "AU": ("אוסטרליה", "Australia", ("australia", "australian", "אוסטרליה", "אוסטרלי", "האוסטרלי")),
    "NZ": ("ניו זילנד", "New Zealand", ("new zealand", "ניו זילנד")),
    "AE": ("איחוד האמירויות", "the United Arab Emirates", ("united arab emirates", "uae", "איחוד האמירויות")),
    "BR": ("ברזיל", "Brazil", ("brazil", "brazilian", "ברזיל", "ברזילאי")),
    "ZA": ("דרום אפריקה", "South Africa", ("south africa", "south african", "דרום אפריקה")),
    "KR": ("דרום קוריאה", "the Republic of Korea", ("south korea", "republic of korea", "korea", "דרום קוריאה")),
}
ALIASES = {"UK": "GB", "GB-ENG": "GB-EAW", "GB-WLS": "GB-EAW", "EAW": "GB-EAW", "ENG": "GB-EAW", "EN-GB": "GB-EAW",
           "USA": "US", "NY": "US-NY", "DE-US": "US-DE"}
_BY_NAME = {}
for _c, (_he, _en, _names) in LAWS.items():
    for _n in (_he, _en) + tuple(_names):
        _BY_NAME.setdefault(_n.lower(), _c)


def _clean(v):
    v = re.sub(r"\s+", " ", str(v or "")).strip(" .,;:")
    v = re.sub(r"^(?:דיני|חוקי|הדין של|הדין)\s+(?:מדינת\s+)?", "", v)
    v = re.sub(r"(?i)^(?:the\s+)?laws?\s+of\s+(?:the\s+)?", "", v)
    v = re.sub(r"(?i)\s+law$", "", v)
    return v.strip()


def code(value):
    """הקוד האחיד של הדין, מקוד (IL, gb-eaw, UK) או משם (Israel, English law, דיני אנגליה). None כשאין או לא מוכר."""
    raw = str(value or "").strip()
    if not raw:
        return None
    up = raw.upper().replace("_", "-")
    if up in LAWS:
        return up
    if up in ALIASES:
        return ALIASES[up]
    return _BY_NAME.get(_clean(raw).lower())


def name(value, lang="he"):
    """שם הדין לתוצר: "דיני אנגליה ווילס" / "the law of England and Wales". קוד לא מוכר נכתב כמו שהוא."""
    c = code(value)
    if not c:
        return str(value or "").strip() or None
    he, en, _ = LAWS[c]
    return ("the law of %s" % en) if str(lang or "he")[:2].lower() == "en" else ("דיני %s" % he)


def same_law(a, b):
    """שני דינים זהים כקוד. אנגליה ווילס, סקוטלנד וצפון אירלנד הם דינים שונים; דין מדינה בארה"ב אינו הדין הפדרלי."""
    ca, cb = code(a), code(b)
    return bool(ca and cb and ca == cb)
