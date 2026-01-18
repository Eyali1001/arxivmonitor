import { useState, useEffect } from 'react';
import { getCategories } from '../api';

export default function CategorySelector({ selectedCategory, onSelectCategory }) {
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchCategories() {
      try {
        const data = await getCategories();
        setCategories(data);
        setLoading(false);
      } catch (err) {
        setError('Failed to load categories');
        setLoading(false);
      }
    }
    fetchCategories();
  }, []);

  if (loading) {
    return <div className="category-selector loading">Loading categories...</div>;
  }

  if (error) {
    return <div className="category-selector error">{error}</div>;
  }

  return (
    <div className="category-selector">
      <label htmlFor="category-select">Select Category:</label>
      <select
        id="category-select"
        value={selectedCategory || ''}
        onChange={(e) => onSelectCategory(e.target.value)}
      >
        <option value="">-- Choose a category --</option>

        {/* Parent categories - view all subcategories at once */}
        <optgroup label="View All Subcategories">
          {categories.map((group) => (
            <option key={`parent:${group.id}`} value={`parent:${group.id}`}>
              📊 All {group.name} ({group.subcategories.length} categories)
            </option>
          ))}
        </optgroup>

        {/* Individual subcategories */}
        {categories.map((group) => (
          <optgroup key={group.id} label={group.name}>
            {group.subcategories.map((sub) => (
              <option key={sub.id} value={sub.id}>
                {sub.id} - {sub.name}
              </option>
            ))}
          </optgroup>
        ))}
      </select>
    </div>
  );
}
