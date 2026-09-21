# Feature System Brief

各機能は次のフォーマットで整理する。

- 機能名
- 対象ユーザー
- 解く行動上の問題
- 必要な画面
- 必要な最小データ
- MVP の範囲

例:

- 機能名: Action Panel
- 対象ユーザー: sales / manager
- 問題: 会議後に next action が曖昧
- 画面: meeting detail, my tasks, manager queue
- データ: action_id, owner, due_date, status, source_segment_ids
- MVP: meeting detail 内の action list のみ
