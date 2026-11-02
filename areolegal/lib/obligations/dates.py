# -*- coding: utf-8 -*-
"""obligations/dates.py: מנוע המועדים של מרשם ההתחייבויות. דטרמיניסטי, ספרייה סטנדרטית בלבד.

המודל אינו כותב תאריך יעד. הוא כותב `timing` מלשון ההסכם, והמנוע מחשב ממנו את המועד ואת שורת
החישוב שמוצגת ללקוח ("90 ימים לפני תום התקופה הנוכחית (31.12.2027) = 2.10.2027").

סוגי timing:
  fixed         {"date": "2027-03-01"}
  relative      {"anchor": <עוגן>, "offset": {"n": 30, "unit": "days", "direction": "after", "clear_days": false}}
  recurring     {"every": {"n": 3, "unit": "months"}, "start": <עוגן או תאריך>, "start_offset": {...}, "until": <עוגן או תאריך>}
  renewal_notice {}            המועד האחרון להודעה על אי חידוש, מ-agreement.dates.auto_renewal
  term_end      {}             תום התקופה הנוכחית (מתגלגל בחידוש אוטומטי)
  event         {"event": "אירוע אבטחה", "offset": {"n": 48, "unit": "hours", "direction": "after"}}
  ongoing       {"until": <עוגן>}   חובה מתמשכת (ביטוח לאורך התקופה)
  survival      {"period": {"n": 3, "unit": "years"}} או {"period": "indefinite"}
  any kind may add "qualifier": "reasonable" | "promptly" | "without_delay" | "other" -> טעון בדיקה משפטית.

עוגנים: signing_date, effective_date, end_date (תום התקופה הראשונה), term_end (תום התקופה הנוכחית),
renewal_date (היום שאחרי term_end), custom:<שם> (agreement.dates.anchors), obl:<מזהה> (מועד של חובה אחרת).

מעמד המועד (date_status): computed, to_complete (עוגן חסר: [להשלים], לעולם לא ניחוש), needs_verification
(ימי עסקים וחגים, שעות שעוגלו לימים, יום שקוצץ לסוף חודש, מסירה נחשבת שלא חושבה), needs_legal_review (מועד
עמום), event_driven, ongoing.

ימי עסקים: הגדרת "יום עסקים" שבהסכם גוברת (agreement.business_days: {"weekend": ["friday", "saturday"],
"calendars": ["England"], "clause": "1.1"}); אחריה סמכות השיפוט (agreement.jurisdiction, בקוד ISO-2 או ISO-3, בשם
או בתואר, בעברית או באנגלית: "IL", "ISR", "Israeli law", "הדין הישראלי"), לפי טבלת סופי השבוע; בלעדיהן, הונח
שבת וראשון, ושורת החישוב אומרת זאת. החגים אינם נוכים, ולכן כל מועד בימי עסקים "טעון אימות".

מסירה נחשבת (agreement.notice_delivery: {"deemed_after": {"n": 2, "unit": "business_days"}, "cutoff_time": "17:00",
"tz": "Europe/London", "clause": "19.3", "text": "..."}), מסעיף ההודעות: בהודעה ששולחים אנחנו (סוג notice או
renewal_notice, obligor us או both, והמועד האחרון להודעה על אי חידוש), המועד הוא מועד השליחה: היום האחרון
לקבלה פחות תקופת המסירה הנחשבת. כשסעיף ההודעות קובע מסירה נחשבת או שעת סגירה שאי אפשר לחשב (רק text), המועד
needs_verification והסיבה בשורת החישוב.

תאריך בשורת החישוב (כלל 3.6): D.M.YYYY בעברית; באנגלית צורה חד-משמעית, "3 April 2027"; ISO ב-JSON.
"""
import calendar
import datetime as dt
import re

UNITS = ('days', 'business_days', 'weeks', 'months', 'years', 'hours')
KINDS = ('fixed', 'relative', 'recurring', 'renewal_notice', 'term_end', 'event', 'ongoing', 'survival')
QUALIFIERS = ('reasonable', 'promptly', 'without_delay', 'other')
STATUSES = ('computed', 'to_complete', 'needs_verification', 'needs_legal_review', 'event_driven', 'ongoing')
IL_NAMES = ('il', 'israel', 'ישראל')   # תאימות לאחור; הנרמול המלא ב-jurisdiction_code
EN_MONTHS = ('January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
             'November', 'December')
# ימי השבוע (weekday של פייתון: שני=0)
DAY_NAMES = {'monday': 0, 'mon': 0, 'tuesday': 1, 'tue': 1, 'wednesday': 2, 'wed': 2, 'thursday': 3, 'thu': 3,
             'friday': 4, 'fri': 4, 'saturday': 5, 'sat': 5, 'sunday': 6, 'sun': 6,
             'שני': 0, 'שלישי': 1, 'רביעי': 2, 'חמישי': 3, 'שישי': 4, 'שבת': 5, 'ראשון': 6,
             'יום שני': 0, 'יום שלישי': 1, 'יום רביעי': 2, 'יום חמישי': 3, 'יום שישי': 4, 'יום ראשון': 6}
# סוף שבוע שישי-שבת. כל סמכות שיפוט ידועה אחרת: שבת-ראשון (כולל AE)
FRI_SAT = ('IL', 'SA', 'KW', 'QA', 'BH', 'OM', 'JO', 'EG')
DEFAULT_WEEKEND = (5, 6)
# שמות, תארים וקודים תלת-אותיים של סמכויות שיפוט, לנרמול agreement.jurisdiction לקוד ISO-2
JURIS_NAMES = {
    'IL': ('israel', 'israeli', 'isr', 'state of israel', 'ישראל', 'ישראלי', 'הישראלי', 'ישראלית', 'הישראלית'),
    'GB': ('united kingdom', 'uk', 'gbr', 'great britain', 'britain', 'british', 'england', 'english', 'wales',
           'welsh', 'england and wales', 'scotland', 'scottish', 'northern ireland', 'בריטניה', 'אנגליה',
           'הבריטי', 'האנגלי', 'אנגלי', 'בריטי'),
    'US': ('united states', 'usa', 'us', 'american', 'new york', 'delaware', 'california', 'texas', 'florida',
           'illinois', 'massachusetts', 'new jersey', 'washington', 'ארצות הברית', 'ארה"ב', 'ניו יורק',
           'דלאוור', 'קליפורניה', 'האמריקאי', 'אמריקאי'),
    'DE': ('germany', 'german', 'deu', 'גרמניה', 'הגרמני', 'גרמני'),
    'FR': ('france', 'french', 'fra', 'צרפת', 'הצרפתי', 'צרפתי'),
    'NL': ('netherlands', 'dutch', 'nld', 'holland', 'הולנד', 'ההולנדי', 'הולנדי'),
    'IE': ('ireland', 'irish', 'irl', 'אירלנד', 'האירי', 'אירי'),
    'CY': ('cyprus', 'cypriot', 'cyp', 'קפריסין', 'הקפריסאי', 'קפריסאי'),
    'CH': ('switzerland', 'swiss', 'che', 'שווייץ', 'שוויץ', 'השווייצרי', 'שווייצרי'),
    'AE': ('united arab emirates', 'uae', 'emirati', 'dubai', 'abu dhabi', 'difc', 'adgm',
           'איחוד האמירויות', 'דובאי'),
    'SA': ('saudi arabia', 'saudi', 'sau', 'ksa', 'ערב הסעודית', 'סעודיה', 'הסעודי'),
    'KW': ('kuwait', 'kuwaiti', 'kwt', 'כווית'), 'QA': ('qatar', 'qatari', 'qat', 'קטאר'),
    'BH': ('bahrain', 'bahraini', 'bhr', 'בחריין'), 'OM': ('oman', 'omani', 'omn', 'עומאן'),
    'JO': ('jordan', 'jordanian', 'jor', 'ירדן', 'הירדני'), 'EG': ('egypt', 'egyptian', 'egy', 'מצרים', 'המצרי'),
    'IT': ('italy', 'italian', 'ita', 'איטליה'), 'ES': ('spain', 'spanish', 'esp', 'ספרד'),
    'SG': ('singapore', 'sgp', 'סינגפור'), 'HK': ('hong kong', 'hkg', 'הונג קונג'),
    'CA': ('canada', 'canadian', 'can', 'קנדה'), 'AU': ('australia', 'australian', 'aus', 'אוסטרליה'),
}
_JURIS_KEYS = sorted(((k, c) for c, ks in JURIS_NAMES.items() for k in ks), key=lambda x: -len(x[0]))

T = {
    'he': {
        'unit': {'days': ('יום אחד', '%d ימים'), 'business_days': ('יום עסקים אחד', '%d ימי עסקים'),
                 'weeks': ('שבוע אחד', '%d שבועות'), 'months': ('חודש אחד', '%d חודשים'),
                 'years': ('שנה אחת', '%d שנים'), 'hours': ('שעה אחת', '%d שעות')},
        'before': 'לפני', 'after': 'אחרי',
        'anchor': {'signing_date': 'מועד החתימה', 'effective_date': 'מועד התחילה',
                   'end_date': 'תום התקופה הראשונה', 'term_end': 'תום התקופה הנוכחית',
                   'renewal_date': 'מועד החידוש הקרוב'},
        'obl': 'המועד של %s',
        'fixed': 'מועד קבוע בהסכם: %s',
        'by': 'עד %s = %s',
        'missing': '[להשלים] חסר: %s',
        'calc': '%s %s %s (%s) = %s',
        'clear': '; ספירה שמרנית של ימים שלמים',
        'bd': '; טעון אימות: ימי המנוחה לפי סמכות השיפוט, %s (%s); החגים לא נוכו',
        'bd_def': '; טעון אימות: ימי המנוחה לפי הגדרת "יום עסקים" בהסכם%s (%s)%s; החגים לא נוכו',
        'bd_cal': '; לוח החגים: %s',
        'bd_assumed': '; טעון אימות: סמכות השיפוט אינה ידועה, ולכן הונח שימי המנוחה הם %s; החגים לא נוכו',
        'clause_ref': ', סעיף %s', 'clause_paren': ' (סעיף %s)',
        'days': ('שני', 'שלישי', 'רביעי', 'חמישי', 'שישי', 'שבת', 'ראשון'), 'and': ' ו',
        'send_by': '; המסירה נחשבת %s אחרי השליחה%s, ולכן מועד השליחה: %s',
        'cutoff': '; מסירה אחרי השעה %s%s אינה נחשבת לאותו יום',
        'notice_unclear': '; טעון אימות: סעיף ההודעות%s קובע מסירה נחשבת או שעת סגירה שלא חושבו (%s), ולכן ייתכן שיש לשלוח מוקדם יותר',
        'hours': '; טעון אימות: %d שעות עוגלו ל-%d ימים',
        'clamp': '; היום קוצץ לסוף החודש',
        'term': '%s ועוד %s, עד היום שלפניו = %s',
        'term_given': 'תום התקופה כתוב בהסכם: %s',
        'renewed': '; התחדש %s, כל פעם ל-%s, עד %s',
        'times': ('פעם אחת', '%d פעמים'),
        'expired': 'ההסכם הסתיים ב-%s, אחרי מספר החידושים המרבי',
        'no_renewal': 'אין חידוש אוטומטי בהסכם',
        'window_closed': '; חלון ההודעה למחזור שמסתיים ב-%s נסגר ב-%s, ולכן מוצג המחזור הבא',
        'recurring': 'כל %s, החל מ-%s; המועד הקרוב: %s',
        'recurring_end': 'כל %s, החל מ-%s; אין מועד נוסף עד %s',
        'event': 'תלוי באירוע: %s',
        'event_off': '%s מ%s',
        'ongoing': 'חובה מתמשכת',
        'ongoing_until': 'חובה מתמשכת עד %s (%s)',
        'survival': 'שורדת את סיום ההסכם: %s אחרי הסיום',
        'survival_if': '; אם ההסכם יסתיים בתום התקופה הנוכחית (%s): עד %s',
        'survival_ind': 'שורדת את סיום ההסכם, בלי הגבלת זמן',
        'qualifier': 'טעון בדיקה משפטית: המועד אינו קצוב בהסכם (%s)',
        'qual': {'reasonable': 'זמן סביר', 'promptly': 'מיד', 'without_delay': 'ללא דיחוי', 'other': 'לשון עמומה'},
        'il': 'ישראל (שישי ושבת)', 'intl': 'שבת וראשון',
        'notice_period': 'תקופת ההודעה',
    },
    'en': {
        'unit': {'days': ('1 day', '%d days'), 'business_days': ('1 business day', '%d business days'),
                 'weeks': ('1 week', '%d weeks'), 'months': ('1 month', '%d months'),
                 'years': ('1 year', '%d years'), 'hours': ('1 hour', '%d hours')},
        'before': 'before', 'after': 'after',
        'anchor': {'signing_date': 'the signing date', 'effective_date': 'the effective date',
                   'end_date': 'the end of the initial term', 'term_end': 'the end of the current term',
                   'renewal_date': 'the next renewal date'},
        'obl': 'the date of %s',
        'fixed': 'Fixed date in the agreement: %s',
        'by': 'By %s = %s',
        'missing': '[to complete] missing: %s',
        'calc': '%s %s %s (%s) = %s',
        'clear': '; conservative count of clear days',
        'bd': '; needs verification: weekend days per the jurisdiction, %s (%s); holidays not deducted',
        'bd_def': '; needs verification: weekend days per the agreement\'s "Business Day" definition%s (%s)%s; holidays not deducted',
        'bd_cal': '; holiday calendar: %s',
        'bd_assumed': '; needs verification: the jurisdiction is not known, so the weekend was assumed to be %s; holidays not deducted',
        'clause_ref': ', clause %s', 'clause_paren': ' (clause %s)',
        'days': ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'), 'and': ' and ',
        'send_by': '; notice is deemed received %s after sending%s, so send by: %s',
        'cutoff': '; delivery after %s%s is not deemed received that day',
        'notice_unclear': '; needs verification: the notices clause%s sets deemed receipt or a cut-off time that was not computed (%s), so notice may have to be sent earlier',
        'hours': '; needs verification: %d hours rounded up to %d days',
        'clamp': '; day clamped to the end of the month',
        'term': '%s plus %s, to the day before = %s',
        'term_given': 'End of term stated in the agreement: %s',
        'renewed': '; renewed %s, each for %s, to %s',
        'times': ('once', '%d times'),
        'expired': 'The agreement ended on %s, after the maximum number of renewals',
        'no_renewal': 'The agreement has no automatic renewal',
        'window_closed': '; the notice window for the term ending %s closed on %s, so the next term is shown',
        'recurring': 'Every %s, starting %s; next: %s',
        'recurring_end': 'Every %s, starting %s; no further date until %s',
        'event': 'Event driven: %s',
        'event_off': '%s from %s',
        'ongoing': 'Continuing obligation',
        'ongoing_until': 'Continuing obligation until %s (%s)',
        'survival': 'Survives termination: %s after termination',
        'survival_if': '; if the agreement ends at the end of the current term (%s): until %s',
        'survival_ind': 'Survives termination, without time limit',
        'qualifier': 'Needs legal review: the agreement sets no fixed period (%s)',
        'qual': {'reasonable': 'reasonable time', 'promptly': 'promptly', 'without_delay': 'without delay',
                 'other': 'vague wording'},
        'il': 'Israel (Friday and Saturday)', 'intl': 'Saturday and Sunday',
        'notice_period': 'notice period',
    },
}


def _t(lang):
    return T['en' if str(lang or '').lower().startswith('en') else 'he']


def parse(s):
    if not s:
        return None
    if isinstance(s, dt.date):
        return s
    try:
        return dt.date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def fmt(d, lang='he'):
    """התאריך בטקסט שהלקוח רואה (כלל 3.6): D.M.YYYY בעברית; באנגלית "3 April 2027", שאינו מתפרש כחודש-יום."""
    if d is None:
        return ''
    if str(lang or '').lower().startswith('en'):
        return '%d %s %d' % (d.day, EN_MONTHS[d.month - 1], d.year)
    return '%d.%d.%d' % (d.day, d.month, d.year)


def iso(d):
    return None if d is None else d.isoformat()


def add_months(d, n):
    """מוסיף n חודשים. יום שאינו קיים בחודש היעד מקוצץ לסוף החודש; מחזיר (תאריך, קוצץ)."""
    m = d.month - 1 + n
    y, m = d.year + m // 12, m % 12 + 1
    last = calendar.monthrange(y, m)[1]
    return dt.date(y, m, min(d.day, last)), d.day > last


def jurisdiction_code(j):
    """קוד ISO-2 מ-agreement.jurisdiction: קוד דו-אותי או תלת-אותי, US-NY או GB-EAW, שם או תואר, בעברית או
    באנגלית, גם בתוך ביטוי ("Israeli law", "the laws of England and Wales", "הדין הישראלי"). לא מזוהה: None."""
    s = re.sub(r'\s+', ' ', str(j or '').replace('״', '"').strip()).casefold()
    if not s:
        return None
    m = re.fullmatch(r'([a-z]{2})(-[a-z]{2,3})?', s)
    if m:
        c = m.group(1).upper()
        return 'GB' if c == 'UK' else c
    for k, c in _JURIS_KEYS:
        if re.search(r'(?<![\w])%s(?![\w])' % re.escape(k.casefold()), s):
            return c
    return None


def weekend_of(agreement):
    """(ימי המנוחה, מקור, קוד): ההגדרה שבהסכם (agreement.business_days.weekend) גוברת; אחריה סמכות השיפוט;
    בלעדיהן, שבת וראשון בהנחה. מקור: 'defined', 'jurisdiction' או 'assumed'."""
    a = agreement or {}
    bd = a.get('business_days') if isinstance(a.get('business_days'), dict) else {}
    days = []
    for x in bd.get('weekend') or []:
        k = str(x).strip().casefold()
        if k in DAY_NAMES and DAY_NAMES[k] not in days:
            days.append(DAY_NAMES[k])
    if days:
        return tuple(sorted(days)), 'defined', None
    code = jurisdiction_code(a.get('jurisdiction'))
    if code:
        return ((4, 5) if code in FRI_SAT else DEFAULT_WEEKEND), 'jurisdiction', code
    return DEFAULT_WEEKEND, 'assumed', None


def weekend_days(jurisdiction):
    """ימי המנוחה השבועיים (weekday של פייתון: שני=0) לפי סמכות השיפוט בלבד. תאימות לאחור."""
    return weekend_of({'jurisdiction': jurisdiction})[0]


def shift(d, n, unit, sign, weekend=(5, 6)):
    """מזיז את d ב-n יחידות, קדימה (sign=1) או אחורה (sign=-1). מחזיר (תאריך, קוצץ, ימים_משעות)."""
    if unit == 'days':
        return d + dt.timedelta(days=sign * n), False, 0
    if unit == 'weeks':
        return d + dt.timedelta(days=sign * 7 * n), False, 0
    if unit == 'months':
        r, c = add_months(d, sign * n)
        return r, c, 0
    if unit == 'years':
        r, c = add_months(d, sign * 12 * n)
        return r, c, 0
    if unit == 'hours':
        days = -(-n // 24)
        return d + dt.timedelta(days=sign * days), False, days
    if unit == 'business_days':
        cur, left = d, n
        while left > 0:
            cur += dt.timedelta(days=sign)
            if cur.weekday() not in weekend:
                left -= 1
        return cur, False, 0
    raise ValueError('unit %r' % unit)


def span(off, lang):
    t = _t(lang)
    one, many = t['unit'][off['unit']]
    return one if int(off['n']) == 1 else many % int(off['n'])


class Ctx(object):
    """העוגנים של הסכם אחד, נכון ליום as_of."""

    def __init__(self, agreement, as_of, lang='he', obligations=None):
        self.a = agreement or {}
        self.d = self.a.get('dates') or {}
        self.as_of = parse(as_of) or dt.date.today()
        self.lang = lang
        self.t = _t(lang)
        self.weekend, self.weekend_src, self.juris = weekend_of(self.a)
        nd = self.a.get('notice_delivery')
        self.nd = nd if isinstance(nd, dict) and nd else None
        self.obls = {o.get('id'): o for o in (obligations or [])}
        self.fmt = lambda d: fmt(d, lang)
        self.done = {}
        self.term = self._term()

    # ---- תקופת ההסכם וחידוש אוטומטי
    def _term(self):
        t, d = self.t, self.d
        out = {'end_date': None, 'term_end': None, 'calc': '', 'renewals': 0, 'expired': False, 'clamp': False,
               'missing': t['anchor']['end_date']}
        start = parse(d.get('effective_date'))
        if not start and not d.get('end_date') and d.get('initial_term'):
            out['missing'] = t['anchor']['effective_date']
        end = parse(d.get('end_date'))
        if end:
            out['calc'] = t['term_given'] % self.fmt(end)
        elif start and d.get('initial_term'):
            it = d['initial_term']
            e, c, _ = shift(start, int(it['n']), it['unit'], 1, self.weekend)
            end = e - dt.timedelta(days=1)
            out['clamp'] = c
            out['calc'] = t['term'] % (self.fmt(start), span(it, self.lang), self.fmt(end))
        if not end:
            return out
        out['end_date'] = end
        cur = end
        ar = d.get('auto_renewal')
        if ar and ar.get('period'):
            p, mx, k = ar['period'], ar.get('max_renewals'), 0
            while cur < self.as_of and (mx is None or k < int(mx)):
                nxt, _, _ = shift(cur + dt.timedelta(days=1), int(p['n']), p['unit'], 1, self.weekend)
                cur, k = nxt - dt.timedelta(days=1), k + 1
            out['renewals'] = k
            if k:
                times = t['times'][0] if k == 1 else t['times'][1] % k
                out['calc'] += t['renewed'] % (times, span(p, self.lang), self.fmt(cur))
            if cur < self.as_of:
                out['expired'] = True
        elif cur < self.as_of:
            out['expired'] = True
        out['term_end'] = cur
        return out

    def renewal_notice(self):
        """(מועד, חישוב, מעמד) של המועד האחרון להודעה על אי חידוש, למחזור הרלוונטי הקרוב."""
        t, ar = self.t, self.d.get('auto_renewal')
        if not ar or not ar.get('period'):
            return None, t['no_renewal'], 'computed'
        if not ar.get('notice'):
            return None, t['missing'] % t['notice_period'], 'to_complete'
        end = self.term['term_end']
        if end is None:
            return None, t['missing'] % self.term['missing'], 'to_complete'
        if self.term['expired']:
            return None, t['expired'] % self.fmt(end), 'computed'
        n = ar['notice']
        ours = ar.get('by') in (None, 'either', 'us', 'both')

        def last_day(end):
            # היום האחרון לקבלת ההודעה, ובהודעה שלנו מועד השליחה לפי המסירה הנחשבת
            dl, _, hd = self._before(end, n)
            calc = t['calc'] % (span(n, self.lang), t['before'], t['anchor']['term_end'], self.fmt(end),
                                self.fmt(dl))
            calc, status = self._notes(calc, n, hd, False, 'computed')
            return self.send_by(dl, calc, status) if ours else (dl, calc, status)
        note = ''
        dl, calc, status = last_day(end)
        if dl < self.as_of:
            mx = ar.get('max_renewals')
            if mx is not None and self.term['renewals'] >= int(mx):
                return None, t['expired'] % self.fmt(end), 'computed'
            p = ar['period']
            nxt, _, _ = shift(end + dt.timedelta(days=1), int(p['n']), p['unit'], 1, self.weekend)
            note = t['window_closed'] % (self.fmt(end), self.fmt(dl))
            end = nxt - dt.timedelta(days=1)
            dl, calc, status = last_day(end)
        return dl, calc + note, status

    def send_by(self, d, calc, status):
        """הודעה ששולחים אנחנו: מהיום האחרון לקבלה למועד השליחה, לפי המסירה הנחשבת שבסעיף ההודעות
        (agreement.notice_delivery). בלי notice_delivery: ללא שינוי. מסירה נחשבת שאי אפשר לחשב: טעון אימות."""
        nd, t = self.nd, self.t
        if not nd or d is None:
            return d, calc, status
        cl = t['clause_ref'] % nd['clause'] if nd.get('clause') else ''
        da = nd.get('deemed_after')
        ok = isinstance(da, dict) and da.get('unit') in UNITS and str(da.get('n', '')).isdigit()
        if ok and int(da['n']) > 0:
            r, c, hd = shift(d, int(da['n']), da['unit'], -1, self.weekend)
            calc += t['send_by'] % (span(da, self.lang), cl, self.fmt(r))
            calc, status = self._notes(calc, da, hd, c, status)
            d = r
        elif da or (nd.get('text') and not nd.get('cutoff_time')):
            cp = t['clause_paren'] % nd['clause'] if nd.get('clause') else ''
            calc += t['notice_unclear'] % (cp, nd.get('text') or str(da))
            return d, calc, 'needs_verification' if status == 'computed' else status
        if nd.get('cutoff_time'):
            tz = ' (%s)' % nd['tz'] if nd.get('tz') else ''
            calc += t['cutoff'] % (nd['cutoff_time'], tz)
            if not nd.get('tz'):
                status = 'needs_verification' if status == 'computed' else status
        return d, calc, status

    def _before(self, d, off):
        r, c, hd = shift(d, int(off['n']), off['unit'], -1, self.weekend)
        if off.get('clear_days'):
            r -= dt.timedelta(days=1)
        return r, c, hd

    def _notes(self, calc, off, hd, clamp, status):
        t = self.t
        if off.get('clear_days'):
            calc += t['clear']
        if off['unit'] == 'business_days':
            calc += self._bd_note()
            status = 'needs_verification'
        if hd:
            calc += t['hours'] % (int(off['n']), hd)
            status = 'needs_verification'
        if clamp:
            calc += t['clamp']
            status = 'needs_verification'
        return calc, status

    def _days(self):
        t = self.t
        names = [t['days'][i] for i in self.weekend]
        return t['and'].join(names) if len(names) < 3 else ', '.join(names[:-1]) + t['and'] + names[-1]

    def _bd_note(self):
        t = self.t
        if self.weekend_src == 'defined':
            bd = self.a.get('business_days') or {}
            cl = t['clause_ref'] % bd['clause'] if bd.get('clause') else ''
            cal = t['bd_cal'] % ', '.join(str(x) for x in bd['calendars']) if bd.get('calendars') else ''
            return t['bd_def'] % (cl, self._days(), cal)
        if self.weekend_src == 'jurisdiction':
            return t['bd'] % (self.juris, self._days())
        return t['bd_assumed'] % self._days()

    # ---- עוגנים
    def anchor(self, name):
        """(תאריך או None, תווית)."""
        t = self.t
        if isinstance(name, str) and parse(name):
            return parse(name), self.fmt(parse(name))
        if name in ('signing_date', 'effective_date'):
            return parse(self.d.get(name)), t['anchor'][name]
        if name == 'end_date':
            return self.term['end_date'], t['anchor'][name] if self.term['end_date'] else self.term['missing']
        if name == 'term_end':
            return self.term['term_end'], t['anchor'][name] if self.term['term_end'] else self.term['missing']
        if name == 'renewal_date':
            e = self.term['term_end']
            return (e + dt.timedelta(days=1) if e else None), t['anchor'][name]
        if isinstance(name, str) and name.startswith('custom:'):
            k = name[7:]
            v = (self.d.get('anchors') or {}).get(k)
            if isinstance(v, dict):
                return parse(v.get('date')), v.get('label') or k
            return parse(v), k
        if isinstance(name, str) and name.startswith('obl:'):
            oid = name[4:]
            o = self.obls.get(oid)
            label = t['obl'] % ((o or {}).get('title') or oid)
            if o is None:
                return None, label
            r = self.compute(o)
            return parse(r['due_date']), label
        return None, str(name)

    # ---- חובה אחת
    def compute(self, o):
        oid = o.get('id')
        if oid in self.done:
            return self.done[oid]
        self.done[oid] = {'due_date': None, 'calc': '', 'date_status': 'to_complete'}   # מעגל: [להשלים]
        r = self._compute(o.get('timing') or {})
        kind = (o.get('timing') or {}).get('kind')
        if (o.get('type') in ('notice', 'renewal_notice') and o.get('obligor') in ('us', 'both')
                and kind in ('fixed', 'relative') and r.get('due_date')):
            d, c, st = self.send_by(parse(r['due_date']), r['calc'], r['date_status'])
            r = dict(r, due_date=iso(d), calc=c, date_status=st)
        q = (o.get('timing') or {}).get('qualifier')
        if q:
            r['calc'] = self.t['qualifier'] % self.t['qual'].get(q, q) + ('; ' + r['calc'] if r['calc'] else '')
            r['date_status'] = 'needs_legal_review'
        self.done[oid] = r
        return r

    def _compute(self, tm):
        t, kind = self.t, tm.get('kind')
        res = lambda d, c, s, **kw: dict({'due_date': iso(d), 'calc': c, 'date_status': s}, **kw)
        if kind == 'fixed':
            d = parse(tm.get('date'))
            return res(d, t['fixed'] % self.fmt(d), 'computed') if d else res(None, t['missing'] % 'date', 'to_complete')
        if kind == 'relative':
            a, label = self.anchor(tm.get('anchor'))
            if a is None:
                return res(None, t['missing'] % label, 'to_complete')
            off = tm.get('offset') or {'n': 0, 'unit': 'days', 'direction': 'after'}
            if off.get('direction') == 'before':
                d, c, hd = self._before(a, off)
            else:
                d, c, hd = shift(a, int(off['n']), off['unit'], 1, self.weekend)
            if int(off['n']) == 0:                       # "עד מועד החתימה", "לפני תום התקופה"
                calc = t['by'] % (label, self.fmt(d))
            else:
                calc = t['calc'] % (span(off, self.lang), t[off.get('direction', 'after')], label, self.fmt(a), self.fmt(d))
            calc, st = self._notes(calc, off, hd, c, 'computed')
            return res(d, calc, st)
        if kind == 'renewal_notice':
            d, calc, st = self.renewal_notice()
            return res(d, calc, st)
        if kind == 'term_end':
            e = self.term['term_end']
            if e is None:
                return res(None, t['missing'] % self.term['missing'], 'to_complete')
            st = 'needs_verification' if self.term['clamp'] else 'computed'
            return res(e, self.term['calc'], st)
        if kind == 'recurring':
            occ, calc, st = self.occurrences(tm, self.as_of, None, first_only=True)
            return res(occ[0] if occ else None, calc, st)
        if kind == 'event':
            off = tm.get('offset')
            ev = tm.get('event') or ''
            txt = t['event_off'] % (span(off, self.lang), ev) if off else ev
            return res(None, t['event'] % txt, 'event_driven')
        if kind == 'ongoing':
            if tm.get('until'):
                a, label = self.anchor(tm['until'])
                if a:
                    return res(a, t['ongoing_until'] % (self.fmt(a), label), 'ongoing')
            return res(None, t['ongoing'], 'ongoing')
        if kind == 'survival':
            p = tm.get('period')
            if p in (None, 'indefinite'):
                return res(None, t['survival_ind'], 'ongoing')
            calc = t['survival'] % span(p, self.lang)
            e = self.term['term_end']
            if e:
                u, _, _ = shift(e, int(p['n']), p['unit'], 1, self.weekend)
                calc += t['survival_if'] % (self.fmt(e), self.fmt(u))
            return res(None, calc, 'ongoing')
        return res(None, t['missing'] % 'timing', 'to_complete')

    def occurrences(self, tm, frm, to, first_only=False):
        """מועדי חובה חוזרת בטווח [frm, to]. מחזיר (רשימת תאריכים, חישוב, מעמד)."""
        t = self.t
        ev = tm.get('every') or {}
        a, label = self.anchor(tm.get('start'))
        if a is None or not ev.get('n'):
            return [], t['missing'] % label, 'to_complete'
        st = 'computed'
        clamp = hd = False
        if tm.get('start_offset'):
            off = tm['start_offset']
            if off.get('direction') == 'before':
                a, clamp, hd = self._before(a, off)
            else:
                a, clamp, hd = shift(a, int(off['n']), off['unit'], 1, self.weekend)
        until = None
        if tm.get('until'):
            until, _ = self.anchor(tm['until'])
        elif self.term['term_end']:
            until = self.term['term_end']
        limit = to or (frm + dt.timedelta(days=3660))
        out, k = [], 0
        while k < 2000:
            n = int(ev['n']) * k
            if ev['unit'] in ('months', 'years'):
                d, c = add_months(a, n * (12 if ev['unit'] == 'years' else 1))
                clamp = clamp or c
            else:
                d, _, _ = shift(a, n, ev['unit'], 1, self.weekend)
            k += 1
            if (until and d > until) or d > limit:
                break
            if d >= frm:
                out.append(d)
                if first_only:
                    break
        every = span(ev, self.lang)
        if out:
            calc = t['recurring'] % (every, self.fmt(a), self.fmt(out[0]))
        else:
            calc = t['recurring_end'] % (every, self.fmt(a), self.fmt(until or limit))
        off = dict(ev, n=ev['n'])
        calc, st = self._notes(calc, off, hd, clamp, st)
        return out, calc, st


def compute_all(agreement, obligations, as_of=None, lang='he'):
    """מחזיר {id: {due_date, calc, date_status}} ואת פרטי התקופה."""
    ctx = Ctx(agreement, as_of, lang, obligations)
    out = {o.get('id'): ctx.compute(o) for o in obligations}
    term = {'end_date': iso(ctx.term['end_date']), 'term_end': iso(ctx.term['term_end']),
            'renewals': ctx.term['renewals'], 'expired': ctx.term['expired'], 'calc': ctx.term['calc']}
    d, c, s = ctx.renewal_notice()
    term['renewal_notice'] = {'date': iso(d), 'calc': c, 'date_status': s}
    return out, term
