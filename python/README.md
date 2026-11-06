# Agent Quartet Template（Python GUI アプリ用）

planner → generator → refiner → evaluator → 人間の画面確認、の流れでスプリント単位に開発を進めるための Claude Code 用の雛形。対象は **サーバーを持たないローカルの Python GUI アプリ**（Tkinter / PySide6 などのネイティブ GUI）。Webアプリ用（`../webapp/`）の骨格を、Python の GUI アプリ向けに作り替えたもの。

`python-gui-app-test`（SQLite の請求書を表示・PDF/CSV 出力・印刷する Tkinter アプリ、全4スプリント）で実際に回した結果を反映している。

## 構成

```
CLAUDE.md                     # オーケストレーションの規則と固定の開発環境
.claude/agents/
├── planner.md                # 技術スタックをユーザーと相談し、仕様書とスプリント契約を作る
├── generator.md              # ロジックを GUI から分離して実装し、ユニットテストを書く
├── refiner.md                # 振る舞いを変えずにコード品質を仕上げる
└── evaluator.md              # 受け入れテストと画面レベルの E2E を書いて実行し、機械判定と4品質基準で合否を出す
tools/
└── run_hidden.py             # 非表示の Windows デスクトップの上で pytest や --smoke を動かすランナー
```

## Webアプリ版との違い

| Webアプリ版 | Python GUI 版 |
|---|---|
| designer（UI を仕上げる） | refiner（コード品質を仕上げる） |
| evaluator が Playwright で画面を操作する | evaluator は `core/` 経由の受け入れテストと、GUI フレームワークを直接操作する画面レベルの E2E（`tests/acceptance/test_sprint_N_gui_e2e.py`）を書く。Playwright MCP はネイティブ GUI を操作できないので使わない |
| デザイン4基準 | 品質4基準（堅牢性・コード品質・設計・テスト品質） |
| `docs/design-tokens.md`（必須） | `docs/coding-standards.md`（任意。無ければ CLAUDE.md の既定の規約） |
| AIスロップのチェック | AI っぽいコードのチェック |
| — | **人間の画面確認**: evaluator の合格後、契約の「人間の確認項目」を人が確認して指示する |
| DB は Turso に固定 | DB は planner と相談して決める（不要／JSON／SQLite） |

## 固定の前提

| 項目 | 内容 |
|---|---|
| アプリの形 | ローカルのデスクトップ GUI。サーバー・Web 版の画面を作らない |
| Python | システムの Python 3.10 以上 |
| 環境管理 | venv + pip（`pyproject.toml` に集約）。uv は使わない |
| lint / format | ruff |
| 型チェック | mypy --strict |
| テスト | pytest + pytest-cov（`core/` のカバレッジ 80% 以上） |
| 設計 | ロジック（`core/`）と GUI（`gui/`）の分離。`core/` は GUI フレームワークを import しない |
| 起動確認 | エントリポイントは `--smoke` に対応し、ウィンドウを表示せずに終了コード 0 で終わる |
| 画面を出さないテスト | pytest と `--smoke` は `tools/run_hidden.py` 経由で実行し、作業中のユーザーのフォーカスを奪わない |
| Windows / 日本語 | `encoding="utf-8"` の明示、`pathlib`、日本語・空白を含むパスで動くこと |
| 相談して決めるもの | GUI フレームワーク、和文フォント、データベース、配布方法 |

## 新しいプロジェクトへの導入

1. `CLAUDE.md`、`.claude/`、`tools/` をプロジェクトのルートにコピーする
2. `CLAUDE.md` の見出しの `{{プロジェクト名}}` を書き換える
3. 独自のコーディング規約があれば `docs/coding-standards.md` に置く（無ければ CLAUDE.md の既定の規約で進む）
4. Claude Code で「planner で〇〇の仕様を作って」と依頼して始める

## 前提

- Windows であること（`tools/run_hidden.py` が Windows 専用のため）
- `python --version` が 3.10 以上であること
- Tkinter を使う場合は `python -c "import tkinter"` が通ること
