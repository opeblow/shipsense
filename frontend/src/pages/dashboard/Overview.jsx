import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import Card from '../../components/Card';
import Button from '../../components/Button';
import Loading from '../../components/Loading';
import StatusMessage from '../../components/StatusMessage';
import {
  createExperiment,
  getDecision,
  getInstrumentationReadiness,
  refreshDecision,
  getAudit,
  listExperiments,
} from '../../api/client';

function ScoreBadge({ label, value, invert = false }) {
  if (value === null || value === undefined) return null;
  const score = Number(value);
  let color;
  if (invert) {
    // lower is better (e.g. CLS, render-blocking count)
    color = score < 0.1 ? 'text-emerald-600 bg-emerald-50 border-emerald-200'
      : score < 0.25 ? 'text-amber-600 bg-amber-50 border-amber-200'
      : 'text-red-600 bg-red-50 border-red-200';
  } else {
    color = score >= 90 ? 'text-emerald-600 bg-emerald-50 border-emerald-200'
      : score >= 70 ? 'text-amber-600 bg-amber-50 border-amber-200'
      : 'text-red-600 bg-red-50 border-red-200';
  }
  return (
    <div className="flex flex-col items-center gap-1">
      <div className={`text-2xl font-bold px-3 py-1 border rounded ${color}`}>
        {typeof value === 'number' ? value : value}
      </div>
      <span className="text-xs text-text-tertiary text-center">{label}</span>
    </div>
  );
}

function AuditRow({ label, value, good, bad }) {
  if (value === null || value === undefined) return null;
  const isGood = good !== undefined ? value === good : undefined;
  const isBad = bad !== undefined ? value === bad : undefined;
  const dot = isGood ? '🟢' : isBad ? '🔴' : '⚪';
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-border last:border-0">
      <span className="text-sm text-text-secondary">{label}</span>
      <span className="text-sm font-medium text-text flex items-center gap-1.5">
        {dot} {String(value)}
      </span>
    </div>
  );
}

function EffortBadge({ level }) {
  const colors = {
    Low: 'text-emerald-700 bg-emerald-50 border-emerald-200',
    Medium: 'text-amber-700 bg-amber-50 border-amber-200',
    High: 'text-red-700 bg-red-50 border-red-200',
  };
  return (
    <span className={`text-xs px-2 py-0.5 border rounded ${colors[level] || 'text-text-secondary bg-zebra border-border'}`}>
      {level}
    </span>
  );
}

function LoopStep({ number, label, value, detail, muted = false }) {
  return (
    <div className={`border p-4 ${muted ? 'border-warning/30 bg-warning/5' : 'border-border bg-surface'}`}>
      <p className="text-xs text-text-tertiary mb-1">{number}. {label}</p>
      <p className="text-sm font-medium text-text">{value}</p>
      {detail && <p className="text-xs text-text-secondary mt-2 leading-relaxed">{detail}</p>}
    </div>
  );
}

function ExperimentResultSummary({ experiment }) {
  if (!experiment) {
    return (
      <p className="text-sm text-text-secondary">
        No experiment has been created for this decision loop yet.
      </p>
    );
  }

  if (!experiment.result) {
    return (
      <p className="text-sm text-text-secondary">
        {experiment.status.replaceAll('_', ' ')} · baseline {experiment.baseline_value}
      </p>
    );
  }

  const result = experiment.result;
  return (
    <div className="space-y-1">
      <p className="text-sm font-medium text-text">
        {result.conclusion?.replaceAll('_', ' ')}
        {result.recommendation ? ` · ${result.recommendation}` : ''}
      </p>
      {result.current !== undefined && (
        <p className="text-xs text-text-secondary">
          Baseline {result.baseline} → current {result.current}
          {result.change !== undefined ? ` (${result.change >= 0 ? '+' : ''}${result.change} ${result.unit})` : ''}
        </p>
      )}
    </div>
  );
}

function hasMeasuredScore(value) {
  return value !== null && value !== undefined;
}

export default function Overview() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const productId = searchParams.get('productId');

  const [decision, setDecision] = useState(null);
  const [audit, setAudit] = useState(null);
  const [readiness, setReadiness] = useState(null);
  const [experiments, setExperiments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [creatingExperiment, setCreatingExperiment] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!productId) { navigate('/onboard', { replace: true }); return; }

    let cancelled = false;
    async function fetchData() {
      try {
        const [dec, aud, instrumented, exp] = await Promise.allSettled([
          getDecision(productId),
          getAudit(productId),
          getInstrumentationReadiness(productId),
          listExperiments(productId),
        ]);
        if (!cancelled) {
          if (dec.status === 'fulfilled') setDecision(dec.value);
          else setError(dec.reason?.response?.data?.detail || 'Failed to load product decision');
          if (aud.status === 'fulfilled') setAudit(aud.value?.audit);
          if (instrumented.status === 'fulfilled') setReadiness(instrumented.value);
          if (exp.status === 'fulfilled') setExperiments(exp.value);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetchData();
    return () => { cancelled = true; };
  }, [productId, navigate]);

  if (!productId) return null;
  if (loading) return <Loading text="Loading dashboard..." />;
  if (error && !decision) return <StatusMessage type="error">{error}</StatusMessage>;

  const a = audit || {};
  const cwv = a.core_web_vitals || {};
  const confidencePercent = decision ? Math.round(decision.confidence * 100) : null;
  const behaviorMetric = decision?.target_metric?.startsWith('funnel:');
  const technicalMetric = decision?.target_metric?.startsWith('technical_audit:');
  const hasAnyBehavior = (readiness?.unique_users || 0) > 0;
  const decisionBasis = behaviorMetric
    ? 'Behavioral funnel'
    : technicalMetric
      ? hasAnyBehavior ? 'Technical audit + behavior pending' : 'Live audit only'
      : 'Evidence readiness';
  const behaviorTransition = behaviorMetric
    ? readiness?.transitions?.find((transition) => (
      decision.target_metric === `funnel:${transition.step}:${transition.next_step}:completion_rate`
    ))
    : null;
  const experimentReady = technicalMetric || Boolean(behaviorTransition?.ready);
  const readinessLabel = readiness?.decision_ready
    ? 'Behavior baseline ready'
    : readiness
      ? `${readiness.coverage_count}/${readiness.configured_steps.length} flow steps · ${readiness.unique_users} users`
      : 'Checking instrumentation';
  const experimentStatus = technicalMetric
    ? 'Technical verification available'
    : experimentReady ? 'Experiment can be created' : 'Needs verified baseline';
  const evidenceCount = decision?.evidence?.length || 0;
  const primaryHypothesis = decision?.hypotheses?.[0];
  const highlightedExperiment = experiments.find((experiment) => experiment.result)
    || experiments.find((experiment) => experiment.status !== 'planned')
    || experiments[0];
  const verificationSummary = highlightedExperiment?.result
    ? highlightedExperiment.result.conclusion?.replaceAll('_', ' ')
    : highlightedExperiment
      ? highlightedExperiment.status.replaceAll('_', ' ')
      : experimentStatus;

  const handleRefresh = async () => {
    setRefreshing(true);
    setError('');
    try {
      const [updatedDecision, updatedReadiness] = await Promise.all([
        refreshDecision(productId),
        getInstrumentationReadiness(productId),
      ]);
      setDecision(updatedDecision);
      setReadiness(updatedReadiness);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to refresh product decision');
    } finally {
      setRefreshing(false);
    }
  };

  const handleCreateExperiment = async () => {
    setCreatingExperiment(true);
    setError('');
    try {
      await createExperiment(productId, decision.decision_id);
      navigate(`/dashboard/experiments?productId=${productId}`);
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(
        typeof detail === 'string'
          ? detail
          : detail?.message || 'Failed to create experiment'
      );
    } finally {
      setCreatingExperiment(false);
    }
  };

  return (
    <div className="flex flex-col gap-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-text">Today</h1>
          <p className="text-sm text-text-secondary mt-1">
            One product decision, grounded in the strongest evidence available
          </p>
        </div>
        <Button variant="secondary" onClick={handleRefresh} disabled={refreshing}>
          {refreshing ? 'Refreshing...' : 'Refresh decision'}
        </Button>
      </div>

      {error && <StatusMessage type="error">{error}</StatusMessage>}

      {a.pagespeed_error && (
        <div className="border border-warning/30 bg-warning/5 p-4">
          <p className="text-sm font-medium text-warning">PageSpeed scores are temporarily unavailable</p>
          <p className="text-xs text-text-secondary mt-1">
            {a.pagespeed_error}. Structural, security, and behavioral evidence remain available.
          </p>
        </div>
      )}

      {decision?.stale && (
        <div className="border border-warning/30 bg-warning/5 p-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm font-medium text-warning">New evidence is available</p>
            <p className="text-xs text-text-secondary mt-1">
              {decision.stale_reasons.join(' ')}
            </p>
          </div>
          <Button variant="secondary" onClick={handleRefresh} disabled={refreshing}>
            {refreshing ? 'Refreshing...' : 'Refresh now'}
          </Button>
        </div>
      )}

      {readiness && !readiness.decision_ready && (
        <div className="border border-warning/30 bg-warning/5 p-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-sm font-medium text-warning">Behavioral evidence is not ready</p>
            <p className="text-xs text-text-secondary mt-1">
              {readiness.coverage_count} of {readiness.configured_steps.length} flow steps observed · {readiness.unique_users} users measured.
            </p>
            {readiness.next_actions[0] && (
              <p className="text-xs text-text-secondary mt-2">{readiness.next_actions[0]}</p>
            )}
          </div>
          <Button
            variant="secondary"
            onClick={() => navigate(`/dashboard/settings?productId=${productId}`)}
          >
            Fix instrumentation
          </Button>
        </div>
      )}

      {technicalMetric && readiness && !readiness.decision_ready && (
        <Card>
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="max-w-3xl">
              <p className="text-xs uppercase tracking-wider text-text-tertiary mb-2">Current data boundary</p>
              <h2 className="text-lg font-semibold text-text">This is a live URL audit decision, not a user-behavior decision yet.</h2>
              <p className="text-sm text-text-secondary mt-2 leading-relaxed">
                ShipSense measured the public page and found a verifiable technical issue. It has not seen real users move through your configured product flow yet, so behavioral drop-off decisions are intentionally blocked.
              </p>
            </div>
            <Button
              variant="secondary"
              onClick={() => navigate(`/dashboard/settings?productId=${productId}`)}
            >
              Install collector
            </Button>
          </div>
        </Card>
      )}

      {decision && (
        <div className="grid gap-3 md:grid-cols-4">
          <LoopStep
            number="1"
            label="Evidence"
            value={readinessLabel}
            detail={evidenceCount ? `${evidenceCount} evidence record${evidenceCount === 1 ? '' : 's'} used in the current decision.` : 'ShipSense needs more measured evidence before recommending a product change.'}
            muted={readiness && !readiness.decision_ready}
          />
          <LoopStep
            number="2"
            label="Decision basis"
            value={decisionBasis}
            detail={decision.target_metric}
          />
          <LoopStep
            number="3"
            label="Hypothesis"
            value={primaryHypothesis ? primaryHypothesis.statement : 'No behavioral hypothesis yet'}
            detail={primaryHypothesis?.validation_action}
            muted={!decision.hypotheses?.length}
          />
          <LoopStep
            number="4"
            label="Verification"
            value={verificationSummary}
            detail={highlightedExperiment ? highlightedExperiment.name : 'Create an experiment when the baseline is ready.'}
            muted={!experimentReady && !highlightedExperiment}
          />
        </div>
      )}

      {decision && (
        <Card className="!p-0 overflow-hidden">
          <div className="border-b border-border p-6 bg-[#0a0a0a] text-white">
            <div className="flex flex-wrap items-center gap-2 mb-4">
              <span className="text-xs uppercase tracking-wider text-[#a3a3a3]">Decision #{decision.version}</span>
              <span className="text-xs px-2 py-0.5 border border-[#3a3a3a] rounded">
                {confidencePercent}% confidence
              </span>
              <EffortBadge level={decision.effort} />
            </div>
            <p className="text-xs text-[#8a8a8a] mb-2">
              Generated {new Date(decision.created_at).toLocaleString()}
            </p>
            <h2 className="text-2xl font-semibold leading-tight max-w-2xl">{decision.title}</h2>
            <p className="text-sm text-[#bdbdbd] mt-3 leading-relaxed max-w-3xl">{decision.problem}</p>
          </div>

          <div className="p-6 grid gap-6 lg:grid-cols-[1.5fr_1fr]">
            <div>
              <p className="text-xs uppercase tracking-wider text-text-tertiary mb-2">What to change</p>
              <p className="text-sm text-text leading-relaxed">{decision.recommendation}</p>
              <div className="mt-5 p-4 bg-accent/5 border border-accent/20">
                <p className="text-xs font-medium text-accent mb-1">Expected outcome</p>
                <p className="text-sm text-text-secondary">{decision.expected_outcome}</p>
              </div>
              <div className="mt-5">
                <Button
                  onClick={handleCreateExperiment}
                  disabled={creatingExperiment || !experimentReady}
                >
                  {creatingExperiment
                    ? 'Creating...'
                    : experimentReady
                      ? technicalMetric ? 'Create technical verification' : 'Create experiment'
                      : 'Baseline not ready'}
                </Button>
                {!experimentReady && (
                  <p className="text-xs text-text-secondary mt-2">
                    Complete the required instrumentation before freezing an experiment baseline.
                  </p>
                )}
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <p className="text-xs uppercase tracking-wider text-text-tertiary mb-1">Verify with</p>
                <p className="text-sm font-medium text-text break-words">{decision.target_metric}</p>
                <p className="text-xs text-text-secondary mt-1">Baseline: {decision.baseline_value}</p>
              </div>
              {decision.affected_flow && (
                <div>
                  <p className="text-xs uppercase tracking-wider text-text-tertiary mb-1">Affected flow</p>
                  <p className="text-sm text-text">{decision.affected_flow}</p>
                </div>
              )}
              <div>
                <p className="text-xs uppercase tracking-wider text-text-tertiary mb-2">Evidence</p>
                {decision.evidence.length > 0 ? (
                  <div className="space-y-2">
                    {decision.evidence.map((item) => (
                      <div key={item.id} className="border border-border p-3">
                        <p className="text-xs text-text-tertiary">{item.source_type.replaceAll('_', ' ')}</p>
                        <p className="text-sm font-medium text-text mt-1">
                          {item.metric_key}: {String(item.value)} {item.unit !== 'boolean' ? item.unit : ''}
                        </p>
                        {item.sample_size !== null && item.sample_size !== undefined && (
                          <p className="text-xs text-text-secondary mt-1">{item.sample_size} unique users measured</p>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-text-secondary">More measured evidence is required.</p>
                )}
              </div>
            </div>
          </div>

          <div className="border-t border-border px-6 py-4 bg-zebra">
            <p className="text-xs text-text-secondary">
              Why this confidence: {decision.confidence_reasons.join(' ')}
            </p>
          </div>
        </Card>
      )}

      {highlightedExperiment && (
        <Card>
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-wider text-text-tertiary mb-2">Verification loop</p>
              <h2 className="text-lg font-semibold text-text">{highlightedExperiment.name}</h2>
              <p className="text-sm text-text-secondary mt-2 max-w-3xl leading-relaxed">
                {highlightedExperiment.hypothesis}
              </p>
            </div>
            <span className="text-xs px-2 py-1 border border-border text-text-secondary">
              {highlightedExperiment.status.replaceAll('_', ' ')}
            </span>
          </div>

          <div className="grid gap-3 sm:grid-cols-3 mt-5">
            <div className="border border-border p-3">
              <p className="text-xs text-text-tertiary">Metric</p>
              <p className="text-sm font-medium text-text mt-1 break-words">{highlightedExperiment.target_metric}</p>
            </div>
            <div className="border border-border p-3">
              <p className="text-xs text-text-tertiary">Frozen baseline</p>
              <p className="text-sm font-medium text-text mt-1">{highlightedExperiment.baseline_value}</p>
            </div>
            <div className="border border-border p-3">
              <p className="text-xs text-text-tertiary">Result</p>
              <div className="mt-1">
                <ExperimentResultSummary experiment={highlightedExperiment} />
              </div>
            </div>
          </div>

          <div className="mt-5">
            <Button
              variant="secondary"
              onClick={() => navigate(`/dashboard/experiments?productId=${productId}`)}
            >
              View experiments
            </Button>
          </div>
        </Card>
      )}

      {decision?.hypotheses?.length > 0 && (
        <Card>
          <div className="mb-4">
            <h2 className="text-sm font-semibold text-text">Possible causes to test</h2>
            <p className="text-xs text-text-secondary mt-1">
              These are evidence-linked hypotheses, not measured findings.
            </p>
          </div>
          <div className="space-y-3">
            {decision.hypotheses.map((hypothesis) => (
              <div key={hypothesis.id} className="border border-border p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-medium text-text">{hypothesis.statement}</p>
                  <span className="text-xs border border-border px-2 py-0.5 text-text-secondary">
                    {hypothesis.confidence} hypothesis confidence
                  </span>
                </div>
                <p className="text-xs text-text-secondary mt-2">{hypothesis.rationale}</p>
                <div className="mt-3 bg-accent/5 border border-accent/20 p-3">
                  <p className="text-xs font-medium text-accent">How to validate</p>
                  <p className="text-sm text-text-secondary mt-1">{hypothesis.validation_action}</p>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Lighthouse Scores */}
      {[
        a.performance_score,
        a.accessibility_score,
        a.seo_score,
        a.best_practices_score,
      ].some(hasMeasuredScore) && (
        <Card>
          <h2 className="text-sm font-semibold text-text mb-4">Lighthouse Scores (Live)</h2>
          <div className="flex flex-wrap gap-6 justify-start">
            <ScoreBadge label="Performance" value={a.performance_score} />
            <ScoreBadge label="Accessibility" value={a.accessibility_score} />
            <ScoreBadge label="SEO" value={a.seo_score} />
            <ScoreBadge label="Best Practices" value={a.best_practices_score} />
          </div>
          {a.strategy_used && (
            <p className="text-xs text-text-tertiary mt-3">Tested on: {a.strategy_used}</p>
          )}
        </Card>
      )}

      {/* Core Web Vitals */}
      {(cwv.lcp || cwv.cls !== undefined || cwv.tbt || cwv.fcp) && (
        <Card>
          <h2 className="text-sm font-semibold text-text mb-4">Core Web Vitals</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {cwv.lcp && <ScoreBadge label="LCP" value={cwv.lcp} />}
            {cwv.fcp && <ScoreBadge label="FCP" value={cwv.fcp} />}
            {cwv.cls !== undefined && <ScoreBadge label="CLS" value={cwv.cls} invert />}
            {cwv.tbt && <ScoreBadge label="TBT" value={cwv.tbt} />}
          </div>
        </Card>
      )}

      {/* Page Health */}
      {audit && (
        <Card>
          <h2 className="text-sm font-semibold text-text mb-4">Page Health</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8">
            <div>
              <AuditRow label="Mobile viewport" value={a.has_mobile_viewport ? 'Yes' : 'No'} good={true} bad={false} />
              <AuditRow label="H1 count" value={a.h1_count} good={1} bad={0} />
              <AuditRow label="Meta description" value={a.meta_description ? 'Present' : 'Missing'} good="Present" bad="Missing" />
              <AuditRow label="Canonical tag" value={a.has_canonical ? 'Present' : 'Missing'} good="Present" bad="Missing" />
              <AuditRow label="Images missing alt" value={a.images_missing_alt} good={0} />
              <AuditRow label="Render-blocking resources" value={a.render_blocking_resources} good={0} />
            </div>
            <div>
              <AuditRow label="Compression enabled" value={a.has_compression ? 'Yes' : 'No'} good="Yes" bad="No" />
              <AuditRow label="HTTPS / HSTS" value={a.security_headers?.has_hsts ? 'Yes' : 'No'} good="Yes" bad="No" />
              <AuditRow label="CSP header" value={a.security_headers?.has_csp ? 'Present' : 'Missing'} good="Present" bad="Missing" />
              <AuditRow label="Tracking scripts" value={a.tracking_script_count} />
              <AuditRow label="CTAs detected" value={a.cta_count} />
              <AuditRow label="Word count" value={a.word_count} />
            </div>
          </div>
          {a.detected_frameworks?.length > 0 && (
            <div className="mt-3 pt-3 border-t border-border flex flex-wrap gap-2">
              {a.detected_frameworks.map(f => (
                <span key={f} className="text-xs bg-accent/10 text-accent px-2 py-0.5 rounded">{f}</span>
              ))}
            </div>
          )}
        </Card>
      )}

      {/* No data state */}
      {!audit && !decision && (
        <Card>
          <p className="text-sm text-text-secondary">
            No audit data yet.{' '}
            <button
              onClick={() => navigate('/onboard')}
              className="text-accent underline hover:no-underline cursor-pointer bg-transparent border-none p-0"
            >
              Run a live audit →
            </button>
          </p>
        </Card>
      )}
    </div>
  );
}
