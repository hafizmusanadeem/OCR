import React, { useState } from 'react';
import Navbar from './components/Navbar';
import JobsPage from './pages/JobsPage';
import BenchmarksPage from './pages/BenchmarksPage';
import DatasetsPage from './pages/DatasetsPage';

function App() {
  const [page, setPage] = useState('jobs');

  return (
    <div className="App">
      <Navbar page={page} setPage={setPage} />
      <div className="container mt-4">
        {page === 'jobs' && <JobsPage />}
        {page === 'benchmarks' && <BenchmarksPage />}
        {page === 'datasets' && <DatasetsPage />}
      </div>
    </div>
  );
}

export default App;
