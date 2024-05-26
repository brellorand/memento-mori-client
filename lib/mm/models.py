"""

"""

from __future__ import annotations

import logging
from functools import cached_property
from typing import TYPE_CHECKING, Any

from .enums import CharacterRarityFlags
from .mb_models import Character as MBCharacter, Equipment as MBEquipment
from .properties import DataProperty

if TYPE_CHECKING:
    from .account import WorldAccount

__all__ = ['WorldEntity', 'Equipment', 'Character']
log = logging.getLogger(__name__)


class WorldEntity:
    def __init__(self, world: WorldAccount, data: dict[str, Any]):
        self.world = world
        self.data = data


class Equipment(WorldEntity):
    guid: str = DataProperty('Guid')
    char_guid: str = DataProperty('CharacterGuid')
    equipment_id: int = DataProperty('EquipmentId')

    """
    TODO:
    "AdditionalParameterHealth": 0,
    "AdditionalParameterIntelligence": 0,
    "AdditionalParameterMuscle": 25,
    "AdditionalParameterEnergy": 0,
    "SphereId1": 0,
    "SphereId2": 0,
    "SphereId3": 0,
    "SphereId4": 0,
    "SphereUnlockedCount": 0,
    "LegendSacredTreasureExp": 0,
    "LegendSacredTreasureLv": 0,
    "MatchlessSacredTreasureExp": 0,
    "MatchlessSacredTreasureLv": 0,
    "ReinforcementLv": 0
    """

    @cached_property
    def equipment(self) -> MBEquipment:
        return self.world.session.mb.equipment[self.equipment_id]

    def __repr__(self) -> str:
        equip = self.equipment
        level, slot_type, rarity = equip.level, equip.slot_type, equip.rarity_flags
        guid = self.guid
        return f'<{self.__class__.__name__}[{equip.name}, {rarity=}, {level=}, {slot_type=}, {guid=}]>'


class Character(WorldEntity):
    guid: str = DataProperty('Guid')
    char_id: int = DataProperty('CharacterId')
    level: int = DataProperty('Level')
    experience: int = DataProperty('Exp')
    rarity: CharacterRarityFlags = DataProperty('RarityFlags', type=CharacterRarityFlags)

    @cached_property
    def equipment(self) -> list[Equipment]:
        return self.world.char_guid_equipment_map.get(self.guid, [])

    @cached_property
    def character(self) -> MBCharacter:
        return self.world.session.mb.characters[self.char_id]

    def __repr__(self) -> str:
        rarity, level, exp, guid = self.rarity.name, self.level, self.experience, self.guid
        return f'<{self.__class__.__name__}[{self.character.full_name}, {rarity=}, {level=}, {exp=}, {guid=}]>'