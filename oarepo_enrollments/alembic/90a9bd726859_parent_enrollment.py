#
# This file is part of Invenio.
# Copyright (C) 2016-2018 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""parent_enrollment"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '90a9bd726859'
down_revision = '16ffa6cb5954'
branch_labels = ()
depends_on = None


def upgrade():
    """Upgrade database."""
    op.add_column('enrollment', sa.Column('parent_enrollment', sa.Integer(), nullable=True))
    op.create_foreign_key(op.f('fk_enrollment_parent_enrollment_enrollment'), 'enrollment', 'enrollment', ['parent_enrollment'], ['id'])


def downgrade():
    """Downgrade database."""
    op.drop_constraint(op.f('fk_enrollment_parent_enrollment_enrollment'), 'enrollment', type_='foreignkey')
    op.drop_column('enrollment', 'parent_enrollment')
