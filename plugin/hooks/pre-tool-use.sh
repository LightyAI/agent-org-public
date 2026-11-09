#!/usr/bin/env bash
# Agents propose; code vetoes. Exit 2 blocks the tool call and feeds stderr back to the agent.
set -euo pipefail
input="$(cat)"
tool="$(jq -r '.tool_name // empty' <<<"$input")"
cmd="$(jq -r '.tool_input.command // empty' <<<"$input")"
path="$(jq -r '.tool_input.file_path // empty' <<<"$input")"

# 1. No merges, no pushes to protected branches.
if [[ "$tool" == "Bash" ]]; then
  if grep -Eq '\bgh pr merge\b|\bgit merge\b|\bgit push\b.*\b(main|master|origin main|origin master)\b|\bgit push\b.*--force' <<<"$cmd"; then
    echo "agent-org: merging or pushing to a protected branch is a human action. Open a PR and raise a review card." >&2; exit 2
  fi
fi

# 2. No direct sends. Draft a `send` card instead.
if [[ "$tool" =~ ^mcp__(Slack|Gmail)__.*(send|reply|forward|post|schedule) ]]; then
  echo "agent-org: outbound messages become a send card; the operator sends on approval." >&2; exit 2
fi

# 3. Forbidden paths from org.yaml always_card.paths (resolved by org-setup into .agent-org/forbidden.txt).
if [[ -n "$path" && -f "${AGENT_ORG_ROOT:-.}/.agent-org/forbidden.txt" ]]; then
  while IFS= read -r pat; do
    [[ -z "$pat" ]] && continue
    if [[ "$path" == $pat ]]; then
      echo "agent-org: $path matches always_card pattern '$pat'. Stop and raise a decide card." >&2; exit 2
    fi
  done < "${AGENT_ORG_ROOT:-.}/.agent-org/forbidden.txt"
fi

# 4. Kill switch.
if [[ -f "${AGENT_ORG_ROOT:-.}/.agent-org/PAUSED" ]]; then
  echo "agent-org: paused by operator. Exit now." >&2; exit 2
fi
exit 0
