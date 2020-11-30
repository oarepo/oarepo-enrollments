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
	* [Task implementation](#Task-implementation)
	* [API](#API)
		* [``enroll``](#``enroll``)
		* [``EnrollmentResult``](#``EnrollmentResult``)
	* [Configuration](#Configuration)



## Installation

```bash
    pip install oarepo-enrollment
```

## Usage

### Enrolling user

To enroll user, call

```python

from oarepo_enrollment import enroll, ENROLL_MANUALLY, ENROLL_AUTOMATICALLY, ENROLL_SKIP_EMAIL
from flask_login import current_user

enroll(
    task='assign_role',
    recipient='sample.user@test.com',
    sender=current_user,
    subject='You have become a curator !',
    body="""
Dear user,
by clicking on the link below you will become a curator for this repository.

    {{ enrollment_url }}

Congratulations!
    """,
    role='curators'
)


```

On the background, this will:

  1. A unique enrollment id is generated and associated with recipent email, kwargs are json-serialized
     and together with id written to the database.
  2. If ``mode`` is not ``ENROLL_MANUALLY``: A check is made if a user with this email
     address already exists. If so, calls the enrollment task (see below) and returns.
  3. An email is created and sent. The subject and body are processed as jinja templates,
     receiving enrollment url in context variables.
  4. User receives the email and clicks on the enrollment link
  5. User must log in or register via standard invenio or 3-rd party registration
  6. the enrollment task is called with:
     * current User of the logged-in user
     * any extra kwargs passed to the enroll call
  7. the enrollment task returns an EnrollmentResult containing flag if the enrollment
     has been successful and optionally a redirection url
  8. The database record is enriched with timestamp, enrollment status and user instance.
  9. user is redirected via 302 to the redirection url, defaulting to success/failure url

### Task implementation

Task is a function with a signature:

```python

from oarepo_enrollment import EnrollmentResult

from invenio_accounts.models import User, Role
from invenio_db import db


def assing_role_task(user: User, extra_data) -> EnrollmentResult:
  role = Role.query.filter_by(name=extra_data['role']).one()
  user.roles.append(role)
  db.session.add(user)
  db.session.commit()
  return EnrollmentResult.success
```

### Task registration

Register task in setup.py:

```python
setup(
  # ...
  entry_points={
    'oarepo_enrollment.tasks': [
        'assign_role = my.module:assing_role_task',
    ],
  }
)
```

### API

#### ``enroll``

```python

from oarepo_enrollment import enroll, ENROLL_MANUALLY, ENROLL_AUTOMATICALLY, ENROLL_SKIP_EMAIL

def enroll(
    task: str,
    recipient: str,
    sender: invenio_accounts.models.User,
    sender_email: str,       # optional
    subject: str,            # jinja template
    body: str,               # jinja template
    html: bool,              # set true if the body is a html document
    language: str,           # language for flask-babelex
    mode: ENROLL_XXX,        # see below
    success_url='url',       # override the success url
    failure_url='url',       # override the failure url
    **kwargs                 # any kwargs
) -> None:
    pass
```

The ``mode`` parameter can be:
  * ``ENROLL_MANUALLY`` - always send the enrollment email and enroll user only after clicked on the link
  * ``ENROLL_AUTOMATICALLY`` - if a user with the given email address exists, enroll him/her but send the mail
    as well
  * ``ENROLL_SKIP_EMAIL`` - if a user with the given email address exists, enroll him/her and skip the mail

``subject`` and ``body`` are jinja templates. The following variables are passed in:
  * ``enrollment_url`` - full enrollment url
  * ``**kwargs`` - all the kwargs
  * ``user`` - if the user has already registered, an instance of ``invenio_accounts.models.User``
  * ``language`` - language parameter

#### ``EnrollmentResult``

```python
from collections import namedtuple
class EnrollmentResult:
  def __init__(self, status, url=None):
    self.status = status
    self.url = url

EnrollmentResult.success = EnrollmentResult(True)
EnrollmentResult.failure = EnrollmentResult(False)
```
### Configuration

```python

# default mail link expiration is 14 days
OAREPO_ENROLLMENT_EXPIRATION = 14

```
