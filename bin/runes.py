#!/usr/bin/env python

from abc import ABC

from cli_command_parser import Command, Positional, Counter, Action, SubCommand, main

from mm.__version__ import __author_email__, __version__  # noqa
from mm.runes import Rune, RuneSet, RuneCalculator


class RunesCLI(Command, description='Memento Mori Rune Calculator', option_name_mode='*-'):
    action = SubCommand()
    stat = Positional(choices=Rune.stat_cls_map, help='The stat for which calculations should be performed')
    verbose = Counter('-v', help='Increase logging verbosity (can specify multiple times)')

    def _init_command_(self):
        from mm.logging import init_logging

        init_logging(self.verbose)


class LevelsCommand(RunesCLI, ABC):
    levels = Positional(type=range(1, 16), nargs=range(1, 4), help='One to three rune levels')

    @property
    def rune_set(self) -> RuneSet:
        return Rune.get_rune_class(self.stat).get_rune_set(*self.levels)


class Total(LevelsCommand, help='Print the total stat value for the specified rune levels'):
    def main(self):
        rune_set = self.rune_set
        print(f'Total {rune_set.type.stat}: {rune_set.total}')


class Cost(LevelsCommand, help='Print the total ticket cost(s) for the specified rune levels'):
    def main(self):
        total = 0
        for rune in self.rune_set:
            total += rune.ticket_cost
            print(f'{rune}: tickets={rune.ticket_cost}')

        print(f'\nTotal ticket cost: {total}')


class Levels(RunesCLI, help='Calculate rune levels to produce the specified stat value'):
    value: int = Positional(help='The total stat value for which rune levels should be calculated')

    def main(self):
        rune_set = RuneCalculator(Rune.get_rune_class(self.stat)).find_closest_min_ticket_set(self.value)
        print(', '.join(map(str, rune_set.levels)))


if __name__ == '__main__':
    main()
