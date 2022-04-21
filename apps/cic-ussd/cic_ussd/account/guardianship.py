# standard imports

# external imports

# local imports

class Guardianship:
    guardians: list = []

    @classmethod
    def load_system_guardians(cls, guardians_file: str):
        with open(guardians_file, 'r') as system_guardians:
            cls.guardians = [line.strip() for line in system_guardians]

    def is_system_guardian(self, phone_number: str):
        """
        :param phone_number:
        :type phone_number:
        :return:
        :rtype:
        """
        return phone_number in self.guardians
