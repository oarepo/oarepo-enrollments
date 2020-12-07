# default mail link expiration is 14 days
from invenio_records_rest.utils import allow_all

# expiration
OAREPO_ENROLLMENT_EXPIRATION = 14

# url for redirection
OAREPO_ENROLLMENT_URL = '/enroll/<key>'

# redirection url if the link has expired
OAREPO_ENROLLMENT_EXPIRED_URL = '/enroll/expired/<key>'

# redirection url if the link has been already consumed
OAREPO_ENROLLMENT_CONSUMED_URL = '/enroll/consumed/<key>'

# default accept url
OAREPO_ENROLLMENT_DEFAULT_ACCEPT_URL = '/enroll/accept/<key>'

# url that user is redirected to if he rejects an enrollment
OAREPO_ENROLLMENT_DEFAULT_REJECT_URL = '/enroll/reject/<key>'

# default url on success (if not specified by the task or caller)
OAREPO_ENROLLMENT_DEFAULT_SUCCESS_URL = '/enroll/success/<key>'

# default url on failure (if not specified by the task or caller)
OAREPO_ENROLLMENT_DEFAULT_FAILURE_URL = '/enroll/failure/<key>'

# pre-configured mail templates
OAREPO_ENROLLMENT_MAIL_TEMPLATES = {
    'default': {
        'subject': 'You are being enrolled!',
        'body': 'Click {{ enrollment_url }} to participate.',
        'html': False
    }
}

# if set, the Sender header will be added, From will be the enrolling user
OAREPO_ENROLLMENT_REAL_SENDER_EMAIL = None

# login url to redirect to when user is not logged in. If not set, SECURITY_LOGIN_URL is used
OAREPO_ENROLLMENT_LOGIN_URL = None

# parameter name for login page that means "redirect after login is successful
OAREPO_ENROLLMENT_LOGIN_URL_NEXT_PARAM = 'next'

# name of the base template, from which enrollment templates inherit. It must supply
# title and content blocks.
OAREPO_ENROLLMENT_BASE_TEMPLATE = 'oarepo/enrollment/base.html'

#
# REST
#
OAREPO_ENROLLMENT_USER_RESTFUL_SERIALIZATION_CLASS = 'oarepo_enrollments.views.api.UserField'

#
# Permissions
#
def allow_all(*args, **kwargs):
    return type('Allow', (), {'can': lambda self: True})()


# Factory (or import string) returning Permission (or an object with ``can`` method) that limits access to listing
OAREPO_ENROLLMENT_LIST_PERMISSION_FACTORY = lambda **kwargs: allow_all()

# A function (or import string) that takes ``Enrollment.query`` as argument and returns filtered
# query set. The function might, for example, limit the enrollments only to those created
# by the ``current_user``.
OAREPO_ENROLLMENT_LIST_PERMISSION_FILTER = lambda queryset: queryset

# Factory (or import string) that takes ``enrollment: Enrollment`` instance and returns Permission.
OAREPO_ENROLLMENT_RETRIEVE_PERMISSION_FACTORY = lambda enrollment=None, **kwargs: allow_all()

# Factory (or import string) that returns Permission representing if user can create an enrollment.
# The factory gets enrollment data passed in request as ``enrollment`` named parameter.
OAREPO_ENROLLMENT_ENROLL_PERMISSION_FACTORY = lambda enrollment=None, **kwargs: allow_all()

# Factory (or import string) that returns Permission representing if user can revoke an enrollment.
# The factory gets enrollment instance as ``enrollment: Enrollment`` named parameter.
OAREPO_ENROLLMENT_REVOKE_PERMISSION_FACTORY = lambda enrollment=None, **kwargs: allow_all()

#
# cmdline
#

# user under which commandline tasks are logged
OAREPO_ENROLLMENT_CMDLINE_USER = None
