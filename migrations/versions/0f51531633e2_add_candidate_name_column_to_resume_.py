"""Add candidate_name column to Resume model

Revision ID: 0f51531633e2
Revises: 200e54fdedf2
Create Date: 2024-08-31 02:54:30.806236

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0f51531633e2'
down_revision = '200e54fdedf2'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('resume', schema=None) as batch_op:
        batch_op.add_column(sa.Column('candidate_name', sa.String(length=128), nullable=False))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('resume', schema=None) as batch_op:
        batch_op.drop_column('candidate_name')

    # ### end Alembic commands ###
