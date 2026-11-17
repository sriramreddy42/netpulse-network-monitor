import pytest
from app import create_app

@pytest.fixture
def client(tmp_path):
    app = create_app({'TESTING': True, 'DATABASE_PATH': str(tmp_path / 'test.db')})
    return app.test_client()

def test_health(client):
    assert client.get('/api/health').json['status'] == 'ok'

def test_device_lifecycle(client):
    created = client.post('/api/devices', json={'name':'Router 1','host':'192.0.2.10','port':22})
    assert created.status_code == 201
    device_id = created.json['id']
    assert client.get('/api/summary').json['unchecked'] == 1
    assert len(client.get('/api/devices').json) == 1
    assert client.post('/api/devices', json={'name':'Duplicate','host':'192.0.2.10'}).status_code == 409
    assert client.post(f'/api/devices/{device_id}/configurations', json={'content':'interface eth0'}).status_code == 201
    assert len(client.get(f'/api/devices/{device_id}/configurations').json) == 1
    assert client.delete(f'/api/devices/{device_id}').status_code == 204
    assert client.get('/api/summary').json['total'] == 0

def test_invalid_device(client):
    assert client.post('/api/devices', json={'name':'bad','host':'not-a-host'}).status_code == 400
    assert client.post('/api/devices', json={'name':'bad','host':'192.0.2.2','port':99999}).status_code == 400

def test_missing_device(client):
    assert client.post('/api/devices/999/check').status_code == 404
    assert client.get('/api/devices/999/checks').status_code == 404
