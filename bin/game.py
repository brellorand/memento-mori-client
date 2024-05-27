#!/usr/bin/env python

import json
import logging
from abc import ABC
from functools import cached_property
from getpass import getpass

from cli_command_parser import Command, SubCommand, Flag, Counter, Option, ParamGroup, Action, after_main, main
from cli_command_parser.inputs import Path as IPath
from cli_command_parser.exceptions import UsageError

from mm.__version__ import __author_email__, __version__  # noqa
from mm.account import PlayerAccount, WorldAccount
from mm.session import MementoMoriSession
from mm.config import AccountConfig
from mm.output import CompactJSONEncoder

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

    world: int
    sort_keys = Flag('-s', help='Sort keys in dictionaries during serialization')

    # region Account Properties

    @cached_property
    def player_account(self) -> PlayerAccount:
        if self.user_id:
            return self.mm_session.get_account_by_id(self.user_id)
        else:
            return self.mm_session.get_account_by_name(self.name)

    @cached_property
    def world_account(self) -> WorldAccount:
        if not self.world:
            raise UsageError('Missing required parameter: --world / -w')
        return self.player_account.get_world(self.world)

    # endregion

    def print(self, data):
        print(json.dumps(data, indent=4, sort_keys=self.sort_keys, ensure_ascii=False, cls=CompactJSONEncoder))


class Show(WorldCommand, help='Show info'):
    item = Action(help='The item to show')

    # with ParamGroup('Account', required=True, mutually_exclusive=True):
    #     user_id = Option('-i', type=int, help='Numeric user ID')
    #     name = Option('-n', help='Friendly name associated with the account')

    world: int = Option('-w', help='The world to log in to (required for some items)')
    # sort_keys = Flag('-s', help='Sort keys in dictionaries during serialization')

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
    world: int = Option('-w', required=True, help='The world to log in to (required for some items)')
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
                self.print(self.world_account.get_daily_vip_gift())
        else:
            log.info('The daily VIP gift was already claimed')


if __name__ == '__main__':
    main()
