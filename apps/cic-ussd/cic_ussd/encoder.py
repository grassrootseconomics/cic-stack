# third party imports
import bcrypt
from cryptography.fernet import Fernet


class PasswordEncoder(Fernet):
    """This class is responsible for defining the encryption function for password encoding in the application and the
    provision of a class method that can be used to define the static key attribute at the application's entry point.

    :cvar key: a URL-safe base64-encoded 32-byte
    :type key: bytes
    """

    key = None

    @classmethod
    def set_key(cls, key: bytes):
        """This method sets the value of the static key attribute to make it accessible to all subsequent instances of
        the class once defined.
        :param key: key: a URL-safe base64-encoded 32-byte
        :type key: bytes
        """
        cls.key = key

    def encrypt(self, ciphertext: bytes):
        """This overloads the encrypt function of the Fernet class
        :param ciphertext: The data to be encrypted.
        :type ciphertext: bytes
        :return: A fernet token (A set of bytes representing the hashed value succeeding the encryption)
        :rtype: bytes
        """
        return super(PasswordEncoder, self).encrypt(ciphertext)


def create_password_hash(password):
    """This method encrypts a password value using a pre-set pepper and an appended salt. Documentation is brief since
    symmetric encryption using a unique key (pepper) and salted passwords before hashing is well documented.
    N/B: Fernet encryption requires the unique key to be a URL-safe base64-encoded 32-byte key.
    https://cryptography.io/en/latest/fernet/
    :param password: A password value
    :type password: str

    :raises ValueError: if a key whose length length is less than 32 bytes.
    :raises binascii.Error: if base64 key is invalid or corrupted.

    :return: A fernet token (A set of bytes representing the hashed value succeeding the encryption)
    :rtype: str
    """
    fernet = PasswordEncoder(PasswordEncoder.key)
    return fernet.encrypt(bcrypt.hashpw(password.encode(), bcrypt.gensalt())).decode()


def check_password_hash(password, hashed_password):
    """This method ascertains a password's validity by hashing the provided password value using the original pepper and
    compares the resultant fernet signature to the one persisted in the db for a given user.
    :param password: A password value
    :type password: str
    :param hashed_password: A hash for a user's password value
    :type hashed_password: str

    :raises ValueError: if a key whose length length is less than 32 bytes.
    :raises binascii.Error: if base64 key is invalid or corrupted.

    :return: Password validity
    :rtype: boolean
    """
    fernet = PasswordEncoder(PasswordEncoder.key)
    hashed_password = fernet.decrypt(hashed_password.encode())
    return bcrypt.checkpw(password.encode(), hashed_password)