---
name: integrate
description: "One-prompt API integration pipeline. Takes any API (docs URL, name, or description) and produces a working CLI wrapper + skill + tests. Automates the full research → plan → parallel-build → test → package flow using subagent orchestration. Triggers on: 'integrate X API', 'build a CLI for X', 'wrap X API', 'create an integration for X', 'one-prompt integration', or when asked to turn any external API into a usable CLI+skill."
---

# integrate — One-Prompt API Integration Pipeline

Turn any API into a working CLI + skill in a single invocation.

## How It Works

This skill orchestrates a multi-phase pipeline using parallel subagents:

```
Phase 1: RESEARCH    → Absorb the API surface (docs, endpoints, auth)
Phase 2: PLAN        → Decompose into parallelizable build units
Phase 3: BUILD       → Fan-out parallel agents (TDD, modular files)
Phase 4: ASSEMBLE    → Merge outputs, integration test, write SKILL.md
```

## Input

Minimum: an API name or docs URL. Optional parameters improve output quality.

| Parameter | Required | Example |
|-----------|----------|---------|
| API name or docs URL | ✅ | `"Calendly API"` or `https://developer.calendly.com/api-docs` |
| Auth method | helpful | `OAuth2`, `API key header`, `Bearer token` |
| Priority endpoints | helpful | `"list events, create booking, cancel event"` |
| Output directory | optional | Default: `~/.claude/skills/<api-name>/` |

## Complexity Tiers

Auto-detected from research output:

| Tier | Endpoints | Research | Build |
|------|-----------|----------|-------|
| **Simple** | ≤15 | 1 agent | 1-2 agents |
| **Medium** | 16-50 | 1 agent + chunking | 3-5 parallel agents |
| **Complex** | 50+ | Multiple parallel research agents, merge | 5-10 parallel build agents + shared types |

## Execution Guide

### Phase 1: RESEARCH

Use a subagent (or TodoWrite → TodoRead loop for Claude Code) to research the API:

**Task for research agent:**

```
Research the {API_NAME} API. Write a structured report to {OUTPUT_DIR}/research.md covering:

1. Auth — method, token flow, scopes, refresh mechanism
2. Base URL — versioning scheme
3. Endpoints — for each: method+path, description, required/optional params, response shape, rate limits
4. Pagination — pattern (cursor/offset/page-token), default/max sizes
5. Rate Limits — global + per-endpoint, response format
6. Error Patterns — standard error shape, common codes
7. Gotchas — non-obvious behaviors (two-step flows, eventual consistency, required delays)

Sources: official docs ({DOCS_URL}), web search for API reference + auth guide + community guides.
Sort endpoints by importance. Flag essential vs nice-to-have.
```

**After research:** Read `research.md`. Count endpoints → determine complexity tier.

### Phase 2: PLAN

Write `{OUTPUT_DIR}/build-plan.md`:

```markdown
# Build Plan: {API_NAME} CLI

## Complexity: {TIER} | Endpoints: {N}

## Module Structure
{api-name}/
├── scripts/
│   └── {cli-name}         # Main CLI entry point
├── references/
│   ├── api-docs.md         # Condensed API reference
│   └── auth-setup.md       # Token acquisition guide
└── SKILL.md

## Build Units (parallel where possible)

### Unit 1: Core + Auth
- Config/token management, HTTP client, error handling, rate limit retry

### Unit 2-N: Resource Groups
- Group related endpoints, list tests for each

### Unit N+1: SKILL.md + References
```

**Key decisions:**
- Simple: combine all units into 1-2 agents
- Medium: Core/Auth first (dependency), then fan out resource groups in parallel
- Complex: Core + shared types first, then parallel fan-out, then integration stitching

### Phase 3: BUILD

**Subagent task template:**

```
Build part of a CLI wrapper for {API_NAME} API.
Output: {OUTPUT_DIR}/scripts/

Context:
- Research: {paste relevant sections}
- Core module: {paste if Wave 2+}

Your endpoints: {list}

Requirements:
1. Python with typer + rich + httpx (or Node with commander if SDK exists)
2. Each command: error handling, --pretty flag, JSON default output
3. Write tests (pytest/vitest) alongside implementation
4. Handle pagination and 429 rate limit retry
```

**Wave execution:**
- Wave 1: Core + Auth (must complete first)
- Wave 2: Resource groups (all parallel)
- Wave 3: SKILL.md + references (needs command inventory)

### Phase 4: ASSEMBLE

1. **Merge check** — no import conflicts, no duplicate functions
2. **Run tests** — fix failures
3. **CLI validation** — `{cli-name} --help` must show all commands
4. **SKILL.md review** — frontmatter has `name` + `description` with trigger phrases, body documents all commands, references linked
5. **Symlink** — `ln -s {OUTPUT_DIR}/scripts/{cli-name} /usr/local/bin/{cli-name}`
6. **Smoke test** — 2-3 real API calls if credentials available

## Error Recovery

| Failure | Recovery |
|---------|----------|
| Thin docs from research | Search for community guides, SDK source, Postman collections |
| Broken build output | Spawn fix-it agent with error context |
| Test failures | Debug agent with failing output + source |
| Rate limited during smoke test | Expected — verify retry logic works |

## Constraints

- Do NOT publish anywhere without explicit permission
- Do NOT make live API calls during build (mock everything in tests)
- Do NOT create extraneous files (README, CHANGELOG, etc.)
- Match the `threads-api` skill structure and quality as reference
- Skip endpoints the user says they don't need

## Reference Implementation

`~/.claude/skills/threads-api/` (if present) or `~/.openclaw/skills/threads-api/` — gold standard CLI+skill output. Match its structure and ergonomics.

## Orchestration Details

See `references/orchestration-patterns.md` for subagent topology diagrams, wave dependency rules, file communication patterns, and practical limits by complexity tier.
