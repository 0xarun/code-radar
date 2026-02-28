"""initial schema"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("status", sa.Enum("PENDING", "RUNNING", "COMPLETED", "FAILED", name="jobstatus"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_findings", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cached_hits", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration", sa.Float(), nullable=True),
    )
    op.create_table(
        "findings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_path", sa.String(length=1024), nullable=False),
        sa.Column("rule_id", sa.String(length=255), nullable=False),
        sa.Column("severity", sa.String(length=64), nullable=False),
        sa.Column("code_snippet", sa.Text(), nullable=False),
        sa.Column("hash", sa.String(length=128), nullable=False),
        sa.Column("ai_analysis", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_findings_job_id", "findings", ["job_id"])
    op.create_index("ix_findings_hash", "findings", ["hash"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_findings_hash", table_name="findings")
    op.drop_index("ix_findings_job_id", table_name="findings")
    op.drop_table("findings")
    op.drop_table("jobs")
    op.execute("DROP TYPE jobstatus")
