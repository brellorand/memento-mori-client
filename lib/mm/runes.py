"""
Classes representing runes, used to calculate stat totals.  WIP.
"""

from __future__ import annotations

import logging
from abc import ABC

from .enums import RuneRarity

__all__ = []
log = logging.getLogger(__name__)

_RARITY_LEVELS = {
    1: RuneRarity.R,
    4: RuneRarity.SR,
    7: RuneRarity.SSR,
    12: RuneRarity.UR,
    # TODO: LR
}


class Rune(ABC):
    stat: str
    value: int
    values: list[int]

    def __init_subclass__(cls, stat: str = None, **kwargs):  # noqa
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, 'values'):
            raise TypeError('Missing required class attribute: values')
        if stat:
            cls.stat = stat
        # Ideally, bases should be checked for ABC here if stat is not truthy

    def __init__(self, level: int):
        self.level = level

    @classmethod
    def get_total(cls, *levels) -> int:
        return RuneSet(*map(cls, levels)).total

    @property
    def level(self) -> int:
        return self._level

    @level.setter
    def level(self, value: int):
        if not (1 <= value <= 15):
            raise ValueError('Runes may only be level 1~15')
        self._level = value

    @property
    def value(self) -> int:
        return self.values[self.level - 1]

    @property
    def rarity(self) -> RuneRarity:
        for level, rarity in _RARITY_LEVELS.items():
            if self.level <= level:
                return rarity
        return RuneRarity.LR

    def __mul__(self, other: int) -> int:
        if not isinstance(other, int):
            raise TypeError(f'Runes may only be multiplied by integers; found type={other.__class__.__name__}')
        return self.value * other

    def __add__(self, other: Rune) -> int:
        cls = self.__class__
        if not isinstance(other, cls):
            raise TypeError(f'{cls.__name__} objects may only be added to other {cls.__name__} objects')
        return self.value + other.value


class RuneSet:
    def __init__(self, *runes: Rune):
        types = {r.__class__ for r in runes}
        if len(types) > 1:
            raise TypeError(f'{self.__class__.__name__} objects may only contain one type of Rune')
        self.runes = list(runes)
        self.type = next(iter(types)) if types else None

    @property
    def total(self) -> int:
        return sum(r.value for r in self.runes) if self.runes else 0

    def add(self, rune: Rune):
        if self.type is None:
            self.type = rune.__class__
        elif rune.__class__ is not self.type:
            raise TypeError(f'{self.__class__.__name__} objects may only contain one type of Rune')

        self.runes.append(rune)


class SpeedRune(Rune, stat='SPD'):
    values = [10, 18, 33, 53, 80, 110, 150, 195, 240, 300]  # TODO: 11+


class PMDefBreakRune(Rune, stat='PMDB'):
    values = [25, 45, 80, 140, 250, 430, 750, 1300, 2200, 3710, 6250, 10400]  # TODO: 13+


class CritRune(Rune, stat='CRIT'):
    values = [60, 100, 190, 370, 730, 1450, 2890, 5770, 11500, 22900]  # TODO: 11+


class CritResistRune(Rune, stat='CRIT RES'):
    values = [60, 100, 190, 370, 730, 1450, 2890, 5770, 11500, 22900]  # TODO: 11+


class EvasionRune(Rune, stat='EVD'):
    values = [260, 500, 970, 1900, 3770, 7500, 14900, 29700, 59300]  # TODO: 10+


# region Base Stat Runes


class OffensiveBaseStatRune(Rune, ABC):
    values = [60, 100, 180, 330, 620, 1130, 2070, 3800, 6930]  # TODO: 10+


class DexRune(OffensiveBaseStatRune, stat='DEX'):
    @property
    def crit(self) -> int:
        return self.value // 2

    @property
    def evd(self) -> int:
        return self.value // 2


class MagRune(OffensiveBaseStatRune, stat='MAG'):
    @property
    def m_def(self) -> int:
        return self.value

    @property
    def debuff_acc(self) -> int:
        return self.value // 2


class StrRune(OffensiveBaseStatRune, stat='STR'):
    @property
    def p_def(self) -> int:
        return self.value

    @property
    def acc(self) -> int:
        return self.value // 2


class StaRune(Rune, stat='STA'):
    values = [35, 60, 90, 150, 270, 510, 930, 1700, 3120]  # TODO: 10+

    @property
    def hp(self) -> int:
        return self.value * 10

    @property
    def crit_res(self) -> int:
        return self.value // 2


# endregion
