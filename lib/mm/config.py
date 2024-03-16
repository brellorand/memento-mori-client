"""

"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from functools import cached_property
from typing import TYPE_CHECKING, Any, Self

from .enums import Locale
from .fs import PathLike, get_config_dir, path_repr

if TYPE_CHECKING:
    from pathlib import Path

__all__ = ['ConfigFile', 'Account']
log = logging.getLogger(__name__)


class ConfigFile:
    def __init__(self, path: PathLike = None):
        if path:
            self.path = Path(path).expanduser().resolve()
        else:
            self.path = get_config_dir().joinpath('config.json')

    @cached_property
    def data(self) -> dict[str, Any]:
        try:
            with self.path.open('r', encoding='utf-8') as f:
                log.debug(f'Loading config from {path_repr(self.path)}')
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save(self):
        if 'data' not in self.__dict__:
            log.debug('No config data was loaded - skipping save')
            return

        log.debug(f'Saving config to {path_repr(self.path)}')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open('w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, sort_keys=True, indent=4)

    @cached_property
    def auth(self) -> AuthOptions:
        return AuthOptions._load(self)

    @cached_property
    def accounts(self) -> dict[str, Account]:
        return Account._load_all(self)


class ConfigSection(ABC):
    section_name: str
    id_attr: str = None

    def __init_subclass__(cls, section: str = None, id_attr: str = None, **kwargs):
        super().__init_subclass__(**kwargs)
        if section:
            cls.section_name = section
        if id_attr:
            cls.id_attr = id_attr

    def __init__(self, config_file: ConfigFile = None, **kwargs):
        self._config = config_file or ConfigFile()

    @classmethod
    def load_all(cls, config_path: PathLike = None) -> dict[str, Self]:
        return cls._load_all(ConfigFile(config_path))

    @classmethod
    def _load_all(cls, config: ConfigFile) -> dict[str, Self]:
        return {key: cls(config_file=config, **val) for key, val in config.data[cls.section_name].items()}

    @classmethod
    def _load(cls, config: ConfigFile) -> Self:
        return cls(config_file=config, **config.data[cls.section_name])

    @abstractmethod
    def as_dict(self) -> dict[str, int | str | None]:
        raise NotImplementedError

    def save(self):
        section = self._config.data.setdefault(self.section_name, {})
        if self.id_attr:
            section[str(getattr(self, self.id_attr))] = self.as_dict()
        else:
            section.update(self.as_dict())
        self._config.save()


class AuthOptions(ConfigSection, section='auth'):
    def __init__(
        self,
        *,
        app_version: str = None,
        os_version: str = None,
        model_name: str = None,
        locale: Locale = None,
        config_file: ConfigFile = None,
    ):
        super().__init__(config_file)
        # TODO: Find more appropriate values?
        self.app_version = app_version
        self.os_version = os_version or 'Android OS 13 / API-33 (TKQ1.220829.002/V14.0.12.0.TLACNXM)'
        self.model_name = model_name or 'Xiaomi 2203121C'
        self.locale = Locale(locale) if locale else Locale.EnUs

    def as_dict(self) -> dict[str, int | str | None]:
        return {
            'app_version': self.app_version,
            'os_version': self.os_version,
            'model_name': self.model_name,
            'locale': self.locale,
        }


class Account(ConfigSection, section='accounts', id_attr='user_id'):
    def __init__(self, user_id: int, client_key: str = None, name: str = None, config_file: ConfigFile = None):
        super().__init__(config_file)
        self.user_id = int(user_id)
        self._client_key = client_key
        self.name = name

    def __str__(self) -> str:
        return f'{self.__class__.__name__}[name={self.name!r}, id={self.user_id}]'

    def as_dict(self) -> dict[str, int | str | None]:
        return {'user_id': self.user_id, 'client_key': self.client_key, 'name': self.name}

    @property
    def client_key(self) -> str | None:
        return self._client_key

    @client_key.setter
    def client_key(self, value: str | None):
        save = hasattr(self, '_client_key')
        self._client_key = value
        if save and value:
            self.save()
