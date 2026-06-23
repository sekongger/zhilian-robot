FROM python:3.10-slim

ENV TZ=Asia/Shanghai
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

COPY modules/kag /app/modules/kag
COPY deploy/kag-mcp/entrypoint.sh /app/deploy/kag-mcp/entrypoint.sh
COPY deploy/kag-mcp/kag_config.yaml.tmpl /app/deploy/kag-mcp/kag_config.yaml.tmpl

RUN python -m pip install --upgrade pip setuptools wheel && \
    python -m pip install -e /app/modules/kag -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com || \
    python -m pip install -e /app/modules/kag

RUN chmod +x /app/deploy/kag-mcp/entrypoint.sh && \
    mkdir -p /app/runtime && \
    chown -R appuser:appuser /app

USER appuser

WORKDIR /app/runtime

EXPOSE 3000

ENTRYPOINT ["/app/deploy/kag-mcp/entrypoint.sh"]
