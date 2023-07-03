# SPDX-License-Identifier: GPL-2.0+

from datetime import datetime, timedelta

import pytest
from requests import ConnectionError, HTTPError
from mock import patch, ANY, Mock
from stomp.exception import StompException

from .utils import create_waiver
from waiverdb import __version__
from waiverdb.models import Waiver


@pytest.fixture
def mocked_get_user(username):
    with patch('waiverdb.auth.get_user', return_value=(username, {})):
        yield username


@pytest.fixture
def mocked_user():
    with patch('waiverdb.auth.get_user', return_value=('foo', {})):
        yield 'foo'


@pytest.fixture
def mocked_bodhi_user():
    with patch('waiverdb.auth.get_user', return_value=('bodhi', {})):
        yield 'bodhi'


@pytest.fixture
def mocked_resultsdb():
    with patch('waiverdb.api_v1.get_resultsdb_result') as mocked_resultsdb:
        yield mocked_resultsdb


def test_create_waiver(mocked_user, client, session):
    data = {
        'subject_type': 'koji_build',
        'subject_identifier': 'glibc-2.26-27.fc27',
        'testcase': 'testcase1',
        'product_version': 'fool-1',
        'waived': True,
        'comment': 'it broke',
    }
    r = client.post('/api/v1.0/waivers/', json=data)
    assert r.status_code == 201, r.text
    assert r.json['username'] == 'foo'
    assert r.json['subject'] == {'type': 'koji_build', 'item': 'glibc-2.26-27.fc27'}
    assert r.json['subject_type'] == 'koji_build'
    assert r.json['subject_identifier'] == 'glibc-2.26-27.fc27'
    assert r.json['testcase'] == 'testcase1'
    assert r.json['product_version'] == 'fool-1'
    assert r.json['waived'] is True
    assert r.json['comment'] == 'it broke'
    assert r.json['scenario'] is None


def test_create_waiver_with_subject(mocked_user, client, session):
    # 'subject' key was the API in Waiverdb < 0.11
    data = {
        'subject': {'type': 'koji_build', 'item': 'glibc-2.26-27.fc27'},
        'testcase': 'dist.rpmdeplint',
        'product_version': 'fedora-27',
        'waived': True,
        'comment': 'it really broke',
    }
    r = client.post('/api/v1.0/waivers/', json=data)
    assert r.status_code == 201, r.text
    assert r.json['username'] == 'foo'
    assert r.json['subject'] == {'type': 'koji_build', 'item': 'glibc-2.26-27.fc27'}
    assert r.json['subject_type'] == 'koji_build'
    assert r.json['subject_identifier'] == 'glibc-2.26-27.fc27'
    assert r.json['testcase'] == 'dist.rpmdeplint'
    assert r.json['product_version'] == 'fedora-27'
    assert r.json['waived'] is True
    assert r.json['comment'] == 'it really broke'


def test_create_waiver_with_result_id(mocked_user, mocked_resultsdb, client, session):
    mocked_resultsdb.return_value = {
        'data': {
            'type': ['koji_build'],
            'item': ['somebuild'],
            'scenario': ['somescenario'],
        },
        'testcase': {'name': 'sometest'}
    }

    # 'result_id' key was the API in Waiverdb < 0.6
    data = {
        'result_id': 123,
        'product_version': 'fool-1',
        'waived': True,
        'comment': 'it broke',
    }
    r = client.post('/api/v1.0/waivers/', json=data)
    assert r.status_code == 201, r.text
    assert r.json['username'] == 'foo'
    assert r.json['scenario'] == 'somescenario'
    assert r.json['subject'] == {'type': 'koji_build', 'item': 'somebuild'}
    assert r.json['subject_type'] == 'koji_build'
    assert r.json['subject_identifier'] == 'somebuild'
    assert r.json['testcase'] == 'sometest'
    assert r.json['product_version'] == 'fool-1'
    assert r.json['waived'] is True
    assert r.json['comment'] == 'it broke'


def test_create_waiver_with_result_for_original_spec_nvr(
        mocked_user, mocked_resultsdb, client, session):
    mocked_resultsdb.return_value = {
        'data': {
            'original_spec_nvr': ['somedata'],
        },
        'testcase': {'name': 'sometest'}
    }

    data = {
        'result_id': 123,
        'product_version': 'fool-1',
        'waived': True,
        'comment': 'it broke',
    }
    r = client.post('/api/v1.0/waivers/', json=data)
    assert r.status_code == 201, r.text
    assert r.json['username'] == 'foo'
    assert r.json['subject'] == {'type': 'koji_build', 'item': 'somedata'}
    assert r.json['subject_type'] == 'koji_build'
    assert r.json['subject_identifier'] == 'somedata'
    assert r.json['testcase'] == 'sometest'
    assert r.json['product_version'] == 'fool-1'
    assert r.json['waived'] is True
    assert r.json['comment'] == 'it broke'


def test_create_waiver_without_comment(mocked_user, client, session):
    data = {
        'subject_type': 'koji_build',
        'subject_identifier': 'glibc-2.26-27.fc27',
        'product_version': 'fool-1',
        'testcase': 'sometest',
        'waived': True,
    }
    r = client.post('/api/v1.0/waivers/', json=data)
    assert r.status_code == 400, r.text
    bp = r.json['validation_error']
    assert {
        'input': data,
        'loc': [ANY, 'comment'],
        'msg': 'Field required',
        'type': 'missing',
        'url': ANY,
    } in bp


def test_create_waiver_with_scenario(mocked_user, client, session):
    data = {
        'subject_type': 'koji_build',
        'subject_identifier': 'glibc-2.26-27.fc27',
        'testcase': 'testcase1',
        'product_version': 'fool-1',
        'scenario': 'scenario1',
        'waived': True,
        'comment': 'it broke',
    }
    r = client.post('/api/v1.0/waivers/', json=data)
    assert r.status_code == 201, r.text
    assert r.json['username'] == 'foo'
    assert r.json['subject'] == {'type': 'koji_build', 'item': 'glibc-2.26-27.fc27'}
    assert r.json['subject_type'] == 'koji_build'
    assert r.json['subject_identifier'] == 'glibc-2.26-27.fc27'
    assert r.json['testcase'] == 'testcase1'
    assert r.json['product_version'] == 'fool-1'
    assert r.json['waived'] is True
    assert r.json['comment'] == 'it broke'
    assert r.json['scenario'] == 'scenario1'


def test_create_waiver_with_unknown_result_id(mocked_user, mocked_resultsdb, client, session):
    mocked_resultsdb.side_effect = HTTPError(response=Mock(status=404))
    data = {
        'result_id': 123,
        'product_version': 'fool-1',
        'waived': True,
        'comment': 'it broke',
    }
    mocked_resultsdb.return_value.status_code = 404
    r = client.post('/api/v1.0/waivers/', json=data)
    assert r.json['message'].startswith('Failed looking up result in Resultsdb:')


def test_create_waiver_with_no_testcase(mocked_user, client):
    data = {
        'subject_type': 'koji_build',
        'subject_identifier': 'glibc-2.26-27.fc27',
        'waived': True,
        'product_version': 'the-best',
        'comment': 'it broke',
    }
    r = client.post('/api/v1.0/waivers/', json=data)
    assert r.status_code == 400, r.text
    bp = r.json['validation_error']
    assert {
        'input': data,
        'loc': ANY,
        'msg': 'Input should be a valid list',
        'type': 'list_type',
        'url': ANY,
    } in bp
    assert {
        'input': data,
        'loc': ANY,
        'msg': 'Value error, Argument testcase is missing',
        'type': 'value_error',
        'url': ANY,
    } in bp


def test_create_waiver_with_malformed_subject(mocked_user, client):
    data = {
        'subject': 'asd',
        'testcase': 'qqq',
    }
    r = client.post('/api/v1.0/waivers/', json=data)
    assert r.status_code == 400, r.text
    bp = r.json['validation_error']
    assert {
        'input': 'asd',
        'loc': [ANY, 'subject'],
        'msg': 'Input should be a valid dictionary or instance of TestSubject',
        'type': 'model_type',
        'url': ANY,
    } in bp


def test_non_superuser_cannot_create_waiver_for_other_users(mocked_user, client):
    data = {
        'subject_type': 'koji_build',
        'subject_identifier': 'glibc-2.26-27.fc27',
        'testcase': 'testcase1',
        'product_version': 'fool-1',
        'waived': True,
        'comment': 'it broke',
        'username': 'bar',
    }
    r = client.post('/api/v1.0/waivers/', json=data)
    assert r.status_code == 403, r.text
    assert 'user foo does not have the proxyuser ability' == r.json['message']


def test_superuser_can_create_waiver_for_other_users(mocked_bodhi_user, client, session):
    data = {
        'subject_type': 'koji_build',
        'subject_identifier': 'glibc-2.26-27.fc27',
        'testcase': 'testcase1',
        'product_version': 'fool-1',
        'waived': True,
        'comment': 'it broke',
        'username': 'bar',
    }
    r = client.post('/api/v1.0/waivers/', json=data)
    assert r.status_code == 201, r.text
    # a waiver should be created for bar by bodhi
    assert r.json['username'] == 'bar'
    assert r.json['proxied_by'] == mocked_bodhi_user


def test_get_waiver(client, session):
    # create a new waiver
    waiver = create_waiver(session, subject_type='koji_build',
                           subject_identifier='glibc-2.26-27.fc27',
                           testcase='testcase1', username='foo',
                           product_version='foo-1', comment='bla bla bla')
    r = client.get('/api/v1.0/waivers/%s' % waiver.id)
    assert r.status_code == 200, r.text
    assert r.json['username'] == waiver.username
    assert r.json['subject'] == {'type': 'koji_build', 'item': 'glibc-2.26-27.fc27'}
    assert r.json['subject_type'] == waiver.subject_type
    assert r.json['subject_identifier'] == waiver.subject_identifier
    assert r.json['testcase'] == waiver.testcase
    assert r.json['product_version'] == waiver.product_version
    assert r.json['waived'] is True
    assert r.json['comment'] == waiver.comment
    assert r.json['scenario'] is None


def test_get_waiver_by_scenario(client, session):
    scenario_name = 'scenario19'
    # create a new waiver
    waiver1 = create_waiver(
        session, subject_type='koji_build', subject_identifier='glibc-2.26-27.fc27',
        testcase='testcase1', username='foo', product_version='foo-1', comment='bla bla bla',
        scenario=scenario_name
    )
    create_waiver(
        session, subject_type='bodhi_update', subject_identifier='glibc-2.26-27.fc27',
        testcase='testcase1', username='foo', product_version='foo-1', comment='bla bla bla',
        scenario='yyyyyy'
    )
    r = client.get(f'/api/v1.0/waivers/?scenario={scenario_name}')
    assert r.status_code == 200, r.text
    assert len(r.json['data']) == 1
    assert r.json['data'][0]['username'] == waiver1.username
    assert r.json['data'][0]['subject'] == {'type': 'koji_build', 'item': 'glibc-2.26-27.fc27'}
    assert r.json['data'][0]['subject_type'] == waiver1.subject_type
    assert r.json['data'][0]['subject_identifier'] == waiver1.subject_identifier
    assert r.json['data'][0]['testcase'] == waiver1.testcase
    assert r.json['data'][0]['product_version'] == waiver1.product_version
    assert r.json['data'][0]['waived'] is True
    assert r.json['data'][0]['comment'] == waiver1.comment
    assert r.json['data'][0]['scenario'] == scenario_name
    assert r.json['prev'] is None
    assert r.json['next'] is None
    assert r.json['first'] == r.json['last']
    assert r.json['last'] == f'http://localhost/api/v1.0/waivers/?page=1&scenario={scenario_name}'


def test_404_for_nonexistent_waiver(client, session):
    r = client.get('/api/v1.0/waivers/foo')
    assert r.status_code == 404, r.text
    assert 'The requested URL was not found on the server' in r.json['message']


@patch('waiverdb.api_v1.AboutResource.get', side_effect=ConnectionError)
def test_500(mocked, client, session):
    r = client.get('/api/v1.0/about')
    assert r.status_code == 500, r.text
    assert r.json['message'] == ''


def test_get_waivers(client, session):
    for i in range(0, 10):
        create_waiver(session, subject_type='koji_build', subject_identifier="%d" % i,
                      testcase="case %d" % i, username='foo %d' % i,
                      product_version='foo-%d' % i, comment='bla bla bla')
    r = client.get('/api/v1.0/waivers/')
    assert r.status_code == 200, r.text
    assert len(r.json['data']) == 10


def test_pagination_waivers(client, session):
    for i in range(0, 30):
        create_waiver(session, subject_type='koji_build', subject_identifier="%d" % i,
                      testcase="case %d" % i, username='foo %d' % i,
                      product_version='foo-%d' % i, comment='bla bla bla')
    r = client.get('/api/v1.0/waivers/?page=2')
    assert r.status_code == 200, r.text
    assert len(r.json['data']) == 10
    assert '/waivers/?page=1' in r.json['prev']
    assert '/waivers/?page=3' in r.json['next']
    assert '/waivers/?page=1' in r.json['first']
    assert '/waivers/?page=3' in r.json['last']


def test_obsolete_waivers_are_excluded_by_default(client, session):
    create_waiver(session, subject_type='koji_build',
                  subject_identifier='glibc-2.26-27.fc27',
                  testcase='testcase1', username='foo',
                  product_version='foo-1')
    new_waiver = create_waiver(session, subject_type='koji_build',
                               subject_identifier='glibc-2.26-27.fc27',
                               testcase='testcase1', username='foo',
                               product_version='foo-1', waived=False)
    r = client.get('/api/v1.0/waivers/')
    assert r.status_code == 200, r.text
    assert len(r.json['data']) == 1
    assert r.json['data'][0]['id'] == new_waiver.id
    assert r.json['data'][0]['waived'] == new_waiver.waived


def test_obsolete_waivers_are_excluded_when_requested(client, session):
    create_waiver(session, subject_type='koji_build',
                  subject_identifier='glibc-2.26-27.fc27',
                  testcase='testcase1', username='foo',
                  product_version='foo-1')
    new_waiver = create_waiver(session, subject_type='koji_build',
                               subject_identifier='glibc-2.26-27.fc27',
                               testcase='testcase1', username='foo',
                               product_version='foo-1', waived=False)
    r = client.get('/api/v1.0/waivers/?include_obsolete=0')
    assert r.status_code == 200, r.text
    assert len(r.json['data']) == 1
    assert r.json['data'][0]['id'] == new_waiver.id
    assert r.json['data'][0]['waived'] == new_waiver.waived


def test_get_obsolete_waivers(client, session):
    old_waiver = create_waiver(session, subject_type='koji_build',
                               subject_identifier='glibc-2.26-27.fc27',
                               testcase='testcase1', username='foo',
                               product_version='foo-1')
    new_waiver = create_waiver(session, subject_type='koji_build',
                               subject_identifier='glibc-2.26-27.fc27',
                               testcase='testcase1', username='foo',
                               product_version='foo-1', waived=False)
    r = client.get('/api/v1.0/waivers/?include_obsolete=1')
    assert r.status_code == 200, r.text
    assert len(r.json['data']) == 2
    assert r.json['data'][0]['id'] == new_waiver.id
    assert r.json['data'][1]['id'] == old_waiver.id


def test_obsolete_waivers_with_different_product_version(client, session):
    old_waiver = create_waiver(session, subject_type='koji_build',
                               subject_identifier='glibc-2.26-27.fc27',
                               testcase='testcase1', username='foo',
                               product_version='foo-1')
    new_waiver = create_waiver(session, subject_type='koji_build',
                               subject_identifier='glibc-2.26-27.fc27',
                               testcase='testcase1', username='foo',
                               product_version='foo-2')
    r = client.get('/api/v1.0/waivers/?include_obsolete=0')
    assert r.status_code == 200, r.text
    assert len(r.json['data']) == 2
    assert r.json['data'][0]['id'] == new_waiver.id
    assert r.json['data'][1]['id'] == old_waiver.id


def test_obsolete_waivers_with_different_username(client, session):
    old_waiver = create_waiver(session, subject_type='koji_build',
                               subject_identifier='glibc-2.26-27.fc27',
                               testcase='testcase1', username='foo',
                               product_version='foo-1')
    new_waiver = create_waiver(session, subject_type='koji_build',
                               subject_identifier='glibc-2.26-27.fc27',
                               testcase='testcase1', username='bar',
                               product_version='foo-1')
    r = client.get('/api/v1.0/waivers/?include_obsolete=0')
    assert r.status_code == 200, r.text
    assert len(r.json['data']) == 2
    assert r.json['data'][0]['id'] == new_waiver.id
    assert r.json['data'][1]['id'] == old_waiver.id


def test_obsolete_waivers_with_different_scenario(client, session):
    old_waiver = create_waiver(session, subject_type='koji_build',
                               subject_identifier='glibc-2.26-27.fc27',
                               testcase='testcase1', username='foo',
                               product_version='foo-1', scenario='scenario1')
    new_waiver = create_waiver(session, subject_type='koji_build',
                               subject_identifier='glibc-2.26-27.fc27',
                               testcase='testcase1', username='foo',
                               product_version='foo-1', scenario='scenario2')
    r = client.get('/api/v1.0/waivers/?include_obsolete=0')
    assert r.status_code == 200, r.text
    assert len(r.json['data']) == 2
    assert r.json['data'][0]['id'] == new_waiver.id
    assert r.json['data'][1]['id'] == old_waiver.id


def test_filtering_waivers_by_subject_type(client, session):
    create_waiver(session, subject_type='koji_build', subject_identifier='glibc-2.26-27.fc27',
                  testcase='testcase', username='foo-1', product_version='foo-1')
    create_waiver(session, subject_type='bodhi_update', subject_identifier='FEDORA-2017-7e594f96bb',
                  testcase='testcase', username='foo-2', product_version='foo-1')

    r = client.get('/api/v1.0/waivers/?subject_type=bodhi_update')
    assert r.status_code == 200, r.text
    assert len(r.json['data']) == 1
    assert r.json['data'][0]['subject_type'] == 'bodhi_update'


def test_filtering_waivers_by_subject_identifier(client, session):
    create_waiver(session, subject_type='koji_build', subject_identifier='glibc-2.26-27.fc27',
                  testcase='testcase', username='foo-1', product_version='foo-1')
    create_waiver(session, subject_type='koji_build', subject_identifier='kernel-4.15.17-300.fc27',
                  testcase='testcase', username='foo-2', product_version='foo-1')

    r = client.get('/api/v1.0/waivers/?subject_identifier=glibc-2.26-27.fc27')
    assert r.status_code == 200, r.text
    assert len(r.json['data']) == 1
    assert r.json['data'][0]['subject_identifier'] == 'glibc-2.26-27.fc27'


def test_filtering_waivers_by_testcase(client, session):
    create_waiver(session, subject_type='koji_build', subject_identifier='glibc-2.26-27.fc27',
                  testcase='testcase1', username='foo-1', product_version='foo-1')
    create_waiver(session, subject_type='koji_build', subject_identifier='glibc-2.26-27.fc27',
                  testcase='testcase2', username='foo-2', product_version='foo-1')

    r = client.get('/api/v1.0/waivers/?testcase=testcase1')
    assert r.status_code == 200, r.text
    assert len(r.json['data']) == 1
    assert r.json['data'][0]['testcase'] == 'testcase1'


def test_filtering_waivers_by_product_version(client, session):
    create_waiver(session, subject_type='koji_build', subject_identifier='glibc-2.26-27.fc27',
                  testcase='testcase1', username='foo-1', product_version='release-1')
    create_waiver(session, subject_type='koji_build', subject_identifier='kernel-4.15.17-300.fc27',
                  testcase='testcase2', username='foo-1', product_version='release-2')
    r = client.get('/api/v1.0/waivers/?product_version=release-1')
    assert r.status_code == 200, r.text
    assert len(r.json['data']) == 1
    assert r.json['data'][0]['product_version'] == 'release-1'


def test_filtering_waivers_by_username(client, session):
    create_waiver(session, subject_type='koji_build', subject_identifier='glibc-2.26-27.fc27',
                  testcase='testcase1', username='foo', product_version='foo-1')
    create_waiver(session, subject_type='koji_build', subject_identifier='kernel-4.15.17-300.fc27',
                  testcase='testcase2', username='bar', product_version='foo-2')
    r = client.get('/api/v1.0/waivers/?username=foo')
    assert r.status_code == 200, r.text
    assert len(r.json['data']) == 1
    assert r.json['data'][0]['username'] == 'foo'


def test_filtering_waivers_by_since(client, session):
    before1 = (datetime.utcnow() - timedelta(seconds=100)).isoformat()
    before2 = (datetime.utcnow() - timedelta(seconds=99)).isoformat()
    after = (datetime.utcnow() + timedelta(seconds=100)).isoformat()
    create_waiver(session, subject_type='koji_build', subject_identifier='glibc-2.26-27.fc27',
                  testcase='testcase1', username='foo', product_version='foo-1')
    r = client.get(f'/api/v1.0/waivers/?since={before1}')
    assert r.status_code == 200, r.text
    assert len(r.json['data']) == 1
    assert r.json['data'][0]['subject_identifier'] == 'glibc-2.26-27.fc27'
    assert r.json['data'][0]['testcase'] == 'testcase1'

    r = client.get('/api/v1.0/waivers/?since=%s,%s' % (before1, after))
    assert r.status_code == 200, r.text
    assert len(r.json['data']) == 1
    assert r.json['data'][0]['subject_identifier'] == 'glibc-2.26-27.fc27'
    assert r.json['data'][0]['testcase'] == 'testcase1'

    r = client.get('/api/v1.0/waivers/?since=%s' % (after))
    assert r.status_code == 200, r.text
    assert len(r.json['data']) == 0

    r = client.get('/api/v1.0/waivers/?since=%s,%s' % (before1, before2))
    assert r.status_code == 200, r.text
    assert len(r.json['data']) == 0


def test_filtering_waivers_by_malformed_since(client, session):
    r = client.get('/api/v1.0/waivers/?since=123')
    assert r.status_code == 400, r.text
    assert r.json['message']['since'] == \
        "Invalid isoformat string: '123'"

    r = client.get(f'/api/v1.0/waivers/?since={datetime.utcnow().isoformat()},badend')
    assert r.status_code == 400, r.text
    assert r.json['message']['since'] == \
        "Invalid isoformat string: 'badend'"

    r = client.get(f'/api/v1.0/waivers/?since={datetime.utcnow().isoformat()},too,many,commas')
    assert r.status_code == 400, r.text
    assert r.json['message']['since'] == \
        "Invalid isoformat string: 'too,many,commas'"


def test_filtering_waivers_by_proxied_by(client, session):
    create_waiver(session, subject_type='koji_build', subject_identifier='glibc-2.26-27.fc27',
                  testcase='testcase1', username='foo-1', product_version='foo-1',
                  proxied_by='bodhi')
    create_waiver(session, subject_type='koji_build', subject_identifier='kernel-4.15.17-300.fc27',
                  testcase='testcase2', username='foo-2', product_version='foo-1')
    r = client.get('/api/v1.0/waivers/?proxied_by=bodhi')
    assert r.status_code == 200, r.text
    assert len(r.json['data']) == 1
    assert r.json['data'][0]['subject'] == {'type': 'koji_build', 'item': 'glibc-2.26-27.fc27'}
    assert r.json['data'][0]['testcase'] == 'testcase1'


def test_jsonp(client, session):
    waiver = create_waiver(session, subject_type='koji_build',
                           subject_identifier='glibc-2.26-27.fc27',
                           testcase='testcase1', username='foo', product_version='foo-1')
    r = client.get('/api/v1.0/waivers/%s?callback=jsonpcallback' % waiver.id)
    assert r.mimetype == 'application/javascript'
    assert 'jsonpcallback' in r.get_data(as_text=True)


def test_healthcheck(client):
    r = client.get('healthcheck')
    assert r.status_code == 200, r.text
    assert r.get_data(as_text=True) == 'Health check OK'


def test_filtering_waivers_with_post(client, session):
    filters = []
    for i in range(1, 51):
        filters.append({'subject_type': 'koji_build',
                        'subject_identifier': 'python2-2.7.14-%d.fc27' % i,
                        'testcase': 'case %d' % i})
        create_waiver(session, subject_type='koji_build',
                      subject_identifier='python2-2.7.14-%d.fc27' % i,
                      testcase='case %d' % i, username='person',
                      product_version='fedora-27', comment='bla bla bla')
    # Unrelated waiver which should not be included
    create_waiver(session, subject_type='koji_build',
                  subject_identifier='glibc-2.26-27.fc27',
                  testcase='dist.rpmdeplint', username='person',
                  product_version='fedora-27', comment='bla bla bla')
    r = client.post('/api/v1.0/waivers/+filtered', json={'filters': filters})
    assert r.status_code == 200, r.text
    assert len(r.json['data']) == 50
    assert all(w['subject_identifier'].startswith('python2-2.7.14') for w in r.json['data'])


def test_filtering_with_missing_filter(client, session):
    data = {'somethingelse': 'what'}
    r = client.post('/api/v1.0/waivers/+filtered', json=data)
    assert r.status_code == 400, r.text
    bp = r.json['validation_error']
    assert {
        'input': data,
        'loc': ANY,
        'msg': 'Field required',
        'type': 'missing',
        'url': ANY,
    } in bp


def test_waivers_by_subjects_and_testcases(client, session):
    """
    This tests that users can get waivers by sending a POST request with a long
    list of result subject/testcase.
    """
    results = []
    for i in range(1, 51):
        results.append({'subject': {'type': 'koji_build', 'item': '%d' % i},
                        'testcase': 'case %d' % i})
        create_waiver(session, subject_type='koji_build', subject_identifier="%d" % i,
                      testcase="case %d" % i, username='foo %d' % i,
                      product_version='foo-%d' % i, comment='bla bla bla')
    data = {
        'results': results
    }
    r = client.post('/api/v1.0/waivers/+by-subjects-and-testcases', json=data)
    assert r.status_code == 200, r.text
    assert len(r.json['data']) == 50
    subject_identifiers = []
    testcases = []
    for i in reversed(range(1, 51)):
        subject_identifiers.append('%d' % i)
        testcases.append('case %d' % i)
    assert [w['subject_identifier'] for w in r.json['data']] == subject_identifiers
    assert set([w['testcase'] for w in r.json['data']]) == set(testcases)
    assert all(w['username'].startswith('foo') for w in r.json['data'])
    assert all(w['product_version'].startswith('foo-') for w in r.json['data'])


@pytest.mark.parametrize("results,expected_loc,excepted_error", [
    ([{'item': {'subject.test1': 'subject1'}}], 'testcase', 'Field required'),
    ([{'subject': 'subject1'}], 'subject',
     'Input should be a valid dictionary or instance of TestSubject'),
    ([{}], 'subject', 'Field required')
])
def test_waivers_by_subjects_and_testcases_with_bad_results_parameter(
        client, session, results, expected_loc, excepted_error
):
    data = {'results': results}
    r = client.post('/api/v1.0/waivers/+by-subjects-and-testcases', json=data)
    assert r.status_code == 400, r.text
    bp = r.json['validation_error']
    print(bp)
    assert {
        'loc': ['results', 0, expected_loc],
        'msg': excepted_error,
        'input': ANY,
        'type': ANY,
        'url': ANY,
    } in bp


def test_waivers_by_subjects_and_testcases_with_unrecognized_subject_type(client, session):
    create_waiver(session, subject_type='koji_build',
                  subject_identifier='python3-flask-0.12.2-1.fc29',
                  testcase='dist.rpmdeplint', username='person',
                  product_version='fedora-29', comment='bla bla bla')
    # This doesn't match any of the known subject types which we understand
    # for backwards compatibility. So if you tried to submit a waiver with a
    # subject like this, Waiverdb would reject it. But if the caller is just
    # *searching* and not *submitting* then instead of giving back an error
    # Waiverdb should just return an empty result set.
    data = {'results': [
        {'subject': {'item': 'python3-flask-0.12.2-1.fc29'}, 'testcase': 'dist.rpmdeplint'},
    ]}
    r = client.post('/api/v1.0/waivers/+by-subjects-and-testcases', json=data)
    assert r.status_code == 200, r.text
    assert r.json['data'] == []


def test_waivers_by_subjects_and_testcases_with_empty_results_parameter(client, session):
    create_waiver(session, subject_type='koji_build', subject_identifier='glibc-2.26-27.fc27',
                  testcase='testcase1', username='foo-1', product_version='foo-1')
    data = {'results': []}
    r = client.post('/api/v1.0/waivers/+by-subjects-and-testcases', json=data)
    assert r.status_code == 200, r.text
    assert len(r.json['data']) == 1


def test_waivers_by_subjects_and_testcases_with_malformed_since(client, session):
    data = {'since': 123}
    r = client.post('/api/v1.0/waivers/+by-subjects-and-testcases', json=data)
    assert r.status_code == 400, r.text
    bp = r.json['validation_error']
    assert {
        'input': 123,
        'loc': ['since'],
        'msg': "Input should be a valid string",
        'type': 'string_type',
        'url': ANY,
    } in bp

    data = {'since': 'asdf'}
    r = client.post('/api/v1.0/waivers/+by-subjects-and-testcases', json=data)
    assert r.status_code == 400, r.text
    assert r.json['message']['since'] == \
        "Invalid isoformat string: 'asdf'"


@pytest.mark.parametrize('trailing_slash', ('', '/'))
def test_about_endpoint(client, trailing_slash):
    r = client.get('/api/v1.0/about' + trailing_slash)
    assert r.status_code == 200, r.text
    assert r.json['version'] == __version__
    assert r.json['auth_method'] == client.application.config['AUTH_METHOD']


def test_config_endpoint_permissions_map(client):
    config = {
        'PERMISSION_MAPPING': {
            '^kernel-qe\\.': {
                'groups': ['devel', 'qa'],
                'users': [],
            },
            '': {
                'groups': ['factory2-admins'],
                'users': [],
            },
        }
    }

    with patch.dict(client.application.config, config):
        r = client.get('/api/v1.0/config')

    assert r.status_code == 200, r.text
    assert r.json['permission_mapping'] == config['PERMISSION_MAPPING']


def test_permissions_endpoint(client):
    config = {
        'PERMISSIONS': [
            {
                "name": "^kernel-qe",
                "maintainers": ["alice@example.com"],
                "_testcase_regex_pattern": "^kernel-qe",
                "groups": ["devel", "qa"],
                "users": ["alice@example.com"],
            },
            {
                "name": "Greenwave Tests",
                "maintainers": ["greenwave-dev@example.com"],
                "testcases": ["greenwave-tests.*"],
                "groups": [],
                "users": ["HTTP/greenwave-dev.tests.example.com"]
            }
        ]
    }

    with patch.dict(client.application.config, config):
        r = client.get('/api/v1.0/permissions')
        assert r.status_code == 200, r.text
        assert r.json == config['PERMISSIONS']

        r = client.get('/api/v1.0/permissions?testcase=xxx')
        assert r.status_code == 200, r.text
        assert r.json == []

        r = client.get('/api/v1.0/permissions?testcase=greenwave-tests.test1')
        assert r.status_code == 200, r.text
        assert r.json == config['PERMISSIONS'][1:]

        r = client.get('/api/v1.0/permissions?testcase=kernel-qe.test1')
        assert r.status_code == 200, r.text
        assert r.json == config['PERMISSIONS'][0:1]


def test_config_endpoint_superusers(client):
    config = {
        'SUPERUSERS': ['alice', 'bob']
    }

    with patch.dict(client.application.config, config):
        r = client.get('/api/v1.0/config')

    assert r.status_code == 200, r.text
    assert r.json['superusers'] == config['SUPERUSERS']


def test_cors_good(client, session):
    headers = {
        'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'Content-Type',
        'Origin': 'https://bodhi.fedoraproject.org',
    }
    r = client.options(
        '/api/v1.0/waivers/',
        content_type='Content-Type',
        headers=headers
    )

    assert r.status_code == 200, r.text
    assert r.headers.get('Access-Control-Allow-Origin') == 'https://bodhi.fedoraproject.org'
    assert 'POST' in r.headers.get('Access-Control-Allow-Methods', '').split(', ')


def test_cors_bad(client, session):
    headers = {
        'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'Content-Type',
        'Origin': 'localhost',
    }
    r = client.options(
        '/api/v1.0/waivers/',
        content_type='Content-Type',
        headers=headers
    )

    assert r.status_code == 200, r.text
    assert 'Access-Control-Allow-Origin' not in r.headers
    assert 'Access-Control-Allow-Methods' not in r.headers


def test_create_multiple_waivers(mocked_user, client, session):
    item1 = {
        'subject_type': 'koji_build',
        'subject_identifier': 'glibc-2.26-27.fc27',
        'testcase': 'testcase1',
        'product_version': 'fool-1',
        'waived': True,
        'comment': 'it broke',
    }
    item2 = {
        'subject_type': 'koji_build',
        'subject_identifier': 'kernel-4.15.17-300.fc27',
        'testcase': 'testcase2',
        'product_version': 'fool-2',
        'waived': False,
        'comment': 'fixed',
    }
    data = [item1, item2]

    r = client.post('/api/v1.0/waivers/', json=data)

    assert r.status_code == 201, r.text
    assert isinstance(r.json, list)
    assert len(r.json) == 2

    actual_item1 = {k: v for k, v in r.json[0].items() if k in item1}
    actual_item2 = {k: v for k, v in r.json[1].items() if k in item2}
    assert actual_item1 == item1
    assert actual_item2 == item2

    # Transaction was not rolled back.
    assert session.query(Waiver).count() == 2


def test_create_multiple_waivers_rollback_on_error(mocked_user, client, session):
    item1 = {
        'subject_type': 'koji_build',
        'subject_identifier': 'glibc-2.26-27.fc27',
        'testcase': 'testcase1',
        'product_version': 'fool-1',
        'waived': True,
        'comment': 'it broke',
    }
    item2 = {}
    data = [item1, item2]

    r = client.post('/api/v1.0/waivers/', json=data)

    assert r.status_code == 400, r.text

    # Transaction was rolled back.
    assert session.query(Waiver).count() == 0


def test_create_waiver_with_arbitrary_subject_type(mocked_user, client, session):
    data = {
        'subject_type': 'kind-of-magic',
        'subject_identifier': 'glibc-2.26-27.fc27',
        'testcase': 'testcase1',
        'product_version': 'fool-1',
        'waived': True,
        'comment': 'it broke',
    }
    r = client.post('/api/v1.0/waivers/', json=data)
    assert r.status_code == 201, r.text
    assert r.json['username'] == 'foo'
    assert r.json['subject'] == {'type': 'kind-of-magic', 'item': 'glibc-2.26-27.fc27'}
    assert r.json['subject_type'] == 'kind-of-magic'
    assert r.json['subject_identifier'] == 'glibc-2.26-27.fc27'
    assert r.json['testcase'] == 'testcase1'
    assert r.json['product_version'] == 'fool-1'
    assert r.json['waived'] is True
    assert r.json['comment'] == 'it broke'


def test_create_waiver_failed_event_once(mocked_user, client, session, caplog):
    config = dict(
        MESSAGE_BUS_PUBLISH=True,
        MESSAGE_PUBLISHER='stomp',
        MAX_STOMP_RETRY=3,
        STOMP_RETRY_DELAY_SECONDS=0,
        STOMP_CONFIGS={
            'destination': '/topic/VirtualTopic.eng.waiverdb.waiver.new',
            'connection': {
                'host_and_ports': [('broker01', 61612)],
            },
        },
    )

    data = {
        'subject_type': 'koji_build',
        'subject_identifier': 'glibc-2.26-27.fc27',
        'testcase': 'testcase1',
        'product_version': 'fool-1',
        'waived': True,
        'comment': 'it broke',
    }

    with patch.dict(client.application.config, config):
        with patch('waiverdb.events.stomp.connect.StompConnection11') as connection:
            connection().connect.side_effect = (StompException, StompException, None)
            r = client.post('/api/v1.0/waivers/', json=data)
            assert r.status_code == 201, r.text
            assert 'Failed to send message (try 1/3)' in caplog.text
            assert 'Failed to send message (try 2/3)' in caplog.text
            assert 'Failed to send message (try 3/3)' not in caplog.text
            assert 'StompException' in caplog.text
