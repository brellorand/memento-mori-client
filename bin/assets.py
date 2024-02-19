#!/usr/bin/env python

import logging
from functools import cached_property
from pathlib import Path

from cli_command_parser import Command, SubCommand, Flag, Counter, Option, main
from cli_command_parser.inputs import Path as IPath

from mm.__version__ import __author_email__, __version__  # noqa
from mm.assets import Asset
from mm.client import DataClient
from mm.fs import path_repr

log = logging.getLogger(__name__)

DIR = IPath(type='dir')


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


# region Save Subcommands


class Save(AssetCLI, help='Save assets to the specified directory'):
    path = Option('-p', help='Save the specified asset, or all assets inside the specified path', required=True)
    output: Path = Option('-o', type=DIR, help='Output directory', required=True)
    dry_run = Flag('-D', help='Print the actions that would be taken instead of taking them')

    def main(self):
        tree = self.client.asset_catalog.get_asset(self.path)
        for asset in tree.iter_flat():
            self._download_and_save(asset)

    def _download_and_save(self, asset: Asset):
        out_path = self.output.joinpath(str(asset))
        if self.dry_run:
            log.info(f'[DRY RUN] Would download {asset} -> {path_repr(out_path)}')
        else:
            log.debug(f'Downloading {asset}')
            data = self.client.get_asset(asset)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            log.info(f'Saving {path_repr(out_path)}')
            out_path.write_bytes(data)


if __name__ == '__main__':
    main()
