"""
全局配置管理
"""

import os
from pathlib import Path

# 项目根目录（backend/ 上级目录）— 同时支持 backend/ 内运行和项目根运行
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = str(Path(BASE_DIR).parent)

# 尝试加载 .env 文件
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
except ImportError:
    pass

# DeepSeek API 配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "glm-5.2")

# 数据库配置（默认 SQLite，本地演示用；部署时设 DATABASE_URL 环境变量切换 MySQL）
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{os.path.join(BASE_DIR, 'data', 'jobcopilot.db')}",
)

# ChromaDB配置
CHROMA_DIR = os.getenv("CHROMA_DIR", os.path.join(BASE_DIR, "data", "chroma_db"))

# Redis 配置（缓存 + Celery 消息队列）
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# CORS配置
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
