"""
"""

from __future__ import annotations

import json
import logging
import re
from enum import Enum
from functools import cached_property
from pathlib import Path
from typing import Iterator, Iterable
from weakref import finalize
from zipfile import ZipFile, ZipInfo

from cloudscraper import CloudScraper
from requests import Session, Response
from tqdm import tqdm

from mm.fs import get_user_cache_dir
from .bundles import DataBundle
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

    def __getstate__(self):
        return self.parent, self.path, self._cache_dir

    def __setstate__(self, state):
        self.parent, self.path, self._cache_dir = state

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

    def get_bundle(self, name: str) -> DataBundle:
        return DataBundle(name, self._zip_file.read(f'assets/aa/Android/{name}'))

    def iter_bundles(self, names: Iterable[str]) -> Iterator[DataBundle]:
        for name in names:
            yield DataBundle(name, self._zip_file.read(f'assets/aa/Android/{name}'))


class ApkType(Enum):
    XAPK = 'xapk'
    APK = 'apk'


class ApkDownloader:
    host = 'apkpure.com'
    package = 'jp.boi.mementomori.android'

    def __init__(self, *, browser: str = 'firefox', platform: str = 'windows', chunk_size: int = 1_048_576):
        self.browser = browser
        self.platform = platform
        self.chunk_size = chunk_size  # default: 1 MB (1024 * 1024)

    @cached_property
    def _session(self) -> Session:
        # Note: CloudScraper is required to handle Cloudflare verification
        return CloudScraper(browser={'browser': self.browser, 'platform': self.platform, 'mobile': False})

    def _get(self, url: str, **kwargs) -> Response:
        resp = self._session.get(url, **kwargs)
        resp.raise_for_status()
        return resp

    @cached_property
    def latest_version(self) -> str | None:
        resp = self._get(f'https://{self.host}/mementomori-afkrpg/{self.package}/download')
        if m := re.match(r"version_name:\s+'(.+?)'", resp.text):
            return m.group(1).strip()
        return None

    def download_latest(self, download_dir: Path) -> tuple[Path, int]:
        resp = self._get(f'https://d.{self.host}/b/XAPK/{self.package}', params={'version': 'latest'}, stream=True)
        path = self._get_path(download_dir, resp.headers.get('Content-Disposition'))
        try:
            size = int(resp.headers.get('Content-Length'))
        except (ValueError, TypeError):
            size = None

        written = 0
        with tqdm(total=size, unit='B', unit_scale=True, smoothing=0.1) as prog_bar, path.open('wb') as f:
            for chunk in resp.iter_content(chunk_size=self.chunk_size):
                written += f.write(chunk)
                prog_bar.update(len(chunk))

        return path, written

    def _get_path(self, download_dir: Path, content_disposition: str | None) -> Path:
        version = _get_version(content_disposition) or self.latest_version
        download_dir.mkdir(parents=True, exist_ok=True)
        return download_dir.joinpath(f'{self.package}_{version}.xapk')


def _get_version(content_disposition: str | None) -> str | None:
    # Example: 'attachment; filename="MementoMori: AFKRPG_2.17.0_APKPure.xapk"'
    if not content_disposition:
        return None
    elif m := re.search(r'_(\d+\.\d+\.\d+)_.*\.xapk"$', content_disposition):
        return m.group(1)
    log.debug(f'Could not find version in {content_disposition=}')
    return None
