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
3. **Fix agents produce diffs, not pushes.** Dispatch `/fix-pr` with `--no-push`
   so fixes land in kept worktrees for operator review before any branch push.
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

Dispatch one `/review` invocation per PR, in parallel, using `compose`:

- Each node: `skill review <pr-url>`
- Model: `claude-sonnet-4-6`
- Max tool rounds per node: 30
- Node timeout: 180000ms (3 min per review)
- Cap at 5 concurrent nodes. If >5 PRs, run sequential waves of 5.

**For each review result, extract:**
- The `Decision: MERGE / DO NOT MERGE` verdict line
- The blocking findings count and severity breakdown
- The full findings list (including non-blocking advisory/low/nit findings)

### Wave 1.5 — Triage Gate (inline, no dispatch)

Classify each PR into exactly one bucket based on the review verdict:

| Bucket | Criteria |
|--------|----------|
| **GREEN** | `Decision: MERGE` — zero blocking findings |
| **BLOCKED** | `Decision: DO NOT MERGE` — has blocking findings that are fixable by `/fix-pr` (code issues, test gaps, missing checks) |
| **FOLLOW-UP** | `Decision: DO NOT MERGE` — has blocking findings that need human judgment (architecture, design, scope questions) or are outside the PR's own code (upstream dependency, spec ambiguity) |
| **SKIP** | PR already merged/closed during review, or review failed/timed out |

Present the triage table to the operator:

```
## Triage Results

| # | Title | Bucket | Blocking | Summary |
|---|-------|--------|----------|---------|
| 101 | Fix auth timeout | 🟢 GREEN | 0 | Clean — 2 low, 1 nit |
| 102 | Add dark mode | 🔴 BLOCKED | 2 high | Missing error handling in theme.ts:41, untested edge case |
| 103 | Bump deps | 🟢 GREEN | 0 | Dep-bump, no issues |
| 104 | Refactor auth | 🟡 FOLLOW-UP | 1 critical | API contract change needs design review |

### Proposed actions:
- **Merge:** #101, #103 (sequential, CI-gated)
- **Fix:** #102 (dispatch /fix-pr --no-push, review diff before push)
- **Issue (FOLLOW-UP):** #104 (create tracking issue with findings)
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

Execute buckets in this order: Merge → Fix → Follow-up. Each bucket is a
sequential sub-wave. Never overlap buckets.

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

For each BLOCKED PR, dispatch `/fix-pr` with `--no-push`:

- If only 1 blocked PR: dispatch inline via `skill fix-pr <N> --no-push`
- If 2+ blocked PRs: dispatch in parallel via `compose`, each node calling
  `skill fix-pr <N> --no-push`, worktree-isolated by `/fix-pr` internally.
- Max 3 concurrent fix agents (narrower than review wave — fixes are heavier).

After all fix agents return, present results to operator:

```
## Fix Results

| # | Title | Status | Worktree | Summary |
|---|-------|--------|----------|---------|
| 102 | Add dark mode | ✅ Fixed | .afk-worktrees/pr102-fix | Added error handling + test |
| 107 | Migrate config | ❌ Blocked | .afk-worktrees/pr107-fix | Needs upstream API change |

Fixed PRs have changes in kept worktrees. To review and push:
- `cd .afk-worktrees/pr102-fix && git diff HEAD~1`
- Then confirm: "push 102" / "push all" / "discard"
```

**Wait for operator approval** before pushing any fixes.

On approval, for each approved fix:
1. `cd` into the worktree
2. `git push origin <head-branch>`
3. Clean up: `worktree remove <name>`

#### 2C — Create Follow-up Issues

For each FOLLOW-UP PR, draft a GitHub issue body containing:
- The review findings (blocking items only)
- The PR link
- A recommended next step

Present all drafted issues to operator for approval before creating:

```
## Proposed Issues

### Issue for PR #104 — Refactor auth
**Title:** Review: API contract change in #104 needs design discussion
**Body:** [preview of the issue body]

Create these issues? (y/n/edit)
```

On approval: `gh issue create --title "..." --body-file <tmpfile>` for each.

#### 2D — Track Advisory Findings from Merged GREEN PRs

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

Batch-present all drafted issues to the operator for approval (same gate as 2C):

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
On "skip": omit without creating. Advisory issues are lower priority than
FOLLOW-UP issues — the operator may reasonably skip all of them.

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
| Fixed + pushed | #102 | ✅ (re-review: GREEN) |
| Issue (follow-up) | #104 | gh#551 |
| Issue (advisory) | #101, #103 | gh#552, gh#553 |
| Skipped | — | — |
| Still blocked | #107 | Needs upstream API change |

Session closed <N> of <M> PRs.
```
