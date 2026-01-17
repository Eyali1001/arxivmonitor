import { useState } from 'react';
import CategorySelector from './CategorySelector';
import TrendChart from './TrendChart';
import HypeIndicator from './HypeIndicator';

export default function Dashboard() {
  const [selectedCategory, setSelectedCategory] = useState(null);

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>arXiv Trends Dashboard</h1>
        <p className="subtitle">Track publication trends across arXiv categories</p>
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
