// MCP server: thin proxy over the queue's HTTP API. `decide` is deliberately absent.
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const URL = process.env.AGENT_ORG_QUEUE_URL ?? "http://127.0.0.1:7340";
const TOKEN = process.env.AGENT_ORG_QUEUE_TOKEN ?? "";
const AREA = process.env.AGENT_ORG_AREA ?? "unknown";

async function api(method: string, path: string, body?: unknown) {
  const r = await fetch(URL + path, {
    method, headers: { "Authorization": `Bearer ${TOKEN}`, "Content-Type": "application/json", "X-Agent-Org-Actor": `lead:${AREA}` },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) throw new Error(`${method} ${path} → ${r.status} ${await r.text()}`);
  return r.json();
}
const text = (v: unknown) => ({ content: [{ type: "text" as const, text: JSON.stringify(v, null, 2) }] });

const s = new McpServer({ name: "agent-org-queue", version: "0.1.0" });

s.tool("raise_card", "Raise a card for the operator.", {
  type: z.enum(["review", "decide", "send", "idea", "brief", "incident"]),
  title: z.string(), body_md: z.string(),
  options: z.array(z.object({ key: z.string(), label: z.string(), consequence: z.string() })).optional(),
  recommended: z.string().optional(),
  evidence: z.array(z.object({ kind: z.enum(["video", "image", "diff", "log"]), path: z.string(), caption: z.string().optional() })).optional(),
  links: z.array(z.string()).optional(),
}, async (a) => text(await api("POST", "/api/cards", { ...a, area: AREA })));

s.tool("update_card", "Edit a card you raised.", { id: z.string(), patch: z.record(z.unknown()) },
  async ({ id, patch }) => text(await api("PATCH", `/api/cards/${id}`, patch)));
s.tool("list_decisions", "Decisions on this area's cards since a timestamp.", { since: z.string().optional() },
  async ({ since }) => text(await api("GET", `/api/decisions?area=${AREA}&since=${since ?? ""}`)));
s.tool("ack_decision", "Mark a decision consumed; card → in_flight.", { decision_id: z.string() },
  async ({ decision_id }) => text(await api("POST", `/api/decisions/${decision_id}/ack`)));
s.tool("close_card", "in_flight → done.", { id: z.string(), outcome_md: z.string() },
  async ({ id, outcome_md }) => text(await api("POST", `/api/cards/${id}/close`, { outcome_md })));
s.tool("rank", "Chief of staff only. Set score; raised → ranked.", { card_id: z.string(), score: z.number(), reason: z.string() },
  async (a) => text(await api("POST", `/api/cards/${a.card_id}/rank`, a)));
s.tool("merge_cards", "Chief of staff only. Dedup.", { keep_id: z.string(), drop_ids: z.array(z.string()) },
  async (a) => text(await api("POST", "/api/cards/merge", a)));
s.tool("read_queue", "Ordered queue.", { state: z.string().optional(), area: z.string().optional() },
  async (f) => text(await api("GET", `/api/queue?state=${f.state ?? ""}&area=${f.area ?? ""}`)));

await s.connect(new StdioServerTransport());
