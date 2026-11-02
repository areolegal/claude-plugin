# -*- coding: utf-8 -*-
"""common/case_law.py: פסיקה רק ממחבר פסיקה סגור שהלקוח חיבר (הכללים המשותפים 1.1), בקוד ולא רק בהוראות.

שני מבחנים, לכל רכיב ולכל מטרה:
- case_law_url(url): כתובת של אתר בית משפט, מאגר פסיקה פתוח או מדור הפסיקה של אתר רשמי. כתובת כזו אינה נקראת
  ואינה נשמרת כמקור, גם כשהדומיין כולו ברשימת המקורות המאושרים (למשל gov.uk, gov.il, europa.eu).
- case_law_hits(text): אזכור של פסק דין בטקסט (ע"א 1234/05, [2019] UKSC 5, Case C-311/18, 550 U.S. 544), כדי
  שבודק התוצר יעצור פסיקה שלא הגיעה מהמחבר. חוק אמריקני (U.S.C.) אינו פסיקה ואינו נתפס.
case_law_problem(text, connector) מחזיר הודעה כשיש אזכור ואין מחבר, או None.
"""
import re
from urllib.parse import unquote

# אתרי בתי משפט ומאגרי פסיקה פתוחים: כל הדומיין
CASE_LAW_HOSTS = (
    # ישראל
    "court.gov.il", "supreme.court.gov.il", "elyon1.court.gov.il", "takdin.co.il", "psakdin.co.il", "lawdata.co.il",
    "dinonline.co.il", "judgments.gov.il",
    # בריטניה ואירלנד
    "caselaw.nationalarchives.gov.uk", "find-case-law.service.gov.uk", "bailii.org", "judiciary.uk", "supremecourt.uk",
    "courts.ie",
    # ארצות הברית
    "supremecourt.gov", "uscourts.gov", "courtlistener.com", "casetext.com", "casemine.com", "leagle.com",
    "nycourts.gov", "courts.ca.gov", "courts.delaware.gov", "txcourts.gov", "courts.state.ny.us", "ttabvue.uspto.gov",
    "pacer.gov",
    # האיחוד האירופי ובינלאומי
    "curia.europa.eu", "hudoc.echr.coe.int", "echr.coe.int", "icj-cij.org", "pca-cpa.org", "italaw.com",
    # מדינות נוספות
    "canlii.org", "austlii.edu.au", "hklii.hk", "nzlii.org", "saflii.org", "worldlii.org", "commonlii.org",
    "bger.ch", "bundesgerichtshof.de", "bverfg.de", "bundesarbeitsgericht.de", "courdecassation.fr",
    "conseil-etat.fr", "orzeczenia.ms.gov.pl", "sn.pl", "poderjudicial.es", "cortedicassazione.it",
    "rechtspraak.nl", "ecourts.gov.in", "sci.gov.in", "elitigation.sg", "judiciary.gov.sg", "vlex.com",
    "cylaw.org", "fwc.gov.au", "rechtsprechung-im-internet.de", "openjur.de", "dejure.org", "juridat.be",
    "stf.jus.br", "stj.jus.br", "jusbrasil.com.br", "yargitay.gov.tr", "danistay.gov.tr", "kararlar.gov.tr",
)
# מדור פסיקה בתוך אתר שמותר כמקור לחקיקה: (דומיין, תחילית נתיב או ביטוי בכתובת)
CASE_LAW_PATHS = (
    ("nevo.co.il", re.compile(r"/(psika|psikasearch|psika_html|verdicts?)", re.I)),
    ("gov.il", re.compile(r"(labor_court|court_verdicts|verdicts|/psika|judgments?|spokmanship_court|"
                          r"ruling-standards-violations|appeals-committee-decisions|registrar-decisions)", re.I)),
    ("gov.uk", re.compile(r"/(employment-tribunal-decisions|employment-appeal-tribunal-decisions|"
                          r"tax-and-chancery-tribunal-decisions|administrative-appeals-chamber-decisions|"
                          r"immigration-asylum-chamber-decisions|residential-property-tribunal-decisions)", re.I)),
    ("eur-lex.europa.eu", re.compile(r"(CELEX[:%3A]+6\d|/juri|ECLI)", re.I)),
    ("legifrance.gouv.fr", re.compile(r"/(juri|ceta|constit|cnil)/", re.I)),
    ("mass.gov", re.compile(r"/orgs/(supreme-judicial-court|appeals-court|trial-court)|/info-details/massachusetts-law-about", re.I)),
    ("law.cornell.edu", re.compile(r"/supremecourt|/supct", re.I)),
    ("justia.com", re.compile(r"(^|/)cases?/|supreme\.justia", re.I)),
    ("gov.pl", re.compile(r"orzeczeni", re.I)),
    ("boe.es", re.compile(r"/buscar/jurisprudencia", re.I)),
    ("bka.gv.at", re.compile(r"judikatur", re.I)),
    ("ejustice.just.fgov.be", re.compile(r"/cgi/juris|juridat", re.I)),
    ("lexml.gov.br", re.compile(r"urn:lex:br:[^/?#]*(tribunal|justica|turma|jurisprudencia)|jurisprudencia", re.I)),
    ("scholar.google.com", re.compile(r"/scholar_case|[?&]as_sdt=[^&]*[2-9]", re.I)),
    ("data.uspto.gov", re.compile(r"^/ptab", re.I)),
    ("uspto.gov", re.compile(r"/patents/ptab/(decisions|precedential)", re.I)),
    ("epo.org", re.compile(r"(case-law-appeals|boards-of-appeal|/legal/case-law)", re.I)),
    ("euipo.europa.eu", re.compile(r"boards-of-appeal", re.I)),
    ("eppo.europa.eu", re.compile(r"(judgments?|verdicts?|convictions?)", re.I)),
)
# סימן בשם המארח: court, cour, gericht, tribunal, judiciary, lii, caselaw, juris
CASE_LAW_HOST_RX = re.compile(r"(^|[.\-])(courts?|cour|gericht\w*|tribunals?|judiciary|judicial|[a-z]*lii|caselaw|"
                              r"jurisprudence|juris|psika)([.\-]|$)", re.I)


def _split(url):
    u = re.sub(r"^[a-z][a-z0-9+.\-]*://", "", (url or "").strip(), flags=re.I)
    host, _, rest = u.partition("/")
    host = host.split("@")[-1].split(":")[0].lower().rstrip(".")
    return host, "/" + unquote(rest).replace(chr(92), "/")


def _on(host, dom):
    return host == dom or host.endswith("." + dom)


def case_law_url(url):
    """סיבה בעברית כשהכתובת היא של אתר בית משפט, מאגר פסיקה או מדור פסיקה; אחרת None."""
    host, path = _split(url)
    if not host:
        return None
    for d in CASE_LAW_HOSTS:
        if _on(host, d):
            return "%s הוא אתר בית משפט או מאגר פסיקה. פסיקה רק ממחבר פסיקה סגור שהלקוח חיבר (כלל 1.1)" % host
    for d, rx in CASE_LAW_PATHS:
        if _on(host, d) and rx.search(path):
            return "%s%s הוא מדור פסיקה. פסיקה רק ממחבר פסיקה סגור שהלקוח חיבר (כלל 1.1)" % (host, path[:60])
    if CASE_LAW_HOST_RX.search(host):
        return "%s נראה כאתר בית משפט או מאגר פסיקה. פסיקה רק ממחבר פסיקה סגור שהלקוח חיבר (כלל 1.1)" % host
    return None


# אזכורי פסקי דין, בעברית ובאנגלית. חוק (U.S.C., C.F.R., סעיף לחוק) אינו נתפס
CITATION_RX = (
    re.compile(r"(?<![\w֐-׿])[ובלמשכה]{0,2}(ע\"?א|ע״א|רע\"?א|רע״א|בג\"?ץ|בג״ץ|דנ\"?א|דנ״א|ע\"?ע|ע״ע|ע\"?פ|ע״פ|רע\"?פ|"
               r"ת\"?א|ת״א|ה\"?פ|ה״פ|עת\"?ם|עת״ם|עע\"?ם|עע״ם|ע\"?מ|ע״מ|ס\"?ע|ס״ע|ב\"?ש|ב״ש|תא\"?מ|תא״מ|"
               r"ת\"?צ|ת״צ|רע\"?ב|רע״ב|דב\"?ע|דב״ע)\s*\(?[֐-׿\"״' -]*\)?\s*\d{1,6}[-/]\d{2,4}"),
    re.compile(r"\[(1[5-9]|20)\d{2}\]\s*(UKSC|UKPC|UKHL|EWCA|EWHC|UKUT|UKFTT|UKEAT|EAT|IESC|IEHC|SGCA|SGHC|HCA|NZSC|SCC|"
               r"CSIH|CSOH|NICA|AC|QB|KB|Ch|WLR|All\s?ER|Lloyd's\s?Rep|IRLR|BCLC|ICR)\b"),
    re.compile(r"\bEWCA\s+(Civ|Crim)\b|\bEWHC\s+\d+\s*\((Ch|QB|KB|Comm|TCC|Pat|IPEC|Admin|Fam)\)"),
    re.compile(r"\b(Case|Joined\s+Cases|Cases)\s+[CTF]-\d{1,4}/\d{2}\b"),
    re.compile(r"\bECLI:[A-Z]{2}:[A-Z0-9]+:\d{4}:[A-Z0-9.]+"),
    re.compile(r"\b\d{1,4}\s+(U\.S\.|S\.\s?Ct\.|L\.\s?Ed\.(\s?2d)?|F\.(2d|3d|4th)?|F\.\s?Supp\.(\s?[23]d)?|"
               r"A\.(2d|3d)|N\.E\.(2d|3d)|N\.Y\.S\.(2d|3d)?|Cal\.\s?Rptr\.(\s?[23]d)?|Del\.\s?Ch\.)\s+\d{1,5}\b"),
    re.compile(r"\b[A-Z][\w.&'\- ]{1,60}\s+v\.?\s+[A-Z][\w.&'\- ]{1,60},?\s+\d{1,4}\s+(U\.S\.|F\.|S\.\s?Ct\.)"),
    re.compile(r"\bBGH,?\s+(Urteil|Beschluss)\b|\bCass\.\s+(civ|com|soc)\b", re.I),
)


def case_law_hits(text):
    """אזכורי פסיקה בטקסט: רשימת הקטעים שנמצאו (ריקה כשאין)."""
    hits = []
    for rx in CITATION_RX:
        for m in rx.finditer(text or ""):
            hits.append(m.group(0).strip())
    return hits


# כינויים כלליים לפסק דין ושמות צדדים בתבנית "X v Y". זה הבודק היחיד: שום קוד אחר בתוכנה אינו מכיל שם של פסק דין
CASE_LAW_EXTRA = re.compile(r'פס"ד|פס״ד|פסק הדין|פסקי הדין|הלכת\s|הפסיקה קבעה|\b[A-Z][A-Za-z&]+ v\.? [A-Z][A-Za-z]+\b')


def case_law_mentions(text):
    """אזכורי פסיקה בטקסט, כולל הכינויים הכלליים: רשימה, ריקה כשאין."""
    hits = case_law_hits(text)
    m = CASE_LAW_EXTRA.search(text or "")
    return hits + ([m.group(0)] if m else [])


def case_law_problem(text, connector=None):
    """הודעה כשבטקסט יש אזכור פסיקה ואין מחבר פסיקה סגור; אחרת None. עם מחבר, הבודק של הרכיב עדיין מוודא
    שהאזכור הוא ממה שהמחבר החזיר בהרצה (case_law[] עם ציטוט מלא)."""
    if connector:
        return None
    hits = case_law_hits(text)
    if hits:
        return "אזכור פסיקה בלי מחבר פסיקה סגור (כלל 1.1): %s" % "; ".join(hits[:3])
    return None


def _walk_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _walk_strings(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _walk_strings(v)


def case_law_in_data(obj, connector=None):
    """אזכורי פסיקה בכל מחרוזת במבנה JSON, כשאין מחבר. מחזיר רשימת אזכורים (ריקה כשאין, או כשיש מחבר)."""
    if connector:
        return []
    out = []
    for s in _walk_strings(obj):
        out.extend(case_law_hits(s))
    return out
