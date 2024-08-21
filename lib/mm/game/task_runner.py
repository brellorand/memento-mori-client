"""
Runner for Tasks that can be performed when logged in to a specific world
"""

from __future__ import annotations

import logging
from collections import deque
from typing import TYPE_CHECKING, Iterable, Type

if TYPE_CHECKING:
    from .session import WorldSession
    from .tasks import Task

__all__ = ['TaskRunner']
log = logging.getLogger(__name__)


class TaskRunner:
    world_session: WorldSession
    dry_run: bool
    tasks: deque[Type[Task]]

    def __init__(self, world_session: WorldSession, dry_run: bool = False):
        self.world_session = world_session
        self.dry_run = dry_run
        self.tasks = deque()

    def add_task(self, task: Type[Task]):
        self.tasks.append(task)

    def add_tasks(self, tasks: Iterable[Type[Task]]):
        self.tasks.extend(tasks)

    def run_tasks(self):
        while self.tasks:
            task_cls = self.tasks.popleft()
            task = task_cls(self.world_session, self.dry_run)
            task.run()
