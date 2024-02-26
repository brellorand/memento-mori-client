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

RANK_BONUS_STATS = [
    'ACC', 'ACC %', 'ATK', 'Counter', 'CRIT', 'CRIT DMG Boost', 'Debuff ACC', 'DEF Break', 'DMG Boost',
    'HP', 'HP %', 'HP Drain', 'SPD',
]


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

    def _get_mb_id_obj_map(self, cls: Type[T], name: str, key: str = 'Id') -> dict[int, T]:
        return {row[key]: cls(self, row) for row in self.get_data(name)}

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

    @cached_property
    def player_ranks(self) -> dict[int, PlayerRank]:
        return self._get_mb_id_obj_map(PlayerRank, 'PlayerRankMB', key='Rank')


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
    """
    Example:
        "Id": 1,
        "IsIgnore": null,
        "Memo": null,
        "AutoBattlePlayerExpBonus": 0,
        "DailyRewardItemList": [
            {"ItemCount": 1, "ItemId": 1, "ItemType": 19}, {"ItemCount": 5000, "ItemId": 1, "ItemType": 3}
        ],
        "DungeonBattleCoinBonus": 0,
        "DungeonBattleGoldBonus": 0,
        "DungeonBattleMissedCompensationCount": 0,
        "IsDestinyGachaAvailable": false,
        "IsDestinyGachaLogAvailable": false,
        "IsStarsGuidanceGachaAvailable": false,
        "IsStarsGuidanceGachaLogAvailable": false,
        "IsLockEquipmentTrainingAvailable": false,
        "IsMultipleBountyQuestAvailable": false,
        "IsMultipleQuickStartGuildRaidAvailable": false,
        "IsQuickBossBattleAvailable": false,
        "IsQuickStartGuildRaidAvailable": false,
        "IsRefundEquipmentMergeAvailable": false,
        "LoginBonusMissedCompensationCount": 0,
        "Lv": 0,
        "MaxBossBattleUseCurrencyCount": 1,
        "MaxCharacterBoxPlus": 0,
        "MaxGuildRaidChallengeCount": 2,
        "MaxQuickUseCurrencyCount": 2,
        "MaxShopItemCountPlus": 0,
        "MaxSoloQuestCount": 6,
        "MaxTeamQuestCount": 1,
        "QuickBattlePlayerExpBonus": 0,
        "ReachRewardItemList": null,
        "RequiredExp": 0,
        "VipGiftInfoList": [
            {
                "GetItemList": [{"ItemCount": 10, "ItemId": 4, "ItemType": 13}],
                "RequiredItemList": [{"ItemCount": 50, "ItemId": 1, "ItemType": 1}],
                "VipGiftId": 0
            }
        ]
    """

    _item_list: list[dict[str, int]] = DataProperty('DailyRewardItemList')
    level: int = DataProperty('Lv')

    @cached_property
    def daily_rewards(self) -> list[tuple[Item, int]]:
        """List of daily item rewards and their quantities"""
        return [(self.mb.get_item(row['ItemType'], row['ItemId']), row['ItemCount']) for row in self._item_list]


class PlayerRank(MBEntity):
    """
    Example:
        "Id": 1,
        "IsIgnore": null,
        "Memo": null,
        "AttackPowerBonus": 0,
        "CriticalBonus": 0,
        "CriticalDamageEnhanceBonus": 0,
        "DamageEnhanceBonus": 0,
        "DamageReflectBonus": 0,
        "DebuffHitBonus": 0,
        "DefensePenetrationBonus": 0,
        "HitBonus": 0,
        "HpBonus": 0,
        "HpPercentBonus": 0,
        "HpDrainBonus": 0,
        "HitDirectPercentBonus": 0,
        "LevelLinkMemberMaxCount": 0,
        "Rank": 1,
        "RequiredTotalExp": 0,
        "StartTimeFixJST": "2020-01-01 00:00:00",
        "SpeedBonus": 0
    """

    rank: int = DataProperty('Rank')
    level_link_slots: int = DataProperty('LevelLinkMemberMaxCount')

    accuracy_bonus: int = DataProperty('HitBonus')
    accuracy_percent_bonus: int = DataProperty('HitDirectPercentBonus')  # Not sure about name; no present values > 0
    attack_bonus: int = DataProperty('AttackPowerBonus')
    counter_bonus: int = DataProperty('DamageReflectBonus')  # Not sure about name
    crit_rate_bonus: int = DataProperty('CriticalBonus')
    crit_damage_bonus: int = DataProperty('CriticalDamageEnhanceBonus')
    damage_bonus: int = DataProperty('DamageEnhanceBonus')
    debuff_accuracy_bonus: int = DataProperty('DebuffHitBonus')
    def_break_bonus: int = DataProperty('DefensePenetrationBonus')
    hp_bonus: int = DataProperty('HpBonus')
    hp_percent_bonus: int = DataProperty('HpPercentBonus', type=lambda v: v // 100)
    hp_drain_bonus: int = DataProperty('HpDrainBonus')
    speed_bonus: int = DataProperty('SpeedBonus')

    def get_stat_bonuses(self) -> dict[str, int]:
        # As of 2024-02-26, only ATK, HP, and HP % bonuses have any non-zero values for any given rank
        return {
            'ACC': self.accuracy_bonus,
            'ACC %': self.accuracy_percent_bonus,
            'ATK': self.attack_bonus,
            'Counter': self.counter_bonus,
            'CRIT': self.crit_rate_bonus,
            'CRIT DMG Boost': self.crit_damage_bonus,
            'Debuff ACC': self.debuff_accuracy_bonus,
            'DEF Break': self.def_break_bonus,
            'DMG Boost': self.damage_bonus,  # Is this key accurate? This does stat not appear in help text
            'HP': self.hp_bonus,
            'HP %': self.hp_percent_bonus,
            'HP Drain': self.hp_drain_bonus,
            'SPD': self.speed_bonus,
        }
