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
