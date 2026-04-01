#!/usr/bin/env bash
# cli-guard: PreToolUse hook
# Reminds Claude to check --help before using an unfamiliar CLI for the first time.
#
# Receives JSON on stdin: {"tool_name": "Bash", "tool_input": {"command": "..."}}
# Writes a reminder to stderr (injected into Claude's context) for new CLIs.
# Tracks seen CLIs in ~/.claude/seen-clis to suppress repeat reminders.

INPUT=$(cat)

TOOL=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
[ "$TOOL" != "Bash" ] && exit 0

CMD=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)
[ -z "$CMD" ] && exit 0

# Extract base binary name (first word, strip path prefix)
BASE_CMD=$(printf '%s' "$CMD" | sed 's/^[[:space:]]*//' | awk '{print $1}' | sed 's|.*/||' | tr -d '\n')
[ -z "$BASE_CMD" ] && exit 0

# Skip shell builtins and universally known commands
SKIP="bash sh zsh fish cd ls echo cat grep find pwd mkdir rm rmdir cp mv ln
      git npm npx node python python3 pip pip3 pip3.11 pip3.12
      curl wget jq sed awk head tail wc tr sort uniq tee xargs
      test true false export set unset read printf source
      if then else fi for while do done case esac return
      pnpm yarn bun npx tsx ts-node
      open kill pkill pgrep lsof ps env which type command
      mkdir touch chmod chown cp mv stat du df"

for s in $SKIP; do
  [ "$BASE_CMD" = "$s" ] && exit 0
done

# Track seen CLIs per user (not per session, so noise stays low across restarts)
SEEN_FILE="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/seen-clis"
mkdir -p "$(dirname "$SEEN_FILE")" 2>/dev/null
touch "$SEEN_FILE" 2>/dev/null || exit 0

if ! grep -qx "$BASE_CMD" "$SEEN_FILE" 2>/dev/null; then
  printf '%s\n' "$BASE_CMD" >> "$SEEN_FILE"
  printf '[cli-guard] First use of `%s`. Run `%s --help` (or `%s help`) before proceeding to verify flags and subcommands.\n' \
    "$BASE_CMD" "$BASE_CMD" "$BASE_CMD" >&2
fi

exit 0
