---
name: spec
description: "Takes a loose idea and transforms it into a structured, actionable spec ready for implementation. Use when the user passes an idea, feature request, or problem description that needs scoping before building."
argument-hint: "<idea or feature request>"
---

Dispatch two sub-agents in parallel. One researches the web for prior art, APIs, and patterns relevant to $ARGUMENT. The other inspects the local codebase for conventions, dependencies, and integration points. When both return, synthesize a concise spec covering: problem, goals, non-goals, approach, key decisions, interface, file plan, test plan, and open questions. Present to the user for confirmation before proceeding.
