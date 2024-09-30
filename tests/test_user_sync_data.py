#!/usr/bin/env python

import json
from copy import deepcopy
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import MagicMock, Mock, patch

from mm.enums import TowerType
from mm.game import PlayerAccount
from mm.game.models import UserSyncData
from mm.http_client import ApiClient


def load_sync_data():
    mb_dir = Path(__file__).resolve().parent.joinpath('data/user_sync')
    return {path.stem: json.loads(path.read_text('utf-8')) for path in mb_dir.iterdir()}


CLEARED_TUTORIAL_IDS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 5000, 12, 13, 14, 15, 16, 17, 18, 2400, 2000, 3200]


class TestUserSyncData(TestCase):
    _sync_data = load_sync_data()
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

    def _get_data(self, name: str):
        return deepcopy(self._sync_data[name])  # deepcopy is needed to prevent tests from affecting each other

    def test_basic_update_user_sync_data(self):
        usd = UserSyncData(Mock(), self._get_data('world_login')['UserSyncData'])

        self.assertIsNone(usd.cleared_tutorial_ids)
        self.assertIsNone(usd.has_vip_daily_gift)
        self.assertIsNone(usd.has_transitioned_panel_picture_book)
        self.assertIsNone(usd.guild_raid_challenge_count)
        self.assertEqual([], usd.character_index_info)

        usd.update(self._get_data('get_user_data')['UserSyncData'])

        self.assertEqual(CLEARED_TUTORIAL_IDS, usd.cleared_tutorial_ids)
        self.assertTrue(usd.has_vip_daily_gift)
        self.assertIs(False, usd.has_transitioned_panel_picture_book)  # assertFalse only checks truthiness
        self.assertEqual(6, usd.guild_raid_challenge_count)
        self.assertEqual(15, len(usd.character_index_info))
        self.assertEqual(
            {'CharacterId': 1, 'MaxCharacterLevel': 1, 'MaxCharacterRarityFlags': 1, 'MaxEpisodeId': 0},
            usd.character_index_info[0],
        )

    def test_world_user_sync_data_automatically_updated(self):
        api_client = Mock(
            login_player=Mock(return_value=self._get_data('world_login')),
            post_msg=Mock(return_value=self._get_data('get_user_data')),
        )

        world = mocked_player_account().get_world(18)
        self.assertEqual(4018, world.world_id)
        self.assertFalse(world.is_logged_in)
        self.assertIsNone(world.user_sync_data)

        with patch.object(ApiClient, 'child_client', return_value=api_client):
            world.login()

        self.assertTrue(world.is_logged_in)
        self.assertIsInstance(world.user_sync_data, UserSyncData)
        self.assertEqual(1710593161000, world.user_sync_data.received_auto_battle_reward_last_time)
        self.assertIsNone(world.user_sync_data.cleared_tutorial_ids)

        usd = world.get_user_sync_data()
        self.assertIs(usd, world.user_sync_data)
        self.assertEqual(CLEARED_TUTORIAL_IDS, world.user_sync_data.cleared_tutorial_ids)

        world.close()
        self.assertFalse(world.is_logged_in)

    def test_tower_battle_updates_sync_data(self):
        api_client = Mock(
            login_player=Mock(return_value=self._get_data('world_login')),
            post_msg=Mock(
                side_effect=[self._get_data('get_user_data__before_tower'), self._get_data('tower_battle_win')]
            ),
        )
        world = mocked_player_account().get_world(18)
        with patch.object(ApiClient, 'child_client', return_value=api_client):
            world.login()
            world.get_user_sync_data()

        with self.subTest('update unique list'):
            self.assertEqual(4, world.user_sync_data.tower_type_status_map[TowerType.Yellow]['MaxTowerBattleId'])
            world.start_tower_battle(TowerType.Yellow, 4)
            self.assertEqual(5, world.user_sync_data.tower_type_status_map[TowerType.Yellow]['MaxTowerBattleId'])

        with self.subTest('update simple list'):
            # Note: the blocked player ids were artificially added to simulate this type of update for testing purposes
            self.assertEqual(4, len(world.user_sync_data.blocked_player_ids))


def mocked_player_account() -> PlayerAccount:
    player_data_info = {
        'CharacterId': 2,
        'LastLoginTime': 1716664759000,
        'LegendLeagueClass': 0,
        'Name': 'New Player',
        'Password': 'fake1b0eea85fake4c34a16891f8fake',
        'PlayerId': 272688835018,
        'PlayerRank': 10,
        'WorldId': 4018,
    }
    auth_client = Mock(login=Mock(return_value={'PlayerDataInfoList': [player_data_info]}), get_server_host=MagicMock())
    return PlayerAccount(Mock(auth_client=auth_client), Mock())


if __name__ == '__main__':
    main(verbosity=2)
