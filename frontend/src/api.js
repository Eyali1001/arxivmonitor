import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
});

export async function getCategories() {
  const response = await api.get('/categories');
  return response.data;
}

export async function getTrends(categoryId) {
  const response = await api.get(`/trends/${categoryId}`);
  return response.data;
}

export async function getTrendStats(categoryId) {
  const response = await api.get(`/trends/${categoryId}/stats`);
  return response.data;
}

export async function getHypeCategories(limit = 10, parent = null) {
  const params = { limit };
  if (parent) params.parent = parent;
  const response = await api.get('/hype', { params });
  return response.data;
}

export async function getDecliningCategories(limit = 10, parent = null) {
  const params = { limit };
  if (parent) params.parent = parent;
  const response = await api.get('/declining', { params });
  return response.data;
}

export async function getSyncStatus() {
  const response = await api.get('/sync/status');
  return response.data;
}

export async function getParentCategoryStats(parentId) {
  const response = await api.get(`/parent/${parentId}/stats`);
  return response.data;
}

export default api;
