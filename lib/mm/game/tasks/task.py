"""
Tasks that can be performed when logged in to a specific world
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass
from functools import cached_property
from random import randint
from typing import TYPE_CHECKING, Iterable, Self, Type

from mm.utils import get_mm_time
from ..utils import wait

if TYPE_CHECKING:
    from datetime import datetime

    from mm.mb_models import MB
    from ..session import WorldSession

__all__ = ['TaskConfig', 'Task', 'DailyTask', 'TaskRunner']
log = logging.getLogger(__name__)


@dataclass
class TaskConfig:
    """Common configurable options for Tasks"""

    dry_run: bool = False
    max_errors: int = 1
    min_wait_ms: int = 300
    max_wait_ms: int = 600
    between_tasks_min_wait_ms: int = 1000
    between_tasks_max_wait_ms: int = 3000

    def get_wait_ms(self, between_tasks: bool = False) -> int:
        if between_tasks:
            return randint(self.between_tasks_min_wait_ms, self.between_tasks_max_wait_ms)
        else:
            return randint(self.min_wait_ms, self.max_wait_ms)


class Task(ABC):
    world_session: WorldSession
    config: TaskConfig

    def __init__(self, world_session: WorldSession, config: TaskConfig = None):
        self.world_session = world_session
        self.config = TaskConfig() if config is None else config

    def before_run(self):
        # This method may be implemented by subclasses to make any necessary preparations
        # before being able to determine if this task can be performed
        pass

    def run(self):
        self.before_run()

        if not self.can_perform():
            log.info(self.cannot_perform_msg)
            return

        result = self.perform_task()
        log.info(f'Result of performing task={self.__class__.__name__}: {result}')

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

    @cached_property
    def mb(self) -> MB:
        return self.world_session.session.mb

    @cached_property
    def world_player(self) -> str:
        return f'[W{self.world_session.world_num}:{self.world_session.player_name}]'

    @cached_property
    def mm_time(self) -> datetime:
        return get_mm_time()


class DailyTask(Task, ABC):
    @property
    @abstractmethod
    def cli_name(self) -> str:
        raise NotImplementedError

    @classmethod
    def get_cli_name_map(cls) -> dict[str, Type[Self]]:
        return {c.cli_name: c for c in cls.get_all()}


class TaskRunner:
    world_session: WorldSession
    config: TaskConfig
    tasks: deque[Task]

    def __init__(self, world_session: WorldSession, config: TaskConfig = None):
        self.world_session = world_session
        self.config = TaskConfig() if config is None else config
        self.tasks = deque()
        self.completed = 0

    def add_task(self, task: Type[Task] | Task):
        self.tasks.append(task if isinstance(task, Task) else task(self.world_session, self.config))

    def add_tasks(self, tasks: Iterable[Type[Task] | Task]):
        self.tasks.extend(t if isinstance(t, Task) else t(self.world_session, self.config) for t in tasks)

    def run_tasks(self):
        while self.tasks:
            self._wait()
            task = self.tasks.popleft()
            task.run()
            self.completed += 1

    def _wait(self):
        if not self.completed:
            return

        wait(self.config, between_tasks=True)
