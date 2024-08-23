"""
GRPC Client (not fully implemented yet)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

# import msgpack
# from google.protobuf.internal import builder
# from google.protobuf import descriptor_pool
from grpc import Channel, RpcContext, StatusCode, insecure_channel, secure_channel

if TYPE_CHECKING:
    from pathlib import Path

__all__ = ['MagicOnionClient']
log = logging.getLogger(__name__)


class MagicOnionClient:
    def __init__(self, address: str, player_id: int, auth_token: str, options=None, compression=None):
        self.player_id = player_id
        self._auth_token = auth_token
        self.channel = insecure_channel(address, options=options, compression=compression)
