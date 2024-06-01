#!/usr/bin/env python

from __future__ import annotations

import json
import logging
import os
from abc import ABC
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from datetime import datetime
from functools import cached_property
from pathlib import Path

from cli_command_parser import Command, SubCommand, Flag, Counter, Option, Action, ParamGroup, main
from cli_command_parser.inputs import Path as IPath, NumRange
from cli_command_parser.inputs.time import DateTime, DEFAULT_DATE_FMT, DEFAULT_DT_FMT

from mm.__version__ import __author_email__, __version__  # noqa
from mm.session import MementoMoriSession
from mm.fs import path_repr
from mm.logging import init_logging, log_initializer
from mm.output import CompactJSONEncoder, pprint
from mm.utils import FutureWaiter

log = logging.getLogger(__name__)

DIR = IPath(type='dir')
NEW_FILE = IPath(type='file', exists=False)
FILES = IPath(type='file|dir', exists=True)
DATE_OR_DT = DateTime(DEFAULT_DATE_FMT, DEFAULT_DT_FMT)


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


class ListAssets(List, choice='assets', help='List asset paths'):
    path = Option('-p', help='Show assets relative to the specified path')
    depth: int = Option('-d', help='Show assets up to the specified depth')

    def main(self):
        asset_catalog = self.mm_session.asset_catalog
        tree = asset_catalog.get_asset(self.path) if self.path else asset_catalog.asset_tree
        for asset in tree.iter_flat(self.depth):
            print(asset)


class ListExtensions(List, choices=('extensions', 'exts'), help='List file extensions used by assets'):
    def main(self):
        from collections import Counter
        from os.path import splitext

        counter = Counter(
            splitext(entry)[-1]
            for entry in self.mm_session.asset_catalog.internal_ids
            if not entry.startswith('0#/')
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
    split = Flag('-s', help='Split the catalog into separate files for each top-level key')
    decode = Flag('-d', help='Decode base64-encoded content (only applies when --split / -s is specified)')

    @section(help='Save the asset catalog, which contains metadata about game assets')
    def data(self):
        for name_parts, data, raw in self.iter_names_and_data():
            self.save_data(data, *name_parts, raw=raw)

    def iter_names_and_data(self):
        asset_catalog = self.mm_session.asset_catalog
        if not self.split:
            yield ('asset-catalog.json',), asset_catalog.data, False
        else:
            dir_name = 'asset-catalog'
            decoded_map = {
                'm_KeyDataString': 'key_data',
                'm_BucketDataString': 'bucket_data',
                'm_EntryDataString': 'entry_data',
                'm_ExtraDataString': 'extra_data',
            }
            for key, val in asset_catalog.data.items():
                if self.decode and (attr := decoded_map.get(key)):
                    yield (dir_name, f'{key}.dat'), getattr(asset_catalog, attr), True
                else:
                    yield (dir_name, f'{key}.json'), val, False

    @section(help='Save the deserialized keys from the asset catalog')
    def keys(self):
        path = self.output.joinpath('asset-catalog-keys.json')
        self._save_data(path, self.mm_session.asset_catalog.keys)

    @section(help='Save the deserialized locations from the asset catalog')
    def locations(self):
        path = self.output.joinpath('asset-catalog-locations.json')
        data = [row.as_dict() for row in self.mm_session.asset_catalog.locations]
        self._save_data(path, data)

    @section(help='Save the deserialized locations from the asset catalog')
    def bundle_path_map(self):
        path = self.output.joinpath('asset-catalog-bundle_path_map.json')
        self._save_data(path, self.mm_session.asset_catalog.bundle_path_map)


class SaveBundlesCmd(Save, ABC):
    with ParamGroup('File'):
        asset_path = Option(
            '-p', nargs='+', metavar='GLOB',
            help='One or more asset paths for which bundles should be included (supports wildcards)',
        )
        extension = Option(
            '-x', nargs='+', help='One or more asset file extensions for which bundles should be included'
        )

    limit: int = Option('-L', type=NumRange(min=1), help='Limit the number of bundle files to download')
    parallel: int = Option('-P', type=NumRange(min=1), default=4, help='Number of download threads to use in parallel')

    def download_bundles(self, save_dir: Path):
        if bundle_names := self._get_bundle_names(save_dir):
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

    def _get_bundle_names(self, save_dir: Path) -> list[str]:
        to_download = self._get_bundle_candidates()
        log.debug(f'Found {len(to_download):,d} total bundles to download')

        if not (self.force or not save_dir.exists()):
            to_download = [name for name in to_download if not save_dir.joinpath(name).exists()]
            log.debug(f'Filtered to {len(to_download):,d} new bundles to download')

        if self.limit:
            return to_download[:self.limit]
        return to_download

    def _get_bundle_candidates(self):
        bundle_path_map = self.mm_session.asset_catalog.bundle_path_map
        if path_pats := self.asset_path:
            from fnmatch import fnmatch

            bundle_path_map = {
                bundle: filtered
                for bundle, files in bundle_path_map.items()
                if (filtered := [f for f in files if any(fnmatch(f, pat) for pat in path_pats)])
            }

        if exts := tuple(self.extension):
            return [bundle for bundle, files in bundle_path_map.items() if any(f.endswith(exts) for f in files)]

        return bundle_path_map


class SaveBundles(SaveBundlesCmd, choice='bundles', help='Download raw bundles'):
    def main(self):
        self.download_bundles(self.output)


class SaveAssets(SaveBundlesCmd, choice='assets', help='Download raw bundles and extract assets from them'):
    bundle_dir = Option(
        '-b', type=DIR, help='Path to a dir that contains .bundle files, or that should be used to store them'
    )
    debug = Flag('-d', help='Enable logging in bundle processing workers')
    allow_raw = Flag(help='Allow extraction of unhandled asset types without any conversion/processing')

    def main(self):
        self.download_bundles(self.bundle_dir)
        self.extract_assets()

    def extract_assets(self):
        from mm.assets import find_bundles

        dst_dir, force, allow_raw = self.output, self.force, self.allow_raw
        with self.executor() as executor:
            futures = [
                executor.submit(bundle.extract, dst_dir, force, allow_raw) for bundle in find_bundles(self.bundle_dir)
            ]
            log.info(f'Extracting assets from {len(futures):,d} bundles...')
            FutureWaiter.wait_for(executor, futures, add_bar=not self.debug)

    def executor(self) -> ProcessPoolExecutor:
        return ProcessPoolExecutor(
            max_workers=self.parallel,
            initializer=log_initializer(self.verbose) if self.debug else None,
        )


# endregion


# region Bundle Commands


class BundleCommand(AssetCLI, ABC):
    input = Option('-i', type=FILES, nargs='+', help='Bundle file(s) or dir(s) containing .bundle files', required=True)
    earliest: datetime = Option('-e', type=DATE_OR_DT, help='Only include assets from bundles modified after this time')

    def find_bundles(self):
        from mm.assets import find_bundles

        yield from find_bundles(self.input, mod_after=self.earliest)


class ParallelBundleCommand(BundleCommand, ABC):
    parallel: int = Option('-P', type=NumRange(min=1), default=4, help='Number of processes to use in parallel')
    debug = Flag('-d', help='Enable logging in bundle processing workers')

    def executor(self) -> ProcessPoolExecutor:
        return ProcessPoolExecutor(
            max_workers=self.parallel,
            initializer=log_initializer(self.verbose) if self.debug else None,
        )


class Index(ParallelBundleCommand, help='Create a bundle index to facilitate bundle discovery for specific assets'):
    output: Path = Option('-o', type=NEW_FILE, help='Output path', required=True)

    def main(self):
        with self.executor() as executor:
            futures = {executor.submit(bundle.get_content_paths): bundle for bundle in self.find_bundles()}
            log.info(f'Processing {len(futures):,d} bundles...')
            with FutureWaiter(executor)(futures, add_bar=not self.debug) as waiter:
                bundle_contents = {futures[future].path.name: future.result() for future in waiter}

        log.info(f'Saving {path_repr(self.output)}')
        with self.output.open('w', encoding='utf-8') as f:
            json.dump(bundle_contents, f, indent=4, sort_keys=True, ensure_ascii=False)


class Find(BundleCommand, help='Find bundles containing the specified paths/files'):
    pattern = Option('-p', help='Path pattern to find (supports glob-style wildcards)')

    def main(self):
        matching_contents_iter = self.iter_matching_contents() if self.pattern else self.iter_bundle_contents()
        for src_path, content_path in matching_contents_iter:
            print(f'Bundle {path_repr(src_path)} contains: {content_path}')

    def iter_bundle_contents(self):
        for bundle in self.find_bundles():
            for path in bundle.contents:
                yield bundle.path, path

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


class Extract(ParallelBundleCommand, help='Extract assets from a .bundle file'):
    output: Path = Option('-o', type=DIR, help='Output directory', required=True)
    force = Flag('-F', help='Force re-extraction even if output files already exist (default: skip existing files)')
    allow_raw = Flag(help='Allow extraction of unhandled asset types without any conversion/processing')

    def main(self):
        dst_dir, force, allow_raw = self.output, self.force, self.allow_raw
        with self.executor() as executor:
            futures = [executor.submit(bundle.extract, dst_dir, force, allow_raw) for bundle in self.find_bundles()]
            log.info(f'Extracting assets from {len(futures):,d} bundles...')
            FutureWaiter.wait_for(executor, futures, add_bar=not self.debug)


# endregion


if __name__ == '__main__':
    main()
