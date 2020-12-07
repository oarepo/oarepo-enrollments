from oarepo_enrollments.api import list_enrollments
from oarepo_enrollments.models import Enrollment
from mock import patch

from tests.helpers import extra_entrypoints


@patch('pkg_resources.iter_entry_points', extra_entrypoints)
def test_create_enrollment(db, granting_user):
    enrollment = Enrollment.create(
        'role', None, 'someone@example.com', granting_user)
    db.session.commit()
    assert enrollment.granting_email == granting_user.email
    assert enrollment.state == Enrollment.PENDING


@patch('pkg_resources.iter_entry_points', extra_entrypoints)
def test_create_linked_enrollment(db, granting_user, enrolled_user):
    enrollment = Enrollment.create(
        'role', None, enrolled_user.email, granting_user)
    db.session.commit()
    assert enrollment.granting_email == granting_user.email
    assert enrollment.state == Enrollment.LINKED


@patch('pkg_resources.iter_entry_points', extra_entrypoints)
def test_enroll_pending_user(db, pending_enrollment, pending_user, test_role):
    pending_user = pending_user()
    pending_enrollment.enroll(pending_user)
    db.session.commit()
    pending_enrollment = Enrollment.query.get(pending_enrollment.id)
    assert pending_enrollment.state == Enrollment.SUCCESS
    db.session.refresh(pending_user)
    assert test_role in pending_user.roles


@patch('pkg_resources.iter_entry_points', extra_entrypoints)
def test_enroll_linked_user(db, linked_enrollment, enrolled_user, test_role):
    linked_enrollment.enroll(enrolled_user)
    db.session.commit()
    pending_enrollment = Enrollment.query.get(linked_enrollment.id)
    assert pending_enrollment.state == Enrollment.SUCCESS
    db.session.refresh(enrolled_user)
    assert test_role in enrolled_user.roles


@patch('pkg_resources.iter_entry_points', extra_entrypoints)
def test_list(linked_enrollment):
    assert list_enrollments().count() == 1
    assert list_enrollments(external_key='blah').count() == 1
    assert list_enrollments(external_key='abc').count() == 0

    assert list_enrollments(enrollment_type='role').count() == 1
    assert list_enrollments(enrollment_type='bad-role').count() == 0
    assert list_enrollments(external_key='blah', enrollment_type='role').count() == 1

    assert list_enrollments(states=[
        Enrollment.PENDING
    ]).count() == 0

    assert list_enrollments(states=[
        Enrollment.PENDING, Enrollment.LINKED
    ]).count() == 1

    assert list_enrollments(states=[
        Enrollment.LINKED
    ]).count() == 1

    assert list_enrollments(external_key='blah', states=[
        Enrollment.PENDING
    ]).count() == 0

    assert list_enrollments(external_key='blah', states=[
        Enrollment.PENDING, Enrollment.LINKED
    ]).count() == 1

    assert list_enrollments(external_key='blah', states=[
        Enrollment.LINKED
    ]).count() == 1

    assert list_enrollments(enrollment_type='role', states=[
        Enrollment.PENDING
    ]).count() == 0

    assert list_enrollments(enrollment_type='role', states=[
        Enrollment.PENDING, Enrollment.LINKED
    ]).count() == 1

    assert list_enrollments(enrollment_type='role', states=[
        Enrollment.LINKED
    ]).count() == 1

    assert list_enrollments(external_key='blah', enrollment_type='role', states=[
        Enrollment.PENDING
    ]).count() == 0

    assert list_enrollments(external_key='blah', enrollment_type='role', states=[
        Enrollment.PENDING, Enrollment.LINKED
    ]).count() == 1

    assert list_enrollments(external_key='blah', enrollment_type='role', states=[
        Enrollment.LINKED
    ]).count() == 1


@patch('pkg_resources.iter_entry_points', extra_entrypoints)
def test_actions(db, granting_user):
    enrollment = Enrollment.create('test', None, 'blah@google.com', granting_user,
                                   actions=['read', 'update', 'delete'])
    db.session.commit()
    assert list(Enrollment.query.filter(Enrollment.actions.any('read'))) == [enrollment]
    assert list(Enrollment.query.filter(Enrollment.actions.any('update'))) == [enrollment]
    assert list(Enrollment.query.filter(Enrollment.actions.any('delete'))) == [enrollment]
    assert list(Enrollment.query.filter(Enrollment.actions.any('blah'))) == []
