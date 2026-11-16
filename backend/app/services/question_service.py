
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ProblemSet, Question


async def pick_question(db: AsyncSession, problem_set_id: UUID | None) -> Question | None:
    """Bốc ngẫu nhiên 1 câu hỏi thuộc bộ đề không bị ẩn (nếu có problem_set_id thì chỉ trong bộ đó)."""
    stmt = (
        select(Question)
        .join(ProblemSet, ProblemSet.id == Question.problem_set_id)
        .where(ProblemSet.is_hidden.is_(False))
    )
    if problem_set_id is not None:
        stmt = stmt.where(Question.problem_set_id == problem_set_id)
    stmt = stmt.order_by(func.random()).limit(1)
    return (await db.execute(stmt)).scalars().first()
