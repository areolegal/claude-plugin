#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Builds the translated Word file from the source Word file, keeping its structure, in two steps.

  1. extract: every non-empty paragraph of the body, tables, headers and footers, with its place, into a JSON
     file of segments. The translator fills "target" for each segment.
         python build_translation_docx.py extract --source "<source>.docx" --out "<temp>/segments.json"
  2. build: the source file with each paragraph's text replaced by its translation, and the direction of the
     target language on every part (body, tables, headers, footers):
       he (or ar): w:bidi on every paragraph, w:rtl and David (cs) on every run, right alignment instead of left,
                   bidiVisual on tables, rtlGutter on sections; a run that is only Latin letters or digits stays LTR.
       en:         no w:bidi, no w:rtl, no bidiVisual, no rtlGutter; right alignment becomes left.
         python build_translation_docx.py build --source "<source>.docx" --segments "<temp>/segments.json" \\
             --lang en --out "<translation>.docx" [--stamp "Produced on 3 April 2027"] [--legend "..."] [--force]
     --stamp and --legend go into the header of every section, never into the body (the integrity check reads
     the body and the headers and footers, and skips only these two lines).

Numbering, styles, tables, sections, headers and footers stay as in the source. A segment without "target" is
refused (exit 1), so a paragraph is never left untranslated by accident. The output is never the source file.

A source without a header gets one: the stamp and the legend are never dropped (a translation that reads as binding
must not go out). A PDF source is accepted through the same text extraction as the rest of the system (pymupdf):
the translation keeps the text and the order of the paragraphs, and the script says what is not kept (layout,
tables, images, headers and footers, page numbers). A file is recognised by its content, not its name: a PDF named
.docx is read as a PDF, and an old .doc file or a damaged file gets a message that says so.
Exit codes: 0 success; 1 a segment is missing a translation; 2 bad input or refused output.
"""
import argparse, copy, hashlib, io, json, os, re, sys, zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python -I: sibling imports

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

from lxml import etree  # noqa: E402

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = "{%s}" % W_NS
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
FONT_HE = "David"
STAMP_STYLE = "AreoStamp"
PARTS = re.compile(r"^word/(document|header\d*|footer\d*|footnotes|endnotes|comments)\.xml$")
MANIFEST_SCHEMA = "areo-translation-manifest/1"
LATIN_ONLY = re.compile(r"^[\sA-Za-z0-9.,;:()\[\]/%&@'\"\-+*=#$€£₪]*$")
RTL_LANGS = ("he", "ar")


PDF_LOST = ("The source is a PDF. The translation keeps its text and the order of its paragraphs; the layout, tables, "
            "images, headers and footers and page numbers of the PDF are not kept.\n"
            "המקור הוא PDF. התרגום שומר את הטקסט ואת סדר הפסקאות; העימוד, הטבלאות, התמונות, הכותרות העליונות "
            "והתחתונות ומספרי העמודים של ה-PDF אינם נשמרים.")


def sniff(path):
    """The real kind of the file, by its first bytes: docx, pdf, doc (old Word or an encrypted file), zip, text."""
    try:
        with open(path, "rb") as fh:
            head = fh.read(8)
    except OSError:
        return "missing"
    if head.startswith(b"%PDF"):
        return "pdf"
    if head.startswith(b"\xd0\xcf\x11\xe0"):
        return "doc"
    if head.startswith(b"PK"):
        try:
            with zipfile.ZipFile(path) as z:
                return "docx" if "word/document.xml" in z.namelist() else "zip"
        except zipfile.BadZipFile:
            return "damaged"
    return "text"


KIND_MSG = {"doc": "%s is an old Word file (.doc) or an encrypted file. Save it as .docx and try again.\n"
                   "%s הוא קובץ Word ישן (.doc) או קובץ מוצפן. שמרו אותו כ-docx ונסו שוב.",
            "zip": "%s is a ZIP file, not a Word document.\n%s הוא קובץ ZIP ולא מסמך Word.",
            "damaged": "%s is damaged: it starts like a Word file but cannot be opened. Save it again from Word.\n"
                       "%s פגום: הוא נפתח כמו קובץ Word אבל אינו נקרא. שמרו אותו שוב מ-Word.",
            "missing": "%s was not found.\n%s לא נמצא."}


def pdf_paragraphs(path):
    """(paragraphs, reason): the PDF's text through pymupdf, the system's extractor. pypdf returns Hebrew in visual
    (reversed) order, so a Hebrew PDF without pymupdf is refused with the reason, never translated reversed."""
    text = ""
    try:
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz
        with fitz.open(path) as d:
            blocks = []
            for pg in d:
                blocks += [b[4] for b in pg.get_text("blocks") if str(b[4]).strip()]
        paras = [re.sub(r"\s+", " ", b).strip() for b in blocks]
        return [x for x in paras if x], None
    except ImportError:
        pass
    except Exception as e:  # noqa: BLE001
        return [], "the PDF could not be opened (%s)" % type(e).__name__
    try:
        from pypdf import PdfReader
        text = "\n".join((pg.extract_text() or "") for pg in PdfReader(path).pages)
    except Exception:  # noqa: BLE001
        return [], "no PDF reader is available (pymupdf)"
    if re.search(r"[\u0590-\u05FF]", text):
        return [], "a Hebrew PDF needs pymupdf; without it the text comes out reversed"
    paras = [re.sub(r"\s+", " ", x).strip() for x in re.split(r"\n\s*\n", text)]
    return [x for x in paras if x], None


def parts_of(path):
    with zipfile.ZipFile(path) as z:
        return {n: z.read(n) for n in z.namelist()}, [i.filename for i in z.infolist()]


def text_parts(parts):
    order = sorted((n for n in parts if PARTS.match(n)), key=lambda n: (0 if "document" in n else 1, n))
    return order


def para_text(p):
    out = []
    for el in p.iter(W + "t", W + "tab", W + "br"):
        if el.getparent() is not None and el.getparent().tag == W + "r":
            if el.tag == W + "t":
                out.append(el.text or "")
            elif el.tag == W + "tab":
                out.append("\t")
            else:
                out.append("\n")
    return "".join(out)


def paragraphs(root):
    # every paragraph, including table cells; text boxes are skipped (Fallback is a duplicate)
    return [p for p in root.iter(W + "p") if not any(a.tag.endswith("}Fallback") for a in p.iterancestors())]


def part_kind(name):
    base = name.rsplit("/", 1)[-1]
    for k in ("footnotes", "endnotes", "comments", "header", "footer"):
        if base.startswith(k):
            return {"footnotes": "footnote", "endnotes": "endnote", "comments": "comment"}.get(k, k)
    return "body"


ANNEX_HEAD = re.compile(r"^\s*(annex|annexure|schedule|appendix|exhibit|attachment|\u05e0\u05e1\u05e4\u05d7|\u05ea\u05d5\u05e1\u05e4\u05ea|\u05e0\u05e1\u05e4\u05d7\u05d9\u05dd)\b", re.I)


def seg_hash(text):
    return hashlib.sha256(re.sub(r"\s+", " ", text).strip().encode("utf-8")).hexdigest()[:16]


def para_features(p):
    """What a paragraph carries besides its words: fields, bookmarks, hyperlinks, footnote/comment references, drawings,
    emphasised runs. The integrity check compares them between the source and the built file."""
    def n(*tags):
        return sum(len(p.findall(".//" + W + t)) for t in tags)
    fld = len([e for e in p.iter(W + "fldChar") if e.get(W + "fldCharType") == "begin"]) + n("fldSimple")
    emph = 0
    runs = 0
    for r in p.iter(W + "r"):
        if r.find(W + "t") is None:
            continue
        runs += 1
        rpr = r.find(W + "rPr")
        if rpr is not None and any(rpr.find(W + t) is not None and rpr.find(W + t).get(W + "val") not in ("0", "false", "none")
                                   for t in ("b", "i", "u")):
            emph += 1
    return {"fields": fld, "bookmarks": n("bookmarkStart"), "hyperlinks": n("hyperlink"),
            "note_refs": n("footnoteReference", "endnoteReference"), "comment_refs": n("commentReference"),
            "drawings": n("drawing", "pict"), "emphasis_runs": emph, "text_runs": runs}


def collect(src):
    """(segments, info) of a Word or PDF source, without any target: the same units extract and the integrity check use."""
    if sniff(src) == "pdf":
        paras, why = pdf_paragraphs(src)
        if why:
            raise ValueError(why)
        segs = [{"id": "pdf:%d" % i, "part": "pdf", "index": i, "kind": "body", "source": t} for i, t in enumerate(paras)]
        return segs, {"parts": {"pdf": {"kind": "body", "segments": len(segs)}},
                      "tracked_changes": {"insertions": 0, "deletions": 0, "moves": 0, "layer": "not_applicable_pdf"}}
    parts, _ = parts_of(src)
    segs, info = [], {"parts": {}, "tracked_changes": {"insertions": 0, "deletions": 0, "moves": 0}}
    for name in text_parts(parts):
        root = etree.fromstring(parts[name])
        tc = info["tracked_changes"]
        tc["insertions"] += len(root.findall(".//" + W + "ins"))
        tc["deletions"] += len(root.findall(".//" + W + "del"))
        tc["moves"] += len(root.findall(".//" + W + "moveFrom")) + len(root.findall(".//" + W + "moveTo"))
        kind0, annex, n = part_kind(name), False, 0
        for i, p in enumerate(paragraphs(root)):
            t = para_text(p).strip()
            if not t:
                continue
            kind = kind0
            if kind0 == "body":
                st = p.find(W + "pPr/" + W + "pStyle")
                sv = (st.get(W + "val") if st is not None else "") or ""
                if ANNEX_HEAD.match(t) and len(t) < 90:
                    annex, kind = True, "annex"
                elif re.search(r"head|title|\u05db\u05d5\u05ea\u05e8\u05ea", sv, re.I):
                    kind = "heading"
                elif any(a.tag == W + "tc" for a in p.iterancestors()):
                    kind = "table"
                elif annex:
                    kind = "annex"
            seg = {"id": "%s:%d" % (re.sub(r"^word/|\.xml$", "", name), i), "part": name, "index": i, "kind": kind,
                   "source": t, "features": para_features(p)}
            if annex:
                seg["in_annex"] = True
            segs.append(seg)
            n += 1
        info["parts"][name] = {"kind": kind0, "segments": n}
    tc = info["tracked_changes"]
    tc["layer"] = ("insertions_shown_deletions_omitted" if tc["insertions"] or tc["deletions"] or tc["moves"]
                   else "none_in_source")
    return segs, info


def extract(src, out, glossary_version=None, allow_scanned=False):
    """segments.json = the translation manifest: source hash, parts, tracked-changes layer, glossary version and one
    entry per segment with its id, kind, source hash, target and (instead of a target) a visible reason."""
    sha = hashlib.sha256(open(src, "rb").read()).hexdigest()
    scanned = False
    segs, info = collect(src)
    if sniff(src) == "pdf" and not segs:
        if not allow_scanned:
            raise ValueError("the PDF has no text layer (a scanned PDF): it needs text recognition first")
        scanned = True
    for sg in segs:
        sg["source_hash"] = seg_hash(sg["source"])
        sg["target"] = ""
        sg["not_translated_reason"] = ""
    man = {"manifest_schema": MANIFEST_SCHEMA, "source_file": os.path.basename(src), "source_sha256": sha,
           "source_kind": sniff(src), "glossary_version": glossary_version or "",
           "parts": info["parts"], "tracked_changes": info["tracked_changes"], "scanned_text_unread": scanned,
           "segments": segs}
    io.open(out, "w", encoding="utf-8").write(json.dumps(man, ensure_ascii=False, indent=1))
    return segs


def _set(parent, tag, before=None, **attrs):
    el = parent.find(W + tag)
    if el is None:
        el = etree.SubElement(parent, W + tag)
    for k, v in attrs.items():
        el.set(W + k, v)
    return el


def _drop(parent, tag):
    for el in parent.findall(W + tag):
        parent.remove(el)


def replace_text(p, target):
    """The paragraph's text becomes target: the first text run keeps its formatting and takes the whole text;
    the other text nodes are emptied. Drawings, fields and bookmarks stay."""
    runs = [r for r in p.iter(W + "r") if r.find(W + "t") is not None]
    if not runs:
        r = etree.SubElement(p, W + "r")
        runs = [r]
        etree.SubElement(r, W + "t")
    first = True
    for r in runs:
        for t in r.findall(W + "t") + r.findall(W + "tab"):
            if first and t.tag == W + "t":
                t.text = target
                t.set(XML_SPACE, "preserve")
                first = False
            else:
                r.remove(t)


def direct_paragraph(p, rtl):
    ppr = p.find(W + "pPr")
    if ppr is None:
        ppr = etree.Element(W + "pPr")
        p.insert(0, ppr)
    if rtl:
        if ppr.find(W + "bidi") is None:
            b = etree.Element(W + "bidi")
            anchor = None
            for tag in ("pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr", "widowControl", "numPr",
                        "suppressLineNumbers", "pBdr", "shd", "tabs", "suppressAutoHyphens", "kinsoku", "wordWrap",
                        "overflowPunct", "topLinePunct", "autoSpaceDE", "autoSpaceDN"):
                if ppr.find(W + tag) is not None:
                    anchor = ppr.find(W + tag)
            (anchor.addnext(b) if anchor is not None else ppr.insert(0, b))
        jc = ppr.find(W + "jc")
        if jc is not None and jc.get(W + "val") in ("left", "start"):
            jc.set(W + "val", "right")
    else:
        _drop(ppr, "bidi")
        jc = ppr.find(W + "jc")
        if jc is not None and jc.get(W + "val") in ("right", "end"):
            jc.set(W + "val", "left")
    for r in p.iter(W + "r"):
        rpr = r.find(W + "rPr")
        if rpr is None:
            rpr = etree.Element(W + "rPr")
            r.insert(0, rpr)
        text = "".join(t.text or "" for t in r.findall(W + "t"))
        if rtl:
            rf = rpr.find(W + "rFonts")
            if rf is None:
                rf = etree.Element(W + "rFonts")
                st = rpr.find(W + "rStyle")
                (st.addnext(rf) if st is not None else rpr.insert(0, rf))
            rf.set(W + "cs", FONT_HE)
            if text and LATIN_ONLY.match(text) and re.search(r"[A-Za-z]", text):
                _drop(rpr, "rtl")          # embedded Latin stays LTR
            elif rpr.find(W + "rtl") is None:
                el = etree.Element(W + "rtl")
                anchor = None
                for ch in rpr:
                    if ch.tag.split("}")[-1] in ("rStyle", "rFonts", "b", "bCs", "i", "iCs", "caps", "smallCaps",
                                                  "strike", "dstrike", "outline", "shadow", "emboss", "imprint",
                                                  "noProof", "snapToGrid", "vanish", "webHidden", "color", "spacing",
                                                  "w", "kern", "position", "sz", "szCs", "highlight", "u", "effect",
                                                  "bdr", "shd", "fitText", "vertAlign"):
                        anchor = ch
                (anchor.addnext(el) if anchor is not None else rpr.insert(0, el))
        else:
            _drop(rpr, "rtl")


def direct_part(root, rtl):
    for p in paragraphs(root):
        direct_paragraph(p, rtl)
    for tbl in root.iter(W + "tblPr"):
        if rtl:
            if tbl.find(W + "bidiVisual") is None:
                tbl.insert(1 if tbl.find(W + "tblStyle") is not None else 0, etree.Element(W + "bidiVisual"))
        else:
            _drop(tbl, "bidiVisual")
    for sp in root.iter(W + "sectPr"):
        # the section's own direction (w:bidi in sectPr) follows the target too: an English file keeps none
        if rtl:
            for tag, after in (("bidi", ("rtlGutter", "docGrid", "printerSettings", "sectPrChange")),
                               ("rtlGutter", ("docGrid", "printerSettings", "sectPrChange"))):
                if sp.find(W + tag) is None:      # CT_SectPr order: ... bidi, rtlGutter, docGrid, printerSettings
                    nxt = next((sp.find(W + t) for t in after if sp.find(W + t) is not None), None)
                    (nxt.addprevious(etree.Element(W + tag)) if nxt is not None else sp.append(etree.Element(W + tag)))
        else:
            _drop(sp, "rtlGutter")
            _drop(sp, "bidi")


def add_header_lines(parts, lines, rtl):
    """The stamp and the legend at the top of every header part, in paragraphs styled AreoStamp."""
    heads = [n for n in parts if re.match(r"^word/header\d*\.xml$", n)]
    if not heads or not lines:
        return bool(heads)
    for n in heads:
        root = etree.fromstring(parts[n])
        for k, line in enumerate(lines):
            p = etree.Element(W + "p")
            ppr = etree.SubElement(p, W + "pPr")
            etree.SubElement(ppr, W + "pStyle").set(W + "val", STAMP_STYLE)
            r = etree.SubElement(p, W + "r")
            etree.SubElement(r, W + "rPr")
            t = etree.SubElement(r, W + "t")
            t.text = line
            t.set(XML_SPACE, "preserve")
            direct_paragraph(p, rtl)
            root.insert(k, p)
        parts[n] = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
    return True


def build_from_pdf(segs, lang, out, stamp, legend):
    """A new Word file from the translated paragraphs of a PDF source, with the stamp and legend in its header."""
    from docx import Document
    rtl = str(lang)[:2].lower() in RTL_LANGS
    d = Document()
    for sg in segs:
        d.add_paragraph(sg["target"])
    hdr = d.sections[0].header
    hdr.is_linked_to_previous = False
    first = True
    for line in [x for x in (stamp, legend) if x]:
        para = hdr.paragraphs[0] if first and hdr.paragraphs else hdr.add_paragraph()
        para.text = line
        first = False
    d.save(out)
    parts, order = parts_of(out)
    for name in text_parts(parts):
        root = etree.fromstring(parts[name])
        direct_part(root, rtl)
        parts[name] = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
    with zipfile.ZipFile(out + ".tmp", "w", zipfile.ZIP_DEFLATED) as z:
        for n in order:
            z.writestr(n, parts[n])
    os.replace(out + ".tmp", out)


def ensure_header(out, lines, rtl):
    """The source had no header: create one in every section, with the stamp and the legend (python-docx)."""
    from docx import Document
    d = Document(out)
    for sec in d.sections:
        hdr = sec.header
        hdr.is_linked_to_previous = False
        first = True
        for line in lines:
            para = hdr.paragraphs[0] if first and hdr.paragraphs and not hdr.paragraphs[0].text else hdr.add_paragraph()
            para.text = line
            first = False
    d.save(out)
    parts, order = parts_of(out)
    for name in [n for n in text_parts(parts) if "header" in n]:
        root = etree.fromstring(parts[name])
        direct_part(root, rtl)
        parts[name] = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
    with zipfile.ZipFile(out + ".tmp", "w", zipfile.ZIP_DEFLATED) as z:
        for n in order:
            z.writestr(n, parts[n])
    os.replace(out + ".tmp", out)


def build(src, segs_path, lang, out, stamp=None, legend=None):
    data = json.load(io.open(segs_path, encoding="utf-8"))
    segs = data.get("segments") if isinstance(data, dict) else data
    missing = [s for s in segs if not str(s.get("target") or "").strip() and not str(s.get("not_translated_reason") or "").strip()]
    both = [s for s in segs if str(s.get("target") or "").strip() and str(s.get("not_translated_reason") or "").strip()]
    if both:
        return 1, ["%s #%d: has both a target and a not_translated_reason" % (s["part"], s["index"]) for s in both[:10]]
    left = [s for s in segs if str(s.get("not_translated_reason") or "").strip()]
    if not missing:     # a segment left untranslated for a stated reason keeps its source text, visibly
        for s in left:
            s["target"] = s["source"]
    if missing:
        return 1, ["%s #%d: %s" % (s["part"], s["index"], s["source"][:60]) for s in missing[:10]]
    if sniff(src) == "pdf":
        build_from_pdf(segs, lang, out, stamp, legend)
        return 0, (["%d segments were left in the source language for a stated reason; the translation is NOT complete" %
                    len(left)] if left else [])
    parts, order = parts_of(src)
    by_part = {}
    for s in segs:
        by_part.setdefault(s["part"], {})[int(s["index"])] = s["target"]
    rtl = str(lang)[:2].lower() in RTL_LANGS
    for name in text_parts(parts):
        root = etree.fromstring(parts[name])
        ps = paragraphs(root)
        for i, target in by_part.get(name, {}).items():
            if i < len(ps):
                replace_text(ps[i], target)
        direct_part(root, rtl)
        parts[name] = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
    notes = []
    lines = [x for x in (stamp, legend) if x]
    has_header = add_header_lines(parts, lines, rtl) if lines else True
    tmp = out + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for n in order:
            z.writestr(n, parts[n])
    os.replace(tmp, out)
    if lines and not has_header:
        ensure_header(out, lines, rtl)       # the source had no header: one is created, never a silent drop
        notes.append("the source had no header: one was created for the stamp and the legend")
    if left:
        notes.append("%d segments were left in the source language for a stated reason; the translation is NOT complete "
                     "until they are translated (the integrity check lists them as gaps)" % len(left))
    return 0, notes


def main():
    ap = argparse.ArgumentParser(description="Builds the translated Word file from the source Word file, "
                                             "keeping its structure and applying the target language's direction")
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extract", help="segments to translate, from the body, tables, headers and footers")
    e.add_argument("--source", required=True)
    e.add_argument("--out", required=True)
    e.add_argument("--glossary-version", help="the glossary id/version used; recorded in the manifest")
    e.add_argument("--allow-scanned", action="store_true",
                   help="a PDF with no text layer: write a manifest that records the unread scanned text as a gap")
    b = sub.add_parser("build", help="the translated file from the source and the filled segments")
    b.add_argument("--source", required=True)
    b.add_argument("--segments", required=True)
    b.add_argument("--lang", required=True, help="target language: he, en, ar ...")
    b.add_argument("--out", required=True)
    b.add_argument("--stamp", help='the production stamp, e.g. "Produced on 3 April 2027" / "הופק בתאריך 3.4.2027"')
    b.add_argument("--legend", help="the status legend, e.g. the binding-version line")
    b.add_argument("--force", action="store_true", help="overwrite an existing output")
    a = ap.parse_args()
    kind = sniff(a.source)
    if kind not in ("docx", "pdf"):
        name = os.path.basename(a.source)
        print(KIND_MSG.get(kind, "%s is not a Word or PDF file.\n%s אינו קובץ Word או PDF.") % (name, name))
        sys.exit(2)
    if kind == "pdf" and not a.source.lower().endswith(".pdf"):
        print("note: %s is a PDF, though its name says otherwise; it is read as a PDF." % os.path.basename(a.source))
    out = a.out
    if os.path.normcase(os.path.realpath(out)) == os.path.normcase(os.path.realpath(a.source)):
        print("refused: --out is the source file")
        sys.exit(2)
    if a.cmd == "extract":
        try:
            segs = extract(a.source, out, a.glossary_version, a.allow_scanned)
        except ValueError as e:
            print("Not extracted: %s" % e)
            sys.exit(2)
        print("segments: %d (body, tables, headers and footers): %s" % (len(segs), out))
        return
    if os.path.exists(out) and not a.force:
        print("refused: %s exists; add --force to overwrite" % out)
        sys.exit(2)
    code, notes = build(a.source, a.segments, a.lang, out, a.stamp, a.legend)
    if code:
        print("Not built: %d segments have no translation:" % len(notes))
        for n in notes:
            print("  " + n)
        sys.exit(code)
    print("translated file: %s (%s)" % (out, "RTL" if str(a.lang)[:2].lower() in RTL_LANGS else "LTR"))
    if sniff(a.source) == "pdf":
        print(PDF_LOST)
    for n in notes:
        print("note: " + n)


if __name__ == "__main__":
    main()
