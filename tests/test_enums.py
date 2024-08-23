#!/usr/bin/env python

from unittest import TestCase, main

from mm.enums import EquipmentRarityFlags, Locale


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

    def test_locale_country_codes(self):
        cases = {
            Locale.DeDe: 'DE',
            Locale.EnUs: 'US',
            Locale.EsMx: 'MX',
            Locale.FrFr: 'FR',
            Locale.IdId: 'ID',
            Locale.JaJp: 'JP',
            Locale.KoKr: 'KR',
            Locale.PtBr: 'BR',
            Locale.RuRu: 'RU',
            Locale.ThTh: 'TH',
            Locale.ViVn: 'VN',
            Locale.ZhCn: 'CN',
            Locale.ZhTw: 'TW',
        }
        for locale, expected in cases.items():
            with self.subTest(locale=locale):
                self.assertEqual(expected, locale.country_code)


if __name__ == '__main__':
    main(verbosity=2)
