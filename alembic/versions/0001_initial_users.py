
"""Create the initial WALOMA user and registration tables."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial_users"
down_revision = None
branch_labels = None
depends_on = None

role_enum = postgresql.ENUM(
    "ADMIN",
    "TREASURER",
    "SECRETARY",
    "MEMBER",
    name="user_role",
    create_type=False,
)

status_enum = postgresql.ENUM(
    "PENDING",
    "APPROVED",
    "REJECTED",
    "SUSPENDED",
    name="account_status",
    create_type=False,
)


def upgrade():
    bind = op.get_bind()

    role_enum.create(bind, checkfirst=True)
    status_enum.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("member_id", sa.String(length=32), nullable=False),
        sa.Column("full_name", sa.String(length=160), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", role_enum, nullable=False),
        sa.Column("status", status_enum, nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "approved_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_users_member_id",
        "users",
        ["member_id"],
        unique=True,
    )

    op.create_index(
        "ix_users_email",
        "users",
        ["email"],
        unique=True,
    )


def downgrade():
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_member_id", table_name="users")
    op.drop_table("users")

    status_enum.drop(op.get_bind(), checkfirst=True)
    role_enum.drop(op.get_bind(), checkfirst=True)
