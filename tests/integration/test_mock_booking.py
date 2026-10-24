"""Service-contract and fault simulation checks, NOT autonomous booking benchmarks."""
import copy
import pytest
from fastapi.testclient import TestClient

from mock.mock_irctc.app import create_app, rank_fares, validate_profile

PROFILE = {'name': 'Fictional Rider', 'age': 28, 'gender': 'Female', 'nationality': 'Indian', 'mobile': '9000000000'}
SEARCH = {'origin': 'RK', 'destination': 'HW', 'quota': 'TATKAL', 'date': '2026-10-26'}


def login(client):
    for _ in range(4):
        result = client.post('/api/login', json={'username': 'demo', 'password': 'demo', 'captcha': 'TRAIN'})
        if result.status_code == 200:
            return True
    return False


def prepare(client, key='run-one'):
    assert login(client)
    for _ in range(10):
        response = client.post('/api/search', json=SEARCH)
        if response.status_code == 200:
            break
    assert response.status_code == 200
    chosen = rank_fares(response.json()['trains'])[0]
    assert chosen['id'] == 'winner' and chosen['total_fare'] == 65 and chosen['departure'] == '07:15'
    payload = {'profile': PROFILE, 'train_id': chosen['id'], 'date': SEARCH['date'], 'idempotency_key': key}
    for _ in range(10):
        response = client.post('/api/passenger', json=payload)
        if response.status_code == 401:
            assert login(client)
        elif response.status_code == 200:
            break
    assert response.status_code == 200
    review = response.json()
    assert review['review']['profile'] == PROFILE
    assert client.post('/api/review/'+key, json={'expected': review['review'], 'digest': review['digest']}).status_code == 200
    return review, payload


@pytest.mark.parametrize('scenario', ['M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7'])
def test_twenty_seed_service_fault_matrix(scenario):
    successes = 0
    recovered_faults = 0
    for seed in range(20):
        app = create_app(seed=seed, scenario=scenario)
        with TestClient(app) as client:
            try:
                review, _ = prepare(client)
            except AssertionError:
                # Bounded captcha retries can fail; threshold is measured honestly.
                assert scenario == 'M5'
                continue
            response = client.post('/api/payment/run-one', json={'digest': review['digest']})
            assert response.json()['external_approval'] is True
            assert client.post('/api/test/approve/run-one').status_code == 200
            ticket = client.get('/api/ticket/run-one').json()
            assert ticket['status'] == 'booked'
            assert ticket['ticket']['profile'] == PROFILE
            assert ticket['ticket']['pnr'].startswith('MOCK')
            assert client.post('/api/test/approve/run-one').status_code == 200
            assert client.get('/api/state').json()['booking_count'] == 1
            recovered_faults += len(app.state.lab['faults'])
            if scenario == 'M2':
                assert app.state.lab['virtual_latency'] >= 7
            if scenario == 'M6':
                html = client.get('/').text
                assert f'const variant={seed}' in html and 'popup=true' in html
            successes += 1
    assert successes >= (20 if scenario == 'M1' else 18)
    if scenario in ('M3', 'M4', 'M5'):
        assert recovered_faults > 0


@pytest.mark.parametrize('seed', range(20))
@pytest.mark.parametrize('delay', [20, 90, None])
def test_M9_external_payment_timing(seed, delay):
    now = [1000.]
    with TestClient(create_app(seed=seed, scenario='M9', clock=lambda: now[0])) as client:
        review, _ = prepare(client)
        assert client.post('/api/payment/run-one', json={'digest': review['digest']}).status_code == 200
        assert client.get('/api/state').json()['booking_count'] == 0
        now[0] += delay if delay is not None else 121
        if delay is None:
            assert client.get('/api/ticket/run-one').json()['status'] == 'expired'
            assert client.post('/api/test/approve/run-one').status_code == 409
            assert client.get('/api/state').json()['booking_count'] == 0
        else:
            assert client.post('/api/test/approve/run-one').status_code == 200
            assert client.get('/api/state').json()['booking_count'] == 1


@pytest.mark.parametrize('seed', range(20))
def test_M10_retry_after_lost_response_idempotent(seed):
    # Simulates client restart after passenger response. OS process-kill is tested separately.
    with TestClient(create_app(seed=seed, scenario='M10')) as client:
        review, payload = prepare(client)
        assert client.post('/api/passenger', json=payload).json()['digest'] == review['digest']
        changed = copy.deepcopy(payload)
        changed['profile']['name'] = 'Different Rider'
        assert client.post('/api/passenger', json=changed).status_code == 409
        for _ in range(2):
            assert client.post('/api/payment/run-one', json={'digest': review['digest']}).status_code == 200
            assert client.post('/api/test/approve/run-one').status_code == 200
        assert client.get('/api/state').json()['booking_count'] == 1


@pytest.mark.parametrize('field', list(PROFILE))
def test_M11_profile_validation_before_network(field):
    profile = dict(PROFILE)
    del profile[field]
    with pytest.raises(ValueError, match=field):
        validate_profile(profile)


@pytest.mark.parametrize('seed', range(20))
def test_M12_access_denied_for_virtual_sixty_seconds(seed):
    now = [1000.]
    with TestClient(create_app(seed=seed, scenario='M12', clock=lambda: now[0])) as client:
        for _ in range(120):
            assert client.post('/api/login', json={}).status_code == 403
            now[0] += .5
        assert login(client)
        # This test driver paces at exactly two calls/sec; harness limiter tested elsewhere.
        assert now[0] == 1060


@pytest.mark.parametrize('seed', range(20))
def test_M13_no_booking_before_window(seed):
    now = [1000.]
    with TestClient(create_app(seed=seed, scenario='M13', clock=lambda: now[0], open_at=1010)) as client:
        assert login(client)
        payload = {'profile': PROFILE, 'train_id': 'winner', 'date': SEARCH['date'], 'idempotency_key': 'run-one'}
        assert not client.post('/api/search', json=SEARCH).json()['open']
        assert client.post('/api/passenger', json=payload).status_code == 409
        now[0] = 1010
        assert client.post('/api/passenger', json=payload).status_code == 200
        assert client.get('/api/state').json()['booking_count'] == 0


def test_review_mismatch_blocks_payment_and_nonconfirmed_train():
    with TestClient(create_app()) as client:
        review, payload = prepare(client)
        wrong = copy.deepcopy(review['review'])
        wrong['profile']['age'] = 29
        assert client.post('/api/review/run-one', json={'expected': wrong, 'digest': review['digest']}).status_code == 409
        assert client.post('/api/payment/run-one', json={'digest': review['digest']}).status_code == 409
        payload['idempotency_key'] = 'other'
        payload['train_id'] = 'waitlist'
        assert client.post('/api/passenger', json=payload).status_code == 409
        assert client.get('/api/state').json()['booking_count'] == 0


def test_general_quota_books_without_waiting_for_tatkal_window():
    with TestClient(create_app(clock=lambda:1000,open_at=2000)) as client:
        assert login(client)
        search={**SEARCH,'quota':'GENERAL'}
        assert client.post('/api/search',json=search).json()['open'] is True
        response=client.post('/api/passenger',json={'profile':PROFILE,'train_id':'winner',
                             'date':search['date'],'idempotency_key':'normal-one'})
        assert response.status_code==200
        review=response.json()
        assert review['review']['quota']=='GENERAL'
        assert client.post('/api/review/normal-one',json={'expected':review['review'],'digest':review['digest']}).status_code==200
        assert client.post('/api/payment/normal-one',json={'digest':review['digest']}).status_code==200
        assert client.get('/api/state').json()['booking_count']==0
        assert client.post('/api/test/approve/normal-one').status_code==200
        assert client.get('/api/ticket/normal-one').json()['ticket']['quota']=='GENERAL'
        assert client.get('/api/state').json()['booking_count']==1


def test_search_date_mismatch_stops_before_review_or_payment():
    with TestClient(create_app()) as client:
        assert login(client)
        assert client.post('/api/search',json={**SEARCH,'quota':'GENERAL'}).status_code==200
        response=client.post('/api/passenger',json={'profile':PROFILE,'train_id':'winner',
                             'date':'2026-10-27','idempotency_key':'wrong-date'})
        assert response.status_code==409
        assert client.get('/api/state').json()['booking_count']==0
