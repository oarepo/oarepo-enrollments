import re

from flask import url_for
from mock import patch

from tests.helpers import extra_entrypoints


def fix_ws(resp):
    resp = resp.data.decode('utf-8').replace('\n', ' ').replace('\t', ' ')
    resp = re.sub('>[ \t\n]+', '> ', resp)
    resp = re.sub('[ \t\n]+<', ' <', resp)
    resp = re.sub('[ \t\n]+', ' ', resp)
    return resp


@patch('pkg_resources.iter_entry_points', extra_entrypoints)
def test_view_enrollment_logged_in(app, db, pending_enrollment, enrolled_user, test_role, test_blueprint):
    with app.test_client() as client:
        resp = client.get(url_for('_tests.test_login', user_id=enrolled_user.id, _external=True))
        assert resp.status_code == 200

        url = url_for('enrollment.enroll', key=pending_enrollment.key, _external=True)
        assert url == 'https://localhost' + app.config['OAREPO_ENROLLMENT_URL'].replace('<key>', pending_enrollment.key)

        resp = client.get(url)
        assert resp.status_code == 302
        location = resp.headers['Location']
        assert location == 'https://localhost/enroll/success/' + pending_enrollment.key

        resp = client.get(location)
        assert resp.status_code == 200
        assert 'You have been successfully enrolled to role &#34;test&#34;, now <a href="/">open the application</a>' in fix_ws(
            resp)

    db.session.refresh(enrolled_user)
    assert test_role in enrolled_user.roles


@patch('pkg_resources.iter_entry_points', extra_entrypoints)
def test_expired_enrollment(app, db, expired_enrollment, enrolled_user, test_role, test_blueprint):
    with app.test_client() as client:
        resp = client.get(url_for('_tests.test_login', user_id=enrolled_user.id, _external=True))
        assert resp.status_code == 200

        url = url_for('enrollment.enroll', key=expired_enrollment.key, _external=True)
        assert url == 'https://localhost' + app.config['OAREPO_ENROLLMENT_URL'].replace('<key>', expired_enrollment.key)

        resp = client.get(url)
        assert resp.status_code == 302
        location = resp.headers['Location']
        assert location == 'https://localhost/enroll/failure/' + expired_enrollment.key

        resp = client.get(location)
        assert resp.status_code == 200
        assert 'Enrollment failed!' in fix_ws(resp)
        assert 'This enrollment has already expired' in fix_ws(resp)

    db.session.refresh(enrolled_user)
    assert test_role not in enrolled_user.roles


@patch('pkg_resources.iter_entry_points', extra_entrypoints)
def test_view_linked_enrollment_logged_in(app, db, linked_enrollment, enrolled_user, test_role, test_blueprint):
    with app.test_client() as client:
        resp = client.get(url_for('_tests.test_login', user_id=enrolled_user.id, _external=True))
        assert resp.status_code == 200

        url = url_for('enrollment.enroll', key=linked_enrollment.key, _external=True)
        assert url == 'https://localhost' + app.config['OAREPO_ENROLLMENT_URL'].replace('<key>', linked_enrollment.key)

        resp = client.get(url)
        assert resp.status_code == 302
        location = resp.headers['Location']
        assert location == 'https://localhost/enroll/success/' + linked_enrollment.key

        resp = client.get(location)
        assert resp.status_code == 200
        assert 'You have been successfully enrolled to role &#34;test&#34;, now <a href="/">open the application</a>' in fix_ws(
            resp)

    db.session.refresh(enrolled_user)
    assert test_role in enrolled_user.roles


@patch('pkg_resources.iter_entry_points', extra_entrypoints)
def test_view_enrollment_no_login(app, db, pending_enrollment, test_role, test_blueprint):
    with app.test_client() as client:
        url = url_for('enrollment.enroll', key=pending_enrollment.key, _external=True)
        assert url == 'https://localhost' + app.config['OAREPO_ENROLLMENT_URL'].replace('<key>', pending_enrollment.key)

        resp = client.get(url)
        assert resp.status_code == 302
        location = resp.headers['Location']
        assert location == 'https://localhost/login/?next=https%3A%2F%2Flocalhost%2Fenroll%2F' + pending_enrollment.key


@patch('pkg_resources.iter_entry_points', extra_entrypoints)
def test_view_enrollment_pending_user_logged_in(app, db, pending_enrollment, pending_user, test_role, test_blueprint):
    with app.test_client() as client:
        # later on user is created
        pending_user = pending_user()
        resp = client.get(url_for('_tests.test_login', user_id=pending_user.id, _external=True))
        assert resp.status_code == 200

        url = url_for('enrollment.enroll', key=pending_enrollment.key, _external=True)
        assert url == 'https://localhost' + app.config['OAREPO_ENROLLMENT_URL'].replace('<key>', pending_enrollment.key)

        resp = client.get(url)
        assert resp.status_code == 302
        location = resp.headers['Location']
        assert location == 'https://localhost/enroll/success/' + pending_enrollment.key

        resp = client.get(location)
        assert resp.status_code == 200
        assert 'You have been successfully enrolled to role &#34;test&#34;, now <a href="/">open the application</a>' in fix_ws(
            resp)

    db.session.refresh(pending_user)
    assert test_role in pending_user.roles


@patch('pkg_resources.iter_entry_points', extra_entrypoints)
def test_accept_accepted(app, db, pending_accept_enrollment, enrolled_user, test_role, test_blueprint):
    with app.test_client() as client:
        resp = client.get(url_for('_tests.test_login', user_id=enrolled_user.id, _external=True))
        assert resp.status_code == 200

        url = url_for('enrollment.enroll', key=pending_accept_enrollment.key, _external=True)
        assert url == 'https://localhost' + app.config['OAREPO_ENROLLMENT_URL'].replace('<key>',
                                                                                        pending_accept_enrollment.key)

        resp = client.get(url)
        assert resp.status_code == 302
        location = resp.headers['Location']
        assert location == 'https://localhost/enroll/accept/' + pending_accept_enrollment.key

        resp = client.get(location)
        assert resp.status_code == 200
        assert 'Enrollment role &#34;test&#34;' in fix_ws(resp)
        assert 'User granting@example.com wants to enroll you in role &#34;test&#34;' in fix_ws(resp)
        assert 'Do you agree?' in fix_ws(resp)
        assert '<button type="submit" name="accept" value="accept">Yes</button> <button type="submit" name="reject" value="reject">No</button>' in fix_ws(
            resp)

        resp = client.post(location, data={"accept": "accept"})
        assert resp.status_code == 302
        location = resp.headers['Location']
        assert location == 'https://localhost/enroll/' + pending_accept_enrollment.key

        resp = client.get(location)
        assert resp.status_code == 302
        location = resp.headers['Location']
        assert location == 'https://localhost/enroll/success/' + pending_accept_enrollment.key

    db.session.refresh(enrolled_user)
    assert test_role in enrolled_user.roles


@patch('pkg_resources.iter_entry_points', extra_entrypoints)
def test_accept_rejected(app, db, pending_accept_enrollment, enrolled_user, test_role, test_blueprint):
    with app.test_client() as client:
        resp = client.get(url_for('_tests.test_login', user_id=enrolled_user.id, _external=True))
        assert resp.status_code == 200

        url = url_for('enrollment.enroll', key=pending_accept_enrollment.key, _external=True)
        assert url == 'https://localhost' + app.config['OAREPO_ENROLLMENT_URL'].replace('<key>',
                                                                                        pending_accept_enrollment.key)

        resp = client.get(url)
        assert resp.status_code == 302
        location = resp.headers['Location']
        assert location == 'https://localhost/enroll/accept/' + pending_accept_enrollment.key

        resp = client.get(location)
        assert resp.status_code == 200
        assert 'Enrollment role &#34;test&#34;' in fix_ws(resp)
        assert 'User granting@example.com wants to enroll you in role &#34;test&#34;' in fix_ws(resp)
        assert 'Do you agree?' in fix_ws(resp)
        assert '<button type="submit" name="accept" value="accept">Yes</button> <button type="submit" name="reject" value="reject">No</button>' in fix_ws(
            resp)

        resp = client.post(location, data={"reject": "reject"})
        assert resp.status_code == 302
        location = resp.headers['Location']
        assert location == 'https://localhost/enroll/reject/' + pending_accept_enrollment.key

        resp = client.get(location)
        assert resp.status_code == 200
        assert 'Enrollment role &#34;test&#34; rejected!' in fix_ws(resp)

        db.session.refresh(enrolled_user)
        assert test_role not in enrolled_user.roles

        # now enroll again, this time accepting

        resp = client.get(url)
        assert resp.status_code == 302
        location = resp.headers['Location']
        assert location == 'https://localhost/enroll/accept/' + pending_accept_enrollment.key

        resp = client.get(location)
        assert resp.status_code == 200
        assert 'Enrollment role &#34;test&#34;' in fix_ws(resp)
        assert 'User granting@example.com wants to enroll you in role &#34;test&#34;' in fix_ws(resp)
        assert 'Do you agree?' in fix_ws(resp)
        assert '<button type="submit" name="accept" value="accept">Yes</button> <button type="submit" name="reject" value="reject">No</button>' in fix_ws(
            resp)

        resp = client.post(location, data={"accept": "accept"})
        assert resp.status_code == 302
        location = resp.headers['Location']
        assert location == 'https://localhost/enroll/' + pending_accept_enrollment.key

        resp = client.get(location)
        assert resp.status_code == 302
        location = resp.headers['Location']
        assert location == 'https://localhost/enroll/success/' + pending_accept_enrollment.key

    db.session.refresh(enrolled_user)
    assert test_role in enrolled_user.roles


@patch('pkg_resources.iter_entry_points', extra_entrypoints)
def test_already_taken_enrollment(app, db, linked_enrollment, impostor_user, test_role, test_blueprint):
    with app.test_client() as client:
        resp = client.get(url_for('_tests.test_login', user_id=impostor_user.id, _external=True))
        assert resp.status_code == 200

        url = url_for('enrollment.enroll', key=linked_enrollment.key, _external=True)
        assert url == 'https://localhost' + app.config['OAREPO_ENROLLMENT_URL'].replace('<key>', linked_enrollment.key)

        resp = client.get(url)
        assert resp.status_code == 302
        location = resp.headers['Location']
        assert location == 'https://localhost/enroll/failure/' + linked_enrollment.key

        resp = client.get(location)
        assert resp.status_code == 200
        assert 'Enrollment failed!' in fix_ws(resp)
        assert 'User impostor@example.com wants to enroll in an already assigned enrollment role "test"' in fix_ws(resp)

    db.session.refresh(impostor_user)
    assert test_role not in impostor_user.roles
