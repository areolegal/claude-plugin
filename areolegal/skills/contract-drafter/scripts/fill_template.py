#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ממלא תבנית אב ומפיק טיוטה ודף ליווי. הנוסח המאושר אינו משתנה אלא במה שנתבקש.

    python3 fill_template.py --template "Areo-נתונים/תבניות/<משפחה>/master.docx" \\
        --values "Areo-נתונים/draft-values-<slug>.json" \\
        --out "<שם המסמך>.docx" [--cover "<שם המסמך> - דף ליווי.docx"]

values.json:
  {
    "variables":       {"מספר_זיהוי_1": "514740433", ...},
    "remove_clauses":  ["9", "3.4"],
    "replace_clauses": {"7.2": "נוסח חדש לסעיף"},
    "add_clauses":     [{"after": "8.1", "text": "נוסח לסעיף חדש"}],
    "segment":         1,
    "author":          "שם עורך הדין",
    "company_role_code": "service_provider",   # מהפלייבוק; נקרא בבקרת השלמות (--draft-json)
    "counterparty_public_body": false,         # true כשהצד שכנגד גוף ציבורי; נקרא בבקרת השלמות
    "cover":          {"title": "...", "source": "תבנית", "key_dates": [{"what": "...", "when": "...", "clause": "..."}],
                        "decisions": ["..."], "notes": ["..."]}
  }

תווית סעיף היא המספר כפי ש-Word מציג אותו ("7.2" או "7.2."). כשבמסמך כמה רצפי
מספור (נספחים), "segment" קובע באיזה רצף מדובר, וברירת המחדל היא הרצף שבו נמצא
גוף ההסכם. אפשר גם לציין רצף לסעיף בודד: "3@2".

מה הסקריפט עושה:
  * מחליף תגיות {{...}} בערכים, ברמת ה-run, בלי לגעת בעיצוב.
  * סעיף שמשתנה לו נוסח, או סעיף חדש, מקבל בועת הערה "נוסח חדש, אינו מהתבנית".
  * מוחק סעיף עם כל תתי-הסעיפים שלו. אחרי מחיקה או הוספה, Word ממספר מחדש, והסקריפט
    מחשב את המספור החדש ומעדכן את ההפניות הפנימיות ("כאמור בסעיף 7"). הפניה לחוק אינה
    נוגעת. הפניה לסעיף שנמחק אינה משתנה ומדווחת.
  * תגית שנותרה בלי ערך נשארת גלויה ומדווחת כחוסמת.

שפה: `--lang he|en`, ובלעדיו "language" ב-values.json, ובלעדיו שפת התבנית עצמה (תבנית
בלי אותיות עבריות היא אנגלית). בועת "נוסח חדש" ודף הליווי בשפה הזו; דף ליווי באנגלית הוא LTR מלא.
"""
import argparse
import copy
import datetime
import io
import json
import os
import re
import sys

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# para_text must be the library's: replace_spans measures offsets on exactly that text,
# tabs included. A local copy without tabs shifted every replacement in a tabbed paragraph.
from docx_numbering import (LITERAL_RX, assign_segments, body_segment, find_refs,  # noqa: E402
                            labelled_paragraphs, norm_label, para_text, replace_spans)
from build_template_registry import guard_out  # noqa: E402

try:                                   # פלט עברי במסוף של Windows
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):   # pragma: no cover
    pass

TAG_RX = re.compile(r"\{\{\s*([^{}]{1,60}?)\s*\}\}")
NEW_WORDING = "נוסח חדש, אינו מהתבנית"
NEW_WORDING_EN = "New wording, not from the template"
HEB_RX = re.compile("[\u0590-\u05FF]")
COVER = {
    "he": {"cover": "דף ליווי: ", "stamp": "טיוטה · הופק בתאריך %s", "template": "תבנית",
           "filled": "משתנים שמולאו", "defaulted": "נשארו כפי שהיו בהסכם המקורי", "unfilled": "טעון השלמה",
           "fill": "[להשלים] %s", "removed": "סעיפים שהוסרו", "clause": "סעיף %s", "new": NEW_WORDING,
           "added": "סעיף חדש %s, אחרי סעיף %s", "refs": "הפניות פנימיות שעודכנו", "ref_line": "%s עודכן ל-%s",
           "dangling": "הפניות לסעיף שהוסר, לבדיקה", "dangling_line": "סעיף %s: %s", "decisions": "הכרעות",
           "notes": "הערות", "run_risk": "להריץ על הטיוטה הערכת סיכונים לפני שהיא יוצאת?",
           "gaps": "מצייני חוסר בטיוטה: %d", "concern": "החשש העיקרי שלכם בעסקה", "concern_answer": "כלשונכם: %s",
           "concern_clauses": "המענה בטיוטה: סעיפים %s", "options": "מוצע כאפשרות, לא נכלל"},
    "en": {"cover": "Cover note: ", "stamp": "Draft · Produced on %s", "template": "template",
           "filled": "Variables filled", "defaulted": "Left as in the original agreement", "unfilled": "To complete",
           "fill": "[to complete] %s", "removed": "Clauses removed", "clause": "Clause %s", "new": NEW_WORDING_EN,
           "added": "New clause %s, after clause %s", "refs": "Internal references updated", "ref_line": "%s updated to %s",
           "dangling": "References to a removed clause, to check", "dangling_line": "Clause %s: %s",
           "decisions": "Decisions", "notes": "Notes", "run_risk": "Run a risk assessment on the draft before it goes out?",
           "gaps": "Placeholders in the draft: %d", "concern": "Your main concern in this deal",
           "concern_answer": "In your words: %s", "concern_clauses": "Where the draft answers it: clauses %s",
           "options": "Offered as an option, not included"},
}


def template_lang(doc):
    """שפת התבנית: אותיות עבריות בגוף ההסכם הן עברית; אחרת אנגלית."""
    return "he" if any(HEB_RX.search(t.text or "") for t in doc.element.body.iter(qn("w:t"))) else "en"
STOP_SUBTREE = re.compile(r"^\s*(?:ולראיה|IN\s+WITNESS|נספח\s|Annex\s|Schedule\s|Exhibit\s)", re.I)


def all_paragraphs(doc):
    for p in doc.element.body.iter(qn("w:p")):
        yield p
    for sec in doc.sections:
        for part in (sec.header, sec.footer, sec.first_page_header, sec.first_page_footer):
            try:
                for p in part._element.iter(qn("w:p")):
                    yield p
            except Exception:
                continue


def in_table(p):
    anc = p.getparent()
    while anc is not None:
        if anc.tag == qn("w:tbl"):
            return anc
        anc = anc.getparent()
    return None


def fill_variables(doc, values, skeleton):
    filled, defaulted = {}, {}
    defaults = {v["id"]: v.get("found_value") for v in (skeleton or {}).get("variables", [])
                if v.get("found_value")}
    for p in all_paragraphs(doc):
        text = para_text(p)
        spans = []
        for m in TAG_RX.finditer(text):
            vid = m.group(1)
            if vid in values:
                spans.append((m.start(), m.end(), str(values[vid])))
                filled[vid] = filled.get(vid, 0) + 1
            elif vid in defaults:
                spans.append((m.start(), m.end(), defaults[vid]))
                defaulted[vid] = defaults[vid]
        if spans:
            replace_spans(p, spans)
    left = sorted({m.group(1) for p in all_paragraphs(doc) for m in TAG_RX.finditer(para_text(p))})
    unknown = sorted(k for k in values if k not in filled)
    return filled, defaulted, left, unknown


def parse_target(label, default_seg):
    if "@" in str(label):
        lab, seg = str(label).split("@", 1)
        return norm_label(lab), int(seg)
    return norm_label(str(label)), default_seg


def subtree(rows, i):
    """הסעיף ששורתו i וכל מה ששייך לו: תתי-סעיפים ופסקאות המשך, עד הסעיף הבא
    באותה רמה או גבוהה ממנה, סוף הרצף, בלוק חתימה או כותרת נספח."""
    head = rows[i]
    tbl = in_table(head["p"])
    out = [head["p"]]
    for r in rows[i + 1:]:
        if r["segment"] != head["segment"]:
            break
        if r["label"] and r["level"] is not None and r["level"] <= head["level"]:
            break
        if not r["label"] and STOP_SUBTREE.match(r["text"]):
            break
        if in_table(r["p"]) is not tbl:
            break
        out.append(r["p"])
    return out


def renumber_literal(rows, before, segments):
    """מספור שכתוב בטקסט אינו מתעדכן לבד כמו מספור של Word. אחרי מחיקה או הוספה,
    רק ברצפים שבהם היה שינוי, כל מספר נכתב מחדש ברצף: 1., 1.1, 1.2, 2. וכו',
    בשמירה על הפיסוק שהיה (נקודה בסוף או בלעדיה). כך טיוטה שנבנתה מאפס (מצב 4)
    ונשמרה כתבנית אב מתנהגת כמו תבנית עם מספור אוטומטי."""
    seg_of = {}
    for r in rows:
        seg_of[id(r["p"])] = before.get(id(r["p"]), (None, r["segment"]))[1]
    counters = {}
    for r in rows:
        if r["kind"] != "literal":
            continue
        seg = seg_of[id(r["p"])]
        if seg not in segments:
            continue
        m = LITERAL_RX.match(r["text"])
        if not m:
            continue
        lvl = r["level"]
        c = counters.setdefault(seg, [])
        while len(c) < lvl + 1:
            c.append(0 if len(c) == lvl else 1)
        del c[lvl + 1:]
        c[lvl] += 1
        new = ".".join(str(x) for x in c)
        old = m.group(1)
        if old.endswith("."):
            new += "."
        if new != old:
            replace_spans(r["p"], [(m.start(1), m.end(1), new)])


def set_text_keep_format(p, text):
    runs = p.findall(qn("w:r"))
    rpr = None
    for r in runs:
        if r.find(qn("w:t")) is not None:
            rpr = r.find(qn("w:rPr"))
            break
    for child in list(p):
        if child.tag in (qn("w:r"), qn("w:hyperlink"), qn("w:ins"), qn("w:del"), qn("w:fldSimple")):
            p.remove(child)
    r = OxmlElement("w:r")
    if rpr is not None:
        r.append(copy.deepcopy(rpr))
    t = OxmlElement("w:t")
    t.text = text
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    r.append(t)
    p.append(r)


def comment(doc, p, author, lang="he"):
    para = Paragraph(p, doc._body)
    runs = [r for r in para.runs if r.text]
    if not runs:
        return False
    try:
        initials = "".join(w[0] for w in (author or "Areo").split()[:2])
        doc.add_comment(runs, text=NEW_WORDING_EN if lang == "en" else NEW_WORDING, author=author or "Areo",
                        initials=initials)
        return True
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True)
    ap.add_argument("--values", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cover")
    ap.add_argument("--skeleton", help="ברירת מחדל: skeleton.json שליד התבנית")
    ap.add_argument("--lang", choices=("he", "en"), help="שפת הבועות ודף הליווי; בלעדיו: language ב-values.json, "
                                                         "ואחריו שפת התבנית")
    ap.add_argument("--force", action="store_true", help="לדרוס טיוטה או דף ליווי קיימים (הרצה חוזרת אחרי תיקון)")
    a = ap.parse_args()

    sk_path = a.skeleton or os.path.join(os.path.dirname(os.path.abspath(a.template)), "skeleton.json")
    # הפלט לעולם אינו תבנית האב, קובץ הערכים או השלד, ומסמך קיים נדרס רק עם --force
    inputs = [a.template, a.values, sk_path]
    guard_out(a.out, inputs, a.force)
    guard_out(os.path.splitext(a.out)[0] + ".report.json", inputs)
    if a.cover:
        guard_out(a.cover, inputs + [a.out], a.force)
    vals = json.load(io.open(a.values, encoding="utf-8"))
    skeleton = json.load(io.open(sk_path, encoding="utf-8")) if os.path.isfile(sk_path) else None

    doc = Document(a.template)
    v = str(a.lang or vals.get("language") or template_lang(doc)).strip().lower()
    lang = "en" if v[:2] == "en" or v in ("english", "אנגלית") else "he"
    author = vals.get("author") or "Areo"
    report = {"template": os.path.basename(a.template), "built_at": datetime.date.today().isoformat(),
              "warnings": []}

    filled, defaulted, left, unknown = fill_variables(doc, vals.get("variables") or {}, skeleton)
    report.update(filled=sorted(filled), defaulted=defaulted, unfilled=left, unknown_variables=unknown)

    rows = labelled_paragraphs(doc)
    assign_segments(rows)
    base_seg = vals.get("segment", (skeleton or {}).get("body_segment", body_segment(rows)))
    multi = {}
    for r in rows:
        if r["label"]:
            multi.setdefault(r["key"], set()).add(r["segment"])
    before = {id(r["p"]): (r["key"], r["segment"]) for r in rows if r["label"]}
    literal = not any(r["kind"] == "auto" for r in rows) and any(r["kind"] == "literal" for r in rows)
    index = {}
    for i, r in enumerate(rows):
        if r["label"]:
            index.setdefault((r["key"], r["segment"]), i)

    def find(label):
        key, seg = parse_target(label, base_seg)
        i = index.get((key, seg))
        if i is not None and "@" not in str(label) and len(multi.get(key, ())) > 1:
            report["warnings"].append(
                ("Clause %s exists in more than one numbering sequence; the agreement body was chosen (sequence %d). "
                 "For an annex: \"%s@<sequence>\"." if lang == "en" else
                 "סעיף %s קיים ביותר מרצף מספור אחד; נבחר גוף ההסכם (רצף %d). לנספח: \"%s@<רצף>\".")
                % (key, seg, key))
        if i is None:
            report["warnings"].append(("Clause %s was not found in sequence %d." if lang == "en" else
                                       "לא נמצא סעיף %s ברצף %d.") % (key, seg))
        return i

    removals, removals_meta = [], []
    for lab in vals.get("remove_clauses") or []:
        i = find(lab)
        if i is not None:
            removals.append((lab, subtree(rows, i)))
            removals_meta.append({"segment": rows[i]["segment"]})
    replaced, added = [], []
    for lab, text in (vals.get("replace_clauses") or {}).items():
        i = find(lab)
        if i is None:
            continue
        set_text_keep_format(rows[i]["p"], text)
        comment(doc, rows[i]["p"], author, lang)
        replaced.append(norm_label(lab))
    for item in vals.get("add_clauses") or []:
        i = find(item.get("after"))
        if i is None:
            continue
        anchor = subtree(rows, i)[-1]
        new_p = copy.deepcopy(rows[i]["p"])
        text = item.get("text", "")
        if literal:
            m = re.match(r"^\s*\S+\s*", rows[i]["text"])
            text = (m.group(0) if m else "") + text
        set_text_keep_format(new_p, text)
        anchor.addnext(new_p)
        comment(doc, new_p, author, lang)
        added.append({"after": norm_label(item.get("after")), "p": new_p,
                      "segment": rows[i]["segment"]})
    removed = []
    for lab, ps in removals:
        for p in ps:
            if p.getparent() is not None:
                p.getparent().remove(p)
        removed.append({"label": norm_label(lab), "paragraphs": len(ps)})
    report.update(replaced=replaced, removed=removed)

    changes, dangling = [], []
    if removed or added:
        rows2 = labelled_paragraphs(doc)
        assign_segments(rows2)
        if literal:
            renumber_literal(rows2, before, {x["segment"] for x in removals_meta} |
                             {x["segment"] for x in added})
            rows2 = labelled_paragraphs(doc)
            assign_segments(rows2)
        mapping, gone = {}, {}
        alive = {id(r["p"]): r["key"] for r in rows2 if r["label"]}
        for pid, (key, seg) in before.items():
            if pid in alive:
                if alive[pid] != key:
                    mapping.setdefault(seg, {})[key] = alive[pid]
            else:
                gone.setdefault(seg, set()).add(key)
        seg_of = {id(r["p"]): before.get(id(r["p"]), (None, r["segment"]))[1] for r in rows2}
        for r in rows2:
            text = r["text"]
            seg = seg_of.get(id(r["p"]), r["segment"])
            spans = []
            for s, e, tok in find_refs(text):
                m = re.match(r"(\d+(?:\.\d+)*)", tok)
                key = m.group(1)
                own = mapping.get(seg, {})
                if key in own:
                    spans.append((s, s + len(key), own[key]))
                    changes.append({"from": key, "to": own[key], "context": text[max(0, s - 25):e + 15].strip()})
                elif key in gone.get(seg, set()):
                    dangling.append({"ref": key, "context": text[max(0, s - 25):e + 15].strip()})
            if spans:
                replace_spans(r["p"], spans)
        for item in added:
            lab = next((rr["label"] for rr in rows2 if rr["p"] is item["p"]), None)
            item["label"] = lab
    report.update(added=[{"after": x["after"], "label": x.get("label")} for x in added],
                  reference_changes=changes, dangling_references=dangling)

    # a replaced or removed clause may have carried a tag: recount what is really left
    left = sorted({m.group(1) for p in all_paragraphs(doc) for m in TAG_RX.finditer(para_text(p))})
    report["unfilled"] = left

    doc.save(a.out)
    # מצייני החוסר נספרים בכלי אחד, בבקרת השלמות, על הקובץ שנשמר: אותו מספר בדוח, בדף הליווי ובבקרה
    from build_template_registry import docx_text
    from check_draft_integrity import count_placeholders
    report["placeholders"] = count_placeholders(docx_text(a.out, limit=400000)[0])
    rep_path = os.path.splitext(a.out)[0] + ".report.json"
    io.open(rep_path, "w", encoding="utf-8").write(json.dumps(report, ensure_ascii=False, indent=2))

    if a.cover:
        write_cover(a.cover, report, vals, skeleton, lang)

    print("הטיוטה: %s" % a.out)
    print("משתנים שמולאו: %d · נשארו מההסכם המקורי: %d · ללא ערך: %d · מצייני חוסר: %d"
          % (len(filled), len(defaulted), len(left), report["placeholders"]))
    print("סעיפים: הוחלפו %d · נוספו %d · נמחקו %d · הפניות שעודכנו %d"
          % (len(replaced), len(added), len(removed), len(changes)))
    for x in added:
        print("  סעיף חדש אחרי %s קיבל את המספר %s" % (x["after"], x.get("label") or "?"))
    for c in changes:
        print("  הפניה: %s -> %s  ·  %s" % (c["from"], c["to"], c["context"]))
    for d in dangling:
        print("  חוסם: הפניה לסעיף %s שנמחק  ·  %s" % (d["ref"], d["context"]))
    if left:
        print("  חוסם: תגיות ללא ערך: %s" % ", ".join(left))
    if unknown:
        print("  שים לב: ערכים לתגיות שאינן בתבנית: %s" % ", ".join(unknown))
    for w in report["warnings"]:
        print("  שים לב: " + w)
    # החשש העיקרי שהלקוח מסר מתורגם לפחות לסעיף אחד (derived-intake.md, רובד 3)
    mc = (vals.get("cover") or {}).get("main_concern") or {}
    concern_open = isinstance(mc, dict) and bool(mc.get("answer")) and not mc.get("clauses")
    if concern_open:
        print("  חוסם: החשש העיקרי שמסר הלקוח (cover.main_concern) לא תורגם לאף סעיף")
    sys.exit(1 if (left or dangling or concern_open) else 0)


def write_cover(path, report, vals, skeleton, lang="he"):
    """דף ליווי של עמוד אחד, באותו עיצוב של בונה הטיוטה, בשפת התוצר."""
    import build_draft_docx as B
    from docx import Document as D

    B.RTL = lang != "en"
    C = COVER["en" if lang == "en" else "he"]
    doc = D()
    B.base(doc)
    cover = vals.get("cover") or {}
    labels = {v["id"]: v.get("label") or v["id"] for v in (skeleton or {}).get("variables", [])}
    B.run(B.para(doc, after=2), C["cover"] + B.s(cover.get("title") or report["template"]), 16, True, B.NAVY)
    B.run(B.para(doc, after=6), C["stamp"] % B.produced_on({"generated_at": report["built_at"]}), 9.5, False,
          B.INK_SOFT)
    # התוצאה קודם, ואחריה פעולה אחת (areo-voice.md); הכול נספר בקוד
    todo = (report.get("placeholders") or 0) + len(report.get("unfilled") or [])
    lead = B.tr("lead")
    if todo:
        lead += " " + B.tr("lead_open") % (todo, 5 * max(1, -(-todo // 5)))
    else:
        lead += " " + B.tr("lead_clear")
    B.run(B.para(doc, after=2), lead, 12, True, B.INK)
    B.run(B.para(doc, after=10), B.tr("next_fill") if todo else B.tr("next_send"), 11, False, B.NAVY)

    def section(title, lines):
        if not lines:
            return
        B.h1(doc, title)
        for ln in lines:
            B.rich(B.para(doc, after=2, indent=0.5), ln, 10.5)

    mc = cover.get("main_concern") or {}
    if isinstance(mc, dict) and mc.get("answer"):
        refs = mc.get("clauses") or []
        section(C["concern"], [C["concern_answer"] % B.s(mc.get("answer")),
                               C["concern_clauses"] % ", ".join(B.s(x) for x in (refs if isinstance(refs, list)
                                                                                  else [refs]))])
    section(B.TXT["en" if lang == "en" else "he"]["choices"], B.choice_lines(cover, lang))
    section(B.TXT["en" if lang == "en" else "he"]["key_dates"], B.key_date_lines(cover, lang))
    section(C["filled"], ["%s: %s" % (labels.get(k, k), (vals.get("variables") or {}).get(k, ""))
                          for k in report["filled"]])
    if report.get("placeholders") is not None:
        B.para(doc, C["gaps"] % report["placeholders"], 10.5, True, B.INK, before=6)
    section(C["defaulted"], ["%s: %s" % (labels.get(k, k), v) for k, v in report["defaulted"].items()])
    section(C["unfilled"], [C["fill"] % labels.get(k, k) for k in report["unfilled"]])
    section(C["removed"], [C["clause"] % x["label"] for x in report["removed"]])
    section(C["new"], [C["clause"] % x for x in report["replaced"]] +
            [C["added"] % (x.get("label") or "", x["after"]) for x in report["added"]])
    section(C["refs"], [C["ref_line"] % (c["from"], c["to"]) for c in report["reference_changes"]])
    section(C["dangling"], [C["dangling_line"] % (d["ref"], d["context"]) for d in report["dangling_references"]])
    section(C["options"], ["%s: %s" % (B.s(o.get("title")), B.s(o.get("reason"))) if isinstance(o, dict) else B.s(o)
                           for o in (cover.get("options") or [])])
    section(C["decisions"], cover.get("decisions") or [])
    section(C["notes"], (cover.get("notes") or []) + report["warnings"])
    B.para(doc, C["run_risk"], 10.5, True, B.INK, before=14)
    doc.save(path)
    from build_template_registry import docx_text
    problems = B.client_text_problems((None, path), B.RTL, docx_text, B._voice_check)
    if problems:
        os.remove(path)
        print("דף הליווי לא נבנה:")
        for p in problems:
            print("  חוסם: " + p)
        sys.exit(1)


if __name__ == "__main__":
    main()
