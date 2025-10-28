import pytest
import pydantic_temporal_example.temporal.client as client_mod


@pytest.mark.asyncio
async def test_build_temporal_client_connect_called(monkeypatch):
    captured = {}
    async def fake_connect(target, *_args, **_kwargs):
        captured["target"] = target
        return "client"
    # Patch the actual symbol used in the function: TemporalClient.connect == temporalio.client.Client.connect
    import temporalio.client
    monkeypatch.setattr(temporalio.client.Client, "connect", staticmethod(fake_connect), raising=True)

    c = await client_mod.build_temporal_client("example.com", 7234)
    assert c == "client"
    assert captured["target"].endswith(":7234")