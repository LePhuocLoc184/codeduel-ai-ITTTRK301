import asyncio
import uuid
import logging
from datetime import datetime, timedelta
import random

from sqlalchemy import select, delete
from app.db.database import AsyncSessionLocal, engine
from app.db.base import Base

# Import đầy đủ 7 Models của CodeDuel AI
from app.models.users import User
from app.models.problem_sets import ProblemSet
from app.models.questions import Question
from app.models.rooms import Room
from app.models.room_players import RoomPlayer
from app.models.submissions import Submission
from app.models.matchmaking_entries import MatchmakingEntry

logger = logging.getLogger(__name__)

# Password hash mặc định cho tất cả user test (Mật khẩu: Password123)
HASHED_PASSWORD = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeg6Lruj3vjPGga31lW"


# ==========================================
# DỮ LIỆU SEED MẪU BÀI TẬP PHONG PHÚ
# ==========================================
SEED_DATA = {
    "users": [
        {
            "username": "phuoc_loc_dev",
            "email": "loc.le@ptit.edu.vn",
            "role": "admin",
            "rating": 1850,
            "rated_games": 50,
            "wins": 40,
            "avatar_url": "https://api.dicebear.com/7.x/bottts/svg?seed=loc_dev",
        },
        {
            "username": "tran_finance",
            "email": "tran.nguyen@hub.edu.vn",
            "role": "user",
            "rating": 1620,
            "rated_games": 35,
            "wins": 24,
            "avatar_url": "https://api.dicebear.com/7.x/bottts/svg?seed=tran_hub",
        },
        {
            "username": "algo_master",
            "email": "algomaster@gmail.com",
            "role": "user",
            "rating": 1780,
            "rated_games": 65,
            "wins": 48,
            "avatar_url": "https://api.dicebear.com/7.x/bottts/svg?seed=algo_master",
        },
        {
            "username": "python_king",
            "email": "pyking@gmail.com",
            "role": "user",
            "rating": 1450,
            "rated_games": 28,
            "wins": 16,
            "avatar_url": "https://api.dicebear.com/7.x/bottts/svg?seed=pyking",
        },
        {
            "username": "cpp_wizard",
            "email": "cppwizard@gmail.com",
            "role": "user",
            "rating": 1320,
            "rated_games": 20,
            "wins": 10,
            "avatar_url": "https://api.dicebear.com/7.x/bottts/svg?seed=cppwizard",
        },
        {
            "username": "noob_coder",
            "email": "noobcoder@gmail.com",
            "role": "user",
            "rating": 1150,
            "rated_games": 12,
            "wins": 3,
            "avatar_url": "https://api.dicebear.com/7.x/bottts/svg?seed=noob",
        },
    ],
    "problem_sets": [
        {
            "title": "Nhập Môn Lập Trình & Thuật Toán Cơ Bản",
            "description": "Bộ bài tập luyện tập xử lý Mảng, Chuỗi, và các cấu trúc điều khiển cơ bản cho C++, Python, Java.",
            "questions": [
                {
                    "title": "Two Sum (Tổng Hai Số)",
                    "description": "Cho mảng số nguyên `nums` và số `target`. Trả về chỉ số 2 số có tổng bằng `target`.",
                    "difficulty": "EASY",
                    "time_limit": 2.0,
                    "memory_limit": 128,
                    "starter_code": {
                        "cpp": "#include <iostream>\n#include <vector>\nusing namespace std;\n\nint main() {\n    // Write C++ code here\n    return 0;\n}",
                        "python": "def two_sum(nums, target):\n    # Write Python code here\n    pass\n",
                        "java": "public class Main {\n    public static void main(String[] args) {\n        // Write Java code here\n    }\n}",
                    },
                    "test_cases": [
                        {"input": "[2, 7, 11, 15]\n9", "expected_output": "[0, 1]", "is_hidden": False},
                        {"input": "[3, 2, 4]\n6", "expected_output": "[1, 2]", "is_hidden": False},
                        {"input": "[3, 3]\n6", "expected_output": "[0, 1]", "is_hidden": True},
                        {"input": "[1, 5, 8, 3]\n11", "expected_output": "[2, 3]", "is_hidden": True},
                    ],
                },
                {
                    "title": "Valid Palindrome (Chuỗi Đối Xứng)",
                    "description": "Kiểm tra một chuỗi có phải đối xứng (Palindrome) hay không sau khi bỏ qua ký tự đặc biệt.",
                    "difficulty": "EASY",
                    "time_limit": 1.5,
                    "memory_limit": 128,
                    "starter_code": {
                        "cpp": "#include <iostream>\nusing namespace std;\nint main() { return 0; }",
                        "python": "def is_palindrome(s: str) -> bool:\n    pass\n",
                        "java": "public class Main { public static void main(String[] args) {} }",
                    },
                    "test_cases": [
                        {"input": "racecar", "expected_output": "true", "is_hidden": False},
                        {"input": "A man, a plan, a canal: Panama", "expected_output": "true", "is_hidden": False},
                        {"input": "hello world", "expected_output": "false", "is_hidden": True},
                    ],
                },
                {
                    "title": "Reverse Integer (Đảo Nguợc Số Nguyên)",
                    "description": "Cho một số nguyên 32-bit `x`, hãy đảo ngược các chữ số của `x`.",
                    "difficulty": "EASY",
                    "time_limit": 2.0,
                    "memory_limit": 128,
                    "starter_code": {
                        "cpp": "#include <iostream>\nusing namespace std;",
                        "python": "def reverse(x: int) -> int:\n    pass",
                        "java": "public class Main {}",
                    },
                    "test_cases": [
                        {"input": "123", "expected_output": "321", "is_hidden": False},
                        {"input": "-123", "expected_output": "-321", "is_hidden": False},
                        {"input": "120", "expected_output": "21", "is_hidden": True},
                    ],
                },
            ],
        },
        {
            "title": "Cấu Trúc Dữ Liệu Nâng Cao & Quy Hoạch Động",
            "description": "Thử thách Rank Gold và Diamond với các thuật toán Đồ thị, Quy hoạch động, Stack/Queue.",
            "questions": [
                {
                    "title": "Longest Increasing Subsequence (LIS)",
                    "description": "Tìm độ dài của dãy con tăng dài nhất trong một mảng số nguyên.",
                    "difficulty": "MEDIUM",
                    "time_limit": 2.0,
                    "memory_limit": 256,
                    "starter_code": {
                        "cpp": "#include <iostream>\nusing namespace std;\nint main() {}",
                        "python": "def length_of_lis(nums):\n    pass\n",
                        "java": "public class Main {}",
                    },
                    "test_cases": [
                        {"input": "[10,9,2,5,3,7,101,18]", "expected_output": "4", "is_hidden": False},
                        {"input": "[0,1,0,3,2,3]", "expected_output": "4", "is_hidden": False},
                        {"input": "[7,7,7,7,7,7]", "expected_output": "1", "is_hidden": True},
                    ],
                },
                {
                    "title": "Valid Parentheses (Kiểm Tra Dấu Ngoặc)",
                    "description": "Sử dụng Stack để kiểm tra chuỗi chứa các ký tự '()', '{}', '[]' có hợp lệ hay không.",
                    "difficulty": "MEDIUM",
                    "time_limit": 1.5,
                    "memory_limit": 128,
                    "starter_code": {
                        "cpp": "#include <iostream>\n#include <stack>",
                        "python": "def is_valid(s: str) -> bool:\n    pass",
                        "java": "public class Main {}",
                    },
                    "test_cases": [
                        {"input": "()[]{}", "expected_output": "true", "is_hidden": False},
                        {"input": "(]", "expected_output": "false", "is_hidden": False},
                        {"input": "([{}])", "expected_output": "true", "is_hidden": True},
                    ],
                },
                {
                    "title": "Coin Change (Bài Toán Đổi Tiền)",
                    "description": "Cho mảng mảng tiền `coins` và tổng tiền `amount`. Tìm số lượng đồng xu ít nhất để tạo nên `amount`.",
                    "difficulty": "HARD",
                    "time_limit": 3.0,
                    "memory_limit": 256,
                    "starter_code": {
                        "cpp": "#include <iostream>",
                        "python": "def coin_change(coins, amount):\n    pass",
                        "java": "public class Main {}",
                    },
                    "test_cases": [
                        {"input": "[1, 2, 5]\n11", "expected_output": "3", "is_hidden": False},
                        {"input": "[2]\n3", "expected_output": "-1", "is_hidden": False},
                        {"input": "[1]\n0", "expected_output": "0", "is_hidden": True},
                    ],
                },
            ],
        },
    ],
}


async def seed_data():
    async with AsyncSessionLocal() as session:
        logger.info("🌱 Đang làm sạch cơ sở dữ liệu cũ...")
        # Xóa dữ liệu cũ theo đúng thứ tự FK
        await session.execute(delete(Submission))
        await session.execute(delete(RoomPlayer))
        await session.execute(delete(MatchmakingEntry))
        await session.execute(delete(Room))
        await session.execute(delete(Question))
        await session.execute(delete(ProblemSet))
        await session.execute(delete(User))
        await session.commit()

        logger.info("👤 1. Đang seed Users (Admin & Players)...")
        created_users = []
        for u in SEED_DATA["users"]:
            user_obj = User(
                username=u["username"],
                email=u["email"],
                password_hash=HASHED_PASSWORD,
                role=u["role"],
                rating=u["rating"],
                rated_games=u["rated_games"],
                wins=u["wins"],
                avatar_url=u["avatar_url"],
            )
            session.add(user_obj)
            created_users.append(user_obj)

        await session.flush()
        admin_user = created_users[0]

        logger.info("📚 2. Đang seed Problem Sets & Questions...")
        created_questions = []
        for ps in SEED_DATA["problem_sets"]:
            ps_obj = ProblemSet(
                title=ps["title"],
                description=ps["description"],
                creator_id=admin_user.id,
                is_hidden=False,
            )
            session.add(ps_obj)
            await session.flush()

            for q in ps["questions"]:
                q_obj = Question(
                    problem_set_id=ps_obj.id,
                    title=q["title"],
                    description=q["description"],
                    difficulty=q["difficulty"],
                    time_limit=q["time_limit"],
                    memory_limit=q["memory_limit"],
                    starter_code=q["starter_code"],
                    test_cases=q["test_cases"],
                    generated_by_ai=False,
                )
                session.add(q_obj)
                created_questions.append(q_obj)

        await session.flush()

        logger.info("⚔️ 3. Đang seed Rooms & Room Players...")
        # Phòng 1: Trận đấu FINISHED
        room1 = Room(
            code="CDUEL1",
            host_id=admin_user.id,
            problem_set_id=created_questions[0].problem_set_id,
            question_id=created_questions[0].id,
            game_mode="RANKED_1V1",
            status="FINISHED",
            rating_applied=True,
            started_at=datetime.utcnow() - timedelta(minutes=20),
            finished_at=datetime.utcnow() - timedelta(minutes=5),
            ai_review={
                "time_complexity_analysis": "Winner đạt O(N) bằng Hash Map, Loser đạt O(N^2) dùng 2 vòng lặp lồng nhau.",
                "space_complexity_analysis": "Winner dùng O(N) bộ nhớ phụ cho dict.",
                "clean_code_evaluation": "Code sạch sẽ, đúng quy chuẩn đặt tên Pythonic.",
                "optimized_solution": {
                    "python": "def two_sum(nums, target):\n    seen = {}\n    for i, n in enumerate(nums):\n        if target - n in seen:\n            return [seen[target - n], i]\n        seen[n] = i",
                    "cpp": "// Optimal C++ Solution\n...",
                },
            },
        )
        # Phòng 2: WAITING Lobby
        room2 = Room(
            code="ROOM99",
            host_id=created_users[1].id,
            problem_set_id=created_questions[0].problem_set_id,
            question_id=None,
            game_mode="CUSTOM_1V1",
            status="WAITING",
            rating_applied=False,
        )
        session.add_all([room1, room2])
        await session.flush()

        # Room Players
        players = [
            RoomPlayer(room_id=room1.id, user_id=admin_user.id, score=100, is_ready=True, elo_change=25),
            RoomPlayer(room_id=room1.id, user_id=created_users[2].id, score=40, is_ready=True, elo_change=-15),
            RoomPlayer(room_id=room2.id, user_id=created_users[1].id, score=0, is_ready=True, elo_change=0),
        ]
        session.add_all(players)

        logger.info("💻 4. Đang seed Submissions...")
        submissions = [
            Submission(
                room_id=room1.id,
                user_id=admin_user.id,
                question_id=created_questions[0].id,
                code_content="def two_sum(nums, target):\n    seen = {}\n    for i, n in enumerate(nums):\n        if target - n in seen:\n            return [seen[target - n], i]\n        seen[n] = i",
                language="python",
                status="PASS",
                passed_test_cases=4,
                total_test_cases=4,
                execution_time=0.03,
                memory_used=13.5,
                error_message=None,
            ),
            Submission(
                room_id=room1.id,
                user_id=created_users[2].id,
                question_id=created_questions[0].id,
                code_content="def two_sum(nums, target):\n    for i in range(len(nums)):\n        for j in range(i+1, len(nums)):\n            if nums[i] + nums[j] == target:\n                return [i, j]",
                language="python",
                status="WRONG_ANSWER",
                passed_test_cases=2,
                total_test_cases=4,
                execution_time=0.15,
                memory_used=14.0,
                error_message="Testcase 3 Output Mismatch",
            ),
        ]
        session.add_all(submissions)

        logger.info("🔍 5. Đang seed Matchmaking Queue...")
        mm_entry = MatchmakingEntry(
            user_id=created_users[3].id,
            game_mode="RANKED_1V1",
            status="searching",
            room_id=None,
        )
        session.add(mm_entry)

        await session.commit()
        logger.info("🎉 HOÀN THÀNH! Đã nạp bộ dữ liệu seed bài tập chuẩn phong phú cho CodeDuel AI.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(seed_data())