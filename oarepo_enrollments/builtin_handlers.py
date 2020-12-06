from flask_babelex import gettext
from invenio_accounts.models import User, Role
from invenio_db import db

from oarepo_enrollments.api import EnrollmentHandler


class AssignRole(EnrollmentHandler):
    @property
    def title(self):
        return gettext("role \"%(role)s\"", role=self.enrollment.extra_data['role'])

    def enroll(self, user: User, role=None, **kwargs) -> None:
        role = Role.query.filter_by(name=role).one()
        user.roles.append(role)
        db.session.add(user)
        db.session.commit()

    def revoke(self, user: User, role=None, **kwargs) -> None:
        role = Role.query.filter_by(name=role).one()
        user.roles.remove(role)
        db.session.add(user)
        db.session.commit()


class AssignRoleAccept(AssignRole):

    @property
    def acceptance_required(self):
        return True
