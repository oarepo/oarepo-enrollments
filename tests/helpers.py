from flask_security import login_user
from invenio_accounts.models import User

from oarepo_enrollment.builtin_handlers import AssignRole, AssignRoleAccept


def test_login(user_id=None):
    login_user(User.query.get(user_id), remember=True)
    return 'OK'


class LiteEntryPoint:
    def __init__(self, name, val):
        self.name = name
        self.val = val

    def load(self):
        return self.val


def extra_entrypoints(app, group=None, name=None):
    data = {
        'oarepo_enrollment.enrollments': [
            LiteEntryPoint('role', AssignRole),
            LiteEntryPoint('role-accept', AssignRoleAccept),
        ],
    }

    names = data.keys() if name is None else [name]
    for key in names:
        for entry_point in data[key]:
            print(entry_point)
            yield entry_point
