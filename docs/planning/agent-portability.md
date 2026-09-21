# Agent portability and optional model API support

## Confirmed requirements

- Support both Claude Code and Codex at minimum.
- Aim for broad drop-in portability across coding agents that support skills.
- Investigate portability as its own work item rather than choosing a single host
  during initial product planning.
- If general-purpose scripts that call model APIs are retained, consider their
  provider portability separately from interactive agent support.

## Scope

Design how shared skills, instructions, and supporting resources are discovered,
installed, and invoked by different agents. Identify which workflow behavior can
be shared and which requires host-specific integration. This is a design task;
no assumption is made that hosts offer identical skill or orchestration features.

Coordinate with the distribution and update design. Favor one maintained source
for common workflow instructions, with host-specific material only where needed.
Do not require a universal agent framework or a provider abstraction before the
inventory demonstrates a need.

## Acceptance criteria

- Inventory host-dependent behavior in candidate skills: discovery, instruction
  precedence, supporting-file paths, tool invocation, review checkpoints,
  delegation, hooks, and any scheduling or persistence requirements.
- Consult current official documentation and record a compatibility matrix for
  Claude Code and Codex. Distinguish verified support, adaptation needed, and
  optional features. Identify a practical route for adding other skill-capable
  coding agents without promising unverified compatibility.
- Specify installation, invocation, local customization, and update behavior for
  both required hosts, including coexistence in the same vault.
- Define shared skill content and any necessary host-specific integration. Explain
  behavior when an optional host capability is unavailable.
- Define equivalent-workflow acceptance scenarios on both hosts using original
  sample content: selecting a campaign, preparing or processing session notes,
  resolving uncertainty with the GM, and invoking validation. Compare behavior
  and required artifacts, not identical generated prose.
- Inventory model API calls in scripts proposed for extraction. If any are kept,
  specify the initial provider scope, model and credential configuration, optional
  dependency boundaries, explicit invocation of paid work, and test strategy.
  Record deliberate deferrals; neither agent-host support nor an installed coding
  agent should imply support for that vendor's model API.
- Keep deterministic setup and validation usable without model API credentials.
- Document findings and create bounded implementation follow-ups where needed.

## Dependencies

Coordinate with [distribution, customization, and updates](https://github.com/willbradshaw/armarium/issues/2).
This design informs skill extraction, the starter setup, and any retained scripts
that make model API calls.
