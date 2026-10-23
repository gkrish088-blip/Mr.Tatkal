"""Domain-specific GUI test plugin, kept outside the generic harness."""
import httpx
from mock.mock_irctc.app import create_app


class DemoPlugin:
    def __init__(self): self.apps={}

    def exists(self, run_id): return run_id in self.apps

    def prepare(self, run_id, base_url):
        self.apps.setdefault(run_id,create_app())
        return {'skill':'mock-ticket','inputs':{'url':base_url.rstrip('/')+'/lab/'+run_id+'/',
                 'date':'2026-10-26','name':'Fictional Rider','age':'28','age_number':28,
                 'gender':'Female','nationality':'Indian','mobile':'9000000000'}}

    async def approve(self, run_id):
        if run_id not in self.apps: raise ValueError('Local test service has restarted')
        app=self.apps[run_id]
        pending=[key for key,value in app.state.lab['reservations'].items() if value['status']=='pending']
        if len(pending)!=1: raise ValueError('Expected one fictional payment request')
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://localhost') as client:
            response=await client.post('/api/test/approve/'+pending[0])
            response.raise_for_status()

    async def __call__(self, scope, receive, send):
        # Mounted at /lab; isolate each test's mock cookies/API path and in-memory state.
        from starlette.responses import PlainTextResponse
        prefix=scope.get('root_path','')
        path=scope['path'][len(prefix):].lstrip('/')
        run_id=path.split('/',1)[0]
        app=self.apps.get(run_id)
        if not app:
            await PlainTextResponse('Local test not found',status_code=404)(scope,receive,send);return
        scope=dict(scope,root_path=prefix+'/'+run_id)
        # Mock UI uses /api/...; rewrite relative requests to its session namespace.
        if path in {run_id,run_id+'/'}:
            from pathlib import Path
            from fastapi.responses import HTMLResponse
            html=Path(__file__).parent.joinpath('mock_irctc/index.html').read_text(encoding='utf-8')
            html=html.replace('__VARIANT__','0').replace('__POPUP__','false')
            html=html.replace("fetch('/api/'", "fetch('"+prefix+'/'+run_id+"/api/'")
            # Avoid sessionStorage collision across separate demo runs.
            html=html.replace("'lab'",repr('lab-'+run_id))
            await HTMLResponse(html)(scope,receive,send);return
        await app(scope,receive,send)
