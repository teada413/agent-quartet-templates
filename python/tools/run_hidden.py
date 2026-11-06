"""画面に出ない別の Windows デスクトップの上で Python のコマンドを実行する。

テストの実行中も利用者が同じ PC で作業できるよう、Tk のウィンドウを作るテストや
``--smoke`` を、``CreateDesktopW`` で作った非表示のデスクトップの上で動かす。
透明化と画面外への配置だけでは、ウィンドウを表示した時点で前面のウィンドウが替わり、
フォーカスを奪うため（実測済み）。

使い方（このスクリプトを実行した Python で、残りの引数をそのまま実行する）::

    .venv/Scripts/python tools/run_hidden.py -m pytest
    .venv/Scripts/python tools/run_hidden.py -m pytest tests/unit -q
    .venv/Scripts/python tools/run_hidden.py -m <パッケージ名> --smoke
    .venv/Scripts/python tools/run_hidden.py --timeout 600 -m pytest

- 子プロセスの標準出力・標準エラーは、そのまま（バイト列のまま）この標準出力・標準エラーに流す
- 終了コードは子プロセスの終了コードをそのまま返す
- 子プロセスとその子孫はジョブにまとめ、このランナーが終わる・時間切れになると一緒に終わらせる
- ``--timeout`` 秒を過ぎたら子プロセスを終わらせ、終了コード 124 を返す
- 子プロセスの ``PYTHONIOENCODING`` が未設定なら ``utf-8`` にする（日本語の出力を壊さないため）

標準ライブラリ（ctypes）だけを使う。Windows 専用。
"""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import threading
from ctypes import wintypes
from typing import BinaryIO, TextIO

DESKTOP_NAME_FORMAT = "python_gui_hidden_{pid}"
DESKTOP_ALL_ACCESS = 0x01FF | 0x000F0000
"""デスクトップへのすべての権限（DESKTOP_* の全ビットと STANDARD_RIGHTS_REQUIRED）。"""
STARTF_USESTDHANDLES = 0x00000100
CREATE_SUSPENDED = 0x00000004
CREATE_NO_WINDOW = 0x08000000
CREATE_UNICODE_ENVIRONMENT = 0x00000400
INFINITE = 0xFFFFFFFF
WAIT_OBJECT_0 = 0
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS = 9
MILLISECONDS_PER_SECOND = 1000
TIMEOUT_EXIT_CODE = 124
"""時間切れで子プロセスを終わらせたときの終了コード（GNU timeout と同じ）。"""
USAGE_EXIT_CODE = 2
FAILURE_EXIT_CODE = 1
COPY_CHUNK_SIZE = 65536
IO_ENCODING_VARIABLE = "PYTHONIOENCODING"
IO_ENCODING_DEFAULT = "utf-8"
TIMEOUT_OPTION = "--timeout"
HELP_OPTIONS = ("-h", "--help")
USAGE = (
    "使い方: python tools/run_hidden.py [--timeout 秒] <Python に渡す引数...>\n"
    "例: .venv/Scripts/python tools/run_hidden.py -m pytest\n"
)


class STARTUPINFOW(ctypes.Structure):
    """Win32 の STARTUPINFOW 構造体。"""

    _fields_ = [
        ("cb", wintypes.DWORD),
        ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR),
        ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD),
        ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD),
        ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD),
        ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD),
        ("cbReserved2", wintypes.WORD),
        ("lpReserved2", ctypes.c_void_p),
        ("hStdInput", wintypes.HANDLE),
        ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
    ]


class PROCESS_INFORMATION(ctypes.Structure):  # noqa: N801  Win32 の構造体名に合わせる
    """Win32 の PROCESS_INFORMATION 構造体。"""

    _fields_ = [
        ("hProcess", wintypes.HANDLE),
        ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD),
    ]


class IO_COUNTERS(ctypes.Structure):  # noqa: N801  Win32 の構造体名に合わせる
    """Win32 の IO_COUNTERS 構造体。"""

    _fields_ = [
        ("ReadOperationCount", ctypes.c_ulonglong),
        ("WriteOperationCount", ctypes.c_ulonglong),
        ("OtherOperationCount", ctypes.c_ulonglong),
        ("ReadTransferCount", ctypes.c_ulonglong),
        ("WriteTransferCount", ctypes.c_ulonglong),
        ("OtherTransferCount", ctypes.c_ulonglong),
    ]


class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):  # noqa: N801  Win32 の構造体名に合わせる
    """Win32 の JOBOBJECT_BASIC_LIMIT_INFORMATION 構造体。"""

    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_longlong),
        ("PerJobUserTimeLimit", ctypes.c_longlong),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):  # noqa: N801  Win32 の構造体名に合わせる
    """Win32 の JOBOBJECT_EXTENDED_LIMIT_INFORMATION 構造体。"""

    _fields_ = [
        ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("IoInfo", IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_user32 = ctypes.WinDLL("user32", use_last_error=True)

_user32.CreateDesktopW.restype = wintypes.HANDLE
_user32.CreateDesktopW.argtypes = [
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    ctypes.c_void_p,
    wintypes.DWORD,
    wintypes.DWORD,
    ctypes.c_void_p,
]
_user32.CloseDesktop.restype = wintypes.BOOL
_user32.CloseDesktop.argtypes = [wintypes.HANDLE]
_kernel32.CreateProcessW.restype = wintypes.BOOL
_kernel32.CreateProcessW.argtypes = [
    wintypes.LPCWSTR,
    wintypes.LPWSTR,
    ctypes.c_void_p,
    ctypes.c_void_p,
    wintypes.BOOL,
    wintypes.DWORD,
    ctypes.c_void_p,
    wintypes.LPCWSTR,
    ctypes.POINTER(STARTUPINFOW),
    ctypes.POINTER(PROCESS_INFORMATION),
]
_kernel32.CreateJobObjectW.restype = wintypes.HANDLE
_kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
_kernel32.SetInformationJobObject.restype = wintypes.BOOL
_kernel32.SetInformationJobObject.argtypes = [
    wintypes.HANDLE,
    ctypes.c_int,
    ctypes.c_void_p,
    wintypes.DWORD,
]
_kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
_kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
_kernel32.TerminateJobObject.restype = wintypes.BOOL
_kernel32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
_kernel32.TerminateProcess.restype = wintypes.BOOL
_kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
_kernel32.ResumeThread.restype = wintypes.DWORD
_kernel32.ResumeThread.argtypes = [wintypes.HANDLE]
_kernel32.WaitForSingleObject.restype = wintypes.DWORD
_kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
_kernel32.GetExitCodeProcess.restype = wintypes.BOOL
_kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
_kernel32.CloseHandle.restype = wintypes.BOOL
_kernel32.CloseHandle.argtypes = [wintypes.HANDLE]


class HiddenRunError(Exception):
    """ランナー自身の失敗（デスクトップやプロセスを作れなかった）。"""


def _win_error(what: str) -> HiddenRunError:
    code = ctypes.get_last_error()
    return HiddenRunError(f"{what}に失敗しました（Windows のエラー {code}）。")


def _write_message(stream: TextIO, text: str) -> None:
    """ランナー自身の案内を、子プロセスの出力と同じ文字コードで書く。

    ``PYTHONIOENCODING`` が未設定なら子プロセスは UTF-8 で書くので、こちらも UTF-8 にそろえる。
    """
    stream.flush()
    if IO_ENCODING_VARIABLE in os.environ:
        stream.write(text)
        stream.flush()
    else:
        stream.buffer.write(text.encode(IO_ENCODING_DEFAULT))
        stream.buffer.flush()


def parse_args(argv: list[str]) -> tuple[float | None, list[str]]:
    """ランナーの引数を、時間切れの秒数と Python に渡す引数に分ける。

    Args:
        argv: スクリプト名を除いた引数。

    Returns:
        時間切れの秒数（指定なしなら ``None``）と、Python に渡す引数。

    Raises:
        ValueError: 引数が足りない、または秒数が正しくない場合。
    """
    timeout: float | None = None
    rest = list(argv)
    if rest[:1] and rest[0] == TIMEOUT_OPTION:
        if len(rest) < 2:
            raise ValueError(f"{TIMEOUT_OPTION} の後に秒数を指定してください。")
        try:
            timeout = float(rest[1])
        except ValueError:
            raise ValueError(f"{TIMEOUT_OPTION} の秒数が正しくありません: {rest[1]}") from None
        if timeout <= 0:
            raise ValueError(f"{TIMEOUT_OPTION} の秒数は 0 より大きくしてください: {rest[1]}")
        rest = rest[2:]
    if not rest:
        raise ValueError("Python に渡す引数を指定してください。")
    return timeout, rest


def _environment_block() -> ctypes.Array[ctypes.c_wchar]:
    """子プロセスの環境変数のブロック（UTF-16、``名前=値`` を NUL で区切る）を作る。"""
    env = dict(os.environ)
    env.setdefault(IO_ENCODING_VARIABLE, IO_ENCODING_DEFAULT)
    entries = sorted(f"{key}={value}" for key, value in env.items())
    block = "\0".join(entries) + "\0\0"
    return ctypes.create_unicode_buffer(block, len(block))


def _inheritable_handle(fd: int) -> int:
    """ファイル記述子の OS のハンドルを取り出し、子プロセスに引き継げるようにする。"""
    import msvcrt

    handle = msvcrt.get_osfhandle(fd)
    os.set_handle_inheritable(handle, True)
    return handle


def _pump(source_fd: int, target: BinaryIO) -> None:
    """パイプから読んだバイト列を、そのまま ``target`` に書き続ける（EOF まで）。"""
    with open(source_fd, "rb", buffering=0) as source:
        while True:
            chunk = source.read(COPY_CHUNK_SIZE)
            if not chunk:
                break
            target.write(chunk)
            target.flush()


def _create_job() -> int:
    """閉じると中のプロセスをすべて終わらせるジョブを作る。"""
    job = _kernel32.CreateJobObjectW(None, None)
    if not job:
        raise _win_error("ジョブの作成")
    info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
    info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not _kernel32.SetInformationJobObject(
        job,
        JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS,
        ctypes.byref(info),
        ctypes.sizeof(info),
    ):
        _kernel32.CloseHandle(job)
        raise _win_error("ジョブの設定")
    return int(job)


def run_hidden(python_args: list[str], timeout: float | None = None) -> int:
    """非表示のデスクトップの上で ``sys.executable`` に引数を渡して実行する。

    Args:
        python_args: Python に渡す引数（例: ``["-m", "pytest"]``）。
        timeout: 時間切れの秒数。``None`` なら無制限。

    Returns:
        子プロセスの終了コード（時間切れなら 124）。

    Raises:
        HiddenRunError: デスクトップ・ジョブ・プロセスを作れなかった場合。
    """
    desktop_name = DESKTOP_NAME_FORMAT.format(pid=os.getpid())
    desktop = _user32.CreateDesktopW(desktop_name, None, None, 0, DESKTOP_ALL_ACCESS, None)
    if not desktop:
        raise _win_error("非表示のデスクトップの作成")
    job = 0
    try:
        job = _create_job()
        return _run_on_desktop(desktop_name, job, python_args, timeout)
    finally:
        if job:
            _kernel32.CloseHandle(job)
        _user32.CloseDesktop(desktop)


def _run_on_desktop(
    desktop_name: str, job: int, python_args: list[str], timeout: float | None
) -> int:
    """デスクトップを指定して子プロセスを作り、出力を流しながら終わるのを待つ。"""
    command_line = subprocess.list2cmdline([sys.executable, *python_args])
    out_read, out_write = os.pipe()
    err_read, err_write = os.pipe()
    stdin_file = open(os.devnull, "rb")  # noqa: SIM115  子プロセスの起動後まで開いておく
    pumps = [
        threading.Thread(target=_pump, args=(out_read, sys.stdout.buffer), daemon=True),
        threading.Thread(target=_pump, args=(err_read, sys.stderr.buffer), daemon=True),
    ]
    startup = STARTUPINFOW()
    startup.cb = ctypes.sizeof(STARTUPINFOW)
    desktop_buffer = ctypes.create_unicode_buffer(desktop_name)
    startup.lpDesktop = ctypes.cast(desktop_buffer, wintypes.LPWSTR)
    startup.dwFlags = STARTF_USESTDHANDLES
    process = PROCESS_INFORMATION()
    environment = _environment_block()
    try:
        startup.hStdInput = _inheritable_handle(stdin_file.fileno())
        startup.hStdOutput = _inheritable_handle(out_write)
        startup.hStdError = _inheritable_handle(err_write)
        created = _kernel32.CreateProcessW(
            None,
            ctypes.create_unicode_buffer(command_line),
            None,
            None,
            True,
            CREATE_SUSPENDED | CREATE_NO_WINDOW | CREATE_UNICODE_ENVIRONMENT,
            ctypes.cast(environment, ctypes.c_void_p),
            os.getcwd(),
            ctypes.byref(startup),
            ctypes.byref(process),
        )
        if not created:
            raise _win_error("子プロセスの起動")
    finally:
        # 書き込み側は子プロセスだけが持つようにする（子が終われば読み込み側が EOF になる）
        os.close(out_write)
        os.close(err_write)
        stdin_file.close()
        if not process.hProcess:
            os.close(out_read)
            os.close(err_read)
    try:
        if not _kernel32.AssignProcessToJobObject(job, process.hProcess):
            error = _win_error("子プロセスのジョブへの登録")
            _kernel32.TerminateProcess(process.hProcess, FAILURE_EXIT_CODE)
            os.close(out_read)
            os.close(err_read)
            raise error
        for pump in pumps:
            pump.start()
        _kernel32.ResumeThread(process.hThread)
        return _wait(job, process.hProcess, timeout, pumps)
    finally:
        _kernel32.CloseHandle(process.hThread)
        _kernel32.CloseHandle(process.hProcess)


def _wait(job: int, process: int, timeout: float | None, pumps: list[threading.Thread]) -> int:
    """子プロセスの終了を待ち、終了コードを返す（時間切れ・中断ならジョブごと終わらせる）。"""
    wait_ms = INFINITE if timeout is None else int(timeout * MILLISECONDS_PER_SECOND)
    try:
        result = _kernel32.WaitForSingleObject(process, wait_ms)
    except KeyboardInterrupt:
        _kernel32.TerminateJobObject(job, FAILURE_EXIT_CODE)
        raise
    if result != WAIT_OBJECT_0:
        _kernel32.TerminateJobObject(job, TIMEOUT_EXIT_CODE)
        _kernel32.WaitForSingleObject(process, INFINITE)
        _write_message(
            sys.stderr, f"run_hidden: {timeout} 秒を過ぎたため、子プロセスを終わらせました。\n"
        )
        exit_code = TIMEOUT_EXIT_CODE
    else:
        code = wintypes.DWORD()
        if not _kernel32.GetExitCodeProcess(process, ctypes.byref(code)):
            raise _win_error("終了コードの取得")
        exit_code = int(code.value)
    # 子プロセスが残した孫プロセスがパイプを持ったままにならないよう、ジョブの残りを終わらせる
    _kernel32.TerminateJobObject(job, exit_code)
    for pump in pumps:
        pump.join()
    return exit_code


def main(argv: list[str] | None = None) -> int:
    """コマンドラインから実行する。

    Args:
        argv: スクリプト名を除いた引数。省略時は ``sys.argv[1:]``。

    Returns:
        子プロセスの終了コード（ランナー自身の失敗なら 1、引数の誤りなら 2）。
    """
    args = sys.argv[1:] if argv is None else argv
    if args[:1] and args[0] in HELP_OPTIONS:
        _write_message(sys.stdout, USAGE)
        return 0
    try:
        timeout, python_args = parse_args(args)
    except ValueError as exc:
        _write_message(sys.stderr, f"run_hidden: {exc}\n{USAGE}")
        return USAGE_EXIT_CODE
    try:
        return run_hidden(python_args, timeout)
    except HiddenRunError as exc:
        _write_message(sys.stderr, f"run_hidden: {exc}\n")
        return FAILURE_EXIT_CODE


if __name__ == "__main__":
    sys.exit(main())
