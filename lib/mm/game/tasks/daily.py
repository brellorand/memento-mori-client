"""
Daily Tasks that can be performed when logged in to a specific world
"""

from __future__ import annotations

import logging
from functools import cached_property
from typing import TYPE_CHECKING

from mm.enums import TransferSpotType
from ..utils import wait
from .task import DailyTask

if TYPE_CHECKING:
    from mm import typing as t
    from mm.mb_models.login_bonus import LimitedLoginBonusRewardList
    from ..models import MyPage

__all__ = ['ClaimDailyVIPGift', 'ClaimDailyLoginRewards', 'ClaimLimitedDailyLoginRewards']
log = logging.getLogger(__name__)


class ClaimDailyVIPGift(DailyTask):
    cli_name = 'vip_gift'
    cannot_perform_msg = 'The daily VIP gift was already claimed'

    def can_perform(self) -> bool:
        return self.world_session.user_sync_data.has_vip_daily_gift

    def perform_task(self):
        if self.config.dry_run:
            log.info('[DRY RUN] Would claim daily VIP gift')
            return

        log.info('Claiming daily VIP gift')
        # TODO: Only print the items that were received
        return self.world_session.get_daily_vip_gift()


class ClaimDailyLoginRewards(DailyTask):
    cli_name = 'daily_login'
    cannot_perform_msg = 'The daily login rewards were already claimed'

    @cached_property
    def login_bonus_info(self) -> t.GetMonthlyLoginBonusInfoResponse:
        return self.world_session.get_monthly_login_bonus_info()

    @cached_property
    def _daily_reward_available(self) -> bool:
        return self.mm_time.day not in self.login_bonus_info['ReceivedDailyRewardDayList']

    @cached_property
    def _count_rewards_available(self) -> list[int]:
        days_received = len(self.login_bonus_info['ReceivedDailyRewardDayList'])
        received_counts = self.login_bonus_info['ReceivedLoginCountRewardDayList']

        available = []
        login_bonus = self.mb.monthly_login_bonuses[self.login_bonus_info['MonthlyLoginBonusId']]
        for count_reward in login_bonus.reward_list.login_count_rewards:
            if count_reward['DayCount'] <= days_received and count_reward['DayCount'] not in received_counts:
                available.append(count_reward['DayCount'])

        return available

    def can_perform(self) -> bool:
        return bool(self._daily_reward_available or self._count_rewards_available)

    def perform_task(self):
        if self.config.dry_run:
            log.info('[DRY RUN] Would claim daily login rewards')
            return

        if self._daily_reward_available:
            log.info(f'Claiming daily login bonus for day={self.mm_time.day}')
            self.world_session.claim_daily_login_bonus(self.mm_time.day)
            del self.__dict__['login_bonus_info']
            self.__dict__.pop('_count_rewards_available', None)
            wait(self.config)

        for day_count in self._count_rewards_available:
            log.info(f'Claiming daily login count bonus for {day_count=}')
            self.world_session.claim_login_count_bonus(day_count)
            wait(self.config)

        return None


class ClaimLimitedDailyLoginRewards(DailyTask):
    # TODO: Handle new event bonuses like the ones in the 2nd anniversary event
    cli_name = 'limited_daily_login'

    @cached_property
    def _icon_info(self) -> t.MypageIconInfo | None:
        my_page: MyPage = self.world_session.get_my_page()
        for icon_info in my_page.my_page_info['MypageIconInfos']:
            if icon_info['TransferDetailInfo']['TransferSpotType'] == TransferSpotType.LimitedLoginBonus:
                return icon_info

        return None

    @cached_property
    def limited_login_bonus_id(self) -> int | None:
        if self._icon_info:
            return self._icon_info['TransferDetailInfo']['NumberInfo1']
        return None

    @cached_property
    def limited_login_bonus_info(self) -> t.GetLimitedLoginBonusInfoResponse | None:
        if self.limited_login_bonus_id is not None:
            return self.world_session.get_limited_login_bonus_info(self.limited_login_bonus_id)
        return None

    @cached_property
    def login_reward_list(self) -> LimitedLoginBonusRewardList | None:
        if self.limited_login_bonus_id is None:
            return None
        return self.mb.limited_login_bonuses[self.limited_login_bonus_id].reward_list

    @cached_property
    def _daily_reward_dates_available(self) -> list[int]:
        if self.limited_login_bonus_id is None:
            return []

        received_dates = self.limited_login_bonus_info['ReceivedDateList']
        total_logins: int = self.limited_login_bonus_info['TotalLoginCount']
        return [
            date
            for date_reward in self.login_reward_list.daily_rewards
            if (date := date_reward['Date']) not in received_dates and total_logins >= date
        ]

    @cached_property
    def _special_reward_available(self) -> bool:
        login_reward_list = self.login_reward_list
        if login_reward_list is None or not login_reward_list.special_reward_exists:
            return False
        elif self.limited_login_bonus_info['TotalLoginCount'] < login_reward_list.special_reward_item['Date']:
            return False
        return not self.limited_login_bonus_info['IsReceivedSpecialReward']

    def can_perform(self) -> bool:
        return bool(self._daily_reward_dates_available or self._special_reward_available)

    @cached_property
    def cannot_perform_msg(self) -> str:
        if self._icon_info:
            return 'The limited daily login rewards were already claimed'
        else:
            return 'There are no limited daily login rewards currently available'

    def perform_task(self):
        if self.config.dry_run:
            log.info('[DRY RUN] Would claim limited daily login rewards')
            return

        for date in self._daily_reward_dates_available:
            log.info(f'Claiming limited daily login bonus for day={date}')
            self.world_session.claim_limited_daily_login_bonus(self.limited_login_bonus_id, date)
            wait(self.config)

        if self._special_reward_available:
            log.info('Claiming special limited login reward')
            self.world_session.claim_special_limited_login_bonus(self.limited_login_bonus_id)

        return None
