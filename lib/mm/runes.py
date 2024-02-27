"""
Classes representing runes, used to calculate stat totals.  WIP.
"""

from __future__ import annotations

import logging
from abc import ABC
from functools import cached_property
from itertools import product
from typing import Type, Iterator

from .enums import RuneRarity
from .exceptions import RuneError

__all__ = []
log = logging.getLogger(__name__)

RuneLevels = tuple[int] | tuple[int, int] | tuple[int, int, int]

_RARITY_LEVELS = {
    1: RuneRarity.R,
    4: RuneRarity.SR,
    7: RuneRarity.SSR,
    12: RuneRarity.UR,
    # TODO: LR
}


class Rune(ABC):
    __slots__ = ('_level',)
    stat_cls_map = {}
    stat: str
    values: list[int]

    def __init_subclass__(cls, stat: str = None, **kwargs):  # noqa
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, 'values'):
            raise TypeError('Missing required class attribute: values')
        if stat:
            cls.stat = stat
            cls.stat_cls_map[stat.replace(' ', '')] = cls
        # Ideally, bases should be checked for ABC here if stat is not truthy

    def __init__(self, level: int):
        self.level = level

    @classmethod
    def get_rune_class(cls, stat: str) -> Type[Rune]:
        try:
            return cls.stat_cls_map[stat.replace(' ', '').upper()]
        except KeyError:
            allowed = ', '.join(sorted(cls.stat_cls_map))
            raise KeyError(f'Invalid rune {stat=} - pick from: {allowed}') from None

    @classmethod
    def get_rune_set(cls, *levels) -> RuneSet:
        return RuneSet(*map(cls, levels))

    @classmethod
    def get_total(cls, *levels) -> int:
        return cls.get_rune_set(*levels).total

    @property
    def level(self) -> int:
        return self._level

    @level.setter
    def level(self, value: int):
        if not (0 <= value <= 15):
            raise ValueError('Runes may only be level 1~15')
        self._level = value

    @property
    def value(self) -> int:
        return self.values[self.level - 1] if self.level else 0

    @property
    def rarity(self) -> RuneRarity:
        for level, rarity in _RARITY_LEVELS.items():
            if self.level <= level:
                return rarity
        return RuneRarity.LR

    @property
    def ticket_cost(self) -> int:
        return 2 ** self.level

    def __mul__(self, other: int) -> int:
        if not isinstance(other, int):
            raise TypeError(f'Runes may only be multiplied by integers; found type={other.__class__.__name__}')
        return self.value * other

    def __add__(self, other: Rune) -> int:
        cls = self.__class__
        if not isinstance(other, cls):
            raise TypeError(f'{cls.__name__} objects may only be added to other {cls.__name__} objects')
        return self.value + other.value

    def __hash__(self) -> int:
        return hash(self.__class__) ^ hash(self.stat) ^ hash(self.level)

    def __eq__(self, other: Rune) -> bool:
        return self.stat == other.stat and self.level == other.level

    def __lt__(self, other: Rune) -> bool:
        return (self.stat, self.level) < (other.stat, other.level)  # noqa

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}({self.level})>'


class RuneSet:
    type: Type[Rune] | None

    def __init__(self, *runes: Rune):
        types = {r.__class__ for r in runes}
        if len(types) > 1:
            raise RuneError(f'{self.__class__.__name__} objects may only contain one type of Rune')
        self._runes = list(runes)
        self.type = next(iter(types)) if types else None

    @cached_property
    def runes(self) -> tuple[Rune, ...]:
        return tuple(self._runes)

    @cached_property
    def total(self) -> int:
        return sum(r.value for r in self._runes) if self._runes else 0

    @cached_property
    def total_ticket_cost(self) -> int:
        return sum(r.ticket_cost for r in self._runes) if self._runes else 0

    @cached_property
    def levels(self) -> RuneLevels:
        return tuple(r.level for r in self._runes)

    def add(self, rune: Rune):
        if self.type is None:
            self.type = rune.__class__
        elif rune.__class__ is not self.type:
            raise RuneError(f'{self.__class__.__name__} objects may only contain one type of Rune')
        elif len(self._runes) >= 3:
            raise RuneError('Rune sets may only contain a maximum of 3 Runes')

        # Reset cached properties that are based on this set's runes
        for key in ('runes', 'total', 'total_ticket_cost', 'levels'):
            try:
                del self.__dict__[key]
            except KeyError:
                pass

        self._runes.append(rune)

    def __iter__(self) -> Iterator[Rune]:
        yield from sorted(self._runes)

    def __hash__(self) -> int:
        return hash(self.__class__) ^ hash(self.type) ^ hash(self.runes)

    def __eq__(self, other: RuneSet) -> bool:
        return self.type is other.type and self.runes == other.runes

    def __lt__(self, other: RuneSet) -> bool:
        if self.type is not other.type:
            return self.type.__name__ < other.type.__name__
        elif self.total != other.total:
            return self.total < other.total
        else:
            return self.total_ticket_cost < other.total_ticket_cost


# region Stat-Specific Rune Classes


class SpeedRune(Rune, stat='SPD'):
    values = [10, 18, 33, 53, 80, 110, 150, 195, 240, 300, 360, 425, 500, 575, 660]


class PMDefBreakRune(Rune, stat='PMDB'):
    values = [25, 45, 80, 140, 250, 430, 750, 1300, 2200, 3710, 6250, 10_400, 15_900, 21_900, 26_900]


class CritRune(Rune, stat='CRIT'):
    values = [60, 100, 190, 370, 730, 1450, 2890, 5770, 11_500, 22_900, 45_700, 91_300, 167_000, 277_000, 416_000]


class CritResistRune(Rune, stat='CRIT RES'):
    values = [60, 100, 190, 370, 730, 1450, 2890, 5770, 11_500, 22_900, 45_700, 91_300, 167_000, 277_000, 416_000]


class EvasionRune(Rune, stat='EVD'):
    values = [
        260, 500, 970, 1900, 3770,
        7500, 14_900, 29_700, 59_300, 118_000,
        235_000, 463_000, 835_000, 1_380_000, 2_080_000,
    ]


# region Base Stat Runes


class OffensiveBaseStatRune(Rune, ABC):
    values = [60, 100, 180, 330, 620, 1130, 2070, 3800, 6930, 12_600, 23_100, 42_300, 77_400, 141_000, 250_000]


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
    values = [35, 60, 90, 150, 270, 510, 930, 1700, 3120, 5700, 10_400, 19_000, 34_800, 63_700, 112_000]

    @property
    def hp(self) -> int:
        return self.value * 10

    @property
    def crit_res(self) -> int:
        return self.value // 2


# endregion


# endregion


class RuneCalculator:
    def __init__(self, rune_cls: Type[Rune]):
        self.rune_cls = rune_cls

    @cached_property
    def value_rune_sets_map(self) -> dict[int, list[RuneSet]]:
        """
        A sorted mapping of ``{value: [RuneSet, ...]}`` for each combination of rune levels that results in
        each total stat value.  Each value's list of RuneSets is sorted in ascending order from fewest / lowest level
        runes to highest.
        """
        val_set_map = {self.rune_cls(level).value: {self.rune_cls.get_rune_set(level)} for level in range(1, 16)}
        for repeat in (2, 3):
            for levels in product(range(1, 16), repeat=repeat):
                rune_set = self.rune_cls.get_rune_set(*levels)
                val_set_map.setdefault(rune_set.total, set()).add(rune_set)

        return {value: sorted(sets) for value, sets in sorted(val_set_map.items())}

    @cached_property
    def max_value(self) -> int:
        return max(self.value_rune_sets_map)

    def find_sets(self, min_value: int) -> list[RuneSet]:
        value_sets = []
        for value, sets in self.value_rune_sets_map.items():
            if value >= min_value:
                value_sets.extend(sets)
        return value_sets

    def find_closest_min_ticket_set(self, min_value: int) -> RuneSet:
        return min(self.find_sets(min_value), key=lambda rs: rs.total_ticket_cost)

    # region Find Closest Value (does not provide the lowest cost option)

    def get_closest_value(self, min_value: int) -> int:
        if min_value in self.value_rune_sets_map:
            log.debug(f'Found an exact rune set match for {min_value=} stat={self.rune_cls.stat!r}')
            return min_value
        elif min_value >= self.max_value:
            log.debug(f'No rune set provides {min_value=} stat={self.rune_cls.stat!r} - returning max={self.max_value}')
            return self.max_value

        for value in self.value_rune_sets_map:
            if value >= min_value:
                log.debug(f'Found a rune set that provides {value=} >= {min_value=} stat={self.rune_cls.stat!r}')
                return value

        raise ValueError(f'Unexpected {min_value=}')  # This should be unreachable

    def get_sets(self, min_value: int) -> list[RuneSet]:
        return self.value_rune_sets_map[self.get_closest_value(min_value)]

    def get_closest_sets(self, min_value: int) -> tuple[int, list[RuneSet]]:
        closest = self.get_closest_value(min_value)
        return closest, self.value_rune_sets_map[closest]

    # endregion
