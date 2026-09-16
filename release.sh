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
import pathlib, sys

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

if bad:
    print("   REFUSING TO RELEASE:")
    for b in bad:
        print("     -", b)
    sys.exit(1)
print("   profile gate consults local_setup in every gated skill; marker is written")
print("   shared folder is written by the setup script and read by every component")
PY

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
