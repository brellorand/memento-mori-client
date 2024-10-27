"""
MB entities related to the Tower of Infinity
"""

from __future__ import annotations

import logging
from functools import cached_property

from mm.enums import TowerType
from mm.properties import DataProperty
from .base import BattleEnemy, MBEntity
from .items import ItemAndCount

__all__ = ['TowerBattleQuest', 'TowerEnemy']
log = logging.getLogger(__name__)


class TowerBattleQuest(MBEntity, file_name_fmt='TowerBattleQuestMB'):
    """
    Example:
        "Id": 1,
        "IsIgnore": null,
        "Memo": "無_1",
        "BaseClearPartyDeckPower": 101846,
        "BattleRewardsConfirmed": [
            {"ItemCount": 500, "ItemId": 1, "ItemType": 11}, {"ItemCount": 800, "ItemId": 1, "ItemType": 3}
        ],
        "BattleRewardsFirst": [
            {"ItemCount": 20, "ItemId": 1, "ItemType": 1}, {"ItemCount": 5, "ItemId": 2, "ItemType": 11},
            {"ItemCount": 5, "ItemId": 27, "ItemType": 17}
        ],
        "EnemyIds": [31000101, 31000102, 31000103, 31000104, 31000105],
        "Floor": 1,
        "LotteryRewardInfoId": 1,
        "TowerType": 1
    """

    type: TowerType = DataProperty('TowerType', TowerType)
    floor: int = DataProperty('Floor')
    enemy_ids: list[int] = DataProperty('EnemyIds')  # Len will always be 5  # TODO: perform lookup

    @cached_property
    def rewards_first_try(self) -> list[ItemAndCount]:
        """List of rewards available on the first win, and their quantities"""
        return [ItemAndCount(self.mb, row) for row in self.data['BattleRewardsFirst']]

    @cached_property
    def other_rewards(self) -> list[ItemAndCount]:
        """List of rewards available on the first and subsequent wins, and their quantities"""
        return [ItemAndCount(self.mb, row) for row in self.data['BattleRewardsConfirmed']]

    @cached_property
    def enemies(self) -> list[TowerEnemy]:
        return [self.mb.tower_enemies[i] for i in self.enemy_ids]


class TowerEnemy(BattleEnemy, file_name_fmt='TowerBattleEnemyMB'):
    """
    Example:
        "Id": 31051203,
        "IsIgnore": null,
        "Memo": "無512_サブリナ",
        "ActiveSkillIds": [15001, 15002],
        "BaseParameter": {"Energy": 2311104, "Health": 2265458, "Intelligence": 2272385, "Muscle": 2574297},
        "BattleEnemyCharacterId": 10015,
        "BattleParameter": {
            "AttackPower": 3228805, "Avoidance": 1155552, "Critical": 1190052, "CriticalDamageEnhance": 0,
            "CriticalResist": 1132729, "DamageEnhance": 6600, "DamageReflect": 0, "DebuffHit": 1136192,
            "DebuffResist": 885313, "Defense": 1947702, "DefensePenetration": 4000, "Hit": 1465048, "HP": 33257477,
            "HpDrain": 0, "MagicCriticalDamageRelax": 0, "MagicDamageRelax": 3514009, "PhysicalCriticalDamageRelax": 0,
            "PhysicalDamageRelax": 3835285, "Speed": 2966
        },
        "BattlePower": 39747989,
        "CharacterRarityFlags": 1024,
        "ElementType": 2,
        "EnemyAdjustId": 30512,
        "EnemyEquipmentId": 1367,
        "ExclusiveEquipmentRarityFlags": 0,
        "EnemyRank": 366,
        "JobFlags": 1,
        "NameKey": "[CharacterName15]",
        "NormalSkillId": 101,
        "PassiveSkillIds": [15003, 15004],
        "UnitIconId": 15,
        "UnitIconType": 0
    """

    @cached_property
    def tower_type(self) -> TowerType:
        return TowerType((self.id - 30_000_000) // 1_000_000)

    @cached_property
    def floor_num(self) -> int:
        return ((self.id - 30_000_000) % 1_000_000) // 100

    @cached_property
    def tower_floor_id(self) -> int:
        if self.tower_type == TowerType.Infinite:
            return self.floor_num
        return (10_000 * self.tower_type) + self.floor_num

    @cached_property
    def tower_floor(self) -> TowerBattleQuest:
        return self.mb.tower_floors[self.tower_floor_id]
