import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import Card from '../../components/Card';
import Loading from '../../components/Loading';
import StatusMessage from '../../components/StatusMessage';
import { getInsights, getAudit } from '../../api/client';

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

export default function Overview() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const productId = searchParams.get('productId');

  const [insights, setInsights] = useState(null);
  const [audit, setAudit] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!productId) { navigate('/onboard', { replace: true }); return; }

    let cancelled = false;
    async function fetchData() {
      try {
        const [ins, aud] = await Promise.allSettled([
          getInsights(productId),
          getAudit(productId),
        ]);
        if (!cancelled) {
          if (ins.status === 'fulfilled') setInsights(ins.value);
          else setError(ins.reason?.response?.data?.detail || 'Failed to load insights');
          if (aud.status === 'fulfilled') setAudit(aud.value?.audit);
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
  if (error && !insights) return <StatusMessage type="error">{error}</StatusMessage>;

  const a = audit || {};
  const cwv = a.core_web_vitals || {};

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-xl font-semibold text-text">Overview</h1>
        <p className="text-sm text-text-secondary mt-1">
          Real measurements from your live URL — no simulated data
        </p>
      </div>

      {/* Lighthouse Scores */}
      {(a.performance_score !== undefined || a.seo_score !== undefined) && (
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

      {/* AI Insight — grounded in audit */}
      {insights?.summary && (
        <Card>
          <div className="flex items-start gap-3">
            <div className="w-7 h-7 bg-accent flex items-center justify-center flex-shrink-0 mt-0.5 rounded">
              <span className="text-xs font-bold text-white">AI</span>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-text mb-2">AI Analysis</h3>
              <p className="text-sm text-text-secondary leading-relaxed whitespace-pre-line">{insights.summary}</p>
            </div>
          </div>
        </Card>
      )}

      {/* Recommended Actions */}
      {insights?.recommended_actions?.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-text mb-3">Recommended Actions</h2>
          <div className="flex flex-col gap-3">
            {insights.recommended_actions.map((action, i) => (
              <Card key={i}>
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-medium text-text">{action.title}</span>
                    </div>
                    <p className="text-sm text-text-secondary">{action.description}</p>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <EffortBadge level={action.effort} />
                    <span className="text-xs text-text-tertiary">Impact: {action.impact}</span>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* No data state */}
      {!audit && !insights && (
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
