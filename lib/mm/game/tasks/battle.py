"""
Tasks related to main quest and tower battles
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from functools import cached_property
from typing import TYPE_CHECKING

from mm.enums import TowerType
from ..battle import BattleResultWrapper, get_available_tower_types
from ..utils import wait
from .task import Task, TaskConfig

if TYPE_CHECKING:
    from pathlib import Path

    from mm.game.battle import BattleResult, QuestBattleResult, TowerBattleResult
    from mm.mb_models.quest import Quest
    from mm.mb_models.tower import TowerBattleQuest
    from mm.typing import UserBattleBossDtoInfo, UserTowerBattleDtoInfo
    from ..session import WorldSession

__all__ = ['ClimbTower', 'QuestBattles']
log = logging.getLogger(__name__)


class BattleTask(Task, ABC):
    battle_type: str

    def __init_subclass__(cls, battle_type: str, **kwargs):  # noqa
        super().__init_subclass__(**kwargs)
        cls.battle_type = battle_type

    def __init__(
        self,
        world_session: WorldSession,
        config: TaskConfig = None,
        *,
        battle_results_dir: Path | None = None,
        show_enemies: bool = True,
    ):
        super().__init__(world_session, config)
        self.total = 0
        self.successes = 0
        self.errors = 0
        self.battle_results_dir = battle_results_dir
        self.show_enemies = show_enemies

    def can_perform(self) -> bool:
        return not self.cannot_perform_msg

    def perform_task(self):
        if self.config.dry_run:
            self._log_battle_start(self._next_battle)
            return

        while self.can_perform():
            self._challenge_until_win()
            self._after_win()

        return self.cannot_perform_msg

    def _after_win(self):
        wait(self.config)

    def _log_result(self, what: str, result: BattleResult, attempts: int):
        message = (
            f'{self.world_player} Challenged {what}: {result.result_message}; {self.battle_type} {attempts=},'
            f' total={self.total}, successes={self.successes}, errors={self.errors}'
        )
        log.info(message, extra={'color': 10 if result.is_winner else None})

    @property
    @abstractmethod
    def _next_battle(self) -> Quest | TowerBattleQuest:
        raise NotImplementedError

    @abstractmethod
    def _get_battle_repr(self, battle: Quest | TowerBattleQuest) -> str:
        raise NotImplementedError

    def _log_battle_start(self, battle: Quest | TowerBattleQuest):
        if not self.show_enemies and not self.config.dry_run:
            return

        if self.config.dry_run:
            prefix, verb = '[DRY RUN] ', 'Would challenge'
        else:
            prefix, verb = '', 'Challenging'

        if self.show_enemies:
            suffix = f' - enemies: {" ".join(e.get_summary() for e in battle.enemies)}'
        else:
            suffix = ''

        log.info(f'{prefix}{self.world_player} {verb} {self._get_battle_repr(battle)}{suffix}')

    @abstractmethod
    def _challenge_until_win(self):
        raise NotImplementedError

    def _challenge_battle_until_win(self, battle: Quest | TowerBattleQuest):
        self._log_battle_start(battle)

        battle_repr = self._get_battle_repr(battle)
        attempts = 0
        while True:
            attempts += 1
            try:
                result = self._challenge_once(battle)
            except Exception as e:
                log.error(f'{self.world_player} Challenged {battle_repr}; error: {e}', exc_info=True)
                self.errors += 1
                if self.errors >= self.config.max_errors:
                    raise RuntimeError(f'Exceeded allowed error count while challenging {battle_repr}') from e
            else:
                self._log_result(battle_repr, result, attempts)
                if result.is_winner:
                    return

            wait(self.config)

    @abstractmethod
    def _challenge_battle(self, battle: Quest | TowerBattleQuest) -> BattleResultWrapper:
        raise NotImplementedError

    def _challenge_once(self, battle: Quest | TowerBattleQuest) -> BattleResult:
        self.total += 1

        result_wrapper = self._challenge_battle(battle)
        if self.battle_results_dir:
            result_wrapper.save(self.battle_results_dir)

        result = result_wrapper.battle_result
        if result.is_winner:
            self.successes += 1

        return result


class QuestBattles(BattleTask, battle_type='quest'):
    def __init__(
        self,
        world_session: WorldSession,
        config: TaskConfig = None,
        *,
        show_enemies: bool = True,
        max_quest: tuple[int, int] = None,
        stop_after: int = None,
        battle_results_dir: Path | None = None,
    ):
        super().__init__(world_session, config, battle_results_dir=battle_results_dir, show_enemies=show_enemies)
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

    _next_battle = _next_quest

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

    def _after_win(self):
        wait(self.config)
        self._get_map_info()
        self.world_session.get_next_quest_info()
        # If the next quest is the first in a chapter, use the between_tasks delay to better simulate needing
        # to click `Next Chapter` and waiting for the longer animation
        wait(self.config, between_tasks=self._next_quest.number[1] == 1)

    def _get_map_info(self):
        include_others = not self._map_info_included_others
        self.world_session.get_quest_map_info(include_others)
        self._map_info_included_others = include_others

    def _get_battle_repr(self, quest: Quest) -> str:
        return f'quest {quest}'

    def _challenge_until_win(self):
        quest = self._next_quest
        self.world_session.get_quest_info(quest.id)

        self._challenge_battle_until_win(quest)

    def _challenge_battle(self, quest: Quest) -> QuestBattleResult:
        return self.world_session.battle_quest_boss(quest.id)


class ClimbTower(BattleTask, battle_type='floor'):
    def __init__(
        self,
        world_session: WorldSession,
        config: TaskConfig = None,
        *,
        show_enemies: bool = True,
        tower_type: TowerType = TowerType.Infinite,
        max_floor: int = None,
        battle_results_dir: Path | None = None,
    ):
        super().__init__(world_session, config, battle_results_dir=battle_results_dir, show_enemies=show_enemies)
        self.tower_type = tower_type
        self.max_floor = max_floor

    @cached_property
    def _available_tower_types(self) -> tuple[TowerType, ...]:
        return get_available_tower_types()

    @cached_property
    def _absolute_max_floor(self) -> int:
        return max(f.floor for f in self.world_session.session.mb.tower_type_floors_map[self.tower_type].values())

    @property
    def tower_info(self) -> UserTowerBattleDtoInfo:
        try:
            return self.world_session.user_sync_data.tower_type_status_map[self.tower_type]
        except KeyError as e:
            raise RuntimeError(f'Could not find tower info for {self.tower_type=}') from e

    @property
    def _next_floor_num(self) -> int:
        return self.tower_info['MaxTowerBattleId'] + 1

    @property
    def _next_floor(self) -> TowerBattleQuest:
        return self.world_session.session.mb.tower_type_floors_map[self.tower_type][self._next_floor_num]

    _next_battle = _next_floor

    @property
    def cannot_perform_msg(self) -> str | None:
        if self.max_floor and self._next_floor_num > self.max_floor:
            return f'You have reached the configured maximum floor in the {self.tower_type.tower_name}'
        elif self._next_floor_num > self._absolute_max_floor:
            return f'You have reached the maximum available floor in the {self.tower_type.tower_name}'
        elif self.tower_type == TowerType.Infinite:
            return None
        elif self.tower_type not in self._available_tower_types:
            return f'The {self.tower_type.tower_name} is not available today'
        elif self.tower_info['TodayClearNewFloorCount'] >= 10:
            return f'You have reached the daily limit for {self.tower_type.tower_name} attempts'
        else:
            return None

    def _get_battle_repr(self, floor: TowerBattleQuest) -> str:
        if self.tower_type == TowerType.Infinite:
            limit = ''
        else:
            limit = f' [{self.tower_info["TodayClearNewFloorCount"] + 1}/10]'

        return f'{self.tower_type.tower_name}{limit} floor={floor.floor}'

    def _challenge_until_win(self):
        self.world_session.get_tower_reward_info(self.tower_type)
        self._challenge_battle_until_win(self._next_floor)

    def _challenge_battle(self, floor: TowerBattleQuest) -> TowerBattleResult:
        return self.world_session.start_tower_battle(self.tower_type, floor.floor)
