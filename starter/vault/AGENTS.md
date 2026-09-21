# Working in this setting vault

These instructions apply to an installed vault with `armarium.json` beside this
file. When editing this file in Armarium's starter source, follow the toolkit
repository's root `AGENTS.md` instead.

Read `armarium.json` and `Vault Guide.md` before editing. Confirm the target
campaign explicitly when more than one is present. Use `templates/` as the page
structure; these are user-owned files and may have been customized.

- Keep shared world information in `world/` and campaign records in `campaigns/<id>/`.
- Preserve other campaigns' state on shared entities. Use fully qualified links
  when a filename could be ambiguous.
- Treat clues as candidate facts, not automatically established canon. An abandoned
  candidate may never become true. Do not embellish unknown details.
- Separate preparation from actual play. Do not infer an appearance from a mention.
- Review proposed Events with the GM. Clarification answers alone do not authorize
  downstream updates: show corrected text and obtain an explicit go-ahead. Derive
  entity records from the final session account and propagate later corrections.
- Preserve raw inputs. Marking something processed does not authorize deleting it.
- If the vault uses Git, work on a branch and submit changes for GM review through
  a PR; do not commit directly to main or merge on the GM's behalf.

This starter does not install shared skills or executable utilities. Do not assume
that an `armarium` command or host-specific skill installation exists. Do not edit
a shared toolkit checkout to apply a vault-specific preference.
