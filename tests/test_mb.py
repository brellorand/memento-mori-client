#!/usr/bin/env python

import json
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import Mock, patch

from mm.fs import CacheMiss
from mm.mb_models import MB

MODULE = 'mm.mb_models.base'


def load_mb_data():
    mb_dir = Path(__file__).resolve().parent.joinpath('data/mb')
    return {path.stem: json.loads(path.read_text('utf-8')) for path in mb_dir.iterdir()}


class TestMB(TestCase):
    _mb_data = load_mb_data()
    _session_patch: patch

    @classmethod
    def setUpClass(cls):
        cls._session_patch = patch(
            'mm.http_client.RequestsClient._init_session', side_effect=RuntimeError('HTTP request leak during test')
        )
        cls._session_patch.start()

    @classmethod
    def tearDownClass(cls):
        cls._session_patch.stop()

    def _get_mb_data(self, name: str, **kwargs):
        return self._mb_data[name]

    def _init_mb(self) -> MB:
        # path_repr
        with patch(f'{MODULE}.MBFileCache', return_value=Mock(get=Mock(side_effect=CacheMiss))):
            with patch(f'{MODULE}.path_repr'):
                return MB(session=Mock(data_client=Mock(get_mb_data=self._get_mb_data)), use_cache=False)

    def test_char_from_short_name(self):
        mb = self._init_mb()
        self.assertEqual(mb.characters[46], mb.get_character('lunalynn'))

    def test_char_from_full_name(self):
        mb = self._init_mb()
        self.assertEqual(mb.characters[46], mb.get_character('Lunalynn (The Witch of Snowy Illusions)'))

    def test_char_from_short_id(self):
        mb = self._init_mb()
        self.assertEqual(mb.characters[43], mb.get_character('43'))

    def test_char_from_long_id(self):
        mb = self._init_mb()
        self.assertEqual(mb.characters[43], mb.get_character('CHR_000043'))

    def test_char_from_alias(self):
        mb = self._init_mb()
        self.assertEqual(mb.characters[46], mb.get_character('luna'))
        self.assertEqual('Florence', mb.get_character('flo').name)

    def test_invalid_char_name(self):
        mb = self._init_mb()
        with self.assertRaisesRegex(KeyError, 'Unknown character name='):
            mb.get_character('foo_bar')


if __name__ == '__main__':
    from mm.logging import init_logging

    init_logging(10)

    main(verbosity=2)
