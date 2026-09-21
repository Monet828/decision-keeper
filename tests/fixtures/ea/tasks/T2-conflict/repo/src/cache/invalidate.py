"""キャッシュの即時無効化。権限変更イベントを購読して purge する。"""

from . import store


def invalidate(key: str) -> None:
    store._store.pop(key, None)


def revoke_user(user_id: str) -> None:
    """権限変更時に該当ユーザーのエントリを即座に purge する。"""
    for key in [k for k in store._store if k.startswith(f"perm:{user_id}:")]:
        invalidate(key)
