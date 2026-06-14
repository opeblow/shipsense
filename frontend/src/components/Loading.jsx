export default function Loading({ text = 'Loading...' }) {
  return (
    <div className="flex items-center gap-3 py-8">
      <span className="w-4 h-4 border border-border border-t-accent rounded-full animate-spin" />
      <span className="text-sm text-text-secondary">{text}</span>
    </div>
  );
}
