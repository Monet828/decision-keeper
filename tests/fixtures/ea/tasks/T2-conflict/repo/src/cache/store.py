"""汎用キャッシュ。"""

_store: dict[str, object] = {}


def get(key: str):
    return _store.get(key)


def put(key: str, value: object) -> None:
    _store[key] = value
