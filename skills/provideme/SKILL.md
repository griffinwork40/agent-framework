---
name: provideme
description: "One-prompt provider bridge. Takes any coding agent CLI (name, docs URL, or install steps) and produces a modular local API server compatible with Claude Code via Anthropic: POST /v1/messages. Includes a {provider}-claude launcher."
argument-hint: "<CLI name, docs URL, or install steps>"
---

## Sub-agent contract
!`awk ‘/^---$/{c++; next} c>=2’ "${CLAUDE_SKILL_DIR}/../contract/SKILL.md"`

Dispatch parallel sub-agents:
1. **Research agent**: investigate the $ARGUMENT provider CLI — installation, invocation syntax, streaming support, output format, authentication/config requirements.
2. **Inspection agent**: scan local codebase for patterns in provider CLI invocation, argument passing, and streaming implementations.

When they return, create a plan for orchestrating parallel implementation waves:
- **Wave 1 (Parallel)**: provider adapter module + core normalization module + `/v1/messages` handler
- **Wave 2 (Parallel)**: `/health` endpoint + error mapping + request validation
- **Wave 3 (Sequential)**: `{provider}-claude` launcher script + README with smoke test + integration instructions

Then dispatch implementation sub-agents for each module. After all implementations complete, return setup instructions with Claude Code env var configuration and smoke test commands.

See `references/anthropic-bridge-spec.md` for Anthropic protocol requirements, modular architecture constraints, hard requirements (secrets, validation, streaming), and Claude Code integration checklist.
