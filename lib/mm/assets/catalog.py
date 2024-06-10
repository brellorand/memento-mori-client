"""
Asset Catalog and related classes.

Deserialization of data in m_KeyDataString, m_BucketDataString, m_EntryDataString, and m_ExtraDataString is based on
this project: https://github.com/nesrak1/AddressablesTools/blob/master/AddressablesTools/Catalog/ContentCatalogData.cs
"""

from __future__ import annotations

import json
import logging
from base64 import b64decode
from dataclasses import dataclass
from enum import IntEnum
from functools import cached_property
from io import BytesIO
from struct import Struct
from typing import Any, Iterator, Sequence, NamedTuple

from mm.data import DictWrapper
from mm.properties import DataProperty

__all__ = ['AssetCatalog', 'Asset', 'AssetDir']
log = logging.getLogger(__name__)

_DIR_0 = '{Ortega.Common.Manager.GameManager.AssetFullUrl}'


class AssetCatalog(DictWrapper):
    """
    Top-level keys:
        m_BucketDataString
        m_EntryDataString
        m_ExtraDataString
        m_InstanceProviderData
        m_InternalIdPrefixes
        m_InternalIds:              Asset bundles
        m_KeyDataString
        m_LocatorId
        m_ProviderIds
        m_ResourceProviderData
        m_SceneProviderData
        m_resourceTypes


    Example:
    {
        'm_LocatorId': 'AddressablesMainContentCatalog',
        'm_InstanceProviderData': {
            'm_Id': 'UnityEngine.ResourceManagement.ResourceProviders.InstanceProvider',
            'm_ObjectType': {'m_AssemblyName': 'Unity.ResourceManager, Version=0.0.0.0, Culture=neutral, PublicKeyToken=null', 'm_ClassName': 'UnityEngine.ResourceManagement.ResourceProviders.InstanceProvider'},
            'm_Data': ''
        },
        'm_SceneProviderData': {
            'm_Id': 'UnityEngine.ResourceManagement.ResourceProviders.SceneProvider',
            'm_ObjectType': {'m_AssemblyName': 'Unity.ResourceManager, Version=0.0.0.0, Culture=neutral, PublicKeyToken=null', 'm_ClassName': 'UnityEngine.ResourceManagement.ResourceProviders.SceneProvider'},
            'm_Data': ''
        },
        'm_ResourceProviderData': [
            {
                'm_Id': 'Ortega.Common.OrtegaAssestBundleProvider',
                'm_ObjectType': {'m_AssemblyName': 'Assembly-CSharp, Version=0.0.0.0, Culture=neutral, PublicKeyToken=null', 'm_ClassName': 'Ortega.Common.OrtegaAssestBundleProvider'},
                'm_Data': ''
            },
            {
                'm_Id': 'UnityEngine.ResourceManagement.ResourceProviders.BundledAssetProvider',
                'm_ObjectType': {'m_AssemblyName': 'Unity.ResourceManager, Version=0.0.0.0, Culture=neutral, PublicKeyToken=null', 'm_ClassName': 'UnityEngine.ResourceManagement.ResourceProviders.BundledAssetProvider'},
                'm_Data': ''
            },
            {
                'm_Id': 'UnityEngine.ResourceManagement.ResourceProviders.BundledAssetProvider',
                'm_ObjectType': {'m_AssemblyName': 'Unity.ResourceManager, Version=0.0.0.0, Culture=neutral, PublicKeyToken=null', 'm_ClassName': 'UnityEngine.ResourceManagement.ResourceProviders.BundledAssetProvider'},
                'm_Data': ''
            },
            {
                'm_Id': 'UnityEngine.ResourceManagement.ResourceProviders.AtlasSpriteProvider',
                'm_ObjectType': {'m_AssemblyName': 'Unity.ResourceManager, Version=0.0.0.0, Culture=neutral, PublicKeyToken=null', 'm_ClassName': 'UnityEngine.ResourceManagement.ResourceProviders.AtlasSpriteProvider'},
                'm_Data': ''
            }
        ],
        'm_ProviderIds': ['Ortega.Common.OrtegaAssestBundleProvider', 'UnityEngine.ResourceManagement.ResourceProviders.BundledAssetProvider'],
        'm_InternalIds': [
            '0#/0004aa460a958eb6464bec077ab56602.bundle',
            '0#/0009f326fb5c3ee00f92ba11c7b0e6c7.bundle',
            '0#/0009f9dbfd2fdbecf57794788e788960.bundle',
            ...

    """

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

    # region Decoded DataString Properties

    @cached_property
    def buckets(self) -> list[Bucket]:
        int32, int32x2 = Struct('i'), Struct('ii')
        reader = BinaryReader(self.bucket_data)
        buckets = []
        for i in range(reader.read(int32)):
            offset, entry_count = reader.read_array(int32x2)
            buckets.append(Bucket(offset, reader.read_n_array(int32, entry_count)))
        return buckets

    @cached_property
    def keys(self):
        # Appears to mostly contain the same data that is in `internal_ids`
        return SerializedObjectDecoder(self.key_data).decode_buckets(self.buckets)

    @cached_property
    def locations(self) -> list[ResourceLocation]:
        extra_decoder = SerializedObjectDecoder(self.extra_data)
        return [
            ResourceLocation(
                internal_id=self.internal_ids[int_id_idx],
                provider_id=self.provider_ids[prov_idx],
                dependency_key_idx=dep_key_idx,
                dependency_key=self.keys[dep_key_idx] if dep_key_idx >= 0 else None,  # bundle file name (usually)
                data=extra_decoder.decode(data_idx) if data_idx >= 0 else None,
                primary_key_idx=pk_idx,
                primary_key=self.keys[pk_idx],  # `internal_id_prefixes` entry + file name stem
                serialized_type=self.resource_types[r_type_idx],
            )
            for int_id_idx, prov_idx, dep_key_idx, dep_hash, data_idx, pk_idx, r_type_idx in self._iter_entry_data()
        ]

    @cached_property
    def resources(self) -> dict[str | int, list[ResourceLocation]]:
        """
        This appears to be a mapping of dependency_key to the list of ResourceLocations that depend on it, but it's
        not clear.
        """
        return {
            self.keys[i]: [self.locations[entry] for entry in bucket.entries]
            for i, bucket in enumerate(self.buckets)
        }

    def _iter_entry_data(self) -> Iterator[tuple[int, int, int, int, int, int, int]]:
        entry_struct = Struct('7i')
        entry_reader = BinaryReader(self.entry_data)
        for _ in range(entry_reader.read(Struct('i'))):  # The first int32 is the number of entries
            yield entry_reader.read_array(entry_struct)

    @cached_property
    def bundle_path_map(self) -> dict[str, list[str]]:
        """Mapping of bundle file names to the list of relative paths for asset files stored in those bundles."""
        bundle_path_map = {}
        for int_id_idx, _, dep_key_idx, _, _, pk_idx, _ in self._iter_entry_data():
            if dep_key_idx < 0:
                continue

            # Note: While it appears as though it would be fine to use `self.internal_ids` with the `dep_key_idx`,
            # in the apk catalog.json, there are some mismatches.
            bundle_name = self.keys[dep_key_idx]  # Bundle file name, without a leading `0#/`
            if not isinstance(bundle_name, str) or not bundle_name.endswith('.bundle'):
                continue

            try:
                bundle_paths = bundle_path_map[bundle_name]
            except KeyError:
                bundle_path_map[bundle_name] = bundle_paths = []

            prefix_index, name = self.internal_ids[int_id_idx].split('#', 1)
            # The `primary_key = self.keys[pk_idx]` value is not used here because it is both incomplete and contains
            # too much at the same time.  For example, `62a70f458f55919d69c737052a1a2a0a.bundle` contains one internal
            # id: `1#/RQB_000001.png`. Its primary_key is `Banner/LocalRaid/RQB_000001`, but the `internal_id_prefixes`
            # value for it provides a more complete relative path: `Assets/AddressableConvertAssets/Banner/LocalRaid`
            path = self.internal_id_prefixes[int(prefix_index)] + name
            if path not in bundle_paths:
                # A given `internal_id` / file may have multiple entries if multiple serialized types are represented
                # by the same file.  For example, `Assets/AddressableConvertAssets/Banner/LocalRaid/RQB_000001.png`
                # has 2 m_ClassName values: UnityEngine.Texture2D and UnityEngine.Sprite.
                bundle_paths.append(path)

        return bundle_path_map

    # endregion


# region Asset + AssetDir


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


# endregion


# region DataString Decoding


class Bucket(NamedTuple):
    offset: int
    entries: Sequence[int]


@dataclass(slots=True)
class ResourceLocation:
    internal_id: str
    provider_id: str
    dependency_key_idx: int
    dependency_key: Any
    data: Any
    # dependency_hash_code: int
    primary_key_idx: int
    primary_key: str
    serialized_type: dict[str, str]

    def as_dict(self):
        return {
            'internal_id': self.internal_id,
            'provider_id': self.provider_id,
            'dependency_key_idx': self.dependency_key_idx,
            'dependency_key': self.dependency_key,
            'data': self.data,
            'primary_key_idx': self.primary_key_idx,
            'primary_key': self.primary_key,
            'serialized_type': self.serialized_type,
        }


class ObjectType(IntEnum):
    AsciiString = 0
    UnicodeString = 1
    UInt16 = 2
    UInt32 = 3
    Int32 = 4
    Hash128 = 5
    Type = 6
    JsonObject = 7


class BinaryReader:
    __slots__ = ('_bio',)

    def __init__(self, data: bytes | bytearray | BytesIO):
        self._bio = data if isinstance(data, BytesIO) else BytesIO(data)

    def read(self, struct: Struct):
        return struct.unpack(self._bio.read(struct.size))[0]

    def read_array(self, struct: Struct):
        return struct.unpack(self._bio.read(struct.size))

    def read_n_array(self, struct: Struct, n: int):
        if n == 1:
            return self.read_array(struct)
        else:
            return self.read_array(Struct(f'{n}{struct.format}'))


class SerializedObjectDecoder:
    __slots__ = ('_bio',)
    _int8 = Struct('b')
    _int32 = Struct('i')
    _type_struct_map = {
        ObjectType.AsciiString: Struct('i'),    ObjectType.UnicodeString: Struct('i'),
        ObjectType.UInt32: Struct('I'),         ObjectType.Int32: Struct('i'),
        ObjectType.Hash128: Struct('b'),        ObjectType.Type: Struct('b'),
        ObjectType.UInt16: Struct('H'),
    }
    _type_encoding_map = {
        ObjectType.AsciiString: 'ascii', ObjectType.UnicodeString: 'utf-8',
        ObjectType.Hash128: 'ascii', ObjectType.Type: 'ascii',
    }

    def __init__(self, data: bytes | bytearray | BytesIO):
        self._bio = data if isinstance(data, BytesIO) else BytesIO(data)

    def decode_buckets(self, buckets: Sequence[Bucket]):
        return [self.decode(bucket.offset) for bucket in buckets]

    def decode(self, offset: int):
        self._bio.seek(offset)
        obj_type = ObjectType(self._int8.unpack(self._bio.read(1))[0])
        if struct := self._type_struct_map.get(obj_type):
            if encoding := self._type_encoding_map.get(obj_type):
                return self._read_string(struct, encoding)
            else:
                return struct.unpack(self._bio.read(struct.size))[0]
        else:
            return self.read_json()

    def _read_string(self, struct: Struct, encoding: str) -> str:
        str_len = struct.unpack(self._bio.read(struct.size))[0]
        return self._bio.read(str_len).decode(encoding)

    def _read_byte_str(self, struct: Struct) -> bytes:
        str_len = struct.unpack(self._bio.read(struct.size))[0]
        return self._bio.read(str_len)

    def read_string_1(self) -> str:
        return self._read_string(self._int8, 'ascii')

    def read_string_4(self, encoding: str = 'utf-8') -> str:
        return self._read_string(self._int32, encoding)

    def read_json(self):
        # Note: The order of the following calls is important
        return {
            'assembly_name': self.read_string_1(),
            'class_name': self.read_string_1(),
            'json': json.loads(self._read_byte_str(self._int32)),
        }


# endregion
