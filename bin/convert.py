#!/usr/bin/env python

from __future__ import annotations

import logging
import re
from pathlib import Path

from cli_command_parser import Command, SubCommand, Counter, Option, main
from cli_command_parser.inputs import Path as IPath
# from cli_command_parser.utils import camel_to_snake_case

from mm.__version__ import __author_email__, __version__  # noqa
# from mm.fs import path_repr
from mm.logging import init_logging

log = logging.getLogger(__name__)


class CodeConversionCLI(Command, description='Memento Mori Code Converter', option_name_mode='*-'):
    action = SubCommand()
    verbose = Counter('-v', help='Increase logging verbosity (can specify multiple times)')

    def _init_command_(self):
        init_logging(self.verbose)


class Enum(CodeConversionCLI, help='Convert an enum class'):
    input: Path = Option(
        '-i', type=IPath(type='file', exists=True), help='Input file containing the enum to convert', required=True
    )
    output: Path = Option(
        '-o', type=IPath(type='file', exists=False, allow_dash=True), help='Output path', default='-'
    )

    def main(self):
        if self.output == Path('-'):
            print('\n'.join(self.iter_py_lines()))
        else:
            with self.output.open('w', encoding='utf-8', newline='\n') as f:
                f.write('\n'.join(self.iter_py_lines()))

    def iter_py_lines(self):
        lines = iter(map(str.strip, self.input.read_text('utf-8').splitlines()))

        cls_name_pat = re.compile(r'^public enum (\w+)$')
        while True:
            if m := cls_name_pat.match(next(lines)):
                cls_name = m.group(1)
                yield f'class {cls_name}(IntEnum):'
                break

        inline_desc_pat = re.compile(r'^\[Description\(".+?"\)] (\w+)(?:\s*=\s*(\d+))?$')

        last = -1
        for line in lines:
            line = line.rstrip(',')
            if not line or line in '{}':
                continue

            if m := inline_desc_pat.match(line):
                name, value = m.groups()
                if value:
                    value = int(value)
                else:
                    value = last + 1
            elif line.startswith('[Description('):
                continue
            else:
                try:
                    name, value = map(str.strip, line.split('=', 1))
                except ValueError:
                    name = line
                    value = last + 1
                else:
                    value = int(value)

            last = value
            if name == 'None':
                name = 'NONE'
            yield f'    {name} = {value:_d}'


if __name__ == '__main__':
    main()
