---
name: resolve
description: "Resolves PR code review feedback. Use when the user asks to fix, address, or resolve issues from a code review or PR review."
---

## Sub-agent contract
/agent-workflow-amplifiers:contract

Using parallel sub-agents – one per issue – for each of the issues pointed out in the PR review:

1. Reads the cited code and verifies the issue is valid (not a false positive or already addressed)
2. If valid, identifies the exact location and proposes the minimal fix (but does not apply it)
3. Reports back: issue summary, validity verdict, proposed fix, and any risks

When all sub-agents return, apply the fixes sequentially. Then run the full test suite. If green, create a single commit with a message summarizing all resolved issues, then push to update the PR.