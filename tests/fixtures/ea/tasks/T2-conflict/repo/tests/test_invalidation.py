from src.cache import invalidate, store


def test_revoke_user_purges_entries_immediately():
    store.put("perm:u1:billing", {"write"})
    invalidate.revoke_user("u1")
    assert store.get("perm:u1:billing") is None
