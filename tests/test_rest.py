import json
from pprint import pprint

from flask import url_for
from mock import patch

from tests.helpers import extra_entrypoints, dedate


@patch('pkg_resources.iter_entry_points', extra_entrypoints)
def test_rest_list_enrollments(app, api, db, pending_enrollment, granting_user, test_role, test_blueprint):
    with api.app_context():
        with api.test_client() as client:
            resp = client.get('/api/enroll/')
            assert resp.status_code == 200
            # print(json.dumps(resp.json, indent=4))
            pagination = resp.json['pagination']
            data = resp.json['data']
            assert pagination['totalElements'] == 1
            assert data[0]['state'] == 'Pending'
            assert data[0]['id'] == 1

            resp = client.get('/api/enroll/', data={
                'external_key': 'record:1'
            })
            assert resp.json['pagination']['totalElements'] == 1

            resp = client.get('/api/enroll/', data={
                'enrollment_type': 'role'
            })
            assert resp.json['pagination']['totalElements'] == 1

            resp = client.get('/api/enroll/', data={
                'state': 'Pending'
            })
            assert resp.json['pagination']['totalElements'] == 1

            resp = client.get('/api/enroll/', data={
                'state': 'Pending,Success'
            })
            assert resp.json['pagination']['totalElements'] == 1


@patch('pkg_resources.iter_entry_points', extra_entrypoints)
def test_rest_get(app, api, db, pending_enrollment, granting_user, test_role, test_blueprint):
    with api.app_context():
        with api.test_client() as client:
            resp = client.get('/api/enroll/1')
            assert dedate(resp.json) == dedate(
                {
                    'accepted_timestamp': None,
                    'enrolled_email': 'someone@example.com',
                    'enrolled_user': None,
                    'enrollment_type': 'role',
                    'expiration_timestamp': '2020-12-18T08:48:12.873987',
                    'external_key': 'record:1',
                    'extra_data': {'role': 'test'},
                    'failure_reason': None,
                    'finalization_timestamp': None,
                    'granting_user': {'email': 'granting@example.com'},
                    'id': 1,
                    'rejected_timestamp': None,
                    'revocation_timestamp': None,
                    'revoker': None,
                    'start_timestamp': '2020-12-04T08:48:12.873987',
                    'state': 'Pending',
                    'user_attached_timestamp': None,
                    'actions': None
                }
            )
            assert resp.status_code == 200


@patch('pkg_resources.iter_entry_points', extra_entrypoints)
def test_rest_revoke(app, api, db, pending_enrollment, granting_user, test_role, test_api_blueprint):
    with api.app_context():
        with api.test_client() as client:
            resp = client.get(f'/_tests/_login/{granting_user.id}')
            assert resp.status_code == 200

            resp = client.delete('/api/enroll/1')
            assert dedate(resp.json) == dedate(
                {
                    'accepted_timestamp': None,
                    'enrolled_email': 'someone@example.com',
                    'enrolled_user': None,
                    'enrollment_type': 'role',
                    'expiration_timestamp': '2020-12-18T08:48:12.873987',
                    'external_key': 'record:1',
                    'extra_data': {'role': 'test'},
                    'failure_reason': None,
                    'finalization_timestamp': None,
                    'granting_user': {'email': 'granting@example.com'},
                    'id': 1,
                    'rejected_timestamp': None,
                    'revocation_timestamp': '2020-12-04T08:48:12.873987',
                    'revoker': {'email': 'granting@example.com'},
                    'start_timestamp': '2020-12-04T08:48:12.873987',
                    'state': 'Revoked',
                    'user_attached_timestamp': None,
                    'actions': None
                }
            )
            assert resp.status_code == 200


@patch('pkg_resources.iter_entry_points', extra_entrypoints)
def test_rest_enroll(app, api, db, pending_enrollment, granting_user, test_role, test_api_blueprint):
    with api.app_context():
        with api.test_client() as client:
            resp = client.get(f'/_tests/_login/{granting_user.id}')
            assert resp.status_code == 200

            resp = client.post('/api/enroll/',
                               data=json.dumps({
                                   'enrollment_type': "role",
                                   'recipient': "someone@example.com",
                                   'email_template': "test-template",
                                   'mode': "automatic",
                                   'role': 'test',
                                   'expiration_interval': 366
                               }),
                               headers={'Content-Type': 'application/json'})
            json_data = json.loads(resp.data)
            assert dedate(json_data) == dedate(
                {
                    'accepted_timestamp': None,
                    'enrolled_email': 'someone@example.com',
                    'enrolled_user': None,
                    'enrollment_type': 'role',
                    'expiration_timestamp': '--timestamp--',
                    'external_key': None,
                    'extra_data': {'role': 'test'},
                    'failure_reason': None,
                    'finalization_timestamp': None,
                    'granting_user': {'email': 'granting@example.com'},
                    'id': 2,
                    'rejected_timestamp': None,
                    'revocation_timestamp': None,
                    'revoker': None,
                    'start_timestamp': '--timestamp--',
                    'state': 'Pending',
                    'user_attached_timestamp': None,
                    'actions': None
                }
            )
            assert resp.status_code == 201
