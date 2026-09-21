# T2: 権限チェックの高速化（無効化機構つき）

権限変更イベントで `revoke_user()` を呼び、該当エントリを即座に invalidate します。
即時反映は `tests/test_invalidation.py` で検証済みです。
