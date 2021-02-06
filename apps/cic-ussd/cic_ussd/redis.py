# third-party imports
from redis import Redis


class InMemoryStore:
    cache: Redis = None
