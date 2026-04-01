---
name: forge
description: "Creates new amplifier skills for this plugin. Use when the user wants to grow the plugin with a new high-leverage skill. Autonomously identifies gaps, generates an idea, creates the skill, and validates it."
---

Dispatch two sub-agents in parallel. One reads every existing skills/*/SKILL.md in this plugin to catalog what's covered, extract amplifier conventions (frontmatter format, compactness, orchestration idioms, writing style), and identify gaps in workflow coverage. The other researches the web for emerging agent workflow patterns, common orchestration pain points, and new capabilities worth amplifying. When both return, synthesize findings to identify the most impactful uncovered workflow transformation and generate a new amplifier concept. Create a compact SKILL.md following the extracted conventions, then run /qualify on it. If REJECT or SALVAGE, iterate — refine the concept or try the next-best gap — until APPROVE. Write the approved SKILL.md to skills/<name>/SKILL.md in this plugin.
