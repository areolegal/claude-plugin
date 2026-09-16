# -*- coding: utf-8 -*-
"""מספור סעיפים כפי ש-Word מציג אותו, ותיקון הפניות פנימיות.

הסכמים אמיתיים בעברית ממוספרים כמעט תמיד במספור אוטומטי של Word: הספרה אינה
כתובה בטקסט אלא מחושבת בזמן התצוגה מ-numbering.xml. לכן אי אפשר לדעת מה מספרו
של סעיף, ואי אפשר לתקן "כאמור בסעיף 7" אחרי מחיקת סעיף, בלי לחשב את המספור בעצמנו.

הספרייה מחשבת תווית לכל פסקה: מספור אוטומטי (כולל מספור שמגיע מסגנון), ואם אין,
מספר שכתוב בתחילת הטקסט. היא אינה מכסה כל פינה של Word (lvlRestart, רשימות
מקושרות בין מסמכים), ולכן כל שינוי הפניה מדווח, ומה שלא הוכרע אינו משתנה בשקט.
"""
import re

from docx.oxml.ns import qn

HEB_LETTERS = "אבגדהוזחטיכלמנסעפצקרשת"
# A typed clause number is "7." or "7.2" / "7.2.". A bare "12 " is not: a paragraph that
# opens "12 חודשים מיום החתימה" would otherwise be read as clause 12 and renumbered.
LITERAL_RX = re.compile(r"^\s*(\d+\.(?:\d+\.?)*|\d+(?:\.\d+)+\.?)(?=\s|\)|$)")


def _roman(n):
    vals = [(1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"), (90, "xc"),
            (50, "l"), (40, "xl"), (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]
    out = ""
    for v, s in vals:
        while n >= v:
            out += s
            n -= v
    return out


def _fmt(n, num_fmt):
    if num_fmt in ("lowerLetter", "upperLetter"):
        s = ""
        while n > 0:
            n, r = divmod(n - 1, 26)
            s = chr(97 + r) + s
        return s.upper() if num_fmt == "upperLetter" else s
    if num_fmt in ("lowerRoman", "upperRoman"):
        s = _roman(n)
        return s.upper() if num_fmt == "upperRoman" else s
    if num_fmt in ("hebrew1", "hebrew2"):
        return HEB_LETTERS[(n - 1) % len(HEB_LETTERS)]
    return str(n)


class Numbering(object):
    def __init__(self, doc):
        self.abstract = {}      # abstractNumId -> {ilvl: {start, fmt, text}}
        self.num = {}           # numId -> (abstractNumId, {ilvl: startOverride})
        self.style_num = {}     # styleId -> (numId, ilvl)
        part = doc.part
        try:
            numbering = part.numbering_part.element
        except (KeyError, NotImplementedError, AttributeError):
            numbering = None
        if numbering is not None:
            self._read_numbering(numbering)
        self._read_styles(doc)
        self.counters = {}
        self.started = set()

    def _read_numbering(self, root):
        links = {}
        for an in root.findall(qn("w:abstractNum")):
            aid = an.get(qn("w:abstractNumId"))
            lv = {}
            for l in an.findall(qn("w:lvl")):
                il = int(l.get(qn("w:ilvl")))
                start = l.find(qn("w:start"))
                fmt = l.find(qn("w:numFmt"))
                txt = l.find(qn("w:lvlText"))
                lgl = l.find(qn("w:isLgl"))
                lv[il] = {"start": int(start.get(qn("w:val"))) if start is not None else 1,
                          "fmt": fmt.get(qn("w:val")) if fmt is not None else "decimal",
                          "text": txt.get(qn("w:val")) if txt is not None else "%d." % (il + 1),
                          "lgl": lgl is not None}
            link = an.find(qn("w:numStyleLink"))
            if link is not None:
                links[aid] = link.get(qn("w:val"))
            self.abstract[aid] = lv
        for n in root.findall(qn("w:num")):
            nid = n.get(qn("w:numId"))
            aid = n.find(qn("w:abstractNumId")).get(qn("w:val"))
            over = {}
            for lo in n.findall(qn("w:lvlOverride")):
                so = lo.find(qn("w:startOverride"))
                if so is not None:
                    over[int(lo.get(qn("w:ilvl")))] = int(so.get(qn("w:val")))
            self.num[nid] = (aid, over)
        # numStyleLink: the abstract that carries the levels is the one whose
        # styleLink names the same style
        by_style = {}
        for an in root.findall(qn("w:abstractNum")):
            sl = an.find(qn("w:styleLink"))
            if sl is not None:
                by_style[sl.get(qn("w:val"))] = an.get(qn("w:abstractNumId"))
        for aid, style in links.items():
            if style in by_style:
                self.abstract[aid] = self.abstract.get(by_style[style], self.abstract[aid])

    def _read_styles(self, doc):
        styles = {}
        for st in doc.styles.element.findall(qn("w:style")):
            sid = st.get(qn("w:styleId"))
            based = st.find(qn("w:basedOn"))
            ppr = st.find(qn("w:pPr"))
            npr = ppr.find(qn("w:numPr")) if ppr is not None else None
            styles[sid] = (based.get(qn("w:val")) if based is not None else None, npr)
        for sid in styles:
            seen, cur = set(), sid
            while cur and cur not in seen:
                seen.add(cur)
                based, npr = styles.get(cur, (None, None))
                if npr is not None:
                    ni = npr.find(qn("w:numId"))
                    il = npr.find(qn("w:ilvl"))
                    if ni is not None:
                        self.style_num[sid] = (ni.get(qn("w:val")),
                                               int(il.get(qn("w:val"))) if il is not None else 0)
                    break
                cur = based

    def _num_of(self, p):
        ppr = p.find(qn("w:pPr"))
        nid, ilvl = None, 0
        if ppr is not None:
            ps = ppr.find(qn("w:pStyle"))
            if ps is not None and ps.get(qn("w:val")) in self.style_num:
                nid, ilvl = self.style_num[ps.get(qn("w:val"))]
            npr = ppr.find(qn("w:numPr"))
            if npr is not None:
                ni = npr.find(qn("w:numId"))
                il = npr.find(qn("w:ilvl"))
                if ni is not None:
                    nid = ni.get(qn("w:val"))
                if il is not None:
                    ilvl = int(il.get(qn("w:val")))
        if not nid or nid == "0" or nid not in self.num:
            return None
        return nid, ilvl

    def label(self, p):
        """התווית שהפסקה מציגה, או None. יש לקרוא בסדר המסמך: המונים מצטברים."""
        got = self._num_of(p)
        if got is None:
            return None, None
        nid, ilvl = got
        aid, over = self.num[nid]
        levels = self.abstract.get(aid, {})
        lv = levels.get(ilvl)
        if lv is None or lv["fmt"] in ("bullet", "none"):
            return None, None
        # Word: separate w:num instances of one abstractNum keep counting together,
        # unless the instance restarts a level with startOverride.
        key = aid
        cnt = self.counters.setdefault(key, {})
        if (nid, ilvl) not in self.started and ilvl in over:
            cnt[ilvl] = over[ilvl] - 1
            for deeper in [k for k in cnt if k > ilvl]:
                del cnt[deeper]
        self.started.add((nid, ilvl))
        cnt[ilvl] = cnt.get(ilvl, lv["start"] - 1) + 1
        for deeper in [k for k in cnt if k > ilvl]:
            del cnt[deeper]

        def sub(m):
            k = int(m.group(1)) - 1
            src = levels.get(k, {"start": 1, "fmt": "decimal"})
            val = cnt.get(k, src["start"])
            fmt = "decimal" if lv.get("lgl") else src["fmt"]
            return _fmt(val, fmt)

        text = re.sub(r"%(\d)", sub, lv["text"])
        return text.strip(), ilvl


def para_text(p):
    out = []
    for node in p.iter():
        if node.tag == qn("w:t"):
            out.append(node.text or "")
        elif node.tag == qn("w:tab"):
            out.append("\t")
    return "".join(out)


def labelled_paragraphs(doc):
    """כל פסקאות גוף המסמך בסדר, עם תווית, רמה וטקסט.
    kind: 'auto' למספור של Word, 'literal' למספר שכתוב בטקסט, None ללא מספר."""
    num = Numbering(doc)
    out = []
    for p in doc.element.body.iter(qn("w:p")):
        text = para_text(p)
        lab, lvl = num.label(p)
        kind = "auto" if lab else None
        if not lab:
            m = LITERAL_RX.match(text)
            if m:
                lab, kind = m.group(1), "literal"
                lvl = norm_label(lab).count(".")
        out.append({"p": p, "label": lab, "key": norm_label(lab), "level": lvl,
                    "kind": kind, "text": text})
    return out


def norm_label(lab):
    """"7." ו-"7" ו-"(7)" הם אותה הפניה."""
    if not lab:
        return None
    return lab.strip().strip("().").strip()


# ---------- הפניות פנימיות ----------
REF_HEAD = re.compile(
    r"(?:(?:ב|ל|מ|ש|ו|וב|ול|שב|כאמור\s+ב)?(?:סעיפים|סעיף(?:\s+קטן)?|ס\"ק|ס״ק|תת[\s-]סעיף)"
    r"|\b(?:[Ss]ections?|[Cc]lauses?|[Pp]aragraphs?))\s*")
REF_TOKEN = re.compile(r"\d+(?:\.\d+)*(?:\([א-תa-z0-9]{1,3}\))?")
REF_JOIN = re.compile(r"\s*(?:,|או|ו-|ו־|ו|-|–|עד|and|or|to)\s*")
# "סעיף 14 לחוק פיצויי פיטורים" מפנה לחוק, לא להסכם. שינוי שלו אחרי מחיקת סעיף
# היה משבש דין מצוטט, ולכן קבוצת הפניות שנמשכת אל שם של חיקוק אינה נוגעת.
EXTERNAL_TAIL = re.compile(
    r"^[א-ת']{0,2}\s*(?:\([^)]{0,12}\)\s*)*(?:ל|ב|של\s+)?"
    r"(?:חוק|תקנות|פקודת|צו|אמנת|הוראות\s+החוק|Act\b|Law\b|Regulations?\b|Code\b|Ordinance\b)"
    r"|^\s*(?:\([^)]{0,12}\)\s*)*of\s+(?:the\s+)?(?:[A-Z][\w'-]*\s+){0,6}(?:Act|Law|Regulations?|Code|Ordinance)\b")
# ספרה שצמודה אליה אות עברית ("30א", "13א'") היא כמעט תמיד סעיף בחיקוק.
LAW_STYLE_TOKEN = re.compile(r"^\d+[א-ת]'?")


def find_refs(text):
    """מחזיר (start, end, token) לכל מספר סעיף פנימי שמופיע אחרי מילת הפניה."""
    refs = []
    for h in REF_HEAD.finditer(text):
        pos, group = h.end(), []
        while True:
            m = REF_TOKEN.match(text, pos)
            if not m:
                break
            group.append((m.start(), m.end(), m.group(0)))
            pos = m.end()
            j = REF_JOIN.match(text, pos)
            if not j or not REF_TOKEN.match(text, j.end()):
                break
            pos = j.end()
        if not group:
            continue
        tail = text[group[-1][1]:group[-1][1] + 40]
        if EXTERNAL_TAIL.match(tail) or any(LAW_STYLE_TOKEN.match(text[s:s + 6]) for s, _, _ in group):
            continue
        refs.extend(group)
    return refs


def _first_num(key):
    m = re.match(r"(\d+)", key or "")
    return int(m.group(1)) if m else None


def assign_segments(rows):
    """רצפי מספור. נספח מתחיל את המספור מחדש, ולכן "סעיף 3" בנספח ו"סעיף 3" בגוף
    ההסכם הם סעיפים שונים. רצף חדש נפתח כשסעיף ברמה העליונה אינו גדול מקודמו.
    המספר נשמר ב-row['segment'], וכל פסקה ללא מספר יורשת את הרצף שלפניה."""
    seg, prev = 0, None
    for r in rows:
        if r["label"] and r["level"] == 0:
            n = _first_num(r["key"])
            if n is not None:
                if prev is not None and n <= prev:
                    seg += 1
                prev = n
        r["segment"] = seg
    return seg + 1


def body_segment(rows):
    """איזה רצף מספור הוא גוף ההסכם. **לא** הרצף עם מרב הסעיפים העליונים: בהסכם
    פרילנס אמיתי הנספח (13 סעיפים) ארוך מגוף ההסכם (11), ובחירה לפי זה מחקה סעיף
    בנספח כשהתבקשה מחיקה בהסכם. גוף ההסכם נבדל בתתי-סעיפים; נספחים הם לרוב רשימה
    שטוחה. לכן: מרב הפסקאות הממוספרות בכל הרמות, ובשוויון, הרצף המוקדם."""
    counts = {}
    for r in rows:
        if r["label"]:
            counts[r["segment"]] = counts.get(r["segment"], 0) + 1
    return max(counts, key=lambda k: (counts[k], -k)) if counts else 0


def segment_summary(rows):
    """לכל רצף: כמה סעיפים עליונים, והכותרת של הראשון. לדיווח, לא להכרעה."""
    out = {}
    for r in rows:
        if r["label"] and r["level"] == 0:
            d = out.setdefault(r["segment"], {"segment": r["segment"], "top_clauses": 0,
                                              "first": r["text"].strip()[:40]})
            d["top_clauses"] += 1
    return [out[k] for k in sorted(out)]


# ---------- החלפה ברמת ה-run ----------
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"


def _deleted(node, p):
    anc = node.getparent()
    while anc is not None and anc is not p:
        if anc.tag in (qn("w:del"), qn("w:moveFrom")):
            return True
        anc = anc.getparent()
    return False


def text_nodes(p):
    """צומתי w:t של הפסקה בסדר, בלי טקסט מחוק. פסקה ממוצעת בהסכם אמיתי מפוצלת
    ל-6 עד 10 ריצות, ולכן ערך אחד (קו תחתון, תאריך, שם) נפרש לרוב על כמה מהן."""
    return [t for t in p.iter(qn("w:t")) if not _deleted(t, p)]


def replace_spans(p, spans):
    """spans: [(start, end, new_text)] במונחי para_text(p), כלומר **כולל טאבים**.
    הטקסט החדש נכנס לריצה שבה מתחיל הקטע ומקבל את העיצוב שלה; שאר הריצות
    שהקטע עבר בהן מקוצרות. העיצוב, הסגנון, המספור והכיווניות של הפסקה לא נוגעים.

    המיקומים נמדדים על אותו טקסט ש-para_text מחזיר, שבו כל w:tab הוא תו אחד.
    כשמדדו רק את w:t, כל טאב בתחילת פסקה הזיז את ההחלפה בתו: "בסעיף 2.4 לעיל"
    הפך ל-"בסעיף 22.3לעיל", ו"______בתוספת" איבד את האות ב'."""
    nodes, bounds, pos = [], [], 0
    for node in p.iter():
        if node.tag == qn("w:t"):
            ln = len(node.text or "")
            if not _deleted(node, p):
                nodes.append(node)
                bounds.append((pos, pos + ln))
            pos += ln
        elif node.tag == qn("w:tab"):
            pos += 1
    if not nodes or not spans:
        return 0

    def locate(off, is_end):
        for i, (a, b) in enumerate(bounds):
            if a <= off < b or (is_end and a < off <= b):
                return i, off - a
        if is_end:     # the end falls on a tab: close at the text node before it
            for i in range(len(bounds) - 1, -1, -1):
                if bounds[i][1] <= off:
                    return i, bounds[i][1] - bounds[i][0]
            return 0, 0
        for i, (a, b) in enumerate(bounds):   # the start falls on a tab: open at the next one
            if a >= off:
                return i, 0
        return len(nodes) - 1, bounds[-1][1] - bounds[-1][0]

    done = 0
    for start, end, new in sorted(spans, key=lambda x: -x[0]):
        si, so = locate(start, False)
        ei, eo = locate(end, True)
        if si == ei:
            t = nodes[si].text or ""
            nodes[si].text = t[:so] + new + t[eo:]
        else:
            nodes[si].text = (nodes[si].text or "")[:so] + new
            for k in range(si + 1, ei):
                nodes[k].text = ""
            nodes[ei].text = (nodes[ei].text or "")[eo:]
        for k in range(si, ei + 1):
            nodes[k].set(XML_SPACE, "preserve")
        done += 1
    return done
