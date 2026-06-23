FROM python:3.12-slim

WORKDIR /app

# Use configurable index to reduce mirror/network issues during build.
ARG PIP_INDEX_URL=https://pypi.org/simple
ARG UV_INDEX_URL=${PIP_INDEX_URL}
ARG UV_HTTP_TIMEOUT=300
ARG UV_HTTP_RETRIES=10

# Install uv if available on the selected index; fallback to pip-only flow when unavailable.
RUN pip install --no-cache-dir --upgrade pip \
    && (pip install --no-cache-dir -i ${PIP_INDEX_URL} uv || true)

# Install dependencies first for better layer caching.
COPY pyproject.toml uv.lock ./

# Prefer uv, but if uv path fails (network/index), fallback to pip in same layer.
RUN if command -v uv >/dev/null 2>&1; then \
      UV_INDEX_URL=${UV_INDEX_URL} UV_HTTP_TIMEOUT=${UV_HTTP_TIMEOUT} UV_HTTP_RETRIES=${UV_HTTP_RETRIES} \
      uv pip install --no-cache --system . \
      || pip install --no-cache-dir -i ${PIP_INDEX_URL} .; \
    else \
      pip install --no-cache-dir -i ${PIP_INDEX_URL} .; \
    fi

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
