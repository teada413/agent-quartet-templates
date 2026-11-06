# Agent Quartet Template（Electron アプリ用）

planner → generator → designer → evaluator の4つのサブエージェントで、スプリント単位に Electron のデスクトップアプリを開発するための Claude Code 用の雛形。Webアプリ用（`../webapp/`）の構成を、Electron 向けに作り替えたもの。

## 構成

```
CLAUDE.md                     # オーケストレーションの規則と固定の前提
.claude/agents/
├── planner.md                # 技術スタックをユーザーと相談し、仕様書とスプリント契約を作る
├── generator.md              # main / preload / renderer を分離して実装し、ユニットテストを書く
├── designer.md               # Vue の UI を仕上げる（Playwright MCP をアプリに接続）
└── evaluator.md              # E2E テストを書いて実行し、セキュリティ設定とデザインを判定する
```

## 固定の前提

| 項目 | 内容 |
|---|---|
| 言語 | TypeScript（strict） |
| 画面のフレームワーク | 原則 Vue 3（単一ファイルコンポーネント） |
| E2E テスト | Playwright の Electron 対応。evaluator が `tests/e2e/` に書いて残す |
| 画面の確認・計測 | Playwright MCP を起動中のアプリ（デバッグポート 9222）に接続する |
| セキュリティ | `contextIsolation: true`・`nodeIntegration: false`・`sandbox: true`・CSP・main 側での入力検証 |
| 設計 | main / preload / renderer の分離。renderer は Node の機能を直接使わない |
| デザイン | `docs/design-tokens.md`（必須・改変禁止） |
| 和文フォント | Noto Sans JP をアプリに同梱する。外部からの読み込みは違反。13px 以下は weight 400 以上 |
| ウィンドウサイズ | 最小サイズを必ず設定し、最小・既定・最大化の3つで確認する |
| 配布用ビルド | 「配布する」と決めたプロジェクトだけ、最後のスプリントで確認する |
| 相談して決めるもの | ビルドツール、ユニットテスト・lint、状態管理、データベース、配布方法、パッケージマネージャー |

## Webアプリ版との違い

| Webアプリ版 | Electron 版 |
|---|---|
| evaluator が Playwright MCP でブラウザを操作する | evaluator は E2E テストを書いて残し、デザインの計測は MCP をアプリに接続して行う |
| レスポンシブ（375 / 768 / 1280px） | ウィンドウサイズ（最小・既定・最大化） |
| 和文フォントは Google Fonts から読み込む | 和文フォントはアプリに同梱する |
| DB は Turso に固定 | DB は planner と相談して決める |
| リロード後のデータ保持 | アプリ再起動後のデータ保持 |
| — | セキュリティ設定の機械判定、3層の分離、デバッグポートは開発時だけ |

## 新しいプロジェクトへの導入

1. `CLAUDE.md` と `.claude/` をプロジェクトのルートにコピーする
2. `CLAUDE.md` の見出しの `{{プロジェクト名}}` を書き換える
3. `docs/design-tokens.md` にデザインシステムを置く（designer の起動前に必須）
4. 参考画像があれば `docs/design-references/` に置く（空でも動く）
5. Claude Code で「planner で〇〇の仕様を作って」と依頼して始める
6. データベースに Turso を使うと決めたら、`.claude/agents/generator.md` の `tools:` に Turso MCP のツールを追記する

## 前提

- Node.js（Playwright MCP を `npx -y @playwright/mcp@latest` で起動する。初回は取得に時間がかかる）
- ポート 9222 が空いていること（デバッグ用に起動した Chrome などが使っていると接続先を取り違える）

## 最初のプロジェクトで確かめること

**Playwright MCP を Electron アプリに接続する方法は、このテンプレートを作った時点では実機で試していない。** Playwright MCP に接続用のオプション（`--cdp-endpoint`）があることだけ確認済み。Sprint 1 で designer / evaluator が接続できたかどうかを完了報告で確かめること。

接続できなかった場合でも、エージェントは E2E テストやスクリプトの中でスクリーンショットとスタイルを取得する方法に切り替えて作業を続ける（CLAUDE.md の「接続できない場合（逃げ道）」）。その場合は、接続方法をテンプレート側で見直す。
