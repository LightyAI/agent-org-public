# agent-org

A lead-agents / chief-of-staff / review-queue operating system for Claude Code, packaged as a plugin plus a queue service. Full design in `SPEC.md`; read it before changing anything structural.

## What this repo is

- `plugin/` — the Claude Code plugin (`agent-org`): agent roles, skills, hooks, the queue MCP server, templates. Company-agnostic; nothing in here knows Lighty.
- `queue/` — the queue service (`agent-org-queue`): SQLite + HTTP API + inbox UI. Runs as a container on a box the company controls.
- `deployments/<company>/` — per-company `org.yaml` and generated `areas/<key>/CLAUDE.md`. Lighty first; a second and a third company follow. Never commit real tokens here.
- `SPEC.md` — the spec this was scaffolded from. Decisions go there, not in chat.

## Working rules

- Agents propose; code vetoes. Every guardrail in SPEC.md §Guardrails is a hook or a credential scope, never a prompt instruction. Don't "fix" a guardrail by rewording an agent prompt.
- Humans merge. Nothing in this repo may call a merge API or push to a protected branch.
- The queue's `decide` endpoint is the only writer to `decisions`. It is never exposed over MCP.
- The plugin and the queue share one version in `VERSION`. Bump both together.
- Vendor-specific code lives only in `plugin/mcp/queue-server/adapters/`. Each adapter implements exactly five calls: `list_work`, `read_item`, `update_status`, `comment`, `list_threads`.
- New deployments start in `shadow` mode for two days. Don't add a flag to skip it.

## Build order (SPEC.md §Build plan)

1. `queue/` with SQLite schema, HTTP API, MCP server, inbox UI with keyboard — then the Platform lead for Lighty.
2. `demo-recorder` and `pr-packet` skills; two more leads; chief of staff ranking + daily brief.
3. Nightly distiller; metrics in the brief; `/org-setup`; private marketplace; voice.
4. Second company (adapters, redaction, second-operator routing).
5. Third company; go/no-go on public listing.

Current phase: **1**. See `TODO.md`.

## Conventions

- Python 3.12 for the queue service (FastAPI + SQLite via `sqlite3`, no ORM). Node 22 for the MCP server (TypeScript, `@modelcontextprotocol/sdk`).
- IDs are ULIDs. Timestamps are ISO-8601 UTC strings.
- Tests live next to the code (`test_*.py`, `*.test.ts`). Run `make test` before opening a PR.
- Keep SPEC.md and this file in sync: if the code diverges from the spec on purpose, change the spec in the same PR.
