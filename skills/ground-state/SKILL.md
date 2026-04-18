---
name: ground-state
description: "Before starting any non-trivial implementation (multi-file edits, new features, config changes, anything that writes), dispatch a parallel pre-flight reconnaissance wave to triangulate git state, project infrastructure, and prior-session memory. Produces a 5-line ground-truth snapshot that grounds the implementation and catches wrong-branch edits, assumed-no-CI, stale origin, and missed memory context before the first edit."
---

## Sub-agent contract
/agent-workflow-amplifiers:contract

Before any multi-step implementation (not single-file fixes, not pure Q&A), dispatch three parallel reconnaissance sub-agents, each with a narrow target:

**Git surveyor**
Return: current branch, `git log --oneline -5`, `git status -s`, diff-summary vs `origin/<default-branch>`, stash list. Flag: diverged, uncommitted changes, stale upstream.

**Infrastructure surveyor**
Scan the project for: CI configs (`.github/workflows/`, `.gitlab-ci.yml`, `Jenkinsfile`), package scripts (`package.json`, `Makefile`, `pyproject.toml`), existing linters/formatters, and authoritative config file locations relevant to the task (e.g., `~/.claude.json` vs `~/.claude/settings.json` when the task touches Claude config). Return 5-bullet inventory.

**Memory surveyor**
Grep the user's auto-memory store (`~/.claude/projects/-<cwd-slug>/memory/`) + any project CLAUDE.md for keywords from the user's current request. Return relevant memory file pointers with 1-line summaries, or "no relevant memory found."

**Synthesize** into a 5-line ground-truth snapshot:
- Branch: `<current>`, `<clean|diverged>`, upstream: `<fresh|stale>`
- Recent work: last 3 commits or stash items
- Infrastructure: CI present? package scripts? authoritative configs for this task
- Memory hits: file refs or "none"
- Implementation risks: e.g. "branch is `main`, don't edit directly"; "CI runs on push"; "memory says prior attempt used approach X"

Surface the snapshot. Implementation then uses these verified facts — not assumptions.

**Skip when:**
Task is Q&A only; single-line fix on an already-identified file; user says "skip pre-flight".
