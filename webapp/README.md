# Agent Quartet Template（Webアプリ用）

planner → generator → designer → evaluator の4つのサブエージェントで、スプリント単位で開発を進めるための Claude Code 用の雛形。simple-kakeibo で使った構成を汎用化したもの。

## 構成

```
CLAUDE.md                     # オーケストレーションの規則と固定の前提（Playwright・Turso・和文フォント）
.claude/agents/
├── planner.md                # 技術スタックをユーザーと相談し、仕様書とスプリント契約を作る
├── generator.md              # 契約を満たすコードを実装する（Turso MCP のツールを付与済み）
├── designer.md               # UI を仕上げる（Playwright MCP をインライン定義）
└── evaluator.md              # 実操作でテストし合否を判定する（Playwright MCP をインライン定義）
```

## 固定の前提

| 項目 | 内容 |
|---|---|
| E2E 確認 | Playwright MCP（designer / evaluator の frontmatter で定義。セッション側への追加は不要） |
| データベース | Turso。generator が Turso MCP（`mcp__mcp-turso-cloud__*`）で操作する。CLI は使わない |
| 和文フォント | Noto Sans JP を実際に読み込む。13px 以下は weight 400 以上。游ゴシック系へのフォールバック禁止 |
| 技術スタック | 固定しない。初回に planner が候補を出し、ユーザーが決める |

## 新しいプロジェクトへの導入

1. `CLAUDE.md` と `.claude/` をプロジェクトのルートにコピーする
2. `CLAUDE.md` の `{{プロジェクト名}}`（見出しと Turso の節の2か所）を書き換える。Turso のデータベース名もこの名前になる
3. `docs/design-tokens.md` にデザインシステムを置く（designer の起動前に必須）
4. 参考画像があれば `docs/design-references/` に置く（空でも動く）
5. DB を使う場合は、Turso に同名のデータベースを作り、接続情報を `.env.local` に書いておく
6. Claude Code で「planner で〇〇の仕様を作って」と依頼して始める

## 前提

- Node.js（Playwright MCP を `npx -y @playwright/mcp@latest` で起動する。初回は取得に時間がかかる）
- Turso MCP がユーザー設定で接続済みであること（サーバー名 `mcp-turso-cloud`）

## プロジェクト固有の情報の置き場所

別のルールファイルは作らない。プロジェクトごとに変わる情報は `docs/spec.md` に集める。

- 技術スタック: planner がユーザーと相談して `## 技術スタック` に書く
- 重点検査（そのドメインで壊れやすい観点）: planner が `## 重点検査` に書き、generator と evaluator が使う
- ユーザー確定事項: 途中でユーザーが下した判断を、メインセッションが `## ユーザー確定事項` に追記する

## オリジナル版からの主な変更点

- メインセッションはオーケストレーターに徹し、コードを書かない
- 完了報告を `docs/reports/` に全文保存し、引き継ぎではパスを明示する
- 差し戻しは SendMessage で同じエージェントに送り、再テストでは合格済みの条件も再確認する
- 差し戻しが3回連続したら止めてユーザーに報告する。合格しても次のスプリントへ自動では進まない
- planner: 技術スタックをユーザーと相談する／合格済みの契約を書き換えない／契約にデザインの具体値を書かない
- generator: 自己テストを実際に実行する／CSS 変数に寄せる／Turso MCP と秘密情報の扱い／起動方法を報告する
- designer: design-tokens.md を全文読む／Do's and Don'ts と和文フォントを実測して自己照合する／Playwright 未接続を偽装しない
- evaluator: トークン値と和文フォントを `browser_evaluate` で実測する／差し戻し先を明記する／コードを直さない／デグレを再確認する
