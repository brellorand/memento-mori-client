"""
MB entities related to the main quest bosses / battles
"""

from __future__ import annotations

import logging
from functools import cached_property

from mm.properties import DataProperty
from .base import BattleEnemy, MBEntity

__all__ = ['Quest', 'QuestEnemy']
log = logging.getLogger(__name__)


class Quest(MBEntity, file_name_fmt='QuestMB'):
    """
    Example:
        "Id": 484,
        "IsIgnore": null,
        "Memo": "19-8",
        "BaseBattlePower": 109583916,
        "ChapterId": 19,
        "GoldPerMinute": 333,
        "MinCharacterExp": 156468,
        "MinPlayerExp": 107328,
        "PotentialJewelPerDay": 1042,
        "Population": 22133728,
        "QuestDifficultyType": 1,
        "QuestMapBuildingId": 103
    """

    chapter: int = DataProperty('ChapterId')
    memo: str = DataProperty('Memo')

    @cached_property
    def number(self) -> tuple[int, int]:
        chapter, num = self.memo.split('-', 1)
        return (int(chapter), int(num))

    @cached_property
    def enemies(self) -> list[QuestEnemy]:
        return self.mb.quest_id_enemies_map[self.id]

    def __str__(self) -> str:
        return self.memo

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}({self.memo!r}, id={self.id})>'


class QuestEnemy(BattleEnemy, file_name_fmt='BossBattleEnemyMB'):
    """
    Example:
        "Id": 20045601,
        "IsIgnore": null,
        "Memo": "18-8_メルティーユ",
        "ActiveSkillIds": [5504029001, 5504029002],
        "BaseParameter": {"Energy": 1044400, "Health": 1148261, "Intelligence": 1054805, "Muscle": 932989},
        "BattleParameter": {
            "AttackPower": 1880075, "Avoidance": 522201, "Critical": 539510, "CriticalDamageEnhance": 24,
            "CriticalResist": 574130, "DamageEnhance": 3900, "DamageReflect": 0, "DebuffHit": 527402,
            "DebuffResist": 346289, "Defense": 836151, "DefensePenetration": 5040, "Hit": 555595, "HP": 8713136,
            "HpDrain": 8, "MagicCriticalDamageRelax": 24, "MagicDamageRelax": 1692389,
            "PhysicalCriticalDamageRelax": 23, "PhysicalDamageRelax": 1546206, "Speed": 2796
        },
        "BattlePower": 13061055,
        "CharacterRarityFlags": 512,
        "ElementType": 3,
        "EnemyAdjustId": 20045601,
        "BattleEnemyCharacterId": 10029,
        "EnemyEquipmentId": 4260,
        "ExclusiveEquipmentRarityFlags": 0,
        "EnemyRank": 259,
        "JobFlags": 4,
        "NameKey": "[CharacterName29]",
        "NormalSkillId": 102,
        "PassiveSkillIds": [5504029003, 5504029004, 5500000001],
        "UnitIconId": 29,
        "UnitIconType": 0
    """

    @cached_property
    def quest_id(self) -> int:
        return (self.id - 20_000_000) // 100

    @cached_property
    def quest(self) -> Quest:
        return self.mb.quests[self.quest_id]
