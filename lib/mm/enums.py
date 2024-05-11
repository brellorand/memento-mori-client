"""

"""

from __future__ import annotations

import logging
from enum import StrEnum, IntEnum

__all__ = ['Rarity', 'RuneRarity', 'Region', 'Locale', 'LOCALES']
log = logging.getLogger(__name__)


class Locale(StrEnum):
    # ls -1 temp/mb/TextResource* | sed 's#temp/mb/TextResource##g' | sed -E "s#(....)MB\.json#'\\1',#g" | paste -sd ' '

    num: int

    def __new__(cls, value, num: int):
        obj = str.__new__(cls)
        obj._value_ = value
        obj.num = num
        return obj

    DeDe = 'DeDe', 13
    EnUs = 'EnUs', 2
    EsMx = 'EsMx', 7
    FrFr = 'FrFr', 5
    IdId = 'IdId', 10
    JaJp = 'JaJp', 1
    KoKr = 'KoKr', 3
    PtBr = 'PtBr', 8
    RuRu = 'RuRu', 12
    ThTh = 'ThTh', 9
    ViVn = 'ViVn', 11
    ZhCn = 'ZhCn', 6
    ZhTw = 'ZhTw', 4

    @property
    def country_code(self) -> str:
        return self._value_[2:].upper()

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            try:
                a, b, c, d = value
            except ValueError:
                pass
            else:
                key = a.upper() + b.lower() + c.upper() + d.lower()
                try:
                    return cls._member_map_[key]
                except KeyError:
                    pass
        return super()._missing_(value)

    def __str__(self) -> str:
        return self._value_

    def __hash__(self) -> int:
        return hash(self.__class__) ^ hash(self._value_)

    def __eq__(self, other: Locale) -> bool:
        return self._value_ == other._value_

    def __lt__(self, other: Locale) -> bool:
        return self._value_ < other._value_

    def __bool__(self) -> bool:
        return True


LOCALES = list(Locale)


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


class Element(IntEnum):
    AZURE = 1
    CRIMSON = 2
    EMERALD = 3
    AMBER = 4
    RADIANCE = 5
    CHAOS = 6


class Job(IntEnum):
    WARRIOR = 1
    SNIPER = 2
    SORCERER = 4


class CharacterRarity(IntEnum):
    N = 1
    R = 2
    SR = 8
