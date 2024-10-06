"""
Tasks related to main quest battles
"""

from __future__ import annotations

import logging
from time import sleep
from typing import TYPE_CHECKING

from ..utils import wait
from .task import Task, TaskConfig

if TYPE_CHECKING:
    from mm.mb_models.quest import Quest
    from mm.typing import UserBattleBossDtoInfo
    from ..session import WorldSession

__all__ = ['QuestBattles']
log = logging.getLogger(__name__)


class QuestBattles(Task):
    def __init__(
        self,
        world_session: WorldSession,
        config: TaskConfig = None,
        *,
        max_quest: tuple[int, int] = None,
        stop_after: int = None,
        # max_errors: int = 5,
        max_errors: int = 1,
    ):
        super().__init__(world_session, config)
        self.max_quest = max_quest
        self.stop_after = stop_after
        self.max_errors = max_errors
        self.total = 0
        self.successes = 0
        self.errors = 0
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

    def can_perform(self) -> bool:
        return not self.cannot_perform_msg

    def run(self):
        self._get_map_info()
        super().run()

    def perform_task(self):
        if self.config.dry_run:
            log.info(f'[DRY RUN] Would challenge quest {self._next_quest}')
            return

        while self.can_perform():
            self._challenge_until_win()
            wait(self.config)
            self._get_map_info()
            self.world_session.get_next_quest_info()
            wait(self.config)

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
            self.total += 1
            try:
                result = self.world_session.battle_quest_boss(quest.id).battle_result
                # TODO: Save the battle logs
                if result.is_winner:
                    self.successes += 1
            except Exception as e:
                log.error(f'{log_prefix}; error: {e}', exc_info=True)
                self.errors += 1
                if self.errors >= self.max_errors:
                    raise RuntimeError(f'Exceeded allowed error count while challenging quest {quest}') from e
            else:
                log.info(
                    f'{log_prefix}: {result.result_message}; quest {attempts=},'
                    f' total={self.total}, successes={self.successes}, errors={self.errors}'
                )
                if result.is_winner:
                    return
                wait(self.config)
