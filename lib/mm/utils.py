"""
Misc utilities.
"""

from __future__ import annotations

import logging
from datetime import datetime
from functools import wraps, partial
from operator import attrgetter
from threading import Lock
from time import sleep, monotonic
from typing import TYPE_CHECKING, Optional, Callable, Any

if TYPE_CHECKING:
    from .client import RequestsClient

__all__ = ['rate_limited', 'format_path_prefix', 'DataProperty']
log = logging.getLogger(__name__)

_NotSet = object()


# region HTTP Client Utils


class UrlPart:
    """Part of a URL.  Enables cached values that rely on this value to be reset if this value is changed"""

    __slots__ = ('formatter', 'name')

    def __init__(self, formatter: Callable = None):
        self.formatter = formatter

    def __set_name__(self, owner, name: str):
        self.name = name

    def __get__(self, instance: RequestsClient, owner):
        # Note: since both __get__ and __set__ are defined, this descriptor takes precedence over __dict__,
        # so this method will always be called upon attr access
        try:
            return instance.__dict__.get(self.name)
        except AttributeError:  # instance is None / this descriptor is being accessed as a class attribute
            return self

    def __set__(self, instance: RequestsClient, value):
        if self.formatter is not None:
            value = self.formatter(value)
        instance.__dict__[self.name] = value
        # _url_fmt is a cached_property in RequestsClient - reset it since this part of the URL changed
        try:
            del instance.__dict__['_url_fmt']
        except KeyError:
            pass


class RequestMethod:
    """
    A request method.  Allows subclasses to override the ``request`` method and have this method call it.

    There isn't a great way to annotate this, but it accepts the same arguments as :meth:`~.RequestsClient.request`,
    except for ``method``, which is injected by this wrapper.
    """

    __slots__ = ('method',)

    def __set_name__(self, owner, name: str):
        self.method = name.upper()

    def __get__(self, instance: RequestsClient, owner):
        try:
            return partial(instance.request, self.method)
        except AttributeError:  # instance is None / this descriptor is being accessed as a class attribute
            return self


def rate_limited(interval: float = 0, log_lvl: int = logging.DEBUG):
    """
    :param interval: Interval between allowed invocations in seconds
    :param log_lvl: The log level that should be used to indicate that the wrapped function is being delayed
    """
    if is_attrgetter := isinstance(interval, (attrgetter, str)):
        interval = attrgetter(interval) if isinstance(interval, str) else interval

    def decorator(func):
        last_call = 0
        lock = Lock()
        log_fmt = 'Rate limited {} {!r} is being delayed {{:,.3f}} seconds'.format(
            'method' if is_attrgetter else 'function', func.__name__
        )

        @wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal last_call
            obj_interval = interval(args[0]) if is_attrgetter else interval  # noqa
            with lock:
                elapsed = monotonic() - last_call
                if elapsed < obj_interval:
                    wait = obj_interval - elapsed
                    log.log(log_lvl, log_fmt.format(wait))
                    sleep(wait)
                last_call = monotonic()
                return func(*args, **kwargs)

        return wrapper

    return decorator


def format_path_prefix(value: Optional[str]) -> str:
    if value:
        value = value if not value.startswith('/') else value[1:]
        return value if value.endswith('/') else value + '/'
    return ''


# endregion


class DataProperty:
    __slots__ = ('path', 'path_repr', 'type', 'name', 'default', 'default_factory')

    def __init__(
        self,
        path: str,
        type: Callable = _NotSet,  # noqa
        default: Any = _NotSet,
        default_factory: Callable = _NotSet,
        delim: str = '.',
    ):
        """
        Descriptor that acts as a cached property for retrieving values nested in a dict stored in the ``data``
        attribute of the object that this :class:`DataProperty` is a member of.  The value is not accessed or stored
        until the first time that it is accessed.

        To un-cache a value (causes the descriptor to take over again)::\n
            >>> del instance.__dict__[attr_name]

        :param path: The nexted key location in the dict attribute of the value that this DataProperty
          represents; dict keys should be separated by ``.``, otherwise the delimiter should be provided via ``delim``
        :param type: Callable that accepts 1 argument; the value of this DataProperty will be passed to it, and the
          result will be returned as this DataProperty's value (default: no conversion)
        :param default: Default value to return if a KeyError is encountered while accessing the given path
        :param default_factory: Callable that accepts no arguments to be used to generate default values
          instead of an explicit default value
        :param delim: Separator that was used between keys in the provided path (default: ``.``)
        """
        self.path = [p for p in path.split(delim) if p]
        self.path_repr = delim.join(self.path)
        self.type = type
        self.default = default
        self.default_factory = default_factory

    def __set_name__(self, owner: type, name: str):
        self.name = name

    def __get__(self, obj, cls):
        try:
            value = obj.data
        except AttributeError:  # obj is None / this descriptor is being accessed as a class attribute
            return self

        for key in self.path:
            try:
                value = value[key]
            except KeyError as e:
                if self.default is not _NotSet:
                    value = self.default
                    break
                elif self.default_factory is not _NotSet:
                    value = self.default_factory()
                    break
                raise DictAttrFieldNotFoundError(obj, self.name, self.path_repr) from e

        if self.type is not _NotSet:
            value = self.type(value)
        obj.__dict__[self.name] = value
        return value


class DictAttrFieldNotFoundError(Exception):
    def __init__(self, obj, prop_name: str, path_repr: str):
        self.obj = obj
        self.prop_name = prop_name
        self.path_repr = path_repr

    def __str__(self) -> str:
        return (
            f'{self.obj.__class__.__name__} object has no attribute {self.prop_name!r}'
            f' ({self.path_repr} not found in {self.obj!r}.data)'
        )


def parse_ms_epoch_ts(epoch_ts: str | int) -> datetime:
    return datetime.fromtimestamp(int(epoch_ts) / 1000)
