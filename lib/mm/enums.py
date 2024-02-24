"""

"""

from __future__ import annotations

import logging
from enum import StrEnum, IntEnum

__all__ = ['Rarity', 'RuneRarity', 'Region']
log = logging.getLogger(__name__)


class Rarity(StrEnum):
    R = 'R'
    R_PLUS = 'R+'
    SR = 'SR'
    SR_PLUS = 'SR+'
    SSR = 'SSR'
    SSR_PLUS = 'SSR+'
    UR = 'UR'
    UR_PLUS = 'UR+'
    LR = 'LR'
    LR_1 = 'LR+1'
    LR_2 = 'LR+2'
    LR_3 = 'LR+3'
    LR_4 = 'LR+4'
    LR_5 = 'LR+5'
    LR_6 = 'LR+6'


class RuneRarity(StrEnum):
    R = 'R'
    SR = 'SR'
    SSR = 'SSR'
    UR = 'UR'
    LR = 'LR'


class Region(IntEnum):
    JAPAN = 1
    KOREA = 2
    ASIA = 3
    NORTH_AMERICA = 4
    EUROPE = 5
    GLOBAL = 6

    @classmethod
    def for_world(cls, world_id: int) -> Region:
        region = world_id // 1000
        try:
            return cls(region)
        except ValueError as e:
            raise ValueError(f'Invalid {region=} for {world_id=}') from e
