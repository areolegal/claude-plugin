# -*- coding: utf-8 -*-
"""playbook/market_counts.py: אותם מספרים של מחקר השוק בכל משטח: המודל, ה-Word, ה-Workspace והצ'אט.

הבעיה: השורה הראשונה של הפלייבוק, של ה-Workspace ושל הודעת
המסירה אמרה "נבנה כולו לפי 10 הסכמים הדדיים שפורסמו ברשת, מ-10 גופים", ובאותו מסמך: "נמצאו 14, נפתחו 12,
נקראו 10, נספרו 6 (מ-6 משפחות תבנית)". ארבעה מהעשרה לא נספרו כלל.

הכלל: המשפט נגזר מ-market_research.counts (found, opened, read, counted), ולא נכתב ידנית. כל מספר שצמוד
ל"הסכמים", "גופים", "משפחות" או "מסמכים" הוא מספר המשפחות שנספרו, אלא אם כתוב לידו במפורש
"שנקראו", "שנמצאו" או "שנפתחו", ואז הוא המספר המתאים. "<N> הסכמים שלכם" הם הסכמי החברה, ואינם נבדקים כאן.
count_claims() מחזיר כל סתירה.

בתוצר באנגלית אותו משפט נגזר באנגלית (basis_sentence(..., lang='en')), ו-count_claims בודק גם טענות באנגלית:
"<N> agreements|bodies|families|template families|documents", ו-"found|opened|read|counted <N>". "<N> company
agreements" ו-"<N> agreements of the company" הם הסכמי החברה, ואינם נבדקים כאן.
"""
import re

_NOUN = r'(הסכמים|גופים|משפחות(?:\s+תבנית)?|מסמכים)'
# טענה היא מספר ושם עצם באותה שורה. הטקסט של ה-Word מחובר
# פסקה-פסקה ב-"\n", ו-`\s+` חיבר את "4" שבסוף שורה בטבלה ל"מסמכים" שבראש השורה הבאה
_CLAIM = re.compile(r'(?:מ-)?(\d+)[^\S\n]+' + _NOUN + r'(?=(?P<tail>[^.;:()\d\n]{0,40}))')
_VERB = re.compile(r'(נמצאו|נפתחו|נקראו|נספרו)[^\S\n]+(\d+)')
# "<N> הסכמים שלכם" ו"<N> הסכמים של החברה" הם הסכמי החברה, ולא מחקר השוק. "של החברה" הוא הנוסח של
# שורת הבסיס במפרט ("נבנה מ-<N> הסכמים של החברה"), ובלעדיו כל פלייבוק בשילוב מחקר שוק נכשל על השער שלו
_OWN = ('שלכם', 'של החברה')
_VERB_KEY = {'נמצאו': 'found', 'נפתחו': 'opened', 'נקראו': 'read', 'נספרו': 'counted'}
# יחיד (1.2.0): "משפחת תבנית אחת", "הסכם אחד", "גוף אחד", "מסמך אחד" הם הטענה 1
_ONE = re.compile(r'(משפחת(?:\s+תבנית)?|הסכם|גוף|מסמך)\s+(?:אחת|אחד)(?=(?P<tail>[^.;:()\d\n]{0,40}))')


_NOUN_EN = r'(agreements|bodies|(?:template\s+)?families|documents)'
_CLAIM_EN = re.compile(r'(?<![\w.])(\d+)[^\S\n]+' + _NOUN_EN + r'(?=(?P<tail>[^.;:()\d\n]{0,40}))', re.I)
_VERB_EN = re.compile(r'\b(found|opened|read|counted)[^\S\n]+(\d+)\b', re.I)
_OWN_EN = ('of the company', 'your', "company's")
_ONE_EN = re.compile(r'\bone\s+(template\s+family|family|agreement|body|document)\b(?=(?P<tail>[^.;:()\d\n]{0,40}))',
                     re.I)


def counts(model):
    c = (model.get('market_research') or {}).get('counts') or {}
    return {k: c.get(k) for k in ('found', 'opened', 'read', 'counted') if isinstance(c.get(k), int)}


def _families(n):
    if n == 1:
        return 'משפחת תבנית אחת של הסכמים שפורסמו ברשת ונספרה'
    return '%d משפחות תבנית של הסכמים שפורסמו ברשת ונספרו' % n


def _docs_read(n):
    return 'מתוך מסמך אחד שנקרא' if n == 1 else 'מתוך %d מסמכים שנקראו' % n


def _legal(n):
    return 'עובדת דין אחת ממקור רשמי' if n == 1 else '%d עובדות דין ממקור רשמי' % n


def _families_en(n):
    if n == 1:
        return 'one template family of agreements published online, which was counted'
    return '%d template families of agreements published online, which were counted' % n


def _docs_read_en(n):
    return 'out of one document read' if n == 1 else 'out of %d documents read' % n


def _legal_en(n):
    return 'one legal fact from an official source' if n == 1 else '%d legal facts from official sources' % n


def basis_sentence(model, legal_sources=None, lang='he'):
    """השורה האחת שמתארת על מה הפלייבוק נשען, מהספירה. legal_sources: מספר עובדות הדין שנקראו.
    1.2.0: יחיד ורבים ("משפחת תבנית אחת", ולא "1 משפחות"). lang='en': אותו משפט באנגלית."""
    c = counts(model)
    if 'counted' not in c:
        return ''
    if lang == 'en':
        s = 'The playbook was built from %s' % _families_en(c['counted'])
        if c.get('read') is not None and c['read'] != c['counted']:
            s += ' (%s)' % _docs_read_en(c['read'])
        if legal_sources:
            s += ', and from %s' % _legal_en(legal_sources)
        return s + '.'
    s = 'הפלייבוק נבנה לפי %s' % _families(c['counted'])
    if c.get('read') is not None and c['read'] != c['counted']:
        s += ' (%s)' % _docs_read(c['read'])
    if legal_sources:
        s += ', ולפי %s' % _legal(legal_sources)
    return s + '.'


def _expected(tail, c):
    for word, key in (('נקראו', 'read'), ('נמצאו', 'found'), ('נפתחו', 'opened')):
        if word in tail:
            return key
    return 'counted'


def count_claims(text, model):
    """סתירות בין המספרים שבטקסט לבין market_research.counts. ריקה = עקבי."""
    c = counts(model)
    if not text or 'counted' not in c:
        return []
    out = []
    for m in _CLAIM.finditer(text):
        if any(w in m.group('tail')[:12] for w in _OWN):
            continue                      # "3 הסכמים שלכם": ההסכמים של החברה, לא מחקר השוק
        key = _expected(m.group('tail'), c)
        want = c.get(key)
        if want is not None and int(m.group(1)) != want:
            out.append('"%s": %s, ובספירה %s=%d' % (m.group(0).strip()[:60], m.group(1), key, want))
    for m in _ONE.finditer(text):
        if any(w in m.group('tail')[:12] for w in _OWN):
            continue
        key = 'read' if m.group(1) == 'מסמך' and 'שנקרא' in m.group('tail') else _expected(m.group('tail'), c)
        want = c.get(key)
        if want is not None and want != 1:
            out.append('"%s": 1, ובספירה %s=%d' % (m.group(0).strip()[:60], key, want))
    for m in _VERB.finditer(text):
        key = _VERB_KEY[m.group(1)]
        want = c.get(key)
        if want is not None and int(m.group(2)) != want:
            out.append('"%s": בספירה %s=%d' % (m.group(0), key, want))
    out += _count_claims_en(text, c)
    return out


def _expected_en(tail):
    t = tail.lower()
    for word, key in (('read', 'read'), ('found', 'found'), ('opened', 'opened')):
        if re.search(r'\b%s\b' % word, t):
            return key
    return 'counted'


def _count_claims_en(text, c):
    """אותה בדיקה לטענות באנגלית. "<N> company agreements" אינו נתפס כלל (company בין המספר לשם העצם), ו-"the
    company's <N> agreements" או "<N> agreements of the company" הם הסכמי החברה, ואינם מחקר השוק."""
    out = []
    for m in _CLAIM_EN.finditer(text):
        tail = m.group('tail')[:16].lower()
        head = text[max(0, m.start() - 12):m.start()].lower()
        if any(w in tail for w in _OWN_EN) or 'company' in head:
            continue
        key = _expected_en(m.group('tail'))
        want = c.get(key)
        if want is not None and int(m.group(1)) != want:
            out.append('"%s": %s, ובספירה %s=%d' % (m.group(0).strip()[:60], m.group(1), key, want))
    for m in _ONE_EN.finditer(text):
        tail = m.group('tail')[:16].lower()
        if any(w in tail for w in _OWN_EN):
            continue
        key = 'read' if m.group(1).lower() == 'document' and 'read' in tail else _expected_en(m.group('tail'))
        want = c.get(key)
        if want is not None and want != 1:
            out.append('"%s": 1, ובספירה %s=%d' % (m.group(0).strip()[:60], key, want))
    for m in _VERB_EN.finditer(text):
        key = m.group(1).lower()
        want = c.get(key)
        if want is not None and int(m.group(2)) != want:
            out.append('"%s": בספירה %s=%d' % (m.group(0), key, want))
    return out
