import redis

from .config import REDIS_HOST, REDIS_PORT

# decode_responses=True：返回值直接是 str，否则是 bytes（b'42'），省去到处解码
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
# ZSET：member=书签ID，score=累计访问次数
RANKING_KEY = "bookmarks:ranking"
