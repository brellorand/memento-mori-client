"""
Classes representing player / player + world accounts
"""

from __future__ import annotations

import logging
from functools import cached_property, partial
from typing import TYPE_CHECKING

from .data import UserSyncData
from .enums import Region, Locale, EquipmentRarityFlags, BaseParameterType, EquipmentSlotType
from .http_client import ApiClient
from .properties import ClearableCachedPropertyMixin
from .models import Character, Equipment

if TYPE_CHECKING:
    from .config import AccountConfig, ConfigFile
    from .grpc_client import MagicOnionClient
    from .session import MementoMoriSession
    from .typing import (
        LoginResponse,
        PlayerDataInfo,
        GetServerHostResponse,
        LoginPlayerResponse,
        GetUserDataResponse,
        GetMypageResponse,
        UserEquipment,
        EquipmentChangeInfo,
        ErrorLogInfo,
    )

__all__ = ['PlayerAccount', 'WorldAccount']
log = logging.getLogger(__name__)


class PlayerAccount:
    """A player account, which may contain one or more :class:`.WorldAccount`s"""

    session: MementoMoriSession
    config: ConfigFile
    account_config: AccountConfig
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


# region API Request Decorator


class ApiRequestMethod:
    __slots__ = ('method', 'requires_login', 'maintenance_ok')

    def __init__(self, method, requires_login: bool, maintenance_ok: bool):
        self.method = method
        self.requires_login = requires_login
        self.maintenance_ok = maintenance_ok

    def _request_wrapper(self, instance: WorldAccount, *args, **kwargs):
        if self.requires_login and not instance.is_logged_in:
            instance.login()

        resp = self.method(instance, *args, **kwargs)
        if user_sync_data := self._get_user_sync_data(resp):
            instance._reset_user_sync_data_properties()
            if instance.user_sync_data is None:
                instance.user_sync_data = UserSyncData(user_sync_data)
            else:
                instance.user_sync_data.update(user_sync_data)

        return resp

    def _get_user_sync_data(self, resp):
        try:
            return resp['UserSyncData']
        except TypeError:
            try:
                return resp.data['UserSyncData']
            except (TypeError, KeyError, AttributeError):
                return None
        except KeyError:
            return None

    def __get__(self, instance: WorldAccount, owner):
        if instance is None:
            return self
        return partial(self._request_wrapper, instance)


def api_request(*, requires_login: bool = True, maintenance_ok: bool = False):
    return lambda method: ApiRequestMethod(method, requires_login, maintenance_ok)


# endregion


class WorldAccount(ClearableCachedPropertyMixin):
    """Represents a player + world account / logged in session for that account."""

    session: MementoMoriSession
    player_data: PlayerDataInfo
    user_sync_data: UserSyncData = None

    def __init__(self, player: PlayerAccount, world_id: int):
        try:
            self.player_data = player.worlds[world_id]
        except KeyError as e:
            raise ValueError(f'Invalid {world_id=} - pick from: {", ".join(map(str, sorted(player.worlds)))}') from e
        self.session = player.session
        self.player = player
        self._world_id = world_id
        self._is_logged_in = False

    # region General Properties

    @cached_property
    def player_id(self) -> int:
        return self.player_data['PlayerId']

    @property
    def world_id(self) -> int:
        return self._world_id

    # endregion

    # region Client Properties

    @cached_property
    def _server_host_info(self) -> GetServerHostResponse:
        return self.session.auth_client.get_server_host(self._world_id)

    @cached_property
    def _api_client(self) -> ApiClient:
        return ApiClient.child_client(self.session.auth_client, self._server_host_info['ApiHost'])

    @cached_property
    def _grpc_client(self) -> MagicOnionClient:
        from .grpc_client import MagicOnionClient

        return MagicOnionClient(
            f'https://{self._server_host_info["MagicOnionHost"]}:{self._server_host_info["MagicOnionPort"]}',
            player_id=self.player_id,
            auth_token=self._login_resp['AuthTokenOfMagicOnion'],
        )

    # endregion

    # region Login

    @property
    def is_logged_in(self) -> bool:
        return self._is_logged_in

    def login(self) -> LoginPlayerResponse:
        return self._login_resp

    @api_request(requires_login=False, maintenance_ok=True)
    def _login(self, error_log_info: list[ErrorLogInfo] = None) -> LoginPlayerResponse:
        log.log(19, f'Logging player_id={self.player_id} into world={self.world_id}')
        resp = self._api_client.login_player(self.player_id, self.player_data['Password'], error_log_info)
        self._is_logged_in = True
        return resp

    @cached_property
    def _login_resp(self) -> LoginPlayerResponse:
        return self._login()

    # endregion

    def close(self):
        for key in ('_server_host_info', '_api_client', '_grpc_client', '_login_resp'):
            try:
                del self.__dict__[key]
            except KeyError:
                pass

        self._is_logged_in = False

    # region User Data Sync / My Page

    @api_request()
    def get_user_data(self) -> GetUserDataResponse:
        return self._api_client.post_msg('user/getUserData', {})

    def get_user_sync_data(self) -> UserSyncData:
        self.get_user_data()
        return self.user_sync_data

    @api_request()
    def get_my_page(self, locale: Locale = None) -> GetMypageResponse:
        # Alt locale value source: self.player.config.auth.locale
        data = {'LanguageType': locale.num} if locale is not None else {}
        return self._api_client.post_msg('user/getMypage', data)

    # endregion

    # region Character / Equipment Data

    def _reset_user_sync_data_properties(self):
        self.clear_cached_properties('characters', 'equipment', 'char_guid_equipment_map')

    @cached_property
    def characters(self) -> dict[str, Character]:
        return {row['Guid']: Character(self, row) for row in self.user_sync_data.user_character_dto_infos}

    @cached_property
    def equipment(self) -> dict[str, Equipment]:
        return {row['Guid']: Equipment(self, row) for row in self.user_sync_data.user_equipment_dto_infos}

    @cached_property
    def char_guid_equipment_map(self) -> dict[str, list[Equipment]]:
        char_guid_equipment_map = {}
        for item in self.equipment.values():
            try:
                char_items = char_guid_equipment_map[item.char_guid]
            except KeyError:
                char_guid_equipment_map[item.char_guid] = [item]
            else:
                char_items.append(item)
        return char_guid_equipment_map

    # endregion

    # region Equipment

    @api_request()
    def smelt_gear(self, guid: str, user_equipment: UserEquipment):
        return self._api_client.post_msg('equipment/cast', {'Guid': guid, 'UserEquipment': user_equipment})

    @api_request()
    def smelt_all_gear(self, rarity: EquipmentRarityFlags | int):
        return self._api_client.post_msg('equipment/castMany', {'RarityFlags': getattr(rarity, 'value', rarity)})

    @api_request()
    def upgrade_gear(self, guid: str, num_times: int = 1):
        """
        Spend `Upgrade Water` and `Upgrade Panacea` to upgrade the specified equipment the specified number of times.

        You must have the required number of upgrade materials in your inventory.
        """
        return self._api_client.post_msg('equipment/reinforcement', {'EquipmentGuid': guid, 'NumberOfTimes': num_times})

    @api_request()
    def reforge_gear(self, guid: str, locked_params: list[BaseParameterType | int] = None):
        params = [getattr(v, 'value', v) for v in locked_params] if locked_params else []
        return self._api_client.post_msg('equipment/training', {'EquipmentGuid': guid, 'ParameterLockedList': params})

    @api_request()
    def transfer_runes_and_augments(self, src_guid: str, dst_guid: str):
        return self._api_client.post_msg(
            'equipment/inheritanceEquipment', {'InheritanceEquipmentGuid': dst_guid, 'SourceEquipmentGuid': src_guid}
        )

    @api_request()
    def remove_gear(self, char_guid: str, slots: list[EquipmentSlotType | int]):
        slots = [getattr(v, 'value', v) for v in slots] if slots else []
        return self._api_client.post_msg(
            'equipment/removeEquipment', {'UserCharacterGuid': char_guid, 'EquipmentSlotTypes': slots}
        )

    @api_request()
    def change_gear(self, char_guid: str, changes: list[EquipmentChangeInfo]):
        return self._api_client.post_msg(
            'equipment/changeEquipment', {'UserCharacterGuid': char_guid, 'EquipmentChangeInfos': changes}
        )

    # endregion
