# -*- coding: utf-8 -*-
"""playbook/market_counts.py: אותם מספרים של מחקר השוק בכל משטח: המודל, ה-Word, ה-Workspace והצ'אט.

הבעיה (סבב 3, ממצא 9 של מנכ"ל ארגון היועמ"שים): השורה הראשונה של הפלייבוק, של ה-Workspace ושל הודעת
המסירה אמרה "נבנה כולו לפי 10 הסכמים הדדיים שפורסמו ברשת, מ-10 גופים", ובאותו מסמך: "נמצאו 14, נפתחו 12,
נקראו 10, נספרו 6 (מ-6 משפחות תבנית)". ארבעה מהעשרה לא נספרו כלל.

הכלל: המשפט נגזר מ-market_research.counts (found, opened, read, counted), ולא נכתב ידנית. כל מספר שצמוד
ל"הסכמים", "גופים", "משפחות" או "מסמכים" הוא מספר המשפחות שנספרו, אלא אם כתוב לידו במפורש
"שנקראו", "שנמצאו" או "שנפתחו", ואז הוא המספר המתאים. "<N> הסכמים שלכם" הם הסכמי החברה, ואינם נבדקים כאן.
count_claims() מחזיר כל סתירה.
"""
import re

_NOUN = r'(הסכמים|גופים|משפחות(?:\s+תבנית)?|מסמכים)'
_CLAIM = re.compile(r'(?:מ-)?(\d+)\s+' + _NOUN + r'(?=(?P<tail>[^.;:()\d]{0,40}))')
_VERB = re.compile(r'(נמצאו|נפתחו|נקראו|נספרו)\s+(\d+)')
_VERB_KEY = {'נמצאו': 'found', 'נפתחו': 'opened', 'נקראו': 'read', 'נספרו': 'counted'}
# יחיד (1.2.0): "משפחת תבנית אחת", "הסכם אחד", "גוף אחד", "מסמך אחד" הם הטענה 1
_ONE = re.compile(r'(משפחת(?:\s+תבנית)?|הסכם|גוף|מסמך)\s+(?:אחת|אחד)(?=(?P<tail>[^.;:()\d]{0,40}))')


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


def basis_sentence(model, legal_sources=None):
    """השורה האחת שמתארת על מה הפלייבוק נשען, מהספירה. legal_sources: מספר עובדות הדין שנקראו.
    1.2.0: יחיד ורבים ("משפחת תבנית אחת", ולא "1 משפחות")."""
    c = counts(model)
    if 'counted' not in c:
        return ''
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
        if 'שלכם' in m.group('tail')[:12]:
            continue                      # "3 הסכמים שלכם": ההסכמים של החברה, לא מחקר השוק
        key = _expected(m.group('tail'), c)
        want = c.get(key)
        if want is not None and int(m.group(1)) != want:
            out.append('"%s": %s, ובספירה %s=%d' % (m.group(0).strip()[:60], m.group(1), key, want))
    for m in _ONE.finditer(text):
        if 'שלכם' in m.group('tail')[:12]:
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
    return out
