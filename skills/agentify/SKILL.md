---
name: agentify
description: "Bootstraps a dispatchable Claude sub-agent skill for every coding agent CLI installed on this machine (codex, aider, cursor, etc.). Use when the user wants to delegate tasks to locally-installed agent CLIs or expand the plugin's agent fleet."
---

## Sub-agent contract
/agent-workflow-amplifiers:contract

Dispatch one sub-agent to detect every coding agent CLI installed on this machine (scan PATH, common install dirs, and package managers; return name + version + help output for each). When it returns, dispatch parallel sub-agents — one per discovered CLI — each reading the CLI's docs and `--help` output to identify its headless execution interface, then producing a compact SKILL.md following this plugin's conventions: `name: <cli>-agent`, description that triggers on delegation requests, body that invokes the CLI with $ARGUMENT in headless mode.
