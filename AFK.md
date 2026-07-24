# AFK.md

System prompt for AFK sessions in this repository.

## What This Is

A Claude Code plugin (`agent-workflow-amplifiers`, repo `agent-framework`) containing high-leverage **skills** and **agents** that improve multi-agent orchestration, API integration, parallel execution, and one-shot task completion. Installed via the `.claude-plugin/plugin.json` manifest. There is **no build step, no test suite, and no runtime dependency graph** — each skill is a single `SKILL.md` (YAML frontmatter + markdown body), and the only executable code is a Python friction analyzer.

## Commands

No `package.json`, `Makefile`, or compiler. Work happens through slash commands, the friction analyzer, and the release flow.

```bash
# Friction analysis (reads ~/.claude telemetry, surfaces recurring patterns)
python3 scripts/friction/analyzer.py

# Release: handled by release-please via conventional commits — no manual version bump.
# Merging Conventional Commits to main opens/updates a release PR that bumps
# CHANGELOG.md and syncs $.version in .claude-plugin/plugin.json automatically.
```

**Slash commands** (the plugin's real entry points):

| Command | Purpose |
|---|---|
| `/integrate <API>` | API docs/name/desc → CLI wrapper + skill + tests |
| `/research` | Parallel web + codebase research brief |
| `/spec "<idea>"` | Loose idea → structured spec |
| `/ground-state` | Pre-flight recon (git + infra + memory) before non-trivial work |
| `/ship` | Already-done work → tests → commit → push → PR |
| `/resolve` | Resolve PR review feedback, one sub-agent per issue |
| `/qualify` | Gate a proposed skill against the force-multiplier bar |
| `/unqualify <name> reason="..."` | Remove a drifted skill, logged to the ledger (dry-run first) |

## Architecture

| Path | Purpose |
|---|---|
| `.claude-plugin/plugin.json` | Plugin manifest (name, version, author, license) — version auto-synced by release-please |
| `.claude-plugin/marketplace.json` | Marketplace listing |
| `skills/<name>/SKILL.md` | 13 skills: `agentify`, `appmap`, `automate`, `contract`, `forge-friction`, `ground-state`, `integrate`, `provideme`, `research`, `resolve`, `ship`, `spec`, `web` |
| `agents/` | `qualify.md` (skill gate-keeper), `unqualify.md` (logged removal) |
| `commands/` | `/qualify` and `/unqualify` slash-command dispatchers |
| `hooks/hooks.json` | Plugin hooks (currently empty `{}`) |
| `scripts/friction/analyzer.py` | Reads Claude Code native telemetry → surfaces friction patterns |
| `.github/workflows/` | `claude.yml`, `claude-code-review.yml`, `release-please.yml` |

**Skill anatomy.** Most skills are a few lines of prompt that change the *shape* of the workflow — adding phases, parallelism, or sub-agent dispatch. Orchestrator skills (`integrate`, `research`, `web`, `resolve`, `agentify`) dispatch sub-agents and merge their output; each loads the I/O schema convention via `/contract` (`skills/contract/SKILL.md`).

## Conventions

- **Skills are force multipliers, not reminders.** A skill must change the *shape* of the workflow, unlock existing agent capabilities, or materially improve one-shot completion. Reminders, checklists, and best-practice nudges are rejected. Run every proposed skill through `/qualify` before adding it.
- **Skill files:** `skills/<name>/SKILL.md` with YAML frontmatter `name` (hyphen-case, must match the directory name), `description` (controls auto-invocation — be specific), and optional `argument-hint`.
- **Agent files:** `agents/<name>.md`, same frontmatter convention plus optional `model:` (e.g. `sonnet`) and `skills:` (preloads skills into the agent's context).
- **High leverage per token.** Keep skills compact — small prompt, disproportionate workflow improvement.
- **Conventional Commits required.** Release automation (release-please) parses commit messages to compute the next version and changelog. Use `feat:`, `fix:`, `chore:`, etc. Do **not** hand-edit the version in `plugin.json`.
- **When adding a skill:** create the `SKILL.md`, pass `/qualify`, and add a row to the skill table in `README.md`.
- **Local-only files** (gitignored): `cli-guard/`, `__pycache__/`, `progress.md`, `todo.md`, `.cursor/`. All friction telemetry stays local under `~/.claude/agent-framework/`.

## License

Apache 2.0 — see `LICENSE`.
