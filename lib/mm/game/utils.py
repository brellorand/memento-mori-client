"""
Utils for logged-in accounts/sessions
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

__all__ = ['load_cached_data']
log = logging.getLogger(__name__)


def load_cached_data(path: Path):
    with path.open('r', encoding='utf-8') as f:
        data = json.load(f)

    if len(data) == 2 and set(data) == {'headers', 'data'}:
        return data['data']
    else:
        return data
