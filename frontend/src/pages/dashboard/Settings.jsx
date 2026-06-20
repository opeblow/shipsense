import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import Card from '../../components/Card';
import Button from '../../components/Button';
import Input from '../../components/Input';
import StatusMessage from '../../components/StatusMessage';
import {
  getCollectorStatus,
  getCollectorKey,
  getInstrumentationReadiness,
  getProduct,
  rotateCollectorKey,
  updateCriticalFlow,
  updateProductContext,
} from '../../api/client';

const API_URL = import.meta.env.VITE_API_URL || 'https://shipsense-knrs.onrender.com';

export default function Settings() {
  const [searchParams] = useSearchParams();
  const productId = searchParams.get('productId');
  const [copied, setCopied] = useState(false);
  const [product, setProduct] = useState(null);
  const [flowSteps, setFlowSteps] = useState('');
  const [savingFlow, setSavingFlow] = useState(false);
  const [flowMessage, setFlowMessage] = useState('');
  const [collectorKey, setCollectorKey] = useState(() => getCollectorKey(productId));
  const [collectorStatus, setCollectorStatus] = useState(null);
  const [readiness, setReadiness] = useState(null);
  const [rotatingKey, setRotatingKey] = useState(false);
  const [integrationMessage, setIntegrationMessage] = useState('');
  const [context, setContext] = useState({
    target_user: '',
    user_problem: '',
    value_proposition: '',
    business_goal: '',
    constraints: '',
  });
  const [savingContext, setSavingContext] = useState(false);
  const [contextMessage, setContextMessage] = useState('');

  const snippet = `<script src="${API_URL}/static/shipsense-collector.js" data-product-id="${productId || 'YOUR_PRODUCT_ID'}" data-collector-key="${collectorKey || 'ROTATE_KEY_TO_REINSTALL'}" data-api-url="${API_URL}"></script>`;
  const isSample = product?.is_sample;

  useEffect(() => {
    if (!productId) return;
    let cancelled = false;
    getProduct(productId)
      .then((p) => {
        if (!cancelled) {
          setProduct(p);
          setFlowSteps((p.critical_flow || []).join(', '));
          setContext((current) => ({ ...current, ...(p.product_context || {}) }));
        }
      })
      .catch(() => { /* ignore */ });
    getCollectorStatus(productId)
      .then((status) => { if (!cancelled) setCollectorStatus(status); })
      .catch(() => {});
    getInstrumentationReadiness(productId)
      .then((status) => { if (!cancelled) setReadiness(status); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [productId]);

  const handleCopySnippet = async () => {
    try {
      await navigator.clipboard.writeText(snippet);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
      window.pendo?.track('settings_snippet_copied', {
        snippet_type: 'shipsense_event_collector',
        copy_success: true,
      });
    } catch {
      // ignore
    }
  };

  const handleRotateKey = async () => {
    setRotatingKey(true);
    setIntegrationMessage('');
    try {
      const result = await rotateCollectorKey(productId);
      setCollectorKey(result.collector_key);
      setIntegrationMessage('Collector key rotated. Replace the old snippet on your product.');
    } catch (err) {
      setIntegrationMessage(err.response?.data?.detail || 'Failed to rotate collector key.');
    } finally {
      setRotatingKey(false);
    }
  };

  const handleSaveFlow = async () => {
    const steps = flowSteps.split(',').map((item) => item.trim()).filter(Boolean);
    if (steps.length < 2) {
      setFlowMessage('Enter at least two ordered event names.');
      return;
    }
    setSavingFlow(true);
    setFlowMessage('');
    try {
      await updateCriticalFlow(productId, steps);
      setProduct((current) => ({ ...current, critical_flow: steps }));
      setReadiness(await getInstrumentationReadiness(productId));
      setFlowMessage('Critical flow saved. Refresh Today to generate a new decision.');
    } catch (err) {
      setFlowMessage(err.response?.data?.detail || 'Failed to save critical flow.');
    } finally {
      setSavingFlow(false);
    }
  };

  const handleSaveContext = async () => {
    setSavingContext(true);
    setContextMessage('');
    try {
      const result = await updateProductContext(productId, context);
      setContext(result.context);
      setContextMessage('Product context saved. Refresh Today to regenerate hypotheses.');
    } catch (err) {
      const detail = err.response?.data?.detail;
      setContextMessage(
        typeof detail === 'string' ? detail : 'Failed to save product context.'
      );
    } finally {
      setSavingContext(false);
    }
  };

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-xl font-semibold text-text">Settings</h1>
        <p className="text-sm text-text-secondary mt-1">Manage your ShipSense integration</p>
      </div>

      <Card>
        <h3 className="text-sm font-semibold text-text mb-1">Integration</h3>
        <p className="text-sm text-text-secondary mb-4">
          Your ShipSense Event Collector. Add it to your site to start collecting behavioral evidence.
          {isSample ? ' This sample workspace already contains synthetic events, so no collector install is required for the demo.' : ''}
        </p>
        <div className="flex items-center gap-2 mb-4">
          <span className={`w-2 h-2 rounded-full ${collectorStatus?.verified ? 'bg-success' : 'bg-warning'}`} />
          <p className="text-sm text-text-secondary">
            {collectorStatus?.verified
              ? `Verified · ${collectorStatus.event_count.toLocaleString()} events received`
              : 'Waiting for the first event'}
          </p>
        </div>
        {collectorStatus?.last_event_at && (
          <p className="text-xs text-text-tertiary mb-4">
            Last event: {new Date(collectorStatus.last_event_at).toLocaleString()}
          </p>
        )}
        <pre className="bg-[#0a0a0a] text-[#e5e5e5] p-4 text-xs overflow-x-auto border border-border mb-4 leading-relaxed">{snippet}</pre>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" onClick={handleCopySnippet} disabled={!collectorKey}>
            {copied ? 'Copied' : 'Copy snippet'}
          </Button>
          <Button variant="secondary" onClick={handleRotateKey} disabled={rotatingKey}>
            {rotatingKey ? 'Rotating...' : collectorKey ? 'Rotate key' : 'Generate new key'}
          </Button>
        </div>
        {!collectorKey && (
          <p className="text-xs text-warning mt-3">
            {isSample
              ? 'Sample workspaces do not expose the original collector key. Generate a new key only if you want to connect this demo workspace to a real product.'
              : 'This browser does not have the original collector key. Generate a new key and reinstall the snippet.'}
          </p>
        )}
        {integrationMessage && (
          <div className="mt-3">
            <StatusMessage type={integrationMessage.startsWith('Collector') ? 'success' : 'error'}>
              {integrationMessage}
            </StatusMessage>
          </div>
        )}
      </Card>

      {readiness && (
        <Card>
          <div className="flex flex-wrap items-start justify-between gap-3 mb-5">
            <div>
              <h3 className="text-sm font-semibold text-text">Instrumentation readiness</h3>
              <p className="text-sm text-text-secondary mt-1">
                ShipSense checks whether the configured flow can support a behavioral decision.
              </p>
            </div>
            <span className={`text-xs px-2 py-1 border rounded ${
              readiness.decision_ready
                ? 'text-success border-success/30 bg-success/5'
                : 'text-warning border-warning/30 bg-warning/5'
            }`}>
              {readiness.decision_ready ? 'Decision ready' : 'Not ready'}
            </span>
          </div>

          <div className="grid gap-3 sm:grid-cols-3 mb-5">
            <div className="border border-border p-3">
              <p className="text-xs text-text-tertiary">Flow coverage</p>
              <p className="text-lg font-semibold text-text mt-1">
                {readiness.coverage_count}/{readiness.configured_steps.length}
              </p>
            </div>
            <div className="border border-border p-3">
              <p className="text-xs text-text-tertiary">Users observed</p>
              <p className="text-lg font-semibold text-text mt-1">{readiness.unique_users}</p>
            </div>
            <div className="border border-border p-3">
              <p className="text-xs text-text-tertiary">Minimum baseline</p>
              <p className="text-lg font-semibold text-text mt-1">{readiness.minimum_sample} users</p>
            </div>
          </div>

          <div className="space-y-2">
            {readiness.flow_steps.map((step) => (
              <div key={step.step} className="border border-border p-3 flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-text">
                    {step.position}. {step.step}
                  </p>
                  <p className="text-xs text-text-secondary mt-1">
                    {step.observed
                      ? `${step.unique_users} unique users · ${step.event_count} events`
                      : 'No matching event received'}
                  </p>
                  {!step.observed && step.possible_matches.length > 0 && (
                    <p className="text-xs text-warning mt-1">
                      Possible naming mismatch: {step.possible_matches.join(', ')}
                    </p>
                  )}
                </div>
                <span className={`text-xs ${step.observed ? 'text-success' : 'text-warning'}`}>
                  {step.observed ? 'Observed' : 'Missing'}
                </span>
              </div>
            ))}
          </div>

          {readiness.transitions.length > 0 && (
            <div className="mt-5">
              <p className="text-xs uppercase tracking-wider text-text-tertiary mb-2">
                Baseline readiness
              </p>
              <div className="space-y-2">
                {readiness.transitions.map((transition) => (
                  <div key={`${transition.step}:${transition.next_step}`} className="text-sm border border-border p-3">
                    <div className="flex flex-wrap justify-between gap-2">
                      <span className="text-text">{transition.step} → {transition.next_step}</span>
                      <span className={transition.ready ? 'text-success' : 'text-warning'}>
                        {transition.ready
                          ? 'Ready'
                          : `${transition.sample_gap} more ${transition.sample_gap === 1 ? 'user' : 'users'} needed`}
                      </span>
                    </div>
                    {(transition.orphaned_next_step_users > 0 || transition.out_of_order_users > 0) && (
                      <p className="text-xs text-warning mt-2">
                        {transition.orphaned_next_step_users} downstream-only · {transition.out_of_order_users} out of order
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {!readiness.decision_ready && readiness.next_actions.length > 0 && (
            <div className="mt-5 border border-warning/30 bg-warning/5 p-4">
              <p className="text-xs font-medium text-warning mb-2">Required next actions</p>
              <ol className="space-y-1 list-decimal list-inside">
                {readiness.next_actions.map((action) => (
                  <li key={action} className="text-sm text-text-secondary">{action}</li>
                ))}
              </ol>
            </div>
          )}
        </Card>
      )}

      <Card>
        <h3 className="text-sm font-semibold text-text mb-1">Product context</h3>
        <p className="text-sm text-text-secondary mb-4">
          Owner-declared context helps ShipSense form better hypotheses. It is never treated as measured behavior.
        </p>
        <div className="space-y-4">
          {[
            ['target_user', 'Primary user', 'Who is trying to complete the critical flow?'],
            ['user_problem', 'User problem', 'What problem brings them to this product?'],
            ['value_proposition', 'Value proposition', 'What outcome should be obvious to the user?'],
            ['business_goal', 'Business goal', 'What result matters to the product?'],
            ['constraints', 'Constraints', 'Traffic, compliance, technical, or operational limits'],
          ].map(([key, label, placeholder]) => (
            <Input
              key={key}
              label={label}
              value={context[key]}
              onChange={(event) => setContext((current) => ({
                ...current,
                [key]: event.target.value,
              }))}
              placeholder={placeholder}
            />
          ))}
        </div>
        <div className="mt-4">
          <Button variant="secondary" onClick={handleSaveContext} disabled={savingContext}>
            {savingContext ? 'Saving...' : 'Save product context'}
          </Button>
        </div>
        {contextMessage && (
          <div className="mt-3">
            <StatusMessage type={contextMessage.startsWith('Product') ? 'success' : 'error'}>
              {contextMessage}
            </StatusMessage>
          </div>
        )}
      </Card>

      <Card>
        <h3 className="text-sm font-semibold text-text mb-1">Critical flow</h3>
        <p className="text-sm text-text-secondary mb-4">
          ShipSense uses this exact event order for trustworthy funnel decisions.
        </p>
        <Input
          value={flowSteps}
          onChange={(event) => setFlowSteps(event.target.value)}
          placeholder="landing viewed, signup started, account created"
          hint="Comma-separated event names in their intended order."
        />
        <div className="mt-4">
          <Button variant="secondary" onClick={handleSaveFlow} disabled={savingFlow}>
            {savingFlow ? 'Saving...' : 'Save critical flow'}
          </Button>
        </div>
        {flowMessage && (
          <div className="mt-3">
            <StatusMessage type={flowMessage.startsWith('Critical') ? 'success' : 'error'}>
              {flowMessage}
            </StatusMessage>
          </div>
        )}
      </Card>

      <Card>
        <h3 className="text-sm font-semibold text-text mb-1">Product URL</h3>
        <p className="text-sm text-text-secondary mb-4">The URL ShipSense monitors for user behavior.</p>
        <p className="text-sm text-text font-medium">{product?.url || '—'}</p>
      </Card>
    </div>
  );
}
