"""
Classes that wrap API responses
"""

from __future__ import annotations

import logging
from datetime import datetime
from functools import cached_property
from itertools import chain
from typing import Any

from .enums import Region, SnsType
from .utils import DataProperty, parse_ms_epoch_ts

__all__ = ['OrtegaInfo', 'GameData', 'WorldInfo']
log = logging.getLogger(__name__)

IUserItem = dict  # TODO
LockEquipmentDeckType = dict  # TODO
LeadLockEquipmentDialogInfo = dict  # TODO
LegendLeagueClassType = dict  # TODO
UserEquipmentDtoInfo = dict  # TODO
PrivacySettingsType = dict  # TODO
RankingDataType = dict  # TODO
ShopProductGuerrillaPack = dict  # TODO
UserBattleBossDtoInfo = dict  # TODO
UserBattleLegendLeagueDtoInfo = dict  # TODO
UserBattlePvpDtoInfo = dict  # TODO
UserBoxSizeDtoInfo = dict  # TODO
UserCharacterBookDtoInfo = dict  # TODO
UserCharacterCollectionDtoInfo = dict  # TODO
UserCharacterDtoInfo = dict  # TODO
UserDeckDtoInfo = dict  # TODO
UserItemDtoInfo = dict  # TODO
UserLevelLinkDtoInfo = dict  # TODO
UserLevelLinkMemberDtoInfo = dict  # TODO
UserMissionActivityDtoInfo = dict  # TODO
UserMissionDtoInfo = dict  # TODO
UserMissionOccurrenceHistoryDtoInfo = dict  # TODO
UserFriendMissionDtoInfo = dict  # TODO
UserNotificationDtoInfo = dict  # TODO
UserOpenContentDtoInfo = dict  # TODO
UserRecruitGuildMemberSettingDtoInfo = dict  # TODO
UserSettingsDtoInfo = dict  # TODO
UserShopAchievementPackDtoInfo = dict  # TODO
UserShopFirstChargeBonusDtoInfo = dict  # TODO
UserShopFreeGrowthPackDtoInfo = dict  # TODO
UserShopMonthlyBoostDtoInfo = dict  # TODO
UserShopSubscriptionDtoInfo = dict  # TODO
UserStatusDtoInfo = dict  # TODO
UserTowerBattleDtoInfo = dict  # TODO
UserVipGiftDtoInfo = dict  # TODO


class DictWrapper:
    __slots__ = ('data',)

    def __init__(self, data: dict[str, Any]):
        self.data = data


# region Auth Client Responses


class OrtegaInfo(DictWrapper):
    status_code: int = DataProperty('ortegastatuscode', int)
    next_access_token: str = DataProperty('orteganextaccesstoken')  # Usually an empty string
    asset_version: str = DataProperty('ortegaassetversion')
    mb_version: str = DataProperty('ortegamasterversion')
    utc_now_timestamp: str = DataProperty('ortegautcnowtimestamp')
    mb_version_dt: datetime = DataProperty('ortegamasterversion', type=parse_ms_epoch_ts)
    utc_now_timestamp_dt: datetime = DataProperty('ortegautcnowtimestamp', type=parse_ms_epoch_ts)


class WorldInfo(DictWrapper):
    """Represents a single row in the ``WorldInfos`` list in the ``auth/getDataUri`` response"""

    game_server_id: int = DataProperty('GameServerId')
    id: int = DataProperty('Id')
    start_time: datetime = DataProperty('StartTime')

    def __repr__(self) -> str:
        start = self.start_time.isoformat(' ')
        return f'<{self.__class__.__name__}[region={self.region}, num={self.number}, {start=!s}]>'

    @cached_property
    def region(self) -> Region:
        return Region(self.id // 1000)

    @cached_property
    def number(self) -> int:
        return self.id - (self.region * 1000)


class GameData(DictWrapper):
    """
    The parsed content from the ``auth/getDataUri`` response.

    Example:
    {
        'AppAssetVersionInfo': {'EnvType': 0, 'IsSkipAssetDownload': False, 'Version': '2.8.1'},
        'WorldInfos': [
            {'GameServerId': 1, 'Id': 1001, 'StartTime': datetime.datetime(2022, 10, 17, 4, 0, tzinfo=datetime.timezone.utc)},
            ...
            {'GameServerId': 60, 'Id': 6020, 'StartTime': datetime.datetime(2024, 1, 26, 4, 0, tzinfo=datetime.timezone.utc)}
        ],
        'MaintenanceDebugUserInfos': [
            {'UserId': 826639594190, 'PlayerId': 855534869003, 'IsDebugUser': True},
            ...
            {'UserId': 204182531577, 'PlayerId': 669925568060, 'IsDebugUser': True}
        ],
        'MaintenanceInfos': [
            {
                'MaintenanceServerType': 0,
                'StartTimeFixJST': datetime.datetime(2024, 2, 7, 14, 30, tzinfo=datetime.timezone.utc),
                'EndTimeFixJST': datetime.datetime(2024, 2, 7, 17, 30, tzinfo=datetime.timezone.utc),
                'MaintenancePlatformTypes': [0],
                'MaintenanceAreaType': 0,
                'AreaIds': [],
                'MaintenanceFunctionTypes': []
            },
            ...
        ],
        'ManagementNewUserInfos': [
            {
                'EndTimeFixJST': datetime.datetime(2100, 1, 1, 0, 0, tzinfo=datetime.timezone.utc),
                'IsUnableToCreateUser': False,
                'ManagementNewUserType': 0,
                'StartTimeFixJST': datetime.datetime(2100, 1, 1, 0, 0, tzinfo=datetime.timezone.utc),
                'TargetIds': [1]
            },
            ...
        ],
        'AssetCatalogFixedUriFormat': 'https://cdn-mememori.akamaized.net/asset/MementoMori/{0}',
        'MasterUriFormat': 'https://cdn-mememori.akamaized.net/master/prd1/version/{0}/{1}',
        'RawDataUriFormat': 'https://cdn-mememori.akamaized.net/asset/MementoMori/Raw/{0}',
        'TitleInfo': {
            'BgmNumberJP': 1,
            'BgmNumberUS': 16,
            'MovieNumber': 12,
            'LogoNumber': 0,
            'X': 20.0,
            'Y': 113.0,
            'Scale': 1.0,
            'AnchorMinX': 0.20000000298023224,
            'AnchorMinY': 0.699999988079071,
            'AnchorMaxX': 0.20000000298023224,
            'AnchorMaxY': 0.699999988079071
        }
    }
    """

    version: str = DataProperty('AppAssetVersionInfo.Version')
    asset_catalog_uri_fmt: str = DataProperty('AssetCatalogFixedUriFormat')
    mb_uri_fmt: str = DataProperty('MasterUriFormat')
    raw_data_uri_fmt: str = DataProperty('RawDataUriFormat')

    def __repr__(self) -> str:
        worlds = len(self.data['WorldInfos'])
        return f'<{self.__class__.__name__}[version={self.version}, {worlds=}]>'

    @cached_property
    def region_world_map(self) -> dict[Region, list[WorldInfo]]:
        region_world_map = {r: [] for r in Region}
        for row in self.data['WorldInfos']:
            world = WorldInfo(row)
            region_world_map[world.region].append(world)
        return region_world_map

    def get_world(self, world_id: int) -> WorldInfo:
        worlds = self.region_world_map.get(Region.for_world(world_id), [])
        if world := next((w for w in worlds if w.id == world_id), None):
            return world
        raise ValueError(f'Invalid {world_id=} - could not find matching world data')

    @cached_property
    def uri_formats(self) -> dict[str, str]:
        return {
            'asset_catalog': self.asset_catalog_uri_fmt,
            'mb_catalog': self.mb_uri_fmt,
            'raw_data': self.raw_data_uri_fmt,
        }


# endregion


class UserSyncData(DictWrapper):
    blocked_player_ids: list[int] = DataProperty('BlockPlayerIdList')
    can_join_legend_league: bool = DataProperty('CanJoinTodayLegendLeague')
    cleared_tutorial_ids: list[int] = DataProperty('ClearedTutorialIdList')
    user_creation_time: int = DataProperty('CreateUserIdTimestamp')
    world_creation_time: int = DataProperty('CreateWorldLocalTimeStamp')
    data_linkage_map: dict[SnsType, bool] = DataProperty('DataLinkageMap')
    deleted_character_guids: list[str] = DataProperty('DeletedCharacterGuidList')
    deleted_equipment_guids: list[str] = DataProperty('DeletedEquipmentGuidList')
    has_unconfirmed_retrieve_item_history: bool = DataProperty('ExistUnconfirmedRetrieveItemHistory')
    has_vip_daily_gift: bool = DataProperty('ExistVipDailyGift')
    item_counts: list[IUserItem] = DataProperty('GivenItemCountInfoList')
    guild_join_limit_count: int = DataProperty('GuildJoinLimitCount')
    has_transitioned_panel_picture_book: bool = DataProperty('HasTransitionedPanelPictureBook')
    is_data_linkage: bool = DataProperty('IsDataLinkage')
    is_joined_global_gvg: bool = DataProperty('IsJoinedGlobalGvg')
    is_joined_local_gvg: bool = DataProperty('IsJoinedLocalGvg')
    has_pending_friend_point_actions: bool = DataProperty('IsReceivedSnsShareReward')
    is_retrieved_item: bool = DataProperty('IsRetrievedItem')
    is_valid_contract_privilege: bool = DataProperty('IsValidContractPrivilege')
    lead_lock_equipment_dialog_info_map: dict[LockEquipmentDeckType, LeadLockEquipmentDialogInfo] = DataProperty('LeadLockEquipmentDialogInfoMap')
    legend_league_class_type: LegendLeagueClassType | None = DataProperty('LegendLeagueClassType')
    local_raid_challenge_count: int = DataProperty('LocalRaidChallengeCount')
    locked_equipment_character_guid_list_map: dict[LockEquipmentDeckType, list[str]] = DataProperty('LockedEquipmentCharacterGuidListMap')
    locked_user_equipment_dto_info_list_map: dict[LockEquipmentDeckType, list[UserEquipmentDtoInfo]] = DataProperty('LockedUserEquipmentDtoInfoListMap')
    present_count: int | None = DataProperty('PresentCount')
    privacy_settings_type: PrivacySettingsType | None = DataProperty('PrivacySettingsType')
    receivable_achieve_ranking_reward_id_map: dict[RankingDataType, int] = DataProperty('ReceivableAchieveRankingRewardIdMap')
    received_achieve_ranking_reward_id_list: list[int] = DataProperty('ReceivedAchieveRankingRewardIdList')
    received_auto_battle_reward_last_time: int | None = DataProperty('ReceivedAutoBattleRewardLastTime')
    received_guild_tower_floor_reward_id_list: list[int] = DataProperty('ReceivedGuildTowerFloorRewardIdList')
    release_lock_equipment_cooldown_time_stamp_map: dict[LockEquipmentDeckType, int] = DataProperty('ReleaseLockEquipmentCooldownTimeStampMap')
    shop_currency_mission_progress_map: dict[str, int] = DataProperty('ShopCurrencyMissionProgressMap')
    shop_product_guerrilla_pack_list: list[ShopProductGuerrillaPack] = DataProperty('ShopProductGuerrillaPackList')
    stripe_point: int = DataProperty('StripePoint')
    time_server_id: int | None = DataProperty('TimeServerId')
    treasure_chest_ceiling_count_map: dict[int, int] = DataProperty('TreasureChestCeilingCountMap')
    user_battle_boss_dto_info: UserBattleBossDtoInfo = DataProperty('UserBattleBossDtoInfo')
    user_battle_legend_league_dto_info: UserBattleLegendLeagueDtoInfo = DataProperty('UserBattleLegendLeagueDtoInfo')
    user_battle_pvp_dto_info: UserBattlePvpDtoInfo = DataProperty('UserBattlePvpDtoInfo')
    user_box_size_dto_info: UserBoxSizeDtoInfo = DataProperty('UserBoxSizeDtoInfo')
    user_character_book_dto_infos: list[UserCharacterBookDtoInfo] = DataProperty('UserCharacterBookDtoInfos')
    user_character_collection_dto_infos: list[UserCharacterCollectionDtoInfo] = DataProperty('UserCharacterCollectionDtoInfos')
    user_character_dto_infos: list[UserCharacterDtoInfo] = DataProperty('UserCharacterDtoInfos')
    user_deck_dto_infos: list[UserDeckDtoInfo] = DataProperty('UserDeckDtoInfos')
    user_equipment_dto_infos: list[UserEquipmentDtoInfo] = DataProperty('UserEquipmentDtoInfos')
    user_item_dto_info: list[UserItemDtoInfo] = DataProperty('UserItemDtoInfo')
    user_level_link_dto_info: UserLevelLinkDtoInfo = DataProperty('UserLevelLinkDtoInfo')
    user_level_link_member_dto_infos: list[UserLevelLinkMemberDtoInfo] = DataProperty('UserLevelLinkMemberDtoInfos')
    user_mission_activity_dto_infos: list[UserMissionActivityDtoInfo] = DataProperty('UserMissionActivityDtoInfos')
    user_mission_dto_infos: list[UserMissionDtoInfo] = DataProperty('UserMissionDtoInfos')
    user_mission_occurrence_history_dto_info: UserMissionOccurrenceHistoryDtoInfo = DataProperty('UserMissionOccurrenceHistoryDtoInfo')
    user_friend_mission_dto_info_list: list[UserFriendMissionDtoInfo] = DataProperty('UserFriendMissionDtoInfoList')
    user_notification_dto_info_infos: list[UserNotificationDtoInfo] = DataProperty('UserNotificationDtoInfoInfos')
    user_open_content_dto_infos: list[UserOpenContentDtoInfo] = DataProperty('UserOpenContentDtoInfos')
    user_recruit_guild_member_setting_dto_info: UserRecruitGuildMemberSettingDtoInfo = DataProperty('UserRecruitGuildMemberSettingDtoInfo')
    user_settings_dto_info_list: list[UserSettingsDtoInfo] = DataProperty('UserSettingsDtoInfoList')
    user_shop_achievement_pack_dto_infos: list[UserShopAchievementPackDtoInfo] = DataProperty('UserShopAchievementPackDtoInfos')
    user_shop_first_charge_bonus_dto_info: UserShopFirstChargeBonusDtoInfo = DataProperty('UserShopFirstChargeBonusDtoInfo')
    user_shop_free_growth_pack_dto_infos: list[UserShopFreeGrowthPackDtoInfo] = DataProperty('UserShopFreeGrowthPackDtoInfos')
    user_shop_monthly_boost_dto_infos: list[UserShopMonthlyBoostDtoInfo] = DataProperty('UserShopMonthlyBoostDtoInfos')
    user_shop_subscription_dto_infos: list[UserShopSubscriptionDtoInfo] = DataProperty('UserShopSubscriptionDtoInfos')
    user_status_dto_info: UserStatusDtoInfo = DataProperty('UserStatusDtoInfo')
    user_tower_battle_dto_infos: list[UserTowerBattleDtoInfo] = DataProperty('UserTowerBattleDtoInfos')
    user_vip_gift_dto_infos: list[UserVipGiftDtoInfo] = DataProperty('UserVipGiftDtoInfos')

    def update(self, data: dict[str, Any]):
        if not data:
            return

        simple_lists = {
            'BlockPlayerIdList', 'ClearedTutorialIdList', 'ReceivedGuildTowerFloorRewardIdList',
            'ReceivedAchieveRankingRewardIdList',
        }
        simple_dicts = {
            'DataLinkageMap', 'TreasureChestCeilingCountMap', 'LeadLockEquipmentDialogInfoMap',
            'LockedEquipmentCharacterGuidListMap', 'LockedUserEquipmentDtoInfoListMap',
            'ReleaseLockEquipmentCooldownTimeStampMap',
        }
        cmp_key_lists = {
            'UserCharacterDtoInfos': ('Guid',),
            'UserEquipmentDtoInfos': ('Guid',),
            'UserItemDtoInfo': ('ItemType', 'ItemId'),
            'UserTowerBattleDtoInfos': ('TowerType',),
            'ShopProductGuerrillaPackList': ('ShopGuerrillaPackId',),
        }
        store_new = simple_lists.union(simple_dicts).union(cmp_key_lists)
        rm_guid_map = {
            'DeletedCharacterGuidList': 'UserCharacterDtoInfos',
            'DeletedEquipmentGuidList': 'UserEquipmentDtoInfos',
        }

        for key, value in data.items():
            if value is False or value is True:
                self.data[key] = value
            elif not value:
                continue

            current = self.data[key]
            if key in store_new and not current:
                self.data[key] = value
                continue

            if key in simple_lists:
                self.data[key] = combined = []
                for v in chain(current, value):
                    if v not in combined:
                        combined.append(v)
            elif key in simple_dicts:
                self.data[key].update(value)
            elif cmp_keys := cmp_key_lists.get(key):
                combined, included = [], set()
                for v in chain(current, value):
                    if (cmp_value := tuple(v[k] for k in cmp_keys)) not in included:
                        combined.append(v)
                        included.add(cmp_value)

                self.data[key] = combined
            elif alt_key := rm_guid_map.get(key):
                if current := self.data[alt_key]:
                    to_rm = set(value)
                    self.data[alt_key] = [v for v in current if v['Guid'] not in to_rm]
            elif key == 'GivenItemCountInfoList':
                items = self.data['UserItemDtoInfo']
                for item_count in value:
                    item_id, item_type = item_count['ItemId'], item_count['ItemType']
                    if ci := next((i for i in items if i['ItemId'] == item_id and i['ItemType'] == item_type), None):
                        ci['ItemCount'] += item_count['ItemCount']
                    else:
                        items.append(item_count)
            else:
                self.data[key] = value
