"""
Classes representing player / player + world accounts
"""

from __future__ import annotations

import json
import logging
from functools import cached_property, partial
from pathlib import Path
from typing import TYPE_CHECKING

from .data import UserSyncData
from .enums import Region, Locale, EquipmentRarityFlags, BaseParameterType, EquipmentSlotType, BattleType
from .http_client import ApiClient
from .properties import ClearableCachedPropertyMixin
from .models import Character, Equipment, ItemAndCount

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

__all__ = ['PlayerAccount', 'WorldSession']
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
        self.__dict__['login_data'] = _load_cached_data(path)
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


# region API Request Decorator


class ApiRequestMethod:
    __slots__ = ('method', 'requires_login', 'maintenance_ok')

    def __init__(self, method, requires_login: bool, maintenance_ok: bool):
        self.method = method
        self.requires_login = requires_login
        self.maintenance_ok = maintenance_ok

    def _request_wrapper(self, instance: WorldSession, *args, **kwargs):
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

    def __get__(self, instance: WorldSession, owner):
        if instance is None:
            return self
        return partial(self._request_wrapper, instance)


def api_request(*, requires_login: bool = True, maintenance_ok: bool = False):
    return lambda method: ApiRequestMethod(method, requires_login, maintenance_ok)


# endregion


class WorldSession(ClearableCachedPropertyMixin):
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

    @classmethod
    def from_cached_sync_data(cls, path: Path, player: PlayerAccount) -> WorldSession:
        data = _load_cached_data(path)
        player_id = data['UserSyncData']['UserStatusDtoInfo']['PlayerId']
        self = cls(player, player.region.normalize_world(player_id % 1000))
        self.user_sync_data = UserSyncData(data['UserSyncData'])
        return self

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
        self.clear_cached_properties('characters', 'equipment', 'char_guid_equipment_map', 'inventory')

    @cached_property
    def characters(self) -> dict[str, Character]:
        return {row['Guid']: Character(self, row) for row in self.user_sync_data.characters}

    @cached_property
    def equipment(self) -> dict[str, Equipment]:
        return {row['Guid']: Equipment(self, row) for row in self.user_sync_data.equipment}

    @cached_property
    def char_guid_equipment_map(self) -> dict[str, list[Equipment]]:
        """
        Mapping of ``{character guid: [Equipment]}``.  Unequipped gear is stored under guid/key ``''`` (empty string).
        """
        char_guid_equipment_map = {}
        for item in self.equipment.values():
            try:
                char_items = char_guid_equipment_map[item.char_guid]
            except KeyError:
                char_guid_equipment_map[item.char_guid] = [item]
            else:
                char_items.append(item)
        return char_guid_equipment_map

    @cached_property
    def inventory(self) -> list[ItemAndCount]:
        return [ItemAndCount(self, row) for row in self.user_sync_data.inventory]

    # endregion

    # region Dailies

    @api_request()
    def get_daily_vip_gift(self):
        return self._api_client.post_msg('vip/getDailyGift', {})

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

    # region Quest

    @api_request()
    def get_quest_map_info(self, include_other_players: bool = True):
        """
        Example response::

            "AutoBattleDropEquipmentPercent": 2500,
            "CurrentQuestAutoEnemyIds": [10116007, ..., 10117033, 10117034],
            "MapOtherPlayerInfos": [
                {"LatestQuestId": 167, "MainCharacterIconId": 13, "PlayerId": 687..., "PlayerRank": 60, "QuestId": 164},
                ...
            ],
            "MapPlayerInfos": [
                {"LatestQuestId": 24, "MainCharacterIconId": 2, "PlayerId": 114005..., "PlayerRank": 34, "QuestId": 24},
                ...
            ],
            "UserMapBuildingDtoInfos": [
                {"SelectedIndex": 1, "QuestMapBuildingId": 1}, {"SelectedIndex": 2, "QuestMapBuildingId": 2},
                {"SelectedIndex": 2, "QuestMapBuildingId": 6}, {"SelectedIndex": 2, "QuestMapBuildingId": 9},
                {"SelectedIndex": 1, "QuestMapBuildingId": 16}, {"SelectedIndex": 2, "QuestMapBuildingId": 28}
            ]

        :param include_other_players: Whether ``MapOtherPlayerInfos`` should be populated in the response
        :return:
        """
        return self._api_client.post_msg('quest/mapInfo', {'IsUpdateOtherPlayerInfo': bool(include_other_players)})

    @api_request()
    def get_quest_info(self, quest_id: int):
        # -> GetQuestInfoResponse => {TargetBossBattleInfo: BossBattleInfo}
        return self._api_client.post_msg('quest/getQuestInfo', {'TargetQuestId': quest_id})

    @api_request()
    def get_next_quest_info(self):
        # This populates ``UserSyncData.UserBattleBossDtoInfo.BossClearMaxQuestId``; add 1 to get the quest ID that
        # should be used with :meth:`.battle_quest_boss` to battle the next quest boss.
        return self._api_client.post_msg('battle/nextQuest', {})

    @api_request()
    def battle_quest_boss(self, quest_id: int):
        # Win/loss info in the response is in ``BattleResult.SimulationResult.BattleEndInfo``
        # After a win, :meth:`.get_next_quest_info` should be called to determine the next quest that is available
        return self._api_client.post_msg('battle/boss', {'QuestId': quest_id})

    @api_request()
    def __get_boss_reward_info(self):
        # This resulted in an error: "There is no information for the next quest."
        # {'ErrorCode': 112003, 'Message': '', 'ErrorHandlingType': 0, 'ErrorMessageId': 0, 'MessageParams': None}
        return self._api_client.post_msg('battle/bossRewardInfo', {})

    @api_request()
    def get_clear_party_log(self, quest_id: int, battle_type: BattleType | int):
        battle_type = BattleType(battle_type).value
        return self._api_client.post_msg('battle/getClearPartyLog', {'QuestId': quest_id, 'BattleType': battle_type})

    @api_request()
    def get_clear_party_battle_log(self, quest_id: int, player_id: int, battle_type: BattleType | int):
        # -> GetClearPartyBattleLogResponse => {BattleSimulationResult: BattleSimulationResult}
        battle_type = BattleType(battle_type).value
        data = {'LogQuestId': quest_id, 'LogPlayerId': player_id, 'BattleType': battle_type}
        return self._api_client.post_msg('battle/getClearPartyBattleLog', data)

    @api_request()
    def get_battle_log(self, battle_token: str):
        # -> GetBattleLogResponse => {BattleSimulationResult: BattleSimulationResult}
        return self._api_client.post_msg('battle/getBattleLog', {'BattleToken': battle_token})

    # endregion

    # region Trials

    # Notes:
    # BountyQuest = Fountain of Prayers
    # DungeonBattle = Cave of Space Time
    # TowerBattle = Tower of Infinity
    # LocalRaid = Temple of Illusions

    @api_request()
    def get_fountain_of_prayers_quests(self):
        return self._api_client.post_msg('bountyQuest/getList', {})

    @api_request()
    def get_temple_of_illusions_info(self):
        return self._api_client.post_msg('localRaid/getLocalRaidInfo', {})

    # endregion


def _load_cached_data(path: Path):
    with path.open('r', encoding='utf-8') as f:
        data = json.load(f)

    if len(data) == 2 and set(data) == {'headers', 'data'}:
        return data['data']
    else:
        return data
