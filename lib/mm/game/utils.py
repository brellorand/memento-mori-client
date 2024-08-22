"""
Utils for logged-in accounts/sessions
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from time import sleep
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .tasks import TaskConfig

__all__ = ['load_cached_data', 'wait']
log = logging.getLogger(__name__)


def load_cached_data(path: Path):
    with path.open('r', encoding='utf-8') as f:
        data = json.load(f)

    if len(data) == 2 and set(data) == {'headers', 'data'}:
        return data['data']
    else:
        return data


def wait(config: TaskConfig):
    wait_ms = config.get_wait_ms()
    log.debug(f'Waiting {wait_ms} ms')
    sleep(wait_ms / 1000)
