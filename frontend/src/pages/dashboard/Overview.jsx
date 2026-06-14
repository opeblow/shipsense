import { useState, useEffect } from 'react';
import MetricCard from '../../components/MetricCard';
import Card from '../../components/Card';
import Loading from '../../components/Loading';
import StatusMessage from '../../components/StatusMessage';
import { METRICS, AI_SUMMARY, RECOMMENDED_ACTIONS } from '../../data/mock';

function EffortBadge({ level }) {
  const colors = {
    Low: 'text-success bg-success/5 border-success/20',
    Medium: 'text-warning bg-warning/5 border-warning/20',
    High: 'text-error bg-error/5 border-error/20',
  };
  return (
    <span className={`text-xs px-2 py-0.5 border ${colors[level] || 'text-text-secondary bg-zebra border-border'}`}>
      {level}
    </span>
  );
}

export default function Overview() {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const t = setTimeout(() => setLoading(false), 600);
    return () => clearTimeout(t);
  }, []);

  if (loading) return <Loading text="Loading dashboard..." />;

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-xl font-semibold text-text">Overview</h1>
        <p className="text-sm text-text-secondary mt-1">Your product at a glance</p>
      </div>

      {/* Metrics row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard label={METRICS.activeUsers.label} value={METRICS.activeUsers.value} change={METRICS.activeUsers.change} />
        <MetricCard label={METRICS.avgSession.label} value={METRICS.avgSession.value} change={METRICS.avgSession.change} />
        <MetricCard label={METRICS.dropoffRate.label} value={METRICS.dropoffRate.value} change={METRICS.dropoffRate.change} />
        <MetricCard label={METRICS.topAction.label} value={METRICS.topAction.value} change={METRICS.topAction.change} />
      </div>

      {/* AI Summary */}
      <Card>
        <div className="flex items-start gap-3">
          <div className="w-7 h-7 bg-accent flex items-center justify-center flex-shrink-0 mt-0.5">
            <span className="text-xs font-bold text-white">AI</span>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-text mb-2">AI Summary</h3>
            <p className="text-sm text-text-secondary leading-relaxed">{AI_SUMMARY.text}</p>
          </div>
        </div>
      </Card>

      {/* Recommended Actions */}
      <div>
        <h2 className="text-sm font-semibold text-text mb-3">Recommended Actions</h2>
        <div className="flex flex-col gap-3">
          {RECOMMENDED_ACTIONS.map((action) => (
            <Card key={action.id}>
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
    </div>
  );
}
