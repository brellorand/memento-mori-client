"""
MB entities related to the main quest bosses / battles
"""

from __future__ import annotations

import logging
from functools import cached_property

from mm.properties import DataProperty
from .base import MBEntity

__all__ = ['Quest']
log = logging.getLogger(__name__)


class Quest(MBEntity, file_name_fmt='QuestMB'):
    """
    Example:
        "Id": 484,
        "IsIgnore": null,
        "Memo": "19-8",
        "BaseBattlePower": 109583916,
        "ChapterId": 19,
        "GoldPerMinute": 333,
        "MinCharacterExp": 156468,
        "MinPlayerExp": 107328,
        "PotentialJewelPerDay": 1042,
        "Population": 22133728,
        "QuestDifficultyType": 1,
        "QuestMapBuildingId": 103
    """

    chapter: int = DataProperty('ChapterId')
    memo: str = DataProperty('Memo')

    @cached_property
    def number(self) -> tuple[int, int]:
        chapter, num = self.memo.split('-', 1)
        return (int(chapter), int(num))

    def __str__(self) -> str:
        return self.memo

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}({self.memo!r}, id={self.id})>'
