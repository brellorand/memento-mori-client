"""
Asset extraction logic using UnityPy (WIP)

Based on: https://github.com/K0lb3/UnityPy/blob/master/UnityPy/tools/extractor.py
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Generic, TypeVar

import UnityPy
from UnityPy.classes import (
    Object,
    PPtr,
    MonoBehaviour,
    TextAsset,
    Font,
    Shader,
    Mesh,
    Sprite,
    Texture2D,
    AudioClip,
    GameObject,
)
from UnityPy.enums.ClassIDType import ClassIDType

from mm.fs import path_repr

__all__ = ['BundleExtractor', 'AssetExporter']
log = logging.getLogger(__name__)

T = TypeVar('T')


class BundleExtractor:
    def __init__(self, dst_dir: Path):
        self.exporters = AssetExporter.init_exporters()
        self.dst_dir = dst_dir

    def extract_bundle(self, src_path: Path):
        env = UnityPy.load(src_path.as_posix())  # UnityPy does not support Path objects
        log.info(f'Loaded {len(env.container)} file(s) from {path_repr(src_path)}')
        for obj_path, obj in env.container.items():
            if exporter := self.exporters.get(obj.type):
                self._save_asset(exporter, obj, obj_path)
            else:
                log.info(f'No exporter is configured for {obj=} with {obj.type=}')

    def _save_asset(self, exporter: AssetExporter, obj, obj_path: str):
        asset = obj.read()
        log.info(f'Extracting {asset.__class__.__name__} object to {obj_path}')
        # log.info(f'Extracting {asset.__class__} object to {obj_path}')
        dst_path = self.dst_dir.joinpath(obj_path)
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        exporter.export(asset, dst_path)


class AssetExporter(ABC, Generic[T]):
    _id_type_cls_map = {}
    id_type: ClassIDType
    default_ext: str | None = None

    def __init_subclass__(cls, id_type: ClassIDType, ext: str = None, **kwargs):  # noqa
        super().__init_subclass__(**kwargs)
        cls.id_type = id_type
        cls._id_type_cls_map[id_type] = cls
        if ext:
            cls.default_ext = ext

    @classmethod
    def init_exporters(cls) -> dict[ClassIDType, AssetExporter]:
        return {id_type: exp_cls() for id_type, exp_cls in cls._id_type_cls_map.items()}

    @abstractmethod
    def export(self, obj: T, dst_path: Path):
        raise NotImplementedError


class TextExporter(AssetExporter[TextAsset], id_type=ClassIDType.TextAsset, ext='.txt'):
    def export(self, obj: TextAsset, dst_path: Path):
        if not dst_path.suffix:  # TODO: This check probably isn't necessary...
            dst_path = dst_path.parent.joinpath(f'{dst_path.name}{self.default_ext}')

        log.info(f'Saving {path_repr(dst_path)}')
        dst_path.write_bytes(obj.script)
