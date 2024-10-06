"""
Helpers for battle-related requests and processing of their responses
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from functools import cached_property
from typing import TYPE_CHECKING

from mm.enums import BattleFieldCharacterGroupType, TowerType
from mm.properties import DataProperty
from mm.session import mm_session

if TYPE_CHECKING:
    from mm import typing as t

__all__ = ['BattleResult', 'QuestBattleResult', 'TowerBattleResult', 'get_available_tower_types']
log = logging.getLogger(__name__)

MM_TZ = timezone(timedelta(hours=-7))
TOWER_TYPES_BY_DAY = (
    (TowerType.Blue,),  # Monday
    (TowerType.Red,),  # Tuesday
    (TowerType.Green,),  # Wednesday
    (TowerType.Yellow,),  # Thursday
    (TowerType.Blue, TowerType.Red),  # Friday
    (TowerType.Green, TowerType.Yellow),  # Saturday
    (TowerType.Blue, TowerType.Red, TowerType.Green, TowerType.Yellow),  # Sunday
)


class BattleResult:
    quest_id: int = DataProperty('QuestId')
    battle_end_info: t.BattleEndInfo = DataProperty('SimulationResult.BattleEndInfo')

    def __init__(self, data: t.BattleResult):
        self.data = data

    @cached_property
    def is_winner(self) -> bool:
        return self.battle_end_info['WinGroupType'] == BattleFieldCharacterGroupType.Attacker

    def is_winning_party(self, player_id: int) -> bool:
        return player_id in self.battle_end_info['WinPlayerIdSet']

    @cached_property
    def result_message(self) -> str:
        key = '[LocalRaidBattleWinMessage]' if self.is_winner else '[LocalRaidBattleLoseMessage]'
        return mm_session.mb.text_resource_map[key]


class QuestBattleResult:
    battle_result: BattleResult = DataProperty('BattleResult', BattleResult)

    def __init__(self, data: t.BossResponse):
        self.data = data


class TowerBattleResult:
    battle_result: BattleResult = DataProperty('BattleResult', BattleResult)

    def __init__(self, data: t.TowerBattleResponse):
        self.data = data


def get_available_tower_types() -> tuple[TowerType, ...]:
    # TODO: Handle limited all type events:
    # foreach (var limitedEventMb in LimitedEventTable.GetArray().Where(d => d.LimitedEventType == LimitedEventType.ElementTowerAllRelease)) {
    #    if (NetworkManager.TimeManager.IsInTime(limitedEventMb)) return new[] {TowerType.Infinite, TowerType.Blue, TowerType.Green, TowerType.Red, TowerType.Yellow};
    # }
    now = datetime.now(MM_TZ) - timedelta(hours=4)  # daily reset is at 4 AM UTC-7
    return TOWER_TYPES_BY_DAY[now.weekday()]
