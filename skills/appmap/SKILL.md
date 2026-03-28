---
name: appmap
description: "Easily map a web UI and create a skill for Claude to automate that interface via parallel orchestration."
---

Dispatch one subagent to map the interface of $ARGUMENT in Chrome. When that subagent returns, use the skill-creator skill to make a skill for Claude to automate $ARGUMENT in Chrome. When complete, send a subagent to test the skill, ensuring everything works. If anything is not working, have a subagent fix the issue and another test again and iterate until it works great.
