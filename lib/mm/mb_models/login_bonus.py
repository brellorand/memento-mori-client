"""
MB entities related to login bonus rewards
"""

from __future__ import annotations

import logging
from functools import cached_property
from typing import TYPE_CHECKING, TypedDict

from mm.properties import DataProperty
from .base import MBEntity

# from .items import ItemAndCount
from .utils import LocalizedString, parse_dt

if TYPE_CHECKING:
    from datetime import datetime

__all__ = ['MonthlyLoginBonus', 'MonthlyLoginBonusRewardList', 'LimitedLoginBonus', 'LimitedLoginBonusRewardList']
log = logging.getLogger(__name__)


class MonthlyLoginBonus(MBEntity, file_name_fmt='MonthlyLoginBonusMB'):
    """
    Example:
        {"Id": 33, "IsIgnore": null, "Memo": null, "ImageId": 1, "RewardListId": 2, "YearMonth": "2024-09"},
    """

    image_id: int = DataProperty('ImageId')
    reward_list_id: int = DataProperty('RewardListId')
    year_and_month: str = DataProperty('YearMonth')

    @cached_property
    def reward_list(self) -> MonthlyLoginBonusRewardList:
        return self.mb.monthly_login_bonus_rewards[self.reward_list_id]


class MonthlyLoginBonusRewardList(MBEntity, file_name_fmt='MonthlyLoginBonusRewardListMB'):
    """
    Example:
        "Id": 3,
        "IsIgnore": null,
        "Memo": "28日用",
        "DailyRewardList": [
            {"Day": 1, "RewardItem": {"ItemCount": 2, "ItemId": 7, "ItemType": 10}},
            {"Day": 2, "RewardItem": {"ItemCount": 100, "ItemId": 1, "ItemType": 1}},
            ...
            {"Day": 28, "RewardItem": {"ItemCount": 1, "ItemId": 14, "ItemType": 10}}
        ],
        "LoginCountRewardList": [
            {
                "DayCount": 3, "ImagePath": "icon_treasure_box", "PositionX": 15,
                "RewardItemList": [
                    {"ItemCount": 200, "ItemId": 1, "ItemType": 1}, {"ItemCount": 1, "ItemId": 17, "ItemType": 10}
                ]
            },
            {
                "DayCount": 7, "ImagePath": "icon_treasure_box", "PositionX": 40,
                "RewardItemList": [
                    {"ItemCount": 200, "ItemId": 1, "ItemType": 1}, {"ItemCount": 1, "ItemId": 17, "ItemType": 10}
                ]
            },
            ...
        ]
    """

    daily_rewards: list[DailyReward] = DataProperty('DailyRewardList')
    login_count_rewards: list[LoginCountReward] = DataProperty('LoginCountRewardList')


class LimitedLoginBonus(MBEntity, file_name_fmt='LimitedLoginBonusMB'):
    """
    Example:
        "Id": 4,
        "IsIgnore": null,
        "Memo": "2023_1周年ログインボーナス",
        "AppealTextKey": "[LimitedLoginBonusAppeal1]",
        "CharacterImageId": 45,
        "DelayDays": 0,
        "RewardBackgroundImageId": 5,
        "RewardListId": 4,
        "SpecialRewardAppealTextKey": "[LimitedLoginBonusSpecialRewardAppeal3]",
        "SpecialRewardBackgroundImageId": 5,
        "SpecialRewardCountTextColor": "#473D3BFF",
        "SpecialRewardLabelTextColor": "#473D3BFF",
        "SpecialRewardLabelTextOutlineColor": "#FFFFFFFF",
        "TitleTextKey": "[LimitedLoginBonusTitle4]",
        "StartTime": "2023-10-18 04:00:00",
        "EndTime": "2023-11-16 03:59:59"
    """

    title: str = LocalizedString('TitleTextKey')
    appeal_text: str = LocalizedString('AppealTextKey')
    special_reward_appeal_text: str = LocalizedString('SpecialRewardAppealTextKey')

    reward_list_id: int = DataProperty('RewardListId')
    start_time: datetime = DataProperty('StartTime', parse_dt)
    end_time: datetime = DataProperty('EndTime', parse_dt)

    @cached_property
    def reward_list(self) -> LimitedLoginBonusRewardList:
        return self.mb.limited_login_bonus_rewards[self.reward_list_id]


class LimitedLoginBonusRewardList(MBEntity, file_name_fmt='LimitedLoginBonusRewardListMB'):
    """
    Example:
        "Id": 4,
        "IsIgnore": null,
        "Memo": "2023_一周年ログインボーナス",
        "DailyRewardList": [
            {"DailyRewardItem": {"ItemCount": 10, "ItemId": 2, "ItemType": 16}, "Date": 1, "RarityFlags": 0},
            {"DailyRewardItem": {"ItemCount": 10, "ItemId": 1, "ItemType": 18}, "Date": 2, "RarityFlags": 0},
            ...,
            {"DailyRewardItem": {"ItemCount": 15, "ItemId": 2, "ItemType": 16}, "Date": 14, "RarityFlags": 0}
        ],
        "EveryDayRewardItem": null,
        "ExistEveryDayReward": false,
        "ExistSpecialReward": true,
        "SpecialRewardItem": {
            "Date": 14, "SpecialRewardItem": {"ItemCount": 2000, "ItemId": 2, "ItemType": 11}, "RarityFlags": 0
        }
    """

    daily_rewards: list[DailyRewardItem] = DataProperty('DailyRewardList')
    special_reward_item: SpecialRewardItem | None = DataProperty('SpecialRewardItem', default=None)
    special_reward_exists: bool = DataProperty('ExistSpecialReward')


class ItemAndCountDict(TypedDict):
    ItemCount: int
    ItemId: int
    ItemType: int


class DailyReward(TypedDict):
    Day: int
    RewardItem: ItemAndCountDict


class LoginCountReward(TypedDict):
    DayCount: int
    ImagePath: str
    PositionX: int
    RewardItemList: list[ItemAndCountDict]


class DailyRewardItem(TypedDict):
    DailyRewardItem: ItemAndCountDict
    Date: int
    RarityFlags: int


class SpecialRewardItem(TypedDict):
    Date: int
    SpecialRewardItem: ItemAndCountDict
    RarityFlags: int
