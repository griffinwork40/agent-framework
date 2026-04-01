#!/usr/bin/env bash
# install.sh — adds the cli-guard PreToolUse hook to ~/.claude/settings.json
#
# Usage:
#   bash skills/cli-guard/scripts/install.sh
#
# Requires: jq

set -euo pipefail

PLUGIN_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
HOOK_SCRIPT="$PLUGIN_DIR/skills/cli-guard/scripts/hook.sh"
SETTINGS="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/settings.json"

# Make hook executable
chmod +x "$HOOK_SCRIPT"

# Dependency check
if ! command -v jq >/dev/null 2>&1; then
  echo "Error: jq is required. Install with: brew install jq" >&2
  exit 1
fi

if [ ! -f "$SETTINGS" ]; then
  echo "Error: settings.json not found at $SETTINGS" >&2
  exit 1
fi

# Idempotency check — skip if already wired up
if jq -e --arg hook "$HOOK_SCRIPT" \
  '.hooks.PreToolUse[]?.hooks[]?.command == $hook' \
  "$SETTINGS" | grep -q true 2>/dev/null; then
  echo "cli-guard already installed in $SETTINGS — nothing to do."
  exit 0
fi

# Backup before patching
BACKUP="$SETTINGS.bak.$(date +%s)"
cp "$SETTINGS" "$BACKUP"

# Inject the hook entry
HOOK_ENTRY=$(jq -n \
  --arg cmd "$HOOK_SCRIPT" \
  '{"matcher": "Bash", "hooks": [{"type": "command", "command": $cmd}]}')

jq --argjson entry "$HOOK_ENTRY" \
  '.hooks.PreToolUse = ((.hooks.PreToolUse // []) + [$entry])' \
  "$SETTINGS" > "$SETTINGS.tmp" && mv "$SETTINGS.tmp" "$SETTINGS"

echo "cli-guard installed."
echo "  Hook:   $HOOK_SCRIPT"
echo "  Config: $SETTINGS"
echo "  Backup: $BACKUP"
echo ""
echo "Claude will now be reminded to run --help the first time it uses any unfamiliar CLI."
