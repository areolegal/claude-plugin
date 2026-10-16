# -*- coding: utf-8 -*-
"""תשובה בשרשור לבועה של הצד שכנגד (הערות הנושא ונותן, שינוי 10).

הבועות של הצד שכנגד נשארות בקובץ (המנוע של ענבל אינו מוחק אותן). כשהכרעה נושאת
`reply_to_comment` (מזהה הבועה שלהם), הבועה החיצונית שלנו נרשמת ב-Word כתשובה
בשרשור לבועה שלהם, ולא כבועה נפרדת לידה: `word/commentsExtended.xml`, ובו לכל
תשובה `w15:paraIdParent` של הבועה שהיא עונה לה. אם החלק חסר, הוא נוצר, עם היחס
וסוג התוכן שלו.
"""
import re
import secrets

from lxml import etree

import common.docx_tracked as dt

W = dt.W
W14 = "http://schemas.microsoft.com/office/word/2010/wordml"
W15 = "http://schemas.microsoft.com/office/word/2012/wordml"
MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"
EXT_PART = "word/commentsExtended.xml"
EXT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.commentsExtended+xml"
EXT_REL = "http://schemas.microsoft.com/office/2011/relationships/commentsExtended"


def _norm(s):
    return re.sub(r"\s+", " ", s or "").strip()


def _text(c):
    return _norm(" ".join("".join(t.text or "" for t in p.iter(W + "t")) for p in c.iter(W + "p")))


def _para_id(c):
    ps = list(c.iter(W + "p"))
    if not ps:
        return None
    p = ps[-1]
    pid = p.get("{%s}paraId" % W14)
    if not pid:
        pid = "%08X" % (secrets.randbits(31))
        p.set("{%s}paraId" % W14, pid)
    return pid


def apply_threads(path, replies, author):
    """replies: [(their_comment_id, our_external_comment)]. מחזיר רשימה של (id, מה קרה)."""
    if not replies:
        return []
    parts = dt.read_package(path)
    order = list(parts)
    if "word/comments.xml" not in parts:
        return [(cid, "אין בועות בקובץ") for cid, _ in replies]
    root = etree.fromstring(parts["word/comments.xml"])
    comments = list(root.iter(W + "comment"))
    by_id = {c.get(W + "id"): c for c in comments}
    if EXT_PART in parts:
        ext = etree.fromstring(parts[EXT_PART])
    else:
        ext = etree.Element("{%s}commentsEx" % W15, nsmap={"w15": W15, "mc": MC})
        ext.set("{%s}Ignorable" % MC, "w15")
    have = {e.get("{%s}paraId" % W15): e for e in ext.iter("{%s}commentEx" % W15)}
    done = []
    for cid, text in replies:
        theirs = by_id.get(str(cid))
        ours = next((c for c in comments if c.get(W + "author") == author and _text(c) == _norm(text)), None)
        if theirs is None or ours is None:
            done.append((cid, "לא נמצאה %s" % ("הבועה שלהם" if theirs is None else "התשובה שלנו")))
            continue
        tp, op = _para_id(theirs), _para_id(ours)
        if tp not in have:
            e = etree.SubElement(ext, "{%s}commentEx" % W15)
            e.set("{%s}paraId" % W15, tp)
            e.set("{%s}done" % W15, "0")
            have[tp] = e
        e = have.get(op) or etree.SubElement(ext, "{%s}commentEx" % W15)
        e.set("{%s}paraId" % W15, op)
        e.set("{%s}paraIdParent" % W15, tp)
        e.set("{%s}done" % W15, "0")
        have[op] = e
        done.append((cid, "נענתה בשרשור"))
    parts["word/comments.xml"] = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
    parts[EXT_PART] = etree.tostring(ext, xml_declaration=True, encoding="UTF-8", standalone=True)
    rels = parts["word/_rels/document.xml.rels"].decode("utf-8")
    if EXT_REL not in rels:
        ids = {int(x) for x in re.findall(r'Id="rId(\d+)"', rels)}
        rid = "rId%d" % (max(ids or {0}) + 1)
        rels = rels.replace("</Relationships>", '<Relationship Id="%s" Type="%s" Target="commentsExtended.xml"/>'
                            "</Relationships>" % (rid, EXT_REL))
        parts["word/_rels/document.xml.rels"] = rels.encode("utf-8")
    ct = parts["[Content_Types].xml"].decode("utf-8")
    if "/word/commentsExtended.xml" not in ct:
        ct = ct.replace("</Types>", '<Override PartName="/word/commentsExtended.xml" ContentType="%s"/></Types>'
                        % EXT_TYPE)
        parts["[Content_Types].xml"] = ct.encode("utf-8")
    with open(path, "wb") as fh:
        fh.write(dt.write_package(parts, order))
    return done
