from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM
    llm_base_url: str = "https://cloud.hongqiye.com/v1"
    llm_api_key: str = ""
    llm_model: str = "glm-5.2"

    # Embedding
    embedding_model: str = "BAAI/bge-small-zh-v1.5"

    # ChromaDB
    chroma_persist_dir: str = "./data/chroma"

    # 飞书
    feishu_app_id: str = ""
    feishu_app_secret: str = ""
    feishu_verify_token: str = ""
    feishu_encrypt_key: str = ""

    # 爬虫
    crawl_schedule_hours: int = 6
    rss_feeds: str = ""

    # 日志
    log_dir: str = "./logs"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
