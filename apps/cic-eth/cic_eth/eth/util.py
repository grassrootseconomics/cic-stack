# external imports
from chainlib.eth.gas import RPCGasOracle

# local imports
from cic_eth.db.models.gas_cache import GasCache


MAXIMUM_FEE_UNITS = 8000000

class MaxGasOracle(RPCGasOracle):

    def get_fee_units(code=None):
        return MAXIMUM_FEE_UNITS


class CacheGasOracle(MaxGasOracle):
    """Returns a previously recorded value for fee unit expenditure for a contract call, if it exists. Otherwise returns max units.

    :todo: instead of max units, connect a pluggable gas heuristics engine.
    """

    def __init__(self, conn, address, method=None, session=None, min_price=None, id_generator=None):
        super(CacheGasOracle, self).__init__(conn, code_callback=self.get_fee_units, min_price=min_price, id_generator=id_generator)
        self.value = None
        self.address = address
        self.method = method

        address = tx_normalize.executable_address(address)
        session = SessionBase.bind_session(session)
        q = session.query(GasCache)
        q = q.filter(GasCache.address=address)
        if method != None:
            method = strip_0x(method)
            q = q.filter(GasCache.method=method)
        o = q.first()
        if o != None:
            self.value = int(o.value)

        SessionBase.release_session(session)


    def get_fee_units(self, code=None):
        if self.value != None:
            logg.debug('found stored gas unit value {} for address {} method {}'.format(self.value, self.address, self.method))
            return self.value
        return super(CacheGasOracle, self).get_fee_units(code=code)
