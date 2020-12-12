# models.py
import datetime
import traceback

from flask import current_app
from invenio_accounts.models import User
from invenio_db import db
from sqlalchemy import ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from base32_lib import base32
from sqlalchemy.orm import relationship
from sqlalchemy_utils import ChoiceType
from werkzeug.utils import cached_property

from oarepo_enrollments.fields import StringArrayType, StringArray
from oarepo_enrollments.proxies import current_enrollments
from oarepo_enrollments.signals import enrollment_linked, enrollment_failed, enrollment_successful, enrollment_revoked, \
    revocation_failed, enrollment_accepted, enrollment_rejected, enrollment_duplicit_user


class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    enrollment_type = db.Column(db.String(32), nullable=False)

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
    ENROLLMENT_STATUS_CHOICES_REVERSE = {v: k for k, v in ENROLLMENT_STATUS_CHOICES}
    state = db.Column(ChoiceType(ENROLLMENT_STATUS_CHOICES), default=PENDING, nullable=False)

    actions = db.Column(
        StringArray().with_variant(
            StringArrayType(256),
            dialect_name='sqlite')
    )

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
               expiration_interval=None, extra_data=None, actions=None):
        if not extra_data:
            extra_data = {}
        if not granting_email:
            granting_email = granting_user.email
        if not expiration_interval:
            expiration_interval = current_app.config['OAREPO_ENROLLMENT_EXPIRATION']

        if not current_app.config.get('TESTING', False) and enrollment_type not in current_enrollments.handlers:
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
        e.external_key = external_key
        e.actions = actions
        e.start_timestamp = datetime.datetime.now()
        e.expiration_timestamp = e.start_timestamp + datetime.timedelta(days=expiration_interval)
        if enrolled_user:
            e.state = Enrollment.LINKED
            e.user_attached_timestamp = datetime.datetime.now()
        db.session.add(e)
        return e

    @cached_property
    def handler(self):
        return current_enrollments.handlers[self.enrollment_type](self)

    @property
    def expired(self):
        return datetime.datetime.now() > self.expiration_timestamp

    def check_user_allowed(self, user):
        if self.enrolled_user and self.enrolled_user != user:
            self.failure_reason = f'User {user.email} wants to enroll in ' \
                                  f'an already assigned enrollment {self.handler.title}'
            db.session.add(self)
            enrollment_duplicit_user.send(self, enrollment=self, impostor=user)
            return False
        return True

    def attach_user(self, user):
        assert self.state == Enrollment.PENDING
        self.state = Enrollment.LINKED
        self.user_attached_timestamp = datetime.datetime.now()
        self.enrolled_user = user
        enrollment_linked.send(self, enrollment=self)
        db.session.add(self)

    def enroll(self, user):
        try:
            self.handler.enroll(user, **self.extra_data)
            self.state = Enrollment.SUCCESS
            self.enrolled_user = user
            self.finalization_timestamp = datetime.datetime.now()
            enrollment_successful.send(self, enrollment=self)
            db.session.add(self)
        except Exception as e:
            self.state = Enrollment.FAILURE
            self.failure_reason = getattr(e, 'message', str(e))
            enrollment_failed.send(self, enrollment=self, exception=e)
            self.finalization_timestamp = datetime.datetime.now()
            db.session.add(self)
            raise

    def revoke(self, revoker):
        if revoker and revoker.is_anonymous:
            revoker = None
        self.revoker = revoker
        try:
            self.state = Enrollment.REVOKED
            if self.enrolled_user:
                self.handler.revoke(self.enrolled_user, **self.extra_data)
            self.revocation_timestamp = datetime.datetime.now()
            db.session.add(self)
            enrollment_revoked.send(self, enrollment=self)
        except Exception as e:
            self.failure_reason = getattr(e, 'message', str(e))
            self.revocation_timestamp = datetime.datetime.now()
            db.session.add(self)
            revocation_failed.send(self, enrollment=self, exception=e)
            raise

    def accept(self):
        self.state = Enrollment.ACCEPTED
        self.accepted_timestamp = datetime.datetime.now()
        db.session.add(self)
        enrollment_accepted.send(self, enrollment=self)

    def reject(self):
        self.state = Enrollment.REJECTED
        self.rejected_timestamp = datetime.datetime.now()
        db.session.add(self)
        enrollment_rejected.send(self, enrollment=self)

    @classmethod
    def list(cls, external_key=None, enrollment_type=None, state=None, actions=None):
        ret = None
        if external_key:
            if ret is None:
                ret = cls.query
            ret = ret.filter(cls.external_key == external_key)
        if enrollment_type:
            if ret is None:
                ret = cls.query
            ret = ret.filter(cls.enrollment_type == enrollment_type)
        if state:
            if ret is None:
                ret = cls.query
            ret = ret.filter(cls.state.in_(state))
        if actions:
            if ret is None:
                ret = cls.query
            if isinstance(actions, (list, tuple)):
                for a in actions:
                    ret = ret.filter(cls.actions.any(a))
            else:
                ret = ret.filter(cls.actions.any(actions))
        if ret is None:
            ret = cls.query
        return ret

    def __str__(self):
        ret = ''
        if self.state == Enrollment.PENDING:
            ret = 'pending'
        elif self.state == Enrollment.LINKED:
            ret = f'linked to {self.enrolled_user.email}'
        elif self.state == Enrollment.ACCEPTED:
            ret = f'accepted by {self.enrolled_user.email}'
        elif self.state == Enrollment.REJECTED:
            ret = f'rejected by {self.enrolled_user.email}'
        elif self.state == Enrollment.SUCCESS:
            ret = f'successfully assigned to {self.enrolled_user.email}'
        elif self.state == Enrollment.FAILURE:
            ret = f'failed, enrolled user {self.enrolled_user.email if self.enrolled_user else self.enrolled_email}, ' \
                  f'error {self.failure_reason}'
        elif self.state == Enrollment.REVOKED:
            ret = f'revoked from {self.enrolled_user.email}'
        if self.external_key:
            ret = f'external key={self.external_key}, {ret}'
        return f'Enrollment[key={self.key}, {ret}'
