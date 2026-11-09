---
name: pr-packet
description: Write packets/<pr>.json and run the lead's acceptance check. Use by sub-agents before opening a PR and by leads before raising a review card.
---

Packet schema: `pr, issue, status (ready|partial), summary, risk, rollback, tests{added,passed,failed}, demo{video,stills[]}, diff_stats{files,added,removed}`.
Acceptance (lead): CI green · every acceptance bullet maps to a test or demo step · diff within scope · no forbidden paths · packet complete. Any miss → return to sub-agent with the list.
