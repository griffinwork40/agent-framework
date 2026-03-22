---
name: qualify
description: Gate proposed plugin skills. Approve only real force multipliers. Reject reminders, checklists, best-practice nudges, and generic execution advice.
---

# Qualify

Evaluate whether a proposed skill truly deserves top-level status in this plugin.

This plugin only contains **force multipliers**: compact, reusable prompts that unlock disproportionate workflow uplift from capabilities the agent already has.

Reject anything that is mainly:
- a reminder
- a checklist
- a quality nudge
- a best-practice instruction
- a subordinate behavior
- something the base agent can already infer reliably

## Required analysis

For the candidate:

1. Infer its true purpose
2. Identify the default failure mode it fixes
3. Identify the latent machinery it exploits
4. Apply the hard gate:
   - compactness
   - outsized uplift
5. Score from 1-5 on:
   - leverage
   - architecture awareness
   - generality
   - non-default value
   - workflow impact
   - missability
6. Run rejection checks
7. Decide:
   - APPROVE
   - SALVAGE
   - REJECT
8. If not approved, state where it belongs instead
9. If SALVAGE, rewrite it into a stronger force multiplier

## Output format

### Candidate
- Name:
- Raw idea:
- Inferred purpose:
- Default failure it fixes:
- Latent machinery exploited:

### Hard gate
- Compactness: PASS or FAIL
- Outsized uplift: PASS or FAIL

### Rubric
- Leverage: X/5
- Architecture Awareness: X/5
- Generality: X/5
- Non-default Value: X/5
- Workflow Impact: X/5
- Missability: X/5
- Total: X/30

### Rejection checks
- Reminder-like: Yes/No
- Checklist-like: Yes/No
- Best-practice nudge: Yes/No
- Subordinate behavior: Yes/No
- Better as normal prompting: Yes/No
- Better folded into another skill: Yes/No

### Decision
- APPROVE, SALVAGE, or REJECT

### Reasoning

### Placement

### Rewrite
Include only if SALVAGE.

Be skeptical by default. Protect the plugin from fluff.
