# Agent Workflow Amplifiers

Seven high-leverage skills for agent-afk that aren't bundled in core: API integration, browser automation, friction detection, provider bridging, review resolution, and agent CLI bootstrapping.

## What Changed (v3.0.0)

18 skills that shipped as duplicates of agent-afk's bundled plugin were removed. They caused a manual sync tax and silent shadowing via first-wins resolution. If you need those skills, they ship with `npm i agent-afk` (v5.x+) or can be found in [agent-afk's bundled plugin](https://github.com/griffinwork40/agent-afk/tree/main/src/bundled-plugins/awa-bundled/skills).

## Skills

| Skill | What it does |
|---|---|
| [`agentify`](skills/agentify/SKILL.md) | Bootstrap a dispatchable sub-agent skill for every coding agent CLI installed on the machine (codex, aider, cursor, etc.) |
| [`appmap`](skills/appmap/SKILL.md) | Map a web UI and generate a browser automation skill via parallel reconnaissance |
| [`forge-friction`](skills/forge-friction/SKILL.md) | Surface recurring friction patterns from session telemetry and generate targeted skill briefs |
| [`integrate`](skills/integrate/SKILL.md) | One-prompt API integration pipeline: any API (docs URL, name, or description) to working CLI wrapper + skill + tests |
| [`provideme`](skills/provideme/SKILL.md) | One-prompt provider bridge: any coding agent CLI to a local Anthropic-compatible API server (`POST /v1/messages`) |
| [`resolve`](skills/resolve/SKILL.md) | Resolve PR code review feedback by dispatching one parallel sub-agent per issue |
| [`web`](skills/web/SKILL.md) | Orchestrate parallel browser automation across independent Chrome tabs, one sub-agent per tab |

### Agents

| Agent | What it does |
|---|---|
| [`qualify`](agents/qualify.md) | Gate-keep proposed skills. Approve only real force multipliers; reject reminders, checklists, and best-practice nudges |
| [`unqualify`](agents/unqualify.md) | Remove a qualified skill that has drifted, become redundant, or broken |

## Installation

### agent-afk

```bash
afk plugin install griffinwork40/agent-framework
```

### Claude Code

```
/plugin marketplace add griffinwork40/agent-framework
/plugin install agent-workflow-amplifiers@griffinwork40-agent-framework
/reload-plugins
```

## Usage

- `/integrate stripe` — read Stripe's docs, produce a CLI wrapper + skill + tests
- `/resolve` — resolve PR review feedback in parallel, one sub-agent per issue
- `/agentify` — discover local coding agent CLIs and create dispatch skills for each
- `/web` — parallel browser automation across independent tabs
- `/forge-friction` — surface recurring friction and generate skill briefs
- `/qualify` — evaluate a proposed skill before adding it

## Friction Detection

The plugin includes a friction analysis pipeline that learns from how you work.

1. **Session telemetry** — hooks log tool calls during sessions
2. **Pattern detection** — at session end, an analyzer detects friction patterns (repeated failures, edit cycling, sequential searches that should be parallel)
3. **Cross-session aggregation** — patterns are tracked across sessions with a 28-day sliding window
4. **Threshold surfacing** — when the same friction appears in 3+ sessions, `/forge-friction` surfaces it with examples and a structured skill brief

Data stays local. All telemetry is stored under the agent framework directory.

## What Qualifies as a Skill

A skill belongs here only if it:

- changes the **shape** of the workflow (adds phases, parallelism, sub-agent dispatch)
- unlocks more of the agent's **existing** capabilities
- materially improves **one-shot** task completion
- creates a **repeatable** workflow upgrade the base agent wouldn't reliably apply by default

The `qualify` agent enforces this bar. See [`agents/qualify.md`](agents/qualify.md) for the rubric.

## License

Apache 2.0 — see [LICENSE](LICENSE).
