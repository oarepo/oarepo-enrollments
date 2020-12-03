# oarepo-enrollment


IDEAS ONLY, DO NOT USE


[![image][]][1]
[![image][2]][3]
[![image][4]][5]
[![image][6]][7]
[![image][8]][9]

  [image]: https://img.shields.io/travis/oarepo/oarepo-enrollment.svg
  [1]: https://travis-ci.com/oarepo/oarepo-enrollment
  [2]: https://img.shields.io/coveralls/oarepo/oarepo-enrollment.svg
  [3]: https://coveralls.io/r/oarepo/oarepo-enrollment
  [4]: https://img.shields.io/github/tag/oarepo/oarepo-enrollment.svg
  [5]: https://github.com/oarepo/oarepo-enrollment/releases
  [6]: https://img.shields.io/pypi/dm/oarepo-enrollment.svg
  [7]: https://pypi.python.org/pypi/oarepo-enrollment
  [8]: https://img.shields.io/github/license/oarepo/oarepo-enrollment.svg
  [9]: https://github.com/oarepo/oarepo-enrollment/blob/master/LICENSE

OArepo Enrollment library provides a unified way for admin, curator or other users
to ask person to enroll in a "task". The task might be anything - for example,
assigning role to a member, to participate on editing a record, etc.

The user being enrolled might not yet exist in Invenio user database. If s/he does not,
the enrollment is completed after the user registers.

The enrollment might be "automatic" as well - that is, if the user already exists,
no intervention is required from him/her.


# Table of Contents
* [Installation](#Installation)
* [Usage](#Usage)
	* [Enrolling user](#Enrolling-user)
	* [Handler implementation](#Handler-implementation)
	* [Task registration](#Task-registration)
	* [Revoking user](#Revoking-user)
	* [Listing enrollments](#Listing-enrollments)
	* [API](#API)
		* [``enroll``](#``enroll``)
		* [``EnrollmentHandler``](#``EnrollmentHandler``)
		* [``Enrollment``](#``Enrollment``)
* [Configuration](#Configuration)
* [Templates](#Templates)


## Installation

```bash
    pip install oarepo-enrollment
```

## Usage

### Enrolling user

To enroll user, call

```python

from oarepo_enrollment import enroll

enroll(
    enrollment='role',
    recipient='sample.user@test.com',
    subject='You have become a curator !',
    body="""
Dear user,
by clicking on the link below you will become a curator for this repository.

    {{ enrollment_url }}

Congratulations!
    """,

    # extra params need by the enrollment handler, in this case the role to assign the user to
    role='curators'
)
```

Alternatively, the email subject and body might be omitted - in that case the caller must
notify the user being enrolled.


On the background, this will:

  1. A unique enrollment id is generated and associated with recipent email, kwargs are json-serialized
     and together with id written to the database.
  2. If ``mode`` is ``ENROLL_SKIP_EMAIL``: A check is made if a user with this email
     address already exists. If so, calls the enrollment handler (see below) and returns.
  3.
      a. An email is created and sent. The subject and body are processed as jinja templates,
         receiving enrollment url in context variables.
      b. or caller is responsible for sending the email / text message / notification / etc.
  4. User receives the email / message / notification and clicks on the enrollment link
  5. User must log in or register via standard invenio or 3-rd party registration
  6. An expiration is checked. If expired or already used, user is redirected to appropriate failure page.
  7. Enrollment url view checks if enrollment handler returns True from ``acceptance_required`` property.
     If so, user is redirected to the ``accept_url`` and when accepts the invitation, timestamp is stored
     in the db and user is redirected back to the enrollment url.
  8. Enrollment url view calls the ``enroll`` method on enrollment handler with:
     * current User of the logged-in user
     * any extra kwargs passed to the enroll call
  9. Enrollment handler performs enrollment action (whatever it is). On error raises EnrollmentException
  10. The database record is enriched with timestamp, enrollment status and user instance.
  11. user is redirected via 302 to the redirection success or failure url. These are taken from:
      * urls passed to enroll function
      * urls retrieved from enrollment handler
      * default urls from flask configuration

**Note:** once the enrollment link has been consumed, it can not be reused by a different user.

**Note:** expired link can not be used to enroll, it might be used if user has already enrolled
and user will be redirected to the success url.

### Handler implementation

Enrollment handler is a function with signature:

```python

from oarepo_enrollment import EnrollmentHandler

from invenio_accounts.models import User, Role
from invenio_db import db

class AssignRole(EnrollmentHandler):
    def enroll(self, user: User, role=None, **kwargs) -> bool:
      role = Role.query.filter_by(name=role).one()
      user.roles.append(role)
      db.session.add(user)
      db.session.commit()

    def revoke(self, user: User, role=None, **kwargs) -> bool:
      role = Role.query.filter_by(name=role).one()
      user.roles.remove(role)
      db.session.add(user)
      db.session.commit()
```

### Task registration

Register task in setup.py:

```python
setup(
  # ...
  entry_points={
    'oarepo_enrollment.enrollments': [
        'role = my.module:AssignRole',
    ],
  }
)
```

### Revoking user

```python

from oarepo_enrollment import revoke

revoke(
    enrollment=<instance of enrollment, key or id>
)
```

### Listing enrollments

If you have specified "external_key" when creating the enrollment, you can list the enrollments
by the key and enrollment type:

```python

from oarepo_enrollment import list_enrollments

for enrollment in list(external_key='test', enrollment='role'):
    print(enrollment)
```

### API

#### ``enroll``

```python

from oarepo_enrollment import enroll, ENROLL_MANUALLY, ENROLL_AUTOMATICALLY, ENROLL_SKIP_EMAIL

def enroll(
    enrollment: str,
    recipient: str,
    sender: invenio_accounts.models.User,  # optional, current_user is used if not specified
    sender_email: str,       # optional, sender's email is used if not specified
    subject: str,            # jinja template
    body: str,               # jinja template
    html: bool,              # set true if the body is a html document
    language: str,           # language for flask-babelex
    mode: ENROLL_XXX,        # see below
    accept_url: str,         # override default accept url
    reject_url: str,         # override default reject url
    success_url='url',       # override the success url
    failure_url='url',       # override the failure url
    commit=True,             # commit the changes
    external_key=None,       # set an external key (any string)
    **kwargs                 # any kwargs
) -> None:
    pass
```

The **``mode``** parameter can be:
  * ``ENROLL_MANUALLY`` - always send the enrollment email and enroll user only after clicked on the link
  * ``ENROLL_AUTOMATICALLY`` - if a user with the given email address exists, enroll him/her but send the mail
    as well
  * ``ENROLL_SKIP_EMAIL`` - if a user with the given email address exists, enroll him/her and skip the mail

**``subject``** and **``body``** are jinja templates. The following variables are passed in:
  * ``enrollment_url`` - full enrollment url
  * ``**kwargs`` - all the kwargs
  * ``user`` - if the user has already registered, an instance of ``invenio_accounts.models.User``
  * ``language`` - language parameter

**``urls``** if passed override the default urls returned by the handler. The default implementation
of the handler returns urls from the configuration

#### ``EnrollmentHandler``

```python
from oarepo_enrollment.models import Enrollment
from invenio_accounts.models import User

class EnrollmentHandler:
    def __init__(self, enrollment: Enrollment):
        self.enrollment = enrollment

    def enroll(self, user: User, **kwargs) -> None:
        raise NotImplementedError('Implement this')

    def revoke(self, user: User, **kwargs) -> None:
        raise NotImplementedError('Implement this')

    acceptance_required = False

    title = "human readable title, implicitly self.__doc__"

    # templates, might be overriden to have per-handler specific template

    success_template = 'oarepo/enrollment/success.html'
    failure_template = 'oarepo/enrollment/failure.html'
    accept_template = 'oarepo/enrollment/accept.html'
    reject_template = 'oarepo/enrollment/reject.html'

    # urls, might be overriden if for example using only rest API

    enrollment_url = "url on which user can enroll"
    accept_url = "url on which user can accept the enrollment"
    reject_url = "url to which user is redirected to when he rejected the enrollment"
    success_url = "url to which user is redirected to when he accepted the enrollment"
    failure_url = "url to which user is redirected to when enrollment failed"
```

#### ``Enrollment``

A database model containing enrollment status.

## Configuration

```python
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
```

## Templates

If you use HTML views provided by this library, you can customize them as follows:

   * Specify your own base template (path within ``templates``) in ``OAREPO_ENROLLMENT_BASE_TEMPLATE``.
      The template must provide ``title`` and ``content`` blocks
   * Override the templates completely in your application templates.
     They are in ``oarepo/enrollment`` folder and are called
     ``accept.html``, ``failure.html``, ``reject.html``, ``success.html``. See the sources for passed
     parameters etc.
   * Override templates for a single enrollment type. In your handler, set
