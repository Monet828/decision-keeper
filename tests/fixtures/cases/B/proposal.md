# 権限チェックの高速化（無効化機構つき）

p95 が 480ms まで悪化しており、権限取得のDB往復が支配的でした。
`get_permissions` の結果をキャッシュしますが、権限変更イベントで
`revoke_user()` を呼び、該当エントリを即座に invalidate します。

即時反映は `tests/test_invalidation.py` で検証済みです。
