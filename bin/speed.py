#!/usr/bin/env python

from __future__ import annotations

import logging
from functools import cached_property

from cli_command_parser import Command, Positional, Counter, SubCommand, Flag, Option, UsageError, main

from mm.__version__ import __author_email__, __version__  # noqa
from mm.runes import PartyMember, speed_tune
from mm.client import DataClient
from mm.mb_models import MB, LOCALES, Character

log = logging.getLogger(__name__)


class SpeedCLI(Command, description='Memento Mori Speed Rune Calculator', option_name_mode='*-'):
    action = SubCommand()
    no_client_cache = Flag('-C', help='Do not read cached game/catalog data')
    no_mb_cache = Flag('-M', help='Do not read cached MB data')
    verbose = Counter('-v', help='Increase logging verbosity (can specify multiple times)')
    locale = Option('-L', choices=LOCALES, default='EnUs', help='Locale to use for text resources')

    def _init_command_(self):
        from mm.logging import init_logging

        init_logging(self.verbose)

    @cached_property
    def client(self) -> DataClient:
        return DataClient(use_cache=not self.no_client_cache)

    def get_mb(self) -> MB:
        return self.client.get_mb(use_cached=not self.no_mb_cache, locale=self.locale)

    @cached_property
    def all_characters(self) -> dict[int, Character]:
        return self.get_mb().characters


class Tune(SpeedCLI, help='Speed tune the specified characters in the specified order'):
    """
    Speed tune the specified characters in the specified order.

    To use base stats for the calculation, simply provide character names or ids, separated by spaces.

    To provide existing rune levels for a given character, specify the name or id plus a comma-separated list of levels.
    For example:
        merlyn cordie+7,7,7 florence
        merlyn florence+5,5
    """

    characters = Positional(
        metavar='ID|NAME[+LEVEL[,LEVEL[,LEVEL]]]',
        nargs=range(2, 6),
        help='The characters to speed tune, in descending turn order',
    )

    @cached_property
    def _char_map(self) -> dict[str, Character]:
        char_map = {}
        for num, char in self.all_characters.items():
            char_map[str(num)] = char
            char_map[char.full_id.upper()] = char
            char_map[char.full_name.upper()] = char
        return char_map

    def get_character(self, id_or_name: str) -> Character:
        try:
            return self._char_map[id_or_name.upper()]
        except KeyError as e:
            raise UsageError(
                f'Unknown character name={id_or_name!r} - use `mb.py show character names`'
                ' to find the correct ID to use here'
            ) from e

    def main(self):
        for member in speed_tune(self.get_members()):
            print(f'{member.char.full_name}: {member.speed} => levels={member.speed_rune_levels}')

    def get_members(self):
        members = []
        for char_info in self.characters:
            try:
                name_or_id, levels = map(str.strip, char_info.split('+', 1))
            except ValueError:
                members.append(PartyMember(self.get_character(char_info)))
            else:
                levels = list(map(int, map(str.strip, levels.split(','))))
                members.append(PartyMember(self.get_character(name_or_id), levels))

        return members


if __name__ == '__main__':
    main()
