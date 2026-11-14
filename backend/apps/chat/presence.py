"""접속 상태(온라인). 캐시 카운터 방식 — 운영에서는 REDIS_URL 을 설정해 프로세스 간 공유되게 할 것."""
from django.core.cache import cache

TTL = 60 * 60 * 12


def _key(user_id):
    return f"chat:presence:{user_id}"


def mark_connected(user_id) -> None:
    cache.add(_key(user_id), 0, TTL)
    cache.incr(_key(user_id))


def mark_disconnected(user_id) -> None:
    try:
        n = cache.decr(_key(user_id))
    except ValueError:
        return
    if n <= 0:
        cache.delete(_key(user_id))


def is_online(user_id) -> bool:
    return (cache.get(_key(user_id)) or 0) > 0
