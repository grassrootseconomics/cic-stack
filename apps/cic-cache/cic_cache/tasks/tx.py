# third-party imports
import celery

# local imports
from cic_cache.cache import BloomCache
from cic_cache.db.models.base import SessionBase

celery_app = celery.current_app


@celery_app.task(bind=True)
def tx_filter(self, offset, limit, address=None, encoding='hex'):
    queue = self.request.delivery_info.get('routing_key')

    session = SessionBase.create_session()

    c = BloomCache(session)
    b = None
    if address == None:
        (lowest_block, highest_block, bloom_filter_block, bloom_filter_tx) = c.load_transactions(offset, limit)
    else:
        (lowest_block, highest_block, bloom_filter_block, bloom_filter_tx) = c.load_transactions_account(address, offset, limit)

    session.close()

    o = {
        'alg': 'sha256',
        'low': lowest_block,
        'high': highest_block,
        'block_filter': bloom_filter_block.hex(), 
        'blocktx_filter': bloom_filter_tx.hex(),
        'filter_rounds': 3,
            }

    return o



