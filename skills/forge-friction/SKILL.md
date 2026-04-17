---
name: forge-friction
description: "Surface recurring friction from Claude Code's native telemetry and identify actionable skill opportunities. Use when the user runs /forge-friction."
---

Run the friction analyzer to get a summary of recent friction patterns:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/friction/analyzer.py"
```

If no friction sessions exist, tell the user there are no friction patterns in the lookback window.

If friction data exists, review the output. It contains friction categories ranked by frequency, each with recent examples showing `friction_detail` (what went wrong) and `goal` (what the user was trying to do).

## Your job

Read through the friction categories and their examples. For each category with 3+ sessions, analyze the `friction_detail` strings to identify **recurring themes** — specific, repeated failure modes that a skill could address.

Not all friction is fixable by a skill. Filter for themes where:
- The same failure mode repeats across multiple sessions (not one-off issues)
- A skill could change Claude's default behavior to avoid the friction
- The fix is a workflow shape change, not a reminder or checklist

Present your findings to the user:

1. **For each actionable theme**: summarize it in one line with the count, then quote 2-3 representative `friction_detail` examples. Ask: "Draft a skill brief for this? (y/n)"

2. **If the user says yes**: Output a structured skill brief for the theme (NOT an actual skill — that's a separate workflow) — a one-paragraph description of what the skill should do, the friction it addresses, and 2-3 representative examples. Also persist the brief to `~/.claude/agent-framework/briefs/<ISO8601-compact>-<theme-slug>.md` (e.g., `2026-04-17T14-30-05-wrong-approach-refactor.md`), creating the directory if needed. Use this format:

   ```markdown
   ---
   theme: <one-line theme>
   session_count: <int>
   created_at: <ISO8601>
   source: forge-friction
   ---

   <brief paragraph>

   ## Friction examples

   - <example 1>
   - <example 2>
   - <example 3>
   ```

   The user can feed the brief into their own skill creation workflow. Downstream tools in separate plugins (e.g., autonomous skill generators) can also consume the persisted briefs.

3. **If the user says no**, skip it and move on.

You can also drill into a specific category:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/friction/analyzer.py" --category wrong_approach
```

Or adjust the lookback window:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/friction/analyzer.py" --days 60
```

After processing, summarize: how many themes found, how many the user approved, how many skills generated.
