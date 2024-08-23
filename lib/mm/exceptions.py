"""
Exceptions for the Memento Mori client / package.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .enums import ErrorCode
from .errors import ERROR_CODE_MESSAGE_MAP

if TYPE_CHECKING:
    from requests import Request, Response

    from .typing import ApiErrorResponse

log = logging.getLogger(__name__)


class MementoMoriException(Exception):
    """Base exception for other exceptions defined in this package"""


class CacheError(MementoMoriException):
    """Raised when an API response cannot be cached to a file or loaded from a cache file"""


class CacheMiss(CacheError):
    """Used internally to signal that a file cache miss occurred"""


class RuneError(MementoMoriException):
    """Raised when an invalid combination of rune types, levels, or quantities is provided"""


class MissingClientKey(MementoMoriException):
    """Raised when no client key is stored for a given account, and a password is required"""


class ApiResponseError(MementoMoriException):
    """Raised when the ortegastatuscode header value in a response is non-zero"""

    _code_msg_map = {
        ErrorCode.InvalidRequestHeader: 'Login expired - please log in again',
        ErrorCode.AuthLoginInvalidRequest: 'Login failed - please check your account configuration',
    }

    def __init__(self, resp: Response, data: ApiErrorResponse):
        self.resp: Response = resp
        self.data: ApiErrorResponse = data
        try:
            self.error_code = ErrorCode(self.data.get('ErrorCode', 0))
        except (ValueError, TypeError):
            log.warning(f'Unrecognized error code found in {self.data}')
            self.error_code = self.error_message = None
        else:
            self.error_message = ERROR_CODE_MESSAGE_MAP.get(self.error_code)

    def _format_message(self, info: str) -> str:
        return f'{info} (unable to access url={self.resp.request.url} - details: {self.data})'

    def __str__(self) -> str:
        if message := self._code_msg_map.get(self.error_code):
            return self._format_message(message)
        elif self.error_message:
            return self._format_message(self.error_message)
        return f'Error requesting url={self.resp.request.url}: {self.data}'
