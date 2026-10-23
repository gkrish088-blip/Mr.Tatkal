"""CLI/chat commands feed the same goal dispatcher as all other triggers."""
import asyncio


async def command(text, dispatch, source="cli"):
    text = text.strip()
    if text.startswith("/run "):
        text = text[5:].strip()
    if not text:
        raise ValueError("A goal is required")
    return await dispatch(text, {"trigger": "chat", "source": source})


async def serve(dispatch):
    while True:
        try:
            text = await asyncio.to_thread(input, "goal> ")
        except EOFError:
            return
        if text.strip() in {"quit", "exit"}:
            return
        if text.strip():
            await command(text, dispatch)
