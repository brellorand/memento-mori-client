#!/usr/bin/env python

from unittest import TestCase, main
from unittest.mock import Mock
from uuid import uuid4
from time import time
from typing import Any

from mm.game.models import Equipment
from mm.game.tasks.smelting import _should_smelt
from mm.mb_models import Equipment as MBEquipment

SWORD_MB_DATA = {
    'Id': 449,
    'IsIgnore': None,
    'Memo': 'S+140_剣',
    'AdditionalParameterTotal': 8753,
    'AfterLevelEvolutionEquipmentId': 0,
    'AfterRarityEvolutionEquipmentId': 0,
    'BattleParameterChangeInfo': {'BattleParameterType': 2, 'ChangeParameterType': 1, 'Value': 8992.0},
    'Category': 1,
    'CompositeId': 0,
    'EquipmentEvolutionId': 0,
    'EquipmentExclusiveSkillDescriptionId': 0,
    'EquipmentForgeId': 6,
    'EquipmentLv': 140,
    'EquipmentReinforcementMaterialId': 1,
    'EquipmentSetId': 0,
    'EquippedJobFlags': 1,
    'ExclusiveEffectId': 0,
    'GoldRequiredToOpeningFirstSphereSlot': 20440,
    'GoldRequiredToTraining': 21020,
    'IconId': 65,
    'NameKey': '[EquipmentName65]',
    'PerformancePoint': 39866,
    'QualityLv': 1,
    'RarityFlags': 16,
    'SlotType': 1,
}


class TestSmelting(TestCase):
    def test_should_smelt(self):
        cases = [
            (True, (1, 160), mock_equipment({})),
            (False, (1, 120), mock_equipment({})),
            (False, (1, 160), mock_equipment({'SphereUnlockedCount': 1})),
            (False, (1, 160), mock_equipment({'SphereUnlockedCount': 2, 'LegendSacredTreasureLv': 1})),
            (False, (1, 160), mock_equipment({'LegendSacredTreasureLv': 2})),
            (False, (1, 160), mock_equipment({'MatchlessSacredTreasureLv': 3})),
            (False, (1, 160), mock_equipment({'MatchlessSacredTreasureLv': 3, 'ReinforcementLv': 60})),
            (False, (1, 160), mock_equipment({'ReinforcementLv': 20})),
        ]
        for expected, min_max_levels, equipment in cases:
            with self.subTest(equipment=equipment, min_max_levels=min_max_levels):
                self.assertEqual(expected, _should_smelt(equipment, *min_max_levels))


def mock_equipment(data: dict[str, Any]) -> Equipment:
    equipment_data = {
        'CharacterGuid': str(uuid4()).replace('-', ''),
        'CreateAt': int(time() * 1000),
        'PlayerId': 255555555018,
        'Guid': str(uuid4()).replace('-', ''),
        'EquipmentId': 449,
        'AdditionalParameterHealth': 0,
        'AdditionalParameterIntelligence': 0,
        'AdditionalParameterMuscle': 0,
        'AdditionalParameterEnergy': 0,
        'SphereId1': 0,
        'SphereId2': 0,
        'SphereId3': 0,
        'SphereId4': 0,
        'SphereUnlockedCount': 0,
        'LegendSacredTreasureExp': 0,
        'LegendSacredTreasureLv': 0,
        'MatchlessSacredTreasureExp': 0,
        'MatchlessSacredTreasureLv': 0,
        'ReinforcementLv': 0,
    }
    equipment = Equipment(Mock(), equipment_data | data)
    equipment.__dict__['equipment'] = MBEquipment(Mock(), SWORD_MB_DATA)
    return equipment


if __name__ == '__main__':
    main(verbosity=2)
