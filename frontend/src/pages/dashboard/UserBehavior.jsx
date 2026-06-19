import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import Table from '../../components/Table';
import Card from '../../components/Card';
import Loading from '../../components/Loading';
import StatusMessage from '../../components/StatusMessage';
import { getBehavior } from '../../api/client';

const COLUMNS = [
  { key: 'action', label: 'Action' },
  { key: 'users', label: 'Users' },
  { key: 'frequency', label: 'Frequency' },
  { key: 'dropoffAfter', label: 'Drop-off after' },
];

export default function UserBehavior() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const productId = searchParams.get('productId');

  const [behavior, setBehavior] = useState(null);
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
        const data = await getBehavior(productId);
        if (!cancelled) setBehavior(data);
      } catch (err) {
        if (!cancelled) setError(err.response?.data?.detail || 'Failed to load behavior data');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetchData();
    return () => { cancelled = true; };
  }, [productId, navigate]);

  if (!productId) return null;
  if (loading) return <Loading text="Loading behavior data..." />;
  if (error) return <StatusMessage type="error">{error}</StatusMessage>;
  if (!behavior) return null;

  const chartData = behavior.top_actions?.map((a) => ({
    action: a.action,
    count: a.users,
  })) || [];

  const tableData = behavior.top_actions?.map((a) => ({
    action: a.action,
    users: a.users.toLocaleString(),
    frequency: a.frequency,
    dropoffAfter: a.dropoff_after,
  })) || [];

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-xl font-semibold text-text">User Behavior</h1>
        <p className="text-sm text-text-secondary mt-1">Track how users interact with your product</p>
      </div>

      {/* Bar chart */}
      {chartData.length > 0 && (
        <Card>
          <h3 className="text-sm font-semibold text-text mb-4">Top User Actions</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} barSize={36}>
                <XAxis
                  dataKey="action"
                  axisLine={{ stroke: '#e5e5e5' }}
                  tickLine={false}
                  tick={{ fontSize: 12, fill: '#6b6b6b' }}
                />
                <YAxis
                  axisLine={false}
                  tickLine={false}
                  tick={{ fontSize: 12, fill: '#6b6b6b' }}
                />
                <Tooltip
                  contentStyle={{ background: '#fff', border: '1px solid #e5e5e5', borderRadius: 0, fontSize: 13 }}
                  cursor={{ fill: '#f7f7f7' }}
                />
                <Bar dataKey="count" fill="#5b6af0" radius={[0, 0, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}

      {/* Summary card */}
      <Card>
        <div className="flex flex-col gap-1">
          <p className="text-sm text-text-secondary">
            <span className="font-medium text-text">Active users:</span> {behavior.active_users?.toLocaleString()}
          </p>
          <p className="text-sm text-text-secondary">
            <span className="font-medium text-text">Avg session:</span> {behavior.avg_session}
          </p>
        </div>
      </Card>

      {/* Table */}
      {tableData.length > 0 && (
        <Card>
          <Table columns={COLUMNS} data={tableData} />
        </Card>
      )}
    </div>
  );
}
