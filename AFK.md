# AFK.md

System prompt for AFK sessions in this repository.

## What This Is

A plugin (`agent-workflow-amplifiers`, repo `agent-framework`) containing 7 high-leverage **skills** that complement agent-afk's bundled set. Focused on API integration, browser automation, friction detection, provider bridging, review resolution, and agent CLI bootstrapping. Installed via `.claude-plugin/plugin.json`. There is **no build step and no runtime dependency graph**: each skill is a single `SKILL.md` (YAML frontmatter + markdown body), and the only executable code is a Python friction analyzer.

`contract` is a shared primitive loaded by orchestrator skills via `/contract` — it is not a user-facing skill and is not counted in the 7.

As of v3.0.0, 17 skills that duplicated agent-afk's bundled plugin were removed. Those skills ship with `npm i agent-afk`.

## Commands

No `package.json`, `Makefile`, or compiler. Work happens through slash commands, the friction analyzer, and the release flow.

```bash
# Friction analysis (reads agent-afk facets + witness traces)
python3 scripts/friction/analyzer.py
python3 -m pytest scripts/friction   # analyzer tests

# Release: handled by release-please via conventional commits.
```

**Slash commands** (the plugin's entry points):

| Command | Purpose |
|---|---|
| `/integrate <API>` | API docs/name/desc to CLI wrapper + skill + tests |
| `/resolve` | Resolve PR review feedback, one sub-agent per issue |
| `/forge-friction` | Surface friction patterns and generate skill briefs |
| `/agentify` | Bootstrap sub-agent skills for local coding agent CLIs |
| `/appmap <url>` | Map a web UI and generate a browser automation skill |
| `/web` | Parallel browser automation across independent tabs |
| `/provideme <CLI>` | Any coding agent CLI to local Anthropic-compatible API server |
| `/qualify` | Gate a proposed skill against the force-multiplier bar |
| `/unqualify <name> reason="..."` | Remove a drifted skill, logged to the ledger (dry-run first) |

## Architecture

| Path | Purpose |
|---|---|
| `.claude-plugin/plugin.json` | Plugin manifest (name, version, author, license) |
| `skills/<name>/SKILL.md` | 7 skills: `agentify`, `appmap`, `forge-friction`, `integrate`, `provideme`, `resolve`, `web` |
| `agents/` | `qualify.md` (skill gate-keeper), `unqualify.md` (logged removal) |
| `commands/` | `/qualify` and `/unqualify` slash-command dispatchers |
| `hooks/hooks.json` | Plugin hooks (currently empty `{}`) |
| `scripts/friction/analyzer.py` | Merges agent-afk session facets, witness traces, and legacy usage-data into ranked friction patterns |
| `.github/workflows/` | `claude.yml`, `claude-code-review.yml`, `release-please.yml` |

**Skill anatomy.** Each skill is a compact prompt that changes the *shape* of the workflow: adding phases, parallelism, or sub-agent dispatch. Orchestrator skills (`integrate`, `web`, `resolve`, `agentify`) dispatch sub-agents and merge output.

## Conventions

- **Skills are force multipliers, not reminders.** A skill must change workflow shape, unlock existing agent capabilities, or materially improve one-shot completion. Run every proposed skill through `/qualify` before adding.
- **Skill files:** `skills/<name>/SKILL.md` with YAML frontmatter `name` (hyphen-case, must match directory name), `description` (controls auto-invocation), and optional `argument-hint`.
- **Agent files:** `agents/<name>.md`, same frontmatter plus optional `model:` and `skills:`.
- **High leverage per token.** Keep skills compact.
- **Conventional Commits required.** release-please parses commit messages for versioning. Use `feat:`, `fix:`, `chore:`, etc.
- **When adding a skill:** create the `SKILL.md`, pass `/qualify`, and add a row to `README.md`.

## License

Apache 2.0.
