---
name: forge-friction
description: "Surface recurring friction from session telemetry and generate targeted skills. Use when the user runs /forge-friction."
argument-hint: "[--dry-run] [--auto]"
---

Run the friction analyzer to get a summary of recent friction patterns:

```bash
python3 "${PLUGIN_ROOT}/scripts/friction/analyzer.py"
```

If no friction sessions exist, tell the user there are no friction patterns in the lookback window.

If friction data exists, review the output. It contains friction categories **ranked by confidence, then frequency**, each with recent examples showing `friction_detail` (what went wrong) and `goal` (what the user was trying to do).

Tool-error categories carry a failure-class suffix. `:timeout`, `:truncated`, and `:slow` are **high-confidence** — real, specific friction a skill can address — and rank first. `:plain` is the **low-confidence residue**: a fast non-zero exit the trace cannot distinguish from a benign result (a `grep` no-match, a `test` that exits 1). It ranks last and should be treated with skepticism.

## Dry-run mode

If `$ARGUMENT` contains `--dry-run`: after the analyzer runs, identify themes using the filter criteria in "Your job" below, but instead of presenting them interactively, output a single markdown table:

| Category | Count | Example friction_detail |
|---|---|---|
| ... | N | "truncated quote 1"; "truncated quote 2" |

One row per theme. Truncate each `friction_detail` to ~80 chars. Up to 3 examples per row (semicolon-separated in the cell). If no themes pass the filter, print "No themes in lookback window."

After the table (or "no themes" line), print:

> dry-run: no /forge invocation, no telemetry written

Stop. Do NOT proceed to the y/n prompts, `/forge` dispatch, or telemetry write described in "Your job" — those are skipped entirely in dry-run.

## Auto mode

If `$ARGUMENTS` contains `--auto`: skip all y/n prompts and auto-approve all qualifying themes. For each theme that passes the filter criteria (3+ sessions, recurring failure mode, skill-addressable), immediately run `/forge` with the theme as a seed. Chain the invocations sequentially, then log telemetry for each generated skill. `--auto` respects `--dry-run` (if both flags are present, dry-run takes precedence and no /forge invocation or telemetry occurs).

## Your job

Read through the friction categories and their examples. For each category with 3+ sessions, analyze the `friction_detail` strings to identify **recurring themes** — specific, repeated failure modes that a skill could address.

Not all friction is fixable by a skill. Filter for themes where:
- The same failure mode repeats across multiple sessions (not one-off issues)
- A skill could change the agent's default behavior to avoid the friction
- The fix is a workflow shape change, not a reminder or checklist
- **Prefer high-confidence failure classes.** Pursue `:timeout` / `:truncated` / `:slow` categories first; they are real friction. Treat `:plain` categories as low-confidence — only pursue one if its `friction_detail` / `goal` examples make the recurring failure mode unmistakable.

**If `--auto` is present** in `$ARGUMENTS`:
- Auto-forge only high-confidence themes. **Skip `:plain` tool-error categories** — without human review, auto-forging the low-confidence residue produces noise skills. Pursue `:timeout` / `:truncated` / `:slow` and non-tool-error categories that pass the filter.
- For each actionable theme, immediately run `/forge` from this plugin, seeding it with: "Create a skill that addresses this recurring friction: [theme summary]. Examples: [2-3 friction_detail quotes]."
- Chain the invocations sequentially (wait for forge + qualify to complete before starting the next one).
- After each forge + qualify completes, log to telemetry (see telemetry format below).
- Do not ask for user confirmation; auto-approve all qualifying themes.

**If `--auto` is not present** (interactive mode):

1. **For each actionable theme**: summarize it in one line with the count, then quote 2-3 representative `friction_detail` examples. Ask: "Generate a skill for this? (y/n)"

2. **If the user says yes**:
   - Run `/forge` from this plugin, seeding it with: "Create a skill that addresses this recurring friction: [theme summary]. Examples: [2-3 friction_detail quotes]."
   - After forge + qualify complete, log to telemetry (see telemetry format below).

3. **If the user says no**, skip it and move on.

**Telemetry** (logged after each skill generation, same in both auto and interactive modes).

Create the telemetry directory if needed and append **one JSONL line** to the SAME file `/forge` writes to — resolve the path identically so both records land together regardless of environment:

```bash
mkdir -p "${AFK_FRAMEWORK_DIR:-${CLAUDE_CONFIG_DIR:-$HOME/.claude}/agent-framework}"
printf '%s\n' '{"timestamp": "<ISO8601>", "source": "friction", "gap": "<THEME_SUMMARY>", "theme": "<THEME_SUMMARY>", "friction_category": "<CATEGORY>", "session_count": <COUNT>, "generated_skill": "<SKILL_NAME>", "qualify_result": "<APPROVE|SALVAGE|REJECT>", "iterations": <ITERATIONS_FROM_FORGE>, "target_scope": "<user|plugin:NAME>"}' >> "${AFK_FRAMEWORK_DIR:-${CLAUDE_CONFIG_DIR:-$HOME/.claude}/agent-framework}/forge-telemetry.jsonl"
```

Substitute the bracketed values, emit compact one-line JSON, and append it with the shell redirect above (or the file-write tool). **Do NOT use `python3 -c`** — the AFK interpreter guard blocks interpreter `-c`/`-e` eval, which silently drops the record. Field notes:
- `gap` mirrors `theme` so friction records join cleanly with `/forge`'s own `generated_skill` records (which key on `gap`); keep both fields.
- `iterations`: use the actual count `/forge` reported (not a hardcoded `1`).
- `target_scope`: where the skill was written (`user` or `plugin:<name>`).
- The `${AFK_FRAMEWORK_DIR:-${CLAUDE_CONFIG_DIR:-$HOME/.claude}/agent-framework}` expression is byte-identical to the one in `/forge`'s telemetry step — do not substitute a hardcoded `~/.afk` path, which diverges from `/forge` under native Claude Code.

You can also drill into a specific category:

```bash
python3 "${PLUGIN_ROOT}/scripts/friction/analyzer.py" --category wrong_approach
```

Or adjust the lookback window:

```bash
python3 "${PLUGIN_ROOT}/scripts/friction/analyzer.py" --days 60
```

After processing, summarize: how many themes found, how many the user approved, how many skills generated.
