import os, tempfile
os.environ["AGENT_ORG_DB"] = tempfile.mktemp(suffix=".sqlite")
os.environ["AGENT_ORG_BRAIN"] = tempfile.mktemp(suffix=".jsonl")
from fastapi.testclient import TestClient
from app.main import app
H = {"Authorization": "Bearer dev", "X-Agent-Org-Actor": "lead:platform"}
c = TestClient(app)

def test_card_lifecycle():
    cid = c.post("/api/cards", headers=H, json={"type":"review","area":"platform","title":"PR 1?","body_md":"x"}).json()["id"]
    assert c.get("/api/queue", headers=H).json()[0]["id"] == cid
    c.post(f"/api/cards/{cid}/rank", headers=H, json={"score": 80, "reason": "t"})
    did = c.post(f"/api/decide/{cid}", headers=H, json={"verdict":"approve","note":"ok","latency_s":12}).json()["id"]
    d = c.get("/api/decisions?area=platform", headers=H).json(); assert d and d[0]["id"] == did
    c.post(f"/api/decisions/{did}/ack", headers=H)
    assert c.get(f"/api/cards/{cid}", headers=H).json()["state"] == "in_flight"
    c.post(f"/api/cards/{cid}/close", headers=H, json={"outcome_md":"merged"})
    assert c.get(f"/api/cards/{cid}", headers=H).json()["state"] == "done"

def test_decide_not_in_mcp_surface():
    # the MCP server source must never reference the decide endpoint
    src = open(os.path.join(os.path.dirname(__file__), "../../plugin/mcp/queue-server/src/index.ts")).read()
    assert "/api/decide" not in src
