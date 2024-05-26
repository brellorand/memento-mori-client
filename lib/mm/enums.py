"""

"""

from __future__ import annotations

import logging
from enum import StrEnum, IntEnum, IntFlag, CONFORM

__all__ = ['Rarity', 'RuneRarity', 'Region', 'Locale', 'LOCALES']
log = logging.getLogger(__name__)


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


class Rarity(StrEnum):
    R = 'R'
    R_PLUS = 'R+'
    SR = 'SR'
    SR_PLUS = 'SR+'
    SSR = 'SSR'
    SSR_PLUS = 'SSR+'
    UR = 'UR'
    UR_PLUS = 'UR+'
    LR = 'LR'
    LR_1 = 'LR+1'
    LR_2 = 'LR+2'
    LR_3 = 'LR+3'
    LR_4 = 'LR+4'
    LR_5 = 'LR+5'
    LR_6 = 'LR+6'


class RuneRarity(StrEnum):
    R = 'R'
    SR = 'SR'
    SSR = 'SSR'
    UR = 'UR'
    LR = 'LR'


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


class Element(IntEnum):
    AZURE = 1
    CRIMSON = 2
    EMERALD = 3
    AMBER = 4
    RADIANCE = 5
    CHAOS = 6


class Job(IntEnum):
    WARRIOR = 1
    SNIPER = 2
    SORCERER = 4


class CharacterRarity(IntEnum):
    N = 1
    R = 2
    SR = 8


class SnsType(IntEnum):
    # Note: C# enums with no explicit values start from 0 and increase by 1 for each item
    NONE = 0
    OrtegaId = 1
    AppleId = 2
    Twitter = 3
    Facebook = 4
    GameCenter = 5
    GooglePlay = 6


class ErrorLogType(IntEnum):
    NONE = 0
    ErrorCode = 1
    ClientErrorCode = 2


class LegendLeagueClassType(IntEnum):
    NONE = 0
    Chevalier = 1
    Paladin = 2
    Duke = 3
    Royal = 4
    Legend = 5
    WorldRuler = 6


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
    Sphere = 14
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
    EventExchangePlaceItem = 50
    StripeCoupon = 1_001


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


class CharacterRarityFlags(IntFlag, boundary=CONFORM):
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


class BaseParameterType(IntEnum):
    Muscle = 1
    Energy = 2
    Intelligence = 3
    Health = 4


class EquipmentSlotType(IntEnum):
    Weapon = 1
    Sub = 2
    Gauntlet = 3
    Helmet = 4
    Armor = 5
    Shoes = 6
