"""
Classes representing runes, used to calculate stat totals.  WIP.
"""

from __future__ import annotations

import logging
from abc import ABC
from collections import Counter, deque
from concurrent.futures import ProcessPoolExecutor, as_completed
from functools import cached_property
from itertools import product, combinations, chain, permutations
from math import factorial
from typing import TYPE_CHECKING, Type, Iterator, Collection, Iterable, Sequence

from .enums import RuneRarity
from .exceptions import RuneError

if TYPE_CHECKING:
    from .mb_models import Character

# fmt: off
__all__ = [
    'Rune', 'RuneSet', 'RuneCalculator', 'PartyMember', 'speed_tune',
    'StrRune', 'DexRune', 'MagRune', 'StaRune',
    'AccuracyRune', 'AttackRune', 'CritRune', 'DebuffAccuracyRune', 'PMDefBreakRune', 'SpeedRune',
    'CritResistRune', 'DebuffResistanceRune', 'EvasionRune', 'HPRune', 'MagicDefenseRune', 'PhysicalDefenseRune',
]
# fmt: on
log = logging.getLogger(__name__)

RuneLevels = tuple[int] | tuple[int, int] | tuple[int, int, int]
AnyRuneLevels = RuneLevels | list[int]

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

    # region Class Methods

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

    # endregion

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
        return 2**self.level

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
        return f'{self.__class__.__name__}({self.level})'


class RuneSet:
    type: Type[Rune] | None

    def __init__(self, *runes: Rune):
        types = {r.__class__ for r in runes}
        if len(types) > 1:
            raise RuneError(f'{self.__class__.__name__} objects may only contain one type of Rune')
        self._runes = tuple(runes)
        self.type = next(iter(types)) if types else None

    @classmethod
    def new(cls, rune_type: Type[Rune]):
        self = cls.__new__(cls)
        self.type = rune_type
        self._runes = ()
        return self

    def __repr__(self) -> str:
        rune_type = self.type.__name__ if self.type else None
        return f'<{self.__class__.__name__}[type={rune_type}, total={self.total}, levels={self.levels}]>'

    @property
    def runes(self) -> tuple[Rune, ...]:
        return self._runes

    @cached_property
    def total(self) -> int:
        return sum(r.value for r in self._runes) if self._runes else 0

    @cached_property
    def levels(self) -> RuneLevels:
        return tuple(r.level for r in self._runes)  # noqa

    @property
    def total_ticket_cost(self) -> int:
        return sum(r.ticket_cost for r in self._runes) if self._runes else 0

    def _reset_properties(self):
        # Reset cached properties that are based on this set's runes
        for key in ('total', 'levels'):
            try:
                del self.__dict__[key]
            except KeyError:
                pass

    def add(self, rune: Rune):
        if self.type is None:
            self.type = rune.__class__
        elif rune.__class__ is not self.type:
            raise RuneError(f'{self.__class__.__name__} objects may only contain one type of Rune')
        elif len(self._runes) >= 3:
            raise RuneError('Rune sets may only contain a maximum of 3 Runes')

        self._reset_properties()
        self._runes = (*self._runes, rune)

    def set_levels(self, levels: AnyRuneLevels, rune_type: Type[Rune] = None):
        if len(levels) > 3:
            raise RuneError('Rune sets may only contain a maximum of 3 Runes')
        if rune_type is not None:
            self.type = rune_type
        elif (rune_type := self.type) is None:
            raise RuneError('A Rune type is required')

        self._reset_properties()
        self._runes = tuple(rune_type(level) for level in levels)

    def reset(self):
        self._reset_properties()
        self._runes = ()

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

    def overlaps(self, other: RuneSet) -> bool:
        """Returns True if this set contains any runes that are the exact same object as one in the other set"""
        # if self.type != other.type or not set(self.levels).intersection(other.levels):
        if self.type != other.type:
            return False
        return any(own_rune is other_rune for own_rune in self.runes for other_rune in other.runes)


class RunePool:
    __slots__ = ('_runes', '_counts')

    def __init__(self, runes: Iterable[Rune] = ()):
        self._runes = list(runes)
        self._counts = Counter(self._runes)

    @classmethod
    def for_levels(cls, rune_cls: Type[Rune], levels: Iterable[int]) -> RunePool:
        return cls(rune_cls(level) for level in levels)

    def add(self, rune: Rune):
        self._runes.append(rune)
        self._counts[rune] += 1

    def remove(self, rune: Rune):
        if count := self._counts[rune]:
            self._runes.remove(rune)
            if count == 1:
                del self._counts[rune]
            else:
                self._counts[rune] -= 1
        else:
            raise ValueError(f'Pool does not contain {rune=} so it cannot be removed')

    def discard(self, rune: Rune):
        try:
            self.remove(rune)
        except ValueError:
            pass

    def iter_groups(self) -> Iterator[RuneSet]:
        """Iterate over possible groupings of the runes in this pool.  Assumes all runes are of the same type."""
        # This is based on the powerset recipe here: https://docs.python.org/3/library/itertools.html#itertools-recipes
        for group in chain.from_iterable(combinations(self._runes, n) for n in range(1, 4)):
            yield RuneSet(*group)

    def iter_set_groups(self) -> Iterator[list[RuneSet]]:
        # Approximately O(n^3) brute-force implementation for discovering all possible groupings of RuneSets
        rune_sets = list(self.iter_groups())[::-1]  # Begin by picking the largest sets instead of the smallest ones
        # Ensure each RuneSet gets to be the first set in a group at least once
        for i, rune_set in enumerate(rune_sets):
            # The other sets to potentially include in each group should exclude the current set
            other_sets = deque(rune_sets[:i] + rune_sets[i + 1 :])
            # Iterating only once over other_sets results in missing some potential combinations containing sets with
            # fewer than 3 runes due to the order of the sets, so a group is created for every possible rotation of
            # other_sets
            for _ in range(len(other_sets)):
                group = [rune_set]
                for other_set in other_sets:
                    if not any(other_set.overlaps(s) for s in group):
                        group.append(other_set)
                yield group
                other_sets.rotate(1)

    def unique_set_groups(self) -> set[tuple[RuneSet, ...]]:
        return {tuple(sorted(group, reverse=True)) for group in self.iter_set_groups()}


# region Stat-Specific Rune Classes

# fmt: off
_ACC_EVD_DEBUFF_VALUES = [
    260, 500, 970, 1_900, 3_770,
    7_500, 14_900, 29_700, 59_300, 118_000,
    235_000, 463_000, 835_000, 1_380_000, 2_080_000,
]
_CRIT_VALUES = [60, 100, 190, 370, 730, 1_450, 2_890, 5_770, 11_500, 22_900, 45_700, 91_300, 167_000, 277_000, 416_000]
_DEF_VALUES = [40, 60, 110, 200, 370, 680, 1_240, 2_270, 4_160, 7_600, 13_900, 25_400, 46_400, 84_900, 150_000]
_OFFENSIVE_BASE_STAT_VALUES = [
    60, 100, 180, 330, 620, 1_130, 2_070, 3_800, 6_930, 12_600, 23_100, 42_300, 77_400, 141_000, 250_000
]
# fmt: on

# region Offensive (Left) Runes


class AccuracyRune(Rune, stat='ACC'):
    __slots__ = ()
    values = _ACC_EVD_DEBUFF_VALUES


class AttackRune(Rune, stat='ATK'):
    __slots__ = ()
    # fmt: off
    values = [
        240, 440, 810, 1_480, 2_710,
        4_950, 9_050, 16_500, 30_200, 55_300,
        101_000, 184_000, 338_000, 617_000, 1_090_000,
    ]
    # fmt: on


class CritRune(Rune, stat='CRIT'):
    __slots__ = ()
    values = _CRIT_VALUES


class DebuffAccuracyRune(Rune, stat='Debuff ACC'):
    __slots__ = ()
    values = _ACC_EVD_DEBUFF_VALUES


class PMDefBreakRune(Rune, stat='PMDB'):
    __slots__ = ()
    values = [25, 45, 80, 140, 250, 430, 750, 1_300, 2_200, 3_710, 6_250, 10_400, 15_900, 21_900, 26_900]


class SpeedRune(Rune, stat='SPD'):
    __slots__ = ()
    values = [10, 18, 33, 53, 80, 110, 150, 195, 240, 300, 360, 425, 500, 575, 660]


# endregion


# region Defensive (Right) Runes


class CritResistRune(Rune, stat='CRIT RES'):
    __slots__ = ()
    values = _CRIT_VALUES


class DebuffResistanceRune(Rune, stat='Debuff RES'):
    __slots__ = ()
    values = _ACC_EVD_DEBUFF_VALUES


class EvasionRune(Rune, stat='EVD'):
    __slots__ = ()
    values = _ACC_EVD_DEBUFF_VALUES


class HPRune(Rune, stat='HP'):
    __slots__ = ()
    # fmt: off
    values = [
        1_000, 1_830, 3_340, 6_110, 11_100,
        20_400, 37_300, 68_300, 124_000, 228_000,
        417_000, 762_000, 1_390_000, 2_540_000, 4_510_000,
    ]
    # fmt: on


class MagicDefenseRune(Rune, stat='M.DEF'):
    __slots__ = ()
    values = _DEF_VALUES


class PhysicalDefenseRune(Rune, stat='P.DEF'):
    __slots__ = ()
    values = _DEF_VALUES


# endregion


# region Base Stat Runes


class DexRune(Rune, stat='DEX'):
    __slots__ = ()
    values = _OFFENSIVE_BASE_STAT_VALUES

    @property
    def crit(self) -> int:
        return self.value // 2

    @property
    def evd(self) -> int:
        return self.value // 2


class MagRune(Rune, stat='MAG'):
    __slots__ = ()
    values = _OFFENSIVE_BASE_STAT_VALUES

    @property
    def m_def(self) -> int:
        return self.value

    @property
    def debuff_acc(self) -> int:
        return self.value // 2


class StrRune(Rune, stat='STR'):
    __slots__ = ()
    values = _OFFENSIVE_BASE_STAT_VALUES

    @property
    def p_def(self) -> int:
        return self.value

    @property
    def acc(self) -> int:
        return self.value // 2


class StaRune(Rune, stat='STA'):
    __slots__ = ()
    values = [35, 60, 90, 150, 270, 510, 930, 1_700, 3_120, 5_700, 10_400, 19_000, 34_800, 63_700, 112_000]

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
                rune_set = self.rune_cls.get_rune_set(*sorted(levels, reverse=True))
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


class PartyMember:
    __slots__ = ('char', '_speed_rune_set', 'after_delta')

    _speed_rune_set: RuneSet

    def __init__(self, char: Character, speed_rune_set: AnyRuneLevels | RuneSet = None, after_delta: int = 150):
        self.char = char
        self.speed_rune_set = speed_rune_set
        self.after_delta = after_delta

    @property
    def speed_rune_set(self) -> RuneSet:
        return self._speed_rune_set

    @speed_rune_set.setter
    def speed_rune_set(self, value: AnyRuneLevels | None | RuneSet):
        if isinstance(value, RuneSet):
            self._speed_rune_set = value
        elif not value:
            self._speed_rune_set = RuneSet.new(SpeedRune)
        else:
            try:
                self._speed_rune_set.set_levels(value)
            except AttributeError:
                # self._speed_rune_set = RuneSet.new(SpeedRune)
                # self._speed_rune_set.set_levels(value)
                self._speed_rune_set = SpeedRune.get_rune_set(*value)

    @property
    def speed(self) -> int:
        """
        Note: the following bonuses are not currently considered here:
        - Stella: 25%
            - Start of Battle, 1T, Cannot be dispelled
            - Metatron LR UW
        - Liselotte: 20%
            - Start of Battle, 1T, Cannot be dispelled
            - Michael UR UW
        - Primavera:
            - 3% per ally alive for full team (up to 15%)
                - Passive, Cannot be dispelled
                - Level 201+
        - Rusalka:
            - 30%
                - Start of Battle, 1T
                - Metatron LR UW
            - 30%
                - Passive, On Death (Level 201+)
        """
        return self.char.speed + self._speed_rune_set.total

    def reset_speed(self):
        self._speed_rune_set.reset()

    def copy(self) -> PartyMember:
        return self.__class__(self.char, self._speed_rune_set, self.after_delta)

    def with_levels(self, levels: AnyRuneLevels | None) -> PartyMember:
        return self.__class__(self.char, levels)

    def __eq__(self, other: PartyMember) -> bool:
        return self.char == other.char and self.speed == other.speed

    def __lt__(self, other: PartyMember) -> bool:
        return (self.speed, self.char) < (other.speed, other.char)  # noqa


class Party:
    __slots__ = ('members',)
    members: list[PartyMember]

    def __init__(self, members: Iterable[PartyMember | Character], deltas: Sequence[int] = ()):
        self.members = [m if isinstance(m, PartyMember) else PartyMember(m) for m in members]
        if deltas:
            for member, delta in zip(self.members, deltas):
                member.after_delta = delta

    def copy(self) -> Party:
        clone = self.__class__.__new__(self.__class__)
        clone.members = [m.copy() for m in self.members]
        return clone
        # return self.__class__(m.copy() for m in self.members)

    def reset_speed(self):
        for member in self.members:
            member.reset_speed()

    def assign_speed_runes(self, level_groups: Collection[AnyRuneLevels | RuneSet], reset: bool = False):
        for member, levels in zip(self.members, level_groups):
            member.speed_rune_set = levels

        if reset:
            for member in self.members[len(level_groups) :]:
                member.reset_speed()

    @property
    def is_speed_tuned(self) -> bool:
        return self._is_speed_tuned(150)

    @property
    def is_speed_ordered(self) -> bool:
        """Returns True if party members' speeds are in descending order, even if not perfectly tuned"""
        return self._is_speed_tuned(0)

    def _is_speed_tuned(self, min_offset: int) -> bool:
        min_speed = 0
        for member in self.members[::-1]:
            if (speed := member.speed) >= min_speed:  # speed is stored since member.speed is a simple property
                min_speed = speed + min_offset
            else:
                return False

        return True

    def speed_order_status(self) -> tuple[bool, bool]:
        # returns tuple of (tuned, ordered)
        min_tuned, min_ordered = 0, 0
        tuned = True
        for member in self.members[::-1]:
            speed = member.speed
            if speed < min_ordered:
                return False, False
            elif speed < min_tuned:
                tuned = False

            min_tuned = speed + member.after_delta
            min_ordered = speed

        return tuned, True

    def tune_speed(self):
        calculator = RuneCalculator(SpeedRune)
        min_speed = 0
        for member in self.members[::-1]:
            if member.speed < min_speed:
                log.debug(f'Updating runes for {member.char} because speed={member.speed} < {min_speed=}')
                # Rune levels need to calculate from base delta to take current runes into account
                rune_set = calculator.find_closest_min_ticket_set(min_speed - member.char.speed)
                member.speed_rune_set = rune_set
                # member.speed_rune_levels = sorted(rune_set.levels, reverse=True)

            min_speed = member.speed + 150

    def allocate_speed_runes(self, levels: Collection[int]) -> Party:
        """
        Allocate speed runes with the specified levels such that this party is speed tuned in the order that the
        members were provided when this Party was initialized.
        """
        # TODO: Alt approach: call tune_speed, and see if runes are available that are >= the suggested levels,
        #  apply those, then call tune_speed again with the updated speed, and apply runes to the next char from the
        #  suggested set the same way?

        if len(levels) >= 10:
            log_lvl = logging.INFO
            log.warning(
                'Determining the best rune allocation for more than 10 level values may be EXTREMELY slow',
                extra={'color': 'red'},
            )
        else:
            log_lvl = logging.DEBUG

        set_groups = RunePool.for_levels(SpeedRune, levels).unique_set_groups()
        n_tests = sum(factorial(len(g) + 1) for g in set_groups)
        log.log(log_lvl, f'Processing {len(set_groups)} groups of speed rune sets with {n_tests:,d} total permutations')

        # This still needs further optimization for cases where 10+ levels are provided...
        tuned_candidates, ordered_candidates = [], []
        with ProcessPoolExecutor() as executor:
            futures = {executor.submit(self._get_alloc_candidates, set_group): set_group for set_group in set_groups}
            try:
                for future in as_completed(futures):
                    new_tuned_candidates, new_ordered_candidates = future.result()
                    tuned_candidates += new_tuned_candidates
                    ordered_candidates += new_ordered_candidates
            except BaseException:
                executor.shutdown(cancel_futures=True)
                raise

        log.debug(f'Found candidates: tuned={len(tuned_candidates)}, ordered={len(ordered_candidates)}')
        if candidates := tuned_candidates or ordered_candidates:
            # TODO: This does not provide very consistent results - need to sort by more members' speeds maybe?
            return max(candidates, key=_candidate_key)
        else:
            return self

    def _get_alloc_candidates(self, set_group: tuple[RuneSet, ...]) -> tuple[list[Party], list[Party]]:
        tuned_candidates, ordered_candidates = [], []
        # TODO: This can use an extreme amount of memory - the overall approach needs to be refactored
        for group_order in permutations([RuneSet(SpeedRune(0)), *set_group]):
            self.assign_speed_runes(group_order, reset=True)
            is_tuned, is_ordered = self.speed_order_status()
            if is_tuned:
                tuned_candidates.append(self.copy())
            elif is_ordered:
                # TODO: Maybe parameterize which char number to filter for delta on?  i.e., ensure faster than 0 or 1
                #  for cases like merlyn+matilda where order between merlyn/matilda doesn't matter
                if (self.members[0].speed - self.members[-1].speed) >= 150:
                    ordered_candidates.append(self.copy())

        return tuned_candidates, ordered_candidates


def _candidate_key(party: Party):
    last_speed = party.members[-1].speed
    return (last_speed, party.members[0].speed - last_speed)


def speed_tune(members: Iterable[PartyMember | Character]) -> list[PartyMember]:
    """
    :param members: A list of :class:`PartyMember` or :class:`~.mb_models.Character` objects, in the order that
      they should act.
    :return: A list of :class:`PartyMember` objects with :attr:`PartyMember.speed_rune_levels` updated so that they act
      in the specified order.
    """
    party = Party(members)
    party.tune_speed()
    return party.members
