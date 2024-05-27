#!/usr/bin/env python

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Iterator

from cli_command_parser import Command, SubCommand, Counter, Option, main
from cli_command_parser.inputs import Path as IPath
# from cli_command_parser.utils import camel_to_snake_case

from mm.__version__ import __author_email__, __version__  # noqa
# from mm.fs import path_repr
from mm.logging import init_logging

log = logging.getLogger(__name__)


class CodeConversionCLI(Command, description='Memento Mori Code Converter', option_name_mode='*-'):
    action = SubCommand()
    input: list[Path] = Option(
        '-i',
        type=IPath(type='file', exists=True),
        nargs='+',
        required=True,
        help='Input file containing the enum to convert',
    )
    output: Path = Option(
        '-o', type=IPath(type='file', exists=False, allow_dash=True), help='Output path', default='-'
    )
    verbose = Counter('-v', help='Increase logging verbosity (can specify multiple times)')

    def _init_command_(self):
        init_logging(self.verbose)

    def main(self):
        if self.output == Path('-'):
            print('\n'.join(self.iter_all_py_lines()))
        else:
            with self.output.open('w', encoding='utf-8', newline='\n') as f:
                f.write('\n'.join(self.iter_all_py_lines()))

    def iter_all_py_lines(self):
        for i, path in enumerate(self.input):
            if i:
                yield '\n'

            try:
                yield from self.iter_py_lines(path)
            except RuntimeError:
                log.error(f'Error processing {path}')
                raise

    def iter_py_lines(self, path: Path) -> Iterator[str]:
        raise NotImplementedError


class Enum(CodeConversionCLI, help='Convert an enum class'):
    def iter_py_lines(self, path: Path) -> Iterator[str]:
        lines = iter(map(str.strip, path.read_text('utf-8').splitlines()))

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


class TypedDict(CodeConversionCLI, help='Convert a response class'):
    def iter_py_lines(self, path: Path) -> Iterator[str]:
        lines = iter(map(str.strip, path.read_text('utf-8').splitlines()))

        cls_name_pat = re.compile(r'^public (?:class|struct) (\w+)')
        line_num = 0
        while True:
            line_num += 1
            if m := cls_name_pat.match(next(lines)):
                cls_name = m.group(1)
                yield f'class {cls_name}(TypedDict):'
                break

        ignore = {'{', '}', 'get;', 'set;', 'readonly get;'}
        property_pat = re.compile(r'^public (.+) (\w+)(?:$|\s*\{)')
        method_pat = re.compile(r'^public (.+) (\w+)\(')
        private_method_pat = re.compile(r'^private (.+) (\w+)\(')
        constructor_pat = re.compile(r'^public (\w+)\(')

        replacements = [
            (re.compile(r'\bDictionary<'), 'dict['),
            (re.compile(r'\bList<'), 'list['),
            (re.compile(r'\bHashSet<'), 'set['),
            (re.compile(r'\bstring\b'), 'str'),
            (re.compile(r'\blong\b'), 'int'),
            (re.compile(r'\bDateTime\b'), 'datetime'),
        ]

        for line in lines:
            line_num += 1
            if not line or line in ignore or line.startswith(('//', '[Description(')):
                continue

            if m := property_pat.search(line):
                attr_type, name = m.groups()
                for pat, replacement in replacements:
                    attr_type = pat.sub(replacement, attr_type)
                attr_type = attr_type.replace('>', ']')
                yield f'    {name}: {attr_type}'
            elif m := constructor_pat.search(line):
                method_name = m.group(1)
                if method_name != cls_name:
                    # line_num = self._consume_method(path, f'method={method_name!r}', lines, line_num)
                    log.warning(f'Unexpected method={method_name!r} in {path}:{line_num}: {line!r}')
                    continue

                log.debug(f'Found constructor @ {path}:{line_num}')
                if line.endswith(','):
                    while True:
                        line_num += 1
                        if next(lines).endswith(')'):
                            break

                line_num = self._consume_method(path, 'constructor', lines, line_num)
            elif m := method_pat.search(line):
                method_name = m.group(1)
                line_num = self._consume_method(path, f'method={method_name!r}', lines, line_num)
            elif m := private_method_pat.search(line):
                method_name = m.group(1)
                line_num = self._consume_method(path, f'private method={method_name!r}', lines, line_num)
            else:
                log.warning(f'Unexpected content in {path}:{line_num}: {line!r}')

    @classmethod
    def _consume_method(cls, path: Path, method_type: str, lines: Iterator[str], line_num: int) -> int:
        line_num += 1
        if (line := next(lines)) != '{':
            log.warning(f'Unexpected {method_type} content in {path}:{line_num}: {line!r}')
            return line_num

        log.debug(f'Consuming {method_type} @ {path}:{line_num}')
        opened = 1
        while opened > 0:
            line_num += 1
            line = next(lines)
            if line == '{':
                opened += 1
                log.debug(f'Consuming nested block @ {path}:{line_num}')
            elif line == '}':
                opened -= 1
                log_type = method_type if opened == 0 else 'nested block'
                log.debug(f'Finished consuming {log_type} @ {path}:{line_num}')
            elif line.startswith('}'):
                for c in line:
                    if c == '{':
                        opened += 1
                    elif c == '}':
                        opened -= 1

                log_type = method_type if opened == 0 else 'nested block'
                log.debug(f'Finished consuming {log_type} with additional content @ {path}:{line_num}')

        return line_num


if __name__ == '__main__':
    main()
