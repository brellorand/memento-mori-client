"""
"""

from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from datetime import datetime
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Collection, Iterator

from mm.fs import path_repr
from mm.logging import log_initializer
from mm.utils import FutureWaiter
from .bundles import FileBundle, Bundle, BundleGroup, find_bundles, find_bundle_paths

if TYPE_CHECKING:
    from mm.session import MementoMoriSession
    from .apk import AssetPackApk
    from .catalog import AssetCatalog

__all__ = ['BundleFinder', 'AssetBundleFinder', 'AssetExtractor', 'AssetConverter']
log = logging.getLogger(__name__)


class BundleFinder:
    """
    Used to find bundles that should be downloaded from the asset catalog.

    This base class is only used when downloading bundles, not when extracting assets from those bundles.
    The :class:`AssetBundleFinder` class below is used when extracting assets.
    """

    def __init__(
        self,
        mm_session: MementoMoriSession,
        bundle_dir: Path,
        *,
        limit: int = None,
        bundle_names: Collection[str] = None,
        asset_path_pats: Collection[str] = None,
        extensions: Collection[str] = None,
    ):
        self.mm_session = mm_session
        self.bundle_dir = bundle_dir
        self.limit = limit
        self.bundle_names = set(bundle_names) if bundle_names else None
        self.asset_path_pats = asset_path_pats
        self.extensions = tuple(extensions) if extensions else None

    @cached_property
    def asset_catalog(self) -> AssetCatalog:
        return self.mm_session.asset_catalog

    def get_bundle_names(self, save_dir: Path = None, force: bool = False, action: str = 'download') -> list[str]:
        bundle_names = self._get_bundle_candidates()
        log.debug(f'Found {len(bundle_names):,d} total bundles to {action}')

        if save_dir and not (force or not save_dir.exists()):
            bundle_names = [name for name in bundle_names if not save_dir.joinpath(name).exists()]
            log.debug(f'Filtered to {len(bundle_names):,d} new bundles to {action}')

        if self.limit:
            return bundle_names[:self.limit]
        return bundle_names

    def _get_bundle_candidates(self):
        bundle_path_map = self.asset_catalog.bundle_path_map
        if self.bundle_names:
            bundle_path_map = {name: bundle_path_map[name] for name in self.bundle_names.intersection(bundle_path_map)}
            for name in self.bundle_names:
                bundle_path_map.setdefault(name, [])  # Allow bundles in a directory but not in the asset catalog

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
    """Used to find bundles from either a directory or an APK file during asset extraction"""

    def __init__(
        self,
        mm_session: MementoMoriSession,
        bundle_dir: Path = None,
        *,
        apk_path: Path = None,
        earliest: datetime = None,
        limit: int = None,
        bundle_names: Collection[str] = None,
        asset_path_pats: Collection[str] = None,
        extensions: Collection[str] = None,
    ):
        super().__init__(
            mm_session,
            bundle_dir,
            limit=limit,
            bundle_names=bundle_names,
            asset_path_pats=asset_path_pats,
            extensions=extensions,
        )
        self.apk_path = apk_path
        self.earliest = earliest

    def get_bundle_group(self) -> BundleGroup | None:
        if (bundle_dir := self.bundle_dir) and not (self.bundle_names or self.asset_path_pats or self.extensions):
            if self.earliest:
                bundle_names = {p.name for p in find_bundle_paths(bundle_dir, mod_after=self.earliest)}
                return BundleGroup.for_dir(bundle_dir, bundle_names=bundle_names)
            return BundleGroup.for_dir(bundle_dir)
        elif not (bundle_names := self.get_bundle_names(action='extract')):
            return None
        elif bundle_dir:
            if self.earliest:
                earliest = self.earliest.timestamp()
                bundle_names = {name for name in bundle_names if bundle_dir.joinpath(name).stat().st_mtime >= earliest}
            return BundleGroup.for_dir(bundle_dir, bundle_names=bundle_names)
        else:
            return BundleGroup.for_apk(self._asset_pack_apk, bundle_names)

    def find_bundles(self) -> Iterator[Bundle]:
        if (bundle_dir := self.bundle_dir) and not (self.bundle_names or self.asset_path_pats or self.extensions):
            yield from find_bundles(self.bundle_dir, mod_after=self.earliest)
        elif bundle_names := self.get_bundle_names(action='extract'):
            if bundle_dir:
                paths = (bundle_dir.joinpath(name) for name in bundle_names)
                if self.earliest:
                    earliest = self.earliest.timestamp()
                    paths = (path for path in paths if path.stat().st_mtime >= earliest)

                for path in paths:
                    yield FileBundle(path)
            else:
                yield from self._asset_pack_apk.iter_bundles(bundle_names)

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
        # TODO: Switch to the group approach?
        # group = self.finder.get_bundle_group()
        with self.executor() as executor:
            # futures = [
            #     executor.submit(group.extract, name, dst_dir, force, allow_raw, exts)
            #     for name in group.bundle_names
            # ]
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
            log.info(f'Converting {len(paths)} audio files to flac...')
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
