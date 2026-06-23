FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
      fastapi>=0.115.0 \
      graphiti-core>=0.28.1 \
      pydantic-settings>=2.4.0 \
      uvicorn>=0.30.6 \
      httpx>=0.28.1

RUN git clone --depth 1 https://github.com/getzep/graphiti /tmp/graphiti-src

WORKDIR /app
RUN cp -r /tmp/graphiti-src/server/graph_service /app/graph_service

COPY deploy/graphiti/zep_graphiti.py /app/graph_service/zep_graphiti.py
COPY deploy/graphiti/ingest.py /app/graph_service/routers/ingest.py

ENV PYTHONUNBUFFERED=1 \
    PORT=8000

EXPOSE 8000

CMD ["uvicorn", "graph_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
