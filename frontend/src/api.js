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

export async function getHypeCategories(limit = 10) {
  const response = await api.get('/hype', { params: { limit } });
  return response.data;
}

export async function getDecliningCategories(limit = 10) {
  const response = await api.get('/declining', { params: { limit } });
  return response.data;
}

export async function getSyncStatus() {
  const response = await api.get('/sync/status');
  return response.data;
}

export default api;
