"""
Tasks related to Tower of Infinity battles
"""

from __future__ import annotations

import logging
from functools import cached_property
from typing import TYPE_CHECKING

from mm.enums import TowerType
from ..battle import get_available_tower_types
from ..utils import wait
from .task import Task, TaskConfig

if TYPE_CHECKING:
    from mm.typing import UserTowerBattleDtoInfo
    from ..session import WorldSession

__all__ = ['ClimbTower']
log = logging.getLogger(__name__)


class ClimbTower(Task):
    def __init__(
        self,
        world_session: WorldSession,
        config: TaskConfig = None,
        *,
        tower_type: TowerType = TowerType.Infinite,
        max_floor: int = None,
        # max_errors: int = 5,
        max_errors: int = 1,
    ):
        super().__init__(world_session, config)
        self.tower_type = tower_type
        self.max_floor = max_floor
        self.max_errors = max_errors
        self.total = 0
        self.successes = 0
        self.errors = 0

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

    def can_perform(self) -> bool:
        return not self.cannot_perform_msg

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
        log_prefix = self._get_log_prefix(floor)
        attempts = 0
        while True:
            attempts += 1
            self.total += 1
            try:
                result = self.world_session.start_tower_battle(self.tower_type, floor).battle_result
                # TODO: Save the battle logs
                if result.is_winner:
                    self.successes += 1
            except Exception as e:
                log.error(f'{log_prefix}; error: {e}', exc_info=True)
                self.errors += 1
                if self.errors >= self.max_errors:
                    raise RuntimeError(
                        f'Exceeded allowed error count while challenging {self.tower_type.tower_name} {floor=}'
                    ) from e
            else:
                log.info(
                    f'{log_prefix}: {result.result_message}; floor {attempts=},'
                    f' total={self.total}, successes={self.successes}, errors={self.errors}'
                )
                if result.is_winner:
                    return
                wait(self.config)
