import os
from urllib.parse import urlparse, urlencode

from flask import Blueprint, render_template, request, redirect, current_app
from flask_login import current_user
from invenio_db import db

from oarepo_enrollments.models import Enrollment


def create_blueprint_from_app(app):
    blueprint = Blueprint(
        'enrollment',
        __name__,
        template_folder='templates',
        url_prefix='',
    )
    blueprint.add_url_rule(app.config['OAREPO_ENROLLMENT_DEFAULT_SUCCESS_URL'], 'success',
                           view_func=default_success_view)
    blueprint.add_url_rule(app.config['OAREPO_ENROLLMENT_DEFAULT_FAILURE_URL'], 'failure',
                           view_func=default_failure_view)
    blueprint.add_url_rule(app.config['OAREPO_ENROLLMENT_DEFAULT_ACCEPT_URL'], 'accept',
                           view_func=default_accept_view, methods=['GET', 'POST'])
    blueprint.add_url_rule(app.config['OAREPO_ENROLLMENT_DEFAULT_REJECT_URL'], 'reject',
                           view_func=default_reject_view)
    blueprint.add_url_rule(app.config['OAREPO_ENROLLMENT_URL'], 'enroll',
                           view_func=enroll_view)

    return blueprint


def default_success_view(key):
    enrollment = Enrollment.query.filter_by(key=key).one()
    return render_template(
        enrollment.handler.success_template,
        BASE=current_app.config['OAREPO_ENROLLMENT_BASE_TEMPLATE'],
        enrollment=enrollment,
        **enrollment.extra_data
    )


def default_failure_view(key):
    enrollment = Enrollment.query.filter_by(key=key).one()
    return render_template(
        enrollment.handler.failure_template,
        BASE=current_app.config['OAREPO_ENROLLMENT_BASE_TEMPLATE'],
        enrollment=enrollment,
        **enrollment.extra_data
    )


def default_accept_view(key):
    enrollment = Enrollment.query.filter_by(key=key).one()
    if request.method == 'POST':
        if request.form.get('accept'):
            enrollment.accept()
            db.session.commit()
            return redirect(enrollment.handler.enrollment_url)
            pass
        else:
            enrollment.reject()
            db.session.commit()
            return redirect(enrollment.handler.reject_url)
    else:
        return render_template(
            enrollment.handler.accept_template,
            BASE=current_app.config['OAREPO_ENROLLMENT_BASE_TEMPLATE'],
            enrollment=enrollment,
            **enrollment.extra_data
        )


def default_reject_view(key):
    enrollment = Enrollment.query.filter_by(key=key).one()
    return render_template(
        enrollment.handler.reject_template,
        BASE=current_app.config['OAREPO_ENROLLMENT_BASE_TEMPLATE'],
        enrollment=enrollment,
        **enrollment.extra_data
    )


def make_login_url(next):
    url = current_app.config['OAREPO_ENROLLMENT_LOGIN_URL'] or current_app.config['SECURITY_LOGIN_URL']
    if not url:
        raise AttributeError('Neither OAREPO_ENROLLMENT_LOGIN_URL nor SECURITY_LOGIN_URL set in the config')
    url += ('&' if urlparse(url).query else '?') + urlencode({
        current_app.config['OAREPO_ENROLLMENT_LOGIN_URL_NEXT_PARAM']: next
    })
    return url


def enroll_view(key):
    if current_user.is_anonymous:
        return redirect(make_login_url(request.url))

    enrollment = Enrollment.query.filter_by(key=key).one()
    try:
        # already registered to someone and someone else reuses the registration url
        if not enrollment.check_user_allowed(current_user):
            db.session.commit()
            return redirect(enrollment.handler.failure_url)

        # user clicked on the link in email more than once
        if enrollment.state == Enrollment.SUCCESS:
            return redirect(enrollment.handler.success_url)

        # if pending, associate with the current user
        if enrollment.state == Enrollment.PENDING:
            enrollment.attach_user(current_user)

        # if user is associated and acceptance is required, redirect to accept page
        if enrollment.state in (Enrollment.LINKED, Enrollment.REJECTED):
            if enrollment.handler.acceptance_required:
                return redirect(enrollment.handler.accept_url)
            else:
                # otherwise just mark as accepted automatically
                enrollment.accept()

        # if already expired, fail
        if enrollment.expired:
            enrollment.state = Enrollment.FAILURE
            enrollment.failure_reason = 'This enrollment has already expired'
            db.session.add(enrollment)
            db.session.commit()
            return redirect(enrollment.handler.failure_url)

        # if accepted, try to enroll (moving to SUCCESS state) and redirect to success url
        # on error, move to FAILED state and redirect to failure url
        if enrollment.state == Enrollment.ACCEPTED:
            try:
                enrollment.enroll(current_user)
                return redirect(enrollment.handler.success_url)
            except:
                return redirect(enrollment.handler.failure_url)

        # on any unhandled state redirect to failure url
        redirect(enrollment.handler.failure_url)
    finally:
        db.session.commit()
