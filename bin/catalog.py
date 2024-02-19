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


class CatalogCLI(Command, description='File Backup Tool', option_name_mode='*-'):
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


class Metadata(CatalogCLI, choices=('metadata', 'meta'), help='Save catalog metadata to a file'):
    catalog = Positional(choices=('master', 'assets'), help='The type of catalog to save')
    output: Path = Option('-o', type=DIR, help='Output directory', required=True)
    split = Flag('-s', help='Split the specified catalog into separate files for each top-level key')

    def main(self):
        catalog = self.client.asset_catalog if self.catalog == 'assets' else self.client.master_catalog
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


if __name__ == '__main__':
    main()
