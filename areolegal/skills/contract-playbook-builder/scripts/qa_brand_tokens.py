# -*- coding: utf-8 -*-
"""בדיקות מיתוג הלקוח (common/brand_tokens.py): ניגודיות, נסיגה בטוחה, פורמטים, וזהות בייטים בלי לוגו.

הרצה:  python3 -B -X utf8 qa_brand_tokens.py
(מוצא את הספרייה המשותפת דרך areo_lib כשהסקריפט בחבילת הריצה, ואחרת בתיקיית הסקילים לצדו)
"""
import json
import os
import struct
import sys
import zlib

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
try:
    import areo_lib  # noqa: F401
except Exception:
    pass
try:
    from common import brand_tokens as B
except ImportError:
    cand = os.path.abspath(os.path.join(here, '..', '..', '..', '..', 'כללים משותפים לכל הסקילים', 'תוכן מהשרת',
                                        'runtime', 'lib'))
    sys.path.insert(0, cand)
    from common import brand_tokens as B

OUT = []


def check(name, ok, note=''):
    OUT.append((name, bool(ok), note))


def png(w, h, px, ctype=6):
    """PNG בלי תלות: px(x,y) -> (r,g,b,a)."""
    raw = b''
    for y in range(h):
        raw += b'\x00'
        for x in range(w):
            r, g, b, a = px(x, y)
            raw += bytes((r, g, b, a)) if ctype == 6 else bytes((r, g, b))
    def chunk(t, d):
        c = struct.pack('>I', len(d)) + t + d
        return c + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, ctype, 0, 0, 0)) +
            chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))


def solid(rgb, bg=(0, 0, 0, 0), ctype=6):
    def f(x, y):
        return rgb + (255,) if (10 <= x < 50 and 10 <= y < 40) else bg
    return png(60, 50, f, ctype)


# ---- ניגודיות: ערכים ידועים
check('שחור על לבן הוא 21:1', abs(B.contrast('#000000', '#FFFFFF') - 21) < 0.01)
check('#767676 על לבן הוא כ-4.54', abs(B.contrast('#767676', '#FFFFFF') - 4.54) < 0.02)

# ---- סריקת גוונים: אסימון שנפלט תמיד עומד ברף, וצבע שלא עומד לא נפלט
import colorsys
emitted = failed = 0
bad = []
for hue in range(0, 360, 15):
    for lt in (0.15, 0.3, 0.5, 0.7, 0.85, 0.95):
        for sat in (0.2, 0.6, 1.0):
            rgb = tuple(round(c * 255) for c in colorsys.hls_to_rgb(hue / 360.0, lt, sat))
            for theme in ('light', 'dark'):
                r = B.derive_theme(rgb, theme)
                if r is None:
                    failed += 1
                    continue
                emitted += 1
                for n, v, t in r['checks']:
                    if v < t:
                        bad.append((rgb, theme, n, v))
check('סריקה: כל אסימון שנפלט עומד ב-4.5 לטקסט וב-3 לבקרים', not bad and emitted > 200, '%d נפלטו, %d נפסלו, %s' % (emitted, failed, bad[:2]))
check('סריקה: יש צבעים שנפסלים (הרף אמיתי)', failed > 0)

# ---- לוגו בהיר חלש: נסיגה בטוחה והודעה גלויה
pale = solid((247, 232, 160))
b = B.build_brand(pale, 'he')
check('לוגו בהיר חלש: נסיגה בטוחה', b['fallback'] is True and b['source'] is None)
check('נסיגה: ההודעה גלויה בעברית', 'ניגודיות' in b['notice'] and b['notice'].strip() != '')
check('נסיגה: ההודעה באנגלית', 'contrast' in B.build_brand(pale, 'en')['notice'])
check('נסיגה: אסימוני AREO בדיוק, בלי דריסת צבעים', b['tokens']['light'] == B.AREO_DEFAULT['light'] and '--accent:' not in b['css'])
check('נסיגה: הלוגו עדיין מוצג (data URI)', b['logo'].startswith('data:image/png;base64,'))
check('נסיגה: ללוגו בהיר יש משטח כהה בתצוגה בהירה', '[data-theme="light"] .client-logo{background:#10221C' in b['css'])

# ---- לוגו כהה: מיתוג מלא
navy = solid((22, 38, 92))
d = B.build_brand(navy, 'he')
check('לוגו כהה: מיתוג בלי נסיגה', d['fallback'] is False and d['notice'] == '' and d['source'] == '#16265C')
check('לוגו כהה: בכהה הצבע הוארה לקריאות', B.contrast(d['tokens']['dark']['accent'], '#202636') >= 4.5)
check('לוגו כהה: כל בדיקות הניגודיות עוברות', all(v >= t for _, v, t in d['checks']) and len(d['checks']) >= 10,
      'מינימום %.2f' % min(v for _, v, _ in d['checks']))
check('לוגו כהה: ארבעת האסימונים בשתי התצוגות', all(set(d['tokens'][k]) == set(B.TOKEN_KEYS) for k in ('light', 'dark')))
check('גוש ה-style עם המזהה הנכון', d['html'].startswith('<style id="client-brand">') and d['html'].endswith('</style>'))
check('לוגו כהה: משטח בהיר בתצוגה כהה', ':root:not([data-theme="light"]) .client-logo{background:#FFFFFF' in d['css'])
css = d['css']
check('מיתוג אינו נוגע ברמזור, בחימר ובסימן', '--tr-' not in css and '--clay' not in css)
check('המיקום לוגי (RTL ו-LTR) בלי left/right פיזיים בשוליים', 'margin-inline-end' in css and 'margin-left' not in css and
      'margin-right' not in css and 'html[dir="rtl"]' in css and 'html[dir="ltr"]' in css)
check('ווידג\'ט: דריסה בלי הערות ובלי גרדיאנט', d['widget_css'] and '/*' not in d['widget_css'] and 'gradient' not in d['widget_css'])

# ---- בלי לוגו: זהות בבייטים
html = '<html><head><title>x</title></head><body>y</body></html>'
check('בלי לוגו: build_brand מחזיר None', B.build_brand(None) is None and B.build_brand('') is None)
check('בלי לוגו: apply_to_html מחזיר את אותו HTML בדיוק', B.apply_to_html(html, None) is html)
pl = {'meta': {'lang': 'he'}, 'rules': []}
before = json.dumps(pl, sort_keys=True)
check('בלי לוגו: ה-payload ללא שינוי', json.dumps(B.merge_into_payload(pl, None), sort_keys=True) == before)
h2 = B.apply_to_html(html, d)
check('עם לוגו: הגוש נכנס לפני </head> ולא משנה דבר אחר', h2.replace(d['html'] + '\n', '') == html)
p2 = B.merge_into_payload({'meta': {}}, d)['meta']['branding']
check('merge: css, logo, notice, fallback', set(p2) == {'css', 'logo', 'notice', 'fallback'})

# ---- פורמטים ושגיאות
svg_ok = '<svg xmlns="http://www.w3.org/2000/svg"><rect fill="#0B6E82" width="9" height="9"/><circle fill="white" r="3"/></svg>'.encode()
s = B.build_brand(svg_ok, 'he')
check('SVG: צבע המותג נקרא וללבן אין משקל', s['source'] == '#0B6E82' and s['fallback'] is False, s['source'])
try:
    B.build_brand(b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>')
    check('SVG עם קוד פעיל נדחה', False)
except B.BrandError as e:
    check('SVG עם קוד פעיל נדחה', 'קוד פעיל' in str(e))
for name, blob in (('קובץ לא מוכר', b'hello world, not an image'), ('PNG פגום', b'\x89PNG\r\n\x1a\n' + b'\x00' * 10),
                   ('PNG שקוף לגמרי', png(20, 20, lambda x, y: (0, 0, 0, 0)))):
    try:
        B.build_brand(blob)
        check(name + ': שגיאה ברורה', False)
    except B.BrandError as e:
        check(name + ': שגיאה ברורה ללקוח', len(str(e)) > 10)
try:
    B.build_brand(os.path.join(here, 'no-such-logo.png'))
    check('קובץ חסר: שגיאה ברורה', False)
except B.BrandError as e:
    check('קובץ חסר: שגיאה ברורה', 'לא נמצא' in str(e))
# צבע אחד בלוגו כבר לא עובר, והשני כן: לוגו שני-צבעים בוחר את השני במקום ליפול
two = png(60, 50, lambda x, y: (247, 232, 160, 255) if x < 30 else (11, 110, 130, 255))
t2 = B.build_brand(two)
check('לוגו עם שני צבעים: נבחר הצבע שעובר ולא נסיגה', t2['fallback'] is False and t2['source'] == '#0B6E82', str(t2['source']))
# שלושת סוגי ה-PNG ללא Pillow
pg = B.build_brand(solid((11, 110, 130), (255, 255, 255, 255), ctype=6), use_pillow=False)
check('PNG אטום עם רקע לבן: הרקע לא נבחר', pg['source'] == '#0B6E82')
rgb_png = B.build_brand(solid((11, 110, 130), (255, 255, 255, 0), ctype=2), use_pillow=False)
check('PNG RGB בלי אלפא (סוג 2)', rgb_png['fallback'] is False)
try:
    import PIL  # noqa: F401
    a1 = B.build_brand(navy, use_pillow=True)['tokens']
    a2 = B.build_brand(navy, use_pillow=False)['tokens']
    check('אותם אסימונים עם Pillow ובלעדיו', a1 == a2)
except ImportError:
    check('Pillow לא מותקן: JPG מבקש PNG או SVG', True, 'לא נבדק: Pillow חסר')

bad = 0
for n, ok, note in OUT:
    bad += 0 if ok else 1
    print(('✓ ' if ok else '✗ ') + n + (('  [' + note + ']') if note else ''))
print('כשלים: %d' % bad if bad else 'בדיקות מיתוג הלקוח עוברות (%d)' % len(OUT))
sys.exit(1 if bad else 0)
