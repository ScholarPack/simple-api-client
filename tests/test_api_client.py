import mock
import pytest
import requests

from freezegun import freeze_time
from logging import Logger
from simple_api_client import ApiClient, ApiResponse
from urllib3.util.retry import Retry
from werkzeug.exceptions import TooManyRequests


class TestApiClient:
    def test_instantiation(self):
        logger = Logger("test", level="DEBUG")
        client = ApiClient("http://www.example.com", logger)

        assert client._host == "http://www.example.com"
        assert client._logger == logger

        assert client._timeout == 30
        assert client._retry_attempts == 0
        assert client._retry_backoff_factor == 0.1
        assert client._retry_on_status == [429, 500, 502, 503, 504]

        assert client._headers == {}
        assert client._cookies == {}

    def test_adding_and_removing_headers(self):
        client = ApiClient("http://www.example.com", Logger("test", level="DEBUG"))
        assert client._headers == {}

        client.add_header("Accept", "application/json")
        client.add_header("Content-Type", "application/json")
        assert client._headers == {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        client.remove_header("Accept")
        client.remove_header("Authorization")
        assert client._headers == {"Content-Type": "application/json"}

    def test_adding_basic_auth(self):
        client = ApiClient("http://www.example.com", Logger("test", level="DEBUG"))
        assert client._headers == {}

        client.set_basic_auth("username", "password")
        assert client._headers == {"Authorization": "Basic dXNlcm5hbWU6cGFzc3dvcmQ="}

    def test_adding_token_auth(self):
        client = ApiClient("http://www.example.com", Logger("test", level="DEBUG"))
        assert client._headers == {}

        client.set_token_auth("ka5ud5455&y&a&e£u£334ee4rka5y&a&e£u£334ud5455&y&£")
        assert client._headers == {
            "Authorization": "Bearer ka5ud5455&y&a&e£u£334ee4rka5y&a&e£u£334ud5455&y&£"
        }

    def test_adding_and_removing_cookies(self):
        client = ApiClient("http://www.example.com", Logger("test", level="DEBUG"))
        assert client._cookies == {}

        client.add_cookie("cookie_name", "cookie_payload")
        assert client._cookies == {"cookie_name": "cookie_payload"}

        client.remove_cookie("cookie_name")
        client.remove_cookie("missing_cookie_name")
        assert client._cookies == {}

    @freeze_time("2020-04-09")
    def test_adding_and_signed_cookie(self):
        client = ApiClient("http://www.example.com", Logger("test", level="DEBUG"))
        assert client._cookies == {}

        cookie_name = "client-details"
        cookie_payload = {"uuid": "19d66a3e-cf98-4d68-8b9a-1df2a40b067f"}
        cookie_signing_key_id = "service1>service2"
        cookie_signing_key = "ka5ud5455&y&a&e£u£334ee4rka5y&a&e£u£334ud5455&y&£"

        client.add_signed_cookie(
            cookie_name, cookie_payload, cookie_signing_key_id, cookie_signing_key
        )
        assert client._cookies == {
            "client-details": '{"uuid": "19d66a3e-cf98-4d68-8b9a-1df2a40b067f", "key_id": "service1>service2"}.Xo5lgA.i3C_q5NExD1dUc42-jyrv-vcFsc'
        }

    def test_creating_a_default_session(self):
        logger = Logger("test", level="DEBUG")
        client = ApiClient("http://www.example.com", logger)

        session = client._create_session()

        assert session.adapters.get("http://").max_retries.total == 0
        assert session.adapters.get("http://").max_retries.backoff_factor == 0.1
        assert session.adapters.get("http://").max_retries.status_forcelist == [
            429,
            500,
            502,
            503,
            504,
        ]

        assert session.adapters.get("https://").max_retries.total == 0
        assert session.adapters.get("https://").max_retries.backoff_factor == 0.1
        assert session.adapters.get("https://").max_retries.status_forcelist == [
            429,
            500,
            502,
            503,
            504,
        ]

    def test_creating_a_custom_session(self):
        logger = Logger("test", level="DEBUG")
        client = ApiClient("http://www.example.com", logger)

        session = client._create_session(3, 0.2, [500])

        assert session.adapters.get("http://").max_retries.total == 3
        assert session.adapters.get("http://").max_retries.backoff_factor == 0.2
        assert session.adapters.get("http://").max_retries.status_forcelist == [500]

        assert session.adapters.get("https://").max_retries.total == 3
        assert session.adapters.get("https://").max_retries.backoff_factor == 0.2
        assert session.adapters.get("https://").max_retries.status_forcelist == [500]

    @mock.patch("requests.Session.get")
    @mock.patch("simple_api_client.ApiClient._create_session")
    def test_making_a_get_request(self, create_session_method, requests_get_method):
        create_session_method.return_value = requests.Session()

        client = ApiClient("http://www.example.com", Logger("test", level="DEBUG"))
        response = client.get(
            "/unknown",
            retry_attempts=3,
            retry_backoff_factor=0.2,
            retry_on_status=[429],
        )

        create_session_method.assert_called_with(3, 0.2, [429])
        requests_get_method.assert_called_with(
            "http://www.example.com/unknown",
            headers={"Accept": "application/json"},
            cookies={},
            timeout=30,
        )

    @mock.patch("requests.Session.get")
    @mock.patch("simple_api_client.ApiClient._create_session")
    def test_making_a_get_binary_request(
        self, create_session_method, requests_get_method
    ):
        create_session_method.return_value = requests.Session()

        client = ApiClient("http://www.example.com", Logger("test", level="DEBUG"))
        response = client.get_binary(
            "/unknown",
            retry_attempts=2,
            retry_backoff_factor=0.1,
            retry_on_status=[500],
        )

        create_session_method.assert_called_with(2, 0.1, [500])
        requests_get_method.assert_called_with(
            "http://www.example.com/unknown",
            headers={"Accept": "application/octet-stream"},
            cookies={},
            timeout=30,
        )

    @mock.patch("requests.Session.post")
    @mock.patch("simple_api_client.ApiClient._create_session")
    def test_making_a_post_request(self, create_session_method, requests_post_method):
        create_session_method.return_value = requests.Session()

        client = ApiClient("http://www.example.com", Logger("test", level="DEBUG"))
        response = client.post(
            "/unknown",
            {"foo": "bar"},
            retry_attempts=1,
            retry_backoff_factor=0.3,
            retry_on_status=[501],
        )

        create_session_method.assert_called_with(1, 0.3, [501])
        requests_post_method.assert_called_with(
            "http://www.example.com/unknown",
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            cookies={},
            timeout=30,
            json={"foo": "bar"},
            data=None,
        )

    @mock.patch("requests.Session.get")
    def test_making_a_rate_limited_get_request(self, requests_get_method):
        requests_get_method.return_value = type(
            "fake_request",
            (),
            {"json": lambda: {"message": "10 per second"}, "status_code": 429},
        )

        client = ApiClient("http://www.example.com", Logger("test", level="DEBUG"))

        with pytest.raises(TooManyRequests) as ex:
            response = client.get("/unknown")
            assert ex.description == "External API rate limit: 10 per second"


class TestApiClientReponse:
    def test_good_data(self):
        mock_reponse = type(
            "mock_reponse",
            (),
            {
                "status_code": 200,
                "content": b"bytes",
                "json": lambda: {"key": "value"},
                "reason": None,
            },
        )

        response = ApiResponse(mock_reponse)

        assert response.status_code == 200
        assert response.bytes == b"bytes"
        assert response.data == {"key": "value"}

    def test_bad_data_using_error(self):
        mock_reponse = type(
            "mock_reponse",
            (),
            {
                "status_code": 500,
                "content": b"bytes",
                "json": lambda: {"error": "Something went wrong"},
                "reason": None,
            },
        )

        response = ApiResponse(mock_reponse)

        assert response.status_code == 500
        assert response.bytes == b"bytes"
        assert response.data == {"error": "Something went wrong"}

    def test_bad_data_using_message(self):
        mock_reponse = type(
            "mock_reponse",
            (),
            {
                "status_code": 500,
                "content": b"bytes",
                "json": lambda: {"message": "Something went wrong"},
                "reason": None,
            },
        )

        response = ApiResponse(mock_reponse)

        assert response.status_code == 500
        assert response.bytes == b"bytes"
        assert response.data == {
            "error": "Something went wrong",
            "message": "Something went wrong",
        }

    def test_bad_data_using_reason(self):
        mock_reponse = type(
            "mock_reponse",
            (),
            {
                "status_code": 500,
                "content": b"bytes",
                "json": lambda: None,
                "reason": "Something went wrong",
            },
        )

        response = ApiResponse(mock_reponse)

        assert response.status_code == 500
        assert response.bytes == b"bytes"
        assert response.data == {"error": "Something went wrong"}

    def test_bad_data_using_default(self):
        mock_reponse = type(
            "mock_reponse",
            (),
            {
                "status_code": 500,
                "content": b"bytes",
                "json": lambda: None,
                "reason": None,
            },
        )

        response = ApiResponse(mock_reponse)

        assert response.status_code == 500
        assert response.bytes == b"bytes"
        assert response.data == {"error": "Unknown error"}
