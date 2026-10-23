import asyncio
import os
from pathlib import Path
import sys
import time

import pytest

from harness.tools.files import FileTools
from harness.tools.shell import ShellTools
from harness.tools.clock import Clock
from harness.tools.desktop import DesktopTools
from harness.tools.browser import RateLimiter


@pytest.mark.asyncio
async def test_atomic_files_and_exact_edit(tmp_path):
    files = FileTools(tmp_path)
    await files.write('nested/note.txt', 'hello\nworld')
    await files.edit('nested/note.txt', 'world', 'project')
    assert (await files.read('nested/note.txt'))['text'] == 'hello\nproject'
    assert not list((tmp_path / 'nested').glob('.write-*'))
    with pytest.raises(ValueError):
        await files.edit('nested/note.txt', 'missing', 'no')
    with pytest.raises(PermissionError):
        await files.write('../escaped.txt', 'no')
    assert (await files.list('nested'))['entries'] == [{'name': 'note.txt', 'directory': False}]
    assert (await files.read('nested/note.txt', max_chars=3)) == {'text': 'hel', 'truncated': True}


@pytest.mark.asyncio
async def test_file_symlink_escape(tmp_path):
    files = FileTools(tmp_path / 'inside')
    outside = tmp_path / 'outside'
    outside.mkdir()
    try:
        (files.workspace / 'link').symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip('Host does not grant symlink privilege')
    with pytest.raises(PermissionError):
        await files.write('link/private.txt', 'no')


@pytest.mark.asyncio
async def test_shell_output_exit_and_timeout(tmp_path):
    shell = ShellTools(tmp_path, max_output=100)
    result = await shell.shell(f'"{sys.executable}" -c "print(\'x\'*10000); raise SystemExit(7)"')
    assert result['exit_code'] == 7
    assert result['truncated'] and len(result['stdout']) == 100
    started = time.monotonic()
    result = await shell.shell(f'"{sys.executable}" -c "import time; time.sleep(30)"', timeout=.2)
    assert result['timed_out']
    assert time.monotonic() - started < 5
    with pytest.raises(PermissionError):
        await shell.shell('echo hello', cwd='..')


@pytest.mark.asyncio
async def test_shell_timeout_kills_descendants(tmp_path):
    import psutil
    script = tmp_path / 'tree.py'
    script.write_text('import subprocess,sys,time\np=subprocess.Popen([sys.executable,"-c","import time; time.sleep(30)"])\nopen("child.pid","w").write(str(p.pid))\ntime.sleep(30)\n')
    result = await ShellTools(tmp_path).shell(f'"{sys.executable}" tree.py', timeout=1)
    assert result['timed_out']
    child_pid = int((tmp_path / 'child.pid').read_text())
    assert not psutil.pid_exists(child_pid)


@pytest.mark.asyncio
async def test_clock_offset_and_timezone():
    clock = Clock(offset=5)
    start = time.monotonic()
    result = await clock.wait_until(time.time() + 5.03)
    assert time.monotonic() - start < .3
    assert result['offset_seconds'] == 5
    with pytest.raises(ValueError):
        await clock.wait_until('2026-01-01T00:00:00')


@pytest.mark.asyncio
async def test_rate_limiter_concurrent_sliding_window():
    limiter = RateLimiter(limit=2, interval=.05)
    times = []
    async def request():
        await limiter.acquire()
        times.append(time.monotonic())
    await asyncio.gather(*(request() for _ in range(6)))
    assert all(times[i+2] - times[i] >= .048 for i in range(4))


@pytest.mark.asyncio
async def test_desktop_disabled_by_default():
    with pytest.raises(PermissionError):
        await DesktopTools().click(1, 1)


@pytest.mark.asyncio
async def test_installed_shell_failure_and_numeric_schemas(tmp_path):
    from harness.core.types import ToolRegistry, ToolCall
    from harness.tools import install_tools
    registry = ToolRegistry()
    install_tools(registry, tmp_path)
    result = await registry.execute(ToolCall('shell', {'cmd': f'"{sys.executable}" -c "raise SystemExit(2)"'}))
    assert not result.ok and result.data['exit_code'] == 2
    schema = next(s['function']['parameters'] for s in registry.schemas() if s['function']['name'] == 'shell')
    assert schema['properties']['timeout']['type'] == 'number'


@pytest.mark.asyncio
async def test_secret_never_returned(monkeypatch):
    from harness.tools.secrets import SecretTools
    class Browser:
        def register_secret(self, value):
            self.secret = value
        async def type(self, ref, text):
            assert ref == 'eface' and text == 'CANARY-NOT-LOGGED'
    monkeypatch.setenv('TEST_SECRET_VALUE', 'CANARY-NOT-LOGGED')
    browser = Browser()
    result = await SecretTools(browser).insert('TEST_SECRET_VALUE', 'eface')
    assert result == {'inserted': True}
    assert browser.secret == 'CANARY-NOT-LOGGED'


@pytest.mark.asyncio
async def test_browser_fill_error_cannot_echo_secret():
    from harness.tools.browser import BrowserTools
    browser = BrowserTools()
    class BrokenField:
        async def fill(self, text, **kwargs):
            raise RuntimeError('Playwright log contains ' + text)
    async def resolve(ref):
        return BrokenField()
    browser._ref = resolve
    with pytest.raises(RuntimeError) as error:
        await browser.type('label:Password', 'ERROR-CANARY')
    assert 'ERROR-CANARY' not in str(error.value)
