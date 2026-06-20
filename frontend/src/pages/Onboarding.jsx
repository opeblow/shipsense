import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import Button from '../components/Button';
import Input from '../components/Input';
import StatusMessage from '../components/StatusMessage';
import { onboardProduct, auditUrl, createSampleProduct } from '../api/client';

const STEPS = [
  { title: 'What\'s your product URL?' },
  { title: 'Who is it for?' },
  { title: 'What\'s the core action?' },
  { title: 'Build your baseline' },
  { title: 'Connect real behavior' },
];

const AUDIENCES = ['Consumers', 'B2B', 'Internal tool'];

const API_URL = import.meta.env.VITE_API_URL || 'https://shipsense-knrs.onrender.com';
function collectorSnippet(productId, collectorKey) {
  return `<script src="${API_URL}/static/shipsense-collector.js" data-product-id="${productId}" data-collector-key="${collectorKey}" data-api-url="${API_URL}"></script>`;
}

const AUDIT_STEPS = [
  { label: 'Running PageSpeed audit...', key: 'pagespeed' },
  { label: 'Scanning page structure...', key: 'structure' },
  { label: 'Generating insights...', key: 'insights' },
];

export default function Onboarding() {
  const navigate = useNavigate();
  const location = useLocation();
  const [step, setStep] = useState(0);
  const [url, setUrl] = useState(location.state?.url || '');
  const [audience, setAudience] = useState('');
  const [coreAction, setCoreAction] = useState('');
  const [targetUser, setTargetUser] = useState('');
  const [userProblem, setUserProblem] = useState('');
  const [valueProposition, setValueProposition] = useState('');
  const [flowSteps, setFlowSteps] = useState('');
  const [copied, setCopied] = useState(false);
  const [errors, setErrors] = useState({});
  const snippetCopiedRef = useRef(false);
  const analysisTriggeredRef = useRef(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [auditProgress, setAuditProgress] = useState(null);
  const [auditError, setAuditError] = useState(null);
  const [creatingSample, setCreatingSample] = useState(false);

  const runAnalysis = useCallback(async () => {
    setAnalyzing(true);
    setAuditProgress(0);
    setAuditError(null);

    try {
      setAuditProgress(1);
      const auditData = await auditUrl(url);

      setAuditProgress(2);
      const result = await onboardProduct({
        url,
        product_type: audience.toLowerCase(),
        core_action: coreAction,
        user_id: 'default',
        critical_flow: flowSteps
          .split(',')
          .map((step) => step.trim())
          .filter(Boolean),
        product_context: {
          target_user: targetUser,
          user_problem: userProblem,
          value_proposition: valueProposition,
          business_goal: coreAction,
          constraints: '',
        },
        audit_data: auditData,
      });

      setAuditProgress(3);
      setAnalysisResult(result);
      window.pendo?.track('onboarding_completed', {
        url: url.trim(),
        audience: audience,
        core_action: coreAction.trim(),
        snippet_copied: snippetCopiedRef.current,
      });
    } catch (err) {
      console.error('[Onboarding] Analysis failed:', err);
      const detail = err.response?.data?.detail;
      const status = err.response?.status;
      const detailMessage = typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail.map((item) => item.msg).filter(Boolean).join(' ')
          : '';
      const msg = detailMessage || (status ? `Server error (${status})` : err.message) || 'Analysis failed. Please try again.';
      const isAuditFailure = msg.toLowerCase().includes('audit') || msg.toLowerCase().includes('scrape') || msg.toLowerCase().includes('timeout');
      setAuditError(isAuditFailure
        ? "We couldn't fully audit this URL — try a different one"
        : msg);
      setErrors({ submit: msg });
    } finally {
      setAnalyzing(false);
    }
  }, [url, audience, coreAction, flowSteps, targetUser, userProblem, valueProposition]);

  useEffect(() => {
    if (step === 3 && !analysisTriggeredRef.current) {
      analysisTriggeredRef.current = true;
      runAnalysis();
    }
  }, [step, runAnalysis]);

  const canProceed = () => {
    if (step === 0) return url.trim().length > 0;
    if (step === 1) return audience.length > 0;
    if (step === 2) {
      const steps = flowSteps.split(',').map((item) => item.trim()).filter(Boolean);
      return (
        coreAction.trim().length > 0
        && targetUser.trim().length > 0
        && userProblem.trim().length > 0
        && valueProposition.trim().length > 0
        && steps.length >= 2
      );
    }
    if (step === 3) return Boolean(analysisResult) && !analyzing;
    return true;
  };

  const handleNext = () => {
    const e = {};
    if (step === 0 && !url.trim()) e.url = 'We need a URL to analyze your product';
    if (step === 1 && !audience) e.audience = 'Pick who your product serves';
    if (step === 2 && !coreAction.trim()) e.coreAction = 'Tell us the one thing users should do';
    if (step === 2 && !targetUser.trim()) e.targetUser = 'Describe the primary user';
    if (step === 2 && !userProblem.trim()) e.userProblem = 'Describe the problem they need solved';
    if (step === 2 && !valueProposition.trim()) e.valueProposition = 'Describe why they should choose this product';
    if (step === 2) {
      const steps = flowSteps.split(',').map((item) => item.trim()).filter(Boolean);
      if (steps.length < 2) e.flowSteps = 'Define at least two ordered event names';
    }
    setErrors(e);
    if (Object.keys(e).length > 0) return;

    if (step < STEPS.length - 1) {
      window.pendo?.track('onboarding_step_completed', {
        step_number: step + 1,
        step_title: STEPS[step].title,
        url: url.trim(),
        audience: audience || '',
        core_action: coreAction.trim(),
        total_steps: STEPS.length,
      });
      setStep((s) => s + 1);
    } else {
      handleFinish();
    }
  };

  const handleFinish = () => {
    if (analysisResult) {
      navigate(`/dashboard?productId=${analysisResult.product_id}`);
    }
  };

  const handleCopy = async () => {
    try {
      if (!analysisResult?.product_id) return;
      await navigator.clipboard.writeText(
        collectorSnippet(analysisResult.product_id, analysisResult.collector_key),
      );
      setCopied(true);
      snippetCopiedRef.current = true;
      setTimeout(() => setCopied(false), 2000);
      window.pendo?.track('snippet_copied', {
        snippet_type: 'shipsense_event_collector',
        copy_success: true,
        onboarding_step: 4,
      });
    } catch {
      // ignore
    }
  };

  const handleSampleWorkspace = async () => {
    setCreatingSample(true);
    setErrors({});
    try {
      const sample = await createSampleProduct();
      window.pendo?.track('sample_workspace_created', {
        sample_data: true,
      });
      navigate(`/dashboard?productId=${sample.product_id}`);
    } catch (err) {
      const detail = err.response?.data?.detail;
      setErrors({
        submit: typeof detail === 'string'
          ? detail
          : 'Failed to create the sample workspace.',
      });
    } finally {
      setCreatingSample(false);
    }
  };

  return (
    <div className="min-h-screen bg-bg flex flex-col">
      <header className="border-b border-border">
        <div className="max-w-lg mx-auto px-6 py-4">
          <span className="text-sm font-semibold text-text tracking-tight">ShipSense</span>
        </div>
      </header>

      <main className="flex-1 flex items-center justify-center px-6 py-16">
        <div className="w-full max-w-lg">
          {/* Step indicator */}
          <div className="flex items-center gap-2 mb-10">
            {STEPS.map((s, i) => (
              <div key={i} className="flex items-center gap-2 flex-1">
                <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-medium transition-colors duration-100
                  ${i < step ? 'bg-accent text-white' : i === step ? 'bg-accent text-white' : 'bg-border text-text-secondary'}`}>
                  {i + 1}
                </div>
                {i < STEPS.length - 1 && <div className={`flex-1 h-px ${i < step ? 'bg-accent' : 'bg-border'}`} />}
              </div>
            ))}
          </div>

          <div className="bg-surface border border-border p-8">
            <h2 className="text-lg font-semibold text-text mb-1">{STEPS[step].title}</h2>

            {step === 0 && (
              <div className="mt-6">
                <Input
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://yourapp.com"
                  onKeyDown={(e) => e.key === 'Enter' && handleNext()}
                  error={errors.url}
                  autoFocus
                />
                <div className="mt-6 pt-5 border-t border-border">
                  <p className="text-xs text-text-tertiary mb-3">
                    Want to inspect the full decision and experiment loop first?
                  </p>
                  <Button
                    variant="secondary"
                    onClick={handleSampleWorkspace}
                    disabled={creatingSample}
                  >
                    {creatingSample ? 'Creating sample...' : 'Explore labelled sample data'}
                  </Button>
                </div>
              </div>
            )}

            {step === 1 && (
              <div className="mt-6 flex flex-col gap-2">
                {AUDIENCES.map((a) => (
                  <button
                    key={a}
                    onClick={() => setAudience(a)}
                    className={`text-left px-4 py-3 text-sm border transition-colors duration-75 cursor-pointer
                      ${audience === a ? 'border-accent bg-accent/5 text-text' : 'border-border bg-transparent text-text-secondary hover:border-accent'}`}
                  >
                    {a}
                  </button>
                ))}
                {errors.audience && (
                  <p className="mt-1 text-xs text-error">{errors.audience}</p>
                )}
              </div>
            )}

            {step === 2 && (
              <div className="mt-6 space-y-5">
                <Input
                  value={coreAction}
                  onChange={(e) => setCoreAction(e.target.value)}
                  placeholder="e.g. Create a project, Complete checkout"
                  onKeyDown={(e) => e.key === 'Enter' && handleNext()}
                  error={errors.coreAction}
                  hint="What's the one action that makes a user successful?"
                  autoFocus
                />
                <Input
                  value={targetUser}
                  onChange={(e) => setTargetUser(e.target.value)}
                  placeholder="e.g. Solo founders shipping their first SaaS"
                  error={errors.targetUser}
                  hint="Who specifically is trying to complete this flow?"
                />
                <Input
                  value={userProblem}
                  onChange={(e) => setUserProblem(e.target.value)}
                  placeholder="e.g. They cannot tell which onboarding issue to fix"
                  error={errors.userProblem}
                  hint="What problem brings them to the product?"
                />
                <Input
                  value={valueProposition}
                  onChange={(e) => setValueProposition(e.target.value)}
                  placeholder="e.g. One evidence-backed action instead of another dashboard"
                  error={errors.valueProposition}
                  hint="What outcome or promise should be obvious to them?"
                />
                <Input
                  value={flowSteps}
                  onChange={(e) => setFlowSteps(e.target.value)}
                  placeholder="landing viewed, signup started, account created"
                  error={errors.flowSteps}
                  hint="Enter the exact event names in order, separated by commas."
                />
              </div>
            )}

            {step === 3 && (
              <div className="mt-6">
                {analyzing && (
                  <div className="space-y-4 py-4">
                    {AUDIT_STEPS.map((s, i) => {
                      const done = auditProgress !== null && i < auditProgress;
                      const active = auditProgress !== null && i === auditProgress;
                      return (
                        <div key={s.key} className="flex items-center gap-3">
                          <div className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-medium shrink-0
                            ${done ? 'bg-success text-white' : active ? 'border-2 border-accent border-t-transparent rounded-full animate-spin' : 'border border-border'}`}>
                            {done ? '\u2713' : ''}
                          </div>
                          <span className={`text-sm ${done ? 'text-text' : active ? 'text-text' : 'text-text-tertiary'}`}>
                            {s.label}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                )}

                {auditError && !analyzing && (
                  <StatusMessage type="error">{auditError}</StatusMessage>
                )}

                {errors.submit && !analyzing && !auditError && (
                  <StatusMessage type="error">{errors.submit}</StatusMessage>
                )}

                {analysisResult && !analyzing && (
                  <>
                    <div className="bg-success/5 border border-success/20 p-4 mb-6">
                      <p className="text-sm text-success font-medium">Your product-health baseline is ready.</p>
                      <p className="text-sm text-text-secondary mt-1">
                        This result comes from a live technical audit. Behavioral evidence becomes available after the collector receives real events.
                      </p>
                    </div>
                    <div className="text-sm text-text-secondary leading-relaxed whitespace-pre-line">
                      {analysisResult.initial_insights}
                    </div>
                  </>
                )}
              </div>
            )}

            {step === 4 && analysisResult && (
              <div className="mt-6">
                <p className="text-sm text-text-secondary mb-4">
                  Add the ShipSense Event Collector to your <code className="text-accent bg-accent/5 px-1">&lt;head&gt;</code> to measure real user actions. This is separate from the official Novus by Pendo installation.
                </p>
                <pre className="bg-[#0a0a0a] text-[#e5e5e5] p-4 text-xs overflow-x-auto border border-border mb-4 leading-relaxed">{collectorSnippet(analysisResult.product_id, analysisResult.collector_key)}</pre>
                <div className="flex items-center gap-3">
                  <Button onClick={handleCopy}>{copied ? 'Copied' : 'Copy collector'}</Button>
                  <span className="text-xs text-text-tertiary">You can install this later from Settings</span>
                </div>
              </div>
            )}
          </div>

          {/* Navigation */}
          <div className="flex items-center justify-between mt-6">
            {step > 0 ? (
              <Button variant="secondary" onClick={() => setStep((s) => s - 1)}>Back</Button>
            ) : (
              <div />
            )}
            <Button onClick={handleNext} disabled={!canProceed() || analyzing || (step === STEPS.length - 1 && !analysisResult)}>
              {step === STEPS.length - 1 ? (analyzing ? 'Analyzing...' : 'Go to Dashboard') : 'Continue'}
            </Button>
          </div>
          {errors.submit && (
            <div className="mt-4">
              <StatusMessage type="error">{errors.submit}</StatusMessage>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
