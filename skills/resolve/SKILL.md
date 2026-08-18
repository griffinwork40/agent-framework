---
name: resolve
description: "Resolves PR code review feedback. Use when the user asks to fix, address, or resolve issues from a code review or PR review."
---

## PR state pre-flight

Before doing anything else, run:

```
gh pr view <PR_NUMBER> --json state,mergedAt,headRefName,baseRefName,mergeCommit
```

**If `state === "MERGED"`:** STOP. Do not investigate issues, do not edit files. Report to the user:

> PR #N is already merged (merged at `<mergedAt>`, commit `<mergeCommit.oid>` into `<baseRefName>`). Pushing fixes to the original branch would orphan them — the merged code on `<baseRefName>` would remain unchanged.
>
> Recovery path: cherry-pick the fix commit(s) to a fresh branch off `origin/<baseRefName>` and open a new PR. Offer to do this automatically if the user confirms.

**If `state === "CLOSED"` (no `mergedAt`):** STOP. Report the PR is closed without merge. Ask the user whether they want to reopen it, branch off its head, or branch off `main` with a new PR.

**If `state === "OPEN"`:** proceed below.

## Sub-agent contract
/contract

Using parallel sub-agents – one per issue – for each of the issues pointed out in the PR review:

1. Reads the cited code and verifies the issue is valid (not a false positive or already addressed)
2. If valid, identifies the exact location and proposes the minimal fix (but does not apply it)
3. Reports back: issue summary, validity verdict, proposed fix, and any risks

When all sub-agents return, apply the fixes sequentially. Then run the full test suite. If green, **before pushing**, re-run the same `gh pr view` check — the PR may have merged during the work. Apply the same MERGED / CLOSED / OPEN logic. If still OPEN, create a single commit with a message summarizing all resolved issues, then push to update the PR.