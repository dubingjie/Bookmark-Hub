import os
from pathlib import Path

from dotenv import load_dotenv

# 加载 backend/.env（config.py 在 app/ 里，.env 在它的上一级）
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "bookmark_db")
# 云端托管 MySQL（如 Aiven 免费档）强制 SSL；本地开发默认关闭
DB_SSL = os.getenv("DB_SSL", "False").lower() in ("true", "1", "yes")

DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
)

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
# 云端托管 Redis（如 Upstash 免费档）的完整连接串（rediss:// 带 TLS 和密码），填了则优先于 HOST/PORT
REDIS_URL = os.getenv("REDIS_URL", "")
