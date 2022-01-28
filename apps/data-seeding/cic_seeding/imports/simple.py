# local imports
from cic_seeding.imports import Importer


class SimpleImporter(Importer):

    def filter(self, conn, block, tx, db_session=None):
        # get user if matching tx
        u = self._user_by_tx(tx)
        if u == None:
            return

        # transfer old balance
        self._gift_tokens(conn, u)
