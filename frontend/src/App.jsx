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

  /* Sync Progress */
  .sync-progress {
    margin-top: 20px;
    padding: 16px 24px;
    background: rgba(255,255,255,0.1);
    border-radius: 10px;
    max-width: 450px;
    margin-left: auto;
    margin-right: auto;
  }

  .sync-progress-header {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 600;
    margin-bottom: 12px;
  }

  .sync-status-dot {
    width: 10px;
    height: 10px;
    background: #22c55e;
    border-radius: 50%;
    animation: pulse 1.5s infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }

  .sync-progress-details {
    display: flex;
    justify-content: space-between;
    font-size: 13px;
    opacity: 0.9;
    margin-bottom: 10px;
  }

  .sync-message {
    font-family: monospace;
  }

  .sync-progress-bar {
    height: 8px;
    background: rgba(255,255,255,0.2);
    border-radius: 4px;
    overflow: hidden;
  }

  .sync-progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #22c55e 0%, #16a34a 100%);
    border-radius: 4px;
    transition: width 0.5s ease;
  }

  .sync-percentage {
    text-align: center;
    margin-top: 8px;
    font-size: 12px;
    opacity: 0.8;
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

  .stat.trend-surging { color: #059669; font-weight: bold; }
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

  /* Tab Navigation */
  .tab-nav {
    display: flex;
    gap: 4px;
    background: #f3f4f6;
    padding: 4px;
    border-radius: 10px;
    margin-bottom: 24px;
  }

  .tab-btn {
    flex: 1;
    padding: 12px 20px;
    border: none;
    background: transparent;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 500;
    color: #6b7280;
    cursor: pointer;
    transition: all 0.2s;
  }

  .tab-btn:hover {
    color: #1a1a2e;
  }

  .tab-btn.active {
    background: white;
    color: #1a1a2e;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  }

  /* Report Viewer */
  .report-viewer {
    background: white;
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    min-height: 600px;
  }

  .report-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
    padding-bottom: 16px;
    border-bottom: 1px solid #e5e7eb;
  }

  .report-header h2 {
    font-size: 1.3rem;
    color: #1a1a2e;
  }

  .report-content {
    font-size: 14px;
    line-height: 1.7;
  }

  .report-content h1 {
    font-size: 1.8rem;
    margin-bottom: 16px;
    color: #1a1a2e;
  }

  .report-content h2 {
    font-size: 1.4rem;
    margin-top: 32px;
    margin-bottom: 16px;
    color: #1a1a2e;
  }

  .report-content h3 {
    font-size: 1.1rem;
    margin-top: 24px;
    margin-bottom: 12px;
    color: #374151;
  }

  .report-content p {
    margin-bottom: 12px;
    color: #4b5563;
  }

  .report-content ul, .report-content ol {
    margin-left: 20px;
    margin-bottom: 12px;
  }

  .report-content li {
    margin-bottom: 4px;
  }

  .report-content table {
    width: 100%;
    border-collapse: collapse;
    margin: 16px 0;
    font-size: 13px;
  }

  .report-content th {
    background: #f9fafb;
    padding: 10px 12px;
    text-align: left;
    border-bottom: 2px solid #e5e7eb;
    font-weight: 600;
    color: #374151;
  }

  .report-content td {
    padding: 8px 12px;
    border-bottom: 1px solid #e5e7eb;
  }

  .report-content tr:hover {
    background: #f9fafb;
  }

  .report-content code {
    background: #f3f4f6;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: monospace;
    font-size: 13px;
  }

  .report-content pre {
    background: #1a1a2e;
    color: #e5e7eb;
    padding: 16px;
    border-radius: 8px;
    overflow-x: auto;
    margin: 16px 0;
  }

  .report-content pre code {
    background: none;
    padding: 0;
    color: inherit;
  }

  .report-content blockquote {
    border-left: 4px solid #2563eb;
    margin: 16px 0;
    padding: 12px 20px;
    background: #f0f9ff;
    color: #1e40af;
  }

  .report-content strong {
    color: #1a1a2e;
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
