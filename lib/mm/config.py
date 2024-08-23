"""
Classes for managing / loading configurable options
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any, Self

from .enums import Locale
from .fs import PathLike, get_config_dir, path_repr

if TYPE_CHECKING:
    from .http_client import AppVersionManager

__all__ = ['ConfigFile', 'AccountConfig', 'AndroidModel', 'ANDROID_MODELS', 'DEFAULT_ANDROID_MODEL']
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

    # region Sections

    @cached_property
    def auth(self) -> AuthOptions:
        return AuthOptions._load(self)

    @cached_property
    def accounts(self) -> dict[str, AccountConfig]:
        return AccountConfig._load_all(self)

    @cached_property
    def mb(self) -> MBOptions:
        return MBOptions._load(self)

    # endregion

    @cached_property
    def app_version_manager(self) -> AppVersionManager:
        from .http_client import AppVersionManager

        return AppVersionManager(self)


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
        return {key: cls(config_file=config, **val) for key, val in config.data.get(cls.section_name, {}).items()}

    @classmethod
    def _load(cls, config: ConfigFile) -> Self:
        return cls(config_file=config, **config.data.get(cls.section_name, {}))

    @abstractmethod
    def as_dict(self) -> dict[str, int | str | None]:
        raise NotImplementedError

    @property
    def parent(self) -> ConfigFile:
        return self._config

    def save(self):
        section = self._config.data.setdefault(self.section_name, {})
        if self.id_attr:
            section[str(getattr(self, self.id_attr))] = self.as_dict()
        else:
            section.update(self.as_dict())
        self._config.save()


# region Android Model


@dataclass
class AndroidModel:
    brand: str
    model: str
    version: int
    api: int
    build_id: str
    build_ver: str

    @property
    def model_name(self) -> str:
        """
        The ModelName value to be used in API requests.

        It appears that real values are from: https://docs.unity3d.com/ScriptReference/SystemInfo-deviceModel.html

        The format is not documented, but it appears to be two build properties, available via ``getprop`` in ``adb``:
            {ro.product.brand} {ro.product.model}

        Example value: ``Xiaomi 2203121C``
        """
        return f'{self.brand} {self.model}'

    @property
    def os_version(self) -> str:
        """
        The OSVersion value to be used in API requests.

        It appears that real values are from: https://docs.unity3d.com/ScriptReference/SystemInfo-operatingSystem.html

        The format is not documented, but it appears to contain build properties, available via ``getprop`` in ``adb``:
            Android OS {ro.build.version.release} / API-{ro.build.version.sdk} ({ro.build.id}/{ro.build.version.incremental})

        Example value: ``Android OS 13 / API-33 (TKQ1.220829.002/V14.0.12.0.TLACNXM)``
        """
        return f'Android OS {self.version} / API-{self.api} ({self.build_id}/{self.build_ver})'


ANDROID_MODELS = {
    'Galaxy S22': AndroidModel('Samsung', 'SM-S901E', 12, 31, 'SP1A.210812.016', 'S901EXXU2AVF1'),
    'Galaxy S21 Ultra': AndroidModel('Samsung', 'SM-G998B', 12, 31, 'SP1A.210812.016', 'G998BXXU4CVC4'),
    'Galaxy S21 Ultra 5G': AndroidModel('samsung', 'SM-G998B', 9, 28, 'SP1A.210812.016', 'G998BXXU4BULF'),  # bluestacks
    'Pixel Tablet': AndroidModel('Google', 'Pixel Tablet', 14, 34, 'UQ1A.240205.002', '11224170'),
    'Xiaomi 12S Ultra': AndroidModel('Xiaomi', '2203121C', 13, 33, 'TKQ1.220829.002', 'V14.0.12.0.TLACNXM'),
}
DEFAULT_ANDROID_MODEL = ANDROID_MODELS['Galaxy S22']


# endregion


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
        self.app_version = app_version
        self.os_version = os_version or DEFAULT_ANDROID_MODEL.os_version
        self.model_name = model_name or DEFAULT_ANDROID_MODEL.model_name
        self.locale = Locale(locale) if locale else Locale.EnUs

    def as_dict(self) -> dict[str, int | str | None]:
        return {
            'app_version': self.app_version,
            'os_version': self.os_version,
            'model_name': self.model_name,
            'locale': self.locale,
        }


class AccountConfig(ConfigSection, section='accounts', id_attr='user_id'):
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


class MBOptions(ConfigSection, section='mb'):
    def __init__(self, *, locale: Locale = None, config_file: ConfigFile = None):
        super().__init__(config_file)
        self.locale = Locale(locale) if locale else Locale.EnUs

    def as_dict(self) -> dict[str, int | str | None]:
        return {'locale': self.locale}
