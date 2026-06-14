import axios from 'axios';
import API_BASE_URL from '../config';

const client = axios.create({
  baseURL: API_BASE_URL,
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
