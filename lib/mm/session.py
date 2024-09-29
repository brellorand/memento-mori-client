"""
Provides a central entry point for initializing API clients with common configs
"""

from __future__ import annotations

import logging
from contextlib import AbstractContextManager
from contextvars import ContextVar
from functools import cached_property
from typing import TYPE_CHECKING, cast

from .assets import AssetCatalog
from .config import AccountConfig, ConfigFile
from .exceptions import NoActiveSession
from .http_client import AuthClient, DataClientWrapper
from .mb_models import MB

if TYPE_CHECKING:
    from .enums import Locale
    from .fs import PathLike
    from .game import PlayerAccount

__all__ = ['MementoMoriSession']
log = logging.getLogger(__name__)

_session_stack = ContextVar('mm.session.stack')


class MementoMoriSession(AbstractContextManager):
    config: ConfigFile

    def __init__(
        self,
        config: PathLike | ConfigFile = None,
        *,
        use_auth_cache: bool = True,
        use_data_cache: bool = True,
        use_mb_cache: bool = True,
        mb_locale: Locale = None,
        populate_mb_cache: bool = False,
        http_save_dir: PathLike = None,
    ):
        self.config = config if isinstance(config, ConfigFile) else ConfigFile(config)
        self._use_cache = {'auth': use_auth_cache, 'data': use_data_cache, 'mb': use_mb_cache}
        self._mb_locale = mb_locale
        self._http_save_dir = http_save_dir
        if populate_mb_cache:
            self.mb.populate_cache()

    def __enter__(self) -> MementoMoriSession:
        try:
            _session_stack.get().append(self)
        except LookupError:
            _session_stack.set([self])
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        _session_stack.get().pop()

    @cached_property
    def auth_client(self) -> AuthClient:
        return AuthClient(config=self.config, use_cache=self._use_cache['auth'], save_dir=self._http_save_dir)

    @cached_property
    def data_client(self) -> DataClientWrapper:
        return DataClientWrapper(auth_client=self.auth_client, use_data_cache=self._use_cache['data'])

    @cached_property
    def asset_catalog(self) -> AssetCatalog:
        return AssetCatalog(self.data_client._get_asset_catalog())

    @cached_property
    def mb(self) -> MB:
        return self.get_mb()

    def get_mb(self, **kwargs) -> MB:
        kwargs.setdefault('use_cache', self._use_cache['mb'])
        if 'locale' not in kwargs:
            kwargs['locale'] = self._mb_locale or self.config.mb.locale
        return MB(self, **kwargs)

    def get_account_config_by_id(self, user_id: int) -> AccountConfig:
        try:
            return self.config.accounts[str(user_id)]
        except KeyError as e:
            raise ValueError(f'Invalid {user_id=} - pick from: {", ".join(sorted(self.config.accounts))}') from e

    def get_account_config_by_name(self, name: str) -> AccountConfig:
        for account in self.config.accounts.values():
            if account.name == name:
                return account

        names = ', '.join(sorted(a.name for a in self.config.accounts.values()))
        raise ValueError(f'Unable to find an account with {name=} - pick from: {names}')

    def get_new_account(self, user_id: int, name: str) -> PlayerAccount:
        from .game import PlayerAccount

        return PlayerAccount(self, AccountConfig(user_id, name=name, config_file=self.config))

    def get_account_by_id(self, user_id: int) -> PlayerAccount:
        from .game import PlayerAccount

        return PlayerAccount(self, self.get_account_config_by_id(user_id))

    def get_account_by_name(self, name: str) -> PlayerAccount:
        from .game import PlayerAccount

        return PlayerAccount(self, self.get_account_config_by_name(name))


class MementoMoriSessionProxy:
    """
    Proxy for the currently active :class:`MementoMoriSession` object.  Allows usage similar to the ``request`` object
    in Flask.

    This class should not be instantiated by users - use the common :data:`mm_session` instance.
    """

    __slots__ = ()

    # region Generic Proxy Methods

    def __getattr__(self, attr: str):
        return getattr(get_current_session(), attr)

    def __setattr__(self, attr: str, value):
        return setattr(get_current_session(), attr, value)

    def __eq__(self, other) -> bool:
        return get_current_session() == other

    def __contains__(self, item) -> bool:
        return item in get_current_session()

    def __enter__(self) -> MementoMoriSession:
        # The current session is already active, so there's no need to re-enter it - it can just be returned
        return get_current_session()

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    # endregion

    # region Proxied Properties

    @property
    def auth_client(self) -> AuthClient:
        return get_current_session().auth_client

    @property
    def data_client(self) -> DataClientWrapper:
        return get_current_session().data_client

    @property
    def asset_catalog(self) -> AssetCatalog:
        return get_current_session().asset_catalog

    @property
    def mb(self) -> MB:
        return get_current_session().mb

    # endregion


mm_session: MementoMoriSession = cast(MementoMoriSession, MementoMoriSessionProxy())


def get_current_session(silent: bool = False) -> MementoMoriSession | None:
    """
    Get the currently active MementoMoriSession.

    :param silent: If True, allow this function to return ``None`` if there is no active :class:`MementoMoriSession`
    :return: The active :class:`MementoMoriSession` object
    :raises: :class:`~.NoActiveSession` if there is no active MementoMoriSession and ``silent=False`` (default)
    """
    try:
        return _session_stack.get()[-1]
    except (LookupError, IndexError):
        if silent:
            return None
        raise NoActiveSession('There is no active session') from None


def get_or_create_session(config: PathLike | ConfigFile = None, **kwargs) -> MementoMoriSession:
    if (session := get_current_session(True)) and config is None or session.config == config:
        return session
    return MementoMoriSession(config, **kwargs)
