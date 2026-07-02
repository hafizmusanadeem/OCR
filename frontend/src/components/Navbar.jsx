import React from 'react';

function Navbar({ page, setPage }) {
  const links = [
    { id: 'jobs', label: 'Jobs' },
    { id: 'benchmarks', label: 'Benchmarks' },
    { id: 'datasets', label: 'Datasets' },
  ];

  return (
    <nav className="navbar navbar-expand-lg navbar-dark bg-dark">
      <div className="container">
        <span className="navbar-brand">OCR Benchmark Platform</span>
        <div className="collapse navbar-collapse">
          <ul className="navbar-nav me-auto">
            {links.map((link) => (
              <li className="nav-item" key={link.id}>
                <button
                  className={`nav-link btn btn-link ${page === link.id ? 'active' : ''}`}
                  onClick={() => setPage(link.id)}
                >
                  {link.label}
                </button>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </nav>
  );
}

export default Navbar;
