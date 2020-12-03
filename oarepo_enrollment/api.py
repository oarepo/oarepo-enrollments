import enum
from typing import Union
from urllib.parse import urljoin

from flask import render_template_string, url_for, current_app
from flask_login import current_user
from invenio_accounts.models import User

from oarepo_enrollment.models import Enrollment
from oarepo_enrollment.proxies import current_enrollment
from invenio_db import db
from flask_mail import Message


class EnrollmentException(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


class EnrollmentHandler:
    def __init__(self, enrollment: Enrollment):
        self.enrollment = enrollment

    def enroll(self, user: User, **kwargs) -> None:
        raise NotImplementedError('Implement this')

    def revoke(self, user: User, **kwargs) -> None:
        raise NotImplementedError('Implement this')

    @property
    def title(self):
        return (self.__doc__ or '').strip() or self.enrollment.enrollment_type

    @property
    def enrollment_url(self):
        return urljoin(
            current_app.config['SERVER_NAME'],
            current_app.config['OAREPO_ENROLLMENT_URL'].replace('<key>', self.enrollment.key)
        )

    @property
    def success_template(self):
        return 'oarepo/enrollment/success.html'

    @property
    def failure_template(self):
        return 'oarepo/enrollment/failure.html'

    @property
    def accept_template(self):
        return 'oarepo/enrollment/accept.html'

    @property
    def reject_template(self):
        return 'oarepo/enrollment/reject.html'

    @property
    def accept_url(self):
        return self.enrollment.accept_url or urljoin(
            current_app.config['SERVER_NAME'],
            current_app.config['OAREPO_ENROLLMENT_DEFAULT_ACCEPT_URL'].replace('<key>', self.enrollment.key)
        )

    @property
    def acceptance_required(self):
        return False

    @property
    def reject_url(self):
        return self.enrollment.reject_url or urljoin(
            current_app.config['SERVER_NAME'],
            current_app.config['OAREPO_ENROLLMENT_DEFAULT_REJECT_URL'].replace('<key>', self.enrollment.key)
        )

    @property
    def success_url(self):
        return self.enrollment.success_url or urljoin(
            current_app.config['SERVER_NAME'],
            current_app.config['OAREPO_ENROLLMENT_DEFAULT_SUCCESS_URL'].replace('<key>', self.enrollment.key)
        )

    @property
    def failure_url(self):
        return self.enrollment.failure_url or urljoin(
            current_app.config['SERVER_NAME'],
            current_app.config['OAREPO_ENROLLMENT_DEFAULT_FAILURE_URL'].replace('<key>', self.enrollment.key)
        )


class EnrollmentMethod(enum.Enum):
    MANUAL = 'manual'
    AUTOMATIC = 'automatic'
    SKIP_EMAIL = 'skip_email'


def enroll(
    enrollment_type: str,
    recipient: str,
    sender: User,
    sender_email: str = None,
    subject: str = None,
    body: str = None,
    html: bool = False,
    language: str = None,
    mode: EnrollmentMethod = EnrollmentMethod.AUTOMATIC,
    accept_url: str = None,
    reject_url: str = None,
    success_url: str = None,
    failure_url: str = None,
    commit=True,
    external_key: str = None,
    **kwargs
) -> Enrollment:
    if enrollment_type not in current_enrollment.tasks:
        raise AttributeError(
            f'Unknown enrollment {enrollment_type}. Registered enrollment types: {list(current_enrollment.tasks.keys())}')
    if not recipient:
        raise AttributeError('Enrollment recipient must not be empty')
    if not sender:
        raise AttributeError('Enrollment sender must not be empty')
    if not subject and body or not body and subject:
        raise AttributeError('Subject and body must not be empty (or both empty in some circumstances, see the readme)')

    db_enrollment = Enrollment.create(enrollment_type, external_key, recipient, sender, sender_email,
                                      accept_url,
                                      reject_url,
                                      success_url,
                                      failure_url, kwargs)
    try:
        if db_enrollment.state == Enrollment.LINKED:
            if mode == EnrollmentMethod.SKIP_EMAIL:
                # enroll the user automatically, do not send email
                try:
                    return db_enrollment.enroll()
                finally:
                    if commit:
                        db.session.commit()
            elif mode == EnrollmentMethod.AUTOMATIC:
                # enroll the user automatically and send email
                try:
                    db_enrollment.enroll()
                except:
                    if commit:
                        db.session.commit()
                    raise

        if not subject or not body:
            return db_enrollment

        _send_enrollment_main(subject, body, db_enrollment, language, html, kwargs)
    except:
        db_enrollment.revoke()
        raise
    finally:
        if commit:
            db.session.commit()

    return db_enrollment


def _send_enrollment_main(subject, body, db_enrollment, language, html, kwargs):
    template_params = dict(
        enrollment_url=url_for('enrollment:enroll', _external=True, key=db_enrollment.key),
        user=db_enrollment.enrolled_user,
        enrollment=db_enrollment,
        language=language, **kwargs
    )
    subject = render_template_string(subject, **template_params)
    body = render_template_string(body, **template_params)
    mail_headers = {}
    if current_app.config['OAREPO_ENROLLMENT_REAL_SENDER_EMAIL']:
        mail_headers['Sender'] = current_app.config['OAREPO_ENROLLMENT_REAL_SENDER_EMAIL']
    msg = Message(
        subject,
        sender=db_enrollment.granting_email,
        reply_to=db_enrollment.granting_email,
        recipients=[db_enrollment.enrolled_email],
        charset='utf-8',
        extra_headers=mail_headers
    )
    if html:
        msg.html = body
    else:
        msg.body = body
    current_app.extensions['mail'].send(msg)


def revoke(
    enrollment: Union[str, int, Enrollment],
    revoker: User=None,
    commit=True
):
    try:
        if isinstance(enrollment, str):
            enrollment = Enrollment.query.filter_by(external_key=enrollment).one()
        elif isinstance(enrollment, int):
            enrollment = Enrollment.query.get(enrollment)
        enrollment.revoke(revoker or current_user)
    finally:
        if commit:
            db.session.commit()


def list_enrollments(external_key=None, enrollment_type=None, states=None):
    return Enrollment.list(external_key, enrollment_type, states)
