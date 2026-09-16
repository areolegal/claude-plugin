#!/bin/bash
# AreoLegal plugin release.
#
#   ./release.sh patch "fixed the setup skill trigger"
#   ./release.sh minor "new skill: contract summary"
#   ./release.sh 1.2.0 "explicit version"
#
# Validates, bumps every version in step, commits, tags and pushes.
# Nothing is pushed unless every check passes.
set -euo pipefail
cd "$(dirname "$0")"

BUMP="${1:-}"; MESSAGE="${2:-}"
if [ -z "$BUMP" ] || [ -z "$MESSAGE" ]; then
  echo "usage: ./release.sh <patch|minor|major|X.Y.Z> \"what changed\""; exit 1
fi

MARKET=".claude-plugin/marketplace.json"
MANIFEST="areolegal/.claude-plugin/plugin.json"
PROXY="areolegal/mcp/areolegal_mcp.py"
CURRENT=$(python3 -c "import json;print(json.load(open('$MANIFEST'))['version'])")

NEW=$(python3 - "$CURRENT" "$BUMP" <<'PY'
import sys, re
cur, bump = sys.argv[1], sys.argv[2]
if re.fullmatch(r"\d+\.\d+\.\d+", bump):
    print(bump); raise SystemExit
major, minor, patch = (int(x) for x in cur.split("."))
if bump == "major":   major, minor, patch = major + 1, 0, 0
elif bump == "minor": minor, patch = minor + 1, 0
elif bump == "patch": patch += 1
else:
    sys.exit(f"unknown bump '{bump}' (use patch|minor|major|X.Y.Z)")
print(f"{major}.{minor}.{patch}")
PY
)

echo "==> Releasing $CURRENT -> $NEW"

echo "==> 1/5 Validating manifests and skills"
python3 - "$MARKET" "$MANIFEST" <<'PY'
import json, sys, pathlib
market, manifest = (json.load(open(p)) for p in sys.argv[1:3])
assert market["plugins"][0]["name"] == manifest["name"], "plugin name mismatch"
root = pathlib.Path("areolegal/skills")
skills = sorted(d.name for d in root.iterdir() if d.is_dir())
assert skills, "no skills found"
for s in skills:
    md = root / s / "SKILL.md"
    assert md.exists(), f"{s}: SKILL.md missing"
    head = md.read_text(encoding="utf-8")[:400]
    assert head.startswith("---") and "name:" in head and "description:" in head, \
        f"{s}: SKILL.md needs YAML frontmatter with name + description"
print("   skills ok:", ", ".join(skills))
PY

echo "==> 1b/5 Verifying the commercial wrapper is intact"
python3 - <<'PY'
import pathlib, sys

# Deliberately ungated: the activation skill (it IS the activation path) and the
# RTL formatter (generic python-docx formatting, no protected content).
UNGATED = {"areolegal-activate", "rtl-docx-enforcer"}
bad = []
for md in sorted(pathlib.Path("areolegal/skills").glob("*/SKILL.md")):
    text = md.read_text(encoding="utf-8")
    skill = md.parent.name
    # A skill that lost its licence gate works without a subscription; one that
    # reads local references/ needs the protected content shipped in this PUBLIC
    # repo. Both have happened by accident when a skill was rewritten elsewhere.
    if skill not in UNGATED and "license_status" not in text:
        bad.append(f"{skill}: no licence gate (license_status missing)")
    if "references/" in text and "get_resource" not in text:
        bad.append(f"{skill}: reads local references/ instead of get_resource()")
if bad:
    print("   REFUSING TO RELEASE:")
    for b in bad:
        print("     -", b)
    print("   Restore the licence gate and server fetching, then release again.")
    sys.exit(1)
print("   licence gate + server fetching present in every skill")
PY

echo "==> 1b2/5 Verifying the profile gate cannot silently re-onboard"
python3 - <<'PY'
import pathlib, re, sys

# A skill that loses this rule answers "no profile file" by running setup, which
# forks the customer's company data into a second, diverging profile that nothing
# reports. The marker it reads is written by mark_setup and rides on
# license_status, so all three pieces are checked together.
GATED = {"contract-drafter", "contract-negotiation-orchestrator",
         "contract-playbook-builder", "contract-risk-assessor",
         "legal-contract-translator", "negotiation-strategist", "playbook-workspace"}
bad = []

mcp = pathlib.Path("areolegal/mcp/areolegal_mcp.py").read_text(encoding="utf-8")
if '"name": "mark_setup"' not in mcp:
    bad.append("mcp: mark_setup tool is gone")
if 'body["local_setup"] = local_setup()' not in mcp:
    bad.append("mcp: license_status no longer carries local_setup")

setup_md = pathlib.Path("areolegal/skills/contract-setup-diagnostician/SKILL.md").read_text(encoding="utf-8")
if "mark_setup" not in setup_md:
    bad.append("contract-setup-diagnostician: never records the marker (mark_setup missing)")

for skill in sorted(GATED):
    text = pathlib.Path("areolegal/skills/%s/SKILL.md" % skill).read_text(encoding="utf-8")
    if "local_setup" not in text:
        bad.append("%s: profile gate does not consult local_setup" % skill)
    if "אם אין פרופיל, עצור והפעל את ההקמה" in text:
        bad.append("%s: still runs setup unconditionally when the profile file is absent" % skill)

# The shared folder is the root of Areo-נתונים, not just an output target. Eight
# components read connections.shared_output_folder, and for a long time nothing
# wrote it -- so the field is asserted at the writer, not only at the readers.
writer = pathlib.Path("areolegal/skills/contract-setup-diagnostician/scripts/build_profile.py").read_text(encoding="utf-8")
if '"shared_output_folder"' not in writer:
    bad.append("build_profile.py: connections.shared_output_folder is not written")

for skill in sorted(GATED | {"contract-setup-diagnostician"}):
    text = pathlib.Path("areolegal/skills/%s/SKILL.md" % skill).read_text(encoding="utf-8")
    if "shared_output_folder" not in text:
        bad.append("%s: lost the shared-folder rule" % skill)

# The drafter must never hand-build a Word document again: that is what made the
# production step take tens of minutes and ship Word-default output.
drafter = pathlib.Path("areolegal/skills/contract-drafter/SKILL.md").read_text(encoding="utf-8")
if not pathlib.Path("areolegal/skills/contract-drafter/scripts/build_draft_docx.py").is_file():
    bad.append("contract-drafter: build_draft_docx.py is missing")
if "build_draft_docx.py" not in drafter:
    bad.append("contract-drafter: the skill no longer calls the builder")
for script in ("build_master_template.py", "fill_template.py", "docx_numbering.py",
               "build_research_brief.py", "research_sources.py"):
    if not pathlib.Path("areolegal/skills/contract-drafter/scripts/" + script).is_file():
        bad.append("contract-drafter: %s is missing" % script)
if "fill_template.py" not in drafter or "build_master_template.py" not in drafter:
    bad.append("contract-drafter: states 1-3 no longer go through the master template")
if "build_research_brief.py" not in drafter:
    bad.append("contract-drafter: state 4 no longer shows the research for approval before drafting")
if "rtl-docx-enforcer" in drafter and "\u05d0\u05d9\u05df \u05dc\u05d4\u05e2\u05d1\u05d9\u05e8" not in drafter:
    bad.append("contract-drafter: the extra rtl-docx-enforcer pass is back")

# A get_resource() pointing at a file that does not exist fails silently at runtime.
# server/content only sits beside the plugin in the working tree, so skip elsewhere.
content_root = pathlib.Path("../server/content")
if content_root.is_dir():
    missing = set()
    for md in sorted(pathlib.Path("areolegal/skills").glob("*/SKILL.md")):
        text = md.read_text(encoding="utf-8")
        for skill_name, res in re.findall(
                r'get_resource\(skill="([^"]+)",\s*name="([^"]+)"\)', text):
            if "<" in skill_name or "<" in res:
                continue
            if not (content_root / skill_name / res).is_file():
                missing.add("%s -> %s/%s" % (md.parent.name, skill_name, res))
    for m in sorted(missing):
        bad.append("dangling get_resource: " + m)
else:
    print("   (server content not beside the plugin; get_resource targets not checked)")

if bad:
    print("   REFUSING TO RELEASE:")
    for b in bad:
        print("     -", b)
    sys.exit(1)
print("   profile gate consults local_setup in every gated skill; marker is written")
print("   shared folder is written by the setup script and read by every component")
print("   drafter builds Word through the script, and every get_resource target exists")
PY

echo "==> 1d/5 Smoke-testing the drafter's template pipeline on a synthetic agreement"
SMOKE_DIR=$(mktemp -d)
python3 - "$SMOKE_DIR" <<'PY'
# -*- coding: utf-8 -*-
# Real Hebrew agreements use Word auto-numbering, tabs at the start of paragraphs, and
# annexes that restart at 1. Two bugs shipped-in-waiting were caught only by running
# the pipeline on such a document: a tab shifted every replacement by one character
# ("בסעיף 2.4 לעיל" became "בסעיף 22.3לעיל"), and a long annex was taken for the body,
# so "remove clause 4" removed the annex's clause 4. This fixture reproduces all of it.
import copy, io, json, os, subprocess, sys
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
out = sys.argv[1]
S = "areolegal/skills/contract-drafter/scripts"
sys.path.insert(0, S)
from docx_numbering import labelled_paragraphs, assign_segments

def el(tag, **kw):
    e = OxmlElement(tag)
    for k, v in kw.items():
        e.set(qn("w:" + k), v)
    return e

doc = Document()
numbering = doc.part.numbering_part.element
an = el("w:abstractNum", abstractNumId="90")
for il, txt in ((0, "%1."), (1, "%1.%2.")):
    lvl = el("w:lvl", ilvl=str(il)); lvl.append(el("w:start", val="1")); lvl.append(el("w:numFmt", val="decimal"))
    lvl.append(el("w:lvlText", val=txt)); an.append(lvl)
numbering.insert(0, an)
for nid in ("91", "92"):
    n = el("w:num", numId=nid); n.append(el("w:abstractNumId", val="90"))
    lo = el("w:lvlOverride", ilvl="0"); lo.append(el("w:startOverride", val="1")); n.append(lo)
    numbering.append(n)

def para(text, num=None, lvl=0):
    p = doc.add_paragraph()
    if num:
        ppr = p._p.get_or_add_pPr(); npr = el("w:numPr")
        npr.append(el("w:ilvl", val=str(lvl))); npr.append(el("w:numId", val=num)); ppr.append(npr)
    if text.startswith("\t"):
        p.add_run().add_tab(); text = text[1:]
    for chunk in (text[:len(text) // 2], text[len(text) // 2:]):   # split runs, like real files
        if chunk:
            p.add_run(chunk)

para('בין: אקמה בע"מ'); para("ח.פ 512345678"); para('לבין: ספק דוגמה בע"מ'); para("ח.פ 598765432")
para("הואיל והצדדים מעוניינים להתקשר;")
body = [(0, "\tמבוא"), (1, "\tהמבוא — כמו הנספחים — מהווה חלק בלתי נפרד."), (0, "\tהשירותים"), (1, "\tהספק ייתן שירותים."),
        (0, "\tהתמורה"), (1, '\tסך חודשי של ______________בתוספת מע"מ.'),
        (0, "\tסודיות"), (1, "\tמוסכם כי סעיף 4 זה יחול גם לאחר הסיום, בכפוף לסעיף 14 לחוק פיצויי פיטורים."),
        (0, "\tשונות"), (1, "\tכאמור בסעיפים 3.1 ו-4 לעיל.")]
for lvl, t in body:
    para(t, "91", lvl)
para("ולראיה באו הצדדים על החתום:"); para("______________        ______________")
for i in range(6):                      # the annex has MORE top clauses than the body
    para("\tהתחייבות נספח %d" % (i + 1), "92", 0)
src = os.path.join(out, "fixture.docx"); doc.save(src)

bad = []
def ck(label, cond):
    print("   %s %s" % ("ok  " if cond else "FAIL", label))
    if not cond: bad.append(label)

tpl = os.path.join(out, "tpl")
r = subprocess.run([sys.executable, S + "/build_master_template.py", "--source", src, "--family", "fixture",
                    "--kind", "template", "--company", 'אקמה בע"מ', "--out-dir", tpl], capture_output=True, text=True)
ck("build_master_template runs", r.returncode == 0)
sk = json.load(io.open(os.path.join(tpl, "skeleton.json"), encoding="utf-8"))
ids = [v["id"] for v in sk["variables"]]
ck("fee blank is the only variable (signature lines excluded): %s" % ids, len(ids) == 1 and ids[0].startswith("סכום"))
vals = {"variables": {ids[0]: '12,000 ש"ח'}, "remove_clauses": ["2"], "author": "בדיקה",
        "add_clauses": [{"after": "4.1", "text": "סעיף שנכתב עכשיו — עם מקף ארוך."}]}
io.open(os.path.join(out, "v.json"), "w", encoding="utf-8").write(json.dumps(vals, ensure_ascii=False))
dr = os.path.join(out, "draft.docx")
r = subprocess.run([sys.executable, S + "/fill_template.py", "--template", os.path.join(tpl, "master.docx"),
                    "--values", os.path.join(out, "v.json"), "--out", dr], capture_output=True, text=True)
ck("fill_template runs clean", r.returncode == 0)
rows = labelled_paragraphs(Document(dr)); assign_segments(rows)
T = "\n".join(x["text"] for x in rows)
tops = [(x["key"], x["segment"]) for x in rows if x["label"] and x["level"] == 0]
ck("body clause 2 removed, not the annex's", ("4", 0) in tops and ("5", 0) not in tops and len([t for t in tops if t[1] == 1]) == 6)
ck("amount filled at the exact spot", 'סך חודשי של 12,000 ש"חבתוספת' in T)
ck("internal refs shifted exactly", "כי סעיף 3 זה יחול" in T and "כאמור בסעיפים 2.1 ו-3 לעיל." in T)
ck("statutory ref untouched", "בכפוף לסעיף 14 לחוק פיצויי פיטורים" in T)

# em-dash: the client's approved wording is a warning, text we wrote still blocks
chk = subprocess.run([sys.executable, S + "/check_draft_integrity.py", dr, "--template",
                      os.path.join(tpl, "master.docx"), "--json", os.path.join(out, "c.json")],
                     capture_output=True, text=True)
found = json.load(io.open(os.path.join(out, "c.json"), encoding="utf-8"))["findings"]
style = [(f["level"], f["message"]) for f in found if f["area"] == "סגנון"]
ck("dashes in the approved template wording are a warning", any(l == "אזהרה" and m.startswith("2 ") for l, m in style))
ck("a dash in newly written text still blocks", any(l == "חוסם" and m.startswith("1 ") for l, m in style))
chk = subprocess.run([sys.executable, S + "/check_draft_integrity.py", dr, "--json", os.path.join(out, "c2.json")],
                     capture_output=True, text=True)
found = json.load(io.open(os.path.join(out, "c2.json"), encoding="utf-8"))["findings"]
ck("without --template every dash blocks, as before",
   any(f["area"] == "סגנון" and f["level"] == "חוסם" and f["message"].startswith("3 ") for f in found))

ag = os.path.join(out, "ag")
subprocess.run([sys.executable, S + "/build_master_template.py", "--source", src, "--family", "fixture",
                "--kind", "agreement", "--company", 'אקמה בע"מ', "--out-dir", ag], capture_output=True, text=True)
skv = json.load(io.open(os.path.join(ag, "skeleton.json"), encoding="utf-8"))["variables"]
found = {v["found_value"] for v in skv}
ck("agreement kind: counterparty and its ID are variables, the company's are not",
   'ספק דוגמה בע"מ' in found and "598765432" in found and "512345678" not in found)
# ---- state 4: research sources are enforced, and a typed-number draft renumbers like Word
research = {"agreement_type": "SaaS", "company_role": "ספק", "consent_at": "2026-09-16",
            "law": [{"instrument": "חוק הגנת הפרטיות", "url": "https://main.knesset.gov.il/x", "verified": True, "effect": "סעיף חובה"}],
            "structures": [{"title": "t%d" % i, "source_type": "אתר משפטי", "url": "https://legal.example/%d" % i,
                            "topics": ["נושא%d" % i]} for i in range(3)]}
def brief(obj, name):
    path = os.path.join(out, name + ".json")
    io.open(path, "w", encoding="utf-8").write(json.dumps(obj, ensure_ascii=False))
    return subprocess.run([sys.executable, S + "/build_research_brief.py", "--research", path,
                           "--out", os.path.join(out, name + ".docx")], capture_output=True, text=True)
ck("valid research builds the approval document", brief(research, "r_ok").returncode == 0)
nevo = json.loads(json.dumps(research)); nevo["law"].append({"instrument": "x", "url": "https://www.nevo.co.il/x", "verified": True})
ck("a law source outside the Knesset/gov.il is refused", brief(nevo, "r_nevo").returncode == 1)
many = json.loads(json.dumps(research)); many["structures"] = many["structures"] * 3
ck("more than 7 structure sources are refused", brief(many, "r_many").returncode == 1)
noc = json.loads(json.dumps(research)); del noc["consent_at"]
ck("research without the user's consent is refused", brief(noc, "r_noconsent").returncode == 1)

d4 = {"meta": {"title": "הסכם", "language": "he", "notice": "טיוטה זו נבנתה ללא נייר של החברה."},
      "clauses": [{"number": "1", "heading": "רישיון", "text": "רישיון שימוש.",
                   "children": [{"number": "1.1", "text": "כפוף לסעיף 3 להלן."}]},
                  {"number": "2", "heading": "רמת שירות", "text": "זמינות."},
                  {"number": "3", "heading": "תמורה", "text": "דמי מנוי.",
                   "children": [{"number": "3.1", "text": "בהתאם לסעיף 3 זה ולסעיף 1.1 לעיל."}]},
                  {"number": "4", "heading": "אחריות", "text": "תקרה.", "needs_case_law": True}],
      "sources": {"law": research["law"], "structures": research["structures"]}}
io.open(os.path.join(out, "d4.json"), "w", encoding="utf-8").write(json.dumps(d4, ensure_ascii=False))
subprocess.run([sys.executable, S + "/build_draft_docx.py", "--draft", os.path.join(out, "d4.json"),
                "--out", os.path.join(out, "d4.docx")], capture_output=True, check=True)
t4 = "\n".join(x["text"] for x in labelled_paragraphs(Document(os.path.join(out, "d4.docx"))))
ck("research draft: notice, case-law marker and internal sources annex",
   "נבנתה ללא נייר של החברה" in t4 and "[טעון בדיקת פסיקה]" in t4 and "נספח מקורות" in t4)
del d4["sources"], d4["meta"]["notice"], d4["clauses"][3]["needs_case_law"]
io.open(os.path.join(out, "a4.json"), "w", encoding="utf-8").write(json.dumps(d4, ensure_ascii=False))
subprocess.run([sys.executable, S + "/build_draft_docx.py", "--draft", os.path.join(out, "a4.json"),
                "--out", os.path.join(out, "a4.docx")], capture_output=True, check=True)
t4dir = os.path.join(out, "t4")
subprocess.run([sys.executable, S + "/build_master_template.py", "--source", os.path.join(out, "a4.docx"),
                "--family", "f", "--kind", "template", "--out-dir", t4dir], capture_output=True, check=True)
io.open(os.path.join(out, "v4.json"), "w", encoding="utf-8").write(json.dumps(
    {"remove_clauses": ["2"], "add_clauses": [{"after": "1.1", "text": "אין הנדסה לאחור."}]}, ensure_ascii=False))
subprocess.run([sys.executable, S + "/fill_template.py", "--template", os.path.join(t4dir, "master.docx"),
                "--values", os.path.join(out, "v4.json"), "--out", os.path.join(out, "f4.docx")], capture_output=True)
f4 = "\n".join(x["text"] for x in labelled_paragraphs(Document(os.path.join(out, "f4.docx"))))
ck("typed numbers rewritten after removal and addition",
   "רמת שירות" not in f4 and "2. תמורה" in f4 and "3. אחריות" in f4 and "1.2 אין הנדסה לאחור." in f4)
ck("references follow the typed renumbering", "כפוף לסעיף 2 להלן." in f4 and "בהתאם לסעיף 2 זה ולסעיף 1.1 לעיל." in f4)

if bad:
    print("   REFUSING TO RELEASE: the drafter template pipeline is broken")
    sys.exit(1)
print("   template pipeline: numbering, references, annexes and variables all correct")
PY
rm -rf "$SMOKE_DIR"

echo "==> 1c/5 Checking commands and referenced scripts are runnable"
python3 - <<'PY'
import pathlib, re, sys

# A get_resource(...) call substituted into a shell command produces a command
# line that cannot run. When that shipped, the skills could not execute their
# documented build step and invented their own HTML, discarding the branded
# template. Also catch scripts a skill tells the client to run but that are not
# in the package -- those fail at the client with no useful message.
FENCE = re.compile(r"```.*?```", re.S)
bad = []
for md in sorted(pathlib.Path("areolegal/skills").glob("*/SKILL.md")):
    text, skill = md.read_text(encoding="utf-8"), md.parent.name
    for fence in FENCE.findall(text):
        if "get_resource(" in fence:
            bad.append(f"{skill}: get_resource() inside a shell command -- not runnable")
            break
    # a reference may be the skill's own (scripts/x.py) or another skill's
    # (other-skill/scripts/x.py); resolve each against the right folder
    for owner, ref in sorted(set(re.findall(
            r"(?:([a-z][\w-]*)/)?(scripts/[\w.-]+\.(?:py|js))", text))):
        base = md.parent.parent / owner if owner else md.parent
        if not (base / ref).exists():
            where = f"{owner}/{ref}" if owner else ref
            bad.append(f"{skill}: references {where}, which is not shipped")
if bad:
    print("   REFUSING TO RELEASE:")
    for b in bad:
        print("     -", b)
    sys.exit(1)
print("   every documented command is runnable and every script is present")
PY

echo "==> 2/5 Compiling bundled Python"
find areolegal -name "*.py" -print0 | xargs -0 -n1 python3 -m py_compile
echo "   all scripts compile"

echo "==> 3/5 Checking nothing secret is bundled"
if grep -rIlE "AREO-[A-Za-z0-9_-]{20,}|re_[A-Za-z0-9]{20,}|x-api-key" \
     --exclude-dir=.git --exclude="release.sh" . 2>/dev/null | grep -q .; then
  echo "   REFUSING: a key-shaped string is present in the plugin repo"; exit 1
fi
echo "   clean"

echo "==> 4/5 Bumping version in manifest, marketplace and proxy"
python3 - "$MARKET" "$MANIFEST" "$PROXY" "$NEW" <<'PY'
import json, re, sys
market_p, manifest_p, proxy_p, new = sys.argv[1:5]
for path, setter in ((market_p, "market"), (manifest_p, "manifest")):
    d = json.load(open(path))
    if setter == "market":
        d["metadata"]["version"] = new
        d["plugins"][0]["version"] = new
    else:
        d["version"] = new
    json.dump(d, open(path, "w"), ensure_ascii=False, indent=2)
    open(path, "a").write("\n")
src = open(proxy_p).read()
src = re.sub(r'PLUGIN_VERSION = "[^"]+"', f'PLUGIN_VERSION = "{new}"', src)
open(proxy_p, "w").write(src)
print(f"   version set to {new} in all three files")
PY

echo "==> 5/5 Commit, tag, push"
git add -A
git commit -q -m "v$NEW: $MESSAGE"
git tag -a "v$NEW" -m "$MESSAGE"
git push -q origin HEAD
git push -q origin "v$NEW"

echo
echo "Released v$NEW — $MESSAGE"
echo "Clients pick it up from Claude: Customize -> Plugins -> AreoLegal -> Update, then restart the app."
