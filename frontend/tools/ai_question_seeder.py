#!/usr/bin/env python3
"""
Nạp đề do AI sinh vào cơ sở dữ liệu để MỌI trận (ranked 1v1 lẫn phòng tùy chỉnh) dùng đề AI.

Script nằm trong frontend/tools, ngoài thư mục backend và KHÔNG import code backend:
  - đọc DATABASE_URL từ backend/.env (chỉ đọc, không ghi)
  - đọc cấu hình AI từ backend/.env (AI_PROVIDER / AI_API_KEY / AI_MODEL / AI_BASE_URL)
  - chỉ INSERT vào bảng problem_sets và questions, không xóa gì

Mỗi đề AI tạo ra phải qua bước xác minh: lời giải tham chiếu (Python) được CHẠY THẬT trên từng
testcase và output phải khớp expected_output. Đề không khớp bị loại, AI được yêu cầu làm lại.
Nhờ vậy bộ chấm của backend chấm theo testcase đã được kiểm chứng, không phụ thuộc AI "tính nhẩm".

Cách chạy (dùng Python của môi trường ảo backend, vì cần asyncpg):
    python frontend/tools/ai_question_seeder.py --count 9
    python frontend/tools/ai_question_seeder.py --count 6 --difficulty EASY,MEDIUM --topics "Array,Stack"
    python frontend/tools/ai_question_seeder.py --count 3 --dry-run        # chỉ in ra, không ghi DB
"""
import argparse
import asyncio
import json
import os
import random
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

FRONTEND_DIR = Path(__file__).resolve().parent.parent      # .../frontend
BACKEND_ENV = FRONTEND_DIR.parent / "backend" / ".env"     # chỉ đọc

PROBLEM_SET_TITLE = "AI Generated"
PROBLEM_SET_DESC = "Bộ đề do AI sinh, testcase đã được xác minh bằng lời giải tham chiếu."
SAMPLE_TOPICS = ["Array", "String", "Math", "Sorting", "Hash Map", "Two Pointers",
                 "Dynamic Programming", "Greedy", "Stack", "Binary Search"]
DIFFICULTIES = ["EASY", "MEDIUM", "HARD"]
MAX_ATTEMPTS = 3
RUN_TIMEOUT_S = 5

PROVIDERS = {
    "openai": ("openai", "https://api.openai.com/v1", "gpt-4o-mini"),
    "gemini": ("openai", "https://generativelanguage.googleapis.com/v1beta/openai", "gemini-3.5-flash"),
    "anthropic": ("anthropic", "https://api.anthropic.com", "claude-sonnet-5-5"),
    "openrouter": ("openai", "https://openrouter.ai/api/v1", "openai/gpt-4o-mini"),
    "custom": ("openai", "", ""),
}

DEFAULT_STARTER = {
    "cpp": "#include <bits/stdc++.h>\nusing namespace std;\n\nint main() {\n    ios::sync_with_stdio(false);\n    cin.tie(nullptr);\n\n    return 0;\n}\n",
    "python": "import sys\n\ndef main():\n    data = sys.stdin.read().split()\n\nmain()\n",
    "java": "import java.util.*;\n\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n    }\n}\n",
}

CONTRACT = """{
  "title": "tên bài, 3-255 ký tự",
  "description": "đề bài Markdown: mô tả, định dạng input, định dạng output, ràng buộc",
  "time_limit": 2.0,
  "memory_limit": 256,
  "starter_code": { "cpp": "...", "python": "...", "java": "..." },
  "test_cases": [ { "input": "...", "expected_output": "...", "is_hidden": false } ],
  "reference_solution": "lời giải tham chiếu bằng Python 3, đọc stdin, in ra stdout"
}"""


# ---------- đọc cấu hình ----------
def read_env(path: Path) -> dict:
    values = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def load_ai_config() -> dict:
    env = read_env(BACKEND_ENV)
    provider = env.get("AI_PROVIDER", "openai")
    if provider not in PROVIDERS:
        provider = "openai"
    kind, base, model = PROVIDERS[provider]
    config = {
        "provider": provider,
        "kind": kind,
        "api_key": env.get("AI_API_KEY", ""),
        "model": env.get("AI_MODEL") or model,
        "base_url": (env.get("AI_BASE_URL") or base).rstrip("/"),
    }
    if not (config["api_key"] and config["model"] and config["base_url"]):
        sys.exit("Thiếu cấu hình AI trong backend/.env (cần AI_API_KEY, AI_MODEL và AI_BASE_URL).")
    return config


def load_database_url() -> str:
    url = os.environ.get("DATABASE_URL") or read_env(BACKEND_ENV).get("DATABASE_URL", "")
    if not url:
        sys.exit("Không tìm thấy DATABASE_URL trong backend/.env.")
    # asyncpg không hiểu tiền tố của SQLAlchemy.
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)


# ---------- gọi AI ----------
def call_ai(config: dict, system: str, user: str) -> str:
    if config["kind"] == "anthropic":
        url = f"{config['base_url']}/v1/messages"
        headers = {"Content-Type": "application/json", "x-api-key": config["api_key"],
                   "anthropic-version": "2023-06-01"}
        body = {"model": config["model"], "max_tokens": 8000, "system": system,
                "messages": [{"role": "user", "content": user}]}
    else:
        url = f"{config['base_url']}/chat/completions"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {config['api_key']}"}
        body = {"model": config["model"],
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    request = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:400]
        raise RuntimeError(f"AI báo lỗi {error.code}: {detail}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Không gọi được API AI: {error.reason}") from error

    if config["kind"] == "anthropic":
        text = "".join(part.get("text", "") for part in data.get("content", []) if part.get("type") == "text")
    else:
        text = (data.get("choices") or [{}])[0].get("message", {}).get("content")
    if not text:
        raise RuntimeError("AI không trả về nội dung.")
    return text


def extract_json(text: str) -> dict:
    cleaned = text.replace("```json", "").replace("```JSON", "").replace("```", "")
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("AI trả về dữ liệu không phải JSON")
    return json.loads(cleaned[start:end + 1])


# ---------- kiểm tra định dạng (theo schemas/questions.py) ----------
def parse_question(raw: dict, difficulty: str) -> tuple[dict, str]:
    errors = []
    title = str(raw.get("title") or "").strip()
    description = str(raw.get("description") or "")
    if not 3 <= len(title) <= 255:
        errors.append("title phải dài 3-255 ký tự")
    if len(description.strip()) < 10:
        errors.append("description phải có ít nhất 10 ký tự")

    cases = []
    for item in raw.get("test_cases") or []:
        if isinstance(item, dict) and isinstance(item.get("input"), str) and isinstance(item.get("expected_output"), str):
            inp, out = item["input"].strip(), item["expected_output"].strip()
            if inp and out:
                cases.append({"input": inp, "expected_output": out, "is_hidden": item.get("is_hidden") is True})
    if len(cases) < 2:
        errors.append("test_cases phải có ít nhất 2 testcase với input và expected_output là chuỗi không rỗng")
    if not any(not c["is_hidden"] for c in cases):
        errors.append("phải có ít nhất 1 testcase công khai (is_hidden=false)")

    reference = str(raw.get("reference_solution") or "").strip()
    if not reference:
        errors.append("thiếu reference_solution")
    if errors:
        raise ValueError("; ".join(errors))

    try:
        time_limit = float(raw.get("time_limit"))
    except (TypeError, ValueError):
        time_limit = 2.0
    try:
        memory_limit = int(round(float(raw.get("memory_limit"))))
    except (TypeError, ValueError):
        memory_limit = 128
    starter = {}
    given = raw.get("starter_code") if isinstance(raw.get("starter_code"), dict) else {}
    for lang in ("cpp", "python", "java"):
        value = str(given.get(lang) or "")
        starter[lang] = value if value.strip() else DEFAULT_STARTER[lang]

    question = {
        "title": title,
        "description": description,
        "difficulty": difficulty,
        "time_limit": min(time_limit, 10.0) if time_limit > 0 else 2.0,
        "memory_limit": min(memory_limit, 1024) if memory_limit > 0 else 128,
        "starter_code": starter,
        "test_cases": cases,
    }
    return question, reference


# ---------- xác minh bằng cách chạy thật lời giải tham chiếu ----------
def verify_reference(reference: str, cases: list[dict]) -> list[str]:
    """Trả về danh sách lỗi; rỗng nghĩa là lời giải khớp MỌI testcase (so sau khi strip, như judge của backend)."""
    problems = []
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "reference.py"
        path.write_text(reference, encoding="utf-8")
        for index, case in enumerate(cases, start=1):
            try:
                result = subprocess.run([sys.executable, str(path)], input=case["input"], capture_output=True,
                                        text=True, encoding="utf-8", errors="replace", timeout=RUN_TIMEOUT_S,
                                        env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            except subprocess.TimeoutExpired:
                problems.append(f"testcase {index}: lời giải tham chiếu chạy quá {RUN_TIMEOUT_S}s")
                continue
            if result.returncode != 0:
                problems.append(f"testcase {index}: lời giải tham chiếu bị lỗi: {result.stderr.strip()[-200:]}")
            elif result.stdout.strip() != case["expected_output"]:
                problems.append(f"testcase {index}: lời giải ra {result.stdout.strip()[:80]!r} "
                                f"nhưng expected_output là {case['expected_output'][:80]!r}")
    return problems


def generate_one(config: dict, topic: str, difficulty: str) -> dict:
    system = ("Bạn là giám khảo ra đề lập trình thi đấu. Chỉ trả về MỘT object JSON hợp lệ, "
              "không thêm chữ nào ngoài JSON. Nội dung viết bằng tiếng Việt.")
    base = (f'Hãy ra một bài lập trình thi đấu về chủ đề "{topic}", độ khó {difficulty}.\n'
            "Bài đọc dữ liệu từ stdin và in kết quả ra stdout. Đáp án phải duy nhất và xác định "
            "(không dùng số thực, không có nhiều đáp án đúng).\n"
            f"Trả về JSON đúng format sau:\n{CONTRACT}\n"
            "Yêu cầu test_cases: 6 testcase; 2 testcase đầu is_hidden=false (ví dụ trong đề), "
            "4 testcase sau is_hidden=true gồm cả trường hợp biên. input/expected_output là văn bản đúng như "
            "stdin/stdout. reference_solution phải là chương trình Python 3 hoàn chỉnh chạy được.")
    feedback = ""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        prompt = base if not feedback else f"{base}\n\nLần trước bị loại vì: {feedback}\nHãy sửa đúng các lỗi này."
        try:
            question, reference = parse_question(extract_json(call_ai(config, system, prompt)), difficulty)
            problems = verify_reference(reference, question["test_cases"])
            if not problems:
                return question
            feedback = "; ".join(problems[:4])
        except (ValueError, json.JSONDecodeError) as error:
            feedback = str(error)
        print(f"    lần {attempt}/{MAX_ATTEMPTS} bị loại: {feedback[:200]}")
    raise RuntimeError(f"Không tạo được đề hợp lệ sau {MAX_ATTEMPTS} lần ({topic}, {difficulty}).")


# ---------- ghi vào DB (chỉ INSERT) ----------
async def save_questions(database_url: str, questions: list[dict]) -> None:
    import asyncpg  # có sẵn trong môi trường backend (requirements.txt)

    connection = await asyncpg.connect(database_url)
    try:
        async with connection.transaction():
            problem_set_id = await connection.fetchval(
                "SELECT id FROM problem_sets WHERE title = $1 AND is_hidden = false LIMIT 1", PROBLEM_SET_TITLE)
            if problem_set_id is None:
                problem_set_id = await connection.fetchval(
                    "INSERT INTO problem_sets (id, title, description, is_hidden) "
                    "VALUES (gen_random_uuid(), $1, $2, false) RETURNING id",
                    PROBLEM_SET_TITLE, PROBLEM_SET_DESC)
            for q in questions:
                await connection.execute(
                    "INSERT INTO questions (id, problem_set_id, title, description, difficulty, time_limit, "
                    "memory_limit, starter_code, test_cases, generated_by_ai) "
                    "VALUES (gen_random_uuid(), $1, $2, $3, $4, $5, $6, $7::jsonb, $8::jsonb, true)",
                    problem_set_id, q["title"], q["description"], q["difficulty"], q["time_limit"],
                    q["memory_limit"], json.dumps(q["starter_code"]), json.dumps(q["test_cases"]))
    finally:
        await connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Nạp đề do AI sinh vào DB cho trận đấu.")
    parser.add_argument("--count", type=int, default=9, help="số đề cần tạo (mặc định 9)")
    parser.add_argument("--difficulty", default=",".join(DIFFICULTIES), help="EASY,MEDIUM,HARD (luân phiên)")
    parser.add_argument("--topics", default=",".join(SAMPLE_TOPICS), help="danh sách chủ đề, phân cách bằng dấu phẩy")
    parser.add_argument("--dry-run", action="store_true", help="chỉ tạo và in đề, không ghi DB")
    args = parser.parse_args()

    difficulties = [d.strip().upper() for d in args.difficulty.split(",") if d.strip().upper() in DIFFICULTIES]
    topics = [t.strip() for t in args.topics.split(",") if 2 <= len(t.strip()) <= 50]
    if not difficulties or not topics or args.count < 1:
        sys.exit("Tham số không hợp lệ: cần ít nhất 1 độ khó, 1 chủ đề (2-50 ký tự) và --count >= 1.")

    config = load_ai_config()
    database_url = None if args.dry_run else load_database_url()
    print(f"AI: {config['provider']} / {config['model']}")

    created = []
    for index in range(args.count):
        difficulty = difficulties[index % len(difficulties)]
        topic = random.choice(topics)
        print(f"[{index + 1}/{args.count}] {topic} - {difficulty}")
        try:
            question = generate_one(config, topic, difficulty)
        except RuntimeError as error:
            print(f"    bỏ qua: {error}")
            continue
        created.append(question)
        print(f"    OK: {question['title']} ({len(question['test_cases'])} testcase)")

    if not created:
        sys.exit("Không tạo được đề nào.")
    if args.dry_run:
        print(json.dumps(created, ensure_ascii=False, indent=2))
        return
    asyncio.run(save_questions(database_url, created))
    print(f"Đã nạp {len(created)} đề vào DB (problem set \"{PROBLEM_SET_TITLE}\").")


if __name__ == "__main__":
    main()
