# -*- coding: utf-8 -*-
"""בדיקות כלל 2.22 ("נוסח שאנחנו כותבים אינו יוצר פער"), בעברית ובאנגלית, במודול משותף אחד
(מימוש ייחוס, הערות הנושא ונותן 4.9, שינוי 81; משמש גם את playbook/validate_model.py ואת risk/validate_register.py).

המודול כללי לכל סוג הסכם (שירותים, סודיות, SaaS ורישוי, אספקה ורכש, הפצה, שכירות, העסקה, מיקור חוץ, הלוואה).
הוא בודק רק מנגנונים שחלים בכל הסכם, ונשען על התפקיד של הסעיף (סיום, סודיות, תקרה, תשלום, מחיקה), ולא על
סוג ההסכם, על הצד או על עובדות של לקוחה. שיקול משפטי על סעיף מסוים בסוג הסכם מסוים שייך לפלייבוק של הלקוחה,
ולא לכאן (החלטה 22, כלל נוקשה 2.26). כלל 2.22 כולל רק את המחלקות האלה:

  GAP_DISPUTE_CARVEOUT            זכות סיום בעילת אי-תשלום: חריג מחלוקת שחל על סכום, מועד וקיזוז.
  GAP_TERMINATION_HANDOVER        זכות סיום בהתקשרות מתמשכת: חובת העברה מסודרת.
  GAP_CONFIDENTIALITY_EXCEPTIONS  חובת סודיות: גילוי לפי דין או רשות, יועצים ומבקרים, צד שלישי, פיתוח עצמאי.
  GAP_PAYMENT_WORDING             נוסח "בטוח" למועד תשלום נוקב מספר (המספר בא מהפלייבוק), ולעולם אינו מפנה
                                  ל"מועד המאוחר ביותר שהדין מתיר" או ל"לפי המוקדם".

    from common.gap_checks import check_wording, check_document
    check_wording(text, lang, topic=None, context=None) -> [{'code', 'message_he', 'span'}]
    check_document(accept_text, touched, lang, context=None) -> [{'code', 'message_he', 'span'}]

- check_wording בודק נוסח אחד (פסקה שהכנסנו, או נוסח ירוק או צהוב בפלייבוק). context['accept_text'] (ההסכם כולו
  בהטלת "קבל הכול", או כל נוסחי הפלייבוק יחד) משמש את הבדיקות שתלויות בשאר ההסכם. בלי context: מול הנוסח עצמו.
- check_document נשמר לממשק (בדיקות שחלות על ההסכם כולו). בכלל 2.22 הנוכחי אין מחלקה כזו, והוא מחזיר רשימה ריקה.
- topic (לא חובה): 'confidentiality' מפעיל את בדיקת החריגים גם בלי מילת החובה. כל ערך אחר אינו משנה דבר.
- context['waived']: קודים שהמשתמש הכריע במפורש לוותר עליהם (ויתור מכוון עם user_decision מפורש).
span הוא (start, end) בתוך text, או None. message_he תמיד בעברית.

Python 3, ספרייה סטנדרטית בלבד. בלי פנייה לרשת.
"""
import re

HEB = re.compile('[א-ת]')

# אוצר ביטויים לפי תפקיד הסעיף, בעברית ובאנגלית. אין כאן מונח של סוג הסכם מסוים.
P = {
    'he': {
        'terminate': r'לסיים|סיום|לבטל את ההסכם',
        'breach': r'הפרה|הפר',
        'payment': r'תשלום|לשלם',
        'dispute': r'חולק|במחלוקת|מחלוקת',
        'd_amount': r'סכום|חיוב|שיעור',
        'd_timing': r'מועד',
        'setoff': r'לקזז|קיזוז|קוזז',
        'term_right': r'רשאי לסיים|רשאי לבטל|יסתיים|סיום מיידי',
        'handover': r'העברה מסודרת|יעביר[^.\n]{0,40}(תוצרים|העבודה|המידע|החומרים|הנכס|המושכר|הציוד)|תקופת מעבר|'
                    r'חפיפה|השבת (המושכר|הנכס|הציוד|החומרים)|יחזיר[^.\n]{0,30}(המושכר|הנכס|הציוד)',
        'ongoing_ctx': r'שירותים|תוצרים|אספקה|יספק|המושכר|רישיון|תחזוקה|הפצה|העבודה',
        'conf': r'סודיות|בסוד|מידע סודי',
        'conf_duty': r'ישמור|לא יגלה|לא ימסור|לא יעביר|ישמרו',
        'law_exc': r'(לפי|על פי|מכוח) (כל )?דין|צו (של )?(בית משפט|שיפוטי)|רשות מוסמכת|דרישת רשות|רגולטור|רשות מפקחת',
        'adv_exc': r'יועצ(יו|יה|יהם|ים)[^.\n]{0,20}(המקצועיים|המשפטיים)|רואי? ה?חשבון|המבקר הפנימי|מבקר הפנים',
        'tp_exc': r'(התקבל|שקיבל|קיבל|שהגיע)[^.\n]{0,60}מצד שלישי',
        'indep': r'פותח[^.\n]{0,20}באופן עצמאי|פיתוח עצמאי|פיתח[^.\n]{0,20}באופן עצמאי',
        'pay_term': r'(ישולם|ישולמו|תשולם|משולמת|ישלם|התשלום|התמורה|דמי \S+)[^.\n]{0,80}(בתוך|תוך|מתום|ממועד|שוטף)',
        'pay_latest': r'המועד המאוחר ביותר|המועד המרבי|המועד המירבי|לפי המוקדם|לפי המאוחר',
        'days': r'\d+\s*(יום|ימים|ימי עסקים)|\[\s*\d+\s*\]\s*(יום|ימים|ימי עסקים)',
    },
    'en': {
        'terminate': r'terminat',
        'breach': r'breach',
        'payment': r'pay',
        'dispute': r'disput',
        'd_amount': r'amount|liability|quantum|sum',
        'd_timing': r'timing|due date|when due|time of payment',
        'setoff': r'set[- ]?off',
        'term_right': r'may terminate|right to terminate|immediate termination|terminate this agreement',
        'handover': r'hand ?over|transition (period|assistance|services)|orderly (transfer|transition)|'
                    r'deliver (all )?(work|deliverables|materials)|return (of )?the (premises|equipment|goods)|vacate',
        'ongoing_ctx': r'\bservices\b|deliverables|\bsupply\b|premises|licen[cs]e|maintenance|distribut|work product',
        'conf': r'Confidential Information|in confidence|confidential',
        'conf_duty': r'shall not (disclose|make any public|use)|shall (keep|hold)[^.\n]{0,40}confiden|'
                     r'(are|as|treat[^.\n]{0,30}as) Confidential Information',
        'law_exc': r'required by (applicable )?law|compelled[^.\n]{0,20}by law|court order|legal process|'
                   r'regulatory|supervisory authority|governmental authority|competent authority',
        'adv_exc': r'advis[eo]rs?|auditors?|accountants?',
        'tp_exc': r'(received|obtained|acquired)[^.\n]{0,80}from a third party|from a third party',
        'indep': r'independently developed|developed independently',
        'pay_term': r'(shall be paid|shall pay|payable|payment)[^.\n]{0,80}(within|net|from the end|after receipt|following)',
        'pay_latest': r'whichever is (earlier|later)|latest (date|time) permitted|maximum (period|term) permitted',
        'days': r'\d+\s*(calendar |business )?days|net\s*\d+',
    },
}

MSG = {
    'GAP_DISPUTE_CARVEOUT': 'זכות סיום בעילת אי-תשלום בלי חריג מחלוקת שחל על סכום, מועד וקיזוז',
    'GAP_TERMINATION_HANDOVER': 'זכות סיום בלי חובת חפיפה והעברה מסודרת',
    'GAP_CONFIDENTIALITY_EXCEPTIONS': 'חובת סודיות בלי החריגים שהחברה עצמה צריכה',
    'GAP_PAYMENT_WORDING': 'נוסח תשלום שאינו נוקב מספר ימים, או שמפנה למועד מרבי בדין',
}
DOCUMENT_CODES = ()
ALL_CODES = tuple(MSG)


def detect_lang(text):
    """'he' כשיש בטקסט לפחות אותיות עבריות כמו לטיניות, אחרת 'en'."""
    return 'he' if len(HEB.findall(text or '')) >= len(re.findall('[A-Za-z]', text or '')) else 'en'


def _f(code, extra='', span=None):
    return {'code': code, 'message_he': MSG[code] + (': ' + extra if extra else ''), 'span': span}


def sentences(text):
    """(משפט, התחלה, סוף). מפריד אחרי . ? ! ; ואחרי מעבר שורה."""
    out = []
    for m in re.finditer(r'[^.?!;\n]+(?:[.?!;]+|$)', text or ''):
        s = m.group(0)
        if s.strip():
            lead = len(s) - len(s.lstrip())
            out.append((s.strip(), m.start() + lead, m.start() + lead + len(s.strip())))
    return out


def _s(rx, text, flags=0):
    return re.search(rx, text or '', flags)


def _paragraphs(doc):
    return [x for x in (doc or '').split('\n') if x.strip()]


def _dedupe(F):
    seen, out = set(), []
    for x in F:
        k = (x['code'], x['message_he'], x['span'])
        if k not in seen:
            seen.add(k)
            out.append(x)
    return out


def check_wording(text, lang, topic=None, context=None):
    """כל המחלקות על נוסח אחד. ראו את ראש המודול."""
    lang = lang if lang in P else detect_lang(text)
    X = P[lang]
    ctx = context or {}
    doc = ctx.get('accept_text') or text
    I = re.I if lang == 'en' else 0
    F = []
    t = text or ''
    sents = sentences(t)
    # חריג מחלוקת בזכות סיום
    if _s(X['terminate'], t, I) and _s(X['breach'], t, I):
        dispute = [(s, a, b) for s, a, b in sents if _s(X['dispute'], s, I)]
        if not dispute and _s(X['payment'], t, I):
            F.append(_f('GAP_DISPUTE_CARVEOUT', 'אין חריג למחלוקת'))
        setoff_anywhere = _s(X['setoff'], doc, I)
        for s, a, b in dispute:
            miss = [n for n, k in (('סכום', 'd_amount'), ('מועד', 'd_timing')) if not _s(X[k], s, I)]
            if setoff_anywhere and not _s(X['setoff'], s, I):
                miss.append('קיזוז')
            if miss:
                F.append(_f('GAP_DISPUTE_CARVEOUT', 'החריג אינו חל על ' + ', '.join(miss), (a, b)))
    # חפיפה בסיום של התקשרות מתמשכת
    m = _s(X['term_right'], t, I)
    if m and _s(X['ongoing_ctx'], doc, I) and not _s(X['handover'], doc, I):
        F.append(_f('GAP_TERMINATION_HANDOVER', '', (m.start(), m.end())))
    # חריגי סודיות
    if (topic == 'confidentiality' or _s(X['conf'], t, I)) and (topic == 'confidentiality' or _s(X['conf_duty'], t, I)):
        names = (('גילוי לפי דין או לפי דרישת רשות', X['law_exc']), ('יועצים, רואה החשבון והמבקר הפנימי', X['adv_exc']),
                 ('מידע שהתקבל כדין מצד שלישי', X['tp_exc']), ('פיתוח עצמאי', X['indep']))
        miss = [n for n, rx in names if not _s(rx, doc, I)]
        if miss:
            F.append(_f('GAP_CONFIDENTIALITY_EXCEPTIONS', 'חסרים: ' + '; '.join(miss)))
    # נוסח תשלום
    if _s(X['pay_term'], t, I):
        m = _s(X['pay_latest'], t, I)
        if m:
            F.append(_f('GAP_PAYMENT_WORDING', 'הפניה ל"מועד מאוחר ביותר" או ל"לפי המוקדם"', (m.start(), m.end())))
        if not _s(X['days'], t, I):
            F.append(_f('GAP_PAYMENT_WORDING', 'אין מספר ימים'))
    if not ctx.get('accept_text'):
        F += check_document(t, [t], lang, ctx)
    waived = set(ctx.get('waived') or ())
    return _dedupe([x for x in F if x['code'] not in waived])


def check_document(accept_text, touched, lang, context=None):
    """בדיקות שחלות על ההסכם כולו. touched: הפסקאות שהכנסנו (רק התנגשות שבה לנוסח שלנו יש חלק נבדקת)."""
    lang = lang if lang in P else detect_lang(accept_text)
    ctx = context or {}
    F = []
    waived = set(ctx.get('waived') or ())
    return _dedupe([x for x in F if x['code'] not in waived])
