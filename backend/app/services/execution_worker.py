"""Chạy đúng một testcase trong tiến trình riêng, không import FastAPI hoặc DB.

Linux cần preexec_fn để đặt RLIMIT_AS. Không gọi preexec_fn ngay trong thread
pool của API vì có nguy cơ deadlock sau fork. Worker này chỉ có một luồng trên
Linux; nó nhận JSON qua stdin và trả đúng một JSON kết quả qua stdout.
"""
import ctypes
import json
import os
import signal
import subprocess
import sys
import threading
import time
from contextlib import suppress
from tempfile import TemporaryFile

import psutil

IS_LINUX = sys.platform.startswith("linux")
OUTPUT_LIMIT_BYTES = 1024 * 1024

if IS_LINUX:
    import resource


def kill_and_wait(processes: list) -> None:
    """Hủy tiến trình đã biết và chờ thu hồi; gọi được cả khi chúng vừa thoát."""
    for process in reversed(processes):
        with suppress(psutil.NoSuchProcess):
            process.kill()
    _, alive = psutil.wait_procs(processes, timeout=1)
    if alive:
        # kill() gửi yêu cầu hủy; tiến trình có thể chưa được hệ điều hành thu hồi
        # ngay. Chờ thêm và kiểm tra kết quả, không bỏ qua danh sách còn sống.
        for process in alive:
            with suppress(psutil.NoSuchProcess):
                process.kill()
        _, alive = psutil.wait_procs(alive, timeout=1)
        if alive:
            raise psutil.TimeoutExpired(2, pid=alive[0].pid)


def cleanup_children(tracked: list) -> None:
    """Dọn con của worker, kể cả tiến trình cháu được nhận nuôi sau khi cha chết."""
    owner = psutil.Process()
    remaining = {process.pid: process for process in tracked}
    deadline = time.monotonic() + 3
    while True:
        # Quét lại sau mỗi lượt kill/wait: một tiến trình có thể kịp sinh thêm
        # con trong khoảng từ lúc lấy danh sách đến khi bị hủy.
        remaining.update((child.pid, child) for child in owner.children(recursive=True))
        if not remaining:
            return
        if time.monotonic() >= deadline:
            raise psutil.TimeoutExpired(3)
        kill_and_wait(list(remaining.values()))
        remaining.clear()


def execute_case(command: list[str], directory: str, stdin: str,
                 time_limit: float = 2.0, memory_limit_mb: int = 128) -> dict:
    """Giới hạn từng testcase; execution_time_ms là thời gian chạy thực tế."""
    status, error = "PASS", None
    peak_mb = 0.0
    completed = None
    pid_read = pid_write = None
    tracked = {}
    stop_monitor = threading.Event()
    memory_exceeded = threading.Event()
    output_exceeded = threading.Event()
    monitor = None
    options = {}

    # Linux: nhận nuôi các tiến trình cháu nếu chương trình cha thoát trước.
    # Nhờ vậy có thể kill + wait, thay vì để chúng thành tiến trình mồ côi/zombie.
    if IS_LINUX:
        libc = ctypes.CDLL(None, use_errno=True)
        libc.prctl.argtypes = [ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong,
                              ctypes.c_ulong, ctypes.c_ulong]
        libc.prctl.restype = ctypes.c_int
        if libc.prctl(36, 1, 0, 0, 0) != 0:  # PR_SET_CHILD_SUBREAPER
            raise OSError(ctypes.get_errno(), "Không thiết lập được thu hồi tiến trình con")
        memory_limit_bytes = memory_limit_mb * 1024 * 1024
        pid_read, pid_write = os.pipe()

        def set_limits():
            # AC 2.1: trần bộ nhớ ẢO, không phải chỉ heap hay RAM RSS.
            # Đặt cả soft/hard limit để code con không tự nâng lại giới hạn.
            resource.setrlimit(resource.RLIMIT_AS, (memory_limit_bytes, memory_limit_bytes))
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            resource.setrlimit(resource.RLIMIT_FSIZE, (OUTPUT_LIMIT_BYTES, OUTPUT_LIMIT_BYTES))
            # Gửi PID qua pipe để sau subprocess.run vẫn biết nhóm nào cần dọn.
            os.write(pid_write, str(os.getpid()).encode("ascii"))
            os.close(pid_write)

        options = {"preexec_fn": set_limits, "start_new_session": True,
                   "pass_fds": (pid_write,)}

    with TemporaryFile() as inp, TemporaryFile() as out, TemporaryFile() as err:
        # Input đi vào stdin qua file tạm; tránh deadlock do pipe đầy.
        inp.write(stdin.encode("utf-8"))
        inp.seek(0)

        def watch_windows():
            # Windows không có resource.RLIMIT_AS: giữ phương án lấy mẫu RSS.
            # Worker chỉ chạy một bài nên không đụng tiến trình của request khác.
            nonlocal peak_mb
            owner = psutil.Process()
            while not stop_monitor.wait(0.005):
                with suppress(psutil.NoSuchProcess):
                    for child in owner.children(recursive=True):
                        tracked[child.pid] = child
                rss = 0
                for child in list(tracked.values()):
                    with suppress(psutil.NoSuchProcess):
                        info = child.memory_info()
                        rss += getattr(info, "peak_wset", info.rss)
                peak_mb = max(peak_mb, rss / (1024 * 1024))
                if peak_mb > memory_limit_mb:
                    memory_exceeded.set()
                    kill_and_wait(list(tracked.values()))
                    return
                if os.fstat(out.fileno()).st_size + os.fstat(err.fileno()).st_size > OUTPUT_LIMIT_BYTES:
                    output_exceeded.set()
                    kill_and_wait(list(tracked.values()))
                    return

        # Tuyệt đối không khởi chạy thread monitor trên Linux trước preexec_fn.
        if not IS_LINUX:
            monitor = threading.Thread(target=watch_windows, daemon=True)
            monitor.start()
        started = time.perf_counter()
        try:
            # AC 1.1: time_limit lấy từ Question trong DB (mặc định 2.0 giây).
            completed = subprocess.run(
                command, cwd=directory, stdin=inp, stdout=out, stderr=err,
                timeout=time_limit, check=False, **options,
            )
        except subprocess.TimeoutExpired:
            # run() đã kill + wait tiến trình trực tiếp trước khi ném ngoại lệ.
            # finally bên dưới tiếp tục dọn toàn bộ nhóm và tiến trình cháu.
            status, error = "TLE", f"Vượt giới hạn {time_limit:g} giây"
        except (OSError, subprocess.SubprocessError):
            status, error = "RUNTIME_ERROR", "Không thể khởi chạy chương trình hoặc đặt giới hạn"
        finally:
            # Không cộng thời gian dọn tiến trình vào số đo của testcase.
            elapsed_ms = (time.perf_counter() - started) * 1000
            stop_monitor.set()
            if monitor is not None:
                monitor.join()
            if IS_LINUX:
                os.close(pid_write)
                child_pid = os.read(pid_read, 32)
                os.close(pid_read)
                if child_pid:
                    # Nhóm mới có PGID = PID của chương trình. Kill cả nhóm,
                    # kể cả khi tiến trình chính đã chết nhưng con vẫn chạy.
                    with suppress(ProcessLookupError):
                        os.killpg(int(child_pid), signal.SIGKILL)
            # Dọn cả khi PASS/FAIL: chương trình chính có thể đã thoát nhưng
            # để lại tiến trình con chạy nền. Worker không được bỏ lại chúng.
            cleanup_children(list(tracked.values()))
            if IS_LINUX:
                # Thu hồi cả zombie đã được subreaper nhận nuôi.
                with suppress(ChildProcessError):
                    while os.waitpid(-1, os.WNOHANG)[0] > 0:
                        pass
                # Worker mới cho mỗi case: ru_maxrss không lẫn với bài nộp khác.
                # Linux trả KiB; chia 1024 để đưa về MB.
                peak_mb = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024

        out.seek(0)
        err.seek(0)
        stdout = out.read(OUTPUT_LIMIT_BYTES).decode("utf-8", errors="replace")
        stderr = err.read(OUTPUT_LIMIT_BYTES).decode("utf-8", errors="replace")
        if memory_exceeded.is_set():
            status, error = "MLE", "Vượt giới hạn bộ nhớ"
        elif output_exceeded.is_set():
            status, error = "RUNTIME_ERROR", "Output vượt giới hạn 1 MB"
        elif completed is not None and completed.returncode != 0:
            # AC 2.2: dưới RLIMIT_AS, thiếu bộ nhớ có thể hiện thành MemoryError,
            # bad_alloc hoặc SIGSEGV. SIGSEGV cũng có thể do truy cập sai địa chỉ;
            # theo quy ước AC này, SIGSEGV dưới giới hạn bộ nhớ được phân loại MLE.
            memory_errors = ("memoryerror", "std::bad_alloc", "outofmemoryerror",
                             "cannot allocate memory", "could not reserve enough space",
                             "native memory allocation", "insufficient memory",
                             "failed to map segment")
            is_memory_error = any(marker in (stderr + stdout).lower() for marker in memory_errors)
            if is_memory_error or (IS_LINUX and completed.returncode == -signal.SIGSEGV):
                status, error = "MLE", "Chương trình vượt giới hạn hoặc không cấp phát được bộ nhớ"
            else:
                status, error = "RUNTIME_ERROR", stderr or f"Mã thoát: {completed.returncode}"
        return {"status": status, "actual_output": stdout,
                "execution_time_ms": elapsed_ms, "memory_used_mb": peak_mb,
                "error_message": error}


if __name__ == "__main__":
    # Chỉ dữ liệu điều khiển nội bộ đi qua JSON; stdout của bài làm nằm ở file tạm.
    request = json.load(sys.stdin)
    print(json.dumps(execute_case(**request), ensure_ascii=True))
