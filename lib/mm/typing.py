"""

"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict, Any

if TYPE_CHECKING:
    from .enums import ErrorLogType, LegendLeagueClassType, ItemType, EquipmentSlotType

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
    ErrorLogType: ErrorLogType
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
    LegendLeagueClass: LegendLeagueClassType
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
    UserSyncData: dict[str, Any]  # -> mm.data.UserSyncData


# endregion


# region Refresh Data


class GetUserDataResponse(TypedDict):
    IsNotClearDungeonBattleMap: bool
    GachaSelectListCharacterIds: list[int]
    UserSyncData: dict[str, Any]  # -> mm.data.UserSyncData


class GetMypageResponse(TypedDict):
    DisplayNoticeIdList: list[int]
    ExistNewFriendPointTransfer: bool
    ExistNewPrivateChat: bool
    ExistNotReceivedBountyQuestReward: bool
    ExistNotReceivedMissionReward: bool
    LatestAnnounceChatRegistrationLocalTimestamp: int
    MissionGuideInfo: dict  # MissionGuideInfo
    MypageInfo: dict  # DisplayMypageInfo
    NotOrderedBountyQuestIdList: list[int]
    UnreadIndividualNotificationIdList: list[int]
    UserFriendDtoInfoList: list[dict]  # list[UserFriendDtoInfo]
    GuildSyncData: dict  # GuildSyncData
    UserSyncData: dict[str, Any]  # -> mm.data.UserSyncData


# endregion


# region Equipment


class UserItem(TypedDict):
    ItemCount: int
    ItemId: int
    ItemType: ItemType


class UserEquipment(TypedDict):
    CharacterGuid: str
    HasParameter: bool
    Guid: str
    ItemCount: int
    # public long EquipmentId {get { return this.ItemId; }}
    ItemId: int
    ItemType: ItemType
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
    UserSyncData: dict[str, Any]  # -> mm.data.UserSyncData


class EquipmentChangeInfo(TypedDict):
    EquipmentGuid: str
    EquipmentId: int
    EquipmentSlotType: EquipmentSlotType
    IsInherit: bool  # Whether runes/augments should be transferred


# endregion
