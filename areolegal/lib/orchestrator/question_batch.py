# -*- coding: utf-8 -*-
"""מנת השאלות האחת שלפני ההכרעות.

בסבב 3 כל רץ כתב את המנה בקוד הדבקה: באחד "חוסם משלוח, תשובה של מילה אחת" הופיע בלי התווית "נדרשת הכרעתך",
שאלת הרכיבים המשלימים נשאלה פעמיים, ושאלת "שווי ההתקשרות" נשאלה על מסמך בלי תמורה.

כללים:
- "נדרשת הכרעתך" רק בתשעת המצבים (1 עד 9). התווית שהמשתמש רואה: "נדרשת הכרעתך", ובפריט חוסם "(חוסם משלוח, תשובה
  של מילה אחת)". מספר המצב נשאר בפריט ובקובץ המצב, ואינו מוצג. אין מצב עשירי:
  מצב שאינו 1 עד 9 זורק ValueError. חציית קו אדום או ירידה מתחת לנסיגה האחרונה היא מצב 2 (החלטת מוצר 1,
  14.10.2026), ואין לצידה "מאשר" או "טעון אישור".
- שאלה שאינה "נדרשת הכרעתך" (כרטיס עסקה, רכיבים משלימים) נשאלת בלי התווית.
- כל שאלה נשאלת פעם אחת: מפתח שכבר נשאל (asked_before) אינו נשאל שוב.
- בהסכם בלי תמורה, שאלת השווי של כרטיס העסקה אינה נשאלת.
- פריט חוסם משלוח ראשון; אחריו לפי מספר המצב; אחריו השאר. מעבר ל-max_questions, פריטים מאותו מצב מקובצים לשאלה אחת,
  שאלות התהליך (PROCESS_KINDS) מקובצות לשורה אחת, ומה שעדיין עובר את התקרה נדחה למנה הבאה (חוסם או דורש תשובה מפורשת)
  או מוכרע לפי ההמלצה. השורה הראשונה של המנה אומרת כמה שאלות יש.
- סבב המשך (בדיקה עצמאית S1c, 28.10.2026): round_items מוסיף מהשוואת הסבב ומקובץ המצב את השינויים השקטים (מצב 9,
  חוסם משלוח), פתיחה מחדש של סעיף מוסכם, מונח שהגדרתו נמחקה, STUCK עם הצעה לשיחה (רק לפי state_builder.stuck_reason:
  שתי דחיות שלהם בשני סבבים בלי תזוזה, או עמדה סופית שלהם), וקבלה שעומדת לשיחה. הקובץ שמוזן הוא תצוגה מקדימה: קובץ
  המצב אחרי apply_compare על השוואת הסבב, לפני ההכרעות (round_tools.py questions --compare). פריט
  kind=counter_tighter (הצעה נגדית שלהם שהדוקה מהנסיגה האחרונה אבל סבירה) הוא מצב 2, עם המלצה, ואינו חריגה.
- מטריצת הסבבים (ROUND_MATRIX, round_row, round_violations): מטרה, נסיגה מותרת, אורך בועה, טון ומה עונים על קבלה,
  לכל סבב, ובדיקה של קובץ ההכרעות מולה.
- פאנל S1d-R2 ו-S1e-R3 (29.10.2026): תשובה כללית אינה אישור (requires_explicit: מצב 2, counter_tighter, סכום, גבול
  הקו האדום של האסטרטג, התחייבות תפעולית, עם שאלה לגורם הרלוונטי); הסימונים של האסטרטג מצוטטים בפריט (strategy_marks);
  סעיף כמותי מורכב מוכרע רכיב אחר רכיב (kind: composite), ויעד שנמסר לפני ההצעה שלהם נשאל מחדש (stale_target_items),
  ובסבב סגירה מעבר לנסיגה האחרונה גם תזכיר החלטה (decision_memo); נקודה לשיחה שלא התקיימה בסבב סגירה, וויתור על נושא
  מסחרי מחייב, הם "נדרשת הכרעתך"; מצב 9 עם אפשרות שלישית, לקבל בתנאי; ותשובה שמחליפה הצעה קודמת שלנו בשרשור פתוח
  אומרת זאת (ROUND_STALE_PROPOSAL).

    from orchestrator.question_batch import build_batch
    b = build_batch(items, no_consideration=False, asked_before={'components'})
    b['text'], b['questions'], b['skipped']

שפה (דרישת מוצר 28.10.2026): המנה היא חלק מהשיחה, ולכן בשפת הממשק (display_language). lang='en' נותן את התווית
"Your decision is needed (situation N[, blocks sending...])", את ההמלצה ואת שורות הקיבוץ באנגלית; lang='he' כמו תמיד.
"""
from orchestrator.state_builder import SITUATIONS
from orchestrator import proportionality as P

# התווית בשפת הממשק (display_language), כי המנה היא חלק מהשיחה; נייר באנגלית בשיחה עברית נשאל בעברית
LABEL = {'he': 'נדרשת הכרעתך', 'en': 'Your decision is needed'}
BLOCKS = 'צריך לפני שליחה, תשובה של מילה אחת'
TXT = {'he': {'sit': 'מצב', 'blocks': BLOCKS, 'rec': ' המלצה: %s.', 'asked': 'כבר נשאלה', 'free': 'הסכם בלי תמורה',
              'opts': ['לאשר את כל ההמלצות', 'לשנות שורה'], 'group': 'כמה נושאים דומים:\n   | הנושא | ההמלצה |\n'},
       'en': {'sit': 'situation', 'blocks': 'needed before sending, one-word answer', 'rec': ' Recommendation: %s.',
              'asked': 'already asked', 'free': 'agreement without consideration',
              'opts': ['Approve all recommendations', 'Change a row'],
              'group': 'Several similar topics:\n   | Topic | Recommendation |\n'}}


# הגישה להחלת הפלייבוק (דרישת מוצר 28.10.2026): שאלה אחת, בסבב הראשון, עם שלושה כפתורים. היא נשאלת שוב רק כשהמשתמש
# מבקש לשנות, או בסבב חדש שבו המצב השתנה (round_tools.py questions --ask-stance). היא קובעת את נקודת המוצא בכל סעיף;
# היקף הבקשות נקבע בנפרד, ברשימת המאבק (proportionality), כדי שלא יהיו שתי שאלות חופפות
STANCE = {'he': {'text': 'איך להחיל את הפלייבוק בעסקה הזו? לפי הפלייבוק: העמדה שבפלייבוק בכל סעיף. מחמירה: מחזיקים '
                         'בעמדה המועדפת גם במקום שהפלייבוק מתיר לוותר, ומבקשים גם בנושאים משניים. מקלה: מקבלים נוסח '
                         'שלהם שבטווח שהפלייבוק מתיר, ומבקשים רק בנושאים החשובים. מה שלא מקבלים נשאר כך בכל גישה.',
                 'rec': 'לפי הפלייבוק',
                 'opts': ['לפי הפלייבוק (ההמלצה)', 'גישה מחמירה יותר', 'גישה מקלה יותר']},
          'en': {'text': 'How should the playbook be applied in this deal? By the playbook: the playbook position in '
                         'each clause. Stricter: hold the preferred position even where the playbook allows a '
                         'concession, and ask on minor topics too. More lenient: accept their wording where it is '
                         'within the range the playbook allows, and ask only on the important topics. What you '
                         'never accept stays the same in every approach.',
                 'rec': 'By the playbook',
                 'opts': ['By the playbook (recommended)', 'A stricter approach', 'A more lenient approach']}}
# הכפתור (בסדר של opts) והערך שנרשם ב-meta.deal_context.stance
STANCE_VALUES = ('playbook', 'stricter', 'lenient')


# הסכם באנגלית ושם חסר בפרופיל: שאלה מראש, בשורת שאלות התהליך, ולא באמצע ההפקה. התשובה נשמרת ב-build_profile.py
# של רכיב ההקמה (--set branding.lawyer_name_en או organization_name_en)
NAME_EN = {'he': {'lawyer_name_en': ('באיזה שם באנגלית לחתום על ההערות לצד השני?', '<השם באנגלית>'),
                  'entity_name_en': ('מה השם הרשום של החברה באנגלית, כפי שהוא מופיע במרשם?', '<השם הרשום באנגלית>')},
           'en': {'lawyer_name_en': ('Which English name should sign the comments to the other side?',
                                     '<the name in English>'),
                  'entity_name_en': ("What is the company's registered name in English?", '<the registered name>')}}


def english_name_items(profile, lang='he'):
    """שאלות השם באנגלית שחסרות בפרופיל (lawyer_name_en, organization_name_en), כפריטי תהליך במנה."""
    p = profile or {}
    t = NAME_EN[_lang(lang)]
    out = []
    if p.get('lawyer_name') and not p.get('lawyer_name_en'):
        # שם חסר חוסם את העותק למשלוח, ולכן השאלה חוסמת: היא לעולם אינה נחתכת בתקרה ואינה מוכרעת לפי המלצה
        out.append({'key': 'lawyer_name_en', 'kind': 'lawyer_name_en', 'situation': None, 'blocks_sending': True,
                    'text': t['lawyer_name_en'][0], 'options': [t['lawyer_name_en'][1]]})
    if p.get('organization_name') and not p.get('organization_name_en'):
        out.append({'key': 'entity_name_en', 'kind': 'entity_name_en', 'situation': None, 'blocks_sending': True,
                    'text': t['entity_name_en'][0], 'options': [t['entity_name_en'][1]]})
    return out


def stance_item(lang='he'):
    """שאלת הגישה, כפריט במנת השאלות (key: stance, kind: stance). אינה "נדרשת הכרעתך": בלי תשובה חלה ההמלצה,
    לפי הפלייבוק, ונרשמת answer_kind: delegated."""
    t = STANCE[_lang(lang)]
    return {'key': 'stance', 'kind': 'stance', 'text': t['text'], 'recommendation': t['rec'],
            'options': list(t['opts']), 'situation': None, 'blocks_sending': False}


# תנאי ההפעלה של הפלייבוק אינם מתקיימים בצד שכנגד הזה (playbook_resolution.activation_ok: false): שאלה אחת, מצב 4,
# בנוסח האחיד לכל סוגי הצד שכנגד (fixV, 28.10.2026). אין כפתור "לא להחיל" בגלל סוג הצד. "להחיל ולסמן": כל עמדה שסוג
# הצד משנה בה את התוצאה מסומנת "נדרשת הכרעתך". כשיש בפלייבוק סגמנט לסוג הזה, מחילים את הווריאנט שלו ואין שאלה.
# השאלה אינה חוסמת. התשובה נרשמת ב-decide --id playbook_activation
ACTIVATION = {'he': {'text': 'בהסכמים שמהם למדנו את המדיניות אין צד שני מסוג %s. איך להחיל אותה בעסקה הזו?',
                     'rec': 'להחיל ולסמן כל הבדל',
                     'opts': ['להחיל ולסמן כל הבדל (מומלץ)', 'להחיל כמו שהיא']},
              'en': {'text': 'The agreements we learned the policy from have no other party of type %s. How should it '
                             'be applied in this deal?',
                     'rec': 'Apply it and flag every difference',
                     'opts': ['Apply it and flag every difference (recommended)', 'Apply it as is']}}
# אותה שאלה, כשהסיבה היא שאלה פתוחה בפלייבוק על העמדה מול סוג הצד (resolve_playbook, open_question), ולא סוג שלא נצפה
ACTIVATION_OPEN = {'he': 'במדיניות עוד אין עמדה מול צד שני מסוג %s ("%s"). איך להחיל אותה בעסקה הזו?',
                   'en': 'The policy has no position yet for another party of type %s ("%s"). How should it be applied '
                         'in this deal?'}
# אוצר המילים של סוג הצד שכנגד (playbook-schema.md, counterparty_kind), עם התווית בשפת הממשק
KIND_LABELS = {'he': {'public_body': 'גוף ציבורי', 'university': 'מוסד להשכלה גבוהה או אוניברסיטה',
                      'non_profit': 'עמותה, חל"צ, הקדש או מלכ"ר', 'npo': 'עמותה, חל"צ, הקדש או מלכ"ר',
                      'government_company': 'חברה ממשלתית', 'foreign': 'צד זר', 'large_enterprise': 'תאגיד גדול',
                      'large': 'תאגיד גדול', 'sme': 'עסק קטן או בינוני', 'small': 'עסק קטן או בינוני',
                      'consumer': 'צרכן', 'individual': 'אדם, כולל עוסק יחיד', 'company': 'חברה',
                      'group': 'חברה בקבוצה'},
               'en': {'public_body': 'public body', 'university': 'university', 'non_profit': 'non-profit or charity',
                      'npo': 'non-profit or charity', 'government_company': 'government company',
                      'foreign': 'foreign party', 'large_enterprise': 'large enterprise', 'large': 'large enterprise',
                      'sme': 'SME', 'small': 'SME', 'consumer': 'consumer', 'individual': 'individual',
                      'company': 'company', 'group': 'group company'}}


def kind_label(kind, lang='he'):
    """התווית של סוג הצד שכנגד (ערך אחד, רשימה, או כמה ערכים בפסיק) בשפת הממשק."""
    raw = kind if isinstance(kind, (list, tuple)) else str(kind or '').split(',')
    names = KIND_LABELS[_lang(lang)]
    return ', '.join(names.get(str(k).strip().lower(), str(k).strip()) for k in raw if str(k).strip())


def activation_item(resolution, lang='he', kind_segment=None):
    """שאלת ההחלה (key: playbook_activation, מצב 4, אינה חוסמת), או None כשהתנאים מתקיימים, לא נבדקו, או כשיש
    בפלייבוק סגמנט לסוג הצד הזה (kind_segment, או playbook_resolution.kind_segment): אז מחילים את הווריאנט שלו."""
    r = resolution or {}
    if r.get('activation_ok') is not False or kind_segment or r.get('kind_segment'):
        return None
    t = ACTIVATION[_lang(lang)]
    kind = kind_label(r.get('counterparty_kind'), lang) or '?'
    reasons = [x for x in r.get('activation_reasons') or () if isinstance(x, dict)]
    text = t['text'] % kind
    if reasons and all(x.get('code') == 'open_question' for x in reasons):
        text = ACTIVATION_OPEN[_lang(lang)] % (kind, reasons[0].get('question') or reasons[0].get('text') or '')
    return {'key': 'playbook_activation', 'kind': 'activation', 'situation': 4, 'text': text,
            'recommendation': t['rec'], 'options': list(t['opts']), 'blocks_sending': False}


def _lang(lang):
    return 'en' if str(lang or '').lower()[:2] == 'en' else 'he'


def label_for(situation, blocks_sending=False, lang='he'):
    """התווית שהמשתמש רואה: "נדרשת הכרעתך", ובפריט חוסם "(חוסם משלוח, תשובה של מילה אחת)". מספר המצב (1 עד 9)
    נשאר בפריט (situation) ובקובץ המצב, ואינו מוצג: הוא קוד פנימי."""
    if situation not in SITUATIONS:
        raise ValueError('אין מצב עשירי ל"נדרשת הכרעתך": %r' % (situation,))
    lang = _lang(lang)
    t = TXT[lang]
    return '%s (%s)' % (LABEL[lang], t['blocks']) if blocks_sending else LABEL[lang]


def _line(n, it, lang='he'):
    opts = ' '.join('[%s]' % o for o in it.get('options', []))
    rec = (TXT[_lang(lang)]['rec'] % it['recommendation'].rstrip('.')) if it.get('recommendation') else ''
    head = ('**%s:** ' % label_for(it['situation'], it.get('blocks_sending'), lang)) if it.get('situation') else ''
    return ('%d. %s%s%s %s' % (n, head, it['text'].rstrip(), rec, opts)).rstrip()


def answer_type(it):
    """סוג התשובה לשאלה: free (מלל חופשי: סכום, שם, יעד, כשאחת האפשרויות היא תבנית "<...>") או choice (בחירה מתוך
    אפשרויות, או אישור ההמלצה)."""
    return 'free' if any('<' in str(o) and '>' in str(o) for o in it.get('options') or ()) else 'choice'


def build_batch(items, no_consideration=False, asked_before=(), max_questions=8, status_line=None, lang='he',
                strategy=None, round_number=None):
    """items: [{'key', 'text', 'situation' (1..9 או None), 'recommendation', 'options', 'blocks_sending',
    'kind' (למשל 'deal_card_value', 'components', 'counter_tighter', 'composite'), 'clause_ids'}]. strategy: הנתונים
    של האסטרטג (strategy-data.json), שמהם מצוטטים גבול הקו האדום והחבילות לכל פריט שיש לו clause_ids. מחזיר dict:
    text, questions, skipped, requires_explicit (מפתחות הפריטים שתשובה כללית אינה מחילה), memos (תזכירי החלטה)."""
    t = TXT[_lang(lang)]
    L = _lang(lang)
    asked = set(asked_before or ())
    qs, skipped, seen, seen_text = [], [], set(), set()
    for it in items:
        if it.get('situation') is not None and it['situation'] not in SITUATIONS:
            raise ValueError('אין מצב עשירי ל"נדרשת הכרעתך": %r' % (it['situation'],))
        key = it.get('key') or it['text']
        norm = ' '.join(str(it.get('text') or '').split())
        # אותה שאלה פעמיים: אותו מפתח, או אותו נוסח בשני מפתחות (שאלה שהודפסה פעמיים במנה)
        if key in asked or key in seen or (norm and norm in seen_text):
            skipped.append({'key': key, 'why': t['asked']})
            continue
        if norm:
            seen_text.add(norm)
        if no_consideration and it.get('kind') == 'deal_card_value':
            skipped.append({'key': key, 'why': t['free']})
            continue
        seen.add(key)
        it = dict(it)
        it['text'] = it.get('text') or ''
        # הסימונים של האסטרטג על הסעיף: גבול הקו האדום וחבילות, מצוטטים בשאלה (פאנל S1d-R2: 48 השעות סומנו אצלו כגבול
        # הקו האדום, והמנה כתבה "אינה בקו האדום")
        marks = strategy_marks(strategy, item_clause_ids(it), it.get('clause')) if strategy else None
        if marks and (marks.get('red_line_edge') or marks.get('packages')):
            it['strategy_marks'] = marks
            it['red_line_edge'] = bool(marks.get('red_line_edge')) or bool(it.get('red_line_edge'))
            note = marks_text(marks, L)
            if note.strip() not in it['text']:
                it['text'] = it['text'].rstrip() + note
        if it.get('kind') == 'composite':
            it = composite_item(it, L, round_number)
        if it.get('kind') == 'counter_tighter':   # פער 6: מצב 2, עם המלצה; אינה חריגה מקו אדום, אלא כשהאסטרטג סימן אחרת
            it['situation'] = 2
            note = (COUNTER_EDGE[L] % _short((it.get('strategy_marks') or {}).get('red_line_edge', [''])[0] or '?')
                    if it.get('red_line_edge') else COUNTER[L])
            if note.strip() not in it['text']:
                it['text'] = it['text'].rstrip() + note
        why = requires_explicit(it)
        if why:
            # תשובה כללית אינה אישור: הפריט נשאר פתוח עד תשובה מפורשת, ובהתחייבות תפעולית מצטרפת שאלה לגורם הרלוונטי
            it['requires_explicit'] = True
            it['requires_explicit_why'] = why
            # השאלה לגורם האחראי רק בהתחייבות תפעולית עצמה, ולא בכל פריט שמופיעה בו שעה או SLA (פריט מעבר לפלייבוק
            # אינו מקבל אותה)
            if why == 'operational' or it.get('operational'):
                owner = operational_owner(it, L)
                it['owner_question'] = OWNER_Q[L] % owner
                if it['owner_question'].strip() not in it['text']:
                    it['text'] = it['text'].rstrip() + it['owner_question']
                ask_owner = OWNER_OPT[L] % owner
                if ask_owner not in (it.get('options') or ()):
                    it['options'] = list(it.get('options') or ()) + [ask_owner]
            if EXPLICIT_NOTE[L].strip() not in it['text']:
                it['text'] = it['text'].rstrip() + EXPLICIT_NOTE[L]
        if it.get('kind') == 'legal_review':
            continue   # אין שאלת אישור עורך דין בעסקה (כלל יסוד 6): עורך דין מאשר את הפלייבוק בלבד
        qs.append(it)
    # שאלת הגישה ראשונה אחרי החוסמים: היא קובעת את נקודת המוצא לכל השאר
    qs.sort(key=lambda x: (not x.get('blocks_sending'), 0 if x.get('kind') == 'stance' else (x.get('situation') or 99)))
    if len(qs) > max_questions:
        # מאחדים רק שאלות מאותו מצב ועם אותו סוג תשובה: שאלת סכום (מלל חופשי) ושאלת בחירה ("לשלוח בנפרד") אינן באותה
        # טבלה (S1d-R2, מצב 3). שאלת בחירה שדורשת תשובה מפורשת אינה נכנסת לטבלת בחירה, שנענית ב"לאשר את כל ההמלצות";
        # שאלת סכום (מלל חופשי) נענית בסכום עצמו, ולכן נשארת בטבלת הסכומים
        grouped, by_sit = [], {}
        for it in qs:
            if it.get('situation') and not it.get('blocks_sending') and not (
                    it.get('requires_explicit') and answer_type(it) == 'choice'):
                by_sit.setdefault((it['situation'], answer_type(it)), []).append(it)
            else:
                grouped.append(it)
        for (sit, kind), group in sorted(by_sit.items()):
            if len(group) == 1:
                grouped.append(group[0])
                continue
            table = '\n'.join('   | %s | %s |' % (g['text'].rstrip('.'), g.get('recommendation', '')) for g in group)
            grouped.append({'key': 'situation-%d' % sit if kind == 'choice' else 'situation-%d-%s' % (sit, kind),
                            'situation': sit, 'options': list(t['opts']), 'text': t['group'] + table})
        qs = grouped
    # שאלות התהליך (גישה, רכיבים משלימים, הפניה לבונה, שמות באנגלית, שפת הבועות, שם הקובץ) בשורה אחת, אחרונה
    proc = [q for q in qs if q.get('kind') in PROCESS_KINDS and not q.get('situation') and not q.get('blocks_sending')]
    if len(proc) > 1:
        qs = [q for q in qs if q not in proc] + [process_group(proc, L)]
    # תקרה אחת, גלויה: עד max_questions שאלות ממוספרות. כל השאלות נשאלות פעם אחת, בפתיחה, ואין מנה שנייה: שאלה חוסמת
    # ופריט שדורש תשובה מפורשת לעולם אינם נחתכים; הם נכנסים גם מעבר לתקרה, והשורה הראשונה אומרת למה. כל השאר מעבר
    # לתקרה מוכרע לפי ההמלצה ומוצג בטבלת "לאישורך" (applied_by_recommendation). deferred נשאר ריק, לתאימות
    deferred, applied, over = [], [], 0
    if len(qs) > max_questions:
        must = lambda q: q.get('blocks_sending') or q.get('requires_explicit')
        keep = [q for q in qs if must(q)]
        rest = [q for q in qs if not must(q)]
        room = max(0, max_questions - len(keep))
        applied.extend(rest[room:])
        chosen = {id(q) for q in keep + rest[:room]}
        qs = [q for q in qs if id(q) in chosen]
        over = max(0, len(qs) - max_questions)
    head = (COUNT_NONE[L] if not qs else COUNT_ONE[L] if len(qs) == 1 else COUNT_LINE[L] % len(qs)) + \
        ((COUNT_OVER[L] % len([q for q in qs if q.get('blocks_sending') or q.get('requires_explicit')])) if over else '') + \
        ((COUNT_MORE[L] % len(applied)) if applied else '')
    lines = ([status_line] if status_line else []) + [head] + [_line(n, it, lang) for n, it in enumerate(qs, 1)]
    return {'text': '\n'.join(lines), 'questions': qs, 'skipped': skipped,
            'requires_explicit': [q.get('key') for q in qs if q.get('requires_explicit')],
            'memos': [q['memo'] for q in qs if q.get('memo')],
            'deferred': [q.get('key') for q in deferred], 'applied_by_recommendation': [q.get('key') for q in applied]}


# שאלות על התהליך, ולא על ההסכם: נשאלות יחד בשורה אחת, ואינן תופסות מקום של שאלה עסקית
PROCESS_KINDS = ('stance', 'components', 'research_referral', 'file_prefix', 'bubble_language', 'entity_name_en',
                 'lawyer_name_en')
COUNT_LINE = {'he': 'לפני שנכין את התגובה: %d שאלות.', 'en': 'Before we prepare the response: %d questions.'}
COUNT_ONE = {'he': 'לפני שנכין את התגובה: שאלה אחת.', 'en': 'Before we prepare the response: one question.'}
COUNT_NONE = {'he': 'אין שאלות. ממשיכים להכנת התגובה.', 'en': 'No questions. We are preparing the response.'}
COUNT_OVER = {'he': ' %d מהן דורשות את ההכרעה שלכם, ולכן הן כאן גם מעבר ל-8. אחרי התשובות העבודה רצה עד הסוף בלי עצירה.',
              'en': ' %d of them need your decision, so they are here even beyond 8. After your answers the work runs to '
                    'the end without stopping.'}
COUNT_MORE = {'he': ' %d נושאים קטנים הכרענו לפי ההמלצה, ותוכלו לעבור עליהם בסוף.',
              'en': ' We decided %d minor topics by the recommendation; you can review them at the end.'}
PROCESS_HEAD = {'he': 'ועוד כמה שאלות קצרות:', 'en': 'And a few short questions:'}
LETTERS = {'he': 'אבגדהוזחטי', 'en': 'abcdefghij'}


def process_group(items, lang='he'):
    """כמה שאלות תהליך כשאלה ממוספרת אחת: כל אחת באות משלה, עם הכפתורים שלה. group_keys: המפתחות של כל השאלות,
    כדי שכל אחת תירשם כשאלה שנשאלה."""
    L = _lang(lang)
    parts = []
    for n, q in enumerate(items):
        opts = ' '.join('[%s]' % o for o in q.get('options') or ())
        rec = (TXT[L]['rec'] % q['recommendation'].rstrip('.')) if q.get('recommendation') else ''
        parts.append('(%s) %s%s %s' % (LETTERS[L][n % len(LETTERS[L])], q['text'].rstrip(), rec, opts))
    return {'key': 'process', 'kind': 'process', 'situation': None, 'blocks_sending': False,
            'group_keys': [q.get('key') or q.get('text') for q in items], 'options': [],
            'text': PROCESS_HEAD[L] + ' ' + ' '.join(p.rstrip() for p in parts)}


# --------------------------------------------------------------------------- מטריצת הסבבים
# בדיקה עצמאית S1c (28.10.2026): בסבבים 1, 2 ו-3 התגובות צריכות להיות שונות זו מזו באופן מהותי, וזה צריך להיות מוגדר
# וניתן לבדיקה. המטריצה כאן היא המקור האחד (n7-rounds.md, "מטריצת הסבבים"), ו-round_violations
# בודק מולה את קובץ ההכרעות: אורך בועה, פתיח חוזר, ניסוחים אסורים, נסיגה אחרונה, ותלויים בלי נימוק.
ROUND_MATRIX = {
    'opening': {
        'goal': {'he': 'פתיחה: עמדה מלאה ומנומקת', 'en': 'Opening: a full, reasoned position'},
        'retreat': {'he': 'לפי round1_posture: hold_green הירוק; offer_yellow הנסיגה הראשונה בלבד. לעולם לא הנסיגה '
                          'האחרונה', 'en': 'Per round1_posture: hold_green the green; offer_yellow the first fallback '
                                           'only. Never the last fallback'},
        'max_sentences': 4, 'max_words': 100,
        'tone': {'he': 'ענייני ומנומק, בגוף ראשון רבים ("We have..."), בלי פתיח קבוע',
                 'en': 'Factual and reasoned, first person plural ("We have..."), no set opener'},
        'on_acceptance': {'he': 'קבלה של שינוי שלהם: אין בועה. כשהם נימקו בבועה: תשובה בשרשור במשפט עובדתי אחד '
                                '("We accept this change.")', 'en': 'Accepting their change: no comment. If they '
                                'explained it in a comment: a one-sentence factual reply in the thread'}},
    'response': {
        'goal': {'he': 'תגובה: רק מה שהשתנה, והתשובות שלהם בשרשור', 'en': 'Response: only what changed, and their '
                                                                          'replies in the threads'},
        'retreat': {'he': 'מדרגה אחת לכל היותר, תמורת תזוזה שלהם; לא הנסיגה האחרונה. אחרי דחייה אחת: מדרגת ביניים, '
                          'גם כשבפלייבוק נסיגה אחת בלבד: הירוק בלי הרכיבים שהם דחו במפורש ושאינם בקו האדום, ועם '
                          'הנסיגה הראשונה (או זכות הסיום של השירות המושפע). הצעה נגדית שלהם שהדוקה מהנסיגה האחרונה '
                          'אבל סבירה: נדרשת הכרעתך (מצב 2), עם המלצה',
                    'en': 'At most one step, in return for movement on their side; not the last fallback. After one '
                          'rejection: an intermediate step, also when the playbook has a single fallback: the green '
                          'without the components they expressly rejected that are not in the red line, plus the '
                          'first fallback (or the right to end the affected service). A reasonable counter tighter '
                          'than our last fallback: your decision is needed (situation 2)'},
        'max_sentences': 3, 'max_words': 60,
        'tone': {'he': 'משיב לנימוק שלהם ומוסיף רק מה שחדש. בלי "כפי שהסברנו" ובלי לחזור על נימוק שנדחה',
                 'en': 'Answers their reasoning and adds only what is new. No "as explained" and no repeated '
                       'rejected reasoning'},
        'on_acceptance': {'he': 'הצעה שלנו שהתקבלה: אין בועה ואין תשובה, גם לא ל-"Agreed" שלהם. שינוי שלהם '
                                'שקיבלנו: כמו בסבב 1', 'en': 'Our proposal accepted: no comment and no reply, not '
                                'even to their "Agreed". Their change we accept: as in round 1'}},
    'closing': {
        'goal': {'he': 'סגירה: חבילות, ומה שנשאר מוצג למשתמש', 'en': 'Closing: packages, and what is left goes to '
                                                                     'the user'},
        'retreat': {'he': 'הנסיגה האחרונה רק אחרי הצגה בצ\'אט ורישום ב-posture_confirmation. מעבר לה: STUCK או '
                          'WALK-AWAY, נדרשת הכרעתך (מצב 2)',
                    'en': 'The last fallback only after it was shown in chat and recorded in posture_confirmation. '
                          'Beyond it: STUCK or WALK-AWAY, your decision is needed (situation 2)'},
        'max_sentences': 2, 'max_words': 40,
        'tone': {'he': 'סגירה: ניסוח חבילה ("נוכל לקבל X, ובלבד ש-Y"), בלי פתח כללי לשיחה',
                 'en': 'Closing: package wording ("We can accept X, provided that Y"), no general invitation to '
                       'talk'},
        'on_acceptance': {'he': 'כמו בסבב 2, והשרשורים של נושאים שנסגרו מסומנים "בוצע" (round_tools.py '
                                'resolve-threads), ואינם נענים', 'en': 'As in round 2, and threads on closed topics '
                                'are marked done (round_tools.py resolve-threads), with no reply'}},
}
# הסלמה: ברירת המחדל אחרי דחייה היא MOVING, מדרגה אחת בנימוק חדש. STUCK רק כשאותה הצעה שלנו, או המדרגה שאחריה,
# נדחתה בשני סבבים בלי תזוזה שלהם (state_builder.stuck_reason). הסלמה מוקדמת בסבב 2 רק כשהצד השני כתב שהעמדה סופית
# או שאינה נתונה למשא ומתן, או בהוראת המשתמש. רשימת המאבק ו-user_focus אינם סיבה (S1d, 28.10.2026). המסגרת לסיום היא
# 4 סבבים או 6 שבועות
ESCALATION_ROUNDS = 4
ESCALATION_WEEKS = 6
# ניסוחים שאסורים בבועה החיצונית בסבב חוזר: פתיח מתוסרט, התנשאות, ומילה בודדת של הסכמה
BANNED = {
    'all': [r'^\s*(?:agreed|accepted|noted|מוסכם|מקובל|מקובל עלינו)\s*[.!]?\s*$',
            r'ההכרעה הייתה ברורה', r'the (?:decision|position) was clear'],
    'repeat': [r'^\s*(?:as (?:previously |we have )?explained|as (?:stated|noted|mentioned) (?:previously|before|'
               r'above)|further to our (?:previous )?comment)', r'^\s*(?:כפי שהסברנו|כפי שציינו|כאמור בסבב הקודם|'
               r'כאמור בהערתנו)'],
    'closing': [r'happy to discuss|open to discuss|glad to discuss|נשמח לדון|פתוחים לדיון|נשמח לשוחח'],
}
PRECEDENCE = r'גוברות|יגבר|יגברו|עדיפות|prevail|precedence|order of priority'


def round_row(round_number, lang='he'):
    """השורה של הסבב במטריצה, בשפת הממשק: stage, goal, retreat, max_sentences, max_words, tone, on_acceptance."""
    from orchestrator.state_builder import stage_for_round
    stage = stage_for_round(round_number)
    r = ROUND_MATRIX[stage]
    L = _lang(lang)
    return {'stage': stage, 'goal': r['goal'][L], 'retreat': r['retreat'][L], 'max_sentences': r['max_sentences'],
            'max_words': r['max_words'], 'tone': r['tone'][L], 'on_acceptance': r['on_acceptance'][L]}


def _sentences(text):
    import re
    parts = [x for x in re.split(r'(?<=[.!?;])\s+(?=[A-Z"“(א-ת0-9])', (text or '').strip()) if x.strip()]
    return len(parts)


def _words(text):
    return len((text or '').split())


# --------------------------------------------------------------------------- מדרגת ביניים ורכיב שנדחה (S1d-R2)
# אחרי דחייה אחת: מדרגת ביניים, ולא הירוק שוב ולא הנסיגה האחרונה. כשבפלייבוק נסיגה אחת בלבד היא גם האחרונה, ולכן
# מדרגת הביניים נבנית מהירוק ומהנסיגה: מוותרים על רכיבים שהצד השני דחה במפורש ושאינם בקו האדום, ומוסיפים את הנסיגה
# הראשונה (או את זכות הסיום של השירות המושפע). בקובץ ההכרעות: offered_now: intermediate, ו-their_rejected: רשימת
# הרכיבים שהם דחו במפורש, כל אחד מחרוזת או {component, terms, red_line}. no_step_reason: אין מדרגה אפשרית, ולמה
INTERMEDIATE = ('intermediate', 'intermediate_step')
# מילים נרדפות לרכיב שנדחה, כדי שבועה לא תחזור על הטיעון במילה אחרת (עלות / הוצאה)
SYNONYMS = {'cost': ('cost', 'expense', 'charge', 'עלות', 'הוצא', 'חשבון'),
            'expense': ('cost', 'expense', 'charge', 'עלות', 'הוצא', 'חשבון'),
            'report': ('report', 'certification', 'דוח', 'הסמכ'),
            'consent': ('consent', 'approval', 'הסכמה', 'אישור'),
            'עלות': ('cost', 'expense', 'עלות', 'הוצא', 'חשבון'), 'דוח': ('report', 'דוח')}
STOP = {'the', 'and', 'for', 'with', 'that', 'this', 'from', 'any', 'all', 'its', 'their', 'our', 'shall', 'will',
        'of', 'to', 'in', 'on', 'by', 'or', 'be', 'is', 'are', 'a', 'an', 'first', 'party', 'third', 'של', 'על', 'את'}
# משפט שאומר שהרכיב הוסר או שוויתרנו עליו אינו טיעון בו
DROPPED = r'\b(?:removed|deleted|dropped|withdrawn|no longer|we have taken out|we do not (?:pursue|insist))\b|' \
          r'הסרנו|ויתרנו|נמחק|הוסר|אינו עוד|איננו עומדים'
# הצד השני כתב שיחזור עם הצעה: אין שינוי בנוסח ואין טיעון חדש בבועה; שאלה פנימית על היעד ועל הנסיגה
WILL_REVERT = r'\bwill (?:revert|come back|get back|propose|send (?:you )?(?:a|our) (?:proposal|counter))|' \
              r'\btaking instructions\b|\brevert to you\b|נחזור אליכם|נחזור עם הצעה|נעביר הצעה|נבדוק ונחזור'
# סכום בשינוי שלהם (ביטוח, תקרה): שאלה פנימית על הסכום שהחברה מחזיקה בפועל
# בכל מטבע: סימן, קוד ISO-4217 (באותיות גדולות בלבד, כדי ש"for 30" לא ייתפס) או שם המטבע בעברית ובאנגלית,
# לפני הסכום או אחריו
_CUR_CODE = r'(?-i:\b(?:USD|EUR|GBP|ILS|NIS|CHF|SGD|JPY|CNY|RMB|HKD|AUD|CAD|NZD|SEK|NOK|DKK|PLN|CZK|HUF|INR|AED|SAR|ZAR|' \
            r'BRL|MXN|KRW|TRY|RON|BGN|ISK)\b)'
_CUR_WORD = r'(?:ש"ח|ש״ח|שקלים|שקל|ש"ח חדשים|דולר(?:ים)?|אירו|יורו|ליש"ט|ליש״ט|לירות שטרלינג|לירה שטרלינג|פרנק(?:ים)?|ין|' \
            r'dollars?|euros?|pounds? sterling|pounds?|sterling|francs?|yen|shekels?)'
_NUM_AMT = r'\d[\d,.]*(?:\s?(?:million|billion|thousand|m|bn|k|מיליון|מיליארד|אלף))?'
AMOUNT = r'[£$€₪¥₣₹]\s?\d[\d,.]*|' + _CUR_CODE + r'\s?' + _NUM_AMT + r'|\b' + _NUM_AMT + r'\s?(?:' + _CUR_CODE + \
         r'|' + _CUR_WORD + r'(?![\w֐-׿])|million|מיליון)'
INSURANCE = r'insurance|insured|indemnity insurance|cover\b|ביטוח|פוליס'


def _component_terms(item):
    """המילים שמזהות רכיב שנדחה: terms כשנמסרו, ואחרת המילים של שם הרכיב, עם המילים הנרדפות."""
    import re
    if isinstance(item, dict):
        base = list(item.get('terms') or ()) or re.findall(r'[\w֐-׿-]+', str(item.get('component') or ''))
    else:
        base = re.findall(r'[\w֐-׿-]+', str(item or ''))
    out = set()
    for w in base:
        w = w.lower().strip('-')
        if len(w) < 3 or w in STOP:
            continue
        stem = w[:-1] if w.endswith('s') and len(w) > 4 else w
        out.add(stem)
        for k, syn in SYNONYMS.items():
            if stem.startswith(k) or k.startswith(stem):
                out.update(syn)
    return out


def _has_term(text, terms):
    import re
    low = (text or '').lower()
    # בעברית, אותיות שימוש לפני המילה ("העלות", "שהדוחות")
    pre = lambda t: '[והבכלמש]{0,3}' if re.match(r'[א-ת]', t) else ''  # noqa: E731
    return next((t for t in terms if re.search(r'(?<![\w֐-׿])%s%s' % (pre(t), re.escape(t)), low)), None)


def _content_words(s):
    import re
    return {w for w in re.findall(r'[\w֐-׿]+', (s or '').lower()) if len(w) > 2 and w not in STOP}


def thread_of(threads, comment_id):
    """השרשור שמכיל את הבועה comment_id (שורש או תשובה), או None."""
    for t in threads or ():
        if str(t.get('root_id')) == str(comment_id) or any(str(e.get('id')) == str(comment_id)
                                                           for e in t.get('entries') or ()):
            return t
    return None


def rejected_argument_findings(d, previous=(), threads=None):
    """רכיבים שהצד השני דחה במפורש (their_rejected) מול הבועה והנוסח החדשים:
    - ROUND_REJECTED_COMPONENT_REOFFERED: רכיב שאינו בקו האדום חוזר בנוסח החדש.
    - ROUND_REPEATS_REJECTED_ARGUMENT: הבועה חוזרת על טיעון ברכיב שנדחה. רכיב שאינו בקו האדום: כל אזכור שלו בבועה
      (ויתרנו עליו, ואין טוענים עליו). רכיב בקו האדום (נשאר בנוסח): משפט בבועה שחופף, ברוב המילים, למשפט בנימוק
      שלנו מהסבב הקודם על אותו רכיב. previous: הבועות שלנו מהסבב הקודם; בלעדיהן, מהשרשור (threads, reply_to_comment).
    מחזיר [{'code', 'id', 'message'}]."""
    import re
    out = []
    items = d.get('their_rejected') or ()
    if not items:
        return out
    prev = list(previous or ())
    if not prev and d.get('reply_to_comment'):
        t = thread_of(threads, d['reply_to_comment'])
        prev = [e.get('text') or '' for e in (t or {}).get('entries') or () if e.get('ours') and not e.get('new')]
    prev = prev + [x for x in (d.get('previous_external_comment'),) if x]
    bub = d.get('external_comment') or ''
    new = ' '.join(str(d.get(k) or '') for k in ('new', 'new_text', 'text'))
    explicit = (d.get('user_decision') or {}).get('answer_kind') == 'explicit'
    for it in items:
        name = it.get('component') if isinstance(it, dict) else str(it)
        red = isinstance(it, dict) and bool(it.get('red_line'))
        terms = _component_terms(it)
        if not terms:
            continue
        if not red and not explicit and _has_term(new, terms):
            out.append({'code': 'ROUND_REJECTED_COMPONENT_REOFFERED', 'id': d.get('id'),
                        'message': 'הרכיב "%s" נדחה במפורש ואינו בקו האדום, והוא חוזר בנוסח החדש. מדרגת ביניים '
                                   'מוותרת עליו' % name})
        sents = [s for s in _split_sentences(bub) if _has_term(s, terms)]
        if not sents:
            continue
        if not red:
            # משפט שאומר שוויתרנו על הרכיב אינו טיעון בו
            sents = [s for s in sents if not re.search(DROPPED, s, re.I)]
            if not sents:
                continue
            out.append({'code': 'ROUND_REPEATS_REJECTED_ARGUMENT', 'id': d.get('id'),
                        'message': 'הבועה חוזרת על טיעון ברכיב שהצד השני דחה ("%s"): "%s". רכיב שוויתרנו עליו אינו '
                                   'נטען שוב' % (name, sents[0][:90])})
            continue
        old = [s for t in prev for s in _split_sentences(t) if _has_term(s, terms)]
        for s in sents:
            ws = _content_words(s)
            if any(ws and len(ws & _content_words(o)) >= 0.5 * len(ws) for o in old):
                out.append({'code': 'ROUND_REPEATS_REJECTED_ARGUMENT', 'id': d.get('id'),
                            'message': 'הבועה חוזרת על הנימוק שלנו מהסבב הקודם ברכיב שנדחה ("%s"): "%s". עונים לנימוק '
                                       'שלהם, או מוסיפים נימוק חדש' % (name, s[:90])})
                break
    return out


def _split_sentences(text):
    import re
    return [x.strip() for x in re.split(r'(?<=[.!?;])\s+', (text or '').strip()) if x.strip()]


def round_violations(decisions, round_number, state=None, lang='he', threads=None):
    """הבדיקה של קובץ ההכרעות מול מטריצת הסבבים. מחזיר [{'code', 'id', 'message'}]; ריק כשהכול תקין.
    ROUND_COMMENT_LONG: בועה ארוכה מהמותר בסבב. ROUND_REPEATED_OPENING: שלוש בועות או יותר שפותחות באותן ארבע מילים
    (פער 4). ROUND_BANNED_PHRASE: ניסוח אסור (מילה בודדת של הסכמה, "כפי שהסברנו" בסבב חוזר, התנשאות, פתח כללי
    לשיחה בסבב סגירה). ROUND_LAST_FALLBACK: נסיגה אחרונה בסבב 1 או 2, או בסבב 3 בלי posture_confirmation או הכרעה
    מפורשת. ROUND_EARLY_STUCK: status STUCK בקובץ ההכרעות לפני סבב 3, בלי הוראה מפורשת של המשתמש (user_decision
    explicit) ובלי escalation_basis: final_position (S1d).
    DEPENDENT_KEEP_NO_REASON / DEPENDENT_KEEP_PRECEDENCE: תלוי שנשאר בלי נימוק, או שנשען רק על סעיף
    "גוברות" (M4).
    S1d-R2 (28.10.2026), מסבב 2: ROUND_HOLD_AFTER_REJECTION: אחרי דחייה שלהם בסבב הזה (their_rejected, או דחייה שלהם
    בסעיף בקובץ המצב) ההכרעה מחזירה את הירוק (offered_now: green) בלי מדרגת ביניים, בלי no_step_reason ובלי הכרעה
    מפורשת של המשתמש. ROUND_REJECTED_COMPONENT_REOFFERED ו-ROUND_REPEATS_REJECTED_ARGUMENT
    (rejected_argument_findings, עם threads: השרשורים מהשוואת הסבב). ROUND_ARGUES_PENDING_PROPOSAL: הצד השני כתב
    בשרשור שיחזור עם הצעה, וההכרעה משנה את הנוסח או מוסיפה בבועה יותר ממשפט אחד."""
    import re
    from orchestrator.state_builder import stage_for_round
    decs = (decisions or {}).get('decisions', []) if isinstance(decisions, dict) else list(decisions or [])
    stage = stage_for_round(round_number)
    row = ROUND_MATRIX[stage]
    out = []
    confirmed = {i.get('clause_id') for i in ((state or {}).get('posture_confirmation') or {}).get('items') or ()}
    rejected_now = {c.get('clause_id') for c in (state or {}).get('clauses') or ()
                    if any(isinstance(r, dict) and r.get('by') == 'them' and int(r.get('round') or 0) == int(round_number)
                           for r in c.get('rejections') or ())}
    openings = {}
    for d in decs:
        did = d.get('id')
        if stage != 'opening':
            explicit = (d.get('user_decision') or {}).get('answer_kind') == 'explicit'
            if (d.get('their_rejected') or did in rejected_now) and d.get('offered_now') == 'green' \
                    and d.get('op') in ('replace', 'replace_span', 'insert_paragraph') and not explicit \
                    and not (d.get('no_step_reason') or '').strip() and d.get('status') != 'STUCK':
                out.append({'code': 'ROUND_HOLD_AFTER_REJECTION', 'id': did,
                            'message': 'אחרי דחייה אחת ההכרעה מחזירה את הירוק. ברירת המחדל היא מדרגת ביניים '
                                       '(offered_now: intermediate), גם כשבפלייבוק נסיגה אחת בלבד: הירוק בלי הרכיבים '
                                       'שהם דחו במפורש ושאינם בקו האדום, ועם הנסיגה הראשונה, או זכות הסיום של השירות '
                                       'המושפע. אין מדרגה אפשרית: no_step_reason'})
            out += rejected_argument_findings(d, threads=threads)
            t = thread_of(threads, d.get('reply_to_comment')) if d.get('reply_to_comment') else None
            if t and any(e.get('new') and not e.get('ours') and re.search(WILL_REVERT, e.get('text') or '', re.I)
                         for e in t.get('entries') or ()):
                if d.get('op') in ('replace', 'replace_span', 'insert_paragraph', 'delete_paragraph') or \
                        _sentences(d.get('external_comment') or '') > 1:
                    out.append({'code': 'ROUND_ARGUES_PENDING_PROPOSAL', 'id': did,
                                'message': 'הצד השני כתב שיחזור עם הצעה: אין שינוי בנוסח ואין טיעון חדש בבועה (משפט '
                                           'אחד לכל היותר). היעד והנסיגה לסבב הבא נקבעים בשאלה פנימית'})
            # עמדה חדשה שלנו בשרשור פתוח שבו ההצעה הקודמת שלנו עדיין עומדת: התשובה אומרת שהיא מחליפה אותה (פאנל S1e-R3:
            # הבועה הישנה על 18.4 נשארה פתוחה לצד הנוסח החדש). בועה חדשה שאינה בשרשור: resolve-threads מסמן את הישנה "בוצע"
            if t and t.get('root_ours') and not t.get('done') and d.get('op') in CHANGE_OPS \
                    and any(e.get('ours') and not e.get('new') for e in t.get('entries') or ()) \
                    and not re.search(REPLACES_RE, d.get('external_comment') or '', re.I):
                out.append({'code': 'ROUND_STALE_PROPOSAL', 'id': did,
                            'message': 'עמדה חדשה בשרשור %s, שבו ההצעה הקודמת שלנו עדיין עומדת: התשובה פותחת ב-"%s"'
                                       % (t.get('root_id'), REPLACES[_bubble_lang(d.get('external_comment'))])})
        text = (d.get('external_comment') or '').strip()
        if text:
            # המשפט "This replaces our earlier proposal." אינו נספר באורך הבועה ואינו פתיח חוזר
            body = re.sub(REPLACES_SENT, ' ', text, flags=re.I).strip() or text
            n_s, n_w = _sentences(body), _words(body)
            if n_s > row['max_sentences'] or n_w > row['max_words']:
                out.append({'code': 'ROUND_COMMENT_LONG', 'id': did,
                            'message': 'בועה של %d משפטים ו-%d מילים; בסבב %s עד %d משפטים ו-%d מילים'
                                       % (n_s, n_w, stage, row['max_sentences'], row['max_words'])})
            key = ' '.join(re.sub(r'[^\w֐-׿ ]', ' ', body.lower()).split()[:4])
            if len(key.split()) == 4:
                openings.setdefault(key, []).append(did)
            pats = BANNED['all'] + (BANNED['repeat'] if stage != 'opening' else []) + \
                (BANNED['closing'] if stage == 'closing' else [])
            for rx in pats:
                if re.search(rx, text, re.I):
                    out.append({'code': 'ROUND_BANNED_PHRASE', 'id': did, 'message': 'ניסוח אסור בסבב %s: %s'
                                % (stage, re.search(rx, text, re.I).group(0).strip())})
                    break
        if d.get('status') == 'STUCK' and stage != 'closing' and d.get('escalation_basis') != 'final_position' \
                and (d.get('user_decision') or {}).get('answer_kind') != 'explicit':
            out.append({'code': 'ROUND_EARLY_STUCK', 'id': did,
                        'message': 'STUCK בסבב %s בלי בסיס: ברירת המחדל אחרי דחייה אחת היא MOVING, מדרגה אחת בנימוק חדש. '
                                   'הסלמה מוקדמת רק כשהצד השני כתב שהעמדה סופית (escalation_basis: final_position) או '
                                   'בהוראה מפורשת של המשתמש' % stage})
        last = d.get('at_last_fallback') or d.get('offered_now') == 'last_fallback'
        if last:
            ok = stage == 'closing' and (did in confirmed or (d.get('user_decision') or {}).get('answer_kind') ==
                                         'explicit')
            if not ok:
                out.append({'code': 'ROUND_LAST_FALLBACK', 'id': did,
                            'message': 'נסיגה אחרונה בסבב %s%s' % (stage, '' if stage == 'closing' else
                                                                   ': מותרת רק מסבב 3, אחרי הצגה בצ\'אט')
                            + ('' if stage != 'closing' else ' בלי רישום ב-posture_confirmation')})
        for dep in d.get('dependents') or ():
            if isinstance(dep, dict) and dep.get('keep'):
                reason = (dep.get('reason') or '').strip()
                if not reason:
                    out.append({'code': 'DEPENDENT_KEEP_NO_REASON', 'id': did,
                                'message': 'תלוי (פסקה %s) נשאר בלי נימוק' % dep.get('para')})
                elif re.search(PRECEDENCE, reason, re.I) and len(reason.split()) < 25:
                    out.append({'code': 'DEPENDENT_KEEP_PRECEDENCE', 'id': did,
                                'message': 'תלוי (פסקה %s) נשאר בהסתמך על סעיף גוברות, שהצד השני עלול לדחות: '
                                           'הכרעה עקבית בתלוי עצמו' % dep.get('para')})
    for key, ids in openings.items():
        if len(ids) > 2:
            out.append({'code': 'ROUND_REPEATED_OPENING', 'id': ', '.join(str(x) for x in ids),
                        'message': '%d בועות פותחות ב-"%s": בלי פתיח מתוסרט שחוזר' % (len(ids), key)})
    return out


# הצעה נגדית שלהם שהדוקה מהנסיגה האחרונה שלנו, אבל סבירה (פער 6): נדרשת הכרעתך, מצב 2, עם המלצה לגופו של עניין
COUNTER = {'he': ' זו אינה חריגה מקו אדום: הנוסח שלהם אינו מבטל את ההגנה, רק הדוק מהנסיגה. ההמלצה לגופו של עניין.',
           'en': ' This is not a red-line exception: their wording does not remove the protection, it is only '
                 'tighter than our fallback. The recommendation is on the merits.'}


ESCALATION_WHY = {'he': {'rejected_twice': 'ההצעה שלנו, או המדרגה שאחריה, נדחתה בשני סבבים בלי תזוזה שלהם',
                         'final_position': 'הצד השני כתב שהעמדה שלו סופית'},
                  'en': {'rejected_twice': 'our proposal, or the next step after it, was rejected in two rounds with no '
                                           'movement on their side',
                         'final_position': 'the other side wrote that its position is final'}}


AMOUNT_REC = {'he': {'silent': 'לסמן מול הנוסח שחזר, עם הסכום שהחברה מחזיקה בפועל, ולא להחזיר גורפת לנוסח שנשלח',
                     'cert': '; אישור ביטוח (certificate of insurance) במקום הפוליסה',
                     'opts': ['לסמן מול הנוסח שחזר, עם הסכום בפועל'],
                     'q': 'השינוי שלהם בסעיף %s נוגע לסכום (%s%s). מה הסכום שהחברה מחזיקה בפועל?',
                     'ins': ', ביטוח', 'q_opts': ['<הסכום בפועל>', 'לא ידוע: להחזיר לנוסח שנשלח']},
              'en': {'silent': 'Mark against the returned wording, with the amount the company actually holds, rather '
                               'than a blanket revert to the sent wording',
                     'cert': '; a certificate of insurance instead of the policy',
                     'opts': ['Mark against the returned wording, with the actual amount'],
                     'q': 'Their change in clause %s concerns an amount (%s%s). What amount does the company actually '
                          'hold?', 'ins': ', insurance', 'q_opts': ['<the actual amount>', 'Unknown: revert to the sent '
                                                                                         'wording']}}
PREPARE = {'he': {'text': 'בסעיף %s הצד השני כתב שיחזור עם הצעה ("%s"). מה היעד שלנו, ומה הנסיגה, כדי להיות מוכנים '
                          'לסבב הבא?',
                  'rec': 'לקבוע עכשיו, פנימית, יעד ונסיגה. בסבב הזה אין שינוי בנוסח ואין טיעון חדש בבועה',
                  'opts': ['יעד: <..>; נסיגה: <..>', 'לקבוע כשתגיע ההצעה']},
           'en': {'text': 'In clause %s the other side wrote that it will come back with a proposal ("%s"). What is our '
                          'target, and our fallback, so that we are ready for the next round?',
                  'rec': 'Set the target and the fallback now, internally. In this round: no change to the wording and '
                         'no new argument in the comment',
                  'opts': ['Target: <..>; fallback: <..>', 'Decide when the proposal arrives']}}


def diff_window(a, b, ctx=60, mark=True):
    """("נשלח", "חזר") כחלון סביב ההבדל: ctx תווים לפניו ואחריו, "..." במקום מה שנחתך, וההבדל עצמו מודגש (**...**)
    כש-mark. השאלה על שינוי שקט קטעה את הנוסח לפני מקום השינוי (S1e-R3, 6(h)). שני נוסחים זהים: ההתחלה בלבד."""
    a, b = ' '.join((a or '').split()), ' '.join((b or '').split())
    k = 0
    while k < min(len(a), len(b)) and a[k] == b[k]:
        k += 1
    e = 0
    while e < min(len(a), len(b)) - k and a[len(a) - 1 - e] == b[len(b) - 1 - e]:
        e += 1
    # ההבדל מתחיל ונגמר בגבול מילה (מספר עם פסיקים הוא מילה אחת), כדי שהקטע המודגש יהיה קריא
    def tok(ch):
        return bool(ch) and (ch.isalnum() or ch in ',.')

    def inner(s, i):
        return tok(s[i:i + 1])
    if inner(a, k) or inner(b, k):
        while k > 0 and tok(a[k - 1]):
            k -= 1
    if inner(a, len(a) - e - 1) or inner(b, len(b) - e - 1):
        while e > 0 and tok(a[len(a) - e]):
            e -= 1

    def cut(s):
        mid_end = len(s) - e
        start, stop = max(0, k - ctx), min(len(s), mid_end + ctx)
        if start and ' ' in s[start:k]:
            start = s.index(' ', start, k) + 1
        if stop < len(s) and ' ' in s[mid_end:stop]:
            stop = s.rindex(' ', mid_end, stop)
        mid = s[k:mid_end]
        if mark:
            # רווח בקצה הקטע יוצא מחוץ להדגשה; צד ריק מסומן [ריק]
            core = mid.strip()
            lead, trail = mid[:len(mid) - len(mid.lstrip())], mid[len(mid.rstrip()):] if core else ''
            mid = lead + ('**%s**' % core if core else '**[ריק]**') + trail
            if not core and s[mid_end:mid_end + 1] not in ('', ' '):
                mid += ' '
            if not core and s[k - 1:k] not in ('', ' '):
                mid = ' ' + mid
        return ('...' if start else '') + s[start:k] + mid + s[mid_end:stop] + ('...' if stop < len(s) else '')
    if a == b:
        return (a[:2 * ctx] + ('...' if len(a) > 2 * ctx else ''),) * 2
    return cut(a), cut(b)


def amount_item(clause, amount, insurance, round_number, para, lang='he'):
    """שאלה פנימית על הסכום שהחברה מחזיקה בפועל: מצב 3 (עובדה עסקית חסרה: סכום), אינה חוסמת משלוח."""
    L = _lang(lang)
    t = AMOUNT_REC[L]
    return {'key': 'amount:r%s:%s' % (round_number, para), 'kind': 'internal_amount', 'situation': 3,
            'blocks_sending': False, 'text': t['q'] % (clause, amount, t['ins'] if insurance else ''),
            'recommendation': t['silent'] + (t['cert'] if insurance else ''), 'options': list(t['q_opts'])}


def round_items(compare=None, state=None, round_number=None, lang='he', strategy=None):
    """הפריטים שהסבב מוסיף למנת השאלות, מתוך השוואת הסבב (compare_rounds.py) ומקובץ המצב:
    - שינוי שקט: מצב 9, חוסם משלוח (H6), עם הנוסח שנשלח והנוסח שחזר, ושלוש אפשרויות: להחזיר, לקבל עם בועה, לקבל
      בתנאי (פאנל S1e-R3).
    - יעד שנמסר לפני שהגיעה הצעה שלהם (prepare:...), כשההצעה הגיעה בסעיף כמותי: נשאל מחדש, רכיב אחר רכיב, ובסבב סגירה
      כשההצעה שלהם מעבר לנסיגה האחרונה גם תזכיר החלטה (stale_target_items, פאנל S1e-R3, 18.4).
    - בסבב סגירה: קבלה שעומדת לשיחה שלא התקיימה היא "נדרשת הכרעתך" (מצב 5): להעלות עכשיו בכתב, או לוותר ביודעין.
    - ויתור מכוון על נושא מסחרי מחייב (proportionality.commercial_topic) בלי תשובה מפורשת: שאלה נפרדת (מצב 5).
    - שינוי שלהם (שקט או מסומן) שנוגע לסכום (ביטוח, תקרה): שאלה פנימית על הסכום שהחברה מחזיקה בפועל (מצב 3), וההמלצה
      בשינוי השקט היא לסמן מול הנוסח שחזר עם הסכום האמיתי (ואישור ביטוח במקום הפוליסה), ולא החזרה גורפת (S1d-R2).
    - הצד השני כתב שיחזור עם הצעה: שאלה פנימית על היעד ועל הנסיגה, בלי שינוי בנוסח ובלי טיעון חדש (S1d-R2).
    - פתיחה מחדש של סעיף מוסכם בידי הצד השני (reopened_by_counterparty): ברירת המחדל להחזיר.
    - מונח שהגדרתו נמחקה בנוסח שלהם (פער 12).
    - STUCK (escalation, לפי state_builder.stuck_reason): הצעה לשיחה (פער 7). לא בגלל רשימת המאבק או user_focus.
    - קבלה שעומדת לשיחה (ACCEPTED_PENDING עם held_for): האם השיחה התקיימה."""
    import re
    from orchestrator.state_builder import stage_for_round
    L = _lang(lang)
    he = L == 'he'
    closing = bool(round_number) and stage_for_round(round_number) == 'closing'
    items = []
    seen = set()
    held_now = set()
    # יעד שנמסר לפני ההצעה שלהם: פריט אחד לסעיף, רכיב אחר רכיב, במקום שאלת הסכום הכללית על אותה פסקה
    stale = stale_target_items(compare, state, round_number, L, strategy)
    stale_paras = {x.get('para') for x in stale}
    for c in (compare or {}).get('clauses') or ():
        if c.get('classification') not in ('their_silent', 'their_tracked'):
            continue
        para = c.get('received_para') if c.get('received_para') is not None else c.get('sent_para')
        # שינוי שלהם (שקט או מסומן) שנוגע לסכום (ביטוח, תקרה): שאלה פנימית על הסכום שהחברה מחזיקה בפועל (S1d-R2)
        back = c.get('they_opened_with') if c.get('classification') == 'their_silent' else c.get('they_added')
        amounts = [a for a in re.findall(AMOUNT, back or '', re.I) if a not in (c.get('we_sent') or '')]
        ins = bool(re.search(INSURANCE, back or '', re.I))
        if amounts and para not in stale_paras:
            items.append(amount_item(c.get('clause') or '?', amounts[0], ins, round_number, para, L))
        if c.get('classification') != 'their_silent':
            continue
        key = 'silent:r%s:%s' % (round_number, para)
        seen.add(key)
        # חלון סביב ההבדל, וההבדל מודגש, ולא תחילת הפסקה (S1e-R3: הנוסח נקטע לפני מקום השינוי)
        sent_s, back_s = diff_window(c.get('we_sent'), c.get('they_opened_with'))
        if not he:
            sent_s, back_s = sent_s.replace('**[ריק]**', '**[empty]**'), back_s.replace('**[ריק]**', '**[empty]**')
        reopen = ' (סעיף מוסכם)' if he and c.get('reopens_closed') else (' (an agreed clause)' if c.get('reopens_closed')
                                                                         else '')
        rec = ('להחזיר בעקוב אחר שינויים לנוסח שנשלח, עם בועה עניינית שהשינוי לא סומן' if he else
               'Revert to the sent wording in tracked changes, with a factual comment that the change was not marked')
        if c.get('reopens_closed'):
            # החזרה לנוסח המוסכם אינה פתיחה מחדש מצדנו: הסעיף נשאר CLOSED, וההכרעה kind: restore_agreed (S1e-R3)
            rec += ('. בסעיף מוסכם זו החזרה לנוסח המוסכם (kind: restore_agreed), ולא פתיחה מחדש: הסעיף נשאר מוסכם'
                    if he else '. In an agreed clause this restores the agreed wording (kind: restore_agreed), and is '
                               'not a reopening: the clause stays agreed')
        opts = ['להחזיר', 'לקבל, עם בועה'] if he else ['Revert', 'Accept, with a comment']
        # אפשרות שלישית: לקבל בתנאי (פאנל S1e-R3, 6(h)). שינוי שמוסיף אישור או הסכמה שלהם: התנאי המוצע הוא שהאישור לא
        # יסורב או יעוכב שלא באופן סביר. בסעיף שאינו מוסכם זו ההמלצה; בסעיף מוסכם ההמלצה נשארת החזרה, והקבלה בתנאי
        # היא פתיחה מחדש בהוראה רשומה
        cond = COND_WORDING[_bubble_lang(c.get('we_sent'))] if re.search(
            APPROVAL, c.get('they_opened_with') or '', re.I) and not re.search(APPROVAL, c.get('we_sent') or '', re.I) \
            else None
        opts = opts + [CONDITION[L]['opt'] % (cond or CONDITION[L]['generic'])]
        if cond and not c.get('reopens_closed') and not amounts:
            rec = CONDITION[L]['rec'] % cond
        elif cond:
            rec += CONDITION[L]['alt'] % cond
        if amounts:
            # סכום: לסמן מול הנוסח שחזר, עם הסכום האמיתי (שאלה פנימית), ולא החזרה גורפת לנוסח שנשלח
            rec = AMOUNT_REC[L]['silent'] + (AMOUNT_REC[L]['cert'] if ins else '')
            opts = AMOUNT_REC[L]['opts'] + opts
        items.append({'key': key, 'kind': 'silent_change', 'situation': 9, 'blocks_sending': True,
                      'text': ('שינוי שלא סומן בסעיף %s%s. נשלח: "%s". חזר: "%s".' if he else
                               'Unmarked change in clause %s%s. Sent: "%s". Returned: "%s".')
                      % (c.get('clause') or '?', reopen, sent_s, back_s),
                      'recommendation': rec, 'options': opts})
    # הצד השני כתב שיחזור עם הצעה: שאלה פנימית על היעד ועל הנסיגה שלנו, כדי להיות מוכנים לסבב הבא (S1d-R2)
    for t in (compare or {}).get('threads') or ():
        hit = next((e for e in t.get('entries') or () if e.get('new') and not e.get('ours')
                    and re.search(WILL_REVERT, e.get('text') or '', re.I)), None)
        if hit:
            q = ' '.join((hit.get('text') or '').split())[:160]
            items.append({'key': 'prepare:%s:r%s' % (t.get('root_id'), round_number), 'kind': 'internal_prepare',
                          'situation': None, 'blocks_sending': False,
                          'text': (PREPARE[L]['text'] % (t.get('clause') or t.get('para') or '?', q)),
                          'recommendation': PREPARE[L]['rec'], 'options': list(PREPARE[L]['opts'])})
    for c in (state or {}).get('clauses') or ():
        cid = c.get('clause_id')
        ref = c.get('contract_ref') or cid
        rb = c.get('reopened_by_counterparty') or {}
        if rb and int(rb.get('round') or 0) == int(round_number or rb.get('round') or 0) \
                and 'their_silent' not in (rb.get('classification') or ()):
            items.append({'key': 'reopened:%s:r%s' % (cid, rb.get('round')), 'kind': 'reopened_closed', 'situation': None,
                          'text': ('הצד שכנגד פתח מחדש סעיף מוסכם: %s.' if he else
                                   'The other side reopened an agreed clause: %s.') % ref,
                          'recommendation': ('להחזיר בעקוב אחר שינויים לנוסח המוסכם, עם בועה קצרה שהנוסח הוסכם'
                                             if he else 'Revert to the agreed wording, with a short comment'),
                          'options': (['להחזיר', 'לקבל את הפתיחה (הוראה רשומה)'] if he else
                                      ['Revert', 'Accept the reopening (recorded instruction)'])})
        esc = c.get('escalation') or {}
        if c.get('status') == 'STUCK' and esc and int(esc.get('round') or 0) == int(round_number or esc.get('round')) \
                and esc.get('basis') != 'user_instruction':
            why = ESCALATION_WHY[L].get(esc.get('basis'), ESCALATION_WHY[L]['rejected_twice'])
            items.append({'key': 'escalation:%s:r%s' % (cid, esc.get('round')), 'kind': 'escalation', 'situation': None,
                          'text': ('%s: %s (STUCK). מוצעת שיחה לפני סבב נוסף.' if he else
                                   '%s: %s (STUCK). A call before another round is proposed.') % (ref, why),
                          'recommendation': ('שיחה בין הצדדים לפני סבב נוסף, ובבועה רק ההצעה לשיחה והנימוק החדש'
                                             if he else 'A call before another round, and in the comment only the '
                                                        'call proposal and the new reasoning'),
                          'options': (['להציע שיחה', 'מדרגה אחת עם נימוק חדש', 'להחזיק'] if he else
                                      ['Propose a call', 'One step with new reasoning', 'Hold'])})
        if c.get('status') == 'ACCEPTED_PENDING' and c.get('held_for') == 'talking_point':
            if closing:
                # סבב סגירה: נקודה לשיחה שלא התקיימה היא "נדרשת הכרעתך": להעלות עכשיו בכתב, או לוותר ביודעין (פאנל
                # S1e-R3: 15.2 נשאר לשיחה שלושה סבבים). נושא מסחרי מחייב: ההמלצה להעלות בכתב
                topic = commercial_of(state, cid)
                T = HELD_CLOSING[L]
                items.append({'key': 'held:%s:r%s' % (cid, round_number), 'kind': 'held_for_call', 'situation': 5,
                              'clause_ids': [cid], 'requires_explicit': True, 'commercial_topic': topic,
                              'text': T['text'] % (ref, (T['commercial'] % P.COMMERCIAL_LABELS[L][topic]) if topic
                                                   else ''),
                              'recommendation': T['rec_raise'] if topic else T['rec_waive'],
                              'options': list(T['opts'])})
                held_now.add(cid)
                continue
            items.append({'key': 'held:%s:r%s' % (cid, round_number), 'kind': 'held_for_call', 'situation': None,
                          'text': ('%s עומד לשיחה. השיחה התקיימה, ומה סוכם?' if he else
                                   '%s is held for the call. Did the call take place, and what was agreed?') % ref,
                          'recommendation': ('לא להעלות בכתב בלי הוראה' if he else 'Do not raise it in writing '
                                                                                  'without an instruction'),
                          'options': (['לא התקיימה', 'התקיימה: <מה סוכם>'] if he else
                                      ['Not yet', 'It did: <what was agreed>'])})
            held_now.add(cid)
    for t in (compare or {}).get('orphaned_terms') or ():
        items.append({'key': 'term:%s' % t.get('term'), 'kind': 'orphaned_term', 'situation': None,
                      'text': ('המונח "%s" משמש ב-%s, וההגדרה שלו (ב-%s) נמחקה בנוסח שלהם.' if he else
                               'The term "%s" is used in %s, and its definition (in %s) was deleted in their '
                               'wording.') % (t.get('term'), ', '.join(x for x in t.get('used_in') or () if x) or '?',
                                              t.get('defined_in') or '?'),
                      'recommendation': ('להחזיר את ההגדרה בעקוב אחר שינויים, או לתקן את הסעיף שמשתמש במונח'
                                         if he else 'Restore the definition in tracked changes, or fix the clause '
                                                    'that uses the term'),
                      'options': (['להחזיר את ההגדרה', 'לתקן את הסעיף'] if he else
                                  ['Restore the definition', 'Fix the clause'])})
    items += stale
    items += commercial_items(state, L, skip=held_now)
    return items


# --------------------------------------------------------------------------- תשובה כללית אינה אישור (פאנל S1d-R2, S1e-R3)
# "תציגו לנו לאישור", "אין לנו מידע נוסף" ו"תפעלו לפי ההמלצה" אינם מחילים הכרעה במצב 2 (מעבר לפלייבוק), ב-counter_tighter,
# בהכרעה על סכום, בנושא שהאסטרטג סימן כגבול הקו האדום, ובהתחייבות תפעולית (שעות הודעה, SLA). הפריט נשאר פתוח ונשאל שוב
# במפורש (state_builder.record_user_decision, held_requires_explicit), ובהתחייבות תפעולית מצטרפת שאלה לגורם הרלוונטי.
# השער קורא את אותה פונקציה על decision_required של כל הכרעה (requires_explicit(dr, decision=d))
EXPLICIT_NOTE = {'he': ' כאן צריך תשובה שלכם לנושא הזה עצמו; "תפעלו לפי ההמלצה" לא מספיק.',
                 'en': ' This needs your own answer on this topic; "follow the recommendation" is not enough.'}
AMOUNT_KINDS = ('internal_amount', 'composite', 'stale_target')
OPERATIONAL = r'\b\d+\s*(?:hours?|business days?|working days?|minutes?)\b|\bSLA\b|\buptime\b|response time|' \
              r'\d+\s*(?:שעות|דקות|ימי עבודה)|זמן תגובה|זמינות השירות|רמת שירות'
# הגורם שנשאל נקבע לפי צירוף מובהק, ולא לפי מילה כללית: "אירוע" (ביטוחי, כוח עליון, הפרה, Event of Default),
# "security" (security deposit, security interest) ו"ביטחונות" (בטוחות) אינם אבטחת מידע. התחייבות במועד בלבד
# (הודעה תוך 48 שעות על נזק) הולכת לגורם האחראי בחברה, ולא לתפעול
SECURITY = r'(?:information|data|cyber|IT)\s+security|security\s+(?:incident|breach|event|measures)|data\s+(?:breach|loss)|' \
           r'personal data breach|cyber|clearance|vetting|אבטחת (?:ה)?מידע|אירוע (?:אבטח|סייבר)|סייבר|' \
           r'דליפ(?:ת|ה) (?:ה)?מידע|פריצה למערכ|סיווג ביטחוני|בדיקה ביטחונית'
OPS_OWNER = r'\bSLA\b|\buptime\b|response time|service levels?|זמן תגובה|זמינות השירות|רמ(?:ת|ות) (?:ה)?שירות'
OWNERS = {'he': {'security': 'אבטחת המידע', 'operations': 'התפעול', 'other': 'הגורם האחראי בחברה'},
          'en': {'security': 'information security', 'operations': 'operations', 'other': 'the responsible team'}}
OWNER_Q = {'he': ' שאלה אל %s: האם אפשר לעמוד בזה בפועל?', 'en': ' Question for %s: can this be met in practice?'}
OWNER_OPT = {'he': 'לבדוק קודם עם %s', 'en': 'Check with %s first'}
# הצעה נגדית הדוקה מהנסיגה בנושא שהאסטרטג סימן כגבול הקו האדום: אינה "הצעה סבירה רגילה"
COUNTER_EDGE = {'he': ' האסטרטג סימן את הנושא כגבול הקו האדום ("%s"): זו הכרעה על הקו האדום, ולא הצעה נגדית סבירה '
                      'רגילה.',
                'en': ' The strategist marked this topic as the edge of the red line ("%s"): this is a red-line '
                      'decision, not an ordinary reasonable counter.'}


def _blob(it):
    return ' '.join(str(it.get(k) or '') for k in ('text', 'gap', 'recommendation'))


def is_operational(it):
    """התחייבות תפעולית (שעות הודעה, ימי עבודה, SLA, זמינות): operational בפריט, או במילים של השאלה."""
    import re
    return bool((it or {}).get('operational')) or bool(re.search(OPERATIONAL, _blob(it or {}), re.I))


def operational_owner(it, lang='he'):
    """הגורם שנשאל על התחייבות תפעולית: owner בפריט; אבטחת המידע רק באירוע אבטחה או דליפת מידע; התפעול ברמת
    שירות וזמינות; ואחרת הגורם האחראי בחברה."""
    import re
    L = _lang(lang)
    if (it or {}).get('owner'):
        return it['owner']
    if re.search(SECURITY, _blob(it or {}), re.I):
        return OWNERS[L]['security']
    return OWNERS[L]['operations'] if re.search(OPS_OWNER, _blob(it or {}), re.I) else OWNERS[L]['other']


def requires_explicit(it, decision=None):
    """הסיבה שפריט במנה (או decision_required של הכרעה, עם decision) דורש תשובה מפורשת, או None:
    beyond_playbook (מצב 2), counter_tighter, red_line_edge (האסטרטג סימן גבול קו אדום), amount (הכרעה על סכום),
    operational (התחייבות תפעולית), או flagged (requires_explicit: true בפריט). שאלה שאינה "נדרשת הכרעתך" (כרטיס עסקה,
    רכיבים משלימים, גישה) אינה דורשת, אלא כשסומנה."""
    import re
    it = it or {}
    d = decision or {}
    if it.get('requires_explicit') or d.get('requires_explicit'):
        return it.get('requires_explicit_why') or 'flagged'
    kind = it.get('kind') or d.get('kind')
    if it.get('situation') == 2:
        return 'beyond_playbook'
    if kind == 'counter_tighter':
        return 'counter_tighter'
    # סוג הנייר בהליך תחרותי (לפני הגשה, אחרי זכייה, או למשא ומתן): תשובה כללית אינה הופכת חוזה הליך תחרותי ל-negotiable
    if kind in ('paper_type', 'tender_stage'):
        return 'tender'
    if it.get('red_line_edge') or d.get('red_line_edge'):
        return 'red_line_edge'
    if it.get('situation') is None and kind not in AMOUNT_KINDS:
        return None
    if kind in AMOUNT_KINDS or it.get('amount') or re.search(AMOUNT, _blob(it), re.I):
        return 'amount'
    if is_operational(it):
        return 'operational'
    return None


# --------------------------------------------------------------------------- הסימונים של האסטרטג (פאנל S1d-R2)
# הנושא ונותן קורא את strategy-data.json ומצטט במנה את מה שהאסטרטג סימן על הסעיף: גבול הקו האדום (ענף בעץ שה-risk שלו
# "גבול הקו האדום", והעמדה שלהם שלפניו) וחבילות (bargain.midpoints). ההתאמה לפי מזהה ההכרעה (clause_ids), ואחריה לפי
# מספר הסעיף בכותרת
EDGE_RE = r'גבול הקו האדום|edge of the red line|red[- ]line (?:boundary|edge)'
MARKS = {'he': {'head': ' האסטרטג סימן:', 'edge': ' גבול הקו האדום: %s.', 'pkg': ' חבילה: %s%s.', 'ret': ', בתמורה ל: %s'},
         'en': {'head': ' The strategist marked:', 'edge': ' edge of the red line: %s.', 'pkg': ' package: %s%s.',
                'ret': ', in return for: %s'}}


def _short(s, n=140):
    s = ' '.join(str(s or '').split())
    return s if len(s) <= n else s[:n - 3].rstrip() + '...'


def item_clause_ids(it):
    """מזהי הסעיפים של פריט במנה: clause_ids, applies_to או clause_id."""
    ids = []
    for k in ('clause_ids', 'applies_to'):
        ids += [x for x in (it or {}).get(k) or () if x and x not in ids]
    if (it or {}).get('clause_id') and it['clause_id'] not in ids:
        ids.append(it['clause_id'])
    return ids


def _refs(text):
    """מספרי הסעיפים בטקסט ("סעיפים 18.1-18.4 ו-15.7", "סעיף 7(vi)", "Clause 18.4"), כולל טווח באותו סעיף ראשי."""
    import re
    out = set()
    for a, b, sub in re.findall(r'(\d+(?:\.\d+)?)(?:\s*-\s*(\d+(?:\.\d+)?))?((?:\([a-z0-9]+\))*)', str(text or ''), re.I):
        out.add((a + sub).lower())
        if b and '.' in a and '.' in b and a.split('.')[0] == b.split('.')[0]:
            for n in range(int(a.split('.')[1]), int(b.split('.')[1]) + 1):
                out.add('%s.%d' % (a.split('.')[0], n))
    return out


def strategy_marks(strategy, clause_ids=(), clause_ref=None):
    """הסימונים של האסטרטג על הסעיף, או None: {clause, title, red_line_edge: [...], packages: [{point, in_return,
    criterion}], red_line}."""
    import re
    clauses = (strategy or {}).get('clauses') or []
    ids = set(clause_ids or ())
    refs = _refs(clause_ref) if clause_ref else set()
    hit = [c for c in clauses if c.get('id') in ids] or (
        [c for c in clauses if refs & _refs(c.get('title'))] if refs else [])
    if not hit:
        return None
    marks = {'clause': hit[0].get('id'), 'title': hit[0].get('title'), 'red_line_edge': [], 'packages': [],
             'red_line': ''}
    for c in hit:
        last_them = ''
        for t in c.get('tree') or ():
            if t.get('side') == 'them':
                last_them = t.get('text') or ''
            elif re.search(EDGE_RE, str(t.get('risk') or ''), re.I):
                marks['red_line_edge'].append(last_them or t.get('text') or '')
        for m in (c.get('bargain') or {}).get('midpoints') or ():
            marks['packages'].append({'point': m.get('point'), 'in_return': m.get('in_return'),
                                      'criterion': m.get('criterion')})
        marks['red_line'] = marks['red_line'] or ((c.get('lines') or {}).get('red') or {}).get('what') or ''
    return marks


def marks_text(marks, lang='he'):
    """הציטוט במנה: גבול הקו האדום (הראשון) ועד שתי חבילות."""
    T = MARKS[_lang(lang)]
    s = T['head']
    for e in (marks.get('red_line_edge') or [])[:1]:
        s += T['edge'] % _short(e).rstrip('.')
    for p in (marks.get('packages') or [])[:2]:
        s += T['pkg'] % (_short(p.get('point')).rstrip('.'),
                         (T['ret'] % _short(p.get('in_return')).rstrip('.')) if p.get('in_return') else '')
    return s


# --------------------------------------------------------------------------- סעיף כמותי מורכב: הכרעה לפי רכיבים (S1e-R3)
# בסבב 3 הצד שכנגד הציע תקרה כללית של £500,000 עם החרגות בלתי מוגבלות, והרכיב החזיר £120,000 לפי יעד שנמסר לפני
# שהמספר שלהם הגיע. הכלל, בשני הכיוונים: רכיב שבו ההצעה שלהם עומדת בירוק או טובה ממנו נשמר, ואינו מוחזר ליעד שלנו;
# משא ומתן רק על הרכיב האדום. הצעה נגדית שלנו שמבקשת ברכיב כזה יותר ממה שהציעו, בכיוון שטוב לנו, היא "נדרשת הכרעתך",
# עם הסבר; הצעה נגדית שגרועה לנו מהמספר שלהם אינה נשלחת. יעד שנמסר לפני שהגיעה הצעה שלהם נשאל מחדש. פריט kind:
# composite במנה: {key, clause, our_side (קוד תפקיד או שם התפקיד בעברית או באנגלית), direction, offer_round,
# components: [{name, their, ours, green, their_track, direction, target_round, beyond_last_fallback}],
# exposure: {their, target, last_fallback, insurance, contract_value}, package}
UNLIMITED = r'no limit|unlimited|uncapped|without limit|not be limited|ללא הגבלה|ללא תקרה|בלתי מוגבל'
# הכיוון (מספר נמוך או גבוה טוב לנו) שייך לרכיב ולא לצד: ריבית, תשלום, פיקדון ותקופת הודעה אינם תקרה,
# וכיוונם נקבע לפי העמדה בפלייבוק (direction ברכיב או בפריט). רק ברכיב שהוא תקרת אחריות (CAP_COMPONENT) יש נפילה לפי
# כיוון התקרה אינו נגזר מתפקיד: אין מיפוי תפקידים לצד "נותן" או "מקבל". הכיוון נלקח רק מ-direction שנרשם ברכיב או
# בפריט בפלייבוק; בלעדיו הרכיב נשאל
CAP_COMPONENT = r'תקר|הגבלת (ה)?אחריות|גבול (ה)?אחריות|liabilit|\bcap\b|\bcapped\b|limitation|' + UNLIMITED
DIRECTIONS = ('lower_better', 'higher_better')


def side_direction(our_side):
    """כיוון התקרה לפי הצד שלנו: תמיד None. הכיוון נרשם בפלייבוק (direction) ולא נגזר משם התפקיד."""
    return None


def component_direction(c, it=None):
    """הכיוון של רכיב: direction ברכיב, direction בפריט, ורק ברכיב שהוא תקרת אחריות, נפילה לפי הצד שלנו."""
    import re
    it = it or {}
    for d in (c.get('direction'), it.get('direction')):
        if d in DIRECTIONS:
            return d
    probe = ' '.join(str(x or '') for x in (c.get('name'), c.get('topic'), it.get('topic'), it.get('title')))
    if not re.search(CAP_COMPONENT, probe, re.I):
        return None
    return side_direction(it.get('our_side'))
COMPOSITE = {
    'he': {'head': 'סעיף %s, רכיב אחר רכיב.', 'keep': ' נשמר כפי שהציעו (בירוק או טוב ממנו): %s.',
           'trade': ' מוצע לקבל כחלק מחבילה, אף שזה מעבר ליעד ולנסיגה שמסרתם: %s. מחייב הכרעה מפורשת שלכם.', 'neg': ' משא ומתן רק על: %s.', 'stale': ' היעד שמסרתם%s נמסר לפני שההצעה שלהם הגיעה, ולכן אינו מוחל כמו '
                                                     'שהוא: מה נשמר, ועל מה מנהלים משא ומתן?',
           'stale_round': ' בסבב %s', 'stale_target': ' ("%s")',
           'retrade': ' ההצעה הנגדית ברכיב "%s" (%s) מבקשת יותר מ-%s שהם הציעו, ברכיב שכבר בירוק: זו חזרה מהתקדמות '
                      'שלהם, והיא עלולה לעכב את הסגירה.',
           'give_back': ' ההצעה הנגדית ברכיב "%s" (%s) גרועה לנו מ-%s שהם הציעו: לא מחזירים ליעד, ונשארים עם המספר '
                        'שלהם.',
           'nodir': ' ברכיב %s לא נקבע בפלייבוק אם מספר גבוה או נמוך טוב לחברה: מה הכיוון, ומה היעד?',
           'rec': 'להשאיר את %s, ולנהל משא ומתן רק על %s', 'rec_keep': 'לקבל את %s כפי שהציעו', 'pkg': '; חבילה: %s',
           'opts': ['לפי ההמלצה', 'יעד אחר לכל רכיב: <..>'], 'opt_target': 'היעד שמסרתם: %s'},
    'en': {'head': 'Clause %s, component by component.', 'keep': ' Kept as they offered (green or better): %s.',
           'trade': ' Proposed to accept as part of a package, although it is beyond the target and fallback you gave: %s. Needs your express decision.', 'neg': ' Negotiate only: %s.', 'stale': ' The target you gave%s was given before their offer arrived, so it '
                                                  'is not applied as is: what is kept, and what is negotiated?',
           'stale_round': ' in round %s', 'stale_target': ' ("%s")',
           'retrade': ' The counter on "%s" (%s) asks for more than the %s they offered, in a component already in '
                      'green: this walks back their movement and may delay closing.',
           'give_back': ' The counter on "%s" (%s) is worse for us than the %s they offered: we do not go back to the '
                        'target, and keep their number.',
           'nodir': ' For %s the playbook does not say whether a higher or a lower number is better for the company: '
                    'which way, and what is the target?',
           'rec': 'Keep %s, and negotiate only %s', 'rec_keep': 'Accept %s as offered', 'pkg': '; package: %s',
           'opts': ['As recommended', 'Another target per component: <..>'], 'opt_target': 'The target you gave: %s'}}
MEMO = {'he': {'title': '**תזכיר החלטה, סעיף %s** (פנימי, להנהלה)', 'cols': '| | |\n|---|---|',
               'rows': (('their', 'ההצעה שלהם'), ('target', 'היעד שלנו'), ('last_fallback', 'הנסיגה הפנימית שלנו (לא נמסרה לצד השני)'),
                        ('insurance', 'הכיסוי הביטוחי'), ('contract_value', 'שווי החוזה')),
               'missing': 'לא נמסר', 'rec': '**ההמלצה:** %s',
               'mandate': '**נדרשת הרחבת מנדט:** ההצעה שלהם מעבר לנסיגה האחרונה. העותק למשלוח אינו מתקדם בנושא הזה עד '
                          'הכרעה מפורשת.'},
        'en': {'title': '**Decision memo, clause %s** (internal, for management)', 'cols': '| | |\n|---|---|',
               'rows': (('their', 'Their offer'), ('target', 'Our target'), ('last_fallback', 'Our internal fallback (not disclosed to them)'),
                        ('insurance', 'Insurance cover'), ('contract_value', 'Contract value')),
               'missing': 'not provided', 'rec': '**Recommendation:** %s',
               'mandate': '**Mandate extension needed:** their offer is beyond our last fallback. The send copy does '
                          'not move on this topic until an express decision.'}}


def parse_amount(s):
    """סכום כמספר: "£500,000" 500000.0, "2 million" 2000000.0, "ללא הגבלה" אינסוף; None כשאין סכום."""
    import re
    if s is None or s == '':
        return None
    if isinstance(s, (int, float)):
        return float(s)
    if re.search(UNLIMITED, str(s), re.I):
        return float('inf')
    m = re.search(r'(\d[\d,]*(?:\.\d+)?)\s*(million|מיליון|m\b|k\b)?', str(s), re.I)
    if not m:
        return None
    v = float(m.group(1).replace(',', ''))
    mult = (m.group(2) or '').lower()
    return v * (1e6 if mult in ('million', 'מיליון', 'm') else 1e3 if mult == 'k' else 1)


def _better(a, b, direction):
    return a < b if direction == 'lower_better' else a > b


def analyse_component(c, direction=None, offer_round=None):
    """{status: keep|negotiate, flags: [retrade, give_back, stale_target], beyond_last_fallback}. keep: ההצעה שלהם
    בירוק או טובה ממנו (their_track green/better, או המספר שלהם לא גרוע מ-green בכיוון שלנו)."""
    d = c.get('direction') or direction
    their, ours, green = parse_amount(c.get('their')), parse_amount(c.get('ours')), parse_amount(c.get('green'))
    keep = c.get('their_track') in ('green', 'better', 'trade') or (
        c.get('their_track') is None and None not in (their, green) and bool(d) and not _better(green, their, d))
    flags = []
    if not d and c.get('their_track') is None:
        flags.append('direction_unknown')
    if None not in (their, ours) and d and ours != their:
        if keep and _better(ours, their, d):
            flags.append('retrade')
        elif _better(their, ours, d):
            flags.append('give_back')
    tr, orr = c.get('target_round'), c.get('offer_round') or offer_round
    if tr and orr and int(tr) < int(orr):
        flags.append('stale_target')
    beyond = bool(c.get('beyond_last_fallback') or c.get('their_track') == 'red' or (
        their == float('inf') and d == 'lower_better'))
    return {'status': 'keep' if keep else 'negotiate', 'flags': flags, 'beyond_last_fallback': beyond and not keep,
            'trade': c.get('their_track') == 'trade'}


def decision_memo(m, lang='he'):
    """תזכיר החלטה קצר להנהלה (בצ'אט, או כתוצר פנימי בעמוד אחד): טבלת חשיפה, המלצה לחבילה, וסימון שנדרשת הרחבת
    מנדט. m: {clause, their, target, last_fallback, insurance, contract_value, package}."""
    T = MEMO[_lang(lang)]
    lines = [T['title'] % (m.get('clause') or '?'), T['cols']]
    for k, label in T['rows']:
        lines.append('| %s | %s |' % (label, _short(m.get(k), 200) or T['missing']))
    lines += [T['rec'] % (m.get('package') or '?'), T['mandate']]
    return '\n'.join(lines)


def composite_item(it, lang='he', round_number=None):
    """פריט kind: composite (סעיף כמותי מורכב) כשאלה אחת, רכיב אחר רכיב: מה נשמר, על מה מנהלים משא ומתן, ומה ההסבר
    כשהיעד התיישן או כשההצעה הנגדית מבקשת יותר ממה שהציעו. בסבב סגירה, רכיב שההצעה שלהם בו מעבר לנסיגה האחרונה מוסיף
    תזכיר החלטה (memo), מצב 2, וחוסם משלוח עד הכרעה מפורשת."""
    from orchestrator.state_builder import stage_for_round
    L = _lang(lang)
    T = COMPOSITE[L]
    comps = [dict(c, **analyse_component(c, component_direction(c, it), it.get('offer_round')))
             for c in it.get('components') or ()]
    lab = lambda c: '%s (%s)' % (c.get('name'), c.get('their'))  # noqa: E731
    keep = [lab(c) for c in comps if c['status'] == 'keep' and not c.get('trade')]
    trade = [lab(c) for c in comps if c.get('trade')]
    neg = [lab(c) for c in comps if c['status'] == 'negotiate']
    flags = {f for c in comps for f in c['flags']}
    text = T['head'] % (it.get('clause') or '?') + (T['keep'] % ', '.join(keep) if keep else '') + \
        (T['trade'] % ', '.join(trade) if trade else '') + (T['neg'] % ', '.join(neg) if neg else '')
    if 'stale_target' in flags:
        tr = next((c.get('target_round') for c in comps if 'stale_target' in c['flags']), None)
        target = (it.get('exposure') or {}).get('target')
        text += T['stale'] % ((T['stale_round'] % tr if tr else '') + (T['stale_target'] % _short(target, 120) if target
                                                                       else ''))
    for c in comps:
        if 'retrade' in c['flags']:
            text += T['retrade'] % (c.get('name'), c.get('ours'), c.get('their'))
        if 'give_back' in c['flags']:
            text += T['give_back'] % (c.get('name'), c.get('ours'), c.get('their'))
    nodir = [c.get('name') for c in comps if 'direction_unknown' in c['flags']]
    if nodir:
        text += T['nodir'] % ', '.join(str(n) for n in nodir)
    keep = keep + trade
    rec = it.get('package') or ((T['rec'] % (', '.join(keep), ', '.join(neg))) if keep and neg else (
        T['rec_keep'] % ', '.join(keep) if keep else it.get('recommendation') or ''))
    if it.get('package') and keep and neg and it['package'] != it.get('recommendation'):
        rec = (T['rec'] % (', '.join(keep), ', '.join(neg))) + T['pkg'] % it['package']
    if it.get('text'):
        text += ' ' + it['text'].strip()
    opts = list(T['opts'])
    target = (it.get('exposure') or {}).get('target')
    if 'stale_target' in flags and target:
        opts.insert(1, T['opt_target'] % _short(target, 80))
    out = dict(it, text=text, recommendation=rec, options=opts, requires_explicit=True,
               requires_explicit_why='amount', amount=True, components=comps)
    rnd = round_number or it.get('round')
    if rnd and (trade or (stage_for_round(rnd) == 'closing' and any(c['beyond_last_fallback'] for c in comps))):
        ex = dict(it.get('exposure') or {})
        ex.setdefault('their', ', '.join(lab(c) for c in comps))
        out['memo'] = decision_memo(dict(ex, clause=it.get('clause'), package=rec), L)
        out.update(situation=2, blocks_sending=True)
    elif 'stale_target' in flags:
        out['situation'] = 3
    elif flags & {'retrade', 'give_back'}:
        out['situation'] = 5
    elif 'direction_unknown' in flags and not out.get('situation'):
        out['situation'] = 3
    return out


PREP_KEY = r'^prepare:(?P<root>[^:]+):r(?P<r>\d+)$'
EXCLUSION = r'(?:save that|except(?: that)?|provided that|other than|excluding|but no limit)[^;]*'
STALE = {'he': {
                'general': 'תקרה כללית', 'amount': 'הסכום שהציעו', 'excl': 'החרגות בלי תקרה',
                'rec': 'להשאיר את %s כתקרה הכללית, ולהחליף את ההחרגות הבלתי מוגבלות בתקרה נפרדת לנושאים שהוחרגו, '
                       'קשורה לכיסוי הביטוחי%s', 'rec_one': 'לבחון את %s מול הירוק לפני שמחזירים ליעד',
                'ins': ' (%s)', 'pkg': '; חבילת האסטרטג: %s'},
         'en': {'general': 'general cap', 'amount': 'the amount they offered', 'excl': 'uncapped exclusions',
                'rec': 'Keep %s as the general cap, and replace the uncapped exclusions with a separate cap for the '
                       'excluded matters, tied to the insurance cover%s', 'rec_one': 'Test %s against the green '
                                                                                    'before returning to the target',
                'ins': ' (%s)', 'pkg': "; the strategist's package: %s"}}


def _our_side(state):
    """התפקיד שלנו מקובץ המצב: קוד התפקיד שבפלייבוק (playbook_side), ואם אין, התפקיד בהסכם כפי שנרשם."""
    pos = (((state or {}).get('meta') or {}).get('position') or {})
    return pos.get('playbook_side') or pos.get('our_side_in_agreement') or ''


def _insurance_of(state):
    import re
    for f in (((state or {}).get('meta') or {}).get('deal_context') or {}).get('facts') or ():
        txt = f.get('fact') if isinstance(f, dict) else str(f)
        if re.search(INSURANCE, txt or '', re.I) and re.search(AMOUNT, txt or '', re.I):
            return txt
    for q in reversed((state or {}).get('user_decisions') or ()):
        if str(q.get('id') or '').startswith('amount:') and re.search(AMOUNT, q.get('answer') or '', re.I):
            return q['answer']
    return ''


def stale_target_items(compare, state, round_number, lang='he', strategy=None):
    """יעד שנמסר לפני שהגיעה הצעה שלהם (תשובה מפורשת ל-prepare:<בועה>:r<N> מסבב קודם), כשההצעה הגיעה עכשיו בסעיף
    כמותי (סכום בשינוי שלהם): פריט kind: composite שנשאל מחדש, רכיב אחר רכיב. התקרה הכללית שהציעו נשמרת (תקרה
    מוגבלת), והמשא ומתן על ההחרגות הבלתי מוגבלות; בסבב סגירה, החרגה בלי תקרה היא מעבר לנסיגה האחרונה, ומצטרף תזכיר
    החלטה (פאנל S1e-R3, 18.4)."""
    import re
    L = _lang(lang)
    T = STALE[L]
    if not compare or not state or not round_number:
        return []
    threads = {str(t.get('root_id')): t for t in compare.get('threads') or ()}
    dc = ((state.get('meta') or {}).get('deal_context') or {})
    value = dc.get('estimated_value') if str(dc.get('estimated_value') or '').strip() not in ('', 'לא ידוע',
                                                                                            'unknown') else ''
    if not value:
        # שווי החוזה מהעובדות של העסקה (תמורה, שווי), כשאינו ב-estimated_value
        value = next((f.get('fact') for f in dc.get('facts') or () if isinstance(f, dict) and re.search(
            r'תמורה|שווי|fees|value|consideration', f.get('fact') or '', re.I) and re.search(AMOUNT, f.get('fact') or '')
            and not re.search(INSURANCE, f.get('fact') or '', re.I)), '')
    out = []
    for q in state.get('user_decisions') or ():
        m = re.match(PREP_KEY, str(q.get('id') or ''))
        if not m or int(m.group('r')) >= int(round_number) or q.get('answer_kind') != 'explicit':
            continue
        t = threads.get(m.group('root'))
        cl = t and next((c for c in compare.get('clauses') or () if c.get('received_para') == t.get('para')
                         and c.get('classification') in ('their_tracked', 'their_silent')), None)
        if not cl:
            continue
        back = cl.get('they_added') if cl['classification'] == 'their_tracked' else cl.get('they_opened_with')
        amounts = [a for a in re.findall(AMOUNT, back or '', re.I) if a not in (cl.get('we_sent') or '')]
        if not amounts:
            continue
        answer = q.get('answer') or ''
        parts = re.split(r'נסיגה\s*:|fallback\s*:', answer, 1, flags=re.I)
        excl = re.search(EXCLUSION, back or '', re.I)
        excl = excl.group(0).strip() if excl and re.search(UNLIMITED, excl.group(0), re.I) else ''
        # המספר שלהם אינו "בירוק" רק מפני שהוא קבוע. כשיש החרגות בלי תקרה, הוא מוצע לקבלה כחלק מחבילה (trade), ומחייב
        # הכרעה מפורשת והרחבת מנדט כשהוא מעבר ליעד (S1g-R3). סכום שאינו תקרת אחריות (ריבית, תשלום, פיקדון)
        # אינו נקרא "תקרה", וכיוונו נקבע לפי הפלייבוק או נשאל (component_direction)
        is_cap = bool(excl) or bool(re.search(CAP_COMPONENT, back or '', re.I))
        comps = [{'name': T['general'] if is_cap else T['amount'], 'their': amounts[0],
                  'their_track': 'trade' if excl else None,
                  'target_round': int(m.group('r')), 'offer_round': int(round_number)}]
        if excl:
            comps.append({'name': T['excl'], 'their': _short(excl, 120), 'their_track': 'red',
                          'beyond_last_fallback': True})
        ins = _insurance_of(state)
        rec = T['rec'] % (amounts[0], T['ins'] % _short(ins, 80) if ins else '') if excl else T['rec_one'] % amounts[0]
        marks = strategy_marks(strategy, q.get('applies_to'), cl.get('clause')) if strategy else None
        pkgs = (marks or {}).get('packages') or []
        pkg = next((p for p in pkgs if re.search(INSURANCE, '%s %s' % (p.get('point'), p.get('criterion')), re.I)),
                   pkgs[0] if pkgs else None)
        if pkg:
            rec += T['pkg'] % _short(pkg.get('point'), 120)
        clause = cl.get('clause') or t.get('clause') or '?'
        # ההמלצה בנויה כאן, כחבילה (package), ו-composite_item מוסיף לה את מה שנשמר ומה שבמשא ומתן
        out.append({'key': 'restate:%s:r%s' % (m.group('root'), round_number), 'kind': 'composite',
                    'clause': clause, 'our_side': _our_side(state), 'clause_ids': list(q.get('applies_to') or ()), 'offer_round': int(round_number),
                    'components': comps, 'recommendation': rec, 'package': rec, 'situation': 3,
                    'exposure': {'their': _short(back, 200), 'target': parts[0].strip(' .;,'),
                                 'last_fallback': parts[1].strip(' .;,') if len(parts) > 1 else '',
                                 'insurance': ins, 'contract_value': value},
                    'round': int(round_number), 'para': t.get('para')})
    return out


# --------------------------------------------------------------------------- סבב סגירה (פאנל S1e-R3)
HELD_CLOSING = {'he': {'text': '%s עמד לשיחה, והשיחה לא התקיימה או שלא נרשם מה סוכם.%s בסבב סגירה: להעלות עכשיו בכתב, '
                               'או לוותר ביודעין?', 'commercial': ' זה נושא מסחרי מחייב (%s).',
                       'rec_raise': 'להעלות עכשיו בכתב, בבועה קצרה בנוסח חבילה. זו פתיחה מכוונת של סעיף שקיבלנו, ונרשמת כך עם הוראתך (reopen)',
                       'rec_waive': 'לוותר ביודעין, ולרשום ויתור מכוון עם נימוק',
                       'opts': ['להעלות עכשיו בכתב', 'לוותר ביודעין', 'השיחה התקיימה (לפרט מה סוכם)']},
                'en': {'text': '%s was held for the call, and the call did not take place or what was agreed was not '
                               'recorded.%s In a closing round: raise it now in writing, or waive it knowingly?',
                       'commercial': ' This is a binding commercial topic (%s).',
                       'rec_raise': 'Raise it now in writing, in a short package-style comment. This deliberately reopens a clause we accepted, and is recorded as such with your instruction (reopen)',
                       'rec_waive': 'Waive it knowingly, and record a deliberate concession with a reason',
                       'opts': ['Raise it now in writing', 'Waive it knowingly', 'The call took place (say what was '
                                                                                 'agreed)']}}
COMMERCIAL_Q = {'he': {'text': 'ויתור מכוון ב%s על נושא מסחרי מחייב (%s): "%s". נושא כזה אינו ויתור בלי שאלה נפרדת: '
                               'להעלות בכתב, או לוותר ביודעין?',
                       'closed': ' הסעיף כבר הוסכם: העלאה מחדש רק בהוראה רשומה (negotiation_state.py reopen).',
                       'rec': 'להעלות בכתב בסבב הזה, בבועה קצרה',
                       'rec_closed': 'לוותר ביודעין: הסעיף הוסכם, ופתיחה מחדש תעלה סבב',
                       'opts': ['להעלות בכתב', 'לוותר ביודעין'], 'opts_closed': ['לוותר ביודעין',
                                                                                  'לפתוח מחדש: הוראה רשומה']},
                'en': {'text': 'A deliberate concession in %s on a binding commercial topic (%s): "%s". Such a topic is '
                               'not conceded without a separate question: raise it in writing, or waive it knowingly?',
                       'closed': ' The clause is already agreed: raising it again only on a recorded instruction '
                                 '(negotiation_state.py reopen).',
                       'rec': 'Raise it in writing in this round, in a short comment',
                       'rec_closed': 'Waive it knowingly: the clause is agreed, and reopening it costs a round',
                       'opts': ['Raise it in writing', 'Waive it knowingly'],
                       'opts_closed': ['Waive it knowingly', 'Reopen: recorded instruction']}}


def commercial_of(state, cid):
    """הנושא המסחרי המחייב של סעיף (proportionality.commercial_topic), לפי הוויתור המכוון או נקודה לשיחה."""
    for w in (state or {}).get('deliberate_concessions') or ():
        if isinstance(w, dict) and w.get('clause_ref') == cid and P.commercial_topic(w):
            return P.commercial_topic(w)
    for p in (state or {}).get('talking_points') or ():
        if isinstance(p, dict) and cid in (p.get('clause_ids') or ()) and P.commercial_topic(p):
            return P.commercial_topic(p)
    return None


def commercial_items(state, lang='he', skip=()):
    """ויתור מכוון על נושא מסחרי מחייב (סיום בלי עילה, תקופה, החזר תשלומים, שינוי שליטה, תקרה מול ביטוח) בלי תשובה
    מפורשת: שאלה נפרדת, מצב 5, שדורשת תשובה מפורשת. skip: סעיפים שכבר יש להם פריט בסבב (קבלה שעומדת לשיחה)."""
    L = _lang(lang)
    T = COMMERCIAL_Q[L]
    by = {c.get('clause_id'): c for c in (state or {}).get('clauses') or () if isinstance(c, dict)}
    nm = (state or {}).get('numbering_map') or {}
    out, seen = [], set(skip or ())
    for w in (state or {}).get('deliberate_concessions') or ():
        if not isinstance(w, dict):
            continue
        cid, topic = w.get('clause_ref'), P.commercial_topic(w)
        if not topic or cid in seen or w.get('reopened_in_round') or \
                (w.get('user_decision') or {}).get('answer_kind') == 'explicit':
            continue
        seen.add(cid)
        closed = (by.get(cid) or {}).get('status') == 'CLOSED'
        out.append({'key': 'commercial:%s' % cid, 'kind': 'commercial_concession', 'situation': 5,
                    'clause_ids': [cid], 'requires_explicit': True, 'commercial_topic': topic,
                    'text': T['text'] % (nm.get(cid) or cid, P.COMMERCIAL_LABELS[L][topic], _short(w.get('topic')))
                    + (T['closed'] if closed else ''),
                    'recommendation': T['rec_closed'] if closed else T['rec'],
                    'options': list(T['opts_closed'] if closed else T['opts'])})
    return out


# הצד השני מאותת שהוא מוכן לסיים: הרשימה לפני חתימה רצה בתצוגה מקדימה, ומציגה את מה שחסר (round_tools.py questions)
READY = r'in a position to finali[sz]e|ready to (?:sign|finali[sz]e|execute|proceed to sign)|proceed to (?:signature|' \
        r'signing)|finali[sz]e (?:this|the) agreement|מוכנים לחתום|מוכנים לסיים|נוכל לחתום|נוכל לסיים'


def ready_signal(compare):
    """{root_id, text} של רשומה חדשה של הצד השני שאומרת שהוא מוכן לסיים או לחתום, או None."""
    import re
    for t in (compare or {}).get('threads') or ():
        for e in t.get('entries') or ():
            if e.get('new') and not e.get('ours') and re.search(READY, e.get('text') or '', re.I):
                return {'root_id': t.get('root_id'), 'text': ' '.join((e.get('text') or '').split())[:200]}
    return None


# מצב 9, אפשרות שלישית: לקבל בתנאי (פאנל S1e-R3, 6(h)). שינוי שמוסיף אישור או הסכמה שלהם: התנאי המוצע הוא שהאישור לא
# יסורב או יעוכב שלא באופן סביר, בשפת ההסכם
APPROVAL = r'approv|consent|הסכמ|אישור'
COND_WORDING = {'en': 'such approval not to be unreasonably withheld or delayed',
                'he': 'ובלבד שהאישור לא יסורב ולא יעוכב שלא באופן סביר'}
CONDITION = {'he': {'opt': 'לקבל בתנאי: %s', 'generic': '<התנאי>',
                    'rec': 'לקבל בתנאי: השינוי שלהם נשאר, ומסמנים עליו בעקוב אחר שינויים "%s" (kind: '
                           'accept_with_condition)',
                    'alt': '. חלופה: לקבל בתנאי ("%s", kind: accept_with_condition); בסעיף מוסכם זו פתיחה מחדש, בהוראה '
                           'רשומה'},
             'en': {'opt': 'Accept on a condition: %s', 'generic': '<the condition>',
                    'rec': 'Accept on a condition: their change stays, and we mark "%s" on it in tracked changes (kind: '
                           'accept_with_condition)',
                    'alt': '. Alternative: accept on a condition ("%s", kind: accept_with_condition); in an agreed '
                           'clause this is a reopening, on a recorded instruction'}}


# עמדה חדשה שלנו בשרשור פתוח: התשובה אומרת שהיא מחליפה את ההצעה הקודמת (round_violations, ROUND_STALE_PROPOSAL), או
# שהבועה הקודמת מסומנת "בוצע" (round_tools.py resolve-threads --decisions). המשפט אינו נספר באורך הבועה
CHANGE_OPS = ('replace', 'replace_span', 'insert_paragraph', 'delete_paragraph')
REPLACES = {'en': 'This replaces our earlier proposal.', 'he': 'זה מחליף את ההצעה הקודמת שלנו.'}
REPLACES_RE = r'replaces our (?:earlier|previous) proposal|מחליפ[הא]? את ההצעה הקודמת'
REPLACES_SENT = r'\s*(?:This replaces our (?:earlier|previous) proposal|זה מחליף את ההצעה הקודמת שלנו)\.?\s*'


def _bubble_lang(text):
    import re
    return 'he' if re.search('[א-ת]', text or '') else 'en'
