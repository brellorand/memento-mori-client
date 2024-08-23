#!/usr/bin/env python

import logging
from functools import cached_property
from typing import Iterator

from cli_command_parser import Command, Counter, Flag, Option, SubCommand, main
from cli_command_parser.inputs import Path as IPath

from mm.__version__ import __author_email__, __version__  # noqa
from mm.enums import LOCALES
from mm.mb_models import Equipment as _Equipment
from mm.output import OUTPUT_FORMATS, YAML, pprint
from mm.session import MementoMoriSession

log = logging.getLogger(__name__)


class GearCLI(Command, description='Memento Mori Gear Helper', option_name_mode='*-'):
    action = SubCommand()
    no_client_cache = Flag('-C', help='Do not read cached game/catalog data')
    no_mb_cache = Flag('-M', help='Do not read cached MB data')
    config_file = Option(
        '-cf', type=IPath(type='file'), help='Config file path (default: ~/.config/memento-mori-client)'
    )
    locale = Option('-loc', choices=LOCALES, default='EnUs', help='Locale to use for text resources')
    verbose = Counter('-v', help='Increase logging verbosity (can specify multiple times)')

    def _init_command_(self):
        from mm.logging import init_logging

        init_logging(self.verbose)

    @cached_property
    def mm_session(self) -> MementoMoriSession:
        return MementoMoriSession(
            self.config_file,
            use_auth_cache=not self.no_client_cache,
            use_data_cache=not self.no_client_cache,
            use_mb_cache=not self.no_mb_cache,
            mb_locale=self.locale,
        )


# region List Commands


class List(GearCLI, help='List the specified items'):
    item = SubCommand()
    format = Option(
        '-f', choices=OUTPUT_FORMATS, default_cb=lambda c: c._format_default(), cb_with_cmd=True, help='Output format'
    )

    @classmethod
    def _format_default(cls) -> str:
        return 'json-pretty' if YAML is None else 'yaml'

    def pprint(self, data):
        if data:
            pprint(self.format, data)
        else:
            print('No results')


class UpgradeReqs(List, help='List all upgrade requirements'):
    type = Option('-t', choices=('weapon', 'armor'), required=True, help='The type of gear to be upgraded')

    @classmethod
    def _format_default(cls) -> str:
        return 'csv'

    def main(self):
        data = self.get_csv_data() if self.format == 'csv' else self.get_data()
        self.pprint(data)

    def _get_requirements(self):
        mb = self.mm_session.mb
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
            f'Level {lv}': [str(ic) for ic in req_ics]
            for lv, req_ics in self._get_requirements().level_required_items_map.items()
        }


class Items(List, help='List all items'):
    def main(self):
        self.pprint(self.get_data())

    def get_data(self):
        return [
            {
                'name': getattr(item, 'name', '?'),
                'display_name': getattr(item, 'display_name', '?'),
                'description': getattr(item, 'description', '?'),
                'type': item.item_type,
                'id': item.id,
            }
            for type_item_map in self.mm_session.mb.items.values()
            for item in type_item_map.values()
        ]


class Equipment(List, help='List all equipment'):
    # full = Flag('-F', help='Output full equipment info (default: only IDs and names)')
    min_level: int = Option('-min', help='Filter to gear at or above the specified level')
    max_level: int = Option('-max', help='Filter to gear at or below the specified level')

    def main(self):
        self.pprint(self.get_data())

    def _iter_items(self) -> Iterator[_Equipment]:
        items = self.mm_session.mb.equipment.values()
        if min_level := self.min_level:
            items = (i for i in items if i.level >= min_level)
        if max_level := self.max_level:
            items = (i for i in items if i.level <= max_level)
        yield from items

    def get_data(self):
        return [
            {
                'name': item.name,
                'id': item.id,
                'level': item.level,
                'rarity': item.rarity_flags,
                'quality': item.quality_level,
                'enhance_reqs': (
                    list(map(str, item.enhance_requirements.required_items)) if item.enhance_requirements else []
                ),
            }
            for item in self._iter_items()
        ]


# endregion


if __name__ == '__main__':
    main()
