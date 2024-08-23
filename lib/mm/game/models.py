"""
Classes that represent structs used when logged in to a specific world, with helpers for mapping to MB entities
"""

from __future__ import annotations

import logging
from functools import cached_property
from itertools import chain
from typing import TYPE_CHECKING, Any

from mm.enums import CharacterRarity, ItemType
from mm.mb_models import AnyItem, Character as MBCharacter, Equipment as MBEquipment
from mm.properties import ClearableCachedPropertyMixin, DataProperty

if TYPE_CHECKING:
    from mm import typing as t
    from mm.enums import LegendLeagueClassType, LockEquipmentDeckType, PrivacySettingsType, RankingDataType, SnsType
    from .session import WorldSession

__all__ = ['WorldEntity', 'Equipment', 'Character']
log = logging.getLogger(__name__)


class WorldEntity:
    def __init__(self, world: WorldSession, data: dict[str, Any]):
        self.world = world
        self.data = data


class Equipment(WorldEntity):
    """
    This class represents ``UserEquipmentDtoInfo``, which is slightly different than the ``UserEquipment`` struct
    that is used related to smelting.
    """

    guid: str = DataProperty('Guid')
    char_guid: str = DataProperty('CharacterGuid')  # Empty string indicates this item is not equipped
    equipment_id: int = DataProperty('EquipmentId')

    upgrade_level: int = DataProperty('ReinforcementLv')

    reforged_str: int = DataProperty('AdditionalParameterMuscle')
    reforged_dex: int = DataProperty('AdditionalParameterEnergy')
    reforged_mag: int = DataProperty('AdditionalParameterIntelligence')
    reforged_sta: int = DataProperty('AdditionalParameterHealth')

    holy_augment_level: int = DataProperty('LegendSacredTreasureLv')
    holy_augment_exp: int = DataProperty('LegendSacredTreasureExp')
    dark_augment_level: int = DataProperty('MatchlessSacredTreasureLv')
    dark_augment_exp: int = DataProperty('MatchlessSacredTreasureExp')

    rune_id_1: int = DataProperty('SphereId1')
    rune_id_2: int = DataProperty('SphereId2')
    rune_id_3: int = DataProperty('SphereId3')
    rune_id_4: int = DataProperty('SphereId4')
    rune_slots_unlocked: int = DataProperty('SphereUnlockedCount')

    @cached_property
    def equipment(self) -> MBEquipment:
        return self.world.session.mb.equipment[self.equipment_id]

    def __repr__(self) -> str:
        equip = self.equipment
        level, slot_type, rarity = equip.level, equip.slot_type.name, equip.rarity_flags.name
        guid = self.guid
        return f'<{self.__class__.__name__}[{equip.name}, {rarity=}, {level=}, {slot_type=}, {guid=}]>'


class ItemAndCount(WorldEntity):
    item_type: ItemType = DataProperty('ItemType', ItemType)
    item_id: int = DataProperty('ItemId')
    count: int = DataProperty('ItemCount')
    player_id: int = DataProperty('PlayerId')

    @cached_property
    def item(self) -> AnyItem:
        return self.world.session.mb.get_item(self.item_type, self.item_id)

    def __repr__(self) -> str:
        type, id, count, item = self.item_type, self.item_id, self.count, self.item  # noqa
        return f'<{self.__class__.__name__}[{type=!s}, {id=!s}, {count=}, {item=!s}]>'


class Character(WorldEntity):
    guid: str = DataProperty('Guid')
    char_id: int = DataProperty('CharacterId')
    level: int = DataProperty('Level')
    experience: int = DataProperty('Exp')
    rarity: CharacterRarity = DataProperty('RarityFlags', type=CharacterRarity)

    @cached_property
    def equipment(self) -> list[Equipment]:
        return self.world.char_guid_equipment_map.get(self.guid, [])

    @cached_property
    def character(self) -> MBCharacter:
        return self.world.session.mb.characters[self.char_id]

    def __repr__(self) -> str:
        rarity, level, exp, guid = self.rarity.name, self.level, self.experience, self.guid
        return f'<{self.__class__.__name__}[{self.character.full_name}, {rarity=}, {level=}, {exp=}, {guid=}]>'


class MyPage(WorldEntity):
    has_pending_friend_point_transfers: bool = DataProperty('ExistNewFriendPointTransfer')
    has_unread_private_chat: bool = DataProperty('ExistNewPrivateChat')

    has_unclaimed_bounty_quest_reward: bool = DataProperty('ExistNotReceivedBountyQuestReward')
    has_unclaimed_mission_reward: bool = DataProperty('ExistNotReceivedMissionReward')

    my_page_info: t.DisplayMypageInfo = DataProperty('MypageInfo')
    guild_sync_data: t.GuildSyncData = DataProperty('GuildSyncData')
    user_sync_data: t.UserSyncData = DataProperty('UserSyncData')
    friend_list: list[t.UserFriendDtoInfo] = DataProperty('UserFriendDtoInfoList')
    mission_guide_info: t.MissionGuideInfo = DataProperty('MissionGuideInfo')
    bounty_quest_ids: list[int] = DataProperty('NotOrderedBountyQuestIdList')
    display_notice_ids: list[int] = DataProperty('DisplayNoticeIdList')
    unread_notification_ids: list[int] = DataProperty('UnreadIndividualNotificationIdList')
    latest_chat_announcement_registered: int = DataProperty('LatestAnnounceChatRegistrationLocalTimestamp')


class UserSyncData(ClearableCachedPropertyMixin, WorldEntity):
    # fmt: off
    player_info: t.UserStatusDtoInfo = DataProperty('UserStatusDtoInfo')  # name, comment, rank, vip level, exp, etc
    quest_status: t.UserBattleBossDtoInfo = DataProperty('UserBattleBossDtoInfo')
    tower_status: list[t.UserTowerBattleDtoInfo] = DataProperty('UserTowerBattleDtoInfos')

    # region Items & Equipment

    equipment: list[t.UserEquipmentDtoInfo] = DataProperty('UserEquipmentDtoInfos')
    inventory: list[t.UserItemDtoInfo] = DataProperty('UserItemDtoInfo')

    deleted_equipment_guids: list[str] = DataProperty('DeletedEquipmentGuidList')
    item_counts: list[t.UserItem] = DataProperty('GivenItemCountInfoList')

    # endregion

    # region Characters & Level Link

    characters: list[t.UserCharacterDtoInfo] = DataProperty('UserCharacterDtoInfos')
    parties: list[t.UserDeckDtoInfo] = DataProperty('UserDeckDtoInfos')
    character_index_info: list[t.UserCharacterBookDtoInfo] = DataProperty('UserCharacterBookDtoInfos')
    character_collection: list[t.UserCharacterCollectionDtoInfo] = DataProperty('UserCharacterCollectionDtoInfos')

    deleted_character_guids: list[str] = DataProperty('DeletedCharacterGuidList')

    level_link_status: t.UserLevelLinkDtoInfo = DataProperty('UserLevelLinkDtoInfo')
    level_link_characters: list[t.UserLevelLinkMemberDtoInfo] = DataProperty('UserLevelLinkMemberDtoInfos')

    # endregion

    # region Daily Tasks

    has_vip_daily_gift: bool = DataProperty('ExistVipDailyGift')                        # Daily VIP chest
    vip_gift_info: list[t.UserVipGiftDtoInfo] = DataProperty('UserVipGiftDtoInfos')     # VIP level, VIP gift ID

    present_count: int | None = DataProperty('PresentCount')                            # Present inbox unread count

    # endregion

    # region Rewards

    receivable_achieve_ranking_reward_id_map: dict[RankingDataType, int] = DataProperty('ReceivableAchieveRankingRewardIdMap')
    received_achieve_ranking_reward_id_list: list[int] = DataProperty('ReceivedAchieveRankingRewardIdList')
    received_auto_battle_reward_last_time: int | None = DataProperty('ReceivedAutoBattleRewardLastTime')

    guild_tower_floor_received_achievement_ids: list[int] = DataProperty('ReceivedGuildTowerFloorRewardIdList')

    # endregion

    # region Gear Lock

    lead_lock_equipment_dialog_info_map: dict[LockEquipmentDeckType, t.LeadLockEquipmentDialogInfo] = DataProperty('LeadLockEquipmentDialogInfoMap')
    locked_equipment_character_guid_list_map: dict[LockEquipmentDeckType, list[str]] = DataProperty('LockedEquipmentCharacterGuidListMap')
    locked_user_equipment_dto_info_list_map: dict[LockEquipmentDeckType, list[t.UserEquipmentDtoInfo]] = DataProperty('LockedUserEquipmentDtoInfoListMap')
    release_lock_equipment_cooldown_time_stamp_map: dict[LockEquipmentDeckType, int] = DataProperty('ReleaseLockEquipmentCooldownTimeStampMap')

    # endregion

    # region PvP

    battle_league_status: t.UserBattlePvpDtoInfo = DataProperty('UserBattlePvpDtoInfo')
    legend_league_status: t.UserBattleLegendLeagueDtoInfo = DataProperty('UserBattleLegendLeagueDtoInfo')

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

    box_size_info: t.UserBoxSizeDtoInfo = DataProperty('UserBoxSizeDtoInfo')
    notifications_info: list[t.UserNotificationDtoInfo] = DataProperty('UserNotificationDtoInfoInfos')
    open_contents: list[t.UserOpenContentDtoInfo] = DataProperty('UserOpenContentDtoInfos')
    settings: list[t.UserSettingsDtoInfo] = DataProperty('UserSettingsDtoInfoList')

    # endregion

    # region Guild

    guild_join_limit_count: int = DataProperty('GuildJoinLimitCount')
    guild_raid_challenge_count: int = DataProperty('LocalRaidChallengeCount')
    recruit_guild_member_setting: t.UserRecruitGuildMemberSettingDtoInfo = DataProperty('UserRecruitGuildMemberSettingDtoInfo')

    # endregion

    # region Shop

    shop_currency_mission_progress_map: dict[str, int] = DataProperty('ShopCurrencyMissionProgressMap')
    shop_product_guerrilla_pack_list: list[t.ShopProductGuerrillaPack] = DataProperty('ShopProductGuerrillaPackList')
    shop_achievement_packs: list[t.UserShopAchievementPackDtoInfo] = DataProperty('UserShopAchievementPackDtoInfos')
    shop_first_charge_bonus: t.UserShopFirstChargeBonusDtoInfo = DataProperty('UserShopFirstChargeBonusDtoInfo')
    shop_free_growth_pack: list[t.UserShopFreeGrowthPackDtoInfo] = DataProperty('UserShopFreeGrowthPackDtoInfos')
    shop_monthly_boost: list[t.UserShopMonthlyBoostDtoInfo] = DataProperty('UserShopMonthlyBoostDtoInfos')
    shop_subscription: list[t.UserShopSubscriptionDtoInfo] = DataProperty('UserShopSubscriptionDtoInfos')

    # endregion

    treasure_chest_ceiling_count_map: dict[int, int] = DataProperty('TreasureChestCeilingCountMap')
    mission_activity: list[t.UserMissionActivityDtoInfo] = DataProperty('UserMissionActivityDtoInfos')
    missions: list[t.UserMissionDtoInfo] = DataProperty('UserMissionDtoInfos')
    mission_history: t.UserMissionOccurrenceHistoryDtoInfo = DataProperty('UserMissionOccurrenceHistoryDtoInfo')
    friend_missions: list[t.UserFriendMissionDtoInfo] = DataProperty('UserFriendMissionDtoInfoList')

    # fmt: on

    def update(self, data: t.UserSyncData):
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