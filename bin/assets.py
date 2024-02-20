#!/usr/bin/env python

import logging
import os
from functools import cached_property
from pathlib import Path

from cli_command_parser import Command, SubCommand, Flag, Counter, Option, Action, main
from cli_command_parser.inputs import Path as IPath, NumRange

from mm.__version__ import __author_email__, __version__  # noqa
from mm.assets import BundleExtractor
from mm.client import DataClient
# from mm.fs import path_repr

log = logging.getLogger(__name__)

DIR = IPath(type='dir')
FILE = IPath(type='file', exists=True)
FILE_OR_DIR = IPath(type='file|dir', exists=True)


class AssetCLI(Command, description='Memento Mori Asset Manager', option_name_mode='*-'):
    action = SubCommand()
    no_cache = Flag('-C', help='Do not read cached game/catalog data')
    verbose = Counter('-v', help='Increase logging verbosity (can specify multiple times)')

    def _init_command_(self):
        log_fmt = '%(asctime)s %(levelname)s %(name)s %(lineno)d %(message)s' if self.verbose > 1 else '%(message)s'
        level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(level=level, format=log_fmt)

    @cached_property
    def client(self) -> DataClient:
        return DataClient(use_cache=not self.no_cache)


class List(AssetCLI, help='List asset paths'):
    path = Option('-p', help='Show assets relative to the specified path')
    depth: int = Option('-d', help='Show assets up to the specified depth')

    def main(self):
        tree = self.client.asset_catalog.get_asset(self.path) if self.path else self.client.asset_catalog.asset_tree
        for asset in tree.iter_flat(self.depth):
            print(asset)


class Save(AssetCLI, help='Save bundles/assets to the specified directory'):
    item = Action()
    # path = Option('-p', help='Save the specified asset, or all assets inside the specified path', required=True)
    output: Path = Option('-o', type=DIR, help='Output directory', required=True)
    limit: int = Option('-L', help='Limit the number of bundle files to download')
    force = Flag('-F', help='Force bundles to be re-downloaded even if they already exist')
    # dry_run = Flag('-D', help='Print the actions that would be taken instead of taking them')
    parallel: int = Option('-P', type=NumRange(min=1), default=4, help='Number of download threads to use in parallel')

    @item(help='Download raw bundles')
    def bundles(self):
        from concurrent.futures import ThreadPoolExecutor, as_completed

        out_dir = self.output.joinpath('bundles')
        out_dir.mkdir(parents=True, exist_ok=True)

        with ThreadPoolExecutor(max_workers=self.parallel) as executor:
            futures = {executor.submit(self.client.get_asset, name): name for name in self._get_bundle_names()}
            log.info(f'Downloading {len(futures)} bundles')
            for future in as_completed(futures):
                bundle_name = futures[future]
                out_path = out_dir.joinpath(bundle_name)
                log.info(f'Saving {bundle_name}')
                out_path.write_bytes(future.result())

        # downloaded = 0
        #
        # for bundle_name in self.client.asset_catalog.bundle_names:
        #     out_path = out_dir.joinpath(bundle_name)
        #     if self.force or not out_path.exists():
        #         log.info(f'Saving {bundle_name}')
        #         out_path.write_bytes(self.client.get_asset(bundle_name))
        #         downloaded += 1
        #         if self.limit and downloaded >= self.limit:
        #             log.info(f'Downloaded {downloaded} bundles - stopping')
        #             break
        #     else:
        #         log.debug(f'Skipping already downloaded {bundle_name}')

    def _get_bundle_names(self) -> list[str]:
        out_dir = self.output.joinpath('bundles')
        if self.force or not out_dir.exists():
            return self.client.asset_catalog.bundle_names

        to_download = [name for name in self.client.asset_catalog.bundle_names if not out_dir.joinpath(name).exists()]
        if self.limit:
            return to_download[:self.limit]
        return to_download

    @item(help='Download bundles and extract the contents')
    def assets(self):
        raise RuntimeError('Not supported yet')

    # def main(self):
    #     tree = self.client.asset_catalog.get_asset(self.path)
    #     for asset in tree.iter_flat():
    #         self._download_and_save(asset)
    #
    # def _download_and_save(self, asset: Asset):
    #     out_path = self.output.joinpath(str(asset))
    #     if self.dry_run:
    #         log.info(f'[DRY RUN] Would download {asset} -> {path_repr(out_path)}')
    #     else:
    #         log.debug(f'Downloading {asset}')
    #         data = self.client.get_asset(asset)
    #         out_path.parent.mkdir(parents=True, exist_ok=True)
    #         log.info(f'Saving {path_repr(out_path)}')
    #         out_path.write_bytes(data)


class Extract(AssetCLI, help='Extract assets from a .bundle file'):
    input: Path = Option(
        '-i', type=FILE_OR_DIR, help='Input .bundle file or dir containing .bundle files', required=True
    )
    output: Path = Option('-o', type=DIR, help='Output directory', required=True)
    parallel: int = Option(
        '-P', type=NumRange(min=1), default=4, help='Number of extraction processes to use in parallel'
    )

    def main(self):
        from concurrent.futures import ProcessPoolExecutor, wait

        extractor = BundleExtractor(self.output)
        with ProcessPoolExecutor(max_workers=self.parallel) as executor:
            # TODO: Fix logging to be initialized in each process
            futures = {
                executor.submit(extractor.extract_bundle, src_path): src_path for src_path in self.iter_src_paths()
            }
            wait(futures)

        # for src_path in self.iter_src_paths():
        #     extractor.extract_bundle(src_path)

    def iter_src_paths(self):
        if self.input.is_file():
            yield self.input
        else:
            for root, dirs, files in os.walk(self.input):
                for file in files:
                    yield Path(root, file)


if __name__ == '__main__':
    main()
