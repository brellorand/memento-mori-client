"""
Classes that wrap API responses
"""

from __future__ import annotations

import logging
from functools import cached_property

from mm.properties import DataProperty
from .base import MBEntity
from .items import ItemAndCount

__all__ = ['VipLevel', 'PlayerRank']
log = logging.getLogger(__name__)


class VipLevel(MBEntity, file_name_fmt='VipMB'):
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


class PlayerRank(MBEntity, file_name_fmt='PlayerRankMB', id_key='Rank'):
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
