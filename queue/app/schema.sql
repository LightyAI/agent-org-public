CREATE TABLE IF NOT EXISTS cards (
  id            TEXT PRIMARY KEY,
  type          TEXT NOT NULL,
  area          TEXT NOT NULL,
  title         TEXT NOT NULL,
  body_md       TEXT NOT NULL,
  options_json  TEXT,
  recommended   TEXT,
  links_json    TEXT,
  evidence_json TEXT,
  score         REAL,
  state         TEXT NOT NULL DEFAULT 'raised',
  merged_into   TEXT,
  raised_at     TEXT NOT NULL,
  snooze_until  TEXT,
  expires_at    TEXT
);
CREATE TABLE IF NOT EXISTS decisions (
  id          TEXT PRIMARY KEY,
  card_id     TEXT NOT NULL REFERENCES cards(id),
  verdict     TEXT NOT NULL,
  note        TEXT,
  latency_s   INTEGER,
  acked_at    TEXT,
  decided_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  card_id   TEXT,
  actor     TEXT NOT NULL,
  kind      TEXT NOT NULL,
  data_json TEXT,
  at        TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS flags (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_cards_state ON cards(state, score DESC, raised_at);
