# NetPulse — Network Automation & Monitoring Platform

A portfolio MVP for managing network device inventory, running **on-demand TCP connectivity checks**, viewing check history, and storing configuration snapshots through a Flask REST API and browser dashboard.

> **Status:** Prototype. Source code is published, but automated tests and live deployment have not yet been verified. Not production-ready.

## Features
- Register and delete devices using IPv4/IPv6 addresses and TCP ports.
- Check whether a TCP connection to a device succeeds (not ICMP ping).
- View last-known device status, response time, and recent check history.
- Store and retrieve configuration text snapshots (never executed on devices).
- See inventory counts on a responsive web dashboard.
- SQLite persistence, REST endpoints, and Pytest test cases.

## Architecture

```text
Browser dashboard (HTML/CSS/JS)
          |
          v
Flask REST API (Python)
    |            |
    v            v
SQLite DB    TCP socket checks
```

## Technology
Python 3, Flask, SQLite, HTML/CSS/JavaScript, Pytest, Docker.

## Local setup

```bash
git clone https://github.com/sriramreddy42/netpulse-network-monitor.git
cd netpulse-network-monitor
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Open **http://127.0.0.1:5000**.

To run tests:

```bash
python -m pytest -v
```

## Docker

```bash
docker build -t netpulse .
docker run --rm -p 5000:5000 netpulse
```

The Dockerfile sets `DATABASE_PATH=/data/network.db`. Mount a writable volume at `/data` for persistent data.

## REST API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/` | Dashboard |
| GET | `/api/health` | API health |
| GET | `/api/summary` | Status counts |
| GET | `/api/devices` | List devices |
| POST | `/api/devices` | Add a device |
| DELETE | `/api/devices/{id}` | Delete a device |
| POST | `/api/devices/{id}/check` | Run TCP check |
| GET | `/api/devices/{id}/checks` | Recent checks |
| GET | `/api/devices/{id}/configurations` | Stored snapshots |
| POST | `/api/devices/{id}/configurations` | Save a snapshot |

Example:

```bash
curl -X POST http://127.0.0.1:5000/api/devices \
  -H 'Content-Type: application/json' \
  -d '{"name":"lab-router","host":"192.0.2.10","port":22,"location":"Lab"}'
```

The example IP is reserved for documentation and will not generally be reachable.

## Important security limitations

This is a **local-only educational prototype**, not a safe public network-scanning service. It has **no authentication**, authorization, rate limiting, or restrictions on target IP addresses. **Do not expose it to the public internet** without adding these controls; only check systems you own or are authorized to test. Stored configuration snapshots may contain sensitive information—do not store credentials or secrets.

## Planned improvements
- Mock/demo device mode for a publicly accessible portfolio demo.
- Authentication, authorization, and restricted monitoring targets.
- Scheduled checks and alert notifications.
- CI tests, PostgreSQL, and production-ready deployment.
- Improved configuration snapshot comparison.

## Resume summary

**NetPulse — Network Automation & Monitoring Platform:** Built a Python/Flask prototype with REST endpoints, SQLite-backed device inventory, on-demand TCP reachability checks, monitoring history, configuration snapshot storage, and a responsive dashboard.

## License
No license has been selected yet. All rights reserved by default.
