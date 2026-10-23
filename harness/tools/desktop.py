"""Optional local desktop adapter. Disabled until the operator enables it."""
import asyncio
import hashlib
from pathlib import Path
import subprocess
import uuid


class DesktopTools:
    def __init__(self, enabled=False, artifact_dir='runs/desktop'):
        self.enabled = enabled
        self.artifact_dir = Path(artifact_dir)

    def _input(self):
        if not self.enabled:
            raise PermissionError('Desktop control requires explicit operator configuration')
        import pyautogui
        return pyautogui

    async def click(self, x: int, y: int):
        await asyncio.to_thread(self._input().click, x, y)
        return {'clicked': True}

    async def double_click(self, x: int, y: int):
        await asyncio.to_thread(self._input().doubleClick, x, y, interval=0.15)
        return {'clicked': True}

    async def drag(self, x: int, y: int, to_x: int, to_y: int, duration: float = 0.5):
        api = self._input()
        await asyncio.to_thread(api.moveTo, x, y)
        await asyncio.to_thread(api.dragTo, to_x, to_y, max(0.2, min(duration, 5)))
        return {'dragged': True}

    async def scroll(self, amount: int):
        await asyncio.to_thread(self._input().scroll, amount)
        return {'scrolled': True}

    async def type_text(self, text: str):
        api = self._input()
        # pyautogui does not support Unicode; fail clearly rather than corrupt text.
        if not text.isascii():
            raise ValueError('Desktop typing currently supports ASCII only; use browser tools for Unicode')
        await asyncio.to_thread(api.write, text, interval=0.03)
        return {'typed': True}

    async def hotkey(self, keys: list):
        if isinstance(keys, str):
            keys = keys.split('+')
        await asyncio.to_thread(self._input().hotkey, *keys)
        return {'pressed': True}

    async def launch_app(self, executable: str, args: list = None):
        self._input()
        process = subprocess.Popen([executable, *(args or [])], shell=False)
        return {'pid': process.pid}

    async def focus_window(self, title: str):
        self._input()
        import pygetwindow
        matches = pygetwindow.getWindowsWithTitle(title)
        if len(matches) != 1:
            raise ValueError('Window title must identify exactly one window')
        await asyncio.to_thread(matches[0].activate)
        return {'focused': True}

    async def screenshot(self):
        api = self._input()
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        path = self.artifact_dir / f'{uuid.uuid4().hex}.png'
        image = await asyncio.to_thread(api.screenshot)
        await asyncio.to_thread(image.save, path)
        return {'screenshot': str(path.resolve()), 'state_hash': hashlib.sha256(path.read_bytes()).hexdigest(),
                'warning': 'Desktop screenshots are not automatically redacted; use a dedicated secret-free desktop'}

    async def a11y_tree(self):
        self._input()
        try:
            import uiautomation as auto
        except ImportError as exc:
            raise RuntimeError('Install optional uiautomation package for Windows accessibility') from exc
        def collect(node, depth=0):
            if depth > 4:
                return []
            rows = [{'name': node.Name, 'role': node.ControlTypeName}]
            for child in node.GetChildren()[:50]:
                rows.extend(collect(child, depth + 1))
            return rows
        return {'elements': await asyncio.to_thread(collect, auto.GetForegroundControl())}
