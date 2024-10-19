#!/usr/bin/env python

from __future__ import annotations

import json
import logging
from abc import ABC
from functools import cached_property
from operator import itemgetter
from typing import TYPE_CHECKING, Iterable, Iterator

from cli_command_parser import Action, Command, Counter, Flag, Option, ParamGroup, SubCommand, main
from cli_command_parser.exceptions import ParamUsageError, UsageError
from cli_command_parser.inputs import ChoiceMap, NumRange, Path as IPath

from mm import enums
from mm.__version__ import __author_email__, __version__  # noqa
from mm.enums import (
    ITEM_PAGE_TYPE_MAP,
    BaseParameterType,
    EquipmentRarityFlags,
    EquipmentSlotType,
    EquipmentType,
    ItemRarityFlags,
    SmeltEquipmentRarity,
)
from mm.fs import get_user_cache_dir
from mm.game import DailyTask, PlayerAccount, TaskConfig, TaskRunner, WorldSession
from mm.output import CompactJSONEncoder
from mm.session import MementoMoriSession

if TYPE_CHECKING:
    from mm.game.models import Equipment, ItemAndCount
    from mm.mb_models import Equipment as MBEquipment

log = logging.getLogger(__name__)


class GameCLI(Command, description='Memento Mori Game Manager', option_name_mode='*-'):
    action = SubCommand()
    verbose = Counter('-v', help='Increase logging verbosity (can specify multiple times)')
    config_file = Option(
        '-cf', type=IPath(type='file'), help='Config file path (default: in ~/.config/memento-mori-client/)'
    )
    http_save_dir = Option('-hsd', type=IPath(type='dir'), help='Save HTTP requests and responses to files in this dir')

    def _init_command_(self):
        from mm.logging import init_logging

        init_logging(self.verbose, file_name=f'game_{self.action}.log')

    @cached_property
    def mm_session(self) -> MementoMoriSession:
        mm_session = MementoMoriSession(self.config_file, use_auth_cache=False, http_save_dir=self.http_save_dir)
        mm_session.__enter__()
        return mm_session


class ListAccounts(GameCLI, help='List account names/ids that have been configured for use'):
    def main(self):
        for account in self.mm_session.config.accounts.values():
            print(f' - {account.name}: {account.user_id}')


class Login(GameCLI, help='Log in for the first time'):
    user_id = Option('-i', type=int, required=True, help='Numeric user ID')
    name = Option('-n', required=True, help='Friendly name to associate with the account (locally only)')

    def main(self):
        account = self.mm_session.get_new_account(self.user_id, self.name)
        account.generate_client_key()
        log.info('Successfully generated a new client key')


class WorldCommand(GameCLI, ABC):
    with ParamGroup('Account', required=True, mutually_exclusive=True):
        user_id = Option('-i', type=int, help='Numeric user ID')
        name = Option('-n', help='Friendly name associated with the account')
        with ParamGroup(mutually_dependent=True):
            player_login_path = Option('-PL', type=IPath(type='file', exists=True), help='Cached player login response')
            user_sync_path = Option('-US', type=IPath(type='file', exists=True), help='Cached user sync data response')

    world: int
    sort_keys = Flag(help='Sort keys in dictionaries during serialization')

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
    def world_session(self) -> WorldSession:
        if self.user_sync_path:
            return WorldSession.from_cached_sync_data(self.user_sync_path, self.player_account)
        elif not self.world:
            raise UsageError('Missing required parameter: --world / -w')
        return self.player_account.get_world(self.world)

    # endregion

    def print(self, data):
        print(json.dumps(data, indent=4, sort_keys=self.sort_keys, ensure_ascii=False, cls=CompactJSONEncoder))


class Inventory(WorldCommand, choices=('inventory', 'inv'), help='Show inventory'):
    _sort_choices = ('Name', 'Rarity', 'Level', 'Slot', 'Quantity')

    view = Action(help='The view to show')
    world: int = Option('-w', help='The world to log in to')
    sort_by = Option('-S', nargs='+', choices=_sort_choices, help='Sort the equipment table by the specified columns')
    show_ids = Flag('-I', help='Show item and type IDs')
    include_zero = Flag('-z', help='Include items with quantity=0')
    page = Option('-p', choices=ITEM_PAGE_TYPE_MAP, help='Show only items that appear on the specified inventory page')

    # region View Actions

    @view
    def unequipped(self):
        self.print_item_rows('Unequipped Gear', self.get_equipment_rows(equipped=False))

    @view
    def equipped(self):
        self.print_item_rows('Equipped Gear', self.get_equipment_rows(equipped=True))

    @view
    def equipped_by_char(self):
        self._ensure_user_sync_data_is_loaded()
        for char_guid, equipment in self.world_session.char_guid_equipment_map.items():
            if not char_guid:
                continue

            if char := self.world_session.characters.get(char_guid):
                char_repr = repr(char)
            else:
                char_repr = char_guid

            self.print_item_rows(f'Gear Equipped By: {char_repr}', self._get_equipment_rows(equipment))

    @view
    def all_equipment(self):
        self.print_item_rows('All Equipment', self.get_equipment_rows())

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

        columns = list(self._table_columns())
        table = Table(*columns, title=title)
        for row in rows:
            table.add_row(*(str(row.get(col if isinstance(col, str) else col.header, '')) for col in columns))

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
            self.world_session.get_user_sync_data()

    # region Equipment

    def get_equipment_rows(self, equipped: bool | None = None):
        return self._get_equipment_rows(self.iter_equipment(equipped=equipped))

    def _get_equipment_rows(self, equipment: Iterable[Equipment]):
        gear = {}
        for item in equipment:
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
                'Item ID': eq.item_id,
                'Name': eq.name,
                'Rarity': eq.rarity_flags,
                'Level': eq.level,
                'Slot': eq.gear_type,
                'Quantity': 1,
            }
        else:
            return {'Name': eq.name, 'Rarity': eq.rarity_flags, 'Level': eq.level, 'Slot': eq.gear_type, 'Quantity': 1}

    def iter_equipment(self, equipped: bool | None) -> Iterator[Equipment]:
        self._ensure_user_sync_data_is_loaded()
        if equipped:
            for char_guid, equipment in self.world_session.char_guid_equipment_map.items():
                if char_guid:
                    yield from equipment
        elif equipped is None:
            yield from self.world_session.equipment.values()
        else:  # Equipped is False
            yield from self.world_session.char_guid_equipment_map.get('', ())

    # endregion

    # region Inventory

    def get_inventory_rows(self):
        self._ensure_user_sync_data_is_loaded()

        inventory = self.world_session.inventory
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


# region Tasks


class TaskCommand(WorldCommand, ABC):
    world: int = Option('-w', help='The world to log in to')
    dry_run = Flag('-D', help='Perform a dry run by printing the actions that would be taken instead of taking them')
    min_wait: float
    max_wait: float

    @cached_property
    def task_config(self) -> TaskConfig:
        return TaskConfig(
            dry_run=self.dry_run,
            min_wait_ms=int(self.min_wait * 1000),
            max_wait_ms=int(self.max_wait * 1000),
        )

    @cached_property
    def task_runner(self) -> TaskRunner:
        return TaskRunner(self.world_session, config=self.task_config)

    def _init_command_(self):
        from mm.logging import init_logging

        init_logging(self.verbose, entry_fmt='%(asctime)s %(message)s', file_name=f'game_{self.action}.log')


class Smelt(TaskCommand, help='Smelt equipment'):
    min_level: int = Option(type=NumRange(min=1), default=1, help='Minimum level of S equipment to smelt')
    max_level: int = Option(type=NumRange(min=1), help='Maximum level of S equipment to smelt')
    min_rarity: SmeltEquipmentRarity = Option(
        default=SmeltEquipmentRarity.D, help='Minimum rarity of equipment to smelt'
    )
    max_rarity: SmeltEquipmentRarity = Option(
        default=SmeltEquipmentRarity.S_PLUS, help='Maximum rarity of equipment to smelt'
    )
    keep: int = Option(
        '-k', default=0, help='Keep the specified number of each piece of the specified max rarity equipment'
    )

    min_wait: float = Option(type=NumRange(min=0.3), default=0.4, help='Minimum wait between smelt requests')
    max_wait: float = Option(type=NumRange(min=0.4), default=0.9, help='Maximum wait between smelt requests')

    def main(self):
        if self.min_level and self.max_level and self.min_level > self.max_level:
            raise UsageError('Invalid min/max levels - the min level must be less than the max level')

        self.mm_session.mb.populate_cache()
        self.world_session.get_user_sync_data()
        self.world_session.get_my_page()

        self.task_runner.add_tasks(self.iter_smelt_tasks())
        self.task_runner.run_tasks()

    def iter_smelt_tasks(self):
        from mm.game.tasks import SmeltAll, SmeltNeverEquippedSGear, SmeltUnequippedGear

        min_rarity, max_rarity = self.min_rarity.as_flag(), self.max_rarity.as_flag()
        if max_rarity == EquipmentRarityFlags.S and min_rarity != EquipmentRarityFlags.S:
            rarity_range = EquipmentRarityFlags.range(min_rarity, EquipmentRarityFlags.A)
        else:
            rarity_range = EquipmentRarityFlags.range(min_rarity, max_rarity)

        yield SmeltAll(self.world_session, self.task_config, rarity=rarity_range)
        yield SmeltNeverEquippedSGear(
            self.world_session, self.task_config, min_level=self.min_level, max_level=self.max_level, keep=self.keep
        )
        yield SmeltUnequippedGear(
            self.world_session, self.task_config, min_level=self.min_level, max_level=self.max_level
        )


class Reforge(TaskCommand, help='Reforge equipment'):
    character = Option(
        '-c', metavar='ID|NAME', nargs='+', required=True, help='The character(s) whose gear should be reforged'
    )
    stat = Option('-s', type=BaseParameterType, required=True, help='The stat to target while reforging')
    with ParamGroup('Target', required=True):
        target_value = Option('-t', type=NumRange(min=1), help='Target reforged value for the specified stat')
        target_pct = Option(
            '-p',
            type=NumRange(min=0.01, max=0.6),
            help='Target reforged value as a percentage of the total available points for the specified stat',
        )

    slots = Option(type=EquipmentSlotType, nargs='+', help='The equipment slots to reforge (default: all)')

    min_wait: float = Option(type=NumRange(min=0.3), default=0.35, help='Minimum wait between reforge requests')
    max_wait: float = Option(type=NumRange(min=0.4), default=0.65, help='Maximum wait between reforge requests')

    def main(self):
        from mm.game.tasks.reforge import ReforgeGear

        self.mm_session.mb.populate_cache()
        self.world_session.get_user_sync_data()
        self.world_session.get_my_page()

        for char in self.character:
            task = ReforgeGear(
                self.world_session,
                self.task_config,
                character=char,
                stat=self.stat,
                slots=self.slots,
                target_value=self.target_value,
                target_pct=self.target_pct,
            )
            self.task_runner.add_task(task)

        self.task_runner.run_tasks()


class BattleTaskCommand(TaskCommand, ABC):
    with ParamGroup('Delay'):
        min_wait: float = Option(type=NumRange(min=0.3), default=0.65, help='Minimum wait between battle attempts')
        max_wait: float = Option(type=NumRange(min=0.4), default=1.0, help='Maximum wait between battle attempts')

    with ParamGroup('Battle results', mutually_exclusive=True):
        battle_results_dir = Option('-brd', type=IPath(type='dir'), help='Save battle results to files in this dir')
        no_save = Flag(
            '-S', help='Do NOT save battle results (default: save to a temp directory if an alt dir is not specified)'
        )

    def _get_results_dir(self, result_type: str):
        if self.no_save:
            return None
        elif self.battle_results_dir:
            return self.battle_results_dir
        else:
            return get_user_cache_dir(f'{result_type}_results')


class Quest(BattleTaskCommand, help='Challenge the main quest'):
    with ParamGroup('Quest', mutually_exclusive=True):
        max_quest = Option(metavar='CHAPTER-NUM', help='The maximum quest to challenge (inclusive) (e.g., 12-5)')
        stop_after: int = Option(type=NumRange(min=1), help='Stop after the specified number of wins')

    def main(self):
        max_quest = self._get_max_quest()
        self._run_task(max_quest)

    def _get_max_quest(self) -> tuple[int, int] | None:
        if not self.max_quest:
            return None

        try:
            chapter, num = self.max_quest.split('-')
            return (int(chapter), int(num))
        except Exception as e:
            raise ParamUsageError(
                self.__class__.max_quest, 'invalid value - expected a quest number in the form of "chapter-num"'
            ) from e

    def _run_task(self, max_quest: tuple[int, int] | None):
        from mm.game.tasks.battle import QuestBattles

        self.mm_session.mb.populate_cache()
        self.world_session.get_user_sync_data()
        self.world_session.get_my_page()

        task = QuestBattles(
            self.world_session,
            self.task_config,
            max_quest=max_quest,
            stop_after=self.stop_after,
            battle_results_dir=self._get_results_dir('quest'),
        )
        self.task_runner.add_task(task)
        self.task_runner.run_tasks()


class Tower(BattleTaskCommand, help='Challenge the Tower of Infinity (or a mono-soul tower)'):
    _types = enums.TowerType.get_choice_map()

    with ParamGroup('Tower'):
        tower_type = Option(
            '-t', type=ChoiceMap(_types), default=enums.TowerType.Infinite, help='Which tower to challenge'
        )
        max_floor: int = Option(type=NumRange(min=1), help='The maximum floor to challenge (inclusive)')

    def main(self):
        from mm.game.tasks.battle import ClimbTower

        self.mm_session.mb.populate_cache()
        self.world_session.get_user_sync_data()
        self.world_session.get_my_page()

        task = ClimbTower(
            self.world_session,
            self.task_config,
            tower_type=self.tower_type,
            max_floor=(self.max_floor + 1) if self.max_floor else None,
            battle_results_dir=self._get_results_dir('tower'),
        )
        self.task_runner.add_task(task)
        self.task_runner.run_tasks()


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
        self.print(self.world_session.login())

    @item
    def user_sync_data(self):
        # self.print(self.world_session.get_user_sync_data().data)
        self.print(self.world_session.get_user_data())

    @item
    def my_page(self):
        self.print(self.world_session.get_my_page())

    @item
    def characters(self):
        self.mm_session.mb.populate_cache()
        self.world_session.get_user_sync_data()
        for char in self.world_session.characters.values():
            print(f'- {char}')
            for item in char.equipment:
                print(f'    - {item}')

    @item
    def quest_map(self):
        self.world_session.get_my_page()
        self.print(self.world_session.get_quest_map_info(True))

    # @item
    # def boss_reward_info(self):
    #     self.world_session.get_my_page()
    #     self.world_session.get_quest_map_info(True)
    #     self.print(self.world_session.get_boss_reward_info())

    # endregion


class BattleLeague(WorldCommand, choices=('battle_league', 'BL'), help='Show PvP info'):
    with ParamGroup(mutually_exclusive=True, required=True):
        history = Flag('-H', help='Show Battle League history')
        details = Option('-d', metavar='BATTLE_TOKEN', help='Show details of the BL battle with the specified token')

    world: int = Option('-w', required=True, help='The world to log in to')

    def main(self):
        if self.history:
            self.show_history()
        elif self.details:
            self.show_battle(self.details)

    def show_history(self):
        self.world_session.get_my_page()
        self.world_session.get_pvp_info()
        self.print(self.world_session.get_pvp_battle_logs())

    def show_battle(self, battle_token: str):
        self.world_session.get_my_page()
        self.world_session.get_pvp_info()
        self.world_session.get_pvp_battle_logs()
        self.print(self.world_session.get_pvp_battle_details(battle_token))


class Dailies(WorldCommand, help='Perform daily tasks'):
    world: int = Option('-w', required=True, help='The world to log in to')
    actions = Option('-a', choices=DailyTask.get_cli_name_map(), help='The actions to take')
    dry_run = Flag('-D', help='Perform a dry run by printing the actions that would be taken instead of taking them')

    def main(self):
        self.mm_session.mb.populate_cache()
        self.world_session.get_user_sync_data()
        self.world_session.get_my_page()

        config = TaskConfig(
            dry_run=self.dry_run,
            # min_wait_ms=int(self.min_wait * 1000),
            # max_wait_ms=int(self.max_wait * 1000),
        )

        task_runner = TaskRunner(self.world_session, config=config)
        if self.actions:
            cli_name_map = DailyTask.get_cli_name_map()
            task_runner.add_tasks(cli_name_map[name] for name in self.actions)
        else:
            task_runner.add_tasks(DailyTask.get_all())

        task_runner.run_tasks()


if __name__ == '__main__':
    main()
