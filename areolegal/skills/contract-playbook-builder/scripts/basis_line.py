# -*- coding: utf-8 -*-
"""שורת הבסיס: על כמה הסכמים הפלייבוק נשען, ובאיזה מסלול נבנה.

אותו נוסח בדיוק מופיע בשער ה-Word (`word-export-spec.md`, "השער") ובפס
הבסיס בארטיפקט (`dashboard_spec.md`, "פס הבסיס"). הוא נגזר כאן ממקום אחד,
כדי ששני התוצרים לא יספרו אחרת, והוא נשען על `corpus_basis.agreement_units`
ועל `corpus_origin` ולא על מספר הקבצים בתיקייה.

בארטיפקט אותו נוסח ממומש ב-JavaScript בתוך התבנית, ו-`qa_basis_line.js`
משווה בין השניים בכל חמשת המצבים, כדי שלא ייווצר הפרש.
"""

AREO_TAG = 'הצעת Areo (לא מבוסס על מסמכי הלקוח)'


def agreement_units(model):
    """מספר ההסכמים שעליו נשען הפלייבוק, או None כשאין ספירה."""
    basis = ((model.get("scope_summary") or {}).get("corpus_basis") or {})
    n = basis.get("agreement_units")
    return n if isinstance(n, int) else None


def basis_line(units, origin):
    """הנוסח לפי מספר ההסכמים ולפי המסלול. None כשאין ספירה."""
    if not isinstance(units, int):
        return None
    if units == 0 or origin == "market_built":
        return ('נבנה לפי השוק, מותאם לפוזיציה של החברה, עם בדיקה רגולטורית מעמיקה. '
                'אין בו עמדה שנגזרה מהסכמי החברה, וכל עמדה בו מסומנת "%s".' % AREO_TAG)
    if units >= 20:
        return 'נבנה מ-%d הסכמים של החברה.' % units
    if units >= 7:
        return ('נבנה מ-%d הסכמים של החברה. זה פחות מהמומלץ (כ-20), ולכן חלק מהעמדות '
                'נשענות על מעט משאים ומתנים.' % units)
    if origin == "own_plus_market":
        return ('נבנה מ-%d הסכמים של החברה, בשילוב מחקר שוק. עמדה שמקורה בשוק '
                'מסומנת "%s".' % (units, AREO_TAG))
    return ('נבנה מ-%d הסכמים של החברה בלבד. לא מומלץ לבנות פלייבוק מפחות מ-20 הסכמים, '
            'והחברה בחרה שלא לשלב מחקר שוק.' % units)


def line_for(model):
    """שורת הבסיס של מודל פלייבוק, או None כשאין במודל ספירה."""
    return basis_line(agreement_units(model),
                      (model.get("scope_summary") or {}).get("corpus_origin"))


def mostly_drafts(model):
    """האם רוב ההסכמים טיוטות. אז נוספת לשער השורה "פלייבוק ראשוני"."""
    rows = [r for r in model.get("source_log") or [] if r.get("included")]
    if not rows:
        return False
    drafts = sum(1 for r in rows if r.get("doc_role") == "draft")
    return drafts * 2 > len(rows)
