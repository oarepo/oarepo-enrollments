import pkg_resources
from werkzeug.utils import cached_property

from . import config


class OARepoEnrollmentState:
    def __init__(self, app):
        self.app = app

    @cached_property
    def handlers(self):
        t = {}
        for entry_point in pkg_resources.iter_entry_points('oarepo_enrollment.enrollments'):
            t[entry_point.name] = entry_point.load()
        return t


class OARepoEnrollmentExt:
    def __init__(self, app, db=None):
        app.extensions['oarepo-enrollment'] = OARepoEnrollmentState(app)
        self.init_config(app)

    def init_config(self, app):
        for k in dir(config):
            if k.startswith('OAREPO_ENROLLMENT_'):
                v = getattr(config, k)
                app.config.setdefault(k, v)
