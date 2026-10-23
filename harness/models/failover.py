import asyncio
import random
import httpx
from harness.models.adapter import ModelError


class FailoverModel:
    def __init__(self, primary, fallback, retries=1, base_delay=0.25):
        self.primary, self.fallback = primary, fallback
        self.retries, self.base_delay = retries, base_delay

    async def decide(self, context, tools):
        last = None
        for model in (self.primary, self.fallback):
            for attempt in range(self.retries+1):
                try:
                    return await model.decide(context, tools)
                except (httpx.TimeoutException, httpx.TransportError, ModelError, httpx.HTTPStatusError) as exc:
                    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code != 429 and exc.response.status_code < 500:
                        raise
                    last = exc
                    if attempt < self.retries:
                        await asyncio.sleep(self.base_delay*2**attempt + random.uniform(0, self.base_delay))
        raise ModelError("All model providers failed") from last
