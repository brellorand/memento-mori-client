"""
Memento Mori API Clients
"""

from __future__ import annotations

import logging
import re
from functools import cached_property
from threading import Lock
from typing import TYPE_CHECKING, Union, MutableMapping, Any, Mapping, Self
from urllib.parse import urlencode, urlparse
from uuid import uuid4
from weakref import finalize

import msgpack
from requests import Session, Response, HTTPError

from .config import ConfigFile, AccountConfig
from .data import GameData, OrtegaInfo
from .exceptions import CacheMiss, MissingClientKey, ApiResponseError
from .fs import FileCache, HTTPSaver, PathLike
from .utils import UrlPart, RequestMethod, format_path_prefix, rate_limited

if TYPE_CHECKING:
    from .typing import LoginResponse, GetServerHostResponse, LoginPlayerResponse, ErrorLogInfo

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
        shared_session: Bool = False,
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
        self._init(rate_limit, shared_session)

    def _init(self, rate_limit: float, shared_session: bool = False):
        # This method is separate from __init__ to allow RequestsClient objects to be pickleable - see __setstate__
        self._lock = Lock()
        self.__session = None
        self._rate_limit = rate_limit
        if not shared_session:
            self.__finalizer = finalize(self, self.__close)
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
            pass  # This happens if sharing a session, or if an exception was raised in __init__
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
        state = {key: self_dict[key] for key in keys}
        try:
            self.__finalizer
        except AttributeError:
            state['shared_session'] = True
        else:
            state['shared_session'] = False
        return state

    def __setstate__(self, state: dict[str, Any]):
        rate_limit = state.pop('_rate_limit')
        shared_session = state.pop('shared_session')
        self.__dict__.update(state)
        self._init(rate_limit, shared_session)

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}[{self.url_for("")}]>'

    # endregion


class AppVersionManager:
    """
    It appears that a different app version value may be expected for different platforms...

    In AppVersionMB:
    [
        {"Id": 1, "IsIgnore": null, "Memo": null, "DeviceType": 1, "AppVersion": "2.8.1"},
        {"Id": 2, "IsIgnore": null, "Memo": null, "DeviceType": 2, "AppVersion": "2.8.1"},
        {"Id": 3, "IsIgnore": null, "Memo": null, "DeviceType": 3, "AppVersion": "2.8.1"},
        {"Id": 4, "IsIgnore": null, "Memo": null, "DeviceType": 5, "AppVersion": "2.8.1"}
    ]

    In mementomori-helper, in MementoMori.Ortega/Share/Enums/DeviceType.cs, iOS is listed as 1, followed by
    Android (2, I assume), UnityEditor, Win64, DmmGames (5, I assume), Steam, Apk

    This class handles caching the latest known version to a local file, and retrieving the latest version from the
    Android Play store.
    """

    __slots__ = ('config',)

    def __init__(self, config: ConfigFile):
        self.config = config

    def _get_latest_version(self) -> str:
        log.debug('Retrieving latest app version from the Play store')
        with RequestsClient('play.google.com', scheme='https') as client:
            # Using this instead of a plain Session / the plain URL just for the request logging
            resp = client.get('store/apps/details', params={'id': 'jp.boi.mementomori.android'})
        # On 2024-03-01 there were 3 occurrences of the version number in the response, 2 of which had the following
        # format...  One (with this format) was in html, the other two were in js.  Maybe there's a better way, but
        # this was the easiest.
        return max(re.findall(r'【v(\d+\.\d+\.\d+)】', resp.text))

    def get_latest_version(self) -> str:
        latest_version = self._get_latest_version()
        self.set_version(latest_version)
        return latest_version

    def get_version(self) -> str:
        if version := self.config.auth.app_version:
            return version
        return self.get_latest_version()

    def set_version(self, app_version: str):
        self.config.auth.app_version = app_version
        self.config.auth.save()


class OrtegaClient(RequestsClient):
    __config: ConfigFile
    _http_saver: HTTPSaver = None

    def __init__(self, host: str, *, config: PathLike | ConfigFile = None, save_dir: PathLike = None, **kwargs):
        super().__init__(host, **kwargs)
        if config is not None:
            self.config = config
        if save_dir:
            self._http_saver = HTTPSaver(save_dir)

    @classmethod
    def child_client(cls, parent_client: OrtegaClient, host: str, **kwargs) -> Self:
        child = cls(host, config=parent_client.config, shared_session=True, **kwargs)
        child.session = parent_client.session
        if parent_client._http_saver:
            child._http_saver = parent_client._http_saver
        return child

    @property
    def config(self) -> ConfigFile:
        try:
            return self.__config
        except AttributeError:
            self.__config = ConfigFile()
            return self.__config

    @config.setter
    def config(self, value: PathLike | ConfigFile):
        self.__config = value if isinstance(value, ConfigFile) else ConfigFile(value)

    def _update_app_version(self):
        self.session.headers['ortegaappversion'] = self.config.app_version_manager.get_latest_version()

    def request(self, *args, **kwargs) -> Response:
        try:
            resp: Response = super().request(*args, **kwargs)
        except HTTPError as e:
            self._maybe_update_headers(e.response.headers)
            raise
        else:
            self._maybe_update_headers(resp.headers)
            return resp

    def _maybe_update_headers(self, headers: dict[str, str] | None):
        log.debug(f'Response {headers=}')  # TODO: This can probably be removed once confident in handling
        if headers and (next_token := headers.get('orteganextaccesstoken')):
            log.debug(f'Updating ortegaaccesstoken=>{next_token!r}')
            self.session.headers['ortegaaccesstoken'] = next_token

    def _post_msg(self, uri_path: str, to_pack, **kwargs):
        if self._http_saver:
            self._http_saver.save_request('POST', self.url_for(uri_path), self.session.headers, to_pack)

        resp = self.post(uri_path, data=msgpack.packb(to_pack), **kwargs)
        # 0=Timestamp, 1=float (Seconds from the EPOCH), 2=int (ns from the EPOCH), 3=datetime.datetime (UTC)
        data = msgpack.unpackb(resp.content, timestamp=3, strict_map_key=False)
        if self._http_saver:
            self._http_saver.save_response('POST', self.url_for(uri_path), resp.headers, resp.content)

        if (status_code := resp.headers.get('ortegastatuscode')) and status_code != '0':
            # TODO: If the error code in the resp body is 103 / CommonRequireClientUpdate, automatically update?
            raise ApiResponseError(resp, data)
        return data


class AuthClient(OrtegaClient):
    def __init__(
        self,
        *,
        app_version: str = None,
        ortega_uuid: str = None,
        use_cache: bool = True,
        config: PathLike | ConfigFile = None,
        **kwargs,
    ):
        self.config = config
        if app_version:
            self.config.app_version_manager.set_version(app_version)

        headers = {
            'content-type': 'application/json; charset=UTF-8',
            'ortegaaccesstoken': '',
            'ortegaappversion': self.config.app_version_manager.get_version(),
            'ortegadevicetype': '2',
            'ortegauuid': ortega_uuid or str(uuid4()).replace('-', ''),
            'accept-encoding': 'gzip',
            'User-Agent': 'BestHTTP/2 v2.3.0',
        }
        super().__init__(AUTH_HOST, scheme='https', path_prefix='api', headers=headers, **kwargs)
        self.cache = FileCache('auth', use_cache=use_cache)
        self.__made_first_req = False

    def _update_app_version(self):
        # Reset cached_property values
        for key in ('_get_data_resp', 'ortega_info', 'game_data'):
            try:
                del self.__dict__[key]
            except KeyError:
                pass

        super()._update_app_version()

    def _post_msg(self, uri_path: str, to_pack, **kwargs):
        if not self.__made_first_req:
            self._get_data_resp  # noqa  # Ensure the app version is up to date

        return super()._post_msg(uri_path, to_pack, **kwargs)

    def request(self, *args, **kwargs) -> Response:
        resp: Response = super().request(*args, **kwargs)
        self.__made_first_req = True
        return resp

    # region getDataUri

    @cached_property
    def _get_data_resp(self) -> Response:
        # This request technically supports the following fields: CountryCode (str), UserId (long)
        # This request may be made during maintenance
        return self.post('auth/getDataUri', data=msgpack.packb({}))

    @cached_property
    def ortega_info(self) -> OrtegaInfo:
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
            game_data = self._get_game_data()

        if game_data.get('ErrorCode') == 103:  # app_version was out of date
            # {"ErrorCode": 103, "Message": "", "ErrorHandlingType": 0, "ErrorMessageId": 0, "MessageParams": null}
            self._update_app_version()
            game_data = self._get_game_data()

        return GameData(game_data)

    def _get_game_data(self):
        self.cache.store(self._get_data_resp.content, 'game-data.msgpack', raw=True)
        return msgpack.unpackb(self._get_data_resp.content, timestamp=3)

    # endregion

    # region Get Client Key

    def get_client_key(self, account: AccountConfig, password: str) -> str:
        """
        Retrieve a reusable client key that may be stored and reused instead of storing the account password.

        :param account: The Account object for which a client key should be obtained
        :param password: The account's password
        :return: The client key value
        """
        create_resp = self._create_user()
        log.debug(f'Create user response={create_resp!r}')
        cb_user_data = self._comeback_user_data(account.user_id, password, create_resp['UserId'])
        log.debug(f'Get comeback user data response={cb_user_data!r}')
        cb_resp = self._comeback_user(account.user_id, create_resp['UserId'], cb_user_data['OneTimeToken'])
        log.debug(f'Get comeback user response={cb_resp!r}')
        return cb_resp['ClientKey']

    def _create_user(self):
        # This request may NOT be made during maintenance
        auth_config = self.config.auth
        data = {
            'AdverisementId': str(uuid4()),  # noqa  # Typo is intentional
            'AppVersion': self.config.app_version_manager.get_version(),
            'CountryCode': auth_config.locale.country_code,
            'DeviceToken': '',
            'ModelName': auth_config.model_name,
            'DisplayLanguage': auth_config.locale.num,
            'OSVersion': auth_config.os_version,
            'SteamTicket': '',
            # TODO: 'AuthToken': ??? (maybe changes in every client version?)
        }
        log.debug(f'Sending createUser request with {data=}')
        return self._post_msg('auth/createUser', data)

    def _comeback_user_data(self, user_id: int, password: str, create_resp_id: int, ):
        # This request may be made during maintenance
        # From helper: public enum SnsType {None, OrtegaId, AppleId, Twitter, Facebook, GameCenter, GooglePlay}
        data = {
            'FromUserId': create_resp_id,
            'Password': password,
            'SnsType': 1,  # SnsType.OrtegaId
            'UserId': user_id,
        }
        return self._post_msg('auth/getComebackUserData', data)

    def _comeback_user(self, user_id: int, create_resp_id: int, token: str):
        # This request may be made during maintenance
        data = {'FromUserId': create_resp_id, 'OneTimeToken': token, 'ToUserId': user_id}
        log.debug(f'Sending comebackUser request with {data=}')
        return self._post_msg('auth/comebackUser', data)

    # endregion

    def login(self, account: AccountConfig) -> LoginResponse:
        """
        Login to the specified account (not a world).

        Note: the helper's logout method only de-registers locally scheduled jobs - no explicit logout appears to be
        necessary.
        """
        # This request may be made during maintenance
        if not account.client_key:
            raise MissingClientKey(f'A password is required for {account}')

        auth_config = self.config.auth
        data = {
            'ClientKey': account.client_key,
            'DeviceToken': '',
            'AppVersion': self.config.app_version_manager.get_version(),
            'OSVersion': auth_config.os_version,
            'ModelName': auth_config.model_name,
            'AdverisementId': str(uuid4()),  # noqa  # Typo is intentional
            'UserId': account.user_id,
        }
        return self._post_msg('auth/login', data)

    def get_server_host(self, world_id: int) -> GetServerHostResponse:
        # This request requires prior login, and may NOT be made during maintenance
        return self._post_msg('auth/getServerHost', {'WorldId': world_id})


class ApiClient(OrtegaClient):
    """
    API client for making requests specific to a logged in player + world.

    Only one specific request method is defined here since it doesn't require prior world login.  Methods for requests
    that require login are defined in :class:`~.WorldSession`
    """

    def post_msg(self, uri_path: str, to_pack, **kwargs):
        return self._post_msg(uri_path, to_pack, **kwargs)

    def login_player(
        self, player_id: int, password: str, error_log_info: list[ErrorLogInfo] = None
    ) -> LoginPlayerResponse:
        # This request does not need prior login, and may be made during maintenance
        data = {'Password': password, 'PlayerId': player_id, 'ErrorLogInfoList': error_log_info or []}
        return self._post_msg('user/loginPlayer', data)


class DataClientWrapper:
    def __init__(self, auth_client: AuthClient = None, *, use_data_cache: bool = True, **kwargs):
        self._auth_client = auth_client
        self._data_client_kwargs = kwargs
        self.cache = FileCache('data', use_cache=use_data_cache)

    @cached_property
    def _data_client(self) -> DataClient:
        # This allows the client to be initialized lazily, only if there is a cache miss
        return DataClient(self._auth_client, **self._data_client_kwargs)

    def get_asset(self, name: str) -> bytes:
        """
        Download the asset catalog, or an asset bundle file.

        From the catalog, only ``.bundle`` entries in ``m_InternalIds`` that begin with ``0#/`` may be requested via
        this method.

        :param name: The name of the file/bundle to download
        :return: The content of the specified file
        """
        return self._data_client.get_asset(name).content

    def get_mb_data(self, name: str):
        return self._data_client.get_mb_data(name)

    def get_raw_data(self, name: str):
        return self._data_client.get_raw_data(name)

    def _get_asset_catalog(self):
        try:
            return self.cache.get('asset-catalog.json')
        except CacheMiss:
            pass

        asset_version = self._data_client.auth.ortega_info.asset_version
        if not self.cache.use_cache or asset_version != self.cache.get('asset-version.txt', None, ignore_age=True):
            return self._get_new_asset_catalog(asset_version)

        if self.cache.touch('asset-catalog.json'):  # This marks the cached data as still fresh
            try:
                return self.cache.get('asset-catalog.json')
            except CacheMiss:  # Technically, it may still fail to be loaded for some reason
                pass

        return self._get_new_asset_catalog(asset_version)

    def _get_new_asset_catalog(self, asset_version: str):
        catalog = self._data_client.get_asset(f'{asset_version}.json').json()
        self.cache.store(catalog, 'asset-catalog.json')
        self.cache.store(asset_version, 'asset-version.txt')
        return catalog

    def _get_mb_catalog(self):
        try:
            return self.cache.get('master-catalog.msgpack')
        except CacheMiss:
            catalog = self._data_client.get_mb_data('master-catalog')
            self.cache.store(catalog, 'master-catalog.msgpack')
            return catalog


class DataClient(RequestsClient):
    def __init__(self, auth_client: AuthClient = None, *, system: str = 'Android', **kwargs):
        self.system = system
        self.auth = auth_client or AuthClient(**kwargs)
        self.game_data = self.auth.game_data
        headers = {
            'content-type': 'application/json; charset=UTF-8',
            'accept-encoding': 'gzip',
            'User-Agent': 'UnityPlayer/2021.3.10f1 (UnityWebRequest/1.0, libcurl/7.80.0-DEV)',
            'X-Unity-Version': '2021.3.10f1',
        }
        super().__init__(urlparse(self.game_data.asset_catalog_uri_fmt).hostname, scheme='https', headers=headers)

    def get_asset(self, name: str) -> Response:
        url = self.game_data.asset_catalog_uri_fmt.format(f'{self.system}/{name}')
        return self.get(url, relative=False)

    # def get_asset_etag(self, name: str) -> str:
    #     url = self.game_data.asset_catalog_uri_fmt.format(f'{self.system}/{name}')
    #     return self.head(url, relative=False).headers['etag'].strip('"')

    def get_mb_data(self, name: str):
        url = self.game_data.mb_uri_fmt.format(self.auth.ortega_info.mb_version, name)
        resp = self.get(url, relative=False)
        return msgpack.unpackb(resp.content, timestamp=3)

    def get_raw_data(self, name: str):
        url = self.game_data.raw_data_uri_fmt.format(name)
        resp = self.get(url, relative=False)
        return resp.content
