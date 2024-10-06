"""
Enums used by the game
"""

from __future__ import annotations

import logging
from enum import CONFORM, IntEnum, IntFlag, StrEnum
from functools import cached_property
from math import log as _log

__all__ = ['Region', 'Locale', 'LOCALES']
log = logging.getLogger(__name__)


# region Locale / Region


class Locale(StrEnum):
    # ls -1 temp/mb/TextResource* | sed 's#temp/mb/TextResource##g' | sed -E "s#(....)MB\.json#'\\1',#g" | paste -sd ' '

    num: int

    def __new__(cls, value, num: int):
        obj = str.__new__(cls)
        obj._value_ = value
        obj.num = num
        return obj

    DeDe = 'DeDe', 13
    EnUs = 'EnUs', 2
    EsMx = 'EsMx', 7
    FrFr = 'FrFr', 5
    IdId = 'IdId', 10
    JaJp = 'JaJp', 1
    KoKr = 'KoKr', 3
    PtBr = 'PtBr', 8
    RuRu = 'RuRu', 12
    ThTh = 'ThTh', 9
    ViVn = 'ViVn', 11
    ZhCn = 'ZhCn', 6
    ZhTw = 'ZhTw', 4

    @property
    def country_code(self) -> str:
        return self._value_[2:].upper()

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            try:
                a, b, c, d = value
            except ValueError:
                pass
            else:
                key = a.upper() + b.lower() + c.upper() + d.lower()
                try:
                    return cls._member_map_[key]
                except KeyError:
                    pass
        return super()._missing_(value)

    def __str__(self) -> str:
        return self._value_

    def __hash__(self) -> int:
        return hash(self.__class__) ^ hash(self._value_)

    def __eq__(self, other: Locale) -> bool:
        return self._value_ == other._value_

    def __lt__(self, other: Locale) -> bool:
        return self._value_ < other._value_

    def __bool__(self) -> bool:
        return True


LOCALES = list(Locale)


class Region(IntEnum):
    JAPAN = 1
    KOREA = 2
    ASIA = 3
    NORTH_AMERICA = 4
    EUROPE = 5
    GLOBAL = 6

    @classmethod
    def for_world(cls, world_id: int) -> Region:
        region = world_id // 1000
        try:
            return cls(region)
        except ValueError as e:
            raise ValueError(f'Invalid {region=} for {world_id=}') from e

    def normalize_world(self, world_id: int) -> int:
        if world_id > 1000:
            return world_id
        return (self._value_ * 1000) + world_id


# endregion


# region Runes


class RuneRarity(StrEnum):
    R = 'R'
    SR = 'SR'
    SSR = 'SSR'
    UR = 'UR'
    LR = 'LR'


# endregion


# region Game Client Internals


class SnsType(IntEnum):
    # Note: C# enums with no explicit values start from 0 and increase by 1 for each item
    NONE = 0
    OrtegaId = 1
    AppleId = 2
    Twitter = 3
    Facebook = 4
    GameCenter = 5
    GooglePlay = 6


class DeviceType(IntEnum):
    iOS = 1
    Android = 2
    UnityEditor = 3
    Win64 = 4
    DmmGames = 5
    Steam = 6
    Apk = 7


class NotificationType(IntEnum):
    NONE = 0
    NewGachaTicket = 1
    MaxRarityInSelectList = 2
    NewCharacterInSelectList = 3
    GachaFreeCount = 4
    GuildRaidAvailable = 5
    NewGuildJoinRequest = 6
    GuildLevelUp = 7
    LocalGvgReward = 8
    GlobalGvgReward = 9
    NewRetrieveItem = 10
    ReceivableGuildMission = 11
    NewRecruitGuildMember = 12
    ReceivableGuildTowerMission = 13


class BingoType(IntEnum):
    NONE = 0
    UpperRow = 1
    CenterRow = 2
    LowerRow = 3
    LeftColumn = 4
    CenterColumn = 5
    RightColumn = 6


class PlayerSettingsType(IntEnum):
    NONE = 0
    AutoSellRarityNCharacter = 1


class PrivacySettingsType(IntEnum):
    NONE = 0
    OptIn = 1
    OptOut = 2


class RankingDataType(IntEnum):
    NONE = 0
    PlayerBattlePower = 1
    PlayerRank = 2
    PlayerMainQuest = 3
    PlayerTower = 4
    TowerBlue = 5
    TowerRed = 6
    TowerGreen = 7
    TowerYellow = 8


class BadgeType(IntEnum):
    Normal = 0
    Special = 1


class TransferSpotType(IntEnum):
    NONE = 0
    AutoBattle = 10
    BountyQuest = 20
    DungeonBattle = 30
    GachaCase = 40
    Competition = 50
    LocalRaid = 60
    Notice = 70
    ShopTab = 80
    ShopItem = 81
    TowerBattle = 90
    TowerBattleSelectTower = 91
    TradeShop = 100
    OuterWebSite = 110
    MonthlyLoginBonus = 120
    LimitedLoginBonus = 121
    BeginnerMission = 130
    ComebackMission = 131
    NewCharacterMission = 132
    EventMission = 133
    FriendCampaign = 134
    PanelMission = 135
    GuerrillaPack = 140
    StoreIcon = 150
    Character = 160
    Chat = 170
    Guild = 180
    GuildRaid = 181
    GuildRaidWorldReward = 182
    RetrieveItem = 190
    GuildMemberRecruit = 200
    IndividualNotification = 210
    StarsGuidanceTradeShop = 220
    Friend = 4


# endregion


# region Errors


class ErrorLogType(IntEnum):
    NONE = 0
    ErrorCode = 1
    ClientErrorCode = 2


class ErrorCode(IntEnum):
    NONE = 0
    UncaughtException = 1
    InvalidRequestHeader = 2
    InvalidDataAppVersionMB = 3
    CommonMaintenance = 100
    CommonSectionMaintenance = 101
    CommonHardMaintenance = 102
    CommonRequireClientUpdate = 103
    CommonNoSession = 111
    CommonLoggedInAnotherDevice = 112
    CommonContainsNgWord = 201
    CommonApiInvalidRequest = 301
    CommonNotFoundMasterData = 401
    CommonNotFoundAppAssetVersionMasterData = 402
    CommonUnableToCreateUser = 998
    CommonUnableToCreatePlayer = 999
    CommonBuyProductDifferentGameServer = 1_000
    CommonDeletedPlayer = 1_001
    AuthNotFoundUserAccountDto = 10_001
    AuthNotFoundUserPlayerDto = 10_002
    AuthNotFoundPlayerDto = 10_003
    AuthAddSnsAccountInvalidRequest = 10_101
    AuthAddSnsAccountInvalidPasswordFormat = 10_102
    AuthAddSnsAccountAlreadyLinkedUserData = 10_103
    AuthCreateUserFailed = 10_201
    AuthInvalidCountryCode = 10_301
    AuthTimeServerDecisionFailed = 10_302
    AuthInvalidCountryCodeOnApk = 10_310
    AuthLoginInvalidRequest = 10_401
    AuthLoginAlreadyDeletedUser = 10_402
    AuthJoinNewWorldMaxPlayerInWorld = 10_501
    AuthJoinNewWorldInvalidRequest = 10_502
    AuthJoinNewWorldAlreadyPlayer = 10_503
    AuthJoinNewWorldInvalidTimeServer = 10_504
    AuthComebackUserNotFoundUserAccountDto = 10_601
    AuthComebackUserPasswordIsNull = 10_602
    AuthComebackUserInvalidPasswordFormat = 10_603
    AuthComebackUserInvalidPassword = 10_604
    AuthComebackUserFailedToGetPlayerDataInfo = 10_605
    AuthComebackUserFailedToGetComebackUserInfo = 10_606
    AuthComebackUserAlreadyDeletedUser = 10_607
    AuthGetServerHostInvalidTimeServer = 10_701
    AuthSetUserSettingsUserSettingsTypeOutOfRange = 10_801
    AuthGiveSnsShareRewardNotSameUserId = 10_901
    AuthGiveSnsShareRewardAlreadyReceived = 10_902
    AuthGiveSnsShareRewardFailedToGiveReward = 10_903
    AuthReserveAccountDeletionAsyncAlreadyReservedAccountDeletion = 11_001
    AuthCancelReservedAccountDeletionNotReservedAccountDeletion = 11_101
    AuthFailedToGetTwitterUserId = 12_001
    AuthUserTwitterLinkageDtoNotFound = 12_002
    AuthFailedToVerifyAppleIdToken = 12_101
    AuthUserAppleLinkageDtoNotFound = 12_102
    AuthFailedToGetGoogleUserId = 12_201
    AuthUserGoogleLinkageDtoNotFound = 12_202
    ItemEditorNotFoundCharacter = 80_000
    ItemEditorNotEnoughItem = 80_001
    ItemEditorNotEnoughCurrency = 80_002
    ItemEditorNotEnoughPaidCurrency = 80_003
    ItemEditorNotConsumableItem = 80_004
    ItemEditorCanNotGiveItem = 80_005
    ItemEditorUserBoxSizeDtoNotFound = 82_000
    ItemEditorUserStatusDtoNotFound = 82_001
    UserUserStatusDtoNotFound = 91_000
    UserUserAccountDtoNotFound = 91_003
    UserUserDeckDtoNotFound = 91_004
    UserClearPartyNotFound = 91_007
    UserTutorialDtoNotFound = 91_008
    UserNotHaveCharacter = 92_000
    UserInvalidBirthday = 92_001
    UserCanOnlySetBirthdayOnce = 92_002
    UserSelectDuplicateCharacterId = 92_003
    UserFailedAuthentication = 92_004
    UserAlreadyClearedChangeNameTutorial = 92_005
    UserNotFoundPlayerInfo = 92_006
    UserSetDeckNotFoundCharacter = 93_101
    UserSaveDeckNobodyCharacter = 93_104
    UserSaveDeckSameIdCharacter = 93_105
    UserSaveDeckOverMaxCharacterCount = 93_106
    UserSaveDeckInvalidDeckNo = 93_107
    BattleCommonUserStatusDtoNotFound = 96_000
    BattleCommonNotFoundIrregularSubSkillConditionFormula = 97_000
    BattleCommonNotFoundIrregularValueFormula = 97_001
    BattleCommonNotFoundSubSetSkillConditionFormula = 97_002
    BattleCommonNotFoundHpSubSkillConditionFormula = 97_003
    BattleCommonNotFoundHpSubSkillPowerValueFormula = 97_004
    BattleCommonNotFoundStatusSubSubSkillConditionFormula = 97_005
    BattleCommonNotFoundStatusSubSubSkillHitValueFormula = 97_006
    BattleCommonNotFoundStatusSubSubSkillEffectTurnFormula = 97_007
    BattleCommonNotFoundStatusSubSubSkillEffectValueFormula = 97_008
    BattleCommonNotFoundActiveSkillConditionFormula = 97_009
    BattleAutoUserBattleAutoDtoNotFound = 101_000
    BattleAutoUserBattleBossDtoNotFound = 101_001
    BattleAutoUserStatusDtoNotFound = 101_002
    BattleAutoUserBattleAutoRewardDtoNotFound = 101_003
    BattleAutoUserTutorialDtoNotFound = 101_004
    BattleAutoNextQuestNotFound = 102_000
    BattleAutoInvalidChangeBattleQuest = 102_001
    BattleAutoInvalidCurrencyBattleQuick = 102_002
    BattleAutoNotEnoughPrivilegeCount = 102_003
    BattleAutoInvalidQuickExecuteType = 102_005
    BattleAutoPrivilegeRemain = 102_006
    BattleAutoOverQuickMaxCount = 102_007
    BattleBossUserBattleBossDtoNotFound = 111_000
    BattleBossUserStatusDtoNotFound = 111_001
    BattleBossUserTutorialDtoNotFound = 111_002
    BattleBossUserBattleAutoDtoNotFound = 111_003
    BattleBossNotYetBossBattleClear = 112_000
    BattleBossNotEnoughBossChallengeCount = 112_001
    BattleBossImpossibleBossChallenge = 112_002
    BattleBossNextQuestNotFound = 112_003
    BattleBossOverBossChallengeMaxCount = 112_004
    BattleBossInvalidBuyBossBattleTicket = 112_005
    BattleBossNotEnoughVipLevelOrMaxQuestIdBossQuick = 112_006
    DungeonBattleCharacterDtoNotFound = 121_000
    DungeonBattleMissedCountDtoNotFound = 121_001
    DungeonBattleUserBattleAutoDtoNotFound = 121_002
    DungeonBattleUserDungeonBattleShopDtoNotFound = 121_003
    DungeonBattleUserShopItemDataNotFound = 121_004
    DungeonBattleDungeonBattleMapDtoNotFound = 121_005
    DungeonBattleUserDungeonBattleEnemyDtoNotFound = 121_006
    DungeonBattleUserDungeonBattleSkipRewardDtoNotFound = 121_007
    DungeonBattleNoActiveTerm = 122_001
    DungeonBattleOutOfTerm = 122_002
    DungeonBattleUserDataNotFound = 122_003
    DungeonBattleInvalidGrid = 122_004
    DungeonBattleInvalidGridRequest = 122_006
    DungeonBattleFirstLayerNotFound = 122_010
    DungeonBattleFirstGridNotFound = 122_011
    DungeonBattleCurrentLayerNotFound = 122_012
    DungeonBattleCurrentGridNotFound = 122_013
    DungeonBattleGuestCharacterNotEnough = 122_014
    DungeonBattleNotClearedLayerYet = 122_015
    DungeonBattleNextLayerNotFound = 122_016
    DungeonBattleCurrentGridIsNotDone = 122_020
    DungeonBattleCanNotReinforceRelic = 122_021
    DungeonBattleBattleNotSelected = 122_031
    DungeonBattleShopNotSelected = 122_040
    DungeonBattleShopItemNotFound = 122_041
    DungeonBattleShopItemAlreadyBought = 122_042
    DungeonBattleInvalidRelicId = 122_043
    DungeonBattleInvalidReinforceRelicRarity = 122_044
    DungeonBattleNotBattleGrid = 122_045
    DungeonBattleBattleResultNotFound = 122_046
    DungeonBattleAllCharacterHPFull = 122_047
    DungeonBattleDeckContainCharacterHPZero = 122_048
    DungeonBattleAlreadyGetClearLayerReward = 122_049
    DungeonBattleCharonInfoNotSetting = 122_050
    DungeonBattleAlreadyHaveRelic = 122_051
    DungeonBattleNotEnoughRelic = 122_052
    DungeonBattleAlreadyMaxHealedByItem = 122_053
    DungeonBattleNotEnoughHardModeCondition = 122_054
    DungeonBattleNotOpen = 122_055
    DungeonBattleMysteryShopBuyLimitCount = 122_056
    DungeonBattleDungeonEnemyNotEnough = 122_067
    DungeonBattleAlreadyDoneGrid = 122_068
    DungeonBattleCanNotMoveGrid = 122_069
    DungeonBattleNotSelectedEventSpecialBattleGrid = 122_070
    DungeonBattleCurrentGridIsNotEventSpecialBattleGrid = 122_071
    DungeonBattleNotLostBattleYet = 122_072
    DungeonBattleUpdatingMap = 122_073
    DungeonBattleCanNotSelectGrid = 122_074
    DungeonBattleNotFoundBattleReward = 122_075
    DungeonBattleCanNotSkip = 122_076
    DungeonBattleSkipGridNotFound = 122_077
    BattlePvpUserBattlePvpDtoNotFound = 131_000
    BattlePvpUserStatusDtoNotFound = 131_001
    BattlePvpUserBattleLegendLeagueDtoNotFound = 131_002
    BattlePvpUserLegendLeagueIconRewardDtoNotFound = 131_003
    BattlePvpInvalidBuyPvpTicket = 132_000
    BattlePvpOverPvpChallengeMaxCount = 132_001
    BattlePvpNotFoundLegendLeagueData = 132_002
    BattlePvpNotOpenLegendLeague = 132_003
    BattlePvpNotFoundLegendLeagueMember = 132_004
    BattlePvpOverLegendLeagueChallengeMaxCount = 132_005
    BattlePvpNotEnoughBuyCount = 132_006
    BattlePvpOverBuyLegendLeagueChallengeCount = 132_007
    BattlePvpInvalidPlayerId = 132_008
    BattlePvpNotEnoughTodayLegendLeagueRequired = 132_009
    BattlePvpLegendLeagueNotOpen = 132_010
    BattlePvpWaitingBattleLeagueBatch = 132_011
    BattlePvpDeletedAccount = 132_012
    BattlePvpNotFoundBattleLog = 132_013
    BattlePvpPlayerRankingNotFound = 132_014
    BattlePvpFailedToUpdateRankingData = 132_015
    BattlePvpFailedToUpdateLegendLeagueRankingData = 132_016
    BattlePvpFailedToGetPlayerInfo = 132_017
    BattlePvpNotBattleTimeLegendLeague = 132_018
    BattlePvpLegendLeagueIconRewardNotOpen = 132_019
    BattlePvpLegendLeagueIconRewardLimitTimeOver = 132_020
    BattlePvpLegendLeagueIconRewardAlreadyBuy = 132_021
    BattleBossUserBountyQuestDtoNotFound = 141_000
    BountyQuestUserStatusDtoNotFound = 141_001
    BountyQuestUserTutorialDtoNotFound = 141_002
    BountyQuestOverDispatchMember = 142_000
    BountyQuestNotHaveCharacter = 142_001
    BountyQuestInvalidBountyQuest = 142_002
    BountyQuestNotEndBountyQuest = 142_003
    BountyQuestNotYetRewardBountyQuest = 142_004
    BountyQuestInvalidMemberCount = 142_005
    BountyQuestInvalidBountyQuestConditionType = 142_006
    BountyQuestNotEnoughElementCondition = 142_007
    BountyQuestNotEnoughRarityCondition = 142_008
    BountyQuestAlreadyUsedOtherSoloQuest = 142_009
    BountyQuestAlreadyUsedOtherTeamQuest = 142_010
    BountyQuestNotDispatchShareCharacter = 142_011
    BountyQuestAlreadyUsedOtherQuest = 142_012
    BountyQuestInvalidRewardBountyQuest = 142_013
    BountyQuestNotEnoughOtherUserCharacter = 142_014
    BountyQuestCanNotAssignDuplicateIdCharacter = 142_015
    BountyQuestInvalidLotteryGroup = 142_016
    BountyQuestNotDefinedElementType = 142_017
    BountyQuestUnavailableMultipleBountyQuest = 142_018
    BountyQuestUnavailableRewardsBountyQuest = 142_019
    BountyQuestInvalidCharacterRarityPoint = 142_020
    BountyQuestNotOpen = 142_021
    BountyQuestContainsDeletedAccountSupportCharacter = 142_022
    CharacterUserCharacterSubDtoNotFound = 161_000
    CharacterUserStatusDtoNotFound = 161_003
    CharacterUserCharacterDtoNotFound = 161_004
    CharacterUserBoxSizeDtoNotFound = 161_005
    CharacterUserCharacterBookDtoNotFound = 161_006
    CharacterUserLevelLinkDtoNotFound = 161_007
    CharacterCannotUseLevelUp = 161_008
    CharacterCannotUseLevelReset = 161_009
    CharacterUserTutorialDtoNotFound = 161_010
    CharacterInvalidEpisodeId = 162_000
    CharacterNotReachRequiredRank = 162_008
    CharacterNotRarityN = 162_017
    CharacterLocked = 162_018
    CharacterLevelInvalid = 162_019
    CharacterNotEnoughBaseCharactersLevel = 162_020
    CharacterAlreadyCharacterBoxMaxSize = 162_021
    CharacterCannotLevelUpWithInLevelLinkCharacters = 162_022
    CharacterResetCharacterLevelAlreadyOne = 162_023
    CharacterNotEnoughInitialRarity = 162_024
    CharacterNotReachCanResetRarity = 162_025
    CharacterCharacterBoxIsOverfull = 162_026
    CharacterHigherSSRCharacterIsOnlyOne = 162_027
    CharacterMaxRarityCharacterIsOnlyOne = 162_028
    CharacterCanNotResetRankMaxLevelInSameRarity = 162_029
    CharacterIdDifferent = 162_030
    CharacterElementDifferent = 162_031
    CharacterRankMaximum = 162_032
    CharacterExistsAutoBattleDeck = 162_033
    CharacterNotEnoughCharacterCollectionCondition = 162_034
    CharacterCannotOpenCharacterCollection = 162_035
    CharacterNotEverExistOverRarityLRPlus5 = 162_036
    CharacterNotRaritySROrSRPlus = 162_037
    CharacterNotExistOverRarityLRPlus5 = 162_038
    CharacterGetCharacterStoryRewardNotOpen = 162_039
    CharacterNotEnoughRankUpRarityCondition = 162_040
    CharacterRankUpNotOpen = 162_041
    CharacterCollectionNotOpen = 162_042
    LocalRaidBattleResultNotFound = 172_000
    LocalRaidNotOpenLocalRaid = 172_001
    LocalRaidNotFoundPlayerDeckData = 172_002
    LocalRaidNotFoundLevelLinkData = 172_003
    LocalRaidDeletedAccount = 172_004
    TowerBattleTowerBattleDtoNotFound = 181_000
    TowerBattleUserStatusDtoNotFound = 181_001
    TowerBattleOverPurchaseLimit = 182_000
    TowerBattleNotClearPreQuest = 182_001
    TowerBattleNotEnoughQuestCondition = 182_002
    TowerBattleNotEnoughChallengeCount = 182_003
    TowerBattleNotFoundTowerType = 182_004
    TowerBattleCharacterElementTypeIsInvalid = 182_005
    TowerBattleLimitOverClearNewFloorPerDay = 182_006
    TowerBattleNotOpen = 182_007
    TowerBattleElementTowerNotOpen = 182_008
    TowerBattleElementTowerNotEnterAlreadyClearedFloor = 182_009
    TowerBattleInvalidTowerType = 182_010
    TowerBattleNotOpenQuest = 182_011
    GuildRaidUserGuildDtoNotFound = 191_000
    GuildRaidGuildDtoNotFound = 191_001
    GuildRaidUserStatusDtoNotFound = 191_002
    GuildRaidExistUserGuildRaidDto = 191_003
    GuildRaidUserBattleAutoDtoNotFound = 191_004
    GuildRaidGuildRaidDtoNotFound = 191_005
    GuildRaidUserGuildRaidDtoNotFound = 191_006
    GuildRaidNotHavePermission = 192_001
    GuildRaidAlreadyOpenGuildRaid = 192_002
    GuildRaidOverChallengeCount = 192_003
    GuildRaidNotExistGuildRaidBoss = 192_004
    GuildRaidNotEnoughGuildFame = 192_005
    GuildRaidNotAvailableQuickStart = 192_006
    GuildRaidNotAllowedChallengeReleasableBoss = 192_007
    GuildRaidRemovedGuildMember = 192_008
    GuildRaidNormalDamageBarInfoNotFound = 192_010
    GuildRaidAlreadyOpened = 192_011
    GuildRaidNotOpenYet = 192_012
    GuildRaidNotFoundGoalDamageWorldReward = 192_013
    GuildRaidNotEnoughGoalDamage = 192_014
    GuildRaidAlreadyRewardWorldItem = 192_015
    GuildRaidNotOpenGuildRaid = 192_016
    GachaAlreadyBeenOpened = 200_110
    GachaAlreadySelectedGachaRelic = 200_120
    GachaOverMaxCountSelectList = 200_130
    GachaOtherCharacterSelectList = 200_131
    GachaOverMaxCountSameElementTypeSelectList = 200_132
    GachaOutOfDate = 200_201
    GachaNotOpen = 200_202
    GachaInvalidButton = 200_203
    GachaHaveMaxCharacter = 200_204
    GachaNotEnoughVipLevelOrMaxQuestIdDestinyGacha = 200_205
    GachaInvalidTutorialGacha = 200_206
    GachaNotEnoughMaxQuestIdEquipmentGacha = 200_207
    GachaInvalidDrawCount = 200_208
    GachaInvalidGachaTicketPeriod = 200_209
    GachaOtherCharacterDestinySelectList = 200_210
    GachaOtherCharacterStarsGuidanceSelectList = 200_211
    GachaNotEnoughVipLevelOrMaxQuestIdStarsGuidanceGacha = 200_212
    GachaUserStatusDtoNotFound = 200_500
    GachaUserBattleAutoDtoNotFound = 200_501
    GachaUserTutorialDtoNotFound = 200_502
    BattleCommonBattleLogNotFound = 220_000
    EquipmentUserEquipmentDtoNotFound = 231_000
    EquipmentUserStatusDtoNotFound = 231_001
    EquipmentUserCharacterDtoNotFound = 231_005
    EquipmentUserLevelLinkDtoNotFound = 231_006
    EquipmentUserTutorialDtoNotFound = 231_007
    EquipmentUserBattleAutoDtoNotFound = 231_008
    EquipmentUserLockCharacterDtoNotFound = 231_009
    EquipmentCanNotEquipSameKindSpheres = 232_000
    EquipmentCanNotEquipOnThisPart = 232_001
    EquipmentMissingSphereSlot = 232_002
    EquipmentSphereSlotAlreadyUnlockedAll = 232_003
    EquipmentDifferentSlotType = 232_004
    EquipmentMissingEquipment = 232_005
    EquipmentInvalidMergeSacredTreasurePattern = 232_006
    EquipmentMissingAbsorbedMaterial = 232_007
    EquipmentCanNotConsumeSacredTreasure = 232_008
    EquipmentCharacterTypeCanNotBeEquipped = 232_009
    EquipmentExceedCanEquipLevel = 232_010
    EquipmentEquippedByOtherCharacters = 232_011
    EquipmentCanNotSelectEquipmentWithSphere = 232_012
    EquipmentReinforcementLvAlreadyUpperLimit = 232_013
    EquipmentCanNotTakeApartNormalEquipment = 232_014
    EquipmentCanNotSelectSetAndExclusiveEquipment = 232_015
    EquipmentCanNotSelectEquippedItem = 232_016
    EquipmentEquipmentCanNotEvolve = 232_018
    EquipmentEquipmentEvolutionInfoNotFound = 232_019
    EquipmentAdditionalParameterCountNotFound = 232_020
    EquipmentSpecifySameEquipmentGuid = 232_021
    EquipmentVipLvNotEnough = 232_022
    EquipmentRequiredItemIsNull = 232_023
    EquipmentNotFoundAdditionalParameterType = 232_024
    EquipmentReinforcementItemNotEnough = 232_025
    EquipmentNotExistEquipment = 232_026
    EquipmentNotEqualEquipmentSlotType = 232_027
    EquipmentGetComposeLackSphereResultFailed = 232_028
    EquipmentInheritanceEquipmentFailed = 232_029
    EquipmentEvolutionSetPossibleLevel = 232_030
    EquipmentEvolutionExclusivePossibleLevel = 232_031
    EquipmentEvolutionNotEnoughEquippingCharacterRarity = 232_032
    EquipmentEquipLREquipmentPossibleCharacterRarity = 232_033
    EquipmentNotOpenSphereSetContent = 232_034
    EquipmentUnlockSphereSlotCountInvalid = 232_035
    EquipmentNotEnoughMaxQuestIdEvolution = 232_036
    EquipmentNotEnoughMaxQuestIdAscend = 232_037
    EquipmentNotEnoughMaxQuestIdStrength = 232_038
    EquipmentNotEnoughMaxQuestIdRefine = 232_039
    EquipmentInvalidLockEquipmentDeckType = 232_040
    EquipmentLockEquipmentCooldownNow = 232_041
    EquipmentLockEquipmentNotOpen = 232_042
    EquipmentLockEquipmentDtoNotFound = 232_043
    EquipmentNotFoundLockCharacter = 232_044
    EquipmentInvalidLeadLockEquipmentDialogType = 232_045
    EquipmentOverMaxRegisterLockCharacterCount = 232_048
    FriendUserFriendDtoNotFound = 241_000
    FriendUserStatusDtoNotFound = 241_001
    FriendUserBattleAutoDtoNotFound = 241_002
    FriendUserFriendMissionDtoNotFound = 241_003
    FriendUserAccountDtoNotFound = 241_004
    FriendUserDataNotFound = 242_000
    FriendCanNotSearchOwnPlayerId = 242_001
    FriendBlockListFull = 242_002
    FriendFriendsFull = 242_003
    FriendNotBlockTargetPlayer = 242_004
    FriendTargetPlayerFriendsFull = 242_005
    FriendFriendApplyingFull = 242_006
    FriendAlreadyFriend = 242_007
    FriendAwaitingApprovalPlayer = 242_008
    FriendTargetPlayerBlocked = 242_009
    FriendTargetPlayerIsFriend = 242_010
    FriendTargetPlayerIdIsMine = 242_011
    FriendInvalidFriendInfoType = 242_012
    FriendTargetPlayerReceivedFriendsFull = 242_013
    FriendAlreadySentFriendPoint = 242_014
    FriendNotSendOrAlreadyReceivedFriendPoint = 242_015
    FriendAlreadyMaxReceived = 242_016
    FriendAlreadyMaxOwned = 242_017
    FriendNotOpenFriendCampaign = 242_018
    FriendNotContainFriendCampaignMission = 242_019
    FriendNotExistFriendCode = 242_020
    FriendNotOpenFriendCode = 242_021
    FriendUnusableAccount = 242_022
    FriendOverTimeFriendCode = 242_023
    FriendAlreadyUseFriendCode = 242_024
    FriendCannotUseSelfFriendCode = 242_025
    FriendCannotUseAnotherTimeServerFriendCode = 242_026
    FriendCannotUseSameUserFriendCode = 242_027
    FriendOverUseLimitFriendCode = 242_028
    GuildJoinRequestDtoNotFound = 251_000
    GuildGuildDtoNotFound = 251_001
    GuildUserGuildDtoNotFound = 251_002
    GuildSystemChatOptionNotFound = 251_003
    StandardGuildNameDtoNotFound = 251_004
    GuildInvalidGuildId = 252_000
    GuildUserHasNoAuthority = 252_001
    GuildAlreadyExistName = 252_002
    GuildAlreadyBelong = 252_003
    GuildCancelJoinRequest = 252_005
    GuildGuildMemberFull = 252_006
    GuildInvalidTargetPlayer = 252_007
    GuildCanNotRemoveLeader = 252_008
    GuildExistMemberOtherThanLeader = 252_009
    GuildNotEnoughBattlePower = 252_010
    GuildApplyCountMax = 252_011
    GuildNotEnoughQuestId = 252_012
    GuildDailyJoinedExceeded = 252_013
    GuildAlreadyApply = 252_014
    GuildUserApplyCountMax = 252_015
    GuildGetGuildIdNotOpen = 252_016
    GuildApplyGuildGuildMemberFull = 252_017
    GuildApplyGuildAlreadyBelong = 252_018
    GuildChangeLeaderNotBelongToGuild = 252_019
    GuildEmptyGuildName = 252_020
    GuildOverMaxLengthGuildName = 252_021
    GuildExistNgWordInGuildName = 252_022
    GuildFailToSaveGuildName = 252_023
    RecruitGuildMemberNotFoundPlayer = 253_000
    RecruitGuildMemberUpperLimitMember = 253_001
    RecruitGuildMemberUpperLimitRecruitCount = 253_002
    RecruitGuildMemberUpperLimitRecruitCountOnPlayerSide = 253_003
    RecruitGuildMemberNotMeetRequired = 253_004
    RecruitGuildMemberSameGuildPlayer = 253_005
    RecruitGuildMemberNotOpenGuild = 253_006
    RecruitGuildMemberSearchNotFoundPlayer = 253_010
    ShopCurrencyMissionDtoNotFound = 261_000
    ShopGuerrillaPackDtoNotFound = 261_001
    ShopFirstChargeBonusDtoNotFound = 261_002
    ShopUserShopChargeBonusMissionDtoNotFound = 261_003
    ShopUserAccountDtoNotFound = 261_004
    ShopUserCurrencyMissionDtoNotFound = 261_005
    ShopMonthlyBoostDtoNotFound = 261_006
    ShopAchievementPackDtoNotFound = 261_007
    ShopBuyProductInvalidRequest = 262_000
    ShopBuyProductNotEnoughVip = 262_001
    ShopBuyProductNotOpen = 262_002
    ShopBuyProductBuyCountLimit = 262_003
    ShopBuyProductAlready = 262_004
    ShopBuyProductNotEnoughChapterId = 262_005
    ShopInvalidReceipt = 262_006
    ShopAlreadyUsedReceipt = 262_007
    ShopAlreadyRecoveredReceipt = 262_008
    ShopReceiveRewardInvalidRequest = 262_009
    ShopReceiveAchievementPackRewardNotEnoughChapterId = 262_010
    ShopReceiveAchievementPackRewardAlreadyReceive = 262_011
    ShopMonthlyBoostExpired = 262_012
    ShopMonthlyBoostDailyRewardAlreadyGet = 262_013
    ShopFirstChargeBonusNotReceived = 262_014
    ShopFirstChargeBonusInvalidDay = 262_015
    ShopChargeBonusMissionTypeInvalid = 262_016
    ShopChargeBonusMissionInfoNotFound = 262_017
    ShopLimitGetChargeBonus = 262_018
    ShopEndChargeBonus = 262_019
    ShopFailVerifyIOSReceipt = 262_020
    ShopGrowthPackIsNotFree = 262_021
    ShopGrowthPackNotEnoughMaxRarity = 262_022
    ShopNotOpen = 262_023
    ShopCurrencyNotEnough = 262_024
    ShopCurrencyMissionRewardAlreadyReceived = 262_025
    ShopInvalidBirthYear = 262_026
    ShopInvalidBirthMonth = 262_027
    ShopConfirmAgeAlreadyRegister = 262_028
    ShopRewardIsNotFree = 262_029
    ShopGuerrillaPackInfoNotFound = 262_030
    ShopCurrencyMissionItemInfoNotFound = 262_031
    ShopAchievementPackItemInfoNotFound = 262_032
    ShopInvalidAccount = 262_033
    ShopBuyProductNotEnoughCondition = 262_034
    ShopInvalidDisplayPeriodType = 262_035
    ShopIosVerifyReceiptProblem = 262_036
    ShopNotFoundReceipt = 262_037
    ShopNotFoundSession = 262_038
    ShopNotPaid = 262_039
    ShopNotFoundCouponData = 262_040
    ShopAlreadyUsedCoupon = 262_041
    ChatUserStatusDtoNotFound = 271_000
    ChatUserAccountDtoNotFound = 271_001
    ChatUserGuildDtoNotFound = 271_002
    ChatBlockedByTargetPlayer = 272_000
    ChatInvalidRequestTimeStamp = 272_001
    ChatPlayerCanNotSendChatToHimself = 272_002
    ChatSendMessageRestriction = 272_003
    ChatSendMessageBanChat = 272_004
    ChatNotBelongToGuild = 272_005
    ChatNotFoundChatInfo = 272_006
    ChatNotSendPlayer = 272_007
    ChatNotDefinedReactionType = 272_008
    ChatCanNotReact = 272_009
    ChatAlreadyRegistered = 272_010
    ChatNotLeaderOrSubLeader = 272_011
    ChatOverMaxRegisterAnnounceChatCount = 272_012
    ChatGuildChatAnnounceInterval = 272_013
    PresentDeleteNotReceivedPresent = 282_001
    PresentReceiveDeletedPresent = 282_002
    PresentItemListDataIsNull = 282_003
    PresentReceiveExpiredPresent = 282_004
    PresentReceiveOverLimitCountPresent = 282_005
    PresentNotOpen = 282_006
    PresentReceiveAlreadyReceivedPresent = 282_007
    LocalGvgUserGuildDtoNotFound = 291_000
    LocalGvgUserBattleAutoDtoNotFound = 291_001
    LocalGvgUserNotJoinGuild = 292_000
    LocalGvgReceiveRewardInvalidRequest = 292_001
    LocalGvgNotMatchingYet = 292_002
    LocalGvgNotFoundReceivableReward = 292_003
    GlobalGvgUserGuildDtoNotFound = 301_000
    GlobalGvgGuildDtoNotFound = 301_001
    GlobalGvgUserNotJoinGuild = 302_000
    GlobalGvgReceiveRewardInvalidRequest = 302_001
    GlobalGvgNotFoundReceivableReward = 302_003
    LevelLinkUserLevelLinkDtoNotFound = 311_000
    LevelLinkUserCharacterDtoNotFound = 311_001
    LevelLinkUserLevelLinkMemberDtoNotFound = 311_002
    LevelLinkUserStatusDtoNotFound = 311_003
    LevelLinkAlreadySetCharacter = 312_000
    LevelLinkOverMember = 312_001
    LevelLinkAlreadyMaxPartyLevel = 312_002
    LevelLinkNotEnoughMaxLevelBaseMember = 312_003
    LevelLinkOverMemberCount = 312_004
    LevelLinkNotPartyLevelModeOpen = 312_008
    LevelLinkOverOpenSlotCountWithCurrency = 312_009
    LevelLinkAlreadyPartyMode = 312_010
    LevelLinkNotOpen = 312_011
    VipBuyVipGiftNotEnoughVipLv = 322_000
    VipBuyVipGiftAlreadyBuy = 322_001
    VipBuyVipGiftInvalidRequestVipGiftId = 322_002
    VipGetDailyGiftAlreadyGet = 322_003
    LoginBonusUserStatusDtoNotFound = 331_000
    LoginBonusUserMonthlyLoginBonusDtoNotFound = 331_001
    LoginBonusUserLimitedLoginBonusDtoNotFound = 331_002
    LoginBonusAlreadyReceivedDailyReward = 332_000
    LoginBonusReceiveFutureReward = 332_001
    LoginBonusReceivablePastRewardCountNotEnough = 332_002
    LoginBonusDailyRewardInfoIsNull = 332_003
    LoginBonusAlreadyReceivedLoginCountReward = 332_004
    LoginBonusLoginCountNotEnough = 332_005
    LoginBonusLoginCountRewardInfoIsNull = 332_006
    LoginBonusLimitedLoginBonusNotOpen = 332_101
    LoginBonusLimitedLoginBonusNotHeld = 332_102
    LoginBonusNotExistSpecialReward = 332_103
    LoginBonusAlreadyReceivedSpecialReward = 332_104
    NoticeUserAccountDtoNotFound = 341_001
    NoticeNotDefinedNoticeAccessType = 342_001
    NoticeNotDefinedNoticeCategoryType = 342_002
    NoticeCanNotGetNoticeAccessCategoryInTitle = 342_003
    NoticeNotDefinedLanguageType = 342_004
    MissionUserMissionDtoNotFound = 351_000
    MissionUserMissionActivityDtoNotFound = 351_001
    MissionUserBattleAutoDtoNotFound = 351_002
    MissionUserTutorialDtoNotFound = 351_003
    MissionUserMissionOccurrenceHistoryDtoNotFound = 351_004
    MissionNotOpenMission = 352_000
    MissionNotReceivedMission = 352_001
    MissionNotEnoughRequireCount = 352_002
    MissionNotExistRewardType = 352_003
    MissionMBNotAchievementType = 352_004
    MissionNotEnoughCurrency = 352_005
    MissionNotExistMissionGroupType = 352_006
    MissionActivityMBNotFoundOrAlreadyAchieved = 352_007
    MissionActivityRewardNotReceived = 352_008
    MissionNotExistSheetNo = 352_021
    MissionNotExistBingoType = 352_022
    MissionAlreadyReceivedBingoReward = 352_023
    MissionNotCompletedBingo = 352_024
    MissionNotFoundBingoReward = 352_025
    MissionNotClearedPrevSheetMission = 352_026
    MissionJoinGuildAfterEndEvent = 352_030
    TradeShopUserBattleAutoDtoNotFound = 361_000
    TradeShopUserStatusDtoNotFound = 361_001
    TradeShopUserTradeShopDtoNotFound = 361_002
    TradeShopInvalidTradeShopItem = 362_000
    TradeShopLimitTimeOver = 362_001
    TradeShopOverLimitBuyCount = 362_002
    TradeShopInvalidResetType = 362_003
    TradeShopIsHideTab = 362_004
    TradeShopNotOpen = 362_005
    RankingWorldReceivableRankingRewardDtoNotFound = 371_000
    RankingNotOpenRankingContent = 372_000
    RankingCanNotReceiveReward = 372_001
    RankingAlreadyReceivedRankingReward = 372_002
    RankingNotOpenAchieveRankingReward = 372_003
    PanelNotStarted = 382_000
    PanelUnlockFreePanel = 382_001
    PanelAlreadyUnlocked = 382_002
    MusicUserMusicDtoNotFound = 391_000
    MusicUserPlaylistDtoNotFound = 391_001
    MusicNotOpenMusicContent = 392_000
    MusicOverMaxPlaylistCount = 392_001
    MusicEmptyPlaylistName = 392_002
    MusicOverMaxLengthPlaylistName = 392_003
    MusicExistNgWordInPlaylistName = 392_004
    MusicAlreadyBuyMusic = 392_005
    MusicInvalidMusicId = 392_006
    MusicOverMaxPlaylistMusicCount = 392_007
    TutorialAccountDtoNotFound = 401_000
    TutorialUserStatusDtoNotFound = 401_001
    TutorialUserBattleAutoDtoNotFound = 401_002
    TutorialUserDeckDtoNotFound = 401_003
    TutorialOpenContentInvalidRequest = 402_000
    TutorialOpenContentAlready = 402_001
    TutorialClearTutorialInvalidTutorialId = 402_002
    TutorialClearTutorialAlreadyCleared = 402_003
    TutorialSkipTutorialIdIsNullOrEmpty = 402_004
    TutorialNotEnoughSkipCondition = 402_005
    GuildTowerUserGuildTowerDtoNotFound = 410_000
    GuildTowerUserCharacterDtoNotFound = 410_001
    GuildTowerUserGuildDtoNotFound = 410_002
    GuildTowerUserStatusDtoNotFound = 410_003
    GuildTowerGuildTowerDtoNotFound = 410_004
    GuildTowerUserGuildTowerPreviousEntryInfoDtoNotFound = 410_005
    GuildTowerGuildDtoNotFound = 410_006
    GuildTowerNotOpenEvent = 412_000
    GuildTowerNotBelongToGuild = 412_001
    GuildTowerNotEnoughChallengeCount = 412_002
    GuildTowerNotFoundCharacter = 412_003
    GuildTowerInvalidGuildTowerEntryType = 412_004
    GuildTowerInvalidCharacter = 412_005
    GuildTowerEmptyEntryCharacter = 412_006
    GuildTowerNotChangeDay = 412_007
    GuildTowerInvalidChallengeFloor = 412_008
    GuildTowerInvalidDifficulty = 412_009
    GuildTowerInvalidJobFlags = 412_100
    GuildTowerNotFoundNextJobLevelData = 412_101
    GuildTowerFailedToReinforceJob = 412_102
    GuildTowerLimitReinforcementJobLevelCap = 412_103
    GuildTowerReachedMaxReinforcementJobLevel = 412_104
    GuildTowerInvalidEntryCharacter = 412_105
    GuildTowerNotYetEndBattle = 412_106
    GuildTowerNotEnoughGuildChallengeCount = 412_107
    GuildTowerCannotChallengeOnJoinGuildDate = 412_108
    GuildTowerNotFoundReinforceJobPlayer = 412_109
    GuildTowerAlreadyClearFloor = 412_110
    GuildTowerCanNotReceiveNotClearedFloorReward = 412_200
    GuildTowerAlreadyReceivedFloorReward = 412_201
    GuildTowerJoinedGuildAfterEndEvent = 412_202
    IndividualNotificationCacheDtoNotFound = 421_000
    IndividualNotificationDtoNotFound = 421_001
    StarsGuidanceTradeShopDtoNotFound = 431_000
    StarsGuidanceTradeShopNotOpen = 432_000
    StarsGuidanceTradeShopUnavailable = 432_001
    StarsGuidanceTradeShopConsumeItemInvalid = 432_002
    StarsGuidanceTradeShopOverLimitTradeCount = 432_003
    ItemOpenTreasureChestIdNotFound = 602_004
    ItemOpenTreasureChestItemNotFound = 602_005
    ItemOpenTreasureChestCountTooLittle = 602_006
    ItemOpenTreasureChestCanNotSelect = 602_007
    ItemOpenTreasureChestNotSelected = 602_008
    ItemNotEnoughChangeItemCount = 602_009
    ItemNotMatchLotteryType = 602_010
    ItemInvalidEndTime = 602_011
    ItemGetLotteryItemListGachaLotteryItemListInfoListIsEmpty = 602_014
    ItemOpenTreasureChestTreasureChestItemListTypeNotDefined = 602_015
    ItemOpenTreasureChestTreasureChestLotteryTypeNotDefined = 602_016
    ItemOpenTreasureChestIndexOutOfRange = 602_017
    ItemOpenTreasureChestStaticItemIsNull = 602_018
    ItemOpenTreasureChestCeilingTargetItemNotFound = 602_019
    ItemSpecialIconItemNotFound = 602_020
    ItemGoldExchangeNotOpen = 602_021
    ItemUsingInvalidItems = 602_022
    MagicOnionLocalRaidDisbandRoomFailed = 900_102
    MagicOnionLocalRaidJoinRoomAlreadyJoinedOtherRoom = 900_103
    MagicOnionLocalRaidJoinRoomNoRemainingChallenges = 900_104
    MagicOnionLocalRaidJoinRoomNotExistRoom = 900_105
    MagicOnionLocalRaidJoinRoomMembersAreFull = 900_106
    MagicOnionLocalRaidJoinRoomNotEnoughBattlePower = 900_107
    MagicOnionLocalRaidJoinRoomWrongPassword = 900_108
    MagicOnionLocalRaidJoinRoomRedisError = 900_109
    MagicOnionLocalRaidLeaveRoomFailed = 900_110
    MagicOnionLocalRaidLeaveRoomNotExistRoom = 900_111
    MagicOnionLocalRaidLeaveRoomIsLeader = 900_112
    MagicOnionLocalRaidLeaveRoomNotFoundData = 900_113
    MagicOnionLocalRaidLeaveRoomRedisError = 900_114
    MagicOnionLocalRaidOpenRoomAlreadyJoinedOtherRoom = 900_115
    MagicOnionLocalRaidOpenRoomQuestNotHeld = 900_116
    MagicOnionLocalRaidOpenRoomNoRemainingChallenges = 900_117
    MagicOnionLocalRaidStartBattleFailed = 900_118
    MagicOnionLocalRaidStartBattleNotFoundData = 900_119
    MagicOnionLocalRaidStartBattleExpiredLocalRaidQuest = 900_120
    MagicOnionLocalRaidRefuse = 900_121
    MagicOnionLocalRaidRefuseNotFoundData = 900_122
    MagicOnionLocalRaidRefuseRedisError = 900_123
    MagicOnionLocalRaidRefuseNotExistRoom = 900_124
    MagicOnionLocalRaidInviteNotFriend = 900_125
    MagicOnionLocalRaidInviteNotFoundData = 900_126
    MagicOnionLocalRaidJoinFriendRoomNotFoundData = 900_127
    MagicOnionLocalRaidJoinFriendRoomAlreadyJoinedOtherRoom = 900_128
    MagicOnionLocalRaidJoinFriendRoomNoRemainingChallenges = 900_129
    MagicOnionLocalRaidJoinFriendRoomMembersAreFull = 900_130
    MagicOnionLocalRaidJoinFriendRoomRedisError = 900_131
    MagicOnionLocalRaidJoinFriendRoomNotExistRoom = 900_132
    MagicOnionLocalRaidJoinRandomRoomAlreadyJoinedOtherRoom = 900_133
    MagicOnionLocalRaidJoinRandomRoomNoRemainingChallenges = 900_134
    MagicOnionLocalRaidJoinRandomRoomNotExistRoom = 900_135
    MagicOnionLocalRaidJoinRandomRoomRedisError = 900_136
    MagicOnionLocalRaidExpiredLocalRaidQuest = 900_137
    MagicOnionLocalRaidInviteNoRemainingChallenges = 900_138
    MagicOnionLocalRaidNotOpenQuest = 900_139
    MagicOnionLocalRaidReadyIsLeader = 900_140
    MagicOnionLocalRaidAllNotReady = 900_141
    MagicOnionLocalRaidReadyFailed = 900_142
    MagicOnionLocalRaidReadyNotExistRoom = 900_143
    MagicOnionLocalRaidReadyNotFoundData = 900_144
    MagicOnionLocalRaidReadyRedisError = 900_145
    MagicOnionLocalRaidUpdateRoomConditionFailed = 900_146
    MagicOnionLocalRaidUpdateRoomConditionIsNotLeader = 900_147
    MagicOnionLocalRaidUpdateRoomConditionRedisError = 900_148
    MagicOnionLocalRaidUpdateBattlePowerFailed = 900_150
    MagicOnionLocalRaidUpdateBattlePowerNotExistRoom = 900_151
    MagicOnionLocalRaidUpdateBattlePowerNotFoundData = 900_152
    MagicOnionLocalRaidUpdateBattlePowerRedisError = 900_153
    MagicOnionLocalRaidStartBattleNotEnoughBattlePower = 900_154
    MagicOnionLocalRaidJoinRoomNotSameWorld = 900_155
    MagicOnionLocalRaidNotEnoughBattleData = 900_156
    MagicOnionGlobalGvgAddCastlePartyInvalidRequest = 900_302
    MagicOnionGlobalGvgAddCastlePartyInvalidData = 900_303
    MagicOnionGlobalGvgAddCastlePartyNotOwnCastle = 900_304
    MagicOnionGlobalGvgAddCastlePartyNotEnoughActionPoint = 900_305
    MagicOnionGlobalGvgAddCastlePartySameCharacter = 900_306
    MagicOnionGlobalGvgOrderCastlePartyFirst = 900_307
    MagicOnionGlobalGvgOrderCastlePartyInvalidData = 900_308
    MagicOnionGlobalGvgCastleDeclarationInvalidData = 900_309
    MagicOnionGlobalGvgCastleDeclarationDistant = 900_310
    MagicOnionGlobalGvgCastleDeclarationByOtherGuild = 900_311
    MagicOnionGlobalGvgCastleDeclarationMaxCount = 900_312
    MagicOnionGlobalGvgCastleDeclarationCounterInvalidData = 900_313
    MagicOnionGlobalGvgCheckCanJoinBattleAndNoticeNotJoinGuild = 900_314
    MagicOnionGlobalGvgCheckCanJoinBattleAndNoticeJoinGuildToDay = 900_315
    MagicOnionGlobalGvgCheckCanJoinBattleAndNoticeNotLeaderAndNotSubLeader = 900_316
    MagicOnionGlobalGvgNotOpen = 900_317
    MagicOnionGlobalGvgAddCastlePartyNotFoundCharacterCache = 900_318
    MagicOnionAuthenticationFail = 1_000_000
    MagicOnionNotFoundPlayerInfo = 1_000_001
    MagicOnionFailedToGetUserId = 1_000_002
    MagicOnionNotJoinGuild = 1_001_000
    MagicOnionChatLimitOver = 1_001_001
    MagicOnionRepeatTimeOver = 1_001_002
    MagicOnionFailSendMessage = 1_001_003
    MagicOnionBanChat = 1_001_004
    MagicOnionInvalidCastleId = 1_002_000
    MagicOnionCannotSetCastle = 1_002_001
    MagicOnionNotEnoughActionPoint = 1_002_002
    MagicOnionAlreadySetCharacter = 1_002_003
    MagicOnionCannotControllFirstParty = 1_002_004
    MagicOnionInvalidData = 1_002_005
    MagicOnionNotFoundCache = 1_002_006
    MagicOnionNotNeighborCastle = 1_002_007
    MagicOnionAlreadySelectedOtherGuild = 1_002_008
    MagicOnionCannotAttackOtherGuild = 1_002_009
    MagicOnionCannotPlayLocalGvgInFirstDay = 1_002_010
    MagicOnionNotLeader = 1_002_011
    MagicOnionNotJoinedGuildBattle = 1_002_012
    MagicOnionCanNotDeclaration = 1_002_013
    MagicOnionNotFoundCharacterCache = 1_002_014
    MagicOnionBeforeDeclarationTime = 1_002_015
    MagicOnionNotOpenGuildBattle = 1_002_016
    MagicOnionLocalGvgAddPartyNotFoundCharacterCache = 1_002_017
    PushNotificationNotSupportedDeviceType = 4_000_000
    InvalidDeviceToken = 4_000_001
    InvalidRemoteNotificationIgnoreTypes = 4_000_002
    NotSupportedRemoteNotificationIgnoreType = 4_000_003
    PushNotificationNotDefinedLanguageType = 4_000_004
    DmmOneTimeTokenExpired = 5_000_100
    DmmFailedToGetParamFromHeader = 5_000_101
    DmmApiRequestFailedAuthCheckLogin = 5_000_102
    DmmApiRequestFailed = 5_000_103
    DmmApiRequestResultNotZero = 5_000_104
    DmmApiRequestFailedIssueOneTimeToken = 5_000_105
    DmmApiRequestFailedIdLinkage = 5_000_106
    DmmMultiViewerIdLinkageRequested = 5_000_107
    DmmUnderMaintenance = 5_000_108
    DmmDataLinkageInfoNotFound = 5_000_109
    DmmDataLinkageNotActive = 5_000_110
    DmmFailedToGetViewerId = 5_000_111
    DmmApiRequestFailedAuthCheckPoint = 5_000_200
    DmmApiRequestNotFoundDmmSubscription = 5_000_201
    DmmApiRequestNotDmmDeviceType = 5_000_202
    StripeNotFoundGivePlayerId = 5_010_000
    StripeNotFoundMbId = 5_010_001
    StripeNotFoundProductId = 5_010_002
    StripeNotFoundShopProductType = 5_010_003
    StripeNotFoundDeviceType = 5_010_004
    StripeNotFoundInvoiceId = 5_010_005
    StripeNotPaidPaymentStatus = 5_010_006
    StripeNotFoundCurrencyDataBase = 5_010_007
    StripeNotFoundPaymentInfo = 5_010_008
    StripeNotFoundCurrencyCode = 5_010_009
    StripeInvalidPrice = 5_010_010
    StripeNotFoundCustomerInfo = 5_010_011
    StripeNotEnoughPoint = 5_010_012
    StripeNotFoundSession = 5_010_013


# endregion


# region Shop


class ShopGuerrillaPackRankType(IntEnum):
    Rank1 = 1
    Rank2 = 2
    Rank3 = 3
    Rank4 = 4
    Rank5 = 5
    Rank6 = 6
    Rank7 = 7


# endregion


# region Items


class ItemType(IntEnum):
    NONE = 0
    CurrencyFree = 1
    CurrencyPaid = 2
    Gold = 3
    Equipment = 4
    EquipmentFragment = 5
    Character = 6
    CharacterFragment = 7
    DungeonBattleRelic = 8
    EquipmentSetMaterial = 9
    QuestQuickTicket = 10
    CharacterTrainingMaterial = 11
    EquipmentReinforcementItem = 12
    ExchangePlaceItem = 13
    Rune = 14  # Renamed from `Sphere`
    MatchlessSacredTreasureExpItem = 15
    GachaTicket = 16
    TreasureChest = 17
    TreasureChestKey = 18
    BossChallengeTicket = 19
    TowerBattleTicket = 20
    DungeonRecoveryItem = 21
    PlayerExp = 22
    FriendPoint = 23
    EquipmentRarityCrystal = 24
    LevelLinkExp = 25
    GuildFame = 26
    GuildExp = 27
    ActivityMedal = 28
    VipExp = 29
    PanelGetJudgmentItem = 30
    UnlockPanelGridItem = 31
    PanelUnlockItem = 32
    MusicTicket = 33
    SpecialIcon = 34
    IconFragment = 35
    GuildTowerJobReinforcementMaterial = 36
    UNKNOWN_37 = 37  # TODO: Fix these
    UNKNOWN_38 = 38
    UNKNOWN_39 = 39
    EventExchangePlaceItem = 50
    StripeCoupon = 1_001


ITEM_PAGE_TYPE_MAP = {
    '_unsorted': {
        ItemType.Character,
        ItemType.DungeonBattleRelic,
        ItemType.EquipmentSetMaterial,
        ItemType.EquipmentRarityCrystal,
        ItemType.LevelLinkExp,
        ItemType.ActivityMedal,
        ItemType.PanelGetJudgmentItem,
        ItemType.UnlockPanelGridItem,
        ItemType.PanelUnlockItem,
        ItemType.MusicTicket,
        ItemType.IconFragment,
        ItemType.EventExchangePlaceItem,
        ItemType.StripeCoupon,
    },
    'Gear': {ItemType.Equipment},
    'Consumables': {
        ItemType.CharacterFragment,
        ItemType.QuestQuickTicket,
        ItemType.TreasureChest,
        ItemType.TreasureChestKey,
    },
    'Materials': {
        ItemType.CharacterTrainingMaterial,  # EXP/Kindling orbs
        ItemType.EquipmentReinforcementItem,
        ItemType.ExchangePlaceItem,
        ItemType.FriendPoint,
        ItemType.MatchlessSacredTreasureExpItem,
        ItemType.GachaTicket,
        ItemType.TowerBattleTicket,
        ItemType.BossChallengeTicket,
        ItemType.DungeonRecoveryItem,
    },
    'Runes': {ItemType.Rune},
    'Parts': {ItemType.EquipmentFragment},
    'Other': {
        ItemType.CurrencyFree,  # Diamonds
        ItemType.CurrencyPaid,
        ItemType.Gold,
        ItemType.PlayerExp,
        ItemType.GuildFame,
        ItemType.GuildExp,
        ItemType.VipExp,
        ItemType.SpecialIcon,
        ItemType.GuildTowerJobReinforcementMaterial,
    },
}


class ItemRarityFlags(IntEnum):
    NONE = 0
    D = 1
    C = 2
    B = 4
    A = 8
    S = 16
    R = 32
    SR = 64
    SSR = 128
    UR = 256
    LR = 512


# endregion


# region Equipment


class EquipmentRarityFlags(IntFlag, boundary=CONFORM):
    NONE = 0
    D = 1
    C = 2
    B = 4
    A = 8
    S = 16
    R = 32
    SR = 64
    SSR = 128
    UR = 256
    LR = 512

    @classmethod
    def range(cls, min_rarity: EquipmentRarityFlags, max_rarity: EquipmentRarityFlags) -> EquipmentRarityFlags:
        rarity = last = min_rarity
        while (next_rarity := last * 2) <= max_rarity:
            rarity |= next_rarity
            last = next_rarity

        return rarity


class SmeltEquipmentRarity(IntEnum):
    D = 1
    C = 2
    B = 4
    A = 8
    S = 16
    S_PLUS = 17

    def as_flag(self) -> EquipmentRarityFlags:
        if self == self.S_PLUS:
            return EquipmentRarityFlags.S
        return EquipmentRarityFlags(self.value)


class EquipmentSlotType(IntEnum):
    NONE = 0
    Weapon = 1
    Accessory = 2  # Renamed from `Sub`
    Gauntlet = 3
    Helmet = 4
    Armor = 5
    Shoes = 6


class EquipmentType(IntEnum):  # This is a custom enum, not one from the game
    NONE = 0
    Sword = 1
    Gun = 2
    Book = 3
    Accessory = 4
    Gauntlet = 5
    Helmet = 6
    Armor = 7
    Shoes = 8

    @classmethod
    def for_slot_and_job(cls, slot_type: EquipmentSlotType, job: Job) -> EquipmentType:
        if slot_type != EquipmentSlotType.Weapon:
            return cls(slot_type.value + 2)
        return cls(int(_log(job.value, 2)) + 1)  # noqa


class EquipmentCategory(IntEnum):
    Normal = 1
    Set = 2
    Exclusive = 3


class BaseParameterType(IntEnum):
    STR = 1  # Renamed from `Muscle`
    DEX = 2  # Renamed from `Energy`
    MAG = 3  # Renamed from `Intelligence`
    STA = 4  # Renamed from `Health`


class ChangeParameterType(IntEnum):
    Addition = 1
    AdditionPercent = 2
    CharacterLevelConstantMultiplicationAddition = 3


class SacredTreasureType(IntEnum):
    NONE = 0
    Matchless = 1
    Legend = 2
    DualStatus = 3


class SphereType(IntEnum):
    EquipmentIcon = 0
    Small = 1
    Medium = 2
    Large = 3


# endregion


# region Character


class Element(IntEnum):
    NONE = 0
    AZURE = 1
    CRIMSON = 2
    EMERALD = 3
    AMBER = 4
    RADIANCE = 5
    CHAOS = 6


class Job(IntFlag, boundary=CONFORM):
    NONE = 0
    WARRIOR = 1
    SNIPER = 2
    SORCERER = 4


class CharacterRarity(IntFlag, boundary=CONFORM):
    NONE = 0
    N = 1
    R = 2
    RPlus = 4
    SR = 8
    SRPlus = 16
    SSR = 32
    SSRPlus = 64
    UR = 128
    URPlus = 256
    LR = 512
    LRPlus = 1_024
    LRPlus2 = 2_048
    LRPlus3 = 4_096
    LRPlus4 = 8_192
    LRPlus5 = 16_384
    LRPlus6 = 32_768
    LRPlus7 = 65_536
    LRPlus8 = 131_072
    LRPlus9 = 262_144
    LRPlus10 = 524_288


class CharacterType(IntEnum):
    Normal = 0
    Qlipha = 1
    ColorChange = 2


class DeckUseContentType(IntEnum):
    # When saving a party to be used for a given purpose (quest, tower, etc), this represents the party type
    NONE = 0
    Auto = 1
    Boss = 2
    Infinite = 3
    DungeonBattle = 4
    LocalRaid = 5
    BattleLeagueOffense = 6
    BattleLeagueDefense = 7
    LegendLeagueOffense = 8
    LegendLeagueDefense = 9
    GuildHunt = 10
    BlueTower = 11
    RedTower = 12
    GreenTower = 13
    YellowTower = 14
    GuildBattle = 1_000
    GrandBattle = 2_000


# endregion


# region Friends


class FriendStatusType(IntEnum):
    NONE = 0
    Stranger = 1
    Friend = 2
    Applying = 3
    Receive = 4


class FriendInfoType(IntEnum):
    NONE = 0
    Friend = 1
    ApprovalPending = 2
    Applying = 3
    Block = 4
    Recommend = 5


# endregion


# region PvP


class LegendLeagueClassType(IntEnum):
    NONE = 0
    Chevalier = 1
    Paladin = 2
    Duke = 3
    Royal = 4
    Legend = 5
    WorldRuler = 6


class LockEquipmentDeckType(IntEnum):
    NONE = 0
    League = 1
    GuildTowerLatestBattle = 2
    GuildTowerLatestRegistration = 3


class LeadLockEquipmentDialogType(IntEnum):
    NONE = 0
    NewCharacter = 1
    PassedDays = 2


# endregion


# region Battle


class BattleType(IntEnum):
    NONE = 0
    Auto = 1
    Boss = 2
    GuildBattle = 3
    GrandBattle = 4
    BattleLeague = 5
    LegendLeague = 6
    LocalRaid = 7
    TowerBattle = 8
    DungeonBattle = 9
    GuildRaid = 11
    GuildTower = 12


class UnitType(IntEnum):
    Character = 0
    AutoBattleEnemy = 1
    DungeonBattleEnemy = 2
    GuildRaidBoss = 3
    BossBattleEnemy = 4
    TowerBattleEnemy = 5
    LocalRaidEnemy = 6
    GuildTowerEnemy = 7


class BattleFieldCharacterGroupType(IntEnum):
    Attacker = 0
    Receiver = 1


class HitType(IntEnum):
    Ignore = 0
    Hit = 1
    Miss = 2
    Critical = 3
    Shield1 = 4
    Shield1Critical = 5
    Shield2 = 6
    Shield2Critical = 7
    ShieldBreak = 8
    ShieldBreakCritical = 9


class SkillCategory(IntEnum):
    Heal = 1
    Buff = 2
    DeBuff = 3
    SpecialBuff = 4
    SpecialDeBuff = 5
    PhysicalAttack = 10
    MagicAttack = 11
    PhysicalNoDefense = 12
    MagicNoDefense = 13
    PhysicalDirectDamage = 14
    MagicDirectDamage = 15
    PhysicalFixDamage = 16
    MagicFixDamage = 17
    SelfInjuryDamage = 18
    Resurrection = 50
    StatusDrain = 100
    SkillMark = 200
    RemoveBuffEffect = 500
    RemoveDebuffEffect = 501
    RemoveOtherEffect = 502
    BuffTransfer = 600
    DeBuffTransfer = 601
    BurstBuffEffect = 1_000
    BurstDeBuffEffect = 1_001


class EffectGroupType(IntEnum):
    NONE = 0
    Stun = 1


class RemoveEffectType(IntEnum):
    TurnCountEnd = 0
    TurnCountEndAndReceiveDamage = 1


class SubSkillResultType(IntEnum):
    NONE = 0
    Damage = 1
    Effect = 2
    Passive = 3
    Temp = 4


class SubSetType(IntEnum):
    Live2DBefore = 0
    DefaultLive2D = 1
    DefaultLive2DAfter = 2
    UnderFiveLive2DInSubSet = 3
    UnderFiveLive2DAfterInSubSet = 4
    AboveFourLive2DInSubSet = 5
    AboveFourLive2DAfterInSubSet = 6
    UnderFiveLive2DOutOfSubSet = 7
    UnderFiveLive2DAfterOutOfSubSet = 8
    AboveFourLive2DOutOfSubSet = 9
    AboveFourLive2DAfterOutOfSubSet = 10


class SkillDisplayType(IntEnum):
    NONE = 0
    Heal = 1
    PhysicalAttack = 2
    MagicAttack = 3
    PhysicalDirectDamage = 4
    MagicDirectDamage = 5
    HpDrain = 6
    Buff = 7
    DeBuff = 8
    PhysicalCounterAttack = 9
    MagicCounterAttack = 10
    PhysicalResonanceAttack = 11
    MagicResonanceAttack = 12
    RemoveEffect = 13
    BurstEffect = 14
    SelfInjuryDamage = 15
    Resurrection = 20


class PassiveTrigger(IntEnum):
    NONE = 0
    TurnStart = 1
    TurnEnd = 2
    BeforeCalculation = 3
    InstantDeathDamage = 5
    SelfDead = 6
    AllyDead = 7
    ReceiveDamage = 8
    GiveDamage = 9
    AllyReceiveDamage = 10
    ReceiveDebuff = 11
    GiveDeBuff = 12
    AllyReceiveDeBuff = 13
    GiveHeal = 14
    AllyReceiveHeal = 15
    GiveBuff = 16
    AllyGiveBuff = 17
    EnemyRecovery = 18
    SelfRecovery = 19
    OtherEnemyDead = 20
    EnemyDead = 21
    AllyGiveDamage = 22
    EnemyReceiveHeal = 23
    ReceiveBuff = 24
    EnemyGiveBuff = 25
    BattleStart = 26
    BattleEnd = 27
    TurnStartBeforeSpeedCheck = 28
    TargetAttack = 29
    ReceiveHeal = 30
    ReceiveResonanceDamage = 31
    ActionStart = 32
    ActionEnd = 33
    SelfInjury = 34
    AllySelfInjury = 35
    CheckReceiveDamageSelf = 41
    CheckReceiveDamage = 42
    NextCheckReceiveDamageSelf = 43
    NextCheckReceiveDamage = 44
    RecoveryFromInstantDeathDamage = 52
    SpecialDamageDead = 62


class EffectType(IntEnum):
    NONE = 0
    SpeedUp = 1_001
    MaxHpUp = 1_002
    AttackPowerUp = 1_003
    DefenseUp = 1_004
    PhysicalDamageRelaxUp = 1_005
    MagicDamageRelaxUp = 1_006
    DefensePenetrationUp = 1_007
    DamageEnhanceUp = 1_008
    HitUp = 1_009
    AvoidanceUp = 1_010
    CriticalUp = 1_011
    CriticalResistUp = 1_012
    HpDrainUp = 1_013
    DamageReflectUp = 1_014
    CriticalDamageEnhanceUp = 1_015
    PhysicalCriticalDamageRelaxUp = 1_016
    MagicCriticalDamageRelaxUp = 1_017
    DebuffHitUp = 1_018
    DebuffResistUp = 1_019
    GiveHealRateUp = 1_020
    ReceiveHealRateUp = 1_021
    GiveDamageUp = 1_022
    ReceiveDamageDown = 1_023
    CoolTimeRecoveryUp = 1_024
    ElementBonusUp = 1_025
    GiveDamageStandardUp = 1_026
    ReceiveDamageStandardDown = 1_027
    HitRateUp = 1_500
    AvoidanceRateUp = 1_501
    CriticalRateUp = 1_502
    CriticalResistRateUp = 1_503
    DebuffHitRateUp = 1_504
    DebuffResistRateUp = 1_505
    DamageGuard = 2_001
    Shield1 = 2_002
    Shield2 = 2_003
    DebuffGuard = 2_004
    ConfuseActionDebuffGuard = 2_005
    Taunt = 2_006
    Stealth = 2_007
    NonTarget = 2_008
    GiveDebuff = 2_009
    NormalSkillEnhance = 2_011
    HealOverTime = 2_012
    NonHit = 2_013
    Immortal = 2_014
    SkillMark = 2_015
    DamageBlock = 2_016
    TransientDamageBlock = 2_017
    ActiveSkill1Enhance = 2_100
    ActiveSkill2Enhance = 2_101
    DamageReflectEnhance11 = 2_111
    DamageReflectEnhance12 = 2_112
    DamageReflectEnhance13 = 2_113
    DamageReflectEnhance14 = 2_114
    DamageReflectEnhance21 = 2_121
    DamageReflectEnhance22 = 2_122
    DamageReflectEnhance23 = 2_123
    DamageReflectEnhance24 = 2_124
    DamageReflectEnhance31 = 2_131
    DamageReflectEnhance32 = 2_132
    DamageReflectEnhance33 = 2_133
    DamageReflectEnhance34 = 2_134
    AllSkillCoolTimeRecovery = 3_001
    Skill1CoolTimeRecovery = 3_002
    Skill2CoolTimeRecovery = 3_003
    AllSkillCoolTimeIncrease = 3_004
    Skill1CoolTimeIncrease = 3_005
    Skill2CoolTimeIncrease = 3_006
    ExtendAllBuffTurn = 3_041
    ExtendAllDeBuffTurn = 3_042
    ExtendStunTurn = 3_043
    ReduceAllBuffTurn = 3_044
    ReduceAllDeBuffTurn = 3_045
    ExtendEffectGroup = 3_046
    ReduceEffectGroup = 3_047
    IncreaseEffectStack = 3_048
    DecreaseEffectStack = 3_049
    RemoveAllBuff = 3_050
    RemoveAllDeBuff = 3_060
    RemoveAllConfuseActionGroupDebuff = 3_061
    RemoveEffectGroup = 3_101
    RemoveEffectType = 3_102
    RemoveBuff = 3_103
    RemoveDeBuff = 3_104
    RemoveSpecialEffectType = 3_105
    CopyArchiveBuff = 3_200
    CopyArchiveDeBuff = 3_201
    CopyAllBuffTargetToSelf = 3_202
    CopyAllDeBuffSelfToTarget = 3_203
    MoveBuffToMeFromEnemy = 3_204
    MoveDebuffToEnemyFromMe = 3_205
    SpeedDown = 5_001
    MaxHpDown = 5_002
    AttackPowerDown = 5_003
    DefenseDown = 5_004
    PhysicalDamageRelaxDown = 5_005
    MagicDamageRelaxDown = 5_006
    DefensePenetrationDown = 5_007
    DamageEnhanceDown = 5_008
    HitDown = 5_009
    AvoidanceDown = 5_010
    CriticalDown = 5_011
    CriticalResistDown = 5_012
    HpDrainDown = 5_013
    DamageReflectDown = 5_014
    CriticalDamageEnhanceDown = 5_015
    PhysicalCriticalDamageRelaxDown = 5_016
    MagicCriticalDamageRelaxDown = 5_017
    DebuffHitDown = 5_018
    DebuffResistDown = 5_019
    GiveHealRateDown = 5_020
    ReceiveHealRateDown = 5_021
    GiveDamageDown = 5_022
    ReceiveDamageUp = 5_023
    CoolTimeRecoveryDown = 5_024
    GiveDamageStandardDown = 5_025
    ReceiveDamageStandardUp = 5_026
    HitRateDown = 5_500
    AvoidanceRateDown = 5_501
    CriticalRateDown = 5_502
    CriticalResistRateDown = 5_503
    DebuffHitRateDown = 5_504
    DebuffResistRateDown = 5_505
    Stun = 6_001
    Confuse = 6_002
    Silence = 6_003
    Stubborn = 6_004
    HpRecoveryForbidden = 7_002
    BuffForbidden = 7_003
    AvoidanceForbidden = 7_004
    LockOnSelf = 7_111
    LockOnAllAlly = 7_121
    LockOnBlueAlly = 7_131
    LockOnRedAlly = 7_132
    LockOnGreenAlly = 7_133
    LockOnYellowAlly = 7_134
    LockOnLightAlly = 7_135
    LockOnDarkAlly = 7_136
    LockOnWarriorAlly = 7_141
    LockOnSniperAlly = 7_142
    LockOnSorcererAlly = 7_143
    LockOnAttack1Ally = 7_151
    LockOnAttack2Ally = 7_152
    LockOnAttack3Ally = 7_153
    Poison = 8_001
    Bleeding = 8_002
    Combustion = 8_003
    Burn = 8_004
    SelfInjuryPoison = 8_101
    SelfInjuryBleeding = 8_102
    SelfInjuryCombustion = 8_103
    DamageResonanceFromSelfAndDamageReduction = 8_111
    DamageResonanceFromHighHpEnemy = 8_121
    DamageResonanceFromLowHpEnemy = 8_122
    DamageResonanceFromHighDefenseEnemy = 8_123
    DamageResonanceFromLowDefenseEnemy = 8_124
    DamageResonanceFromRandomEnemy = 8_125
    DamageResonanceFromHighBaseMaxHpEnemy = 8_126
    DamageResonanceFromLowBaseMaxHpEnemy = 8_127
    DamageResonanceFromHighBaseDefenseEnemy = 8_128
    DamageResonanceFromLowBaseDefenseEnemy = 8_129
    DamageResonanceFromAllEnemy = 8_131
    DamageResonanceFromAllAllyAndDamageReduction = 8_141
    SpeedDrain = 9_001
    AttackPowerDrain = 9_003
    DefenseDrain = 9_004


# endregion


# region Guild


class GuildRaidBossType(IntEnum):
    Normal = 0
    Releasable = 1
    Event = 2


class GuildActivityPolicyType(IntEnum):
    NONE = 0
    PlayFreely = 1
    PlayGuts = 2
    PlayLeisurely = 3
    PlayNoisy = 4
    BeginnerWelcome = 5


class GlobalGvgGroupType(IntEnum):
    All = 0
    Bronze = 1
    Silver = 2
    Golden = 3


class PlayerGuildPositionType(IntEnum):
    NONE = 0
    Leader = 1
    SubLeader = 2
    Member = 3


# endregion


# region Quest


class QuestQuickExecuteType(IntEnum):
    # Reap quest for diamonds vs ticket, I assume
    Currency = 1
    Privilege = 2


# endregion


# region Trials


_TOWER_TYPE_NAMES = ('', 'Infinity', 'Azure', 'Crimson', 'Emerald', 'Amber')


class TowerType(IntEnum):
    NONE = 0
    Infinite = 1
    Blue = 2
    Red = 3
    Green = 4
    Yellow = 5

    @cached_property
    def tower_name(self) -> str:
        return f'Tower of {_TOWER_TYPE_NAMES[self]}'

    @cached_property
    def alias(self) -> str | None:
        if self.value < 2:
            return None
        return _TOWER_TYPE_NAMES[self]

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            lc_value = value.lower()
            for key, member in cls._member_map_.items():
                if lc_value == key.lower() or ((alias := member.alias) and alias.lower() == lc_value):  # noqa
                    return member

        return super()._missing_(value)

    @classmethod
    def get_choice_map(cls) -> dict[str, TowerType]:
        choice_map = {}
        for key, member in cls._member_map_.items():
            if member is cls.NONE:
                continue
            choice_map[key] = member
            if member.alias:  # noqa
                choice_map[member.alias] = member  # noqa

        return choice_map  # type: ignore


class TowerBattleRewardsType(IntEnum):
    NONE = 0
    First = 1
    Confirmed = 2
    Lottery = 3


class BountyQuestType(IntEnum):
    Solo = 0
    Team = 1
    Guerrilla = 2


class BountyQuestRarityFlags(IntEnum):
    NONE = 0
    NInit = 1
    N = 2
    R = 4
    SR = 8
    SSR = 16
    UR = 32
    LR = 64


class DungeonBattleGridState(IntEnum):
    Done = 0
    Selected = 1
    Reward = 2
    SkipShop = 3


# endregion


# region Missions


class MissionGroupType(IntEnum):
    Main = 0
    Daily = 1
    Weekly = 2
    Beginner = 3
    Comeback = 4
    NewCharacter = 5
    Limited = 6
    Panel = 9
    Guild = 10
    GuildTower = 11


class MissionStatusType(IntEnum):
    Locked = 0
    Progress = 1
    NotReceived = 2
    Received = 3


class MissionActivityRewardStatusType(IntEnum):
    Locked = 0
    NotReceived = 1
    Received = 2


class MissionType(IntEnum):
    Main = 0
    Daily = 1
    Weekly = 2
    BeginnerFirstDay = 311
    BeginnerFirstDayLevel = 312
    BeginnerFirstDayStage = 313
    BeginnerFirstDayBuy = 314
    BeginnerSecondDay = 321
    BeginnerSecondDayQuick = 322
    BeginnerSecondDayBattleLeague = 323
    BeginnerSecondDayBuy = 324
    BeginnerThirdDay = 331
    BeginnerThirdDayForge = 332
    BeginnerThirdDayDungeonBattle = 333
    BeginnerThirdDayBuy = 334
    BeginnerFourthDay = 341
    BeginnerFourthDayReinforceEquipment = 342
    BeginnerFourthDayTowerBattle = 343
    BeginnerFourthDayBuy = 344
    BeginnerFifthDay = 351
    BeginnerFifthDayBountyQuest = 352
    BeginnerFifthDayTotalCharacter = 353
    BeginnerFifthDayBuy = 354
    BeginnerSixthDay = 361
    BeginnerSixthDaySphere = 362
    BeginnerSixthDayCharacterEvolution = 363
    BeginnerSixthDayBuy = 364
    BeginnerSeventhDay = 371
    BeginnerSeventhDayTraining = 372
    BeginnerSeventhDayLocalRaid = 373
    BeginnerSeventhDayBuy = 374
    ComebackLogin = 401
    ComebackActivity = 402
    ComebackConsumeCurrency = 403
    NewCharacter = 5
    LimitedFirstDayTab1 = 611
    LimitedFirstDayTab2 = 612
    LimitedFirstDayTab3 = 613
    LimitedFirstDayTab4 = 614
    LimitedSecondDayTab1 = 621
    LimitedSecondDayTab2 = 622
    LimitedSecondDayTab3 = 623
    LimitedSecondDayTab4 = 624
    LimitedThirdDayTab1 = 631
    LimitedThirdDayTab2 = 632
    LimitedThirdDayTab3 = 633
    LimitedThirdDayTab4 = 634
    LimitedFourthDayTab1 = 641
    LimitedFourthDayTab2 = 642
    LimitedFourthDayTab3 = 643
    LimitedFourthDayTab4 = 644
    LimitedFifthDayTab1 = 651
    LimitedFifthDayTab2 = 652
    LimitedFifthDayTab3 = 653
    LimitedFifthDayTab4 = 654
    LimitedSixthDayTab1 = 661
    LimitedSixthDayTab2 = 662
    LimitedSixthDayTab3 = 663
    LimitedSixthDayTab4 = 664
    LimitedSeventhDayTab1 = 671
    LimitedSeventhDayTab2 = 672
    LimitedSeventhDayTab3 = 673
    LimitedSeventhDayTab4 = 674
    PanelSheet1 = 901
    PanelSheet2 = 902
    PanelSheet3 = 903
    Guild = 10
    GuildTower = 11


class MissionAchievementType(IntEnum):
    NONE = 0
    Login = 100
    BoughtByCurrency = 200
    UseFriendCode = 300
    NewCharacter = 1_000
    MissionTotalActivityAtComeback = 1_010_100
    MissionTotalActivityAtNewCharacterMission = 1_010_200
    MissionTotalActivityAtEvent = 1_010_300
    MissionTotalActivityAtPanelMission = 1_010_400
    PlayerInfoEditComment = 2_010_100
    FriendMaxFriendCount = 3_010_100
    FriendSendFriendPointCount = 3_010_200
    SocialAuthAccount = 4_010_100
    SocialFollowOfficialTwitter = 4_020_100
    SocialFollowOfficialYoutube = 4_020_200
    ExchangeLegendForgeMergeCount = 5_010_100
    ExchangeEquipmentForgeMergeCount = 5_020_200
    ExchangeAllBuyCount = 5_030_100
    ExchangeRegularBuyCount = 5_030_200
    ExchangeGvGBuyCount = 5_040_100
    ExchangeDungeonBattleBuyCount = 5_050_100
    ShopTotalBuyCurrency = 6_010_100
    CharacterLevelUpCount = 7_010_100
    CharacterLevelLinkMaxLevel = 7_010_200
    CharacterEquipmentMaxLevel = 7_010_300
    CharacterSphereMaxEquipCountLevel1 = 7_010_401
    CharacterSphereMaxEquipCountLevel2 = 7_010_402
    CharacterSphereMaxEquipCountLevel3 = 7_010_403
    CharacterSphereMaxEquipCountLevel4 = 7_010_404
    CharacterSphereMaxEquipCountLevel5 = 7_010_405
    CharacterSphereMaxEquipCountLevel6 = 7_010_406
    CharacterSphereMaxEquipCountLevel7 = 7_010_407
    CharacterSphereMaxEquipCountLevel8 = 7_010_408
    CharacterSphereMaxEquipCountLevel9 = 7_010_409
    CharacterMatchlessSacredTreasureMaxLevel = 7_010_500
    CharacterLegendSacredTreasureMaxLevel = 7_010_600
    CharacterEquipmentTrainingCount = 7_010_700
    CharacterEquipmentReinforceMaxLevel = 7_010_800
    CharacterEquipmentMergeCount = 7_010_900
    CharacterMaxBattlePower = 7_011_000
    CharacterCharacterMaxLevel = 7_011_100
    CharacterAllEquipmentReinforceMaxLevel = 7_011_200
    CharacterRankUpMaxRarity = 7_020_100
    CharacterRankUpEvolutionCount = 7_020_200
    CharacterLevelLinkOpenSlotCount = 7_030_100
    EquipmentSphereMaxLevel = 8_010_100
    EquipmentSphereComposeCount = 8_010_200
    EquipmentForgeCount = 8_020_100
    EquipmentComposeCountR = 8_030_101
    EquipmentComposeCountSR = 8_030_102
    EquipmentComposeCountSSR = 8_030_103
    AutoBattleMaxPlayerLevel = 9_010_100
    AutoBattleAddPopulation = 9_010_200
    BossBattleVictoryCount = 9_010_300
    AutoBattleMaxClearQuest = 9_010_400
    AutoBattledMaxClearChapter = 9_010_500
    AutoBattleGetRewardCount = 9_010_600
    AutoBattleQuickCount = 9_020_100
    DungeonBattleClearThirdFloorCount = 10_010_100
    DungeonBattleClearFirstFloorCount = 10_010_200
    DungeonBattleClearUnitJobTypeBase = 10_010_300
    DungeonBattleClear1UnitWarriorType = 10_010_311
    DungeonBattleClear1UnitSniperType = 10_010_312
    DungeonBattleClear1UnitSorcererType = 10_010_314
    DungeonBattleClear2UnitWarriorType = 10_010_321
    DungeonBattleClear2UnitSniperType = 10_010_322
    DungeonBattleClear2UnitSorcererType = 10_010_324
    DungeonBattleClear3UnitWarriorType = 10_010_331
    DungeonBattleClear3UnitSniperType = 10_010_332
    DungeonBattleClear3UnitSorcererType = 10_010_334
    DungeonBattleClear4UnitWarriorType = 10_010_341
    DungeonBattleClear4UnitSniperType = 10_010_342
    DungeonBattleClear4UnitSorcererType = 10_010_344
    DungeonBattleClear5UnitWarriorType = 10_010_351
    DungeonBattleClear5UnitSniperType = 10_010_352
    DungeonBattleClear5UnitSorcererType = 10_010_354
    DungeonBattleNewCharacter = 10_011_000
    TowerBattleMaxClearFloor = 11_010_100
    TowerBattleMinClearElementTower = 11_010_200
    TowerBattleTotalWinCount = 11_010_300
    BattleLeagueChallengeCount = 12_010_100
    BattleLeagueMaxRanking = 12_010_200
    LocalRaidVictoryCount = 13_010_100
    LocalRaidVictoryUnitElementTypeBase = 13_010_200
    LocalRaidVictory1UnitLightAndDarkType = 13_010_210
    LocalRaidVictory1UnitBlueType = 13_010_211
    LocalRaidVictory1UnitRedType = 13_010_212
    LocalRaidVictory1UnitGreenType = 13_010_213
    LocalRaidVictory1UnitYellowType = 13_010_214
    LocalRaidVictory1UnitLightType = 13_010_215
    LocalRaidVictory1UnitDarkType = 13_010_216
    LocalRaidVictory2UnitLightAndDarkType = 13_010_220
    LocalRaidVictory2UnitBlueType = 13_010_221
    LocalRaidVictory2UnitRedType = 13_010_222
    LocalRaidVictory2UnitGreenType = 13_010_223
    LocalRaidVictory2UnitYellowType = 13_010_224
    LocalRaidVictory2UnitLightType = 13_010_225
    LocalRaidVictory2UnitDarkType = 13_010_226
    LocalRaidVictory3UnitLightAndDarkType = 13_010_230
    LocalRaidVictory3UnitBlueType = 13_010_231
    LocalRaidVictory3UnitRedType = 13_010_232
    LocalRaidVictory3UnitGreenType = 13_010_233
    LocalRaidVictory3UnitYellowType = 13_010_234
    LocalRaidVictory3UnitLightType = 13_010_235
    LocalRaidVictory3UnitDarkType = 13_010_236
    LocalRaidVictory4UnitLightAndDarkType = 13_010_240
    LocalRaidVictory4UnitBlueType = 13_010_241
    LocalRaidVictory4UnitRedType = 13_010_242
    LocalRaidVictory4UnitGreenType = 13_010_243
    LocalRaidVictory4UnitYellowType = 13_010_244
    LocalRaidVictory4UnitLightType = 13_010_245
    LocalRaidVictory4UnitDarkType = 13_010_246
    LocalRaidVictory5UnitLightAndDarkType = 13_010_250
    LocalRaidVictory5UnitBlueType = 13_010_251
    LocalRaidVictory5UnitRedType = 13_010_252
    LocalRaidVictory5UnitGreenType = 13_010_253
    LocalRaidVictory5UnitYellowType = 13_010_254
    LocalRaidVictory5UnitLightType = 13_010_255
    LocalRaidVictory5UnitDarkType = 13_010_256
    BountyQuestAllStartQuestCount = 14_010_100
    BountyQuestNewCharacter = 14_011_000
    BountyQuestTeamStartQuestCount = 14_020_100
    GachaNewJoinCharacter = 15_010_100
    GachaDrawCount = 15_010_200
    ConsumeCurrencyCount = 15_010_300
    GuildJoinCount = 16_010_100
    GuildLoginCount = 16_010_200
    GuildGuildRaidChallengeCount = 16_020_100
    ChatSayWorldChatCount = 17_010_100
    OsStoreUpdateCount = 18_010_100
    PictureBookTransitionPanel = 21_010_100
    MusicPlayerTransitionCount = 22_010_100
    GuildTowerWinUnitSameJobTypeBase = 23_010_100
    GuildTowerWin1UnitSameJobType = 23_010_101
    GuildTowerWin2UnitSameJobType = 23_010_102
    GuildTowerWin3UnitSameJobType = 23_010_103
    GuildTowerWin4UnitSameJobType = 23_010_104
    GuildTowerWin5UnitSameJobType = 23_010_105
    GuildTowerWinCount = 23_010_200
    GuildTowerMaxComboCount = 23_010_300
    GuildTowerGetJobReinforcementMaterialCount = 23_010_400
    GuildTowerMaxJobLevel = 23_020_100
    GuildTowerMinJobLevel = 23_020_200


# endregion
