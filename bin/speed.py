#!/usr/bin/env python

from __future__ import annotations

import logging
from abc import ABC
from functools import cached_property

from cli_command_parser import Command, Positional, Counter, SubCommand, Flag, Option, main

# from mm.__version__ import __author_email__, __version__  # noqa
from mm.enums import LOCALES
from mm.http_client import DataClient
from mm.mb_models import MB
from mm.runes import PartyMember, Party, speed_tune

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

    @cached_property
    def mb(self) -> MB:
        return self.client.get_mb(use_cached=not self.no_mb_cache, locale=self.locale)

    def print_members(self, members: list[PartyMember]):
        from colored import stylize, fg

        last = 0
        for i, member in enumerate(members):
            if i:
                delta = last - member.speed
                if delta > member.after_delta:
                    color = 'green'
                elif delta > (member.after_delta * 2 / 3):
                    color = 'yellow'
                else:
                    color = 'red'

                speed = stylize(str(member.speed), fg(color))
            else:
                speed = member.speed
                delta = '-'

            print(f'{member.char.full_name}: {speed} ({delta=!s}) with levels={member.speed_rune_set.levels}')
            last = member.speed


class Allocate(SpeedCLI, help='Speed tune the specified characters using the specified rune levels'):
    characters = Positional(
        metavar='ID|NAME', nargs=range(2, 6), help='The characters to speed tune, in descending turn order'
    )
    runes = Option('-r', nargs='+', type=int, required=True, help='Speed rune levels that should be allocated')
    deltas = Option('-d', nargs=range(1, 4), type=int, help='The speed deltas to target between users, in order')

    def main(self):
        party = Party(
            [PartyMember(self.mb.get_character(char_info)) for char_info in self.characters], deltas=self.deltas
        )
        new_party = party.allocate_speed_runes(self.runes)
        self.print_members(new_party.members)


class AugmentedMembers(SpeedCLI, ABC):
    characters: list[str]

    def get_members(self):
        members = []
        for char_info in self.characters:
            try:
                name_or_id, levels = map(str.strip, char_info.split('+', 1))
            except ValueError:
                members.append(PartyMember(self.mb.get_character(char_info)))
            else:
                levels = list(map(int, map(str.strip, levels.split(','))))
                members.append(PartyMember(self.mb.get_character(name_or_id), levels))

        return members


class Order(AugmentedMembers, help='Show the order in which the specified characters with runes would attack'):
    characters = Positional(
        metavar='ID|NAME[+LEVEL[,LEVEL[,LEVEL]]]',
        nargs=range(2, 6),
        help='The characters to sort by speed',
    )

    def main(self):
        self.print_members(sorted(self.get_members(), reverse=True))


class Tune(AugmentedMembers, help='Speed tune the specified characters in the specified order'):
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
    multiplier: float = Option(
        '-m', help='Multiplier to apply to output values (use 1.1 for Primavera < level 200, 1.15 for 201 or above)'
    )

    def main(self):
        for member in speed_tune(self.get_members()):
            speed = int(member.speed * self.multiplier) if self.multiplier else member.speed
            # print(f'{member.char.full_name}: {speed} => levels={member.speed_rune_levels}')
            print(f'{member.char.full_name}: {speed} => levels={member.speed_rune_set.levels}')


if __name__ == '__main__':
    main()
