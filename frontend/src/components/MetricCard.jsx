export default function MetricCard({ label, value, change }) {
  const isPositive = change?.startsWith('+');
  const isNegative = change?.startsWith('-');

  return (
    <div className="bg-surface border border-border p-6 flex flex-col gap-1">
      <span className="text-sm text-text-secondary">{label}</span>
      <div className="flex items-baseline gap-2">
        <span className="text-2xl font-semibold text-text">{value}</span>
        {change && (
          <span className={`text-xs font-medium ${isPositive ? 'text-success' : isNegative ? 'text-error' : 'text-text-secondary'}`}>
            {change}
          </span>
        )}
      </div>
    </div>
  );
}
