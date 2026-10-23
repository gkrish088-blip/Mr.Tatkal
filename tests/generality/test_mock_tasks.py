from fastapi.testclient import TestClient
from mock.mock_tasks.app import app, records


def test_local_research_and_contact_fixture():
    records.clear()
    with TestClient(app) as client:
        page = client.get('/').text
        assert 'The library opens at 09:30 on Tuesday.' in page
        assert client.post('/messages', json={'name': 'Fictional Reader', 'message': 'Opens Tuesday 09:30'}).json()['saved']
        assert client.get('/messages').json() == [{'name': 'Fictional Reader', 'message': 'Opens Tuesday 09:30'}]
