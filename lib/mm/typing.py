"""

"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict, Any, Collection

if TYPE_CHECKING:
    from .enums import ErrorLogType, LegendLeagueClassType
#     from .data import UserSyncData as _UserSyncData


class ApiErrorResponse(TypedDict):
    ErrorCode: int  # ErrorCode
    Message: str
    ErrorHandlingType: int  # ErrorHandlingType (Obsolete)
    ErrorMessageId: int  # Obsolete
    MessageParams: list[str]  # Obsolete


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


class ErrorLogInfo(TypedDict):
    ApiName: str
    ErrorCode: int
    ErrorLogType: ErrorLogType
    LocalTimeStamp: int
    Message: str


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
