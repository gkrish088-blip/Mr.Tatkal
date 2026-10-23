"""Seeded local booking simulator. All accounts, tickets and payments are fictional.

Run: python -m uvicorn mock.mock_irctc.app:app --host 127.0.0.1
Latency uses a virtual clock by default; real_latency=True sleeps for browser chaos runs.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import random
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse


REQUIRED_PROFILE = ('name', 'age', 'gender', 'nationality', 'mobile')


def validate_profile(profile: dict) -> dict:
    missing = [key for key in REQUIRED_PROFILE if profile.get(key) in (None, '')]
    if missing:
        raise ValueError('Missing passenger fields: ' + ', '.join(missing))
    if isinstance(profile['age'], bool) or not str(profile['age']).isdigit() or not 1 <= int(profile['age']) <= 120:
        raise ValueError('Passenger age must be between 1 and 120')
    if not str(profile['mobile']).isdigit() or len(str(profile['mobile'])) != 10:
        raise ValueError('Passenger mobile must contain ten digits')
    return dict(profile, age=int(profile['age']), mobile=str(profile['mobile']))


def rank_fares(trains: list[dict]) -> list[dict]:
    """Total fare, then departure, then a deterministic identifier; AVL only."""
    return sorted((t for t in trains if t['availability'] == 'AVL'),
                  key=lambda t: (t['total_fare'], t['departure'], t['id']))


def create_app(seed: int = 0, scenario: str = 'M1', *, real_latency: bool = False,
               open_at: float = 0, clock=None, payment_timeout: float = 120) -> FastAPI:
    app = FastAPI(title='Local Rail Lab - fictional tickets only')
    rng = random.Random(seed)
    clock = clock or time.time
    state = {'sessions': {}, 'reservations': {}, 'bookings': {}, 'faults': [],
             'requests': [], 'virtual_latency': 0.0, 'expired': False,
             'denied_until': clock() + (60 if scenario == 'M12' else 0)}
    app.state.lab = state
    trains = [
        {'id': 'waitlist', 'name': 'Budget connection', 'class': '2S', 'total_fare': 35, 'departure': '06:00', 'availability': 'WL'},
        {'id': 'later', 'name': 'Valley local', 'class': '2S', 'total_fare': 65, 'departure': '09:40', 'availability': 'AVL'},
        {'id': 'winner', 'name': 'Morning local', 'class': '2S', 'total_fare': 65, 'departure': '07:15', 'availability': 'AVL'},
        {'id': 'sleeper', 'name': 'River express', 'class': 'SL', 'total_fare': 135, 'departure': '06:30', 'availability': 'AVL'},
        {'id': 'rac', 'name': 'Hills local', 'class': '2S', 'total_fare': 40, 'departure': '05:30', 'availability': 'RAC'},
        {'id': 'regret', 'name': 'Sold out express', 'class': 'SL', 'total_fare': 45, 'departure': '05:00', 'availability': 'REGRET'},
    ]

    @app.middleware('http')
    async def inject(request: Request, call_next):
        path = request.url.path
        if path.startswith('/api/') and path not in ('/api/health', '/api/state'):
            state['requests'].append({'path': path, 'time': clock()})
            if scenario == 'M12' and clock() < state['denied_until']:
                from fastapi.responses import JSONResponse
                return JSONResponse({'detail': 'Access denied; wait before retry'}, status_code=403)
            if scenario == 'M2':
                delay = rng.uniform(1, 8)
                state['virtual_latency'] += delay
                if real_latency:
                    await asyncio.sleep(delay)
            if scenario == 'M3' and path in ('/api/search', '/api/passenger') and rng.random() < .2:
                state['faults'].append('server_error')
                from fastapi.responses import JSONResponse
                return JSONResponse({'detail': 'Temporary service unavailable'}, status_code=503)
        return await call_next(request)

    def session(request):
        token = request.cookies.get('lab_session')
        if token not in state['sessions']:
            raise HTTPException(401, 'Session expired; log in again')
        return token

    def reservation(key):
        if key not in state['reservations']:
            raise HTTPException(404, 'Reservation not found')
        return state['reservations'][key]

    @app.get('/', response_class=HTMLResponse)
    async def page():
        html = Path(__file__).with_name('index.html').read_text(encoding='utf-8')
        return html.replace('__VARIANT__', str(seed if scenario == 'M6' else 0)).replace('__POPUP__', 'true' if scenario == 'M6' else 'false')

    @app.get('/api/health')
    async def health():
        return {'mock': True, 'scenario': scenario, 'seed': seed}

    @app.get('/api/captcha')
    async def captcha():
        # Visible challenge is an accessible SVG in the UI. No production captcha bypass.
        return {'challenge': 'TRAIN', 'svg': '<svg xmlns="http://www.w3.org/2000/svg" width="180" height="55"><rect width="180" height="55" fill="#eee"/><text x="15" y="40" transform="skewX(-12)" font-size="32">TRAIN</text><path d="M0 18L180 30" stroke="#777"/></svg>'}

    @app.post('/api/login')
    async def login(data: dict, response: Response):
        if data.get('username') != 'demo' or data.get('password') != 'demo':
            raise HTTPException(401, 'Use the fictional demo/demo account')
        if data.get('captcha') != 'TRAIN' or (scenario == 'M5' and rng.random() < .4):
            state['faults'].append('captcha')
            raise HTTPException(422, 'Captcha incorrect; refresh and retry')
        token = uuid.uuid4().hex
        state['sessions'][token] = True
        response.set_cookie('lab_session', token, httponly=True, samesite='strict')
        return {'logged_in': True}

    @app.post('/api/search')
    async def search(data: dict, request: Request):
        session(request)
        if data.get('origin') != 'RK' or data.get('destination') != 'HW' or data.get('quota') != 'TATKAL' or not data.get('date'):
            raise HTTPException(422, 'Expected RK to HW, date, and TATKAL quota')
        return {'trains': trains, 'open': clock() >= open_at, 'opens_at': open_at}

    @app.post('/api/passenger')
    async def passenger(data: dict, request: Request):
        token = session(request)
        if scenario == 'M4' and not state['expired']:
            state['expired'] = True
            state['sessions'].pop(token)
            state['faults'].append('session_expiry')
            raise HTTPException(401, 'Session expired; log in again')
        if clock() < open_at:
            raise HTTPException(409, 'Booking window has not opened')
        try:
            profile = validate_profile(data.get('profile', {}))
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        if data.get('train_id') != rank_fares(trains)[0]['id']:
            raise HTTPException(409, 'Selected train is not the cheapest confirmed option')
        key = data.get('idempotency_key')
        if not isinstance(key, str) or not key:
            raise HTTPException(422, 'idempotency_key is required')
        payload = {'profile': profile, 'train': rank_fares(trains)[0], 'date': data.get('date'),
                   'origin': 'RK', 'destination': 'HW', 'quota': 'TATKAL'}
        if not payload['date']:
            raise HTTPException(422, 'Journey date is required')
        existing = state['reservations'].get(key)
        if existing and existing['review'] != payload:
            raise HTTPException(409, 'Idempotency key already used for different details')
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        state['reservations'].setdefault(key, {'review': payload, 'digest': digest, 'verified': False, 'status': 'review'})
        return {'reservation_id': key, 'review': payload, 'digest': digest}

    @app.post('/api/review/{key}')
    async def verify_review(key: str, data: dict, request: Request):
        session(request)
        record = reservation(key)
        if data.get('expected') != record['review'] or data.get('digest') != record['digest']:
            record['verified'] = False
            raise HTTPException(409, 'Review mismatch: payment blocked')
        record['verified'] = True
        return {'verified': True, 'digest': record['digest']}

    @app.post('/api/payment/{key}')
    async def payment(key: str, data: dict, request: Request):
        session(request)
        record = reservation(key)
        if state['bookings'] and key not in state['bookings']:
            raise HTTPException(409, 'One booking per team; an existing ticket is already confirmed')
        if not record['verified'] or data.get('digest') != record['digest']:
            raise HTTPException(409, 'Verified review required before payment')
        if record['status'] == 'review':
            record.update(status='pending', requested_at=clock())
        return {'status': record['status'], 'external_approval': True, 'amount': record['review']['train']['total_fare']}

    @app.post('/api/test/approve/{key}')
    async def approve(key: str):
        record = reservation(key)
        if key in state['bookings']:
            return state['bookings'][key]
        if state['bookings']:
            raise HTTPException(409, 'One booking per team; another reservation is already confirmed')
        if record['status'] != 'pending' and key not in state['bookings']:
            raise HTTPException(409, 'No pending payment')
        if record.get('requested_at', clock()) + payment_timeout < clock():
            record['status'] = 'expired'
            raise HTTPException(409, 'Payment approval timed out')
        state['bookings'].setdefault(key, {'pnr': f'MOCK{seed:06d}', **record['review']})
        record['status'] = 'booked'
        return state['bookings'][key]

    @app.get('/api/ticket/{key}')
    async def ticket(key: str, request: Request):
        session(request)
        record = reservation(key)
        if record['status'] == 'pending' and record['requested_at'] + payment_timeout < clock():
            record['status'] = 'expired'
        return {'status': record['status'], 'ticket': state['bookings'].get(key)}

    @app.get('/api/state')
    async def inspect_state():
        return {'booking_count': len(state['bookings']), 'faults': state['faults'], 'virtual_latency': state['virtual_latency']}

    return app


app = create_app()
