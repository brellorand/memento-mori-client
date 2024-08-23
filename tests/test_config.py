#!/usr/bin/env python

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main

from mm.config import AccountConfig, ConfigFile


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


if __name__ == '__main__':
    main(verbosity=2)
