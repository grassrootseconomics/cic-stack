# third party imports
import bcrypt


def create_password_hash(password):
    """This method encrypts a password value using a pre-set pepper and an appended salt.
    """
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(8)).decode("utf-8")


def check_password_hash(password, hashed_password):
    """This method ascertains a password's validity by hashing the provided password value using the original pepper and
    compares the resultant fernet signature to the one persisted in the db for a given user.
    :param password: A password value
    :type password: str
    :param hashed_password: A hash for a user's password value
    :type hashed_password: str

    :raises ValueError: if a key whose length is less than 32 bytes.
    :raises binascii.Error: if base64 key is invalid or corrupted.

    :return: Password validity
    :rtype: boolean
    """
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
