import { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import Table from '../../components/Table';
import Card from '../../components/Card';
import Loading from '../../components/Loading';
import { BEHAVIOR_DATA, BAR_CHART_DATA } from '../../data/mock';

const COLUMNS = [
  { key: 'action', label: 'Action' },
  { key: 'users', label: 'Users' },
  { key: 'frequency', label: 'Frequency' },
  { key: 'dropoffAfter', label: 'Drop-off after' },
];

export default function UserBehavior() {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const t = setTimeout(() => setLoading(false), 500);
    return () => clearTimeout(t);
  }, []);

  if (loading) return <Loading text="Loading behavior data..." />;

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-xl font-semibold text-text">User Behavior</h1>
        <p className="text-sm text-text-secondary mt-1">Track how users interact with your product</p>
      </div>

      {/* Bar chart */}
      <Card>
        <h3 className="text-sm font-semibold text-text mb-4">Top 5 User Actions</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={BAR_CHART_DATA} barSize={36}>
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

      {/* Agent annotation */}
      <Card>
        <p className="text-sm text-text-secondary leading-relaxed">
          <span className="font-medium text-text">Agent note:</span> "Create Project" is your most-used feature, but 45% of users who configure an API key never return. Consider simplifying that flow.
        </p>
      </Card>

      {/* Table */}
      <Card>
        <Table columns={COLUMNS} data={BEHAVIOR_DATA} />
      </Card>
    </div>
  );
}
