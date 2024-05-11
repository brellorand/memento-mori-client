"""
Classes that wrap API responses
"""

from __future__ import annotations

import logging
from datetime import datetime
from functools import cached_property

from mm.enums import Region
from mm.utils import DataProperty
from .base import MBEntity
from .utils import parse_dt

__all__ = ['WorldGroup']
log = logging.getLogger(__name__)


class WorldGroup(MBEntity, file_name_fmt='WorldGroupMB'):
    """
    Represents a row in WorldGroupMB

    Example content:
        "Id": 23,
        "IsIgnore": null,
        "Memo": "us",
        "EndTime": "2100-01-01 00:00:00",
        "EndLegendLeagueDateTime": "2100-01-01 00:00:00",
        "TimeServerId": 4,
        "StartTime": "2023-08-08 04:00:00",
        "GrandBattleDateTimeList": [
            {"EndTime": "2023-08-28 03:59:59", "StartTime": "2023-08-21 04:00:00"},
            ...
            {"EndTime": "2024-02-19 03:59:59", "StartTime": "2024-02-12 04:00:00"}
        ],
        "StartLegendLeagueDateTime": "2023-09-05 04:00:00",
        "WorldIdList": [4001, 4002, 4003, 4004, 4005, 4006, 4007, 4008]
    """

    region: Region = DataProperty('TimeServerId', type=Region)
    first_legend_league_dt: datetime = DataProperty('StartLegendLeagueDateTime', type=parse_dt)
    world_ids: list[int] = DataProperty('WorldIdList')

    @cached_property
    def grand_battles(self) -> list[tuple[datetime, datetime]]:
        return [
            (parse_dt(row['StartTime']), parse_dt(row['EndTime']))
            for row in self.data['GrandBattleDateTimeList']
        ]
