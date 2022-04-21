import json
import logging
import uuid
import redis

log = logging.getLogger(__name__)

class RedisGetter:
        def __init__(self, chain_spec, redis_host, redis_port, redis_db, redis_timeout) -> None:
            self.redis_host=redis_host
            self.redis_port=redis_port
            self.chain_spec=chain_spec
            self.redis_db=redis_db
            self.redis_timeout=redis_timeout
            self.callback_task = 'cic_eth.callbacks.redis.redis'
            log.debug(f"Using redis: {redis_host}, {redis_port}, {redis_db}")
            self.redis_channel = str(uuid.uuid4())
            r = redis.Redis(redis_host, redis_port, redis_db)
            ps = r.pubsub()
            ps.subscribe(self.redis_channel)
            self.ps = ps

        def get_callback_param(self):
            return '{}:{}:{}:{}'.format(self.redis_host, self.redis_port, self.redis_db, self.redis_channel)

        def get(self, catch=1):
            self.ps.get_message()
            try:
                data = []
                if catch == 1:
                    message = self.ps.get_message(timeout=self.redis_timeout)
                    data = json.loads(message['data'])["result"]
                else:
                    for _i in range(catch):
                        message = self.ps.get_message(
                            timeout=self.redis_timeout)
                        result = json.loads(message['data'])["result"]
                        data.append(result)
            except Exception as e:
                raise BaseException(message)

            self.ps.unsubscribe()
            return data
