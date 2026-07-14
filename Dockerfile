FROM docker.m.daocloud.io/library/python:3.11-slim

# HuggingFace 镜像（国内镜像）
ENV HF_ENDPOINT=https://hf-mirror.com

WORKDIR /app

# 系统依赖
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# PyTorch CPU 版本（先于 sentence-transformers 安装，避免拉取 CUDA 依赖）
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 源码
COPY app/ ./app/

# 预下载 Embedding 模型
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-zh-v1.5')"

# 创建数据和日志目录
RUN mkdir -p data logs

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
