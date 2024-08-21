"""
Classes representing a logged in player account
"""

from __future__ import annotations

import logging
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING

from ..enums import Region
from .session import WorldSession
from .utils import load_cached_data

if TYPE_CHECKING:
    from ..config import AccountConfig, ConfigFile
    from ..session import MementoMoriSession
    from ..typing import LoginResponse, PlayerDataInfo

__all__ = ['PlayerAccount']
log = logging.getLogger(__name__)


class PlayerAccount:
    """A player account, which may contain one or more :class:`.WorldSession`s"""

    session: MementoMoriSession
    config: ConfigFile = None
    account_config: AccountConfig = None
    _last_world: WorldSession = None

    def __init__(self, session: MementoMoriSession, config: AccountConfig | None):
        self.session = session
        if config is not None:
            self.config = config.parent
            self.account_config = config

    @classmethod
    def from_cached_login(cls, path: Path, session: MementoMoriSession, config: AccountConfig = None) -> PlayerAccount:
        self = cls(session, config)
        if config is None:
            self.config = session.config
        self.__dict__['login_data'] = load_cached_data(path)
        return self

    @cached_property
    def login_data(self) -> LoginResponse:
        return self.session.auth_client.login(self.account_config)

    @cached_property
    def region(self) -> Region:
        regions = {Region.for_world(world_id) for world_id in self.worlds}
        if len(regions) != 1:
            raise ValueError(f'Found an unexpected number of regions: {regions}')
        return next(iter(regions))

    @cached_property
    def worlds(self) -> dict[int, PlayerDataInfo]:
        """
        Mapping of world_id: world/character info.

        Example entry::

            {
                "CharacterId": 2,
                "LastLoginTime": 1710572380924,
                "LegendLeagueClass": 0,
                "Name": "New Player",
                "Password": "...",  # hashed or something
                "PlayerId": ...,  # integer
                "PlayerRank": 10,
                "WorldId": 4013
            }
        """
        return {row['WorldId']: row for row in self.login_data['PlayerDataInfoList']}

    def get_world(self, world_id: int) -> WorldSession:
        if self._last_world is not None:
            self._last_world.close()

        self._last_world = world = WorldSession(self, self.region.normalize_world(world_id))
        return world
