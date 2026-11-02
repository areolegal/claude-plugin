import os
from clm import fingerprint


def _write(p, text):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)


def test_scan_statuses(tmp_path):
    root = tmp_path / "הסכמים"
    _write(str(root / "a.docx"), "A")
    _write(str(root / "sub" / "b.pdf"), "B")
    _write(str(root / "copy-of-a.docx"), "A")
    _write(str(root / "~$lock.docx"), "X")
    _write(str(root / "notes.xlsx"), "N")
    report = {}
    first = fingerprint.scan([str(root)], report=report)
    by = {x["path"]: x for x in first}
    assert by["הסכמים/a.docx"]["status"] == "new"
    assert by["הסכמים/sub/b.pdf"]["status"] == "new"
    assert by["הסכמים/copy-of-a.docx"]["status"] == "duplicate"
    assert by["הסכמים/copy-of-a.docx"]["duplicate_of"] == "הסכמים/a.docx"
    # אף קובץ אינו נעלם בשקט: סוג שאינו נקרא מסומן unsupported, וקובץ נעילה נרשם בדוח
    assert "הסכמים/~$lock.docx" not in by and report["system"] == ["הסכמים/~$lock.docx"]
    assert by["הסכמים/notes.xlsx"]["status"] == "unsupported" and by["הסכמים/notes.xlsx"]["reason"] == "file_type"

    prev = {x["path"]: x["sha256"] for x in first if x["status"] not in ("duplicate", "unsupported")}
    _write(str(root / "sub" / "b.pdf"), "B2")
    os.remove(str(root / "a.docx"))
    second = {x["path"]: x for x in fingerprint.scan([str(root)], previous=prev)}
    assert second["הסכמים/sub/b.pdf"]["status"] == "changed"
    assert second["הסכמים/a.docx"]["status"] == "removed"
    assert second["הסכמים/copy-of-a.docx"]["status"] == "new"


def test_excluded_paths(tmp_path):
    root = tmp_path / "הסכמים"
    _write(str(root / "hr" / "x.docx"), "X")
    _write(str(root / "y.docx"), "Y")
    paths = {x["path"] for x in fingerprint.scan([str(root)], excluded=("hr/",))}
    assert paths == {"הסכמים/y.docx"}


def test_exclude_normalises_slashes_case_absolute_and_segments(tmp_path):
    root = tmp_path / "הסכמים"
    _write(str(root / "HR" / "Private" / "x.docx"), "X")
    _write(str(root / "HR" / "keep.docx"), "K")
    _write(str(root / "HR2" / "z.docx"), "Z")
    _write(str(root / "y.docx"), "Y")

    def paths(*ex):
        return {x["path"] for x in fingerprint.scan([str(root)], excluded=ex)}
    everything = {"הסכמים/HR/Private/x.docx", "הסכמים/HR/keep.docx", "הסכמים/HR2/z.docx", "הסכמים/y.docx"}
    assert paths("hr\\private") == everything - {"הסכמים/HR/Private/x.docx"}
    assert paths("./HR/") == {"הסכמים/HR2/z.docx", "הסכמים/y.docx"}
    assert paths("הסכמים/hr") == {"הסכמים/HR2/z.docx", "הסכמים/y.docx"}
    assert paths(str(root / "HR")) == {"הסכמים/HR2/z.docx", "הסכמים/y.docx"}
    assert paths(str(root / "y.docx")) == everything - {"הסכמים/y.docx"}
    assert paths("h") == everything and paths("HR/Priv") == everything


def test_unreadable_file_does_not_abort_and_keeps_previous_sha(tmp_path, monkeypatch):
    root = tmp_path / "הסכמים"
    _write(str(root / "a.docx"), "A")
    _write(str(root / "b.docx"), "B")
    first = {x["path"]: x["sha256"] for x in fingerprint.scan([str(root)])}
    real = fingerprint.sha256_file

    def locked(path):
        if path.endswith("a.docx"):
            raise PermissionError(13, "locked")
        return real(path)
    monkeypatch.setattr(fingerprint, "sha256_file", locked)
    by = {x["path"]: x for x in fingerprint.scan([str(root)], previous=first)}
    assert by["הסכמים/a.docx"]["status"] == "unreadable"
    assert by["הסכמים/a.docx"]["sha256"] == first["הסכמים/a.docx"]
    assert by["הסכמים/b.docx"]["status"] == "same" and len(by) == 2
    new = {x["path"]: x for x in fingerprint.scan([str(root)])}
    assert new["הסכמים/a.docx"]["status"] == "unreadable" and new["הסכמים/a.docx"]["sha256"] is None
