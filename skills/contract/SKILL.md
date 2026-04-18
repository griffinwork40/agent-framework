---
name: contract
description: "Reference convention for sub-agent I/O schemas. Loaded by orchestrator skills via /agent-workflow-amplifiers:contract and into agents (e.g., qualify) via the `skills:` field."
---

# Contract

For each sub-agent you plan to dispatch, define a schema before the call:

- `goal` — one-sentence objective
- `inputs` — data/context the sub-agent receives
- `artifacts` — named structured fields expected back (not freeform prose)
- `non_goals` — what the sub-agent must NOT do
- `failure_modes` — how to report blocked or partial work

Embed the schema at the top of every sub-agent's prompt and require results in that exact shape. Instruct each sub-agent explicitly: "Return ONLY the schema fields. No preamble, no analysis prose, no explanation — begin your response with the first schema field." When sub-agents return, validate field-by-field. If any artifact is missing, malformed, or wrapped in prose, re-dispatch only the failing sub-agent with the gap cited. Merge only schema-valid responses.

## Skip if

- Single-agent dispatch
- Sub-agents returning freeform prose where structure doesn't help merge
- Exploratory tasks where the output shape isn't known yet
