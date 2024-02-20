"""
Asset Catalog and related classes
"""

from __future__ import annotations

import logging
from base64 import b64decode
from functools import cached_property
from typing import Any, Iterator, Sequence

from .data import DictWrapper
from .utils import DataProperty

__all__ = ['AssetCatalog', 'Asset', 'AssetDir']
log = logging.getLogger(__name__)

_DIR_0 = '{Ortega.Common.Manager.GameManager.AssetFullUrl}'


class AssetCatalog(DictWrapper):
    locator_id: str = DataProperty('m_LocatorId')
    instance_provider_data: dict[str, Any] = DataProperty('m_InstanceProviderData')
    scene_provider_data: dict[str, Any] = DataProperty('m_SceneProviderData')
    resource_provider_data: list[dict[str, Any]] = DataProperty('m_ResourceProviderData')
    provider_ids: list[str] = DataProperty('m_ProviderIds')  # class/module names?
    internal_ids: list[str] = DataProperty('m_InternalIds')  # `{prefix_index}#/{file_name}`

    key_data: bytes = DataProperty('m_KeyDataString', type=b64decode)
    bucket_data: bytes = DataProperty('m_BucketDataString', type=b64decode)
    entry_data: bytes = DataProperty('m_EntryDataString', type=b64decode)
    extra_data: bytes = DataProperty('m_ExtraDataString', type=b64decode)

    resource_types: list[dict[str, str]] = DataProperty('m_resourceTypes')  # list of {m_AssemblyName, m_ClassName}
    internal_id_prefixes: list[str] = DataProperty('m_InternalIdPrefixes')  # directories for InternalIds?

    @cached_property
    def asset_tree(self) -> AssetDir:
        root = AssetDir('')
        dir_nodes = [root.add_dir(prefix) for prefix in self.internal_id_prefixes]
        for internal_id in self.internal_ids:
            num, name = internal_id.split('#', 1)
            dir_nodes[int(num)].add_asset(name[1:])
        return root

    def get_asset(self, name_or_path: str) -> AssetDir | Asset:
        try:
            return self.asset_tree[name_or_path]
        except KeyError as e:
            raise KeyError(f'Invalid asset path: {name_or_path!r}') from e

    @cached_property
    def bundle_names(self) -> list[str]:
        return [name[3:] for name in self.internal_ids if name.startswith('0#/')]


class Asset:
    __slots__ = ('name', 'parent')

    def __init__(self, name: str, parent: AssetDir | None = None):
        self.name = name
        self.parent = parent

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}[{self.name!r}, parent={self.parent}]>'

    def __str__(self) -> str:
        if self.parent:
            return f'{self.parent}/{self.name}' if self.parent.name else self.name
        else:
            return self.name

    def __eq__(self, other: Asset) -> bool:
        return self.name == other.name and self.parent is other.parent

    def __lt__(self, other: Asset) -> bool:
        return (self.name, self.parent) < (other.name, other.parent)  # noqa

    @property
    def depth(self) -> int:
        if self.parent:
            return self.parent.depth + 1
        return 0


class AssetDir(Asset):
    __slots__ = ('children',)

    def __init__(self, name: str, parent: AssetDir | None = None):
        super().__init__(name, parent)
        self.children = {}

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}[{self.name!r}, children={len(self.children)}, parent={self.parent}]>'

    def add_asset(self, name: str) -> Asset:
        *parts, name = name.split('/')
        asset_dir = self._get_or_add_dir(parts) if parts else self
        asset_dir.children[name] = asset = Asset(name, self)
        return asset

    def add_dir(self, name: str) -> AssetDir | Asset:
        return self._get_or_add_dir(name.split('/'))

    def _get_or_add_dir(self, parts: Sequence[str]) -> AssetDir:
        name, *parts = parts
        try:
            asset = self.children[name]
        except KeyError:
            self.children[name] = asset = AssetDir(name, self)

        return asset._get_or_add_dir(parts) if parts else asset

    def iter_flat(self, max_depth: int = None, skip_0: bool = True) -> Iterator[Asset]:
        if skip_0 and not self.parent:
            children = (child for name, child in self.children.items() if name != _DIR_0)
        else:
            children = self.children.values()

        if max_depth is not None and self.depth == max_depth:
            yield from children
        else:
            for child in children:
                try:
                    yield from child.iter_flat(max_depth)
                except AttributeError:  # it's an Asset, not an AssetDir
                    yield child

    def _get(self, parts: Sequence[str]) -> AssetDir | Asset:
        name, *parts = parts
        asset = self.children[name]
        return asset._get(parts) if parts else asset

    def __getitem__(self, path: str) -> AssetDir | Asset:
        return self._get(path.split('/'))

    def __iter__(self) -> Iterator[AssetDir | Asset]:
        yield from self.children.values()

    def __len__(self) -> int:
        return len(self.children)
