.PHONY: dev test
dev:
	uv run uvicorn app.main:app --host 127.0.0.1 --port 7340 --reload
test:
	uv run pytest -q
