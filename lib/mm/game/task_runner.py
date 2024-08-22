"""
Runner for Tasks that can be performed when logged in to a specific world
"""

from __future__ import annotations

import logging
from collections import deque
from typing import TYPE_CHECKING, Iterable, Type

from .tasks import Task, TaskConfig
from .utils import wait

if TYPE_CHECKING:
    from .session import WorldSession

__all__ = ['TaskRunner']
log = logging.getLogger(__name__)


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

        wait(self.config)
