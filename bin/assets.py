#!/usr/bin/env python

from __future__ import annotations

import json
import logging
import os
from abc import ABC
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from datetime import datetime
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING

from cli_command_parser import Action, Command, Counter, Flag, Option, ParamGroup, SubCommand, main
from cli_command_parser.inputs import NumRange, Path as IPath
from cli_command_parser.inputs.time import DEFAULT_DATE_FMT, DEFAULT_DT_FMT, DateTime

from mm.__version__ import __author_email__, __version__  # noqa
from mm.assets.processing import AssetBundleFinder, AssetConverter, AssetExtractor, BundleFinder
from mm.fs import path_repr
from mm.logging import init_logging, log_initializer
from mm.output import CompactJSONEncoder, pprint
from mm.session import MementoMoriSession
from mm.utils import FutureWaiter

if TYPE_CHECKING:
    from mm.assets.catalog import AssetCatalog

log = logging.getLogger(__name__)

DIR = IPath(type='dir')
REAL_DIR = IPath(type='dir', exists=True)
NEW_FILE = IPath(type='file', exists=False)
FILES = IPath(type='file|dir', exists=True)
FILE = IPath(type='file', exists=True)
DATE_OR_DT = DateTime(DEFAULT_DATE_FMT, DEFAULT_DT_FMT)
ASSET_PATH_HELP = 'One or more asset paths for which bundles should be included (supports wildcards)'


class AssetCLI(Command, description='Memento Mori Asset Manager', option_name_mode='*-'):
    action = SubCommand()
    no_cache = Flag('-C', help='Do not read cached game/catalog data')
    config_file = Option(
        '-cf', type=IPath(type='file'), help='Config file path (default: ~/.config/memento-mori-client)'
    )
    verbose = Counter('-v', help='Increase logging verbosity (can specify multiple times)')

    def _init_command_(self):
        init_logging(self.verbose)

    @cached_property
    def mm_session(self) -> MementoMoriSession:
        return MementoMoriSession(self.config_file, use_auth_cache=not self.no_cache, use_data_cache=not self.no_cache)


class List(AssetCLI, help='List asset paths'):
    item = SubCommand(help='What to list')
    apk_path = Option('-a', type=FILE, help='Path to an APK file to use as a source for bundles')

    @cached_property
    def asset_catalog(self) -> AssetCatalog:
        if self.apk_path:
            from mm.assets.apk import ApkArchive

            return ApkArchive(self.apk_path).asset_pack_apk.catalog
        else:
            return self.mm_session.asset_catalog


class ListAssets(List, choice='assets', help='List asset paths'):
    path = Option('-p', help='Show assets relative to the specified path')
    depth: int = Option('-d', help='Show assets up to the specified depth')

    def main(self):
        tree = self.asset_catalog.get_asset(self.path) if self.path else self.asset_catalog.asset_tree
        for asset in tree.iter_flat(self.depth):
            print(asset)


class ListExtensions(List, choices=('extensions', 'exts'), help='List file extensions used by assets'):
    def main(self):
        from collections import Counter
        from os.path import splitext

        counter = Counter(
            splitext(entry)[-1] for entry in self.asset_catalog.internal_ids if not entry.startswith('0#/')
        )
        pprint('json-pretty', counter)


# region Save Commands


class Save(AssetCLI, help='Save bundles/assets to the specified directory'):
    item = SubCommand(help='What to save')
    output: Path = Option('-o', type=DIR, help='Output directory', required=True)
    force = Flag('-F', help='Force files to be overwritten even if they already exist')

    def save_data(self, data, *name, raw: bool = False):
        self._save_data(self.output.joinpath(*name), data, raw)

    def _save_data(self, path: Path, data, raw: bool = False):
        if not self.force and path.exists():
            log.warning(f'Skipping {path_repr(path)} - it already exists (use --force to overwrite)')
            return

        path.parent.mkdir(parents=True, exist_ok=True)
        log.info(f'Saving {path_repr(path)}')
        if raw:
            path.write_bytes(data)
        else:
            with path.open('w', encoding='utf-8', newline='\n') as f:
                json.dump(data, f, ensure_ascii=False, indent=4, cls=CompactJSONEncoder)


class Catalog(Save, help='Save the asset catalog, which contains metadata about game assets'):
    section = Action()
    apk_path = Option('-a', type=FILE, help='Path to an APK file to use as a source for bundles')
    split = Flag('-s', help='Split the catalog into separate files for each top-level key')
    decode = Flag('-d', help='Decode base64-encoded content (only applies when --split / -s is specified)')
    no_subdir = Flag(
        '-S', help='When splitting the catalog into separate files, use the provided output dir, not a subdirectory'
    )

    @section(help='Save the asset catalog, which contains metadata about game assets')
    def data(self):
        for name_parts, data, raw in self.iter_names_and_data():
            if self.no_subdir:
                name_parts = (name_parts[-1],)
            self.save_data(data, *name_parts, raw=raw)

    @cached_property
    def asset_catalog(self) -> AssetCatalog:
        if self.apk_path:
            from mm.assets.apk import ApkArchive

            return ApkArchive(self.apk_path).asset_pack_apk.catalog
        else:
            return self.mm_session.asset_catalog

    def iter_names_and_data(self):
        if not self.split:
            yield ('asset-catalog.json',), self.asset_catalog.data, False
        else:
            dir_name = 'asset-catalog'
            decoded_map = {
                'm_KeyDataString': 'key_data',
                'm_BucketDataString': 'bucket_data',
                'm_EntryDataString': 'entry_data',
                'm_ExtraDataString': 'extra_data',
            }
            for key, val in self.asset_catalog.data.items():
                if self.decode and (attr := decoded_map.get(key)):
                    yield (dir_name, f'{key}.dat'), getattr(self.asset_catalog, attr), True
                else:
                    yield (dir_name, f'{key}.json'), val, False

    @section(help='Save the deserialized keys from the asset catalog')
    def keys(self):
        path = self.output.joinpath('asset-catalog-keys.json')
        self._save_data(path, self.asset_catalog.keys)

    @section(help='Save the deserialized locations from the asset catalog')
    def locations(self):
        path = self.output.joinpath('asset-catalog-locations.json')
        data = [row.as_dict() for row in self.asset_catalog.locations]
        self._save_data(path, data)

    @section(help='Save the deserialized locations from the asset catalog')
    def bundle_path_map(self):
        path = self.output.joinpath('asset-catalog-bundle_path_map.json')
        self._save_data(path, self.asset_catalog.bundle_path_map)


class SaveBundlesCmd(Save, ABC):
    with ParamGroup('Asset File'):
        bundle_names = Option('-n', nargs='+', help='Names of specific bundles to include')
        asset_path = Option('-p', nargs='+', metavar='GLOB', help=ASSET_PATH_HELP)
        extension = Option(
            '-x', nargs='+', help='One or more asset file extensions for which bundles should be included'
        )

    limit: int = Option('-L', type=NumRange(min=1), help='Limit the number of bundle files to download')
    parallel: int = Option('-P', type=NumRange(min=1), default=4, help='Number of download threads to use in parallel')

    def download_bundles(self, save_dir: Path):
        finder = BundleFinder(
            self.mm_session,
            save_dir,
            limit=self.limit,
            bundle_names=self.bundle_names,
            asset_path_pats=self.asset_path,
            extensions=self.extension,
        )
        if bundle_names := finder.get_bundle_names(save_dir, self.force):
            self._download_bundles(save_dir, bundle_names)
        else:
            log.info('All bundles have already been downloaded (use --force to force them to be re-downloaded)')

    def _download_bundles(self, save_dir: Path, bundle_names: list[str]):
        save_dir.mkdir(parents=True, exist_ok=True)
        log.info(f'Downloading {len(bundle_names):,d} bundles using {self.parallel} workers')
        with ThreadPoolExecutor(max_workers=self.parallel) as executor:
            futures = {executor.submit(self.mm_session.data_client.get_asset, name): name for name in bundle_names}
            with FutureWaiter(executor)(futures, add_bar=not self.verbose) as waiter:
                for future in waiter:
                    self._save_bundle(save_dir, futures[future], future.result())

    def _save_bundle(self, save_dir: Path, bundle_name: str, data: bytes):
        out_path = save_dir.joinpath(bundle_name)
        log.debug(f'Saving {bundle_name}')
        out_path.write_bytes(data)


class SaveBundles(SaveBundlesCmd, choice='bundles', help='Download raw bundles'):
    def main(self):
        self.download_bundles(self.output)


class ConverterMixin:
    skip_flac: bool
    ffmpeg_path: Path | None
    output: Path
    force: bool
    debug: bool

    def _should_convert_to_flac(self) -> bool:
        if self.skip_flac:
            return False
        if self.ffmpeg_path:
            return True

        from shutil import which

        return bool(which('ffmpeg'))

    def maybe_convert_audio(self):
        if not self._should_convert_to_flac():
            return

        converter = AssetConverter(self.output, self.ffmpeg_path, self.force, self.debug)
        converter.convert_audio()


class SaveAssets(
    ConverterMixin, SaveBundlesCmd, choice='assets', help='Download raw bundles and extract assets from them'
):
    with ParamGroup(mutually_exclusive=True, required=True):
        latest_apk = Flag('-A', help='Save assets from the latest APK')
        apk_path: Path = Option('-a', type=FILE, help='Path to an APK file to use as a source for bundles')
        bundle_dir: Path = Option(
            '-b', type=DIR, help='Path to a dir that contains .bundle files, or that should be used to store them'
        )

    debug = Flag('-d', help='Enable logging in bundle processing workers')
    allow_raw = Flag(help='Allow extraction of unhandled asset types without any conversion/processing')
    skip_flac = Flag(help='Skip conversion of audio files to flac (default: attempt to convert if ffmpeg is available)')
    ffmpeg_path = Option('-f', type=FILE, help='Path to ffmpeg, if it is not in your $PATH')

    def main(self):
        if self.bundle_dir:
            self.download_bundles(self.bundle_dir)
        elif self.latest_apk:
            from mm.assets.apk import ApkDownloader

            downloader = ApkDownloader()
            path = downloader.get_path(None)
            if path.exists():
                log.debug(f'The latest APK was already saved: {path.as_posix()}')
                self.apk_path = path
            else:
                self.apk_path = downloader.download_latest(None)[0]  # noqa

        self.extract_assets()
        self.maybe_convert_audio()

    def extract_assets(self):
        finder = AssetBundleFinder(
            self.mm_session,
            self.bundle_dir,
            apk_path=self.apk_path,
            limit=self.limit,
            bundle_names=self.bundle_names,
            asset_path_pats=self.asset_path,
            extensions=self.extension,
        )
        extractor = AssetExtractor(finder, self.output, self.parallel, self.verbose, self.debug)
        extractor.extract_assets(self.force, self.allow_raw)


# endregion


# region Bundle Commands


class BundleCommand(AssetCLI, ABC):
    with ParamGroup('Asset File'):
        bundle_names = Option('-n', nargs='+', help='Names of specific bundles to include')
        asset_path = Option('-p', nargs='+', metavar='GLOB', help=ASSET_PATH_HELP)
        extension = Option(
            '-x', nargs='+', help='One or more asset file extensions for which bundles should be included'
        )

    with ParamGroup(mutually_exclusive=True, required=True):
        apk_path = Option('-a', type=FILE, help='Path to an APK file to use as a source for bundles')
        bundle_dir = Option(
            '-b', type=DIR, help='Path to a dir that contains .bundle files, or that should be used to store them'
        )

    earliest: datetime = Option('-e', type=DATE_OR_DT, help='Only include assets from bundles modified after this time')

    @cached_property
    def finder(self) -> AssetBundleFinder:
        return AssetBundleFinder(
            self.mm_session,
            self.bundle_dir,
            apk_path=self.apk_path,
            bundle_names=self.bundle_names,
            asset_path_pats=self.asset_path,
            extensions=self.extension,
            earliest=self.earliest,
        )


class Index(BundleCommand, help='Create a bundle index to facilitate bundle discovery for specific assets'):
    output: Path = Option('-o', type=NEW_FILE, help='Output path', required=True)
    parallel: int = Option('-P', type=NumRange(min=1), default=4, help='Number of processes to use in parallel')
    debug = Flag('-d', help='Enable logging in bundle processing workers')

    def main(self):
        group = self.finder.get_bundle_group()
        with self.executor() as executor:
            futures = {executor.submit(group.get_container, name): name for name in group.bundle_names}
            log.info(f'Processing {len(futures):,d} bundles...')
            with FutureWaiter(executor)(futures, add_bar=not self.debug) as waiter:
                bundle_contents = {futures[future]: list(future.result()) for future in waiter}

        log.info(f'Saving {path_repr(self.output)}')
        with self.output.open('w', encoding='utf-8') as f:
            json.dump(bundle_contents, f, indent=4, sort_keys=True, ensure_ascii=False)

    def executor(self) -> ProcessPoolExecutor:
        return ProcessPoolExecutor(
            max_workers=self.parallel,
            initializer=log_initializer(self.verbose) if self.debug else None,
        )


class Find(BundleCommand, help='Find bundles containing the specified paths/files'):
    pattern = Option('-P', help='Path pattern to find (supports glob-style wildcards)')

    def main(self):
        matching_contents_iter = self.iter_matching_contents() if self.pattern else self.iter_bundle_contents()
        for src_path, content_path in matching_contents_iter:
            print(f'Bundle {src_path} contains: {content_path}')

    def iter_bundle_contents(self):
        group = self.finder.get_bundle_group()
        for name in group.bundle_names:
            for path in group.get_container(name):
                yield name, path

    def iter_matching_contents(self):
        import posixpath
        from fnmatch import _compile_pattern  # noqa
        from os.path import normcase

        match = _compile_pattern(normcase(self.pattern))
        if os.path is posixpath:  # normcase on posix is NOP. Optimize it away from the loop.
            for src_path, content_path in self.iter_bundle_contents():
                if match(content_path):
                    yield src_path, content_path
        else:
            for src_path, content_path in self.iter_bundle_contents():
                if match(normcase(content_path)):
                    yield src_path, content_path


class Extract(ConverterMixin, BundleCommand, help='Extract assets from a .bundle file'):
    output: Path = Option('-o', type=DIR, help='Output directory', required=True)

    force = Flag('-F', help='Force re-extraction even if output files already exist (default: skip existing files)')
    allow_raw = Flag(help='Allow extraction of unhandled asset types without any conversion/processing')
    skip_flac = Flag(help='Skip conversion of audio files to flac (default: attempt to convert if ffmpeg is available)')
    ffmpeg_path = Option('-f', type=FILE, help='Path to ffmpeg, if it is not in your $PATH')

    parallel: int = Option('-P', type=NumRange(min=1), default=4, help='Number of processes to use in parallel')
    debug = Flag('-d', help='Enable logging in bundle processing workers')

    def main(self):
        extractor = AssetExtractor(self.finder, self.output, self.parallel, self.verbose, self.debug)
        extractor.extract_assets(self.force, self.allow_raw)
        self.maybe_convert_audio()


# endregion


class Convert(AssetCLI, help='Convert extracted audio assets to FLAC'):
    asset_dir = Option('-a', type=REAL_DIR, help='Directory containing assets to possibly be converted', required=True)
    parallel: int = Option('-P', type=NumRange(min=1), default=4, help='Number of processes to use in parallel')
    force = Flag('-F', help='Force re-extraction even if output files already exist (default: skip existing files)')
    debug = Flag('-d', help='Enable logging in bundle processing workers')
    ffmpeg_path = Option('-f', type=FILE, help='Path to ffmpeg, if it is not in your $PATH')

    def main(self):
        AssetConverter(self.asset_dir, self.ffmpeg_path, self.force, self.debug, self.parallel).convert_audio()


if __name__ == '__main__':
    main()
