# -*- coding: utf-8 -*-
"""בדיקות ל-common/gap_checks.py: ארבע המחלקות של כלל 2.22 (חריג מחלוקת, חפיפה בסיום, חריגי סודיות, ונוסח בטוח
שנוקב מספר בלי מועד מרבי בדין), בעברית ובאנגלית, בכמה משפחות הסכמים. הבדיקות מוכיחות שהמנגנון כללי: אותה מחלקה
נכשלת על נוסח פגום ועוברת על נוסח מתוקן בהסכם שירותים, אספקה, שכירות, SaaS, הפצה, העסקה והלוואה (החלטה 22)."""
import pytest

import orch_helpers  # noqa: F401
from common.gap_checks import ALL_CODES, check_document, check_wording, detect_lang


def codes(text, lang, **ctx):
    return {x['code'] for x in check_wording(text, lang, context=ctx or None)}


# (code, family, lang, bad wording, good wording)
CASES = [
    # חריג מחלוקת בזכות סיום בעילת אי-תשלום: סכום, מועד, וקיזוז כשיש זכות קיזוז
    ('GAP_DISPUTE_CARVEOUT', 'services', 'he',
     'כל צד רשאי לסיים את ההסכם בשל הפרה, לרבות אי-תשלום.',
     'כל צד רשאי לסיים את ההסכם בשל הפרה. אי-תשלום של סכום שחולקים בתום לב על החיוב בו או על מועד פירעונו אינו הפרה.'),
    ('GAP_DISPUTE_CARVEOUT', 'lease', 'he',
     'המשכיר רשאי לסיים את ההסכם אם השוכר הפר אותו. אי-תשלום של סכום שהשוכר חולק עליו אינו הפרה.',
     'המשכיר רשאי לסיים את ההסכם אם השוכר הפר אותו. אי-תשלום של סכום שהשוכר חולק בתום לב על חיובו או על מועד '
     'פירעונו אינו הפרה.'),
    ('GAP_DISPUTE_CARVEOUT', 'saas', 'en',
     'Provider may terminate this agreement for any breach by Customer, including non-payment.',
     'Provider may terminate this agreement for breach. Non-payment of an amount disputed in good faith, as to liability, '
     'amount or timing, is not a breach.'),
    ('GAP_DISPUTE_CARVEOUT', 'loan', 'en',
     'The Lender may terminate the facility upon any breach, including failure to pay. A disputed amount is not a breach.',
     'The Lender may terminate the facility upon any breach. Failure to pay an amount disputed in good faith as to '
     'liability, amount or timing is not a breach.'),
    # חפיפה בסיום של התקשרות מתמשכת
    ('GAP_TERMINATION_HANDOVER', 'supply', 'he',
     'הקונה רשאי לסיים את ההסכם בהודעה מוקדמת של 30 יום. הספק יספק את ההזמנות עד הסיום.',
     'הקונה רשאי לסיים את ההסכם בהודעה מוקדמת של 30 יום. בכל סיום יבצע הספק העברה מסודרת של ההזמנות הפתוחות.'),
    ('GAP_TERMINATION_HANDOVER', 'distribution', 'en',
     'Either party may terminate this agreement on 90 days notice. The Distributor shall supply customers until then.',
     'Either party may terminate this agreement on 90 days notice, and the Distributor shall provide transition '
     'assistance for 60 days and supply customers until then.'),
    ('GAP_TERMINATION_HANDOVER', 'lease', 'he',
     'המשכיר רשאי לסיים את ההסכם בהודעה של 60 יום על המושכר.',
     'המשכיר רשאי לסיים את ההסכם בהודעה של 60 יום, והשוכר יחזיר את המושכר בתוך 30 ימים.'),
    # חריגי סודיות
    ('GAP_CONFIDENTIALITY_EXCEPTIONS', 'employment', 'he',
     'העובד ישמור בסוד את המידע של המעסיק.',
     'העובד ישמור בסוד את המידע של המעסיק. החובה אינה חלה על מידע שהתקבל כדין מצד שלישי או שפותח באופן עצמאי, והעובד '
     'רשאי לגלות מידע לפי דין, וליועציו המקצועיים.'),
    ('GAP_CONFIDENTIALITY_EXCEPTIONS', 'saas', 'en',
     'Customer shall keep the Documentation confidential and shall not disclose it.',
     'Customer shall keep the Documentation confidential and shall not disclose it, except as required by applicable '
     'law, to its advisers and auditors, information received from a third party, or information independently developed.'),
    ('GAP_CONFIDENTIALITY_EXCEPTIONS', 'supply', 'he',
     'כל צד ישמור בסוד את המידע של הצד האחר.',
     'כל צד ישמור בסוד את המידע של הצד האחר. החובה אינה חלה על מידע שהתקבל כדין מצד שלישי או שפותח באופן עצמאי, וכל '
     'צד רשאי לגלות מידע לפי דין או לפי דרישת רשות מוסמכת, וליועציו המקצועיים.'),
    # נוסח בטוח נוקב מספר, ולעולם אינו מפנה למועד מרבי בדין
    ('GAP_PAYMENT_WORDING', 'services', 'he',
     'התשלום ישולם בתוך המועד המאוחר ביותר שהדין מתיר מתום החודש.',
     'התשלום ישולם בתוך 60 ימים מתום החודש שבו הומצא החשבון.'),
    ('GAP_PAYMENT_WORDING', 'lease', 'he',
     'דמי השכירות ישולמו בתוך זמן סביר מקבלת החשבון.',
     'דמי השכירות ישולמו בתוך 10 ימים מקבלת החשבון.'),
    ('GAP_PAYMENT_WORDING', 'saas', 'en',
     'Fees are payable within the latest time permitted by law, whichever is earlier.',
     'Fees are payable within 30 days after receipt of a valid invoice.'),
]


@pytest.mark.parametrize('code,family,lang,bad,good', CASES, ids=['%s-%s-%s' % (c[0], c[1], c[2]) for c in CASES])
def test_generic_class_fails_on_bad_and_passes_on_good(code, family, lang, bad, good):
    assert code in codes(bad, lang)
    assert code not in codes(good, lang)


def test_only_the_four_generic_classes():
    """החלטה 22 (כלל נוקשה 2.26): אין בסקיל מחלקה שתוכנה המשפטי תלוי בסוג הסכם."""
    assert set(ALL_CODES) == {'GAP_DISPUTE_CARVEOUT', 'GAP_TERMINATION_HANDOVER', 'GAP_CONFIDENTIALITY_EXCEPTIONS',
                              'GAP_PAYMENT_WORDING'}


def test_no_handover_needed_without_continuing_performance():
    """בהסכם בלי ביצוע מתמשך (למשל הסכם סודיות לבדו) אין חובת חפיפה."""
    assert 'GAP_TERMINATION_HANDOVER' not in codes('Either party may terminate this agreement on 30 days notice.', 'en')


def test_dispute_carveout_includes_setoff_when_setoff_exists():
    t = 'כל צד רשאי לסיים בשל הפרה. אי-תשלום של סכום שהלקוח חולק בתום לב על חיובו או על מועד פירעונו אינו הפרה.'
    doc = t + '\nהלקוח רשאי לקזז סכום קצוב.'
    msg = ' '.join(x['message_he'] for x in check_wording(t, 'he', context={'accept_text': doc}))
    assert 'קיזוז' in msg


def test_result_shape_and_hebrew_message():
    res = check_wording('Fees are payable within the latest time permitted by law.', 'en')
    assert res and all(set(x) == {'code', 'message_he', 'span'} for x in res)
    assert all(any('א' <= ch <= 'ת' for ch in x['message_he']) for x in res)


def test_waived_code_is_not_reported_and_document_check_is_empty():
    t = 'Fees are payable within the latest time permitted by law.'
    assert 'GAP_PAYMENT_WORDING' not in codes(t, 'en', waived=['GAP_PAYMENT_WORDING'])
    assert check_document(t, [t], 'en') == []


def test_detect_lang():
    assert detect_lang('הסכם שירותים') == 'he' and detect_lang('Mutual NDA') == 'en'
