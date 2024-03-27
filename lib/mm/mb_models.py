"""
Classes that wrap API responses
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import datetime
from functools import cached_property
from typing import TYPE_CHECKING, Any, Type, TypeVar, Iterator

from .enums import Region, Element, Job, CharacterRarity, Locale
from .data import DictWrapper
from .utils import DataProperty, DictAttrFieldNotFoundError

if TYPE_CHECKING:
    from pathlib import Path
    from .http_client import DataClient

__all__ = ['MB', 'Character']
log = logging.getLogger(__name__)

T = TypeVar('T')

RANK_BONUS_STATS = [
    'ACC', 'ACC %', 'ATK', 'Counter', 'CRIT', 'CRIT DMG Boost', 'Debuff ACC', 'DEF Break', 'DMG Boost',
    'HP', 'HP %', 'HP Drain', 'SPD',
]


class MB:
    def __init__(
        self,
        client: DataClient,
        *,
        data: dict[str, Any] = None,
        use_cached: bool = True,
        json_cache_map: dict[str, Path] = None,
        locale: Locale = 'EnUS',
    ):
        self._client = client
        self.__data = data
        self._use_cached = use_cached
        self._json_cache_map = json_cache_map or {}
        self.locale = locale

    # region Base MB data

    @cached_property
    def _data(self) -> dict[str, Any]:
        if self.__data:
            return self.__data
        return self._client._get_mb_catalog()

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
        return {name: FileInfo(data) for name, data in self._data['MasterBookInfoMap'].items()}

    # endregion

    # region File-Specific Helpers

    def get_data(self, name: str):
        if json_path := self._json_cache_map.get(name):
            return json.loads(json_path.read_text('utf-8'))
        return self._client.get_mb_data(name, use_cached=self._use_cached)

    def _iter_mb_objects(self, cls: Type[T], name: str) -> Iterator[T]:
        for row in self.get_data(name):
            yield cls(self, row)

    def _get_mb_objects(self, cls: Type[T], name: str) -> list[T]:
        return [cls(self, row) for row in self.get_data(name)]

    def _get_mb_id_obj_map(self, cls: Type[T], name: str, key: str = 'Id') -> dict[int, T]:
        return {row[key]: cls(self, row) for row in self.get_data(name)}

    # endregion

    @cached_property
    def text_resource_map(self) -> dict[str, str]:
        return {res.key: res.value for res in self._iter_mb_objects(TextResource, f'TextResource{self.locale}MB')}

    # region Items & Equipment

    def _get_typed_items(self, cls: Type[T], name: str) -> dict[int, dict[int, T]]:
        type_id_item_map = {}
        for item in self._iter_mb_objects(cls, name):
            try:
                type_id_item_map[item.item_type][item.item_id] = item
            except KeyError:
                type_id_item_map[item.item_type] = {item.item_id: item}
        return type_id_item_map

    @cached_property
    def items(self) -> dict[int, dict[int, Item]]:
        return self._get_typed_items(Item, 'ItemMB')

    @cached_property
    def change_items(self) -> dict[int, dict[int, ChangeItem]]:
        return self._get_typed_items(ChangeItem, 'ChangeItemMB')

    @cached_property
    def adamantite(self) -> dict[int, EquipmentSetMaterial]:
        return self._get_mb_id_obj_map(EquipmentSetMaterial, 'EquipmentSetMaterialMB')

    def get_item(self, item_type: int, item_id: int) -> Item | EquipmentPart | EquipmentSetMaterial:
        # ItemType=3: Gold
        # ItemType=5: object parts for a given slot/set
        # ItemType=9: Adamantite material for a given slot/level
        if type_group := self.items.get(item_type):
            return type_group[item_id]
        elif item_type == 5:
            return self.equipment_parts[item_id]
        elif item_type == 9:
            return self.adamantite[item_id]
        raise KeyError(f'Unable to find item with {item_type=}, {item_id=}')

    @cached_property
    def equipment(self) -> dict[int, Equipment]:
        return self._get_mb_id_obj_map(Equipment, 'EquipmentMB')

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
    def equipment_enhance_requirements(self) -> dict[int, EquipmentEnhanceRequirements]:
        return self._get_mb_id_obj_map(EquipmentEnhanceRequirements, 'EquipmentEvolutionMB')

    @cached_property
    def _equipment_upgrade_requirements(self) -> dict[int, EquipmentUpgradeRequirements]:
        return self._get_mb_id_obj_map(EquipmentUpgradeRequirements, 'EquipmentReinforcementMaterialMB')

    @cached_property
    def weapon_upgrade_requirements(self) -> EquipmentUpgradeRequirements:
        return self._equipment_upgrade_requirements[1]

    @cached_property
    def armor_upgrade_requirements(self) -> EquipmentUpgradeRequirements:
        return self._equipment_upgrade_requirements[2]

    # endregion

    @cached_property
    def world_groups(self) -> list[WorldGroup]:
        return self._get_mb_objects(WorldGroup, 'WorldGroupMB')

    # region Player Attributes

    @cached_property
    def vip_levels(self) -> list[VipLevel]:
        return self._get_mb_objects(VipLevel, 'VipMB')

    @cached_property
    def player_ranks(self) -> dict[int, PlayerRank]:
        return self._get_mb_id_obj_map(PlayerRank, 'PlayerRankMB', key='Rank')

    # endregion

    @cached_property
    def characters(self) -> dict[int, Character]:
        return self._get_mb_id_obj_map(Character, 'CharacterMB')


class FileInfo(DictWrapper):
    hash: str = DataProperty('Hash')
    name: str = DataProperty('Name')
    size: int = DataProperty('Size', int)


def _parse_dt(dt_str: str) -> datetime:
    return datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')


# region Generic / Base Entity Classes


class MBEntity:
    __slots__ = ('data', 'mb')

    id: int = DataProperty('Id')
    ignore: bool = DataProperty('IsIgnore', default=False)

    def __init__(self, mb: MB, data: dict[str, Any]):
        self.mb = mb
        self.data = data

    def __repr__(self) -> str:
        attrs = ('full_name', 'name', 'id')
        key, val = next((attr, v) for attr in attrs if (v := getattr(self, attr, None)) is not None)
        return f'<{self.__class__.__name__}[{key}={val!r}]>'


class TextResource(MBEntity):
    """A row in TextResource[locale]MB"""

    key = DataProperty('StringKey')
    value = DataProperty('Text')


class NamedEntity(MBEntity):
    name_key = DataProperty('NameKey')  # matches a TextResource.key (StringKey) value

    @cached_property
    def name(self) -> str:
        return self.mb.text_resource_map.get(self.name_key, self.name_key)


class FullyNamedEntity(NamedEntity):
    icon_id: int = DataProperty('IconId')
    description_key = DataProperty('DescriptionKey')  # matches a TextResource.key (StringKey) value
    display_name_key = DataProperty('DisplayName')  # matches a TextResource.key (StringKey) value

    @cached_property
    def display_name(self) -> str:
        return self.mb.text_resource_map.get(self.display_name_key, self.display_name_key)

    @cached_property
    def description(self) -> str:
        return self.mb.text_resource_map.get(self.description_key, self.description_key)


# endregion


# region Items & Equipment


class TypedItem:
    item_id: int = DataProperty('ItemId')
    item_type: int = DataProperty('ItemType')


class Item(TypedItem, FullyNamedEntity):
    """
    Represents a row in ItemMB

    Example content:
        "Id": 1,
        "IsIgnore": null,
        "Memo": "ダイヤ（無償）",
        "DescriptionKey": "[ItemDescription1]",
        "DisplayName": "[ItemDisplayName1]",
        "EndTime": null,
        "ItemId": 1,
        "ItemRarityFlags": 0,
        "ItemType": 1,
        "MaxItemCount": 0,
        "NameKey": "[ItemName1]",
        "IconId": 9,
        "SecondaryFrameNum": 0,
        "SecondaryFrameType": 0,
        "SortOrder": 0,
        "StartTime": null,
        "TransferSpotId": 0
    """


class ItemAndCount(MBEntity):
    """A row in a list of reward/required items"""

    item_type: int = DataProperty('ItemType')
    item_id: int = DataProperty('ItemId')
    count: int = DataProperty('ItemCount')

    @cached_property
    def item(self) -> Item | TypedItem:
        return self.mb.get_item(self.item_type, self.item_id)

    def __str__(self) -> str:
        item = self.item
        try:
            name = item.display_name
        except (AttributeError, DictAttrFieldNotFoundError):
            try:
                name = item.name
            except (AttributeError, DictAttrFieldNotFoundError):
                name = f'item_type={item.item_type}, item_id={item.item_id}'

        return f'{name} x {self.count:,d}'


class EquipmentSetMaterial(FullyNamedEntity):
    """
    Represents an entry in ``EquipmentSetMaterialMB`` (an Adamantite material).

    Example content:
        "Id": 2,
        "IsIgnore": null,
        "Memo": "220剣",
        "DescriptionKey": "[EquipmentSetMaterialDescription2]",
        "IconId": 1,
        "ItemRarityFlags": 64,
        "Lv": 220,
        "NameKey": "[EquipmentSetMaterialNameSword]",
        "DisplayNameKey": "[EquipmentSlotTypeSword]",
        "QuestIdList": [364, 365, 366, 367, 392, 393, 394, 395]
    """

    level: int = DataProperty('Lv')

    @cached_property
    def display_name(self) -> str:
        return f'Lv {self.level} {self.name}'


class ChangeItem(TypedItem, MBEntity):
    """
    Represents an entry in ``ChangeItemMB``.  Most entries appear to be related to Adamantite materials.
    """

    change_item_type: int = DataProperty('ChangeItemType')
    need_count: int = DataProperty('NeedCount')

    @cached_property
    def change_items(self) -> list[ItemAndCount]:
        return [ItemAndCount(self.mb, ic) for ic in self.data['ChangeItems']]


class EquipmentPart(TypedItem, MBEntity):
    """Pseudo MBEntity that represents parts of upgradable equipment."""

    def __init__(self, mb: MB, equipment: Equipment):
        super().__init__(mb, {'Id': equipment.part_id, 'ItemType': 5})
        self.equipment = equipment
        self.name = f'{equipment.name} Parts'


class Equipment(NamedEntity):
    """
    Represents a row in EquipmentMB

    Example content:
        "Id": 529,
        "IsIgnore": null,
        "Memo": "R180_剣",
        "AdditionalParameterTotal": 32603,
        "AfterLevelEvolutionEquipmentId": 530,
        "AfterRarityEvolutionEquipmentId": 0,
        "BattleParameterChangeInfo": {"BattleParameterType": 2, "ChangeParameterType": 1, "Value": 26024.0},
        "Category": 2,
        "CompositeId": 1,
        "EquipmentEvolutionId": 3,
        "EquipmentExclusiveSkillDescriptionId": 0,
        "EquipmentForgeId": 0,
        "EquipmentLv": 180,
        "EquipmentReinforcementMaterialId": 1,
        "EquipmentSetId": 1,
        "EquippedJobFlags": 1,
        "ExclusiveEffectId": 0,
        "GoldRequiredToOpeningFirstSphereSlot": 26000,
        "GoldRequiredToTraining": 25000,
        "IconId": 89,
        "NameKey": "[EquipmentName89]",
        "PerformancePoint": 133555,
        "QualityLv": 1,
        "RarityFlags": 32,
        "SlotType": 1
    """

    level: int = DataProperty('EquipmentLv')
    set_id: int = DataProperty('EquipmentSetId')
    part_id: int = DataProperty('CompositeId')  # ID for this item's part (ItemType=5)
    enhance_id: int = DataProperty('EquipmentEvolutionId')

    slot_type: int = DataProperty('SlotType')
    effect_id: int = DataProperty('ExclusiveEffectId')
    icon_id: int = DataProperty('IconId')
    quality_level: int = DataProperty('QualityLv')  # Likely enum for SR/SSR/UR/LR?
    job_flags: int = DataProperty('EquippedJobFlags')
    rarity_flags: int = DataProperty('RarityFlags')
    after_level_enhance_id: int = DataProperty('AfterLevelEvolutionEquipmentId')
    after_rarity_enhance_id: int = DataProperty('AfterRarityEvolutionEquipmentId')
    category: int = DataProperty('Category')
    exclusive_skill_desc_id: int = DataProperty('EquipmentExclusiveSkillDescriptionId')
    forge_id: int = DataProperty('EquipmentForgeId')
    reinforce_material_id: int = DataProperty('EquipmentReinforcementMaterialId')
    additional_param_total: int = DataProperty('AdditionalParameterTotal')
    performance_point: int = DataProperty('PerformancePoint')
    first_rune_slot_cost: int = DataProperty('GoldRequiredToOpeningFirstSphereSlot')
    subsequent_rune_slot_cost: int = DataProperty('GoldRequiredToTraining')  # This name is a guess

    @cached_property
    def enhance_requirements(self) -> EquipmentEnhancement | None:
        try:
            return self.mb.equipment_enhance_requirements[self.enhance_id].level_enhancement_map[self.level]
        except KeyError:
            return None

    @cached_property
    def upgrade_requirements(self) -> EquipmentUpgradeRequirements:
        return self.mb.weapon_upgrade_requirements if self.slot_type == 1 else self.mb.armor_upgrade_requirements


class EquipmentUpgradeRequirements(MBEntity):
    """
    Represents a "row" (which contains many other rows of data) in ``EquipmentReinforcementMaterialMB``.  There are
    only two rows/entries at the top level - Id=1 contains upgrade requirements for weapons, and Id=2 contains upgrade
    requirements for armor.
    """

    @cached_property
    def level_required_items_map(self) -> dict[int, list[ItemAndCount]]:
        return {
            row['Lv']: [ItemAndCount(self.mb, ic) for ic in row['RequiredItemList']]
            for row in self.data['ReinforcementMap']
        }


class EquipmentEnhancement(MBEntity):
    """
    Represents a row in the ``EquipmentEvolutionInfoList`` for a given :class:`EquipmentEnhanceRequirements` object.
    """

    rarity_flags: int = DataProperty('RarityFlags')
    from_level: int = DataProperty('BeforeEquipmentLv')
    to_level: int = DataProperty('AfterEquipmentLv')

    @cached_property
    def required_items(self) -> list[ItemAndCount]:
        return [ItemAndCount(self.mb, ic) for ic in self.data['RequiredItemList']]


class EquipmentEnhanceRequirements(MBEntity):
    """Represents a row in ``EquipmentEvolutionMB``."""

    @cached_property
    def level_enhancement_map(self) -> dict[int, EquipmentEnhancement]:
        return {
            row['BeforeEquipmentLv']: EquipmentEnhancement(self.mb, row)
            for row in self.data['EquipmentEvolutionInfoList']
        }


# endregion


# region Player Attributes


class VipLevel(MBEntity):
    """
    Example:
        "Id": 1,
        "IsIgnore": null,
        "Memo": null,
        "AutoBattlePlayerExpBonus": 0,
        "DailyRewardItemList": [
            {"ItemCount": 1, "ItemId": 1, "ItemType": 19}, {"ItemCount": 5000, "ItemId": 1, "ItemType": 3}
        ],
        "DungeonBattleCoinBonus": 0,
        "DungeonBattleGoldBonus": 0,
        "DungeonBattleMissedCompensationCount": 0,
        "IsDestinyGachaAvailable": false,
        "IsDestinyGachaLogAvailable": false,
        "IsStarsGuidanceGachaAvailable": false,
        "IsStarsGuidanceGachaLogAvailable": false,
        "IsLockEquipmentTrainingAvailable": false,
        "IsMultipleBountyQuestAvailable": false,
        "IsMultipleQuickStartGuildRaidAvailable": false,
        "IsQuickBossBattleAvailable": false,
        "IsQuickStartGuildRaidAvailable": false,
        "IsRefundEquipmentMergeAvailable": false,
        "LoginBonusMissedCompensationCount": 0,
        "Lv": 0,
        "MaxBossBattleUseCurrencyCount": 1,
        "MaxCharacterBoxPlus": 0,
        "MaxGuildRaidChallengeCount": 2,
        "MaxQuickUseCurrencyCount": 2,
        "MaxShopItemCountPlus": 0,
        "MaxSoloQuestCount": 6,
        "MaxTeamQuestCount": 1,
        "QuickBattlePlayerExpBonus": 0,
        "ReachRewardItemList": null,
        "RequiredExp": 0,
        "VipGiftInfoList": [
            {
                "GetItemList": [{"ItemCount": 10, "ItemId": 4, "ItemType": 13}],
                "RequiredItemList": [{"ItemCount": 50, "ItemId": 1, "ItemType": 1}],
                "VipGiftId": 0
            }
        ]
    """

    level: int = DataProperty('Lv')

    @cached_property
    def daily_rewards(self) -> list[ItemAndCount]:
        """List of daily item rewards and their quantities"""
        return [ItemAndCount(self.mb, row) for row in self.data['DailyRewardItemList']]


class PlayerRank(MBEntity):
    """
    Example:
        "Id": 1,
        "IsIgnore": null,
        "Memo": null,
        "AttackPowerBonus": 0,
        "CriticalBonus": 0,
        "CriticalDamageEnhanceBonus": 0,
        "DamageEnhanceBonus": 0,
        "DamageReflectBonus": 0,
        "DebuffHitBonus": 0,
        "DefensePenetrationBonus": 0,
        "HitBonus": 0,
        "HpBonus": 0,
        "HpPercentBonus": 0,
        "HpDrainBonus": 0,
        "HitDirectPercentBonus": 0,
        "LevelLinkMemberMaxCount": 0,
        "Rank": 1,
        "RequiredTotalExp": 0,
        "StartTimeFixJST": "2020-01-01 00:00:00",
        "SpeedBonus": 0
    """

    rank: int = DataProperty('Rank')
    level_link_slots: int = DataProperty('LevelLinkMemberMaxCount')

    accuracy_bonus: int = DataProperty('HitBonus')
    accuracy_percent_bonus: int = DataProperty('HitDirectPercentBonus')  # Not sure about name; no present values > 0
    attack_bonus: int = DataProperty('AttackPowerBonus')
    counter_bonus: int = DataProperty('DamageReflectBonus')  # Not sure about name
    crit_rate_bonus: int = DataProperty('CriticalBonus')
    crit_damage_bonus: int = DataProperty('CriticalDamageEnhanceBonus')
    damage_bonus: int = DataProperty('DamageEnhanceBonus')
    debuff_accuracy_bonus: int = DataProperty('DebuffHitBonus')
    def_break_bonus: int = DataProperty('DefensePenetrationBonus')
    hp_bonus: int = DataProperty('HpBonus')
    hp_percent_bonus: int = DataProperty('HpPercentBonus', type=lambda v: v // 100)
    hp_drain_bonus: int = DataProperty('HpDrainBonus')
    speed_bonus: int = DataProperty('SpeedBonus')

    def get_stat_bonuses(self) -> dict[str, int]:
        # As of 2024-02-26, only ATK, HP, and HP % bonuses have any non-zero values for any given rank
        return {
            'ACC': self.accuracy_bonus,
            'ACC %': self.accuracy_percent_bonus,
            'ATK': self.attack_bonus,
            'Counter': self.counter_bonus,
            'CRIT': self.crit_rate_bonus,
            'CRIT DMG Boost': self.crit_damage_bonus,
            'Debuff ACC': self.debuff_accuracy_bonus,
            'DEF Break': self.def_break_bonus,
            'DMG Boost': self.damage_bonus,  # Is this key accurate? This does stat not appear in help text
            'HP': self.hp_bonus,
            'HP %': self.hp_percent_bonus,
            'HP Drain': self.hp_drain_bonus,
            'SPD': self.speed_bonus,
        }


# endregion


# region Misc


class WorldGroup(MBEntity):
    """
    Represents a row in WorldGroupMB

    Example content:
        "Id": 23,
        "IsIgnore": null,
        "Memo": "us",
        "EndTime": "2100-01-01 00:00:00",
        "EndLegendLeagueDateTime": "2100-01-01 00:00:00",
        "TimeServerId": 4,
        "StartTime": "2023-08-08 04:00:00",
        "GrandBattleDateTimeList": [
            {"EndTime": "2023-08-28 03:59:59", "StartTime": "2023-08-21 04:00:00"},
            ...
            {"EndTime": "2024-02-19 03:59:59", "StartTime": "2024-02-12 04:00:00"}
        ],
        "StartLegendLeagueDateTime": "2023-09-05 04:00:00",
        "WorldIdList": [4001, 4002, 4003, 4004, 4005, 4006, 4007, 4008]
    """

    region: Region = DataProperty('TimeServerId', type=Region)
    first_legend_league_dt: datetime = DataProperty('StartLegendLeagueDateTime', type=_parse_dt)
    world_ids: list[int] = DataProperty('WorldIdList')

    @cached_property
    def grand_battles(self) -> list[tuple[datetime, datetime]]:
        return [
            (_parse_dt(row['StartTime']), _parse_dt(row['EndTime']))
            for row in self.data['GrandBattleDateTimeList']
        ]


# endregion


class Character(MBEntity):
    """
    Example:
        "Id": 43,
        "IsIgnore": null,
        "Memo": "【雷啼の魔女】ケルベロス",
        "ActiveSkillIds": [43001, 43002],
        "BaseParameterCoefficient": {"Energy": 83, "Health": 69, "Intelligence": 86, "Muscle": 100},
        "BaseParameterGrossCoefficient": 338,
        "CharacterType": 1,
        "ElementType": 5,
        "InitialBattleParameter": {
            "AttackPower": 0, "Avoidance": 0, "Critical": 0, "CriticalDamageEnhance": 0, "CriticalResist": 0,
            "DamageEnhance": 0, "DamageReflect": 0, "DebuffHit": 0, "DebuffResist": 0, "Defense": 10,
            "DefensePenetration": 0, "Hit": 0, "HP": 0, "HpDrain": 0, "MagicCriticalDamageRelax": 0,
            "MagicDamageRelax": 0, "PhysicalCriticalDamageRelax": 0, "PhysicalDamageRelax": 0, "Speed": 3363
        },
        "ItemRarityFlags": 64,
        "JobFlags": 1,
        "Name2Key": "[CharacterSubName43]",
        "NameKey": "[CharacterName43]",
        "NormalSkillId": 101,
        "PassiveSkillIds": [43003, 43004],
        "RarityFlags": 8,
        "RequireFragmentCount": 60,
        "EndTimeFixJST": "2100-12-31 23:59:59",
        "StartTimeFixJST": "2023-01-17 15:00:00"
    """

    name_key = DataProperty('NameKey')          # matches a TextResource.key (StringKey) value
    sub_name_key = DataProperty('Name2Key')     # matches a TextResource.key (StringKey) value
    type_id: int = DataProperty('CharacterType')  # 0 (56 matches), 1 (11), or 2 (7); not clear what this indicates
    element: Element = DataProperty('ElementType', Element)

    job: Job = DataProperty('JobFlags', Job)
    rarity: CharacterRarity = DataProperty('RarityFlags', CharacterRarity)
    item_rarity_flags: int = DataProperty('ItemRarityFlags')  # Seems to always correlate with rarity

    normal_skill_id: int = DataProperty('NormalSkillId')
    active_skill_ids: list[int] = DataProperty('ActiveSkillIds')
    passive_skill_ids: list[int] = DataProperty('PassiveSkillIds')

    speed: int = DataProperty('InitialBattleParameter.Speed')

    def __repr__(self) -> str:
        name, element, job = self.full_name, self.element.name.title(), self.job.name.title()
        return f'<{self.__class__.__name__}[id={self.full_id!r}, {name=}, {element=}, {job=}]>'

    @cached_property
    def full_id(self) -> str:
        return f'CHR_{self.id:06d}'

    @cached_property
    def name(self) -> str:
        return self.mb.text_resource_map[self.name_key]

    @cached_property
    def sub_name(self) -> None:
        return self.mb.text_resource_map.get(self.sub_name_key)

    @cached_property
    def full_name(self) -> str:
        return f'{self.name} ({self.sub_name})' if self.sub_name else self.name

    def get_summary(self) -> dict[str, Any]:
        return {
            # 'id': self.full_id,
            'name': self.full_name,
            'type': self.type_id,
            'element': self.element.name.title(),
            'job': self.job.name.title(),
            'rarity': self.rarity.name,
            # 'item_rarity': self.item_rarity_flags,
        }
