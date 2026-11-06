import ssl

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import DATABASE_URL, DB_SSL


def _connect_args() -> dict:
    """DB_SSL 开启时加密连接（不校验 CA，适用于 Aiven 等托管库），本地默认不加"""
    if not DB_SSL:
        return {}
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return {"ssl": ctx}


# pool_pre_ping：Aiven 免费实例不活动会自动关机，连接失效后首次请求自动重建，无需重启进程
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=_connect_args())
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI 依赖：每个请求分配一个数据库会话，用完自动关闭"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
