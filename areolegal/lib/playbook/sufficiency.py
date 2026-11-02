# -*- coding: utf-8 -*-
"""playbook/sufficiency.py: האם ההסכמים של הלקוח מספיקים כדי להסיק את קווי הנסיגה שלו (כלל מייסד 13).

הבעיה: פלייבוק שנבנה מדגם דל נראה כמו כל פלייבוק אחר, אבל הצהוב והאדום בו אינם של הלקוח: אין לו ראיה
לאן הוא מוכן לוותר. הבונה צריך לומר זאת לפני הבנייה, ולבקש חומר מסוים שיחדד את התוצאה.

בדיקה דטרמיניסטית אחת, כללית לכל סוג הסכם, לכל דין ולכל שפה. היא קוראת רק את רישום המקורות (source_log) ואת
הכללים (rules), ואינה מכירה סוג הסכם, צד או דין:
- agreements_per_family: כמה הסכמים (חתומים, בסוג ובעמדה, בלי תבניות ובלי נוסחים לא חתומים) יש לכל סוג.
- negotiation_trail: כמה טיוטות משא ומתן (doc_role: draft) וכמה התכתבויות (doc_role: correspondence) נמסרו,
  וכמה הסכמים מסומנים acceptance_mode: negotiated.
- spread (אחרי הגזירה, כשנמסרו כללים): בכמה נושאים נצפו עמדות שונות בין המסמכים, ובכמה נושאים הצהוב נשען על
  מסמכי הלקוח, לעומת הצעת Areo בלבד.

הרמה: sufficient | thin | insufficient. לעולם אינה חוסמת בנייה: הלקוח יכול להמשיך בלי חומר נוסף, וקווי נסיגה שאינם
נשענים על החומר שלו מסומנים "הצעת Areo". חוסם רק שהשאלה לא נשאלה: model["sufficiency"] נרשם עם requests והתשובה.

שימוש:
    from playbook.sufficiency import assess, client_message
    res = assess(model["source_log"], model.get("rules"))
    for line in client_message(res, "he"):
        print(line)
    python3 -B sufficiency.py --model <playbook-model.json> [--lang he|en]   # קוד יציאה: 0 sufficient, 1 thin, 2 insufficient
    python3 -B sufficiency.py --sources <sources.json> [--rules <rules.json>]
"""
import argparse
import io
import json
import sys

# --- הסף, במקום אחד. מספר ההסכמים נספר בקוד (build_corpus_manifest.py), לא בהערכה ---
SOLID_AGREEMENTS = 7        # מ-7 הסכמים בסוג, הפיזור בין ההסכמים לבדו כבר מראה אילו עמדות נשארות קבועות
OPTIMAL_AGREEMENTS = 20     # הרף שממנו הדיוק של קווי הנסיגה משתפר עוד (נאמר ללקוח, אינו משנה את הרמה)
MIN_WITH_TRAIL = 3          # מ-3 הסכמים עם עקבות משא ומתן (טיוטות או התכתבות) אפשר להסיק קווי נסיגה
MIN_ANY = 3                 # מתחת ל-3 הסכמים אין פיזור שאפשר להסיק ממנו, גם עם עקבות
AREO_FALLBACK_SHARE = 0.5   # יותר מחצי מהנושאים עם צהוב שהוא הצעת Areo בלבד: הדגימה דלה לנסיגה

SIGNED_ROLES = ('signed', 'agreement')          # amendment נספר עם ההסכם שלו ולא לבדו
DRAFT_ROLES = ('draft',)
CORRESPONDENCE_ROLES = ('correspondence',)
NOT_AGREEMENT_ROLES = ('template', 'form', 'amendment') + DRAFT_ROLES + CORRESPONDENCE_ROLES
DOCUMENT_BASES = ('established', 'single', 'offered_unexecuted', 'client_answer')   # צהוב שנשען על הלקוח
AREO_BASES = ('areo_proposal', 'market_standard')

LEVELS = ('sufficient', 'thin', 'insufficient')

# --- המלצה ללקוח: בקול של מנהל מוצר, התוצאה קודם, בלי קודים ובלי שמות פנימיים ---
TEXT = {
    'he': {
        'thin_head': 'החומר שמסרתם מספיק כדי להתחיל, אבל לא כדי לדייק את קווי הנסיגה של החברה.',
        'insufficient_head': 'החומר שמסרתם אינו מספיק כדי להסיק איפה החברה מוכנה לוותר.',
        'ok': 'החומר מספיק כדי להסיק את קווי הנסיגה של החברה מההסכמים שלה. מ-20 הסכמים ומעלה מאותו סוג הדיוק משתפר עוד.',
        'few': 'עוד {k} הסכמים לפחות מאותו סוג ומאותה עמדה של החברה (מול צדדים שונים או בתקופות שונות).',
        'trail': 'טיוטות משא ומתן (גרסאות עם שינויים במעקב) והתכתבות עם הצד השני על סעיפים שהתמקחתם עליהם. '
                 'הן מראות מה ביקשתם, על מה ויתרתם ובמה התעקשתם.',
        'spread': 'הסכמים שנחתמו מול צדדים שונים. כשכל ההסכמים כמעט זהים, אי אפשר לדעת איפה יש לכם גמישות.',
        'areo': 'ב-{n} מתוך {m} נושאים הצהוב מבוסס על הצעת Areo בלבד, כי אין במסמכים שלכם פשרה בנושא.',
        'ask': 'מה שיחדד את התוצאה:',
        'tail': 'אפשר להמשיך גם עכשיו. קווי נסיגה שאינם נשענים על החומר שלכם יסומנו "הצעת Areo", ואפשר להשלים '
                'חומר ולעדכן את הפלייבוק בכל שלב.',
    },
    'en': {
        'thin_head': "What you gave is enough to start, but not enough to pin down the company's fallback lines.",
        'insufficient_head': "What you gave is not enough to tell where the company is willing to give ground.",
        'ok': "The material is enough to infer the company's fallback lines from its own agreements. From 20 agreements of the same type the precision improves further.",
        'few': 'At least {k} more agreements of the same type and the same company side (with different '
               'counterparties or from different periods).',
        'trail': 'Negotiation drafts (versions with tracked changes) and correspondence with the other side on the '
                 'clauses you bargained over. They show what you asked for, what you gave up and where you held.',
        'spread': 'Agreements signed with different counterparties. When all agreements are nearly identical, there is '
                  'no way to tell where you have flexibility.',
        'areo': 'In {n} of {m} topics the fallback rests on an Areo proposal alone, because your documents hold no '
                'compromise on the topic.',
        'ask': 'What would sharpen the result:',
        'tail': 'You can go on now. Fallback lines that do not rest on your material will be marked "Areo proposal", '
                'and you can add material and update the playbook at any time.',
    },
}


def _lang(lang):
    return 'en' if str(lang or '').strip().lower().startswith('en') else 'he'


def _included(s):
    return isinstance(s, dict) and s.get('included') is not False


def _role(s):
    return str(s.get('doc_role') or '').strip().lower()


def _family(s):
    return str(s.get('family_id') or s.get('contract_family_id') or s.get('family') or '') or '_'


def agreements_per_family(sources):
    """{family: מספר ההסכמים החתומים}. הסכם חתום: doc_role signed או agreement (או בלי doc_role וסטטוס חתום),
    ולא תבנית, נוסח לא חתום, טיוטה או התכתבות. מקור שאינו בסוג (same_family: false) אינו נספר."""
    out = {}
    for s in sources or []:
        if not _included(s) or s.get('same_family') is False:
            continue
        r = _role(s)
        if r in NOT_AGREEMENT_ROLES:
            continue
        if r in SIGNED_ROLES or (not r and str(s.get('status') or '').lower() in ('signed', 'executed')):
            f = _family(s)
            out[f] = out.get(f, 0) + 1
    return out


def negotiation_trail(sources):
    """{drafts, correspondence, negotiated_agreements}: עקבות של משא ומתן בחומר שנמסר."""
    drafts = corr = negotiated = 0
    for s in sources or []:
        if not _included(s):
            continue
        r = _role(s)
        if r in DRAFT_ROLES:
            drafts += 1
        elif r in CORRESPONDENCE_ROLES:
            corr += 1
        elif r in SIGNED_ROLES and str(s.get('acceptance_mode') or '') == 'negotiated':
            negotiated += 1
    return {'drafts': drafts, 'correspondence': corr, 'negotiated_agreements': negotiated}


def _tracks_seen(rule):
    """קבוצת הצבעים שנצפו בראיות הכלל (green | yellow | red), בלי הקשר."""
    return {str(e.get('track')) for e in rule.get('evidence') or [] if isinstance(e, dict)
            and e.get('track') in ('green', 'yellow', 'red')}


def spread(rules):
    """{rules, with_spread, yellow_from_documents, yellow_areo_only}. None כשלא נמסרו כללים.
    with_spread: נושא שנצפו בו לפחות שתי עמדות שונות (ירוק וגם צהוב או אדום). yellow_from_documents: הצהוב נשען על
    מסמכי הלקוח (basis מ-DOCUMENT_BASES). yellow_areo_only: הצהוב הוא הצעת Areo או תקן שוק."""
    rs = [r for r in rules or [] if isinstance(r, dict)]
    if not rs:
        return None
    sp = doc = areo = 0
    for r in rs:
        if len(_tracks_seen(r)) >= 2:
            sp += 1
        y = ((r.get('traffic_light') or {}).get('yellow') or {}).get('basis')
        if y in DOCUMENT_BASES:
            doc += 1
        elif y in AREO_BASES:
            areo += 1
    return {'rules': len(rs), 'with_spread': sp, 'yellow_from_documents': doc, 'yellow_areo_only': areo}


def assess(sources, rules=None):
    """הערכה אחת, דטרמיניסטית. מחזיר:
    {level, agreements_per_family, agreements (הקטן שבסוגים: הסוג המצומצם ביותר קובע), negotiation_trail, spread,
     reasons[] (FEW_AGREEMENTS | NO_NEGOTIATION_TRAIL | NO_SPREAD | FALLBACK_FROM_AREO), requests[] (kind + need)}."""
    per = agreements_per_family(sources)
    n = min(per.values()) if per else 0
    trail = negotiation_trail(sources)
    has_trail = (trail['drafts'] + trail['correspondence']) > 0
    sp = spread(rules)
    reasons, requests = [], []

    if n >= SOLID_AGREEMENTS:
        level = 'sufficient'
    elif n >= MIN_WITH_TRAIL and has_trail:
        level = 'sufficient'
    elif n >= MIN_ANY or (n >= 1 and has_trail):
        level = 'thin'
    else:
        level = 'insufficient'

    if n < (MIN_WITH_TRAIL if has_trail else SOLID_AGREEMENTS):
        reasons.append('FEW_AGREEMENTS')
        target = MIN_WITH_TRAIL if has_trail else SOLID_AGREEMENTS
        requests.append({'kind': 'more_agreements', 'need': max(1, target - n)})
    if not has_trail and n < SOLID_AGREEMENTS:
        reasons.append('NO_NEGOTIATION_TRAIL')
        requests.append({'kind': 'negotiation_trail'})
    if sp and sp['rules'] >= 3 and sp['with_spread'] == 0 and n < SOLID_AGREEMENTS:
        reasons.append('NO_SPREAD')
        requests.append({'kind': 'varied_counterparties'})
    if sp and sp['rules'] and sp['yellow_areo_only'] / float(sp['rules']) > AREO_FALLBACK_SHARE:
        reasons.append('FALLBACK_FROM_AREO')
        if level == 'sufficient':
            level = 'thin'
        if not any(r['kind'] == 'negotiation_trail' for r in requests):
            requests.append({'kind': 'negotiation_trail'})
    return {'level': level, 'agreements': n, 'agreements_per_family': per, 'negotiation_trail': trail,
            'spread': sp, 'reasons': reasons, 'requests': requests}


def client_message(res, lang='he'):
    """שורות ללקוח (מנהל מוצר: התוצאה, ואז מה יחדד אותה). רשימה עם שורה אחת ('ok') כשהחומר מספיק."""
    T = TEXT[_lang(lang)]
    if res.get('level') == 'sufficient' and not res.get('requests'):
        return [T['ok']]
    out = [T['insufficient_head'] if res.get('level') == 'insufficient' else T['thin_head'], T['ask']]
    sp = res.get('spread') or {}
    for rq in res.get('requests') or []:
        k = rq.get('kind')
        if k == 'more_agreements':
            out.append('- ' + T['few'].format(k=rq.get('need', 1)))
        elif k == 'negotiation_trail':
            out.append('- ' + T['trail'])
        elif k == 'varied_counterparties':
            out.append('- ' + T['spread'])
    if 'FALLBACK_FROM_AREO' in (res.get('reasons') or []):
        out.append(T['areo'].format(n=sp.get('yellow_areo_only', 0), m=sp.get('rules', 0)))
    out.append(T['tail'])
    return out


def record(res, client_response='pending', asked_at=None):
    """הבלוק שהבונה כותב ל-model["sufficiency"]: ההערכה, מה התבקש, ומה הלקוח ענה (pending | provided | declined)."""
    return {'level': res['level'], 'agreements': res['agreements'], 'reasons': list(res['reasons']),
            'requests': [dict(r) for r in res['requests']], 'asked_at': asked_at or '',
            'client_response': client_response}


def findings(model):
    """ממצאים למאמת: [(code, severity, message)]. שני קודים בלבד, ושניהם על כך שלא נשאל:
    SUFFICIENCY_NOT_ASKED: ההערכה אינה sufficient ובמודל אין model["sufficiency"] עם requests ותשובה. error כשהחומר
    insufficient (אין על מה להסיק קווי נסיגה, והלקוח חייב להישאל), warning כשהוא thin.
    SUFFICIENCY_STALE (warning): ההערכה שנרשמה במודל שונה מזו שנגזרת עכשיו מהמקורות."""
    out = []
    if not isinstance(model, dict):
        return out
    res = assess(model.get('source_log'), model.get('rules'))
    if res['level'] == 'sufficient' and not res['requests']:
        return out
    rec = model.get('sufficiency')
    if not isinstance(rec, dict) or not rec.get('requests') or rec.get('client_response') not in (
            'pending', 'provided', 'declined'):
        out.append(('SUFFICIENCY_NOT_ASKED', 'error' if res['level'] == 'insufficient' else 'warning',
                    'החומר אינו מספיק להסקת קווי הנסיגה (%s), והמודל אינו נושא sufficiency עם requests ועם תשובת '
                    'הלקוח. בקשו מהלקוח חומר מסוים, והסבירו מה יחדד את התוצאה.' % (', '.join(res['reasons']) or res['level'])))
    elif rec.get('level') != res['level']:
        out.append(('SUFFICIENCY_STALE', 'warning',
                    'sufficiency.level במודל הוא %s, ומהמקורות הנוכחיים נגזר %s.' % (rec.get('level'), res['level'])))
    return out


def main(argv=None):
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--model', help='playbook-model.json (source_log ו-rules)')
    ap.add_argument('--sources', help='קובץ JSON של רשימת מקורות (source_log), לפני שנבנה מודל')
    ap.add_argument('--rules', help='קובץ JSON של הכללים, אופציונלי')
    ap.add_argument('--lang', default='he')
    ap.add_argument('--json', action='store_true', help='הפלט כ-JSON')
    a = ap.parse_args(argv)
    try:
        return _run(a, ap)
    except (OSError, ValueError) as e:
        # קובץ חסר או JSON פגום: שורה ברורה וקוד יציאה 3, בלי traceback
        print('לא ניתן לקרוא את הקובץ: %s' % e)
        return 3


def _run(a, ap):
    if a.model:
        with io.open(a.model, encoding='utf-8') as fh:
            m = json.load(fh)
        sources, rules = m.get('source_log'), m.get('rules')
    elif a.sources:
        with io.open(a.sources, encoding='utf-8') as fh:
            sources = json.load(fh)
        sources = sources.get('source_log', sources) if isinstance(sources, dict) else sources
        rules = None
        if a.rules:
            with io.open(a.rules, encoding='utf-8') as fh:
                rules = json.load(fh)
    else:
        ap.error('נדרש --model או --sources')
        return 2
    res = assess(sources, rules)
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
    else:
        for line in client_message(res, a.lang):
            print(line)
    return {'sufficient': 0, 'thin': 1, 'insufficient': 2}[res['level']]


if __name__ == '__main__':
    sys.dont_write_bytecode = True
    sys.exit(main())
