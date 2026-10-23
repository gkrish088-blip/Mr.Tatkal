"""UTC clock with explicit measured offset; monotonic waits resist clock jumps."""
import asyncio
from datetime import datetime, timezone
import socket
import struct
import time


class Clock:
    def __init__(self, offset=0.0):
        self.offset = float(offset)

    def now(self):
        return time.time() + self.offset

    async def wait_until(self, timestamp):
        if isinstance(timestamp, str):
            parsed = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            if parsed.tzinfo is None:
                raise ValueError('Timestamp must include a timezone')
            timestamp = parsed.timestamp()
        while (remaining := float(timestamp) - self.now()) > 0:
            await asyncio.sleep(min(remaining, 0.1))
        return {'timestamp': datetime.fromtimestamp(self.now(), timezone.utc).isoformat(),
                'offset_seconds': self.offset}

    async def synchronize(self, server='pool.ntp.org', timeout=2):
        def measure():
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(timeout)
                start = time.time()
                sock.sendto(b'\x23' + 47 * b'\0', (server, 123))
                packet, _ = sock.recvfrom(512)
                end = time.time()
            if len(packet) < 48 or (packet[0] & 7) != 4 or packet[1] == 0:
                raise ValueError('Invalid NTP response')
            receive_s, receive_f, transmit_s, transmit_f = struct.unpack('!4I', packet[32:48])
            received = receive_s - 2208988800 + receive_f / 2**32
            transmitted = transmit_s - 2208988800 + transmit_f / 2**32
            return ((received - start) + (transmitted - end)) / 2, end - start
        self.offset, latency = await asyncio.to_thread(measure)
        return {'offset_seconds': self.offset, 'roundtrip_seconds': latency}
