# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## What This Is

A plugin (`agent-workflow-amplifiers`) containing 7 high-leverage skills that complement agent-afk's bundled set. As of v3.0.0, skills that duplicated agent-afk's bundled plugin were removed. This repo contains only skills unique to the plugin.

## Repository Structure

```
.claude-plugin/
  plugin.json                  # Plugin manifest (name, version) — version auto-synced by release-please
  marketplace.json             # Marketplace listing
agents/
  qualify.md                   # Gate-keeper agent: approves/rejects proposed skills
  unqualify.md                 # Removal agent: dry-run plan then confirmed destruction
commands/
  qualify.md                   # /qualify slash command
  unqualify.md                 # /unqualify slash command
skills/
  agentify/SKILL.md            # Bootstrap sub-agent skills for locally-installed coding agent CLIs
  appmap/SKILL.md              # Map a web UI and generate a browser automation skill
  forge-friction/SKILL.md      # Surface friction patterns and generate skill briefs
  integrate/SKILL.md           # API docs to CLI wrapper + skill + tests pipeline
  provideme/SKILL.md           # Any coding-agent CLI to local Anthropic-compatible /v1/messages bridge
  resolve/SKILL.md             # Resolve PR code review feedback via parallel sub-agents
  web/SKILL.md                 # Parallel browser automation across independent Chrome tabs
hooks/
  hooks.json                   # Plugin hooks (currently empty)
scripts/
  friction/
    analyzer.py                # Ranks friction from agent-afk facets + witness traces
    afk_facets.py              # agent-afk SessionFacet source
```

No build steps or dependencies. Each skill is a single `SKILL.md` with YAML frontmatter (`name`, `description`, optional `argument-hint`) and a markdown body.

## Releases

Versioning is automated by **release-please**. Use **Conventional Commits** (`feat:`, `fix:`, `chore:`). Do **not** hand-edit the version in `plugin.json`.

## Skill Design Principles

- A skill must **change workflow shape**, **unlock existing agent capabilities**, or **materially improve one-shot completion**.
- Skills should be compact: high leverage per token.
- Skills that orchestrate sub-agents (`integrate`, `web`, `resolve`, `agentify`) should define what each sub-agent does and how results merge.
- Run proposed skills through `/qualify` before adding.

## How Skills Are Invoked

- `/integrate <API>` — pass an API name, docs URL, or description
- `/resolve` — resolve PR review feedback in parallel
- `/forge-friction` — review friction patterns and generate skill briefs
- `/agentify` — discover local coding agent CLIs and create dispatch skills
- `/appmap <url>` — map a web UI and generate an automation skill
- `/web` — parallel browser workflows across tabs
- `/provideme <CLI>` — bridge a coding agent CLI to Anthropic API format
- `/qualify` — evaluate a proposed skill against the force-multiplier bar
- `/unqualify <name> reason="..."` — remove a drifted skill

## Adding a New Skill

Create `skills/<skill-name>/SKILL.md`:

```yaml
---
name: <skill-name>
description: "<when the agent should auto-invoke this skill>"
---

<instructions for what the agent should do when triggered>
```

- `name` must be hyphen-case and match the directory name.
- Run through `/qualify` before adding.
- Update `README.md` with a table entry.
