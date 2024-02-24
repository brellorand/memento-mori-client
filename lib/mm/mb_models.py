"""
Classes that wrap API responses
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from functools import cached_property
from typing import TYPE_CHECKING, Any, Type, TypeVar, Literal, Iterator

from .enums import Region
from .data import DictWrapper
from .utils import DataProperty

if TYPE_CHECKING:
    from pathlib import Path
    from .client import DataClient

__all__ = []
log = logging.getLogger(__name__)

T = TypeVar('T')

# ls -1 temp/mb/TextResource* | sed 's#temp/mb/TextResource##g' | sed -E "s#(....)MB\.json#'\\1',#g" | paste -sd ' '
Locale = Literal['DeDe', 'EnUs', 'EsMx', 'FrFr', 'IdId', 'JaJp', 'KoKr', 'PtBr', 'RuRu', 'ThTh', 'ViVn', 'ZhCn', 'ZhTw']
LOCALES = ['DeDe', 'EnUs', 'EsMx', 'FrFr', 'IdId', 'JaJp', 'KoKr', 'PtBr', 'RuRu', 'ThTh', 'ViVn', 'ZhCn', 'ZhTw']


class MB:
    def __init__(
        self,
        client: DataClient,
        *,
        data: dict[str, Any] = None,
        use_cached: bool = True,
        json_cache_map: dict[str, Path] = None,
        locale: Locale = 'EnUS',
    ):
        self._client = client
        self.__data = data
        self._use_cached = use_cached
        self._json_cache_map = json_cache_map or {}
        self.locale = locale

    @cached_property
    def _data(self) -> dict[str, Any]:
        if self.__data:
            return self.__data
        return self._client._get_mb_catalog()

    @cached_property
    def file_map(self) -> dict[str, FileInfo]:
        """
        Example info map:
        {
            'AchieveRankingRewardMB': {'Hash': 'fd9d21d514779c2e3758992907156420', 'Name': 'AchieveRankingRewardMB', 'Size': 47188},
            'ActiveSkillMB': {'Hash': 'ae15826e4bd042d14a61dad219c91932', 'Name': 'ActiveSkillMB', 'Size': 372286},
            ...
            'VipMB': {'Hash': 'be0114a5a24b5350459cdba6eea6bbcf', 'Name': 'VipMB', 'Size': 16293},
            'WorldGroupMB': {'Hash': '34afb2d419e8153a451d53b54d9829ae', 'Name': 'WorldGroupMB', 'Size': 20907}
        }
        """
        return {name: FileInfo(data) for name, data in self._data['MasterBookInfoMap'].items()}

    def get_data(self, name: str):
        if json_path := self._json_cache_map.get(name):
            return json.loads(json_path.read_text('utf-8'))
        return self._client.get_mb_data(name, use_cached=self._use_cached)

    def _iter_mb_objects(self, cls: Type[T], name: str) -> Iterator[T]:
        for row in self.get_data(name):
            yield cls(self, row)

    def _get_mb_objects(self, cls: Type[T], name: str) -> list[T]:
        return [cls(self, row) for row in self.get_data(name)]

    def _get_mb_id_obj_map(self, cls: Type[T], name: str) -> dict[int, T]:
        return {row['Id']: cls(self, row) for row in self.get_data(name)}

    @cached_property
    def world_groups(self) -> list[WorldGroup]:
        return self._get_mb_objects(WorldGroup, 'WorldGroupMB')

    @cached_property
    def items(self) -> dict[int, dict[int, Item]]:
        type_id_item_map = {}
        for item in self._iter_mb_objects(Item, 'ItemMB'):
            try:
                type_id_item_map[item.item_type][item.item_id] = item
            except KeyError:
                type_id_item_map[item.item_type] = {item.item_id: item}
        return type_id_item_map

    def get_item(self, item_type: int, item_id: int) -> Item:
        return self.items[item_type][item_id]

    @cached_property
    def text_resource_map(self) -> dict[str, str]:
        return {res.key: res.value for res in self._iter_mb_objects(TextResource, f'TextResource{self.locale}MB')}

    @cached_property
    def vip_levels(self) -> list[VipLevel]:
        return self._get_mb_objects(VipLevel, 'VipMB')


class FileInfo(DictWrapper):
    hash: str = DataProperty('Hash')
    name: str = DataProperty('Name')
    size: int = DataProperty('Size', int)


def _parse_dt(dt_str: str) -> datetime:
    return datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')


class MBEntity:
    __slots__ = ('data', 'mb')

    id: int = DataProperty('Id')
    ignore: bool = DataProperty('IsIgnore', default=False)

    def __init__(self, mb: MB, data: dict[str, Any]):
        self.mb = mb
        self.data = data


class WorldGroup(MBEntity):
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
    first_legend_league_dt: datetime = DataProperty('StartLegendLeagueDateTime', type=_parse_dt)
    world_ids: list[int] = DataProperty('WorldIdList')

    @cached_property
    def grand_battles(self) -> list[tuple[datetime, datetime]]:
        return [
            (_parse_dt(row['StartTime']), _parse_dt(row['EndTime']))
            for row in self.data['GrandBattleDateTimeList']
        ]


class TextResource(MBEntity):
    """A row in TextResource[locale]MB"""

    key = DataProperty('StringKey')
    value = DataProperty('Text')


class Item(MBEntity):
    """
    Represents a row in ItemMB

    Example content:
        "Id": 1,
        "IsIgnore": null,
        "Memo": "ダイヤ（無償）",
        "DescriptionKey": "[ItemDescription1]",
        "DisplayName": "[ItemDisplayName1]",
        "EndTime": null,
        "ItemId": 1,
        "ItemRarityFlags": 0,
        "ItemType": 1,
        "MaxItemCount": 0,
        "NameKey": "[ItemName1]",
        "IconId": 9,
        "SecondaryFrameNum": 0,
        "SecondaryFrameType": 0,
        "SortOrder": 0,
        "StartTime": null,
        "TransferSpotId": 0
    """

    item_id: int = DataProperty('ItemId')
    item_type: int = DataProperty('ItemType')
    icon_id: int = DataProperty('IconId')
    name_key = DataProperty('NameKey')                  # matches a TextResource.key (StringKey) value
    description_key = DataProperty('DescriptionKey')    # matches a TextResource.key (StringKey) value
    display_name_key = DataProperty('DisplayName')      # matches a TextResource.key (StringKey) value

    @cached_property
    def name(self) -> str:
        return self.mb.text_resource_map[self.name_key]

    @cached_property
    def display_name(self) -> str:
        return self.mb.text_resource_map[self.display_name_key]

    @cached_property
    def description(self) -> str:
        return self.mb.text_resource_map[self.description_key]


class VipLevel(MBEntity):
    _item_list: list[dict[str, int]] = DataProperty('DailyRewardItemList')
    level: int = DataProperty('Lv')

    @cached_property
    def daily_rewards(self) -> list[tuple[Item, int]]:
        """List of daily item rewards and their quantities"""
        return [(self.mb.get_item(row['ItemType'], row['ItemId']), row['ItemCount']) for row in self._item_list]
