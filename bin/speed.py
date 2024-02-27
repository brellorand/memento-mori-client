#!/usr/bin/env python

from __future__ import annotations

import logging
from functools import cached_property

from cli_command_parser import Command, Positional, Counter, SubCommand, Flag, Option, main

from mm.__version__ import __author_email__, __version__  # noqa
from mm.runes import SpeedRune, RuneCalculator
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
    characters = Positional(
        metavar='ID|NAME', nargs=range(2, 6), help='The characters to speed tune, in descending turn order'
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
            raise ValueError(
                f'Unknown character name={id_or_name!r} - use `mb.py show character names`'
                ' to find the correct ID to use here'
            ) from e

    def main(self):
        # TODO: Add way to specify current/base runes or a speed override for the fastest/specific member(s)
        for member in fix_speeds([PartyMember(self.get_character(c)) for c in self.characters]):
            print(f'{member.char.full_name}: {member.speed} => levels={member.levels}')


class PartyMember:
    def __init__(self, char: Character, levels: list[int] = None):
        self.char = char
        self.levels = levels or [0, 0, 0]

    @property
    def speed(self) -> int:
        return self.char.speed + SpeedRune.get_rune_set(*self.levels).total


def fix_speeds(members: list[PartyMember]):
    calculator = RuneCalculator(SpeedRune)
    min_speed = members[-1].speed + 150
    for member in members[-2::-1]:  # reverse order, starting from the 2nd to last element
        if member.speed < min_speed:
            log.debug(f'Updating runes for {member.char} because speed={member.speed} < {min_speed=}')
            # Rune levels need to calculate from base delta to take current runes into account
            rune_set = calculator.find_closest_min_ticket_set(min_speed - member.char.speed)
            member.levels = sorted(rune_set.levels, reverse=True)

        min_speed = member.speed + 150

    return members


if __name__ == '__main__':
    main()
