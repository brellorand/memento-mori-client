#!/usr/bin/env python

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from subprocess import check_call, check_output
from tempfile import TemporaryDirectory
from typing import TextIO

from cli_command_parser import Command, Counter, Flag, Option, main

log = logging.getLogger(__name__)
DEFAULT_PATH = Path('lib/mm/__version__.py')


class TagUpdater(Command):
    version_file_path: Path = Option(
        '-p', metavar='PATH', default=DEFAULT_PATH, help='Path to the __version__.py file to update'
    )
    verbose = Counter('-v', help='Increase logging verbosity (can specify multiple times)')
    dry_run = Flag('-D', help='Print the actions that would be taken instead of taking them')
    force_suffix = Flag(
        '-S', help='Always include a suffix (default: only when multiple versions are created on the same day)'
    )

    def _init_command_(self):
        log_fmt = '%(asctime)s %(levelname)s %(name)s %(lineno)d %(message)s' if self.verbose > 1 else '%(message)s'
        logging.basicConfig(level=logging.DEBUG if self.verbose else logging.INFO, format=log_fmt)

    def main(self):
        next_version = self.update_version()

        if self.dry_run:
            log.info(f'[DRY RUN] Would commit version file: {self.version_file_path.as_posix()}')
            log.info(f'[DRY RUN] Would create tag: {next_version}')
        else:
            log.info(f'Committing version file: {self.version_file_path.as_posix()}')
            check_call(['git', 'add', self.version_file_path.as_posix()])
            check_call(['git', 'commit', '-m', f'updated version to {next_version}'])
            check_call(['git', 'push'])

            log.info(f'Creating tag: {next_version}')
            check_call(['git', 'tag', next_version])
            check_call(['git', 'push', '--tags'])

    def update_version(self) -> str | None:
        path = self.version_file_path
        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir).joinpath('tmp.txt')
            log.debug(f'Writing updated file to temp file={tmp_path}')
            with path.open('r', encoding='utf-8') as f_in:
                with tmp_path.open('w', encoding='utf-8', newline='\n') as f_out:
                    new_ver = self._process_version_files(f_in, f_out)

            if new_ver:
                if self.dry_run:
                    log.info(f'[DRY RUN] Would replace original file={path.as_posix()} with modified version')
                else:
                    log.info(f'Replacing original file={path.as_posix()} with modified version')
                    tmp_path.replace(path)
            else:
                raise RuntimeError(f'No valid version was found in {path.as_posix()}')

        return new_ver

    def _process_version_files(self, f_in: TextIO, f_out: TextIO) -> str | None:
        version_pat = re.compile(r'^(\s*__version__\s?=\s?)(["\'])(\d{4}\.\d{2}\.\d{2}(?:-\d+)?)\2$')
        new_ver = None
        for line in f_in:
            if new_ver:
                f_out.write(line)
            elif m := version_pat.match(line):
                new_ver, new_line = self._updated_version_line(*m.groups())
                f_out.write(new_line)
            else:
                f_out.write(line)

        return new_ver

    def _updated_version_line(self, var: str, quote: str, old_ver: str):
        new_ver = get_next_version(old_ver, self.force_suffix)
        prefix = '[DRY RUN] Would replace' if self.dry_run else 'Replacing'
        log.info(f'{prefix} old version={old_ver} with new={new_ver}')
        return new_ver, f'{var}{quote}{new_ver}{quote}\n'


def get_latest_tag() -> str:
    stdout: str = check_output(['git', 'tag', '--list'], text=True)
    date, suffix = max(_date_and_suffix(line) for line in stdout.splitlines())
    return f'{date}-{suffix}'


def get_next_version(old_ver: str, force_suffix: bool = False) -> str:
    today = datetime.now(timezone.utc).date()
    old_date_str, old_suffix = _date_and_suffix(old_ver)
    if datetime.strptime(old_date_str, '%Y.%m.%d').replace(tzinfo=timezone.utc).date() < today:
        suffix = '-1' if force_suffix else ''
    else:
        suffix = f'-{old_suffix + 1}'
    return today.strftime(f'%Y.%m.%d{suffix}')


def _date_and_suffix(version: str) -> tuple[str, int]:
    try:
        date, suffix = version.split('-')
    except ValueError:
        return version, 0
    else:
        return date, int(suffix)


if __name__ == '__main__':
    main()
