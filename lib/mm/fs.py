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

from .exceptions import CacheError, CacheMiss

__all__ = ['get_user_temp_dir', 'get_user_cache_dir', 'relative_path', 'path_repr', 'get_config_dir']
log = logging.getLogger(__name__)

ON_WINDOWS = os.name == 'nt'
LIB_NAME = 'memento-mori-client'

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
            value = self._get(path)
        except CacheError:
            raise
        except Exception as e:
            log.warning(f'Error reading or deserializing cached data from path={path.as_posix()}')
            raise CacheMiss from e
        else:
            log.debug(f'Loaded cached data from {path.relative_to(self.root).as_posix()}')
            return value

    @classmethod
    def _get(cls, path: Path):
        if path.suffix == '.json':
            return json.loads(path.read_text('utf-8'))
        elif path.suffix in ('.mpk', '.msgpack'):
            return msgpack.unpackb(path.read_bytes(), timestamp=3)
        else:
            raise CacheError(f'Unexpected extension for cache path={path.as_posix()}')

    def store(self, data, name: str, raw: bool = False):
        path = self.root.joinpath(name)
        if raw:
            path.write_bytes(data)
        elif path.suffix == '.json':
            with path.open('w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        elif path.suffix in ('.mpk', '.msgpack'):
            path.write_bytes(msgpack.packb(data))
        else:
            raise ValueError(f'Unexpected extension for cache path={path.as_posix()}')


def get_config_dir(mode: int = 0o755) -> Path:
    path = Path('~/.config', LIB_NAME).expanduser()
    if not path.exists():
        path.mkdir(mode, parents=True, exist_ok=True)
    return path


def get_user_cache_dir(subdir: str = None, mode: int = 0o755) -> Path:
    cache_dir = get_user_temp_dir(*filter(None, (LIB_NAME, subdir)), mode=mode)
    if not cache_dir.is_dir():
        raise ValueError(f'Invalid path - not a directory: {cache_dir.as_posix()}')
    return cache_dir


def get_user_temp_dir(*sub_dirs, mode: int = 0o755) -> Path:
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
