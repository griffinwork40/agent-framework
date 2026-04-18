---
name: integrate
description: "One-prompt API integration pipeline. Takes any API (docs URL, name, or description) and produces a working CLI wrapper + skill + tests."
argument-hint: "<API name, docs URL, or description>"
---

## Sub-agent contract
/agent-workflow-amplifiers:contract

Send parallel sub-agents to research the $ARGUMENT API docs and create a reference file(s) in markdown. When they return, send another subagent to make a plan to orchestrate waves of parallel subagents to build and test a lightweight CLI wrapper for the $ARGUMENT API using TDD and modular files. It also needs to create a skill so Claude knows how to use the CLI.
