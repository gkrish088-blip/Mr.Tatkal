import argparse
from pathlib import Path
import uvicorn
from harness.web.settings import Settings


def main():
    parser=argparse.ArgumentParser(description='Start the single-worker agent GUI server')
    parser.add_argument('--host');parser.add_argument('--port',type=int);parser.add_argument('--env',default='.env')
    args=parser.parse_args()
    env=Path(args.env)
    template=Path('.env.example')
    if not env.exists() and template.exists(): env.write_bytes(template.read_bytes())
    settings=Settings.from_env(args.env)
    if args.host: settings.host=args.host
    if args.port:
        settings.port=args.port;settings.internal_url=f'http://127.0.0.1:{args.port}'
    settings.validate()
    from harness.web.app import create_app
    uvicorn.run(create_app(settings),host=settings.host,port=settings.port,workers=1)


if __name__=='__main__': main()
