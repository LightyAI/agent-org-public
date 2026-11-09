# Agent Org Spec: Leads, Chief of Staff, Review Queue

Nov 7, 2026 · Anthony Johnson · Live doc with diagrams: https://claude.ai/artifact/SzYGr26ZMzmf1XUmQFwJqM

## Summary

We are building a three-layer agent org on top of Claude Code: always-on lead agents, one per area of Lighty, each dispatching short-lived sub-agents to ship PRs; a chief-of-staff agent that prioritizes everything the leads surface; and a single review queue where the operator clears decisions in batches by keyboard and voice. Approvals feed a decision log that is compressed nightly into a shared preferences file, so every agent's first draft drifts toward what the operator would have chosen.

The whole thing ships as one Claude Code plugin plus a queue service, so it installs into any company's Claude Code with a config file naming their areas, repos and trackers. Lighty is the first tenant; a second and a third company follow. Leads run as scheduled Claude Code sessions with per-area CLAUDE.md files; sub-agents are the Agent tool in worktrees; the queue is a SQLite-backed local web app exposed to agents as an MCP server. Humans still merge every PR and approve every outbound action.

The operator's time moves from running sessions to reading cards. The first milestone is one lead plus the queue, in production for one area, within two weeks.

## Goals and non-goals

The system succeeds when the operator reviews finished work instead of supervising sessions, and when the number of corrections per approved change falls month over month.

**Goals**

- One place to decide: every question, review and proposal from every agent lands in one ordered queue.
- Leads that keep moving between check-ins: open PRs, chase reviewers, update Linear, without a human in the loop until a card is raised.
- Evidence on every card: a diff summary, a recorded demo and a risk note, so a decision takes under a minute.
- A preference loop: approvals and rejections change what agents propose next.
- Scoped blast radius: each lead holds credentials for its own area only.

**Non-goals**

- Agents merging to main or deploying. Humans merge; CI deploys.
- Agents sending email or Slack messages without a draft card.
- Replacing Linear or Notion as the system of record. The queue holds decisions, not roadmap.
- A hosted multi-tenant SaaS. Each company runs its own queue and its own leads inside its own Claude Code; nothing crosses company boundaries, including the preference brain.
- Hierarchy for its own sake. The chief of staff exists only once three or more leads compete for attention.

## System architecture

The queue service is the only thing every agent talks to; the operator, the chief of staff and the leads never address each other directly.

```
                    ┌─────────────────────────────┐
                    │ Operator · Review Queue UI  │
                    └──────────────┬──────────────┘
                          decisions│cards
┌──────────────────┐   ┌──────────▼──────────────┐   ┌──────────────────┐
│ Preference brain │◄──│ Queue service           │◄─►│ Chief of staff   │
│ preferences.md   │   │ SQLite · HTTP · MCP     │   │ prioritize·dedup │
│ decisions.jsonl  │   └──────────┬──────────────┘   │ conflicts·ideas  │
└────────┬─────────┘              │                  └──────────────────┘
         │ loaded by all agents   │ cards / decisions
   ┌─────▼────────┐  ┌────────────▼────┐  ┌──────────────────────┐
   │ Lead: Platform│  │ Lead: Analysis  │  │ Lead: Customer autom.│
   └─────┬────────┘  └────────┬────────┘  └──────────┬───────────┘
         │ dispatch           │                      │
   ┌─────▼────────┐  ┌────────▼────────┐  ┌──────────▼───────────┐
   │ Sub-agents    │  │ Sub-agents      │  │ Sub-agents           │
   │ (worktrees)   │  │ (worktrees)     │  │ (worktrees)          │
   └─────┬────────┘  └────────┬────────┘  └──────────┬───────────┘
         ▼                    ▼                      ▼
   Systems of record: GitHub · CI · Linear · Slack · Notion
```

Leads raise cards into the queue and read decisions back from it. The chief of staff reads the queue and reorders it. The operator clears it. Approvals flow to the preference brain nightly, and every agent loads the brain at wake.

**Components**

| Component | Runs as | Wakes | Owns |
| --- | --- | --- | --- |
| Lead agent (one per area) | Claude Code session, headless, cron | every 2 h in business hours, 6 h overnight | its Linear team, its repos, its Slack channels |
| Sub-agent | Agent tool in a git worktree, spawned by a lead | on dispatch | one issue, one PR |
| Chief of staff | Claude Code session, headless, cron | 30 min after each lead cycle | queue order, idea proposals |
| Queue service | Node or Python service on the operator's box; SQLite | always on | cards, decisions, evidence files |
| Review Queue UI | local web app served by the queue service | on demand | keyboard and voice review |
| Nightly distiller | Claude Code session, cron | 02:00 local | decisions.jsonl → preferences.md |

**Hosting.** Phase 1 runs everything on one machine the operator controls, with the queue bound to localhost and reached from a phone over Tailscale. Leads move to Claude Managed Agents once there are more than three, since Managed Agents already supplies the sandbox and the credential proxy; the queue stays local.

**Data flow for one change.** Lead wakes → picks a Linear issue → dispatches a sub-agent → sub-agent opens a PR and records a demo → lead reviews the PR packet, raises a `review` card → chief of staff ranks it → operator approves → lead requests human review on GitHub and moves the Linear issue → reviewer merges → CI deploys → lead closes the card.

## Lead agents

A lead is a scheduled, headless Claude Code session with one charter, one set of credentials and one job: keep its area moving between check-ins and raise a card only when a human must decide.

**Wake cycle.** Each wake is a fresh session with no memory of the last one; continuity comes from files. On wake the lead:

1. Loads `preferences.md` (shared) and `areas/<area>/STATE.md` (its own running notes).
2. Pulls its Linear team board, open PRs on its repos, unread threads in its Slack channels, and any decisions returned by the queue since last wake.
3. Acts on returned decisions first: approved → request human review, move the issue; rejected → close the PR, file the reason in STATE.md; deferred → snooze.
4. Picks the next work by board priority and dispatches up to N sub-agents (N = 2 to start).
5. Reviews any sub-agent packets that finished, raises `review` cards for the ones that pass its own checks, sends the rest back with notes.
6. Chases: comments on PRs waiting more than 24 h, drafts a Slack nudge card for stalled reviewers.
7. Writes STATE.md and exits. Target wall time per wake: under 20 minutes.

**CLAUDE.md template (one per area)** — see `plugin/templates/area-CLAUDE.md`.

**Sub-agent dispatch.** The lead writes a brief (issue link, acceptance criteria, files likely touched, what not to touch, demo script) and spawns the sub-agent in a worktree with `isolation: worktree`. The lead never edits code itself; that keeps its context small and its judgment on the packets.

**Credentials.** Each lead gets a GitHub App installation scoped to its repos, a Linear API key scoped to its team, and a Slack bot token limited to its channels. Tokens live in the credential proxy, not the session. A lead can read anything in its area and write only through the actions listed in its CLAUDE.md.

**First three areas for Lighty.** Platform (ingest, auth, infra), Analysis engine (workflow reconstruction, causal discovery, report pipeline), Customer automation (per-client automations such as the bank-data pull and the UiPath work). Each maps to an existing Linear team, which is the test for whether an area is ready to have a lead.

## Sub-agents and the demo recorder

A sub-agent does one issue, in one worktree, and ends by handing its lead a PR packet; it never talks to the queue or to a human.

**Brief contract.** Every dispatch carries the same fields, so packets are comparable across leads:

| Field | Content |
| --- | --- |
| issue | Linear issue URL and title |
| acceptance | bullet list the lead will check |
| scope | files or modules expected to change; anything outside is a question back to the lead |
| forbidden | paths never to touch (migrations, auth, billing unless the issue is about them) |
| demo_script | the user-visible path to record: URL, clicks, expected result |
| budget | max tokens and wall time before the sub-agent stops and reports partial |

**Work loop.** Branch from main in a worktree → implement → run the existing test suite → add tests for the change → run the demo recorder → open a draft PR → write the packet → exit. A sub-agent that cannot meet acceptance within budget opens the draft PR anyway and marks the packet `partial`, so the lead sees the attempt rather than nothing.

**PR packet.** Written to `packets/<pr-number>.json` and attached to the draft PR description:

```json
{
  "pr": 412,
  "issue": "LIG-831",
  "status": "ready | partial",
  "summary": "one paragraph, what changed and why",
  "risk": "what could break, who notices, how fast",
  "rollback": "revert PR, no data migration",
  "tests": { "added": 6, "passed": 212, "failed": 0 },
  "demo": { "video": "evidence/412/demo.webm", "stills": ["evidence/412/01.png", "evidence/412/02.png"] },
  "diff_stats": { "files": 7, "added": 180, "removed": 42 }
}
```

**Demo recorder.** A shared skill every sub-agent invokes before opening its PR. It starts the app from the worktree, runs the `demo_script` with Playwright under `recordVideo`, captures a still at each step, and writes everything to `evidence/<pr>/`. The script is Playwright code generated from the brief's demo_script, kept in the PR so a reviewer can re-run it. Recordings are 15 to 60 seconds; the recorder fails the packet if the final expected result is not on screen.

For changes with no UI (a pipeline, an API), the demo is a terminal recording of the before and after against a fixture dataset, produced the same way with `asciinema` and rendered to a short video, so every card has something to watch.

**Lead's acceptance check.** Before raising a card the lead confirms: CI green, every acceptance bullet mapped to a test or a demo step, diff within scope, no forbidden paths touched, packet complete. Packets that fail go back to the same sub-agent with the failures listed; after two returns the lead raises a `decide` card asking whether to continue.

## Chief of staff

The chief of staff never creates work and never touches code; it orders the queue, merges duplicates, flags conflicts between areas, and once a week proposes ideas. It is the only agent with read access to every area's STATE.md.

**Prioritization.** Each new card gets a score from four signals, and the queue is sorted by score then age:

| Signal | Weight | Source |
| --- | --- | --- |
| Customer impact | 40 | Linear issue labels and customer field; a named customer blocked scores highest |
| Reversibility | 25 | packet rollback line; irreversible actions rise so they get fresh attention |
| Staleness | 20 | hours since the card was raised, capped at 48 |
| Operator pattern | 15 | preferences.md: topics the operator has historically answered fast or asked to see first |

The weights are a starting point and live in `queue/config.yaml`; the distiller may propose changes to them as a `decide` card, never apply them.

**Dedup and conflicts.** Two leads can raise cards about the same thing: a shared library bumped in two repos, two PRs editing the same config. The chief of staff compares open cards by linked issues, touched paths and summary embedding; above a similarity threshold it merges them into one card that names both leads and asks a single question. When two open PRs touch the same files it marks both cards `conflict` and adds a line saying which should land first.

**Ideas pass.** Every Monday at 06:00 it reads the week's STATE.md files, closed cards and rejected packets, and raises up to three `idea` cards: recurring friction a lead has logged twice, a rejection pattern that suggests a missing rule, or an issue that keeps bouncing between areas. Ideas are always low in the queue and expire unanswered after seven days.

**Daily brief.** At 07:30 local it writes one `brief` card at the top of the queue: how many cards are waiting by type, what landed yesterday, what is blocked and on whom, and the one thing it recommends the operator look at first. The brief is the only card that is a read, not a decision; dismissing it clears it.

**What it is not allowed to do.** Approve or reject any card. Dispatch sub-agents. Message anyone. Change a lead's CLAUDE.md. Each of those is a card for the operator.

## Review queue

The queue is a SQLite database behind a small service that exposes the same operations twice: as an HTTP API for the UI and as an MCP server for agents. Agents write cards and read decisions; only the UI can write a decision.

**Card types**

| Type | Raised by | Question it asks | Typical evidence |
| --- | --- | --- | --- |
| review | lead | approve this PR for human review? | packet, demo video, diff stats |
| decide | lead or chief of staff | which of these options? | options with trade-offs, a recommendation |
| send | lead | send this message as drafted? | recipient, channel, full text |
| idea | lead or chief of staff | worth putting on the board? | the observation, the proposed issue |
| brief | chief of staff | none; read and dismiss | counts, yesterday, blockers |
| incident | lead | something broke; act or acknowledge? | alert, affected customers, proposed fix |

**Data model** — see `queue/app/schema.sql` (tables `cards`, `decisions`, `events`).

**MCP tools for agents**

| Tool | Who calls it | Effect |
| --- | --- | --- |
| `raise_card(type, title, body_md, options?, evidence?, links?)` | lead, chief of staff | inserts in `raised`; returns id |
| `update_card(id, patch)` | the raising lead | edits body or evidence; a card in `needs_info` moves back to `raised` |
| `list_decisions(area, since)` | lead | decisions on its cards since its last wake |
| `ack_decision(decision_id)` | lead | marks the decision consumed; card moves `approved` → `in_flight` |
| `close_card(id, outcome_md)` | lead | `in_flight` → `done` with what happened |
| `rank(card_id, score, reason)` | chief of staff only | sets score; `raised` → `ranked` |
| `merge_cards(keep_id, drop_ids)` | chief of staff only | dedup |
| `read_queue(filter)` | chief of staff, UI | the ordered list |

Every tool call is an `events` row. The UI's `decide` endpoint is the only writer to `decisions`, and it is not exposed over MCP.

**States**

```
raised ──(CoS ranks)──► ranked ──► [operator] ──approve──► approved ──(lead executes)──► in flight ──► done
                                       │ defer / ask ──► deferred or needs info ──(lead updates)──► raised
                                       └ reject ──► rejected
```

Hard rules: a card in `raised` for more than 48 h without a rank is surfaced at the top anyway, so a chief-of-staff outage cannot hide work. A card the operator has not seen in 7 days expires with a `defer` decision auto-recorded, and the lead learns it was not worth asking.

## Review queue UI

The UI is an inbox, not a dashboard: one ordered list, one card open at a time, and every action one key away. The design target is a decision in under 60 seconds for a review card and under 20 for a send or idea.

The list on the left is the chief of staff's order. The open card shows the question first, then the evidence, then the actions; the demo plays with the space bar and the stills and diff sit below the fold for the cases that need them.

**Card anatomy, top to bottom**

1. Tag line: type, area, age, and the raising agent's recommendation when it has one.
2. Title: the question as a sentence the operator can say yes or no to.
3. Meta line: linked issue, diff stats, CI, tests. For `decide` cards this is replaced by the options with one line of consequence each.
4. Evidence: the demo video first, stills in a strip, then the diff summary and the full risk note. For `send` cards, the exact message text with recipient and channel.
5. Actions: the key bar. Keys are the same on every card type; `?` opens a one-line text box for a question back to the lead.

**Keyboard**

| Key | Action |
| --- | --- |
| J / K | next / previous card |
| A | approve (for `decide`, 1 to 4 picks an option and approves) |
| R | reject; prompts for a one-line reason, required |
| D | defer; snoozes 24 h by default, Shift+D asks how long |
| ? | needs info; types a question to the lead |
| V | hold to talk; released audio is transcribed into the decision note |
| Space | play / pause the demo |
| Enter | open the PR, issue or thread in the browser |
| Shift+A | approve this and every lower-ranked card of the same type from the same lead (batch) |

**Voice.** Holding V records locally; on release, Whisper (local model, no audio leaves the machine) transcribes and the text becomes the decision note. A spoken verdict word at the start ("approve", "reject", "defer", "ask") is parsed as the verdict, so a card can be cleared hands-off. The distiller reads these notes; they are the richest signal it has.

**Batch flow.** The operator opens the queue two or three times a day, not continuously. The daily brief sits on top; clearing it reveals the ranked cards. Cards of the same type from the same lead can be approved together with Shift+A when the first one earns trust. Nothing in the UI nags; there are no notifications beyond an optional morning push with the count.

**Phone.** The same page at phone width shows the list collapsed into a swipe stack: swipe right approves, left rejects, down defers, and V becomes a hold-to-talk button. Review cards with a video are the main phone use case; `decide` cards with long options are flagged "better on desktop" and skipped by default.

**Empty state.** When the queue is empty the page shows yesterday's closed cards and the current preferences file, so the operator can see what the system learned.

## Preference distillation

Every decision is a labeled example of the operator's judgment; the distiller turns them into rules every agent reads at wake, so first drafts need fewer corrections over time.

**Decision log.** The queue appends one line per decision to `brain/decisions.jsonl`: card type, area, the card's recommendation, the verdict, the note (typed or transcribed), the latency, and a hash of the evidence. The log is the raw record and is never edited.

**Nightly distiller.** At 02:00 a scheduled Claude Code session reads the last 30 days of decisions and the current `preferences.md`, and rewrites `preferences.md` under three headings:

1. **Standing rules.** Patterns seen three or more times with no counter-example. Each rule cites the decision ids it came from.
2. **Tendencies.** Patterns with counter-examples, stated with their strength ("11 of 13").
3. **Open questions.** Places where the operator has gone both ways on similar cards; raised as a `decide` card.

The distiller may not delete a standing rule; it marks it `stale` when 30 days pass with no supporting decision, and the operator removes it from the empty-state view. The file stays under 2,000 words; when it grows past that the distiller merges rules rather than appending.

**How agents use it.** Leads read `preferences.md` before writing any card and before accepting any packet; a card that a standing rule would reject is not raised, and the lead sends the packet back citing the rule. The chief of staff uses the tendencies for the operator-pattern score. Sub-agents receive only the rules tagged `code` in their brief.

**Measuring it.** Two numbers in the daily brief: corrections per approved change (decisions with a non-empty note divided by approvals, 7-day rolling) and recommendation agreement (how often the operator's verdict matched the lead's recommendation). The system is working when the first falls and the second rises without the operator approving more blindly, which is why reject rate is shown next to them.

**Portability.** The brain is per company and per operator. A second operator at the same company gets their own `preferences.<name>.md` and the chief of staff routes cards by area ownership; the distiller writes a shared section only for rules both operators have independently produced.

## Guardrails

Agents propose; code vetoes. Every rule here is enforced by a hook or by credential scope, not by instructions in a prompt.

| Risk | Control | Enforced by |
| --- | --- | --- |
| Agent merges or pushes to main | branch protection requires a human review; agents' GitHub App has no merge permission | GitHub |
| Agent sends a message | Slack and email tools are not in any agent's tool set; `send` cards carry the text and the UI sends on approval | tool allowlist, `pre-tool-use` hook |
| Agent touches a forbidden path | hook diffs the worktree against `always_card.paths` before any commit and aborts with a card | `pre-tool-use` hook |
| Over-broad credentials | `/org-setup` checks each token's scope and refuses repo-wide or workspace-wide tokens | setup |
| Runaway spend | per-lead daily token budget in `org.yaml`; the lead stops dispatching when 80% is spent and raises a `brief` line | queue service meters usage from session-end hooks |
| Stuck or looping sub-agent | wall-time and token caps in the brief; the lead kills and reports `partial` | Agent tool budget |
| Prompt injection from PR comments, issues, Slack | all external text is wrapped as data in the lead's context; anything in it that reads as an instruction becomes a card, never an action | lead role prompt plus hook that flags imperative text in fetched content |
| Secrets in evidence | demo recorder redacts env vars and masks fields matching `evidence.redact`; videos are checked with OCR for token-shaped strings before upload | demo-recorder skill |
| Chief of staff hides work | any card unranked for 48 h surfaces at the top | queue service |
| Operator approves blindly | reject rate and agreement rate shown in the brief; Shift+A batch approve requires at least one individually approved card of that type that day | UI |

**Kill switch.** `agent-org pause` sets a flag in the queue; every lead checks it at wake and exits immediately, and the scheduled tasks are disabled. `agent-org pause --area platform` pauses one lead. Resume is the same command. The flag is also a button in the UI top bar.

**Shadow mode.** New deployments and new areas start in shadow for two days: leads raise cards but dispatch nothing and the chief of staff ranks as normal. The operator sees what would have happened and approves leaving shadow with a `decide` card.

**Audit.** The `events` table is append-only and exported nightly to the company's own storage as JSON lines. Every card links to the events that produced it, so a reviewer can reconstruct why a PR was proposed and who approved it.

## Packaging and deployment to other companies

The system is a Claude Code plugin named `agent-org` plus a queue service container; installing it at a new company is a config file and one command, and no company-specific logic lives in the plugin.

**Plugin layout** — see `plugin/` in this repo.

The queue service is a separate container (`agent-org-queue`), because it must stay up between sessions and hold the SQLite file and evidence directory. It runs on a box the company controls; the plugin only needs its URL and a token.

**Per-company config (`org.yaml`)** — see `plugin/templates/org.yaml.example` and `deployments/<company>/`.

`/org-setup` writes this file by interviewing the operator and reading what is already connected (Linear teams, GitHub repos the app can see, Slack channels), then generates one `areas/<key>/CLAUDE.md` from the template. Changing an area later is editing the yaml and re-running setup.

**Install at a new company**

1. Company adds the plugin from the marketplace (private marketplace first; public later) and runs `/org-setup`.
2. They stand up `agent-org-queue` with `docker compose up` on an operator-controlled machine and paste its URL and token into setup.
3. They install the GitHub App and create a Linear key and Slack bot per area; setup checks each credential against its scope and refuses over-broad ones.
4. Setup registers the scheduled tasks for each lead, the chief of staff and the distiller.
5. First wake runs in `shadow` mode: leads raise cards but dispatch nothing, so the operator sees what the system would have done for two days before anything moves.

**What varies by company and how it is handled**

| Variation | Where it lives | Lighty | Second company | Third company |
| --- | --- | --- | --- | --- |
| Issue tracker | `trackers.issues` adapter | Linear | to confirm | to confirm |
| Chat | `trackers.chat` adapter | Slack | to confirm | to confirm |
| Regulated data in evidence | `evidence.redact` rules | none | likely: regulated data in demos must be synthetic fixtures only | to confirm |
| Operator count | `operators[]`; cards can route to a named person | 1 | fractional CTO plus internal lead | to confirm |
| Hosting of the queue | company's box or Managed Agents | local, Tailscale | company VPC | to confirm |

Adapters are the only code that knows a vendor. The first release ships Linear, GitHub and Slack; Jira and Teams adapters are the first thing a second company will need, and they are small because each adapter implements five calls: list work, read item, update status, comment, list threads.

**Tenant isolation.** One company's `preferences.md`, decisions and evidence never leave its queue. The plugin collects no telemetry by default; an opt-in `metrics` flag reports counts only (cards per day, decision latency, corrections per change) to a Lighty endpoint, so we can compare deployments without seeing content.

**Versioning.** The plugin and the queue service share a version. `/org-setup` refuses to run against a queue more than one minor version apart, and the queue migrates its schema forward on start.

## Build plan

Five phases over twelve weeks, each ending at a gate the operator can see in the queue itself; nothing in a later phase starts until its gate is passed.

| Phase | Deliverables | Gate |
| --- | --- | --- |
| 1. Queue + lead 1 (weeks 1–2) | queue service with SQLite, MCP server, HTTP API; inbox UI with keyboard; Platform lead CLAUDE.md and cron; shadow mode | Platform lead raising and executing real cards at Lighty for 5 consecutive business days |
| 2. Packets + CoS (weeks 3–4) | demo-recorder skill; packet contract and acceptance check; Analysis and Customer-automation leads; chief of staff ranking, dedup, daily brief | three leads live; operator reports the brief is the first thing opened in the morning |
| 3. Brain + plugin (weeks 5–6) | nightly distiller; corrections and agreement metrics in the brief; `agent-org` plugin with `/org-setup`; private marketplace; voice input | fresh install on a clean Lighty machine in under one day by someone other than the author |
| 4. Second company (weeks 7–10) | second company's deployment; adapters their stack needs; evidence redaction rules; second-operator routing | their lead live and their operator clearing cards without us on the call |
| 5. Third company (weeks 11–12) | third company's deployment; adapter gaps closed; decision on public marketplace listing | third company live; go/no-go on public listing with pricing |

**Success metrics** (shown in the daily brief from phase 3)

- Cards per operator-hour cleared: target 20 or more for review cards.
- Median decision latency: under 60 s for review, under 20 s for send and idea.
- Corrections per approved change: falling week over week after the distiller ships.
- Recommendation agreement: above 80% by week 8, with reject rate not below 10%.
- Time to install at a new company: under one day by phase 4.

**Staffing.** One engineer full time on the queue and plugin, with the author as the first operator. Leads are configured, not coded, so adding an area is an afternoon once the plugin exists.

## Open questions and prior art

**Open questions**

- [ ] Which Claude Code primitive runs the leads in phase 1: scheduled tasks against a cloud environment, or a cron on the operator's machine? Decide before week 1.
- [ ] Do the second and third companies use Linear or Jira, Slack or Teams? This sets the adapter order for phase 4.
- [ ] Should sub-agents run on a cheaper model than leads by default? Likely yes for implement-and-test; measure packet return rate before deciding.
- [ ] Where does the demo recorder run for apps with no local dev server? Probably a per-area `docker compose` the brief points at; confirm per company.
- [ ] How is the plugin licensed and priced for the second and third companies?
- [ ] Does the distiller need a human review step before rules go live, or is marking rules `stale` and showing them in the empty state enough?

**Prior art this spec borrows from**

| Source | What we take | What we leave |
| --- | --- | --- |
| [Brian Armstrong's setup](https://x.com/brian_armstrong/status/2119112609223827547) | leads per area, chief of staff, one queue, video on every review, voice clearing, preference brain | nothing specified publicly about implementation |
| [appletechie/agent-chief-of-staff](https://github.com/appletechie/agent-chief-of-staff) | durable ledger, duplicate-dispatch guard, merge gate, cheap polling that only wakes the model on change | its own ledger format; we use the queue's SQLite |
| [Arnold Wang's review queue](https://dev.to/arnold_wang_dfbbb991be9ff/my-agents-ran-in-parallel-i-didnt-2enh) | one card per waiting item, oldest first; model proposes, code vetoes; cheap triage | the DSH harness |
| [Kortix CompanyOS](https://kortix.com/blog/how-to-run-a-company-with-ai-agents) | size the org by review capacity; every agent's output lands on one named person | per-agent Linux users and gateways |
| [Claude Code agent teams](https://theexcitedengineer.substack.com/p/claude-agent-teams-why-ai-coding) | team lead spawning teammates, file-backed task list and mailbox | persistent teammates; ours are short-lived |
| [Coinbase "update the brain, not the draft"](https://www.the-ai-corner.com/p/brian-armstrong-coinbase-1200-ai-agents-operating-model-2026) | lessons encoded as markdown in the repo, read by every agent | nothing |
| Claude Duet and OpenAI Dots | the approval-gate and always-on patterns operators now expect | single-agent model; no hierarchy or cross-agent queue today |
