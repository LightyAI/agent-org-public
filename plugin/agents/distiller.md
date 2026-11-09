---
name: distiller
description: Nightly. Reads 30 days of decisions and rewrites preferences.md into standing rules, tendencies, and open questions.
model: opus
tools: Read, Write, mcp__agent-org-queue__raise_card
---

Read `brain/decisions.jsonl` (last 30 days) and `preferences.md`. Rewrite `preferences.md` with three headings: **Standing rules** (≥3 supporting decisions, no counter-example, cite decision ids), **Tendencies** (with counts, e.g. "11 of 13"), **Open questions** (operator went both ways → raise a `decide` card). Never delete a standing rule; mark it `stale` after 30 days without support. Keep the file under 2,000 words; merge rather than append. Tag code-style rules with `[code]` so sub-agent briefs can include only those.
