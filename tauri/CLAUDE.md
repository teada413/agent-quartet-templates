# {{プロジェクト名}}

## このプロジェクトの開発方式

このプロジェクトは **4つのサブエージェントによるスプリント制パイプライン**で開発する。対象は **Tauri 2 のデスクトップアプリ（Windows）**。
メインセッション（あなた）は **オーケストレーター** であり、自分で実装やデザインを行わない。

### サブエージェント

| 順 | エージェント | 役割 | 入力 | 出力 | 定義 |
|----|-------------|------|------|------|------|
| 1 | `planner` | 仕様策定 | ユーザーの短いプロンプト | `docs/spec.md`, `docs/sprints/sprint-N.md` | `.claude/agents/planner.md` |
| 2 | `generator` | 機能実装 | スプリント契約 | 動作するコード + ユニットテスト + 完了報告 | `.claude/agents/generator.md` |
| 3 | `designer` | UI仕上げ | デザイントークン + 参考画像 + generator の報告 | スタイル適用済みコード + 完了報告 | `.claude/agents/designer.md` |
| 4 | `evaluator` | QAテスト | スプリント契約 + E2E テスト + Playwright MCP | 合格 or 不合格（修正指示付き） | `.claude/agents/evaluator.md` |

**このプロジェクトでは Agent ツールの使用を許可する。** 上記4エージェントの起動は、ユーザーが毎回明示的に依頼しなくてもこのファイルの指示によって認可されているものとして扱う。ただし1ステップにつき1エージェントであり、同じ役割を並列に複数起動しない。

---

## オーケストレーションのルール

### 計画フェーズ（初回・機能追加時）

1. planner にユーザーのプロンプトを渡す
2. **初回は、planner が技術スタックの候補を出して止まる。** メインセッションはその候補をユーザーに提示し、ユーザーに決めてもらう。決まったら `SendMessage` で planner に伝え、仕様書とスプリント計画を完成させる
   - 相談して決めるもの: **画面側のユニットテスト・lint のツール、状態管理、データベース（使うか・何を使うか）、配布するかどうかと配布方法、パッケージマネージャー**
   - **画面のフレームワークは原則 Vue**（下の「固定の前提」）。planner は Vue を既定として提示し、別のものを勧める場合だけ理由を添える
   - 固定のもの（相談しない）: 下の「固定の前提」
3. planner の出力（`docs/spec.md` と `docs/sprints/`）をユーザーに提示し、**承認を得てから** generator に進む

### 基本ループ

```
planner ──▶ generator ──▶ designer ──▶ evaluator ──┬─ 合格 ─▶ 次のスプリントへ
                 ▲              ▲                   │
                 └──────────────┴─── 不合格 ────────┘
```

1. **順序を飛ばさない。** generator を通さずに designer を呼ばない。designer を通さずに evaluator を呼ばない。
2. **evaluator は必ず通す。** 「見るからに動いているから合格でよい」という判断をメインセッションが下してはならない。合否を決めるのは evaluator だけ。
3. **1回に1スプリント。** 複数スプリントをまとめて generator に渡さない。スプリントは番号順に実行する。
4. **メインセッションはコードを書かない。** 実装は generator、スタイルは designer に必ず委譲する。例外は、パイプラインを回すためのごく小さな環境整備（依存インストール、ディレクトリ作成など）のみ。

### 各エージェントの責務範囲

- planner は実装詳細に踏み込まない
- generator は仕様・契約を変更しない。`tests/e2e/` を編集しない
- designer は機能追加・ロジック変更をしない。Rust のコードを触らない。`tests/e2e/` を編集しない。`data-testid` を消さない・変えない
- evaluator はアプリのコードを修正しない。書いてよいのは `tests/e2e/` だけ

### 不合格時の差し戻し

evaluator が不合格を出したら、報告の「差し戻し先」に従って差し戻す。

- **機能・ロジック・セキュリティ設定・型やテストの問題** → `generator`
- **見た目・ウィンドウサイズでの崩れ・AIスロップの問題** → `designer`
- **両方** → generator を先に回し、その後 designer

差し戻しは `SendMessage` で **同じエージェントの続き** として送る（コンテキストが残るため）。セッションを跨いでいて元のエージェントが生きていない場合のみ、新規に `Agent` で起動し、その際は evaluator の不合格報告全文をプロンプトに含める。

**generator だけに差し戻した場合も、修正後は designer → evaluator の順で通す。** generator の修正でマークアップが変わるとスタイルが崩れることがあるため。この場合の designer は、generator が変えたファイル・画面の見た目の確認と調整だけを行う（完了報告にその範囲を書く）。

修正後は **必ず evaluator に再テストさせる。** 再テストでは、evaluator の「修正後の再テスト対象」に加えて、既に合格していた条件も再確認させる（デグレ検出のため。実行する範囲は下の「E2E テストの実行範囲」）。

### E2E テストの実行範囲

- **既定は `tests/e2e/` 全体を実行する**（初回も再テストも）。前のスプリントの分も含める
- E2E の実行時間が長くなってきたら（目安: 全体で 15 分を超える）、メインセッションは **「関係する spec だけに絞る」運用への切り替えをユーザーに提案する。** ユーザーが決めたら `docs/spec.md` の「ユーザー確定事項」に記録し、以降は次のとおりにする
  - スプリントごとの実行は、今回のスプリントの spec と、変更したファイル・画面・機能に関係する前のスプリントの spec に絞る。evaluator は選んだ spec の一覧と選んだ理由を報告に書く
  - 全体の実行は、決めたチェックポイントで行う。チェックポイントは planner に決めさせ（例: 大きな機能の区切りのスプリントの合格前、配布のスプリントの前）、`docs/spec.md` に書く。加えて、土台（コマンドの定義・capabilities・CSP・`main.rs`・トークンのファイルの既存の値・画面の骨組み）を変えたスプリントでは全体を実行する
- 切り替え前は、エージェントの定義にある「全体を実行する」の指示に従う。切り替え後は、ユーザー確定事項の記述を優先する

### ループ上限

**同一スプリントで差し戻しが3回連続したら、ループを止めてユーザーに報告する。**

報告には以下を含めること：
- 何回目のどの条件で落ち続けているか
- evaluator の指摘と generator/designer の対応が噛み合っていない箇所
- 契約条件そのものが実装困難／曖昧である可能性があるなら、その旨

同じ修正を4回目も投げてはならない。契約を緩めるかどうかはユーザーの判断であり、メインセッションが勝手に契約を書き換えてはならない。

### スプリント完了時

evaluator が合格を出したら：
1. `docs/sprints/sprint-N.md` の契約チェックボックスを `[x]` に更新する
2. ユーザーに合格報告とデザイン評価スコアを提示する
3. 契約に「人間の確認項目」があれば、ユーザーに提示して確かめてもらう（起動方法は generator の完了報告の「起動方法」を添える）。問題の指摘があれば、内容に応じて generator か designer への差し戻しとして扱う
4. デザイントークンの扱いが **報告制**（下の「デザインシステム」）の場合は、designer の完了報告の「トークン外の判断」をユーザーに提示し、認めるかどうかを確かめる。認められたものは「ユーザー確定事項」に、スプリント番号と報告のパスつきで記録する。認められなかったものは designer への差し戻しとして扱う
5. ユーザーの了解を得て、スプリントの変更をコミットする（下の「ソース管理」）
6. **次のスプリントに自動で進まない。** ユーザーの指示を待つ。

### ソース管理

- **エージェントはコミットしない。** コミット・ブランチの操作・push は、メインセッションがユーザーの了解のもとで行う
- 既定は、スプリントの合格ごとに1コミット。ブランチの切り方（`main` に直接か、スプリントごとにブランチを切るか）、リリースのタグ、リモートへの push の決まりは、planner の初回の相談で決めて `docs/spec.md` の「技術スタック」に記録する
- 秘密情報（`.env*`）、ビルドの出力（`dist/`、`src-tauri/target/`）、E2E の記録（`test-results/`、`.playwright-mcp/`）はコミットしない。`.gitignore` は generator が Sprint 1 で用意する

### ユーザーの決定の記録

スプリントの途中でユーザーが仕様・デザイン・運用について判断を下したら、メインセッションはそれを **`docs/spec.md` の「ユーザー確定事項」に日付とスプリント番号付きで追記する。** 以降のエージェントはそこを読んで判断する。

- 記録するのはユーザーが明示した判断だけ。メインセッションの推測や提案を確定事項として書かない
- 既存の契約（`docs/sprints/sprint-N.md`）の内容を変える判断なら、書き換えは planner に依頼する

---

## 成果物とファイル配置

`docs/` は **プロジェクトルート直下の `docs/`** を指す（ファイルシステムのルートではない）。

```
src/                             # 画面（Vue）。OS の機能を直接使わない
├── api/                         # Rust のコマンドを呼ぶ型付きの関数（invoke はここだけで使う）
└── styles/tokens.css            # デザイントークンの CSS 変数（場所は generator が決めて報告する）
src-tauri/
├── src/
│   ├── main.rs                  # 起動。リリース版で WEBVIEW2_* を消す（下の「セキュリティ設定」）
│   ├── lib.rs                   # Builder の組み立て、debug 版だけの capability
│   ├── commands/                # #[tauri::command]。薄く保ち、ロジックを持たない
│   └── core/                    # 業務ロジック。tauri に依存せず cargo test できる
├── capabilities/                # 本番の権限（E2E だけで要る権限は置かない）
└── tauri.conf.json              # CSP、ウィンドウの最小サイズなど
tests/
├── unit/                        # generator が書く画面側のユニットテスト（配置はツールの流儀に合わせてよい）
└── e2e/                         # evaluator が書く E2E テスト（契約1条件ごと）。fixtures.ts は雛形に同梱
tools/
└── check-release.mjs            # リリース版の機械判定（デバッグポート・テスト用コードの混入）
docs/
├── spec.md                      # planner が生成（仕様・技術スタック・重点検査・ユーザー確定事項）
├── design-tokens.md             # デザインシステム（唯一の権威・改変禁止）
├── design-references/           # 参考画像（人間が配置する）。design-tokens.md を補う基準のファイルもここに置く
├── sprints/
│   └── sprint-N.md              # planner が生成（計画と契約）
└── reports/
    ├── planner-spec.md          # planner の報告（初回の計画。修正のたびに -2, -3 と連番）
    ├── sprint-N-planner.md      # planner の報告（スプリント N に関わる計画の修正）
    ├── sprint-N-generator.md    # 各エージェントの完了報告
    ├── sprint-N-designer.md
    └── sprint-N-evaluator.md
```

### 報告の保存（重要）

**各エージェントの完了報告は、受け取ったらメインセッションが `docs/reports/` に保存する。**

サブエージェントの作業ログはメインセッションのコンテキストに残らない。報告をファイル化しておかないと、次のエージェントに渡す情報も、差し戻し時の経緯も失われる。エージェントから報告が返ったら、要約せず **全文をそのまま** 保存すること。

同一スプリントで再実行した場合は上書きせず、`sprint-N-generator-2.md` のように連番を付ける。planner の報告も同じく保存する（技術スタックの候補、計画の修正の提案も含む）。

### 次のエージェントへの引き継ぎ

エージェントを起動するときのプロンプトには、必ず以下を含める：

- 対象スプリント番号と `docs/sprints/sprint-N.md` のパス
- 直前のエージェントの完了報告のパス（`docs/reports/...`）
- 差し戻しの場合は、evaluator の不合格報告全文

「前のエージェントの結果を見て」では伝わらない。**パスを明示する。**

---

## 固定の前提

| 項目 | 内容 |
|---|---|
| 対象 OS | **Windows**（WebView2）。E2E と Playwright MCP の接続が WebView2 の CDP に依存するため |
| フレームワーク | **Tauri 2** |
| 言語 | 画面は **TypeScript（strict）**、バックエンドは **Rust（stable）** |
| 画面のフレームワーク | **原則 Vue 3**（単一ファイルコンポーネント、`<script setup lang="ts">`）。別のものにするのは、ユーザーが明示的に決めた場合だけ |
| ビルドツール | **Vite**（Tauri の標準） |
| Rust の検査 | `cargo fmt --check`、`cargo clippy --all-targets -- -D warnings`、`cargo test` |
| E2E テスト | **Playwright Test** で debug 版の exe を起動し、`chromium.connectOverCDP` で接続する。evaluator が `tests/e2e/` に書く（`tests/e2e/fixtures.ts` は雛形に同梱） |
| 画面の確認・計測 | **Playwright MCP を起動中のアプリに接続**して行う（下の「Playwright MCP」） |
| デザイン | `docs/design-tokens.md` が唯一の権威 |
| 和文フォント | Noto Sans JP を **アプリに同梱**する |

画面側のユニットテスト・lint・状態管理・データベース・配布方法・パッケージマネージャーは planner と相談して決め、`docs/spec.md` の「技術スタック」に記録する。

### 共通のスクリプト名

使うツールが何であっても、`package.json` に **以下の名前でスクリプトを用意する**（generator が Sprint 1 で用意する）。エージェントはこの名前で実行する。以下 `npm run` と書くが、パッケージマネージャーは `docs/spec.md` で決めたものに読み替える。

| スクリプト | 内容 |
|---|---|
| `npm run typecheck` | 画面側の型チェック（`vue-tsc --noEmit`）と `cargo check` |
| `npm run lint` | 画面側の lint、`cargo fmt --check`、`cargo clippy --all-targets -- -D warnings` |
| `npm run test` | 画面側のユニットテストと `cargo test` |
| `npm run build:e2e` | E2E 用の debug 版 exe を作る（`tauri build --debug --no-bundle`。画面を exe に埋め込む） |
| `npm run test:e2e` | `build:e2e` のあと `playwright test`（`tests/e2e/`） |
| `npm run dev` | 開発用の起動（`tauri dev`） |
| `npm run dev:debug` | `tauri dev` を、環境変数 `WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--remote-debugging-port=9222` と、利用者のデータの場所を一時フォルダにする `APP_E2E_*` の変数をつけて起動する（Playwright MCP の接続用） |
| `npm run build` | リリース版の exe を作る（`tauri build --no-bundle`。インストーラーは作らない） |
| `npm run check:release` | `build` のあと `node tools/check-release.mjs`（下の「リリース版の機械判定」） |

**Rust のビルドは時間がかかる**（目安: debug の初回は数分、差分は十数秒〜1分、release は数分）。エージェントはビルドとテストをバックグラウンドで実行し、終わるのを待つ。タイムアウトで止まったものを「失敗」や「成功」と取り違えない。

### 2層の分離（設計の必須ルール）

- **Rust（`src-tauri/`）**: ファイルの読み書き、データベース、OS の機能、業務ロジック
  - 業務ロジックは `core/` に置き、**tauri に依存させない。** `cargo test` で画面なしにテストできる形で書く
  - `#[tauri::command]` は `commands/` に置き、入力の検証と `core/` の呼び出しだけを行う
- **画面（`src/`）**: Vue。**Rust の機能は `src/api/` の型付きの関数を通してだけ呼ぶ。** `invoke` を画面のコンポーネントから直接呼ばない
- コマンドの名前と、引数・戻り値の型は、Rust 側と `src/api/` の2か所で対応させる。どちらかを変えたら必ずもう一方も変える
- コマンドのエラーは、利用者に見せられる日本語の文字列（またはそれを持つ型）で返す。**コマンドの中で `unwrap` / `expect` / `panic!` を使わない**（リリース版は `panic = "abort"` のため、アプリごと落ちる）
- **OS のダイアログ（ファイルを開く・保存）は Rust 側から開く。** 選ばれたパスを画面側から Rust に渡す設計にしない（画面側を信頼しない）。ダイアログを開くコマンドは `async` にする（同期のコマンドはメインスレッドで動き、`blocking_*` で固まる）

### セキュリティ設定（厳守）

evaluator が機械判定する。1つでも違反があれば不合格。

- **capabilities は最小限。** 使う機能の権限だけを、使うウィンドウにだけ与える。各権限を何のために使うかを generator が完了報告に書く
  - fs などのプラグインを使う場合は、スコープを必要な場所に絞る。`*:default` を使う場合は、その中身を確かめて報告する
  - **データベースやファイルを画面側から直接触らせるプラグインの権限（SQL の実行、任意のパスの fs など）を画面に与えない。** その処理は Rust のコマンドに置く
  - `remote`（外部の URL に IPC を許す設定）を使わない
- **E2E だけで要る権限（ウィンドウのサイズ変更など）を `capabilities/` に置かない。** `setup` の中で `#[cfg(debug_assertions)]` を付けて `app.add_capability(tauri::ipc::CapabilityBuilder::new("debug-only-…"))` で足す。識別子は必ず `debug-only-` で始める
- **CSP を `tauri.conf.json` の `app.security.csp` に設定する**（`null` にしない）。`unsafe-eval` を許可しない。外部のスクリプト・スタイル・フォントを読み込まない
- `app.withGlobalTauri` を `true` にしない
- **Rust 側で、画面から受け取った値を検証する**（型、範囲、長さ、パスが想定の場所の中にあるか）。画面は信頼しない
- 外部リンクは opener プラグインで開き、開いてよい URL（`https:` と決まったドメインなど）を権限のスコープか Rust 側で絞る
- **リリース版では、`main` の最初で `WEBVIEW2_` で始まる環境変数をすべて消す。** 消さないと、`WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS` だけで配布版のデバッグポートが開き、外から画面を操作できてしまう（検証済み）。実装は次のとおり（`#[cfg(not(debug_assertions))]`、ほかのスレッドが無い `main` の冒頭で行う）

  ```rust
  #[cfg(not(debug_assertions))]
  fn strip_webview2_env() {
      let keys: Vec<_> = std::env::vars_os()
          .map(|(k, _)| k)
          .filter(|k| {
              k.to_string_lossy()
                  .to_ascii_uppercase()
                  .starts_with("WEBVIEW2_")
          })
          .collect();
      for k in keys {
          // SAFETY: main の冒頭で、ほかのスレッドがまだ無い時点で呼ぶ
          unsafe { std::env::remove_var(k) };
      }
  }
  ```
- **テストのための仕組み（下の「テストのためのデータの分離」「OS のダイアログの差し替え」）は `#[cfg(debug_assertions)]` の中にだけ書く。** リリース版の exe に含めない
- tauri の `devtools` feature をリリース版で有効にしない

### テストのためのデータの分離

- **テストのための環境変数は、名前を必ず `APP_E2E_` で始め、debug 版だけで読む**（`#[cfg(debug_assertions)]`）。リリース版の exe に名前の文字列が残らないことを `tools/check-release.mjs` で確かめる
- **利用者のデータを置く場所は、すべて debug 版で環境変数で差し替えられるようにする。** アプリの設定や状態は `app.path().app_data_dir()` の下に置き、`APP_E2E_DATA_DIR` などで差し替える。利用者が選ぶ保存先（書類のフォルダなど）が別にある場合は、それにも別の変数を用意する
- **debug 版の既定のデータの場所は、リリース版と別にする**（例: `app_data_dir()` の隣の `-dev` 付きのフォルダ）。開発中の確認で利用者の実データを汚さないため
- E2E テストと `dev:debug` での確認は、それらの場所をすべて一時フォルダにして行う
- 変数名は generator が決め、完了報告と `docs/spec.md` の技術スタックに記録する

### OS のダイアログの差し替え

- debug 版に限り、環境変数 `APP_E2E_DIALOG_STUB` が指すファイルがあれば、ダイアログを出さずに **その1行目を選ばれたパスとして使う**（空ならキャンセル）。E2E テストはクリックの前にそのファイルを書く
- generator はダイアログを開く処理を1か所の関数にまとめ、その中で差し替えを行う（下は形の例）

  ```rust
  #[cfg(debug_assertions)]
  fn dialog_stub() -> Option<Option<std::path::PathBuf>> {
      let stub = std::env::var_os("APP_E2E_DIALOG_STUB")?;
      let content = std::fs::read_to_string(stub).ok()?;
      let line = content.lines().next().unwrap_or("").trim();
      Some(if line.is_empty() {
          None
      } else {
          Some(line.into())
      })
  }
  ```
- 本物のダイアログが正しく開くこと（日本語のフィルター名、既定のファイル名）は自動では確かめられない。planner は契約の「人間の確認項目」に入れる

### Windows と日本語の前提

- **日本語・空白を含むパス**（例: `C:\Users\テスト ユーザー\書類`）で動くこと。evaluator の重点検査に必ず含める
- Rust ではパスを `PathBuf` / `Path::join` で組み立て、区切り文字を文字列で書かない。`to_str().unwrap()` で文字列にしない
- テキストファイルの読み書きは UTF-8 を前提にし、UTF-8 でないときは日本語のエラーを返す
- ユーザーに見せるエラーメッセージは、何が起きて何をすればよいかが分かる日本語にする。生のエラーやスタックトレースを画面に出さない

### 配布用ビルド

- planner との相談で **「配布する」と決めたプロジェクトだけ**、配布のためのスプリントを最後に設け、次を契約に入れる
  - インストーラーの作成（`tauri build`。NSIS か MSI かは planner と相談）が成功し、インストールしたアプリが起動する
  - **インストールしたアプリで `tools/check-release.mjs` が通る**（デバッグポートが開かない、テスト用のコードが入っていない）
  - 右クリックやショートカットで開発者ツールが開かない
  - 秘密情報・テストのコード・開発用の依存がインストーラーに含まれていない
  - コード署名・自動更新（updater プラグイン）を使うかどうかは planner と相談する。署名の鍵の作成と保管はユーザーが行い、エージェントは鍵の値を読まない
- それ以外のスプリントでは、インストーラーは作らない。`npm run check:release` が通ることを毎回確認する

### データベース

使うかどうか・何を使うかは planner と相談して決める。

- ローカルに保存する場合（SQLite など）、ファイルは `app_data_dir()` の下に置く。**データベースの処理は Rust 側に置き、画面から SQL を実行させない**
- Turso を使う場合は、generator の `tools:` に Turso MCP のツール（`mcp__mcp-turso-cloud__*`）を追記し、Turso CLI は使わない。データベースの作成・削除・トークンの発行はユーザーが行う。**接続情報を画面に渡さない**
- **スキーマを作った・変えたら、generator は完了報告に DDL をそのまま書く**

### 秘密情報

- 秘密情報は `.env` などに置き、**値をコード・テスト・完了報告・コミット・スクリーンショットのどこにも書かない。** 環境変数として参照するだけにする
- `.env*` をコミットしない
- **秘密情報を画面に渡さない。配布するアプリに埋め込まない**（埋め込みが必要になる設計なら、完了報告に書いてユーザーの判断を仰ぐ）
- メインセッションも秘密情報の値を読まない・表示しない

---

## 前提条件のチェック

パイプラインを回す前に確認し、欠けていればユーザーに伝える。

- `cargo --version` が通る（Rust の stable、`x86_64-pc-windows-msvc`）
- Visual Studio Build Tools の C++（`Microsoft.VisualStudio.Workload.VCTools`）が入っている
- WebView2 Runtime が入っている（Windows 11 は標準で入っている）
- Node.js が入っている

### Playwright MCP

`designer` と `evaluator` は Playwright MCP を **起動中の Tauri アプリ（WebView2）に接続して** 使う。

**Playwright は各エージェントの frontmatter に `mcpServers` としてインライン定義されている**（`--cdp-endpoint http://localhost:9222` 付き）。セッション側の設定に依存せず、エージェント起動時に立ち上がり、終了時に切断される。CDP への接続は最初のブラウザ操作のときに行われるので、MCP サーバーが先に立ち上がっていても、アプリを後から起動すれば接続できる。

- **メインセッションから playwright ツールを呼ばない。** 画面の確認が必要なら designer / evaluator に委譲する
- セッション側に `claude mcp add` で playwright を追加する必要はない
- エージェントは **先に `npm run dev:debug` でアプリを起動してから** playwright ツールを呼ぶ。起動すると `http://localhost:9222/json/version` が `Edg/…` を返す
- **接続した直後のページが `about:blank` のことがある。** 最初にスナップショットを取り、アプリの画面でなければ少し待ってから取り直す
- **MCP の `browser_resize` は表示領域のエミュレーションだけで、ネイティブのウィンドウの大きさは変わらない**（検証済み）。ウィンドウサイズの確認は E2E テストで行う（下の「ウィンドウサイズの確認」）
- **OS のダーク／ライト設定で computed style が変わる。** 計測の前に、どちらの配色で測るかを決めて固定する（E2E では `page.emulateMedia({ colorScheme })`）
- 初回起動時に `npx` がパッケージを取得するため、初回だけ待ち時間が発生する
- **ポート 9222 をほかのアプリ（デバッグ用に起動した Chrome など）が使っていると接続先を取り違える。** 起動前に空いていることを確認する
- 作業が終わったら、起動したアプリ（`tauri dev` が立ち上げた Vite のサーバーも）を終了し、ポート 9222 が空いていることを確かめる

#### 接続できない場合（逃げ道）

MCP がアプリに接続できない場合、designer / evaluator は **確認済みと偽装せず**、次の方法に切り替える。

- Playwright で debug 版の exe を起動して `connectOverCDP` で接続するスクリプトを書き（`tests/e2e/fixtures.ts` の `launchApp` と同じ方法）、**スクリーンショットと computed style をその中で取得して** 確認する
  - evaluator は `tests/e2e/` の中で行う
  - designer は `tests/e2e/` を編集できないので、`scripts/design-check/` に確認用のスクリプトを置いて実行する（`tests/e2e/fixtures.ts` を import して使ってよい）
- 完了報告に「MCP 未接続のためスクリプトで確認した」と、その原因として分かったことを明記する
- **スクリプトでも確認できなかった項目を「確認済み」「合格」と書かない。** evaluator がデザインを実測できなかった場合、その出力を合格扱いにしない

接続できない状態が続く場合は、`npx -y @playwright/mcp@latest --version` が通るか、`npm run dev:debug` の起動後に `http://localhost:9222/json/version` が応答するかを、ユーザーに確認してもらう。

### リリース版の機械判定

リリース版はデバッグポートを塞いでいるので、外から操作して確かめることはできない。代わりに `tools/check-release.mjs`（雛形に同梱）で次を確かめる。

- 環境変数 `WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--remote-debugging-port=…` を渡して起動しても、アプリは起動したままポートが応答しない
- exe の中に、`APP_E2E_` と `debug-only-` の文字列が含まれていない（テストのための仕組みと debug 版だけの権限が混入していない）

使い方: `node tools/check-release.mjs [exe のパス]`（省略すると `src-tauri/target/release/` の exe を使う）。終了コード 0 が合格。

### デザインシステム

**`docs/design-tokens.md`** がこのプロジェクト唯一のデザイン権威。人間が用意した資産であり、**メインセッションもサブエージェントも改変してはならない。**

- `designer` は必ず `docs/design-tokens.md` を全文読んでから作業する。特に **Do's and Don'ts セクションは禁止事項としてそのまま適用する**
- `evaluator` は期待値を書き起こし、機械的に検査する。期待値の決め方は下の「トークンの扱い」による
- `generator` は見た目を作り込まないが、後で designer がトークンを流し込めるよう、**色やサイズをコンポーネント内にハードコードせず CSS 変数に寄せておく**
- ユーザーが「docs/design-tokens.md を変えたい」と言わない限り、契約と同様に不可侵
- **`docs/design-tokens.md` が無いまま designer を起動しない。** 無ければユーザーに用意を依頼する

`docs/design-references/` が空でも designer は動く（`docs/design-tokens.md` の記述だけで作業可能）。その場合、参考画像が無かったことが完了報告に明記される。

#### トークンの扱い（厳格／報告制）

`docs/design-tokens.md` がこのアプリのために書かれたものか、別の用途（Web サイトなど）のものを流用しているかで、扱いを変える。**planner が初回の相談で確かめ、`docs/spec.md` の「デザインの扱い」に記録する。**

| | 厳格 | 報告制 |
|---|---|---|
| 向く場合 | トークンがこのアプリ向けに書かれている | トークンを別の用途から流用している。アプリに必要な値（文字の大きさ、状態の色、強い影など）が定義されていない |
| designer | トークンの値を変えない。定義が無い値は既存のトークンから最も近いものを選ぶ。新しい値を発明しない | トークンを「見た目のイメージの基準」として扱い、アプリに合わせた調整と、定義が無い値の補いをしてよい。まず既存のトークンから選び、足りないときだけ新しい値を決める |
| designer の報告 | 既存のトークンから選んだ箇所を「トークン外の判断」に書く | **変えた点・決めた点を、元の値・変えた値・理由つきで、すべて「トークン外の判断」に書く** |
| evaluator の期待値 | `docs/design-tokens.md` + 「ユーザー確定事項」 | `docs/design-tokens.md` + 「ユーザー確定事項」+ **designer が報告した「トークン外の判断」** |
| 違反 | 期待値との食い違いが1つでもあれば「デザインの質」は 5/10 以下 | **報告されていない食い違い** が1つでもあれば「デザインの質」は 5/10 以下。報告済みでユーザーの確認がまだのものは違反と数えず、「確認待ち」として報告に挙げる |
| 合格後 | — | メインセッションが「トークン外の判断」をユーザーに提示し、認められたものを「ユーザー確定事項」に記録する（「スプリント完了時」の手順） |

どちらの場合も、色・角丸・影・余白の考え方と Do's and Don'ts は基準としてそのまま尊重し、スプリント契約には具体的なデザイン値（色・大きさ）を書かない。

#### トークンを補う基準のファイル

`docs/design-tokens.md` が定義しない配色や状態（例: ダークの配色、状態を表す色の方針）に人間が基準を用意する場合は、**`docs/design-references/` にファイルとして置き、ここにファイル名と役割を書き足す。** designer と evaluator はそのファイルも `docs/design-tokens.md` と同じ資産として扱う（改変しない、期待値に含める）。

- 例: 配色が2組（ライトとダーク）あるアプリでは、`docs/design-references/dark-palette.md` に「ライトとダークの対応」の表を置き、designer と evaluator は両方の配色で確認・実測する（ウィンドウサイズの確認も配色ごとに行う）
- 配色が1組だけのアプリでも、OS のダーク設定で画面が崩れないこと（配色を固定するか、両方に対応するか）は planner が仕様で決める

デザインシステムが Web サイト向けに書かれている場合、スマホ幅のレスポンシブ規定やマーケティング用のコンポーネントはデスクトップアプリには当てはまらない。どう読み替えたかは designer が完了報告の「トークン外の判断」に書き、ユーザーが判断を下したら `docs/spec.md` の「ユーザー確定事項」に記録する。

#### Vue でのスタイルの書き方

- **色・フォントサイズ・角丸・余白・影は、CSS 変数として1つのファイルにまとめる**（例: `src/styles/tokens.css`）。場所は generator が決めて完了報告に書く
- 各コンポーネントは `<style scoped>` の中で CSS 変数を参照する。**hex や px の値をコンポーネントに直接書かない**（1px の罫線など、トークンに無い構造上の値を除く）
- インラインの `style` 属性で見た目を指定しない（計算で決まる値を `:style` で渡す場合を除く）
- **designer が触ってよいのは、トークンのファイル、`<style>` ブロック、そして `<template>` のうちスタイルに必要な最小限（クラスの付け外し、包む要素の追加）だけ。** `<script>` ブロックと Rust のコードは触らない。ウィンドウの最小サイズを変えるときだけ `tauri.conf.json` の `minWidth` / `minHeight` を触ってよい
- E2E テストが要素を特定するための **`data-testid` は generator が付け、designer は消さない・変えない**

#### ウィンドウサイズの確認（レスポンシブの代わり）

- **`tauri.conf.json` のウィンドウに最小サイズ（`minWidth` / `minHeight`）を必ず設定する。** 値は generator が仮に決め、designer が画面の内容に合わせて調整してよい
- 次の3つで、崩れ・はみ出し・意図しない横スクロールがないこと：**最小サイズ／起動時の既定サイズ／最大化**。配色が複数あるアプリでは、配色ごとに行う
- ウィンドウのサイズ変更は、E2E テストやスクリプトから Tauri の window のコマンドを呼んで行う（`window.__TAURI_INTERNALS__.invoke("plugin:window|set_size", { label: "main", value: { Logical: { width, height } } })`、`plugin:window|maximize`）。そのための権限（`core:window:allow-set-size`・`allow-maximize`・`allow-unmaximize`）は、generator が Sprint 1 で **debug 版だけの capability**（上の「セキュリティ設定」）として足す

#### 和文フォント（design-tokens.md の欠落を埋める規定）

デザインシステムが欧文専用で日本語を規定していない場合、UI の日本語には以下を適用する。**designer はこれに従い、evaluator は機械判定の対象に含める。**

- **和文は Noto Sans JP。フォントファイルをアプリに同梱し、`@font-face` でローカルから読み込む。** Google Fonts などの外部から読み込むのは違反（オフラインで游ゴシックに切り替わり、細いウェイトの小さい文字が霞んで読めなくなるため。CSP でも外部のフォントを許可しない）
- 同梱するのは、実際に使うウェイトだけにする
- **欧文・数字は design-tokens.md 指定の欧文フォント。これも同梱する。** スタックは `<欧文フォント>, "Noto Sans JP", sans-serif` の順にし、数字が欧文フォントで描画されるようにする
- **游ゴシック / Yu Gothic / MS PGothic へのフォールバックは違反**
- **13px 以下の文字は weight 400 以上。** 和文は欧文より小サイズでの可読性が落ちるため、300 以下で描画しない
- **見出し（display 系）のウェイトは design-tokens.md の定義どおり維持する**
- 小サイズの可読性をさらに上げたい場合の代替は **BIZ UDPGothic**

evaluator の確認方法: `document.fonts` で Noto Sans JP が `loaded` になっていること、フォントの読み込み元が外部でないこと、13px 以下の要素の computed `font-weight` が 400 以上であること、`font-family` に游ゴシック系が含まれていないこと。

---

## 公開後の運用

アプリを配布・公開したあとに寄せられる意見・不具合の報告は、このパイプラインの外で受け取る。受け取ったら次の形で扱う。

- 台帳は `docs/issues/` に置く。報告者の個人情報（名前・メールアドレス・表示名）は書かず、番号に置き換える
- 整理の手順（分類・重さ・仕様との照合・重複の確認・返信の下書き）は、必要になった時点で `.claude/skills/` にスキルとして足す。**直すかどうか・優先順位を決めるのはユーザー**
- 直すと決めたものは、planner に新しいスプリントとして計画させる（合格済みの契約は書き換えない）

---

## やってはいけないこと

- メインセッションが実装・スタイリングを肩代わりする
- evaluator を飛ばして「合格」とする
- evaluator の不合格を「軽微だから」と握りつぶす
- スプリント契約をメインセッションの判断で書き換える・緩める
- 技術スタックをユーザーに確認せずに決める
- `docs/design-tokens.md` を書き換える（人間の資産。変更依頼があった場合のみ）
- `docs/design-tokens.md` が無いまま designer を起動する
- generator / designer が `tests/e2e/` を編集して合格させる
- generator だけに差し戻したあと、designer を通さずに evaluator を呼ぶ
- エージェントがコミットする。メインセッションがユーザーの了解なしにコミット・push する
- セキュリティ設定を「開発中だから」と緩める。E2E のための権限やテスト用の仕組みを、`#[cfg(debug_assertions)]` の外に置く
- 報告制のとき、designer が報告していないトークンからの調整を evaluator が見逃す。厳格のとき、designer がトークンに無い値を発明する
- 4エージェントを並列起動する（順序に意味がある）
- 完了報告を要約してファイル保存する（全文を残す）
- 画面を実測できていない evaluator の出力を合格扱いにする
- Rust のビルドがタイムアウトで止まったのを、成功や失敗と取り違えて報告する
- 秘密情報の値を読んで表示する・どこかに書く
- ユーザーが言っていないことを `docs/spec.md` の「ユーザー確定事項」に書く
