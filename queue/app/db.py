import os, sqlite3, pathlib
DB = os.environ.get("AGENT_ORG_DB", "data/queue.sqlite")

def connect() -> sqlite3.Connection:
    pathlib.Path(DB).parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB, check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    return c

def migrate(c: sqlite3.Connection) -> None:
    c.executescript((pathlib.Path(__file__).parent / "schema.sql").read_text())
