from src.auth.permissions import can


def test_permission_revoked_is_reflected_immediately(db):
    db.revoke("u1", "billing:write")
    assert can(db, "u1", "billing:write") is False
