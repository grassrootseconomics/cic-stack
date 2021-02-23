# standard imports
import logging

# local imports
from cic_eth.db.models.sync import BlockchainSync
from cic_eth.db.models.base import SessionBase

logg = logging.getLogger()


class SyncerBackend:
    """Interface to block and transaction sync state.

    :param chain_spec: Chain spec for the chain that syncer is running for.
    :type chain_spec: cic_registry.chain.ChainSpec
    :param object_id: Unique id for the syncer session.
    :type object_id: number
    """
    def __init__(self, chain_spec, object_id):
        self.db_session = None
        self.db_object = None
        self.chain_spec = chain_spec
        self.object_id = object_id
        self.connect()
        self.disconnect()


    def connect(self):
        """Loads the state of the syncer session with the given id.
        """
        if self.db_session == None:
            self.db_session = SessionBase.create_session()
        q = self.db_session.query(BlockchainSync)
        q = q.filter(BlockchainSync.id==self.object_id)
        self.db_object = q.first()
        if self.db_object == None:
            self.disconnect()
            raise ValueError('sync entry with id {} not found'.format(self.object_id))
        return self.db_session


    def disconnect(self):
        """Commits state of sync to backend.
        """
        if self.db_session != None:
            self.db_session.add(self.db_object)
            self.db_session.commit()
            self.db_session.close()
            self.db_session = None
       

    def chain(self):
        """Returns chain spec for syncer

        :returns: Chain spec
        :rtype chain_spec: cic_registry.chain.ChainSpec
        """
        return self.chain_spec
   

    def get(self):
        """Get the current state of the syncer cursor.

        :returns: Block and block transaction height, respectively
        :rtype: tuple
        """
        self.connect()
        pair = self.db_object.cursor()
        self.disconnect()
        return pair
   

    def set(self, block_height, tx_height):
        """Update the state of the syncer cursor
        :param block_height: Block height of cursor
        :type block_height: number
        :param tx_height: Block transaction height of cursor
        :type tx_height: number
        :returns: Block and block transaction height, respectively
        :rtype: tuple
        """
        self.connect()
        pair = self.db_object.set(block_height, tx_height)
        self.disconnect()
        return pair


    def start(self):
        """Get the initial state of the syncer cursor.

        :returns: Initial block and block transaction height, respectively
        :rtype: tuple
        """
        self.connect()
        pair = self.db_object.start()
        self.disconnect()
        return pair

    
    def target(self):
        """Get the target state (upper bound of sync) of the syncer cursor.

        :returns: Target block height
        :rtype: number
        """
        self.connect()
        target = self.db_object.target()
        self.disconnect()
        return target


    @staticmethod
    def first(chain):
        """Returns the model object of the most recent syncer in backend.

        :param chain: Chain spec of chain that syncer is running for.
        :type chain: cic_registry.chain.ChainSpec
        :returns: Last syncer object 
        :rtype: cic_eth.db.models.BlockchainSync
        """
        return BlockchainSync.first(chain)


    @staticmethod
    def initial(chain, block_height):
        """Creates a new syncer session and commit its initial state to backend.

        :param chain: Chain spec of chain that syncer is running for.
        :type chain: cic_registry.chain.ChainSpec
        :param block_height: Target block height
        :type block_height: number
        :returns: New syncer object 
        :rtype: cic_eth.db.models.BlockchainSync
        """
        object_id = None
        session = SessionBase.create_session()
        o = BlockchainSync(chain, 0, 0, block_height)
        session.add(o)
        session.commit()
        object_id = o.id
        session.close()

        return SyncerBackend(chain, object_id)


    @staticmethod
    def resume(chain, block_height):
        """Retrieves and returns all previously unfinished syncer sessions.


        :param chain: Chain spec of chain that syncer is running for.
        :type chain: cic_registry.chain.ChainSpec
        :param block_height: Target block height
        :type block_height: number
        :returns: Syncer objects of unfinished syncs
        :rtype: list of cic_eth.db.models.BlockchainSync
        """
        syncers = []

        session = SessionBase.create_session()

        object_id = None

        for object_id in BlockchainSync.get_unsynced(session=session):
            logg.debug('block syncer resume added previously unsynced sync entry id {}'.format(object_id))
            syncers.append(SyncerBackend(chain, object_id))

        (block_resume, tx_resume) = BlockchainSync.get_last_live_height(block_height, session=session)
        if block_height != block_resume:
            o = BlockchainSync(chain, block_resume, tx_resume, block_height)
            session.add(o)
            session.commit()
            object_id = o.id
            syncers.append(SyncerBackend(chain, object_id))
            logg.debug('block syncer resume added new sync entry from previous run id {}, start{}:{} target {}'.format(object_id, block_resume, tx_resume, block_height))

        session.close()

        return syncers


    @staticmethod
    def live(chain, block_height):
        """Creates a new open-ended syncer session starting at the given block height.

        :param chain: Chain spec of chain that syncer is running for.
        :type chain: cic_registry.chain.ChainSpec
        :param block_height: Target block height
        :type block_height: number
        :returns: "Live" syncer object
        :rtype: cic_eth.db.models.BlockchainSync
        """
        object_id = None
        session = SessionBase.create_session()
        o = BlockchainSync(chain, block_height, 0, None)
        session.add(o)
        session.commit()
        object_id = o.id
        session.close()

        return SyncerBackend(chain, object_id)
