"""Bổ sung người thắng chính thức cho phòng đấu đã tồn tại trong PostgreSQL.

Chạy `alembic upgrade head` từ backend để áp dụng. Sửa model Python hoặc gọi
metadata.create_all() không tự thêm cột vào bảng rooms đã tồn tại.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "d19a28f74c01"
# Nối tiếp migration trước để Alembic biết thứ tự thay đổi schema.
down_revision = "0be6fa4d3503"
branch_labels = None
depends_on = None


def upgrade():
    # Nullable để phòng đang chơi và lịch sử cũ không cần gán người thắng giả.
    op.add_column("rooms", sa.Column("winner_id", postgresql.UUID(as_uuid=True), nullable=True))
    # winner_id phải tham chiếu user tồn tại; xóa user chỉ xóa liên kết người thắng.
    op.create_foreign_key("fk_rooms_winner_id", "rooms", "users", ["winner_id"], ["id"], ondelete="SET NULL")


def downgrade():
    # Gỡ khóa ngoại trước rồi mới bỏ cột. Downgrade sẽ mất dữ liệu winner_id
    # đã lưu, dù các thông tin khác của phòng vẫn còn.
    op.drop_constraint("fk_rooms_winner_id", "rooms", type_="foreignkey")
    op.drop_column("rooms", "winner_id")
