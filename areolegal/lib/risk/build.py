# -*- coding: utf-8 -*-
"""risk/build.py: בניית הדוח וכתיבתו לתיקיית העסקה, עם המרשם לצדו (הערות 3.6).

הבעיה (סבב 3, סיכום C1 פער 3): build_report מחזיר HTML, והכתיבה לתיקיית העסקה, הסירוב לדרוס דוח של עסקה
אחרת ושמירת המרשם לצדו נכתבו בכל הרצה בעטיפה אחרת.

write_report(deal_dir, template_path, data, kind='risk'|'entity'):
1. שם קבוע: "Areo Workspace - סיכונים.html" ו-risk-register.json; לחקר ישות "Areo Workspace - חקר ישות.html"
   ו-entity-report.json.
2. מזהה העסקה במרשם (meta.transaction_id) זהה לשם תיקיית העסקה; אחרת נכשל.
3. דוח קיים בתיקייה שנבנה לעסקה אחרת (מזהה אחר בנתונים המוטמעים) אינו נדרס: BuildError.
4. בדיקה סטטית של התבנית (static_checks) ובדיקת אורך הנתיב (common/paths.check_write_path) לפני כל כתיבה.
5. כותב רק את שני הקבצים, ורק לתיקיית העסקה.
"""
import io
import json
import os
import re
import sys

try:
    from .render_check import build_report, static_checks
except ImportError:  # pragma: no cover
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from render_check import build_report, static_checks

try:
    from common.paths import check_write_path
except ImportError:  # pragma: no cover
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from common.paths import check_write_path

NAMES = {'risk': ('Areo Workspace - סיכונים.html', 'risk-register.json', '__RISK_DATA__'),
         'entity': ('Areo Workspace - חקר ישות.html', 'entity-report.json', '__ENTITY_DATA__')}


class BuildError(Exception):
    pass


def _embedded_tid(html_path):
    try:
        with io.open(html_path, encoding='utf-8') as fh:
            html = fh.read()
    except OSError:
        return None
    m = re.search(r'"transaction_id"\s*:\s*"([^"]*)"', html)
    return m.group(1) if m else None


def write_report(deal_dir, template_path, data, kind='risk'):
    html_name, json_name, placeholder = NAMES[kind]
    tid = ((data.get('meta') or {}).get('transaction_id'))
    if kind == 'risk' and (data.get('meta') or {}).get('scope') == 'deal' and tid != os.path.basename(
            os.path.normpath(deal_dir)):
        raise BuildError('meta.transaction_id (%s) אינו שם תיקיית העסקה (%s)' % (tid, os.path.basename(deal_dir)))
    with io.open(template_path, encoding='utf-8') as fh:
        tpl = fh.read()
    st = static_checks(tpl)
    if st:
        raise BuildError('התבנית נכשלה בבדיקה הסטטית: %s' % '; '.join(st))
    html_path = os.path.join(deal_dir, html_name)
    json_path = os.path.join(deal_dir, json_name)
    old = _embedded_tid(html_path) if os.path.exists(html_path) else None
    if old and tid and old != tid:
        raise BuildError('בתיקייה דוח של עסקה אחרת (%s): לא נדרס' % old)
    for p in (html_path, json_path):
        check_write_path(p)
    html = build_report(tpl, data, placeholder)
    with io.open(json_path, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    with io.open(html_path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(html)
    return html_path, json_path
