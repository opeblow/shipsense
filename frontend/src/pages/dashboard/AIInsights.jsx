import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import Card from '../../components/Card';
import Loading from '../../components/Loading';
import StatusMessage from '../../components/StatusMessage';
import { getInsights, getAudit } from '../../api/client';

function PriorityDot({ priority }) {
  const cls = priority <= 2
    ? 'bg-red-500'
    : priority <= 4 ? 'bg-amber-400' : 'bg-emerald-500';
  return <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${cls}`} />;
}

function OpportunityRow({ title, savingsMs }) {
  const secs = (savingsMs / 1000).toFixed(1);
  const barWidth = Math.min(100, Math.round(savingsMs / 30));
  return (
    <div className="py-2 border-b border-border last:border-0">
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm text-text">{title}</span>
        <span className="text-xs font-mono text-amber-600">−{secs}s</span>
      </div>
      <div className="h-1.5 bg-border rounded-full overflow-hidden">
        <div className="h-full bg-amber-400 rounded-full" style={{ width: `${barWidth}%` }} />
      </div>
    </div>
  );
}

export default function AIInsights() {
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
  if (loading) return <Loading text="Loading insights..." />;

  const a = audit || {};
  const opportunities = a.pagespeed_opportunities?.filter(o => o.savings_ms > 100) || [];
  const diagnostics = a.pagespeed_diagnostics || [];
  const headingIssues = a.heading_issues || [];
  const trackingTools = a.tracking_tools || [];

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-xl font-semibold text-text">AI Insights</h1>
        <p className="text-sm text-text-secondary mt-1">
          Every finding below is backed by a real, measured data point from your live URL
        </p>
      </div>

      {error && <StatusMessage type="error">{error}</StatusMessage>}

      {/* Main AI analysis card */}
      {insights?.summary && (
        <Card>
          <div className="flex items-start gap-3">
            <div className="w-7 h-7 bg-accent flex items-center justify-center flex-shrink-0 mt-0.5 rounded">
              <span className="text-xs font-bold text-white">AI</span>
            </div>
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-text mb-2">Top Finding</h3>
              <p className="text-sm text-text-secondary leading-relaxed whitespace-pre-line">{insights.summary}</p>
            </div>
          </div>
        </Card>
      )}

      {/* Recommended actions */}
      {insights?.recommended_actions?.length > 0 && (
        <div className="flex flex-col gap-3">
          {insights.recommended_actions.map((action, i) => (
            <Card key={i}>
              <div className="flex items-start gap-3">
                <PriorityDot priority={action.priority} />
                <div>
                  <h3 className="text-sm font-semibold text-text mb-1">{action.title}</h3>
                  <p className="text-sm text-text-secondary leading-relaxed">{action.description}</p>
                  <div className="flex items-center gap-3 mt-2">
                    <span className="text-xs text-text-tertiary">Effort: <strong>{action.effort}</strong></span>
                    <span className="text-xs text-text-tertiary">Impact: <strong>{action.impact}</strong></span>
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* PageSpeed Opportunities (real ms savings from actual audit) */}
      {opportunities.length > 0 && (
        <Card>
          <h2 className="text-sm font-semibold text-text mb-4">
            Speed Opportunities{' '}
            <span className="text-text-tertiary font-normal">(real savings from PageSpeed audit)</span>
          </h2>
          {opportunities.slice(0, 8).map((o, i) => (
            <OpportunityRow key={i} title={o.title} savingsMs={o.savings_ms} />
          ))}
        </Card>
      )}

      {/* Heading / SEO issues */}
      {headingIssues.length > 0 && (
        <Card>
          <h2 className="text-sm font-semibold text-text mb-3">SEO / Heading Issues</h2>
          <ul className="space-y-1">
            {headingIssues.map((issue, i) => (
              <li key={i} className="text-sm text-red-600 flex items-center gap-2">
                <span>🔴</span> {issue}
              </li>
            ))}
          </ul>
        </Card>
      )}

      {/* Tracking Inventory */}
      {trackingTools.length > 0 && (
        <Card>
          <h2 className="text-sm font-semibold text-text mb-3">
            Tracking Tools Detected ({a.tracking_script_count})
          </h2>
          <div className="flex flex-wrap gap-2">
            {trackingTools.map(t => (
              <span key={t} className="text-xs bg-surface border border-border px-2 py-0.5 rounded text-text-secondary">
                {t}
              </span>
            ))}
          </div>
          {a.tracking_script_count > 8 && (
            <p className="text-xs text-amber-600 mt-3">
              ⚠️ {a.tracking_script_count} tracking scripts can slow page load and impact privacy compliance.
            </p>
          )}
        </Card>
      )}

      {/* Security summary */}
      {a.security_headers && (
        <Card>
          <h2 className="text-sm font-semibold text-text mb-3">
            Security Headers — Score: {a.security_headers.security_score}/100
          </h2>
          <div className="grid grid-cols-2 gap-2">
            {[
              { key: 'has_hsts', label: 'HSTS' },
              { key: 'has_csp', label: 'CSP' },
              { key: 'has_xframe', label: 'X-Frame-Options' },
              { key: 'has_xcontent', label: 'X-Content-Type' },
              { key: 'has_referrer_policy', label: 'Referrer-Policy' },
              { key: 'has_permissions_policy', label: 'Permissions-Policy' },
            ].map(({ key, label }) => (
              <div key={key} className="flex items-center gap-2">
                <span>{a.security_headers[key] ? '🟢' : '🔴'}</span>
                <span className="text-sm text-text-secondary">{label}</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Diagnostics */}
      {diagnostics.length > 0 && (
        <Card>
          <h2 className="text-sm font-semibold text-text mb-3">PageSpeed Diagnostics</h2>
          <div className="space-y-2">
            {diagnostics.map((d, i) => (
              <div key={i} className="flex items-center justify-between">
                <span className="text-sm text-text-secondary">{d.title}</span>
                <span className="text-xs font-mono text-red-600">{d.score}/100</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {!insights && !audit && (
        <p className="text-sm text-text-tertiary">
          No audit data yet.{' '}
          <button
            onClick={() => navigate('/onboard')}
            className="text-accent underline hover:no-underline cursor-pointer bg-transparent border-none p-0"
          >
            Run a live audit →
          </button>
        </p>
      )}
    </div>
  );
}
