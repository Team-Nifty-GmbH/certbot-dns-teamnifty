# certbot-dns-teamnifty

Certbot DNS-01 authenticator plugin for Flux ERP. It publishes the ACME
challenge through the `dns-01` API of a Flux ERP instance and removes it again
after the certificate has been issued. It also works for wildcard certificates.

Besides the plugin, this repository documents how to use the same API with
[lego](#lego) and [acme.sh](#acmesh).

## Installation

```sh
pip install certbot-dns-teamnifty
```

The plugin is published on PyPI only. It cannot be loaded by the certbot snap
(the snap's Python is read-only and `trust-plugin-with-root` only applies to
plugin snaps), so use certbot installed with pip, for example in a venv:

```sh
python3 -m venv /opt/certbot
/opt/certbot/bin/pip install certbot certbot-dns-teamnifty
```

Check that certbot sees the plugin:

```sh
certbot plugins
```

## Credentials

Create an API token for dns-01 in your Flux portal. It shows you the API URL
and the token. Put both into an INI file and make it readable only by you:

```ini
# /etc/letsencrypt/teamnifty.ini
dns_teamnifty_api_url = https://flux.example.com/api/dns-01
dns_teamnifty_token = <your token>
```

```sh
chmod 600 /etc/letsencrypt/teamnifty.ini
```

There is no built in default URL, `dns_teamnifty_api_url` is required.

## Usage

Single name:

```sh
certbot certonly \
  --authenticator dns-teamnifty \
  --dns-teamnifty-credentials /etc/letsencrypt/teamnifty.ini \
  -d example.com
```

Wildcard plus apex:

```sh
certbot certonly \
  --authenticator dns-teamnifty \
  --dns-teamnifty-credentials /etc/letsencrypt/teamnifty.ini \
  -d example.com -d '*.example.com'
```

Arguments:

| Argument | Default | Description |
| --- | --- | --- |
| `--dns-teamnifty-credentials` | | Path to the credentials INI file (required) |
| `--dns-teamnifty-propagation-seconds` | 120 | Seconds to wait for the record to reach the name servers before certbot asks the CA to validate |

The plugin calls `POST {api_url}/present` and `POST {api_url}/cleanup` with
`Authorization: Bearer <token>` and a JSON body `{"fqdn": "...", "value": "..."}`.
A failing cleanup is only logged, it never fails an issuance that already worked.

## lego

[lego](https://go-acme.github.io/lego/) needs no plugin, use its built in
`httpreq` provider:

```sh
HTTPREQ_ENDPOINT=https://flux.example.com/api/dns-01 \
HTTPREQ_USERNAME=token \
HTTPREQ_PASSWORD=<your token> \
lego --dns httpreq --domains example.com --domains '*.example.com' \
  --email you@example.com run
```

lego sends Basic auth only when both `HTTPREQ_USERNAME` and `HTTPREQ_PASSWORD` are
set, so set both. The API takes the token from the password, the user name is not
checked (use any value).
Leave `HTTPREQ_MODE` unset (not `RAW`).

## acme.sh

Copy `contrib/acme.sh/dns_teamnifty.sh` into `~/.acme.sh/dnsapi/`, then:

```sh
export TEAMNIFTY_API_URL=https://flux.example.com/api/dns-01
export TEAMNIFTY_TOKEN=<your token>
acme.sh --issue --dns dns_teamnifty -d example.com -d '*.example.com'
```

Both values are saved in the acme.sh account configuration for renewals.

## Development

```sh
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
.venv/bin/python -m pytest -q && .venv/bin/ruff check .
```

## License

Apache License 2.0, see [LICENSE](LICENSE).
