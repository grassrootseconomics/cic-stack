# external imports
import celery


def test_default_token(
        default_token,
        celery_session_worker,
        foo_token,
        foo_token_symbol,
        ):
      
    s = celery.signature(
            'cic_eth.admin.token.default_token',
            [],
            queue=None,
            )
    t = s.apply_async()
    r = t.get()

    assert r['address'] == foo_token
    assert r['symbol'] == foo_token_symbol
