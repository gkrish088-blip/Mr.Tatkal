"""Actual GUI browser -> server queue -> persistent agent browser -> approval -> ticket."""
import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
import socket
import threading
import time
from zoneinfo import ZoneInfo

import httpx
import pytest
from playwright.async_api import async_playwright
import uvicorn
from fastapi import Request

from harness.web.app import create_app
from harness.web.settings import Settings

ROOT=Path(__file__).resolve().parents[2]


@pytest.fixture
def gui_server(tmp_path):
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    base=f'http://127.0.0.1:{port}'
    cfg=Settings(tmp_path/'data',ROOT/'skills',port=port,internal_url=base,max_seconds=90)
    app=create_app(cfg)
    model_calls=[]
    @app.post('/fixture/messages')
    async def model_fixture(request: Request):
        model_calls.append(await request.json())
        content=model_calls[-1]['messages'][0]['content']
        context=json.loads(content[0]['text'] if isinstance(content,list) else content)
        if context['goal']=='List your skills.':
            return {'content':[{'type':'text','text':'My available skills include '+', '.join(s['name'] for s in context['skills'])+'.'}],
                    'usage':{'input_tokens':30,'output_tokens':15}}
        if context['goal']=='Which skill helps fill a form?':
            assert context['messages'][-2]['role']=='assistant'
            return {'content':[{'type':'text','text':'Use web-form-fill. <script>window.unsafe=true</script>'}]}
        if len(model_calls)==1:
            return {'content':[{'type':'text','text':'Write the requested workspace note.'},
                    {'type':'tool_use','id':'fixture-write','name':'file_write','input':{'path':'gui-note.txt','text':'Written through the general agent GUI.'}}]}
        return {'content':[{'type':'text','text':'DONE'}]}
    server=uvicorn.Server(uvicorn.Config(app,log_level='error'))
    thread=threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True);thread.start()
    deadline=time.monotonic()+10
    while not server.started and time.monotonic()<deadline:time.sleep(.01)
    assert server.started
    yield base,cfg
    server.should_exit=True;thread.join(timeout=15);sock.close()
    assert not thread.is_alive(),'Server did not shut down cleanly'


async def test_gui_local_ticket_and_schedule_controls(gui_server):
    base,cfg=gui_server
    artifact_dir=ROOT/'test'/'browser-artifacts';artifact_dir.mkdir(exist_ok=True)
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True)
        try:
            page=await browser.new_page(viewport={'width':1440,'height':1060})
            errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
            await page.goto(base)
            await page.get_by_role('heading',name='Agent control room.').wait_for()
            await page.screenshot(path=str(artifact_dir/'overview.png'),full_page=True)
            await page.get_by_role('button',name='Run local test').click()
            await page.get_by_role('button',name='Approve test',exact=True).wait_for(timeout=45000)
            assert 'fictional payment only' in await page.locator('#handoff-box').inner_text()
            await page.get_by_role('button',name='Approve test',exact=True).click()
            deadline=time.monotonic()+30
            while 'COMPLETED' not in await page.locator('#live-badge').inner_text() and time.monotonic()<deadline:
                await asyncio.sleep(.3)
            assert 'COMPLETED' in await page.locator('#live-badge').inner_text(),await page.locator('#session-error').inner_text()
            assert await page.locator('#session-handoffs').inner_text()=='1 handoffs'
            assert await page.locator('#screenshot').is_visible()
            assert await page.locator('#replay-link').is_visible()
            await page.screenshot(path=str(artifact_dir/'completed.png'),full_page=True)
            async with httpx.AsyncClient() as client:
                rows=(await client.get(base+'/api/sessions')).json()
                detail=(await client.get(base+'/api/sessions/'+rows[0]['id'])).json()
                assert detail['status']=='completed'
                assert detail['handoffs']==1
                response=await client.get(base+await page.locator('#replay-link').get_attribute('href'))
                assert response.status_code==200 and '<img ' in response.text
                # A protected artifact route cannot reveal the session's raw state file.
                assert (await client.get(base+'/api/sessions/'+rows[0]['id']+'/artifacts/state.json')).status_code==404
            await page.get_by_role('button',name='Schedules',exact=True).click()
            await page.locator('#schedule-goal').fill('One future fictional test')
            await page.locator('#schedule-mode').select_option('demo')
            future=datetime.now(ZoneInfo('Asia/Kolkata'))+timedelta(hours=2)
            await page.locator('#schedule-when').fill(future.strftime('%Y-%m-%dT%H:%M:%S'))
            await page.get_by_role('button',name='Create schedule').click()
            await page.locator('.job').filter(has_text='One future fictional test').wait_for()
            await page.get_by_role('button',name='Pause',exact=True).click()
            await page.locator('.job .pill').filter(has_text='PAUSED').wait_for()
            await page.get_by_role('button',name='Resume',exact=True).click()
            await page.locator('.job .pill').filter(has_text='PENDING').wait_for()
            await page.get_by_role('button',name='Delete',exact=True).click()
            await page.locator('.job').wait_for(state='detached')
            await page.get_by_role('button',name='Server settings',exact=True).click()
            await page.get_by_role('heading',name='Behind the controls.').wait_for()
            assert await page.locator('input[type=password]').count()==1  # operator login, never provider keys
            assert not await page.locator('#view-settings input').count()
            # Mobile navigation and layout remain usable without horizontal page overflow.
            await page.set_viewport_size({'width':390,'height':844})
            await page.get_by_role('button',name='Overview',exact=True).click()
            assert await page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            await page.screenshot(path=str(artifact_dir/'mobile.png'),full_page=True)
            assert not errors,errors
        finally: await browser.close()


async def test_managed_browser_cookies_survive_restart(tmp_path):
    from harness.tools.browser import BrowserTools
    profile=tmp_path/'profile'
    browser=BrowserTools(artifact_dir=tmp_path/'artifacts')
    await browser.launch(str(profile))
    try:
        await browser.page.context.add_cookies([{'name':'fixture-session','value':'cookie-survives','domain':'localhost','path':'/','expires':time.time()+3600}])
    finally: await browser.close()
    restored=BrowserTools(artifact_dir=tmp_path/'artifacts')
    await restored.launch(str(profile))
    try:
        cookies=await restored.page.context.cookies()
        assert any(c['name']=='fixture-session' and c['value']=='cookie-survives' for c in cookies)
    finally: await restored.close()


async def test_gui_general_agent_uses_server_provider(gui_server,monkeypatch):
    base,cfg=gui_server
    canary='fixture-server-owned-claude-canary'
    monkeypatch.setenv('ANTHROPIC_API_KEY',canary)
    monkeypatch.setenv('CLAUDE_BASE_URL',base+'/fixture')
    monkeypatch.delenv('DEEPSEEK_API_KEY',raising=False)
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True)
        try:
            page=await browser.new_page(viewport={'width':1360,'height':950})
            await page.goto(base)
            from harness.skillrt.loader import SkillLoader
            from harness.skillrt.writer import SkillWriter
            from harness.log.redact import Redactor
            await SkillWriter(SkillLoader(ROOT/'skills',cfg.data_dir/'skills'),Redactor()).create('gui-learned','A newly learned fixture task','# Goal\nWrite a local note.')
            await page.locator('#goal').fill('Create gui-note.txt with a short note in the workspace.')
            await page.locator('#run-button').click()
            deadline=time.monotonic()+20
            while time.monotonic()<deadline:
                if 'COMPLETED' in await page.locator('#live-badge').inner_text():break
                await asyncio.sleep(.2)
            assert 'COMPLETED' in await page.locator('#live-badge').inner_text()
            assert (cfg.data_dir/'workspace/gui-note.txt').read_text()=='Written through the general agent GUI.'
            await page.locator('#skill option[value="gui-learned"]').wait_for(state='attached')
            assert canary not in await page.content()
            async with httpx.AsyncClient() as client:
                status=await client.get(base+'/api/status');assert canary not in status.text
            await page.reload()
            await page.locator('#recent-list .session-row').wait_for()
            await page.locator('#live-badge').filter(has_text='COMPLETED').wait_for()
            assert 'COMPLETED' in await page.locator('#live-badge').inner_text()
        finally:await browser.close()


async def test_gui_answers_and_followup_survive_reload(gui_server,monkeypatch):
    base,cfg=gui_server
    monkeypatch.setenv('ANTHROPIC_API_KEY','fixture-only')
    monkeypatch.setenv('CLAUDE_BASE_URL',base+'/fixture')
    monkeypatch.delenv('DEEPSEEK_API_KEY',raising=False)
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True)
        try:
            page=await browser.new_page()
            errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
            await page.goto(base)
            await page.locator('#goal').fill('List your skills.')
            await page.locator('#run-button').click()
            await page.locator('#conversation .assistant').filter(has_text='web-form-fill').wait_for(timeout=20000)
            assert 'COMPLETED' in await page.locator('#live-badge').inner_text()
            assert await page.locator('#session-steps').inner_text()=='0 steps'
            await page.locator('#followup').fill('Which skill helps fill a form?')
            await page.locator('#followup-button').click()
            await page.locator('#conversation .assistant').filter(has_text='Use web-form-fill.').wait_for(timeout=20000)
            assert await page.locator('#conversation .assistant').count()==2
            assert await page.evaluate('window.unsafe') is None
            await page.reload()
            await page.locator('#conversation .assistant').filter(has_text='Use web-form-fill.').wait_for()
            await page.screenshot(path=str(ROOT/'test/browser-artifacts/general-conversation.png'),full_page=True)
            assert not errors
        finally:await browser.close()
