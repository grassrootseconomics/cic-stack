class MemPoolSyncer(Syncer):


    def __init__(self, bc_cache):
        raise NotImplementedError('incomplete, needs web3 tx to raw transaction conversion')
        super(MemPoolSyncer, self).__init__(bc_cache)
#        self.w3_filter = Syncer.w3.eth.filter('pending')
#        for tx in tx_cache.txs:
#            self.txs.append(tx)
#            logg.debug('add tx {} to mempoolsyncer'.format(tx))
#
#
#    def get(self):
#        return self.w3_filter.get_new_entries()
#
#
#    def process(self, tx_hash):
#        tx_hash_hex = tx_hash.hex()
#        if tx_hash_hex in self.txs:
#            logg.debug('syncer already watching {}, skipping'.format(tx_hash_hex))
#        tx = self.w3.eth.getTransaction(tx_hash_hex)
#        serialized_tx = rlp.encode({
#            'nonce': tx.nonce,
#            'from': getattr(tx, 'from'),
#            })
#        logg.info('add {} to syncer: {}'.format(tx, serialized_tx))
#        otx = Otx(
#                nonce=tx.nonce,
#                address=getattr(tx, 'from'),
#                tx_hash=tx_hash_hex,
#                signed_tx=serialized_tx,
#                )
#        Otx.session.add(otx)
#        Otx.session.commit()
#
#
#    def loop(self, interval):
#        while Syncer.running:
#            logg.debug('loop execute')
#            txs = self.get()
#            logg.debug('got txs {}'.format(txs))
#            for tx in txs:
#                #block_number = self.process(block.hex())
#                self.process(tx)
#                #if block_number > self.bc_cache.head():
#                #    self.bc_cache.head(block_number)
#            time.sleep(interval)
#        logg.info("Syncer no longer set to run, gracefully exiting")


