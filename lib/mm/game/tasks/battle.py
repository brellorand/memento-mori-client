"""
Tasks related to main quest and tower battles
"""

from __future__ import annotations

import logging
from abc import ABC
from functools import cached_property
from typing import TYPE_CHECKING

from mm.enums import TowerType
from ..battle import get_available_tower_types
from ..utils import wait
from .task import Task, TaskConfig

if TYPE_CHECKING:
    from pathlib import Path

    from mm.game.battle import BattleResult, QuestBattleResult, TowerBattleResult
    from mm.mb_models.quest import Quest
    from mm.typing import UserBattleBossDtoInfo, UserTowerBattleDtoInfo
    from ..session import WorldSession

__all__ = ['ClimbTower', 'QuestBattles']
log = logging.getLogger(__name__)


class BattleTask(Task, ABC):
    def __init__(
        self,
        world_session: WorldSession,
        config: TaskConfig = None,
        *,
        battle_results_dir: Path | None = None,
    ):
        super().__init__(world_session, config)
        self.total = 0
        self.successes = 0
        self.errors = 0
        self.battle_results_dir = battle_results_dir

    def can_perform(self) -> bool:
        return not self.cannot_perform_msg

    def _log_result(self, prefix: str, result: BattleResult, attempts: int, what: str):
        message = (
            f'{prefix}: {result.result_message}; {what} {attempts=},'
            f' total={self.total}, successes={self.successes}, errors={self.errors}'
        )
        log.info(message, extra={'color': 10 if result.is_winner else None})


class QuestBattles(BattleTask):
    def __init__(
        self,
        world_session: WorldSession,
        config: TaskConfig = None,
        *,
        max_quest: tuple[int, int] = None,
        stop_after: int = None,
        battle_results_dir: Path | None = None,
    ):
        super().__init__(world_session, config, battle_results_dir=battle_results_dir)
        self.max_quest = max_quest
        self.stop_after = stop_after
        self._map_info_included_others = False

    @property
    def quest_info(self) -> UserBattleBossDtoInfo:
        return self.world_session.user_sync_data.quest_status

    @property
    def _last_cleared_id(self) -> int:
        return self.quest_info['BossClearMaxQuestId']

    @property
    def _next_quest(self) -> Quest:
        return self.world_session.session.mb.quests[self._last_cleared_id + 1]

    @property
    def cannot_perform_msg(self) -> str | None:
        if self.stop_after and self.successes >= self.stop_after:
            return 'You have succeeded the configured maximum number of times'

        try:
            next_quest = self._next_quest
        except KeyError:
            return 'You have defeated the last quest boss available in the game'

        if self.max_quest and next_quest.number > self.max_quest:
            return 'You have reached the configured maximum quest'
        else:
            return None

    def before_run(self):
        self._get_map_info()

    def perform_task(self):
        if self.config.dry_run:
            log.info(f'[DRY RUN] Would challenge quest {self._next_quest}')
            return

        while self.can_perform():
            self._challenge_until_win()
            wait(self.config)
            self._get_map_info()
            self.world_session.get_next_quest_info()
            # If the next quest is the first in a chapter, use the between_tasks delay to better simulate needing
            # to click `Next Chapter` and waiting for the longer animation
            wait(self.config, between_tasks=self._next_quest.number[1] == 1)

        return self.cannot_perform_msg

    def _get_map_info(self):
        include_others = not self._map_info_included_others
        self.world_session.get_quest_map_info(include_others)
        self._map_info_included_others = include_others

    def _challenge_until_win(self):
        quest = self._next_quest
        self.world_session.get_quest_info(quest.id)

        log_prefix = f'[W{self.world_session.world_num}:{self.world_session.player_name}] Challenged quest {quest}'
        attempts = 0
        while True:
            attempts += 1
            try:
                result = self._challenge_once(quest)
            except Exception as e:
                log.error(f'{log_prefix}; error: {e}', exc_info=True)
                self.errors += 1
                if self.errors >= self.config.max_errors:
                    raise RuntimeError(f'Exceeded allowed error count while challenging quest {quest}') from e
            else:
                self._log_result(log_prefix, result, attempts, 'quest')
                if result.is_winner:
                    return

            wait(self.config)

    def _challenge_once(self, quest: Quest) -> BattleResult:
        self.total += 1

        quest_result: QuestBattleResult = self.world_session.battle_quest_boss(quest.id)
        if self.battle_results_dir:
            quest_result.save(
                self.battle_results_dir,
                f'W{self.world_session.world_num}_{self.world_session.player_name}__quest_{quest}',
            )

        result = quest_result.battle_result
        if result.is_winner:
            self.successes += 1

        return result


class ClimbTower(BattleTask):
    def __init__(
        self,
        world_session: WorldSession,
        config: TaskConfig = None,
        *,
        tower_type: TowerType = TowerType.Infinite,
        max_floor: int = None,
        battle_results_dir: Path | None = None,
    ):
        super().__init__(world_session, config, battle_results_dir=battle_results_dir)
        self.tower_type = tower_type
        self.max_floor = max_floor

    @cached_property
    def _available_tower_types(self) -> tuple[TowerType, ...]:
        return get_available_tower_types()

    @cached_property
    def _absolute_max_floor(self) -> int:
        return max(f.floor for f in self.world_session.session.mb.tower_type_floors_map[self.tower_type])

    @property
    def tower_info(self) -> UserTowerBattleDtoInfo:
        try:
            return self.world_session.user_sync_data.tower_type_status_map[self.tower_type]
        except KeyError as e:
            raise RuntimeError(f'Could not find tower info for {self.tower_type=}') from e

    @property
    def _current_floor(self) -> int:
        return self.tower_info['MaxTowerBattleId']

    @property
    def _next_floor(self) -> int:
        return self._current_floor + 1

    @property
    def cannot_perform_msg(self) -> str | None:
        if self.max_floor and self._next_floor > self.max_floor:
            return f'You have reached the configured maximum floor in the {self.tower_type.tower_name}'
        elif self._next_floor > self._absolute_max_floor:
            return f'You have reached the maximum available floor in the {self.tower_type.tower_name}'
        elif self.tower_type == TowerType.Infinite:
            return None
        elif self.tower_type not in self._available_tower_types:
            return f'The {self.tower_type.tower_name} is not available today'
        elif self.tower_info['TodayClearNewFloorCount'] >= 10:
            return f'You have reached the daily limit for {self.tower_type.tower_name} attempts'
        else:
            return None

    def perform_task(self):
        if self.config.dry_run:
            log.info(f'[DRY RUN] Would challenge the {self.tower_type.tower_name} floor {self._next_floor}')
            return

        while self.can_perform():
            self._challenge_until_win()
            wait(self.config)

        return self.cannot_perform_msg

    def _get_log_prefix(self, floor: int) -> str:
        if self.tower_type == TowerType.Infinite:
            limit = ''
        else:
            limit = f' [{self.tower_info["TodayClearNewFloorCount"]}/10]'

        ws = self.world_session
        return f'[W{ws.world_num}:{ws.player_name}] Challenged {self.tower_type.tower_name}{limit} {floor=}'

    def _challenge_until_win(self):
        self.world_session.get_tower_reward_info(self.tower_type)
        floor = self._next_floor
        attempts = 0
        while True:
            attempts += 1
            try:
                result = self._challenge_once(floor)
            except Exception as e:
                log.error(f'{self._get_log_prefix(floor)}; error: {e}', exc_info=True)
                self.errors += 1
                if self.errors >= self.config.max_errors:
                    raise RuntimeError(
                        f'Exceeded allowed error count while challenging {self.tower_type.tower_name} {floor=}'
                    ) from e
            else:
                self._log_result(self._get_log_prefix(floor), result, attempts, 'floor')
                if result.is_winner:
                    return

            wait(self.config)

    def _challenge_once(self, floor: int) -> BattleResult:
        self.total += 1

        tower_result: TowerBattleResult = self.world_session.start_tower_battle(self.tower_type, floor)
        if self.battle_results_dir:
            tower_name = self.tower_type.snake_case
            tower_result.save(
                self.battle_results_dir,
                f'W{self.world_session.world_num}_{self.world_session.player_name}__{tower_name}_{floor}',
            )

        result = tower_result.battle_result
        if result.is_winner:
            self.successes += 1

        return result
