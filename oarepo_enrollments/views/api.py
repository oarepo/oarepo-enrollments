from functools import lru_cache, wraps, cached_property

from flask import current_app, Blueprint
from flask_login import current_user
from flask_rest_paginate import Pagination
from flask_restful import Resource, abort, Api, fields as rf, output_json
from invenio_base.utils import obj_or_import_string
from invenio_db import db
from flask import request
from webargs import fields
from webargs.flaskparser import use_kwargs, use_args

from oarepo_enrollments import revoke, enroll
from oarepo_enrollments.models import Enrollment
from oarepo_enrollments.proxies import current_enrollments
import flask_restful


class UserField(rf.Nested):
    def __init__(self, **kwargs):
        super().__init__({
            'email': rf.String
        }, **kwargs)


@lru_cache(maxsize=32)
def get_permission_factory(perm_or_factory):
    perm_or_factory = obj_or_import_string(perm_or_factory)

    def func(*args, **kwargs):
        if callable(perm_or_factory):
            return perm_or_factory(*args, **kwargs)
        return perm_or_factory

    return func


def need_config_permission(perm_name):
    def permission_wrapper(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            perm = get_permission_factory(current_app.config[perm_name])
            perm = perm(**kwargs)
            if not perm.can():
                from flask_login import current_user
                if not current_user.is_authenticated:
                    abort(401)
                abort(403)
            return f(*args, **kwargs)

        return wrapper

    return permission_wrapper


def pass_enrollment(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        enrollment = Enrollment.query.get(kwargs['id'])
        return f(*args, **kwargs, enrollment=enrollment)

    return wrapper


class EnrollmentBase:
    @cached_property
    def enrollment_fields(self):
        user_field_class = obj_or_import_string(
            current_app.config['OAREPO_ENROLLMENT_USER_RESTFUL_SERIALIZATION_CLASS'])
        return {
            'id': rf.Integer,
            'enrollment_type': rf.String,
            'external_key': rf.String,
            'enrolled_email': rf.String,
            'enrolled_user': user_field_class(allow_null=True),
            'granting_user': user_field_class,
            'revoker': user_field_class(allow_null=True),
            'extra_data': rf.Raw,
            'state': rf.String,
            'start_timestamp': rf.DateTime(dt_format='iso8601'),
            'expiration_timestamp': rf.DateTime(dt_format='iso8601'),
            'user_attached_timestamp': rf.DateTime(dt_format='iso8601'),
            'accepted_timestamp': rf.DateTime(dt_format='iso8601'),
            'rejected_timestamp': rf.DateTime(dt_format='iso8601'),
            'finalization_timestamp': rf.DateTime(dt_format='iso8601'),
            'revocation_timestamp': rf.DateTime(dt_format='iso8601'),
            'failure_reason': rf.String,
            'actions': rf.List(rf.String)
        }


class NeverEmptyList(list):
    def __bool__(self):
        return True


class EnrollmentListResource(Resource, EnrollmentBase):

    @use_kwargs({
        "external_key": fields.Str(),
        "enrollment_type": fields.Str(),
        "state": fields.Str()
    })
    @need_config_permission('OAREPO_ENROLLMENT_LIST_PERMISSION_FACTORY')
    def get(self, external_key=None, enrollment_type=None, state=None, **kwargs):
        if state:
            state = [x.strip() for x in state.split(',')]
            state = [Enrollment.ENROLLMENT_STATUS_CHOICES_REVERSE.get(s, s) for s in state if s]
        enrollments = Enrollment.list(external_key=external_key, enrollment_type=enrollment_type, state=state)

        query_filter = current_enrollments.list_permission_filter
        enrollments = query_filter(enrollments)

        pagination = Pagination(current_app, db)
        return pagination.paginate(enrollments, self.enrollment_fields, post_query_hook=lambda l: NeverEmptyList(l))

    @need_config_permission('OAREPO_ENROLLMENT_ENROLL_PERMISSION_FACTORY')
    @use_args({
        'enrollment_type': fields.Str(),
        'recipient': fields.Email(),
        'email_template': fields.Str(),
        'language': fields.Str(),
        'mode': fields.Str(),
        'external_key': fields.Str(),
        'expiration_interval': fields.Int(),
        'actions': fields.List(fields.Str())
    })
    def post(self, args):
        extra_data = {k: v for k, v in request.json.items() if k not in args}
        enrollment = enroll(**args, sender=current_user, extra_data=extra_data)
        return output_json(flask_restful.marshal(enrollment, self.enrollment_fields), 201)


class EnrollmentDetailResource(Resource, EnrollmentBase):
    @pass_enrollment
    @need_config_permission('OAREPO_ENROLLMENT_RETRIEVE_PERMISSION_FACTORY')
    def get(self, enrollment=None, **kwargs):
        return flask_restful.marshal(enrollment, self.enrollment_fields)

    @pass_enrollment
    @need_config_permission('OAREPO_ENROLLMENT_REVOKE_PERMISSION_FACTORY')
    def delete(self, enrollment=None, **kwargs):
        revoke(enrollment)
        return flask_restful.marshal(enrollment, self.enrollment_fields)


def create_blueprint_from_app(app):
    blueprint = Blueprint(
        'enrollment_rest',
        __name__,
        template_folder='templates',
        url_prefix='/api/enroll/',
    )
    api = Api(blueprint)
    api.add_resource(EnrollmentDetailResource, '<int:id>', endpoint='detail')
    api.add_resource(EnrollmentListResource, '', endpoint='list')
    return blueprint
