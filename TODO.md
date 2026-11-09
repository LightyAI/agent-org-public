# Phase 1 — Queue + lead 1 (weeks 1–2)

Gate: Platform lead raising and executing real cards at Lighty for 5 consecutive business days.

## Queue service
- [ ] SQLite schema (`cards`, `decisions`, `events`) + forward migrations on start
- [ ] HTTP API: list queue, get card, decide (UI only), pause flag
- [ ] MCP server: raise_card, update_card, list_decisions, ack_decision, close_card, rank, merge_cards, read_queue
- [ ] Token auth; `decide` never exposed over MCP
- [ ] Inbox UI: list + open card, J/K/A/R/D/?/Space/Enter/Shift+A
- [ ] Unranked-48h surfaces at top; 7-day expiry auto-defers
- [ ] docker compose

## Plugin
- [ ] `agents/lead.md` — wake cycle from SPEC §Lead agents
- [ ] `agents/sub-agent.md` — brief contract, packet contract
- [ ] `hooks/pre-tool-use.sh` — block merge/push-to-main, block send tools, forbidden paths
- [ ] `hooks/session-end.sh` — write STATE.md, post wake summary event
- [ ] `skills/raise-card/SKILL.md`
- [ ] `skills/org-setup/SKILL.md` — reads org.yaml, writes areas/<key>/CLAUDE.md, registers scheduled tasks
- [ ] Shadow mode flag honored by lead

## Lighty deployment
- [ ] `deployments/lighty/org.yaml` with Platform area
- [ ] Scoped GitHub App, Linear key, Slack bot for Platform
- [ ] Two days shadow, then live

## Open questions (decide before week 1)
- [ ] Leads as cloud scheduled tasks vs cron on operator machine
