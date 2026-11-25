"""Generate, independently review, validate and persist match questions."""
import asyncio
import json
import random

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.database import AsyncSessionLocal
from app.models import ProblemSet, Question, RoomPlayer, User
from app.schemas.questions import QuestionBase, QuestionDifficulty
from app.services.ai_client import ask_json
from app.utils.starter_code import BASIC_STARTER_CODE

TOPICS = ["Array", "String", "Math", "Sorting", "Hash Map", "Two Pointers",
          "Dynamic Programming", "Greedy", "Stack", "Binary Search"]

QUESTION_FORMAT = '''Return a JSON object with title, description (Vietnamese Markdown including
input/output format and constraints), difficulty, time_limit (0 < x <= 10), memory_limit
(1..1024 MB), starter_code with generic TODO scaffolds and at least 4 test_cases.
Each test case has string input, string expected_output and boolean is_hidden. Include at least
one public and one hidden case. Also include reference_solution (Python) for review only.
The task must have a deterministic answer. Do not include markdown fences.'''


def _difficulty(rating: int) -> QuestionDifficulty:
    if rating < 1100:
        return QuestionDifficulty.EASY
    if rating < 1600:
        return QuestionDifficulty.MEDIUM
    return QuestionDifficulty.HARD


async def _ai_problem_set(db: AsyncSession) -> ProblemSet:
    # Serialize first creation across matchmaking tasks without adding a migration.
    await db.execute(select(func.pg_advisory_xact_lock(721943854)))
    problem_set = await db.scalar(select(ProblemSet).where(ProblemSet.title == "AI Generated").limit(1))
    if problem_set is None:
        problem_set = ProblemSet(title="AI Generated", description="Questions generated and reviewed by AI")
        db.add(problem_set)
        await db.flush()
    return problem_set


async def generate_and_save_match_question(db: AsyncSession, room_id) -> Question:
    """Generate and persist one question; the caller handles fallback on any error."""
    if not settings.AI_API_KEY.strip():
        raise RuntimeError("AI is not configured")

    # Read ratings and release the connection before waiting on the provider.
    async with AsyncSessionLocal() as read_db:
        players = (await read_db.scalars(
            select(RoomPlayer).where(RoomPlayer.room_id == room_id)
        )).all()
        ratings = list((await read_db.scalars(select(User.rating).where(
            User.id.in_([player.user_id for player in players])))).all())
        recent_questions = (await read_db.execute(
            select(Question.title, Question.description)
            .where(Question.generated_by_ai.is_(True))
            .order_by(Question.created_at.desc())
            .limit(12)
        )).all()
    average_rating = sum(ratings) // len(ratings) if ratings else 1200
    difficulty, topic = _difficulty(average_rating), random.choice(TOPICS)
    recent_brief = [
        {"title": title, "summary": description[:350]}
        for title, description in recent_questions
    ]

    async def generate_and_review() -> QuestionBase:
        raw = await ask_json(
            "You create programming contest problems. Return only valid JSON. Write the problem in Vietnamese.",
            f"Create a NEW {difficulty.value} programming problem about {topic}. Do not repeat or "
            f"closely resemble these recent questions: {json.dumps(recent_brief, ensure_ascii=False)}. "
            f"Choose a fresh title, algorithm, input shape, and examples. {QUESTION_FORMAT}",
        )
        question_data = {key: raw.get(key) for key in (
            "title", "description", "difficulty", "time_limit", "memory_limit",
            "starter_code", "test_cases", "generated_by_ai")}
        question_data["difficulty"] = difficulty
        question_data["generated_by_ai"] = True
        # Ignore any full solution the model may put in starter_code.
        question_data["starter_code"] = BASIC_STARTER_CODE
        question = QuestionBase.model_validate(question_data)
        if not any(not case.is_hidden for case in question.test_cases):
            raise ValueError("Generated question must have a public testcase")

        review = await ask_json(
            "You independently audit programming problems and testcases. Return only JSON.",
            "Review the problem and run the reference solution mentally against every testcase. "
            "Check ambiguity and expected outputs. Return {verdict: 'OK'|'FIX', issues: [], "
            "corrected_test_cases: []}. If any issue exists, return a complete corrected list.\n" +
            str({"question": question.model_dump(mode="json"),
                 "reference_solution": raw.get("reference_solution", "")}),
        )
        if str(review.get("verdict", "")).upper() != "OK":
            corrected = review.get("corrected_test_cases")
            if not isinstance(corrected, list):
                raise ValueError("AI review rejected the question without corrected testcases")
            question = QuestionBase.model_validate({**question.model_dump(), "test_cases": corrected})
            if not any(not case.is_hidden for case in question.test_cases):
                raise ValueError("Reviewed question must have a public testcase")
        return question

    # Generation and independent review are sequential model calls. Each HTTP call
    # has its own configured timeout; bound the combined workflow to both budgets.
    question = await asyncio.wait_for(
        generate_and_review(), timeout=2 * settings.AI_QUESTION_TIMEOUT_SECONDS
    )

    problem_set = await _ai_problem_set(db)
    saved = Question(
        problem_set_id=problem_set.id,
        title=question.title,
        description=question.description,
        difficulty=question.difficulty.value,
        time_limit=question.time_limit,
        memory_limit=question.memory_limit,
        starter_code=question.starter_code.model_dump(),
        test_cases=[case.model_dump() for case in question.test_cases],
        generated_by_ai=True,
    )
    db.add(saved)
    await db.flush()
    return saved
