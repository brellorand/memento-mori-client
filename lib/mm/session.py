"""

"""

from __future__ import annotations

import logging
from functools import cached_property
from typing import TYPE_CHECKING

from .assets import AssetCatalog
from .config import ConfigFile
from .http_client import AuthClient, DataClient
from .mb_models import MB

if TYPE_CHECKING:
    from pathlib import Path
    from .enums import Locale
    from .fs import PathLike
    from .account import PlayerAccount

__all__ = ['MementoMoriSession']
log = logging.getLogger(__name__)


class MementoMoriSession:
    config: ConfigFile

    def __init__(
        self,
        config: PathLike | ConfigFile = None,
        *,
        use_auth_cache: bool = True,
        use_data_cache: bool = True,
        use_mb_cache: bool = True,
        mb_locale: Locale = None,
        mb_json_cache_map: dict[str, Path] = None,
        populate_mb_cache: bool = False,
        http_save_dir: PathLike = None,
    ):
        self.config = config if isinstance(config, ConfigFile) else ConfigFile(config)
        self._use_cache = {'auth': use_auth_cache, 'data': use_data_cache, 'mb': use_mb_cache}
        self._mb_locale = mb_locale
        self._mb_json_cache_map = mb_json_cache_map
        self._http_save_dir = http_save_dir
        if populate_mb_cache:
            self.mb.populate_cache()

    @cached_property
    def auth_client(self) -> AuthClient:
        return AuthClient(config=self.config, use_cache=self._use_cache['auth'], save_dir=self._http_save_dir)

    @cached_property
    def data_client(self) -> DataClient:
        return DataClient(
            auth_client=self.auth_client, use_data_cache=self._use_cache['data'], use_mb_cache=self._use_cache['mb']
        )

    @cached_property
    def asset_catalog(self) -> AssetCatalog:
        return AssetCatalog(self.data_client._get_asset_catalog())

    @cached_property
    def mb(self) -> MB:
        return self.get_mb()

    def get_mb(self, **kwargs) -> MB:
        kwargs.setdefault('json_cache_map', self._mb_json_cache_map)
        if 'locale' not in kwargs:
            kwargs['locale'] = self._mb_locale or self.config.mb.locale
        return MB(self.data_client, **kwargs)

    def get_account_by_id(self, user_id: int) -> PlayerAccount:
        from .account import PlayerAccount

        try:
            account_config = self.config.accounts[str(user_id)]
        except KeyError as e:
            raise ValueError(f'Invalid {user_id=} - pick from: {", ".join(sorted(self.config.accounts))}') from e
        else:
            return PlayerAccount(self, account_config)

    def get_account_by_name(self, name: str) -> PlayerAccount:
        from .account import PlayerAccount

        for account in self.config.accounts.values():
            if account.name == name:
                return PlayerAccount(self, account)

        names = ', '.join(sorted(a.name for a in self.config.accounts.values()))
        raise ValueError(f'Unable to find an account with {name=} - pick from: {names}')
