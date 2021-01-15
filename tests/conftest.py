import os

import pytest
from flask import Blueprint
from invenio_accounts.models import User, Role
from invenio_app.factory import create_app as factory_app
from invenio_db import db as _db
from sqlalchemy_utils import database_exists, create_database

from oarepo_enrollments.models import Enrollment
from .helpers import test_login


@pytest.fixture(scope="module")
def create_app():
    """Return invenio app."""
    return factory_app


@pytest.fixture()
def api(app):
    yield app.wsgi_app.mounts['/api']


@pytest.fixture(scope='session')
def celery_config():
    """Celery app test configuration."""
    return {
        'broker_url': 'memory://localhost/',
        'result_backend': 'rpc'
    }


@pytest.fixture(scope="module")
def app_config(app_config):
    """Flask application fixture."""
    app_config = dict(
        TESTING=True,
        JSON_AS_ASCII=True,
        SQLALCHEMY_TRACK_MODIFICATIONS=True,
        PREFERRED_URL_SCHEME='https',
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            'SQLALCHEMY_DATABASE_URI',
            'sqlite:///:memory:'),
        SERVER_NAME='localhost',
        MAIL_SUPPRESS_SEND=True,
        OAREPO_ENROLLMENT_MAIL_TEMPLATES={
            'test-template': {
                'subject': 'subject',
                'body': 'body {{ enrollment_url }}',
                'html': False
            }
        }
    )
    return app_config


@pytest.fixture
def db(app):
    """Returns fresh db."""
    with app.app_context():
        if not database_exists(str(_db.engine.url)) and \
            app.config['SQLALCHEMY_DATABASE_URI'] != 'sqlite://':
            create_database(_db.engine.url)
        _db.create_all()

    yield _db

    # Explicitly close DB connection
    _db.session.close()
    _db.drop_all()


def create_user(db, email):
    u = User()
    u.email = email
    u.active = True
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def granting_user(db):
    return create_user(db, 'granting@example.com')


@pytest.fixture
def enrolled_user(db):
    return create_user(db, 'enrolled@example.com')


@pytest.fixture
def impostor_user(db):
    return create_user(db, 'impostor@example.com')


@pytest.fixture
def pending_user(db):
    return lambda: create_user(db, 'someone@example.com')


@pytest.fixture
def test_role(db):
    r = Role()
    r.name = 'test'
    db.session.add(r)
    db.session.commit()
    return r


@pytest.fixture
def pending_enrollment(db, granting_user):
    enrollment = Enrollment.create(
        'role', 'record:1', 'someone@example.com', granting_user, extra_data=dict(role='test'))
    db.session.commit()
    return enrollment


@pytest.fixture
def expired_enrollment(db, granting_user):
    enrollment = Enrollment.create(
        'role', None, 'someone@example.com', granting_user, extra_data=dict(role='test'),
        expiration_interval=-1  # expired yesterday
    )
    db.session.commit()
    return enrollment


@pytest.fixture
def pending_accept_enrollment(db, granting_user):
    enrollment = Enrollment.create(
        'role-accept', None, 'someone@example.com', granting_user, extra_data=dict(role='test'))
    db.session.commit()
    return enrollment


@pytest.fixture
def linked_enrollment(db, granting_user, enrolled_user):
    enrollment = Enrollment.create(
        'role', 'blah', enrolled_user.email, granting_user, extra_data=dict(role='test'))
    db.session.commit()
    return enrollment


@pytest.fixture
def users(granting_user, enrolled_user, impostor_user):
    return {
        'granting': granting_user,
        'enrolled': enrolled_user,
        'impostor': impostor_user
    }


@pytest.fixture()
def test_blueprint(users, app):
    """Test blueprint with dynamically added testing endpoints."""
    blue = Blueprint(
        '_tests',
        __name__,
        url_prefix='/_tests/'
    )

    if blue.name in app.blueprints:
        del app.blueprints[blue.name]

    if app.view_functions.get('_tests.test_login') is not None:
        del app.view_functions['_tests.test_login']

    blue.add_url_rule('_login/<user_id>', view_func=test_login)

    app.register_blueprint(blue)
    return blue


@pytest.fixture()
def test_api_blueprint(users, api):
    """Test blueprint with dynamically added testing endpoints."""
    blue = Blueprint(
        '_tests',
        __name__,
        url_prefix='/_tests/'
    )

    if blue.name in api.blueprints:
        del api.blueprints[blue.name]

    if api.view_functions.get('_tests.test_login') is not None:
        del api.view_functions['_tests.test_login']

    blue.add_url_rule('_login/<user_id>', view_func=test_login)

    api.register_blueprint(blue)
    return blue
