"""
Classes that wrap API responses
"""

from __future__ import annotations

import logging
from functools import cached_property

from mm.properties import DataProperty, DictAttrFieldNotFoundError
from .base import MB, MBEntity, NamedEntity, FullyNamedEntity

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
    item_id: int = DataProperty('ItemId')
    item_type: int = DataProperty('ItemType')


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


class EquipmentSetMaterial(FullyNamedEntity, file_name_fmt='EquipmentSetMaterialMB'):
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


class ChangeItem(TypedItem, MBEntity, file_name_fmt='ChangeItemMB'):
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


class Equipment(NamedEntity, file_name_fmt='EquipmentMB'):
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
            return self.mb.equipment_enhance_reqs[self.enhance_id].level_enhancement_map[self.level]
        except KeyError:
            return None

    @cached_property
    def upgrade_requirements(self) -> EquipmentUpgradeRequirements:
        return self.mb.weapon_upgrade_requirements if self.slot_type == 1 else self.mb.armor_upgrade_requirements


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
