# -*- coding: utf-8 -*-
"""risk/build.py: בניית הדוח וכתיבתו לתיקיית העסקה, עם המרשם לצדו.

write_report(deal_dir, template_path, data, kind='risk'|'entity', lang=None):
1. שם קבוע לפי שפת הדוח (meta.display_language, או lang): בעברית "Areo Workspace - סיכונים.html", ולחקר ישות
   "Areo Workspace - חקר ישות.html"; באנגלית "Areo Workspace - Risks.html" ו-"Areo Workspace - Entity check.html".
   לצדו risk-register.json או entity-report.json. דוח קיים בשפה האחרת נחשב לאותו דוח (בדיקת העסקה והעברה
   ל-history), כך שבתיקיית העסקה יש תמיד דוח אחד.
2. מזהה העסקה במרשם (meta.transaction_id) זהה לשם תיקיית העסקה; אחרת נכשל.
3. דוח קיים בתיקייה שנבנה לעסקה אחרת (מזהה אחר בנתונים המוטמעים) אינו נדרס: BuildError.
4. בדיקה סטטית של התבנית (static_checks) ובדיקת אורך הנתיב (common/paths.check_write_path) לפני כל כתיבה.
5. כותב רק את שני הקבצים, ורק לתיקיית העסקה.
6. גרסה קודמת של אותה עסקה אינה נדרסת: לפני הכתיבה הדוח והמרשם הקודמים עוברים לתיקייה
   history שבתיקיית העסקה, עם התאריך והשעה שבהם נכתבו ("Areo Workspace - סיכונים.20261028T134800.html").
   מרשם שהוא קובץ הקלט עצמו (--data) כבר נדרס בידי המעריך: הגרסה הקודמת שלו נשמרת מהנתונים שמוטמעים בדוח הקודם.
   archive_previous מחזיר את הנתיבים שהועברו, ו-write_report מוסיף אותם לרשימה archived כשנמסרה.
"""
import io
import json
import os
import re
import shutil
import sys
import time

try:
    from .render_check import build_report, static_checks
except ImportError:  # pragma: no cover
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from render_check import build_report, static_checks

try:
    from common.paths import check_write_path, long_path
except ImportError:  # pragma: no cover
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from common.paths import check_write_path, long_path

NAMES = {'risk': ('Areo Workspace - סיכונים.html', 'risk-register.json', '__RISK_DATA__'),
         'entity': ('Areo Workspace - חקר ישות.html', 'entity-report.json', '__ENTITY_DATA__')}
NAMES_EN = {'risk': ('Areo Workspace - Risks.html', 'risk-register.json', '__RISK_DATA__'),
            'entity': ('Areo Workspace - Entity check.html', 'entity-report.json', '__ENTITY_DATA__')}


def names_for(kind, lang=None):
    """(שם הדוח, שם קובץ הנתונים, המציין) בשפת הדוח: 'en' באנגלית, כל ערך אחר בעברית."""
    return (NAMES_EN if lang == 'en' else NAMES)[kind]


def html_names(kind):
    """שני השמות האפשריים של הדוח, בעברית ובאנגלית: לבדיקת דוח קיים בתיקייה."""
    return (NAMES[kind][0], NAMES_EN[kind][0])


def lang_of(data):
    return 'en' if ((data or {}).get('meta') or {}).get('display_language') == 'en' else 'he'


class BuildError(Exception):
    pass


def _embedded_tid(html_path):
    try:
        with io.open(long_path(html_path), encoding='utf-8') as fh:
            html = fh.read()
    except OSError:
        return None
    m = re.search(r'"transaction_id"\s*:\s*"([^"]*)"', html)
    return m.group(1) if m else None


HISTORY_DIR = 'history'
_EMBED_RE = re.compile(r'const DATA\s*=\s*')


def _embedded_data(html_path):
    """הנתונים שמוטמעים בדוח (const DATA = {...}), או None."""
    try:
        with io.open(long_path(html_path), encoding='utf-8') as fh:
            html = fh.read()
        m = _EMBED_RE.search(html)
        return json.JSONDecoder().raw_decode(html, m.end())[0] if m else None
    except (OSError, ValueError):
        return None


def _history_path(hist, name, stamp):
    base, ext = os.path.splitext(name)
    p = os.path.join(hist, '%s.%s%s' % (base, stamp, ext))
    n = 2
    while os.path.exists(long_path(p)):
        p = os.path.join(hist, '%s.%s-%d%s' % (base, stamp, n, ext))
        n += 1
    return p


def _same_file(a, b):
    try:
        return bool(a) and os.path.exists(long_path(a)) and os.path.samefile(long_path(a), long_path(b))
    except OSError:
        return False


def archive_previous(deal_dir, kind='risk', data_path=None, lang=None):
    """מעביר את הדוח והמרשם הקודמים של העסקה ל-<תיקיית העסקה>/history, עם התאריך והשעה שבהם נכתבו. מרשם שהוא
    קובץ הקלט (data_path) אינו מועבר, כי הוא הגרסה החדשה; הגרסה הקודמת שלו נכתבת מהנתונים שבדוח הקודם. בלי דוח
    ובלי מרשם קודמים: רשימה ריקה. אין מחיקה: רק העברה בתוך תיקיית העסקה."""
    html_name, json_name, _ = names_for(kind, lang)
    json_path = os.path.join(deal_dir, json_name)
    # הדוח הקודם, בשפה שלו: השם בשפת הדוח החדש קודם, ואחריו השם בשפה האחרת
    olds = [os.path.join(deal_dir, n) for n in dict.fromkeys((html_name,) + html_names(kind))
            if os.path.exists(long_path(os.path.join(deal_dir, n)))]
    html_path = olds[0] if olds else os.path.join(deal_dir, html_name)
    old_html = bool(olds)
    old_json = os.path.exists(long_path(json_path)) and not _same_file(data_path, json_path)
    if not old_html and not old_json:
        return []
    hist = os.path.join(deal_dir, HISTORY_DIR)
    os.makedirs(long_path(hist), exist_ok=True)
    moved = []
    embedded = _embedded_data(html_path) if old_html and not old_json else None
    for p, ok in [(x, True) for x in olds] + [(json_path, old_json)]:
        if not ok:
            continue
        stamp = time.strftime('%Y%m%dT%H%M%S', time.localtime(os.path.getmtime(long_path(p))))
        dst = _history_path(hist, os.path.basename(p), stamp)
        check_write_path(dst)
        shutil.move(long_path(p), long_path(dst))
        moved.append(dst)
        if p == html_path and embedded is not None:
            jdst = _history_path(hist, json_name, stamp)
            check_write_path(jdst)
            with io.open(long_path(jdst), 'w', encoding='utf-8', newline='\n') as fh:
                json.dump(embedded, fh, ensure_ascii=False, indent=1)
            moved.append(jdst)
    return moved


def write_report(deal_dir, template_path, data, kind='risk', data_path=None, archived=None, lang=None):
    lang = lang or lang_of(data)
    html_name, json_name, placeholder = names_for(kind, lang)
    tid = ((data.get('meta') or {}).get('transaction_id'))
    if kind == 'risk' and (data.get('meta') or {}).get('scope') == 'deal' and tid != os.path.basename(
            os.path.normpath(deal_dir)):
        raise BuildError('meta.transaction_id (%s) אינו שם תיקיית העסקה (%s)' % (tid, os.path.basename(deal_dir)))
    with io.open(long_path(template_path), encoding='utf-8') as fh:
        tpl = fh.read()
    st = static_checks(tpl)
    if st:
        raise BuildError('התבנית נכשלה בבדיקה הסטטית: %s' % '; '.join(st))
    html_path = os.path.join(deal_dir, html_name)
    json_path = os.path.join(deal_dir, json_name)
    for n in html_names(kind):
        p = os.path.join(deal_dir, n)
        old = _embedded_tid(p) if os.path.exists(long_path(p)) else None
        if old and tid and old != tid:
            raise BuildError('בתיקייה דוח של עסקה אחרת (%s): לא נדרס' % old)
    for p in (html_path, json_path):
        check_write_path(p)
    html = build_report(tpl, data, placeholder)
    moved = archive_previous(deal_dir, kind, data_path, lang)
    if archived is not None:
        archived.extend(moved)
    with io.open(json_path, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    with io.open(html_path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(html)
    return html_path, json_path
