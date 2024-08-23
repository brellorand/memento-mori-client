#!/usr/bin/env python

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main

from mm.config import ANDROID_MODELS, AccountConfig, ConfigFile


class TestConfig(TestCase):
    def test_add_accounts(self):
        accounts = {
            '1234': {'client_key': 'abc123', 'name': 'test_1', 'user_id': 1234},
            '4567': {'client_key': 'xyz987', 'name': 'test_2', 'user_id': 4567},
        }
        with TemporaryDirectory() as tmp:
            path = Path(tmp).joinpath('config.json')
            AccountConfig(1234, name='test_1', config_file=ConfigFile(path)).client_key = 'abc123'
            # Using a separate ConfigFile instance below is intentional
            AccountConfig(4567, name='test_2', config_file=ConfigFile(path)).client_key = 'xyz987'
            self.assertEqual({'accounts': accounts}, json.loads(path.read_text()))

    def test_android_model(self):
        android_model = ANDROID_MODELS['Galaxy S21 Ultra 5G']
        # The below expected values were observed in a packet capture of the game running on BlueStacks
        self.assertEqual('samsung SM-G998B', android_model.model_name)
        self.assertEqual('Android OS 9 / API-28 (SP1A.210812.016/G998BXXU4BULF)', android_model.os_version)


if __name__ == '__main__':
    main(verbosity=2)
