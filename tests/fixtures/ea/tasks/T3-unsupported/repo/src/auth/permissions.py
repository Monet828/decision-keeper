"""権限チェック。"""


def get_permissions(db, user_id: str) -> set[str]:
    row = db.query("SELECT perms FROM user_permissions WHERE user_id = ?", user_id)
    return set(row["perms"]) if row else set()


def can(db, user_id: str, action: str) -> bool:
    return action in get_permissions(db, user_id)
