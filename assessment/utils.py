import redis
from django.conf import settings


redis_client = redis.StrictRedis.from_url(settings.CELERY_BROKER_URL, decode_responses=True)

def check_rate_limit(limit=200, window_seconds=60):
    """
    Fixed Window Rate Limiter using a Redis Pipeline.
    Returns True if allowed, False if the limit is exceeded.
    """
    key = "email_rate_limit_counter"

    pipeline = redis_client.pipeline()

    pipeline.incr(key)
    
    pipeline.expire(key, window_seconds, nx=True)
    
    results = pipeline.execute()
    
    current_count = results[0]

    if current_count > limit:
        return False  # Limit exceeded, stop the email
    
    return True # Limit is fine, send the email