---
name: pr-triage
description: "Batch-review open PRs in parallel, triage into merge/fix/follow-up buckets, then execute each bucket with per-action human gates on every irreversible operation. Parallel reviews in worktrees compress wall-clock; sequential human-gated merges and diff-only fixes keep blast radius bounded."
argument-hint: "[--prs <N,N,...>] [--limit <N>] [--repo <owner/repo>] [--auto-merge] [--skip-fix]"
category: "Build & ship"
when-to-use: "When 2+ PRs are open and you want to review, triage, merge, and fix them in a single session. Triggers on 'triage PRs', 'review open PRs', 'batch review', 'clear the PR queue'."
skills: [review, fix-pr, contract]
flags: [--auto-merge, --skip-fix, --prs, --limit, --repo]
failure_modes:
  - rate_limit_429_on_wide_fanout
  - merge_conflict_after_sibling_merge
  - fix_agent_misreads_stale_comment
  - gh_auth_missing
---

# PR Triage — decision-support orchestrator

You are executing a PR triage session. This skill reviews open PRs in parallel,
triages results into actionable buckets, and executes each bucket with human gates
on every irreversible operation.

## Hard constraints

1. **No irreversible external write without human confirmation.** Merges, pushes,
   issue creation, and GH comment posting each require explicit operator approval.
   The only exception: `--auto-merge` flag opts into batch-merge of green PRs
   (still sequential with CI check between each).
2. **Reviews are read-only.** `/review` never posts to GitHub. This skill owns
   the decision of what to post and when.
3. **Fix agents push directly.** Dispatch `/fix-pr` (no `--no-push`) so fixes
   are pushed to the PR branch immediately after passing the test gate.
4. **Sequential merges only.** Never merge two PRs in parallel. After each merge,
   verify CI / build before proceeding to the next.
5. **Rate-limit awareness.** Cap concurrent review dispatches at 5. For >5 PRs,
   run in waves of 5.

## Arguments

Parse these from `$ARGUMENTS`:

| Flag | Default | Meaning |
|------|---------|---------|
| `--prs 101,102,105` | (all open) | Specific PR numbers to triage |
| `--limit N` | 10 | Max PRs to fetch when using all-open discovery |
| `--repo owner/repo` | (cwd git remote) | Target repository |
| `--auto-merge` | off | Skip human gate for merge of green PRs (still sequential + CI-gated) |
| `--skip-fix` | off | Skip Wave 3 fix phase; just triage and merge |

## Execution

### Wave 0 — Preflight (inline, no dispatch)

1. Verify `gh` CLI is authenticated: `gh auth status`. **Fail closed** if not.
2. Determine target repo from `--repo` flag or `gh repo view --json nameWithOwner`.
3. Fetch open PRs:
   - If `--prs` provided: `gh pr view <N> --json number,title,headRefName,url,author,reviewDecision,statusCheckRollup` for each.
   - Otherwise: `gh pr list --state open --limit <limit> --json number,title,headRefName,url,author,reviewDecision,statusCheckRollup`.
4. If 0 PRs found, report Done with "No open PRs to triage" and stop.
5. Print the PR manifest table to the operator:

```
## PR Triage — <repo> — <N> open PRs

| # | Title | Author | Branch | CI | Review |
|---|-------|--------|--------|----|--------|
| 101 | Fix auth timeout | dependabot | fix/auth | ✅ | APPROVED |
| 102 | Add dark mode | griffin | feat/dark | ❌ | CHANGES_REQUESTED |
| ... | ... | ... | ... | ... | ... |

Proceeding to parallel review wave...
```

### Wave 1 — Parallel Review (subagent fan-out)

Dispatch one `agent` call per PR, in parallel:

- Each call: `skill review <pr-url>`
- Model: `claude-opus-5-5`
- Cap at 5 concurrent agents. If >5 PRs, run sequential waves of 5 (dispatch the first batch, await all results, then dispatch the next batch).
- These are read-only reviews — no `isolation: "worktree"` needed.

**For each review result, extract:**
- The `Decision: MERGE / DO NOT MERGE` verdict line
- The blocking findings count and severity breakdown
- The full findings list (including non-blocking advisory/low/nit findings)

### Wave 1.5 — Triage Gate (inline, no dispatch)

Classify each PR into exactly one bucket based on the review verdict:

| Bucket | Criteria |
|--------|----------|
| **GREEN** | `Decision: MERGE` — zero blocking findings |
| **BLOCKED** | `Decision: DO NOT MERGE` — has blocking findings. Dispatch `/fix-pr` to address them. |
| **SKIP** | PR already merged/closed during review, or review failed/timed out |

Present the triage table to the operator:

```
## Triage Results

| # | Title | Bucket | Blocking | Summary |
|---|-------|--------|----------|---------|
| 101 | Fix auth timeout | 🟢 GREEN | 0 | Clean — 2 low, 1 nit |
| 102 | Add dark mode | 🔴 BLOCKED | 2 high | Missing error handling in theme.ts:41, untested edge case |
| 103 | Bump deps | 🟢 GREEN | 0 | Dep-bump, no issues |
| 104 | Refactor auth | 🔴 BLOCKED | 1 critical | API contract change needs fix |

### Proposed actions:
- **Merge:** #101, #103 (sequential, CI-gated)
- **Fix:** #102, #104 (dispatch /fix-pr, push after test gate)
- **Issue (advisory):** #101 has 2 low findings, #103 has 1 nit — track after merge

Awaiting your approval to proceed. Reply with:
- "go" or "yes" — execute all proposed actions
- "merge only" — only merge green PRs
- "fix only" — only fix blocked PRs
- "skip <number>" — exclude a specific PR
- Any custom instruction
```

**Wait for operator approval** via `ask_question` before proceeding to Wave 2.
If on a non-interactive surface (daemon, one-shot), **stop here** — emit the
triage table as the terminal artifact and report Done.

### Wave 2 — Execute Buckets (sequential, human-gated)

Execute buckets in this order: Merge → Fix. Each bucket is a sequential
sub-wave. Never overlap buckets.

#### 2A — Merge Green PRs

For each GREEN PR, **sequentially** (never parallel):

1. Re-check mergeability: `gh pr view <N> --json mergeable,mergeStateStatus`.
   If no longer mergeable (conflict from sibling merge), move to BLOCKED bucket
   and inform operator.
2. Unless `--auto-merge` is set, confirm with operator:
   `"Merge #<N> '<title>' into <base>? (y/n)"`
3. Merge: `gh pr merge <N> --merge --delete-branch`
   (Use `--merge` not `--squash` unless the PR is single-commit; respect repo's
   merge strategy if detectable from `gh api repos/{owner}/{repo}` settings.)
4. **After each merge**, verify the base branch CI:
   - `gh pr checks` on the next candidate (if any) — if the base branch now
     shows failures, **stop merging** and inform the operator.
   - Brief pause (5s) to let CI pick up the new base.

#### 2B — Fix Blocked PRs

For each BLOCKED PR, dispatch `/fix-pr`:

- If only 1 blocked PR: dispatch a single `agent` call: `skill fix-pr <N>`
- If 2+ blocked PRs: dispatch parallel `agent` calls, each calling `skill fix-pr <N>`.
  `/fix-pr` handles its own worktree creation internally, so no `isolation: "worktree"` is needed on the dispatch.
- Max 3 concurrent fix agents (narrower than review wave — fixes are heavier).

`/fix-pr` handles its own worktree creation, test gate, push, and cleanup.
After all fix agents return, present results:

```
## Fix Results

| # | Title | Status | Summary |
|---|-------|--------|---------|
| 102 | Add dark mode | ✅ Fixed + pushed | Added error handling + test |
| 107 | Migrate config | ❌ Blocked | Needs upstream API change (worktree kept) |
```

#### 2C — Track Advisory Findings from Merged GREEN PRs

After merging GREEN PRs (Wave 2A), create tracking issues for any non-blocking
findings (low, advisory, nit) that the review surfaced. These findings were not
severe enough to block merge but represent real improvement opportunities that
will otherwise be lost in the triage session transcript.

**Skip when:** a GREEN PR's review had zero non-blocking findings (truly clean).

For each GREEN PR with non-blocking findings, draft a GitHub issue:
- **Title:** `review: advisory findings from #<N> — <PR title summary>`
- **Body:** the non-blocking findings list (severity, file/line, description,
  suggestion), the merged PR link, and a note that these were reviewed and
  accepted at merge time.
- **Labels:** if the repo has a `review-followup` or `tech-debt` label, apply it.

Batch-present all drafted issues to the operator for approval:

```
## Advisory Follow-ups from Merged PRs

### Issue for PR #101 — Fix auth timeout
**Title:** review: advisory findings from #101 — fix auth timeout
**Findings:** 2 low (missing null check in fallback path, stale comment)

### Issue for PR #103 — Bump deps
**Title:** review: advisory findings from #103 — bump deps
**Findings:** 1 nit (changelog entry formatting)

Create these issues? (y/n/edit/skip)
```

On approval: `gh issue create --title "..." --body-file <tmpfile>` for each.
On "skip": omit without creating. Advisory issues are optional — the operator
may reasonably skip all of them.

### Wave 3 — Re-review Fixed PRs (conditional)

If any fixes were pushed in Wave 2B AND `--skip-fix` is not set:

1. For each pushed fix, dispatch `/review <pr-url>` (single agent, not parallel —
   there are typically 1-2 fixed PRs).
2. If the re-review returns GREEN, inform operator and offer to merge.
3. If still BLOCKED, report findings and stop — do not loop.

### Terminal State

Report Done with a structured summary:

```
## PR Triage Complete — <repo>

| Action | PRs | Result |
|--------|-----|--------|
| Merged | #101, #103 | ✅ |
| Fixed + pushed | #102, #104 | ✅ (re-review: GREEN) |
| Issue (advisory) | #101, #103 | gh#552, gh#553 |
| Skipped | — | — |
| Still blocked | #107 | Needs upstream API change |

Session closed <N> of <M> PRs.
```
