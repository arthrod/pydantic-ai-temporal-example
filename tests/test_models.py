import json
from pydantic_temporal_example.models import (
    SlackReply,
    SlackMessageID,
    SlackEventsAPIBodyAdapter,
    SlackEventsAPIBody,
    URLVerificationEvent,
)


def test_slack_reply_text_and_blocks():
    thread = SlackMessageID(channel="C123", ts="1700000000.000100")
    # text case
    r1 = SlackReply(thread=thread, content="hello")
    assert r1.text == "hello"
    assert r1.blocks is None
    # blocks case
    blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": "hi"}}]
    r2 = SlackReply(thread=thread, content=blocks)
    assert r2.text is None
    assert r2.blocks == blocks


def test_adapter_parses_url_verification_event():
    body = {
        "type": "url_verification",
        "token": "t",
        "challenge": "abc123",
    }
    obj = SlackEventsAPIBodyAdapter.validate_python(body)
    assert isinstance(obj, URLVerificationEvent)
    assert obj.challenge == "abc123"


def test_adapter_parses_event_callback():
    body = {
        "type": "event_callback",
        "token": "t",
        "team_id": "T1",
        "api_app_id": "A1",
        "event": {
            "type": "message",
            "user": "U1",
            "text": "hi",
            "ts": "1700000000.000100",
            "channel": "C1",
            "event_ts": "1700000000.000100",
            "channel_type": "channel",
        },
        "event_id": "Ev1",
        "event_time": 1700000000,
        "authed_users": ["U1"],
    }
    obj = SlackEventsAPIBodyAdapter.validate_python(body)
    assert isinstance(obj, SlackEventsAPIBody)
    assert obj.event.type == "message"
    # round-trip via JSON path too
    obj2 = SlackEventsAPIBodyAdapter.validate_json(json.dumps(body))
    assert isinstance(obj2, SlackEventsAPIBody)