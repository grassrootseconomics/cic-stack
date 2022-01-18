import json
import logging
import mmap
import os
import time
import uuid

import redis
from cic_eth.pytest.mock.callback import CallbackTask

log = logging.getLogger(__name__)

class TestGetter:
        """
        Only Used for Testing 
        """   
        def __init__(self, _cs, _rh, _rp, _rdb, _rto) -> None:         
            self.callback_task = 'cic_eth.pytest.mock.callback.test_getter_callback'
            self.callback_param = str(uuid.uuid4())

        def get_callback_param(self):
            return self.callback_param

        def read_mm(self, callback_param, timeout=15):
            """Read Memory Map created by `cic_eth.pytest.mock.callback.test_getter_callback` task and identified by the `callback_param`

            Args:
                callback_param ([type]): Callback Parameter passed to celery
                timeout (int, optional): Duration in seconds to wait before throwing. Defaults to 15.

            Raises:
                TimeoutError: Thrown when timout exceeded 

            Returns: str | List | Dict 
            """           
            timeout = time.time() + timeout   # 30s from now

            while True:
                if time.time() > timeout:
                    raise TimeoutError(f"Timeout ocurred waiting for {callback_param}")
                print(f'Waiting for {callback_param}')
                fp = os.path.join(CallbackTask.mmap_path, callback_param)
                try:
                    f = open(fp, 'rb')
                    f.close()
                except FileNotFoundError:
                    time.sleep(0.1)
                    log.debug('look for {}'.format(fp))
                    continue
                f = open(fp, 'rb')
                m = mmap.mmap(f.fileno(), access=mmap.ACCESS_READ, length=0)
                idx = m.find(b'\x00')
                v = m.read(idx)
                m.close()
                f.close()
                try:
                    # When data is a json
                    data = json.loads(v.decode())
                except:
                    # When it's a string
                    data = v.decode()

                return data
        def get(self, length=4000, catch=1):
                if catch==1:
                    return self.read_mm(f"{self.callback_param}_0")
                else:
                    data = []
                    for i in range(catch):
                        result = self.read_mm(f"{self.callback_param}_{i}")
                        data.append(result)
                    return data
                
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
                        print(message)
                        result = json.loads(message['data'])["result"]
                        data.append(result)
            except Exception as e:
                raise BaseException(message)

            self.ps.unsubscribe()
            return data
