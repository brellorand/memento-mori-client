"""
Typing helpers
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from datetime import datetime

    from . import enums as e


# region Errors


class ApiErrorResponse(TypedDict):
    ErrorCode: int  # ErrorCode
    Message: str
    ErrorHandlingType: int  # ErrorHandlingType (Obsolete)
    ErrorMessageId: int  # Obsolete
    MessageParams: list[str]  # Obsolete


class ErrorLogInfo(TypedDict):
    ApiName: str
    ErrorCode: int
    ErrorLogType: e.ErrorLogType
    LocalTimeStamp: int
    Message: str


# endregion


# region Login-related


class GetServerHostResponse(TypedDict):
    ApiHost: str
    MagicOnionHost: str
    MagicOnionPort: int


class PlayerDataInfo(TypedDict):
    CharacterId: int
    LastLoginTime: int
    LegendLeagueClass: e.LegendLeagueClassType
    Name: str
    Password: str
    PlayerId: int
    PlayerRank: int
    WorldId: int


class LoginResponse(TypedDict):
    AccountMessageInfo: dict
    IsReservedAccountDeletion: bool
    IgnoreTypes: list[dict]
    MaxVip: int
    PlayerDataInfoList: list[PlayerDataInfo]
    RecommendWorldId: int
    TextLanguageType: int  # LanguageType enum
    VoiceLanguageType: int  # LanguageType enum
    WarningMessageInfos: list[dict]
    WorldIdList: list[int]
    SelectShopProductInfoDict: dict[int, list[dict]]
    StripeShopProductInfo: dict
    SpecialWorldDict: dict[int, str]
    UserSyncData: dict


class LoginPlayerResponse(TypedDict):
    AuthTokenOfMagicOnion: str
    BanChatInfo: dict
    UserSyncData: UserSyncData


# endregion


# region Refresh Data


class GetUserDataResponse(TypedDict):
    IsNotClearDungeonBattleMap: bool
    GachaSelectListCharacterIds: list[int]
    UserSyncData: UserSyncData


class GetMypageResponse(TypedDict):
    DisplayNoticeIdList: list[int]
    ExistNewFriendPointTransfer: bool
    ExistNewPrivateChat: bool
    ExistNotReceivedBountyQuestReward: bool
    ExistNotReceivedMissionReward: bool
    LatestAnnounceChatRegistrationLocalTimestamp: int
    MissionGuideInfo: MissionGuideInfo
    MypageInfo: DisplayMypageInfo
    NotOrderedBountyQuestIdList: list[int]
    UnreadIndividualNotificationIdList: list[int]
    UserFriendDtoInfoList: list[UserFriendDtoInfo]
    GuildSyncData: GuildSyncData
    UserSyncData: UserSyncData


class DisplayMypageInfo(TypedDict):
    MypageBannerInfos: list[MypageBannerInfo]
    MypageIconInfos: list[MypageIconInfo]


class MissionGuideInfo(TypedDict):
    GuideId: int
    MissionGroupType: e.MissionGroupType
    MissionStatus: e.MissionStatusType


class MypageBannerInfo(TypedDict):
    DisplayPriority: int
    ImageId: int
    MBId: int
    SortOrder: int
    TransferDetailInfo: TransferDetailInfo


class MypageIconInfo(TypedDict):
    BadgeType: e.BadgeType
    DisplayPriority: int
    HidePriority: int
    IconNameKey: str
    Id: int
    ImageId: int
    IsBlackout: bool
    IsDisplayBadge: bool
    NotOpenEventStoreIconId: int
    OpenContentLocalTimestamp: int
    SortOrder: int
    StoredIconInfoList: list[MypageIconInfo]
    StoreIconId: int
    TransferDetailInfo: TransferDetailInfo


class SnsInfo(TypedDict):
    NameKey: str
    Url: str
    MissionAchievementType: e.MissionAchievementType


class TransferDetailInfo(TypedDict):
    NumberInfo1: int
    NumberInfo2: int
    StringInfo: str
    TransferSpotType: e.TransferSpotType


# endregion


# region Player


class PlayerInfo(TypedDict):
    DeckUserCharacterInfoList: list[UserCharacterInfo]
    BattlePower: int
    Comment: str
    CumulativeGuildFame: int
    FriendStatus: e.FriendStatusType
    GuildId: int
    GuildJoinRequestUtcTimeStamp: int
    GuildJoinTimeStamp: int
    GuildName: str
    GuildPeriodTotalFame: int
    IsBlock: bool
    IsRecruit: bool
    LastLoginTime: int  # Divide by 1,000,000 to get the time delta in seconds
    LatestQuestId: int
    LatestTowerBattleQuestId: int
    LocalRaidBattlePower: int
    MainCharacterIconId: int
    NpcNameKey: str
    PlayerGuildPositionType: e.PlayerGuildPositionType
    PlayerId: int
    PlayerLevel: int
    PlayerName: str
    PrevLegendLeagueClass: e.LegendLeagueClassType


class UserCharacterInfo(TypedDict):
    Guid: str
    PlayerId: int
    CharacterId: int
    Level: int
    SubLevel: int
    Exp: int
    RarityFlags: e.CharacterRarity
    IsLocked: bool


class UserSyncData(TypedDict):
    BlockPlayerIdList: list[int]
    CanJoinTodayLegendLeague: bool | None
    ClearedTutorialIdList: list[int]
    CreateUserIdTimestamp: int | None
    CreateWorldLocalTimeStamp: int | None
    DataLinkageMap: dict[e.SnsType, bool]
    DeletedCharacterGuidList: list[str]
    DeletedEquipmentGuidList: list[str]
    ExistUnconfirmedRetrieveItemHistory: bool | None
    ExistVipDailyGift: bool | None
    GivenItemCountInfoList: list[UserItem]
    GuildJoinLimitCount: int | None
    HasTransitionedPanelPictureBook: bool | None
    IsDataLinkage: bool | None
    IsJoinedGlobalGvg: bool | None
    IsJoinedLocalGvg: bool | None
    IsReceivedSnsShareReward: bool | None
    IsRetrievedItem: bool | None
    IsValidContractPrivilege: bool | None
    LeadLockEquipmentDialogInfoMap: dict[e.LockEquipmentDeckType, LeadLockEquipmentDialogInfo]
    LegendLeagueClassType: e.LegendLeagueClassType | None
    LocalRaidChallengeCount: int | None
    LockedEquipmentCharacterGuidListMap: dict[e.LockEquipmentDeckType, list[str]]
    LockedUserEquipmentDtoInfoListMap: dict[e.LockEquipmentDeckType, list[UserEquipmentDtoInfo]]
    PresentCount: int | None
    PrivacySettingsType: e.PrivacySettingsType | None
    ReceivableAchieveRankingRewardIdMap: dict[e.RankingDataType, int]
    ReceivedAchieveRankingRewardIdList: list[int]
    ReceivedAutoBattleRewardLastTime: int | None
    ReceivedGuildTowerFloorRewardIdList: list[int]
    ReleaseLockEquipmentCooldownTimeStampMap: dict[e.LockEquipmentDeckType, int]
    ShopCurrencyMissionProgressMap: dict[str, int]
    ShopProductGuerrillaPackList: list[ShopProductGuerrillaPack]
    StripePoint: int
    TimeServerId: int | None
    TreasureChestCeilingCountMap: dict[int, int]
    UserBattleBossDtoInfo: UserBattleBossDtoInfo
    UserBattleLegendLeagueDtoInfo: UserBattleLegendLeagueDtoInfo
    UserBattlePvpDtoInfo: UserBattlePvpDtoInfo
    UserBoxSizeDtoInfo: UserBoxSizeDtoInfo
    UserCharacterBookDtoInfos: list[UserCharacterBookDtoInfo]
    UserCharacterCollectionDtoInfos: list[UserCharacterCollectionDtoInfo]
    UserCharacterDtoInfos: list[UserCharacterDtoInfo]
    UserDeckDtoInfos: list[UserDeckDtoInfo]
    UserEquipmentDtoInfos: list[UserEquipmentDtoInfo]
    UserItemDtoInfo: list[UserItemDtoInfo]
    UserLevelLinkDtoInfo: UserLevelLinkDtoInfo
    UserLevelLinkMemberDtoInfos: list[UserLevelLinkMemberDtoInfo]
    UserMissionActivityDtoInfos: list[UserMissionActivityDtoInfo]
    UserMissionDtoInfos: list[UserMissionDtoInfo]
    UserMissionOccurrenceHistoryDtoInfo: UserMissionOccurrenceHistoryDtoInfo
    UserFriendMissionDtoInfoList: list[UserFriendMissionDtoInfo]
    UserNotificationDtoInfoInfos: list[UserNotificationDtoInfo]
    UserOpenContentDtoInfos: list[UserOpenContentDtoInfo]
    UserRecruitGuildMemberSettingDtoInfo: UserRecruitGuildMemberSettingDtoInfo
    UserSettingsDtoInfoList: list[UserSettingsDtoInfo]
    UserShopAchievementPackDtoInfos: list[UserShopAchievementPackDtoInfo]
    UserShopFirstChargeBonusDtoInfo: UserShopFirstChargeBonusDtoInfo
    UserShopFreeGrowthPackDtoInfos: list[UserShopFreeGrowthPackDtoInfo]
    UserShopMonthlyBoostDtoInfos: list[UserShopMonthlyBoostDtoInfo]
    UserShopSubscriptionDtoInfos: list[UserShopSubscriptionDtoInfo]
    UserStatusDtoInfo: UserStatusDtoInfo
    UserTowerBattleDtoInfos: list[UserTowerBattleDtoInfo]
    UserVipGiftDtoInfos: list[UserVipGiftDtoInfo]


# endregion


# region Guild


class GuildInfo(TypedDict):
    GuildExp: int
    GuildId: int
    GuildLevel: int
    GuildFame: int
    GuildMemberCount: int
    GuildOverView: GuildOverView
    LeaderPlayerInfo: PlayerInfo


class GuildOverView(TypedDict):
    ActivityPolicyType: e.GuildActivityPolicyType
    GuildDescription: str
    GuildName: str
    IsFreeJoin: bool
    RequireBattlePower: int


class GuildSyncData(TypedDict):
    ApplyPlayerInfoList: list[PlayerInfo]
    CreateGuildLocalTime: int
    GlobalGvgGroupType: e.GlobalGvgGroupType
    GuildAnnouncement: str
    GuildAnnouncementUpdateTime: int
    GuildBattlePower: int
    GuildInfo: GuildInfo
    GuildPlayerInfoList: list[PlayerInfo]
    GuildTowerBadgeInfo: GuildTowerBadgeInfo
    JoinGuildTime: int
    MatchingNumber: int
    PlayerGuildPositionType: e.PlayerGuildPositionType


class GuildTowerBadgeInfo(TypedDict):
    CurrentFloorId: int
    TodayTotalGuildWinCount: int
    TodayWinCount: int


# endregion


# region Items & Equipment


class UserItem(TypedDict):
    ItemCount: int
    ItemId: int
    ItemType: e.ItemType


class UserEquipment(TypedDict):
    """
    This class represents ``UserEquipment`` and is used for requests related to smelting.  It is similar to the
    ``UserEquipmentDtoInfo`` struct that is used in other contexts.
    """

    CharacterGuid: str | None
    HasParameter: bool
    Guid: str | None
    ItemCount: int
    # public long EquipmentId {get { return this.ItemId; }}
    ItemId: int
    ItemType: e.ItemType
    AdditionalParameterHealth: int
    AdditionalParameterIntelligence: int
    AdditionalParameterMuscle: int
    AdditionalParameterEnergy: int
    SphereId1: int
    SphereId2: int
    SphereId3: int
    SphereId4: int
    SphereUnlockedCount: int
    LegendSacredTreasureExp: int
    LegendSacredTreasureLv: int
    MatchlessSacredTreasureExp: int
    MatchlessSacredTreasureLv: int
    ReinforcementLv: int


class SmeltResponse(TypedDict):  # Same response for smelt 1 vs smelt many
    ResultEquipmentList: list[UserEquipment]
    ResultItemList: list[UserItem]
    UserSyncData: UserSyncData


class EquipmentChangeInfo(TypedDict):
    EquipmentGuid: str
    EquipmentId: int
    EquipmentSlotType: e.EquipmentSlotType
    IsInherit: bool  # Whether runes/augments should be transferred


class PresentItem(TypedDict):
    Item: UserItem
    RarityFlags: e.CharacterRarity


# endregion


# region Bounty Quest


class BountyQuestMemberInfo(TypedDict):
    PlayerId: int
    CharacterId: int
    UserCharacterGuid: str
    CharacterRarityFlags: e.CharacterRarity


# endregion


# region Shop


class TradeShopItem(TypedDict):
    TradeShopItemId: int
    ConsumeItem1: UserItem
    ConsumeItem2: UserItem
    GiveItem: UserItem
    SalePercent: int
    TradeCount: int
    LimitTradeCount: int
    SacredTreasureType: e.SacredTreasureType
    SortOrder: int
    RequiredCharacterId: int
    Disabled: bool
    ExpirationTimeStamp: int


class ShopProductGuerrillaPack(TypedDict):
    DialogImageId: int
    DiscountRate: int
    EndTime: int
    NameKey: str
    ProductIdDict: dict[e.DeviceType, str]
    ShopGuerrillaPackRankType: e.ShopGuerrillaPackRankType
    ShopProductPrice: int
    ShopGuerrillaPackId: int
    TextKey: str
    UserItemList: list[UserItem]


class UserShopAchievementPackDtoInfo(TypedDict):
    ChapterId: int
    ShopAchievementPackId: int


class UserShopCurrencyMissionRewardDtoInfo(TypedDict):
    IsReceiveCommon: bool
    IsReceivePremium: bool
    RequiredPoint: int


class UserShopFirstChargeBonusDtoInfo(TypedDict):
    IsReceivedDay1: bool
    IsReceivedDay2: bool
    IsReceivedDay3: bool
    OpenTimeStamp: int


class UserShopFreeGrowthPackDtoInfo(TypedDict):
    ShopGrowthPackId: int
    IsBuff: bool
    PlayerId: int
    ReceiveDateTime: datetime
    ShopProductGrowthPackId: int


class UserShopMonthlyBoostDtoInfo(TypedDict):
    ExpirationTimeStamp: int
    IsPrePurchased: bool
    LatestReceivedDate: int
    PlayerId: int
    PrevReceivedDate: int
    ShopMonthlyBoostId: int


# endregion


# region Character


class BaseParameter(TypedDict):
    Energy: int
    Health: int
    Intelligence: int
    Muscle: int


# endregion


# region PvP


class LeadLockEquipmentDialogInfo(TypedDict):
    DialogType: e.LeadLockEquipmentDialogType
    PassedDays: int


# endregion


# region Battle


class BattleField(TypedDict):
    BattleType: e.BattleType
    Characters: list[BattleFieldCharacter]
    AttackTeamPassiveSkillIds: list[int]
    ReceiveTeamPassiveSkillIds: list[int]
    AttackTeamTotalKillCount: int
    ReceiveTeamTotalKillCount: int


class BattleFieldCharacter(TypedDict):
    PlayerName: str
    CharacterGuid: str
    CharacterLevel: int
    CharacterRarityFlags: e.CharacterRarity
    EquipmentMaxLevel: int
    EquipmentDtoInfos: list[UserEquipmentDtoInfo]
    UnitType: e.UnitType
    UnitId: int
    JobFlags: e.Job
    ElementType: e.Element
    DefaultBaseParameter: BaseParameter
    DefaultBattleParameter: BattleParameter
    BattleParameterWithoutBonus: BattleParameter
    OnStartHP: int
    DefaultPosition: BattlePosition
    Guid: int
    NormalSkill: BattleActiveSkill
    ActiveSkills: list[BattleActiveSkill]
    PassiveSkills: list[BattlePassiveSkill]
    OwnerPlayerId: int
    PlayerRankHitBonus: int
    DungeonBattleInfo: DungeonBattleInfo


class BattleActiveSkill(TypedDict):
    ActiveSkillId: int
    SkillOrderNumber: int
    SkillMaxCoolTime: int
    SkillCoolTime: int
    SubSetSkillIds: list[int]


class BattlePassiveSkill(TypedDict):
    PassiveSkillId: int
    PassiveSubSetSkillInfos: list[PassiveSubSetSkillInfo]


class PassiveSubSetSkillInfo(TypedDict):
    PassiveTrigger: e.PassiveTrigger
    SkillCoolTime: int
    SkillMaxCoolTime: int
    PassiveGroupId: int
    SubSetSkillId: int


class BattleParameter(TypedDict):
    AttackPower: int
    Avoidance: int
    Critical: int
    CriticalDamageEnhance: int
    CriticalResist: int
    DamageEnhance: int
    DamageReflect: int
    DebuffHit: int
    DebuffResist: int
    Defense: int
    DefensePenetration: int
    Hit: int
    HP: int
    HpDrain: int
    MagicCriticalDamageRelax: int
    MagicDamageRelax: int
    PhysicalCriticalDamageRelax: int
    PhysicalDamageRelax: int
    Speed: int


class BattlePosition(TypedDict):
    DeckIndex: int
    GroupType: e.BattleFieldCharacterGroupType


class DungeonBattleInfo(TypedDict):
    DungeonBattleVictoryCount: int
    IsDungeonBattleHardMode: bool
    UseDungeonRecoveryItemCount: int
    UseDungeonRelicCountDict: dict[int, int]


class Effect(TypedDict):
    EffectType: e.EffectType
    EffectValue: int
    EffectMaxCount: int
    EffectCount: int


class TransientEffect(TypedDict):
    EffectType: e.EffectType
    EffectValue: int
    HitType: e.HitType
    AddEffectGroups: list[EffectGroup]
    RemoveEffectGroups: list[EffectGroup]


class EffectGroup(TypedDict):
    EffectGroupId: int
    SkillCategory: e.SkillCategory
    EffectGroupType: e.EffectGroupType
    EffectTurn: int
    Effects: list[Effect]
    RemoveEffectType: e.RemoveEffectType
    LinkTargetGuid: int
    GranterGuid: int
    IsExtendEffectTurn: bool


# endregion


# region Battle Results


class BattleResult(TypedDict):
    BattleTime: BattleTime
    QuestId: int
    Reward: BattleReward
    SimulationResult: BattleSimulationResult


class BattleReward(TypedDict):
    CharacterExp: int
    DropItemList: list[UserItem]
    FixedItemList: list[UserItem]
    PlayerExp: int
    PopulationGold: int
    PopulationPotentialJewel: int


class BattleTime(TypedDict):
    StartBattle: int
    EndBattle: int
    TotalCommand: int
    TotalCommandOrMinBattleTime: int


class BattleSimulationResult(TypedDict):
    BattleEndInfo: BattleEndInfo
    BattleField: BattleField
    BattleLog: BattleLog
    BattleToken: str
    BattleCharacterReports: list[BattleCharacterReport]


class BattleCharacterReport(TypedDict):
    PlayerName: str
    OwnerPlayerId: int
    DeckIndex: int
    GroupType: e.BattleFieldCharacterGroupType
    CharacterGuid: str
    BattleCharacterGuid: int
    UnitType: e.UnitType
    UnitId: int
    CharacterLevel: int
    CharacterRarityFlags: e.CharacterRarity
    ElementType: e.Element
    TotalGiveDamage: int
    TotalHpRecovery: int
    TotalReceiveDamage: int
    MaxHp: int
    Hp: int


class BattleEndInfo(TypedDict):
    IsOutOfTurn: bool
    EndTurn: int
    WinGroupType: e.BattleFieldCharacterGroupType
    WinPlayerIdSet: set[int]


class BattleLog(TypedDict):
    BattleStartPassiveResults: list[SubSkillResult]
    BattleEndPassiveResults: list[SubSkillResult]
    BattleSubLogs: list[BattleSubLog]


class BattleSubLog(TypedDict):
    TurnStartPassiveResults: list[SubSkillResult]
    TurnEndPassiveResults: list[SubSkillResult]
    ActiveSkillDatas: list[ActiveSkillData]
    Turn: int


class ActiveSkillData(TypedDict):
    TransientEffectResult: TransientEffectResult
    ActiveSkillId: int
    SubSetSkillResults: list[SubSetSkillResult]
    ActionStartSubSkillResults: list[SubSkillResult]
    ActionEndSubSkillResults: list[SubSkillResult]
    TurnEndSubSkillResults: list[SubSkillResult]
    IsNonActionStance: bool
    FromGuid: int


class SubSkillResult(TypedDict):
    SubSkillResultType: e.SubSkillResultType
    SubSkillIndex: int
    SkillDisplayType: e.SkillDisplayType
    AttackUnitGuid: int
    TargetUnitGuid: int
    AddEffectGroups: list[EffectGroup]
    RemoveEffectGroups: list[EffectGroup]
    HitType: e.HitType
    ChangeHp: int
    TargetRemainHp: int


class SubSetSkillResult(TypedDict):
    DamageSubSkillResults: list[SubSkillResult]
    EffectSubSkillResults: list[SubSkillResult]
    PassiveSubSkillResults: list[SubSkillResult]
    TempSubSkillResults: list[SubSkillResult]
    SubSkillResults: list[SubSkillResult]
    SubSetType: e.SubSetType


class TransientEffectResult(TypedDict):
    TransientEffects: list[TransientEffect]
    TransientEffectSubSkillResults: list[SubSkillResult]
    RemainHp: int


# endregion


# region Tower Battle Results


class TowerBattleResponse(TypedDict):  # renamed from `StartResponse`
    BattleResult: BattleResult
    BattleRewardResult: BattleRewardResult
    TowerBattleRewardsItemList: list[TowerBattleRewardsItem]
    UserSyncData: UserSyncData


class BattleRewardResult(TypedDict):
    CharacterExp: int
    DropItemList: list[UserItem]
    ExtraGold: int
    FixedItemList: list[UserItem]
    PlayerExp: int
    RankUp: int


class TowerBattleRewardsItem(TypedDict):
    Item: UserItem
    RewardsType: e.TowerBattleRewardsType


# endregion


# region PvP Battle Results


class GetPvpInfoResponse(TypedDict):
    CurrentRank: int
    ExistNewDefenseBattleLog: bool
    MatchingRivalList: list[PvpRankingPlayerInfo]
    TopRankerList: list[PvpRankingPlayerInfo]
    UserSyncData: UserSyncData


class GetPvpBattleLogsResponse(TypedDict):
    AttackPvpBattleLogInfoList: list[PvpBattleLogInfo]
    DefensePvpBattleLogInfoList: list[PvpBattleLogInfo]


class GetPvpBattleResultDetailResponse(TypedDict):
    BattleResult: BattleResult


class PvpBattleLogInfo(TypedDict):
    AttackBattlePower: int
    AttackCharacterBaseParameterMap: dict[str, BaseParameter]
    AttackCharacterBattleParameterMap: dict[str, BattleParameter]
    AttackCharacterInfoList: list[UserCharacterInfo]
    AttackEquipmentDtoInfoListMap: dict[str, list[UserEquipmentDtoInfo]]
    BattleEndInfo: BattleEndInfo
    BattleTime: int
    BattleToken: str
    DefenseBattlePower: int
    DefenseCharacterBaseParameterMap: dict[str, BaseParameter]
    DefenseCharacterBattleParameterMap: dict[str, BattleParameter]
    DefenseCharacterInfoList: list[UserCharacterInfo]
    DefenseEquipmentDtoInfoListMap: dict[str, list[UserEquipmentDtoInfo]]
    NewRank: int
    OldRank: int
    RivalPlayerInfo: PlayerInfo


class PvpRankingPlayerInfo(TypedDict):
    CurrentRank: int
    DefenseBattlePower: int
    PlayerInfo: PlayerInfo
    UserCharacterInfoList: list[UserCharacterInfo]


# endregion


# region DtoInfo


class GuildRaidBossInfo(TypedDict):
    BossGuid: str
    Name: str
    MaxHp: int
    TotalDamage: int
    StartTimeStamp: int
    EndTimeStamp: int
    CurrentHp: int


class GuildRaidDtoInfo(TypedDict):
    BossType: e.GuildRaidBossType
    CloseLimitTime: int
    LastReleaseTime: int
    TotalChallengeCount: int
    TotalDamage: int


class UserBattleAutoDtoInfo(TypedDict):
    AverageBattleTime: int
    BattleEfficiency: int
    ConsecutiveWinCount: int
    CurrentQuestId: int
    CurrentMaxQuestId: int
    ExpectedCharacterExp: int
    ExpectedPlayerExp: int
    QuickLastExecuteTime: int
    QuickTodayUseCurrencyCount: int
    QuickTodayUsePrivilegeCount: int
    BattleResult: BattleResult


class UserBattleBossDtoInfo(TypedDict):
    BossLastChallengeTime: int
    BossClearMaxQuestId: int
    BossTodayUseCurrencyCount: int
    BossTodayUseTicketCount: int
    BossTodayWinCount: int
    IsOpenedNewQuest: bool


class UserBattleLegendLeagueDtoInfo(TypedDict):
    AttackSucceededNum: int
    DefenseSucceededNum: int
    LegendLeagueLastChallengeTime: int
    LegendLeagueTodayCount: int
    LegendLeagueTodayUseCurrencyCount: int
    LegendLeagueConsecutiveVictoryCount: int


class UserBattlePvpDtoInfo(TypedDict):
    AttackSucceededNum: int
    DefenseSucceededNum: int
    GetTodayDefenseSucceededRewardCount: int
    MaxRanking: int
    PvpLastChallengeTime: int
    PvpTodayCount: int
    PvpTodayUseCurrencyCount: int


class UserBountyQuestBoardDtoInfo(TypedDict):
    BountyQuestType: e.BountyQuestType
    BountyQuestRarity: e.BountyQuestRarityFlags
    ClearCount: int


class UserBountyQuestDtoInfo(TypedDict):
    Date: int
    BountyQuestId: int
    BountyQuestType: e.BountyQuestType
    BountyQuestLimitStartTime: int
    BountyQuestEndTime: int
    RewardEndTime: int
    IsReward: bool
    StartMembers: list[BountyQuestMemberInfo]


class UserBountyQuestMemberDtoInfo(TypedDict):
    UserCharacterGuid: str
    CharacterId: int
    RarityFlags: e.CharacterRarity
    DispatchPlayerId: int
    DispatchPlayerName: str
    DispatchEndTime: int
    PlayerId: int


class UserBoxSizeDtoInfo(TypedDict):
    CharacterBoxSizeId: int
    PlayerId: int


class UserCharacterBookDtoInfo(TypedDict):
    CharacterId: int
    MaxCharacterLevel: int
    MaxCharacterRarityFlags: e.CharacterRarity
    MaxEpisodeId: int


class UserCharacterCollectionDtoInfo(TypedDict):
    CharacterCollectionId: int
    CollectionLevel: int


class UserCharacterDtoInfo(TypedDict):
    Guid: str
    PlayerId: int
    CharacterId: int
    Level: int
    Exp: int
    RarityFlags: e.CharacterRarity
    IsLocked: bool


class UserDeckDtoInfo(TypedDict):
    DeckNo: int
    DeckUseContentType: e.DeckUseContentType
    DeckBattlePower: int
    UserCharacterGuid1: str
    CharacterId1: int
    UserCharacterGuid2: str
    CharacterId2: int
    UserCharacterGuid3: str
    CharacterId3: int
    UserCharacterGuid4: str
    CharacterId4: int
    UserCharacterGuid5: str
    CharacterId5: int


class UserDungeonBattleCharacterDtoInfo(TypedDict):
    CharacterId: int
    CurrentHpPerMill: int
    GuestId: int
    Guid: str


class UserDungeonBattleDtoInfo(TypedDict):
    CurrentBoughtShopCounts: list[int]
    CurrentGridGuid: str
    CurrentGridState: e.DungeonBattleGridState
    DoneGridGuids: list[str]
    DoneRewardClearLayers: list[int]
    GuestCharacterMap: dict[str, list[int]]
    IsLostLatestBattle: bool
    RelicIds: list[int]
    UseDungeonRecoveryItemCount: int


class UserDungeonBattleEnemyDtoInfo(TypedDict):
    EnemyDataJson: str
    EnemyGuid: int
    GroupId: int
    IsNpc: bool
    NpcEnemyDataJson: str


class UserDungeonBattleGuestCharacterDtoInfo(TypedDict):
    BaseParameter: BaseParameter
    BattleParameter: BattleParameter
    BattlePower: int
    CharacterId: int
    GuestEquipmentDtoInfos: list[UserEquipmentDtoInfo]
    Guid: str
    Level: int
    PlayerId: int
    RarityFlags: e.CharacterRarity


class UserDungeonBattleMissedCountDtoInfo(TypedDict):
    LatestChallengeTermId: int
    MissedCount: int
    PlayerId: int


class UserDungeonBattleShopDtoInfo(TypedDict):
    GridGuid: str
    PlayerId: int
    TermId: int
    TradeShopItemList: list[TradeShopItem]


class UserEquipmentDtoInfo(TypedDict):
    CharacterGuid: str
    CreateAt: int
    PlayerId: int
    AdditionalParameterHealth: int
    AdditionalParameterIntelligence: int
    AdditionalParameterMuscle: int
    AdditionalParameterEnergy: int
    EquipmentId: int
    Guid: str
    SphereId1: int
    SphereId2: int
    SphereId3: int
    SphereId4: int
    SphereUnlockedCount: int
    LegendSacredTreasureExp: int
    LegendSacredTreasureLv: int
    MatchlessSacredTreasureExp: int
    MatchlessSacredTreasureLv: int
    ReinforcementLv: int


class UserFriendDtoInfo(TypedDict):
    FriendPointSendDate: int
    FriendStatusType: e.FriendStatusType
    IsChecked: bool
    IsReceived: bool
    OtherPlayerId: int
    RegistrationDate: int


class UserFriendMissionDtoInfo(TypedDict):
    FriendCampaignId: int
    AchievementType: e.MissionAchievementType
    ProgressCount: int
    MissionStatusHistory: dict[e.MissionStatusType, list[int]]


class UserGuildRaidDtoInfo(TypedDict):
    BattleLogAtMaxDamageJson: str
    BossGuid: str
    ChallengeCount: int
    DropItemJson: str
    MaxDamage: int
    TotalDamage: int


class UserGuildRaidPreviousDtoInfo(TypedDict):
    BattleLogJson: str
    Damage: int
    DropItemCount: int
    GuildRaidBossType: e.GuildRaidBossType


class UserItemDtoInfo(TypedDict):
    ItemCount: int
    ItemId: int
    ItemType: e.ItemType
    PlayerId: int


class UserLevelLinkDtoInfo(TypedDict):
    PartyMaxLevel: int
    PartyLevel: int
    PartySubLevel: int
    MemberMaxCount: int
    BuyFrameCount: int
    IsPartyMode: bool


class UserLevelLinkMemberDtoInfo(TypedDict):
    CellNo: int
    UserCharacterGuid: str
    CharacterId: int
    UnavailableTime: int


class UserMapBuildingDtoInfo(TypedDict):
    SelectedIndex: int
    QuestMapBuildingId: int


class UserMissionActivityDtoInfo(TypedDict):
    MissionGroupType: e.MissionGroupType
    PlayerId: int
    ProgressCount: int
    RewardStatusDict: dict[int, e.MissionActivityRewardStatusType]


class UserMissionDtoInfo(TypedDict):
    AchievementType: e.MissionAchievementType
    MissionStatusHistory: dict[e.MissionStatusType, list[int]]
    MissionType: e.MissionType
    PlayerId: int
    ProgressCount: int


class UserMissionOccurrenceHistoryDtoInfo(TypedDict):
    BeginnerStartTime: int
    ComebackStartTime: int
    DailyStartTime: int
    WeeklyStartTime: int
    LimitedStartTime: int
    LimitedMissionMBId: int
    NewCharacterMissionMBId: int


class UserNotificationDtoInfo(TypedDict):
    NotificationType: e.NotificationType
    Value: int


class UserOpenContentDtoInfo(TypedDict):
    OpenContentId: int


class UserPanelMissionDtoInfo(TypedDict):
    SheetNo: int
    ReceivedBingoTypeList: list[e.BingoType]


class UserPresentDtoInfo(TypedDict):
    CreateAt: int
    DisplayLimitDate: int
    Guid: str
    IsReceived: bool
    ItemList: list[PresentItem]
    Message: str
    ReceiveLimitDate: int
    Title: str


class UserRecruitGuildMemberSettingDtoInfo(TypedDict):
    GuildPowerLowerLimit: int
    GuildLvLowerLimit: int
    IsRecruit: bool


class UserSettingsDtoInfo(TypedDict):
    PlayerSettingsType: e.PlayerSettingsType
    Value: int
    PlayerId: int


class UserShopSubscriptionDtoInfo(TypedDict):
    ProductId: str
    DeviceType: e.DeviceType
    TransactionId: str
    ExpirationTimeStamp: int


class UserStatusDtoInfo(TypedDict):
    CreateAt: int
    IsFirstVisitGuildAtDay: bool
    IsReachBattleLeagueTop50: bool
    IsAlreadyChangedName: bool
    Birthday: int
    Comment: str
    PlayerId: int
    MainCharacterIconId: int
    FavoriteCharacterId1: int
    FavoriteCharacterId2: int
    FavoriteCharacterId3: int
    FavoriteCharacterId4: int
    FavoriteCharacterId5: int
    Name: str
    Rank: int
    BoardRank: int
    Exp: int
    Vip: int
    LastLoginTime: int
    PreviousLoginTime: int
    LastLvUpTime: int
    VipExp: int


class UserTowerBattleDtoInfo(TypedDict):
    BoughtCount: int
    LastUpdateTime: int
    MaxTowerBattleId: int  # "quest id" for the last floor that was cleared in this tower; add 1 for target quest id
    PlayerId: int
    TodayBattleCount: int
    TodayBoughtCountByCurrency: int
    TodayClearNewFloorCount: int  # When == 10 for mono-soul towers, stop (ClientErrorMessage1700007)
    TowerType: e.TowerType


class UserVipGiftDtoInfo(TypedDict):
    PlayerId: int
    VipGiftId: int
    VipLv: int


# endregion
