import pkg_resources
from invenio_base.utils import obj_or_import_string
from werkzeug.utils import cached_property

from . import config


class OARepoEnrollmentsState:
    def __init__(self, app):
        self.app = app

    @cached_property
    def handlers(self):
        t = {}
        for entry_point in pkg_resources.iter_entry_points('oarepo_enrollments.enrollments'):
            t[entry_point.name] = entry_point.load()
        return t

    @cached_property
    def list_permission_filter(self):
        permission_filter = self.app.config['OAREPO_ENROLLMENT_LIST_PERMISSION_FILTER']
        permission_filter = obj_or_import_string(permission_filter)
        return permission_filter


class OARepoEnrollmentsExt:
    def __init__(self, app, db=None):
        app.extensions['oarepo-enrollments'] = OARepoEnrollmentsState(app)
        self.init_config(app)

    def init_config(self, app):
        for k in dir(config):
            if k.startswith('OAREPO_ENROLLMENT_'):
                v = getattr(config, k)
                app.config.setdefault(k, v)
