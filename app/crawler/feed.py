import os
import hashlib
import feedparser
import httpx
from pathlib import Path
from datetime import datetime
from app.config import settings

RSS_STORE_DIR = "./data/rss"


def _fetch_entries(feed_url: str) -> list[dict]:
    """拉取 RSS 条目"""
    try:
        resp = httpx.get(feed_url, timeout=30, follow_redirects=True)
        resp.raise_for_status()
    except Exception:
        return []

    feed = feedparser.parse(resp.text)
    entries = []
    for entry in feed.entries:
        title = entry.get("title", "未命名")
        summary = entry.get("summary", entry.get("description", ""))
        link = entry.get("link", "")

        content = f"# {title}\n\n来源：{link}\n\n{summary}"
        entry_id = hashlib.md5(content.encode()).hexdigest()

        entries.append({"id": entry_id, "content": content, "title": title})
    return entries


def fetch_feeds() -> int:
    """抓取所有 RSS 源，将新文章保存为 Markdown 文件并入库，返回新增篇数"""
    feed_urls = [u.strip() for u in settings.rss_feeds.split(",") if u.strip()]
    if not feed_urls:
        return 0

    os.makedirs(RSS_STORE_DIR, exist_ok=True)
    new_count = 0

    for feed_url in feed_urls:
        entries = _fetch_entries(feed_url)
        for entry in entries:
            filepath = Path(RSS_STORE_DIR) / f"{entry['id']}.md"
            if filepath.exists():
                continue  # 已存在，跳过

            filepath.write_text(entry["content"], encoding="utf-8")
            try:
                from app.rag.loader import index_document
                index_document(str(filepath))
                new_count += 1
            except Exception:
                pass

    return new_count


def start_scheduler():
    """启动定时爬虫任务"""
    from apscheduler.schedulers.background import BackgroundScheduler

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        fetch_feeds,
        "interval",
        hours=settings.crawl_schedule_hours,
        id="rss_crawler",
        replace_existing=True,
    )
    scheduler.start()
