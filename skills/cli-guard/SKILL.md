---
name: cli-guard
description: "Install a PreToolUse hook that reminds Claude to run --help before using an unfamiliar CLI for the first time. Use when the user asks to set up or install cli-guard, or enable the CLI help-first behavior."
---

# CLI Guard

Ships a `PreToolUse` hook that fires whenever Claude is about to run a Bash command. For any CLI it hasn't seen before, it writes a reminder to check `--help` first — injecting that nudge directly into Claude's context before the command executes.

Seen CLIs are tracked in `~/.claude/seen-clis` so the reminder only fires once per tool, not on every use.

## Install

Run once after installing the plugin:

```bash
bash skills/cli-guard/scripts/install.sh
```

This patches `~/.claude/settings.json` to add the `PreToolUse` hook. A timestamped backup is created automatically.

## Uninstall

Remove the entry from `~/.claude/settings.json` under `.hooks.PreToolUse` where the command path ends in `cli-guard/scripts/hook.sh`.

To also clear the seen-CLIs history:

```bash
rm ~/.claude/seen-clis
```

## How It Works

- **Hook script**: `skills/cli-guard/scripts/hook.sh`
- **Trigger**: `PreToolUse` on `Bash` tool calls
- **Logic**: extracts the base binary name, skips builtins and known-safe commands, checks `~/.claude/seen-clis`, and writes a one-line reminder to stderr if the CLI is new
- **Effect**: Claude sees the reminder before deciding how to invoke the command

## Adding to the Skip List

Edit `hook.sh` and add the CLI name to the `SKIP` list to suppress reminders for it permanently.
