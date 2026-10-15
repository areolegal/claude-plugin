# -*- coding: utf-8 -*-
"""בדיקות ל-risk/render_check.py: התבנית המתוקנת (הערות 3.5) עם המרשם של C1ב מסבב 2 נטענת בדפדפן אמיתי,
אינה ריקה, אינה פונה לרשת, ופס הסימון אינו חופף לשום טקסט; גוף הדוח עד 8 עמודים. ובכיוון ההפוך: פס
position:fixed (כמו בגרסה 3.4) נתפס כחפיפה עם הכותרות, הערה שלא נסגרה נתפסת כעמוד ריק, ובקשה חיצונית נתפסת.
הבדיקות בדפדפן מדולגות כשאין Chrome או Edge במחשב."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from risk.render_check import (ENTITY_BODY_LIMIT, ENTITY_MARKERS, analyse, band_text_from_register,  # noqa: E402
                               build_report, find_browser, run_check, static_checks)

FX = ROOT / 'tests' / 'fixtures' / 'risk'
TEMPLATE = (FX / 'risk-report-template.html').read_text(encoding='utf-8')
REGISTER = json.loads((FX / 'c1b_register.json').read_text(encoding='utf-8'))
BROWSER = find_browser()
needs_browser = pytest.mark.skipif(BROWSER is None, reason='אין Chrome או Edge במחשב')


# ---------- בלי דפדפן ----------
def test_build_report_requires_single_placeholder():
    html = build_report(TEMPLATE, REGISTER)
    assert "__RISK_DATA__" not in html
    with pytest.raises(ValueError):
        build_report(TEMPLATE + '__RISK_DATA__', REGISTER)


def test_static_checks_on_fixed_template_and_on_defects():
    assert static_checks(TEMPLATE) == []
    assert static_checks(TEMPLATE.replace('-->', '', 1))  # הערה שלא נסגרה (התקלה של 3.3)
    assert static_checks(TEMPLATE.replace('</head>', '<link rel="stylesheet" href="https://fonts.googleapis.com/x"></head>'))


def test_template_has_no_fixed_band_in_print_and_has_margin_boxes():
    import re
    assert not re.search(r'position:\s*fixed\s*[;}!]', TEMPLATE)
    assert '@top-center' in TEMPLATE and '@bottom-center' in TEMPLATE
    # תוויות קבועות שהקורא רואה: "הצד השני", לא "הצד שכנגד"
    assert 'cp:"הצד השני"' in TEMPLATE and 'בדיקת הצד השני לא בוצעה' in TEMPLATE
    assert 'cp:"הצד שכנגד"' not in TEMPLATE and 'בדיקת הצד שכנגד' not in TEMPLATE


def test_analyse_detects_overlap_geometry():
    marker = 'טיוטה, טעונה אישור · חסוי: מסמך עבודה של המחלקה המשפטית'
    band = {'text': marker, 'x0': 40, 'x1': 550, 'top': 45, 'bottom': 57}
    head = {'text': 'התמונה במבט אחד', 'x0': 450, 'x1': 542, 'top': 49, 'bottom': 66}
    body = {'text': 'טקסט רגיל', 'x0': 100, 'x1': 300, 'top': 120, 'bottom': 132}
    res = analyse([{'size': (595, 842), 'runs': [band, head, body]}], marker)
    assert res['band_lines'] == 1 and len(res['overlaps']) == 1
    assert res['heading_overlaps'][0]['heading'] == 'התמונה במבט אחד'
    clean = analyse([{'size': (595, 842), 'runs': [dict(band, top=20, bottom=28), head, body]}], marker)
    assert clean['overlaps'] == [] and clean['body_pages'] == 1


def test_band_text_from_register():
    t = band_text_from_register(REGISTER)
    assert t.startswith('טיוטה, טעונה אישור · חסוי:') and 'EXAMPLECO' in t
    assert 'קיים ספק' in band_text_from_register({'meta': {'company': 'X'}})


# ---------- בדפדפן אמיתי ----------
def _run(tmp_path, html, **kw):
    page = tmp_path / 'report.html'
    page.write_text(html, encoding='utf-8')
    return run_check(str(page), str(tmp_path / 'out'), band_text_from_register(REGISTER), browser=BROWSER, **kw)


@needs_browser
def test_fixed_template_passes_with_round2_register(tmp_path):
    res = _run(tmp_path, build_report(TEMPLATE, REGISTER), twice=True)
    assert res['verdict'] == 'PASS', res['fails']
    assert res['dom_text_chars'] > 5000 and res['title'].startswith('Areo Workspace')
    assert res['external_requests'] == [] and res['js_exceptions'] == []
    assert res['overlaps'] == [] and res['band_on_pages'] == res['pages']
    assert res['appendix_page'] and 1 <= res['body_pages'] <= 8
    assert res['second_print']['pages'] == res['pages']


@needs_browser
def test_fixed_position_band_is_caught(tmp_path):
    bad = TEMPLATE.replace('</style>', '@media print{.warnband{position:fixed!important;top:0;left:0;right:0;z-index:50}}</style>', 1)
    res = _run(tmp_path, build_report(bad, REGISTER))
    assert 'band_overlap' in res['fails']
    assert res['heading_overlaps'], 'החפיפה צריכה לכלול כותרת או שורת כותרת של טבלה'


@needs_browser
def test_blank_page_and_external_request_are_caught(tmp_path):
    bad = TEMPLATE.replace('-->', '', 1).replace('</head>', '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Heebo"></head>', 1)
    res = _run(tmp_path, build_report(bad, REGISTER))
    assert 'blank' in res['fails']
    ext = TEMPLATE.replace('</body>', '<img src="https://example.invalid/pixel.png" alt=""></body>', 1)
    res2 = _run(tmp_path, build_report(ext, REGISTER))
    assert 'external_requests' in res2['fails'] and res2['external_requests']


@needs_browser
def test_body_page_limit_gives_exit_2(tmp_path):
    res = _run(tmp_path, build_report(TEMPLATE, REGISTER), body_limit=2)
    assert res['exit'] == 2 and res['fails'] == ['body_pages>2']


@needs_browser
def test_entity_report_template_renders_within_two_pages(tmp_path):
    """תבנית דוח חקר הישות (הערות 3.5, החלפה 9.17), עם נתוני חקר הישות של סבב 2 אחרי ניקוי הטוקנים."""
    tpl = (ROOT / 'risk' / 'resources' / 'entity-report-template.html').read_text(encoding='utf-8')  # הקובץ המוגש (3.6)
    data = json.loads((FX / 'c2_entity_report.json').read_text(encoding='utf-8'))
    assert static_checks(tpl) == []
    page = tmp_path / 'entity.html'
    page.write_text(build_report(tpl, data, '__ENTITY_DATA__'), encoding='utf-8')
    res = run_check(str(page), str(tmp_path / 'out'), band_text_from_register(data), browser=BROWSER,
                    markers=ENTITY_MARKERS, body_limit=ENTITY_BODY_LIMIT)
    assert res['verdict'] == 'PASS', res['fails']
    assert res['pages'] <= 2 and res['external_requests'] == [] and res['overlaps'] == []
