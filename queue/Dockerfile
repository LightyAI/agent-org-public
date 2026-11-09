FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir uv && uv sync --no-dev
COPY app ./app
VOLUME ["/data"]
ENV AGENT_ORG_DB=/data/queue.sqlite AGENT_ORG_EVIDENCE=/data/evidence
EXPOSE 7340
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7340"]
