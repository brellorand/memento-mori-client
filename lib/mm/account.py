"""

"""

from __future__ import annotations

import logging
from functools import cached_property, partial
from typing import TYPE_CHECKING

from .assets import AssetCatalog
from .config import AccountConfig, ConfigFile
from .data import UserSyncData
from .enums import Region, Locale, EquipmentRarityFlags, BaseParameterType, EquipmentSlotType
from .http_client import AuthClient, ApiClient, DataClient
from .grpc_client import MagicOnionClient
from .mb_models import MB

if TYPE_CHECKING:
    from pathlib import Path
    from .fs import PathLike
    from .typing import (
        LoginResponse, PlayerDataInfo, GetServerHostResponse, LoginPlayerResponse, GetMypageResponse,
        UserEquipment, EquipmentChangeInfo
    )

__all__ = ['MementoMoriSession', 'PlayerAccount', 'WorldAccount']
log = logging.getLogger(__name__)


class MementoMoriSession:
    config: ConfigFile

    def __init__(
        self,
        config: PathLike | ConfigFile = None,
        *,
        use_auth_cache: bool = True,
        use_data_cache: bool = True,
        use_mb_cache: bool = True,
        mb_locale: Locale = None,
        mb_json_cache_map: dict[str, Path] = None,
    ):
        self.config = config if isinstance(config, ConfigFile) else ConfigFile(config)
        self._use_cache = {'auth': use_auth_cache, 'data': use_data_cache, 'mb': use_mb_cache}
        self._mb_locale = mb_locale
        self._mb_json_cache_map = mb_json_cache_map

    @cached_property
    def auth_client(self) -> AuthClient:
        return AuthClient(config=self.config, use_cache=self._use_cache['auth'])

    @cached_property
    def data_client(self) -> DataClient:
        return DataClient(
            auth_client=self.auth_client, use_data_cache=self._use_cache['data'], use_mb_cache=self._use_cache['mb']
        )

    @cached_property
    def asset_catalog(self) -> AssetCatalog:
        return AssetCatalog(self.data_client._get_asset_catalog())

    @cached_property
    def mb(self) -> MB:
        return self.get_mb()

    def get_mb(self, **kwargs) -> MB:
        kwargs.setdefault('json_cache_map', self._mb_json_cache_map)
        if 'locale' not in kwargs:
            kwargs['locale'] = self._mb_locale or self.config.mb.locale
        return self.data_client.get_mb(**kwargs)

    def get_account_by_id(self, user_id: int) -> PlayerAccount:
        try:
            account_config = self.config.accounts[str(user_id)]
        except KeyError as e:
            raise ValueError(f'Invalid {user_id=} - pick from: {", ".join(sorted(self.config.accounts))}') from e
        else:
            return PlayerAccount(self, account_config)

    def get_account_by_name(self, name: str) -> PlayerAccount:
        for account in self.config.accounts.values():
            if account.name == name:
                return PlayerAccount(self, account)

        names = ', '.join(sorted(a.name for a in self.config.accounts.values()))
        raise ValueError(f'Unable to find an account with {name=} - pick from: {names}')


class PlayerAccount:
    session: MementoMoriSession
    _last_world: WorldAccount = None

    def __init__(self, session: MementoMoriSession, config: AccountConfig):
        self.session = session
        self.config = config.parent
        self.account_config = config

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

    def get_world(self, world_id: int) -> WorldAccount:
        if self._last_world is not None:
            self._last_world.close()

        self._last_world = world = WorldAccount(self, self.region.normalize_world(world_id))
        return world


class requires_login:
    __slots__ = ('method',)

    def __init__(self, method):
        self.method = method

    def _request_wrapper(self, instance: WorldAccount, *args, **kwargs):
        resp = self.method(instance, *args, **kwargs)
        try:
            user_sync_data = resp['UserSyncData']
        except TypeError:
            try:
                user_sync_data = resp.data['UserSyncData']
            except (TypeError, KeyError):
                user_sync_data = None
        except KeyError:
            user_sync_data = None

        if user_sync_data is not None:
            instance.user_sync_data.update(user_sync_data)

        return resp

    def __get__(self, instance: WorldAccount, owner):
        if instance is None:
            return self
        instance._login_resp  # noqa
        return partial(self._request_wrapper, instance)


class WorldAccount:
    session: MementoMoriSession
    user_sync_data: UserSyncData = None

    def __init__(self, player: PlayerAccount, world_id: int):
        try:
            self._player_data: PlayerDataInfo = player.worlds[world_id]
        except KeyError as e:
            raise ValueError(f'Invalid {world_id=} - pick from: {", ".join(map(str, sorted(player.worlds)))}') from e
        self.session = player.session
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
        return self.session.auth_client.get_server_host(self._world_id)

    @cached_property
    def _api_client(self) -> ApiClient:
        return ApiClient.child_client(self.session.auth_client, self._server_host_info['ApiHost'])

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
    def get_user_data(self):
        return self._api_client.get_user_data()

    @requires_login
    def get_user_sync_data(self) -> UserSyncData:
        self._api_client.get_user_data()
        return self.user_sync_data

    @requires_login
    def get_my_page(self) -> GetMypageResponse:
        # return self._api_client.get_my_page(self.player.config.auth.locale)
        return self._api_client.get_my_page()

    # region Equipment

    @requires_login
    def smelt_gear(self, guid: str, user_equipment: UserEquipment):
        return self._api_client.post_msg('equipment/cast', {'Guid': guid, 'UserEquipment': user_equipment})

    @requires_login
    def smelt_all_gear(self, rarity: EquipmentRarityFlags | int):
        return self._api_client.post_msg('equipment/castMany', {'RarityFlags': getattr(rarity, 'value', rarity)})

    @requires_login
    def upgrade_gear(self, guid: str, num_times: int = 1):
        """
        Spend `Upgrade Water` and `Upgrade Panacea` to upgrade the specified equipment the specified number of times.

        You must have the required number of upgrade materials in your inventory.
        """
        return self._api_client.post_msg('equipment/reinforcement', {'EquipmentGuid': guid, 'NumberOfTimes': num_times})

    @requires_login
    def reforge_gear(self, guid: str, locked_params: list[BaseParameterType | int] = None):
        params = [getattr(v, 'value', v) for v in locked_params] if locked_params else []
        return self._api_client.post_msg('equipment/training', {'EquipmentGuid': guid, 'ParameterLockedList': params})

    @requires_login
    def transfer_runes_and_augments(self, src_guid: str, dst_guid: str):
        return self._api_client.post_msg(
            'equipment/inheritanceEquipment', {'InheritanceEquipmentGuid': dst_guid, 'SourceEquipmentGuid': src_guid}
        )

    @requires_login
    def remove_gear(self, char_guid: str, slots: list[EquipmentSlotType | int]):
        slots = [getattr(v, 'value', v) for v in slots] if slots else []
        return self._api_client.post_msg(
            'equipment/removeEquipment', {'UserCharacterGuid': char_guid, 'EquipmentSlotTypes': slots}
        )

    @requires_login
    def change_gear(self, char_guid: str, changes: list[EquipmentChangeInfo]):
        return self._api_client.post_msg(
            'equipment/changeEquipment', {'UserCharacterGuid': char_guid, 'EquipmentChangeInfos': changes}
        )

    # endregion
