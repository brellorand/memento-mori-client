"""
Helpers for working with filesystems / paths
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, date
from getpass import getuser
from hashlib import md5
from pathlib import Path
from string import printable
from tempfile import gettempdir
from time import time_ns
from typing import TYPE_CHECKING, Mapping, Any
from urllib.parse import quote, urlparse

import msgpack

from .exceptions import CacheError, CacheMiss
from .output import CompactJSONEncoder
from .properties import cached_classproperty

if TYPE_CHECKING:
    from .mb_models import MB

__all__ = [
    'get_user_temp_dir', 'get_user_cache_dir', 'relative_path', 'path_repr', 'get_config_dir',
    'sanitize_file_name',
]
log = logging.getLogger(__name__)

ON_WINDOWS = os.name == 'nt'
LIB_NAME = 'memento-mori-client'
_NotSet = object()

PathLike = str | Path


class FileCache:
    __slots__ = ('use_cache', 'root')

    def __init__(self, subdir: str = None, use_cache: bool = True):
        self.use_cache = use_cache
        self.root = get_user_cache_dir(subdir)

    def get(self, name: str, default=_NotSet):
        try:
            return self._get(name)
        except CacheMiss:
            if default is _NotSet:
                raise
            return default

    def _get(self, name: str):
        if not self.use_cache:
            raise CacheMiss

        path = self.root.joinpath(name)
        try:
            mod_time = datetime.fromtimestamp(path.stat().st_mtime)
        except OSError as e:
            raise CacheMiss from e

        # Ignore modification date if this cache is based on app version.
        # The date is still obtained above in this case to verify the existence of the file.
        if mod_time.date() != date.today():
            raise CacheMiss

        try:
            value = self._read(path)
        except CacheError:
            raise
        except Exception as e:
            log.warning(f'Error reading or deserializing cached data from path={path.as_posix()}')
            raise CacheMiss from e
        else:
            log.debug(f'Loaded cached data from {path.relative_to(self.root).as_posix()}')
            return value

    @classmethod
    def _read(cls, path: Path):
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


class MBFileCache(FileCache):
    __slots__ = ('mb',)

    def __init__(self, mb: MB, subdir: str = None, use_cache: bool = True):
        super().__init__(subdir, use_cache)
        self.mb = mb

    def _get(self, name: str):
        if not self.use_cache:
            raise CacheMiss

        path = self.root.joinpath(f'{name}.msgpack')
        try:
            data = path.read_bytes()
        except OSError as e:
            raise CacheMiss from e

        # The MB catalog contains MD5 hashes of the msgpack serialized MB files, which can be used for cache
        # invalidation.  This helps to avoid re-downloading files that have not changed between versions.
        cached_hash = md5(data, usedforsecurity=False).hexdigest().lower()
        if (expected_hash := self.mb.file_map[name].hash) != cached_hash:
            log.debug(f'Data in {name} changed - {cached_hash=} != {expected_hash=}')
            raise CacheMiss

        try:
            value = msgpack.unpackb(data, timestamp=3)
        except Exception as e:
            log.warning(f'Error deserializing cached data from path={path.as_posix()}')
            raise CacheMiss from e
        else:
            log.debug(f'Loaded cached data from {path.relative_to(self.root).as_posix()}')
            return value

    def store(self, data, name: str, raw: bool = False):
        super().store(data, f'{name}.msgpack', raw)


class HTTPSaver:
    __slots__ = ('dir',)

    def __init__(self, directory: PathLike):
        self.dir = Path(directory).resolve()
        self.dir.mkdir(parents=True, exist_ok=True)

    def save_request(self, method: str, url: str, headers: dict[str, Any], data=None):
        self._save('req', method, url, headers, data)

    def save_response(self, method: str, url: str, headers: dict[str, Any], data: bytes):
        # 0=Timestamp, 1=float (Seconds from the EPOCH), 2=int (ns from the EPOCH), 3=datetime.datetime (UTC)
        self._save('resp', method, url, headers, msgpack.unpackb(data, timestamp=2, strict_map_key=False))

    @classmethod
    def _prep_data(cls, data):
        if isinstance(data, dict):
            # msgpack supports int keys, but json does not
            return {str(k): cls._prep_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [cls._prep_data(v) for v in data]
        else:
            return data

    def _save(self, kind: str, method: str, url: str, headers, data):
        to_save = {'headers': dict(headers), 'data': self._prep_data(data)}
        parsed = urlparse(url)
        name = f'{time_ns()}_{method}_{kind}_{parsed.hostname}{"__".join(parsed.path.split("/"))}.json'
        with self.dir.joinpath(name).open('w', encoding='utf-8') as f:
            json.dump(to_save, f, indent=4, ensure_ascii=False, cls=CompactJSONEncoder)


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


class PathValidator:
    _replacements = {'/': '_', ':': '-', '\\': '_', '|': '-'}
    _mac_reserved = {':'}

    def __init__(self, replacements: Mapping[str, str] | None = _NotSet):
        replacements = self._replacements if replacements is _NotSet else {} if replacements is None else replacements
        self.table = str.maketrans({i: replacements.get(i) or quote(i, safe='') for i in self._invalid_chars})  # noqa

    def validate(self, file_name: str):
        root = os.path.splitext(os.path.basename(file_name))[0]
        if root in self._mac_reserved or root in self._win_reserved:
            raise ValueError(f'Invalid {file_name=} - it contains reserved name={root!r}')
        if invalid := next((c for c in self._invalid_chars if c in file_name), None):  # noqa
            raise ValueError(f'Invalid {file_name=} - it contains 1 or more invalid characters, including {invalid!r}')

    def sanitize(self, file_name: str) -> str:
        root = os.path.splitext(os.path.basename(file_name))[0]
        if root in self._mac_reserved or root in self._win_reserved:
            file_name = f'_{file_name}'
        return file_name.translate(self.table)

    @classmethod
    def _sanitize(cls, file_name: str, replacements: Mapping[str, str] | None = _NotSet) -> str:
        return cls(replacements).sanitize(file_name)

    @cached_classproperty
    def _win_reserved(cls) -> set[str]:  # noqa
        reserved = {'CON', 'PRN', 'AUX', 'CLOCK$', 'NUL'}
        reserved.update(f'{n}{i}' for n in ('COM', 'LPT') for i in range(1, 10))
        return reserved

    @cached_classproperty
    def _invalid_chars(cls) -> set[str]:  # noqa
        unprintable_ascii = {c for c in map(chr, range(128)) if c not in printable}
        win_invalid = '/:*?"<>|\t\n\r\x0b\x0c\\'
        return unprintable_ascii.union(win_invalid)


sanitize_file_name = PathValidator._sanitize
