#!/usr/bin/env python3
import argparse, hashlib, json, os, re, sys, zipfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python -I: sibling imports
from xml.etree import ElementTree as ET

for _s in (sys.stdout, sys.stderr):  # Hebrew on a non-UTF-8 console (cp1252): no UnicodeEncodeError
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):   # not a TextIOWrapper (captured in tests, pythonw)
        pass

# The shared library (areolegal/lib) gives guard_out and load_docx_or_explain. Without it the script still runs,
# with the two minimal checks below: the report is never written over an input, and a non-docx file gets a message.
_LIB = Path(__file__).resolve().parents[3] / 'lib'
if _LIB.is_dir() and str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))
try:
    from common.cli import OutputRefused, guard_out, load_docx_or_explain
except ImportError:
    class OutputRefused(Exception):
        pass

    def guard_out(out, inputs=()):
        k = os.path.normcase(os.path.realpath(out))
        if any(p and os.path.normcase(os.path.realpath(p)) == k for p in inputs):
            raise OutputRefused('--out is an input file: %s' % out)
        if os.path.isfile(k) and k.lower().endswith(('.docx', '.doc', '.pdf')):
            raise OutputRefused('--out is an existing document: %s' % out)
        return os.path.abspath(out)

    def load_docx_or_explain(path, loader=None, strict_ok=False):
        try:
            with zipfile.ZipFile(path) as z:
                z.getinfo('word/document.xml')
            return path, None, 0
        except Exception as e:
            return None, 'לא ניתן לקרוא את %s כמסמך Word (%s).\n%s cannot be read as a Word document (%s).' % (
                os.path.basename(path), type(e).__name__, os.path.basename(path), type(e).__name__), 2

HEB = re.compile(r'[\u0590-\u05ff]')
LAT = re.compile(r'[A-Za-z]')

W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

try:    # sniff, seg_hash and collect need lxml; without it the manifest checks report 'not checked'
    from build_translation_docx import sniff, seg_hash, collect
except ImportError:      # pragma: no cover
    sniff = seg_hash = collect = None

# Hebrew <-> English: the same amount is written "100 ש״ח" in one language and "NIS 100" / "ILS 100" / "₪100" in
# the other, and "10 אחוזים" against "10%" or "10 percent". Both sides are normalised to one form before comparing,
# so a correct translation in either direction is not reported as a numeric change, and a swapped currency
# (CHF -> EUR, SEK -> NOK) is. Currencies: ISO 4217 codes (upper case only, so "all" or "try" in a sentence are not
# currencies), symbols, and English and Hebrew names.
CUR_WORDS={'₪':'ILS','nis':'ILS','ש"ח':'ILS','ש״ח':'ILS','שח':'ILS','שקל':'ILS','שקלים':'ILS','שקלים חדשים':'ILS',
           'new israeli shekels':'ILS','shekels':'ILS','shekel':'ILS',
           '$':'USD','us$':'USD','dollar':'USD','dollars':'USD','us dollars':'USD','דולר':'USD','דולרים':'USD',
           'דולר ארה"ב':'USD','דולר ארה״ב':'USD','דולר אמריקאי':'USD','€':'EUR','euro':'EUR','euros':'EUR',
           'אירו':'EUR','יורו':'EUR','£':'GBP','pound':'GBP','pounds':'GBP','pounds sterling':'GBP','sterling':'GBP',
           'ליש"ט':'GBP','ליש״ט':'GBP','לירות שטרלינג':'GBP','לירה שטרלינג':'GBP',
           'swiss francs':'CHF','swiss franc':'CHF','francs':'CHF','franc':'CHF','fr.':'CHF','פרנק':'CHF',
           'פרנקים':'CHF','פרנק שווייצרי':'CHF','פרנקים שווייצריים':'CHF','פרנק שוויצרי':'CHF',
           '¥':'JPY','yen':'JPY','ין':'JPY','ין יפני':'JPY','yuan':'CNY','renminbi':'CNY','יואן':'CNY',
           '₹':'INR','rupees':'INR','rupee':'INR','רופי':'INR','₩':'KRW','won':'KRW','₽':'RUB','roubles':'RUB',
           'rubles':'RUB','רובל':'RUB','₺':'TRY','turkish lira':'TRY','לירה טורקית':'TRY',
           'c$':'CAD','canadian dollars':'CAD','canadian dollar':'CAD','דולר קנדי':'CAD',
           'a$':'AUD','australian dollars':'AUD','australian dollar':'AUD','דולר אוסטרלי':'AUD',
           'hk$':'HKD','hong kong dollars':'HKD','s$':'SGD','singapore dollars':'SGD','nz$':'NZD',
           'swedish kronor':'SEK','swedish krona':'SEK','כתר שוודי':'SEK','norwegian kroner':'NOK','כתר נורווגי':'NOK',
           'danish kroner':'DKK','כתר דני':'DKK','zloty':'PLN','złoty':'PLN','זלוטי':'PLN','forint':'HUF',
           'koruna':'CZK','rand':'ZAR','dirham':'AED','dirhams':'AED','דירהם':'AED','real':'BRL','reais':'BRL',
           'pesos':'MXN','peso':'MXN'}
ISO_4217=('ILS','USD','EUR','GBP','CHF','JPY','CNY','INR','KRW','RUB','TRY','CAD','AUD','HKD','SGD','NZD','SEK','NOK',
          'DKK','PLN','HUF','CZK','RON','BGN','ZAR','AED','SAR','QAR','KWD','BHD','OMR','JOD','EGP','MAD','BRL','MXN',
          'ARS','CLP','COP','PEN','THB','MYR','IDR','PHP','VND','TWD','UAH','KZT','ISK','NGN','KES','XAU','XAG')
_CW='|'.join(sorted((re.escape(k) for k in CUR_WORDS), key=len, reverse=True))
_ISO='|'.join(ISO_4217)
_AMT=r'\d[\d,.]*\d|\d'
# ISO codes upper case only ((?-i:...)); names and symbols in any case
_CUR=r'(?-i:%s)(?![A-Za-z])|%s' % (_ISO, _CW)
CUR_AFTER=re.compile(r'(%s)\s?(%s)(?![\w֐-׿])' % (_AMT,_CUR), re.I)
CUR_BEFORE=re.compile(r'(?<![\w֐-׿])(%s)\s?(%s)' % (_CUR,_AMT), re.I)
PCT_WORDS=re.compile(r'(\d+(?:[.,]\d+)?)\s?(?:%|אחוזים|אחוז|percent|per cent|pct\.?)(?![\w֐-׿])', re.I)
# A grouped number: "1,000,000.00", "1.000.000,00", "1 000 000,00" (groups of exactly three digits). Section numbers
# ("5.2.1") and dates ("12.10.2026") do not have that shape and are compared as written.
_GROUPED=re.compile(r'^\d{1,3}(?P<g>[.,   ])\d{3}(?:(?P=g)\d{3})*(?:(?P<d>[.,])\d+)?$')


def norm_num(v):
    """One form for one number: thousands separators removed, a decimal comma becomes a point.
    "1.000.000,00" and "1,000,000.00" both give "1000000.00". "1,000" is a thousand; "1.000" alone is ambiguous
    (a thousand in German, one in English) and stays as written, so a mismatch is reported, not hidden."""
    t=v.strip()
    m=_GROUPED.match(t)
    if m and (m.group('d') is None or m.group('d')!=m.group('g')):
        g=m.group('g')
        if g=='.' and m.group('d') is None and t.count('.')==1:
            return t
        head,dec=(t.rsplit(m.group('d'),1)+[''])[:2] if m.group('d') else (t,'')
        return head.replace(g,'')+('.'+dec if dec else '')
    if re.match(r'^\d+,\d{1,2}$', t) or re.match(r'^\d+,\d{4,}$', t):
        return t.replace(',', '.')
    return t


def _cur_code(tok):
    return tok.upper() if tok.upper() in ISO_4217 and tok.isupper() else CUR_WORDS.get(tok.lower())


# The translation's own production stamp and status legend belong in the header or footer, which are never read here
# (only word/document.xml). Fallback for a template with no header: a body paragraph styled AreoStamp is skipped on
# both sides and listed under ignored_stamp_paragraphs, so a skipped line is always visible in the report.
STAMP_STYLE='areostamp'

def text_of(path, skipped=None):
    p=Path(path)
    from build_translation_docx import sniff, pdf_paragraphs
    kind=sniff(str(p))
    if kind=='pdf':
        # A PDF source or target: the same extraction as the translation builder (pymupdf)
        paras, why = pdf_paragraphs(str(p))
        if why:
            raise SystemExit('%s: %s' % (p.name, why))
        return '\n'.join(paras)
    if kind=='docx':
        with zipfile.ZipFile(p) as z:
            xml=z.read('word/document.xml')
        root=ET.fromstring(xml)
        parts=[]
        for para in root.iter(W+'p'):
            txt=''.join(t.text or '' for t in para.iter(W+'t'))
            st=para.find(W+'pPr/'+W+'pStyle')
            if st is not None and (st.get(W+'val') or '').lower()==STAMP_STYLE:
                if skipped is not None: skipped.append(txt)
                continue
            parts.append(txt)
        return '\n'.join(parts)
    return p.read_text(encoding='utf-8')

# The stamp and the legend of the translation sit in its header or footer; they are not source content
STAMP_LINE = re.compile(r"^\s*(?:produced on|last updated|translation for reference|draft\b|הופק בתאריך|עדכון אחרון|"
                        r"תרגום לעיון|טיוטה\b)", re.I)


def hf_paragraphs(path):
    """[(part, text, has_bidi)] for every non-empty paragraph of the headers and footers, without the stamp and
    the legend (paragraphs styled AreoStamp, or lines that open like them)."""
    out = []
    from build_translation_docx import sniff
    if sniff(str(path)) != 'docx':      # a PDF has no headers or footers to compare
        return out
    with zipfile.ZipFile(path) as z:
        for n in sorted(z.namelist()):
            if not re.match(r'^word/(header|footer)\d*\.xml$', n):
                continue
            root = ET.fromstring(z.read(n))
            for para in root.iter(W + 'p'):
                txt = ''.join(t.text or '' for t in para.iter(W + 't')).strip()
                st = para.find(W + 'pPr/' + W + 'pStyle')
                if not txt or (st is not None and (st.get(W + 'val') or '').lower() == STAMP_STYLE) or STAMP_LINE.match(txt):
                    continue
                out.append((n, txt, para.find(W + 'pPr/' + W + 'bidi') is not None))
    return out


# A Hebrew-calendar year (5741) appears in digits in an English translation and in letters (התשמ"א) in Hebrew:
# the same year in two writing systems, not an added number
HEB_YEAR = re.compile(r'^57\d\d$')


def currencies(text):
    out=[]
    for m in CUR_AFTER.finditer(text):
        code=_cur_code(m.group(2))
        if code:
            out.append((m.start(), m.end(), '%s %s' % (code, norm_num(m.group(1)))))
    for m in CUR_BEFORE.finditer(text):
        code=_cur_code(m.group(1))
        if code and not any(a<m.end() and m.start()<b for a,b,_ in out):
            out.append((m.start(), m.end(), '%s %s' % (code, norm_num(m.group(2)))))
    return [t for _,_,t in sorted(out)]

MONTHS={m:i+1 for i,m in enumerate(['january','february','march','april','may','june','july','august','september',
                                    'october','november','december'])}
MONTHS.update({m:i+1 for i,m in enumerate(['ינואר','פברואר','מרץ','אפריל','מאי','יוני','יולי','אוגוסט','ספטמבר',
                                         'אוקטובר','נובמבר','דצמבר'])})
_MON='|'.join(sorted(MONTHS, key=len, reverse=True))
DATE_WORDS=re.compile(r'(?<!\d)(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+|ב)?(%s),?\s+(\d{4})|(%s)\s+(\d{1,2}),\s+(\d{4})' % (_MON,_MON), re.I)
DATE_NUM=re.compile(r'(?<![\d.])(\d{1,2})[./](\d{1,2})[./](\d{4})(?!\d)(?!\.\d)')
DATE_ISO=re.compile(r'(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)')


def norm_dates(text):
    """Every date in one form (YYYY-MM-DD), so "30 October 2026" and "30.10.2026" are the same date."""
    def words(m):
        if m.group(1):
            d, mo, y = m.group(1), MONTHS[m.group(2).lower()], m.group(3)
        else:
            mo, d, y = MONTHS[m.group(4).lower()], m.group(5), m.group(6)
        return ' %s-%02d-%02d ' % (y, mo, int(d))
    text=DATE_WORDS.sub(words, text)
    text=DATE_NUM.sub(lambda m: ' %s-%02d-%02d ' % (m.group(3), int(m.group(2)), int(m.group(1))), text)
    return text


def tokens(text):
    # Numeric integrity: dates, percentages, currency-like values and section-number patterns.
    text=PCT_WORDS.sub(lambda m: m.group(1)+'%', text)
    text=norm_dates(text)
    dates=DATE_ISO.findall(text)
    text=DATE_ISO.sub(' ', text)
    nums=[n for n in [norm_num(x[:-1])+'%' if x.endswith('%') else norm_num(x) for x in
          re.findall(r'(?<![\w])(?:\d{1,4}(?:[.,]\d+)*%?|\d{1,2}[./-]\d{1,2}[./-]\d{2,4})(?![\w])', text)]
          if not HEB_YEAR.match(n)]
    nums=nums+['%s-%s-%s' % d for d in dates]
    headings=re.findall(r'(?m)^\s*(\d+(?:\.\d+){0,4})[.)]?\s+', text)
    return {'numeric_tokens': nums, 'currency_tokens': currencies(text), 'section_numbers': headings}

def multiset_diff(a,b):
    from collections import Counter
    ca,cb=Counter(a),Counter(b)
    return list((ca-cb).elements()), list((cb-ca).elements())

def target_lang(text):
    """he or en, by the share of Hebrew letters in the target: the suffix of the canonical report name."""
    he, la = len(HEB.findall(text)), len(LAT.findall(text))
    return 'he' if he and he >= la else 'en'

def canonical_name(doc_id, lang):
    """translation-integrity-<id>-<en|he>.json (SKILL.md, "דוח השלמות"): the name is fixed here, not by the model.
    The id is transaction_id, or a short Latin id of the document; anything else in it becomes '-'."""
    clean = re.sub(r'[^A-Za-z0-9_.-]+', '-', doc_id or '').strip('-.') or 'document'
    return 'translation-integrity-%s-%s.json' % (clean[:60], lang)

def unique(path):
    """An existing file is never overwritten: a taken name gets a number in parentheses."""
    if not os.path.exists(path):
        return path
    stem, ext = os.path.splitext(path)
    n = 2
    while os.path.exists('%s (%d)%s' % (stem, n, ext)):
        n += 1
    return '%s (%d)%s' % (stem, n, ext)

# ===================================================================================================================
# Segment-level integrity (translation manifest mode, `--manifest segments.json`).
#   Level 1  coverage + structure: every source segment has exactly one target or a visible reason; a missing,
#            duplicated, source-changed or hidden-untranslated segment is rejected; a material gap blocks "complete".
#   Level 2  per segment: numbers, currencies, dates, percentages, section numbers, placeholders, definition markers and
#            glossary terms, each compared with its ALIGNED source segment (never with global totals).
#   Level 3  per segment: obligation cues from generic bilingual lexicons (modality, negation, exception, trigger,
#            deadline, party role, remedy, action, cross-reference) and amount/party attachment per obligation.
# What no script can decide goes to the review queue for a clean-context verifier read, labelled as judgement.
# Nothing here asserts legal validity: it is a mechanical comparison of two texts.
# ===================================================================================================================
REPORT_SCHEMA = 'areo-translation-integrity/2'
MANIFEST_SCHEMA = 'areo-translation-manifest/1'
_HB = '֐-׿'
_L = r'(?<![A-Za-z0-9_%s])' % _HB
_R = r'(?![A-Za-z0-9_%s])' % _HB

MECHANICAL_CHECKS = [
    'manifest_matches_source_hash', 'every_segment_has_one_target_or_reason', 'missing_or_duplicate_segment',
    'source_changed_segment', 'footnotes_comments_tables_headings_annexes_covered', 'untranslated_copy_detected',
    'built_file_matches_manifest', 'fields_bookmarks_references_attached', 'numbers_currencies_dates_per_segment',
    'glossary_terms_per_segment', 'modality_shall_may_per_segment', 'negation_per_segment', 'exception_per_segment',
    'deadline_per_segment', 'amount_and_party_attachment_per_obligation', 'cross_references_per_segment']
JUDGEMENT_CHECKS = [
    'whether_the_target_wording_really_carries_the_same_obligation', 'obligations_without_an_explicit_marker',
    'trigger_and_condition_equivalence', 'remedy_and_liability_scope', 'defined_term_use_in_context',
    'non_equivalent_concepts', 'scanned_text_read_against_the_image', 'emphasis_that_carries_meaning']
NEVER_CLAIMED = ('This report compares two texts mechanically and lists what still needs a human read. It does not '
                 'assess legal validity or legal equivalence.\nהדוח משווה שני טקסטים באופן ממוכן ומפרט מה עדיין טעון '
                 'קריאה אנושית. הוא אינו קובע תוקף משפטי או שקילות משפטית.')


def _rx(alts, pre=''):
    return re.compile(_L + pre + '(?:' + '|'.join(alts) + ')' + _R, re.I)


_H = lambda w: w + '(?:ת|ים|ות|ם|ן)?'      # Hebrew inflection of an adjective/participle
RULES = [
    ('exc', _rx([r'except(?:ing)?(?: that| for)?', r'unless', r'save(?: for| that)', r'other than', r'excluding',
                 r'exclusive of', r'apart from', r'with the exception of', r'but for', r'barring',
                 r'למעט', r'אלא\s+אם(?:\s+כן)?', r'פרט\s+ל\S*', r'מלבד'], 'ו?')),
    ('prohib', _rx([r'(?:shall|must|may|will|can) not', r'cannot', r'(?:is|are) not (?:permitted|allowed|entitled|'
                    r'authori[sz]ed) to', r'(?:is|are) (?:prohibited|forbidden|barred|precluded) from',
                    r'shall refrain from', r'(?:agrees|undertakes|covenants) not to',
                    r'אינ(?:ו|ה|ם|ן)\s+רשאי(?:ת|ם|ן|ות)?', r'לא\s+(?:יהיה|יהיו|תהיה|תהיינה)\s+רשאי(?:ת|ם|ן|ות)?',
                    r'אסור(?:ה|ים|ות)?', r'מנוע(?:ה|ים|ות)?', r'מתחייב(?:ת|ים|ות)?\s+שלא',
                    r'(?:יימנע|תימנע|יימנעו|תימנעו)', r'לא\s+(?:יוכל|תוכל|יוכלו)'], 'ו?')),
    ('perm', _rx([r'(?:shall|will) (?:be entitled|have the right|be permitted|be free|be authori[sz]ed) to',
                  r'(?:is|are) (?:entitled|permitted|allowed|authori[sz]ed|free) to',
                  r'(?:has|have) the (?:right|option|discretion) to',
                  r'(?:at|in) (?:its|his|her|their|the) (?:sole |absolute |own |reasonable )*discretion',
                  r'רשאי(?:ת|ם|ן|ות)?', r'זכאי(?:ת|ם|ן|ות)?', r'מותר', r'בשיקול\s+דעת(?:ו|ה|ם|ן)(?:\s+ה(?:בלעדי|מוחלט))?',
                  r'(?:הזכות|זכות)\s+ל', r'יוכל|תוכל|יוכלו'], 'ו?')),
    ('duty', _rx([r'shall', r'must', r'(?:is|are) (?:required|obliged|obligated|bound) to',
                  r'(?:undertakes?|agrees?|covenants?|commits?) to', r'will', r'(?:has|have|needs?) to',
                  r'מתחייב(?:ת|ים|ות)?', r'חייב(?:ת|ים|ות)?', r'מחויב(?:ת|ים|ות)?', r'נדרש(?:ת|ים|ות)?',
                  r'יידרש(?:ו)?', r'על(?:יו|יה|יהם|יהן)\s+ל(?=[א-ת])', r'על\s+ה(?!ידי)[א-ת]+\s+ל(?=[א-ת])'], 'ו?')),
    ('perm', _rx([r'may', r'can'])),
    ('neg', _rx([r'not', r'no(?!\.\s*\d)', r'never', r'neither', r'nor', r'none', r'nothing', r'nobody', r'without',
                 r'[A-Za-z]+n\'t', r'לא', r'אין', r'אינ(?:ו|ה|ם|ן)', r'איננ(?:ו|ה)', r'ללא', r'בלי', r'מבלי', r'שלא',
                 r'לעולם\s+לא'], 'ו?')),
    ('cond', _rx([r'if', r'upon', r'in the event(?: that| of)?', r'where', r'when', r'whenever', r'once',
                  r'provided(?:,? however,?)? that', r'subject to', r'prior to', r'following', r'after', r'before',
                  r'as of', r'from the date', r'in case(?: of)?',
                  r'אם', r'ככל\s+ש', r'במקרה\s+(?:ש|של)', r'כאשר', r'בעת', r'לאחר', r'לפני', r'בכפוף\s+ל', r'בהתקיים',
                  r'ובלבד\s+ש', r'בתנאי\s+ש', r'מרגע', r'מיום', r'עם\s+(?:קרות|קבלת|התקיימות)', r'בהינתן'], 'ו?')),
]

REMEDIES = {
    'indemnity': r'indemnif|hold harmless|שיפוי|ישפה|תשפה|לשפות|ישפו',
    'liability': r'liab|אחראי|אחריות|אחראית|אחראים',
    'damages': r'damages|compensat|פיצוי|יפצה|לפצות|נזק|נזקים',
    'termination': r'terminat|rescind|ביטול|יבטל|לבטל|מבטל|הפסקת ההסכם|יסיים|לסיים',
    'cure': r'\bcure\b|rectif|לתקן|יתקן|תיקון ההפרה',
    'penalty': r'penalt|liquidated damages|late fee|interest on|קנס|פיצוי מוסכם|ריבית',
    'refund': r'refund|reimburs|credit note|החזר|יחזיר|השבה|זיכוי',
    'injunction': r'injunct|specific performance|צו מניעה|אכיפה|סעד',
    'limitation': r'limit(?:ed|ation) (?:of|to)|\bcap(?:ped)?\b|shall not exceed|aggregate liability|מוגבל|הגבלת|תקרה|לא יעלה על',
    'uncapped': r'unlimited|without limit|uncapped|ללא הגבלה|בלתי מוגבל'}
ACTIONS = {
    'pay': r'\bpay|payment|שיל[םמ]|תשלום|ישלם|לשלם|תשלם|ישלמו',
    'deliver': r'deliver|supply|provide|יספק|לספק|אספקה|ימסור|למסור|מסירה',
    'notify': r'notify|notice|inform|יודיע|להודיע|הודעה|ימסור הודעה',
    'return': r'\breturn|\brestore|יחזיר|להחזיר',
    'confidential': r'confidential|keep secret|סודיות|בסוד|יסוד',
    'comply': r'comply|compliance|יעמוד ב|לעמוד ב|יקיים|לקיים|ציות',
    'repair': r'\brepair|replace|fix|יתקן|לתקן|יחליף|להחליף',
    'insure': r'insur|ביטוח|יבטח|לבטח',
    'assign': r'\bassign|transfer|delegate|המחאה|להמחות|יעביר|להעביר',
    'report': r'\breport|account for|דיווח|ידווח|לדווח',
    'maintain': r'maintain|preserve|keep|ישמור|לשמור|יתחזק'}

NUMWORDS = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
            'eleven': 11, 'twelve': 12, 'fifteen': 15, 'twenty': 20, 'thirty': 30, 'forty': 40, 'fifty': 50, 'sixty': 60,
            'ninety': 90, 'hundred': 100, 'אחד': 1, 'שניים': 2, 'שני': 2, 'שלושה': 3, 'ארבעה': 4, 'חמישה': 5, 'שישה': 6,
            'שבעה': 7, 'שמונה': 8, 'תשעה': 9, 'עשרה': 10, 'חמישה עשר': 15, 'עשרים': 20, 'שלושים': 30, 'ארבעים': 40,
            'חמישים': 50, 'שישים': 60, 'תשעים': 90, 'מאה': 100}
_NW = '|'.join(sorted((re.escape(k) for k in NUMWORDS), key=len, reverse=True))
UNITS = {'day': 'day', 'days': 'day', 'week': 'week', 'weeks': 'week', 'month': 'month', 'months': 'month', 'year': 'year',
         'years': 'year', 'hour': 'hour', 'hours': 'hour', 'יום': 'day', 'ימים': 'day', 'שבוע': 'week', 'שבועות': 'week',
         'חודש': 'month', 'חודשים': 'month', 'שנה': 'year', 'שנים': 'year', 'שעה': 'hour', 'שעות': 'hour',
         'ימי עסקים': 'day', 'ימי עבודה': 'day', 'ימי בנקאות': 'day'}
_UN = '|'.join(sorted((re.escape(k) for k in UNITS), key=len, reverse=True))
DURATION = re.compile(_L + r'(?P<n>\d+|%s)(?:\s*\((?P<n2>\d+)\))?\s+(?P<dt>business |working |banking |calendar )?'
                      r'(?P<u>%s)' % (_NW, _UN) + _R, re.I)
PLACEHOLDER = re.compile(r'\[(?:להשלים|to complete|TBC)[^\]]*\]|\[●\]|\[\s*\]', re.I)
DEFMARK = re.compile(r'\((?:להלן|hereinafter|hereafter|the|each|together)?:?\s*[\"“”״\']+[^\"“”״\']{2,40}[\"“”״\']+\s*\)', re.I)
REFWORD = (r'(?:sections?|clauses?|articles?|paragraphs?|schedules?|annex(?:es|ure)?|appendix|appendices|exhibits?|'
           r'סעיפים|סעיף|פרק|נספח|תוספת|לוח|סעיף קטן)')
# "בתוספת מע"מ" (plus VAT) is not a reference to an addendum: the word is followed by a tax, not by an id
XREF = re.compile(_L + '[ובלכמש]{0,2}' + REFWORD + r'(?!\s+(?:מע["״\']?מ|מס\b|מיסים|מסים))'
                  + r'\s+((?:[A-Za-z]|[א-ת]\'?|\d)[\w.()א-ת\'’״-]*)', re.I)
HE2LAT = dict(zip('אבגדהוזחטיכלמנסעפצקרשת', 'abcdefghijklmnopqrstuv'))
HE2LAT.update({'ך': 'k', 'ם': 'm', 'ן': 'n', 'ף': 'q', 'ץ': 'r'})
PASSIVE_BY = re.compile(r'(?:\bby\s+(?:the\s+)?|על[\s-]ידי\s+|בידי\s+)$', re.I)


def _norm_ref(r):
    r = re.sub(r'[\'’״"]', '', r).rstrip('.,;:)')
    r = re.sub(r'[א-ת]', lambda m: HE2LAT.get(m.group(0), m.group(0)), r)
    return r.lower()


def refs_of(text):
    return [_norm_ref(m.group(1)) for m in XREF.finditer(text) if _norm_ref(m.group(1))]


def _words_to_n(tok):
    return str(NUMWORDS.get(tok.lower(), tok)) if not tok.isdigit() else tok


def durations(text):
    """[(start, end, 'D <n> <unit>[ business]')]: a deadline in one form, in either language."""
    out = []
    for m in DURATION.finditer(text):
        n = m.group('n2') or _words_to_n(m.group('n'))
        u = m.group('u').lower()
        biz = (m.group('dt') or '').strip().lower() in ('business', 'working', 'banking') or u in (
            'ימי עסקים', 'ימי עבודה', 'ימי בנקאות')
        out.append((m.start(), m.end(), 'D %s %s%s' % (n, UNITS.get(u, u), ' business' if biz else '')))
    return out


def quants(text):
    """[(start, end, token)] in text order: currency amounts, percentages and deadlines."""
    out = []
    for m in CUR_AFTER.finditer(text):
        c = _cur_code(m.group(2))
        if c:
            out.append((m.start(), m.end(), '%s %s' % (c, norm_num(m.group(1)))))
    for m in CUR_BEFORE.finditer(text):
        c = _cur_code(m.group(1))
        if c and not any(a < m.end() and m.start() < b for a, b, _ in out):
            out.append((m.start(), m.end(), '%s %s' % (c, norm_num(m.group(2)))))
    for m in PCT_WORDS.finditer(text):
        out.append((m.start(), m.end(), m.group(1) + '%'))
    for a, b, t in durations(text):
        if not any(x < b and a < y for x, y, _ in out):
            out.append((a, b, t))
    return sorted(out)


def _scan(text):
    work, found = text, []
    for cls, rx in RULES:
        for m in rx.finditer(work):
            found.append((cls, m.start(), m.end()))
        work = rx.sub(lambda m: ' ' * len(m.group(0)), work)
    return sorted(found, key=lambda x: x[1])


def _cats(table, text):
    return sorted(k for k, v in table.items() if re.search(v, text, re.I))


# ---- parties: from the glossary (role: party), the manifest's `parties`, a --parties file, plus generic markers -------
GENERIC_PARTIES = [
    {'id': 'other_party', 'en': ['the other party', 'the counterparty'], 'he': ['הצד השני', 'הצד האחר', 'הצד שכנגד']},
    {'id': 'all_parties', 'en': ['each party', 'either party', 'both parties', 'each of the parties'],
     'he': ['כל צד', 'שני הצדדים', 'כל אחד מהצדדים']},
    {'id': 'party_a', 'en': ['party a', 'the first party'], 'he': ['צד א', 'צד א\'', 'הצד הראשון']},
    {'id': 'party_b', 'en': ['party b', 'the second party'], 'he': ['צד ב', 'צד ב\'', 'הצד השני']}]
_term_cache = {}


def _term_rx(term):
    if term in _term_cache:
        return _term_cache[term]
    t = re.sub(r'\s+', ' ', term.strip())
    if re.search('[֐-׿]', t):
        core = t[1:] if len(t) > 3 and t.startswith('ה') else t
        rx = re.compile(r'(?<![A-Za-z0-9_%s])[ושבלכמ]{0,2}ה?%s(?:ים|ות|ו|ה|ם|ן|י)?%s' % (
            _HB, re.escape(core).replace('\\ ', r'\s+'), _R))
    else:
        rx = re.compile(_L + r"(?:the\s+)?%s(?:'s|s)?" % re.escape(t).replace('\\ ', r'\s+') + _R, re.I)
    _term_cache[term] = rx
    return rx


def find_parties(text, pmap):
    """[(start, end, party_id)] non-overlapping, longest first, in text order."""
    cand = []
    for ent in pmap:
        for lang in ('he', 'en'):
            for term in ent.get(lang, []):
                for m in _term_rx(term).finditer(text):
                    cand.append((m.start(), m.end(), ent['id']))
    cand.sort(key=lambda x: (-(x[1] - x[0]), x[0]))
    taken, out = [], []
    for a, b, i in cand:
        if not any(a < y and x < b for x, y in taken):
            taken.append((a, b))
            out.append((a, b, i))
    return sorted(out)


def _lang_of_term(t):
    return 'he' if re.search('[֐-׿]', t) else 'en'


def load_party_map(glossary_entries, extra):
    pm = [dict(e) for e in GENERIC_PARTIES]
    for e in list(glossary_entries) + list(extra or []):
        if e.get('role') == 'party' or e.get('party'):
            pm.append({'id': e.get('id') or (e.get('en') or e.get('he') or ['?'])[0], 'he': e.get('he', []), 'en': e.get('en', [])})
    return pm


# ---- glossary ------------------------------------------------------------------------------------------------------
def load_glossary(path):
    """(version, entries[{'id','he':[..],'en':[..],'status','role'}]) from any of the usual JSON shapes."""
    data = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    version = ''
    items = data
    if isinstance(data, dict):
        version = str(data.get('glossary_version') or data.get('version') or data.get('id') or '')
        items = data.get('terms') or data.get('entries') or data.get('glossary')
        if items is None:
            items = [{'source': k, 'target': v} for k, v in data.items() if isinstance(v, (str, list))]
    out = []
    keys = ('source', 'target', 'src', 'tgt', 'he', 'en', 'hebrew', 'english', 'term', 'translation', 'term_he', 'term_en',
            'source_term', 'target_term', 'approved_translation')
    for n, it in enumerate(items or []):
        if not isinstance(it, dict):
            continue
        ent = {'id': str(it.get('id') or it.get('term_id') or n), 'he': [], 'en': [],
               'status': str(it.get('status') or 'approved').lower(), 'role': it.get('role') or ('party' if it.get('party') else '')}
        for k in keys:
            v = it.get(k)
            for s in ([v] if isinstance(v, str) else (v if isinstance(v, list) else [])):
                for part in re.split(r'\s*[;|]\s*', str(s)):
                    if part.strip():
                        ent[_lang_of_term(part)].append(part.strip())
        for k in ('alternates', 'variants', 'allowed'):
            v = it.get(k)
            for s in (v if isinstance(v, list) else []):
                ent[_lang_of_term(str(s))].append(str(s))
        if ent['he'] or ent['en']:
            out.append(ent)
    return version, out


def glossary_findings(src, tgt, src_lang, tgt_lang, entries):
    out = []
    for e in entries:
        if e['status'] not in ('approved', 'approved_term', 'מאושר'):
            continue
        s_terms, t_terms = e.get(src_lang, []), e.get(tgt_lang, [])
        if not s_terms or not t_terms:
            continue
        if any(_term_rx(t).search(src) for t in s_terms) and not any(_term_rx(t).search(tgt) for t in t_terms):
            out.append({'type': 'glossary_term_missing', 'severity': 'error',
                        'detail': 'approved term %r is in the source but none of %r is in the target' % (s_terms[0], t_terms)})
    return out


# ---- Level 2 ---------------------------------------------------------------------------------------------------------
def level2_pair(src, tgt, src_lang, tgt_lang, entries):
    f = []
    s, t = tokens(src), tokens(tgt)
    for key, code in (('numeric_tokens', 'number_mismatch'), ('currency_tokens', 'currency_mismatch'),
                      ('section_numbers', 'section_number_mismatch')):
        miss, extra = multiset_diff(s[key], t[key])
        if miss or extra:
            f.append({'type': code, 'severity': 'error', 'detail': {'missing_in_target': miss, 'extra_in_target': extra}})
    ps, pt = len(PLACEHOLDER.findall(src)), len(PLACEHOLDER.findall(tgt))
    if ps != pt:
        f.append({'type': 'placeholder_count_mismatch', 'severity': 'error', 'detail': {'source': ps, 'target': pt}})
    ds, dt = len(DEFMARK.findall(src)), len(DEFMARK.findall(tgt))
    if ds != dt:
        f.append({'type': 'definition_marker_mismatch', 'severity': 'review', 'detail': {'source': ds, 'target': dt}})
    f += glossary_findings(src, tgt, src_lang, tgt_lang, entries)
    return f


# ---- Level 3 ---------------------------------------------------------------------------------------------------------
def _parts(text, pmap_hits, qs, found):
    """Split a segment into obligation parts: sentences, then before a party mention that follows an amount, else
    between consecutive obligation cues."""
    spans, pos = [], 0
    for m in re.finditer(r'(?<=[.;])\s+(?=\S)|\n', text):
        spans.append((pos, m.start()))
        pos = m.end()
    spans.append((pos, len(text)))
    out = []
    for a, b in spans:
        if b <= a:
            continue
        ps = [p for p in pmap_hits if a <= p[0] < b]
        cuts = [ps[k][0] for k in range(1, len(ps)) if any(ps[k - 1][0] < q[0] < ps[k][0] for q in qs)]
        if not cuts:
            cs = [c for c in found if c[0] in ('duty', 'perm', 'prohib') and a <= c[1] < b]
            for k in range(1, len(cs)):
                seg = text[cs[k - 1][2]:cs[k][1]]
                m = list(re.finditer(r'[,;]|\band\b|\sו(?=[֐-׿])', seg))
                cuts.append(cs[k - 1][2] + (m[-1].start() if m else len(seg) // 2))
        edges = [a] + sorted(set(cuts)) + [b]
        out += [(edges[i], edges[i + 1]) for i in range(len(edges) - 1) if edges[i + 1] > edges[i]]
    return out


def obligation_view(text, pmap):
    found = _scan(text)
    hits = find_parties(text, pmap)
    qs = quants(text)
    parts = []
    for a, b in _parts(text, hits, qs, found):
        ps = [p for p in hits if a <= p[0] < b]
        cues = [c for c in found if c[0] in ('duty', 'perm', 'prohib') and a <= c[1] < b]
        seg = text[a:b]
        obligor, conf = None, 'none'
        passive = [p for p in ps if PASSIVE_BY.search(text[max(a, p[0] - 14):p[0]])]
        if passive:
            obligor, conf = passive[0][2], 'high'
        elif cues:
            c0 = cues[0]
            before = [p for p in ps if p[0] < c0[2]]
            if before:
                obligor = before[-1][2]
                conf = 'high' if len({p[2] for p in before}) == 1 else 'low'
            elif ps:
                obligor, conf = ps[0][2], 'low'
        elif ps:
            obligor = ps[0][2]
            lead = len(re.match(r'^[^A-Za-z֐-׿]*', text[a:b]).group(0))
            conf = 'high' if ps[0][0] - a - lead <= 25 else 'low'
        parts.append({'text': seg.strip(), 'quants': [q[2] for q in qs if a <= q[0] < b], 'obligor': obligor,
                      'confidence': conf, 'passive': bool(passive), 'cues': [c[0] for c in cues]})
    cls = sorted({c[0] for c in found if c[0] in ('duty', 'perm', 'prohib')})
    return {'classes': cls, 'neg': sum(1 for c in found if c[0] == 'prohib') + sum(1 for c in found if c[0] == 'neg'),
            'exc': sum(1 for c in found if c[0] == 'exc'), 'cond': sum(1 for c in found if c[0] == 'cond'),
            'durations': sorted(d[2] for d in durations(text)), 'remedies': _cats(REMEDIES, text),
            'actions': _cats(ACTIONS, text), 'refs': sorted(refs_of(text)), 'parts': parts}


def _diff(a, b):
    return multiset_diff(a, b)


def level3_pair(src, tgt, pmap, tgt_lang):
    """Findings of severity 'error' (mechanically certain enough to reject) or 'review' (goes to the verifier)."""
    S, T = obligation_view(src, pmap), obligation_view(tgt, pmap)
    f = []

    def add(code, sev, detail=''):
        f.append({'type': code, 'severity': sev, 'detail': detail})
    ss, ts = set(S['classes']), set(T['classes'])
    if ss and ts and ss != ts:
        if ('perm' in ts) != ('perm' in ss):
            add('modality_changed', 'error', 'source %s -> target %s (duty/permission differ)' % (sorted(ss), sorted(ts)))
        elif ('prohib' in ts) == ('prohib' in ss):
            add('modality_changed', 'review', 'source %s -> target %s' % (sorted(ss), sorted(ts)))
    elif ss and not ts and not (tgt_lang == 'he' and ss == {'duty'}):
        add('modality_not_expressed', 'review', 'source %s, no explicit modal marker in the target' % sorted(ss))
    elif ts and not ss and 'perm' in ts:
        add('permission_added', 'review', 'the target says may/רשאי; the source has no explicit modal')
    if S['neg'] and not T['neg']:
        add('negation_dropped', 'error', 'the source negates (%d), the target does not' % S['neg'])
    elif T['neg'] and not S['neg']:
        add('negation_added', 'error', 'the target negates (%d), the source does not' % T['neg'])
    elif S['neg'] != T['neg'] and (S['neg'] - T['neg']) % 2:
        add('negation_parity', 'review', 'negations: source %d, target %d' % (S['neg'], T['neg']))
    if S['exc'] and not T['exc']:
        add('exception_dropped', 'error', 'the source has %d exception marker(s) (except/unless/למעט...), the target none' % S['exc'])
    elif T['exc'] and not S['exc']:
        add('exception_added', 'error', 'the target has %d exception marker(s), the source none' % T['exc'])
    elif S['exc'] != T['exc']:
        add('exception_count', 'review', 'exception markers: source %d, target %d' % (S['exc'], T['exc']))
    if bool(S['cond']) != bool(T['cond']):
        add('trigger_not_expressed' if S['cond'] else 'trigger_added', 'review',
            'condition/trigger wording present in the %s only' % ('source' if S['cond'] else 'target'))
    miss, extra = _diff(S['durations'], T['durations'])
    if miss or extra:
        add('deadline_changed', 'error', {'missing_in_target': miss, 'extra_in_target': extra})
    miss, extra = _diff(S['refs'], T['refs'])
    if miss or extra:
        add('cross_reference_changed', 'error', {'missing_in_target': miss, 'extra_in_target': extra})
    rs, rt = set(S['remedies']), set(T['remedies'])
    if rs != rt:
        add('remedy_scope_differs', 'review', {'only_in_source': sorted(rs - rt), 'only_in_target': sorted(rt - rs)})
    if S['actions'] and T['actions'] and not set(S['actions']) & set(T['actions']):
        add('action_differs', 'review', {'source': S['actions'], 'target': T['actions']})
    # amounts and parties per obligation
    sp, tp = S['parts'], T['parts']
    if len(sp) != len(tp):
        if sum(1 for p in sp + tp if p['quants'] or p['obligor']) > 2 and (len(sp) > 1 or len(tp) > 1):
            add('clause_structure_differs', 'review', 'source %d obligation parts, target %d' % (len(sp), len(tp)))
    else:
        for i, (a, b) in enumerate(zip(sp, tp), 1):
            if a['quants'] != b['quants'] and len(sp) > 1:
                whole = sorted(x for p in sp for x in p['quants']) == sorted(x for p in tp for x in p['quants'])
                if whole:
                    add('amounts_swapped', 'error', 'obligation %d: source %s, target %s (all values preserved, '
                        'attached to the wrong obligation)' % (i, a['quants'], b['quants']))
            if a['obligor'] and b['obligor'] and a['obligor'] != b['obligor']:
                sev = 'error' if (a['confidence'] == b['confidence'] == 'high') else 'review'
                add('obligor_changed', sev, 'obligation %d: source obligor %s, target obligor %s' % (i, a['obligor'], b['obligor']))
            elif bool(a['obligor']) != bool(b['obligor']):
                add('obligor_not_identified', 'review', 'obligation %d: party named in only one side' % i)
    return f, S, T


def view_has_cues(v):
    return bool(v['classes'] or v['neg'] or v['exc'] or v['cond'] or v['durations'] or v['remedies'] or
                any(p['obligor'] for p in v['parts']))


# ---- Level 1 + structure + orchestration -------------------------------------------------------------------------------
def _norm_ws(t):
    return re.sub(r'\s+', ' ', t or '').strip()


def _has_letters(t):
    return bool(re.search(r'[A-Za-z֐-׿]', t))


def level1(man, src_path, tgt_path):
    """(coverage dict, per-id source dict or None, not_checked list)."""
    F, gaps, notchecked, notes = [], [], [], []

    def err(code, detail, sid=None):
        F.append({'code': code, 'id': sid, 'detail': detail})
    if man.get('manifest_schema') != MANIFEST_SCHEMA:
        err('MANIFEST_INVALID', 'manifest_schema must be %s' % MANIFEST_SCHEMA)
    segs = man.get('segments') or []
    sha = hashlib.sha256(open(src_path, 'rb').read()).hexdigest()
    if man.get('source_sha256') != sha:
        err('SOURCE_CHANGED', 'the source file is not the version the manifest was made from (manifest %s, file %s)' % (
            (man.get('source_sha256') or '')[:12], sha[:12]))
    seen, ids = set(), {}
    for sg in segs:
        k = (sg.get('part'), sg.get('index'))
        if sg.get('id') in ids or k in seen:
            err('DUPLICATE_SEGMENT', 'the segment appears twice in the manifest', sg.get('id'))
        ids[sg.get('id')] = sg
        seen.add(k)
    src_by_id = None
    kind = sniff(src_path)
    if kind in ('docx', 'pdf'):
        try:
            ssegs, info = collect(src_path)
            src_by_id = {s['id']: s for s in ssegs}
            for sid, s in src_by_id.items():
                if sid not in ids:
                    err('MISSING_SEGMENT', 'a segment of the source (%s) is not in the manifest: %s' % (s['kind'], s['source'][:50]), sid)
            tc = man.get('tracked_changes')
            if not isinstance(tc, dict) or 'layer' not in tc:
                err('TRACKED_CHANGES_NOT_RECORDED', 'the manifest does not record the tracked-changes layer')
            else:
                a, b = info['tracked_changes'], tc
                if (a['insertions'], a['deletions'], a['moves']) != (b.get('insertions'), b.get('deletions'), b.get('moves')):
                    err('SOURCE_CHANGED', 'tracked changes differ from the manifest (source %s, manifest %s)' % (
                        {k: a[k] for k in ('insertions', 'deletions', 'moves')}, {k: b.get(k) for k in ('insertions', 'deletions', 'moves')}))
                if a['insertions'] or a['deletions'] or a['moves']:
                    notes.append('The source has a tracked-changes layer (%d insertions, %d deletions, %d moves): the '
                                 'translation covers the text with insertions shown and deletions omitted.' % (
                                     a['insertions'], a['deletions'], a['moves']))
        except ImportError as e:
            notchecked.append('source re-extraction (a required library is missing: %s)' % e)
    else:
        notchecked.append('source re-extraction (the source is a plain-text file)')
    by_kind = {}
    for sg in segs:
        sid, k, src = sg.get('id'), sg.get('kind') or 'body', sg.get('source') or ''
        row = by_kind.setdefault(k, {'segments': 0, 'translated': 0, 'untranslated_with_reason': 0})
        row['segments'] += 1
        s0 = src_by_id.get(sid) if src_by_id is not None else None
        if k == 'scanned':
            if not sg.get('source_confirmed'):
                gaps.append({'code': 'SCANNED_SEGMENT_UNCONFIRMED', 'id': sid, 'kind': k,
                             'detail': 'text read from an image is not marked source_confirmed'})
            notchecked.append('scanned text %s against the image (judgement step)' % sid)
        elif src_by_id is not None:
            if s0 is None:
                err('EXTRA_SEGMENT', 'the manifest has a segment that is not in the source', sid)
            elif _norm_ws(s0['source']) != _norm_ws(src) or seg_hash(s0['source']) != sg.get('source_hash'):
                err('SOURCE_CHANGED_SEGMENT', 'the source text of this segment is not what was translated', sid)
        tg, rs = _norm_ws(sg.get('target')), _norm_ws(sg.get('not_translated_reason'))
        if tg and rs:
            err('AMBIGUOUS_SEGMENT', 'has both a target and a not_translated_reason', sid)
        elif not tg and not rs:
            err('MISSING_TARGET', 'no target and no stated reason: %s' % src[:50], sid)
        elif rs:
            row['untranslated_with_reason'] += 1
            if not (rs.lower().startswith('immaterial:') and not _has_letters(src)):
                gaps.append({'code': 'UNTRANSLATED_SEGMENT', 'id': sid, 'kind': k, 'reason': rs, 'source': src[:80]})
        else:
            row['translated'] += 1
    langs = {}
    allsrc = ' '.join(s.get('source', '') for s in segs)
    changed = [s for s in segs if _norm_ws(s.get('target')) and _norm_ws(s.get('target')) != _norm_ws(s.get('source'))]
    sl = target_lang(allsrc) if allsrc.strip() else ''
    tl = target_lang(' '.join(s.get('target', '') for s in changed)) if changed else ''
    langs.update(source=sl, target=tl)
    for sg in segs:
        tg, src = _norm_ws(sg.get('target')), _norm_ws(sg.get('source'))
        if tg and src == tg and sl != tl and len(src.split()) >= 3 and (HEB.search(src) if sl == 'he' else LAT.search(src)):
            err('UNTRANSLATED_COPY', 'the target is the source text copied unchanged and not marked as untranslated', sg.get('id'))
    groups = {}
    for sg in segs:
        tg = _norm_ws(sg.get('target')).lower()
        if len(tg) >= 25:
            groups.setdefault(tg, []).append(sg)
    for tg, g in groups.items():
        if len({x.get('source_hash') for x in g}) > 1:
            err('DUPLICATE_TARGET', 'one target text is used for %d different source segments: %s' % (
                len(g), [x.get('id') for x in g][:6]), g[0].get('id'))
    if not _norm_ws(man.get('glossary_version')):
        err('GLOSSARY_VERSION_NOT_RECORDED', 'the manifest does not record the glossary id/version (write "none" when no glossary applies)')
    if man.get('scanned_text_unread'):
        gaps.append({'code': 'SCANNED_TEXT_UNREAD', 'id': None, 'kind': 'scanned',
                     'detail': 'the source has pages with no text layer that were not read'})
    notes_by = {k: by_kind.get(k, {'segments': 0, 'translated': 0, 'untranslated_with_reason': 0})
                for k in ('footnote', 'endnote', 'comment', 'table', 'heading', 'annex', 'header', 'footer')}
    status = 'complete' if not F and not gaps else 'incomplete'
    cov = {'status': status, 'may_present_as_complete': status == 'complete', 'findings': F, 'material_gaps': gaps,
           'by_kind': by_kind, 'footnotes': notes_by['footnote'], 'endnotes': notes_by['endnote'],
           'comments': notes_by['comment'], 'notes': notes, 'languages': langs,
           'rule': 'A segment with no target needs a stated reason; any such segment except a source with no words '
                   '("immaterial:") is a material gap and blocks presenting the translation as complete.'}
    return cov, src_by_id, notchecked


def structure(man, src_path, tgt_path):
    F, warn, notchecked = [], [], []
    ks, kt = sniff(src_path), sniff(tgt_path)
    if not (ks == 'docx' and kt == 'docx'):
        notchecked.append('built file compared with the manifest, and fields/bookmarks/references attachment '
                          '(needs a Word source and a Word target)')
        return {'status': 'not_checked', 'findings': F, 'warnings': warn}, notchecked
    try:
        tsegs, _ = collect(tgt_path)
    except ImportError as e:
        notchecked.append('built file comparison (a required library is missing: %s)' % e)
        return {'status': 'not_checked', 'findings': F, 'warnings': warn}, notchecked
    tby = {s['id']: s for s in tsegs}
    for sg in man.get('segments') or []:
        sid = sg.get('id')
        t = tby.get(sid)
        if t is None:
            if sg.get('kind') != 'scanned':
                F.append({'code': 'BUILT_FILE_MISSING_SEGMENT', 'id': sid, 'detail': 'the built file has no text at this place'})
            continue
        want = _norm_ws(sg.get('target')) or _norm_ws(sg.get('source'))
        if _norm_ws(t['source']) != want:
            F.append({'code': 'BUILT_FILE_DIFFERS_FROM_MANIFEST', 'id': sid,
                      'detail': 'the text in the built file is not the manifest target'})
        a, b = (sg.get('features') or {}), (t.get('features') or {})
        for k in ('fields', 'bookmarks', 'hyperlinks', 'note_refs', 'comment_refs', 'drawings'):
            if a.get(k, 0) != b.get(k, 0):
                F.append({'code': 'ATTACHMENT_LOST', 'id': sid, 'detail': '%s: source %s, built %s' % (k, a.get(k, 0), b.get(k, 0))})
        if a.get('emphasis_runs', 0) != b.get('emphasis_runs', 0) and a.get('emphasis_runs', 0):
            warn.append({'code': 'EMPHASIS_CHANGED', 'id': sid,
                         'detail': 'emphasised runs: source %s, built %s (judgement: does the emphasis carry meaning?)' % (
                             a.get('emphasis_runs'), b.get('emphasis_runs'))})
    return {'status': 'fail' if F else 'pass', 'findings': F, 'warnings': warn}, notchecked


def run_manifest_checks(man, src_path, tgt_path, glossary=None, parties=None, verifier=None):
    gl_version, entries = glossary if glossary else ('', [])
    pmap = load_party_map(entries, list(parties or []) + list(man.get('parties') or []))
    cov, src_by_id, nc = level1(man, src_path, tgt_path)
    st, nc2 = structure(man, src_path, tgt_path)
    if gl_version and man.get('glossary_version') and gl_version != man.get('glossary_version'):
        cov['findings'].append({'code': 'GLOSSARY_VERSION_DIFFERS', 'id': None,
                                'detail': 'glossary file %s, manifest %s' % (gl_version, man.get('glossary_version'))})
        cov['status'], cov['may_present_as_complete'] = 'incomplete', False
    sl, tl = cov['languages']['source'], cov['languages']['target']
    l2, l3, queue, cue_free = [], [], [], 0
    if sl and tl and sl != tl:
        for sg in man.get('segments') or []:
            src, tgt = _norm_ws(sg.get('source')), _norm_ws(sg.get('target'))
            if not src or not tgt:
                continue
            sid = sg.get('id')
            for x in level2_pair(src, tgt, sl, tl, entries):
                l2.append(dict(x, id=sid, kind=sg.get('kind')))
            f3, S, T = level3_pair(src, tgt, pmap, tl)
            for x in f3:
                l3.append(dict(x, id=sid, kind=sg.get('kind')))
            ids_flag = [x['type'] for x in l2 + l3 if x['id'] == sid]
            if view_has_cues(S) or view_has_cues(T) or ids_flag:
                queue.append({'id': sid, 'kind': sg.get('kind'), 'source': src, 'target': tgt,
                              'flags': ids_flag, 'source_cues': {k: S[k] for k in ('classes', 'neg', 'exc', 'cond', 'durations', 'remedies', 'actions', 'refs')},
                              'target_cues': {k: T[k] for k in ('classes', 'neg', 'exc', 'cond', 'durations', 'remedies', 'actions', 'refs')}})
            else:
                cue_free += 1
        queue.sort(key=lambda q: 0 if q['flags'] else 1)
    else:
        nc.append('per-segment checks (the source and target languages could not be told apart: %r/%r)' % (sl, tl))
    err2 = [x for x in l2 if x['severity'] == 'error']
    err3 = [x for x in l3 if x['severity'] == 'error']
    rev = [x for x in l2 + l3 if x['severity'] == 'review']
    ver = {'status': 'not_performed', 'findings': [], 'reviewed': 0}
    qids = {q['id'] for q in queue}
    if verifier:
        ver['source_sha256_matches'] = verifier.get('source_sha256') == hashlib.sha256(open(src_path, 'rb').read()).hexdigest()
        rv = set(verifier.get('segments_reviewed') or [])
        ver.update(verifier=verifier.get('verifier'), reviewed=len(rv & qids), unreviewed=sorted(qids - rv)[:50],
                   findings=verifier.get('findings') or [])
        ver['status'] = ('performed' if ver['source_sha256_matches'] and not (qids - rv) else
                         'stale_source_version' if not ver['source_sha256_matches'] else 'partial')
    blocking = [x for x in ver['findings'] if x.get('severity') == 'error' and not x.get('resolved')]
    mech_ok = not err2 and not err3
    return {
        'coverage': cov,
        'structural_integrity': st,
        'segment_checks': {
            'level2_numbers_dates_terms': {'status': 'fail' if err2 else 'pass', 'errors': err2,
                                           'review': [x for x in l2 if x['severity'] == 'review']},
            'level3_obligations': {'status': 'fail' if err3 else 'pass', 'errors': err3,
                                   'review': [x for x in l3 if x['severity'] == 'review']},
            'segments_without_any_obligation_cue': cue_free},
        'linguistic_legal_review': {
            'status': ver['status'], 'performed_by': 'clean-context verifier read' if verifier else None,
            'mechanical_checks': MECHANICAL_CHECKS, 'judgement_checks': JUDGEMENT_CHECKS,
            'items_for_review': len(queue), 'review_flags': len(rev), 'queue': queue, 'verifier': ver,
            'note': 'The queue is the input of the verifier: every segment with an obligation cue or a flag, source and '
                    'target side by side, flagged ones first. The verifier answers per segment id, without the '
                    'translator\'s reasoning.'},
        'not_checked': sorted(set(nc + nc2) | {'obligations written without an explicit marker (for example a bare '
                                               'Hebrew future verb) are not detected mechanically'}),
        'summary': {'coverage': cov['status'], 'structure': st['status'], 'mechanical_errors': len(err2) + len(err3),
                    'review_flags': len(rev), 'review': ver['status'], 'verifier_blocking': len(blocking)},
        'pass': cov['status'] == 'complete' and st['status'] != 'fail' and mech_ok and not blocking,
        'may_present_as_checked_and_complete': (cov['status'] == 'complete' and st['status'] == 'pass' and mech_ok and
                                                ver['status'] == 'performed' and not blocking),
    }


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('source'); ap.add_argument('target'); ap.add_argument('--out')
    ap.add_argument('--out-dir', help='without --out: the report is written here under the canonical name '
                                      'translation-integrity-<id>-<en|he>.json')
    ap.add_argument('--id', help='with --out-dir: transaction_id, or a short Latin id of the document '
                                 '(default: the source file name)')
    ap.add_argument('--manifest', help='segments.json made by build_translation_docx.py extract and filled by the '
                                       'translator: turns on the per-segment checks (coverage, numbers/terms, obligations)')
    ap.add_argument('--glossary', help='the approved glossary JSON (מילון-מונחים.json): per-segment defined-term check')
    ap.add_argument('--parties', help='JSON list of party roles [{"id","he":[..],"en":[..]}] for the obligor check')
    ap.add_argument('--verifier-result', help='JSON written by the clean-context verifier read: source_sha256, '
                                              'segments_reviewed, findings')
    ap.add_argument('--review-queue-out', help='write the verifier input (segment pairs with cues, flagged first) here')
    args=ap.parse_args()
    # A damaged, old (DOC), password-protected or Strict Word file: a bilingual message and exit 2, not a traceback
    # The kind by content, not by name: a PDF (also one named .docx) is read as a PDF, never reported as a damaged
    # Word file; an old .doc or a damaged file gets its own message
    from build_translation_docx import sniff, KIND_MSG
    for p in (args.source, args.target):
        kind=sniff(p)
        if kind in KIND_MSG:
            print(KIND_MSG[kind] % (Path(p).name, Path(p).name)); raise SystemExit(1 if kind=='missing' else 2)
        if kind=='docx':
            ok,msg,code=load_docx_or_explain(p, loader=False)
            if ok is None:
                print(msg); raise SystemExit(code)
    ss,ts=[],[]
    target_text=text_of(args.target,ts)
    s=tokens(text_of(args.source,ss)); t=tokens(target_text)
    report={'schema':REPORT_SCHEMA,'source_version':{'file':Path(args.source).name,
            'sha256':hashlib.sha256(open(args.source,'rb').read()).hexdigest()},
            'checks':{},'pass':True,'ignored_stamp_paragraphs':{'source':ss,'target':ts},
            'disclaimer':NEVER_CLAIMED,'legal_validity':'not_assessed'}
    for key in s:
        missing,extra=multiset_diff(s[key],t[key])
        report['checks'][key]={'missing_in_target':missing,'extra_in_target':extra}
        if missing or extra: report['pass']=False
    # Headers and footers: the same numbers, amounts and structure as the source, and the target's direction.
    # A header left in the source language, or left RTL in an English translation, fails here.
    shf, thf = hf_paragraphs(args.source), hf_paragraphs(args.target)
    hs, ht = tokens('\n'.join(x[1] for x in shf)), tokens('\n'.join(x[1] for x in thf))
    hf = {}
    for key in ('numeric_tokens', 'currency_tokens'):
        missing, extra = multiset_diff(hs[key], ht[key])
        hf[key] = {'missing_in_target': missing, 'extra_in_target': extra}
        if missing or extra: report['pass'] = False
    tl = target_lang(target_text)
    wrong_dir = [x[1][:60] for x in thf if (tl == 'he') != x[2] and (tl == 'he' or not HEB.search(x[1]))]
    src_lang = target_lang(text_of(args.source))
    untranslated = [x[1][:60] for x in thf if src_lang != tl and ((src_lang == 'he' and HEB.search(x[1]) and
                    not LAT.search(x[1])) or (src_lang == 'en' and LAT.search(x[1]) and not HEB.search(x[1])
                    and len(LAT.findall(x[1])) > 8))]
    hf['wrong_direction'] = wrong_dir
    hf['untranslated'] = untranslated
    if wrong_dir or untranslated: report['pass'] = False
    report['checks']['headers_footers'] = hf
    if args.manifest:
        try:
            man=load_json(args.manifest)
            gl=load_glossary(args.glossary) if args.glossary else None
            pt=load_json(args.parties) if args.parties else None
            vr=load_json(args.verifier_result) if args.verifier_result else None
        except (OSError, ValueError) as e:
            print('refused: cannot read a --manifest/--glossary/--parties/--verifier-result file (%s)' % type(e).__name__, file=sys.stderr)
            raise SystemExit(2)
        m=run_manifest_checks(man,args.source,args.target,gl,pt,vr)
        if not args.glossary:
            m['not_checked'].append('defined terms against the glossary (no --glossary file was supplied)')
        report['manifest_mode']=True
        report['manifest']={'file':Path(args.manifest).name,'glossary_version':man.get('glossary_version'),
                            'tracked_changes':man.get('tracked_changes'),'parts':man.get('parts'),
                            'segments':len(man.get('segments') or [])}
        for k in ('coverage','structural_integrity','segment_checks','linguistic_legal_review','not_checked','summary',
                  'may_present_as_checked_and_complete'):
            report[k]=m[k]
        report['pass']=report['pass'] and m['pass']
        if args.review_queue_out:
            q=os.path.abspath(args.review_queue_out)
            try:
                q=guard_out(q, inputs=[args.source, args.target, args.manifest])
            except OutputRefused as e:
                print('refused: %s' % e, file=sys.stderr); raise SystemExit(2)
            Path(q).write_text(json.dumps({'source_version':report['source_version'],'instructions':
                'Read each pair cold, without the reasoning of the translation. Per segment id say whether the target carries '
                'the same obligor, action, duty-vs-permission, negation, amount, trigger, deadline, exception and remedy as '
                'the source. Return JSON {verifier, source_sha256, segments_reviewed:[ids], findings:[{id,type,severity,note}]}. '
                'Do not assess legal validity.','queue':m['linguistic_legal_review']['queue']},
                ensure_ascii=False,indent=1),encoding='utf-8')
    else:
        w=('No --manifest was supplied: only the legacy global counts (numbers, currencies, section numbers, headers and '
           'footers) were checked. Coverage, per-segment checks and obligation checks were NOT checked.'+chr(10)+
           'לא סופק --manifest: נבדקו רק הספירות הגלובליות הישנות. כיסוי, בדיקות לפי קטע ובדיקת התחייבויות לא נבדקו.')
        report['manifest_mode']=False
        report['warnings']=['NO_MANIFEST: '+w]
        report['coverage']={'status':'not_checked','may_present_as_complete':False}
        print('warning: '+w, file=sys.stderr)
    text=json.dumps(report,ensure_ascii=False,indent=2)
    out=args.out
    if not out and args.out_dir:
        out=unique(os.path.join(args.out_dir, canonical_name(args.id or Path(args.source).stem,
                                                             target_lang(target_text))))
    if out:
        # The report is never written over the source or the translation, or over an existing document
        try:
            out=guard_out(out, inputs=[args.source, args.target])
        except OutputRefused as e:
            print('refused: %s' % e, file=sys.stderr); raise SystemExit(2)
        if os.path.dirname(out): os.makedirs(os.path.dirname(out), exist_ok=True)
        Path(out).write_text(text+'\n',encoding='utf-8')
    print(text)
    raise SystemExit(0 if report['pass'] else 1)
if __name__=='__main__': main()
