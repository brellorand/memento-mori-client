"""
Tasks related to reforging equipment
"""

from __future__ import annotations

import logging
from functools import cached_property
from typing import TYPE_CHECKING, Collection

from mm.enums import BaseParameterType, EquipmentSlotType
from ..utils import wait
from .task import Task, TaskConfig

if TYPE_CHECKING:
    from ..models import Character, Equipment
    from ..session import WorldSession

__all__ = ['ReforgeGear']
log = logging.getLogger(__name__)


class ReforgeGear(Task):
    def __init__(
        self,
        world_session: WorldSession,
        config: TaskConfig = None,
        *,
        character: str,
        stat: BaseParameterType,
        slots: Collection[EquipmentSlotType] = (),
        target_value: int = None,
        target_pct: float = None,
        max_errors: int = 1,
    ):
        super().__init__(world_session, config)
        self._character = character
        self.stat = stat
        self.slots = slots
        self.target_value = target_value
        self.target_pct = target_pct
        self.max_errors = max_errors
        self.total = 0
        self.errors = 0

    @cached_property
    def character(self) -> Character | None:
        mb_char = self.world_session.session.mb.get_character(self._character)
        for char in sorted(self.world_session.characters.values()):
            if char.character == mb_char:
                return char
        return None

    @property
    def all_equipment(self) -> list[Equipment]:
        return sorted(self.world_session.char_guid_equipment_map.get(self.character.guid, []))

    def _should_reforge(self, equipment: Equipment) -> bool:
        if self.slots and equipment.equipment.slot_type not in self.slots:
            return False
        if self.target_value and self.target_value <= equipment.reforged_stat_value(self.stat):
            return False
        if self.target_pct and self.target_pct <= equipment.reforged_stat_percent(self.stat):
            return False
        return True

    def _get_target_value(self, equipment: Equipment) -> int:
        targets = []
        if self.target_value:
            targets.append(self.target_value)
        if self.target_pct:
            targets.append(int(equipment.equipment.additional_param_total * self.target_pct))
        return min(targets)

    @property
    def to_reforge(self) -> list[Equipment]:
        return [e for e in self.all_equipment if self._should_reforge(e)]

    @property
    def cannot_perform_msg(self) -> str | None:
        if self.target_pct is self.target_value is None:
            return 'No target value or percentage was set'
        elif self.character is None:
            return f'Could not identify a character matching {self._character!r}'
        elif not self.to_reforge:
            return f'No matching equipment was found on {self.character}'
        # TODO: Validate target value is <= 60% of max

        return None

    def can_perform(self) -> bool:
        return not self.cannot_perform_msg

    def perform_task(self):
        to_reforge_guids = [e.guid for e in self.to_reforge]
        to_rf_num = len(to_reforge_guids)

        prefix = '[DRY RUN] Would reforge' if self.config.dry_run else 'Reforging'
        log.info(f'{prefix} {to_rf_num} items equipped by {self.character}')
        for i, guid in enumerate(to_reforge_guids, 1):
            self._reforge_item(self.world_session.equipment[guid], guid, f'[Item {i}/{to_rf_num}]')

    def _reforge_item(self, item: Equipment, guid: str, prefix: str):
        log.info(f'{prefix} Initial State: {item.reforge_summary(self.stat, 11)}')

        if self.config.dry_run:
            log.info(f'[DRY RUN] Would reforge {item}')
            return

        target = self._get_target_value(item)

        attempts = 0
        while self._should_reforge(item):
            attempts += 1
            self.total += 1
            try:
                self.world_session.reforge_gear(guid)
            except Exception as e:
                log.error(f'{prefix}#{attempts} Reforged {item.basic_info}; error: {e}', exc_info=True)
                self.errors += 1
                if self.errors >= self.max_errors:
                    raise RuntimeError(f'Exceeded allowed error count while reforging {item.basic_info}') from e
            else:
                item = self.world_session.equipment[guid]  # Refresh the item based on the latest request
                color = 10 if item.reforged_stat_value(self.stat) >= target else 11
                log.info(f'{prefix}#{attempts} Reforged {item.reforge_summary(self.stat, color)}')

            wait(self.config)
