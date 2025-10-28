"""Slack Events API verification and request signing utilities."""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException

from pydantic_temporal_example.config import get_settings
from pydantic_temporal_example.models import SlackEventsAPIBody, SlackEventsAPIBodyAdapter, URLVerificationEvent

if TYPE_CHECKING:
    from starlette.requests import Request


async def get_verified_slack_events_body(
    request: Request,
) -> SlackEventsAPIBody | URLVerificationEvent | dict[str, Any]:
    """Verify Slack request signature and timestamp, then parse the events payload."""
    settings = get_settings()
    signing_secret = settings.slack_signing_secret.get_secret_value()
    if not signing_secret:
        raise HTTPException(status_code=401, detail='Slack signing secret not configured')

    # Get timestamp header
    timestamp_header = request.headers.get('x-slack-request-timestamp')
    if not timestamp_header:
        raise HTTPException(status_code=401, detail='Missing x-slack-request-timestamp header')

    # Check if timestamp is valid and not older than 5 minutes or far in the future
    now = int(time.time())
    try:
        ts = int(timestamp_header)
    except ValueError:
        raise HTTPException(status_code=401, detail='Invalid x-slack-request-timestamp header')
    if ts < (now - 300) or ts > (now + 300):
        raise HTTPException(status_code=401, detail='Request timestamp too old or too far in the future')

    # Get signature header
    signature_header = request.headers.get('x-slack-signature')
    if not signature_header:
        raise HTTPException(status_code=401, detail='Missing x-slack-signature header')

    # Get request body
    request_body = await request.body()
    request_body_str = request_body.decode('utf-8')

    # Create the base string for the signature
    base_string = f'v0:{timestamp_header}:{request_body_str}'

    # Calculate expected signature
    expected_signature = (
        'v0=' + hmac.new(signing_secret.encode('utf-8'), base_string.encode('utf-8'), hashlib.sha256).hexdigest()
    )

    # Compare signatures
    if not hmac.compare_digest(expected_signature, signature_header):
        raise HTTPException(status_code=401, detail='Invalid request signature')

    return SlackEventsAPIBodyAdapter.validate_json(request_body_str)
