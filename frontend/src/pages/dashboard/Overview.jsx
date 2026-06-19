import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import Card from '../../components/Card';
import Loading from '../../components/Loading';
import StatusMessage from '../../components/StatusMessage';
import { getInsights } from '../../api/client';

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
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const productId = searchParams.get('productId');

  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!productId) {
      navigate('/onboard', { replace: true });
      return;
    }

    let cancelled = false;
    async function fetchData() {
      try {
        const i = await getInsights(productId);
        if (!cancelled) {
          setInsights(i);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.response?.data?.detail || 'Failed to load dashboard data');
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
  if (error) return <StatusMessage type="error">{error}</StatusMessage>;
  if (!insights) return null;

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-xl font-semibold text-text">Overview</h1>
        <p className="text-sm text-text-secondary mt-1">Your product at a glance</p>
      </div>

      {/* AI Summary */}
      {insights?.summary && (
        <Card>
          <div className="flex items-start gap-3">
            <div className="w-7 h-7 bg-accent flex items-center justify-center flex-shrink-0 mt-0.5">
              <span className="text-xs font-bold text-white">AI</span>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-text mb-2">AI Summary</h3>
              <p className="text-sm text-text-secondary leading-relaxed">{insights.summary}</p>
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
    </div>
  );
}
