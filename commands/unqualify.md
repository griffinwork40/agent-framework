---
description: Remove a qualified skill from this plugin and log the removal to the ledger.
argument-hint: "<skill-name> reason=\"<why>\""
---

Dispatch the `unqualify` agent via the Agent tool with `subagent_type: unqualify`, passing $ARGUMENTS as the skill name and removal reason.

The agent runs dry-run by default — it returns a proposed removal plan with skill metadata, reason, planned actions, and known risks. Surface that plan to the user and ask for explicit confirmation before proceeding. On confirmation, re-dispatch the agent with `$ARGUMENTS --confirm` appended to perform the destruction.

If $ARGUMENTS is empty, missing a skill name, or missing a reason, ask the user to supply both before dispatching.
