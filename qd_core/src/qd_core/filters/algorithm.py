import base64
import hashlib
import uuid
from hashlib import sha1
from typing import Callable, Union

from qd_core.filters.convert import to_bytes, to_native, to_text

try:
    from hashlib import md5 as _md5  # pylint: disable=ungrouped-imports
except ImportError:
    # Assume we're running in FIPS mode here
    _md5 = None  # type: ignore


def secure_hash_s(value: Union[str, bytes], hash_func: Callable = sha1) -> str:
    """
    Return a secure hash hex digest of the provided data.

    :param value: The input data to be hashed, which can be either a string or bytes.
    :param hash_func: A hash function that returns an instance of a hashing object when called without arguments (default is hashlib.sha1).
    :return: A hexadecimal string representation of the hash digest.
    """  # noqa: E501
    digest = hash_func()
    value_bytes: bytes = to_bytes(value, errors="surrogate_or_strict")
    digest.update(value_bytes)
    return digest.hexdigest()


def md5string(value):
    if _md5 is None:
        raise ValueError("MD5 not available. Possibly running in FIPS mode")
    return secure_hash_s(value, _md5)


def get_hash(value, hashtype="sha1"):
    try:
        h = hashlib.new(hashtype)
    except Exception as e:
        # hash is not supported?
        raise e

    h.update(to_bytes(value, errors="surrogate_or_strict"))
    return h.hexdigest()


def to_uuid(value, namespace=uuid.NAMESPACE_URL):
    uuid_namespace = namespace
    if not isinstance(uuid_namespace, uuid.UUID):
        try:
            uuid_namespace = uuid.UUID(namespace)
        except (AttributeError, ValueError) as e:
            raise Exception(f"Invalid value '{to_native(namespace)}' for 'namespace': {to_native(e)}") from e
    # uuid.uuid5() requires bytes on Python 2 and bytes or text or Python 3
    return to_text(uuid.uuid5(uuid_namespace, to_native(value, errors="surrogate_or_strict")))


def b64encode(value, encoding="utf-8"):
    return to_text(base64.b64encode(to_bytes(value, encoding=encoding, errors="surrogate_or_strict")))


def b64decode(value, encoding="utf-8"):
    return to_text(base64.b64decode(to_bytes(value, errors="surrogate_or_strict")), encoding=encoding)
