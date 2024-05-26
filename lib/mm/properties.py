"""
A ``DataProperty`` class is defined here to simplify the definition of properties that expose data in a given
instance's ``.data`` attribute, and to cache the results.

Helpers are also defined here for clearing those cached values, as well as those cached by ``@cached_property``, so
that they may be re-computed.
"""

from __future__ import annotations

from functools import lru_cache, cached_property
from typing import Any, Callable, Collection

__all__ = [
    'DataProperty',
    'DictAttrFieldNotFoundError',
    'ClearableCachedPropertyMixin',
    'register_cached_property_class',
    'unregister_cached_property_class',
    'cached_classproperty',
]

_NotSet = object()


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
        # noinspection PyUnresolvedReferences
        """
        Descriptor that acts as a cached property for retrieving values nested in a dict stored in the ``data``
        attribute of the object that this :class:`DataProperty` is a member of.  The value is not accessed or stored
        until the first time that it is accessed.

        To un-cache a value (causes the descriptor to take over again)::\n
            >>> del instance.__dict__[attr_name]

        :param path: The nested key location in the dict attribute of the value that this DataProperty
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


# region Clearable Cached Property


class ClearableCachedPropertyMixin:
    """
    Mixin for classes containing descriptors that cache results, including methods decorated with ``cached_property``.
    Adds the :meth:`.clear_cached_properties` method to facilitate clearing all or specific cached values.
    """

    __slots__ = ()

    def clear_cached_properties(self, *names: str, skip: Collection[str] = None):
        """
        Purge the cached values for the cached properties with the specified names, or all cached properties that are
        present in this class if no names are specified.  Properties that did not have a cached value are ignored.

        :param names: The names of the cached properties to be cleared
        :param skip: A collection of names of cached properties that should NOT be cleared
        """
        clear_cached_properties(self, *names, skip=skip)


def get_cached_property_names(obj) -> set[str]:
    """Get the names of all cached properties that exist in the given object or class."""
    try:
        mro = type.mro(obj)
    except TypeError:
        obj = obj.__class__
        mro = type.mro(obj)

    return _get_cached_property_names(obj, tuple(mro[1:]))


@lru_cache(20)
def _get_cached_property_names(obj, mro) -> set[str]:
    names = {k for k, v in obj.__dict__.items() if is_cached_property(v)}
    for cls in mro:
        names |= get_cached_property_names(cls)

    return names


def clear_cached_properties(instance, *names: str, skip: Collection[str] = None):
    """
    Purge the cached values for the cached properties with the specified names, or all cached properties that are
    present in the given object if no names are specified.  Properties that did not have a cached value are ignored.

    :param instance: An object that contains cached properties
    :param names: The names of the cached properties to be cleared
    :param skip: A collection of names of cached properties that should NOT be cleared
    """
    names = set(names) if names else get_cached_property_names(instance.__class__)
    if skip:
        names = names.difference({skip} if isinstance(skip, str) else set(skip))

    cache = instance.__dict__
    for name in names.intersection(cache):
        try:
            del cache[name]
        except KeyError:
            pass


_CACHED_PROPERTY_CLASSES: tuple[type, ...] = (DataProperty, cached_property)


def is_cached_property(obj) -> bool:
    return isinstance(obj, _CACHED_PROPERTY_CLASSES)


def register_cached_property_class(cls: type):
    global _CACHED_PROPERTY_CLASSES
    _CACHED_PROPERTY_CLASSES = (*_CACHED_PROPERTY_CLASSES, cls)


def unregister_cached_property_class(cls: type):
    global _CACHED_PROPERTY_CLASSES
    _CACHED_PROPERTY_CLASSES = tuple(c for c in _CACHED_PROPERTY_CLASSES if c is not cls)


# endregion


class cached_classproperty(classmethod):
    def __init__(self, func: Callable):
        super().__init__(property(func))  # noqa  # makes Sphinx handle it better than if this was not done
        self.__doc__ = func.__doc__
        self.func = func
        self.values = {}

    def __get__(self, obj: None, cls):  # noqa
        try:
            return self.values[cls]
        except KeyError:
            self.values[cls] = value = self.func(cls)
            return value
