"""DNS Authenticator for the Flux ERP dns-01 API."""

import logging
from collections.abc import Callable

import requests
from certbot import errors
from certbot.plugins import dns_common
from certbot.plugins.dns_common import CredentialsConfiguration

logger = logging.getLogger(__name__)

TIMEOUT = 30


class Authenticator(dns_common.DNSAuthenticator):
    """DNS Authenticator that publishes challenges through the Flux dns-01 API.

    This Authenticator uses the dns-01 API of a Flux ERP instance to fulfill
    a dns-01 challenge. The API URL and token come from the credentials file.
    """

    description = "Obtain certificates using a DNS TXT record via the Flux ERP dns-01 API."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.credentials: CredentialsConfiguration | None = None

    @classmethod
    def add_parser_arguments(cls, add: Callable[..., None], default_propagation_seconds: int = 120):
        super().add_parser_arguments(add, default_propagation_seconds)
        add("credentials", help="Teamnifty credentials INI file.")

    def more_info(self) -> str:
        return (
            "This plugin configures a DNS TXT record to respond to a dns-01 challenge "
            "using the Flux ERP dns-01 API."
        )

    def _setup_credentials(self) -> None:
        self.credentials = self._configure_credentials(
            "credentials",
            "Teamnifty credentials INI file",
            {
                "api_url": "URL of the dns-01 API, e.g. https://flux.example.com/api/dns-01",
                "token": "API token for the dns-01 API",
            },
        )

    def _perform(self, domain: str, validation_name: str, validation: str) -> None:
        self._post("present", domain, validation_name, validation)

    def _cleanup(self, domain: str, validation_name: str, validation: str) -> None:
        # A failed cleanup must not fail an issuance that already succeeded.
        try:
            self._post("cleanup", domain, validation_name, validation)
        except errors.PluginError as e:
            logger.warning("Could not remove TXT record %s for %s: %s", validation_name, domain, e)

    def _post(self, action: str, domain: str, validation_name: str, validation: str) -> None:
        creds = self.credentials
        url = f"{creds.conf('api_url').rstrip('/')}/{action}"
        try:
            resp = requests.post(
                url,
                json={"fqdn": validation_name, "value": validation},
                headers={"Authorization": f"Bearer {creds.conf('token')}"},
                timeout=TIMEOUT,
            )
        except requests.RequestException as e:
            raise errors.PluginError(f"Error calling {action} for {domain}: {e}") from e

        if resp.ok:
            return
        try:
            body = resp.json()
            detail = body.get("message") or body.get("error")
        except (ValueError, AttributeError):
            detail = None
        raise errors.PluginError(
            f"Error calling {action} for {domain}: HTTP {resp.status_code}"
            + (f": {detail}" if detail else "")
        )
