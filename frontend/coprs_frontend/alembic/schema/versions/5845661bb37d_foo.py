"""add playgroung column

Revision ID: 5845661bb37d
Revises: 498884ac47db
Create Date: 2014-04-04 11:25:36.216132

"""

# revision identifiers, used by Alembic.
revision = '5845661bb37d'
down_revision = '498884ac47db'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('copr', sa.Column('playground', sa.Boolean(), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('copr', 'playground')
    ### end Alembic commands ###