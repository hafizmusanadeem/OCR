const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';

async function fetchJson(url) {
  const res = await fetch(`${API_BASE}${url}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function getJobs() {
  return fetchJson('/jobs');
}

export async function getJob(jobId) {
  return fetchJson(`/jobs/${jobId}`);
}

export async function getBenchmarks() {
  return fetchJson('/benchmarks');
}

export async function getBenchmark(benchmarkId) {
  return fetchJson(`/benchmarks/${benchmarkId}`);
}

export async function getBenchmarkLeaderboard(benchmarkId) {
  return fetchJson(`/benchmarks/${benchmarkId}/leaderboard`);
}

export async function runBenchmark(data) {
  const res = await fetch(`${API_BASE}/benchmarks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function getDatasets() {
  return fetchJson('/datasets');
}

export async function getDataset(datasetId) {
  return fetchJson(`/datasets/${datasetId}`);
}

export async function getHealth() {
  return fetchJson('/health');
}
