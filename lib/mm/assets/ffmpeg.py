"""
Utilities for interacting with ffmpeg.
"""

from __future__ import annotations

import logging
from pathlib import Path
from subprocess import CalledProcessError, run
from typing import TYPE_CHECKING, Any, Sequence

if TYPE_CHECKING:
    from mm.fs import PathLike

__all__ = ['Ffmpeg', 'FfmpegError']
log = logging.getLogger(__name__)


class Ffmpeg:
    __slots__ = ('bin_path',)

    def __init__(self, path: PathLike = None):
        self.bin_path = path.as_posix() if isinstance(path, Path) else path or 'ffmpeg'

    def convert_to_flac(self, in_path: PathLike, out_path: PathLike = None, capture: bool = False) -> Path:
        in_path = Path(in_path).resolve() if not isinstance(in_path, Path) else in_path
        if out_path is None:
            out_path = in_path.with_suffix('.flac')

        self.run(['-i', in_path.as_posix(), out_path.as_posix()], capture=capture)
        return out_path

    def run(
        self,
        args: Sequence[str] = (),
        file: PathLike = None,
        *,
        capture: bool = False,
        decode: bool = True,
        kwargs: dict[str, Any] = None,
        log_level: int = logging.DEBUG,
    ):
        command = [self.bin_path, *args]
        if kwargs:
            command.extend(kwargs_to_cli_args(kwargs))
        if file is not None:
            command.append(file.as_posix() if isinstance(file, Path) else file)

        log.log(log_level, f'Running command: {command}')
        try:
            results = run(command, capture_output=capture, check=True)
        except CalledProcessError as e:
            raise FfmpegError(command, 'Command did not complete successfully') from e

        if not capture:
            return None
        return results.stdout.decode('utf-8') if decode else results.stdout


def kwargs_to_cli_args(kwargs: dict[str, Any]) -> list[str]:
    args = []
    for k, v in sorted(kwargs.items()):
        args.append(f'-{k}')
        if v is not None:
            args.append(str(v))
    return args


class FfmpegError(Exception):
    """Base exception for errors related to using ffmpeg"""

    def __init__(self, command: list[str], message: str):
        self.command = command
        self.message = message

    def __str__(self) -> str:
        return f'Error running {self.command[0]}: {self.message}'
