# Agent Workflow Amplifiers (AWAs)

A Claude Code plugin of high-leverage skills that improve orchestration, integration, and one-shot task completion with minimal prompt overhead.

## What This Is

This repo contains compact skills for agentic workflows.

These skills are not meant to add net-new intelligence. They are meant to extract more value from capabilities the agent already has — planning, execution, sub-agents, validation, and tool use.

The goal is simple: small prompts, disproportionate workflow improvement.

## Why This Exists

AI coding agents are good out of the box. They read files, write code, run tests. But left to their own defaults, they work linearly — one hypothesis at a time, one file at a time, one pass. The failure mode isn't stupidity. It's underutilization. The agent has sub-agent dispatch, parallel execution, isolated worktrees, web search, and browser automation available. It almost never uses them together without being told to.

That's the gap this plugin fills. Each skill here is a small, structured prompt that changes the *shape* of how the agent works — not what it knows, but how it moves. Pre-flight recon before editing. Parallel research across web and codebase simultaneously. One-prompt API integrations that chain sub-agents through a full build pipeline. Friction detection that turns recurring pain into permanent solutions.

The design constraint is intentional: high leverage per token. A skill that takes 200 tokens of prompt and saves 30 minutes of manual orchestration is worth keeping. A skill that reminds the agent to write tests is not. The `qualify` agent enforces this bar on every addition.

## Core Idea

A good skill is not just a reminder. It should do one of three things:

- act as a **force multiplier** by unlocking more of the agent's existing capabilities
- improve **one-shot completion** by increasing the odds a large task is fully completed in one pass
- do **both**

This repo is focused on high leverage per token.

## Included Skills & Agents

Every skill is a single `SKILL.md`. The `description` field controls when Claude auto-invokes it — see each file for the full body.

### Skills

| Skill | What it does |
|---|---|
| [`agentify`](skills/agentify/SKILL.md) | Bootstraps a dispatchable sub-agent skill for every coding agent CLI installed on the machine (codex, aider, cursor, etc.). |
| [`appmap`](skills/appmap/SKILL.md) | Maps a web UI and generates a Claude skill to automate it via parallel orchestration. |
| [`automate`](skills/automate/SKILL.md) | Sets up a cron/launchd job to run Claude headlessly and send results to Telegram. |
| [`contract`](skills/contract/SKILL.md) | Reference convention for sub-agent I/O schemas. Loaded by orchestrator skills via `/agent-workflow-amplifiers:contract` and into agents via `skills:` field. |
| [`forge-friction`](skills/forge-friction/SKILL.md) | Surfaces recurring friction patterns detected across sessions and identifies actionable skill opportunities. |
| [`ground-state`](skills/ground-state/SKILL.md) | Before any non-trivial implementation, dispatches a parallel recon wave (git + infrastructure + memory) that produces a 5-line ground-truth snapshot to prevent wrong-branch edits, assumed-no-CI, and missed memory context. |
| [`integrate`](skills/integrate/SKILL.md) | One-prompt API integration pipeline. Any API (docs URL, name, or description) → working CLI wrapper + skill + tests. |
| [`provideme`](skills/provideme/SKILL.md) | One-prompt provider bridge. Any coding agent CLI → local Anthropic-compatible API server (`POST /v1/messages`) with a `{provider}-claude` launcher. |
| [`research`](skills/research/SKILL.md) | Dispatches two sub-agents in parallel — one to search the web, one to inspect the local codebase — and returns a merged research brief. |
| [`resolve`](skills/resolve/SKILL.md) | Resolves PR code review feedback by dispatching one parallel sub-agent per issue. |
| [`spec`](skills/spec/SKILL.md) | Transforms a loose idea into a structured, actionable spec ready for implementation. |
| [`web`](skills/web/SKILL.md) | Orchestrates parallel browser automation across independent Chrome tabs, one sub-agent per tab. |

### Agents

| Agent | What it does |
|---|---|
| [`qualify`](agents/qualify.md) | Gate-keeps proposed skills. Approves only real force multipliers; rejects reminders, checklists, and best-practice nudges. |

## Installation

### From the marketplace

Inside a Claude Code session:

```
/plugin marketplace add griffinwork40/agent-framework
/plugin install agent-workflow-amplifiers@griffinwork40-agent-framework
/reload-plugins
```

### Local installation

```bash
git clone https://github.com/griffinwork40/agent-framework.git
claude --plugin-dir ./agent-framework
```

> Requires Claude Code v1.0.33 or later.

## Usage

Examples:

- `/integrate stripe` — read Stripe's docs, produce a CLI wrapper + skill + tests.
- `/research` — before starting a task, get web + codebase context in one shot.
- `/spec "idea in one sentence"` — turn an idea into a scoped plan.
- `/resolve` — resolve PR review feedback in parallel, one sub-agent per issue.
- `/ground-state` — pre-flight recon before any non-trivial implementation.
- `/qualify` — evaluate a proposed skill before adding it.
- `/unqualify` — remove a qualified skill that has drifted and log the removal.

## Friction Detection

The plugin includes a friction analysis pipeline that learns from how you work.

**How it works:**

1. **Session telemetry** — hooks automatically log every tool call during your Claude Code sessions
2. **Pattern detection** — at session end, an analyzer detects friction patterns (repeated failures, edit cycling, sequential searches that should be parallel)
3. **Cross-session aggregation** — patterns are tracked across sessions with a 28-day sliding window
4. **Threshold surfacing** — when the same friction appears in 3+ sessions, `/forge-friction` surfaces it with examples and a structured skill brief

The result: recurring pain points are identified and documented, ready to be turned into permanent solutions.

**Data stays local.** All telemetry is stored in `~/.claude/agent-framework/` — session transcripts are deleted after analysis, only aggregated pattern signatures persist.

## What Qualifies as a Skill

A skill belongs in this repo only if it does at least one of:

- changes the **shape** of the workflow (adds phases, parallelism, sub-agent dispatch)
- unlocks more of the agent's **existing** capabilities
- materially improves **one-shot** task completion
- creates a **repeatable** workflow upgrade the base agent wouldn't reliably apply by default

Useful behaviors like validation, review, or TDD may still matter, but they are usually not strong enough to deserve first-class status on their own. The `qualify` agent enforces this bar — see [`agents/qualify.md`](agents/qualify.md) for the rubric.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). New skills are expected to pass the `qualify` gate before submission.

## License

Apache 2.0 — see [LICENSE](LICENSE).
