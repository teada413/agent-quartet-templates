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
| デザイン | `docs/design-tokens.md`（必須・改変禁止）。トークンの値をどこまで動かせるかは **厳格／報告制** のどちらかを planner と相談して決める。トークンを補う基準のファイルは `docs/design-references/` に置ける |
| 和文フォント | Noto Sans JP をアプリに同梱する。外部からの読み込みは違反。13px 以下は weight 400 以上 |
| ウィンドウサイズ | 最小サイズを必ず設定し、最小・既定・最大化の3つで確認する（配色が複数あれば配色ごと） |
| デバッグポート | `dev:debug` のときだけ開く。配布版では環境変数を無視し、Chromium のスイッチがあれば起動を拒否し、fuse で `--inspect` 系と `NODE_OPTIONS` を止める |
| 配布用ビルド | 「配布する」と決めたプロジェクトだけ、最後のスプリントで確認する（fuse、デバッグポート、開発用の項目、パッケージの中身） |
| E2E の範囲 | 既定は毎回全体。実行時間が長くなったら「関係する spec だけ」に切り替え、全体はチェックポイントで回す（ユーザー確定事項に記録） |
| ソース管理 | エージェントはコミットしない。コミット・ブランチ・push はメインセッションがユーザーの了解のもとで行う |
| 相談して決めるもの | ビルドツール、ユニットテスト・lint、状態管理、データベース、配布方法、パッケージマネージャー、デザイントークンの扱い、ブランチとタグの決まり |

## Webアプリ版との違い

| Webアプリ版 | Electron 版 |
|---|---|
| evaluator が Playwright MCP でブラウザを操作する | evaluator は E2E テストを書いて残し、デザインの計測は MCP をアプリに接続して行う |
| レスポンシブ（375 / 768 / 1280px） | ウィンドウサイズ（最小・既定・最大化） |
| 和文フォントは Google Fonts から読み込む | 和文フォントはアプリに同梱する |
| DB は Turso に固定 | DB は planner と相談して決める |
| リロード後のデータ保持 | アプリ再起動後のデータ保持 |
| — | セキュリティ設定の機械判定、3層の分離、デバッグポートは開発時だけ |
| トークンは厳格に適用 | 厳格／報告制を選べる。報告制では designer の調整を evaluator が期待値に含め、合格後にユーザーが認めて確定事項に記録する |
| — | E2E の範囲の切り替え、ソース管理、公開後の運用（`docs/issues/`）の決まり |

## 新しいプロジェクトへの導入

1. `CLAUDE.md` と `.claude/` をプロジェクトのルートにコピーする
2. `CLAUDE.md` の見出しの `{{プロジェクト名}}` を書き換える
3. `docs/design-tokens.md` にデザインシステムを置く（designer の起動前に必須）
4. 参考画像があれば `docs/design-references/` に置く（空でも動く）。トークンを補う基準（配色が複数あるときの対応表など）があれば同じ場所にファイルで置き、`CLAUDE.md` の「トークンを補う基準のファイル」にファイル名と役割を書き足す
5. Claude Code で「planner で〇〇の仕様を作って」と依頼して始める。planner が技術スタックと一緒に、トークンの扱い（厳格／報告制）とソース管理の決まりを聞いてくる
6. データベースに Turso を使うと決めたら、`.claude/agents/generator.md` の `tools:` に Turso MCP のツールを追記する

## 前提

- Node.js（Playwright MCP を `npx -y @playwright/mcp@latest` で起動する。初回は取得に時間がかかる）
- ポート 9222 が空いていること（デバッグ用に起動した Chrome などが使っていると接続先を取り違える）

## 実プロジェクトで確かめたこと

このテンプレートの前提のうち、次は Electron + Vue のアプリ（45 スプリント、Microsoft Store に公開）で実際に回して確かめたもの。

- **Playwright MCP の `--cdp-endpoint` で、起動中の Electron アプリに接続できる。** 接続は最初のブラウザ操作のときに行われるので、MCP サーバーがエージェントの起動時に先に立ち上がっていても、アプリを後から `dev:debug` で起こせばつながる。main が `remote-allow-origins` を付けていることが前提
- **MCP のリサイズは Electron のウィンドウに効かない。** ウィンドウサイズの確認は `_electron` で起動するスクリプト・E2E テストで行う
- まれに、接続はできているのにスクリーンショットだけがタイムアウトする（Windows の窓の隠れ判定でページが `hidden` になる）。`--disable-features=CalculateNativeWinOcclusion` を付けたスクリプトで回避できる
- **配布版でデバッグポートを閉じ切ることはできる。** Chromium のスイッチはアプリ側で止められないので、検出して起動を拒否する。`--inspect` 系・`NODE_OPTIONS`・`ELECTRON_RUN_AS_NODE` は fuse で止める。配布版の E2E が起動方法ごとに確かめる
- **E2E は 15〜20 スプリントあたりで全体実行が重くなる。** 「関係する spec だけ」への切り替えと、全体を回すチェックポイントの決め方は CLAUDE.md の「E2E テストの実行範囲」
- **Web サイト向けのデザインシステムを流用すると、厳格な適用では回らない。** 報告制（designer が調整を全件報告し、evaluator がそれを期待値に含め、合格後にユーザーが認める）に切り替えて回した

接続できなかった場合でも、エージェントは E2E テストやスクリプトの中でスクリーンショットとスタイルを取得する方法に切り替えて作業を続ける（CLAUDE.md の「接続できない場合（逃げ道）」）。
