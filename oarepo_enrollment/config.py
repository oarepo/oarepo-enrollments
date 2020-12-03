# default mail link expiration is 14 days
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

# if set, the Sender header will be added, From will be the enrolling user
OAREPO_ENROLLMENT_REAL_SENDER_EMAIL = None

# login url to redirect to when user is not logged in. If not set, SECURITY_LOGIN_URL is used
OAREPO_ENROLLMENT_LOGIN_URL = None

# parameter name for login page that means "redirect after login is successful
OAREPO_ENROLLMENT_LOGIN_URL_NEXT_PARAM = 'next'

# name of the base template, from which enrollment templates inherit. It must supply
# title and content blocks.
OAREPO_ENROLLMENT_BASE_TEMPLATE = 'oarepo/enrollment/base.html'
