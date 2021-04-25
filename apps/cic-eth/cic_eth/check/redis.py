# external imports
import redis
import os


def health(*args, **kwargs):
    r = redis.Redis(
            host=kwargs['config'].get('REDIS_HOST'),
            port=kwargs['config'].get('REDIS_PORT'),
            db=kwargs['config'].get('REDIS_DB'),
            )
    try:
        r.set(kwargs['unit'], os.getpid())
    except redis.connection.ConnectionError:
        return False
    except redis.connection.ResponseError:
        return False
    return True
