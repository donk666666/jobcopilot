"""
Redis 缓存层 — LLM 分析结果缓存 + RAG 检索结果缓存

Redis 不可用时静默降级：写缓存直接 return，读缓存返回 None。
"""

import hashlib
import json
import logging
from typing import Optional, Any

from config import REDIS_URL

logger = logging.getLogger("jobcopilot.cache")

_redis = None
_redis_available: Optional[bool] = None


def _get_redis():
    """延迟初始化 Redis 连接，失败则标记不可用"""
    global _redis, _redis_available
    if _redis_available is not None:
        return _redis if _redis_available else None

    try:
        import redis as redis_lib

        _redis = redis_lib.Redis.from_url(
            REDIS_URL,
            socket_connect_timeout=2,
            socket_timeout=2,
            decode_responses=True,
        )
        _redis.ping()
        _redis_available = True
        logger.info("Redis 连接成功")
        return _redis
    except Exception as e:
        _redis_available = False
        logger.warning(f"Redis 不可用，缓存功能降级: {e}")
        return None


def _make_key(prefix: str, *args: str) -> str:
    joined = "|".join(args)
    digest = hashlib.md5(joined.encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


def get_redis_status() -> dict:
    r = _get_redis()
    if r is not None:
        return {"available": True}
    return {"available": False, "error": "Redis 连接不可用"}


# ---- LLM 缓存 ----

def cache_llm_result(jd_text: str, resume_text: str, operation: str, result: Any) -> None:
    r = _get_redis()
    if r is None:
        return
    try:
        key = _make_key("llm", jd_text, resume_text, operation)
        r.setex(key, 3600, json.dumps(result, ensure_ascii=False))
    except Exception as e:
        logger.warning(f"LLM 缓存写入失败: {e}")


def get_cached_llm(jd_text: str, resume_text: str, operation: str) -> Optional[Any]:
    r = _get_redis()
    if r is None:
        return None
    try:
        key = _make_key("llm", jd_text, resume_text, operation)
        val = r.get(key)
        return json.loads(val) if val else None
    except Exception as e:
        logger.warning(f"LLM 缓存读取失败: {e}")
        return None


# ---- RAG 缓存 ----

def cache_rag_result(query: str, result: str) -> None:
    r = _get_redis()
    if r is None:
        return
    try:
        key = _make_key("rag", query)
        r.setex(key, 1800, result)
    except Exception as e:
        logger.warning(f"RAG 缓存写入失败: {e}")


def get_cached_rag(query: str) -> Optional[str]:
    r = _get_redis()
    if r is None:
        return None
    try:
        key = _make_key("rag", query)
        return r.get(key)
    except Exception as e:
        logger.warning(f"RAG 缓存读取失败: {e}")
        return None


def invalidate(pattern: str) -> None:
    r = _get_redis()
    if r is None:
        return
    try:
        keys = r.keys(pattern)
        if keys:
            r.delete(*keys)
    except Exception as e:
        logger.warning(f"缓存清除失败: {e}")
