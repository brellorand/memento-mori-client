"""
Helpers for working with filesystems / paths
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from getpass import getuser
from pathlib import Path
from tempfile import gettempdir

import msgpack

from .exceptions import CacheMiss

__all__ = ['validate_or_make_dir', 'get_user_temp_dir', 'get_user_cache_dir', 'relative_path', 'path_repr']
log = logging.getLogger(__name__)

ON_WINDOWS = os.name == 'nt'

PathLike = str | Path


class FileCache:
    def __init__(self, subdir: str = None, use_cache: bool = True):
        self.use_cache = use_cache
        self.root = get_user_cache_dir(subdir)

    def get(self, name: str):
        if not self.use_cache:
            raise CacheMiss

        path = self.root.joinpath(name)
        try:
            mod_time = datetime.fromtimestamp(path.stat().st_mtime)
        except OSError as e:
            raise CacheMiss from e

        if mod_time.date() != datetime.now().date():
            raise CacheMiss

        try:
            if path.suffix == '.json':
                return json.loads(path.read_text('utf-8'))
            elif path.suffix in ('.mpk', '.msgpack'):
                return msgpack.unpackb(path.read_bytes(), timestamp=3)
        except Exception as e:
            log.warning(f'Error reading or deserializing cached data from path={path.as_posix()}')
            raise CacheMiss from e

        raise ValueError(f'Unexpected extension for cache path={path.as_posix()}')

    def store(self, data, name: str, raw: bool = False):
        path = self.root.joinpath(name)
        if raw:
            path.write_bytes(data)
        elif path.suffix == '.json':
            with path.open('w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        elif path.suffix in ('.mpk', '.msgpack'):
            path.write_bytes(msgpack.packb(data, timestamp=3))
        else:
            raise ValueError(f'Unexpected extension for cache path={path.as_posix()}')


def validate_or_make_dir(
    dir_path: PathLike, permissions: int = None, suppress_perm_change_exc: bool = True
) -> Path:
    """
    Validate that the given path exists and is a directory.  If it does not exist, then create it and any intermediate
    directories.

    Example value for permissions: 0o1777

    :param dir_path: The path of a directory that exists or should be created if it doesn't
    :param permissions: Permissions to set on the directory if it needs to be created (octal notation is suggested)
    :param suppress_perm_change_exc: Suppress an OSError if the permission change is unsuccessful (default:
      suppress/True)
    :return: The path
    """
    path = Path(dir_path).expanduser()
    if path.is_dir():
        return path
    elif path.exists():
        raise ValueError(f'Invalid path - not a directory: {dir_path}')
    else:
        path.mkdir(parents=True)
        if permissions is not None:
            try:
                path.chmod(permissions)
            except OSError as e:
                log.error(f'Error changing permissions of path {dir_path!r} to 0o{permissions:o}: {e}')
                if not suppress_perm_change_exc:
                    raise
    return path


def get_user_cache_dir(subdir: str = None, mode: int = 0o777) -> Path:
    cache_dir = get_user_temp_dir(*filter(None, ('mememori', subdir)), mode=mode)
    if not cache_dir.is_dir():
        raise ValueError(f'Invalid path - not a directory: {cache_dir.as_posix()}')
    return cache_dir


def get_user_temp_dir(*sub_dirs, mode: int = 0o777) -> Path:
    """
    On Windows, returns `~/AppData/Local/Temp` or a sub-directory named after the current user of another temporary
    directory.  On Linux, returns a sub-directory named after the current user in `/tmp`, `/var/tmp`, or `/usr/tmp`.

    :param sub_dirs: Child directories of the chosen directory to include/create
    :param mode: Permissions to set if the directory needs to be created (0o777 by default, which matches the default
      for :meth:`pathlib.Path.mkdir`)
    """
    path = Path(gettempdir())
    if not ON_WINDOWS or not path.as_posix().endswith('AppData/Local/Temp'):
        path = path.joinpath(getuser())
    if sub_dirs:
        path = path.joinpath(*sub_dirs)
    if not path.exists():
        path.mkdir(mode=mode, parents=True, exist_ok=True)
    return path


def relative_path(path: PathLike, to: PathLike = '.') -> str:
    path = Path(path).resolve()
    to = Path(to).resolve()
    try:
        return path.relative_to(to).as_posix()
    except Exception:  # noqa
        return path.as_posix()


def path_repr(path: Path, is_dir: bool = None) -> str:
    try:
        home_str = f'~/{path.relative_to(Path.home()).as_posix()}'
    except Exception:  # noqa
        home_str = path.as_posix()

    path_str = min((home_str, relative_path(path)), key=len)
    if is_dir is None:
        is_dir = path.is_dir()
    return (path_str + '/') if is_dir else path_str