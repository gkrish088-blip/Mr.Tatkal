"""Real headless Chromium against localhost; test-only payment approval transport."""
import asyncio
import json
import socket
import threading
import time
from pathlib import Path

import httpx
import pytest
import uvicorn
from playwright.async_api import async_playwright

from harness.core.loop import Engine
from harness.core.macro import MacroRunner
from harness.core.run_manager import RunStore
from harness.core.types import ToolCall, ToolRegistry
from harness.handoff.channel import HumanChannel
from harness.log.runlog import RunLog
from harness.skillrt.loader import SkillLoader
from harness.tools.browser import BrowserTools
from mock.mock_irctc.app import create_app


@pytest.fixture
def local_lab():
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(create_app(), log_level='error'))
    thread = threading.Thread(target=lambda: server.run(sockets=[sock]), daemon=True)
    thread.start()
    deadline = time.monotonic()+10
    while not server.started and time.monotonic() < deadline:
        time.sleep(.01)
    if not server.started:
        raise RuntimeError('Local fixture server failed to start')
    yield f'http://127.0.0.1:{port}'
    server.should_exit = True
    thread.join(timeout=5)
    sock.close()


@pytest.mark.asyncio
async def test_generic_engine_skill_macro_local_ticket(local_lab, tmp_path):
    async with async_playwright() as playwright:
        chromium = await playwright.chromium.launch(headless=True)
        try:
            page = await chromium.new_page()
            browser = BrowserTools(page=page, artifact_dir=tmp_path/'screenshots')
            registry = ToolRegistry()
            for method in ('goto', 'wait_for', 'type', 'click', 'select', 'snapshot', 'screenshot'):
                registry.register('browser_'+method, getattr(browser, method))

            async def observe():
                return {**await browser.snapshot(), **await browser.screenshot()}

            registry.capture = observe
            store = RunStore(tmp_path/'runs')
            state = store.create('Rehearse one fictional ticket', {
                'url': local_lab, 'date': '2026-10-26', 'name': 'Fictional Rider',
                'age': '28', 'gender': 'Female', 'nationality': 'Indian', 'mobile': '9000000000'})
            log = RunLog(tmp_path/'runs', state.run_id)
            # The test transport is isolated here; production tools never auto-approve.
            class MockApprovalTransport:
                async def send(self, request):
                    assert request['kind'] == 'external_approval'
                    key = await page.evaluate('ctx.key')
                    async with httpx.AsyncClient() as client:
                        response = await client.post(local_lab+'/api/test/approve/'+key)
                        assert response.status_code == 200
                    assert human.reply(request['id'], 'done')

            human = HumanChannel(tmp_path/'handoff.json', transport=MockApprovalTransport())
            loader = SkillLoader(Path(__file__).resolve().parents[2]/'skills')
            engine = Engine(registry, store, log, loader, human=human, max_seconds=120)
            result = await MacroRunner(engine).run(state, loader.load('mock-booking'))
            assert result.status == 'completed', result.history[-1] if result.history else result
            assert 'Review journey before payment' in await page.inner_text('body')
            # Inspect the actual rendered review against all requested values before submission.
            review = await page.locator('pre').inner_text()
            reviewed = json.loads(review)
            assert reviewed['profile'] == {'name': 'Fictional Rider', 'age': 28, 'gender': 'Female', 'nationality': 'Indian', 'mobile': '9000000000'}
            assert reviewed['train']['id'] == 'winner'
            assert reviewed['origin'] == 'RK' and reviewed['destination'] == 'HW'
            assert reviewed['date'] == '2026-10-26' and reviewed['quota'] == 'TATKAL'
            assert (await engine.act(state, ToolCall('browser_click', {'ref': 'text:Verify review and request test payment'}), 'Submit the verified fictional payment request')).ok
            await browser.wait_for(text='External payment approval required')
            assert (await engine.act(state, ToolCall('ask_human', {'kind': 'external_approval', 'text': 'Approve fictional Rs 65 in the test transport', 'timeout': 10}), 'Pause for the single external payment approval', 'human')).ok
            assert (await engine.act(state, ToolCall('browser_click', {'ref': 'text:Check payment status'}), 'Check for the fictional ticket after approval')).ok
            await browser.wait_for(text='Ticket confirmed')
            assert state.handoffs == 1
            assert await page.get_by_text('MOCK000000', exact=True).count() == 1
            async with httpx.AsyncClient() as client:
                assert (await client.get(local_lab+'/api/state')).json()['booking_count'] == 1
            log.summary(state)
            assert (log.path/'replay.html').exists()
            events = [json.loads(line) for line in (log.path/'run.jsonl').read_text(encoding='utf-8').splitlines()]
            assert all(e['reason'] and e['before']['screenshot'] and e['after']['screenshot'] for e in events)
            assert all(Path(e['after']['screenshot']).exists() for e in events)
        finally:
            await chromium.close()
