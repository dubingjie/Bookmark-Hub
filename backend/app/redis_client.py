import redis

from .config import REDIS_HOST, REDIS_PORT, REDIS_URL

# decode_responses=True：返回值直接是 str，否则是 bytes（b'42'），省去到处解码
# 云端托管 Redis（如 Upstash 免费档）用 REDIS_URL 完整连接串（rediss:// 自带 TLS 和密码）
if REDIS_URL:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
else:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# ZSET：member=书签ID，score=累计访问次数
RANKING_KEY = "bookmarks:ranking"
