# Review instructions

How to review a pull request in this repo. The Claude review workflow (`.github/workflows/claude-review.yml`) follows this file; human reviewers should too. `CLAUDE.md` has the working rules and `SPEC.md` the design; this file only says what a review must check and how to report it.

This repo is public. Review every change as if a stranger will read it and an attacker will open the next pull request.

## Verdict

Start the summary comment with one line:

- `Verdict: blocking` if there is at least one blocking finding.
- `Verdict: needs changes` if there are only non-blocking findings worth fixing before merge.
- `Verdict: no findings` if there is nothing to fix.

Then list findings, most severe first. Each one names the file and line, says what goes wrong and under what input, and suggests the smallest fix. Say what you did not check. Do not praise the change and do not restate the diff.

The review never approves or merges. A human does both.

## Blocking: guardrails

These are the rules the product exists to enforce. A change that weakens one is blocking even if tests pass.

- **Humans merge.** Nothing in the repo may call a merge API, enable auto-merge, or push to a protected branch. That includes workflows, hooks, skills, agent prompts and the queue service.
- **Guardrails are code.** Every control in `SPEC.md` §Guardrails is a hook or a credential scope. Flag a change that moves a control into an agent prompt, or that "fixes" a hook by rewording a prompt.
- **`decide` stays off MCP.** The queue's `decide` endpoint is the only writer to `decisions`, and the MCP server must not expose it or reach it another way.
- **Hooks fail closed.** A change to `plugin/hooks/` must still block: merges and pushes to protected branches, direct sends, `always_card` paths, and everything when the kill switch is set. Look for bypasses: quoting, wrappers such as `env`, `xargs` or `sh -c`, variable expansion, command names the hook cannot resolve, and an error path that exits 0.
- **Shadow mode cannot be skipped.** No flag, env var or config key that shortens or bypasses the two days.
- **Vendor code stays in adapters.** Vendor-specific code lives only in `plugin/mcp/queue-server/adapters/`, and each adapter implements exactly the five calls in `CLAUDE.md`.

## Blocking: security

- **Secrets and private data.** No tokens, keys, real `org.yaml` files, customer data, internal hostnames or personal email addresses in code, fixtures, docs, test output or commit messages. `deployments/` holds examples only.
- **Auth on every queue route.** Each HTTP route checks the token and the actor's role server-side. Flag a route added without it, a comparison that is not constant-time, a default credential that works outside local dev, and a token written to a log or an event.
- **Injection.** SQL built by string formatting, shell commands built from card or tracker text, path traversal in evidence reads and writes, and HTML in the inbox UI rendered from card content without escaping.
- **External text is data.** Anything fetched from PRs, issues, Slack or trackers must reach agents wrapped as data. Flag a path that lets it act as an instruction.
- **Evidence.** Served evidence types stay inert (no HTML, SVG or script served from the queue origin) and redaction runs before upload.
- **Workflows.** No `pull_request_target`, no untrusted event fields interpolated into `run:`, least-privilege `permissions:`, actions pinned to a commit SHA, and no secret reachable from a fork pull request.
- **Dependencies.** A new dependency needs a reason. Flag unpinned installs in the Dockerfile, packages with install scripts, and anything the dependency review check reported.

## Non-blocking

- Code that diverges from `SPEC.md` without changing the spec in the same pull request.
- `VERSION`, `plugin.json`, `package.json` and `pyproject.toml` out of step.
- Missing or weak tests for a changed behavior, especially a hook or an auth check. Tests live next to the code.
- IDs that are not ULIDs, timestamps that are not ISO-8601 UTC.
- Scope: features beyond what the pull request says it does.

## Skip

Formatting, naming taste, import order, and anything CI already reports. Do not ask for comments or docstrings.
