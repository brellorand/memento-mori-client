"""
Daily Tasks that can be performed when logged in to a specific world
"""

from __future__ import annotations

import logging

from .task import DailyTask

__all__ = ['ClaimDailyVIPGift']
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
