"""Install independently reusable tools in a generic registry."""
from .files import FileTools
from .shell import ShellTools
from .clock import Clock
from .secrets import SecretTools
from .browser import BrowserTools
from .desktop import DesktopTools


def install_tools(registry, workspace, browser=None, desktop=None):
    import os
    import platform
    import sys
    files, shell, clock = FileTools(workspace), ShellTools(workspace), Clock()
    capabilities = {'workspace': str(files.workspace), 'platform': platform.platform(),
                    'python': sys.executable, 'shell': os.environ.get('COMSPEC', '/bin/sh'),
                    'browser_enabled': bool(browser), 'desktop_enabled': bool(desktop),
                    'browser_allowed_hosts': sorted(browser.allowed_hosts) if browser else []}
    registry.capabilities = capabilities
    async def system_info():
        return capabilities
    registry.register('system_info', system_info, 'Get the workspace, OS, Python executable and enabled computer capabilities')
    async def execute_shell(cmd: str, timeout: float = 30, cwd: str = '.'):
        from harness.core.types import ToolResult
        result = await shell.shell(cmd, timeout, cwd)
        ok = not result['timed_out'] and result['exit_code'] == 0
        return ToolResult(ok, result, None if ok else 'Shell timed out' if result['timed_out'] else 'Shell command failed')
    registry.register('shell', execute_shell, 'Run a trusted shell command; commands are not OS sandboxed.')
    for name in ('read', 'write', 'edit', 'list', 'extract'):
        registry.register('file_' + name, getattr(files, name), 'Workspace-confined file ' + name)
    registry.register('clock_wait_until', clock.wait_until, 'Wait for timezone-aware timestamp')
    if browser:
        for name in ('goto', 'snapshot', 'click', 'type', 'press', 'select', 'scroll', 'wait_for', 'screenshot', 'tabs', 'select_tab', 'download', 'assert_json'):
            registry.register('browser_' + name, getattr(browser, name), 'Browser ' + name)
        registry.register('secret', SecretTools(browser, getattr(registry, 'redactor', None)).insert,
                          'Insert a named environment/keychain secret without returning it')
        registry.capture = browser.screenshot
    if desktop:
        for name in ('click', 'double_click', 'drag', 'scroll', 'type_text', 'hotkey', 'launch_app', 'focus_window', 'screenshot', 'a11y_tree'):
            registry.register('desktop_' + name, getattr(desktop, name), 'Optional local desktop ' + name)
        if not browser:
            registry.capture = desktop.screenshot
    return {'files': files, 'shell': shell, 'clock': clock, 'browser': browser, 'desktop': desktop}
