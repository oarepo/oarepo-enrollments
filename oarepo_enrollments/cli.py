import json
from collections import defaultdict

import click
from click.utils import make_str
from flask import current_app
from flask.cli import with_appcontext
from invenio_accounts.models import User
from tabulate import tabulate

from oarepo_enrollments import enroll, list_enrollments as api_list_enrollments, revoke
from oarepo_enrollments.api import EnrollmentMethod
from oarepo_enrollments.models import Enrollment


class CatchAll(click.Group):
    def resolve_command(self, ctx, args):
        cmd_name = make_str(args[0])
        if cmd_name in self.commands:
            return super().resolve_command(ctx, args)

        # Get the enrollment command
        cmd = self.get_command(ctx, 'enroll')
        return 'enroll', cmd, args


@click.group(name='oarepo:enroll', cls=CatchAll)
def enrollments():
    """OARepo record drafts commands."""


def parse_enrollment_method(method):
    if not method:
        return None
    return {
        'automatic': EnrollmentMethod.AUTOMATIC,
        'manual': EnrollmentMethod.MANUAL,
        'skip_email': EnrollmentMethod.SKIP_EMAIL
    }.get(method.lower().replace('-', '_'))


@enrollments.command('enroll')
@click.argument('enrollment-type')
@click.argument('recipient')
@click.argument('external-key', required=False)
@click.argument('extra-data', nargs=-1)
@click.option('--email-template', help='Mail template to use for mailing the user; if unspecified,  "default" is used')
@click.option('--enrollment-method',
              type=click.Choice(['automatic', 'manual', 'skip_email', 'skip-email'], case_sensitive=False))
@click.option('--expiration', type=int, help="Expiration in days, default value is in the configuration")
@with_appcontext
def enroll_user(enrollment_type, recipient, external_key, extra_data, email_template, enrollment_method, expiration):
    """
    Enrolls user.

    extra-data is a list of either key=value pairs or a serialized json with extra data
    """
    external_key_and_value_list = list(extra_data)
    if external_key:
        external_key_and_value_list.insert(0, external_key)
    external_key = None
    extra_data = {}
    for k in external_key_and_value_list:
        if k[0] == '{':
            extra_data.update(json.loads(k))
        elif '=' in k:
            k = [x.strip() for x in k.split('=', maxsplit=1)]
            extra_data[k[0]] = k[1]
        else:
            external_key = k
    actions = extra_data.pop('actions', None)
    enroll(
        enrollment_type=enrollment_type,
        recipient=recipient,
        sender=User.query.filter_by(email=current_app.config['OAREPO_ENROLLMENT_CMDLINE_USER']).one(),
        external_key=external_key,
        extra_data=extra_data,
        email_template=email_template,
        mode=parse_enrollment_method(enrollment_method),
        actions=actions,
        expiration_interval=int(expiration) if expiration else None
    )


def parse_states(states):
    if states is None:
        return None
    states = [x.strip() for x in states.split(',')]
    states = [x for x in states if x]
    ret = []
    for s in states:
        ret.append(Enrollment.ENROLLMENT_STATUS_CHOICES_REVERSE[s])
    return ret


@enrollments.command('list')
@click.option('--enrollment-type')
@click.option('--external-key')
@click.option('--state',
              help='An array of "Pending", "Success", "Accepted", "Not accepted", '
                   '"User attached", "Failed", "Revoked" separated by comma')
@click.option('--actions',
              help='Comma-separated list of actions')
@click.option('--format', default='simple')
@with_appcontext
def list_enrollments(enrollment_type=None, external_key=None, state=None, format=None, actions=None):
    """
    List enrollments with optional filtering
    """
    enrollments = api_list_enrollments(external_key=external_key, enrollment_type=enrollment_type,
                                       states=parse_states(state), actions=actions)
    enrollments = [
        {
            'id': x.id,
            'type': x.enrollment_type,
            'key': x.external_key,
            'recipient': x.enrolled_email,
            'enrolled_user': x.enrolled_user.email if x.enrolled_user else '',
            'state': str(x.state),
            'actions': str(x.actions),
            **(x.extra_data or {}),
        }
        for x in enrollments
    ]
    if format != 'json':
        column_names = {
            'type',
            'key',
            'recipient',
            'enrolled_user',
            'state',
            'actions'
        }
        for x in enrollments:
            column_names.update(x.keys())
        columns = defaultdict(list)
        column_names = list(column_names)
        column_names.sort()
        for x in enrollments:
            for xn in column_names:
                columns[xn].append(x.get(xn))
        print()
        print(tabulate(columns, headers="keys", tablefmt=format))
    else:
        print(json.dumps(enrollments, ensure_ascii=False, indent=4))


@enrollments.command('revoke')
@click.argument('id', type=int)
@with_appcontext
def revoke_enrollment(id=None):
    """
    Revokes an enrollment
    """
    revoke(id, revoker=User.query.filter_by(email=current_app.config['OAREPO_ENROLLMENT_CMDLINE_USER']).one())
