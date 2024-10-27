"""
Helpers for battle-related requests and processing of their responses
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from functools import cached_property
from typing import TYPE_CHECKING

from mm.enums import BattleFieldCharacterGroupType, TowerType
from mm.properties import DataProperty
from mm.session import mm_session
from .models import WorldEntity

if TYPE_CHECKING:
    from pathlib import Path

    from mm import typing as t
    from mm.mb_models.quest import Quest
    from mm.mb_models.tower import TowerBattleQuest

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


class BattleResult(WorldEntity):
    data: t.BattleResult
    quest_id: int = DataProperty('QuestId')
    battle_end_info: t.BattleEndInfo = DataProperty('SimulationResult.BattleEndInfo')

    @cached_property
    def is_winner(self) -> bool:
        return self.battle_end_info['WinGroupType'] == BattleFieldCharacterGroupType.Attacker

    def is_winning_party(self, player_id: int) -> bool:
        return player_id in self.battle_end_info['WinPlayerIdSet']

    @cached_property
    def result_message(self) -> str:
        key = '[LocalRaidBattleWinMessage]' if self.is_winner else '[LocalRaidBattleLoseMessage]'
        return mm_session.mb.text_resource_map[key]


class BattleResultWrapper(WorldEntity, ABC):
    @cached_property
    def battle_result(self) -> BattleResult:
        return BattleResult(self.world, self.data['BattleResult'])

    def save(self, out_dir: Path, battle_identifier: str | None = None):
        now = datetime.now()
        out_dir = out_dir.joinpath(f'W{self.world.world_num}', self.world.player_name, now.strftime('%Y-%m-%d'))
        if not out_dir.exists():
            out_dir.mkdir(parents=True, exist_ok=True)

        path = out_dir.joinpath(self._get_save_file_name(now, battle_identifier))
        log.debug(f'Saving battle results: {path.as_posix()}')
        with path.open('w', encoding='utf-8', newline='\n') as f:
            json.dump(self.data, f, indent=4)

    def _get_save_file_name(self, now: datetime, battle_identifier: str | None = None) -> str:
        parts = [now.strftime('%Y-%m-%d_%H.%M.%S.%f')]
        if battle_identifier:
            parts.append(battle_identifier)
        else:
            parts += [f'W{self.world.world_num}_{self.world.player_name}', self.save_battle_name_repr]

        parts.append('win' if self.battle_result.is_winner else 'fail')
        return '__'.join(parts) + '.json'

    @property
    @abstractmethod
    def battle(self) -> Quest | TowerBattleQuest:
        raise NotImplementedError

    @property
    @abstractmethod
    def save_battle_name_repr(self) -> str:
        raise NotImplementedError


class QuestBattleResult(BattleResultWrapper):
    data: t.BossResponse

    @cached_property
    def battle(self) -> Quest:
        return self.world.session.mb.quests[self.battle_result.quest_id]

    @property
    def save_battle_name_repr(self) -> str:
        return f'quest_{self.battle}'


class TowerBattleResult(BattleResultWrapper):
    data: t.TowerBattleResponse

    @cached_property
    def battle(self) -> TowerBattleQuest:
        return self.world.session.mb.tower_floors[self.battle_result.quest_id]

    @property
    def save_battle_name_repr(self) -> str:
        return f'{self.battle.type.snake_case}_{self.battle.floor}'


def get_available_tower_types() -> tuple[TowerType, ...]:
    # TODO: Handle limited all type events:
    # foreach (var limitedEventMb in LimitedEventTable.GetArray().Where(d => d.LimitedEventType == LimitedEventType.ElementTowerAllRelease)) {
    #    if (NetworkManager.TimeManager.IsInTime(limitedEventMb)) return new[] {TowerType.Infinite, TowerType.Blue, TowerType.Green, TowerType.Red, TowerType.Yellow};
    # }
    now = datetime.now(MM_TZ) - timedelta(hours=4)  # daily reset is at 4 AM UTC-7
    return TOWER_TYPES_BY_DAY[now.weekday()]
