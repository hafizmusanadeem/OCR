import React, { useEffect, useState } from 'react';
import { getJobs, getHealth } from '../services/api';

function JobsPage() {
  const [jobs, setJobs] = useState([]);
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function load() {
      try {
        const [jobsData, healthData] = await Promise.all([
          getJobs(),
          getHealth(),
        ]);
        setJobs(jobsData.jobs || []);
        setHealth(healthData);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) return <div className="alert alert-info">Loading...</div>;
  if (error) return <div className="alert alert-danger">Error: {error}</div>;

  return (
    <div>
      <h2>Jobs</h2>
      <div className="row mb-3">
        <div className="col">
          <div className="card">
            <div className="card-body">
              <h5 className="card-title">API Health</h5>
              <p className="card-text">
                Status: <span className={health?.status === 'ok' ? 'text-success' : 'text-danger'}>{health?.status || 'unknown'}</span>
              </p>
            </div>
          </div>
        </div>
        <div className="col">
          <div className="card">
            <div className="card-body">
              <h5 className="card-title">Total Jobs</h5>
              <p className="card-text fs-4">{jobs.length}</p>
            </div>
          </div>
        </div>
      </div>

      <table className="table table-striped">
        <thead>
          <tr>
            <th>Job ID</th>
            <th>Document Type</th>
            <th>Pages</th>
            <th>Status</th>
            <th>Created</th>
          </tr>
        </thead>
        <tbody>
          {jobs.length === 0 && (
            <tr><td colSpan="5" className="text-center text-muted">No jobs yet</td></tr>
          )}
          {jobs.map((job) => (
            <tr key={job.job_id}>
              <td><code>{job.job_id}</code></td>
              <td>{job.document_type}</td>
              <td>{job.total_pages}</td>
              <td>
                <span className={`badge bg-${job.status === 'completed' ? 'success' : job.status === 'failed' ? 'danger' : 'warning'}`}>
                  {job.status}
                </span>
              </td>
              <td>{new Date(job.created_at).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default JobsPage;
