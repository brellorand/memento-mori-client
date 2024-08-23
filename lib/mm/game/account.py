"""
Classes representing a logged in player account
"""

from __future__ import annotations

import logging
from functools import cached_property
from typing import TYPE_CHECKING

from mm.enums import Region
from mm.exceptions import LoginFailure
from .session import WorldSession
from .utils import load_cached_data

if TYPE_CHECKING:
    from pathlib import Path

    from ..config import AccountConfig, ConfigFile
    from ..session import MementoMoriSession
    from ..typing import LoginResponse, PlayerDataInfo

__all__ = ['PlayerAccount']
log = logging.getLogger(__name__)

AUTH_TOKEN_ASSET_PATH = 'Assets/AddressableLocalAssets/ScriptableObjects/AuthToken/AuthTokenData.asset'


class PlayerAccount:
    """A player account, which may contain one or more :class:`.WorldSession`s"""

    session: MementoMoriSession
    config: ConfigFile
    account_config: AccountConfig | None = None
    _last_world: WorldSession = None

    # region Initialization

    def __init__(self, session: MementoMoriSession, account_config: AccountConfig | None, config: ConfigFile = None):
        self.session = session
        if config is account_config is None:
            raise ValueError('PlayerAccount requires config info from AccountConfig and/or ConfigFile')
        self.config = config or account_config.parent
        self.account_config = account_config

    @classmethod
    def from_cached_login(cls, path: Path, session: MementoMoriSession) -> PlayerAccount:
        self = cls(session, account_config=None, config=session.config)
        self.__dict__['login_data'] = load_cached_data(path)
        return self

    # endregion

    # region Login / Auth

    @cached_property
    def login_data(self) -> LoginResponse:
        if not self.account_config:
            raise LoginFailure('An AccountConfig with a user ID configured is required')
        elif not self.account_config.client_key:
            self.generate_client_key()

        return self.session.auth_client.login(self.account_config)

    def generate_client_key(self, apk_path: Path | None = None):
        from getpass import getpass

        if not self.account_config:
            raise LoginFailure('An AccountConfig with a user ID configured is required')

        auth_token = _get_auth_token(apk_path)
        client_key = self.session.auth_client.get_client_key(
            self.account_config,
            password=getpass('Please enter the account password: '),
            auth_token=auth_token,
        )
        log.debug(f'Received {client_key=}')
        self.account_config.client_key = client_key

    # endregion

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


def _get_auth_token(apk_path: Path | None) -> int:
    from mm.assets.apk import load_apk_or_latest

    apk = load_apk_or_latest(apk_path, 'it contains data that is required to generate a client key').asset_pack_apk
    bundle_name = apk.catalog.find_bundle(AUTH_TOKEN_ASSET_PATH)
    if not bundle_name:
        raise LoginFailure(f'Unable to find bundle for {AUTH_TOKEN_ASSET_PATH} in {apk}')

    try:
        bundle = apk.get_bundle(bundle_name)
        return bundle.env.container[AUTH_TOKEN_ASSET_PATH].read().read_typetree()['_authToken']
    except Exception as e:
        raise LoginFailure(f'Failed to extract the auth token from {bundle_name} in {apk}') from e
