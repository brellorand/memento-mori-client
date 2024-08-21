"""
Tasks that can be performed when logged in to a specific world
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Type, Self

if TYPE_CHECKING:
    from .session import WorldSession

__all__ = ['Task', 'DailyTask']
log = logging.getLogger(__name__)


class Task(ABC):
    world_session: WorldSession
    dry_run: bool

    def __init__(self, world_session: WorldSession, dry_run: bool = False):
        self.world_session = world_session
        self.dry_run = dry_run

    def run(self):
        if not self.can_perform():
            log.info(self.cannot_perform_msg)
            return

        result = self.perform_task()
        log.info(f'Result of performing task={self.__class__.__name__}: {result}')

    @property
    @abstractmethod
    def cli_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def can_perform(self) -> bool:
        raise NotImplementedError

    @property
    @abstractmethod
    def cannot_perform_msg(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def perform_task(self):
        raise NotImplementedError

    @classmethod
    def get_all(cls) -> list[Type[Self]]:
        return cls.__subclasses__()

    @classmethod
    def get_cli_name_map(cls) -> dict[str, Type[Self]]:
        return {c.cli_name: c for c in cls.get_all()}


class DailyTask(Task, ABC):
    pass


class ClaimDailyVIPGift(DailyTask):
    cli_name = 'vip_gift'
    cannot_perform_msg = 'The daily VIP gift was already claimed'

    def can_perform(self) -> bool:
        return self.world_session.user_sync_data.has_vip_daily_gift

    def perform_task(self):
        if self.dry_run:
            log.info('[DRY RUN] Would claim daily VIP gift')
            return

        log.info('Claiming daily VIP gift')
        # TODO: Only print the items that were received
        return self.world_session.get_daily_vip_gift()
