import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import Card from '../../components/Card';
import Loading from '../../components/Loading';
import StatusMessage from '../../components/StatusMessage';
import { getInsights } from '../../api/client';

function severity(priority) {
  if (priority <= 2) return 'high';
  if (priority <= 4) return 'medium';
  return 'low';
}

export default function AIInsights() {
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
        const data = await getInsights(productId);
        if (!cancelled) setInsights(data);
      } catch (err) {
        if (!cancelled) setError(err.response?.data?.detail || 'Failed to load insights');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetchData();
    return () => { cancelled = true; };
  }, [productId, navigate]);

  if (!productId) return null;
  if (loading) return <Loading text="Loading insights..." />;
  if (error) return <StatusMessage type="error">{error}</StatusMessage>;

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-xl font-semibold text-text">AI Insights</h1>
        <p className="text-sm text-text-secondary mt-1">Patterns ShipSense has detected in your user data</p>
      </div>

      {!insights?.recommended_actions?.length && !insights?.summary ? (
        <p className="text-sm text-text-tertiary">No insights available yet.</p>
      ) : (
        <div className="flex flex-col gap-3">
          {insights.summary && (
            <Card>
              <div className="flex items-start gap-3">
                <div className="w-7 h-7 bg-accent flex items-center justify-center flex-shrink-0 mt-0.5">
                  <span className="text-xs font-bold text-white">AI</span>
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-text mb-1">Summary</h3>
                  <p className="text-sm text-text-secondary leading-relaxed">{insights.summary}</p>
                </div>
              </div>
            </Card>
          )}
          {insights.recommended_actions?.map((action, i) => (
            <Card key={i}>
              <div className="flex items-start gap-3">
                <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${
                  severity(action.priority) === 'high' ? 'bg-error' : severity(action.priority) === 'medium' ? 'bg-warning' : 'bg-success'
                }`} />
                <div>
                  <h3 className="text-sm font-semibold text-text mb-1">{action.title}</h3>
                  <p className="text-sm text-text-secondary leading-relaxed">{action.description}</p>
                  <div className="flex items-center gap-2 mt-2">
                    <span className="text-xs text-text-tertiary">Effort: {action.effort}</span>
                    <span className="text-xs text-text-tertiary">Impact: {action.impact}</span>
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
