"""
"""

from __future__ import annotations

import json
import logging
from enum import Enum
from functools import cached_property
from pathlib import Path
from weakref import finalize
from zipfile import ZipFile, ZipInfo

from mm.fs import get_user_cache_dir
from .bundles import Bundle
from .catalog import AssetCatalog

__all__ = ['ApkArchive', 'AssetPackApk', 'ApkType']
log = logging.getLogger(__name__)

ASSET_PACK_NAME = 'UnityDataAssetPack.apk'


class ApkArchive:
    def __init__(self, path: Path | str, parent: ApkArchive = None):
        self.parent = parent
        self.path = Path(path).expanduser() if not isinstance(path, Path) else path
        self._cache_dir = get_user_cache_dir(f'apk/{self.version}' if self.version else 'apk')

    @cached_property
    def asset_pack_apk(self) -> AssetPackApk:
        if self.type == ApkType.APK:
            return AssetPackApk(self.path)

        path = self._cache_dir.joinpath(ASSET_PACK_NAME)
        if path.exists():
            return AssetPackApk(path, parent=self)

        self._zip_file.extract(ASSET_PACK_NAME, self._cache_dir)
        return AssetPackApk(path, parent=self)

    @cached_property
    def _zip_file(self) -> ZipFile:
        file = ZipFile(self.path)
        self._finalizer = finalize(self, self._close, file)  # noqa
        return file

    @cached_property
    def file_info(self) -> dict[str, ZipInfo]:
        return {file.filename: file for file in self._zip_file.infolist()}

    @cached_property
    def type(self) -> ApkType:
        if 'manifest.json' in self.file_info and ASSET_PACK_NAME in self.file_info:
            return ApkType.XAPK
        else:
            return ApkType.APK

    @cached_property
    def version(self) -> str | None:
        if self.type == ApkType.APK:
            return self.parent.version if self.parent else None
        manifest = json.loads(self._zip_file.read('manifest.json'))
        return manifest['version_name']

    @classmethod
    def _close(cls, file: ZipFile):
        file.close()


class AssetPackApk(ApkArchive):
    @cached_property
    def asset_pack_apk(self) -> AssetPackApk:
        return self

    @cached_property
    def catalog(self) -> AssetCatalog:
        path = self._cache_dir.joinpath('catalog.json')
        if not path.exists():
            path.write_bytes(self._zip_file.read('assets/aa/catalog.json'))
        return AssetCatalog(json.loads(path.read_text('utf-8')))

    @cached_property
    def bundle_dir(self) -> Path:
        return self._cache_dir.joinpath('bundles')

    def get_bundle(self, name: str) -> Bundle:
        return Bundle(self.get_bundle_path(name))

    def get_bundle_path(self, name: str) -> Path:
        path = self.bundle_dir.joinpath(name)
        if path.exists():
            return path

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self._zip_file.read(f'assets/aa/Android/{name}'))
        return path


class ApkType(Enum):
    XAPK = 'xapk'
    APK = 'apk'
