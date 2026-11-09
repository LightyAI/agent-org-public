#!/usr/bin/env bash
# Post a wake summary to the queue's events table. STATE.md is written by the lead itself.
set -euo pipefail
[[ -z "${AGENT_ORG_QUEUE_URL:-}" ]] && exit 0
area="${AGENT_ORG_AREA:-unknown}"
state="${AGENT_ORG_ROOT:-.}/areas/${area}/STATE.md"
summary="$( [[ -f "$state" ]] && head -c 2000 "$state" || echo "no STATE.md" )"
curl -fsS -X POST "$AGENT_ORG_QUEUE_URL/api/events" \
  -H "Authorization: Bearer ${AGENT_ORG_QUEUE_TOKEN:-}" -H "Content-Type: application/json" \
  -d "$(jq -n --arg a "lead:$area" --arg s "$summary" '{actor:$a, kind:"wake_end", data:{summary:$s}}')" >/dev/null || true
