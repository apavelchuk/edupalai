"""init rev

Revision ID: aceb5ad2a86c
Revises:
Create Date: 2023-02-21 15:25:28.377792

"""
import sqlalchemy as sa
from sqlalchemy_utils.types.uuid import UUIDType
from sqlalchemy_utils.types.choice import ChoiceType
from alembic import op
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'aceb5ad2a86c'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('content',
        sa.Column('id', UUIDType(), nullable=False),
        sa.Column('content', sa.JSON(), nullable=False),
        sa.Column('content_type', ChoiceType([('t', "Tale"), ('f', "Fact")], impl=sa.String()), nullable=False),
        sa.Column('language', ChoiceType([("en", "English"), ("ru", "Russian")], impl=sa.String()), nullable=False),
        sa.Column('audio_url', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.PrimaryKeyConstraint('id'),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('content')
    # ### end Alembic commands ###
