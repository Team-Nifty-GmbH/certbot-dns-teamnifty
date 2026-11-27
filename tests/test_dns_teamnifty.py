import unittest
from unittest import mock

import pytest
import requests
from certbot import errors
from certbot.plugins import dns_test_common
from certbot.plugins.dns_test_common import DOMAIN

from certbot_dns_teamnifty._internal.dns_teamnifty import Authenticator

API_URL = "https://flux.example.com/api/dns-01"
TOKEN = "t"
NAME = "_acme-challenge.example.com"
VALUE = "x"


def make_auth(tmp_path, api_url=API_URL, token=TOKEN):
    lines = []
    if api_url is not None:
        lines.append(f"dns_teamnifty_api_url = {api_url}")
    if token is not None:
        lines.append(f"dns_teamnifty_token = {token}")
    path = tmp_path / "credentials.ini"
    path.write_text("\n".join(lines) + "\n")
    path.chmod(0o600)
    config = mock.MagicMock(
        dns_teamnifty_credentials=str(path),
        dns_teamnifty_propagation_seconds=0,
    )
    auth = Authenticator(config, "dns-teamnifty")
    auth._setup_credentials()
    return auth


def response(status=200, body=None):
    resp = mock.Mock(spec=requests.Response)
    resp.status_code = status
    resp.ok = status < 400
    resp.json.return_value = body if body is not None else {}
    return resp


def test_perform_posts_present(tmp_path):
    auth = make_auth(tmp_path)
    with mock.patch("requests.post", return_value=response()) as post:
        auth._perform(DOMAIN, NAME, VALUE)
    post.assert_called_once_with(
        f"{API_URL}/present",
        json={"fqdn": NAME, "value": VALUE},
        headers={"Authorization": "Bearer t"},
        timeout=30,
    )


def test_cleanup_posts_cleanup(tmp_path):
    auth = make_auth(tmp_path)
    with mock.patch("requests.post", return_value=response()) as post:
        auth._cleanup(DOMAIN, NAME, VALUE)
    post.assert_called_once_with(
        f"{API_URL}/cleanup",
        json={"fqdn": NAME, "value": VALUE},
        headers={"Authorization": "Bearer t"},
        timeout=30,
    )


def test_trailing_slash_in_api_url(tmp_path):
    auth = make_auth(tmp_path, api_url=API_URL + "/")
    with mock.patch("requests.post", return_value=response()) as post:
        auth._perform(DOMAIN, NAME, VALUE)
    assert post.call_args.args[0] == f"{API_URL}/present"


def test_error_is_plugin_error_with_server_message(tmp_path):
    auth = make_auth(tmp_path)
    body = {"error": "forbidden", "message": "Token may not manage this domain"}
    with mock.patch("requests.post", return_value=response(403, body)):
        with pytest.raises(errors.PluginError) as exc:
            auth._perform(DOMAIN, NAME, VALUE)
    text = str(exc.value)
    assert DOMAIN in text
    assert "Token may not manage this domain" in text
    assert "403" in text


def test_error_without_json_body_still_plugin_error(tmp_path):
    auth = make_auth(tmp_path)
    resp = response(502)
    resp.json.side_effect = ValueError
    with mock.patch("requests.post", return_value=resp):
        with pytest.raises(errors.PluginError) as exc:
            auth._perform(DOMAIN, NAME, VALUE)
    assert "502" in str(exc.value)


def test_network_error_is_plugin_error(tmp_path):
    auth = make_auth(tmp_path)
    with mock.patch("requests.post", side_effect=requests.ConnectionError("boom")):
        with pytest.raises(errors.PluginError) as exc:
            auth._perform(DOMAIN, NAME, VALUE)
    assert DOMAIN in str(exc.value)


def test_cleanup_failure_only_logs(tmp_path, caplog):
    auth = make_auth(tmp_path)
    with mock.patch("requests.post", return_value=response(502, {"error": "upstream"})):
        auth._cleanup(DOMAIN, NAME, VALUE)
    with mock.patch("requests.post", side_effect=requests.ConnectionError("boom")):
        auth._cleanup(DOMAIN, NAME, VALUE)
    assert "Could not remove" in caplog.text


@pytest.mark.parametrize("missing", ["api_url", "token"])
def test_missing_credentials_rejected(tmp_path, missing):
    with pytest.raises(errors.PluginError):
        make_auth(tmp_path, **{missing: None})


def test_default_propagation_seconds_is_120():
    add = mock.MagicMock()
    Authenticator.add_parser_arguments(add)
    add.assert_any_call("propagation-seconds", type=int, default=120, help=mock.ANY)


class TestBase(dns_test_common.BaseAuthenticatorTest, unittest.TestCase):
    def setUp(self):
        self.auth = Authenticator(mock.MagicMock(), "dns-teamnifty")
