#!/usr/bin/env python

from __future__ import annotations

import json
import logging
from abc import ABC
from functools import cached_property
from getpass import getpass
from operator import itemgetter
from typing import TYPE_CHECKING, Iterator

from cli_command_parser import Command, SubCommand, Flag, Counter, Option, ParamGroup, Action, main
from cli_command_parser.inputs import Path as IPath
from cli_command_parser.exceptions import UsageError

from mm.__version__ import __author_email__, __version__  # noqa
from mm.account import PlayerAccount, WorldAccount
from mm.config import AccountConfig
from mm.enums import ItemRarityFlags, EquipmentType, ITEM_PAGE_TYPE_MAP
from mm.output import CompactJSONEncoder
from mm.session import MementoMoriSession

if TYPE_CHECKING:
    from mm.models import Equipment, ItemAndCount
    from mm.mb_models import Equipment as MBEquipment

log = logging.getLogger(__name__)


class GameCLI(Command, description='Memento Mori Game Manager', option_name_mode='*-'):
    action = SubCommand()
    verbose = Counter('-v', help='Increase logging verbosity (can specify multiple times)')
    config_file = Option(
        '-cf', type=IPath(type='file'), help='Config file path (default: ~/.config/memento-mori-client)'
    )
    http_save_dir = Option('-hsd', type=IPath(type='dir'), help='Save HTTP requests and responses to files in this dir')

    def _init_command_(self):
        from mm.logging import init_logging

        init_logging(self.verbose)

    @cached_property
    def mm_session(self) -> MementoMoriSession:
        return MementoMoriSession(self.config_file, use_auth_cache=False, http_save_dir=self.http_save_dir)


class Login(GameCLI, help='Log in for the first time'):
    user_id = Option('-i', type=int, required=True, help='Numeric user ID')
    name = Option('-n', required=True, help='Friendly name to associate with the account (locally only)')

    def main(self):
        account = AccountConfig(self.user_id, name=self.name, config_file=self.mm_session.config)
        client_key = self.mm_session.auth_client.get_client_key(
            account, password=getpass('Please enter the account password: ')
        )
        log.debug(f'Received {client_key=}')
        account.client_key = client_key


class WorldCommand(GameCLI, ABC):
    with ParamGroup('Account', required=True, mutually_exclusive=True):
        user_id = Option('-i', type=int, help='Numeric user ID')
        name = Option('-n', help='Friendly name associated with the account')
        with ParamGroup(mutually_dependent=True):
            player_login_path = Option('-PL', type=IPath(type='file', exists=True), help='Cached player login response')
            user_sync_path = Option('-US', type=IPath(type='file', exists=True), help='Cached user sync data response')

    world: int
    sort_keys = Flag('-s', help='Sort keys in dictionaries during serialization')

    # region Account Properties

    @cached_property
    def player_account(self) -> PlayerAccount:
        if self.user_id:
            return self.mm_session.get_account_by_id(self.user_id)
        elif self.name:
            return self.mm_session.get_account_by_name(self.name)
        else:
            return PlayerAccount.from_cached_login(self.player_login_path, self.mm_session)

    @cached_property
    def world_account(self) -> WorldAccount:
        if self.user_sync_path:
            return WorldAccount.from_cached_sync_data(self.user_sync_path, self.player_account)
        elif not self.world:
            raise UsageError('Missing required parameter: --world / -w')
        return self.player_account.get_world(self.world)

    # endregion

    def print(self, data):
        print(json.dumps(data, indent=4, sort_keys=self.sort_keys, ensure_ascii=False, cls=CompactJSONEncoder))


class Inventory(WorldCommand, choices=('inventory', 'inv'), help='Show inventory'):
    view = Action(help='The view to show')
    world: int = Option('-w', help='The world to log in to')
    sort_by = Option(
        '-S', nargs='+', choices=('Name', 'Rarity', 'Level', 'Slot', 'Quantity'),
        help='Sort the equipment table by the specified columns',
    )
    show_ids = Flag('-I', help='Show item and type IDs')
    include_zero = Flag('-z', help='Include items with quantity=0')
    page = Option('-p', choices=ITEM_PAGE_TYPE_MAP, help='Show only items that appear on the specified inventory page')

    # region View Actions

    @view
    def unequipped(self):
        self.print_item_rows('Unequipped Gear', self.get_equipment_rows(unequipped=True))

    @view
    def all_equipment(self):
        self.print_item_rows('All Equipment', self.get_equipment_rows(unequipped=False))

    @view
    def inventory(self):
        rows = self.get_inventory_rows()
        rows = sorted(rows, key=itemgetter(*(self.sort_by or ['Type', 'Level', 'Slot', 'Rarity', 'Name'])))
        for row in rows:
            row['Quantity'] = f'{row["Quantity"]:,d}'
            row['Rarity'] = '' if row['Rarity'] == ItemRarityFlags.NONE else row['Rarity'].name
            row['Slot'] = '' if row['Slot'] == EquipmentType.NONE else row['Slot'].name
            if row['Level'] == -1:
                row['Level'] = ''

        self.print_item_rows('Inventory', rows)

    # endregion

    # region Print Table

    def print_item_rows(self, title: str, rows):
        from rich.console import Console
        from rich.table import Table

        table = Table(*self._table_columns(), title=title)
        for row in rows:
            table.add_row(*map(str, row.values()))

        Console().print(table)

    def _table_columns(self):
        from rich.table import Column

        if self.view == 'inventory':
            if self.show_ids:
                yield Column('Type ID', justify='right')
            yield 'Type'

        if self.show_ids:
            yield Column('Item ID', justify='right')

        yield 'Name'
        yield Column('Quantity', justify='right')
        yield 'Rarity'
        yield Column('Level', justify='right')
        yield 'Slot'

    # endregion

    def _ensure_user_sync_data_is_loaded(self):
        self.mm_session.mb.populate_cache()
        if not self.user_sync_path:
            self.world_account.get_user_sync_data()

    # region Equipment

    def get_equipment_rows(self, unequipped: bool):
        gear = {}
        for item in self.iter_equipment(unequipped=unequipped):
            try:
                row = gear[item.equipment_id]
            except KeyError:
                gear[item.equipment_id] = self._get_equipment_row(item.equipment)
            else:
                row['Quantity'] += 1

        rows = sorted(gear.values(), key=itemgetter(*(self.sort_by or ['Level', 'Slot', 'Rarity', 'Name'])))
        for row in rows:
            row['Rarity'] = row['Rarity'].name
            row['Slot'] = row['Slot'].name

        return rows

    def _get_equipment_row(self, eq: MBEquipment):
        if self.show_ids:
            return {
                'Item ID': eq.item_id, 'Name': eq.name, 'Rarity': eq.rarity_flags,
                'Level': eq.level, 'Slot': eq.gear_type, 'Quantity': 1,
            }
        else:
            return {'Name': eq.name, 'Rarity': eq.rarity_flags, 'Level': eq.level, 'Slot': eq.gear_type, 'Quantity': 1}

    def iter_equipment(self, unequipped: bool) -> Iterator[Equipment]:
        self._ensure_user_sync_data_is_loaded()
        if unequipped:
            yield from self.world_account.char_guid_equipment_map.get('', ())
        else:
            yield from self.world_account.equipment.values()

    # endregion

    # region Inventory

    def get_inventory_rows(self):
        self._ensure_user_sync_data_is_loaded()

        inventory = self.world_account.inventory
        if not self.include_zero:
            inventory = (i for i in inventory if i.count != 0)
        if self.page:
            types = ITEM_PAGE_TYPE_MAP[self.page]
            inventory = (i for i in inventory if i.item_type in types)

        return [self._get_inventory_row(item_and_count) for item_and_count in inventory]

    def _get_inventory_row(self, item_and_count: ItemAndCount):
        try:
            item = item_and_count.item
        except KeyError:
            name = f'id={item_and_count.item_id}'
            level, rarity, slot = -1, ItemRarityFlags.NONE, EquipmentType.NONE
        else:
            name = getattr(item, 'display_name', item.name)
            level = getattr(item, 'level', -1)
            rarity = getattr(item, 'rarity_flags', ItemRarityFlags.NONE)
            slot = getattr(item, 'gear_type', EquipmentType.NONE)

        if self.show_ids:
            row = {
                'Type ID': item_and_count.item_type.value,
                'Type': item_and_count.item_type.name,
                'Item ID': item_and_count.item_id,
            }
        else:
            row = {'Type': item_and_count.item_type.name}

        # TODO: The count for runes and some other items is 0 for many rows - does it just indicate that the user has
        #  obtained that item at least once, but consumed it?
        return row | {
            'Name': name,
            'Quantity': item_and_count.count,
            'Rarity': rarity,
            'Level': level,
            'Slot': slot,
        }

    # endregion


class Show(WorldCommand, help='Show info'):
    item = Action(help='The item to show')

    # with ParamGroup('Account', required=True, mutually_exclusive=True):
    #     user_id = Option('-i', type=int, help='Numeric user ID')
    #     name = Option('-n', help='Friendly name associated with the account')

    world: int = Option('-w', help='The world to log in to (required for some items)')

    # region Actions

    @item
    def player_login(self):
        self.print(self.player_account.login_data)

    @item
    def world_login(self):
        self.print(self.world_account.login())

    @item
    def user_sync_data(self):
        # self.print(self.world_account.get_user_sync_data().data)
        self.print(self.world_account.get_user_data())

    @item
    def my_page(self):
        self.print(self.world_account.get_my_page())

    @item
    def characters(self):
        self.mm_session.mb.populate_cache()
        self.world_account.get_user_sync_data()
        for char in self.world_account.characters.values():
            print(f'- {char}')
            for item in char.equipment:
                print(f'    - {item}')

    # endregion


class Dailies(WorldCommand, help='Perform daily tasks'):
    world: int = Option('-w', required=True, help='The world to log in to')
    actions = Option('-a', choices=('vip_gift',), required=True, help='The actions to take')
    dry_run = Flag('-D', help='Perform a dry run by printing the actions that would be taken instead of taking them')

    def main(self):
        self.mm_session.mb.populate_cache()
        self.world_account.get_user_sync_data()
        self.world_account.get_my_page()

        if 'vip_gift' in self.actions:
            self.get_vip_gift()

    def get_vip_gift(self):
        if self.world_account.user_sync_data.has_vip_daily_gift:
            if self.dry_run:
                log.info('[DRY RUN] Would claim daily VIP gift')
            else:
                log.info('Claiming daily VIP gift')
                # TODO: Only print the items that were received
                self.print(self.world_account.get_daily_vip_gift())
        else:
            log.info('The daily VIP gift was already claimed')


if __name__ == '__main__':
    main()
