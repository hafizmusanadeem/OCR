# OCR Benchmark & Stress Testing Platform — Frontend

React-based dashboard for the OCR Benchmark & Stress Testing Platform.

## Features

- **Jobs page**: View all OCR jobs, their status, and health checks.
- **Benchmarks page**: Run benchmarks, view results, and inspect leaderboards.
- **Datasets page**: Browse available benchmark datasets and inspect ground truth.

## Local development

```bash
npm install
npm run dev
```

The dev server runs on `http://localhost:3000` and proxies `/api` to the backend at `http://localhost:8000`.

## Build

```bash
npm run build
```

Static files are output to `dist/` and served by the Docker image via Nginx.
