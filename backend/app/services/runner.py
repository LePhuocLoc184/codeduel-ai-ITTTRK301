import os
import re
import subprocess
from pathlib import Path
from tempfile import mkdtemp
from uuid import UUID

from app.schemas.runner import CompileResult


# AC 1.1: Dùng đường dẫn cố định theo vị trí backend, không phụ thuộc thư mục chạy.
CODE_BACKUP_DIR = Path(__file__).resolve().parents[2] / "code_backup"

# AC 1.2: Java bắt buộc dùng Main.java; c/cpp dùng chung solution.cpp theo yêu cầu.
CODE_FILENAMES = {
    "c": "solution.cpp",
    "cpp": "solution.cpp",
    "python": "solution.py",
    "java": "Main.java",
}


def _sanitize_compile_error(error: str, code_path: Path) -> str:
    """AC 3.3: Giữ tên file và số dòng, loại đường dẫn tuyệt đối Linux/Windows."""
    # Thư mục lượt nộp có thể chứa khoảng trắng (ví dụ tên tài khoản Windows).
    for directory in (str(code_path.parent), code_path.parent.as_posix()):
        error = error.replace(directory + "/", "").replace(directory + "\\", "")

    def basename(match: re.Match[str]) -> str:
        return re.split(r"[\\/]", match.group(0))[-1]

    # Xử lý đường dẫn trong dấu nháy trước để giữ nguyên các tên chứa khoảng trắng.
    error = re.sub(
        r"(?P<quote>['\"])(?P<path>(?:[A-Za-z]:[\\/]|\\\\|/)[^'\"\r\n]+)(?P=quote)",
        lambda match: match.group("quote")
        + re.split(r"[\\/]", match.group("path"))[-1]
        + match.group("quote"),
        error,
    )
    return re.sub(
        r"(?<![\w])(?:[A-Za-z]:[\\/]|\\\\|/)[^\s'\"<>|:]+",
        basename,
        error,
    )


def _compile_error(error: str, code_path: Path) -> CompileResult:
    # Mọi nhánh lỗi dùng chung phản hồi chuẩn và được làm sạch trước khi trả ra.
    return {
        "status": "COMPILE_ERROR",
        "error": _sanitize_compile_error(error, code_path),
        "executable_path": None,
    }


def save_code_file(code_content: str, language: str, user_id: UUID) -> Path:
    """Lưu mã vào thư mục của user đăng nhập, tách riêng từng lượt lưu."""
    if language not in CODE_FILENAMES:
        raise ValueError("Ngôn ngữ không được hỗ trợ")
    if not code_content.strip():
        raise ValueError("Mã nguồn không được để trống")

    # UUID do router lấy từ user đã xác thực, không tự tạo UUID cho user.
    user_id = UUID(str(user_id))
    sandbox_dir = CODE_BACKUP_DIR / f"sandbox_{user_id}"
    sandbox_dir.mkdir(parents=True, exist_ok=True)
    # Tách từng lượt lưu để cùng một user gửi đồng thời không ghi đè mã nguồn.
    run_dir = Path(mkdtemp(prefix="run_", dir=sandbox_dir))
    code_path = run_dir / CODE_FILENAMES[language]

    # Lưu UTF-8 và giữ nguyên xuống dòng, chỉ ghi nội dung chứ không thực thi mã.
    with code_path.open("x", encoding="utf-8", newline="") as code_file:
        code_file.write(code_content)
    return code_path


def compile_code(code_path: Path | str, language: str) -> CompileResult:
    """Biên dịch file đã lưu, trả về kết quả và đường dẫn phục vụ bước thực thi."""
    if language not in CODE_FILENAMES:
        raise ValueError("Ngôn ngữ không được hỗ trợ")

    code_path = Path(code_path).resolve()
    if not code_path.is_file():
        return _compile_error("Không tìm thấy file mã nguồn", code_path)

    # AC 2.3: Python chạy trực tiếp file .py, không gọi subprocess để build.
    if language == "python":
        return {"status": "READY", "error": None, "executable_path": str(code_path)}

    if language in ("c", "cpp"):
        # AC 2.1: Dùng file solution.cpp từ save_code_file và bật tối ưu -O2.
        executable_path = code_path.parent / ("temp.exe" if os.name == "nt" else "temp")
        command = ["g++", "-O2", code_path.name, "-o", executable_path.name]
    else:
        # AC 2.2: Java phải dùng Main.java để khớp public class Main.
        if code_path.name != "Main.java":
            return _compile_error("File Java phải có tên Main.java", code_path)
        executable_path = code_path.parent / "Main.class"
        command = ["javac", "Main.java"]

    try:
        # AC 2.4: Giới hạn mỗi lệnh build tối đa 10 giây, chạy trong thư mục lượt nộp.
        result = subprocess.run(
            command,
            cwd=code_path.parent,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return _compile_error("Biên dịch vượt quá 10 giây", code_path)
    except OSError as exc:
        # Báo rõ lỗi khi máy chủ thiếu compiler hoặc không thể khởi chạy lệnh.
        return _compile_error(f"Không thể chạy trình biên dịch: {exc}", code_path)

    # AC 3.1: Exit code khác 0 thì dừng tại đây, không trả đường dẫn thực thi.
    if result.returncode != 0:
        return _compile_error(
            result.stderr or result.stdout or "Biên dịch thất bại",
            code_path,
        )
    return {"status": "READY", "error": None, "executable_path": str(executable_path)}
