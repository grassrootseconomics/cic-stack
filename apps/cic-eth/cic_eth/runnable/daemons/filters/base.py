class SyncFilter:
    
    def __init__(self):
        self.exec_count = 0
        self.match_count = 0


    def filter(self, conn, block, tx, db_session):
        self.exec_count += 1


    def register_match(self):
        self.match_count += 1


    def to_logline(self, block, tx, v):
        return '{} exec {} match {} block {} tx {}: {}'.format(self, self.exec_count, self.match_count, block.number, tx.index, v)
