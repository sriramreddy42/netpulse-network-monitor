import os
import sqlite3
import socket
import ipaddress
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, jsonify, request, render_template

BASE = Path(__file__).resolve().parent
DB = Path(os.environ.get('DATABASE_PATH', str(BASE / 'network.db')))

def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(DATABASE_PATH=str(DB), TESTING=False)
    if test_config:
        app.config.update(test_config)

    def connect():
        con = sqlite3.connect(app.config['DATABASE_PATH'])
        con.row_factory = sqlite3.Row
        return con

    def initialize():
        with connect() as con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS devices (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL, host TEXT NOT NULL UNIQUE,
                  port INTEGER NOT NULL DEFAULT 22,
                  location TEXT NOT NULL DEFAULT '',
                  created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS checks (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  device_id INTEGER NOT NULL REFERENCES devices(id),
                  status TEXT NOT NULL, latency_ms REAL,
                  message TEXT NOT NULL, checked_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS configurations (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  device_id INTEGER NOT NULL REFERENCES devices(id),
                  content TEXT NOT NULL, created_at TEXT NOT NULL
                );
            """)

    initialize()

    def device_with_status(con, row):
        result = dict(row)
        check = con.execute('SELECT status, latency_ms, message, checked_at FROM checks WHERE device_id=? ORDER BY id DESC LIMIT 1', (row['id'],)).fetchone()
        result['latest_check'] = dict(check) if check else None
        return result

    @app.get('/')
    def home():
        return render_template('index.html')

    @app.get('/api/health')
    def health():
        return jsonify({'service': 'network-monitor', 'status': 'ok', 'timestamp': utcnow()})

    @app.get('/api/devices')
    def list_devices():
        with connect() as con:
            rows = con.execute('SELECT * FROM devices ORDER BY id DESC').fetchall()
            return jsonify([device_with_status(con, row) for row in rows])

    @app.post('/api/devices')
    def add_device():
        data = request.get_json(silent=True) or {}
        name = str(data.get('name', '')).strip()
        host = str(data.get('host', '')).strip()
        location = str(data.get('location', '')).strip()
        try:
            port = int(data.get('port', 22))
            ipaddress.ip_address(host)
        except (ValueError, TypeError):
            return jsonify({'error': 'host must be a valid IPv4/IPv6 address and port an integer'}), 400
        if not name or len(name) > 100 or len(location) > 100 or not 1 <= port <= 65535:
            return jsonify({'error': 'Invalid name, location, or port'}), 400
        try:
            with connect() as con:
                cur = con.execute('INSERT INTO devices (name,host,port,location,created_at) VALUES (?,?,?,?,?)', (name, host, port, location, utcnow()))
                return jsonify({'id': cur.lastrowid, 'name': name, 'host': host, 'port': port, 'location': location}), 201
        except sqlite3.IntegrityError:
            return jsonify({'error': 'Device IP already exists'}), 409

    @app.delete('/api/devices/<int:device_id>')
    def delete_device(device_id):
        with connect() as con:
            exists = con.execute('SELECT id FROM devices WHERE id=?', (device_id,)).fetchone()
            if not exists:
                return jsonify({'error': 'Device not found'}), 404
            con.execute('DELETE FROM checks WHERE device_id=?', (device_id,))
            con.execute('DELETE FROM configurations WHERE device_id=?', (device_id,))
            con.execute('DELETE FROM devices WHERE id=?', (device_id,))
        return '', 204

    def run_check(con, device):
        import time
        started = time.monotonic()
        try:
            with socket.create_connection((device['host'], device['port']), timeout=1.5):
                pass
            status, message = 'up', 'TCP connection succeeded'
        except OSError as exc:
            status, message = 'down', f'TCP connection failed: {type(exc).__name__}'
        latency = round((time.monotonic() - started) * 1000, 2)
        timestamp = utcnow()
        con.execute('INSERT INTO checks (device_id,status,latency_ms,message,checked_at) VALUES (?,?,?,?,?)', (device['id'], status, latency, message, timestamp))
        return {'device_id': device['id'], 'status': status, 'latency_ms': latency, 'message': message, 'checked_at': timestamp}

    @app.post('/api/devices/<int:device_id>/check')
    def check_device(device_id):
        with connect() as con:
            device = con.execute('SELECT * FROM devices WHERE id=?', (device_id,)).fetchone()
            if not device:
                return jsonify({'error': 'Device not found'}), 404
            return jsonify(run_check(con, device))

    @app.get('/api/devices/<int:device_id>/checks')
    def check_history(device_id):
        with connect() as con:
            if not con.execute('SELECT id FROM devices WHERE id=?', (device_id,)).fetchone():
                return jsonify({'error': 'Device not found'}), 404
            return jsonify([dict(r) for r in con.execute('SELECT * FROM checks WHERE device_id=? ORDER BY id DESC LIMIT 50', (device_id,))])

    @app.get('/api/summary')
    def summary():
        with connect() as con:
            rows = con.execute("""SELECT d.id, (SELECT status FROM checks c WHERE c.device_id=d.id ORDER BY c.id DESC LIMIT 1) AS status FROM devices d""").fetchall()
            statuses = [r['status'] for r in rows]
            return jsonify({'total': len(rows), 'up': statuses.count('up'), 'down': statuses.count('down'), 'unchecked': statuses.count(None)})

    @app.get('/api/devices/<int:device_id>/configurations')
    def configurations(device_id):
        with connect() as con:
            if not con.execute('SELECT id FROM devices WHERE id=?', (device_id,)).fetchone():
                return jsonify({'error': 'Device not found'}), 404
            return jsonify([dict(r) for r in con.execute('SELECT * FROM configurations WHERE device_id=? ORDER BY id DESC LIMIT 20', (device_id,))])

    @app.post('/api/devices/<int:device_id>/configurations')
    def add_configuration(device_id):
        data = request.get_json(silent=True) or {}
        content = data.get('content')
        if not isinstance(content, str) or not content.strip() or len(content) > 10000:
            return jsonify({'error': 'content must be a nonempty string (max 10000 characters)'}), 400
        with connect() as con:
            if not con.execute('SELECT id FROM devices WHERE id=?', (device_id,)).fetchone():
                return jsonify({'error': 'Device not found'}), 404
            cur = con.execute('INSERT INTO configurations (device_id,content,created_at) VALUES (?,?,?)', (device_id, content, utcnow()))
            return jsonify({'id': cur.lastrowid, 'device_id': device_id, 'created_at': utcnow()}), 201

    return app

app = create_app()
if __name__ == '__main__':
    app.run(host='127.0.0.1', port=int(os.environ.get('PORT', 5000)), debug=False)
