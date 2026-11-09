---
name: demo-recorder
description: Record a 15–60 s demo of a change to evidence/<pr>/ with Playwright (UI) or asciinema (no UI). Fails the packet if the final expected result is not on screen.
---

UI: start the app from the worktree; generate a Playwright script from the brief's `demo_script`; run with `recordVideo` + a screenshot per step → `evidence/<pr>/demo.webm`, `01.png…`. Commit the script to the PR so reviewers can re-run it.
No UI: `asciinema rec` a before/after against a fixture dataset; render to webm with `agg`.
Redact env vars and fields matching `evidence.redact`; OCR frames for token-shaped strings before writing the packet.
