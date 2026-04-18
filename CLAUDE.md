# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Claude Code plugin (`agent-workflow-amplifiers`) containing high-leverage skills and agents that improve multi-agent orchestration, API integration, and one-shot task completion. Installed via the `.claude-plugin/plugin.json` manifest.

## Repository Structure

```
.claude-plugin/
  plugin.json                  # Plugin manifest (name, version, author, license)
  marketplace.json             # Marketplace listing
agents/
  qualify.md                   # Gate-keeper agent: approves/rejects proposed skills
commands/
  qualify.md                   # /qualify slash command — dispatches the qualify agent
skills/
  agentify/SKILL.md            # Bootstraps sub-agent skills for each locally-installed coding agent CLI
  appmap/SKILL.md              # Map a web UI → create a Claude skill to automate it
  automate/SKILL.md            # Cron/launchd-driven headless Claude runs → Telegram summaries
  contract/SKILL.md            # Sub-agent I/O schema reference (loaded by orchestrator skills via /agent-workflow-amplifiers:contract; also preloaded into agents via `skills:` field)
  forge-friction/SKILL.md      # Surface friction patterns and identify actionable skill opportunities
  ground-state/SKILL.md        # Pre-implementation recon wave (git + infra + memory) → 5-line ground-truth snapshot
  integrate/SKILL.md           # API docs → CLI wrapper + skill + tests pipeline
  provideme/SKILL.md           # Any coding-agent CLI → local Anthropic-compatible /v1/messages bridge
  research/SKILL.md            # Parallel web + local codebase research brief
  resolve/SKILL.md             # Resolve PR code review feedback via parallel sub-agents
  spec/SKILL.md                # Idea → structured spec
  web/SKILL.md                 # Parallel browser automation across independent Chrome tabs
hooks/
  hooks.json                   # Plugin hooks (currently empty)
scripts/
  friction/
    analyzer.py                # Reads Claude Code native telemetry to surface friction patterns
```

There are no build steps, tests, or dependencies. Each skill is a single `SKILL.md` with YAML frontmatter (`name`, `description`) and a markdown body. Agents live under `agents/` and follow the same frontmatter convention plus optional `model:` and `skills:` fields.

## Skill Design Principles

- A skill must **change workflow shape**, **unlock existing agent capabilities**, or **materially improve one-shot completion**. Mere reminders or generic advice don't qualify.
- Skills should be compact — high leverage per token. The `description` field controls when Claude auto-invokes the skill, so it must be specific.
- Skills that orchestrate sub-agents (`integrate`, `research`, `web`, `resolve`, `agentify`) should clearly define what each sub-agent does and how results merge. Each includes `## Sub-agent contract\n/agent-workflow-amplifiers:contract` which loads `skills/contract/SKILL.md` into context at invocation time.
- Run proposed skills through the `qualify` agent before adding them. See [`agents/qualify.md`](agents/qualify.md) for the rubric and decision thresholds.

## How Skills & Agents Are Invoked

- `/integrate <API>` — pass an API name, docs URL, or description as the argument
- `/research` — dispatches automatically based on task context, or invoke directly
- `/spec <idea>` — pass a loose idea to structure
- `/forge-friction` — review friction-detected patterns and generate skill briefs
- `/qualify` — evaluate a proposed skill against the force-multiplier bar
- `/appmap <url>` — map a web UI and generate an automation skill
- `/web` — parallel browser workflows across tabs
- `/resolve` — resolve PR review feedback in parallel
- `/ground-state` — pre-flight recon before non-trivial implementations

## Adding a New Skill

Create `skills/<skill-name>/SKILL.md`:

```yaml
---
name: <skill-name>
description: "<when Claude should auto-invoke this skill>"
---

<instructions for what Claude should do when the skill is triggered>
```

- `name` must be hyphen-case and match the directory name.
- Run the draft through `/qualify` before adding.
- Update `README.md` with a table entry describing the new skill.

## Adding a New Agent

Create `agents/<agent-name>.md`:

```yaml
---
name: <agent-name>
description: "<when to invoke this agent>"
model: sonnet              # optional
skills: [contract, ...]    # optional; preloads skills into the agent's context
---

<agent system prompt / instructions>
```
