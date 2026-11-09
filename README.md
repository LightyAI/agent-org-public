# agent-org

Lead agents per area, a chief-of-staff agent that ranks what they surface, and one review queue the operator clears by keyboard and voice. Built on Claude Code; installs into any company's Claude Code with an `org.yaml`.

See `SPEC.md` for the full design and `CLAUDE.md` for working rules.

## Layout

    plugin/        the Claude Code plugin (agents, skills, hooks, queue MCP server, templates)
    queue/         the queue service: SQLite + HTTP API + inbox UI
    deployments/   per-company org.yaml and generated area CLAUDE.md files
    SPEC.md        the spec
    TODO.md        phase-1 task list

## Quick start (phase 1, Lighty)

    cd queue && make dev            # queue + UI on http://127.0.0.1:7340
    cp deployments/lighty/org.yaml.example deployments/lighty/org.yaml
    # fill in queue token, Linear team keys, repos, Slack channels
    claude --plugin-dir ./plugin    # then: /org-setup deployments/lighty/org.yaml
