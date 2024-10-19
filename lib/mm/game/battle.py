"""
Helpers for battle-related requests and processing of their responses
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from functools import cached_property
from typing import TYPE_CHECKING

from mm.enums import BattleFieldCharacterGroupType, TowerType
from mm.properties import DataProperty
from mm.session import mm_session

if TYPE_CHECKING:
    from pathlib import Path

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


class BattleResultWrapper:
    battle_result: BattleResult = DataProperty('BattleResult', BattleResult)

    def __init__(self, data):
        self.data = data

    def save(self, out_dir: Path, battle_identifier: str):
        if not out_dir.exists():
            out_dir.mkdir(parents=True, exist_ok=True)

        dt_str = datetime.now().strftime('%Y-%m-%d_%H.%M.%S.%f')
        result_str = 'win' if self.battle_result.is_winner else 'fail'
        path = out_dir.joinpath(f'{dt_str}__{battle_identifier}__{result_str}.json')
        log.debug(f'Saving battle results: {path.as_posix()}')
        with path.open('w', encoding='utf-8', newline='\n') as f:
            json.dump(self.data, f, indent=4)


class QuestBattleResult(BattleResultWrapper):
    data: t.BossResponse


class TowerBattleResult(BattleResultWrapper):
    data: t.TowerBattleResponse


def get_available_tower_types() -> tuple[TowerType, ...]:
    # TODO: Handle limited all type events:
    # foreach (var limitedEventMb in LimitedEventTable.GetArray().Where(d => d.LimitedEventType == LimitedEventType.ElementTowerAllRelease)) {
    #    if (NetworkManager.TimeManager.IsInTime(limitedEventMb)) return new[] {TowerType.Infinite, TowerType.Blue, TowerType.Green, TowerType.Red, TowerType.Yellow};
    # }
    now = datetime.now(MM_TZ) - timedelta(hours=4)  # daily reset is at 4 AM UTC-7
    return TOWER_TYPES_BY_DAY[now.weekday()]
