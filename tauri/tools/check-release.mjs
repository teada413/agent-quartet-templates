#!/usr/bin/env node
// リリース版の Tauri アプリ（Windows）の機械判定。
//
// 1. WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS でデバッグポートを指定して起動しても、
//    アプリは起動したまま、ポートが応答しないこと
// 2. exe の中に、テストのための仕組み（APP_E2E_）と debug 版だけの権限（debug-only-）の
//    文字列が含まれていないこと
//
// 使い方: node tools/check-release.mjs [exe のパス]
//   exe のパスを省略すると src-tauri/target/release/ の exe を使う。終了コード 0 が合格。

import { spawn } from "node:child_process";
import { existsSync, mkdtempSync, readdirSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

const FORBIDDEN = ["APP_E2E_", "debug-only-"];
const PORT = 9400 + Math.floor(Math.random() * 400);

function findExe() {
  const dir = path.resolve("src-tauri/target/release");
  if (!existsSync(dir)) return null;
  const exes = readdirSync(dir).filter((f) => f.toLowerCase().endsWith(".exe"));
  return exes.length === 1 ? path.join(dir, exes[0]) : null;
}

const exe = process.argv[2] ? path.resolve(process.argv[2]) : findExe();
if (!exe || !existsSync(exe)) {
  console.error("exe が見つかりません。`npm run build` のあとに実行するか、パスを指定してください。");
  process.exit(2);
}

let failed = false;
const report = (ok, label, detail = "") => {
  if (!ok) failed = true;
  console.log(`${ok ? "OK  " : "NG  "} ${label}${detail ? ` — ${detail}` : ""}`);
};

// 2. 文字列の検査（UTF-8 と UTF-16LE の両方で探す）
const bin = readFileSync(exe);
for (const s of FORBIDDEN) {
  const found =
    bin.includes(Buffer.from(s, "utf8")) || bin.includes(Buffer.from(s, "utf16le"));
  report(!found, `exe に "${s}" が含まれていない`);
}

// 1. デバッグポートの検査
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function portResponds() {
  try {
    const res = await fetch(`http://127.0.0.1:${PORT}/json/version`, {
      signal: AbortSignal.timeout(1000),
    });
    return res.ok;
  } catch {
    return false;
  }
}

const dataDir = mkdtempSync(path.join(tmpdir(), "check-release-"));
const proc = spawn(exe, [], {
  env: {
    ...process.env,
    WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS: `--remote-debugging-port=${PORT}`,
    // リリース版は無視するはずの変数。読んでしまう場合に利用者の実データを汚さないよう一時フォルダを渡す
    APP_E2E_DATA_DIR: dataDir,
  },
  stdio: "ignore",
});
let exited = false;
proc.once("exit", () => (exited = true));

let opened = false;
for (let i = 0; i < 20 && !opened; i++) {
  await sleep(500);
  opened = await portResponds();
}
report(!exited, "アプリが起動したままである", exited ? `終了コード ${proc.exitCode}` : "");
report(!opened, `デバッグポート ${PORT} が応答しない`);

if (!exited) {
  proc.kill();
  await new Promise((r) => proc.once("exit", r));
}
rmSync(dataDir, { recursive: true, force: true });

console.log(failed ? "\n不合格" : "\n合格");
process.exit(failed ? 1 : 0);
