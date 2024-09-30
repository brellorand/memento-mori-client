"""
Class that represents a single asset Bundle file, and helpers for Bundle file discovery
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Collection, Iterable, Iterator

from UnityPy import Environment
from UnityPy.files.BundleFile import BundleFile, DirectoryInfoFS
from UnityPy.files.File import File
from UnityPy.files.SerializedFile import SerializedFile
from UnityPy.helpers.ImportHelper import parse_file
from UnityPy.streams import EndianBinaryReader

from mm.fs import path_repr
from .extraction import BundleExtractor

if TYPE_CHECKING:
    from datetime import datetime

    from UnityPy.files.ObjectReader import ObjectReader
    from UnityPy.files.WebFile import WebFile

    from .apk import AssetPackApk

    UnityFile = File | SerializedFile | BundleFile | WebFile | EndianBinaryReader

__all__ = ['Bundle', 'DataBundle', 'FileBundle', 'find_bundles']
log = logging.getLogger(__name__)

PathLike = Path | str
PathOrPaths = PathLike | Iterable[PathLike]


class Bundle(ABC):
    def __init__(self, name: str):
        self.name = name

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}({str(self)!r})>'

    @property
    @abstractmethod
    def env(self) -> Environment:
        raise NotImplementedError

    @property
    def contents(self) -> dict[str, ObjectReader]:
        return self.env.container

    def get_content_paths(self) -> list[str]:
        return list(self.env.container)

    def extract(
        self,
        dst_dir: Path,
        force: bool = False,
        unknown_as_raw: bool = False,
        include_exts: tuple[str, ...] = None,
        debug: bool = False,
    ):
        BundleExtractor(dst_dir, force, unknown_as_raw, include_exts=include_exts, debug=debug).extract_bundle(self)

    def __len__(self) -> int:
        return len(self.env.container)


class DataBundle(Bundle):
    def __init__(self, name: str, raw_data: bytes):
        super().__init__(name)
        self.raw_data = raw_data

    def __str__(self) -> str:
        return self.name

    @cached_property
    def env(self) -> Environment:
        return Environment(self.raw_data)


class FileBundle(Bundle):
    def __init__(self, path: Path):
        super().__init__(path.name)
        self.path = path

    def __str__(self) -> str:
        return self.path_str

    @cached_property
    def path_str(self) -> str:
        return path_repr(self.path)

    @cached_property
    def env(self) -> Environment:
        return Environment(self.path.as_posix())  # UnityPy does not support Path objects


class LazyBundleFile(BundleFile):
    """
    UnityPy eagerly reads and processes data from bundles during ``BundleFile`` initialization, which results in high
    up-front loading time for an entire directory/APK and the need for significantly more data to be re-serialized
    and de-serialized via pickle when using multiprocessing.

    This class patches ``BundleFile`` to read data lazily.  When using multiprocessing, data is only read/processed in
    the worker process (assuming no relevant attributes are accessed before passing the object to the worker process).
    """

    def __init__(self, apk: AssetPackApk, parent: File | Environment, name: str, **kwargs):  # noqa
        File.__init__(self, parent, name, **kwargs)
        self.__apk = apk

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}[{self.name}]>'

    @cached_property
    def __reader(self) -> EndianBinaryReader:
        return EndianBinaryReader(self.__apk.get_bundle_data(self.name))

    @cached_property
    def __header_data(self):
        reader = self.__reader
        signature = reader.read_string_to_null()
        version = reader.read_u_int()
        version_player = reader.read_string_to_null()
        version_engine = reader.read_string_to_null()
        return signature, version, version_player, version_engine

    @cached_property
    def signature(self) -> str:
        return self.__header_data[0]

    @cached_property
    def version(self) -> int:
        return self.__header_data[1]

    @cached_property
    def version_player(self) -> str:
        return self.__header_data[2]

    @cached_property
    def version_engine(self) -> str:
        return self.__header_data[3]

    @property
    def files(self) -> dict[str, UnityFile]:
        return self.__files

    @files.setter
    def files(self, value):
        return  # Ignore the initial set in File.__init__

    @cached_property
    def __files(self) -> dict[str, UnityFile]:
        if self.signature == 'UnityFS':
            m_directory_info, blocks_reader = self.read_fs(self.__reader)
        elif self.signature in ('UnityWeb', 'UnityRaw'):
            m_directory_info, blocks_reader = self.read_web_raw(self.__reader)
        elif self.signature == 'UnityArchive':
            raise NotImplementedError('BundleFile - UnityArchive')
        else:
            raise NotImplementedError(f'Unknown Bundle signature: {self.signature}')

        return self.__read_files(blocks_reader, m_directory_info)

    def __read_files(self, reader: EndianBinaryReader, files: list[DirectoryInfoFS]) -> dict[str, UnityFile]:
        log.debug(f'Reading files for {self}')
        parsed_files = {}
        for node in files:
            reader.Position = node.offset
            node_reader = EndianBinaryReader(reader.read(node.size), offset=(reader.BaseOffset + node.offset))
            parsed_files[node.path] = f = parse_file(node_reader, self, node.path, is_dependency=self.is_dependency)
            if self.environment and isinstance(f, (EndianBinaryReader, SerializedFile)):
                self.environment.register_cab(node.path, f)

            # required for BundleFiles
            f.flags = getattr(node, 'flags', 0)

        del self.__dict__['_LazyBundleFile__reader']
        return parsed_files


AnyBundleFile = LazyBundleFile | BundleFile | File


class BundleGroup:
    def __init__(self, env: Environment, name: str, bundle_names: Collection[str] = ()):
        self.env = env
        self.name = name
        self._bundle_names = set(bundle_names) if bundle_names else bundle_names

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}({str(self)!r})>'

    @classmethod
    def for_apk(cls, apk: AssetPackApk, bundle_names: Collection[str] = ()) -> BundleGroup:
        env = Environment()
        # The following replaces a call to `env.load(files)` / `env.load_files(files)` / similar
        env.files = {name: LazyBundleFile(apk, env, name=name, is_dependency=False) for name in apk.iter_bundle_names()}
        log.debug(
            f'Initializing {cls.__name__} for {apk=} with total_bundles={len(env.files)}, names={len(bundle_names)}'
        )
        return cls(env, apk.path.name, bundle_names)

    @classmethod
    def for_dir(cls, path: Path, bundle_names: Collection[str] = ()) -> BundleGroup:
        return cls(Environment(path.as_posix()), path.name, bundle_names)

    @cached_property
    def bundle_names(self) -> set[str]:
        if self._bundle_names:
            return self._bundle_names.intersection(self.env.files)
        return set(self.env.files)

    def get_container(self, bundle_name: str) -> dict[str, ObjectReader]:
        file: AnyBundleFile = self.env.files[bundle_name]
        return {} if file.is_dependency else file.container

    def extract(
        self,
        bundle_name: str,
        dst_dir: Path,
        force: bool = False,
        unknown_as_raw: bool = False,
        include_exts: tuple[str] = None,
    ):
        extractor = BundleExtractor(dst_dir, force, unknown_as_raw, include_exts=include_exts)
        extractor.extract_group_bundle(self, bundle_name)

    def __len__(self) -> int:
        return len(self.env.container)


def find_bundles(path_or_paths: PathOrPaths, *, mod_after: datetime = None) -> Iterator[FileBundle]:
    for path in find_bundle_paths(path_or_paths, mod_after=mod_after):
        yield FileBundle(path)


def find_bundle_paths(path_or_paths: PathOrPaths, *, mod_after: datetime = None) -> Iterator[Path]:
    if mod_after:
        earliest = mod_after.timestamp()
        return (path for path in _find_bundles(path_or_paths) if path.stat().st_mtime >= earliest)
    else:
        return _find_bundles(path_or_paths)


def _find_bundles(src_paths: PathOrPaths) -> Iterator[Path]:
    if isinstance(src_paths, (str, Path)):
        src_paths = [_normalize_path(src_paths)]

    for path in src_paths:
        if path.is_file():
            yield path
        else:
            for root, dirs, files in os.walk(path):
                for file in files:
                    yield Path(root, file)


def _normalize_path(path: PathLike) -> Path:
    return Path(path).expanduser().resolve() if isinstance(path, str) else path
