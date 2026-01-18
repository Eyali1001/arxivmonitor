import { useState, useEffect } from 'react';
import { getHypeCategories, getDecliningCategories, getCategories } from '../api';

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
        <p className="no-data">No data available.</p>
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
  const [parentCategories, setParentCategories] = useState([]);
  const [selectedParent, setSelectedParent] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch parent categories on mount
  useEffect(() => {
    async function fetchParents() {
      try {
        const cats = await getCategories();
        setParentCategories(cats);
      } catch (err) {
        console.error('Failed to load parent categories');
      }
    }
    fetchParents();
  }, []);

  // Fetch hype/declining when filter changes
  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      try {
        const parent = selectedParent || null;
        const [hype, declining] = await Promise.all([
          getHypeCategories(5, parent),
          getDecliningCategories(5, parent)
        ]);
        setHypeCategories(hype);
        setDecliningCategories(declining);
        setError(null);
      } catch (err) {
        setError('Failed to load trend indicators');
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [selectedParent]);

  const handleFilterChange = (e) => {
    setSelectedParent(e.target.value);
  };

  if (error) {
    return <div className="hype-indicator error">{error}</div>;
  }

  return (
    <div className="hype-indicator">
      <div className="hype-header">
        <h2>Trend Overview</h2>
      </div>

      {/* Filter dropdown */}
      <div style={{ marginBottom: '16px' }}>
        <select
          value={selectedParent}
          onChange={handleFilterChange}
          style={{
            width: '100%',
            padding: '8px 12px',
            borderRadius: '6px',
            border: '1px solid #d1d5db',
            fontSize: '13px',
            cursor: 'pointer'
          }}
        >
          <option value="">All Categories</option>
          {parentCategories.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name} ({p.subcategories.length})
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', color: '#6b7280', padding: '20px' }}>
          Loading...
        </div>
      ) : (
        <div className="hype-lists">
          <CategoryList
            title={selectedParent ? `Hottest in ${selectedParent.toUpperCase()}` : "Hottest Categories"}
            categories={hypeCategories}
            type="rising"
            onSelectCategory={onSelectCategory}
          />
          <CategoryList
            title={selectedParent ? `Cooling in ${selectedParent.toUpperCase()}` : "Cooling Down"}
            categories={decliningCategories}
            type="declining"
            onSelectCategory={onSelectCategory}
          />
        </div>
      )}
    </div>
  );
}
