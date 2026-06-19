import axios from 'axios';
import API_BASE_URL from '../config';

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000,
  headers: { 'Content-Type': 'application/json' },
});

export async function auditUrl(url) {
  const res = await client.post('/api/audit-url', { url });
  return res.data;
}

export async function onboardProduct(data) {
  const res = await client.post('/api/onboard', data);
  return res.data;
}

export async function getMetrics(productId) {
  const res = await client.get(`/api/metrics/${productId}`);
  return res.data;
}

export async function getBehavior(productId) {
  const res = await client.get(`/api/behavior/${productId}`);
  return res.data;
}

export async function getInsights(productId) {
  const res = await client.get(`/api/insights/${productId}`);
  return res.data;
}

export async function askAgent(productId, userId, message) {
  const res = await client.post('/api/agent/chat', {
    product_id: productId,
    user_id: userId,
    message,
  });
  return res.data;
}

export async function getProduct(productId) {
  const res = await client.get(`/api/product/${productId}`);
  return res.data;
}

export default client;
