"""Create the current mapped schema on a fresh database."""

from alembic import op

from bot.database import models as _models  # noqa: F401
from bot.database.base import Base

revision = '0001_baseline'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    Base.metadata.create_all(bind=op.get_bind())


def downgrade():
    pass
