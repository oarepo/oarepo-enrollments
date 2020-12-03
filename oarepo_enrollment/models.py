# models.py
import datetime
import traceback

from flask import current_app
from invenio_accounts.models import User
from invenio_db import db
from sqlalchemy.dialects.postgresql import JSONB
from base32_lib import base32
from sqlalchemy.orm import relationship
from sqlalchemy_utils import ChoiceType
from werkzeug.utils import cached_property

from oarepo_enrollment.proxies import current_enrollment


class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    enrollment_type = db.Column(db.String(32), nullable=False, unique=True)

    key = db.Column(db.String(100), nullable=False, unique=True)
    external_key = db.Column(db.String(100))

    enrolled_email = db.Column(db.String(128), nullable=False)
    enrolled_user_id = db.Column(db.Integer, db.ForeignKey(User.id), name="enrolled_user")
    enrolled_user = relationship(User, foreign_keys=[enrolled_user_id])

    granting_user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False, name="granting_user")
    granting_user = relationship(User, foreign_keys=[granting_user_id])
    granting_email = db.Column(db.String(128))

    revoker_id = db.Column(db.ForeignKey(User.id), name="revoker")
    revoker = relationship(User, foreign_keys=[revoker_id])

    extra_data = db.Column(db.JSON().with_variant(JSONB(), dialect_name='postgresql'))

    PENDING = 'P'
    LINKED = 'L'

    ACCEPTED = 'A'
    REJECTED = 'N'

    SUCCESS = 'S'
    FAILURE = 'F'

    REVOKED = 'R'

    ENROLLMENT_STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (SUCCESS, 'Success'),
        (ACCEPTED, 'Accepted'),
        (REJECTED, 'Not accepted'),
        (LINKED, 'User attached'),
        (FAILURE, 'Failed'),
        (REVOKED, 'Revoked'),
    ]
    state = db.Column(ChoiceType(ENROLLMENT_STATUS_CHOICES), default=PENDING, nullable=False)

    start_timestamp = db.Column(db.DateTime(), nullable=False)
    expiration_timestamp = db.Column(db.DateTime(), nullable=True)

    user_attached_timestamp = db.Column(db.DateTime())
    accepted_timestamp = db.Column(db.DateTime())
    rejected_timestamp = db.Column(db.DateTime())
    finalization_timestamp = db.Column(db.DateTime())
    revocation_timestamp = db.Column(db.DateTime())

    failure_reason = db.Column(db.Text())

    accept_url = db.Column(db.String(256))
    reject_url = db.Column(db.String(256))
    success_url = db.Column(db.String(256))
    failure_url = db.Column(db.String(256))

    @classmethod
    def create(cls, enrollment_type, external_key, enrolled_email, granting_user, granting_email=None,
               accept_url=None, reject_url=None, success_url=None, failure_url=None,
               expiration_interval=None, extra_data=None):
        if not extra_data:
            extra_data = {}
        if not granting_email:
            granting_email = granting_user.email
        if not expiration_interval:
            expiration_interval = current_app.config['OAREPO_ENROLLMENT_EXPIRATION']

        if not current_app.config.get('TESTING', False) and enrollment_type not in current_enrollment.handlers:
            raise AttributeError(f'No handler defined for enrollment type {enrollment_type}')

        enrolled_user = User.query.filter_by(email=enrolled_email).one_or_none()
        e = cls()
        e.enrollment_type = enrollment_type
        e.external_key = external_key
        e.key = base32.generate(length=32, split_every=4)
        e.enrolled_email = enrolled_email
        e.enrolled_user = enrolled_user
        e.granting_user = granting_user
        e.granting_email = granting_email or (granting_user.email if granting_user else None)
        e.accept_url = accept_url
        e.reject_url = reject_url
        e.success_url = success_url
        e.failure_url = failure_url
        e.extra_data = extra_data
        e.start_timestamp = datetime.datetime.now()
        e.expiration_timestamp = e.start_timestamp + datetime.timedelta(days=expiration_interval)
        if enrolled_user:
            e.state = Enrollment.LINKED
            e.user_attached_timestamp = datetime.datetime.now()
        db.session.add(e)
        return e

    @cached_property
    def handler(self):
        return current_enrollment.handlers[self.enrollment_type](self)

    @property
    def expired(self):
        return datetime.datetime.now() > self.expiration_timestamp

    def attach_user(self, user):
        assert self.state == Enrollment.PENDING
        self.state = Enrollment.LINKED
        self.user_attached_timestamp = datetime.datetime.now()
        self.enrolled_user = user
        db.session.add(self)

    def enroll(self, user):
        try:
            self.handler.enroll(user, **self.extra_data)
            self.state = Enrollment.SUCCESS
            self.enrolled_user = user
        except Exception as e:
            self.state = Enrollment.FAILURE
            self.failure_reason = getattr(e, 'message', str(e))
            raise
        finally:
            self.finalization_timestamp = datetime.datetime.now()
            db.session.add(self)

    def revoke(self, revoker):
        if not self.enrolled_user:
            return
        self.revoker = revoker
        try:
            self.state = Enrollment.REVOKED
            self.handler.revoke(self.enrolled_user, **self.extra_data)
        except Exception as e:
            self.failure_reason = getattr(e, 'message', str(e))
            raise
        finally:
            self.revocation_timestamp = datetime.datetime.now()
            db.session.add(self)

    def accept(self):
        self.state = Enrollment.ACCEPTED
        self.accepted_timestamp = datetime.datetime.now()
        db.session.add(self)

    def reject(self):
        self.state = Enrollment.REJECTED
        self.rejected_timestamp = datetime.datetime.now()
        db.session.add(self)

    @classmethod
    def list(cls, external_key, state=None):
        ret = cls.query.filter_by(cls.external_key == external_key)
        if state:
            ret = ret.filter_by(state in cls.state)
        return ret
