"""טביעות אצבע לקבצים בתיקיות המחוברות.

כל קובץ מזוהה לפי SHA-256. קובץ שלא השתנה אינו נקרא שוב, קובץ זהה בשם אחר
מסומן כפול, וקובץ שהוסר מסומן כך ואינו נמחק מהמאגר. קובץ נעול או לא זמין
מסומן unreadable, שומר את טביעת האצבע הקודמת, ואינו עוצר את הסריקה.

החרגה (--exclude): נתיב יחסי לתיקייה המחוברת, נתיב שמתחיל בשם התיקייה המחוברת, או נתיב מוחלט.
לוכסנים ואותיות גדולות מנורמלים, וההתאמה היא לגבול תיקייה או קובץ שלם בלבד.

אף קובץ אינו נעלם בשקט. קובץ מסוג שאינו נקרא נרשם במצב unsupported (ופותח פריט באימות הנתונים); קובצי מערכת,
קובצי נעילה (~$), נתיב שלא נמצא ותיקיית Areo-נתונים נרשמים בדוח הסריקה. מייל (.eml) נסרק, וכל קובץ מצורף בו נכנס
כרשומה משלו (container). PDF בלי שכבת טקסט מסומן scanned, ועובר זיהוי טקסט כשיש במחשב tesseract ו-PyMuPDF.
"""
import email
import email.policy
import hashlib
import os
import re
import shutil
import subprocess
import tempfile

EXTS = (".docx", ".pdf", ".doc", ".txt", ".md", ".eml")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _norm(p):
    return p.replace("\\", "/").lower()


def _prepare(excluded):
    rel, absolute = [], []
    for e in excluded or ():
        if not e or not e.strip():
            continue
        if os.path.isabs(e):
            absolute.append(_norm(os.path.normcase(os.path.abspath(e))).rstrip("/"))
        else:
            n = _norm(e).strip()
            while n.startswith("./"):
                n = n[2:]
            n = n.strip("/")
            if n:
                rel.append(n)
    return rel, absolute


def _under(path, prefix):
    return path == prefix or path.startswith(prefix + "/")


def _is_excluded(full, rel, key, rules):
    rel_rules, abs_rules = rules
    r, k = _norm(rel), _norm(key)
    if any(_under(r, e) or _under(k, e) for e in rel_rules):
        return True
    f = _norm(os.path.normcase(os.path.abspath(full)))
    return any(_under(f, e) for e in abs_rules)


SYSTEM_FILES = {"desktop.ini", "thumbs.db", ".ds_store"}
# תיקיית הנתונים של Areo (אם היא בתוך התיקייה המחוברת) אינה הסכמים, ואינה נסרקת. הדילוג מדווח
DATA_DIRS = {"areo-נתונים"}
PAGE_TEXT_MIN = 30  # פחות תווי טקסט מזה בעמוד בממוצע: PDF סרוק, בלי שכבת טקסט
OCR_MAX_PAGES = 60


def _safe_name(name):
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', "_", name or "").strip(" .")
    return name or "attachment"


def _pymupdf():
    try:
        import pymupdf
        return pymupdf
    except ImportError:
        try:
            import fitz
            return fitz
        except ImportError:
            return None


def pdf_signals(path):
    """{readable, pages, text_chars, scanned, method}. סרוק: יש עמודים, ובממוצע פחות מ-30 תווי טקסט בעמוד."""
    pages = chars = None
    mu = _pymupdf()
    try:
        if mu is not None:
            with mu.open(path) as doc:
                pages = len(doc)
                chars = sum(len(p.get_text().strip()) for p in doc)
            method = "pymupdf"
        else:
            from pypdf import PdfReader
            reader = PdfReader(path)
            pages = len(reader.pages)
            chars = sum(len((p.extract_text() or "").strip()) for p in reader.pages)
            method = "pypdf"
    except ImportError:
        return {"readable": None, "method": None}
    except Exception:  # noqa: BLE001 (PDF פגום או מוצפן: לא קורסים, מסמנים)
        return {"readable": False, "method": None}
    return {"readable": True, "pages": pages, "text_chars": chars, "method": method,
            "scanned": bool(pages) and chars < PAGE_TEXT_MIN * pages}


def dependencies():
    """מה מותקן מהתלויות של הסריקה: pymupdf (בדיקת PDF סרוק ורינדור לזיהוי טקסט), pypdf (בדיקה בלבד), tesseract."""
    try:
        import pypdf  # noqa: F401
        has_pypdf = True
    except ImportError:
        has_pypdf = False
    return {"pymupdf": _pymupdf() is not None, "pypdf": has_pypdf, "tesseract": bool(tesseract())}


def tesseract():
    """הנתיב לכלי זיהוי הטקסט tesseract, אם מותקן; אחרת None."""
    exe = shutil.which("tesseract")
    if not exe and os.name == "nt":
        for base in (os.environ.get("ProgramFiles", r"C:\Program Files"), os.environ.get("ProgramFiles(x86)", "")):
            cand = os.path.join(base, "Tesseract-OCR", "tesseract.exe") if base else ""
            if cand and os.path.exists(cand):
                exe = cand
                break
    return exe


def _ocr_langs(exe):
    try:
        out = subprocess.run([exe, "--list-langs"], capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.SubprocessError):
        return "eng"
    have = {ln.strip() for ln in out.splitlines()}
    return "+".join(x for x in ("heb", "eng") if x in have) or "eng"


def ocr_pdf(path, out_txt):
    """זיהוי טקסט ל-PDF סרוק: done (נכתב out_txt), unavailable (אין tesseract או אין PyMuPDF), failed."""
    exe, mu = tesseract(), _pymupdf()
    if not exe or mu is None:
        return "unavailable"
    langs, texts = _ocr_langs(exe), []
    try:
        with tempfile.TemporaryDirectory() as tmp, mu.open(path) as doc:
            for i, page in enumerate(doc):
                if i >= OCR_MAX_PAGES:
                    break
                png = os.path.join(tmp, "p%d.png" % i)
                page.get_pixmap(dpi=300).save(png)
                r = subprocess.run([exe, png, "stdout", "-l", langs], capture_output=True, timeout=180)
                texts.append("--- page %d ---\n%s" % (i + 1, r.stdout.decode("utf-8", "replace").strip()))
    except (OSError, subprocess.SubprocessError, RuntimeError, ValueError):
        return "failed"
    body = "\n\n".join(texts)
    if not re.sub(r"--- page \d+ ---", "", body).strip():
        return "failed"
    os.makedirs(os.path.dirname(out_txt), exist_ok=True)
    with open(out_txt, "w", encoding="utf-8") as f:
        f.write(body)
    return "done"


COPY_NAME = re.compile(r"(\bcopy\b|עותק|העתק|\(\d+\)(?=\.[^.]+$))", re.I)


def _copy_last(name):
    """בתוך תיקייה, קובץ ששמו מעיד על עותק ("(copy)", "(עותק)", "(1)") נסרק אחרי המקור, ולכן הוא שמסומן כפול."""
    return (bool(COPY_NAME.search(name)), name)


# A file Areo writes next to its own output (the drafter's "<draft>.report.json"). Skipped only when the document
# it belongs to is right beside it; otherwise it is an ordinary unreadable file and is reported as one
AREO_SIDECARS = (".report.json",)


def _areo_sidecar(dirpath, name):
    low = name.lower()
    for suf in AREO_SIDECARS:
        if low.endswith(suf):
            stem = name[:-len(suf)]
            return any(os.path.isfile(os.path.join(dirpath, stem + ext)) for ext in (".docx", ".doc", ".pdf"))
    return False


def _status(key, sha, previous, seen):
    if sha in seen:
        return "duplicate"
    if key not in previous:
        return "new"
    return "changed" if previous[key] != sha else "same"


def _eml_parts(raw):
    """(גוף המייל כטקסט, [(שם, בייטים)]) ממייל גולמי. מייל מצורף (message/rfc822) נשמר כקובץ .eml."""
    msg = email.message_from_bytes(raw, policy=email.policy.default)
    body = msg.get_body(preferencelist=("plain", "html"))
    text = ""
    if body is not None:
        try:
            text = body.get_content()
        except (LookupError, ValueError):
            text = ""
        if body.get_content_type() == "text/html":
            text = re.sub(r"<[^>]+>", " ", text)
    head = "\n".join("%s: %s" % (h, msg.get(h, "")) for h in ("From", "To", "Date", "Subject"))
    files = []
    for part in msg.iter_attachments():
        name = part.get_filename()
        if part.get_content_type() == "message/rfc822":
            inner = part.get_payload()
            inner = inner[0] if isinstance(inner, list) and inner else inner
            data = inner.as_bytes() if hasattr(inner, "as_bytes") else bytes(part.get_payload(decode=True) or b"")
            name = name or ((inner.get("Subject") if hasattr(inner, "get") else None) or "message") + ".eml"
        else:
            data = part.get_payload(decode=True) or b""
        files.append((_safe_name(name or "attachment"), data))
    return head + "\n\n" + (text or "").strip(), files


def _add_eml(entry, raw, work_dir, previous, seen, out, depth=0):
    """מייל: גוף המייל נשמר כטקסט, וכל קובץ מצורף נכנס לסריקה כרשומה משלו (container = המייל)."""
    try:
        text, files = _eml_parts(raw)
    except Exception:  # noqa: BLE001 (מייל פגום: מסומן ולא עוצר)
        entry["reason"] = "eml_unreadable"
        return
    base = os.path.join(work_dir, "attachments", entry["sha256"][:16]) if work_dir else None
    if base:
        os.makedirs(base, exist_ok=True)
        with open(os.path.join(base, "_message.txt"), "w", encoding="utf-8") as f:
            f.write(text)
        entry["text_path"] = os.path.join(base, "_message.txt")
    entry["attachments"] = []
    used = set()
    for name, data in files:
        stem, ext = os.path.splitext(name)
        n, i = name, 1
        while n.lower() in used:
            i += 1
            n = "%s (%d)%s" % (stem, i, ext)
        used.add(n.lower())
        key = entry["path"] + "/" + n
        sha = hashlib.sha256(data).hexdigest()
        full = os.path.join(base, n) if base else None
        if full:
            with open(full, "wb") as f:
                f.write(data)
        child = {"path": key, "abs": full, "sha256": sha, "container": entry["path"], "duplicate_of": None}
        entry["attachments"].append(key)
        if not n.lower().endswith(EXTS):
            child.update(status="unsupported", reason="file_type")
            out.append(child)
            continue
        child["status"] = _status(key, sha, previous, seen)
        child["duplicate_of"] = seen.get(sha) if child["status"] == "duplicate" else None
        seen.setdefault(sha, key)
        out.append(child)
        if n.lower().endswith(".eml") and depth < 2 and child["status"] != "duplicate":
            _add_eml(child, data, work_dir, previous, seen, out, depth + 1)
        elif n.lower().endswith(".pdf") and full:
            _add_pdf(child, full, work_dir)


def _add_pdf(entry, full, work_dir):
    """PDF בלי שכבת טקסט: scanned, וזיהוי טקסט כשיש במחשב כלי לכך (ocr: done / unavailable / failed)."""
    sig = pdf_signals(full)
    if sig.get("readable") is None:
        # אין במחשב pymupdf ואין pypdf: אי אפשר לבדוק אם ה-PDF סרוק. זה מסומן, ולא עובר בשקט
        entry["pdf_check"] = "unavailable"
        return
    if not sig.get("scanned"):
        return
    entry["scanned"] = True
    if not work_dir or not entry.get("sha256"):
        entry["ocr"] = "unavailable"
        return
    out_txt = os.path.join(work_dir, "ocr", entry["sha256"] + ".txt")
    entry["ocr"] = "done" if os.path.exists(out_txt) else ocr_pdf(full, out_txt)
    if entry["ocr"] == "done":
        entry["text_path"] = out_txt


def scan(folders, previous=None, excluded=(), work_dir=None, report=None):
    """רשומה לכל קובץ. אף קובץ אינו נעלם בשקט: קובץ מסוג שאינו נקרא מסומן unsupported, ומה שלא נסרק נרשם ב-report:
    missing (נתיב שלא נמצא), system (קובצי מערכת וקובצי נעילה), data_dirs (תיקיית Areo-נתונים).
    נתיב יכול להיות תיקייה או קובץ בודד. work_dir (ingest): לשם נכתבים קבצים מצורפים ממיילים וזיהוי טקסט."""
    previous = previous or {}
    report = report if report is not None else {}
    for k in ("missing", "system", "data_dirs"):
        report.setdefault(k, [])
    rules = _prepare(excluded)
    seen, out = {}, []
    for folder in folders:
        if not os.path.exists(folder):
            report["missing"].append(folder)
            continue
        if os.path.isfile(folder):
            parent = os.path.dirname(os.path.abspath(folder))
            walk = [(parent, [], [os.path.basename(folder)])]
            folder = parent
        else:
            walk = os.walk(folder)
        top = os.path.basename(os.path.normpath(folder))
        for dirpath, dirs, files in walk:
            dirs.sort()
            for d in [d for d in dirs if d.lower() in DATA_DIRS]:
                dirs.remove(d)
                report["data_dirs"].append(os.path.join(dirpath, d))
            for name in sorted(files, key=_copy_last):
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, folder).replace("\\", "/")
                key = top + "/" + rel
                if name.startswith("~$") or name.lower() in SYSTEM_FILES or _areo_sidecar(dirpath, name):
                    report["system"].append(key)
                    continue
                if _is_excluded(full, rel, key, rules):
                    continue
                supported = name.lower().endswith(EXTS)
                try:
                    sha = sha256_file(full)
                except OSError:
                    out.append({"path": key, "abs": full, "sha256": previous.get(key), "status": "unreadable",
                                "duplicate_of": None})
                    continue
                if not supported:
                    out.append({"path": key, "abs": full, "sha256": sha, "status": "unsupported", "reason": "file_type",
                                "duplicate_of": None})
                    continue
                status = _status(key, sha, previous, seen)
                entry = {"path": key, "abs": full, "sha256": sha, "status": status,
                         "duplicate_of": seen.get(sha) if status == "duplicate" else None}
                out.append(entry)
                seen.setdefault(sha, key)
                if status == "duplicate":
                    continue
                if name.lower().endswith(".eml"):
                    with open(full, "rb") as f:
                        _add_eml(entry, f.read(), work_dir, previous, seen, out)
                elif name.lower().endswith(".pdf"):
                    _add_pdf(entry, full, work_dir)
    present = {x["path"] for x in out}
    for key, sha in sorted(previous.items()):
        if key not in present:
            out.append({"path": key, "abs": None, "sha256": sha, "status": "removed", "duplicate_of": None})
    return out
