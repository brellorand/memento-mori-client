"""
MB entities related to the Tower of Infinity
"""

from __future__ import annotations

import logging
from functools import cached_property

from mm.enums import TowerType
from mm.properties import DataProperty
from .base import MBEntity
from .items import ItemAndCount

__all__ = ['TowerBattleQuest']
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
