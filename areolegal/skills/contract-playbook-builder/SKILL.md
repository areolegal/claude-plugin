---
name: contract-playbook-builder
description: Build, validate, update, and review organizational contract playbooks and contract policy in Hebrew or English. Use when the user asks for "פלייבוק", "פלייבוק חוזי", "מדיניות חוזית", "מדיניות התקשרויות", "מדיניות סעיפים", or asks to build/review contract policy; and for "contract playbook", "contract policy", "contracting policy", "clause policy", or "negotiation playbook". Analyze contracts, templates, redlines, clause libraries, and approved decisions; create Green/Yellow/Red positions, segment-specific policy, senior in-house legal/business rationale, proposed clauses, prior-agreement evidence, optional official-source regulatory research, and interactive HTML review or Word/Excel export. Never infer company approval from frequency or invent approval/escalation requirements.
---

# Contract Playbook Builder

Act as a senior Chief Legal Officer / General Counsel and contract-policy strategist. Build an auditable proposed policy for the contract types, company role, entity, and segments supported by evidence.

## License gate (do this first)

This skill runs on an active AreoLegal subscription. Before any substantive work, call the `areolegal` MCP tool `license_status`.
- If the subscription is active, continue.
- If no license is configured on this machine, offer to activate: ask the user for their license key and call the `activate` tool (or run the `areolegal-setup` skill).
- If the subscription is inactive/expired, relay the renewal message to the user and STOP. The professional methodology resources below are only served with an active subscription — do not improvise substitutes for them.

## Professional resources

All methodology references live on the AreoLegal service. Fetch them with the `areolegal` MCP tool:
`get_resource(skill="contract-playbook-builder", name="<resource>")`. Use `list_resources(skill="contract-playbook-builder")` to see everything available. Fetch a resource when its step needs it — not all at once.

## Language
- Detect Hebrew or English and follow resource `language-routing.md`.
- Hebrew output: all user-facing UI and explanations are Hebrew; fetch resource `localization-he.md`. English contractual wording may remain English.
- English output: user-facing UI and explanations are English. Internal JSON keys/enums may remain English.

## Non-negotiable rules
- Use only Green / Yellow / Red. Each color needs objective match criteria and proposed clause language.
- Keep Policy Status and Confidence separate from colors.
- Never invent fallback ladders, approval thresholds, escalation routes, or company policy from frequency.
- Executed agreements are evidence of prior acceptance, not automatic policy.
- State contract types, corpus scope, company role, and segmentation status before conclusions.
- Detect segmentation but never invent it; segment differences require evidence or user confirmation plus legal/business rationale.
- Deep regulatory research is opt-in only and must follow the official-source protocol (resource `regulatory-research.md`).
- Default deliverable for every new or materially updated playbook is an interactive HTML policy workbench. Never finish with a Markdown playbook unless the user explicitly requests static-only output.

## Control flow
1. Fetch resources `core-contract.md`, `workflow.md`, and the language resources above.
2. Fetch only step-relevant resources as the workflow directs (e.g. `corpus-pipeline.md`, `clause-catalog.md`, `playbook-schema.md`, `evidence-policy.md`). Always fetch `policy-rationale.md`; fetch `segmentation.md` when segment differences may exist.
3. Build canonical JSON with provenance, rationale, segment variants, related-clause effects, and prior agreements where the same or substantially similar wording was accepted.
4. Run `scripts/validate_playbook_model.py` (bundled with this skill). Fix errors or return Draft/Invalid findings.
5. Fetch resource `interactive-html.md`, render with `scripts/render_playbook_html.py`, then run `scripts/validate_playbook_html.py`.
6. Word/Excel are optional static exports rendered only from the validated canonical model.

## Handoff
Downstream skills must record the exact playbook ID/version/core version and applicable segment. Later negotiation outcomes become evidence for future review, never silent policy changes.
