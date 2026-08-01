"""
数据库模型 — SQLAlchemy ORM（MySQL）
"""

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, JSON, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone
from config import DATABASE_URL
from urllib.parse import urlparse

# 自动建库（MySQL 需要先有库才能建表；SQLite 自动创建，跳过）
parsed = urlparse(DATABASE_URL)
if parsed.scheme in ("mysql+pymysql", "mysql"):
    db_name = parsed.path.lstrip("/")
    admin_url = DATABASE_URL.replace(f"/{db_name}", "/") if db_name else DATABASE_URL
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        conn.execute(
            text(f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                 f"DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        )
    admin_engine.dispose()

engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ----- JD分析记录 -----

class JDAnalysis(Base):
    __tablename__ = "jd_analyses"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    position_title = Column(String(200), nullable=True, comment="职位名称")
    company_name = Column(String(200), nullable=True, comment="公司名称")
    jd_raw = Column(Text, nullable=False, comment="原始JD文本")
    analysis_json = Column(Text, nullable=False, comment="分析结果JSON字符串")
    match_weight = Column(Text, nullable=True, comment="评分权重JSON")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ----- 投递记录 -----

class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    company_name = Column(String(200), nullable=False, comment="公司名称")
    position_title = Column(String(200), nullable=False, comment="职位名称")
    jd_text = Column(Text, nullable=True, comment="原始JD文本")
    jd_analysis = Column(Text, nullable=True, comment="JD分析结果JSON")
    match_score = Column(Float, nullable=True, comment="匹配度评分")
    match_detail = Column(Text, nullable=True, comment="匹配度详细分析JSON")
    tailored_resume = Column(Text, nullable=True, comment="优化后的简历")
    cover_letter = Column(Text, nullable=True, comment="生成的求职信")
    status = Column(
        String(50), nullable=False, default="待投递",
        comment="投递状态: 待投递/已投递/初筛中/面试中/已发Offer/已拒绝"
    )
    notes = Column(Text, nullable=True, comment="用户备注")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


# ----- 简历存储 -----

class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="简历名称/版本")
    content = Column(Text, nullable=False, comment="简历内容")
    is_active = Column(Integer, default=0, comment="是否当前激活版本")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


# ----- 简历优化记录 -----

class ResumeOptimization(Base):
    __tablename__ = "resume_optimizations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    jd_analysis_id = Column(Integer, nullable=True, comment="关联的JD分析ID")
    resume_text = Column(Text, nullable=False, comment="原始简历")
    jd_analysis_json = Column(Text, nullable=True, comment="JD分析结果JSON")
    match_score = Column(Float, nullable=True, comment="匹配度评分")
    match_detail = Column(Text, nullable=True, comment="匹配度详细JSON")
    tailored_resume = Column(Text, nullable=True, comment="优化后简历")
    annotations_enabled = Column(Integer, default=1, comment="是否开启改动注释")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


def init_db():
    """初始化数据库表"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """获取数据库会话（FastAPI依赖注入）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
