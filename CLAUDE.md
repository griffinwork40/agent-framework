# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Claude Code plugin (`agent-framework`) containing high-leverage skills that improve multi-agent orchestration, API integration, and one-shot task completion. Installed via the `.claude-plugin/plugin.json` manifest.

## Repository Structure

```
.claude-plugin/plugin.json   # Plugin manifest (name, version, author)
skills/
  parallelize/SKILL.md       # Transforms a plan into parallel sub-agent waves
  integrate/SKILL.md          # One-prompt API → CLI wrapper + skill + tests pipeline
  research/SKILL.md           # Parallel web + local codebase research brief
  spec/SKILL.md               # Idea → structured spec (minimal, needs content)
```

There are no build steps, tests, or dependencies. Each skill is a single `SKILL.md` with YAML frontmatter (`name`, `description`) and a markdown body containing the skill instructions.

## Skill Design Principles

- A skill must change workflow shape, unlock existing agent capabilities, or materially improve one-shot completion. Mere reminders or generic advice don't qualify.
- Skills should be compact — high leverage per token. The `description` field controls when Claude auto-invokes the skill, so it must be specific.
- Skills that orchestrate sub-agents (parallelize, integrate, research) should clearly define what each sub-agent does and how results merge.

## How Skills Are Invoked

- `/parallelize` — run after finishing a plan in plan mode
- `/integrate <API>` — pass an API name, docs URL, or description as the argument (`$ARGUMENT`)
- `/research` — dispatches automatically based on task context
- `/spec` — pass an idea to structure

## Adding a New Skill

Create `skills/<skill-name>/SKILL.md` with this structure:

```yaml
---
name: <skill-name>
description: "<when Claude should auto-invoke this skill>"
---

<instructions for what Claude should do when the skill is triggered>
```

The `name` must be hyphen-case and match the directory name.
