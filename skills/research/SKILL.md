---
name: research
description: "Dispatches two sub-agents in parallel to gather external and local context for the current task."
---

## Sub-agent contract
/agent-workflow-amplifiers:contract

Dispatch two sub-agents in parallel. One sub-agent researches the web for external context relevant to the current task. The other inspects the current directory for local code, files, docs, patterns, and constraints relevant to the current task. Return a concise merged research brief highlighting relevant findings, conflicts, risks, and implications for the task.
