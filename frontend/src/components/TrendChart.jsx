import { useState, useEffect } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  BarChart,
  Bar
} from 'recharts';
import { getTrends, getTrendStats, getParentCategoryStats } from '../api';

// Colors for multi-line chart
const COLORS = [
  '#2563eb', '#dc2626', '#16a34a', '#ea580c', '#8b5cf6',
  '#06b6d4', '#ec4899', '#84cc16', '#f59e0b', '#6366f1'
];

function SingleCategoryChart({ categoryId }) {
  const [data, setData] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!categoryId) return;

    async function fetchData() {
      setLoading(true);
      setError(null);
      try {
        const [trendsData, statsData] = await Promise.all([
          getTrends(categoryId),
          getTrendStats(categoryId)
        ]);

        const formatted = trendsData.map(item => ({
          date: `${item.year}-${String(item.month).padStart(2, '0')}`,
          count: item.count
        }));

        setData(formatted);
        setStats(statsData);
      } catch (err) {
        setError('Failed to load trend data');
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [categoryId]);

  if (loading) return <div className="trend-chart loading">Loading...</div>;
  if (error) return <div className="trend-chart error">{error}</div>;
  if (data.length === 0) return null;

  return (
    <div className="trend-chart">
      {stats && (
        <div className="stats-header">
          <h3>{stats.category_name}</h3>
          <div className="stats-summary">
            <span className="stat">
              <strong>Total:</strong> {stats.total_papers.toLocaleString()}
            </span>
            <span className="stat">
              <strong>Avg:</strong> {stats.average_monthly}/mo
            </span>
            <span className={`stat trend-${stats.trend_direction}`}>
              <strong>Growth:</strong>
              {stats.hype_score > 0 ? ' +' : ' '}{stats.hype_score}%
            </span>
          </div>
        </div>
      )}
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
          <XAxis dataKey="date" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
          <YAxis tick={{ fontSize: 10 }} />
          <Tooltip />
          <Line type="monotone" dataKey="count" stroke="#2563eb" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function ParentCategoryView({ parentId }) {
  const [stats, setStats] = useState([]);
  const [trendsData, setTrendsData] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      try {
        const statsData = await getParentCategoryStats(parentId);
        setStats(statsData);

        // Fetch trends for top 10 categories
        const top10 = statsData.slice(0, 10);
        const trendsPromises = top10.map(s => getTrends(s.category_id));
        const trendsResults = await Promise.all(trendsPromises);

        const trendsMap = {};
        top10.forEach((s, i) => {
          trendsMap[s.category_id] = trendsResults[i];
        });
        setTrendsData(trendsMap);
      } catch (err) {
        setError('Failed to load data');
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [parentId]);

  if (loading) return <div className="trend-chart loading">Loading all subcategories...</div>;
  if (error) return <div className="trend-chart error">{error}</div>;

  // Prepare comparison bar chart data
  const barData = stats.map(s => ({
    name: s.category_id,
    growth: s.hype_score,
    papers: s.total_papers
  }));

  // Prepare multi-line chart data
  const dates = new Set();
  Object.values(trendsData).forEach(trends => {
    trends.forEach(t => dates.add(`${t.year}-${String(t.month).padStart(2, '0')}`));
  });
  const sortedDates = Array.from(dates).sort();

  const multiLineData = sortedDates.map(date => {
    const point = { date };
    Object.entries(trendsData).forEach(([catId, trends]) => {
      const match = trends.find(t => `${t.year}-${String(t.month).padStart(2, '0')}` === date);
      point[catId] = match ? match.count : null;
    });
    return point;
  });

  return (
    <div className="parent-category-view">
      <h3 style={{ marginBottom: '20px' }}>
        {parentId.toUpperCase()} - Growth Rankings (2022 → Now)
      </h3>

      {/* Growth comparison bar chart */}
      <div style={{ marginBottom: '30px' }}>
        <h4>Long-term Growth by Subcategory</h4>
        <ResponsiveContainer width="100%" height={Math.max(300, stats.length * 25)}>
          <BarChart data={barData} layout="vertical" margin={{ left: 100, right: 30 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" unit="%" />
            <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={90} />
            <Tooltip formatter={(value) => `${value.toFixed(1)}%`} />
            <Bar
              dataKey="growth"
              fill="#2563eb"
              label={{ position: 'right', fontSize: 10, formatter: (v) => `${v.toFixed(0)}%` }}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Multi-line trends chart for top 10 */}
      {Object.keys(trendsData).length > 0 && (
        <div style={{ marginBottom: '30px' }}>
          <h4>Publication Trends (Top 10 by Growth)</h4>
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={multiLineData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
              <XAxis dataKey="date" tick={{ fontSize: 10 }} interval={5} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Legend />
              {Object.keys(trendsData).map((catId, i) => (
                <Line
                  key={catId}
                  type="monotone"
                  dataKey={catId}
                  stroke={COLORS[i % COLORS.length]}
                  strokeWidth={2}
                  dot={false}
                  connectNulls
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Stats table */}
      <div>
        <h4>All Subcategories</h4>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #e5e7eb', textAlign: 'left' }}>
              <th style={{ padding: '8px' }}>Category</th>
              <th style={{ padding: '8px' }}>Name</th>
              <th style={{ padding: '8px', textAlign: 'right' }}>Total Papers</th>
              <th style={{ padding: '8px', textAlign: 'right' }}>Avg/Month</th>
              <th style={{ padding: '8px', textAlign: 'right' }}>Growth</th>
            </tr>
          </thead>
          <tbody>
            {stats.map((s, i) => (
              <tr key={s.category_id} style={{ borderBottom: '1px solid #e5e7eb', background: i % 2 ? '#f9fafb' : 'white' }}>
                <td style={{ padding: '8px', fontWeight: 'bold' }}>{s.category_id}</td>
                <td style={{ padding: '8px' }}>{s.category_name}</td>
                <td style={{ padding: '8px', textAlign: 'right' }}>{s.total_papers.toLocaleString()}</td>
                <td style={{ padding: '8px', textAlign: 'right' }}>{s.average_monthly.toFixed(0)}</td>
                <td style={{
                  padding: '8px',
                  textAlign: 'right',
                  color: s.hype_score > 20 ? '#16a34a' : s.hype_score < -5 ? '#dc2626' : '#6b7280',
                  fontWeight: 'bold'
                }}>
                  {s.hype_score > 0 ? '+' : ''}{s.hype_score.toFixed(1)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function TrendChart({ categoryId }) {
  if (!categoryId) {
    return (
      <div className="trend-chart empty">
        <p>Select a category to view trends</p>
      </div>
    );
  }

  // Check if it's a parent category view
  if (categoryId.startsWith('parent:')) {
    const parentId = categoryId.replace('parent:', '');
    return <ParentCategoryView parentId={parentId} />;
  }

  return <SingleCategoryChart categoryId={categoryId} />;
}
