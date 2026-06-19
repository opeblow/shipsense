import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import Table from '../../components/Table';
import Card from '../../components/Card';
import Loading from '../../components/Loading';
import StatusMessage from '../../components/StatusMessage';
import { getBehavior, getAudit } from '../../api/client';

const COLUMNS = [
  { key: 'action', label: 'Action' },
  { key: 'users', label: 'Users (real)' },
  { key: 'frequency', label: 'Frequency' },
  { key: 'dropoffAfter', label: 'Drop-off after' },
];

const DROP_COLS = [
  { key: 'step', label: 'Step' },
  { key: 'next_step', label: 'Next Step' },
  { key: 'users_who_reached', label: 'Reached' },
  { key: 'users_who_continued', label: 'Continued' },
  { key: 'drop_off_rate', label: 'Drop-off Rate' },
];

const BAR_COLORS = ['#5b6af0', '#7c84f5', '#9ea4f8', '#bfc3fb', '#dfe1fd'];

export default function UserBehavior() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const productId = searchParams.get('productId');

  const [behavior, setBehavior] = useState(null);
  const [audit, setAudit] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!productId) { navigate('/onboard', { replace: true }); return; }

    let cancelled = false;
    async function fetchData() {
      try {
        const [beh, aud] = await Promise.allSettled([
          getBehavior(productId),
          getAudit(productId),
        ]);
        if (!cancelled) {
          if (beh.status === 'fulfilled') setBehavior(beh.value);
          else setError(beh.reason?.response?.data?.detail || 'Failed to load behavior data');
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
  if (loading) return <Loading text="Loading behavior data..." />;

  const hasRealEvents = behavior?.active_users > 0 || behavior?.top_actions?.length > 0;

  const chartData = behavior?.top_actions?.map((a) => ({
    action: a.action.length > 18 ? a.action.slice(0, 18) + '…' : a.action,
    count: a.users,
  })) || [];

  const tableData = behavior?.top_actions?.map((a) => ({
    action: a.action,
    users: typeof a.users === 'number' ? a.users.toLocaleString() : a.users,
    frequency: a.frequency,
    dropoffAfter: a.dropoff_after,
  })) || [];

  const a = audit || {};

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-xl font-semibold text-text">User Behavior</h1>
        <p className="text-sm text-text-secondary mt-1">
          Real events from the Novus tracker — zero simulated data
        </p>
      </div>

      {error && <StatusMessage type="error">{error}</StatusMessage>}

      {/* No real events yet */}
      {!hasRealEvents && (
        <Card>
          <div className="flex flex-col gap-3">
            <p className="text-sm font-medium text-text">
              No user events recorded yet
            </p>
            <p className="text-sm text-text-secondary leading-relaxed">
              Install the Novus tracker snippet on your site to start collecting real click, navigation,
              and interaction data. Once users trigger events, this page will show their actual behavior —
              top actions, drop-off points, session length, and more.
            </p>
            <p className="text-sm text-text-secondary">
              In the meantime, the{' '}
              <button
                onClick={() => navigate(`/dashboard/insights?productId=${productId}`)}
                className="text-accent underline hover:no-underline bg-transparent border-none p-0 cursor-pointer"
              >
                AI Insights tab
              </button>{' '}
              shows real findings from the live PageSpeed &amp; HTML audit of your URL.
            </p>
          </div>
        </Card>
      )}

      {/* Real event bar chart */}
      {chartData.length > 0 && (
        <Card>
          <h3 className="text-sm font-semibold text-text mb-1">Top User Actions</h3>
          <p className="text-xs text-text-tertiary mb-4">From real Novus tracker events</p>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} barSize={36}>
                <XAxis
                  dataKey="action"
                  axisLine={{ stroke: '#e5e5e5' }}
                  tickLine={false}
                  tick={{ fontSize: 11, fill: '#6b6b6b' }}
                />
                <YAxis
                  axisLine={false}
                  tickLine={false}
                  tick={{ fontSize: 12, fill: '#6b6b6b' }}
                  allowDecimals={false}
                />
                <Tooltip
                  contentStyle={{ background: '#fff', border: '1px solid #e5e5e5', borderRadius: 4, fontSize: 13 }}
                  cursor={{ fill: '#f7f7f7' }}
                  formatter={(val) => [val.toLocaleString(), 'Users']}
                />
                <Bar dataKey="count" radius={[2, 2, 0, 0]}>
                  {chartData.map((_, i) => (
                    <Cell key={i} fill={BAR_COLORS[i % BAR_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}

      {/* Real session stats */}
      {hasRealEvents && (
        <Card>
          <h3 className="text-sm font-semibold text-text mb-3">Session Stats (real)</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-2xl font-bold text-text">{behavior.active_users?.toLocaleString()}</p>
              <p className="text-xs text-text-tertiary mt-0.5">Active users (last 7 days)</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-text">{behavior.avg_session}</p>
              <p className="text-xs text-text-tertiary mt-0.5">Avg session duration</p>
            </div>
          </div>
        </Card>
      )}

      {/* Real drop-off table */}
      {behavior?.drop_off_points?.length > 0 && (
        <Card>
          <h3 className="text-sm font-semibold text-text mb-4">Drop-off Points (real)</h3>
          <Table columns={DROP_COLS} data={behavior.drop_off_points} />
        </Card>
      )}

      {/* Real top actions table */}
      {tableData.length > 0 && (
        <Card>
          <h3 className="text-sm font-semibold text-text mb-4">Action Breakdown (real)</h3>
          <Table columns={COLUMNS} data={tableData} />
        </Card>
      )}

      {/* Real structural signals from audit (always available) */}
      {audit && (
        <Card>
          <h3 className="text-sm font-semibold text-text mb-1">Structural Signals</h3>
          <p className="text-xs text-text-tertiary mb-4">
            From live HTML audit of your URL — proxy indicators for UX friction
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {[
              { label: 'Form fields', value: a.form_field_count, warn: v => v > 6 },
              { label: 'CTAs', value: a.cta_count, warn: v => v === 0 },
              { label: 'Submit buttons', value: a.submit_button_count },
              { label: 'Tracking scripts', value: a.tracking_script_count, warn: v => v > 8 },
              { label: 'Render-blocking', value: a.render_blocking_resources, warn: v => v > 3 },
              { label: 'Images missing alt', value: a.images_missing_alt, warn: v => v > 0 },
              { label: 'Internal links', value: a.internal_link_count },
              { label: 'External links', value: a.external_link_count },
              { label: 'Word count', value: a.word_count },
            ].filter(item => item.value !== undefined && item.value !== null).map(({ label, value, warn }) => {
              const isWarn = warn && warn(value);
              return (
                <div key={label} className={`p-3 border rounded ${isWarn ? 'border-amber-200 bg-amber-50' : 'border-border bg-surface'}`}>
                  <p className={`text-lg font-bold ${isWarn ? 'text-amber-700' : 'text-text'}`}>
                    {typeof value === 'number' ? value.toLocaleString() : value}
                  </p>
                  <p className="text-xs text-text-tertiary mt-0.5">{label}</p>
                </div>
              );
            })}
          </div>
          {a.has_guest_checkout !== undefined && (
            <p className="text-sm text-text-secondary mt-4">
              {a.has_guest_checkout ? '🟢' : '🔴'} Guest checkout: <strong>{a.has_guest_checkout ? 'Available' : 'Not detected'}</strong>
            </p>
          )}
          {a.has_search !== undefined && (
            <p className="text-sm text-text-secondary mt-1">
              {a.has_search ? '🟢' : '⚪'} Search: <strong>{a.has_search ? 'Present' : 'Not detected'}</strong>
            </p>
          )}
        </Card>
      )}
    </div>
  );
}
