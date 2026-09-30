---
name: automate
description: "Set up a scheduled headless Claude run that sends summaries to Telegram. Use when the user wants to automate a recurring task via launchd (macOS) with push-notified results."
disable-model-invocation: true
---

Dispatch two sub-agents in parallel:
1. **Scout** — inspect `~/.claude/automations/` (scripts, plists, existing jobs) and the target project folder to surface conventions, naming, and overlapping jobs. Report any conflicts.
2. **Prompt designer** — draft the headless Claude prompt for the recurring task. Encode the input context explicitly and require a concise Telegram-ready summary as output.

When both return, generate:
- Shell script at `~/.claude/automations/scripts/<slug>.sh` that `cd`s into the target folder and runs:
  `claude --dangerously-skip-permissions --channels plugin:telegram@claude-plugins-official "<prompt>"`
- launchd plist at `~/Library/LaunchAgents/com.claude.automate.<slug>.plist` with the requested `StartCalendarInterval` or `StartInterval`, plus `StandardOutPath`/`StandardErrorPath` pointing at `~/.claude/automations/logs/<slug>.log`.

Load it: `launchctl bootstrap gui/$(id -u) <plist>` and confirm with `launchctl list | grep <slug>`.

Dispatch a **verification** sub-agent to run the script once manually, confirm the Telegram summary arrives, and tail the log. On failure, diagnose (permissions, path, channel config, prompt shape) and fix before exiting. Report final status, script path, plist path, and next scheduled run time.
