#
# This file is part of Invenio.
# Copyright (C) 2016-2018 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""model"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '816163ff5ad9'
down_revision = '3eb23e67dae3'
branch_labels = ()
depends_on = None


def upgrade():
    """Upgrade database."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('enrollment',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('enrollment_type', sa.String(length=32), nullable=False),
                    sa.Column('key', sa.String(length=100), nullable=False),
                    sa.Column('external_key', sa.String(length=100), nullable=True),
                    sa.Column('enrolled_email', sa.String(length=128), nullable=False),
                    sa.Column('enrolled_user', sa.Integer(), nullable=True),
                    sa.Column('granting_user', sa.Integer(), nullable=False),
                    sa.Column('granting_email', sa.String(length=128), nullable=True),
                    sa.Column('revoker', sa.Integer(), nullable=True),
                    sa.Column('extra_data', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True),
                    sa.Column('state', sa.String(length=1), nullable=False),
                    sa.Column('start_timestamp', sa.DateTime(), nullable=False),
                    sa.Column('expiration_timestamp', sa.DateTime(), nullable=True),
                    sa.Column('user_attached_timestamp', sa.DateTime(), nullable=True),
                    sa.Column('accepted_timestamp', sa.DateTime(), nullable=True),
                    sa.Column('rejected_timestamp', sa.DateTime(), nullable=True),
                    sa.Column('finalization_timestamp', sa.DateTime(), nullable=True),
                    sa.Column('revocation_timestamp', sa.DateTime(), nullable=True),
                    sa.Column('failure_reason', sa.Text(), nullable=True),
                    sa.Column('accept_url', sa.String(length=256), nullable=True),
                    sa.Column('reject_url', sa.String(length=256), nullable=True),
                    sa.Column('success_url', sa.String(length=256), nullable=True),
                    sa.Column('failure_url', sa.String(length=256), nullable=True),
                    sa.ForeignKeyConstraint(['enrolled_user'], ['accounts_user.id'], name=op.f('fk_enrollment_enrolled_user_accounts_user')),
                    sa.ForeignKeyConstraint(['granting_user'], ['accounts_user.id'], name=op.f('fk_enrollment_granting_user_accounts_user')),
                    sa.ForeignKeyConstraint(['revoker'], ['accounts_user.id'], name=op.f('fk_enrollment_revoker_accounts_user')),
                    sa.PrimaryKeyConstraint('id', name=op.f('pk_enrollment')),
                    sa.UniqueConstraint('key', name=op.f('uq_enrollment_key'))
                    )
    # ### end Alembic commands ###


def downgrade():
    """Downgrade database."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('enrollment')
    # ### end Alembic commands ###