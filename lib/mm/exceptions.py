"""
Exceptions for the Memento Mori client / package.
"""


class MementoMoriException(Exception):
    """Base exception for other exceptions defined in this package"""


class CacheMiss(MementoMoriException):
    """Used internally to signal that a file cache miss occurred"""
