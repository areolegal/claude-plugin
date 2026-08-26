# Shipping AreoLegal updates

Two kinds of update. **Most changes are the first kind — and clients never have to do anything.**

## 1. Content / methodology → server deploy, instant, no client action

Anything that is professional substance — taxonomies, clause libraries, legal anchors,
phase methodologies, reasoning templates, prompts the skills fetch at runtime — lives in
`server/content/`, not in the plugin. Clients pull it fresh on every use.

```bash
cd ~/Documents/Projects/areolegal/server && ./deploy.sh
```

Live in ~3 minutes for everyone. Nobody updates anything. **Default to this path.**
If you find yourself about to edit a skill just to change wording of legal substance,
move that text into `server/content/` instead and let the skill fetch it.

## 2. Skill instructions / proxy → plugin release, clients must update

Only these require a release:

- a skill's triggers, workflow steps, or the files it fetches
- adding or removing a skill
- bundled scripts (`skills/*/scripts/*.py`)
- the MCP proxy (`areolegal/mcp/areolegal_mcp.py`)

```bash
cd ~/Documents/Projects/areolegal/plugin
./release.sh patch "fixed the setup skill trigger"
```

`patch` for fixes, `minor` for new capability, `major` for anything clients must relearn.
An explicit `1.2.0` also works.

The script refuses to push unless: both manifests agree, every skill has `SKILL.md` with
valid frontmatter, all bundled Python compiles, and no key-shaped string is in the repo.
Then it bumps the version in **all three** places (marketplace.json, plugin.json, proxy),
commits, tags `vX.Y.Z`, and pushes.

**Clients update in Claude:** Customize → Plugins → AreoLegal → Update, then restart the app.

## Telling clients

Only for path 2, and only when it changes what they see. The proxy sends its version to the
server on every request, so you can check who is still on an old build:

```bash
cd ~/Documents/Projects/areolegal/server
CLOUDSDK_PYTHON=/opt/homebrew/bin/python3.11 gcloud logging read \
  'resource.type=cloud_run_revision AND httpRequest.userAgent:"areolegal-mcp"' \
  --project areolegal-api --limit 50 --freshness=7d \
  --format="value(httpRequest.userAgent)" | sort | uniq -c
```

## Rules

1. **Never put protected content in the plugin.** Skills are plaintext on client machines.
   Anything worth paying for stays server-side behind the licence check.
2. **Never commit a licence key, API key or token** to this repo — it is public. The release
   script blocks the obvious shapes, but it is not a substitute for care.
3. **Client documents never leave the client.** Do not add any upload path to a skill.
4. Test a skill change in your own Claude (Code tab) before releasing.
