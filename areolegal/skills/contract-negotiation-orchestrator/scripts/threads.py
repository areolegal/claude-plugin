# -*- coding: utf-8 -*-
"""תשובה בשרשור לבועה של הצד שכנגד (הערות הנושא ונותן, שינוי 10), קריאת השרשורים, וסימון "בוצע".

הבועות של הצד שכנגד נשארות בקובץ (המנוע המשותף אינו מוחק אותן). כשהכרעה נושאת
`reply_to_comment` (מזהה הבועה שלהם), הבועה החיצונית שלנו נרשמת ב-Word כתשובה
בשרשור לבועה שלהם, ולא כבועה נפרדת לידה: `word/commentsExtended.xml`, ובו לכל
תשובה `w15:paraIdParent` של **בועת השורש** של השרשור, כמו ש-Word כותב: גם כשהבועה
שלהם היא עצמה תשובה בשרשור, התשובה שלנו מצביעה על השורש ולא עליה (בדיקה עצמאית
S1c, פער 10, 28.10.2026). אם החלק חסר, הוא נוצר, עם היחס וסוג התוכן שלו.

`read_threads` קורא את הבועות עם השרשור שלהן (paraIdParent, done) ועם הפסקה שהן
מעוגנות בה. `mark_done` מסמן שרשור כ"בוצע" (w15:done="1"), כמו "Resolve" ב-Word:
בסבב סגירה, הבועות שלנו בנושאים שנסגרו אינן נשארות פתוחות (פער 3).
"""
import os
import re
import secrets
import sys

from lxml import etree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # גם ב-python -I, שאינו מוסיף את תיקיית הסקריפט
import areo_lib  # noqa: F401,E402  מוסיף את areolegal/lib לנתיב הייבוא

import common.docx_tracked as dt  # noqa: E402

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


def _para_id(c, create=True):
    ps = list(c.iter(W + "p"))
    if not ps:
        return None
    p = ps[-1]
    pid = p.get("{%s}paraId" % W14)
    if not pid and create:
        pid = "%08X" % (secrets.randbits(31))
        p.set("{%s}paraId" % W14, pid)
    return pid


def _root_para(pid, have):
    """בועת השורש של השרשור: עולים לפי paraIdParent עד בועה בלי הורה (Word מצביע תמיד על השורש)."""
    seen = set()
    while pid in have and have[pid].get("{%s}paraIdParent" % W15) and pid not in seen:
        seen.add(pid)
        pid = have[pid].get("{%s}paraIdParent" % W15)
    return pid


def _ext_root(parts):
    if EXT_PART in parts:
        return etree.fromstring(parts[EXT_PART])
    ext = etree.Element("{%s}commentsEx" % W15, nsmap={"w15": W15, "mc": MC})
    ext.set("{%s}Ignorable" % MC, "w15")
    return ext


def _write_ext(parts, root, ext):
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
    ext = _ext_root(parts)
    have = {e.get("{%s}paraId" % W15): e for e in ext.iter("{%s}commentEx" % W15)}
    done = []
    for cid, text in replies:
        theirs = by_id.get(str(cid))
        ours = next((c for c in comments if c.get(W + "author") == author and _text(c) == _norm(text)), None)
        if theirs is None or ours is None:
            done.append((cid, "לא נמצאה %s" % ("הבועה שלהם" if theirs is None else "התשובה שלנו")))
            continue
        tp, op = _root_para(_para_id(theirs), have), _para_id(ours)
        if tp not in have:
            e = etree.SubElement(ext, "{%s}commentEx" % W15)
            e.set("{%s}paraId" % W15, tp)
            e.set("{%s}done" % W15, "0")
            have[tp] = e
        e = have.get(op)
        if e is None:
            e = etree.SubElement(ext, "{%s}commentEx" % W15)
        e.set("{%s}paraId" % W15, op)
        e.set("{%s}paraIdParent" % W15, tp)
        e.set("{%s}done" % W15, "0")
        have[op] = e
        done.append((cid, "נענתה בשרשור"))
    _write_ext(parts, root, ext)
    with open(path, "wb") as fh:
        fh.write(dt.write_package(parts, order))
    return done


def read_threads(path_or_parts):
    """כל הבועות של הקובץ, לפי הסדר: id, author, initials, date, text, para_id, parent_id (מזהה הבועה שהיא
    עונה לה, לפי paraIdParent), root_id (בועת השורש), done (w15:done) ו-para (הפסקה ב-body_paragraphs שבה היא
    מעוגנת, או None). קובץ בלי commentsExtended: כל בועה היא שורש."""
    parts = path_or_parts if isinstance(path_or_parts, dict) else dt.read_package(path_or_parts)
    if "word/comments.xml" not in parts:
        return []
    root = etree.fromstring(parts["word/comments.xml"])
    ext = etree.fromstring(parts[EXT_PART]) if EXT_PART in parts else None
    info = {}
    if ext is not None:
        for e in ext.iter("{%s}commentEx" % W15):
            info[e.get("{%s}paraId" % W15)] = (e.get("{%s}paraIdParent" % W15), e.get("{%s}done" % W15) == "1")
    where = dt.comment_paragraphs(etree.fromstring(parts["word/document.xml"])) if "word/document.xml" in parts else {}
    out, by_pid = [], {}
    for c in root.findall(W + "comment"):
        pid = _para_id(c, create=False)
        rec = {"id": c.get(W + "id"), "author": c.get(W + "author"), "initials": c.get(W + "initials"),
               "date": c.get(W + "date"), "text": _text(c), "para_id": pid,
               "done": bool(info.get(pid, (None, False))[1]), "para": where.get(c.get(W + "id"))}
        out.append(rec)
        if pid:
            by_pid[pid] = rec
    for rec in out:
        parent_pid = info.get(rec["para_id"], (None, False))[0]
        rec["parent_id"] = by_pid[parent_pid]["id"] if parent_pid in by_pid else None
    by_id = {r["id"]: r for r in out}
    for rec in out:
        cur, seen = rec, set()
        while cur.get("parent_id") in by_id and cur["id"] not in seen:
            seen.add(cur["id"])
            cur = by_id[cur["parent_id"]]
        rec["root_id"] = cur["id"]
    for rec in out:   # תשובה בלי עוגן משלה יושבת בפסקה של השורש
        if rec["para"] is None:
            rec["para"] = next((r["para"] for r in out if r["id"] == rec["root_id"]), None)
    return out


def mark_done(path, root_ids, out_path=None):
    """מסמן כ"בוצע" (w15:done="1") את השרשורים ששורשם ב-root_ids: השורש וכל התשובות, כמו "Resolve" ב-Word.
    הבועות עצמן אינן נמחקות. מחזיר את מזהי הבועות שסומנו."""
    want = {str(x) for x in root_ids or ()}
    if not want:
        return []
    parts = dt.read_package(path)
    order = list(parts)
    if "word/comments.xml" not in parts:
        return []
    root = etree.fromstring(parts["word/comments.xml"])
    ext = _ext_root(parts)
    have = {e.get("{%s}paraId" % W15): e for e in ext.iter("{%s}commentEx" % W15)}
    marked = []
    for rec in read_threads(parts):
        if rec["root_id"] not in want:
            continue
        c = next((x for x in root.findall(W + "comment") if x.get(W + "id") == rec["id"]), None)
        pid = _para_id(c) if c is not None else None
        if not pid:
            continue
        e = have.get(pid)
        if e is None:
            e = etree.SubElement(ext, "{%s}commentEx" % W15)
            e.set("{%s}paraId" % W15, pid)
            have[pid] = e
        e.set("{%s}done" % W15, "1")
        marked.append(rec["id"])
    if marked:
        _write_ext(parts, root, ext)
        with open(out_path or path, "wb") as fh:
            fh.write(dt.write_package(parts, order))
    return marked
