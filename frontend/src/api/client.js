import axios from 'axios';
import API_BASE_URL from '../config';

const WORKSPACE_KEY_STORAGE = 'shipsense_workspace_key';
const COLLECTOR_KEYS_STORAGE = 'shipsense_collector_keys';
let workspacePromise = null;

function readCollectorKeys() {
  try {
    return JSON.parse(localStorage.getItem(COLLECTOR_KEYS_STORAGE) || '{}');
  } catch {
    return {};
  }
}

export function saveCollectorKey(productId, collectorKey) {
  const keys = readCollectorKeys();
  keys[productId] = collectorKey;
  localStorage.setItem(COLLECTOR_KEYS_STORAGE, JSON.stringify(keys));
}

export function getCollectorKey(productId) {
  return readCollectorKeys()[productId] || '';
}

export async function ensureWorkspaceKey() {
  const existing = localStorage.getItem(WORKSPACE_KEY_STORAGE);
  if (existing) return existing;
  if (!workspacePromise) {
    workspacePromise = axios.post(`${API_BASE_URL}/api/workspaces`)
      .then((response) => {
        localStorage.setItem(WORKSPACE_KEY_STORAGE, response.data.workspace_key);
        return response.data.workspace_key;
      })
      .finally(() => {
        workspacePromise = null;
      });
  }
  return workspacePromise;
}

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000,
  headers: { 'Content-Type': 'application/json' },
});

client.interceptors.request.use(async (config) => {
  config.headers['X-Workspace-Key'] = await ensureWorkspaceKey();
  return config;
});

export async function auditUrl(url) {
  const res = await client.post('/api/audit-url', { url });
  return res.data;
}

export async function onboardProduct(data) {
  const res = await client.post('/api/onboard', data);
  saveCollectorKey(res.data.product_id, res.data.collector_key);
  return res.data;
}

export async function listProducts() {
  const res = await client.get('/api/products');
  return res.data;
}

export async function createSampleProduct() {
  const res = await client.post('/api/demo/sample-product');
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

export async function getDecision(productId) {
  const res = await client.get(`/api/decision/${productId}`);
  return res.data;
}

export async function refreshDecision(productId) {
  const res = await client.post(`/api/decision/${productId}/refresh`);
  return res.data;
}

export async function createExperiment(productId, decisionId) {
  const res = await client.post('/api/experiments', {
    product_id: productId,
    decision_id: decisionId,
  });
  return res.data;
}

export async function listExperiments(productId) {
  const res = await client.get(`/api/product/${productId}/experiments`);
  return res.data;
}

export async function shipExperiment(experimentId) {
  const res = await client.post(`/api/experiments/${experimentId}/ship`);
  return res.data;
}

export async function evaluateExperiment(experimentId) {
  const res = await client.post(`/api/experiments/${experimentId}/evaluate`);
  return res.data;
}

export async function refreshAudit(productId) {
  const res = await client.post(`/api/audit/${productId}/refresh`);
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

export async function getAnalystContext(productId) {
  const res = await client.get(`/api/agent/context/${productId}`);
  return res.data;
}

export async function getProduct(productId) {
  const res = await client.get(`/api/product/${productId}`);
  return res.data;
}

export async function updateCriticalFlow(productId, steps) {
  const res = await client.put(`/api/product/${productId}/critical-flow`, { steps });
  return res.data;
}

export async function updateProductContext(productId, context) {
  const res = await client.put(`/api/product/${productId}/context`, context);
  return res.data;
}

export async function getCollectorStatus(productId) {
  const res = await client.get(`/api/product/${productId}/collector/status`);
  return res.data;
}

export async function getInstrumentationReadiness(productId) {
  const res = await client.get(`/api/product/${productId}/instrumentation-readiness`);
  return res.data;
}

export async function rotateCollectorKey(productId) {
  const res = await client.post(`/api/product/${productId}/collector/rotate`);
  saveCollectorKey(productId, res.data.collector_key);
  return res.data;
}

export async function getAudit(productId) {
  const res = await client.get(`/api/audit/${productId}`);
  return res.data;
}

export default client;
