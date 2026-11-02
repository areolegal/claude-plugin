# -*- coding: utf-8 -*-
"""common/brand_tokens.py: מיתוג לקוח לפי בקשה, במערכת אסימונים סגורה.

ברירת המחדל היא עיצוב AREO, בלי שום סטייה. רק כשהלקוח מבקש להשתמש בלוגו שלו, ובקובץ לוגו בפועל, המודול
קורא את הצבעים הבולטים בלוגו, גוזר מהם קבוצה סגורה של ארבעה אסימונים (accent, accent-bg, accent-ink, on-brand)
לתצוגה כהה ולתצוגה בהירה, בודק ניגודיות, ומחזיר גוש <style id="client-brand"> שדורס רק את האסימונים האלה
ומיקום ללוגו (RTL ו-LTR). בלי קובץ לוגו הוא מחזיר None, ועמוד שלא קיבל מיתוג נשאר זהה בבייטים לעיצוב AREO.

מה שאינו משתנה לעולם: צבעי הרמזור (--tr-*), צבע החימר של פעולת Claude (--clay) וסימן Areo.

בדיקת ניגודיות (WCAG 2.x, יחס בין הארוך יחסי):
  * accent כטקסט או כקישור, על כל המשטחים של התצוגה: לפחות 4.5:1 (גם הרף לגודל רגיל של טקסט);
  * accent-ink על accent-bg ועל המשטח: לפחות 4.5:1;
  * on-brand על accent, ועל שני קצות המעבר של כפתור ראשי: לפחות 4.5:1 (ובכל מקרה לא פחות מ-3:1 לטקסט גדול ובקרים).
צבע שחורג מהרף מותאם בגוון קבוע, בשינוי בהירות בלבד, עד MAX_SHIFT (הכהיה) או MAX_SHIFT_DARK (הבהרה). צבע שדורש יותר מזה נפסל, ובודקים את הצבע הבא בלוגו.
אם אף צבע בלוגו אינו עומד ברף בשתי התצוגות, זה "נסיגה בטוחה": נשארים בצבעי AREO והמודול מחזיר הודעה גלויה ללקוח.
הלוגו עצמו מוצג בכל מקרה, על לוחית בצבע מנוגד כשהוא היה נבלע ברקע.

פורמטים: PNG, SVG (בלי תלות). JPG, GIF ו-WebP דורשים Pillow; בלעדיו המודול מבקש PNG או SVG, ואינו מנחש.
הגבלה: ב-SVG הצבעים נספרים לפי מספר ההופעות ולא לפי שטח; PNG בשזירה (interlaced) ובתמונה גדולה מאוד בלי Pillow מטופלים לאט או נדחים.

שימוש:
  python3 -B brand_tokens.py --logo logo.png [--lang he|en] --out brand.json
  from common.brand_tokens import build_brand, merge_into_payload, apply_to_html
"""
import base64
import colorsys
import io
import math
import re
import struct
import sys
import zlib

if __name__ == '__main__':
    sys.dont_write_bytecode = True

MIN_TEXT = 4.5       # טקסט רגיל
MIN_LARGE = 3.0      # טקסט גדול ובקרים
MAX_SHIFT = 0.40     # שינוי הבהירות המרבי (HSL) להכהיה בתצוגה בהירה, בגוון קבוע
MAX_SHIFT_DARK = 0.60  # להבהרה בתצוגה כהה: כל צבע כהה חייב להתבהר שם, ולכן הרף מתון יותר
MAX_LOGO_BYTES = 150 * 1024

# המשטחים של התצוגות (כמו ב-AREO-KIT): הטקסט והבקרים של המותג חייבים לעמוד בניגודיות מול כולם
SURFACES = {
    'light': ['#FFFFFF', '#F4F7F5', '#F0F3F6', '#E7EDEA'],
    'dark': ['#0E1016', '#151923', '#1A1F2B', '#202636'],
}
ON_BRAND_CANDIDATES = {'light': ['#FFFFFF', '#10221C', '#04140E'], 'dark': ['#04140E', '#0E1016', '#FFFFFF']}
# ברירת המחדל של AREO (נסיגה בטוחה): בדיוק האסימונים של ה-KIT
AREO_DEFAULT = {
    'light': {'accent': '#0B8C66', 'accent-bg': '#E1F5EC', 'accent-ink': '#0B6B4F', 'on-brand': '#FFFFFF'},
    'dark': {'accent': '#2FE6A6', 'accent-bg': 'rgba(47,230,166,.12)', 'accent-ink': '#7DF2C8', 'on-brand': '#04140E'},
}
TOKEN_KEYS = ('accent', 'accent-bg', 'accent-ink', 'on-brand')

NOTICE = {
    'he': 'הצבעים של הלוגו שלכם לא עומדים בבדיקת הקריאות (ניגודיות), ולכן העמודים נשארו בצבעי Areo. הלוגו מוצג כרגיל. '
          'אפשר לשלוח גרסה של הלוגו בצבעים כהים וחדים יותר.',
    'en': 'Your logo colours do not pass the readability (contrast) check, so the pages stay in Areo colours. '
          'The logo is shown as usual. You can send a version of the logo in darker, stronger colours.',
}


class BrandError(Exception):
    """הלוגו אינו ניתן לקריאה. ההודעה אומרת ללקוח מה לעשות."""


# ---------------------------------------------------------------- צבע וניגודיות
def hex_to_rgb(h):
    h = h.strip().lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return '#%02X%02X%02X' % tuple(max(0, min(255, int(round(c)))) for c in rgb)


def _lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(rgb):
    r, g, b = (_lin(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    """יחס הניגודיות (1 עד 21) בין שני צבעים (#hex או tuple)."""
    la = luminance(hex_to_rgb(a) if isinstance(a, str) else a)
    lb = luminance(hex_to_rgb(b) if isinstance(b, str) else b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def mix(a, b, t):
    """t חלק מ-b ו-(1-t) מ-a."""
    return tuple(a[i] * (1 - t) + b[i] * t for i in range(3))


def _hls(rgb):
    h, l, s = colorsys.rgb_to_hls(*(c / 255.0 for c in rgb))
    return h, l, s


def _from_hls(h, l, s):
    return tuple(c * 255 for c in colorsys.hls_to_rgb(h, max(0.0, min(1.0, l)), s))


def fit(rgb, bgs, target, direction):
    """מחזיר צבע באותו גוון ורוויה, שהניגודיות שלו מול כל ה-bgs היא לפחות target, בשינוי בהירות מינימלי
    לכיוון direction (-1 כהה יותר, +1 בהיר יותר). None כשהשינוי הנדרש חורג מהמרבי."""
    h, l, s = _hls(rgb)
    cur = rgb
    steps = int((MAX_SHIFT if direction < 0 else MAX_SHIFT_DARK) / 0.005) + 1
    for i in range(steps):
        nl = l + direction * 0.005 * i
        if nl < 0 or nl > 1:
            break
        cur = _from_hls(h, nl, s)
        q = tuple(round(c) for c in cur)
        if min(contrast(q, bg) for bg in bgs) >= target:
            return q
    return None


def _flat(accent, alpha, surface):
    return mix(hex_to_rgb(surface), accent, alpha)


# ---------------------------------------------------------------- גזירת האסימונים
def derive_theme(rgb, theme):
    """אסימוני תצוגה אחת מצבע אחד, או None כשהצבע לא יכול לעמוד ברף. מחזיר dict עם האסימונים, הצבעים הגולמיים
    ורשימת בדיקות (שם, יחס, רף)."""
    surfaces = SURFACES[theme]
    base = surfaces[1]
    direction = -1 if theme == 'light' else 1
    # accent: משמש גם כטקסט וגם כמילוי כפתור
    accent = fit(rgb, surfaces, MIN_TEXT, direction)
    if accent is None:
        return None
    if theme == 'light':
        bg = mix(accent, (255, 255, 255), 0.88)
        bg_css = rgb_to_hex(bg)
        bg_flat = bg
        ink0 = _from_hls(*(lambda h, l, s: (h, l - 0.06, s))(*_hls(accent)))
    else:
        bg_css = 'rgba(%d,%d,%d,.12)' % tuple(accent)
        bg_flat = _flat(accent, 0.12, base)
        ink0 = _from_hls(*(lambda h, l, s: (h, l + 0.08, s))(*_hls(accent)))
    ink = fit(ink0, surfaces + [rgb_to_hex(bg_flat)], MIN_TEXT, direction)
    if ink is None:
        return None
    # מעבר הכפתור הראשי: קצה שני קרוב לאקסנט, מעט כהה בבהיר ומעט בהיר בכהה? לא: מעט מוסט בלבד, ובלבד שהטקסט נשאר קריא
    h, l, s = _hls(accent)
    brand2 = _from_hls(h, l + (-0.05 if theme == 'light' else -0.06), s)
    brand2 = tuple(round(c) for c in brand2)
    on_brand = None
    for cand in ON_BRAND_CANDIDATES[theme]:
        if min(contrast(cand, accent), contrast(cand, brand2)) >= MIN_TEXT:
            on_brand = cand
            break
    if on_brand is None:
        brand2 = accent
        for cand in ON_BRAND_CANDIDATES[theme]:
            if contrast(cand, accent) >= MIN_TEXT:
                on_brand = cand
                break
    if on_brand is None:
        return None
    checks = [
        ('accent/' + theme + ' surfaces (text)', min(contrast(accent, s_) for s_ in surfaces), MIN_TEXT),
        ('accent-ink/accent-bg', contrast(ink, bg_flat), MIN_TEXT),
        ('accent-ink/surfaces', min(contrast(ink, s_) for s_ in surfaces), MIN_TEXT),
        ('on-brand/accent', contrast(on_brand, accent), MIN_TEXT),
        ('on-brand/brand-2', contrast(on_brand, brand2), MIN_TEXT),
        ('accent/surfaces (controls)', min(contrast(accent, s_) for s_ in surfaces), MIN_LARGE),
    ]
    if any(c[1] < c[2] for c in checks):
        return None
    return {
        'tokens': {'accent': rgb_to_hex(accent), 'accent-bg': bg_css, 'accent-ink': rgb_to_hex(ink), 'on-brand': on_brand},
        'brand-2': rgb_to_hex(brand2), 'accent_rgb': tuple(accent),
        'checks': [(n, round(v, 2), t) for n, v, t in checks],
    }


def derive_tokens(candidates):
    """candidates: צבעי הלוגו לפי חשיבות. מחזיר (light, dark, צבע מקור) לצבע הראשון שעובר בשתי התצוגות,
    או None כשאף צבע אינו עובר."""
    for rgb in candidates:
        light = derive_theme(rgb, 'light')
        dark = derive_theme(rgb, 'dark')
        if light and dark:
            return light, dark, rgb
    return None


# ---------------------------------------------------------------- קריאת צבעים מהלוגו
_NAMED = {'black': '#000000', 'white': '#ffffff', 'red': '#ff0000', 'blue': '#0000ff', 'green': '#008000',
          'navy': '#000080', 'yellow': '#ffff00', 'orange': '#ffa500', 'purple': '#800080', 'teal': '#008080',
          'gray': '#808080', 'grey': '#808080', 'maroon': '#800000', 'olive': '#808000', 'lime': '#00ff00',
          'aqua': '#00ffff', 'cyan': '#00ffff', 'fuchsia': '#ff00ff', 'magenta': '#ff00ff', 'silver': '#c0c0c0',
          'gold': '#ffd700', 'pink': '#ffc0cb', 'brown': '#a52a2a', 'crimson': '#dc143c', 'indigo': '#4b0082',
          'darkblue': '#00008b', 'darkgreen': '#006400', 'darkred': '#8b0000', 'royalblue': '#4169e1'}
_HEXRE = re.compile(r'#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})(?![0-9a-zA-Z])')
_RGBRE = re.compile(r'rgba?\(\s*(\d{1,3})\s*[, ]\s*(\d{1,3})\s*[, ]\s*(\d{1,3})')
_SVGPROP = re.compile(r'(?:fill|stroke|stop-color|color)\s*[:=]\s*["\']?\s*([^;"\'>]+)', re.I)


def _svg_colors(text):
    if re.search(r'<script|\bon[a-z]+\s*=|javascript:', text, re.I):
        raise BrandError('קובץ ה-SVG מכיל קוד פעיל ולכן לא נקרא. שלחו לוגו כקובץ SVG נקי, או כ-PNG.\n'
                         'The SVG file contains active code, so it was not read. Send a clean SVG, or a PNG.')
    counts = {}
    for m in _SVGPROP.finditer(text):
        v = m.group(1).strip().lower()
        rgb = None
        h = _HEXRE.search(v)
        r = _RGBRE.search(v)
        if h:
            rgb = hex_to_rgb(h.group(1))
        elif r:
            rgb = tuple(min(255, int(x)) for x in r.groups())
        elif v in _NAMED:
            rgb = hex_to_rgb(_NAMED[v])
        if rgb:
            counts[rgb] = counts.get(rgb, 0) + 1
    return counts


def _paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    return a if pa <= pb and pa <= pc else (b if pb <= pc else c)


def _png_counts(raw):
    """קורא PNG בלי תלות: עומק 1 עד 16 סיביות, כל סוגי הצבע, בלי שזירה. מחזיר {rgb: ספירה} של פיקסלים אטומים."""
    if not raw.startswith(b'\x89PNG\r\n\x1a\n'):
        raise BrandError('הקובץ אינו PNG תקין.')
    pos, idat, plte, trns = 8, [], None, None
    w = h = depth = ctype = interlace = None
    while pos + 8 <= len(raw):
        ln, typ = struct.unpack('>I4s', raw[pos:pos + 8])
        body = raw[pos + 8:pos + 8 + ln]
        pos += 12 + ln
        if typ == b'IHDR':
            w, h, depth, ctype, _, _, interlace = struct.unpack('>IIBBBBB', body)
        elif typ == b'PLTE':
            plte = body
        elif typ == b'tRNS':
            trns = body
        elif typ == b'IDAT':
            idat.append(body)
        elif typ == b'IEND':
            break
    if w is None or not idat:
        raise BrandError('קובץ ה-PNG פגום.')
    if interlace:
        raise _NeedPillow('PNG בשזירה')
    ch = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(ctype)
    if ch is None:
        raise BrandError('סוג צבע לא נתמך ב-PNG.')
    data = zlib.decompress(b''.join(idat))
    bits = ch * depth
    stride = (w * bits + 7) // 8
    bpp = max(1, bits // 8)
    step = max(1, int(math.sqrt(w * h / 40000.0)))   # דגימה: כ-40,000 פיקסלים לכל היותר
    prev = bytearray(stride)
    counts = {}
    p = 0
    for y in range(h):
        ft = data[p]
        line = bytearray(data[p + 1:p + 1 + stride])
        p += 1 + stride
        if ft == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 255
        elif ft == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 255
        elif ft == 3:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 255
        elif ft == 4:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                c = prev[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + _paeth(a, prev[i], c)) & 255
        prev = line
        if y % step:
            continue
        for x in range(0, w, step):
            if depth == 8:
                o = x * ch
                px = line[o:o + ch]
                vals = list(px)
            elif depth == 16:
                o = x * ch * 2
                vals = [line[o + 2 * k] for k in range(ch)]
            else:
                per = 8 // depth
                byte = line[x // per]
                shift = 8 - depth * (x % per + 1)
                v = (byte >> shift) & ((1 << depth) - 1)
                vals = [v if ctype == 3 else v * 255 // ((1 << depth) - 1)]
            a = 255
            if ctype == 0:
                rgb = (vals[0],) * 3
            elif ctype == 2:
                rgb = tuple(vals[:3])
            elif ctype == 3:
                idx = vals[0]
                if not plte or idx * 3 + 3 > len(plte):
                    continue
                rgb = tuple(plte[idx * 3:idx * 3 + 3])
                if trns and idx < len(trns):
                    a = trns[idx]
            elif ctype == 4:
                rgb, a = (vals[0],) * 3, vals[1]
            else:
                rgb, a = tuple(vals[:3]), vals[3]
            if a >= 128:
                counts[rgb] = counts.get(rgb, 0) + 1
    return counts


class _NeedPillow(Exception):
    pass


def _pillow_counts(raw):
    try:
        from PIL import Image
    except ImportError:
        raise BrandError('קובץ הלוגו בפורמט שדורש רכיב קריאה נוסף שאינו מותקן (JPG, GIF, WebP או PNG בשזירה). '
                         'שלחו את הלוגו כ-PNG רגיל או כ-SVG.\nThis logo format needs an extra image reader that is '
                         'not installed (JPG, GIF, WebP or interlaced PNG). Send the logo as a plain PNG or an SVG.')
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except Exception:
        raise BrandError('קובץ הלוגו פגום או שאינו תמונה. שלחו קובץ אחר.\nThe logo file is damaged or is not an image.')
    im = img.convert('RGBA')
    im.thumbnail((200, 200))
    counts = {}
    for r, g, b, a in im.getdata():
        if a >= 128:
            counts[(r, g, b)] = counts.get((r, g, b), 0) + 1
    return counts


def sniff(raw):
    if raw.startswith(b'\x89PNG'):
        return 'png'
    if raw[:3] == b'\xff\xd8\xff':
        return 'jpg'
    if raw[:4] == b'GIF8':
        return 'gif'
    if raw[:4] == b'RIFF' and raw[8:12] == b'WEBP':
        return 'webp'
    head = raw[:600].lstrip(b'\xef\xbb\xbf \r\n\t').lower()
    if head.startswith(b'<?xml') or head.startswith(b'<svg') or b'<svg' in head:
        return 'svg'
    return None


def logo_counts(raw, use_pillow=None):
    """{rgb: משקל} של פיקסלי הלוגו. use_pillow: None (אוטומטי: PNG בלי תלות, השאר ב-Pillow), True, False."""
    kind = sniff(raw)
    if kind is None:
        raise BrandError('פורמט הלוגו לא מוכר. שלחו PNG או SVG.\nUnknown logo format. Send a PNG or an SVG.')
    if kind == 'svg':
        return kind, _svg_colors(raw.decode('utf-8', 'replace'))
    if kind == 'png' and use_pillow is not True:
        try:
            return kind, _png_counts(raw)
        except _NeedPillow:
            pass
        except (zlib.error, struct.error, IndexError):
            raise BrandError('קובץ ה-PNG פגום. שלחו קובץ אחר.\nThe PNG file is damaged.')
    return kind, _pillow_counts(raw)


def dominant_colors(counts):
    """צבעי הלוגו לפי חשיבות: צבעוניים לפני נייטרליים, ובתוכם לפי נפח, ללא לבן ושחור גמורים כצבע מותג."""
    if not counts:
        raise BrandError('לא נמצאו צבעים בלוגו (שקוף או ריק). שלחו לוגו אחר.\nNo colours were found in the logo.')
    buckets = {}
    for rgb, n in counts.items():
        key = tuple(c >> 3 for c in rgb)           # 5 סיביות לערוץ
        b = buckets.setdefault(key, [0, 0, 0, 0])
        b[0] += n
        for i in range(3):
            b[i + 1] += rgb[i] * n
    items = []
    for key, (n, r, g, b) in buckets.items():
        rgb = (r / n, g / n, b / n)
        h, l, s = _hls(rgb)
        items.append([rgb, n, l, s])
    # איחוד שכנים קרובים
    items.sort(key=lambda x: -x[1])
    merged = []
    for it in items:
        for m in merged:
            if sum((it[0][i] - m[0][i]) ** 2 for i in range(3)) < 40 ** 2:
                tot = m[1] + it[1]
                m[0] = tuple((m[0][i] * m[1] + it[0][i] * it[1]) / tot for i in range(3))
                m[1] = tot
                break
        else:
            merged.append(it)
    total = float(sum(m[1] for m in merged))
    chrom, neutral = [], []
    for rgb, n, l, s in merged:
        rgb = tuple(int(round(c)) for c in rgb)
        l = _hls(rgb)[1]
        s = _hls(rgb)[2]
        near_white = min(rgb) >= 235
        near_black = max(rgb) <= 24
        if near_white and s < 0.5:
            continue                                  # רקע
        if s >= 0.25 and not near_black:
            chrom.append((n * (0.4 + s), rgb))
        elif not near_white:
            neutral.append((n, rgb))
    if not chrom and not neutral:
        raise BrandError('הלוגו כולו לבן או שקוף ואין בו צבע לגזור ממנו מותג. שלחו לוגו אחר.\n'
                         'The logo is all white or transparent, so there is no colour to build a brand from.')
    chrom.sort(key=lambda x: -x[0])
    neutral.sort(key=lambda x: -x[0])
    # צבע ששוקל פחות מ-2 אחוז מהלוגו הוא רעש (קצוות החלקה)
    out = [c for w_, c in chrom if w_ / (total or 1) >= 0.02] or [c for _, c in chrom[:1]]
    out += [c for _, c in neutral]
    return out


# ---------------------------------------------------------------- הפלט
def _rgba(rgb, a):
    return 'rgba(%d,%d,%d,%s)' % (rgb[0], rgb[1], rgb[2], a)


def _theme_block(sel, tk, brand2, accent_rgb):
    a = tk['accent']
    return ('%s{--accent:%s;--accent-bg:%s;--accent-ink:%s;--on-brand:%s;--brand:%s;--brand-2:%s;'
            '--grad:linear-gradient(120deg,%s 0%%,%s 100%%);--glow:0 0 0 1px %s,0 8px 30px %s}'
            % (sel, a, tk['accent-bg'], tk['accent-ink'], tk['on-brand'], a, brand2, a, brand2,
               _rgba(accent_rgb, '.35'), _rgba(accent_rgb, '.18')))


# מיקום הלוגו: בצד ההתחלה של הכותרת בשתי הכיוונים (שוליים לוגיים), ומשטח מנוגד כשהוא נבלע ברקע
LOGO_CSS = (
    '.client-logo{max-height:34px;max-width:190px;width:auto;height:auto;object-fit:contain;flex:0 0 auto;'
    'margin-inline-end:14px;border-radius:6px}\n'
    'html[dir="rtl"] .client-logo{object-position:right center}\n'
    'html[dir="ltr"] .client-logo{object-position:left center}\n'
    '@media print{.client-logo{max-height:28px}}')


def _logo_plate(logo_rgb):
    """משטח מאחורי הלוגו לפי הבהירות שלו: לוגו כהה מקבל משטח בהיר בתצוגה כהה, ולוגו בהיר משטח כהה בתצוגה בהירה."""
    lum = luminance(logo_rgb)
    css = ''
    if lum < 0.18:
        css += ':root:not([data-theme="light"]) .client-logo{background:#FFFFFF;padding:4px 8px}\n'
    if lum > 0.45:
        css += ':root[data-theme="light"] .client-logo{background:#10221C;padding:4px 8px}\n'
    return css


def _data_uri(raw, kind):
    mime = {'png': 'image/png', 'jpg': 'image/jpeg', 'gif': 'image/gif', 'webp': 'image/webp',
            'svg': 'image/svg+xml'}[kind]
    if len(raw) > MAX_LOGO_BYTES:
        if kind == 'svg':
            raise BrandError('קובץ הלוגו גדול מ-%d קילובייט. שלחו גרסה קטנה יותר.\nThe logo file is larger than %d KB.'
                             % (MAX_LOGO_BYTES // 1024, MAX_LOGO_BYTES // 1024))
        try:   # raster: הקטנה באמצעות מודול הלוגו הקיים (Pillow), כמו בדוח הסיכונים
            from PIL import Image
            img = Image.open(io.BytesIO(raw))
            img.load()
            img.thumbnail((240, 240))
            buf = io.BytesIO()
            img.convert('RGBA').save(buf, 'PNG', optimize=True)
            raw, mime = buf.getvalue(), 'image/png'
        except Exception:
            raise BrandError('קובץ הלוגו גדול מ-%d קילובייט. שלחו גרסה קטנה יותר.\nThe logo file is larger than %d KB.'
                             % (MAX_LOGO_BYTES // 1024, MAX_LOGO_BYTES // 1024))
        if len(raw) > MAX_LOGO_BYTES:
            raise BrandError('קובץ הלוגו גדול מ-%d קילובייט גם אחרי הקטנה.\nThe logo is still too large after resizing.'
                             % (MAX_LOGO_BYTES // 1024))
    return 'data:%s;base64,%s' % (mime, base64.b64encode(raw).decode('ascii'))


def build_brand(logo, lang='he', use_pillow=None):
    """logo: נתיב לקובץ לוגו או bytes. בלי לוגו (None או ריק): מחזיר None, והעמוד נשאר בעיצוב AREO, זהה בבייטים.
    מחזיר dict:
      css       גוש ה-CSS (בלי תגית): אסימונים בכהה ובבהיר, ומיקום הלוגו. ריק מאסימונים בנסיגה בטוחה.
      html      '<style id="client-brand">' + css + '</style>' להזרקה בשרת
      logo      data URI של הלוגו
      notice    הודעה גלויה ללקוח בנסיגה בטוחה ('' אחרת)
      fallback  True כשהלוגו לא עמד בניגודיות
      tokens    {'light': {...}, 'dark': {...}} האסימונים בפועל
      widget_css  דריסה של אסימוני ה-.af לווידג'טים של הצ'אט (בלי הערות ובלי גרדיאנט)
      checks    רשימת בדיקות הניגודיות
      source    צבע הלוגו שנבחר (או None), ו-candidates: הצבעים שנבדקו"""
    if logo is None or logo == '' or logo == b'':
        return None
    lang = 'en' if str(lang).lower().startswith('en') else 'he'
    if isinstance(logo, (bytes, bytearray)):
        raw = bytes(logo)
    else:
        try:
            with open(logo, 'rb') as fh:
                raw = fh.read()
        except OSError:
            raise BrandError('קובץ הלוגו לא נמצא או לא נפתח. בדקו את הנתיב ושלחו שוב.\nThe logo file was not found.')
    kind, counts = logo_counts(raw, use_pillow)
    cands = dominant_colors(counts)
    res = derive_tokens(cands)
    uri = _data_uri(raw, kind)
    out = {'logo': uri, 'candidates': [rgb_to_hex(c) for c in cands[:6]], 'lang': lang}
    if res is None:
        out.update(fallback=True, notice=NOTICE[lang], source=None,
                   tokens={k: dict(v) for k, v in AREO_DEFAULT.items()}, checks=[],
                   widget_css='')
        css = LOGO_CSS + '\n' + _logo_plate(cands[0])
    else:
        light, dark, src = res
        out.update(fallback=False, notice='', source=rgb_to_hex(src),
                   tokens={'light': light['tokens'], 'dark': dark['tokens']},
                   checks=[('light ' + n, v, t) for n, v, t in light['checks']] +
                          [('dark ' + n, v, t) for n, v, t in dark['checks']])
        css = (_theme_block(':root:not([data-theme="light"])', dark['tokens'], dark['brand-2'], dark['accent_rgb']) + '\n' +
               _theme_block(':root[data-theme="light"]', light['tokens'], light['brand-2'], light['accent_rgb']) + '\n' +
               LOGO_CSS + '\n' + _logo_plate(src))
        lt, dk = light['tokens'], dark['tokens']
        out['widget_css'] = (
            '.af{--accent:%s;--accent-bg:%s;--accent-ink:%s;--on-brand:%s}\n'
            '@media (prefers-color-scheme:dark){.af{--accent:%s;--accent-bg:%s;--accent-ink:%s;--on-brand:%s}}\n'
            ':root[data-mode="dark"] .af{--accent:%s;--accent-bg:%s;--accent-ink:%s;--on-brand:%s}\n'
            ':root[data-mode="light"] .af{--accent:%s;--accent-bg:%s;--accent-ink:%s;--on-brand:%s}'
            % ((lt['accent'], lt['accent-bg'], lt['accent-ink'], lt['on-brand']) +
               (dk["accent"], dk["accent-bg"], dk["accent-ink"], dk["on-brand"]) +
               (dk['accent'], dk['accent-bg'], dk['accent-ink'], dk['on-brand']) +
               (lt['accent'], lt['accent-bg'], lt['accent-ink'], lt['on-brand'])))
    out['css'] = css.strip()
    out['html'] = '<style id="client-brand">\n' + out['css'] + '\n</style>'
    return out


def merge_into_payload(payload, brand):
    """שם את התוצאה ב-payload['meta']['branding'] (css, logo, notice). בלי brand (None): מחזיר את ה-payload כמות
    שהוא, ולכן הפלט זהה בבייטים לעיצוב AREO."""
    if brand is None:
        return payload
    b = payload.setdefault('meta', {}).setdefault('branding', {})
    b['css'] = brand['css']
    b['logo'] = brand['logo']
    b['notice'] = brand['notice']
    b['fallback'] = brand['fallback']
    return payload


def apply_to_html(html, brand):
    """מזריק את <style id="client-brand"> לפני </head>. בלי brand: מחזיר את אותו אובייקט, בלי שינוי."""
    if brand is None:
        return html
    i = html.find('</head>')
    if i < 0:
        return html
    return html[:i] + brand['html'] + '\n' + html[i:]


def main(argv=None):
    import json
    try:
        from common.cli import guard_out, parser, run, write_json
    except ImportError:  # pragma: no cover
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from common.cli import guard_out, parser, run, write_json
    ap = parser('מיתוג לקוח מלוגו: אסימונים סגורים, בדיקת ניגודיות והודעה', out_required=False)
    ap.add_argument('--logo', required=True, help='קובץ לוגו (PNG או SVG, ובהתקנה עם Pillow גם JPG)')
    ap.add_argument('--lang', default='he', choices=('he', 'en'))
    a = ap.parse_args(argv)
    try:
        b = build_brand(a.logo, a.lang)
    except BrandError as e:
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:  # pragma: no cover
            pass
        print(e)
        return 3
    if a.out:
        path = write_json(a.out, b, [a.logo])
        print('written', path)
    print('fallback' if b['fallback'] else 'branded', b['source'], b['notice'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
