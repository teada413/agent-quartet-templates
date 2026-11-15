# Agent Quartet Template（Tauri アプリ用）

planner → generator → designer → evaluator の4つのサブエージェントで、スプリント単位に Tauri 2 のデスクトップアプリ（Windows）を開発するための Claude Code 用の雛形。Electron 版（`../electron/`）の構成を、Tauri 向けに作り替えたもの。

最小の Tauri 2 + Vue アプリで、E2E テストと Playwright MCP の接続、リリース版の対策を実機で確かめてから作った（下の「検証済みのこと」）。

## 構成

```
CLAUDE.md                     # オーケストレーションの規則と固定の前提
.claude/agents/
├── planner.md                # 技術スタックをユーザーと相談し、仕様書とスプリント契約を作る
├── generator.md              # Rust と Vue を分離して実装し、ユニットテストを書く
├── designer.md               # Vue の UI を仕上げる（Playwright MCP をアプリに接続）
└── evaluator.md              # E2E テストを書いて実行し、セキュリティ設定・リリース版・デザインを判定する
tests/e2e/
└── fixtures.ts               # E2E の土台: exe の起動と CDP 接続、ダイアログの差し替え、ウィンドウサイズの変更
tools/
└── check-release.mjs         # リリース版の機械判定: デバッグポートが開かない、テスト用のコードが入っていない
```

## 固定の前提

| 項目 | 内容 |
|---|---|
| 対象 OS | Windows（WebView2） |
| 言語 | 画面は TypeScript（strict）、バックエンドは Rust |
| 画面のフレームワーク | 原則 Vue 3。ビルドツールは Vite |
| E2E テスト | Playwright Test で debug 版の exe を起動し、`connectOverCDP` で接続する |
| 画面の確認・計測 | Playwright MCP を起動中のアプリ（WebView2 のデバッグポート 9222）に接続する |
| セキュリティ | 最小限の capabilities、CSP、Rust 側での入力検証、リリース版で `WEBVIEW2_*` の環境変数を消す |
| テストのための仕組み | `APP_E2E_*` の環境変数と `debug-only-` の権限は debug 版だけ。リリース版に入っていないことを `check-release.mjs` で確かめる |
| 設計 | Rust（`core/` と `commands/`）と画面（`src/`、`invoke` は `src/api/` だけ）の分離 |
| OS のダイアログ | Rust 側から開く。debug 版はテストが決めた結果を返す |
| デザイン | `docs/design-tokens.md`（必須・改変禁止） |
| 和文フォント | Noto Sans JP をアプリに同梱する。外部からの読み込みは違反。13px 以下は weight 400 以上 |
| ウィンドウサイズ | 最小サイズを必ず設定し、最小・既定・最大化の3つで確認する |
| 相談して決めるもの | 画面側のユニットテスト・lint、状態管理、データベース、使うプラグイン、配布方法、パッケージマネージャー、配色 |

## Electron 版との違い

| Electron 版 | Tauri 版 |
|---|---|
| main / preload / renderer の3層 | Rust と画面の2層 |
| E2E は Playwright の `_electron` で起動 | exe を子プロセスで起動し、WebView2 のデバッグポートに `connectOverCDP` |
| ダイアログは `electronApp.evaluate` で差し替え | Rust 側で開き、debug 版は `APP_E2E_DIALOG_STUB` のファイルの結果を返す |
| ウィンドウサイズは `BrowserWindow` を操作 | Tauri の window のコマンドを、debug 版だけの権限で呼ぶ |
| `contextIsolation`・`sandbox`・fuse の判定 | capabilities・CSP・`WEBVIEW2_*` の除去・`check-release.mjs` の判定 |
| デバッグポートはスイッチを検出して起動を拒否 | リリース版の起動直後に `WEBVIEW2_*` の環境変数を消す |
| 配布は electron-builder / Forge | Tauri の bundler（NSIS / MSI） |
| — | Rust のビルドに時間がかかるので、エージェントはバックグラウンドで実行する |
| — | 自動で確かめられないもの（本物のダイアログなど）は、契約の「人間の確認項目」にする |

## 新しいプロジェクトへの導入

1. `CLAUDE.md`、`.claude/`、`tests/`、`tools/` をプロジェクトのルートにコピーする
2. `CLAUDE.md` の見出しの `{{プロジェクト名}}` を書き換える
3. `docs/design-tokens.md` にデザインシステムを置く（designer の起動前に必須）
4. 参考画像があれば `docs/design-references/` に置く（空でも動く）
5. Claude Code で「planner で〇〇の仕様を作って」と依頼して始める
6. データベースに Turso を使うと決めたら、`.claude/agents/generator.md` の `tools:` に Turso MCP のツールを追記する

## 前提

- Windows 10 / 11（WebView2 Runtime。Windows 11 は標準で入っている）
- Rust（stable、`x86_64-pc-windows-msvc`）: `winget install --id Rustlang.Rustup`
- Visual Studio Build Tools の C++: `winget install --id Microsoft.VisualStudio.2022.BuildTools --override "--wait --passive --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"`
- Node.js（Playwright MCP を `npx -y @playwright/mcp@latest` で起動する。初回は取得に時間がかかる）
- ポート 9222 が空いていること（デバッグ用に起動した Chrome などが使っていると接続先を取り違える）

## 検証済みのこと

Tauri 2.12 / WebView2 157 / Playwright 1.65 / Rust 1.100 で確かめた。

- `WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--remote-debugging-port=9222` で、debug 版の exe と `tauri dev` のどちらにも Playwright MCP（`--cdp-endpoint`）が接続でき、スナップショット・入力・クリック・待ち受け・computed style・スクリーンショット・コンソール・通信の確認ができる
- `tests/e2e/fixtures.ts` で、日本語の入力、再起動後のデータ保持、ダイアログの差し替え（開く・キャンセル・UTF-8 でないファイル・保存）、ウィンドウの最小化と最大化、権限の無いコマンドが拒否されることを E2E で確かめられる（11件、約7秒）
- **対策をしないと、リリース版でも環境変数だけでデバッグポートが開く。** `main` の冒頭で `WEBVIEW2_*` を消すと閉じる。`check-release.mjs` は、対策済みの版を合格、対策なしの版と debug 版を不合格にする
- debug 版だけの capability と `APP_E2E_*` の仕組みは、リリース版の exe に文字列として残らない
- 接続した直後のページが `about:blank` のことがあり、画面の読み込みを待たないと E2E が落ちる（`fixtures.ts` で対処済み）
- MCP の `browser_resize` は、ネイティブのウィンドウの大きさを変えない

## 最初のプロジェクトで確かめること

- **サブエージェントの frontmatter に書いた Playwright MCP が、Tauri アプリに接続できるか。** 検証では MCP サーバーを確認用のスクリプトから直接呼んだ。Electron 版で確認済みの仕組みと同じだが、Sprint 1 で designer / evaluator の完了報告を見て確かめる
- generator が作る `dev:debug` などの環境変数付きのスクリプトが、Windows の npm で動くか
- インストーラー（NSIS / MSI）でインストールしたアプリで `check-release.mjs` が合格するか（検証では `--no-bundle` の exe だけを確かめた）
- 利用者のレジストリのポリシー（`HKCU\Software\Policies\Microsoft\Edge\WebView2`）で WebView2 の引数を指定された場合は、アプリからは止められない（未検証。ポリシーを書ける時点で、その利用者の権限はすでに握られている）
