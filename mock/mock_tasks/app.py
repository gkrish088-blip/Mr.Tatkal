from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title='Local generality fixtures')
records = []


@app.get('/', response_class=HTMLResponse)
async def index():
    return '''<!doctype html><html lang="en"><title>Community desk</title><h1>Community desk</h1>
    <p id="fact">The library opens at 09:30 on Tuesday.</p><h2>Contact form</h2>
    <form id="contact"><label>Name <input name="name" required></label>
    <label>Message <textarea name="message" required></textarea></label><button>Save message</button></form>
    <p role="status" id="status"></p><script>document.querySelector('form').onsubmit=async e=>{e.preventDefault();
    const r=await fetch('/messages',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(Object.fromEntries(new FormData(e.target)))});
    document.querySelector('#status').textContent=r.ok?'Message saved':'Could not save'};</script></html>'''


@app.post('/messages')
async def save(data: dict):
    records.append({'name': str(data.get('name', '')), 'message': str(data.get('message', ''))})
    return {'saved': True}


@app.get('/messages')
async def messages():
    return records
