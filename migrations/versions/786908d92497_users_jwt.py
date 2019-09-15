"""users jwt

Revision ID: 786908d92497
Revises: 5a11244fecad
Create Date: 2019-09-15 15:15:57.682022

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '786908d92497'
down_revision = '5a11244fecad'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_index('ix_user_token')
        batch_op.drop_column('token_expiration')
        batch_op.drop_column('token')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('token', sa.VARCHAR(length=32), nullable=True))
        batch_op.add_column(sa.Column('token_expiration', sa.DATETIME(), nullable=True))
        batch_op.create_index('ix_user_token', ['token'], unique=1)

    # ### end Alembic commands ###
