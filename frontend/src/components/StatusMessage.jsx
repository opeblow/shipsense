export default function StatusMessage({ type = 'info', children }) {
  const colors = {
    info: 'text-text-secondary',
    success: 'text-success',
    warning: 'text-warning',
    error: 'text-error',
  };

  return (
    <p className={`text-sm ${colors[type]} flex items-center gap-2`}>
      {children}
    </p>
  );
}
