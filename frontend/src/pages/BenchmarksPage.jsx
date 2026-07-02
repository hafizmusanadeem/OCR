import React, { useEffect, useState } from 'react';
import { getBenchmarks, getBenchmarkLeaderboard, runBenchmark } from '../services/api';

function BenchmarksPage() {
  const [benchmarks, setBenchmarks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(null);
  const [leaderboard, setLeaderboard] = useState(null);
  const [lbLoading, setLbLoading] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const data = await getBenchmarks();
        setBenchmarks(data.benchmarks || []);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  async function showLeaderboard(benchmarkId) {
    setLbLoading(true);
    try {
      const data = await getBenchmarkLeaderboard(benchmarkId);
      setLeaderboard(data);
      setSelected(benchmarkId);
    } catch (err) {
      setError(err.message);
    } finally {
      setLbLoading(false);
    }
  }

  async function runDemoBenchmark() {
    try {
      setLoading(true);
      await runBenchmark({
        dataset_name: 'english',
        engines: ['mock'],
        pages: [
          {
            page_number: 1,
            ground_truth: 'Hello world',
            hypotheses: { mock: { text: 'Hello world', confidence: 0.99, latency_ms: 10 } },
          },
        ],
      });
      const data = await getBenchmarks();
      setBenchmarks(data.benchmarks || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (loading) return <div className="alert alert-info">Loading...</div>;
  if (error) return <div className="alert alert-danger">Error: {error}</div>;

  return (
    <div>
      <h2>Benchmarks</h2>
      <button className="btn btn-primary mb-3" onClick={runDemoBenchmark}>
        Run Demo Benchmark
      </button>

      <table className="table table-striped">
        <thead>
          <tr>
            <th>Benchmark ID</th>
            <th>Dataset</th>
            <th>Status</th>
            <th>Created</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {benchmarks.length === 0 && (
            <tr><td colSpan="5" className="text-center text-muted">No benchmarks yet</td></tr>
          )}
          {benchmarks.map((b) => (
            <tr key={b.benchmark_id}>
              <td><code>{b.benchmark_id}</code></td>
              <td>{b.dataset_name}</td>
              <td>
                <span className={`badge bg-${b.status === 'completed' ? 'success' : b.status === 'failed' ? 'danger' : 'warning'}`}>
                  {b.status}
                </span>
              </td>
              <td>{new Date(b.created_at).toLocaleString()}</td>
              <td>
                <button
                  className="btn btn-sm btn-outline-primary"
                  onClick={() => showLeaderboard(b.benchmark_id)}
                  disabled={b.status !== 'completed' || lbLoading}
                >
                  Leaderboard
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {selected && leaderboard && (
        <div className="card mt-3">
          <div className="card-header">Leaderboard: {leaderboard.dataset_name}</div>
          <div className="card-body">
            <p>Best Engine: <strong>{leaderboard.best_engine}</strong></p>
            <p>Total Pages: {leaderboard.total_pages} | Total Engines: {leaderboard.total_engines}</p>
            <table className="table table-sm">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Engine</th>
                  <th>Avg Accuracy</th>
                  <th>Avg CER</th>
                  <th>Avg WER</th>
                  <th>Avg Confidence</th>
                  <th>Avg Latency (ms)</th>
                </tr>
              </thead>
              <tbody>
                {leaderboard.leaderboard.map((score, idx) => (
                  <tr key={score.engine}>
                    <td>{idx + 1}</td>
                    <td>{score.engine}</td>
                    <td>{(score.average_accuracy * 100).toFixed(2)}%</td>
                    <td>{(score.average_cer * 100).toFixed(2)}%</td>
                    <td>{(score.average_wer * 100).toFixed(2)}%</td>
                    <td>{score.average_confidence != null ? (score.average_confidence * 100).toFixed(2) + '%' : 'N/A'}</td>
                    <td>{score.average_latency_ms != null ? score.average_latency_ms.toFixed(1) : 'N/A'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

export default BenchmarksPage;
