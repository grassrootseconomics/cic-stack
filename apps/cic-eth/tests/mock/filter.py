# third-party imports
import celery
import moolb

celery_app = celery.current_app

block_filter = moolb.Bloom(1024, 3)
tx_filter = moolb.Bloom(1024, 3)
lo = 0
hi = 100


@celery_app.task()
def filter(address, offset, limit):
    return {
        'alg': 'sha256',
        'high': hi,
        'low': lo,
        'block_filter': block_filter.to_bytes().hex(),
        'blocktx_filter': tx_filter.to_bytes().hex(),
        'filter_rounds': 3,
            }
