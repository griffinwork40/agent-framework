# Orchestration Patterns Reference

## Subagent Topology by Complexity

### Simple (≤15 endpoints)
```
[Research] → [Plan] → [Build All + SKILL.md] → [Smoke Test]
     1 agent     inline    1-2 agents              inline
Total subagents: 2-3
Estimated time: 5-10 min
```

### Medium (16-50 endpoints)
```
[Research] → [Plan] → [Core/Auth] → [Group A] [Group B] [Group C] → [SKILL.md] → [Integration Test]
     1          inline      1            ←— parallel (3-5) —→           1              1
Total subagents: 6-8
Estimated time: 10-20 min
```

### Complex (50+ endpoints)
```
[Research A] [Research B] [Research C]  → [Merge + Plan] → [Core] → [G1]..[G10] → [Stitch] → [SKILL.md] → [Integration]
        ←— parallel (3-5) —→                  1              1    ←— parallel —→      1          1             1
Total subagents: 10-18
Estimated time: 20-40 min
```

## Wave Dependency Rules

1. Research must fully complete before Planning begins
2. Core/Auth must complete before resource group agents spawn
3. Resource group agents have NO dependencies on each other (fully parallel)
4. SKILL.md agent needs the command inventory from build agents
5. Integration test needs all code assembled

## Subagent Communication Pattern

Subagents communicate through files, not messages:

```
research.md          ← Research output (read by Planner)
build-plan.md        ← Plan output (read by Orchestrator)
scripts/{cli-name}   ← Build output (assembled by Orchestrator)
scripts/test_*.py    ← Test output (run by Orchestrator)
SKILL.md             ← Skill output (validated by Orchestrator)
references/*.md      ← Reference docs (written by SKILL.md agent)
```

## Practical Limits

| Resource | Limit | Why |
|----------|-------|-----|
| Parallel subagents | 5-8 max | Context window + memory pressure |
| CLI file size | <30KB | Single-file CLIs stay maintainable |
| SKILL.md | <500 lines | Skill-creator spec requirement |
| Research doc | <15K words | Context window for planning agent |
| Total pipeline time | <45 min | Diminishing returns after that |

## When to Split a CLI into Multiple Files

Default: **single file** (like threads-api). Split only when:
- CLI exceeds 30KB / 800 lines
- 3+ distinct resource groups with no shared logic
- Different auth methods for different endpoint groups

When splitting, use a package structure:
```
scripts/
├── {cli-name}           # Entry point (imports submodules)
├── {cli-name}_core.py   # Shared: auth, HTTP, errors
├── {cli-name}_foo.py    # Resource group commands
└── {cli-name}_bar.py    # Resource group commands
```
