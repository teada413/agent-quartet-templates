// Tauri アプリ（Windows / WebView2）の E2E テストのフィクスチャ。雛形に同梱。evaluator が拡張してよい。
//
// Playwright には Tauri を起動する仕組みが無いので、debug 版の exe を子プロセスで起動し、
// WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS でデバッグポートを開いて connectOverCDP する。
// exe は `npm run build:e2e`（tauri build --debug --no-bundle）で作る。
//
// 前提（CLAUDE.md「テストのためのデータの分離」「OS のダイアログの差し替え」）:
// - debug 版は APP_E2E_DATA_DIR でデータの場所を差し替えられる
// - debug 版は APP_E2E_DIALOG_STUB が指すファイルの1行目を、ダイアログで選ばれたパスとして使う（空ならキャンセル）
// generator が別の変数名を決めた場合は、generator の完了報告に合わせてここを直す。

import { test as base, chromium, type Browser, type Page } from "@playwright/test";
import { spawn, type ChildProcess } from "node:child_process";
import { existsSync, mkdtempSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

function findDebugExe(): string {
  if (process.env.APP_EXE) return path.resolve(process.env.APP_EXE);
  const dir = path.resolve("src-tauri/target/debug");
  const exes = existsSync(dir) ? readdirSync(dir).filter((f) => f.toLowerCase().endsWith(".exe")) : [];
  if (exes.length !== 1) {
    throw new Error(
      `debug 版の exe を1つに特定できません（${dir}: ${exes.join(", ") || "なし"}）。` +
        "`npm run build:e2e` を実行するか、環境変数 APP_EXE で指定してください。",
    );
  }
  return path.join(dir, exes[0]);
}

async function waitForCdp(port: number, timeoutMs = 30_000): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(`http://127.0.0.1:${port}/json/version`);
      if (res.ok) return;
    } catch {
      /* まだ起動していない */
    }
    await new Promise((r) => setTimeout(r, 250));
  }
  throw new Error(`CDP のポート ${port} が ${timeoutMs}ms 以内に応答しませんでした`);
}

export type TauriApp = {
  proc: ChildProcess;
  browser: Browser;
  page: Page;
  close: () => Promise<void>;
};

/** ダイアログの差し替え用ファイルのパス */
export const dialogStubFile = (dataDir: string) => path.join(dataDir, "dialog-stub.txt");

/** 次に開くダイアログの結果を決める。null ならキャンセル */
export const setDialogResult = (dataDir: string, picked: string | null) =>
  writeFileSync(dialogStubFile(dataDir), picked ?? "", "utf8");

let nextPort = 9300;
export const allocPort = () => nextPort++;

export async function launchApp(opts: {
  dataDir: string;
  port?: number;
  env?: Record<string, string>;
}): Promise<TauriApp> {
  const port = opts.port ?? allocPort();
  const proc = spawn(findDebugExe(), [], {
    env: {
      ...process.env,
      WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS: `--remote-debugging-port=${port}`,
      APP_E2E_DATA_DIR: opts.dataDir,
      APP_E2E_DIALOG_STUB: dialogStubFile(opts.dataDir),
      ...opts.env,
    },
    stdio: "ignore",
  });
  await waitForCdp(port);
  const browser = await chromium.connectOverCDP(`http://127.0.0.1:${port}`);
  const context = browser.contexts()[0];
  const page = context.pages()[0] ?? (await context.waitForEvent("page"));
  // 接続した直後は about:blank のことがある。アプリの画面（http://tauri.localhost/）に移って
  // 読み込みが終わるのを待たないと「Execution context was destroyed」で落ちる（検証済み）
  await page.waitForURL(/^http:\/\/tauri\.localhost\//, { waitUntil: "load" });
  const close = async () => {
    await browser.close().catch(() => {});
    if (proc.exitCode === null) {
      proc.kill();
      await new Promise((r) => proc.once("exit", r));
    }
  };
  return { proc, browser, page, close };
}

/** ネイティブのウィンドウの大きさを変える（debug 版だけの capability が必要） */
export async function setWindowSize(page: Page, width: number, height: number) {
  await page.evaluate(
    ([w, h]) =>
      (window as any).__TAURI_INTERNALS__.invoke("plugin:window|set_size", {
        label: "main",
        value: { Logical: { width: w, height: h } },
      }),
    [width, height] as const,
  );
  await page.waitForFunction(([w]) => Math.abs(window.innerWidth - w) <= 2, [width] as const);
}

/** ウィンドウを最大化する（debug 版だけの capability が必要） */
export async function maximizeWindow(page: Page) {
  const before = await page.evaluate(() => window.innerWidth);
  await page.evaluate(() =>
    (window as any).__TAURI_INTERNALS__.invoke("plugin:window|maximize", { label: "main" }),
  );
  await page.waitForFunction((b) => window.innerWidth > b, before);
}

export const test = base.extend<{ dataDir: string; app: TauriApp }>({
  dataDir: async ({}, use) => {
    // 日本語と空白を含む一時フォルダ
    const dir = mkdtempSync(path.join(tmpdir(), "テスト データ-"));
    await use(dir);
    rmSync(dir, { recursive: true, force: true });
  },
  app: async ({ dataDir }, use) => {
    const app = await launchApp({ dataDir });
    await use(app);
    await app.close();
  },
});

export { expect } from "@playwright/test";
