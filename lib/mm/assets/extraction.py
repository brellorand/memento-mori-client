"""
Asset extraction logic using UnityPy

Based on: https://github.com/K0lb3/UnityPy/blob/master/UnityPy/tools/extractor.py

Unhandled types (not a comprehensive list):
No exporter is configured for obj=<PPtr <ObjectReader Material>> with obj.type=<ClassIDType.Material: 21>
No exporter is configured for obj=<PPtr <ObjectReader SpriteAtlas>> with obj.type=<ClassIDType.SpriteAtlas: 687078895>
No exporter is configured for obj=<PPtr <ObjectReader AnimationClip>> with obj.type=<ClassIDType.AnimationClip: 74>
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Generic, Type, TypeVar

from UnityPy.classes import (
    AudioClip,
    Font,
    GameObject,
    Mesh,
    MonoBehaviour,
    Object,
    PPtr,
    Shader,
    Sprite,
    SpriteAtlas,
    TextAsset,
    Texture2D,
)
from UnityPy.enums.ClassIDType import ClassIDType

from mm.fs import path_repr

if TYPE_CHECKING:
    from UnityPy.files.ObjectReader import ObjectReader

    from .bundles import Bundle, BundleGroup

__all__ = ['BundleExtractor', 'AssetExporter']
log = logging.getLogger(__name__)

T = TypeVar('T')


class BundleExtractor:
    __slots__ = ('dst_dir', 'force', 'exported', '_exporters', 'unknown_as_raw', 'include_exts')

    def __init__(
        self, dst_dir: Path, force: bool = False, unknown_as_raw: bool = False, include_exts: tuple[str] = None
    ):
        self.dst_dir = dst_dir
        self.force = force
        self.exported = set()
        self._exporters = {}
        self.unknown_as_raw = unknown_as_raw
        self.include_exts = include_exts

    def _get_exporter(self, id_type: ClassIDType) -> AssetExporter:
        if exporter := self._exporters.get(id_type):
            return exporter
        try:
            exp_cls = AssetExporter.for_type(id_type)
        except KeyError as e:
            if self.unknown_as_raw:
                exp_cls = RawExporter
            else:
                raise MissingExporter from e
        self._exporters[id_type] = exporter = exp_cls(self)
        return exporter

    def extract_group_bundle(self, group: BundleGroup, bundle_name: str):
        log.debug(f'Loading asset file(s) from {bundle_name}...')
        container = group.get_container(bundle_name)
        log.debug(f'Loaded {len(container)} asset file(s) from {bundle_name}')
        for obj_path, obj in container.items():
            if self.include_exts and not obj_path.endswith(self.include_exts):
                log.debug(f'Skipping {obj_path} from {bundle_name}')
                continue

            try:
                self.save_asset(obj_path, obj)
            except MissingExporter:
                log.warning(
                    f'No exporter is configured for {obj_path} in {obj=} with {obj.type=} from {bundle_name}',
                    extra={'color': 'yellow'},
                )

    def extract_bundle(self, bundle: Bundle):
        log.debug(f'Loaded {len(bundle)} asset file(s) from {bundle}')
        for obj_path, obj in bundle.env.container.items():
            if self.include_exts and not obj_path.endswith(self.include_exts):
                log.debug(f'Skipping {obj_path} from {bundle}')
                continue

            try:
                self.save_asset(obj_path, obj)
            except MissingExporter:
                log.warning(
                    f'No exporter is configured for {obj_path} in {obj=} with {obj.type=} from {bundle}',
                    extra={'color': 'yellow'},
                )

    def save_asset(self, obj_path: str, obj: ObjectReader, nested: bool = False):
        exporter = self._get_exporter(obj.type)
        log.debug(f'{exporter.__class__.__name__}: Exporting all from {obj} for {obj_path}')
        exporter.export_all(obj.read(), self.dst_dir.joinpath(obj_path), nested)


class AssetExporter(ABC, Generic[T]):
    __slots__ = ('extractor', 'exported', 'force')
    _id_type_cls_map = {}
    id_type: ClassIDType = None
    default_ext: str | None = None

    def __init_subclass__(cls, id_type: ClassIDType = None, ext: str = None, **kwargs):
        super().__init_subclass__(**kwargs)
        if id_type is not None:
            cls.id_type = id_type
            cls._id_type_cls_map[id_type] = cls
        if ext:
            cls.default_ext = ext

    def __init__(self, extractor: BundleExtractor):
        self.extractor = extractor
        self.exported = extractor.exported
        self.force = extractor.force

    @classmethod
    def for_type(cls, id_type: ClassIDType) -> Type[AssetExporter]:
        return cls._id_type_cls_map[id_type]

    @abstractmethod
    def export_bytes(self, obj: T) -> bytes:
        """
        Required because the majority of subclasses only need to implement this method, but overriding
        :meth:`.export_all` can obviate the need for this method.
        """
        raise NotImplementedError

    def _register(self, obj: T):
        """Register an asset as having been exported to avoid duplicate work / problems caused by circular refs"""
        self.exported.add((obj.assets_file, obj.path_id))

    def maybe_update_dst_path(self, obj: T, dst_path: Path) -> Path:
        if dst_path.suffix or not self.default_ext:
            return dst_path
        return dst_path.parent.joinpath(f'{dst_path.name}{self.default_ext}')

    def export_all(self, obj: T, dst_path: Path, nested: bool = False):
        self._export(obj, dst_path)

    def _export(self, obj: T, dst_path: Path):
        dst_path = self.maybe_update_dst_path(obj, dst_path)
        if not self.force and dst_path.exists():
            # TODO: Behavior control to skip / overwrite / check hash + create dated version on change?
            log.debug(f'Skipping {path_repr(dst_path)} - it already exists')
            return

        try:
            data = self.export_bytes(obj)
        except SkipExport:
            pass
        else:
            self._save(obj, data, dst_path)

    def _save(self, obj: T, data: bytes, dst_path: Path):
        log.info(f'Saving {obj.__class__.__name__} object to {path_repr(dst_path)}')
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        dst_path.write_bytes(data)
        self._register(obj)


class RawExporter(AssetExporter[Object]):
    def export_bytes(self, obj: Object) -> bytes:
        return obj.get_raw_data()

    def _save(self, obj: T, data: bytes, dst_path: Path):
        log.info(f'Saving raw {obj.__class__.__name__} object to {path_repr(dst_path)}', extra={'color': 13})
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        dst_path.write_bytes(data)
        self._register(obj)


class TextExporter(AssetExporter[TextAsset], id_type=ClassIDType.TextAsset, ext='.txt'):
    def export_bytes(self, obj: TextAsset) -> bytes:
        return obj.script


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
    """
    MonoBehaviour assets are usually used to save the class instances with their values. If a type tree exists, it
    can be used to read the whole data, but if it doesn't exist, then it is usually necessary to investigate the
    class that loads the specific MonoBehaviour to extract the data.
    """

    def maybe_update_dst_path(self, obj: Font, dst_path: Path) -> Path:
        use_json = obj.serialized_type and obj.serialized_type.nodes
        if suffix := dst_path.suffix:
            # if suffix != '.asset' or not use_json:
            if not use_json:
                return dst_path
            # name = dst_path.stem
            name = dst_path.name
        else:
            name = dst_path.name

        if use_json:
            ext = '.json'
        # elif isinstance(obj, MonoBehaviour) and obj.m_Script:
        #     pass  # It's unclear what should be handled here, but the extension would be json in the extractor code
        else:
            ext = self.default_ext

        return dst_path.parent.joinpath(f'{name}{ext}')

    def export_bytes(self, obj: MonoBehaviour | Object) -> bytes:
        if obj.serialized_type and obj.serialized_type.nodes:
            return json.dumps(obj.read_typetree(), indent=4, ensure_ascii=False).encode('utf-8', 'surrogateescape')
        # elif isinstance(obj, MonoBehaviour) and obj.m_Script:
        #     pass  # It's unclear what should be handled here
        else:
            return obj.raw_data


class AudioClipExporter(AssetExporter[AudioClip], id_type=ClassIDType.AudioClip, ext='.wav'):
    """
    Exporter for audio clips.

    The raw / original data is accessible via the :attr:`AudioClip.m_AudioData` property.

    The raw data for some audio files in bundles that have a ``.ogg`` extension begins with ``FSB5``, which apparently
    indicates that it is using an optimized format that is primarily used by Unity.  This format is apparently missing
    some parts that general OggVorbis players expect to exist, so such files are converted (by UnityPy) to WAV for
    compatibility.
    """

    def maybe_update_dst_path(self, obj: T, dst_path: Path, sample_name: str = None) -> Path:
        if dst_path.suffix:
            if not sample_name or sample_name.endswith(dst_path.suffix) or '.' not in sample_name:
                return dst_path
            ext = '.' + sample_name.rsplit('.', 1)[1]
            name = dst_path.stem
        else:
            ext = self.default_ext
            name = dst_path.name

        return dst_path.parent.joinpath(f'{name}{ext}')

    def export_bytes(self, obj: AudioClip) -> bytes:
        # This method is not actually used since export_all is defined here
        # return obj.m_AudioData
        return b''

    def export_all(self, obj: AudioClip, dst_path: Path, nested: bool = False):
        log.debug(f'{self.__class__.__name__}: Exporting all from {nested=} {obj}')
        self._register(obj)
        samples: dict[str, bytes] = obj.samples  # This is a plain property - stored here to avoid re-computation
        if not samples:
            log.info(f'No audio samples found for {path_repr(dst_path)}', extra={'color': 'yellow'})
        elif len(samples) == 1:
            name, clip_data = samples.popitem()
            dst_path = self.maybe_update_dst_path(obj, dst_path, name)
            log.info(f'Saving {obj.__class__.__name__} object to {path_repr(dst_path)}')
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            dst_path.write_bytes(clip_data)
        else:
            # TODO: Handling for this case could probably use some improvement
            dst_path.mkdir(parents=True, exist_ok=True)
            for name, clip_data in samples.items():
                clip_path = self.maybe_update_dst_path(obj, dst_path.joinpath(name), name)
                log.info(f'Saving {obj.__class__.__name__} object to {path_repr(dst_path)}')
                clip_path.parent.mkdir(parents=True, exist_ok=True)
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


class SpriteAtlasExporter(AssetExporter[SpriteAtlas], id_type=ClassIDType.SpriteAtlas, ext='.png'):
    def export_bytes(self, obj: SpriteAtlas) -> bytes:
        return b''

    def export_all(self, obj: SpriteAtlas, dst_path: Path, nested: bool = False):
        log.debug(f'{self.__class__.__name__}: Exporting {len(obj.m_PackedSprites)} from {nested=} {obj}')
        dst_dir = dst_path.relative_to(self.extractor.dst_dir).with_suffix('')
        for i, sprite_ref in enumerate(obj.m_PackedSprites):
            if name := sprite_ref.read().name:
                if dst_dir.joinpath(name + self.default_ext).exists():
                    name += f'__{i}'
            else:
                name = f'{sprite_ref.type.name}_{i}'

            self.extractor.save_asset(dst_dir.joinpath(name).as_posix(), sprite_ref, nested=True)


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

        log.debug(f'GameObjectExporter._crawl found: {obj}')
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

    def export_all(self, obj: GameObject, dst_path: Path, nested: bool = False):
        log.debug(f'{self.__class__.__name__}: Exporting all from {nested=} {obj}')
        refs = self._crawl(obj)
        if not refs:
            log.info(f'No game objects found for {nested=} {dst_path.as_posix()}')
            if not nested and self.extractor.unknown_as_raw:
                RawExporter(self.extractor).export_all(obj, dst_path)
            return

        self._register(obj)
        dst_dir = dst_path.relative_to(self.extractor.dst_dir)
        for ref_id, ref in refs.items():
            # Don't export already exported objects a second time
            # and prevent circular calls by excluding other GameObjects.
            # The other GameObjects were already exported in this call.
            if (ref.assets_file, ref_id) in self.exported or ref.type == ClassIDType.GameObject:
                continue

            ref_path = dst_dir.joinpath(ref.name if ref.name else ref.type.name)
            self.extractor.save_asset(ref_path.as_posix(), ref, nested=True)


class SkipExport(Exception):
    """Used internally to indicate there is nothing to export"""


class MissingExporter(Exception):
    """Used internally to indicate no exporter is configured for a given ClassIDType"""
