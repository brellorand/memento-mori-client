#!/usr/bin/env python

from __future__ import annotations

import json
import logging

from cli_command_parser import Command, Counter, Option, SubCommand, main
from cli_command_parser.exceptions import ParamUsageError
from cli_command_parser.inputs import File, FileWrapper, Json

from mm.__version__ import __author_email__, __version__  # noqa
from mm.logging import init_logging

log = logging.getLogger(__name__)


class BattleLogCLI(Command, description='Memento Mori Battle Log CLI', option_name_mode='*-'):
    action = SubCommand()
    verbose = Counter('-v', help='Increase logging verbosity (can specify multiple times)')

    def _init_command_(self):
        init_logging(self.verbose)


class Extract(BattleLogCLI, help='Extract the portion of a battle log that can be viewed via mentemori.icu'):
    input: FileWrapper = Option(
        '-i', type=Json(type='file', exists=True), required=True, help='Input file generated during a battle'
    )
    output: FileWrapper = Option(
        '-o', type=File('w', allow_dash=True, encoding='utf-8', parents=True), default='-', help='Output destination'
    )

    def main(self):
        data = self.input.read()
        try:
            simulation_result = data['BattleResult']['SimulationResult']
        except KeyError as e:
            raise ParamUsageError(self.__class__.input, f'Missing expected key: {e}') from e

        self.output.write(json.dumps(simulation_result, indent=4))


if __name__ == '__main__':
    main()
