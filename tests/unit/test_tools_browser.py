import asyncio
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading

import pytest
from playwright.async_api import async_playwright

from harness.tools.browser import BrowserTools


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
async def test_browser_real_dom_refs_actions_and_masked_screenshot(tmp_path):
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
            await tools.type(refs['Name'], 'CANARY-SECRET')
            await tools.type(refs['Password'], 'PASSWORD-CANARY')
            snapshot = await tools.snapshot()
            assert 'CANARY-SECRET' not in str(snapshot)
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
            with pytest.raises(PermissionError):
                await tools.goto('https://example.com')
            with pytest.raises(ValueError):
                await tools.click('invalid')
            await browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
