"""
Class that represents a single asset Bundle file, and helpers for Bundle file discovery
"""

from __future__ import annotations

import logging
import os
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Iterator, Iterable

from UnityPy import load as load_bundle

from mm.fs import path_repr
from .extraction import BundleExtractor

if TYPE_CHECKING:
    from datetime import datetime
    from UnityPy.environment import Environment

__all__ = ['Bundle', 'find_bundles']
log = logging.getLogger(__name__)

PathLike = Path | str
PathOrPaths = PathLike | Iterable[PathLike]


class Bundle:
    def __init__(self, path: PathLike):
        self.path = path

    def __repr__(self) -> str:
        return f'<Bundle({self.path_str!r})>'

    @cached_property
    def path_str(self) -> str:
        return path_repr(self.path)

    @cached_property
    def env(self) -> Environment:
        return load_bundle(self.path.as_posix())  # UnityPy does not support Path objects

    @property
    def contents(self):
        return self.env.container

    def get_content_paths(self) -> list[str]:
        return list(self.env.container)

    def extract(
        self, dst_dir: Path, force: bool = False, unknown_as_raw: bool = False, include_exts: tuple[str] = None
    ):
        BundleExtractor(dst_dir, force, unknown_as_raw, include_exts=include_exts).extract_bundle(self)

    def __len__(self) -> int:
        return len(self.env.container)


def find_bundles(path_or_paths: PathOrPaths, *, mod_after: datetime = None) -> Iterator[Bundle]:
    if mod_after:
        earliest = mod_after.timestamp()
        paths = (path for path in _find_bundles(path_or_paths) if path.stat().st_mtime >= earliest)
    else:
        paths = _find_bundles(path_or_paths)

    for path in paths:
        yield Bundle(path)


def _find_bundles(src_paths: PathOrPaths) -> Iterator[Path]:
    if isinstance(src_paths, (str, Path)):
        src_paths = [_normalize_path(src_paths)]

    for path in src_paths:
        if path.is_file():
            yield path
        else:
            for root, dirs, files in os.walk(path):
                for file in files:
                    yield Path(root, file)


def _normalize_path(path: PathLike) -> Path:
    return Path(path).expanduser().resolve() if isinstance(path, str) else path
