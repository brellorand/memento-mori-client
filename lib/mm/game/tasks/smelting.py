"""
Tasks related to smelting equipment
"""

from __future__ import annotations

import logging
from functools import cached_property
from typing import TYPE_CHECKING, Collection

from mm.enums import EquipmentRarityFlags, ItemType
from ..utils import wait
from .task import DailyTask, Task, TaskConfig

if TYPE_CHECKING:
    from ..models import Equipment, ItemAndCount
    from ..session import WorldSession

__all__ = ['SmeltAll', 'SmeltUnequippedGear', 'SmeltNeverEquippedSGear']
log = logging.getLogger(__name__)


class SmeltAll(DailyTask):
    cli_name = 'smelt_all'

    def __init__(
        self,
        world_session: WorldSession,
        config: TaskConfig = None,
        *,
        rarity: EquipmentRarityFlags = EquipmentRarityFlags.range(EquipmentRarityFlags.D, EquipmentRarityFlags.A),
    ):
        super().__init__(world_session, config)
        self.rarity = rarity

    @property
    def cannot_perform_msg(self) -> str:
        return f'There are no never-equipped items with rarity={self.rarity} in your inventory'

    def can_perform(self) -> bool:
        return any(
            ic.count and ic.item_type == ItemType.Equipment and ic.item.rarity_flags in self.rarity
            for ic in self.world_session.inventory
        )

    def perform_task(self):
        if self.config.dry_run:
            log.info(f'[DRY RUN] Would smelt all rarity={self.rarity} never-equipped equipment')
            return

        log.info(f'Smelting all rarity={self.rarity} never-equipped equipment')
        return self.world_session.smelt_all_gear(self.rarity)


class SmeltNeverEquippedSGear(Task):
    def __init__(
        self,
        world_session: WorldSession,
        config: TaskConfig = None,
        *,
        min_level: int = 1,
        max_level: int | None = None,
        keep: int = 0,
    ):
        super().__init__(world_session, config)
        self.keep = keep
        self.min_level = min_level
        self.max_level = max_level

    @cached_property
    def _all_s_equipment_items(self) -> list[ItemAndCount]:
        return [
            ic
            for ic in self.world_session.inventory
            if ic.count and ic.item_type == ItemType.Equipment and ic.item.rarity_flags == EquipmentRarityFlags.S
        ]

    @cached_property
    def _max_level(self) -> int:
        return max(ic.item.level for ic in self._all_s_equipment_items) if self._all_s_equipment_items else 9999

    @cached_property
    def _to_be_smelted(self) -> list[tuple[ItemAndCount, int]]:
        min_level, max_level = self.min_level, self.max_level or self._max_level
        to_be_smelted = []
        for ic in self._all_s_equipment_items:
            equipment = ic.item
            if not min_level <= equipment.level <= max_level:
                continue

            if equipment.level == max_level and self.keep and equipment.quality_level:
                count = ic.count - self.keep
                if count > 0:
                    to_be_smelted.append((ic, count))
            else:
                to_be_smelted.append((ic, ic.count))

        return to_be_smelted

    def can_perform(self) -> bool:
        return bool(self._to_be_smelted)

    @cached_property
    def _description(self) -> str:
        min_lvl, max_lvl = self.min_level, self.max_level or self._max_level
        return f'never-equipped items with rarity=S and {min_lvl} <= level <= {max_lvl}'

    @property
    def cannot_perform_msg(self) -> str:
        return f'There are no {self._description} in your inventory'

    def perform_task(self):
        if self.config.dry_run:
            log.info(f'[DRY RUN] Would smelt all {self._description}:')
            for item_and_count, count in self._to_be_smelted:
                log.info(f'  -> Would smelt {count} x {item_and_count}')

            return

        log.info(f'Smelting all {self._description}')
        for i, (item_and_count, count) in enumerate(self._to_be_smelted):
            if i:
                wait(self.config)

            log.info(f'  -> Smelting {count} x {item_and_count}')
            self.world_session.smelt_never_equipped_gear(item_and_count, count)


class SmeltUnequippedGear(Task):
    def __init__(
        self,
        world_session: WorldSession,
        config: TaskConfig = None,
        *,
        min_level: int = 1,
        max_level: int | None = None,
    ):
        super().__init__(world_session, config)
        self.min_level = min_level
        self.max_level = max_level

    @cached_property
    def _all_unequipped(self) -> Collection[Equipment]:
        return self.world_session.char_guid_equipment_map.get('', ())

    @cached_property
    def _max_level(self) -> int:
        return max(e.equipment.level for e in self._all_unequipped) if self._all_unequipped else 9999

    @cached_property
    def _to_be_smelted(self) -> list[Equipment]:
        min_level, max_level = self.min_level, self.max_level or self._max_level
        return [e for e in self._all_unequipped if _should_smelt(e, min_level, max_level)]

    def can_perform(self) -> bool:
        return bool(self._to_be_smelted)

    @cached_property
    def _description(self) -> str:
        min_lvl, max_lvl = self.min_level, self.max_level or self._max_level
        return f'unequipped items with {min_lvl} <= level <= {max_lvl}'

    @property
    def cannot_perform_msg(self) -> str:
        return f'There are no {self._description} in your inventory'

    def perform_task(self):
        if self.config.dry_run:
            log.info(f'[DRY RUN] Would smelt all {self._description}:')
            for equipment in self._to_be_smelted:
                log.info(f'  -> Would smelt {equipment}')

            return

        log.info(f'Smelting all {self._description}')
        for i, equipment in enumerate(self._to_be_smelted):
            if i:
                wait(self.config)

            log.info(f'  -> Smelting {equipment}')
            self.world_session.smelt_gear(equipment.guid)


def _should_smelt(equipment: Equipment, min_level: int, max_level: int) -> bool:
    if not min_level <= equipment.equipment.level <= max_level:
        return False
    elif equipment.holy_augment_level or equipment.dark_augment_level:
        return False
    return not (equipment.rune_slots_unlocked or equipment.upgrade_level)
