import axios from 'axios';

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
});

export async function analyzeProduct(url) {
  const res = await client.post('/analyze', { url });
  return res.data;
}

export async function getDashboardData() {
  const res = await client.get('/dashboard');
  return res.data;
}

export async function askAgent(question) {
  const res = await client.post('/agent/ask', { question });
  return res.data;
}

export async function getBehaviorData() {
  const res = await client.get('/behavior');
  return res.data;
}

export default client;
