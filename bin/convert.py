#!/usr/bin/env python

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Iterator

from cli_command_parser import Command, Counter, Option, SubCommand, main
from cli_command_parser.inputs import Path as IPath
from cli_command_parser.utils import camel_to_snake_case

from mm.__version__ import __author_email__, __version__  # noqa
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
    output: Path = Option('-o', type=IPath(type='file', exists=False, allow_dash=True), help='Output path', default='-')
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


class LineIterator:
    __slots__ = ('line_num', 'last_line', 'lines')

    last_line: str | None

    def __init__(self, path: Path):
        self.line_num = 0
        self.last_line = None
        self.lines = iter(map(str.strip, path.read_text('utf-8').splitlines()))

    def __iter__(self):
        return self

    def __next__(self) -> str:
        line = next(self.lines)
        self.last_line = line
        self.line_num += 1
        return line


class Data(CodeConversionCLI, help='Convert a data class'):
    mode = Option('-m', choices=('stub', 'wrapper'), default='stub', help='Conversion mode')

    _annotation_replacements = [
        (re.compile(r'\bDictionary<'), 'dict['),
        (re.compile(r'\bList<'), 'list['),
        (re.compile(r'\bHashSet<'), 'set['),
        (re.compile(r'\bstring\b'), 'str'),
        (re.compile(r'\blong\b'), 'int'),
        (re.compile(r'\bDateTime\b'), 'datetime'),
    ]

    def format_class_line(self, cls_name: str) -> str:
        if self.mode == 'stub':
            return f'class {cls_name}(TypedDict):'
        else:
            return f'class {cls_name}(DictWrapper):'

    def format_property(self, attr_type: str, name: str) -> str:
        for pat, replacement in self._annotation_replacements:
            attr_type = pat.sub(replacement, attr_type)

        attr_type = attr_type.replace('>', ']')
        if attr_type == 'TimeSpan':
            attr_type = 'int'
            comment = '  # Divide by 1,000,000 to get the time delta in seconds'
        else:
            comment = ''

        if attr_type.endswith('?'):
            attr_type = attr_type[:-1] + ' | None'

        if self.mode == 'stub':
            return f'    {name}: {attr_type}{comment}'
        else:
            return f'    {camel_to_snake_case(name)}: {attr_type} = DataProperty({name!r}){comment}'

    def iter_py_lines(self, path: Path) -> Iterator[str]:
        lines = LineIterator(path)
        cls_name_pat = re.compile(r'^public (?:class|struct) (\w+)')
        while True:
            if m := cls_name_pat.match(next(lines)):
                cls_name = m.group(1)
                yield self.format_class_line(cls_name)
                break

        ignore = {'{', '}', 'get;', 'set;', 'readonly get;'}
        property_pat = re.compile(r'^public (.+) (\w+)(?:$|\s*\{)')
        method_pat = re.compile(r'^public (.+) (\w+)\(')
        private_method_pat = re.compile(r'^private (.+) (\w+)\(')
        constructor_pat = re.compile(r'^public (\w+)\(')

        for line in lines:
            if not line or line in ignore or line.startswith(('//', '[Description(', '[PropertyOrder(')):
                continue

            if m := property_pat.search(line):
                yield self.format_property(*m.groups())
            elif m := constructor_pat.search(line):
                method_name = m.group(1)
                if method_name != cls_name:
                    log.warning(f'Unexpected method={method_name!r} in {path}:{lines.line_num}: {line!r}')
                    continue

                self._consume_method(path, 'constructor', lines)
            elif m := method_pat.search(line):
                self._consume_method(path, f'method={m.group(1)!r}', lines)
            elif m := private_method_pat.search(line):
                self._consume_method(path, f'private method={m.group(1)!r}', lines)
            else:
                log.warning(f'Unexpected content in {path}:{lines.line_num}: {line!r}')

    @classmethod
    def _consume_method(cls, path: Path, method_type: str, lines: LineIterator):
        if lines.last_line.endswith(','):
            while True:
                if next(lines).endswith(')'):
                    break

        if next(lines) != '{':
            log.warning(f'Unexpected {method_type} content in {path}:{lines.line_num}: {lines.last_line!r}')
            return

        log.debug(f'Consuming {method_type} @ {path}:{lines.line_num}')
        opened = 1
        while opened > 0:
            line = next(lines)
            if line == '{':
                opened += 1
                log.debug(f'Consuming nested block @ {path}:{lines.line_num}')
            elif line == '}':
                opened -= 1
                log_type = method_type if opened == 0 else 'nested block'
                log.debug(f'Finished consuming {log_type} @ {path}:{lines.line_num}')
            elif line.startswith('}'):
                for c in line:
                    if c == '{':
                        opened += 1
                    elif c == '}':
                        opened -= 1

                log_type = method_type if opened == 0 else 'nested block'
                log.debug(f'Finished consuming {log_type} with additional content @ {path}:{lines.line_num}')


if __name__ == '__main__':
    main()
