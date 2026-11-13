"""Thực thi và chấm testcase, dùng chung cho Run và Submit.

judge_code() lưu/compile một lần, rồi gọi run_case() cho từng testcase.
Service execute.py chọn testcase public hay toàn bộ; module này không tự chọn
testcase, không truy cập DB, không quyết định thắng trận hoặc cộng điểm Elo.

Lưu ý: subprocess chạy với quyền của server. Thư mục riêng và lấy mẫu tài nguyên
chưa tạo thành sandbox bảo mật để cô lập hoàn toàn code không đáng tin cậy.
"""
import os
import subprocess
import sys
import time
from contextlib import suppress
from pathlib import Path
from tempfile import TemporaryFile
from uuid import UUID

import psutil

from app.services.runner import save_code_file, compile_code, _sanitize_compile_error


def run_case(command: list[str], directory: Path, stdin: str,
             time_limit: float, memory_limit: int) -> dict:
    """Chạy một testcase, trả stdout, lỗi, thời gian (giây) và RAM (MB).

    command là danh sách đối số chạy Python/Java/binary; directory là thư mục
    riêng của lượt nộp; stdin chứa input của testcase. time_limit/memory_limit
    áp dụng cho mỗi case, không phải tổng tất cả case.

    PASS ở hàm này chỉ có nghĩa tiến trình thoát bình thường. judge_code()
    còn phải đối chiếu stdout với đáp án mới xác nhận testcase thực sự đạt.
    """
    # perf_counter đo khoảng thời gian trôi qua, gồm cả khởi động tiến trình.
    # Đây là thời gian thực tế, không phải số giây CPU sử dụng riêng cho code.
    started = time.perf_counter()
    peak_memory = 0.0
    status, error = "PASS", None
    # Ghi sẵn input rồi đưa con trỏ về đầu để chương trình đọc từ byte đầu tiên.
    # Output/error đi vào file tạm thay vì pipe có bộ đệm hữu hạn dễ gây kẹt.
    # Ba file này tự đóng/xóa khi rời with; file mã nguồn vẫn được giữ ở code_backup.
    with TemporaryFile() as inp, TemporaryFile() as out, TemporaryFile() as err:
        inp.write(stdin.encode("utf-8"))
        inp.seek(0)
        # cwd giúp chương trình tìm file trong lượt chạy; không giới hạn được quyền
        # đọc/ghi ra ngoài thư mục này. command dạng list không cần shell=True.
        process = subprocess.Popen(command, cwd=directory, stdin=inp, stdout=out, stderr=err)
        # Giữ lại các tiến trình đã quan sát để đo RAM và dọn khi kết thúc testcase.
        tracked = {}
        try:
            # Chương trình rất ngắn có thể đã thoát trước lần lấy thông tin đầu tiên.
            root = None
            with suppress(psutil.NoSuchProcess):
                root = psutil.Process(process.pid)
                tracked[root.pid] = root
            while process.poll() is None:
                with suppress(psutil.NoSuchProcess):
                    for child in root.children(recursive=True) if root else []:
                        tracked[child.pid] = child
                # RSS là lượng RAM vật lý tiến trình đang chiếm. Cộng RAM của
                # tiến trình chính và các tiến trình con đã theo dõi, đổi byte -> MB.
                rss = 0
                for child in tracked.values():
                    with suppress(psutil.NoSuchProcess):
                        rss += child.memory_info().rss
                # Đây là đỉnh RAM QUAN SÁT ĐƯỢC: lấy mẫu có thể bỏ sót đỉnh rất ngắn.
                peak_memory = max(peak_memory, rss / (1024 * 1024))
                if peak_memory > memory_limit:
                    status, error = "MLE", "Vượt giới hạn bộ nhớ"
                    break
                if time.perf_counter() - started > time_limit:
                    status, error = "TLE", "Vượt giới hạn thời gian"
                    break
                # Nếu tổng stdout + stderr quan sát được vượt 1 MB, dừng testcase.
                # Kiểm tra định kỳ nên đây không phải hạn mức cứng ở cấp hệ điều hành.
                if os.fstat(out.fileno()).st_size + os.fstat(err.fileno()).st_size > 1024 * 1024:
                    status, error = "RUNTIME_ERROR", "Output vượt giới hạn 1 MB"
                    break
                # Chờ 5 ms giữa các lần lấy mẫu để tránh vòng lặp chiếm toàn bộ CPU.
                time.sleep(0.005)
        finally:
            # finally chạy cả khi hoàn thành bình thường lẫn khi bị ngắt do lỗi.
            # Dọn các tiến trình con đã thấy; tiến trình tạo/thoát giữa hai lần lấy
            # mẫu có thể không được theo dõi, nên đây chưa thay thế sandbox hệ điều hành.
            for child in reversed(list(tracked.values())):
                with suppress(psutil.NoSuchProcess):
                    child.kill()
            if process.poll() is None:
                process.kill()
            # Chờ tiến trình chính được thu hồi trước khi đọc file output/error.
            process.wait()
        elapsed = time.perf_counter() - started
        # Giới hạn cả phần đọc vào RAM; errors='replace' tránh lỗi giải mã output
        # không phải UTF-8 làm hỏng toàn bộ request chấm bài.
        out.seek(0)
        err.seek(0)
        actual = out.read(1024 * 1024).decode("utf-8", errors="replace")
        stderr = err.read(1024 * 1024).decode("utf-8", errors="replace")
        if status == "PASS" and process.returncode != 0:
            status, error = "RUNTIME_ERROR", stderr or f"Mã thoát: {process.returncode}"
            # JVM/Python có thể tự báo hết bộ nhớ trước lần lấy mẫu RSS kế tiếp.
            # Nhận diện theo chuỗi stderr chỉ là suy đoán, không phải số đo chắc chắn.
            if "java.lang.OutOfMemoryError" in stderr or "MemoryError" in stderr or "std::bad_alloc" in stderr:
                status, error = "MLE", "Chương trình không cấp phát được bộ nhớ"
        # Làm sạch đường dẫn trong lỗi runtime bằng helper đang dùng cho lỗi compile.
        # 'source' chỉ là tên placeholder để helper lấy directory, không tạo thêm file.
        return {"status": status, "actual_output": actual,
                "execution_time": elapsed, "memory_used": peak_memory,
                "error_message": _sanitize_compile_error(error, directory / "source") if error else None}


def judge_code(code_content: str, language: str, user_id: UUID,
               cases: list[dict], time_limit: float, memory_limit: int) -> dict:
    """Trả kết quả tổng hợp của bài nộp và danh sách chi tiết từng testcase.

    status: PASS/FAIL/TLE/MLE/COMPILE_ERROR/RUNTIME_ERROR.
    execution_time: tổng giây chạy các case, không tính compile.
    memory_used: đỉnh RAM quan sát được lớn nhất giữa các case, không cộng dồn.
    results: có input/output nên service chỉ đưa danh sách này ra client khi Run.
    """
    # Khởi tạo FAIL để danh sách testcase rỗng không thể được tính là PASS.
    summary = {"status": "FAIL", "passed_test_cases": 0, "total_test_cases": len(cases),
               "execution_time": 0.0, "memory_used": 0.0, "error_message": None, "results": []}
    if not cases:
        summary["error_message"] = "Bài toán chưa có testcase"
        return summary
    try:
        # Dùng UUID người đăng nhập để lưu file; chỉ compile một lần cho cả bộ case.
        path = save_code_file(code_content, language, user_id)
        compiled = compile_code(path, language)
        if compiled["status"] == "COMPILE_ERROR":
            # Lỗi compile thì dừng trước vòng lặp; chưa có testcase nào được chạy.
            summary.update(status="COMPILE_ERROR", error_message=compiled["error"])
            return summary
        # Python dùng interpreter hiện tại; -I bỏ một số ảnh hưởng môi trường Python,
        # không chặn truy cập file/network. Java dùng thư mục class qua -cp;
        # -Xmx chỉ giới hạn heap, còn RSS đo cả bộ nhớ JVM. C/C++ chạy binary đã build.
        command = ([sys.executable, "-I", str(path)] if language == "python" else
                   ["java", f"-Xmx{memory_limit}m", "-cp", str(path.parent), "Main"] if language == "java" else
                   [compiled["executable_path"]])
        summary["status"] = "PASS"
        for case in cases:
            # Mỗi case khởi chạy một tiến trình mới, không tái sử dụng trạng thái RAM.
            result = run_case(command, path.parent, case["input"], time_limit, memory_limit)
            # So sánh token: "1 2" và "1\n2" được xem là giống nhau.
            # Không có sai số số thực: token "1.0" khác "1.00".
            passed = result["status"] == "PASS" and result["actual_output"].split() == case["expected_output"].split()
            # Chạy bình thường nhưng sai đáp án -> FAIL; giữ nguyên TLE/MLE/lỗi chạy.
            if result["status"] == "PASS" and not passed:
                result["status"] = "FAIL"
            result.update(input=case["input"], expected_output=case["expected_output"], passed=passed)
            summary["results"].append(result)
            summary["passed_test_cases"] += int(passed)
            summary["execution_time"] += result["execution_time"]
            summary["memory_used"] = max(summary["memory_used"], result["memory_used"])
            # Tiếp tục các case sau để đếm đầy đủ. Một khi đã gặp TLE/MLE/RUNTIME_ERROR
            # thì giữ lỗi đó làm trạng thái tổng; case PASS sau không xóa lỗi trước.
            if not passed and summary["status"] in ("PASS", "FAIL"):
                summary["status"] = result["status"]
                summary["error_message"] = result["error_message"]
    except (OSError, ValueError, psutil.Error):
        # Lỗi lưu file/khởi chạy/đo tiến trình: trả lỗi tổng quát, không lộ đường dẫn máy chủ.
        summary.update(status="RUNTIME_ERROR", error_message="Không thể khởi chạy chương trình")
    return summary
