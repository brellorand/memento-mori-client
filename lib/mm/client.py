"""
Memento Mori API Clients
"""

from __future__ import annotations

import logging
import re
from functools import cached_property
from threading import Lock
from typing import TYPE_CHECKING, Union, MutableMapping, Any, Mapping
from urllib.parse import urlencode, urlparse
from uuid import uuid4
from weakref import finalize

import msgpack
from requests import Session, Response

from .assets import AssetCatalog, Asset
from .data import GameData, OrtegaInfo
from .exceptions import CacheMiss
from .fs import FileCache
from .utils import UrlPart, RequestMethod, format_path_prefix, rate_limited

if TYPE_CHECKING:
    from pathlib import Path

__all__ = ['AuthClient', 'DataClient']
log = logging.getLogger(__name__)

Bool = Union[bool, Any]
OptStr = str | None

AUTH_HOST = 'prd1-auth.mememori-boi.com'


class RequestsClient:
    """
    Facilitates submission of multiple requests for different endpoints to a single server.

    :param host_or_url: A hostname or host:port, or a URL from which the scheme, host, port, and path_prefix should
      be derived.
    :param port: A port
    :param scheme: The URI scheme to use (http, https, etc.) (default: http)
    :param path_prefix: A URI path prefix to include on all URLs.  If provided, it may be overridden on a
      per-request basis.  A ``/`` will be added to the beginning and end if it was not included.
    :param raise_errors: Whether :meth:`Response.raise_for_status<requests.Response.raise_for_status>` should be used
      to raise an exception if a response has a 4xx/5xx status code.  This may be overridden on a per-request basis.
    :param headers: Headers that should be included in the session.
    :param log_lvl: Log level to use when logging messages about the method/url when requests are made
    :param log_params: Include query params in logged messages when requests are made
    :param rate_limit: Interval in seconds to wait between requests (default: no rate limiting).  If specified,
      then a lock is used to prevent concurrent requests.
    :param nopath: When initialized with a URL, ignore the path portion
    """

    scheme = UrlPart()
    host = UrlPart()
    port = UrlPart(lambda v: int(v) if v is not None else v)
    path_prefix = UrlPart(format_path_prefix)

    def __init__(
        self,
        host_or_url: str,
        port: Union[int, str, None] = None,
        *,
        scheme: OptStr = None,
        path_prefix: OptStr = None,
        raise_errors: Bool = True,
        headers: MutableMapping[str, Any] = None,
        log_lvl: int = logging.DEBUG,
        log_params: Bool = True,
        log_data: Bool = False,
        rate_limit: float = 0,
        nopath: Bool = False,
    ):
        if host_or_url and re.match('^[a-zA-Z]+://', host_or_url):  # If it begins with a scheme, assume it is a url
            parsed = urlparse(host_or_url)
            self.host = parsed.hostname
            port = port or parsed.port
            scheme = scheme or parsed.scheme
            path_prefix = path_prefix if nopath else path_prefix or parsed.path
        else:
            self.host = host_or_url
            if self.host and ':' in self.host and port:
                raise ValueError(f'Conflicting arguments: port provided twice (host_or_url={self.host!r}, {port=})')

        self.scheme = scheme or 'http'
        self.port = port
        self.path_prefix = path_prefix
        self.raise_errors = raise_errors
        self._headers = headers or {}
        self.log_lvl = log_lvl
        self.log_params = log_params
        self.log_data = log_data
        self._init(rate_limit)

    def _init(self, rate_limit: float):
        # This method is separate from __init__ to allow RequestsClient objects to be pickleable - see __setstate__
        self._lock = Lock()
        self.__session = None
        self.__finalizer = finalize(self, self.__close)
        self._rate_limit = rate_limit
        if rate_limit:
            self.request = rate_limited(rate_limit)(self.request)

    # region Session Initialization

    def _init_session(self) -> Session:
        session = Session()
        session.headers.update(self._headers)
        if not self.__finalizer.alive:
            self.__finalizer = finalize(self, self.__close)
        return session

    @property
    def session(self) -> Session:
        """
        Initializes a new session using the provided ``session_fn``, or returns the already created one if it already
        exists.

        :return: The :class:`Session<requests.Session>` that will be used for requests
        """
        with self._lock:
            if self.__session is None:
                self.__session = self._init_session()  # noqa
            return self.__session

    @session.setter
    def session(self, value: Session):
        with self._lock:
            self.__session = value  # noqa

    # endregion

    # region URL Formatting & Request Logging

    @cached_property
    def _url_fmt(self) -> str:
        host_port = f'{self.host}:{self.port}' if self.port else self.host
        return f'{self.scheme}://{host_port}/{{}}'

    def url_for(self, path: str, params: Mapping[str, Any] = None, relative: Bool = True) -> str:
        """
        :param path: The URL path to retrieve
        :param params: Request query parameters
        :param relative: Whether the stored :attr:`.path_prefix` should be used
        :return: The full URL for the given path
        """
        if not relative and path.startswith(('http://', 'https://')):
            url = path
        else:
            path = path[1:] if path.startswith('/') else path
            url = self._url_fmt.format(self.path_prefix + path if relative else path)
        if params:
            url = f'{url}?{urlencode(params, True)}'
        return url

    def _log_req(
        self,
        method: str,
        url: str,
        path: str = '',
        relative: Bool = True,
        params: Mapping[str, Any] = None,
        log_params: Bool = None,
        log_data: Bool = None,
        kwargs: Mapping[str, Any] = None,
    ):
        if params and (log_params or (log_params is None and self.log_params)):
            url = self.url_for(path, params, relative=relative)

        if (log_data or (log_data is None and self.log_data)) and (data := kwargs.get('data') or kwargs.get('json')):
            data_repr = f' < {data=}'
        else:
            data_repr = ''

        log.log(self.log_lvl, f'{method} -> {url}{data_repr}')

    # endregion

    # region Request Methods

    def request(
        self,
        method: str,
        path: str,
        *,
        relative: Bool = True,
        raise_errors: Bool = None,
        log: Bool = True,  # noqa
        log_params: Bool = None,
        log_data: Bool = None,
        **kwargs,
    ) -> Response:
        """
        Submit a request to the URL based on the given path, using the given HTTP method.

        :param method: HTTP method to use (GET/PUT/POST/etc.)
        :param path: The URL path to retrieve
        :param relative: Whether the stored :attr:`.path_prefix` should be used
        :param raise_errors: Whether :meth:`Response.raise_for_status<requests.Response.raise_for_status>` should
          be used to raise an exception if the response has a 4xx/5xx status code.  Overrides the setting stored when
          initializing :class:`RequestsClient`, if provided.  Setting this to False does not prevent exceptions caused
          by anything other than 4xx/5xx errors from being raised.
        :param log: Whether a message should be logged with the method and url.  The log level is set when
          initializing :class:`RequestsClient`.
        :param log_params: Whether query params should be logged, if ``log=True``.  Overrides the setting stored
          when initializing :class:`RequestsClient`, if provided.
        :param log_data: Whether POST/PUT data should be logged, if ``log=True``.  Overrides the setting stored when
          initializing :class:`RequestsClient`, if provided.
        :param kwargs: Keyword arguments to pass to :meth:`Session.request<requests.Session.request>`
        :return: The :class:`Response<requests.Response>` to the request
        :raises: :class:`RequestException<requests.RequestException>` (or a subclass thereof) if the request failed.
          If the exception is caused by an HTTP error code, then a :class:`HTTPError<requests.HTTPError>` will be
          raised, and the code can be accessed via the exception's ``.response.status_code`` attribute. If the
          exception is due to a request or connection timeout, then a :class:`Timeout<requests.Timeout>` (or further
          subclass thereof) will be raised, and the exception will not have a ``response`` property.
        """
        url = self.url_for(path, relative=relative)
        if log:
            self._log_req(method, url, path, relative, kwargs.get('params'), log_params, log_data, kwargs)

        resp = self.session.request(method, url, **kwargs)
        if raise_errors or (raise_errors is None and self.raise_errors):
            resp.raise_for_status()
        return resp

    get = RequestMethod()
    put = RequestMethod()
    post = RequestMethod()
    delete = RequestMethod()
    options = RequestMethod()
    head = RequestMethod()
    patch = RequestMethod()

    # endregion

    # region Session Teardown

    def close(self):
        try:
            finalizer = self.__finalizer
        except AttributeError:
            pass  # This happens if an exception was raised in __init__
        else:
            if finalizer.detach():
                self.__close()

    def __close(self):
        """Close the session, if it exists"""
        with self._lock:
            if self.__session is not None:
                self.__session.close()
                self.__session = None

    def __del__(self):
        self.close()

    # endregion

    # region Internal Methods

    def __enter__(self) -> RequestsClient:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __getstate__(self) -> dict[str, Any]:
        # fmt: off
        keys = (
            'scheme', 'port', 'path_prefix', 'raise_errors', '_headers',
            'log_lvl', 'log_params', 'log_data', '_rate_limit',
        )
        # fmt: on
        self_dict = self.__dict__
        return {key: self_dict[key] for key in keys}

    def __setstate__(self, state: dict[str, Any]):
        rate_limit = state.pop('_rate_limit')
        self.__dict__.update(state)
        self._init(rate_limit)

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}[{self.url_for("")}]>'

    # endregion


class AuthClient(RequestsClient):
    def __init__(self, app_version: str = '2.8.1', *, ortega_uuid: str = None, use_cache: bool = True):
        headers = {
            'content-type': 'application/json; charset=UTF-8',
            'ortegaaccesstoken': '',
            'ortegaappversion': app_version,
            'ortegadevicetype': '2',
            'ortegauuid': ortega_uuid or str(uuid4()).replace('-', ''),
            'accept-encoding': 'gzip',
            'User-Agent': 'BestHTTP/2 v2.3.0',
            # 'User-Agent': 'UnityPlayer/2021.3.10f1 (UnityWebRequest/1.0, libcurl/7.80.0-DEV)',
            # 'X-Unity-Version': '2021.3.10f1',
        }
        super().__init__(AUTH_HOST, scheme='https', headers=headers)
        self.cache = FileCache('auth', use_cache=use_cache)

    @cached_property
    def _get_data_resp(self) -> Response:
        return self.post('api/auth/getDataUri', data=msgpack.packb({}))

    @cached_property
    def ortega_info(self) -> OrtegaInfo:
        """
        Example info::

            {
                'ortegastatuscode': '0',
                'orteganextaccesstoken': '',
                'ortegaassetversion': 'fd54f8ee7ec14a3f498fc7d31f7b4b1e1f5988fd',
                'ortegamasterversion': '1707981566144',
                'ortegautcnowtimestamp': '1708294191117',
            }
        """
        try:
            headers = self.cache.get('ortega-headers.json')
        except CacheMiss:
            headers = {k: v for k, v in self._get_data_resp.headers.items() if 'ortega' in k}
            self.cache.store(headers, 'ortega-headers.json')

        return OrtegaInfo(headers)

    @cached_property
    def game_data(self) -> GameData:
        try:
            game_data = self.cache.get('game-data.msgpack')
        except CacheMiss:
            self.cache.store(self._get_data_resp.content, 'game-data.msgpack', raw=True)
            game_data = msgpack.unpackb(self._get_data_resp.content, timestamp=3)

        return GameData(game_data)


class DataClient(RequestsClient):
    def __init__(self, auth_client: AuthClient = None, system: str = 'Android', use_cache: bool = True, **kwargs):
        self.system = system
        self.auth = auth_client or AuthClient(**kwargs)
        self.game_data = self.auth.game_data
        headers = {
            'content-type': 'application/json; charset=UTF-8',
            'accept-encoding': 'gzip',
            # 'User-Agent': 'BestHTTP/2 v2.3.0',
            'User-Agent': 'UnityPlayer/2021.3.10f1 (UnityWebRequest/1.0, libcurl/7.80.0-DEV)',
            'X-Unity-Version': '2021.3.10f1',
        }
        super().__init__(urlparse(self.game_data.asset_catalog_uri_fmt).hostname, scheme='https', headers=headers)
        self.cache = FileCache('data', use_cache=use_cache)

    def _get_asset(self, name: str) -> Response:
        url = self.game_data.asset_catalog_uri_fmt.format(f'{self.system}/{name}')
        return self.get(url, relative=False)

    def get_asset(self, name: str | Asset) -> bytes:
        # TODO: This is not currently working for any request other than the asset catalog
        if isinstance(name, Asset):
            name = name.name
        return self._get_asset(name).content

    # def get_asset_bundle(self, name: str) -> bytes:
    #     # This is incomplete / untested
    #     if not name.startswith('0#/'):
    #         raise ValueError(f'Invalid bundle {name=}')
    #     return self.get_asset(name[3:])

    # def get_asset_etag(self, name: str) -> str:
    #     url = self.game_data.asset_catalog_uri_fmt.format(f'{self.system}/{name}')
    #     return self.head(url, relative=False).headers['etag'].strip('"')

    def get_master(self, name: str):
        url = self.game_data.master_uri_fmt.format(self.auth.ortega_info.master_version, name)
        resp = self.get(url, relative=False)
        return msgpack.unpackb(resp.content, timestamp=3)

    @cached_property
    def master_catalog(self):
        """
        Example:
        {
            'MasterBookInfoMap': {
                'AchieveRankingRewardMB': {'Hash': 'fd9d21d514779c2e3758992907156420', 'Name': 'AchieveRankingRewardMB', 'Size': 47188},
                'ActiveSkillMB': {'Hash': 'ae15826e4bd042d14a61dad219c91932', 'Name': 'ActiveSkillMB', 'Size': 372286},
                ...
                'VipMB': {'Hash': 'be0114a5a24b5350459cdba6eea6bbcf', 'Name': 'VipMB', 'Size': 16293},
                'WorldGroupMB': {'Hash': '34afb2d419e8153a451d53b54d9829ae', 'Name': 'WorldGroupMB', 'Size': 20907}
            }
        }
        """
        try:
            catalog = self.cache.get('master-catalog.msgpack')
        except CacheMiss:
            catalog = self.get_master('master-catalog')
            self.cache.store(catalog, 'master-catalog.msgpack')

        return catalog

    @cached_property
    def asset_catalog(self) -> AssetCatalog:
        """
        Top-level keys:
            m_BucketDataString
            m_EntryDataString
            m_ExtraDataString
            m_InstanceProviderData
            m_InternalIdPrefixes
            m_InternalIds:              Asset bundles
            m_KeyDataString
            m_LocatorId
            m_ProviderIds
            m_ResourceProviderData
            m_SceneProviderData
            m_resourceTypes


        Example:
        {
            'm_LocatorId': 'AddressablesMainContentCatalog',
            'm_InstanceProviderData': {
                'm_Id': 'UnityEngine.ResourceManagement.ResourceProviders.InstanceProvider',
                'm_ObjectType': {'m_AssemblyName': 'Unity.ResourceManager, Version=0.0.0.0, Culture=neutral, PublicKeyToken=null', 'm_ClassName': 'UnityEngine.ResourceManagement.ResourceProviders.InstanceProvider'},
                'm_Data': ''
            },
            'm_SceneProviderData': {
                'm_Id': 'UnityEngine.ResourceManagement.ResourceProviders.SceneProvider',
                'm_ObjectType': {'m_AssemblyName': 'Unity.ResourceManager, Version=0.0.0.0, Culture=neutral, PublicKeyToken=null', 'm_ClassName': 'UnityEngine.ResourceManagement.ResourceProviders.SceneProvider'},
                'm_Data': ''
            },
            'm_ResourceProviderData': [
                {
                    'm_Id': 'Ortega.Common.OrtegaAssestBundleProvider',
                    'm_ObjectType': {'m_AssemblyName': 'Assembly-CSharp, Version=0.0.0.0, Culture=neutral, PublicKeyToken=null', 'm_ClassName': 'Ortega.Common.OrtegaAssestBundleProvider'},
                    'm_Data': ''
                },
                {
                    'm_Id': 'UnityEngine.ResourceManagement.ResourceProviders.BundledAssetProvider',
                    'm_ObjectType': {'m_AssemblyName': 'Unity.ResourceManager, Version=0.0.0.0, Culture=neutral, PublicKeyToken=null', 'm_ClassName': 'UnityEngine.ResourceManagement.ResourceProviders.BundledAssetProvider'},
                    'm_Data': ''
                },
                {
                    'm_Id': 'UnityEngine.ResourceManagement.ResourceProviders.BundledAssetProvider',
                    'm_ObjectType': {'m_AssemblyName': 'Unity.ResourceManager, Version=0.0.0.0, Culture=neutral, PublicKeyToken=null', 'm_ClassName': 'UnityEngine.ResourceManagement.ResourceProviders.BundledAssetProvider'},
                    'm_Data': ''
                },
                {
                    'm_Id': 'UnityEngine.ResourceManagement.ResourceProviders.AtlasSpriteProvider',
                    'm_ObjectType': {'m_AssemblyName': 'Unity.ResourceManager, Version=0.0.0.0, Culture=neutral, PublicKeyToken=null', 'm_ClassName': 'UnityEngine.ResourceManagement.ResourceProviders.AtlasSpriteProvider'},
                    'm_Data': ''
                }
            ],
            'm_ProviderIds': ['Ortega.Common.OrtegaAssestBundleProvider', 'UnityEngine.ResourceManagement.ResourceProviders.BundledAssetProvider'],
            'm_InternalIds': [
                '0#/0004aa460a958eb6464bec077ab56602.bundle',
                '0#/0009f326fb5c3ee00f92ba11c7b0e6c7.bundle',
                '0#/0009f9dbfd2fdbecf57794788e788960.bundle',
                ...

        """
        try:
            catalog = self.cache.get('asset-catalog.json')
        except CacheMiss:
            catalog = self._get_asset(f'{self.auth.ortega_info.asset_version}.json').json()
            self.cache.store(catalog, 'asset-catalog.json')

        return AssetCatalog(catalog)
