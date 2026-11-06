# Agent Quartet Templates

Claude Code のサブエージェント4体でスプリント単位に開発を進めるためのハーネステンプレート集。作るアプリの種類に合わせて、3種類から選んで使う。

```
planner → generator → designer / refiner → evaluator
              ↑                                │
              └──────── 不合格時の差し戻し ────────┘
```

## テンプレート一覧

| フォルダ | 対象 | エージェント | 主な固定の前提 |
|---|---|---|---|
| [`webapp/`](webapp/) | Web アプリ | planner / generator / designer / evaluator | Playwright MCP で実操作テスト、DB は Turso、Noto Sans JP |
| [`electron/`](electron/) | Electron デスクトップアプリ | planner / generator / designer / evaluator | TypeScript + Vue 3、Playwright の Electron 対応で E2E、セキュリティ設定の機械判定 |
| [`python/`](python/) | ローカルの Python GUI アプリ（Tkinter / PySide6 など） | planner / generator / refiner / evaluator + 人間の画面確認 | venv + pip、ruff、mypy --strict、pytest、`core/` と `gui/` の分離 |

各テンプレートの詳しい前提と使い方は、それぞれの `README.md` を参照。

## 使い方

1. 使うテンプレートのフォルダから、`CLAUDE.md` と `.claude/`（Python 版は `tools/` も）を自分のプロジェクトのルートにコピーする

   ```bash
   cp -r webapp/.claude webapp/CLAUDE.md /path/to/your-project/
   ```

2. `CLAUDE.md` の `{{プロジェクト名}}` を書き換える
3. Web / Electron 版は `docs/design-tokens.md` にデザイントークンを置く（designer の起動前に必須）。参考画像があれば `docs/design-references/` に置く
4. Claude Code で「planner で〇〇の仕様を作って」と依頼して始める

## 共通の流れ

1. **計画**: planner が技術スタックの候補を出し、ユーザーが決める。仕様書 `docs/spec.md` とスプリント契約 `docs/sprints/sprint-N.md` を作る
2. **実装**: generator がスプリント契約を満たすコードを書く
3. **仕上げ**: designer（Web / Electron）が UI を、refiner（Python）がコード品質を仕上げる
4. **評価**: evaluator がテストを実行して合否を出す。不合格なら修正指示付きで該当エージェントに差し戻す

メインセッションはオーケストレーターに徹し、自分ではコードを書かない。差し戻しが3回続いたら止めてユーザーに報告する。

## 参考

[Shin-sibainu/agent-quartet-harness](https://github.com/Shin-sibainu/agent-quartet-harness) の構成をもとに、アプリの種類ごとに作り替えた。

## ライセンス

[MIT](LICENSE)
