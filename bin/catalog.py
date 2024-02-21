#!/usr/bin/env python

import json
import logging
from functools import cached_property
from pathlib import Path

from cli_command_parser import Command, Positional, SubCommand, Flag, Counter, Option, main
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
        from mm.logging import init_logging

        init_logging(self.verbose)

    @cached_property
    def client(self) -> DataClient:
        return DataClient(use_cache=not self.no_cache)


class Show(CatalogCLI, help='Show info'):
    item = Positional(choices=('game_data', 'uri_formats'), help='The item to show')
    sort_keys = Flag('-s', help='Sort keys in dictionaries during serialization')

    def main(self):
        if self.item == 'game_data':
            self.print(self.client.game_data.data)
        elif self.item == 'uri_formats':
            self.print(self.client.game_data.uri_formats)

    def print(self, data):
        from mm.utils import PermissiveJSONEncoder

        print(json.dumps(data, indent=4, sort_keys=self.sort_keys, ensure_ascii=False, cls=PermissiveJSONEncoder))


class Save(CatalogCLI, help='Save catalog metadata to a file'):
    item = Positional(choices=('master', 'assets', 'asset_data'), help='The type of catalog/item to save')
    output: Path = Option('-o', type=DIR, help='Output directory', required=True)
    split = Flag('-s', help='Split the specified catalog into separate files for each top-level key')

    def main(self):
        for name_parts, data, raw in self.iter_names_and_data():
            self._save(data, *name_parts, raw=raw)

    def iter_names_and_data(self):
        if self.item in ('assets', 'master'):
            name = f'{self.item}-catalog'
            data = self.client.asset_catalog.data if self.item == 'assets' else self.client.master_catalog
            if self.split:
                for key, val in data.items():
                    yield (name, f'{key}.json'), val, False
            else:
                yield (f'{name}.json',), data, False
        elif self.item == 'asset_data':
            asset_catalog = self.client.asset_catalog
            for attr in ('key_data', 'bucket_data', 'entry_data', 'extra_data'):
                yield (f'{attr}.dat',), getattr(asset_catalog, attr), True

    def _save(self, data, *name, raw: bool = False):
        path = self.output.joinpath(*name)
        path.parent.mkdir(parents=True, exist_ok=True)
        log.info(f'Saving {path_repr(path)}')
        if raw:
            path.write_bytes(data)
        else:
            with path.open('w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)


if __name__ == '__main__':
    main()
