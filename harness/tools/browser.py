"""Generic Playwright browser tools with stable semantic refs and masked evidence."""
import asyncio
from collections import deque
import hashlib
from pathlib import Path
import time
from urllib.parse import urlsplit
import uuid


class RateLimiter:
    def __init__(self, limit=2, interval=1.0):
        if limit < 1 or interval <= 0:
            raise ValueError('Rate limits must be positive')
        self.limit, self.interval = limit, interval
        self.times = deque()
        self.lock = asyncio.Lock()

    async def acquire(self):
        async with self.lock:
            while True:
                now = time.monotonic()
                while self.times and now - self.times[0] >= self.interval:
                    self.times.popleft()
                if len(self.times) < self.limit:
                    self.times.append(now)
                    return
                await asyncio.sleep(self.interval - (now - self.times[0]))


SNAPSHOT_SCRIPT = r'''() => {
 const counts = {}, elements = [];
 const visible = e => !!(e.getClientRects().length) && getComputedStyle(e).visibility !== 'hidden';
 for (const e of document.querySelectorAll('a,button,input,select,textarea,[role="button"],[role="textbox"],[contenteditable="true"]')) {
   if (!visible(e)) continue;
   const label = e.getAttribute('aria-label') ||
     (e.labels && [...e.labels].map(x => { const copy=x.cloneNode(true); for(const c of copy.querySelectorAll('input,select,textarea')) c.remove(); return copy.textContent.trim(); }).join(' ')) ||
     e.getAttribute('placeholder') || (e.tagName === 'INPUT' ? '' : e.innerText) || '';
   const role = e.getAttribute('role') || e.tagName.toLowerCase();
   const key = [role, label.trim(), e.type || '', e.getAttribute('name') || '', e.getAttribute('href') || ''].join('|');
   counts[key] = (counts[key] || 0) + 1;
   // Stable across replacement of an element with identical semantic landmarks.
   let hash = 2166136261;
   for (const c of key + '|' + counts[key]) { hash ^= c.charCodeAt(0); hash = Math.imul(hash, 16777619); }
   const ref = 'e' + (hash >>> 0).toString(16);
   e.setAttribute('data-harness-ref', ref);
   elements.push({ref, role, name: label.trim().slice(0,300), disabled: !!e.disabled,
     options: e.tagName === 'SELECT' ? [...e.options].map(o => ({label:o.label,value:o.value})) : undefined});
 }
 return {url: location.href, title: document.title, text: document.body.innerText.slice(0,20000), elements};
}'''


class BrowserTools:
    def __init__(self, page=None, allowed_hosts=None, artifact_dir='runs/browser', max_requests=2):
        self.page = page
        self.allowed_hosts = set(allowed_hosts or ['localhost', '127.0.0.1', '::1'])
        self.artifact_dir = Path(artifact_dir)
        self.limiter = RateLimiter(max_requests)
        self._playwright = self._browser = None
        self._secret_values = set()
        self._guarded_contexts = set()

    def _allowed(self, url):
        parsed = urlsplit(url)
        return parsed.scheme in ('http', 'https') and parsed.hostname in self.allowed_hosts

    def register_secret(self, value):
        if value:
            self._secret_values.add(value)

    def _clean(self, value):
        if isinstance(value, str):
            for secret in sorted(self._secret_values, key=len, reverse=True):
                value = value.replace(secret, '[REDACTED]')
            return value
        if isinstance(value, dict):
            return {k: self._clean(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._clean(v) for v in value]
        return value

    async def _guard(self):
        if self.page is None:
            raise RuntimeError('Attach a browser first')
        context = self.page.context
        if id(context) not in self._guarded_contexts:
            async def route_request(route):
                if self._allowed(route.request.url):
                    # Only navigations and application requests consume site pacing;
                    # assets do not cause a deadlock on a normal page load.
                    if route.request.is_navigation_request() or route.request.resource_type in ('xhr', 'fetch'):
                        await self.limiter.acquire()
                    await route.continue_()
                else:
                    await route.abort('blockedbyclient')
            await context.route('**/*', route_request)
            self._guarded_contexts.add(id(context))

    async def attach(self, cdp_url='http://127.0.0.1:9222'):
        parsed = urlsplit(cdp_url)
        if parsed.hostname not in ('localhost', '127.0.0.1', '::1'):
            raise PermissionError('CDP must be on the local machine')
        from playwright.async_api import async_playwright
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.connect_over_cdp(cdp_url)
        context = self._browser.contexts[0] if self._browser.contexts else await self._browser.new_context()
        # Never claim an arbitrary existing real-site tab.
        self.page = await context.new_page()
        await self._guard()
        return {'attached': True}

    async def goto(self, url: str):
        if not self._allowed(url):
            raise PermissionError('Host is not in the configured browser allowlist')
        await self._guard()
        await self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
        if not self._allowed(self.page.url):
            raise PermissionError('Navigation escaped the browser allowlist')
        return await self.snapshot()

    async def snapshot(self):
        await self._guard()
        if self.page.url != 'about:blank' and not self._allowed(self.page.url):
            raise PermissionError('Current page is outside the browser allowlist')
        data = self._clean(await self.page.evaluate(SNAPSHOT_SCRIPT))
        data['state_hash'] = hashlib.sha256(str(data).encode()).hexdigest()
        return data

    async def _ref(self, ref):
        # Declarative macros can bind semantic landmarks before their first snapshot.
        if isinstance(ref, str) and ref.startswith(('label:', 'text:')):
            await self.snapshot()
            kind, value = ref.split(':', 1)
            if not value:
                raise ValueError('Semantic reference text must not be empty')
            locator = (self.page.get_by_label(value, exact=True) if kind == 'label'
                       else self.page.get_by_text(value, exact=True))
            if await locator.count() != 1:
                raise ValueError('Semantic reference must identify exactly one element')
            return locator
        if not isinstance(ref, str) or not ref.startswith('e') or not all(c in '0123456789abcdef' for c in ref[1:]):
            raise ValueError('Invalid element reference')
        await self.snapshot()
        locator = self.page.locator(f'[data-harness-ref="{ref}"]')
        if await locator.count() != 1:
            raise ValueError('Element reference is stale or ambiguous; take a new snapshot')
        return locator

    async def click(self, ref: str):
        locator = await self._ref(ref)
        await locator.click(timeout=10000)
        return await self.snapshot()

    async def type(self, ref: str, text: str):
        locator = await self._ref(ref)
        # All typed values are excluded from snapshots and masked in screenshots.
        self.register_secret(text)
        try:
            await locator.fill(text, timeout=10000)
        except Exception:
            # Playwright errors can include a call log containing the fill value.
            raise RuntimeError('Browser fill failed; refresh the field reference') from None
        return {'typed': True}

    async def press(self, key: str):
        await self._guard()
        await self.page.keyboard.press(key)
        return await self.snapshot()

    async def select(self, ref: str, value: str):
        locator = await self._ref(ref)
        await locator.select_option(value)
        return await self.snapshot()

    async def scroll(self, amount: int = 500):
        await self._guard()
        await self.page.mouse.wheel(0, amount)
        return await self.snapshot()

    async def wait_for(self, text: str = None, ref: str = None, url: str = None, timeout: int = 10000):
        await self._guard()
        if sum(x is not None for x in (text, ref, url)) != 1:
            raise ValueError('Specify exactly one of text, ref, url')
        if text is not None:
            await self.page.get_by_text(text, exact=False).first.wait_for(timeout=timeout)
        elif ref is not None:
            await (await self._ref(ref)).wait_for(timeout=timeout)
        else:
            if not self._allowed(url):
                raise PermissionError('Wait URL is outside allowlist')
            await self.page.wait_for_url(url, timeout=timeout)
        return await self.snapshot()

    async def screenshot(self):
        await self.snapshot()
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        path = self.artifact_dir / f'{uuid.uuid4().hex}.png'
        # Hide every form value, plus any element visibly echoing an inserted value.
        mask = self.page.locator('input,textarea,select,[contenteditable="true"],iframe')
        masks = [mask]
        for value in self._secret_values:
            masks.append(self.page.get_by_text(value, exact=False))
        data = await self.page.screenshot(path=str(path), mask=masks, mask_color='#202938')
        return {'screenshot': str(path.resolve()), 'state_hash': hashlib.sha256(data).hexdigest()}

    async def tabs(self):
        await self._guard()
        return {'tabs': [{'index': i, 'url': self._clean(p.url)}
                         for i, p in enumerate(self.page.context.pages) if self._allowed(p.url)]}

    async def select_tab(self, index: int):
        await self._guard()
        pages = self.page.context.pages
        if index < 0 or index >= len(pages) or not self._allowed(pages[index].url):
            raise PermissionError('Tab is unavailable or outside the browser allowlist')
        self.page = pages[index]
        return await self.snapshot()

    async def download(self, ref: str):
        locator = await self._ref(ref)
        async with self.page.expect_download(timeout=30000) as pending:
            await locator.click()
        download = await pending.value
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        # Never trust a server-supplied filename as an output path.
        name = Path(download.suggested_filename.replace('\\', '/')).name
        path = self.artifact_dir / (uuid.uuid4().hex + '-' + name)
        await download.save_as(path)
        return {'path': str(path.resolve()), 'filename': name}

    async def close(self):
        # Disconnecting Playwright does not close the operator's persistent Chrome.
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
