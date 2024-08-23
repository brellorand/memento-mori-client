"""
Classes that wrap API responses
"""

from __future__ import annotations

import logging
from datetime import datetime
from functools import cached_property
from itertools import chain
from typing import TYPE_CHECKING, Any

from .enums import Region, SnsType
from .properties import DataProperty, ClearableCachedPropertyMixin
from .utils import parse_ms_epoch_ts

if TYPE_CHECKING:
    # fmt: off
    from .enums import LegendLeagueClassType, LockEquipmentDeckType, PrivacySettingsType, RankingDataType
    from .typing import (
        UserSyncData as _UserSyncData,
        MissionGuideInfo, DisplayMypageInfo, GuildSyncData,
        UserItem, LeadLockEquipmentDialogInfo, ShopProductGuerrillaPack,
        UserBattleBossDtoInfo, UserBattleLegendLeagueDtoInfo, UserBattlePvpDtoInfo, UserBoxSizeDtoInfo,
        UserCharacterBookDtoInfo, UserCharacterCollectionDtoInfo, UserCharacterDtoInfo, UserDeckDtoInfo,
        UserEquipmentDtoInfo, UserFriendDtoInfo, UserFriendMissionDtoInfo, UserItemDtoInfo, UserLevelLinkDtoInfo,
        UserLevelLinkMemberDtoInfo, UserMissionActivityDtoInfo, UserMissionDtoInfo, UserMissionOccurrenceHistoryDtoInfo,
        UserNotificationDtoInfo, UserOpenContentDtoInfo, UserRecruitGuildMemberSettingDtoInfo, UserSettingsDtoInfo,
        UserShopSubscriptionDtoInfo, UserStatusDtoInfo, UserTowerBattleDtoInfo, UserVipGiftDtoInfo,
        UserShopAchievementPackDtoInfo, UserShopFirstChargeBonusDtoInfo, UserShopFreeGrowthPackDtoInfo,
        UserShopMonthlyBoostDtoInfo,
    )
    # fmt: on

__all__ = ['OrtegaInfo', 'GameData', 'WorldInfo']
log = logging.getLogger(__name__)


class DictWrapper(ClearableCachedPropertyMixin):
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


class MyPage(DictWrapper):
    has_pending_friend_point_transfers: bool = DataProperty('ExistNewFriendPointTransfer')
    has_unread_private_chat: bool = DataProperty('ExistNewPrivateChat')

    has_unclaimed_bounty_quest_reward: bool = DataProperty('ExistNotReceivedBountyQuestReward')
    has_unclaimed_mission_reward: bool = DataProperty('ExistNotReceivedMissionReward')

    my_page_info: DisplayMypageInfo = DataProperty('MypageInfo')
    guild_sync_data: GuildSyncData = DataProperty('GuildSyncData')
    user_sync_data: _UserSyncData = DataProperty('UserSyncData')
    friend_list: list[UserFriendDtoInfo] = DataProperty('UserFriendDtoInfoList')
    mission_guide_info: MissionGuideInfo = DataProperty('MissionGuideInfo')
    bounty_quest_ids: list[int] = DataProperty('NotOrderedBountyQuestIdList')
    display_notice_ids: list[int] = DataProperty('DisplayNoticeIdList')
    unread_notification_ids: list[int] = DataProperty('UnreadIndividualNotificationIdList')
    latest_chat_announcement_registered: int = DataProperty('LatestAnnounceChatRegistrationLocalTimestamp')


class UserSyncData(DictWrapper):
    # fmt: off
    player_info: UserStatusDtoInfo = DataProperty('UserStatusDtoInfo')  # name, comment, rank, vip level, exp, etc
    quest_status: UserBattleBossDtoInfo = DataProperty('UserBattleBossDtoInfo')
    tower_status: list[UserTowerBattleDtoInfo] = DataProperty('UserTowerBattleDtoInfos')

    # region Items & Equipment

    equipment: list[UserEquipmentDtoInfo] = DataProperty('UserEquipmentDtoInfos')
    inventory: list[UserItemDtoInfo] = DataProperty('UserItemDtoInfo')

    deleted_equipment_guids: list[str] = DataProperty('DeletedEquipmentGuidList')
    item_counts: list[UserItem] = DataProperty('GivenItemCountInfoList')

    # endregion

    # region Characters & Level Link

    characters: list[UserCharacterDtoInfo] = DataProperty('UserCharacterDtoInfos')
    parties: list[UserDeckDtoInfo] = DataProperty('UserDeckDtoInfos')
    character_index_info: list[UserCharacterBookDtoInfo] = DataProperty('UserCharacterBookDtoInfos')
    character_collection: list[UserCharacterCollectionDtoInfo] = DataProperty('UserCharacterCollectionDtoInfos')

    deleted_character_guids: list[str] = DataProperty('DeletedCharacterGuidList')

    level_link_status: UserLevelLinkDtoInfo = DataProperty('UserLevelLinkDtoInfo')
    level_link_characters: list[UserLevelLinkMemberDtoInfo] = DataProperty('UserLevelLinkMemberDtoInfos')

    # endregion

    # region Daily Tasks

    has_vip_daily_gift: bool = DataProperty('ExistVipDailyGift')                    # Daily VIP chest
    vip_gift_info: list[UserVipGiftDtoInfo] = DataProperty('UserVipGiftDtoInfos')   # VIP level, VIP gift ID

    present_count: int | None = DataProperty('PresentCount')                        # Present inbox unread count

    # endregion

    # region Rewards

    receivable_achieve_ranking_reward_id_map: dict[RankingDataType, int] = DataProperty('ReceivableAchieveRankingRewardIdMap')
    received_achieve_ranking_reward_id_list: list[int] = DataProperty('ReceivedAchieveRankingRewardIdList')
    received_auto_battle_reward_last_time: int | None = DataProperty('ReceivedAutoBattleRewardLastTime')

    guild_tower_floor_received_achievement_ids: list[int] = DataProperty('ReceivedGuildTowerFloorRewardIdList')

    # endregion

    # region Gear Lock

    lead_lock_equipment_dialog_info_map: dict[LockEquipmentDeckType, LeadLockEquipmentDialogInfo] = DataProperty('LeadLockEquipmentDialogInfoMap')
    locked_equipment_character_guid_list_map: dict[LockEquipmentDeckType, list[str]] = DataProperty('LockedEquipmentCharacterGuidListMap')
    locked_user_equipment_dto_info_list_map: dict[LockEquipmentDeckType, list[UserEquipmentDtoInfo]] = DataProperty('LockedUserEquipmentDtoInfoListMap')
    release_lock_equipment_cooldown_time_stamp_map: dict[LockEquipmentDeckType, int] = DataProperty('ReleaseLockEquipmentCooldownTimeStampMap')

    # endregion

    # region PvP

    battle_league_status: UserBattlePvpDtoInfo = DataProperty('UserBattlePvpDtoInfo')
    legend_league_status: UserBattleLegendLeagueDtoInfo = DataProperty('UserBattleLegendLeagueDtoInfo')

    can_join_legend_league: bool = DataProperty('CanJoinTodayLegendLeague')
    legend_league_class_type: LegendLeagueClassType | None = DataProperty('LegendLeagueClassType')

    # endregion

    # region General

    user_creation_time: int = DataProperty('CreateUserIdTimestamp')
    world_creation_time: int = DataProperty('CreateWorldLocalTimeStamp')
    time_server_id: int | None = DataProperty('TimeServerId')

    blocked_player_ids: list[int] = DataProperty('BlockPlayerIdList')
    privacy_settings_type: PrivacySettingsType | None = DataProperty('PrivacySettingsType')

    stripe_point: int = DataProperty('StripePoint')
    cleared_tutorial_ids: list[int] = DataProperty('ClearedTutorialIdList')
    data_linkage_map: dict[SnsType, bool] = DataProperty('DataLinkageMap')

    has_unconfirmed_retrieve_item_history: bool = DataProperty('ExistUnconfirmedRetrieveItemHistory')
    has_transitioned_panel_picture_book: bool = DataProperty('HasTransitionedPanelPictureBook')
    is_data_linkage: bool = DataProperty('IsDataLinkage')
    is_joined_global_gvg: bool = DataProperty('IsJoinedGlobalGvg')
    is_joined_local_gvg: bool = DataProperty('IsJoinedLocalGvg')
    is_received_sns_share_reward: bool = DataProperty('IsReceivedSnsShareReward')  # Not related to friend points
    is_retrieved_item: bool = DataProperty('IsRetrievedItem')
    is_valid_contract_privilege: bool = DataProperty('IsValidContractPrivilege')

    box_size_info: UserBoxSizeDtoInfo = DataProperty('UserBoxSizeDtoInfo')
    notifications_info: list[UserNotificationDtoInfo] = DataProperty('UserNotificationDtoInfoInfos')
    open_contents: list[UserOpenContentDtoInfo] = DataProperty('UserOpenContentDtoInfos')
    settings: list[UserSettingsDtoInfo] = DataProperty('UserSettingsDtoInfoList')

    # endregion

    # region Guild

    guild_join_limit_count: int = DataProperty('GuildJoinLimitCount')
    guild_raid_challenge_count: int = DataProperty('LocalRaidChallengeCount')
    recruit_guild_member_setting: UserRecruitGuildMemberSettingDtoInfo = DataProperty('UserRecruitGuildMemberSettingDtoInfo')

    # endregion

    # region Shop

    shop_currency_mission_progress_map: dict[str, int] = DataProperty('ShopCurrencyMissionProgressMap')
    shop_product_guerrilla_pack_list: list[ShopProductGuerrillaPack] = DataProperty('ShopProductGuerrillaPackList')
    shop_achievement_packs: list[UserShopAchievementPackDtoInfo] = DataProperty('UserShopAchievementPackDtoInfos')
    shop_first_charge_bonus: UserShopFirstChargeBonusDtoInfo = DataProperty('UserShopFirstChargeBonusDtoInfo')
    shop_free_growth_pack: list[UserShopFreeGrowthPackDtoInfo] = DataProperty('UserShopFreeGrowthPackDtoInfos')
    shop_monthly_boost: list[UserShopMonthlyBoostDtoInfo] = DataProperty('UserShopMonthlyBoostDtoInfos')
    shop_subscription: list[UserShopSubscriptionDtoInfo] = DataProperty('UserShopSubscriptionDtoInfos')

    # endregion

    treasure_chest_ceiling_count_map: dict[int, int] = DataProperty('TreasureChestCeilingCountMap')
    mission_activity: list[UserMissionActivityDtoInfo] = DataProperty('UserMissionActivityDtoInfos')
    missions: list[UserMissionDtoInfo] = DataProperty('UserMissionDtoInfos')
    mission_history: UserMissionOccurrenceHistoryDtoInfo = DataProperty('UserMissionOccurrenceHistoryDtoInfo')
    friend_missions: list[UserFriendMissionDtoInfo] = DataProperty('UserFriendMissionDtoInfoList')

    # fmt: on

    def update(self, data: _UserSyncData):
        if not data:
            log.debug('Ignoring UserSyncData update with no data')
            return

        self.clear_cached_properties()

        simple_lists = {
            'BlockPlayerIdList',
            'ClearedTutorialIdList',
            'ReceivedGuildTowerFloorRewardIdList',
            'ReceivedAchieveRankingRewardIdList',
        }
        simple_dicts = {
            'DataLinkageMap',
            'TreasureChestCeilingCountMap',
            'LeadLockEquipmentDialogInfoMap',
            'LockedEquipmentCharacterGuidListMap',
            'LockedUserEquipmentDtoInfoListMap',
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
                # log.debug(f'UserSyncData: storing {key} => {value!r}')
                self.data[key] = value
            elif not value:
                continue

            current = self.data[key]
            if key in store_new and not current:
                # log.debug(f'UserSyncData: storing {key} => {value!r}')
                self.data[key] = value
                continue

            if key in simple_lists:
                self.data[key] = combined = []
                for v in chain(current, value):
                    if v not in combined:
                        combined.append(v)
                # log.debug(f'UserSyncData: updating {key}(list) from {len(current)} to {len(combined)} items')
            elif key in simple_dicts:
                # log.debug(f'UserSyncData: updating {key}(dict) from {len(current)} with {len(value)} items')
                self.data[key].update(value)
            elif cmp_keys := cmp_key_lists.get(key):
                combined, included = [], set()
                for v in chain(current, value):
                    if (cmp_value := tuple(v[k] for k in cmp_keys)) not in included:
                        combined.append(v)
                        included.add(cmp_value)

                # log.debug(f'UserSyncData: updating {key}(cmp list) from {len(current)} to {len(combined)} items')
                self.data[key] = combined
            elif alt_key := rm_guid_map.get(key):
                if current := self.data[alt_key]:
                    to_rm = set(value)
                    # log.debug(f'UserSyncData: removing {len(to_rm)} items from {key} that had {len(current)} items')
                    self.data[alt_key] = [v for v in current if v['Guid'] not in to_rm]
            elif key == 'GivenItemCountInfoList':
                items = self.data['UserItemDtoInfo']
                # log.debug(f'UserSyncData: updating {len(items)} item counts for {key}')
                for _, item_info in value:
                    item_id, item_type = item_info['ItemId'], item_info['ItemType']
                    if ci := next((i for i in items if i['ItemId'] == item_id and i['ItemType'] == item_type), None):
                        ci['ItemCount'] += item_info['ItemCount']
                    else:
                        items.append(item_info | {'PlayerId': self.player_info['PlayerId']})
            else:
                # log.debug(f'UserSyncData: storing {key} => {value!r}')
                self.data[key] = value
