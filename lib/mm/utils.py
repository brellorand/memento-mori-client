"""
Misc utilities.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from datetime import datetime
from functools import wraps, partial
from json.encoder import JSONEncoder, encode_basestring_ascii, encode_basestring  # noqa
from operator import attrgetter
from threading import Lock
from time import sleep, monotonic
from typing import TYPE_CHECKING, Optional, Callable, Any

from tqdm import tqdm

if TYPE_CHECKING:
    from .client import RequestsClient

__all__ = ['rate_limited', 'format_path_prefix', 'DataProperty', 'parse_ms_epoch_ts', 'FutureWaiter']
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


# region Data Property


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


# endregion


def parse_ms_epoch_ts(epoch_ts: str | int) -> datetime:
    return datetime.fromtimestamp(int(epoch_ts) / 1000)


class FutureWaiter:
    __slots__ = ('executor', 'futures', 'tqdm', '_close_tqdm')

    def __init__(self, executor: ProcessPoolExecutor | ThreadPoolExecutor):
        self.executor = executor
        self.futures = None
        self.tqdm = None
        self._close_tqdm = False

    @classmethod
    def wait_for(cls, executor: ProcessPoolExecutor | ThreadPoolExecutor, futures, **kwargs):
        with cls(executor) as waiter:
            waiter.wait(futures, **kwargs)

    def __enter__(self) -> FutureWaiter:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            return
        if self._close_tqdm:
            try:
                self.tqdm.close()
            except Exception:  # noqa
                log.error('Error closing tqdm during executor shutdown', exc_info=True)
        self.executor.shutdown(cancel_futures=True)

    def __call__(
        self,
        futures,
        prog_bar: tqdm | None = None,
        *,
        add_bar: bool = False,
        unit: str = ' bundles',
        maxinterval: float = 1,
    ):
        if add_bar:
            if prog_bar is not None:
                raise ValueError('Invalid combination of prog_bar and add_bar - only one is allowed')
            self.init_tqdm(total=len(futures), unit=unit, maxinterval=maxinterval)
        elif prog_bar is not None:
            self.tqdm = prog_bar

        self.futures = futures
        return self

    def __iter__(self):
        if not self.futures:
            raise RuntimeError(f'It is only possible to iterate over {self.__class__.__name__} if called with futures')
        elif (prog_bar := self.tqdm) is not None:
            for future in as_completed(self.futures):
                prog_bar.update()
                yield future
        else:
            yield from as_completed(self.futures)

    def init_tqdm(self, **kwargs):
        self.tqdm = bar = tqdm(**kwargs)
        self._close_tqdm = True
        return bar

    def wait(self, futures, prog_bar: tqdm | None = None, **kwargs):
        self(futures, prog_bar, **kwargs)
        for future in self:
            future.result()
