import { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import Button from '../components/Button';
import Input from '../components/Input';
import StatusMessage from '../components/StatusMessage';
import Loading from '../components/Loading';
import { onboardProduct } from '../api/client';

const STEPS = [
  { title: 'What\'s your product URL?' },
  { title: 'Who is it for?' },
  { title: 'What\'s the core action?' },
  { title: 'Install Novus snippet' },
  { title: 'You\'re live' },
];

const AUDIENCES = ['Consumers', 'B2B', 'Internal tool'];

const API_URL = import.meta.env.VITE_API_URL || 'https://shipsense-knrs.onrender.com';
const NOVUS_SNIPPET = `<!-- ShipSense Novus Tracker -->
<script>
  (function(w,d,s){
    w._novusQueue = w._novusQueue || [];
    w._novusAppId = 'YOUR_APP_ID';
    var f=d.getElementsByTagName(s)[0],
        j=d.createElement(s);
    j.async=true;
    j.src='${API_URL}/static/novus.js';
    j.setAttribute('data-api-url','${API_URL}');
    f.parentNode.insertBefore(j,f);
  })(window,document,'script');
</script>`;

export default function Onboarding() {
  const navigate = useNavigate();
  const location = useLocation();
  const [step, setStep] = useState(0);
  const [url, setUrl] = useState(location.state?.url || '');
  const [audience, setAudience] = useState('');
  const [coreAction, setCoreAction] = useState('');
  const [copied, setCopied] = useState(false);
  const [errors, setErrors] = useState({});
  const snippetCopiedRef = useRef(false);
  const analysisTriggeredRef = useRef(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);

  const runAnalysis = async () => {
    setAnalyzing(true);
    try {
      const result = await onboardProduct({
        url,
        product_type: audience.toLowerCase(),
        core_action: coreAction,
        user_id: 'default',
      });
      setAnalysisResult(result);
      const startTime = Date.now();
      pendo.track('onboarding_completed', {
        url: url.trim(),
        audience: audience,
        core_action: coreAction.trim(),
        snippet_copied: snippetCopiedRef.current,
        setup_duration_ms: Date.now() - startTime,
      });
    } catch (err) {
      console.error('[Onboarding] API call failed:', err);
      const detail = err.response?.data?.detail;
      const status = err.response?.status;
      const statusText = err.response?.statusText;
      const message = detail || (status ? `Server error (${status}${statusText ? ': ' + statusText : ''})` : err.message) || 'Analysis failed. Please try again.';
      setErrors({ submit: message });
    } finally {
      setAnalyzing(false);
    }
  };

  useEffect(() => {
    if (step === 4 && !analysisTriggeredRef.current) {
      analysisTriggeredRef.current = true;
      runAnalysis();
    }
  }, [step]);

  const canProceed = () => {
    if (step === 0) return url.trim().length > 0;
    if (step === 1) return audience.length > 0;
    if (step === 2) return coreAction.trim().length > 0;
    return true;
  };

  const handleNext = () => {
    const e = {};
    if (step === 0 && !url.trim()) e.url = 'We need a URL to analyze your product';
    if (step === 1 && !audience) e.audience = 'Pick who your product serves';
    if (step === 2 && !coreAction.trim()) e.coreAction = 'Tell us the one thing users should do';
    setErrors(e);
    if (Object.keys(e).length > 0) return;

    if (step < STEPS.length - 1) {
      pendo.track('onboarding_step_completed', {
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
      await navigator.clipboard.writeText(NOVUS_SNIPPET);
      setCopied(true);
      snippetCopiedRef.current = true;
      setTimeout(() => setCopied(false), 2000);
      pendo.track('snippet_copied', {
        snippet_type: 'novus_tracker',
        copy_success: true,
        onboarding_step: 4,
      });
    } catch {
      // ignore
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
              <div className="mt-6">
                <Input
                  value={coreAction}
                  onChange={(e) => setCoreAction(e.target.value)}
                  placeholder="e.g. Create a project, Complete checkout"
                  onKeyDown={(e) => e.key === 'Enter' && handleNext()}
                  error={errors.coreAction}
                  hint="What's the one action that makes a user successful?"
                  autoFocus
                />
              </div>
            )}

            {step === 3 && (
              <div className="mt-6">
                <p className="text-sm text-text-secondary mb-4">
                  Add this snippet to your <code className="text-accent bg-accent/5 px-1">&lt;head&gt;</code> tag.
                </p>
                <pre className="bg-[#0a0a0a] text-[#e5e5e5] p-4 text-xs overflow-x-auto border border-border mb-4 leading-relaxed">{NOVUS_SNIPPET}</pre>
                <div className="flex items-center gap-3">
                  <Button onClick={handleCopy}>{copied ? 'Copied' : 'Copy snippet'}</Button>
                  <span className="text-xs text-text-tertiary">Or continue and do this later</span>
                </div>
              </div>
            )}

            {step === 4 && (
              <div className="mt-6">
                {analyzing && <Loading text="Analyzing your product..." />}

                {errors.submit && !analyzing && (
                  <StatusMessage type="error">{errors.submit}</StatusMessage>
                )}

                {analysisResult && !analyzing && (
                  <>
                    <div className="bg-success/5 border border-success/20 p-4 mb-6">
                      <p className="text-sm text-success font-medium">ShipSense has analyzed your product.</p>
                      <p className="text-sm text-text-secondary mt-1">
                        {url ? url.replace(/^https?:\/\//, '').split('/')[0] : 'Your product'} is set up. Data is flowing in.
                      </p>
                    </div>
                    <div className="text-sm text-text-secondary leading-relaxed whitespace-pre-line">
                      {analysisResult.initial_insights}
                    </div>
                  </>
                )}
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
