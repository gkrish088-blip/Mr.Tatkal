"""Bounded shell execution. This is a trusted command tool, not an OS sandbox."""
import asyncio
import os
from pathlib import Path
import signal


async def _kill_tree(process):
    if os.name == 'nt':
        import psutil
        try:
            parent = psutil.Process(process.pid)
            children = parent.children(recursive=True)
            for child in reversed(children):
                try:
                    child.kill()
                except psutil.NoSuchProcess:
                    pass
            parent.kill()
            await asyncio.to_thread(psutil.wait_procs, children, timeout=3)
        except psutil.NoSuchProcess:
            pass
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    await process.wait()


class ShellTools:
    def __init__(self, workspace, max_output=32000):
        self.workspace = Path(workspace).resolve()
        self.max_output = max_output

    async def shell(self, cmd: str, timeout: float = 30, cwd: str = '.'):
        if not isinstance(cmd, str) or not cmd.strip():
            raise ValueError('cmd must be a nonempty string')
        if timeout <= 0 or timeout > 300:
            raise ValueError('timeout must be in (0, 300] seconds')
        directory = (self.workspace / cwd).resolve()
        if not directory.is_relative_to(self.workspace):
            raise PermissionError('cwd is outside the configured workspace')
        options = {'start_new_session': True} if os.name != 'nt' else {}
        process = await asyncio.create_subprocess_shell(
            cmd, cwd=directory, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE, **options)

        async def drain(stream):
            output = bytearray()
            total = 0
            while chunk := await stream.read(8192):
                total += len(chunk)
                output.extend(chunk[:max(0, self.max_output - len(output))])
            return output.decode('utf-8', errors='replace'), total > self.max_output

        stdout = asyncio.create_task(drain(process.stdout))
        stderr = asyncio.create_task(drain(process.stderr))
        timed_out = False
        try:
            await asyncio.wait_for(process.wait(), timeout)
        except asyncio.TimeoutError:
            timed_out = True
            await _kill_tree(process)
        except asyncio.CancelledError:
            await _kill_tree(process)
            stdout.cancel()
            stderr.cancel()
            raise
        out, err = await asyncio.gather(stdout, stderr)
        return {'stdout': out[0], 'stderr': err[0], 'truncated': out[1] or err[1],
                'exit_code': process.returncode, 'timed_out': timed_out}
