"""Render an offline, HTML-escaped run timeline: python -m harness.log.replay RUN_DIR."""
import argparse
from html import escape
import json
from pathlib import Path


def read_events(path):
    log = Path(path) / "run.jsonl"
    if not log.exists():
        return []
    result = []
    lines = log.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        try:
            result.append(json.loads(line))
        except json.JSONDecodeError:
            # Power loss may leave the final JSONL record partially written.
            if index != len(lines) - 1:
                raise
    return result


def build_replay(path):
    path = Path(path).resolve()
    cards = []
    for event in read_events(path):
        pictures = []
        for key in ("before", "after", "screenshot"):
            source = event.get(key)
            if isinstance(source, dict):
                source = source.get("screenshot") or source.get("path")
            if not isinstance(source, str):
                continue
            target = (path / source).resolve()
            if target.is_relative_to(path) and target.suffix.lower() in (".png", ".jpg", ".jpeg") and target.exists():
                pictures.append(f'<figure><figcaption>{key}</figcaption><img loading="lazy" src="{escape(target.relative_to(path).as_posix(), quote=True)}"></figure>')
        cards.append(f'<article><h2>Step {escape(str(event.get("step", "")))}</h2>'
                     f'<p>{escape(str(event.get("reason", "")))}</p>'
                     f'<pre>{escape(json.dumps(event, indent=2, ensure_ascii=False))}</pre>'
                     f'<div class="images">{"".join(pictures)}</div></article>')
    html = ('<!doctype html><html lang="en"><meta charset="utf-8">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; img-src \'self\'; style-src \'unsafe-inline\'">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>Run replay</title><style>body{background:#f1f5f9;color:#17233b;font:16px system-ui;max-width:1100px;margin:40px auto;padding:0 20px}'
            'article{background:white;border-radius:12px;padding:24px;margin:20px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f8fafc;padding:16px}'
            '.images{display:flex;flex-wrap:wrap;gap:12px}figure{margin:0;flex:1;min-width:250px}img{max-width:100%}figcaption{font-weight:bold}</style>'
            f'<h1>Run {escape(path.name)}</h1>{"".join(cards)}</html>')
    (path / "replay.html").write_text(html, encoding="utf-8")
    return path / "replay.html"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir")
    print(build_replay(parser.parse_args().run_dir))
