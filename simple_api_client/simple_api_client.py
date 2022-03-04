import requests
import json
import base64

from cookie_manager.cookie_manager import CookieManager
from logging import Logger
from requests.adapters import HTTPAdapter
from typing import Any, List, Dict, Optional, Iterator
from urllib.parse import urlparse
from urllib3.util.retry import Retry
from werkzeug import exceptions


class ApiResponse:
    def __init__(self, response: requests.Response):
        """
        Create a response object that deals with bad data from the API.
        :param response: A standard requests response object.
        """
        self.status_code = response.status_code
        self.bytes = response.content

        try:
            self.data = response.json()
            if self.data is None:
                raise ValueError
        except ValueError:
            self.data = {}

        if self.status_code != 200:
            error = self.data.get("error")
            if not error:
                error = self.data.get("message", response.reason)
                if not error:
                    error = "Unknown error"
            self.data["error"] = error

    def get(self, *args, **kwargs) -> Any:
        """
        Delegate get calls to the actual response data.
        """
        return self.data.get(*args, **kwargs)

    def __str__(self) -> str:
        """
        Return the string representation.
        """
        return f"Response: {self.status_code}, {self.data}"


class ApiClientHostError(Exception):
    """
    Raised when the host has a bad format.
    """

    pass


class ApiClientPathError(Exception):
    """
    Raised when a path has a bad format.
    """

    pass


class ApiClient:
    def __init__(
        self,
        host: str,
        logger: Logger,
        timeout: int = 30,
        retry_attempts: int = 0,
        retry_backoff_factor: float = 0.1,
        retry_on_status: List[int] = [429, 500, 502, 503, 504],
    ):
        """
        Initialise a new api client.
        :param host: The host of the api.
        :param logger: A logger.
        :param timeout: A timeout specified in seconds.
        :param retry_attempts: The amount of times to attempt to retry.
        :param retry_backoff_factor: A multipler to increase the time between retries by.
        :param retry_on_status: Retry on encountering these status codes.
        :raises: ApiClientHostError: If the host contains a path.
        """
        self._set_host(host)
        self._logger: Logger = logger
        self._timeout: int = timeout
        self._retry_attempts: int = retry_attempts
        self._retry_backoff_factor: float = retry_backoff_factor
        self._retry_on_status: List[int] = retry_on_status
        self._headers = {}
        self._cookies = {}

    def add_header(self, name: str, value: str) -> None:
        """
        Set a global header to be added to all requests.
        :param name: The name of the header
        :param value: The value of the header.
        """
        self._headers[name] = value

    def remove_header(self, name: str) -> None:
        """
        Remove a global header to be removed from all requests.
        :param name: The name of the header
        """
        self._headers.pop(name, None)

    def set_basic_auth(self, username: str, password: str) -> None:
        """
        Add a header to support basic auth.
        :param username: The username to use.
        :param password: The password to use.
        """
        bytes = f"{username}:{password}".encode("ascii")
        encoded = base64.b64encode(bytes).decode("utf-8")

        self.add_header("Authorization", f"Basic {encoded}")

    def set_token_auth(self, token: str) -> None:
        """
        Add a header to support basic auth.
        :param token: The token to use.
        """
        self.add_header("Authorization", f"Bearer {token}")

    def add_cookie(self, name: str, payload: str) -> None:
        """
        Set a global cookie to be added to all requests.
        :param name: The name of the cookie
        :param value: The payload of the cookie.
        """
        self._cookies[name] = payload

    def remove_cookie(self, name: str) -> None:
        """
        Remove a global cookie to be removed from all requests.
        :param name: The name of the cookie
        """
        self._cookies.pop(name, None)

    def add_signed_cookie(
        self, name: str, payload: Dict, signing_key_id: str, signing_key: str
    ) -> None:
        """
        :param name: The name of the cookie.
        :param payload: The payload of the cookie.
        :param signing_key_id: The internal key id of the signing key, also sent as part of the payload so the receiver knows which key was used for signing.
        :param signing_key: The actual key used to sign the cookie.
        """
        keys = {signing_key_id: signing_key}

        cookie_manager = CookieManager(
            keys=keys, exceptions=exceptions, logger=self._logger
        )

        payload = cookie_manager.sign(cookie=payload, key_id=signing_key_id)
        self.add_cookie(name, payload)

    def get(
        self,
        path: str,
        retry_attempts: Optional[int] = None,
        retry_backoff_factor: Optional[float] = None,
        retry_on_status: Optional[List[int]] = None,
        verify=True,
    ) -> ApiResponse:
        """
        Send a GET request to the API
        :param path: The API path to hit
        :param retry_attempts: The amount of times to attempt to retry.
        :param retry_backoff_factor: A multipler to increase the time between retries by.
        :param retry_on_status: Retry on encountering these status codes.
        :return: The response converted from Json to a dict
        :raises: ApiClientPathError: If the path doesn't start with a forward-slash.
        """
        full_url = self._create_full_url(path)
        headers = self._headers
        headers["Accept"] = "application/json"

        self._logger.debug(f"GET: {full_url}")
        self._logger.debug(f"Headers: {headers}")
        self._logger.debug(f"Cookies: {self._cookies}")
        self._logger.debug(f"Timeout: {self._timeout}")

        with self._create_session(
            retry_attempts, retry_backoff_factor, retry_on_status
        ) as session:
            response = session.get(
                full_url,
                headers=headers,
                cookies=self._cookies,
                timeout=self._timeout,
                verify=verify,
            )

        return self._handle_response(response)

    def get_binary(
        self,
        path: str,
        retry_attempts: Optional[int] = None,
        retry_backoff_factor: Optional[float] = None,
        retry_on_status: Optional[List[int]] = None,
    ) -> ApiResponse:
        """
        Send a GET request to the API and expect a binary object back
        :param path: The API path to hit
        :param retry_attempts: The amount of times to attempt to retry.
        :param retry_backoff_factor: A multipler to increase the time between retries by.
        :param retry_on_status: Retry on encountering these status codes.
        :return: The response is a binary object
        :raises: ApiClientPathError: If the path doesn't start with a forward-slash.
        """
        full_url = self._create_full_url(path)
        headers = self._headers
        headers["Accept"] = "application/octet-stream"

        self._logger.debug(f"GET (binary): {full_url}")
        self._logger.debug(f"Headers: {headers}")
        self._logger.debug(f"Cookies: {self._cookies}")
        self._logger.debug(f"Timeout: {self._timeout}")

        with self._create_session(
            retry_attempts, retry_backoff_factor, retry_on_status
        ) as session:
            response = session.get(
                full_url, headers=headers, cookies=self._cookies, timeout=self._timeout
            )

        return self._handle_response(response)

    def post(
        self,
        path: str,
        json: Optional[Dict] = None,
        data: Optional[Dict] = None,
        retry_attempts: Optional[int] = None,
        retry_backoff_factor: Optional[float] = None,
        retry_on_status: Optional[List[int]] = None,
    ) -> ApiResponse:
        """
        Send a POST request to the API.
        :param path: The API path to hit.
        :param json: Json encoded data to send to the path.
        :param data: Form encoded data to send to the path.
        :param retry_attempts: The amount of times to attempt to retry.
        :param retry_backoff_factor: A multipler to increase the time between retries by.
        :param retry_on_status: Retry on encountering these status codes.
        :return: The response as a dict.
        :raises: ApiClientPathError: If the path doesn't start with a forward-slash.
        """
        full_url = self._create_full_url(path)
        headers = self._headers
        headers["Accept"] = "application/json"

        if data:
            headers["Content-Type"] = "application/x-www-form-urlencoded"

        if json:
            headers["Content-Type"] = "application/json"

        self._logger.debug(f"POST: {full_url}")
        self._logger.debug(f"Headers: {headers}")
        self._logger.debug(f"Cookies: {self._cookies}")
        self._logger.debug(f"Timeout: {self._timeout}")
        self._logger.debug(f"Data: {data}")

        with self._create_session(
            retry_attempts, retry_backoff_factor, retry_on_status
        ) as session:
            response = session.post(
                full_url,
                headers=headers,
                cookies=self._cookies,
                timeout=self._timeout,
                json=json,
                data=data,
            )

        return self._handle_response(response)

    def delete(
        self,
        path: str,
        retry_attempts: Optional[int] = None,
        retry_backoff_factor: Optional[float] = None,
        retry_on_status: Optional[List[int]] = None,
    ) -> ApiResponse:
        """
        Send a DELETE request to the API.
        :param path: The API path to hit.
        :param retry_attempts: The amount of times to attempt to retry.
        :param retry_backoff_factor: A multipler to increase the time between retries by.
        :param retry_on_status: Retry on encountering these status codes.
        :return: The response as a dict.
        :raises: ApiClientPathError: If the path doesn't start with a forward-slash.
        """
        full_url = self._create_full_url(path)
        headers = self._headers
        headers["Accept"] = "application/json"

        self._logger.debug(f"DELETE: {full_url}")
        self._logger.debug(f"Headers: {headers}")
        self._logger.debug(f"Cookies: {self._cookies}")
        self._logger.debug(f"Timeout: {self._timeout}")

        with self._create_session(
            retry_attempts, retry_backoff_factor, retry_on_status
        ) as session:
            response = session.delete(
                full_url, headers=headers, cookies=self._cookies, timeout=self._timeout
            )

        return self._handle_response(response)

    def _set_host(self, host: str) -> None:
        """
        Set a correct base host for the client.
        :param host: The host to set.
        :raises: ApiClientHostError: If the host contains a path.
        """
        url = urlparse(host)
        if url.path:
            raise ApiClientHostError("No path should be specified on the host")
        self._host = f"{url.scheme}://{url.netloc}"

    def _create_full_url(self, path) -> str:
        """
        Create and return the full url based on the passed path.
        :param path: The path to append to the host.
        :return: The full url.
        :raises: ApiClientPathError: If the path doesn't start with a forward-slash.
        """
        if path[0] != "/":
            raise ApiClientPathError("Path needs to start with a forward-slash")
        return f"{self._host}{path}"

    def _create_session(
        self,
        retry_attempts: Optional[int] = None,
        retry_backoff_factor: Optional[float] = None,
        retry_on_status: Optional[List[int]] = None,
    ) -> requests.Session:
        """
        Create a new request session.
        :param retry_attempts: The amount of times to attempt to retry.
        :param retry_backoff_factor: A multipler to increase the time between retries by.
        :param retry_on_status: Retry on encountering these status codes.
        :return: A requests session object.
        """
        retry_attempts = retry_attempts or self._retry_attempts
        retry_backoff_factor = retry_backoff_factor or self._retry_backoff_factor
        retry_on_status = retry_on_status or self._retry_on_status

        retries = Retry(
            total=retry_attempts,
            backoff_factor=retry_backoff_factor,
            status_forcelist=retry_on_status,
            raise_on_status=False,
        )

        session = requests.Session()
        session.mount("https://", HTTPAdapter(max_retries=retries))
        session.mount("http://", HTTPAdapter(max_retries=retries))
        return session

    def _handle_response(self, response: requests.Response) -> ApiResponse:
        """
        Handle the response of a request by checking for rate limiting and
        returning a cleaned up response
        :param response: A standard requests response.
        """
        self._check_for_rate_limit(response)

        response = ApiResponse(response)
        self._logger.debug(response)

        return response

    def _check_for_rate_limit(self, response: requests.Response) -> None:
        """
        Check the passed response for rate limiting.
        :param response: A standard requests response.
        :raises: TooManyRequests: If rate limiting is detected.
        """
        if response.status_code == 429:
            message = response.json().get("message", "Rate limit exceeded")
            message = f"External API rate limit: {message}"
            self._logger.warning(message)
            raise exceptions.TooManyRequests(description=message)
