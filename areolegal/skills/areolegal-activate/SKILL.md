---
name: areolegal-activate
description: Activate and onboard the AreoLegal legal suite. Use when the user wants to activate their AreoLegal subscription or license key, mentions "הפעלה", "רישיון", "מפתח רישיון", "activate areolegal", "setup areolegal", asks why AreoLegal skills say the subscription is inactive, or right after installing the AreoLegal plugin. Also use to explain what the suite can do.
---

# AreoLegal Setup & Onboarding

Guide the user through activating the AreoLegal suite on this machine. Speak the user's language (Hebrew by default for Hebrew speakers).

## Step 0, Which path is this session on

AreoLegal reaches its service two ways, and BOTH are fully supported. Never tell a user that their environment is unsupported.

- **Code tab / Claude Code**: the plugin's own MCP server runs locally and calls the service directly. Activation happens here via the `activate` tool, below.
- **Cowork (and any sandboxed chat session)**: the sandbox blocks the local server from reaching the network, so access comes from the **AreoLegal connector** instead, which runs outside the sandbox. The connector authenticates the user itself, so there is no `activate` step: once the connector is added, `license_status` and the content tools work.

If the tools are missing or a call fails with a connection/network error in a chat session, do not ask for the licence key again. Walk the user through adding the connector:

1. Settings → Connectors → Add custom connector
2. URL: `https://areo.co.il/mcp`
3. Connect → an AreoLegal sign-in page opens → paste the licence key (`AREO-…`) there → approve
4. Return to the chat and retry, `license_status` should now report ACTIVE.

The key is entered on AreoLegal's own sign-in page, never pasted into the chat.

## כללי הרוחב: נטענים מהקובץ המשותף

לפני כל פעולה אחרת, אחרי אימות הרישיון, טען `get_resource(skill="areo-shared", name="areo-hard-rules.md")`, ואחריו `get_resource(skill="areo-shared", name="hard-rules.md")`. הראשון הוא הנוסח הרשמי של הכללים שחלים על כל רכיבי Areo: פסיקה, מקורות, יציאה לרשת, פרטיות, שפה, סימון תוצרים ואיסור המצאה. השני הוא תוספות מקומיות שממתינות להכרעה. **כלל שכתוב שם גובר על כל נוסח בקובץ הזה.**

הרכיב אינו מחזיק עותק משלו של כלל שנמצא שם ואינו חוזר עליו במילים אחרות. כאן נשאר רק מה שייחודי לו.

**רשימת המקורות המורשים** נטענת בנפרד, `get_resource(skill="areo-shared", name="approved-regulatory-sources.md")`, ורק כשהרכיב עומד לצאת לרשת.

## Step 1, Activate the license

Skip this step entirely when the connector is the access path (see Step 0), the connector already authenticated the user, so ask for nothing and go straight to `license_status`.

1. Ask the user for their AreoLegal license key (they received it on the purchase success page / from AreoLegal). It looks like `AREO-...`.
2. Call the `areolegal` MCP tool `activate` with the key. This stores it locally and validates it against the AreoLegal service.
3. On success, show the subscription status (plan, expiry), but never repeat the key itself back into the conversation. On failure, relay the message; if they don't have a key yet, direct them to purchase a subscription on the AreoLegal website.

Never ask the user to paste the key into files manually; the `activate` tool handles storage.

## Step 2, Tour (brief)

Tell the user what is now available, one short line each. Keep it to this list; do not invent
components and do not promise anything outside it.

- **contract-setup-diagnostician**: builds the Organization Profile from a short questionnaire (company, incorporation, sector, markets, regulators, interface language). Recommend running this FIRST, once. Every other component is gated on it.
- **contract-playbook-builder**: builds a Green/Yellow/Red contract playbook from a folder of signed agreements, with evidence and source quotes. Exports designed Word (short and full), Excel and a PowerPoint summary.
- **playbook-workspace**: Areo Workspace | playbook: an interactive HTML workspace over the playbook model.
- **contract-negotiation-orchestrator**: applies the playbook to the counterparty's redlines on their own draft: a work file with track changes, reasoned comment bubbles and an internal layer, and a send copy derived from it after the quality gate.
- **contract-risk-assessor**: maps exposures across six lenses and produces Areo Workspace | risks.
- **negotiation-strategist**: balance of power, sequencing, concession packages, an interactive prep centre and a sparring simulation.
- **contract-drafter**: first drafts, amendments, annexes, termination and demand letters, from the client's own approved templates.
- **legal-contract-translator**: Hebrew↔English legal translation that preserves defined terms, numbering, cross-references and amounts.
- Word documents in Hebrew are automatically RTL-enforced.

Also state the privacy guarantee clearly: the user's contracts and documents are processed in
their own working environment and are NEVER uploaded to the AreoLegal service, the service only
validates the license and serves methodology content downward.

Offer to run the Organization Profile setup now.

## Step 3, Nothing runs on a schedule

**No component ever schedules work.** There is no background folder scan, no weekly sweep, no
automatic playbook update and no automatic profile refresh. Adding a file to a folder is not an
event and triggers nothing. Do not offer any of these, not even with the user's approval.

If the user asks for recurring automation, say plainly that everything runs on an explicit
request: the playbook is rebuilt when they ask for it, and the Workspace is rebuilt right after.

**A reminder is a different thing and is allowed:** a message to a person about a date, which
never changes content. Reminders are offered by the component that produced the deliverable
(a negotiation round awaiting an answer, a playbook worth refreshing), not here.

## Step 4, Workspaces

Explain that the playbook and the risk register are delivered as interactive HTML workspaces,
generated by their components automatically. No setup needed.

## Stale plugin: what "Couldn't check for updates" really means

`license_status` may return `update_message`. **Relay it once, plainly.** It means the
installed plugin is behind the published version, and, in most cases, that the
marketplace is registered under a URL that no longer resolves, so Claude's update check
returns 404 and shows only "Couldn't check for updates. Try again." Retrying never helps,
because the address itself is dead.

The fix is to remove the AreoLegal marketplace and add it back as `areolegal/claude-plugin`,
then restart. **The subscription is unaffected and nothing should be blocked**: the client
is simply running old instructions.

## Troubleshooting

- "Subscription inactive": call `license_status` and show the message; renewal is on the AreoLegal website.
- Connection errors in a chat/Cowork session: this is the sandbox, not a fault and not an unsupported environment, add the connector as described in Step 0.
- Connection errors in the Code tab: check internet access; `https://areo.co.il` must be reachable.
- Moving to a new machine: just run activation again with the same key.

## סיום כל הודעה

**כל מילה שהלקוח רואה היא בשפת הממשק שלו.** לפני פעולה, בין פעולות ואחריהן. לא רק השורה האחרונה: גם "Now let's publish this", גם "I'll wait for their response", וגם כל מחשבה שנכתבה החוצה. **שורה באנגלית בשיחה עברית נראית ללקוח כתקלה**, וזו השגיאה השכיחה ביותר.

**אין לתאר ללקוח את הנהלים שלנו.** לא "לפי הכלל של הרכיב", לא "לפי התהליך המחייב", לא "אמתין לתשובה לפני שאמשיך", ולא הסבר מה מותר או אסור לך לעשות. **הלקוח שכר תוצר משפטי, לא תיאור של איך הוא מיוצר.** עשה את הפעולה, ומסור את התוצאה.

**וכל הודעה מסתיימת בשורה המתוסרטת האחרונה שלה או בשאלה שנשאלה.** אין לסכם את התור אחריה.
