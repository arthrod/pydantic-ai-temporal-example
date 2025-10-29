import hmac
import hashlib
import json
import time
import pytest

import pydantic_temporal_example.tools.slack as slack_mod


class DummySecret(str):
    def get_secret_value(self) -> str:  # mimic SecretStr API used by the code
        return str(self)


class FakeRequest:
    def __init__(self, headers: dict[str, str], body: bytes):
        self.headers = headers
        self._body = body

    async def body(self) -> bytes:
        return self._body


def _signed_headers(secret: str, body: dict) -> tuple[dict, bytes]:
    ts = str(int(time.time()))
    raw = json.dumps(body).encode()
    base = f"v0:{ts}:{raw.decode()}".encode()
    signature = "v0=" + hmac.new(secret.encode(), base, hashlib.sha256).hexdigest()
    return ({"x-slack-request-timestamp": ts, "x-slack-signature": signature}, raw)


@pytest.mark.asyncio
async def test_get_verified_slack_events_body_happy_path(monkeypatch):
    # Monkeypatch settings to expose get_secret_value() as the code expects
    class DummySettings:
        slack_signing_secret = DummySecret("supersecret")
    monkeypatch.setattr(slack_mod, "get_settings", lambda: DummySettings(), raising=True)

    payload = {"type": "url_verification", "token": "t", "challenge": "xyz"}
    headers, raw = _signed_headers("supersecret", payload)
    req = FakeRequest(headers, raw)

    result = await slack_mod.get_verified_slack_events_body(req)  # type: ignore[arg-type]
    assert result.type == "url_verification"  # type: ignore[union-attr]
    assert result.challenge == "xyz"  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_get_verified_slack_events_body_invalid_signature(monkeypatch):
    class DummySettings:
        slack_signing_secret = DummySecret("supersecret")
    monkeypatch.setattr(slack_mod, "get_settings", lambda: DummySettings(), raising=True)

    payload = {"type": "url_verification", "token": "t", "challenge": "xyz"}
    ts = str(int(time.time()))
    req = FakeRequest(
        {"x-slack-request-timestamp": ts, "x-slack-signature": "v0=bad"},
        json.dumps(payload).encode(),
    )
    with pytest.raises(Exception):
        await slack_mod.get_verified_slack_events_body(req)  # type: ignore[arg-type]