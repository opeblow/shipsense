import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import Button from '../../components/Button';
import Card from '../../components/Card';
import Loading from '../../components/Loading';
import StatusMessage from '../../components/StatusMessage';
import {
  evaluateExperiment,
  listExperiments,
  refreshAudit,
  shipExperiment,
} from '../../api/client';

function Result({ result }) {
  if (!result) return null;
  if (result.conclusion === 'insufficient_data' || result.conclusion === 'missing_measurement') {
    return <StatusMessage type="warning">{result.message}</StatusMessage>;
  }
  const positive = result.conclusion === 'improved';
  return (
    <div className={`border p-4 ${positive ? 'border-success/30 bg-success/5' : 'border-warning/30 bg-warning/5'}`}>
      <p className={`text-sm font-medium ${positive ? 'text-success' : 'text-warning'}`}>
        {result.conclusion.replaceAll('_', ' ')}
      </p>
      {result.current !== undefined && (
        <p className="text-sm text-text-secondary mt-1">
          Baseline {result.baseline} → current {result.current} ({result.change >= 0 ? '+' : ''}{result.change} {result.unit})
        </p>
      )}
      {result.recommendation && (
        <p className="text-xs text-text-tertiary mt-2">
          Recommendation: {result.recommendation}
        </p>
      )}
    </div>
  );
}

export default function Experiments() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const productId = searchParams.get('productId');
  const [experiments, setExperiments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [workingId, setWorkingId] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    if (!productId) {
      navigate('/onboard', { replace: true });
      return;
    }
    listExperiments(productId)
      .then(setExperiments)
      .catch((err) => setError(err.response?.data?.detail || 'Failed to load experiments'))
      .finally(() => setLoading(false));
  }, [productId, navigate]);

  const replaceExperiment = (updated) => {
    setExperiments((current) => current.map((item) => (
      item.id === updated.id ? updated : item
    )));
  };

  const handleShip = async (experimentId) => {
    setWorkingId(experimentId);
    setError('');
    try {
      replaceExperiment(await shipExperiment(experimentId));
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to mark experiment as shipped');
    } finally {
      setWorkingId('');
    }
  };

  const handleEvaluate = async (experiment) => {
    setWorkingId(experiment.id);
    setError('');
    try {
      if (experiment.target_metric.startsWith('technical_audit:')) {
        await refreshAudit(productId);
      }
      replaceExperiment(await evaluateExperiment(experiment.id));
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to evaluate experiment');
    } finally {
      setWorkingId('');
    }
  };

  if (!productId) return null;
  if (loading) return <Loading text="Loading experiments..." />;

  const evaluatedCount = experiments.filter((experiment) => experiment.status === 'evaluated').length;
  const collectingCount = experiments.filter((experiment) => experiment.status === 'collecting').length;
  const plannedCount = experiments.filter((experiment) => experiment.status === 'planned').length;

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-xl font-semibold text-text">Experiments</h1>
        <p className="text-sm text-text-secondary mt-1">
          Freeze the baseline, ship one change, and verify the result
        </p>
      </div>

      {error && <StatusMessage type="error">{error}</StatusMessage>}

      {experiments.length > 0 && (
        <Card>
          <div className="grid gap-3 sm:grid-cols-4">
            <div>
              <p className="text-2xl font-bold text-text">{experiments.length}</p>
              <p className="text-xs text-text-tertiary mt-0.5">Total loops</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-text">{plannedCount}</p>
              <p className="text-xs text-text-tertiary mt-0.5">Planned</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-text">{collectingCount}</p>
              <p className="text-xs text-text-tertiary mt-0.5">Collecting</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-text">{evaluatedCount}</p>
              <p className="text-xs text-text-tertiary mt-0.5">Evaluated</p>
            </div>
          </div>
          <p className="text-sm text-text-secondary mt-4">
            Each experiment is created from a decision, keeps the original baseline, and evaluates against the same target metric after shipping.
          </p>
        </Card>
      )}

      {experiments.length === 0 && (
        <Card>
          <p className="text-sm font-medium text-text">No experiments yet</p>
          <p className="text-sm text-text-secondary mt-2">
            Create one from the current Decision Card on Today.
          </p>
          <div className="mt-4">
            <Button variant="secondary" onClick={() => navigate(`/dashboard?productId=${productId}`)}>
              Go to Today
            </Button>
          </div>
        </Card>
      )}

      {experiments.map((experiment) => (
        <Card key={experiment.id}>
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="max-w-2xl">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs uppercase tracking-wider text-text-tertiary">
                  {experiment.status}
                </span>
                <span className="text-xs text-text-tertiary">Baseline: {experiment.baseline_value}</span>
              </div>
              <h2 className="text-lg font-semibold text-text">{experiment.name}</h2>
              <p className="text-sm text-text-secondary mt-2 leading-relaxed">
                {experiment.hypothesis}
              </p>
              <p className="text-xs text-text-tertiary mt-3 break-words">
                Target metric: {experiment.target_metric}
              </p>
            </div>
            <div className="flex gap-2">
              {experiment.status === 'planned' && (
                <Button
                  onClick={() => handleShip(experiment.id)}
                  disabled={workingId === experiment.id}
                >
                  {workingId === experiment.id ? 'Saving...' : 'Mark shipped'}
                </Button>
              )}
              {['collecting', 'inconclusive', 'evaluated'].includes(experiment.status) && (
                <Button
                  variant="secondary"
                  onClick={() => handleEvaluate(experiment)}
                  disabled={workingId === experiment.id}
                >
                  {workingId === experiment.id ? 'Evaluating...' : 'Evaluate now'}
                </Button>
              )}
            </div>
          </div>
          {experiment.shipped_at && (
            <p className="text-xs text-text-tertiary mt-4">
              Shipped {new Date(experiment.shipped_at).toLocaleString()}
            </p>
          )}
          <div className="mt-5">
            <Result result={experiment.result} />
          </div>
        </Card>
      ))}
    </div>
  );
}
