#!/usr/bin/env python

import json
import logging
from functools import cached_property
from pathlib import Path

from cli_command_parser import Command, Positional, SubCommand, Flag, Counter, Option, ParamGroup, main
from cli_command_parser.inputs import Path as IPath

from mm.__version__ import __author_email__, __version__  # noqa
from mm.client import DataClient
from mm.fs import path_repr

log = logging.getLogger(__name__)

DIR = IPath(type='dir')


class CatalogCLI(Command, description='Memento Mori Catalog Manager', option_name_mode='*-'):
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


class Show(CatalogCLI, help='Show info'):
    item = Positional(choices=('game_data',), help='The item to show')
    sort_keys = Flag('-s', help='Sort keys in dictionaries during serialization')

    def main(self):
        if self.item == 'game_data':
            self.print(self.client.game_data.data)

    def print(self, data):
        from mm.utils import PermissiveJSONEncoder

        print(json.dumps(data, indent=4, sort_keys=self.sort_keys, ensure_ascii=False, cls=PermissiveJSONEncoder))


class Metadata(CatalogCLI, choices=('metadata', 'meta'), help='Save catalog metadata to a file'):
    catalog = Positional(choices=('master', 'assets'), help='The type of catalog to save')
    output: Path = Option('-o', type=DIR, help='Output directory', required=True)
    split = Flag('-s', help='Split the specified catalog into separate files for each top-level key')

    def main(self):
        catalog = self.client.asset_catalog.data if self.catalog == 'assets' else self.client.master_catalog
        name = f'{self.catalog}-catalog'
        if self.split:
            for key, val in catalog.items():
                self._save(val, name, f'{key}.json')
        else:
            self._save(catalog, f'{name}.json')

    def _save(self, data, *name):
        path = self.output.joinpath(*name)
        path.parent.mkdir(parents=True, exist_ok=True)
        log.info(f'Saving {path_repr(path)}')
        with path.open('w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)


class Assets(CatalogCLI, help='Show asset paths'):
    path = Option('-p', help='Show assets relative to the specified path')
    depth: int = Option('-d', help='Show assets up to the specified depth')

    def main(self):
        tree = self.client.asset_catalog.asset_tree
        if self.path:
            try:
                tree = tree[self.path]
            except KeyError as e:
                raise KeyError(f'Invalid asset path: {self.path!r}') from e

        for asset in tree.iter_flat(self.depth):
            print(asset)


if __name__ == '__main__':
    main()
