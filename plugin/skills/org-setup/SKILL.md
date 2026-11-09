---
name: org-setup
description: /org-setup <path/to/org.yaml> — validate config, check credential scopes, generate areas/<key>/CLAUDE.md, write .agent-org/forbidden.txt, register scheduled tasks, start in shadow mode.
---

1. Parse `org.yaml`; refuse if `queue_url` unreachable or plugin/queue versions differ by more than one minor.
2. For each area: render `templates/area-CLAUDE.md` → `areas/<key>/CLAUDE.md`; create empty `STATE.md`.
3. Expand `always_card.paths` into `.agent-org/forbidden.txt` (one glob per line).
4. Check each credential's scope: refuse repo-wide GitHub tokens, workspace-wide Linear keys, Slack bots with channels outside the area.
5. Register scheduled tasks: one per area on `wake_cron`, chief of staff 30 min after each cycle and 07:30, distiller 02:00.
6. Write `.agent-org/SHADOW` with a 48 h expiry. Tell the operator leaving shadow is a `decide` card.
