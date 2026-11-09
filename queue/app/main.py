"""Queue service: HTTP API for the UI and the MCP proxy. `decide` is UI-only and never reaches MCP."""
import json, os, datetime as dt
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from ulid import ULID
from . import db

TOKEN = os.environ.get("AGENT_ORG_TOKEN", "dev")
app = FastAPI(title="agent-org-queue", version="0.1.0")
conn = db.connect(); db.migrate(conn)
now = lambda: dt.datetime.now(dt.timezone.utc).isoformat()

def auth(authorization: str | None):
    if authorization != f"Bearer {TOKEN}": raise HTTPException(401)

def event(card_id, actor, kind, data=None):
    conn.execute("INSERT INTO events(card_id,actor,kind,data_json,at) VALUES(?,?,?,?,?)",
                 (card_id, actor, kind, json.dumps(data or {}), now())); conn.commit()

def row(r): return dict(r) if r else None

@app.post("/api/cards")
async def raise_card(req: Request, authorization: str | None = Header(None), x_agent_org_actor: str = Header("unknown")):
    auth(authorization); b = await req.json()
    if conn.execute("SELECT value FROM flags WHERE key='paused'").fetchone(): raise HTTPException(423, "paused")
    cid = str(ULID())
    conn.execute("""INSERT INTO cards(id,type,area,title,body_md,options_json,recommended,links_json,evidence_json,state,raised_at,expires_at)
        VALUES(?,?,?,?,?,?,?,?,?,'raised',?,?)""",
        (cid, b["type"], b["area"], b["title"], b["body_md"], json.dumps(b.get("options")), b.get("recommended"),
         json.dumps(b.get("links")), json.dumps(b.get("evidence")), now(),
         (dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=7)).isoformat()))
    event(cid, x_agent_org_actor, "raised", b); return {"id": cid}

@app.get("/api/queue")
def read_queue(state: str = "", area: str = "", authorization: str | None = Header(None)):
    auth(authorization)
    q = "SELECT * FROM cards WHERE merged_into IS NULL"; p = []
    if state: q += " AND state=?"; p.append(state)
    else: q += " AND state IN ('raised','ranked')"
    if area: q += " AND area=?"; p.append(area)
    # unranked > 48h surface at top regardless of score
    q += """ ORDER BY CASE WHEN state='raised' AND raised_at < datetime('now','-48 hours') THEN 0 ELSE 1 END,
               CASE WHEN type='brief' THEN 0 ELSE 1 END, score DESC NULLS LAST, raised_at"""
    return [row(r) for r in conn.execute(q, p)]

@app.get("/api/cards/{cid}")
def get_card(cid: str, authorization: str | None = Header(None)):
    auth(authorization); r = conn.execute("SELECT * FROM cards WHERE id=?", (cid,)).fetchone()
    if not r: raise HTTPException(404)
    return row(r)

@app.patch("/api/cards/{cid}")
async def update_card(cid: str, req: Request, authorization: str | None = Header(None), x_agent_org_actor: str = Header("unknown")):
    auth(authorization); patch = await req.json()
    allowed = {"title","body_md","options_json","recommended","links_json","evidence_json"}
    sets = {k: (json.dumps(v) if k.endswith("_json") else v) for k, v in patch.items() if k in allowed}
    if sets:
        conn.execute(f"UPDATE cards SET {','.join(k+'=?' for k in sets)}, state=CASE WHEN state='needs_info' THEN 'raised' ELSE state END WHERE id=?",
                     (*sets.values(), cid))
    event(cid, x_agent_org_actor, "updated", patch); return get_card(cid, authorization)

@app.post("/api/cards/{cid}/rank")
async def rank(cid: str, req: Request, authorization: str | None = Header(None)):
    auth(authorization); b = await req.json()
    conn.execute("UPDATE cards SET score=?, state=CASE WHEN state='raised' THEN 'ranked' ELSE state END WHERE id=?", (b["score"], cid))
    event(cid, "cos", "ranked", b); return get_card(cid, authorization)

@app.post("/api/cards/merge")
async def merge(req: Request, authorization: str | None = Header(None)):
    auth(authorization); b = await req.json()
    for d in b["drop_ids"]:
        conn.execute("UPDATE cards SET merged_into=? WHERE id=?", (b["keep_id"], d)); event(d, "cos", "merged", b)
    conn.commit(); return {"ok": True}

@app.post("/api/decide/{cid}")
async def decide(cid: str, req: Request, authorization: str | None = Header(None)):
    """UI only. verdict: approve | reject | defer | needs_info | pick:<key>"""
    auth(authorization); b = await req.json(); v = b["verdict"]
    state = {"approve": "approved", "reject": "rejected", "defer": "deferred", "needs_info": "needs_info"}.get(v.split(":")[0], "approved")
    did = str(ULID())
    conn.execute("INSERT INTO decisions(id,card_id,verdict,note,latency_s,decided_at) VALUES(?,?,?,?,?,?)",
                 (did, cid, v, b.get("note"), b.get("latency_s"), now()))
    conn.execute("UPDATE cards SET state=?, snooze_until=? WHERE id=?",
                 (state, (dt.datetime.now(dt.timezone.utc)+dt.timedelta(hours=b.get("snooze_h", 24))).isoformat() if state=="deferred" else None, cid))
    event(cid, "operator", "decided", b)
    with open(os.environ.get("AGENT_ORG_BRAIN", "data/decisions.jsonl"), "a") as f:
        card = get_card(cid, authorization)
        f.write(json.dumps({"id": did, "card_id": cid, "type": card["type"], "area": card["area"],
                            "recommended": card["recommended"], "verdict": v, "note": b.get("note"),
                            "latency_s": b.get("latency_s"), "at": now()}) + "\n")
    return {"id": did}

@app.get("/api/decisions")
def list_decisions(area: str = "", since: str = "", authorization: str | None = Header(None)):
    auth(authorization)
    return [row(r) for r in conn.execute("""SELECT d.*, c.area FROM decisions d JOIN cards c ON c.id=d.card_id
        WHERE (?='' OR c.area=?) AND (?='' OR d.decided_at>?) AND d.acked_at IS NULL ORDER BY d.decided_at""", (area, area, since, since))]

@app.post("/api/decisions/{did}/ack")
def ack(did: str, authorization: str | None = Header(None), x_agent_org_actor: str = Header("unknown")):
    auth(authorization)
    conn.execute("UPDATE decisions SET acked_at=? WHERE id=?", (now(), did))
    conn.execute("UPDATE cards SET state='in_flight' WHERE state='approved' AND id=(SELECT card_id FROM decisions WHERE id=?)", (did,))
    event(None, x_agent_org_actor, "acked", {"decision_id": did}); return {"ok": True}

@app.post("/api/cards/{cid}/close")
async def close(cid: str, req: Request, authorization: str | None = Header(None), x_agent_org_actor: str = Header("unknown")):
    auth(authorization); b = await req.json()
    conn.execute("UPDATE cards SET state='done' WHERE id=?", (cid,)); event(cid, x_agent_org_actor, "closed", b); return {"ok": True}

@app.post("/api/events")
async def post_event(req: Request, authorization: str | None = Header(None)):
    auth(authorization); b = await req.json(); event(b.get("card_id"), b["actor"], b["kind"], b.get("data")); return {"ok": True}

@app.post("/api/pause")
def pause(on: bool = True, authorization: str | None = Header(None)):
    auth(authorization)
    if on: conn.execute("INSERT OR REPLACE INTO flags VALUES('paused','1')")
    else: conn.execute("DELETE FROM flags WHERE key='paused'")
    conn.commit(); event(None, "operator", "pause" if on else "resume"); return {"paused": on}

@app.get("/", response_class=HTMLResponse)
def ui():
    return (__import__("pathlib").Path(__file__).parent / "ui" / "index.html").read_text()
