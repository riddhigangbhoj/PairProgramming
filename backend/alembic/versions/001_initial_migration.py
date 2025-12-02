"""Initial migration - create rooms table

Revision ID: 001
Revises:
Create Date: 2025-12-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create rooms table
    op.create_table(
        'rooms',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('code', sa.Text(), default='# Start coding here...'),
        sa.Column('language', sa.String(50), default='python'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=True),
    )

    # Create index on name column
    op.create_index(op.f('ix_rooms_name'), 'rooms', ['name'], unique=False)


def downgrade() -> None:
    # Drop index
    op.drop_index(op.f('ix_rooms_name'), table_name='rooms')

    # Drop rooms table
    op.drop_table('rooms')
