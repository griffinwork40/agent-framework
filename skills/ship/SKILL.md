---
name: ship
description: "Release pipeline for already-done local work. Dispatches /ground-state pre-flight, runs the project test suite, drafts a commit message for user approval, pushes, and opens a PR with a structured verification summary. Use when local changes are ready to hand off to review — e.g. 'ship this', 'push and open a PR', 'release this work'. Add --verify to trigger an adversarial verifier wave on the diff before a human reads the PR."
---

## Sub-agent contract
/agent-workflow-amplifiers:contract

Release pipeline for work that is **already done locally**. This skill does NOT build, implement, or fix — if the task needs code, route to `/mint`; if a bug needs diagnosis, route to `/diagnose`. This skill's job is the hand-off from "done locally" to "visible in a PR."

**Skip when:**
- Working tree is clean (nothing to ship — tell the user).
- Current branch is the default branch (`main`/`master`) — ask the user for a feature branch.
- User invokes with `--dry-run` → produce the plan but take no git actions.

**Arguments:**
- `--verify` — force the optional adversarial verifier wave (Phase 6), regardless of diff size.
- `--draft` — open the PR as a draft.
- `--dry-run` — run phases 1–5 but stop before Phase 7 (no push, no PR).

---

**Phase 1 — Pre-flight (mandatory).**
Invoke `agent-workflow-amplifiers:ground-state` via the Skill tool. Abort and surface the blocker with remediation steps if ground-state reports any of:
- Uncommitted changes in files unrelated to the declared scope
- Branch behind `origin/<default>` (stale — user needs to rebase/merge first)
- Current branch IS the default branch
- Wrong-repo context (user's cwd doesn't match the branch's purpose)

**Phase 2 — Test gate.**
Detect the project's test harness by scanning, in order:
1. `package.json` → `scripts.test` (run via the project's package manager: `pnpm`/`yarn`/`npm`)
2. `pyproject.toml` → `pytest` if configured, or `scripts.test`
3. `Cargo.toml` → `cargo test`
4. `go.mod` → `go test ./...`
5. `Makefile` → `test` target

If found → run it. Non-zero exit → **abort**; surface the failing output and recommend `/diagnose`. Do not proceed to commit.

If no harness detected → **warn the user:** "No test harness detected. Ship without running tests?" Require explicit yes. Do not silently skip.

**Phase 3 — Draft commit message (user-approval gate).**
Read the cumulative diff: `git diff --stat origin/<default>...HEAD` + full `git diff`. Synthesize a commit message:
- **Subject (≤70 chars):** imperative, Conventional Commits format (`feat`, `fix`, `chore`, `refactor`, `docs`, etc.)
- **Body:** 2–5 bullets on WHY — the motivation, constraint, or trade-off. Skip the WHAT — the diff speaks for itself.

Before committing, confirm the **file list** to stage with the user — don't sweep in untracked config/scratch/secret files. Surface the draft message + file list; wait for explicit approval. If the user edits the message, use the edited version.

**Phase 4 — Commit.**
Stage only the confirmed files. Commit via HEREDOC to preserve formatting:

```
git commit -m "$(cat <<'EOF'
<subject>

<body>
EOF
)"
```

Never `--amend` (creates a new commit each time). Never bypass hooks (`--no-verify`).

**Phase 5 — Push.**
- Upstream unset → `git push -u origin <branch>`
- Upstream set → `git push`
- Non-fast-forward rejection → **abort**; do not force-push. Surface and let the user decide.

**Phase 6 — Optional adversarial verifier wave.**
Trigger when `$ARGUMENT` contains `--verify`, OR when the cumulative diff exceeds **100 changed lines** (rough proxy for "big enough that a human reviewer will miss something"). Skip for diffs under 100 lines unless `--verify` is explicit.

Dispatch an adversarial verifier sub-agent via the Agent tool. Use `subagent_type: "research-agent"` (read-only, no Edit/Bash-that-mutates). Brief it with:
- The cumulative branch diff
- The draft PR body (Phase 7)
- Instruction: from the diff alone — **without consulting the draft's reasoning** — independently re-derive the 2–3 load-bearing claims the PR body makes. Return per claim: `CONFIRM` / `REFINE` / `CONTRADICT` with file:line evidence.

If any verifier returns `CONTRADICT` → **surface to the user** before opening the PR. Append the counter-claim to the PR body's Verification section. User decides whether to proceed, revise, or abort.

**Phase 7 — Synthesize PR body.**
Structure:

```
## Summary
<2–4 bullets: what changed, why>

## Test results
- <command>: <passed/failed + counts>
<repeat per test invocation>

## Verification
<if --verify ran: per-claim verdict + evidence>
<if skipped: "No adversarial verify requested (diff under threshold).">

## Out of scope
<anything touched but not central to this PR, if any; omit section otherwise>
```

**Phase 8 — Open PR.**
```
gh pr create \
  --title "<subject line of the commit>" \
  --body "$(cat <<'EOF'
<PR body from Phase 7>
EOF
)" \
  --base <default-branch> \
  [--draft]
```

Return the PR URL to the user. Done.

---

**Failure modes to watch:**
- `/ground-state` unavailable → skip Phase 1 with a loud warning; do not proceed silently.
- `gh` CLI not authenticated → abort Phase 8 with the exact `gh auth login` command.
- Detached HEAD or shallow clone → abort at Phase 1; these are edge cases `/ship` should not try to auto-recover.
