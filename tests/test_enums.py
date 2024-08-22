#!/usr/bin/env python

from unittest import TestCase, main

from mm.enums import EquipmentRarityFlags


class TestEnums(TestCase):
    def test_equipment_rarity_flags_range(self):
        ERF = EquipmentRarityFlags
        cases = [
            (ERF.D | ERF.C | ERF.B | ERF.A, EquipmentRarityFlags.range(ERF.D, ERF.A)),
            (ERF.D | ERF.C | ERF.B, EquipmentRarityFlags.range(ERF.D, ERF.B)),
            (ERF.C | ERF.B | ERF.A, EquipmentRarityFlags.range(ERF.C, ERF.A)),
            (ERF.C, EquipmentRarityFlags.range(ERF.C, ERF.C)),
        ]
        for expected, erf_range in cases:
            with self.subTest(expected=expected):
                self.assertEqual(expected, erf_range)


if __name__ == '__main__':
    main(verbosity=2)
