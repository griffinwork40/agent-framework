---
name: appmap
description: "Map a web UI and generate a Claude automation skill via parallel reconnaissance, synthesis, and iterative validation."
argument-hint: "<URL or app description>"
---

## Sub-agent contract
!`awk '/^---$/{c++; next} c>=2' "${CLAUDE_SKILL_DIR}/../contract/SKILL.md"`

**Wave 1 (parallel):** Dispatch two sub-agents. One maps the $ARGUMENT UI in Chrome: navigation structure, key pages/forms, interaction patterns, CSS selectors, and automatable workflows. The other researches $ARGUMENT's public API, docs, authentication, rate limits, and architectural patterns. Both return structured findings.

**Synthesis:** Merge Wave 1 outputs into a skill plan: list of automatable workflows (with interaction patterns and selectors), recommended API calls to supplement UI workflows, and implementation priorities.

**Wave 2 (parallel):** For each top-priority workflow, dispatch a sub-agent to implement it in the generated skill and unit-test it against the live UI. Agents operate in isolated tabs and return pass/fail results per workflow.

**Verification:** One final sub-agent runs the complete generated skill end-to-end against $ARGUMENT, validating all workflows together. If any workflow fails, re-dispatch failing workflow agents in Wave 2 and re-verify (max 2 retries; after that, report partial results with failing workflows noted).
