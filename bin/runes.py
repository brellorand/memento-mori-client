#!/usr/bin/env python

from cli_command_parser import Command, Positional, Counter, Action, main

from mm.__version__ import __author_email__, __version__  # noqa
from mm.runes import Rune, RuneSet


class RunesCLI(Command, description='Memento Mori Rune Calculator', option_name_mode='*-'):
    action = Action()
    stat = Positional(choices=Rune.stat_cls_map, help='The stat for which calculations should be performed')
    levels = Positional(type=range(1, 16), nargs=range(1, 4), help='One to three rune levels')
    verbose = Counter('-v', help='Increase logging verbosity (can specify multiple times)')

    def _init_command_(self):
        from mm.logging import init_logging

        init_logging(self.verbose)

    @property
    def rune_set(self) -> RuneSet:
        return Rune.get_rune_class(self.stat).get_rune_set(*self.levels)

    @action(help='Print the total stat value for the specified rune levels')
    def total(self):
        rune_set = self.rune_set
        print(f'Total {rune_set.type.stat}: {rune_set.total}')

    @action(help='Print the total ticket cost(s) for the specified rune levels')
    def cost(self):
        total = 0
        for rune in self.rune_set:
            total += rune.ticket_cost
            print(f'{rune}: tickets={rune.ticket_cost}')

        print(f'\nTotal ticket cost: {total}')


if __name__ == '__main__':
    main()
