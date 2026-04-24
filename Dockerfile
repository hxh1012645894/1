# ============================================================
# FastAPI 后端服务 Dockerfile
# 基础镜像: python:3.12-slim
# 生产运行: gunicorn + uvicorn.workers.UvicornWorker (多进程守护)
# ============================================================

FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
# PYTHONDONTWRITEBYTECODE: 防止 Python 生成 .pyc 文件
# PYTHONUNBUFFERED: 确保 Python 输出直接打印到终端
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖
# libgl1: PIL/Pillow 图像处理依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn

# 复制应用代码
COPY main.py .
COPY processor.py .

# 创建必要的数据目录
# 这些目录将通过 Volume 持久化
RUN mkdir -p /app/uploads /app/processed /app/logs /app/data

# 暴露端口
EXPOSE 8001

# 启动命令
# 使用 gunicorn 管理 uvicorn workers，支持多进程
# workers 数量建议: (2 * CPU核心数) + 1
# bind: 监听所有网络接口的 8001 端口
# worker-class: 使用 uvicorn 的异步 worker
# timeout: worker 超时时间（秒）
CMD ["gunicorn", \
    "--bind", "0.0.0.0:8001", \
    "--workers", "4", \
    "--worker-class", "uvicorn.workers.UvicornWorker", \
    "--timeout", "120", \
    "--keep-alive", "5", \
    "--access-logfile", "-", \
    "--error-logfile", "-", \
    "main:app"]