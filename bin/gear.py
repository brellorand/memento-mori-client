#!/usr/bin/env python

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import cached_property
from pathlib import Path

from cli_command_parser import Command, Positional, SubCommand, Flag, Counter, Option, Action, main
from cli_command_parser.inputs import Path as IPath, NumRange

from mm.__version__ import __author_email__, __version__  # noqa
from mm.enums import Region, LOCALES
from mm.fs import path_repr
from mm.http_client import DataClient
from mm.mb_models import MB, RANK_BONUS_STATS, WorldGroup
from mm.output import OUTPUT_FORMATS, YAML, pprint
from mm.utils import FutureWaiter

log = logging.getLogger(__name__)

DIR = IPath(type='dir')
IN_FILE = IPath(type='file', exists=True)


class GearCLI(Command, description='Memento Mori Gear Helper', option_name_mode='*-'):
    action = SubCommand()
    no_client_cache = Flag('-C', help='Do not read cached game/catalog data')
    no_mb_cache = Flag('-M', help='Do not read cached MB data')
    verbose = Counter('-v', help='Increase logging verbosity (can specify multiple times)')
    locale = Option('-loc', choices=LOCALES, default='EnUs', help='Locale to use for text resources')

    def _init_command_(self):
        from mm.logging import init_logging

        init_logging(self.verbose)

    @cached_property
    def client(self) -> DataClient:
        return DataClient(use_cache=not self.no_client_cache)

    def get_mb(self, json_cache_map=None) -> MB:
        return self.client.get_mb(use_cached=not self.no_mb_cache, json_cache_map=json_cache_map, locale=self.locale)


class UpgradeReqs(GearCLI, help='Calculate gear upgrade requirements'):
    action = SubCommand()


class List(UpgradeReqs, help='List all upgrade requirements'):
    type = Option('-t', choices=('weapon', 'armor'), required=True, help='The type of gear to be upgraded')
    format = Option('-f', choices=OUTPUT_FORMATS, default='csv', help='Output format')

    def main(self):
        data = self.get_csv_data() if self.format == 'csv' else self.get_data()
        self.pprint(data)

    def _get_requirements(self):
        mb = self.get_mb()
        return mb.armor_upgrade_requirements if self.type == 'armor' else mb.weapon_upgrade_requirements

    def get_csv_data(self):
        rows = []
        for lv, req_ics in self._get_requirements().level_required_items_map.items():
            row = {'Level': lv, 'Gold': 0, 'Upgrade Water': 0, 'Upgrade Panacea': 0}
            for ic in req_ics:
                row[ic.item.display_name] = ic.count

            rows.append(row)

        return rows

    def get_data(self):
        return {
            f'Level {lv}': {f'{ic.item.display_name} x {ic.count:,d}' for ic in req_ics}
            for lv, req_ics in self._get_requirements().level_required_items_map.items()
        }

    def pprint(self, data):
        if data:
            pprint(self.format, data)
        else:
            print('No results')


if __name__ == '__main__':
    main()
