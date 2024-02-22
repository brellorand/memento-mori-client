"""
Misc utilities.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping, KeysView, ValuesView
from datetime import datetime, date, timedelta
from functools import wraps, partial
from json.encoder import JSONEncoder, encode_basestring_ascii, encode_basestring  # noqa
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
        log_fmt = (
            f'Rate limited {"method" if is_attrgetter else "function"}'
            f' {func.__name__!r} is being delayed {{:,.3f}} seconds'
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


class PermissiveJSONEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, (set, KeysView)):
            return sorted(o)
        elif isinstance(o, ValuesView):
            return list(o)
        elif isinstance(o, Mapping):
            return dict(o)
        elif isinstance(o, bytes):
            try:
                return o.decode('utf-8')
            except UnicodeDecodeError:
                return o.hex(' ', -4)
        elif isinstance(o, datetime):
            return o.isoformat(' ')
        elif isinstance(o, date):
            return o.strftime('%Y-%m-%d')
        elif isinstance(o, (type, timedelta)):
            return str(o)
        return super().default(o)


class CompactJSONEncoder(PermissiveJSONEncoder):
    """A JSON Encoder that puts small containers on single lines."""

    CONTAINER_TYPES = (list, tuple, dict)

    def __init__(self, *args, indent: int = None, max_line_len: int = 100, max_line_items: int = 10, **kwargs):
        # Using this class without indentation is pointless - force indent=4 if not specified
        kwargs.setdefault('ensure_ascii', False)
        super().__init__(*args, indent=indent or 4, **kwargs)
        self._indentation_level = 0
        self._max_line_len = max_line_len
        self._max_line_items = max_line_items

    def encode(self, o):
        match o:
            case list() | tuple():
                return self._encode_list(o)
            case dict():
                return self._encode_object(o)
            case float():
                return self._encode_float(o)
            case str():
                return encode_basestring_ascii(o) if self.ensure_ascii else encode_basestring(o)
            case _:
                return json.dumps(
                    o,
                    skipkeys=self.skipkeys,
                    ensure_ascii=self.ensure_ascii,
                    check_circular=self.check_circular,
                    allow_nan=self.allow_nan,
                    sort_keys=self.sort_keys,
                    indent=self.indent,
                    separators=(self.item_separator, self.key_separator),
                    default=self.__dict__.get('default'),  # Only set if a default func was provided
                    cls=PermissiveJSONEncoder,
                )

    def _encode_float(self, o: float, _repr=float.__repr__, _inf=float('inf'), _neginf=-float('inf')):
        # Mostly copied from the implementation in json.encoder.JSONEncoder.iterencode
        if o != o:
            text = 'NaN'
        elif o == _inf:
            text = 'Infinity'
        elif o == _neginf:
            text = '-Infinity'
        else:
            return _repr(o)  # noqa

        if not self.allow_nan:
            raise ValueError(f'Out of range float values are not JSON compliant: {o!r}')
        return text

    def _encode_list(self, obj: list) -> str:
        if self._len_okay_and_not_nested(obj):
            parts = [self.encode(v) for v in obj]
            if self._str_len_is_below_max(parts):
                return f'[{", ".join(parts)}]'

        self._indentation_level += 1
        content = ',\n'.join(self.indent_str + self.encode(v) for v in obj)
        self._indentation_level -= 1
        return f'[\n{content}\n{self.indent_str}]'

    def _encode_object(self, obj: dict):
        if not obj:
            return '{}'

        # ensure keys are converted to strings
        obj = {str(k) if k is not None else 'null': v for k, v in obj.items()}
        if self.sort_keys:
            obj = dict(sorted(obj.items()))

        dump_str = encode_basestring_ascii if self.ensure_ascii else encode_basestring
        if self._len_okay_and_not_nested(obj):
            parts = [f'{dump_str(k)}: {self.encode(v)}' for k, v in obj.items()]
            if self._str_len_is_below_max(parts):
                return f'{{{", ".join(parts)}}}'

        self._indentation_level += 1
        output = ',\n'.join(f'{self.indent_str}{dump_str(k)}: {self.encode(v)}' for k, v in obj.items())
        self._indentation_level -= 1
        return f'{{\n{output}\n{self.indent_str}}}'

    def iterencode(self, o, **kwargs):
        """Required to also work with `json.dump`."""
        return self.encode(o)

    def _len_okay_and_not_nested(self, obj: list | tuple | dict) -> bool:
        return (
            len(obj) <= self._max_line_items
            and not any(isinstance(v, self.CONTAINER_TYPES) for v in (obj.values() if isinstance(obj, dict) else obj))
        )

    def _str_len_is_below_max(self, parts: list[str]) -> bool:
        return (2 + sum(map(len, parts)) + (2 * len(parts))) <= self._max_line_len

    @property
    def indent_str(self) -> str:
        if isinstance(self.indent, int):
            return ' ' * (self._indentation_level * self.indent)
        elif isinstance(self.indent, str):
            return self._indentation_level * self.indent
        else:
            raise TypeError(f'indent must either be of type int or str (found: {self.indent.__class__.__name__})')
