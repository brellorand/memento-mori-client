"""
Classes that wrap API responses
"""

from __future__ import annotations

import logging
from datetime import datetime
from functools import cached_property
from typing import Any

from .enums import Region
from .utils import DataProperty, parse_ms_epoch_ts

__all__ = ['OrtegaInfo', 'GameData', 'WorldInfo', 'MBFileMap']
log = logging.getLogger(__name__)


class DictWrapper:
    __slots__ = ('data',)

    def __init__(self, data: dict[str, Any]):
        self.data = data


# region Auth Client Responses


class OrtegaInfo(DictWrapper):
    status_code: int = DataProperty('ortegastatuscode', int)
    next_access_token: str = DataProperty('orteganextaccesstoken')  # Usually an empty string
    asset_version: str = DataProperty('ortegaassetversion')
    mb_version: str = DataProperty('ortegamasterversion')
    utc_now_timestamp: str = DataProperty('ortegautcnowtimestamp')
    mb_version_dt: datetime = DataProperty('ortegamasterversion', type=parse_ms_epoch_ts)
    utc_now_timestamp_dt: datetime = DataProperty('ortegautcnowtimestamp', type=parse_ms_epoch_ts)


class WorldInfo(DictWrapper):
    """Represents a single row in the ``WorldInfos`` list in the ``auth/getDataUri`` response"""

    game_server_id: int = DataProperty('GameServerId')
    id: int = DataProperty('Id')
    start_time: datetime = DataProperty('StartTime')

    def __repr__(self) -> str:
        start = self.start_time.isoformat(' ')
        return f'<{self.__class__.__name__}[region={self.region}, num={self.number}, {start=!s}]>'

    @cached_property
    def region(self) -> Region:
        return Region(self.id // 1000)

    @cached_property
    def number(self) -> int:
        return self.id - (self.region * 1000)


class GameData(DictWrapper):
    """
    The parsed content from the ``auth/getDataUri`` response.

    Example:
    {
        'AppAssetVersionInfo': {'EnvType': 0, 'IsSkipAssetDownload': False, 'Version': '2.8.1'},
        'WorldInfos': [
            {'GameServerId': 1, 'Id': 1001, 'StartTime': datetime.datetime(2022, 10, 17, 4, 0, tzinfo=datetime.timezone.utc)},
            ...
            {'GameServerId': 60, 'Id': 6020, 'StartTime': datetime.datetime(2024, 1, 26, 4, 0, tzinfo=datetime.timezone.utc)}
        ],
        'MaintenanceDebugUserInfos': [
            {'UserId': 826639594190, 'PlayerId': 855534869003, 'IsDebugUser': True},
            ...
            {'UserId': 204182531577, 'PlayerId': 669925568060, 'IsDebugUser': True}
        ],
        'MaintenanceInfos': [
            {
                'MaintenanceServerType': 0,
                'StartTimeFixJST': datetime.datetime(2024, 2, 7, 14, 30, tzinfo=datetime.timezone.utc),
                'EndTimeFixJST': datetime.datetime(2024, 2, 7, 17, 30, tzinfo=datetime.timezone.utc),
                'MaintenancePlatformTypes': [0],
                'MaintenanceAreaType': 0,
                'AreaIds': [],
                'MaintenanceFunctionTypes': []
            },
            ...
        ],
        'ManagementNewUserInfos': [
            {
                'EndTimeFixJST': datetime.datetime(2100, 1, 1, 0, 0, tzinfo=datetime.timezone.utc),
                'IsUnableToCreateUser': False,
                'ManagementNewUserType': 0,
                'StartTimeFixJST': datetime.datetime(2100, 1, 1, 0, 0, tzinfo=datetime.timezone.utc),
                'TargetIds': [1]
            },
            ...
        ],
        'AssetCatalogFixedUriFormat': 'https://cdn-mememori.akamaized.net/asset/MementoMori/{0}',
        'MasterUriFormat': 'https://cdn-mememori.akamaized.net/master/prd1/version/{0}/{1}',
        'RawDataUriFormat': 'https://cdn-mememori.akamaized.net/asset/MementoMori/Raw/{0}',
        'TitleInfo': {
            'BgmNumberJP': 1,
            'BgmNumberUS': 16,
            'MovieNumber': 12,
            'LogoNumber': 0,
            'X': 20.0,
            'Y': 113.0,
            'Scale': 1.0,
            'AnchorMinX': 0.20000000298023224,
            'AnchorMinY': 0.699999988079071,
            'AnchorMaxX': 0.20000000298023224,
            'AnchorMaxY': 0.699999988079071
        }
    }
    """

    version: str = DataProperty('AppAssetVersionInfo.Version')
    asset_catalog_uri_fmt: str = DataProperty('AssetCatalogFixedUriFormat')
    mb_uri_fmt: str = DataProperty('MasterUriFormat')
    raw_data_uri_fmt: str = DataProperty('RawDataUriFormat')

    def __repr__(self) -> str:
        worlds = len(self.data['WorldInfos'])
        return f'<{self.__class__.__name__}[version={self.version}, {worlds=}]>'

    @cached_property
    def region_world_map(self) -> dict[Region, list[WorldInfo]]:
        region_world_map = {r: [] for r in Region}
        for row in self.data['WorldInfos']:
            world = WorldInfo(row)
            region_world_map[world.region].append(world)
        return region_world_map

    def get_world(self, world_id: int) -> WorldInfo:
        worlds = self.region_world_map.get(Region.for_world(world_id), [])
        if world := next((w for w in worlds if w.id == world_id), None):
            return world
        raise ValueError(f'Invalid {world_id=} - could not find matching world data')

    @cached_property
    def uri_formats(self) -> dict[str, str]:
        return {
            'asset_catalog': self.asset_catalog_uri_fmt,
            'mb_catalog': self.mb_uri_fmt,
            'raw_data': self.raw_data_uri_fmt,
        }


# endregion


class MBFileMap(DictWrapper):
    @cached_property
    def files(self) -> dict[str, FileInfo]:
        return {name: FileInfo(data) for name, data in self.data['MasterBookInfoMap'].items()}


class FileInfo(DictWrapper):
    hash: str = DataProperty('Hash')
    name: str = DataProperty('Name')
    size: int = DataProperty('Size', int)


def _parse_dt(dt_str: str) -> datetime:
    return datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')


class WorldGroup(DictWrapper):
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

    id: int = DataProperty('Id')
    region: Region = DataProperty('TimeServerId', type=Region)
    first_legend_league_dt: datetime = DataProperty('StartLegendLeagueDateTime', type=_parse_dt)
    world_ids: list[int] = DataProperty('WorldIdList')

    @cached_property
    def grand_battles(self) -> list[tuple[datetime, datetime]]:
        return [
            (_parse_dt(row['StartTime']), _parse_dt(row['EndTime']))
            for row in self.data['GrandBattleDateTimeList']
        ]
