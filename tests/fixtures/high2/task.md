# High-2: reel-auto でも account_source_scope を参照する

## 背景
`drive_images` 台帳からアカウントの画像を読むとき、reel-auto はアカウントフォルダ配下を
すべて対象にしている。連携アプリ Insta AI Pro には `account_source_scope` という
「唯一の正本」指定があり、特定のサブフォルダ1つに限定できる。
scope が入っているアカウントが3件あり、reel-auto 側がこれを見ていないため、
本来対象外のフォルダの画像まで拾っている。

## やること
Insta AI Pro の実装を参考に、reel-auto の台帳読み取り経路で
`account_source_scope` を参照し、scope があればそのサブフォルダに限定する。

## 移植元（タスク起票時の記述）
前例は連携アプリの `~/Developer/Insta/repo/src/lib/sourceScope.ts`（ほぼそのまま移植可）。
