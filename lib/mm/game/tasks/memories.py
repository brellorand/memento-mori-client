"""
Task for viewing character memories
"""

from __future__ import annotations

import logging
from functools import cached_property
from typing import TYPE_CHECKING

from ..utils import wait
from .task import Task, TaskConfig

if TYPE_CHECKING:
    from mm.mb_models.characters import CharacterStory
    from ..session import WorldSession

__all__ = ['ViewMemories']
log = logging.getLogger(__name__)


class ViewMemories(Task):
    def __init__(
        self,
        world_session: WorldSession,
        config: TaskConfig = None,
        *,
        limit: int | None = None,
    ):
        super().__init__(world_session, config)
        self.total = 0
        self.limit = limit

    def can_perform(self) -> bool:
        return not self.cannot_perform_msg

    @cached_property
    def to_read(self) -> list[CharacterStory]:
        to_read = []
        for entry in self.world_session.user_sync_data.character_index_info:
            stories = self.world_session.session.mb.characters[entry['CharacterId']].stories
            for story in stories.values():
                if story.level <= entry['MaxCharacterLevel'] and story.episode_id > entry['MaxEpisodeId']:
                    to_read.append(story)

        return to_read

    @cached_property
    def _max_readable(self) -> int:
        return len(self.to_read)

    @property
    def cannot_perform_msg(self) -> str | None:
        if not self.to_read:
            return 'There are no new memories available to view'
        elif self.limit is not None and self.total >= self.limit:
            return 'You have reached the configured view limit'
        elif self.total >= self._max_readable:
            return 'You have viewed all memories that were available'
        else:
            return None

    def perform_task(self):
        to_read = self.to_read[: self.limit] if self.limit else self.to_read
        to_read_count = len(to_read)
        expected_diamonds = to_read_count * 20

        prefix = '[DRY RUN] Would view' if self.config.dry_run else 'Viewing'
        log.info(f'{prefix} {to_read_count} memories, which would result in {expected_diamonds} diamonds')
        if self.config.dry_run:
            return

        for story in self.to_read:
            if not self.can_perform():
                break

            log.info(f'{self.world_player} Viewing memory: {story}')
            self.world_session.view_character_story(story.id)
            self.total += 1
            wait(self.config)

        return self.cannot_perform_msg
