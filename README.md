# Agent Workflow Amplifiers

A repo of high-leverage agent skills that improve orchestration, integration, and one-shot task completion with minimal prompt overhead.

## What This Is

This repo contains compact skills for agentic workflows.

These skills are not meant to add net-new intelligence. They are meant to extract more value from capabilities the agent already has, such as planning, execution, sub-agents, validation, and tool use.

The goal is simple: small prompts, disproportionate workflow improvement.

## Core Idea

A good skill is not just a reminder.

It should do one of three things:

- act as a **force multiplier** by unlocking more of the agent's existing capabilities
- improve **one-shot completion** by increasing the odds a large task is fully completed in one pass
- do **both**

This repo is focused on high leverage per token.

## Skill Taxonomy

### Force Multipliers
Skills that improve how the agent uses its existing architecture.

### One-Shot Improvers
Skills that increase the odds a task is completed cleanly in one pass.

### Both
The highest-leverage skills. These improve internal workflow and final completion quality at the same time.

## Included Skills

### Parallelize
Transforms a linear plan into a wave-based orchestration plan for parallel sub-agents.

Use it when:
- the task is large
- work can be split into independent lanes
- structured concurrency will improve speed or quality

### Integrate
Reads API docs and converts them into an agent-usable integration surface by generating:
- a CLI wrapper
- an agent-facing skill
- usage guidance for the wrapper

Use it when:
- a new external API or service needs to be connected
- you want to turn docs into a reusable agent capability
- you want a repeatable bridge from API surface to agent workflow

### Research
Dispatches two sub-agents in parallel — one to search the web for external context, one to inspect the local codebase — then returns a merged research brief.

Use it when:
- you need both external and local context before starting a task
- you want to understand how a codebase relates to external docs or standards

### Spec
Takes an idea and transforms it into a structured spec.

Use it when:
- you have a rough idea that needs structure before implementation
- you want a clear spec to hand off to another skill like Parallelize

## Why This Exists

Most prompt collections are either too generic, too narrow, or mostly reminders for things the agent can already do.

This repo focuses on a smaller and more useful category:
reusable workflow transforms that create outsized value relative to their size.

## Installation

### From the marketplace

1. Add the marketplace inside a Claude Code session:

```
/plugin marketplace add griffinwork40/agent-framework
```

2. Install the plugin:

```
/plugin install agent-workflow-amplifiers@griffinwork40-agent-framework
```

3. Reload to activate:

```
/reload-plugins
```

### Local installation

Clone the repo and load it directly:

```bash
git clone https://github.com/griffinwork40/agent-framework.git
claude --plugin-dir ./agent-framework
```

> Requires Claude Code v1.0.33 or later.

## Usage

Use these skills when you want to shift the agent into a stronger operating mode with minimal prompt overhead.

Examples:
- use `Parallelize` after planning to restructure work into concurrent waves
- use `Integrate` when introducing a new API or service into the agent's toolset

## What Qualifies as a Skill

A skill belongs in this repo only if it does at least one of the following:

- changes the shape of the workflow
- unlocks more of the agent's existing capabilities
- materially improves one-shot task completion
- creates a repeatable workflow upgrade that the base agent would not reliably apply by default

Useful behaviors like validation, review, or TDD may still matter, but they are usually not strong enough to deserve first-class status on their own.