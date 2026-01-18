import { useState, useEffect } from 'react';
import CategorySelector from './CategorySelector';
import TrendChart from './TrendChart';
import HypeIndicator from './HypeIndicator';
import { getSyncStatus } from '../api';

function SyncProgress({ current, total, message }) {
  const percentage = total > 0 ? Math.round((current / total) * 100) : 0;

  return (
    <div className="sync-progress">
      <div className="sync-progress-header">
        <span className="sync-status-dot"></span>
        <span>Data sync in progress</span>
      </div>
      <div className="sync-progress-details">
        <span className="sync-message">{message}</span>
        <span className="sync-count">{current} / {total} months</span>
      </div>
      <div className="sync-progress-bar">
        <div
          className="sync-progress-fill"
          style={{ width: `${percentage}%` }}
        />
      </div>
      <div className="sync-percentage">{percentage}% complete</div>
    </div>
  );
}

export default function Dashboard() {
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [syncStatus, setSyncStatus] = useState(null);

  useEffect(() => {
    let interval;

    const checkSync = async () => {
      try {
        const status = await getSyncStatus();
        setSyncStatus(status);

        if (status.is_syncing) {
          interval = setTimeout(checkSync, 2000);
        }
      } catch (err) {
        console.error('Failed to check sync status:', err);
      }
    };

    checkSync();

    return () => {
      if (interval) clearTimeout(interval);
    };
  }, []);

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>arXiv Trends Dashboard</h1>
        <p className="subtitle">Track publication trends across arXiv categories</p>
        {syncStatus?.is_syncing && (
          <SyncProgress
            current={syncStatus.current}
            total={syncStatus.total}
            message={syncStatus.progress}
          />
        )}
      </header>

      <main className="dashboard-main">
        <section className="chart-section">
          <CategorySelector
            selectedCategory={selectedCategory}
            onSelectCategory={setSelectedCategory}
          />
          <TrendChart categoryId={selectedCategory} />
        </section>

        <aside className="sidebar">
          <HypeIndicator onSelectCategory={setSelectedCategory} />
        </aside>
      </main>
    </div>
  );
}
