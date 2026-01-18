import { useState, useEffect } from 'react';
import { getHypeCategories, getDecliningCategories } from '../api';

function TrendBadge({ direction, score }) {
  const getColor = () => {
    if (direction === 'surging') return '#059669';
    if (direction === 'rising') return '#16a34a';
    if (direction === 'growing') return '#65a30d';
    if (direction === 'declining') return '#dc2626';
    if (direction === 'cooling') return '#ea580c';
    return '#6b7280';
  };

  const getIcon = () => {
    if (direction === 'surging') return '⬆';
    if (direction === 'rising' || direction === 'growing') return '↑';
    if (direction === 'declining' || direction === 'cooling') return '↓';
    return '→';
  };

  return (
    <span
      className="trend-badge"
      style={{
        backgroundColor: getColor(),
        color: 'white',
        padding: '2px 8px',
        borderRadius: '12px',
        fontSize: '12px',
        fontWeight: 'bold'
      }}
    >
      {getIcon()} {Math.abs(score).toFixed(1)}%
    </span>
  );
}

function CategoryList({ title, categories, type, onSelectCategory }) {
  if (categories.length === 0) {
    return (
      <div className={`category-list ${type}`}>
        <h3>{title}</h3>
        <p className="no-data">No data available. Sync data to see trends.</p>
      </div>
    );
  }

  return (
    <div className={`category-list ${type}`}>
      <h3>{title}</h3>
      <ul>
        {categories.map((cat) => (
          <li
            key={cat.category_id}
            onClick={() => onSelectCategory(cat.category_id)}
            style={{ cursor: 'pointer' }}
          >
            <div className="category-info">
              <span className="category-id">{cat.category_id}</span>
              <span className="category-name">{cat.category_name}</span>
            </div>
            <TrendBadge direction={cat.trend_direction} score={cat.hype_score} />
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function HypeIndicator({ onSelectCategory }) {
  const [hypeCategories, setHypeCategories] = useState([]);
  const [decliningCategories, setDecliningCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const [hype, declining] = await Promise.all([
          getHypeCategories(5),
          getDecliningCategories(5)
        ]);
        setHypeCategories(hype);
        setDecliningCategories(declining);
      } catch (err) {
        setError('Failed to load trend indicators');
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  const refresh = async () => {
    setLoading(true);
    try {
      const [hype, declining] = await Promise.all([
        getHypeCategories(5),
        getDecliningCategories(5)
      ]);
      setHypeCategories(hype);
      setDecliningCategories(declining);
    } catch (err) {
      setError('Failed to refresh');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="hype-indicator loading">Loading trends...</div>;
  }

  if (error) {
    return <div className="hype-indicator error">{error}</div>;
  }

  return (
    <div className="hype-indicator">
      <div className="hype-header">
        <h2>Trend Overview</h2>
        <button onClick={refresh} className="refresh-btn">Refresh</button>
      </div>
      <div className="hype-lists">
        <CategoryList
          title="Hottest Categories"
          categories={hypeCategories}
          type="rising"
          onSelectCategory={onSelectCategory}
        />
        <CategoryList
          title="Cooling Down"
          categories={decliningCategories}
          type="declining"
          onSelectCategory={onSelectCategory}
        />
      </div>
    </div>
  );
}
