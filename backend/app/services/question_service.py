
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ProblemSet, Question, Room
from app.utils.starter_code import BASIC_STARTER_CODE

FALLBACK_QUESTIONS = [
    {
        "title": "Sum Two Integers",
        "description": "## Mô tả\nĐọc hai số nguyên `a` và `b`, in ra tổng của chúng.\n\n## Input\nMột dòng gồm hai số nguyên `a` và `b`.\n\n## Output\nIn ra `a + b`.\n\n## Giới hạn\n`-10^9 ≤ a, b ≤ 10^9`.",
        "difficulty": "EASY",
        "test_cases": [
            {"input": "2 3", "expected_output": "5", "is_hidden": False},
            {"input": "-4 9", "expected_output": "5", "is_hidden": True},
            {"input": "0 0", "expected_output": "0", "is_hidden": True},
        ],
    },
    {
        "title": "Maximum of Three Numbers",
        "description": "## Mô tả\nCho ba số nguyên, hãy in số lớn nhất.\n\n## Input\nMột dòng gồm ba số nguyên `a`, `b`, `c`.\n\n## Output\nIn ra giá trị lớn nhất.\n\n## Giới hạn\n`-10^9 ≤ a, b, c ≤ 10^9`.",
        "difficulty": "EASY",
        "test_cases": [
            {"input": "4 9 2", "expected_output": "9", "is_hidden": False},
            {"input": "-3 -1 -8", "expected_output": "-1", "is_hidden": True},
            {"input": "7 7 2", "expected_output": "7", "is_hidden": True},
        ],
    },
    {
        "title": "Count Positive Numbers",
        "description": "## Mô tả\nCho danh sách `n` số nguyên, hãy đếm có bao nhiêu số dương.\n\n## Input\nDòng đầu là `n`. Dòng tiếp theo gồm `n` số nguyên.\n\n## Output\nIn ra số lượng số dương.\n\n## Giới hạn\n`1 ≤ n ≤ 100000`, `-10^9 ≤ a[i] ≤ 10^9`.",
        "difficulty": "EASY",
        "test_cases": [
            {"input": "5\n-2 0 4 8 -1", "expected_output": "2", "is_hidden": False},
            {"input": "3\n-1 -5 -9", "expected_output": "0", "is_hidden": True},
            {"input": "4\n1 2 3 4", "expected_output": "4", "is_hidden": True},
        ],
    },
    {
        "title": "Greatest Common Divisor",
        "description": "## Mô tả\nCho hai số nguyên không âm `a` và `b`, hãy in ước chung lớn nhất của chúng.\n\n## Input\nMột dòng gồm `a` và `b`.\n\n## Output\nIn ra `gcd(a, b)`.\n\n## Giới hạn\n`0 ≤ a, b ≤ 10^9`; ít nhất một số khác 0.",
        "difficulty": "EASY",
        "test_cases": [
            {"input": "18 24", "expected_output": "6", "is_hidden": False},
            {"input": "7 13", "expected_output": "1", "is_hidden": True},
            {"input": "0 25", "expected_output": "25", "is_hidden": True},
        ],
    },
]


async def pick_question(db: AsyncSession, problem_set_id: UUID | None) -> Question | None:
    """Bốc ngẫu nhiên 1 câu hỏi thuộc bộ đề không bị ẩn (nếu có problem_set_id thì chỉ trong bộ đó)."""
    stmt = (
        select(Question)
        .join(ProblemSet, ProblemSet.id == Question.problem_set_id)
        .where(ProblemSet.is_hidden.is_(False))
    )
    if problem_set_id is not None:
        stmt = stmt.where(Question.problem_set_id == problem_set_id)
    recent_question_ids = select(Room.question_id).where(
        Room.question_id.is_not(None)
    ).order_by(Room.created_at.desc()).limit(2)
    fresh = (await db.execute(
        stmt.where(Question.id.not_in(recent_question_ids)).order_by(func.random()).limit(1)
    )).scalars().first()
    if fresh is not None:
        return fresh
    return (await db.execute(stmt.order_by(func.random()).limit(1))).scalars().first()


async def ensure_fallback_question(db: AsyncSession) -> Question:
    """Create a usable public fallback question and set when the database is empty."""
    await db.execute(select(func.pg_advisory_xact_lock(721943854)))
    problem_set = await db.scalar(
        select(ProblemSet).where(ProblemSet.title == "AI Generated").limit(1)
    )
    if problem_set is None:
        problem_set = ProblemSet(
            title="AI Generated",
            description="Đề thi được tạo tự động và đề dự phòng.",
        )
        db.add(problem_set)
        await db.flush()

    existing_titles = set((await db.scalars(
        select(Question.title).where(Question.problem_set_id == problem_set.id)
    )).all())
    for item in FALLBACK_QUESTIONS:
        if item["title"] in existing_titles:
            continue
        db.add(Question(
            problem_set_id=problem_set.id,
            title=item["title"],
            description=item["description"],
            difficulty=item["difficulty"],
            time_limit=2.0,
            memory_limit=128,
            starter_code=BASIC_STARTER_CODE,
            test_cases=item["test_cases"],
            generated_by_ai=False,
        ))
    await db.flush()
    return await pick_question(db, problem_set.id)
