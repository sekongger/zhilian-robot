# 生产阶段 - 直接使用预编译包，无需编译器
FROM python:3.11-slim

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 创建非root用户
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 复制依赖文件
COPY backend/requirements.txt /app/backend/requirements.txt
COPY backend/requirements-openks.txt /app/backend/requirements-openks.txt
COPY supxmind/supxmind-openks /app/supxmind/supxmind-openks

# 安装Python依赖（优先使用预编译的二进制轮子）
# 使用阿里云镜像加速下载，失败则使用官方PyPI
RUN pip install --upgrade pip && \
    pip install -r /app/backend/requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com || \
    pip install -r /app/backend/requirements.txt && \
    pip install -r /app/backend/requirements-openks.txt && \
    pip install ruamel.yaml cachetools

# 复制应用代码
COPY --chown=appuser:appuser backend /app/backend
COPY --chown=appuser:appuser supxmind /app/supxmind
COPY --chown=appuser:appuser modules /app/modules

# 后端代码工作目录
WORKDIR /app/backend

# 切换到非root用户
USER appuser

# 暴露端口
EXPOSE 8000

# 健康检查（使用Python内置库，不依赖外部工具）
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=5)" || exit 1

# 启动命令：先等待数据库就绪，再启动应用
CMD ["sh", "-c", "python wait_for_db.py && uvicorn main:app --host 0.0.0.0 --port 8000"]
