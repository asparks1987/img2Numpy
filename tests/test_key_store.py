from pathlib import Path

from app.key_store import APIKeyStore


def test_key_store_seeds_persists_and_revokes(tmp_path: Path):
    store_path = tmp_path / "api_keys.json"
    store = APIKeyStore(store_path, ("seed-a",))

    initial = store.list_records()
    assert len(initial) == 1
    assert initial[0].api_key == "seed-a"
    assert initial[0].active

    created = store.create_key("client-1", description="test client")
    assert created.client_name == "client-1"
    assert created.active

    reloaded = APIKeyStore(store_path, ("ignored-seed",))
    records = reloaded.list_records()
    assert any(record.client_name == "client-1" for record in records)
    assert reloaded.validate_and_mark_used(created.api_key)

    assert reloaded.revoke_key(created.key_id)
    assert not reloaded.validate_and_mark_used(created.api_key)
