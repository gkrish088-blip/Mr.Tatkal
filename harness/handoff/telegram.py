"""Telegram transport; constructed only when explicitly configured by the operator."""
import asyncio
import json
from pathlib import Path
import httpx
from .channel import atomic_json


class TelegramTransport:
    def __init__(self, token, chat_id, client=None, state_path=None):
        self._base = f"https://api.telegram.org/bot{token}"
        self.chat_id = str(chat_id)
        self.client = client or httpx.AsyncClient(timeout=20)
        self.state_path = Path(state_path) if state_path else None
        self.offset = json.loads(self.state_path.read_text())["offset"] if self.state_path and self.state_path.exists() else 0

    async def _request(self, method, endpoint, **kwargs):
        try:
            response = await self.client.request(method, self._base + endpoint, **kwargs)
            response.raise_for_status()
            if not response.json().get("ok"):
                raise RuntimeError("Transport rejected request")
            return response
        except (httpx.HTTPError, ValueError) as error:
            # Never include credential-bearing API URLs in exceptions or run logs.
            raise RuntimeError("Handoff transport request failed") from None

    async def send(self, request):
        text = (f"Request {request['id']} ({request['kind']})\n{request['text']}\n"
                f"Reply: /reply {request['id']} <answer>")
        if request.get("options"):
            text += "\nOptions: " + ", ".join(map(str, request["options"]))
        await self._request("POST", "/sendMessage", json={"chat_id": self.chat_id, "text": text})
        for attachment in request.get("attachments", []):
            with Path(attachment).open("rb") as image:
                await self._request("POST", "/sendPhoto", data={"chat_id": self.chat_id}, files={"photo": image})

    async def poll_once(self, channel, dispatch=None):
        response = await self._request("GET", "/getUpdates", params={"offset": self.offset, "timeout": 0})
        updates = response.json()
        if not updates.get("ok"):
            raise RuntimeError("Reply polling rejected")
        for update in updates.get("result", []):
            next_offset = max(self.offset, update["update_id"] + 1)
            message = update.get("message", {})
            if str(message.get("chat", {}).get("id")) != self.chat_id:
                self.offset = next_offset
                continue
            text = message.get("text", "")
            if text.startswith("/reply "):
                parts = text.split(" ", 2)
                if len(parts) == 3:
                    channel.reply(parts[1], parts[2])
            elif text.startswith("/run ") and dispatch:
                await dispatch(text[5:].strip(), {"trigger": "chat", "update_id": update["update_id"],
                                                  "trigger_id": f"chat:{self.chat_id}:{update['update_id']}"})
            self.offset = next_offset
            if self.state_path:
                atomic_json(self.state_path, {"offset": self.offset})

    async def serve(self, channel, dispatch=None, interval=1):
        while True:
            await self.poll_once(channel, dispatch)
            await asyncio.sleep(interval)

    async def close(self):
        await self.client.aclose()
