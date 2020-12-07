# oarepo-enrollments



[![image][]][1]
[![image][2]][3]
[![image][4]][5]
[![image][6]][7]
[![image][8]][9]

  [image]: https://img.shields.io/travis/oarepo/oarepo-enrollments.svg
  [1]: https://travis-ci.com/oarepo/oarepo-enrollments
  [2]: https://img.shields.io/coveralls/oarepo/oarepo-enrollments.svg
  [3]: https://coveralls.io/r/oarepo/oarepo-enrollments
  [4]: https://img.shields.io/github/tag/oarepo/oarepo-enrollments.svg
  [5]: https://github.com/oarepo/oarepo-enrollments/releases
  [6]: https://img.shields.io/pypi/dm/oarepo-enrollments.svg
  [7]: https://pypi.python.org/pypi/oarepo-enrollments
  [8]: https://img.shields.io/github/license/oarepo/oarepo-enrollments.svg
  [9]: https://github.com/oarepo/oarepo-enrollments/blob/master/LICENSE

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
	* [Handler registration](#Handler-registration)
	* [Revoking user](#Revoking-user)
	* [Listing enrollments](#Listing-enrollments)
* [API](#API)
	* [``enroll``](#``enroll``)
	* [``EnrollmentHandler``](#``EnrollmentHandler``)
	* [``Enrollment``](#``Enrollment``)
* [REST API](#REST-API)
	* [Enrolling user via POST](#Enrolling-user-via-POST)
	* [List enrollments](#List-enrollments)
	* [Getting enrollment](#Getting-enrollment)
	* [Revoking enrollment](#Revoking-enrollment)
	* [Security](#Security)
		* [``OAREPO_ENROLLMENT_LIST_PERMISSION_FACTORY``](#``OAREPO_ENROLLMENT_LIST_PERMISSION_FACTORY``)
		* [``OAREPO_ENROLLMENT_LIST_PERMISSION_FILTER``](#``OAREPO_ENROLLMENT_LIST_PERMISSION_FILTER``)
		* [``OAREPO_ENROLLMENT_RETRIEVE_PERMISSION_FACTORY``](#``OAREPO_ENROLLMENT_RETRIEVE_PERMISSION_FACTORY``)
		* [``OAREPO_ENROLLMENT_ENROLL_PERMISSION_FACTORY``](#``OAREPO_ENROLLMENT_ENROLL_PERMISSION_FACTORY``)
		* [``OAREPO_ENROLLMENT_REVOKE_PERMISSION_FACTORY``](#``OAREPO_ENROLLMENT_REVOKE_PERMISSION_FACTORY``)
* [Command-line tools](#Command-line-tools)
	* [Listing enrollments on cmdline](#Listing-enrollments-on-cmdline)
	* [Revoking enrollments on cmdline](#Revoking-enrollments-on-cmdline)
	* [Creating enrollments on cmdline](#Creating-enrollments-on-cmdline)
* [Configuration](#Configuration)
* [Templates](#Templates)
* [Signals](#Signals)


## Installation

```bash
    pip install oarepo-enrollments
```

## Usage

### Enrolling user

To enroll user, call

```python

from oarepo_enrollments import enroll

enroll(
    enrollment_type='role',
    recipient='sample.user@test.com',
    subject='You have become a curator !',
    body="""
Dear user,
by clicking on the link below you will become a curator for this repository.

    {{ enrollment_url }}

Congratulations!
    """,

    # extra params need by the enrollment handler, in this case the role to assign the user to
    extra_data=dict(role='curators')
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

from oarepo_enrollments import EnrollmentHandler

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

### Handler registration

Register handler in setup.py:

```python
setup(
  # ...
  entry_points={
    'oarepo_enrollments.enrollments': [
        'role = my.module:AssignRole',
    ],
  }
)
```

### Revoking user

```python

from oarepo_enrollments import revoke

revoke(
    enrollment=<instance of enrollment, key or id>
)
```

### Listing enrollments

If you have specified "external_key" when creating the enrollment, you can list the enrollments
by the key and enrollment type:

```python

from oarepo_enrollments import list_enrollments

for enrollment in list_enrollments(external_key='test', enrollment_type='role'):
    print(enrollment)
```

## API

### ``enroll``

```python

from oarepo_enrollments import enroll, ENROLL_MANUALLY, ENROLL_AUTOMATICALLY, ENROLL_SKIP_EMAIL

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
    actions=None,            # actions
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

**Actions** might be an array of strings associated with the enrollment. They can be used
to provide searchable granularity to enrollments. For example, if the enrollment means
"right to a collection", the actions might be an array of "read", "update", "delete".


### ``EnrollmentHandler``

```python
from oarepo_enrollments.models import Enrollment
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

    email_template = {
        'subject': None,
        'body': None,
        'html': None
    }

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

### ``Enrollment``

A database model containing enrollment status.

## REST API

### Enrolling user via POST

```
POST /api/enroll/
```
```json5
{
    enrollment_type: "role", // enrollment type, role is a built in enrollment type
    recipient: "someone@example.com",
    email_template: "role-enrollment-email",
    language: "language for email translations",
    mode: "manual | automatic | skip_email",
    external_key: "caller key - any - for later identification",
    // any args that will get passed to the handler
    role: 'test',
    actions: ['test']
}
```
Returns:

```json5
{
    'id': 1,
    'enrollment_type': 'role',
    'enrolled_email': 'someone@example.com',
    'enrolled_user': null,
    'granting_user': {
        'email': 'granting@example.com'   // always the current user
    },
    'state': 'Pending',
    'external_key': 'caller key - any - for later identification',
    'extra_data': {
        'role': 'test'
    },
    'start_timestamp': '2020-12-04T08:48:12.873987',
    'expiration_timestamp': '2020-12-18T08:48:12.873987',
    'accepted_timestamp': null,
    'failure_reason': null,
    'finalization_timestamp': null,
    'rejected_timestamp': null,
    'revocation_timestamp': null,
    'revoker': null,
    'user_attached_timestamp': null,
    'actions': ['test']
}
```

An email will be sent to the user with the content (given by the template, see ``OAREPO_ENROLLMENT_MAIL_TEMPLATES``
in configuration):

```make
Content-Type: text/plain; charset="utf-8"
MIME-Version: 1.0
Content-Transfer-Encoding: 7bit
Subject: New role assigned to you
From: granting@example.com
To: someone@example.com
Date: Fri, 04 Dec 2020 10:11:08 +0100
Message-ID: <160707306860.2310753.11343254980107038800@krokd.local>
Reply-To: granting@example.com

miroslav.simek@vscht.cz wants to assign you a role "test" in UCT repository.
To accept or reject the role, please click on

https://localhost/enroll/j2eh-ctr0-q2d6-4drb-y7kc-mapt-axfd-3053

Thank you for your cooperation,

repository@UCT
```

**Note:** Key or enrollment url (sent via email) is not returned for security reasons. If you need to pass it
to javascript, make your own enrollment API. See [oarepo_enrollment/views/api.py](oarepo_enrollments/views/api.py)
for details.

### List enrollments

```
GET /api/enroll/?enrollment_type=<abc>&external_key=<abc>&state=[pending,linked,accepted,rejected,success,failure,revoked]&page=&size=10
```
Returns:
```json5
{
    "pagination": {
        "currentPage": "/api/enroll/?size=20&page=1",
        "hasNext": false,
        "hasPrev": false,
        "pages": 1,
        "size": 20,
        "totalElements": 1
    },
    "data": [
        {
            "id": 1,
            // as in get below
        }
    ]
}
```

**Note:** Key (sent via email) is not returned for security reasons.

### Getting enrollment

```
GET /api/enroll/<id>
```
Returns:
```json5
{
    "id": 1,
    "enrollment_type": "role",
    "external_key": null,
    "enrolled_email": "someone@example.com",
    "enrolled_user": null,
    "granting_user": {
        "email": "granting@example.com"
    },
    "revoker": null,
    "extra_data": {
        "role": "test"
    },
    "state": "Pending",
    "actions": ["test"],
    "start_timestamp": "Thu, 03 Dec 2020 21:26:40 -0000",
    "expiration_timestamp": "Thu, 17 Dec 2020 21:26:40 -0000",
    "user_attached_timestamp": null,
    "accepted_timestamp": null,
    "rejected_timestamp": null,
    "finalization_timestamp": null,
    "revocation_timestamp": null,
    "failure_reason": null
}
```

**Note:** Key (sent via email) is not returned for security reasons.

### Revoking enrollment

```
DELETE /api/enroll/<id>
```
Returns:
```json5
{
    'id': 1,
    'state': 'Revoked',
    'revocation_timestamp': '2020-12-04T08:48:12.873987',
    'revoker': {'email': 'revoker@example.com'},
    // ... rest of data
}
```


### Security

The following configuration options define who has access to enrollments:

#### ``OAREPO_ENROLLMENT_LIST_PERMISSION_FACTORY``

Factory (or import string) returning Permission (or an object with ``can`` method) that limits access to listing.
For extensibility reasons the factory function must accept ``**kwargs``

#### ``OAREPO_ENROLLMENT_LIST_PERMISSION_FILTER``

A function (or import string) that takes ``Enrollment.query`` as argument and returns filtered
query set. The function might, for example, limit the enrollments only to those created
by the ``current_user``.

The default implementation returns the input query without modification

#### ``OAREPO_ENROLLMENT_RETRIEVE_PERMISSION_FACTORY``

Factory (or import string) that takes ``enrollment: Enrollment`` instance and returns Permission.
For extensibility reasons the factory function must accept ``**kwargs``

#### ``OAREPO_ENROLLMENT_ENROLL_PERMISSION_FACTORY``

Factory (or import string) that returns Permission representing if user can create an enrollment.
The factory gets enrollment data passed in request as ``enrollment`` named parameter.
For extensibility reasons the factory function must accept ``**kwargs``

#### ``OAREPO_ENROLLMENT_REVOKE_PERMISSION_FACTORY``

Factory (or import string) that returns Permission representing if user can revoke an enrollment.
The factory gets enrollment instance as ``enrollment: Enrollment`` named parameter.
For extensibility reasons the factory function must accept ``**kwargs``


## Command-line tools

### Listing enrollments on cmdline

```bash
$ invenio oarepo:enroll list --state=Revoked

enrolled_user      id  key    operation                  recipient        state    type
---------------  ----  -----  -------------------------  ---------------  -------  ------
                    2  vscht  read,update,delete,create  simeki@vscht.cz  Revoked  role

$ invenio oarepo:enroll list --state=Revoked --format=json
[
    {
        "id": 2,
        "type": "role",
        "key": "vscht",
        "recipient": "simeki@vscht.cz",
        "enrolled_user": "",
        "state": "Revoked",
        "operation": "read,update,delete,create",
        "actions": []
    }
]
```

Options:

  * ``--enrollment-type`` - filter for this enrollment type
  * ``--external-key`` - only return enrollments with this external key
  * ``--state`` - only return enrollments in this state. Can be a list of
    "Pending", "Success", "Accepted", "Not accepted", "User attached", "Failed", "Revoked"
    separated by comma
  * ``--actions`` - only return enrollments with these comma-separated actions


### Revoking enrollments on cmdline

```bash
$ invenio oarepo:enroll revoke <enrollment_id>
```

### Creating enrollments on cmdline

```bash
# invenio oarepo:enroll enroll <enrollment_type> <recipient_email> <external_key> <extra_data>
$ invenio oarepo:enroll enroll role simeki@vscht.cz vscht role=test
```

Arguments:

  * ``enrollment_type`` - the enrollment type for the new enrollment
  * ``recipient_email`` - the email of the recipinet
  * ``external_key`` - any string identifying the enrollment for out-of-this-library purposes
  * ``extra_data`` - any extra data required by the enrollment's handler. Either use:
     * `key=value`
     * `{json_serialization of extra_data object}`

Options:
  * ``--email-template`` - the email template to be used. If unset, defaults to 'default'
  * ``--enrollment-method`` - the enrollment method. Use 'automatic', 'manual', 'skip-email',
     see above for the meaning
  * ``--expiration`` - override the default enrollment expiration period

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

# pre-configured mail templates
OAREPO_ENROLLMENT_MAIL_TEMPLATES = {
    'default': {
        'subject': 'You are being enrolled!',
        'body': 'Click {{ enrollment_url }} to participate.',
        'html': False
    }
}

# user under which commandline tasks (enroll, revoke) are logged
OAREPO_ENROLLMENT_CMDLINE_USER = None
```

## Templates

If you use HTML views provided by this library, you can customize them as follows:

   * Specify your own base template (path within ``templates``) in ``OAREPO_ENROLLMENT_BASE_TEMPLATE``.
      The template must provide ``title`` and ``content`` blocks
   * Override the templates completely in your application templates.
     They are in ``oarepo/enrollment`` folder and are called
     ``accept.html``, ``failure.html``, ``reject.html``, ``success.html``. See the sources for passed
     parameters etc.
   * Override templates for a single enrollment type. In your handler, set the appropriate ``*_url``
     properties

## Signals

```python
import oarepo_enrollments.signals

oarepo_enrollments.signals.enrollment_linked
"""Notifies receivers that enrollment has been linked to an invenio user

:param  enrollment: the linked enrollment
"""

oarepo_enrollments.signals.enrollment_created
"""Notifies receivers that enrollment has been created.

:param  enrollment: the linked enrollment
:return True if no notification should be sent
"""

oarepo_enrollments.signals.enrollment_accepted
"""Notifies receivers that enrollment has been accepted (when accept is required)

:param  enrollment: the accepted enrollment
"""

oarepo_enrollments.signals.enrollment_rejected
"""Notifies receivers that enrollment has been rejected (when accept is required)

:param  enrollment: the rejected enrollment
"""

oarepo_enrollments.signals.enrollment_successful
"""Notifies receivers that enrollment has been successfully carried out

:param  enrollment: the successful enrollment
"""

oarepo_enrollments.signals.enrollment_failed
"""Notifies receivers that enrollment failed.

:param  enrollment: the failed enrollment
:param  exception: failure exception
"""

oarepo_enrollments.signals.enrollment_duplicit_user
"""Notifies receivers that the same enrollment is used by two different accounts.

:param  enrollment: the failed enrollment
:param  impostor: the second user that wants to use the enrollment
"""

oarepo_enrollments.signals.enrollment_revoked
"""Notifies receivers that enrollment has been successfully revoked

:param  enrollment: the revoked enrollment
"""

oarepo_enrollments.signals.revocation_failed
"""Notifies receivers that revocation failed.

:param  enrollment: the failed enrollment
:param  exception: failure exception
"""
```
