import Dashboard from './components/Dashboard';

const styles = `
  * {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }

  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen,
      Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
    background: #f5f7fa;
    color: #1a1a2e;
    line-height: 1.6;
  }

  .dashboard {
    max-width: 1400px;
    margin: 0 auto;
    padding: 20px;
  }

  .dashboard-header {
    text-align: center;
    padding: 30px 20px;
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    color: white;
    border-radius: 12px;
    margin-bottom: 30px;
  }

  .dashboard-header h1 {
    font-size: 2.5rem;
    font-weight: 700;
    margin-bottom: 8px;
  }

  .dashboard-header .subtitle {
    opacity: 0.8;
    font-size: 1.1rem;
  }

  .dashboard-main {
    display: grid;
    grid-template-columns: 1fr 350px;
    gap: 24px;
  }

  @media (max-width: 1024px) {
    .dashboard-main {
      grid-template-columns: 1fr;
    }
  }

  .chart-section {
    background: white;
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  }

  .sidebar {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  /* Category Selector */
  .category-selector {
    margin-bottom: 24px;
  }

  .category-selector label {
    display: block;
    font-weight: 600;
    margin-bottom: 8px;
    color: #374151;
  }

  .category-selector select {
    width: 100%;
    padding: 12px 16px;
    border: 2px solid #e5e7eb;
    border-radius: 8px;
    font-size: 15px;
    background: white;
    cursor: pointer;
    transition: border-color 0.2s;
  }

  .category-selector select:focus {
    outline: none;
    border-color: #2563eb;
  }

  /* Trend Chart */
  .trend-chart {
    min-height: 450px;
  }

  .trend-chart.empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: #6b7280;
    text-align: center;
  }

  .trend-chart.loading {
    display: flex;
    align-items: center;
    justify-content: center;
    color: #6b7280;
  }

  .stats-header {
    margin-bottom: 20px;
    padding-bottom: 16px;
    border-bottom: 1px solid #e5e7eb;
  }

  .stats-header h3 {
    font-size: 1.3rem;
    color: #1a1a2e;
    margin-bottom: 12px;
  }

  .stats-summary {
    display: flex;
    gap: 24px;
    flex-wrap: wrap;
  }

  .stats-summary .stat {
    font-size: 14px;
    color: #4b5563;
  }

  .stats-summary .stat strong {
    color: #1a1a2e;
  }

  .stat.trend-rising { color: #16a34a; }
  .stat.trend-growing { color: #65a30d; }
  .stat.trend-declining { color: #dc2626; }
  .stat.trend-cooling { color: #ea580c; }
  .stat.trend-stable { color: #6b7280; }

  /* Hype Indicator */
  .hype-indicator {
    background: white;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  }

  .hype-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
  }

  .hype-header h2 {
    font-size: 1.2rem;
    color: #1a1a2e;
  }

  .refresh-btn {
    padding: 6px 14px;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    background: white;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;
  }

  .refresh-btn:hover {
    background: #f3f4f6;
    border-color: #d1d5db;
  }

  .hype-lists {
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  .category-list h3 {
    font-size: 14px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #6b7280;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 2px solid #e5e7eb;
  }

  .category-list.rising h3 {
    color: #16a34a;
    border-color: #16a34a;
  }

  .category-list.declining h3 {
    color: #dc2626;
    border-color: #dc2626;
  }

  .category-list ul {
    list-style: none;
  }

  .category-list li {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 12px;
    border-radius: 8px;
    margin-bottom: 4px;
    transition: background 0.2s;
  }

  .category-list li:hover {
    background: #f3f4f6;
  }

  .category-info {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .category-id {
    font-weight: 600;
    font-size: 14px;
    color: #1a1a2e;
  }

  .category-name {
    font-size: 12px;
    color: #6b7280;
  }

  .no-data {
    color: #9ca3af;
    font-size: 14px;
    text-align: center;
    padding: 20px;
  }

  .error {
    color: #dc2626;
    text-align: center;
    padding: 20px;
  }
`;

function App() {
  return (
    <>
      <style>{styles}</style>
      <Dashboard />
    </>
  );
}

export default App;
