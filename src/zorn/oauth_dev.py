from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from .config import AppSettings
from .time_utils import utc_now


@dataclass(frozen=True, slots=True)
class IssuedOAuthDevToken:
    token: str
    scope: str
    expires_in: int
####


class OAuthDevTokenStore:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self._secret = self._resolve_secret(settings)
    ####

    @staticmethod
    def _resolve_secret(settings: AppSettings) -> bytes:
        if settings.oauth_dev_signing_secret:
            return hashlib.sha256(settings.oauth_dev_signing_secret.encode("utf-8")).digest()
        ####
        seed = "|".join(settings.static_tokens) or "dev-token"
        return hashlib.sha256(f"{settings.product_name}|{seed}".encode("utf-8")).digest()
    ####

    def issue_token(self, *, scope: str | None = None) -> IssuedOAuthDevToken:
        now = utc_now()
        expires_in = max(int(self.settings.oauth_dev_token_ttl_seconds), 1)
        effective_scope = scope or "entities tasks objects"
        payload = {
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
            "scope": effective_scope,
            "jti": secrets.token_hex(12),
        }
        encoded = _urlsafe_b64(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
        signature = hmac.new(self._secret, encoded.encode("ascii"), hashlib.sha256).hexdigest()
        token = f"zorn-oauth-dev.{encoded}.{signature}"
        return IssuedOAuthDevToken(token=token, scope=str(payload["scope"]), expires_in=expires_in)
    ####

    def is_valid(self, token: str | None) -> bool:
        return self.token_claims(token) is not None
    ####

    def token_claims(self, token: str | None) -> dict[str, Any] | None:
        if not token:
            return None
        ####
        try:
            prefix, encoded, signature = token.split(".", 2)
        except ValueError:
            return None
        ####
        if prefix != "zorn-oauth-dev":
            return None
        ####
        expected = hmac.new(self._secret, encoded.encode("ascii"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return None
        ####
        try:
            payload = json.loads(_urlsafe_b64_decode(encoded))
        except (ValueError, json.JSONDecodeError):
            return None
        ####
        expiry = payload.get("exp")
        if not isinstance(expiry, int):
            return None
        ####
        if expiry <= int(utc_now().timestamp()):
            return None
        ####
        return payload if isinstance(payload, dict) else None
    ####

    def token_scope_allows(self, token: str | None, required_scope: str) -> bool:
        payload = self.token_claims(token)
        if payload is None:
            return False
        ####
        scope = payload.get("scope")
        if not isinstance(scope, str):
            return False
        ####
        from .auth_scopes import scope_allows

        return scope_allows(scope, required_scope)
    ####
####


def _urlsafe_b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")
####


def _urlsafe_b64_decode(value: str) -> str:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}".encode("ascii")).decode("utf-8")
####
