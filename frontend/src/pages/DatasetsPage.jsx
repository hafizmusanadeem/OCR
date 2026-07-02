import React, { useEffect, useState } from 'react';
import { getDatasets, getDataset } from '../services/api';

function DatasetsPage() {
  const [datasets, setDatasets] = useState([]);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await getDatasets();
        setDatasets(data.datasets || []);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  async function showDetail(datasetId) {
    try {
      const data = await getDataset(datasetId);
      setDetail(data.dataset);
      setSelected(datasetId);
    } catch (err) {
      setError(err.message);
    }
  }

  if (loading) return <div className="alert alert-info">Loading...</div>;
  if (error) return <div className="alert alert-danger">Error: {error}</div>;

  return (
    <div>
      <h2>Datasets</h2>
      <div className="row">
        {datasets.map((ds) => (
          <div className="col-md-4 mb-3" key={ds.id}>
            <div className={`card ${selected === ds.id ? 'border-primary' : ''}`}>
              <div className="card-body">
                <h5 className="card-title">{ds.name}</h5>
                <p className="card-text text-muted">{ds.description}</p>
                <p className="card-text">
                  <span className="badge bg-secondary">{ds.category}</span>{' '}
                  <span className="badge bg-info">{ds.language}</span>
                </p>
                <p className="card-text">Pages: {ds.page_count} | Chars: {ds.total_characters} | Words: {ds.total_words}</p>
                <button className="btn btn-sm btn-outline-primary" onClick={() => showDetail(ds.id)}>
                  View Ground Truth
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {detail && (
        <div className="card mt-3">
          <div className="card-header">{detail.name} — Ground Truth</div>
          <div className="card-body">
            {detail.pages.map((page) => (
              <div className="mb-3" key={page.page_number}>
                <h6>Page {page.page_number}</h6>
                <p className="font-monospace bg-light p-2 rounded">{page.ground_truth}</p>
                {page.tags.length > 0 && (
                  <p>
                    {page.tags.map((tag) => (
                      <span className="badge bg-light text-dark me-1" key={tag}>{tag}</span>
                    ))}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default DatasetsPage;
