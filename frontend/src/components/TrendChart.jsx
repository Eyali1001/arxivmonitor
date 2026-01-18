import { useState, useEffect } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';
import { getTrends, getTrendStats } from '../api';

export default function TrendChart({ categoryId }) {
  const [data, setData] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!categoryId) {
      setData([]);
      setStats(null);
      return;
    }

    async function fetchData() {
      setLoading(true);
      setError(null);
      try {
        const [trendsData, statsData] = await Promise.all([
          getTrends(categoryId),
          getTrendStats(categoryId)
        ]);

        // Format data for chart
        const formatted = trendsData.map(item => ({
          date: `${item.year}-${String(item.month).padStart(2, '0')}`,
          count: item.count,
          year: item.year,
          month: item.month
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

  if (!categoryId) {
    return (
      <div className="trend-chart empty">
        <p>Select a category to view trends</p>
      </div>
    );
  }

  if (loading) {
    return <div className="trend-chart loading">Loading trend data...</div>;
  }

  if (error) {
    return <div className="trend-chart error">{error}</div>;
  }

  if (data.length === 0) {
    return (
      <div className="trend-chart empty">
        <p>No data available for this category.</p>
        <p>Click "Sync Data" to fetch publication data from arXiv.</p>
      </div>
    );
  }

  return (
    <div className="trend-chart">
      {stats && (
        <div className="stats-header">
          <h3>{stats.category_name}</h3>
          <div className="stats-summary">
            <span className="stat">
              <strong>Total Papers:</strong> {stats.total_papers.toLocaleString()}
            </span>
            <span className="stat">
              <strong>Monthly Avg:</strong> {stats.average_monthly}
            </span>
            <span className={`stat trend-${stats.trend_direction}`}>
              <strong>Growth since 2022:</strong>
              {stats.hype_score > 0 ? ' +' : ' '}
              {stats.hype_score}%
            </span>
          </div>
        </div>
      )}

      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 12 }}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fontSize: 12 }}
            label={{ value: 'Publications', angle: -90, position: 'insideLeft' }}
          />
          <Tooltip
            contentStyle={{ backgroundColor: '#fff', border: '1px solid #ccc' }}
            labelStyle={{ fontWeight: 'bold' }}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="count"
            name="Publications"
            stroke="#2563eb"
            strokeWidth={2}
            dot={{ fill: '#2563eb', strokeWidth: 2 }}
            activeDot={{ r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
