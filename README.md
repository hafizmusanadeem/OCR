# OCR Benchmark & Stress Testing Platform

A production-grade distributed OCR evaluation platform designed to benchmark OCR engines across multiple dimensions: accuracy, latency, concurrency, and language support.

## Vision

This platform answers engineering questions such as:

- Can the OCR engine scale?
- How does it perform on 100-page PDFs?
- How accurate is it on RTL languages?
- What happens under concurrent load?
- Which OCR engine performs best?

## Architecture

The project follows a clean, modular architecture with a **plugin-based OCR provider system**:

- **Backend**: FastAPI Python service with structured logging, async task queues, and a pluggable OCR engine interface.
- **Frontend**: React-based dashboard (future milestone) for visualizing jobs, queues, results, and benchmarks.
- **Workers**: Redis-backed Celery/RQ workers for concurrent page processing.
- **Database**: PostgreSQL for persisting jobs, results, and benchmark data.
- **Monitoring**: Prometheus + Grafana for live metrics and alerting.

Key design principles:

- **SOLID** — Every component has a single responsibility; interfaces are abstracted.
- **Clean Architecture** — Business logic is independent of frameworks, UI, and external services.
- **Plugin Architecture** — OCR engines are swappable providers; adding a new engine requires zero backend changes.
- **Horizontal Scaling** — Workers scale independently based on queue depth.

## Milestones

| Milestone | Description | Status |
|-----------|-------------|--------|
| 0 | Repository Setup & Tooling | 🚧 In Progress |
| 1 | FastAPI Backend — Health & Metrics | ⏳ Planned |
| 2 | Plugin Architecture — OCR Provider Interface | ⏳ Planned |
| 3 | First OCR Provider — Mistral OCR | ⏳ Planned |
| 4 | PDF Preprocessing & Page Splitting | ⏳ Planned |
| 5 | Redis Queue & Async Jobs | ⏳ Planned |
| 6 | Multiple Concurrent Workers | ⏳ Planned |
| 7 | Result Aggregation | ⏳ Planned |
| 8 | Database Persistence | ⏳ Planned |
| 9 | Benchmark Module (CER, WER) | ⏳ Planned |
| 10 | Benchmark Datasets | ⏳ Planned |
| 11 | Dashboard Frontend | ⏳ Planned |
| 12 | Monitoring (Prometheus + Grafana) | ⏳ Planned |
| 13 | Stress Testing (Locust) | ⏳ Planned |
| 14 | Failure Recovery & Retries | ⏳ Planned |
| 15 | Horizontal Scaling | ⏳ Planned |
| 16 | RTL Evaluation | ⏳ Planned |
| 17 | OCR Engine Comparison Leaderboard | ⏳ Planned |
| 18 | Report Generation (MD, HTML, PDF) | ⏳ Planned |

## Project Structure

```
ocr-benchmark-platform/
├── .github/
│   └── workflows/          # CI/CD pipelines
├── backend/
│   ├── src/ocr_platform/     # Main Python package
│   │   ├── __init__.py
│   │   ├── config.py         # Pydantic settings & env parsing
│   │   └── logging_config.py # Structured logging setup
│   ├── tests/                # Unit & integration tests
│   ├── Dockerfile            # Backend container image
│   ├── pyproject.toml        # Python tooling configuration
│   └── requirements.txt      # Python dependencies
├── frontend/                 # React dashboard (future)
├── docker-compose.yml        # Local development orchestration
├── Makefile                  # Convenience commands
├── pyproject.toml            # Root project metadata
└── README.md                 # This file
```

## Getting Started

### Prerequisites

- Docker & Docker Compose
- Python 3.12+ (for local development)
- Make (optional, for convenience commands)

### Quick Start

```bash
# 1. Clone the repository
git clone <repository-url>
cd ocr-benchmark-platform

# 2. Copy environment configuration
cp .env.example .env

# 3. Start the development stack
docker compose up --build

# 4. Verify the backend (once Milestone 1 is complete)
curl http://localhost:8000/health
```

### Local Development

```bash
# Create a virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install backend dependencies
pip install -r backend/requirements.txt
pip install -r backend/requirements-dev.txt

# Run linting and formatting
make lint
make format
make typecheck

# Run tests
make test

# Start the backend (Milestone 1+)
make dev
```

## Makefile Commands

| Command | Description |
|---------|-------------|
| `make build` | Build Docker images |
| `make up` | Start the full stack with Docker Compose |
| `make down` | Stop the full stack |
| `make dev` | Start the backend in local development mode |
| `make test` | Run all tests with pytest |
| `make lint` | Run Ruff linter |
| `make format` | Run Black formatter and Ruff auto-fix |
| `make typecheck` | Run MyPy type checker |
| `make clean` | Remove build artifacts and cache |
| `make all` | Run format, lint, typecheck, and test |

## Tooling

- **Ruff** — Ultra-fast Python linter and code formatter
- **Black** — Opinionated Python code formatter
- **MyPy** — Static type checker
- **Pytest** — Testing framework with coverage support
- **Pre-commit** — Git hooks for running checks before commits
- **Docker** — Containerization for consistent environments
- **Docker Compose** — Local multi-service orchestration

## License

MIT
