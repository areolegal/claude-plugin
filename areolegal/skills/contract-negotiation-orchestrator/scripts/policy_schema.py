"""
policy_schema.py

הסכמת ה-JSON של מסמך הפוליסי. מאפשרת ולידציה של מבנה הפוליסי
לפני הפעלתו בפאזה 2.

המבנה משקף את 18 הקטגוריות בטקסונומיה ומאפשר לכל קטגוריה:
    - default_position: עמדת ברירת המחדל
    - fallback_1: ויתור ראשוני
    - fallback_2: הקו האדום
    - reasoning: הנימוק המשפטי
    - example_clauses: דוגמאות ניסוח מהסכמים קיימים
    - documented_exceptions: חריגים מהסכמים שנותחו
"""

from typing import TypedDict, List, Optional


class CategoryPosition(TypedDict, total=False):
    category_number: int
    category_name: str
    default_position: str
    fallback_1: str
    fallback_2: str
    reasoning: str
    legal_anchors: List[str]
    example_clauses: List[dict]
    documented_exceptions: List[dict]
    importance: str  # 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'


class PolicyDocument(TypedDict, total=False):
    client_name: str
    policy_version: str
    policy_date: str
    contracts_analyzed: List[dict]
    introduction: str
    categories: List[CategoryPosition]
    appendix_supplier_matrix: dict
    appendix_clause_examples: dict


# מבנה ברירת מחדל - 18 קטגוריות
DEFAULT_CATEGORIES_TEMPLATE = [
    {
        'category_number': 1,
        'category_name': 'הגדרות',
        'importance': 'MEDIUM',
        'default_position': '',
        'fallback_1': '',
        'fallback_2': '',
        'reasoning': '',
        'legal_anchors': [],
        'example_clauses': [],
        'documented_exceptions': [],
    },
    {
        'category_number': 2,
        'category_name': 'היקף השירותים והתוצרים',
        'importance': 'CRITICAL',
        'default_position': '',
        'fallback_1': '',
        'fallback_2': '',
        'reasoning': '',
        'legal_anchors': [],
        'example_clauses': [],
        'documented_exceptions': [],
    },
    {
        'category_number': 3,
        'category_name': 'תקופת התקשרות וחידוש',
        'importance': 'HIGH',
        'default_position': '',
        'fallback_1': '',
        'fallback_2': '',
        'reasoning': '',
        'legal_anchors': [],
        'example_clauses': [],
        'documented_exceptions': [],
    },
    {
        'category_number': 4,
        'category_name': 'סיום ההסכם',
        'importance': 'CRITICAL',
        'default_position': '',
        'fallback_1': '',
        'fallback_2': '',
        'reasoning': '',
        'legal_anchors': [],
        'example_clauses': [],
        'documented_exceptions': [],
    },
    {
        'category_number': 5,
        'category_name': 'תמורה ותנאי תשלום',
        'importance': 'CRITICAL',
        'default_position': '',
        'fallback_1': '',
        'fallback_2': '',
        'reasoning': '',
        'legal_anchors': [],
        'example_clauses': [],
        'documented_exceptions': [],
    },
    {
        'category_number': 6,
        'category_name': 'הגבלת אחריות',
        'importance': 'CRITICAL',
        'default_position': '',
        'fallback_1': '',
        'fallback_2': '',
        'reasoning': '',
        'legal_anchors': [],
        'example_clauses': [],
        'documented_exceptions': [],
    },
    {
        'category_number': 7,
        'category_name': 'שיפוי',
        'importance': 'CRITICAL',
        'default_position': '',
        'fallback_1': '',
        'fallback_2': '',
        'reasoning': '',
        'legal_anchors': [],
        'example_clauses': [],
        'documented_exceptions': [],
    },
    {
        'category_number': 8,
        'category_name': 'סודיות',
        'importance': 'HIGH',
        'default_position': '',
        'fallback_1': '',
        'fallback_2': '',
        'reasoning': '',
        'legal_anchors': [],
        'example_clauses': [],
        'documented_exceptions': [],
    },
    {
        'category_number': 9,
        'category_name': 'בעלות בקניין רוחני',
        'importance': 'CRITICAL',
        'default_position': '',
        'fallback_1': '',
        'fallback_2': '',
        'reasoning': '',
        'legal_anchors': [],
        'example_clauses': [],
        'documented_exceptions': [],
    },
    {
        'category_number': 10,
        'category_name': 'ביטוח',
        'importance': 'HIGH',
        'default_position': '',
        'fallback_1': '',
        'fallback_2': '',
        'reasoning': '',
        'legal_anchors': [],
        'example_clauses': [],
        'documented_exceptions': [],
    },
    {
        'category_number': 11,
        'category_name': 'הגנת פרטיות והגנת מידע',
        'importance': 'CRITICAL',
        'default_position': '',
        'fallback_1': '',
        'fallback_2': '',
        'reasoning': '',
        'legal_anchors': [],
        'example_clauses': [],
        'documented_exceptions': [],
    },
    {
        'category_number': 12,
        'category_name': 'אבטחת מידע וסייבר',
        'importance': 'CRITICAL',
        'default_position': '',
        'fallback_1': '',
        'fallback_2': '',
        'reasoning': '',
        'legal_anchors': [],
        'example_clauses': [],
        'documented_exceptions': [],
    },
    {
        'category_number': 13,
        'category_name': 'רמות שירות (SLA)',
        'importance': 'HIGH',
        'default_position': '',
        'fallback_1': '',
        'fallback_2': '',
        'reasoning': '',
        'legal_anchors': [],
        'example_clauses': [],
        'documented_exceptions': [],
    },
    {
        'category_number': 14,
        'category_name': 'כוח עליון',
        'importance': 'MEDIUM',
        'default_position': '',
        'fallback_1': '',
        'fallback_2': '',
        'reasoning': '',
        'legal_anchors': [],
        'example_clauses': [],
        'documented_exceptions': [],
    },
    {
        'category_number': 15,
        'category_name': 'דיני מדינה ופורום',
        'importance': 'HIGH',
        'default_position': '',
        'fallback_1': '',
        'fallback_2': '',
        'reasoning': '',
        'legal_anchors': [],
        'example_clauses': [],
        'documented_exceptions': [],
    },
    {
        'category_number': 16,
        'category_name': 'בוררות וישוב סכסוכים',
        'importance': 'MEDIUM',
        'default_position': '',
        'fallback_1': '',
        'fallback_2': '',
        'reasoning': '',
        'legal_anchors': [],
        'example_clauses': [],
        'documented_exceptions': [],
    },
    {
        'category_number': 17,
        'category_name': 'הסבה והעברת זכויות',
        'importance': 'MEDIUM',
        'default_position': '',
        'fallback_1': '',
        'fallback_2': '',
        'reasoning': '',
        'legal_anchors': [],
        'example_clauses': [],
        'documented_exceptions': [],
    },
    {
        'category_number': 18,
        'category_name': 'ליווי תהליך מעבר וסיום',
        'importance': 'HIGH',
        'default_position': '',
        'fallback_1': '',
        'fallback_2': '',
        'reasoning': '',
        'legal_anchors': [],
        'example_clauses': [],
        'documented_exceptions': [],
    },
]


def validate_policy(policy: dict) -> List[str]:
    """ולידציה של מסמך הפוליסי. מחזיר רשימת שגיאות (ריקה אם הכל בסדר)."""
    errors = []

    # שדות חובה ברמת המסמך
    required_top = ['client_name', 'policy_version', 'categories']
    for field in required_top:
        if field not in policy or not policy[field]:
            errors.append(f'שדה חסר: {field}')

    # ולידציה של הקטגוריות
    if 'categories' in policy:
        cats = policy['categories']
        if len(cats) != 18:
            errors.append(f'מספר קטגוריות לא תקין: {len(cats)} (צריך להיות 18)')

        for i, cat in enumerate(cats):
            if 'category_number' not in cat:
                errors.append(f'קטגוריה באינדקס {i} בלי category_number')
            elif cat['category_number'] != i + 1:
                errors.append(f'קטגוריה באינדקס {i} עם מספר {cat["category_number"]} - לא תואם')

            if not cat.get('default_position'):
                errors.append(f'קטגוריה {cat.get("category_number")}: חסר default_position')

            # אזהרות על קטגוריות קריטיות שדורשות יותר תוכן
            if cat.get('importance') == 'CRITICAL':
                if not cat.get('fallback_1'):
                    errors.append(f'קטגוריה קריטית {cat.get("category_number")}: חסר fallback_1')
                if not cat.get('fallback_2'):
                    errors.append(f'קטגוריה קריטית {cat.get("category_number")}: חסר fallback_2')
                if not cat.get('reasoning'):
                    errors.append(f'קטגוריה קריטית {cat.get("category_number")}: חסר reasoning')

    return errors


def get_empty_template(client_name: str = '', policy_version: str = '1.0') -> dict:
    """מחזיר תבנית פוליסי ריקה למילוי בפאזה 1."""
    import datetime
    import copy
    return {
        'client_name': client_name,
        'policy_version': policy_version,
        'policy_date': datetime.date.today().isoformat(),
        'contracts_analyzed': [],
        'introduction': '',
        'categories': copy.deepcopy(DEFAULT_CATEGORIES_TEMPLATE),
        'appendix_supplier_matrix': {},
        'appendix_clause_examples': {},
    }


def get_category(policy: dict, category_number: int) -> Optional[dict]:
    """שליפת קטגוריה לפי מספר."""
    for cat in policy.get('categories', []):
        if cat.get('category_number') == category_number:
            return cat
    return None
