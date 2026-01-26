"""
Redis cache utilities.
"""
import json
import redis
from typing import Optional, Any
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Global Redis client
_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    """Get or create Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
    return _redis_client


def get_cache_key(game_id: str, ply: int, suffix: Optional[str] = None) -> str:
    """Generate cache key for engine analysis."""
    key = f"game:{game_id}:ply:{ply}"
    if suffix:
        key += f":{suffix}"
    return key


def get_from_cache(key: str) -> Optional[Any]:
    """Get value from cache."""
    try:
        client = get_redis_client()
        value = client.get(key)
        if value:
            return json.loads(value)
        return None
    except Exception as e:
        logger.warning(f"Cache get error for key {key}: {e}")
        return None


def set_to_cache(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """Set value in cache."""
    try:
        client = get_redis_client()
        ttl = ttl or settings.redis_cache_ttl
        serialized = json.dumps(value)
        client.setex(key, ttl, serialized)
        return True
    except Exception as e:
        logger.warning(f"Cache set error for key {key}: {e}")
        return False


def delete_from_cache(key: str) -> bool:
    """Delete key from cache."""
    try:
        client = get_redis_client()
        client.delete(key)
        return True
    except Exception as e:
        logger.warning(f"Cache delete error for key {key}: {e}")
        return False


def clear_game_cache(game_id: str) -> bool:
    """Clear all cache entries for a game."""
    try:
        client = get_redis_client()
        pattern = f"game:{game_id}:*"
        keys = client.keys(pattern)
        if keys:
            client.delete(*keys)
        return True
    except Exception as e:
        logger.warning(f"Cache clear error for game {game_id}: {e}")
        return False
