"""
Classes that wrap API responses
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

from mm.enums import Locale
from mm.properties import DictAttrFieldNotFoundError

if TYPE_CHECKING:
    from .base import MB, MBEntity

__all__ = ['LocalizedString', 'MBEntityList', 'MBEntityMap', 'parse_dt']
log = logging.getLogger(__name__)

_NotSet = object()


class LocalizedString:
    __slots__ = ('path', 'path_repr', 'name', 'default', 'default_key', 'default_to_key', 'locale')

    def __init__(
        self,
        path: str,
        default: Any = _NotSet,
        *,
        default_key: str = None,
        default_to_key: bool = False,
        delim: str = '.',
        locale: Locale = None
    ):
        # noinspection PyUnresolvedReferences
        """
        Descriptor that facilitates access to localized versions of strings in :class:`~.MBEntity` objects referenced
        by the specified localization key.

        To un-cache a value (causes the descriptor to take over again)::\n
            >>> del instance.__dict__[attr_name]

        :param path: The nested key location in the dict attribute of the value that this LocalizedString
          represents; dict keys should be separated by ``.``, otherwise the delimiter should be provided via ``delim``
        :param default: Default value to return if a KeyError is encountered while accessing the given path or
          localization key
        :param default_key: Default key to use if a KeyError is encountered while accessing the given path
        :param default_to_key: Whether the key value should be used as the default value if a KeyError is encountered
          while accessing the discovered localization key
        :param delim: Separator that was used between keys in the provided path (default: ``.``)
        """
        if default_to_key and default is not _NotSet:
            raise ValueError(
                f'Invalid combination of {default_to_key=!s} and {default=}'
                ' - default_to_key may only be True if no default is provided'
            )

        self.path = [p for p in path.split(delim) if p]
        self.path_repr = delim.join(self.path)
        self.default = default
        self.default_key = default_key
        self.default_to_key = default_to_key
        self.locale = Locale(locale) if locale else None

    def __set_name__(self, owner: type, name: str):
        self.name = name

    def _get_key(self, data) -> str:
        for key in self.path:
            try:
                data = data[key]
            except KeyError:
                if self.default_key:
                    return self.default_key
                raise

        return data

    def __get__(self, obj: MBEntity, cls):
        try:
            data = obj.data
        except AttributeError:  # obj is None / this descriptor is being accessed as a class attribute
            return self

        try:
            loc_key = self._get_key(data)
            if self.locale:
                value = obj.mb.get_text_resource_map(self.locale)[loc_key]
            else:
                value = obj.mb.text_resource_map[loc_key]
        except KeyError as e:
            if self.default is not _NotSet:
                value = self.default
            elif self.default_to_key:
                try:
                    value = loc_key  # noqa
                except NameError:
                    raise DictAttrFieldNotFoundError(obj, self.name, self.path_repr) from e
            else:
                raise DictAttrFieldNotFoundError(obj, self.name, self.path_repr) from e

        obj.__dict__[self.name] = value
        return value


class MBEntityContainer:
    __slots__ = ('name', 'mb_cls_name')

    def __init__(self, mb_cls_name: str):
        self.mb_cls_name = mb_cls_name

    def __set_name__(self, owner: type, name: str):
        self.name = name


class MBEntityList(MBEntityContainer):
    __slots__ = ()

    def __get__(self, obj: MB, cls):
        try:
            mb_entity_cls = obj._mb_entity_classes[self.mb_cls_name]
        except AttributeError:  # obj is None
            return self

        obj.__dict__[self.name] = entities = [mb_entity_cls(obj, row) for row in obj.get_data(mb_entity_cls)]
        return entities


class MBEntityMap(MBEntityContainer):
    __slots__ = ()

    def __get__(self, obj: MB, cls):
        try:
            mb_entity_cls = obj._mb_entity_classes[self.mb_cls_name]
        except AttributeError:  # obj is None
            return self

        key = mb_entity_cls._id_key
        obj.__dict__[self.name] = entities = {row[key]: mb_entity_cls(obj, row) for row in obj.get_data(mb_entity_cls)}
        return entities


def parse_dt(dt_str: str) -> datetime:
    return datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
