---
name: forge-friction
description: "Surface recurring friction from session telemetry, classify as operational vs shape-gap, and generate targeted skills for shape-gap themes only. Use when the user runs /forge-friction."
argument-hint: "[--dry-run] [--auto]"
---

Run the friction analyzer to get a summary of recent friction patterns:

```bash
python3 "${PLUGIN_ROOT}/scripts/friction/analyzer.py"
```

If no friction sessions exist, tell the user there are no friction patterns in the lookback window.

If friction data exists, review the output. It contains friction categories **ranked by confidence, then frequency**, each with recent examples showing `friction_detail` (what went wrong) and `goal` (what the user was trying to do).

Tool-error categories carry a failure-class suffix. `:timeout`, `:truncated`, and `:slow` are **high-confidence** — real, specific friction a skill can address — and rank first. `:plain` is the **low-confidence residue**: a fast non-zero exit the trace cannot distinguish from a benign result (a `grep` no-match, a `test` that exits 1). It ranks last and should be treated with skepticism. `:unclassified` comes from agent-afk session facets, which count tool errors without a failure class; treat it exactly like `:plain`. Facets also supply each example's `goal`, joined to witness traces through the session ledger's `traceLabel`.

## Dry-run mode

If `$ARGUMENTS` contains `--dry-run`: after the analyzer runs, identify, filter, and classify themes using the criteria in "Your job" below, but instead of presenting them interactively, output two sections:

**Operational** (recommendations only — not skill candidates):

| Category | Count | Recommendation |
|---|---|---|
| ... | N | PreToolUse hook / config change / budget adjustment / ... |

**Shape-gap** (forge candidates):

| Category | Count | Example friction_detail |
|---|---|---|
| ... | N | "truncated quote 1"; "truncated quote 2" |

One row per theme. Truncate each `friction_detail` to ~80 chars. Up to 3 examples per row (semicolon-separated in the cell). If neither table has any rows, print "No themes in lookback window." If only one table is empty, omit that table's header and add a `(none)` row placeholder instead.

After the table (or "no themes" line), print:

> dry-run: no /forge invocation, no telemetry written

Stop. Do NOT proceed to the y/n prompts, `/forge` dispatch, or telemetry write described in "Your job" — those are skipped entirely in dry-run.

## Auto mode

If `$ARGUMENTS` contains `--auto`: skip all y/n prompts and auto-approve all qualifying themes. For each theme classified as shape-gap in Step 2, immediately run `/forge` with the theme as a seed. Chain the invocations sequentially, then log telemetry for each generated skill. `--auto` respects `--dry-run` (if both flags are present, dry-run takes precedence and no /forge invocation or telemetry occurs).

## Your job

Read through the friction categories and their examples. For each category with 3+ sessions, analyze the `friction_detail` strings to identify **recurring themes** — specific, repeated failure modes.

### Step 1 — Filter

Not all friction is actionable. Filter for themes where:
- The same failure mode repeats across multiple sessions (not one-off issues)
- The failure mode is specific enough to act on (not a grab-bag of unrelated errors)
- **Prefer high-confidence failure classes.** Pursue `:timeout` / `:truncated` / `:slow` categories first; they are real friction. Treat `:plain` and `:unclassified` categories as low-confidence — only pursue one if its `friction_detail` / `goal` examples make the recurring failure mode unmistakable.

<!-- Note: two earlier filter bullets — "A skill could change the agent's default behavior" and "The fix is a workflow shape change" — were consolidated into Step 2 Classify (shape-gap indicators), where they fit more naturally as classification criteria rather than pre-filters. -->

### Step 2 — Classify

For each theme that passes the filter, classify it as **operational** or **shape-gap**:

**Operational** — infrastructure/tooling misbehavior, not a missing workflow. Indicators:
- Tool timeouts, slow tools, truncated output (`:timeout`, `:slow`, `:truncated` on any tool)
- Rate limits, usage limits, connection errors (`subagent_fail:RateLimitError`, `UsageLimitError`, `APIConnectionError`, `APIConnectionTimeoutError`)
- Hook blocks working as designed (`hook_block:*` categories)
- Session closures from external causes (`closure:abort`, `closure:timeout` from usage caps, network, or user signal)
- Permission errors, idle watchdog kills (`subagent_fail:PermissionDeniedError`, `IdleWatchdogError`)
- Model rejection errors (`subagent_fail:Error` from HTTP 400/404 on model ids)
- Iteration cap exhaustion from budget undersizing (`closure:iteration_cap`)

**Shape-gap** — a recurring workflow pattern agents perform without skill coverage. Indicators:
- Multiple sessions performing the same multi-step sequence ad-hoc (visible in `goal` field)
- A structural problem agents solve differently each time with no consistent approach
- Goals that consistently `partially_achieved` or `aborted` because no skill owns the workflow shape — not because tools broke
- The `friction_detail` shows the agent improvising a multi-step workaround, not a single tool failing

### Step 3 — Route

**Operational themes:** For each, emit a one-line **recommendation** — the right fix category (PreToolUse hook, config change, budget adjustment, existing skill routing fix, or infrastructure improvement). Do NOT propose `/forge` for operational themes — they are not skill candidates.

**Shape-gap themes:** These are the forge candidates. Route them through the interactive or auto flow below.

**If `--auto` is present** in `$ARGUMENTS`:
- List operational themes with their recommendations (no forge).
- Auto-forge only shape-gap themes. **Skip `:plain` and `:unclassified` tool-error categories entirely in auto mode** — without human review, the low-confidence residue produces noise.
- For each shape-gap theme, immediately run `/forge` from this plugin, seeding it with: "Create a skill that addresses this recurring workflow gap: [theme summary]. Examples: [2-3 friction_detail quotes showing the ad-hoc workaround pattern]."
- Chain the invocations sequentially (wait for forge + qualify to complete before starting the next one).
- After each forge + qualify completes, log to telemetry (see telemetry format below).
- Do not ask for user confirmation; auto-approve all qualifying shape-gap themes.

**If `--auto` is not present** (interactive mode):

1. **Operational themes first**: list each with its one-line recommendation (same `Category | Count | Recommendation` columns as dry-run). No y/n prompt — these are informational.

2. **Shape-gap themes next**: for each, summarize it in one line with the count, then quote 2-3 representative `friction_detail` examples. Ask: "Generate a skill for this? (y/n)"

3. **If the user says yes**:
   - Run `/forge` from this plugin, seeding it with: "Create a skill that addresses this recurring workflow gap: [theme summary]. Examples: [2-3 friction_detail quotes showing the ad-hoc workaround pattern]."
   - After forge + qualify complete, log to telemetry (see telemetry format below).

4. **If the user says no**, skip it and move on.

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

After processing, summarize: how many themes found, how many classified operational (with recommendations listed), how many classified shape-gap, how many approved for forge, how many skills generated.
