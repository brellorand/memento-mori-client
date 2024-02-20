"""
Asset extraction logic using UnityPy (WIP)

Based on: https://github.com/K0lb3/UnityPy/blob/master/UnityPy/tools/extractor.py
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from io import BytesIO, StringIO
from pathlib import Path
from typing import Generic, TypeVar, Iterator

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
    def __init__(self, dst_dir: Path, force: bool = False):
        self.dst_dir = dst_dir
        self.force = force
        self.exported = set()
        self.exporters = AssetExporter.init_exporters(self)

    def extract_bundle(self, src_path: Path):
        env = UnityPy.load(src_path.as_posix())  # UnityPy does not support Path objects
        log.info(f'Loaded {len(env.container)} file(s) from {path_repr(src_path)}')
        for obj_path, obj in env.container.items():
            self.save_asset(obj_path, obj)

    def save_asset(self, obj_path: str, obj):
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
        exporter.export_all(asset, dst_path)


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

    def __init__(self, extractor: BundleExtractor):
        self.extractor = extractor
        self.exported = extractor.exported
        self.force = extractor.force

    @classmethod
    def init_exporters(cls, extractor: BundleExtractor) -> dict[ClassIDType, AssetExporter]:
        return {id_type: exp_cls(extractor) for id_type, exp_cls in cls._id_type_cls_map.items()}

    # @abstractmethod
    # def export(self, obj: T, dst_path: Path):
    #     raise NotImplementedError

    @abstractmethod
    def export_bytes(self, obj: T) -> bytes:
        raise NotImplementedError

    def _register(self, obj: T):
        self.exported.add((obj.assets_file, obj.path_id))

    def maybe_update_dst_path(self, obj: T, dst_path: Path) -> Path:
        # TODO: This check probably isn't necessary...
        if dst_path.suffix:
            return dst_path
        return dst_path.parent.joinpath(f'{dst_path.name}{self.default_ext}')

    def export_all(self, obj: T, dst_path: Path):
        self._export(obj, dst_path)

    def _export(self, obj: T, dst_path: Path):
        dst_path = self.maybe_update_dst_path(obj, dst_path)
        if not self.force and dst_path.exists():
            log.debug(f'Skipping {path_repr(dst_path)} - it already exists')
            return

        try:
            data = self.export_bytes(obj)
        except SkipExport:
            pass
        else:
            log.info(f'Saving {path_repr(dst_path)}')
            dst_path.write_bytes(data)
            self._register(obj)


class TextExporter(AssetExporter[TextAsset], id_type=ClassIDType.TextAsset, ext='.txt'):
    def export_bytes(self, obj: TextAsset) -> bytes:
        return obj.script

    # def export(self, obj: TextAsset, dst_path: Path):
    #     dst_path = self.maybe_update_dst_path(obj, dst_path)
    #     log.info(f'Saving {path_repr(dst_path)}')
    #     dst_path.write_bytes(obj.script)


class FontExporter(AssetExporter[Font], id_type=ClassIDType.Font, ext='.ttf'):
    def maybe_update_dst_path(self, obj: Font, dst_path: Path) -> Path:
        if not dst_path.suffix:
            if obj.m_FontData[0:4] == b'OTTO':
                ext = '.otf'
            else:
                ext = self.default_ext
            return dst_path.parent.joinpath(f'{dst_path.name}{ext}')
        return dst_path

    def export_bytes(self, obj: Font) -> bytes:
        return obj.m_FontData


class MeshExporter(AssetExporter[Mesh], id_type=ClassIDType.Mesh, ext='.obj'):
    def export_bytes(self, obj: Mesh) -> bytes:
        return obj.export().encode('utf-8')


class ShaderExporter(AssetExporter[Shader], id_type=ClassIDType.Shader, ext='.txt'):
    def export_bytes(self, obj: Shader) -> bytes:
        try:
            return obj.export().encode('utf-8')
        except AttributeError as e:
            log.debug(f'Unable to export {obj}')
            raise SkipExport from e


class MonoBehaviorExporter(AssetExporter[MonoBehaviour | Object], id_type=ClassIDType.MonoBehaviour, ext='.bin'):
    def maybe_update_dst_path(self, obj: Font, dst_path: Path) -> Path:
        if dst_path.suffix:
            return dst_path
        elif obj.serialized_type and obj.serialized_type.nodes:
            ext = '.json'
        # elif isinstance(obj, MonoBehaviour) and obj.m_Script:
        #     pass  # It's unclear what should be handled here, but the extension would be json in the extractor code
        else:
            ext = self.default_ext
        return dst_path.parent.joinpath(f'{dst_path.name}{ext}')

    def export_bytes(self, obj: MonoBehaviour | Object) -> bytes:
        if obj.serialized_type and obj.serialized_type.nodes:
            return json.dumps(obj.read_typetree(), indent=4, ensure_ascii=False).encode('utf-8', 'surrogateescape')
        # elif isinstance(obj, MonoBehaviour) and obj.m_Script:
        #     pass  # It's unclear what should be handled here
        else:
            return obj.raw_data


class AudioClipExporter(AssetExporter[AudioClip], id_type=ClassIDType.AudioClip, ext='.wav'):
    def maybe_update_dst_path(self, obj: T, dst_path: Path, sample_name: str = None) -> Path:
        if dst_path.suffix:
            if not sample_name or sample_name.endswith(dst_path.suffix) or '.' not in sample_name:
                return dst_path
            ext = '.' + sample_name.rsplit('.', 1)[1]
        else:
            ext = self.default_ext
        return dst_path.parent.joinpath(f'{dst_path.name}{ext}')

    def export_bytes(self, obj: AudioClip) -> bytes:
        return b''

    def export_all(self, obj: AudioClip, dst_path: Path):
        self._register(obj)
        samples = obj.samples
        if not samples:
            log.info(f'No audio samples found for {dst_path.as_posix()}')
        elif len(samples) == 1:
            dst_path = self.maybe_update_dst_path(obj, dst_path, next(iter(samples)))
            log.info(f'Saving {path_repr(dst_path)}')
            dst_path.write_bytes(next(iter(samples.values())))
        else:
            dst_path.mkdir(parents=True, exist_ok=True)
            for name, clip_data in samples.items():
                clip_path = self.maybe_update_dst_path(obj, dst_path.joinpath(name), name)
                log.info(f'Saving {path_repr(clip_path)}')
                clip_path.write_bytes(clip_data)


class SpriteExporter(AssetExporter[Sprite], id_type=ClassIDType.Sprite, ext='.png'):
    def export_bytes(self, obj: Sprite) -> bytes:
        self.exported.add((obj.assets_file, obj.path_id))
        self.exported.add((obj.m_RD.texture.assets_file, obj.m_RD.texture.path_id))
        alpha_assets_file = getattr(obj.m_RD.alphaTexture, 'assets_file', None)
        alpha_path_id = getattr(obj.m_RD.alphaTexture, 'path_id', None)
        if alpha_path_id and alpha_assets_file:
            self.exported.add((alpha_assets_file, alpha_path_id))

        bio = BytesIO()
        obj.image.save(bio, 'png')
        return bio.getvalue()


class Texture2DExporter(AssetExporter[Texture2D], id_type=ClassIDType.Texture2D, ext='.png'):
    def export_bytes(self, obj: Texture2D) -> bytes:
        if not obj.m_Width:
            raise SkipExport

        bio = BytesIO()
        obj.image.save(bio, 'png')
        return bio.getvalue()


class GameObjectExporter(AssetExporter[GameObject], id_type=ClassIDType.GameObject):
    def export_bytes(self, obj: GameObject) -> bytes:
        return b''

    @classmethod
    def _crawl(cls, obj: Object, found: dict = None):
        if found is None:
            found = {}

        if not isinstance(obj, PPtr) or (obj.path_id == 0 and obj.file_id == 0 and obj.index == -2):
            return found

        try:
            obj = obj.read()
        except AttributeError:
            return found

        found[obj.path_id] = obj
        # MonoBehaviour relies on their typetree while Object denotes that the class of the object isn't implemented yet
        if isinstance(obj, (MonoBehaviour, Object)):
            obj.read_typetree()
            data = obj.type_tree.__dict__.values()
        else:
            data = obj.__dict__.values()

        for value in cls._flatten(data):
            if isinstance(value, (Object, PPtr)) and value.path_id not in found:
                cls._crawl(value, found)

        return found

    @classmethod
    def _flatten(cls, obj):
        for item in obj:
            if isinstance(item, (list, tuple)):
                yield from cls._flatten(item)
            elif isinstance(item, dict):
                yield from cls._flatten(item.values())
            else:
                yield item

    def export_all(self, obj: GameObject, dst_path: Path):
        refs = self._crawl(obj)
        if not refs:
            log.info(f'No game objects found for {dst_path.as_posix()}')
            return

        self._register(obj)
        for ref_id, ref in refs.items():
            # Don't export already exported objects a second time
            # and prevent circular calls by excluding other GameObjects.
            # The other GameObjects were already exported in the this call.
            if (ref.assets_file, ref_id) in self.exported or ref.type == ClassIDType.GameObject:
                continue

            ref_path = dst_path.relative_to(self.extractor.dst_dir).joinpath(ref.name if ref.name else ref.type.name)
            self.extractor.save_asset(ref_path.as_posix(), ref)


class SkipExport(Exception):
    """Used internally to indicate there is nothing to export"""
