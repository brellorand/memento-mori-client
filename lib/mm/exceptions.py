"""
Exceptions for the Memento Mori client / package.
"""


class MementoMoriException(Exception):
    """Base exception for other exceptions defined in this package"""


class CacheError(MementoMoriException):
    """Raised when an API response cannot be cached to a file or loaded from a cache file"""


class CacheMiss(CacheError):
    """Used internally to signal that a file cache miss occurred"""
