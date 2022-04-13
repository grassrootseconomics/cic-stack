class Monitor:

    def __init__(self, domain):
        self.domain = domain
        self.u = []
        self.persist = []
        self.connect()
        self.lock()
        self.load()
