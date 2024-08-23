"""
Classes that wrap API responses
"""

from __future__ import annotations

import logging
from functools import cached_property
from typing import TYPE_CHECKING

from mm.enums import (
    EquipmentSlotType,
    EquipmentRarityFlags,
    Job,
    EquipmentCategory,
    ItemType,
    SphereType,
    BaseParameterType,
    ChangeParameterType,
    EquipmentType,
)
from mm.properties import DataProperty, DictAttrFieldNotFoundError
from .base import MB, MBEntity, NamedEntity, FullyNamedEntity
from .utils import LocalizedString

if TYPE_CHECKING:
    from .characters import Character

__all__ = [
    'Item',
    'EquipmentSetMaterial',
    'ChangeItem',
    'EquipmentPart',
    'Equipment',
    'EquipmentUpgradeRequirements',
    'EquipmentEnhancement',
    'EquipmentEnhanceRequirements',
]
log = logging.getLogger(__name__)


class TypedItem:
    _item_type: ItemType = None
    _item_type_cls_map = {}
    item_type: ItemType

    def __init_subclass__(cls, item_type: ItemType = None, **kwargs):
        super().__init_subclass__(**kwargs)
        if item_type is not None:
            cls._item_type = item_type
            cls._item_type_cls_map[item_type] = cls
            cls.item_type = DataProperty('ItemType', ItemType, default=item_type)  # noqa
        else:
            cls.item_type = DataProperty('ItemType', ItemType)  # noqa

        cls.item_type.name = 'item_type'

    @classmethod
    def get_type_class(cls, item_type: ItemType):
        return cls._item_type_cls_map.get(item_type, Item)

    @cached_property
    def item_id(self) -> int:
        try:
            return self.data['ItemId']  # noqa
        except KeyError:
            return self.data['Id']  # noqa


class Item(TypedItem, FullyNamedEntity, file_name_fmt='ItemMB'):
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

    item_type: ItemType = DataProperty('ItemType', ItemType)
    item_id: int = DataProperty('ItemId')
    count: int = DataProperty('ItemCount')

    @cached_property
    def item(self) -> AnyItem:
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


class EquipmentSetMaterial(
    TypedItem, FullyNamedEntity, file_name_fmt='EquipmentSetMaterialMB', item_type=ItemType.EquipmentSetMaterial
):
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


class ChangeItem(TypedItem, MBEntity, file_name_fmt='ChangeItemMB'):  # Each entry has its own type
    """
    Represents an entry in ``ChangeItemMB``.  Most entries appear to be related to Adamantite materials.
    """

    change_item_type: int = DataProperty('ChangeItemType')
    need_count: int = DataProperty('NeedCount')

    @cached_property
    def change_items(self) -> list[ItemAndCount]:
        return [ItemAndCount(self.mb, ic) for ic in self.data['ChangeItems']]


class EquipmentPart(TypedItem, MBEntity, item_type=ItemType.EquipmentFragment):
    """Pseudo MBEntity that represents parts of upgradable equipment."""

    def __init__(self, mb: MB, equipment: Equipment):
        super().__init__(mb, {'Id': equipment.part_id, 'ItemType': 5})
        self.equipment = equipment
        self.name = f'{equipment.name} Parts'


class Equipment(TypedItem, NamedEntity, file_name_fmt='EquipmentMB', item_type=ItemType.Equipment):
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
    category: EquipmentCategory = DataProperty('Category', EquipmentCategory)

    slot_type: EquipmentSlotType = DataProperty('SlotType', EquipmentSlotType)
    job_flags: Job = DataProperty('EquippedJobFlags', Job)
    rarity_flags: EquipmentRarityFlags = DataProperty('RarityFlags', EquipmentRarityFlags)
    quality_level: int = DataProperty('QualityLv')  # 0 for normal, 1 for S+ (with the additional icon in the corner)

    additional_param_total: int = DataProperty('AdditionalParameterTotal')
    performance_point: int = DataProperty('PerformancePoint')
    first_rune_slot_cost: int = DataProperty('GoldRequiredToOpeningFirstSphereSlot')
    subsequent_rune_slot_cost: int = DataProperty('GoldRequiredToTraining')  # This name is a guess

    icon_id: int = DataProperty('IconId')
    forge_id: int = DataProperty('EquipmentForgeId')
    effect_id: int = DataProperty('ExclusiveEffectId')
    after_level_enhance_id: int = DataProperty('AfterLevelEvolutionEquipmentId')
    after_rarity_enhance_id: int = DataProperty('AfterRarityEvolutionEquipmentId')
    exclusive_skill_desc_id: int = DataProperty('EquipmentExclusiveSkillDescriptionId')
    reinforce_material_id: int = DataProperty('EquipmentReinforcementMaterialId')

    @cached_property
    def gear_type(self) -> EquipmentType:
        return EquipmentType.for_slot_and_job(self.slot_type, self.job_flags)

    @cached_property
    def enhance_requirements(self) -> EquipmentEnhancement | None:
        try:
            return self.mb.equipment_enhance_reqs[self.enhance_id].level_enhancement_map[self.level]
        except KeyError:
            return None

    @cached_property
    def upgrade_requirements(self) -> EquipmentUpgradeRequirements:
        return self.mb.weapon_upgrade_requirements if self.slot_type == 1 else self.mb.armor_upgrade_requirements

    def __repr__(self) -> str:
        attrs = ('full_name', 'name', 'id')
        key, val = next((attr, v) for attr in attrs if (v := getattr(self, attr, None)) is not None)
        rarity = self.rarity_flags.name
        if self.rarity_flags == EquipmentRarityFlags.S and self.quality_level:
            rarity += '+'
        return f'<{self.__class__.__name__}[{key}={val!r}, slot={self.gear_type}, {rarity=!s}, level={self.level}]>'


class EquipmentUpgradeRequirements(MBEntity, file_name_fmt='EquipmentReinforcementMaterialMB'):
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


class EquipmentEnhancement(MBEntity, file_name_fmt='EquipmentEvolutionInfoList'):
    """
    Represents a row in the ``EquipmentEvolutionInfoList`` for a given :class:`EquipmentEnhanceRequirements` object.
    """

    rarity_flags: int = DataProperty('RarityFlags')
    from_level: int = DataProperty('BeforeEquipmentLv')
    to_level: int = DataProperty('AfterEquipmentLv')

    @cached_property
    def required_items(self) -> list[ItemAndCount]:
        return [ItemAndCount(self.mb, ic) for ic in self.data['RequiredItemList']]


class EquipmentEnhanceRequirements(MBEntity, file_name_fmt='EquipmentEvolutionMB'):
    """Represents a row in ``EquipmentEvolutionMB``."""

    @cached_property
    def level_enhancement_map(self) -> dict[int, EquipmentEnhancement]:
        return {
            row['BeforeEquipmentLv']: EquipmentEnhancement(self.mb, row)
            for row in self.data['EquipmentEvolutionInfoList']
        }


class Rune(TypedItem, NamedEntity, file_name_fmt='SphereMB', item_type=ItemType.Rune):
    """
    Example:
        "Id": 15,
        "IsIgnore": null,
        "Memo": "腕力Lv15",
        "BaseParameterChangeInfo": {"BaseParameterType": 1, "ChangeParameterType": 1, "Value": 250000.0},
        "BattleParameterChangeInfo": null,
        "CategoryId": 1,
        "DescriptionKey": "[SphereDescription1]",
        "IsAttackType": true,
        "ItemListRequiredToCombine": [{"ItemCount": 99999, "ItemId": 1, "ItemType": 1}],
        "Lv": 15,
        "NameKey": "[SphereName1]",
        "RarityFlags": 256,
        "SphereType": 3
    """

    level: int = DataProperty('Lv')
    description: str = LocalizedString('DescriptionKey', default_to_key=True)
    rarity_flags: EquipmentRarityFlags = DataProperty('RarityFlags', EquipmentRarityFlags)
    sphere_type: SphereType = DataProperty('SphereType', SphereType)
    is_attack_type: bool = DataProperty('IsAttackType')  # Offensive (as opposed to defensive)

    param_type: BaseParameterType = DataProperty('BaseParameterChangeInfo.BaseParameterType', BaseParameterType)
    change_type: ChangeParameterType = DataProperty('BaseParameterChangeInfo.ChangeParameterType', ChangeParameterType)
    change_amount: float = DataProperty('BaseParameterChangeInfo.Value')

    category_id: int = DataProperty('CategoryId')

    @cached_property
    def display_name(self) -> str:
        return f'Lv {self.level} {self.name}'


class TreasureChest(TypedItem, FullyNamedEntity, file_name_fmt='TreasureChestMB', item_type=ItemType.TreasureChest):
    """
    Represents a row in ``TreasureChestMB``.

    Note: TreasureChestItemMB appears to contain reward info for each of these
    """

    display_name: str = LocalizedString('DisplayNameKey', default_to_key=True)
    rarity_flags: EquipmentRarityFlags = DataProperty('ItemRarityFlags', EquipmentRarityFlags)
    key_item_id: int = DataProperty('ChestKeyItemId')  # Very few rows have this; I assume `0` means no key is needed

    @cached_property
    def key(self) -> Item | None:
        if self.key_item_id == 0:
            return None
        return self.mb.get_item(ItemType.TreasureChestKey, self.key_item_id)


class CharacterFragment(TypedItem, MBEntity, item_type=ItemType.CharacterFragment):
    """Pseudo MBEntity that represents character fragments."""

    def __init__(self, mb: MB, character: Character):
        # TODO: Confirm whether this is accurate
        super().__init__(mb, {'Id': character.id, 'ItemType': 7})
        self.character = character
        self.name = f'{character.full_name} Parts'


AnyItem = Item | Equipment | EquipmentPart | EquipmentSetMaterial | Rune | TreasureChest | CharacterFragment
