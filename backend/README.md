# OCR Benchmark Platform — Backend

Backend service for the OCR Benchmark & Stress Testing Platform.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt
pip install -e .

# Run tests
pytest tests/ -v

# Run linting
ruff check src/ tests/
black --check src/ tests/
mypy src/ tests/
```
