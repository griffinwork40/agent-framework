# Contributing

Thanks for considering a contribution. This plugin has an intentionally narrow bar: **force multipliers only.**

## The Bar

A new skill must do at least one of:

- change the **shape** of the workflow (phases, parallelism, sub-agent dispatch)
- unlock more of the agent's **existing** capabilities
- materially improve **one-shot** task completion
- create a **repeatable** workflow upgrade the base agent wouldn't reliably apply by default

Reminders, checklists, best-practice nudges, and generic execution advice will be rejected — not because they're bad, but because they don't belong here. They belong in a project's `CLAUDE.md`.

## Before Opening a PR

1. **Run your draft through `/qualify`** — this is the same gate the maintainers will apply. If qualify returns `REJECT` or `SALVAGE`, either revise or reconsider.
2. **Check for overlap** — read every existing `SKILL.md` and confirm your skill is not ≥60% functionally overlapping with an existing one. If it is, extend the existing skill instead.
3. **Keep it compact** — a skill's body should be the minimum prompt that reliably triggers the intended behavior. Prune aggressively.
4. **Update `README.md`** — add your skill to the skills table.

## Skill Structure

```
skills/<skill-name>/
  SKILL.md         ← required
```

Frontmatter:

```yaml
---
name: <skill-name>          # hyphen-case, matches directory name
description: "<trigger>"    # specific — controls auto-invocation
---
```

## PR Checklist

- [ ] Ran `/qualify` on the draft — paste the decision in the PR description
- [ ] Checked overlap with existing skills
- [ ] Updated `README.md` skills table
- [ ] Skill body is as compact as possible

## License

By submitting a PR you agree your contribution is licensed under Apache 2.0 (see `LICENSE`).
