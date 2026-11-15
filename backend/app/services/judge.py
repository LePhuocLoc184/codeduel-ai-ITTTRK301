"""Chấm code: lưu/compile -> evaluate_testcases -> dừng ở testcase lỗi đầu tiên.

Runner chỉ xử lý file và compiler; evaluator chạy testcase, chuẩn hóa output
và trả số đo theo ms/MB. Service execute.py chọn testcase và ghi dữ liệu DB.
"""
import json
import math
import subprocess
import sys
from contextlib import suppress
from pathlib import Path
from uuid import UUID

import psutil

from app.services.execution_worker import kill_and_wait


def run_case(command: list[str], directory: Path, stdin: str,
             time_limit: float = 2.0, memory_limit: int = 128) -> dict:
    """Chạy một testcase qua worker độc lập để dùng preexec_fn an toàn trên Linux."""
    worker_path = Path(__file__).with_name("execution_worker.py")
    request = {
        "command": command, "directory": str(directory), "stdin": stdin,
        "time_limit": time_limit, "memory_limit_mb": memory_limit,
    }
    worker = subprocess.Popen(
        [sys.executable, str(worker_path)], stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        encoding="utf-8", errors="replace",
    )
    try:
        # Timeout chấm THỰC SỰ nằm trong subprocess.run của worker = time_limit.
        # 5 giây thêm chỉ để worker khởi động/dọn con; không cộng vào số đo testcase.
        stdout, stderr = worker.communicate(json.dumps(request), timeout=time_limit + 5)
    except subprocess.TimeoutExpired:
        # Đây là worker bị kẹt, không phải lỗi TLE của bài làm. Thu hồi worker
        # và các con còn sống, rồi báo lỗi hạ tầng thay vì công nhận bài đã chạy.
        # Worker có thể vừa thoát ngay khi timeout xảy ra; vẫn phải thu hồi nó.
        try:
            with suppress(psutil.NoSuchProcess):
                kill_and_wait(psutil.Process(worker.pid).children(recursive=True))
        finally:
            if worker.poll() is None:
                worker.kill()
            worker.communicate()
        return {"status": "RUNTIME_ERROR", "actual_output": "",
                "execution_time_ms": 0.0, "memory_used_mb": 0.0,
                "error_message": "Worker không phản hồi trong thời hạn"}
    if worker.returncode != 0:
        return {"status": "RUNTIME_ERROR", "actual_output": "",
                "execution_time_ms": 0.0, "memory_used_mb": 0.0,
                "error_message": "Worker không thể chạy testcase"}
    return json.loads(stdout)


def evaluate_testcases(command: list[str], directory: Path | str,
                       test_cases: list[dict], time_limit: float = 2.0,
                       memory_limit_mb: int = 128) -> dict:
    """AC 3/4: chấm danh sách JSON, trả kết quả tổng hợp và chi tiết case public.

    passed_count là số case đúng trước lỗi đầu tiên; total_count luôn là tổng
    số case của đề, kể cả các case chưa chạy. execution_time_ms lấy MAX giữa
    các case đã chạy, memory_used_mb cũng lấy MAX. Danh sách results là phần
    bổ sung cho Console của API Run; tuyệt đối không chứa dữ liệu hidden case.
    """
    if not math.isfinite(time_limit) or time_limit <= 0 or memory_limit_mb <= 0:
        raise ValueError("Giới hạn thời gian và bộ nhớ phải lớn hơn 0")
    summary = {
        "status": "FAIL",
        "passed_count": 0,
        "total_count": len(test_cases),
        "execution_time_ms": 0.0,
        "memory_used_mb": 0.0,
        "error_message": None,
        "results": [],
    }
    if not test_cases:
        # Không cho trường hợp 0/0 được công nhận PASS và thắng trận.
        summary["error_message"] = "Bài toán chưa có testcase"
        return summary

    for index, case in enumerate(test_cases, start=1):
        # AC 3.1: mỗi input được đưa nguyên vẹn vào stdin của một tiến trình mới.
        result = run_case(command, Path(directory), case["input"], time_limit, memory_limit_mb)
        # AC 3.2: chỉ bỏ khoảng trắng ở HAI ĐẦU, giữ nguyên khoảng trắng bên trong.
        # Ví dụ " 3\\n" khớp "3", nhưng "1  2" không khớp "1 2".
        passed = (result["status"] == "PASS"
                  and result["actual_output"].strip() == case["expected_output"].strip())
        if result["status"] == "PASS" and not passed:
            result["status"] = "FAIL"
            result["error_message"] = f"Sai kết quả ở testcase {index}"

        summary["execution_time_ms"] = max(summary["execution_time_ms"], result["execution_time_ms"])
        summary["memory_used_mb"] = max(summary["memory_used_mb"], result["memory_used_mb"])

        # Dữ liệu chi tiết chỉ được đưa ra nếu is_hidden đúng bằng False.
        # Thiếu cờ cũng coi là hidden; stderr có thể chứa input do người chơi in ra.
        if case.get("is_hidden") is False:
            from app.services.runner import _sanitize_compile_error

            if result["error_message"]:
                result["error_message"] = _sanitize_compile_error(
                    result["error_message"], Path(directory) / "source",
                )
            summary["results"].append({
                "input": case["input"], "expected_output": case["expected_output"],
                "actual_output": result["actual_output"], "passed": passed,
                "status": result["status"], "error_message": result["error_message"],
                "execution_time_ms": result["execution_time_ms"],
                "memory_used_mb": result["memory_used_mb"],
            })
        elif result["error_message"]:
            # Không trả traceback/output của hidden case qua trường lỗi tổng hợp.
            result["error_message"] = {
                "FAIL": "Sai kết quả ở testcase ẩn",
                "TLE": "Testcase ẩn vượt giới hạn thời gian",
                "MLE": "Testcase ẩn vượt giới hạn bộ nhớ",
                "RUNTIME_ERROR": "Lỗi thực thi ở testcase ẩn",
            }.get(result["status"], "Không chấm được testcase ẩn")

        if not passed:
            # AC 1.4/4.2: dừng ngay với FAIL, TLE, MLE hoặc RUNTIME_ERROR.
            # Giữ số case đã đạt; không tính các case chưa được chạy là đã PASS.
            summary["status"] = result["status"]
            summary["error_message"] = result["error_message"]
            return summary
        summary["passed_count"] += 1

    # Chỉ đi tới đây khi mọi case đều đã chạy thành công và đúng đáp án.
    if summary["passed_count"] == summary["total_count"]:
        summary["status"] = "PASS"
    return summary


def judge_code(code_content: str, language: str, user_id: UUID,
               cases: list[dict], time_limit: float = 2.0, memory_limit: int = 128) -> dict:
    """Nối bước lưu file/compile với evaluator, trả cùng cấu trúc ms/MB cho service."""
    from app.services.runner import save_code_file, compile_code

    summary = {
        "status": "FAIL", "passed_count": 0, "total_count": len(cases),
        "execution_time_ms": 0.0, "memory_used_mb": 0.0,
        "error_message": None, "results": [],
    }
    if not cases:
        summary["error_message"] = "Bài toán chưa có testcase"
        return summary
    try:
        path = save_code_file(code_content, language, user_id)
        compiled = compile_code(path, language)
        if compiled["status"] == "COMPILE_ERROR":
            summary.update(status="COMPILE_ERROR", error_message=compiled["error"])
            return summary
        if language == "python":
            command = [sys.executable, "-I", str(path)]
        elif language == "java":
            # -Xmx giới hạn heap; RLIMIT_AS trên Linux giới hạn toàn bộ không gian
            # địa chỉ của JVM. Với mức thấp (như 128 MB), JVM có thể không khởi động.
            command = ["java", f"-Xmx{memory_limit}m", "-cp", str(path.parent), "Main"]
        else:
            command = [compiled["executable_path"]]
        return evaluate_testcases(command, path.parent, cases, time_limit, memory_limit)
    except (OSError, ValueError, subprocess.SubprocessError, psutil.Error):
        # Lỗi hạ tầng/file/worker không được đổi thành PASS hay lộ đường dẫn server.
        summary.update(status="RUNTIME_ERROR", error_message="Không thể khởi chạy bộ chấm")
        return summary
