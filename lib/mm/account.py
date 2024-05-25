"""

"""

from __future__ import annotations

import logging
from functools import cached_property, partial
from typing import TYPE_CHECKING

from .config import AccountConfig
from .data import UserSyncData
from .enums import Region
from .http_client import AuthClient, ApiClient
from .grpc_client import MagicOnionClient

if TYPE_CHECKING:
    from .typing import LoginResponse, PlayerDataInfo, GetServerHostResponse, LoginPlayerResponse

__all__ = ['PlayerAccount', 'WorldAccount']
log = logging.getLogger(__name__)


class PlayerAccount:
    _last_world: WorldAccount = None

    def __init__(self, config: AccountConfig, auth_client: AuthClient):
        self.config = config.parent
        self.account_config = config
        self.auth_client = auth_client

    @cached_property
    def login_data(self) -> LoginResponse:
        return self.auth_client.login(self.account_config)

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

    def get_world(self, world_id: int) -> WorldAccount:
        if self._last_world is not None:
            self._last_world.close()

        self._last_world = world = WorldAccount(self, self.region.normalize_world(world_id))
        return world


class requires_login:
    __slots__ = ('method',)

    def __init__(self, method):
        self.method = method

    def __get__(self, instance: WorldAccount, owner):
        if instance is None:
            return self
        instance._login_resp  # noqa
        return partial(self.method, instance)


class WorldAccount:
    user_sync_data: UserSyncData = None

    def __init__(self, player: PlayerAccount, world_id: int):
        try:
            self._player_data: PlayerDataInfo = player.worlds[world_id]
        except KeyError as e:
            raise ValueError(f'Invalid {world_id=} - pick from: {", ".join(map(str, sorted(player.worlds)))}') from e
        self.player = player
        self._world_id = world_id

    @cached_property
    def player_id(self) -> int:
        return self._player_data['PlayerId']

    @property
    def world_id(self) -> int:
        return self._world_id

    @cached_property
    def _server_host_info(self) -> GetServerHostResponse:
        return self.player.auth_client.get_server_host(self._world_id)

    @cached_property
    def _api_client(self) -> ApiClient:
        return ApiClient.child_client(self.player.auth_client, self._server_host_info['ApiHost'])

    @cached_property
    def _login_resp(self) -> LoginPlayerResponse:
        resp = self._api_client.login_player(self.player_id, self._player_data['Password'])
        self.user_sync_data = UserSyncData(resp['UserSyncData'])
        return resp

    @cached_property
    def _grpc_client(self) -> MagicOnionClient:
        return MagicOnionClient(
            f'https://{self._server_host_info["MagicOnionHost"]}:{self._server_host_info["MagicOnionPort"]}',
            player_id=self.player_id,
            auth_token=self._login_resp['AuthTokenOfMagicOnion'],
        )

    def close(self):
        for key in ('_server_host_info', '_api_client', '_login_resp', '_grpc_client'):
            try:
                del self.__dict__[key]
            except KeyError:
                pass

    # def login(self) -> LoginPlayerResponse:
    #     return self._login_resp

    @requires_login
    def get_user_sync_data(self) -> UserSyncData:
        return self.user_sync_data

    @requires_login
    def get_my_page(self):
        # return self._api_client.get_my_page(self.player.config.auth.locale)
        return self._api_client.get_my_page()
