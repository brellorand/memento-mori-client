"""
"""

from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from datetime import datetime
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Collection

from mm.fs import path_repr
from mm.logging import log_initializer
from mm.utils import FutureWaiter

if TYPE_CHECKING:
    from mm.session import MementoMoriSession
    from .apk import AssetPackApk
    from .catalog import AssetCatalog

__all__ = ['BundleFinder', 'AssetBundleFinder', 'AssetExtractor', 'AssetConverter']
log = logging.getLogger(__name__)


class BundleFinder:
    def __init__(
        self,
        mm_session: MementoMoriSession,
        bundle_dir: Path,
        *,
        limit: int = None,
        asset_path_pats: Collection[str] = None,
        extensions: Collection[str] = None,
    ):
        self.mm_session = mm_session
        self.bundle_dir = bundle_dir
        self.limit = limit
        self.asset_path_pats = asset_path_pats
        self.extensions = tuple(extensions) if extensions else None

    def find_bundles(self):
        from mm.assets import find_bundles

        yield from find_bundles(self.bundle_dir)

    @cached_property
    def asset_catalog(self) -> AssetCatalog:
        return self.mm_session.asset_catalog

    def get_bundle_names(self, save_dir: Path, force: bool = False) -> list[str]:
        to_download = self._get_bundle_candidates()
        log.debug(f'Found {len(to_download):,d} total bundles to download')

        if not (force or not save_dir.exists()):
            to_download = [name for name in to_download if not save_dir.joinpath(name).exists()]
            log.debug(f'Filtered to {len(to_download):,d} new bundles to download')

        if self.limit:
            return to_download[:self.limit]
        return to_download

    def _get_bundle_candidates(self):
        bundle_path_map = self.asset_catalog.bundle_path_map
        if asset_path_pats := self.asset_path_pats:
            from fnmatch import fnmatch

            bundle_path_map = {
                bundle: filtered
                for bundle, files in bundle_path_map.items()
                if (filtered := [f for f in files if any(fnmatch(f, pat) for pat in asset_path_pats)])
            }

        if exts := self.extensions:
            return [bundle for bundle, files in bundle_path_map.items() if any(f.endswith(exts) for f in files)]

        return bundle_path_map


class AssetBundleFinder(BundleFinder):
    def __init__(
        self,
        mm_session: MementoMoriSession,
        bundle_dir: Path = None,
        *,
        apk_path: Path = None,
        earliest: datetime = None,
        limit: int = None,
        asset_path_pats: Collection[str] = None,
        extensions: Collection[str] = None,
    ):
        super().__init__(mm_session, bundle_dir, limit=limit, asset_path_pats=asset_path_pats, extensions=extensions)
        self.apk_path = apk_path
        self.earliest = earliest

    def find_bundles(self):
        if self.bundle_dir:
            from mm.assets import find_bundles

            yield from find_bundles(self.bundle_dir, mod_after=self.earliest)
        else:
            bundle_names = self.get_bundle_names(self._asset_pack_apk.bundle_dir, force=True)
            for name in bundle_names:
                yield self._asset_pack_apk.get_bundle(name)

    @cached_property
    def asset_catalog(self) -> AssetCatalog:
        if self.apk_path:
            return self._asset_pack_apk.catalog
        else:
            return self.mm_session.asset_catalog

    @cached_property
    def _asset_pack_apk(self) -> AssetPackApk | None:
        if not self.apk_path:
            return None

        from mm.assets.apk import ApkArchive

        return ApkArchive(self.apk_path).asset_pack_apk


class AssetExtractor:
    def __init__(self, finder: AssetBundleFinder, output: Path, parallel: int, verbose: int, debug: bool):
        self.finder = finder
        self.output = output
        self.parallel = parallel
        self.verbose = verbose
        self.debug = debug

    def executor(self) -> ProcessPoolExecutor:
        return ProcessPoolExecutor(
            max_workers=self.parallel,
            initializer=log_initializer(self.verbose) if self.debug else None,
        )

    def extract_assets(self, force: bool, allow_raw: bool):
        dst_dir, exts = self.output, self.finder.extensions
        with self.executor() as executor:
            futures = [
                executor.submit(bundle.extract, dst_dir, force, allow_raw, exts)
                for bundle in self.finder.find_bundles()
            ]
            log.info(f'Extracting assets from {len(futures):,d} bundles...')
            if futures:
                FutureWaiter.wait_for(executor, futures, add_bar=not self.debug, unit=' assets')


class AssetConverter:
    def __init__(self, asset_dir: Path, ffmpeg_path: Path, force: bool, debug: bool, parallel: int = 1):
        self.asset_dir = asset_dir
        self.ffmpeg_path = ffmpeg_path
        self.force = force
        self.debug = debug
        self.parallel = parallel

    def convert_audio(self):
        if paths := list(self.find_audio_files()):
            self._convert_audio(paths)
        else:
            log.info(f'No .wav files were found in {path_repr(self.asset_dir)} (or all had .flac equivalents already)')

    def _convert_audio(self, paths: list[tuple[Path, Path]]):
        from mm.assets.ffmpeg import Ffmpeg

        ffmpeg = Ffmpeg(self.ffmpeg_path)
        with ThreadPoolExecutor(max_workers=self.parallel) as executor:
            futures = [
                executor.submit(ffmpeg.convert_to_flac, wav_path, flac_path, capture=not self.debug)
                for wav_path, flac_path in paths
            ]
            FutureWaiter.wait_for(executor, futures, add_bar=not self.debug, unit=' assets')

    def find_audio_files(self):
        for root, dirs, files in os.walk(self.asset_dir):
            for f in files:
                if f.endswith('.wav'):
                    wav_path = Path(root, f)
                    flac_path = wav_path.with_suffix('.flac')
                    if self.force or not flac_path.exists():
                        yield wav_path, flac_path
