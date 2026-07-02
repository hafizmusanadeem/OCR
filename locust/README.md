# Locust Stress Testing

This directory contains Locust load tests for the OCR Benchmark Platform.

## Quick Start

### Install Locust

```bash
pip install locust
```

### Run Locust UI

```bash
locust -f locust/locustfile.py --host http://localhost:8000
```

Open http://localhost:8089 and set the number of users and spawn rate.

### Run Headless (CI/CD)

```bash
locust -f locust/locustfile.py \
  --host http://localhost:8000 \
  --headless -u 100 -r 10 -t 60s \
  --csv=locust/results
```

- `-u 100`: 100 concurrent users
- `-r 10`: 10 users spawned per second
- `-t 60s`: Run for 60 seconds
- `--csv=locust/results`: Export CSV results

## Docker

A locust service can be added to `docker-compose.yml` for containerised load testing.
