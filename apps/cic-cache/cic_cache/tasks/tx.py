# third-party imports
import celery

# local imports
from cic_cache.cache import (
        BloomCache,
        DataCache,
        )
from cic_cache.db.models.base import SessionBase

celery_app = celery.current_app


@celery_app.task(bind=True)
def tx_filter(self, offset, limit, address=None, oldest=False, encoding='hex'):
    queue = self.request.delivery_info.get('routing_key')

    session = SessionBase.create_session()

    c = BloomCache(session)
    b = None
    if address == None:
        (lowest_block, highest_block, bloom_filter_block, bloom_filter_tx) = c.load_transactions(offset, limit, oldest=oldest)
    else:
        (lowest_block, highest_block, bloom_filter_block, bloom_filter_tx) = c.load_transactions_account(address, offset, limit, oldest=oldest)

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


@celery_app.task(bind=True)
def tx_filter_content(self, offset, limit, address=None, block_offset=None, block_limit=None, oldest=False, encoding='hex'):
    session = SessionBase.create_session()

    c = DataCache(session)
    b = None
    if address == None:
        if block_offset:
            (lowest_block, highest_block, tx_cache) = c.load_transactions_with_data(offset, limit, block_offset=block_offset, block_limit=block_limit, oldest=oldest)
        else:
            (lowest_block, highest_block, tx_cache) = c.load_transactions_with_data_index(offset, limit, block_offset=block_offset, block_limit=block_limit)
    else:
        if block_offset:
            (lowest_block, highest_block, tx_cache) = c.load_transactions_account_with_data(address, offset, limit, block_offset=block_offset, block_limit=block_limit)
        else:
            (lowest_block, highest_block, tx_cache) = c.load_transactions_account_with_data_index(address, offset, limit, block_offset=block_offset, block_limit=block_limit)

    session.close()

    return (lowest_block, highest_block, tx_cache,)
