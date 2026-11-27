#!/usr/bin/env sh
# shellcheck shell=sh disable=SC2034
# acme.sh DNS API hook for the Flux ERP dns-01 API.
#
# Usage:
#   export TEAMNIFTY_API_URL="https://flux.example.com/api/dns-01"
#   export TEAMNIFTY_TOKEN="<your token>"
#   acme.sh --issue --dns dns_teamnifty -d example.com -d '*.example.com'
dns_teamnifty_info='Flux ERP dns-01 API
Site: github.com/Team-Nifty-GmbH/certbot-dns-teamnifty
Options:
 TEAMNIFTY_API_URL API URL, e.g. https://flux.example.com/api/dns-01
 TEAMNIFTY_TOKEN API token
'

# Usage: dns_teamnifty_add _acme-challenge.www.example.com "txtvalue"
dns_teamnifty_add() {
  fulldomain=$1
  txtvalue=$2
  _teamnifty_init || return 1
  _info "Adding TXT record for $fulldomain"
  _teamnifty_call present "$fulldomain" "$txtvalue"
}

# Usage: dns_teamnifty_rm _acme-challenge.www.example.com "txtvalue"
dns_teamnifty_rm() {
  fulldomain=$1
  txtvalue=$2
  _teamnifty_init || return 1
  _info "Removing TXT record for $fulldomain"
  _teamnifty_call cleanup "$fulldomain" "$txtvalue"
}

_teamnifty_init() {
  TEAMNIFTY_API_URL="${TEAMNIFTY_API_URL:-$(_readaccountconf_mutable TEAMNIFTY_API_URL)}"
  TEAMNIFTY_TOKEN="${TEAMNIFTY_TOKEN:-$(_readaccountconf_mutable TEAMNIFTY_TOKEN)}"
  if [ -z "$TEAMNIFTY_API_URL" ] || [ -z "$TEAMNIFTY_TOKEN" ]; then
    _err "You must set TEAMNIFTY_API_URL and TEAMNIFTY_TOKEN."
    return 1
  fi
  _saveaccountconf_mutable TEAMNIFTY_API_URL "$TEAMNIFTY_API_URL"
  _saveaccountconf_mutable TEAMNIFTY_TOKEN "$TEAMNIFTY_TOKEN"
  # strip one trailing slash
  TEAMNIFTY_API_URL="${TEAMNIFTY_API_URL%/}"
}

# Usage: _teamnifty_call present|cleanup fqdn value
_teamnifty_call() {
  _action=$1
  export _H1="Authorization: Bearer $TEAMNIFTY_TOKEN"
  _body="{\"fqdn\": \"$2\", \"value\": \"$3\"}"
  if ! response="$(_post "$_body" "$TEAMNIFTY_API_URL/$_action" "" "POST" "application/json")"; then
    _err "Request to $_action failed: $response"
    return 1
  fi
  # _post only fails on transport errors; the server reports problems as {"error": ...}
  if _contains "$response" '"error"'; then
    _err "dns-01 API error: $response"
    return 1
  fi
  return 0
}
