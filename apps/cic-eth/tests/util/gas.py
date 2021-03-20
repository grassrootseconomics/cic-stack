class StaticGasOracle:

    def __init__(self, price, limit):
        self.price = price
        self.limit = limit


    def get_gas(self):
        return (self.price, self.limit)
