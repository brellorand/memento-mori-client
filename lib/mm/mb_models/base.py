"""
Classes that wrap API responses
"""

from __future__ import annotations

import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import cached_property
from typing import TYPE_CHECKING, Any, Iterator, Type, TypeVar

from mm.data import DictWrapper
from mm.enums import ItemType, Locale, TowerType
from mm.fs import CacheMiss, MBFileCache, path_repr
from mm.properties import DataProperty
from .utils import LocalizedString, MBEntityList, MBEntityMap

if TYPE_CHECKING:
    from mm.session import MementoMoriSession
    from .characters import Character, CharacterProfile
    from .items import (
        AnyItem,
        ChangeItem,
        CharacterFragment,
        Equipment,
        EquipmentEnhanceRequirements,
        EquipmentPart,
        EquipmentSetMaterial,
        EquipmentUpgradeRequirements,
        Item,
        Rune,
        TreasureChest,
    )
    from .player import PlayerRank, VipLevel
    from .quest import Quest
    from .tower import TowerBattleQuest
    from .world_group import WorldGroup

__all__ = ['MB', 'MBEntity']
log = logging.getLogger(__name__)

MBE = TypeVar('MBE', bound='MBEntity')


class MB:
    def __init__(
        self,
        session: MementoMoriSession,
        *,
        catalog: dict[str, Any] = None,
        use_cache: bool = True,
        locale: Locale = Locale.EnUs,
    ):
        self._session = session
        self.__catalog = catalog
        self.locale = Locale(locale)
        self._locale_text_resource_map = {}
        self._cache = MBFileCache(self, 'mb', use_cache=use_cache)
        log.debug(f'Using MB cache dir: {path_repr(self._cache.root)}')

    # region Base MB data

    @cached_property
    def catalog(self) -> dict[str, Any]:
        if self.__catalog:
            return self.__catalog
        return self._session.data_client._get_mb_catalog()

    @cached_property
    def file_map(self) -> dict[str, FileInfo]:
        """
        Example info map:
        {
            'AchieveRankingRewardMB': {'Hash': 'fd9d21d514779c2e3758992907156420', 'Name': 'AchieveRankingRewardMB', 'Size': 47188},
            'ActiveSkillMB': {'Hash': 'ae15826e4bd042d14a61dad219c91932', 'Name': 'ActiveSkillMB', 'Size': 372286},
            ...
            'VipMB': {'Hash': 'be0114a5a24b5350459cdba6eea6bbcf', 'Name': 'VipMB', 'Size': 16293},
            'WorldGroupMB': {'Hash': '34afb2d419e8153a451d53b54d9829ae', 'Name': 'WorldGroupMB', 'Size': 20907}
        }
        """
        return {name: FileInfo(data) for name, data in self.catalog['MasterBookInfoMap'].items()}

    @cached_property
    def _mb_raw_cache(self):
        # TODO: Only check for file existence here instead of keeping all of these raw values in memory
        return {name: data for name in self.file_map if (data := self._cache.get(name, None)) is not None}

    def populate_cache(self, parallel: int = 4):
        file_names = set(self.file_map).difference(self._mb_raw_cache)
        if not file_names:
            log.log(19, 'All MB files are already in the cache')
            return

        log.log(19, f'Downloading {len(file_names):,d} files using {parallel} threads')
        with ThreadPoolExecutor(max_workers=parallel) as executor:
            futures = {executor.submit(self._get_mb_data, name, refresh=True): name for name in file_names}
            for future in as_completed(futures):
                self._mb_raw_cache[futures[future]] = future.result()

    # endregion

    # region File-Specific Helpers

    @cached_property
    def _mb_entity_classes(self) -> dict[str, Type[MBEntity]]:
        return MBEntity._name_cls_map

    def _get_mb_data(self, name: str, refresh: bool = False):
        if not refresh:
            try:
                return self._cache.get(name)
            except CacheMiss:
                pass

        data = self._session.data_client.get_mb_data(name)
        self._cache.store(data, name)
        return data

    def get_raw_data(self, name: str):
        if mb_raw_cache := self.__dict__.get('_mb_raw_cache'):
            # Avoid populating the cache if `populate_cache` was not called
            return mb_raw_cache[name]
        else:
            return self._get_mb_data(name)

    def get_data(self, cls: Type[MBEntity], locale: Locale = None):
        return self.get_raw_data(cls._file_name_fmt.format(locale=locale or self.locale))

    def _iter_mb_objects(self, cls: Type[MBE], locale: Locale = None) -> Iterator[MBE]:
        for row in self.get_data(cls, locale):
            yield cls(self, row)

    # endregion

    # region Text Resources / Localization

    @cached_property
    def text_resource_map(self) -> dict[str, str]:
        """Mapping of ``{StringKey: Text}`` for every entry in the `TextResource{locale}MB`."""
        return self.get_text_resource_map(self.locale)

    def get_text_resource_map(self, locale: Locale) -> dict[str, str]:
        try:
            return self._locale_text_resource_map[locale]
        except KeyError:
            pass

        text_resource_map = {res.key: res.value for res in self._iter_mb_objects(TextResource, locale)}
        self._locale_text_resource_map[locale] = text_resource_map
        return text_resource_map

    # endregion

    # region Items & Equipment

    # @cached_property
    # def _get_item_type_class(self) -> Callable[[ItemType], Type[AnyItem]]:
    #     from .items import TypedItem
    #
    #     return TypedItem.get_type_class

    def get_item(self, item_type: ItemType | int, item_id: int) -> AnyItem:
        # ItemType=3: Gold
        # ItemType=5: object parts for a given slot/set
        # ItemType=9: Adamantite material for a given slot/level
        if type_group := self.items.get(item_type):
            return type_group[item_id]
        elif item_type == ItemType.Equipment:  # 4
            return self.equipment[item_id]
        elif item_type == ItemType.EquipmentFragment:  # 5
            return self.equipment_parts[item_id]
        elif item_type == ItemType.EquipmentSetMaterial:  # 9
            return self.adamantite[item_id]
        elif item_type == ItemType.Rune:  # 14
            return self.runes[item_id]
        elif item_type == ItemType.TreasureChest:  # 17
            return self.treasure_chests[item_id]
        elif item_type == ItemType.CharacterFragment:  # 7
            return self.character_fragments[item_id]
        raise KeyError(f'Unable to find item with {item_type=}, {item_id=}')

    @cached_property
    def items(self) -> dict[int, dict[int, Item]]:
        from .items import Item

        return self._get_typed_items(Item)

    @cached_property
    def change_items(self) -> dict[int, dict[int, ChangeItem]]:
        return self._get_typed_items(ChangeItem)

    def _get_typed_items(self, cls: Type[MBE], locale: Locale = None) -> dict[int, dict[int, MBE]]:
        type_id_item_map = {}
        for item in self._iter_mb_objects(cls, locale):
            try:
                type_id_item_map[item.item_type][item.item_id] = item
            except KeyError:
                type_id_item_map[item.item_type] = {item.item_id: item}

        return type_id_item_map

    adamantite: dict[int, EquipmentSetMaterial] = MBEntityMap('EquipmentSetMaterial')
    equipment: dict[int, Equipment] = MBEntityMap('Equipment')
    equipment_enhance_reqs: dict[int, EquipmentEnhanceRequirements] = MBEntityMap('EquipmentEnhanceRequirements')
    _equipment_upgrade_reqs: dict[int, EquipmentUpgradeRequirements] = MBEntityMap('EquipmentUpgradeRequirements')
    runes: dict[int, Rune] = MBEntityMap('Rune')
    treasure_chests: dict[int, TreasureChest] = MBEntityMap('TreasureChest')

    @cached_property
    def equipment_parts(self) -> dict[int, EquipmentPart]:
        part_id_items_map = defaultdict(list)
        for item in self.equipment.values():
            if item.part_id:
                part_id_items_map[item.part_id].append(item)

        return {
            part_id: EquipmentPart(self, min(items, key=lambda i: i.level))
            for part_id, items in part_id_items_map.items()
        }

    @cached_property
    def weapon_upgrade_requirements(self) -> EquipmentUpgradeRequirements:
        return self._equipment_upgrade_reqs[1]

    @cached_property
    def armor_upgrade_requirements(self) -> EquipmentUpgradeRequirements:
        return self._equipment_upgrade_reqs[2]

    @cached_property
    def character_fragments(self) -> dict[int, CharacterFragment]:
        from .items import CharacterFragment

        return {char.id: CharacterFragment(self, char) for char in self.characters.values()}

    # endregion

    quests: dict[int, Quest] = MBEntityMap('Quest')
    tower_floors: dict[int, TowerBattleQuest] = MBEntityMap('TowerBattleQuest')

    @cached_property
    def tower_type_floors_map(self) -> dict[TowerType, list[TowerBattleQuest]]:
        tower_type_floors_map = {t: [] for t in TowerType if t != TowerType.NONE}
        for floor in self.tower_floors.values():
            tower_type_floors_map[floor.type].append(floor)
        return tower_type_floors_map

    world_groups: list[WorldGroup] = MBEntityList('WorldGroup')

    # region Player Attributes

    vip_levels: list[VipLevel] = MBEntityList('VipLevel')
    player_ranks: dict[int, PlayerRank] = MBEntityMap('PlayerRank')

    # endregion

    # region Characters

    characters: dict[int, Character] = MBEntityMap('Character')
    character_profiles: dict[int, CharacterProfile] = MBEntityMap('CharacterProfile')

    @cached_property
    def _char_map(self) -> dict[str, Character]:
        all_aliases = {8: ('FLO',), 46: ('LUNA',)}

        char_map = {}
        for num, char in self.characters.items():
            char_map[str(num)] = char
            char_map[char.full_id.upper()] = char
            char_map[char.full_name.upper()] = char
            # Using setdefault here to prevent summer Cordie from conflicting with normal Cordie, for example
            char_map.setdefault(char.name.upper(), char)

            if aliases := all_aliases.get(num):
                for alias in aliases:
                    char_map[alias] = char

        return char_map

    def get_character(self, id_or_name: str) -> Character:
        try:
            return self._char_map[id_or_name.upper()]
        except KeyError as e:
            raise KeyError(
                f'Unknown character name={id_or_name!r} - use `mb.py show character names`'
                ' to find the correct ID to use here'
            ) from e

    # endregion


class FileInfo(DictWrapper):
    hash: str = DataProperty('Hash', str.lower)
    name: str = DataProperty('Name')
    size: int = DataProperty('Size', int)


# region Generic / Base Entity Classes


class MBEntity:
    __slots__ = ('data', 'mb')

    id: int = DataProperty('Id')
    ignore: bool = DataProperty('IsIgnore', default=False)

    _id_key: str = 'Id'
    _file_name_fmt: str = None
    _name_cls_map = {}

    def __init_subclass__(cls, file_name_fmt: str = None, id_key: str = None, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._name_cls_map[cls.__name__] = cls
        if file_name_fmt:
            cls._file_name_fmt = file_name_fmt
        if id_key:
            cls._id_key = id_key

    def __init__(self, mb: MB, data: dict[str, Any]):
        self.mb = mb
        self.data = data

    def __repr__(self) -> str:
        attrs = ('full_name', 'name', 'id')
        key, val = next((attr, v) for attr in attrs if (v := getattr(self, attr, None)) is not None)
        return f'<{self.__class__.__name__}[{key}={val!r}]>'

    def __eq__(self, other: MBEntity) -> bool:
        return isinstance(other, self.__class__) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.__class__) ^ hash(self.id)


class TextResource(MBEntity, file_name_fmt='TextResource{locale}MB'):
    """A row in TextResource[locale]MB"""

    key = DataProperty('StringKey')
    value = DataProperty('Text')


class NamedEntity(MBEntity):
    name: str = LocalizedString('NameKey', default_to_key=True)


class FullyNamedEntity(NamedEntity):
    icon_id: int = DataProperty('IconId')
    description: str = LocalizedString('DescriptionKey', default_to_key=True)
    display_name: str = LocalizedString('DisplayName', default_to_key=True)


# endregion
